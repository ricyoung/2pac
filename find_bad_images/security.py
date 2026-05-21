import os
import hashlib
import re
import logging

from PIL import Image, UnidentifiedImageError
import humanize

from find_bad_images.config import SUPPORTED_FORMATS, MAX_FILE_SIZE, MAX_IMAGE_PIXELS


def validate_subprocess_path(file_path):
    """
    Validate file path before passing to subprocess to prevent command injection.

    Args:
        file_path: Path to validate

    Returns:
        True if path is safe

    Raises:
        ValueError: If path contains dangerous characters or patterns
    """
    if not os.path.isabs(file_path):
        raise ValueError(f"Path must be absolute: {file_path}")

    if not os.path.exists(file_path):
        raise ValueError(f"File does not exist: {file_path}")

    dangerous_chars = ['`', '$', '&', '|', ';', '>', '<', '\n', '\r', '(', ')']
    for char in dangerous_chars:
        if char in file_path:
            raise ValueError(f"Dangerous character '{char}' found in path: {file_path}")

    if '..' in file_path:
        raise ValueError(f"Path traversal pattern '..' detected: {file_path}")

    if '\x00' in file_path:
        raise ValueError("Null byte detected in path")

    return True


def validate_file_security(file_path, check_size=True, check_dimensions=True):
    """
    Perform security validation on a file before processing.

    Args:
        file_path: Path to the file
        check_size: Whether to check file size limits
        check_dimensions: Whether to check image dimension limits

    Returns:
        (is_safe, warnings) - tuple of boolean and list of warning messages

    Raises:
        ValueError: If file fails critical security checks
    """
    warnings = []

    if not os.path.exists(file_path):
        raise ValueError(f"File does not exist: {file_path}")

    if check_size:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({file_size} bytes, max {MAX_FILE_SIZE}). "
                           f"This could indicate a malicious file or decompression bomb.")

        if file_size > 10 * 1024 * 1024:
            warnings.append(f"Large file size: {humanize.naturalsize(file_size)}")

    if check_dimensions:
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                total_pixels = width * height

                if total_pixels > MAX_IMAGE_PIXELS:
                    raise ValueError(f"Image dimensions too large ({width}x{height} = {total_pixels} pixels, "
                                   f"max {MAX_IMAGE_PIXELS}). This could be a decompression bomb attack.")

                if total_pixels > 10000 * 10000:
                    warnings.append(f"Large image dimensions: {width}x{height}")

                actual_format = img.format
                expected_formats = []
                for fmt, extensions in SUPPORTED_FORMATS.items():
                    if file_path.lower().endswith(extensions):
                        expected_formats.append(fmt)

                if actual_format and expected_formats and actual_format not in expected_formats:
                    warnings.append(f"Format mismatch: file has '{file_path.split('.')[-1]}' extension "
                                  f"but is actually '{actual_format}' format")

        except UnidentifiedImageError:
            raise ValueError(f"Cannot identify image format - file may be corrupted or malicious")
        except Exception as e:
            raise ValueError(f"Error validating image: {str(e)}")

    return True, warnings


def calculate_file_hash(file_path, algorithm='sha256'):
    """
    Calculate cryptographic hash of a file.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (sha256, sha512, etc.)

    Returns:
        Hexadecimal hash string
    """
    hash_obj = hashlib.new(algorithm)

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def safe_join_path(base_dir, user_path):
    """
    Safely join paths and prevent path traversal attacks.

    Args:
        base_dir: Base directory (trusted)
        user_path: User-provided path component (untrusted)

    Returns:
        Safe absolute path within base_dir

    Raises:
        ValueError: If path traversal is detected
    """
    base_dir = os.path.abspath(base_dir)

    full_path = os.path.normpath(os.path.join(base_dir, user_path))

    full_path = os.path.abspath(full_path)

    if not full_path.startswith(base_dir + os.sep) and full_path != base_dir:
        raise ValueError(f"Path traversal detected: '{user_path}' resolves outside base directory")

    return full_path
