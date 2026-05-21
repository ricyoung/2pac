import os
import struct
import io
import shutil
import tempfile
import subprocess
import logging

from PIL import Image

from find_bad_images.config import SUPPORTED_FORMATS, REPAIRABLE_FORMATS
from find_bad_images.security import validate_subprocess_path


def diagnose_image_issue(file_path):
    """
    Attempts to diagnose what's wrong with the image.
    Returns: (error_type, details)
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)

        if len(header) == 0:
            return "empty_file", "File is empty (0 bytes)"

        if file_path.lower().endswith(SUPPORTED_FORMATS['JPEG']):
            if not (header.startswith(b'\xff\xd8\xff')):
                return "invalid_header", "Invalid JPEG header"

        elif file_path.lower().endswith(SUPPORTED_FORMATS['PNG']):
            if not header.startswith(b'\x89PNG\r\n\x1a\n'):
                return "invalid_header", "Invalid PNG header"

        try:
            with Image.open(file_path) as img:
                img.verify()
        except Exception as e:
            error_str = str(e).lower()

            if "truncated" in error_str:
                return "truncated", "File is truncated"
            elif "corrupt" in error_str:
                return "corrupt_data", "Data corruption detected"
            elif "incorrect mode" in error_str or "decoder" in error_str:
                return "decoder_issue", "Image decoder issue"
            else:
                return "unknown", f"Unknown issue: {str(e)}"

        try:
            with Image.open(file_path) as img:
                img.load()
        except Exception as e:
            return "data_load_failed", f"Image data couldn't be loaded: {str(e)}"

        return "unknown", "Unknown issue"

    except Exception as e:
        return "access_error", f"Error accessing file: {str(e)}"


def check_jpeg_structure(file_path):
    """
    Performs a deep check of JPEG file structure to find corruption that PIL might miss.
    Returns (is_valid, error_message)
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        if not data.startswith(b'\xFF\xD8'):
            return False, "Invalid JPEG header (missing SOI marker)"

        if not data.endswith(b'\xFF\xD9'):
            return False, "Missing EOI marker at end of file"

        sof_markers = [b'\xFF\xC0', b'\xFF\xC1', b'\xFF\xC2', b'\xFF\xC3']
        has_sof = any(marker in data for marker in sof_markers)
        if not has_sof:
            return False, "No Start of Frame (SOF) marker found"

        if b'\xFF\xDA' not in data:
            return False, "No Start of Scan (SOS) marker found"

        i = 2
        while i < len(data) - 1:
            if data[i] == 0xFF and data[i+1] != 0x00 and data[i+1] != 0xFF:
                marker = data[i:i+2]

                if (0xC0 <= data[i+1] <= 0xCF and data[i+1] != 0xC4 and data[i+1] != 0xC8) or \
                   (0xDB <= data[i+1] <= 0xFE):
                    if i + 4 >= len(data):
                        return False, f"Truncated marker {data[i+1]:02X} at position {i}"
                    length = struct.unpack('>H', data[i+2:i+4])[0]
                    if i + 2 + length > len(data):
                        return False, f"Invalid segment length for marker {data[i+1]:02X}"
                    i += 2 + length
                    continue

            i += 1

        return True, "JPEG structure appears valid"
    except Exception as e:
        return False, f"Error during JPEG structure check: {str(e)}"


def check_png_structure(file_path):
    """
    Performs a deep check of PNG file structure to find corruption.
    Returns (is_valid, error_message)
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        png_signature = b'\x89PNG\r\n\x1a\n'
        if not data.startswith(png_signature):
            return False, "Invalid PNG signature"

        if len(data) < 8 + 12:
            return False, "PNG file too small to contain valid header"

        if not data.endswith(b'IEND\xaeB`\x82'):
            return False, "Missing IEND chunk at end of file"

        pos = 8
        required_chunks = {'IHDR': False}

        while pos < len(data):
            if pos + 8 > len(data):
                return False, "Truncated chunk header"

            chunk_len = struct.unpack('>I', data[pos:pos+4])[0]
            chunk_type = data[pos+4:pos+8].decode('ascii', errors='replace')

            if pos + chunk_len + 12 > len(data):
                return False, f"Truncated {chunk_type} chunk"

            if chunk_type in required_chunks:
                required_chunks[chunk_type] = True

            if chunk_type == 'IHDR' and chunk_len != 13:
                return False, "Invalid IHDR chunk length"

            if pos == 8 and chunk_type != 'IHDR':
                return False, "First chunk must be IHDR"

            if chunk_type == 'IEND' and pos + chunk_len + 12 != len(data):
                return False, "Data after IEND chunk"

            pos += chunk_len + 12

        for chunk, present in required_chunks.items():
            if not present:
                return False, f"Missing required {chunk} chunk"

        return True, "PNG structure appears valid"
    except Exception as e:
        return False, f"Error during PNG structure check: {str(e)}"


def try_external_tools(file_path):
    """
    Try using external tools to validate the image if they're available.
    Returns (is_valid, message)

    Security: Validates file path before passing to subprocess to prevent
    command injection attacks.
    """
    try:
        validate_subprocess_path(file_path)
    except ValueError as e:
        logging.warning(f"Skipping external tool validation due to security check: {e}")
        return True, "External tools check skipped (security)"

    try:
        result = subprocess.run(['exiftool', '-m', '-p', '$Error', file_path],
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return False, f"Exiftool error: {result.stdout.strip()}"

        result = subprocess.run(['identify', '-verbose', file_path],
                               capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return False, "ImageMagick identify failed to read the image"

        return True, "Passed external tool validation"
    except (subprocess.SubprocessError, FileNotFoundError):
        return True, "External tools check skipped"


def try_full_decode_check(file_path):
    """
    Try to fully decode the image to a temporary file.
    This catches more subtle corruption that might otherwise be missed.
    """
    try:
        with Image.open(file_path) as img:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                img.save(tmp.name, format="BMP")

                return True, "Full decode test passed"
    except Exception as e:
        return False, f"Full decode test failed: {str(e)}"


def check_visual_corruption(file_path, block_threshold=0.20, uniform_threshold=10, strict_mode=False):
    """
    Analyze image content to detect visual corruption like large uniform areas.

    Args:
        file_path: Path to the image file
        block_threshold: Percentage of image that must be uniform to be considered corrupt (0.0-1.0)
        uniform_threshold: Color variation threshold for considering pixels "uniform"
        strict_mode: If True, only detect gray/black areas as corruption indicators

    Returns:
        (is_visually_corrupt, details)
    """
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            total_pixels = width * height

            if img.mode != "RGB":
                img = img.convert("RGB")

            sample_step = max(1, min(width, height) // 150)

            color_counts = {}
            total_samples = 0

            for y in range(0, height, sample_step):
                for x in range(0, width, sample_step):
                    total_samples += 1
                    pixel = img.getpixel((x, y))

                    rounded_pixel = (
                        pixel[0] // uniform_threshold * uniform_threshold,
                        pixel[1] // uniform_threshold * uniform_threshold,
                        pixel[2] // uniform_threshold * uniform_threshold
                    )

                    if rounded_pixel in color_counts:
                        color_counts[rounded_pixel] += 1
                    else:
                        color_counts[rounded_pixel] = 1

            most_common_color = max(color_counts.items(), key=lambda x: x[1])
            most_common_percentage = most_common_color[1] / total_samples

            if most_common_percentage > block_threshold:
                affected_pct = most_common_percentage * 100
                color_value = most_common_color[0]

                is_dark = sum(color_value) < 3 * uniform_threshold

                is_gray = abs(color_value[0] - color_value[1]) < uniform_threshold and \
                          abs(color_value[1] - color_value[2]) < uniform_threshold and \
                          abs(color_value[0] - color_value[2]) < uniform_threshold

                is_mid_gray = is_gray and 30 < sum(color_value)/3 < 220

                is_white = color_value[0] > 240 and color_value[1] > 240 and color_value[2] > 240

                if (is_dark or is_mid_gray) and not is_white:
                    white_threshold = 0.4
                    if is_white and most_common_percentage < white_threshold:
                        return False, f"Large white area ({affected_pct:.1f}%) but likely not corruption"

                    return True, f"Visual corruption detected: {affected_pct:.1f}% of image is uniform {color_value}"
                else:
                    return False, f"Large uniform area ({affected_pct:.1f}%) but likely not corruption"

            if strict_mode:
                if len(color_counts) > total_samples * 0.85 and total_samples > 200:
                    return True, f"Excessive color fragmentation detected ({len(color_counts)} colors in {total_samples} samples)"

                if total_samples > 500:
                    sorted_counts = sorted(color_counts.values(), reverse=True)

                    if len(sorted_counts) > 5:
                        top5_ratio = sum(sorted_counts[:5]) / sum(sorted_counts)
                        if top5_ratio < 0.2 and most_common_percentage < 0.1:
                            return True, f"Unusual color distribution (possible noise/corruption)"

            return False, "No visual corruption detected"

    except Exception as e:
        return False, f"Error during visual analysis: {str(e)}"


def is_valid_image(file_path, thorough=True, sensitivity='medium', ignore_eof=False, check_visual=False, visual_strictness='medium'):
    """
    Validate image file integrity using multiple methods.

    Args:
        file_path: Path to the image file
        thorough: Whether to perform deep structure validation
        sensitivity: 'low', 'medium', or 'high'
        ignore_eof: Whether to ignore missing end-of-file markers
        check_visual: Whether to perform visual content analysis to detect corruption
        visual_strictness: 'low', 'medium', or 'high' strictness for visual corruption detection

    Returns:
        True if valid, False if corrupt.
    """
    try:
        with Image.open(file_path) as img:
            img.verify()

            with Image.open(file_path) as img2:
                img2.load()

            if check_visual:
                if visual_strictness == 'low':
                    block_threshold = 0.3
                    uniform_threshold = 5
                elif visual_strictness == 'high':
                    block_threshold = 0.15
                    uniform_threshold = 15
                else:
                    block_threshold = 0.20
                    uniform_threshold = 10

                is_visually_corrupt, msg = check_visual_corruption(
                    file_path,
                    block_threshold=block_threshold,
                    uniform_threshold=uniform_threshold,
                    strict_mode=(visual_strictness == 'high')
                )

                if is_visually_corrupt:
                    logging.debug(f"Visual corruption detected in {file_path}: {msg}")
                    return False

            if not thorough or sensitivity == 'low':
                return True

            if file_path.lower().endswith(tuple(SUPPORTED_FORMATS['JPEG'])):
                is_valid, error_msg = check_jpeg_structure(file_path)
                if not is_valid:
                    if ignore_eof and error_msg == "Missing EOI marker at end of file":
                        logging.debug(f"Ignoring missing EOI marker for {file_path} as requested")
                    else:
                        logging.debug(f"JPEG structure invalid for {file_path}: {error_msg}")
                        return False

                is_valid, error_msg = try_full_decode_check(file_path)
                if not is_valid:
                    logging.debug(f"Full decode test failed for {file_path}: {error_msg}")
                    return False

                is_valid, error_msg = try_external_tools(file_path)
                if not is_valid:
                    logging.debug(f"External tool validation failed for {file_path}: {error_msg}")
                    return False

            elif file_path.lower().endswith(tuple(SUPPORTED_FORMATS['PNG'])):
                is_valid, error_msg = check_png_structure(file_path)
                if not is_valid:
                    logging.debug(f"PNG structure invalid for {file_path}: {error_msg}")
                    return False

                is_valid, error_msg = try_full_decode_check(file_path)
                if not is_valid:
                    logging.debug(f"Full decode test failed for {file_path}: {error_msg}")
                    return False

            return True
    except Exception as e:
        logging.debug(f"Invalid image {file_path}: {str(e)}")
        return False


def attempt_repair(file_path, backup_dir=None):
    """
    Attempts to repair corrupt image files.
    Returns: (success, message, fixed_width, fixed_height)
    """
    if backup_dir:
        backup_path = os.path.join(backup_dir, os.path.basename(file_path) + ".bak")
        try:
            shutil.copy2(file_path, backup_path)
            logging.debug(f"Created backup at {backup_path}")
        except Exception as e:
            logging.warning(f"Could not create backup: {str(e)}")

    try:
        issue_type, details = diagnose_image_issue(file_path)
        logging.debug(f"Diagnosis for {file_path}: {issue_type} - {details}")

        file_ext = os.path.splitext(file_path)[1].lower()

        format_supported = False
        for fmt in REPAIRABLE_FORMATS:
            if file_ext in SUPPORTED_FORMATS[fmt]:
                format_supported = True
                break

        if not format_supported:
            return False, f"Format not supported for repair ({file_ext})", None, None

        try:
            with Image.open(file_path) as img:
                width, height = img.size
                format = img.format

                buffer = io.BytesIO()
                img.save(buffer, format=format)

                with open(file_path, 'wb') as f:
                    f.write(buffer.getvalue())

                if is_valid_image(file_path):
                    return True, f"Repaired {issue_type} issue", width, height
                else:
                    if format == 'JPEG':
                        with Image.open(file_path) as img:
                            buffer = io.BytesIO()
                            img.save(buffer, format='JPEG', optimize=True, quality=85)
                            with open(file_path, 'wb') as f:
                                f.write(buffer.getvalue())

                            if is_valid_image(file_path):
                                return True, f"Repaired {issue_type} issue with JPEG optimization", width, height

                    return False, f"Failed to repair {issue_type} issue", None, None

        except Exception as e:
            logging.debug(f"Repair attempt failed for {file_path}: {str(e)}")
            return False, f"Repair failed: {str(e)}", None, None

    except Exception as e:
        logging.debug(f"Error during repair of {file_path}: {str(e)}")
        return False, f"Repair error: {str(e)}", None, None
