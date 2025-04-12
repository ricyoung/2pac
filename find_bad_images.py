#!/usr/bin/env python3
"""
2PAC: The Picture Analyzer & Corruption killer
Author: Richard Young
License: MIT

In memory of Jeff Young, who loved Tupac's music and lived by his values of helping others.
Like Tupac, Jeff believed in bringing people together and always lending a hand to those in need.
May your photos always be as clear as the memories they capture, and may we all strive to help others as Jeff did.
"""

import os
import argparse
import concurrent.futures
import sys
import time
import io
import json
import shutil
import pickle
import hashlib
import struct
import tempfile
import subprocess
import random
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageFile, UnidentifiedImageError
from tqdm import tqdm
import tqdm.auto as tqdm_auto
import colorama
import humanize
import logging

# Import 2PAC quotes
try:
    from quotes import QUOTES
except ImportError:
    # Default quotes if file is missing
    QUOTES = ["All Eyez On Your Images."]

# Initialize colorama (required for Windows)
colorama.init()

# Allow loading of truncated images for repair attempts
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Dictionary of supported image formats with their extensions
SUPPORTED_FORMATS = {
    'JPEG': ('.jpg', '.jpeg', '.jpe', '.jif', '.jfif', '.jfi'),
    'PNG': ('.png',),
    'GIF': ('.gif',),
    'TIFF': ('.tiff', '.tif'),
    'BMP': ('.bmp', '.dib'),
    'WEBP': ('.webp',),
    'ICO': ('.ico',),
    'HEIC': ('.heic',),
}

# Default formats (all supported formats)
DEFAULT_FORMATS = list(SUPPORTED_FORMATS.keys())

# List of formats that can potentially be repaired
REPAIRABLE_FORMATS = ['JPEG', 'PNG', 'GIF']

# Default progress directory
DEFAULT_PROGRESS_DIR = os.path.expanduser("~/.bad_image_finder/progress")

# Current version
VERSION = "1.5.0"

def setup_logging(verbose, no_color=False):
    level = logging.DEBUG if verbose else logging.INFO
    
    # Define color codes
    if not no_color:
        # Color scheme
        COLORS = {
            'DEBUG': colorama.Fore.CYAN,
            'INFO': colorama.Fore.GREEN,
            'WARNING': colorama.Fore.YELLOW,
            'ERROR': colorama.Fore.RED,
            'CRITICAL': colorama.Fore.MAGENTA + colorama.Style.BRIGHT,
            'RESET': colorama.Style.RESET_ALL
        }
        
        # Custom formatter with colors
        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                levelname = record.levelname
                if levelname in COLORS:
                    record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
                    record.msg = f"{COLORS[levelname]}{record.msg}{COLORS['RESET']}"
                return super().format(record)
                
        formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=level,
        handlers=[handler]
    )

def diagnose_image_issue(file_path):
    """
    Attempts to diagnose what's wrong with the image.
    Returns: (error_type, details)
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)  # Read first 16 bytes
        
        # Check for zero-byte file
        if len(header) == 0:
            return "empty_file", "File is empty (0 bytes)"
        
        # Check for correct JPEG header
        if file_path.lower().endswith(SUPPORTED_FORMATS['JPEG']):
            if not (header.startswith(b'\xff\xd8\xff')):
                return "invalid_header", "Invalid JPEG header"
        
        # Check for correct PNG header
        elif file_path.lower().endswith(SUPPORTED_FORMATS['PNG']):
            if not header.startswith(b'\x89PNG\r\n\x1a\n'):
                return "invalid_header", "Invalid PNG header"
        
        # Try to open with PIL for more detailed diagnosis
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
                
        # Now try to load the data
        try:
            with Image.open(file_path) as img:
                img.load()
        except Exception as e:
            return "data_load_failed", f"Image data couldn't be loaded: {str(e)}"
            
        # If we got here, there's some other issue
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
        
        # Check for correct JPEG header (SOI marker)
        if not data.startswith(b'\xFF\xD8'):
            return False, "Invalid JPEG header (missing SOI marker)"
        
        # Check for proper EOI marker at the end
        if not data.endswith(b'\xFF\xD9'):
            return False, "Missing EOI marker at end of file"
        
        # Check for key JPEG segments
        # SOF marker (Start of Frame) - At least one should be present
        sof_markers = [b'\xFF\xC0', b'\xFF\xC1', b'\xFF\xC2', b'\xFF\xC3']
        has_sof = any(marker in data for marker in sof_markers)
        if not has_sof:
            return False, "No Start of Frame (SOF) marker found"
        
        # Check for SOS marker (Start of Scan)
        if b'\xFF\xDA' not in data:
            return False, "No Start of Scan (SOS) marker found"
        
        # Scan through the file to check marker structure
        i = 2  # Skip SOI marker
        while i < len(data) - 1:
            if data[i] == 0xFF and data[i+1] != 0x00 and data[i+1] != 0xFF:
                # Found a marker
                marker = data[i:i+2]
                
                # For markers with length fields, validate length
                if (0xC0 <= data[i+1] <= 0xCF and data[i+1] != 0xC4 and data[i+1] != 0xC8) or \
                   (0xDB <= data[i+1] <= 0xFE):
                    if i + 4 >= len(data):
                        return False, f"Truncated marker {data[i+1]:02X} at position {i}"
                    length = struct.unpack('>H', data[i+2:i+4])[0]
                    if i + 2 + length > len(data):
                        return False, f"Invalid segment length for marker {data[i+1]:02X}"
                    i += 2 + length
                    continue
            
            # Move to next byte
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
        
        # Check for PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        if not data.startswith(png_signature):
            return False, "Invalid PNG signature"
        
        # Check minimum viable PNG (signature + IHDR chunk)
        if len(data) < 8 + 12:  # 8 bytes signature + 12 bytes min IHDR chunk
            return False, "PNG file too small to contain valid header"
            
        # Check for IEND chunk at the end
        if not data.endswith(b'IEND\xaeB`\x82'):
            return False, "Missing IEND chunk at end of file"
        
        # Parse chunks
        pos = 8  # Skip signature
        required_chunks = {'IHDR': False}
        
        while pos < len(data):
            if pos + 8 > len(data):
                return False, "Truncated chunk header"
                
            # Read chunk length and type
            chunk_len = struct.unpack('>I', data[pos:pos+4])[0]
            chunk_type = data[pos+4:pos+8].decode('ascii', errors='replace')
            
            # Validate chunk length
            if pos + chunk_len + 12 > len(data):
                return False, f"Truncated {chunk_type} chunk"
            
            # Track required chunks
            if chunk_type in required_chunks:
                required_chunks[chunk_type] = True
                
            # Special validation for IHDR chunk
            if chunk_type == 'IHDR' and chunk_len != 13:
                return False, "Invalid IHDR chunk length"
                
            # Mandatory IHDR must be first chunk
            if pos == 8 and chunk_type != 'IHDR':
                return False, "First chunk must be IHDR"
                
            # IEND must be the last chunk
            if chunk_type == 'IEND' and pos + chunk_len + 12 != len(data):
                return False, "Data after IEND chunk"
            
            # Move to next chunk
            pos += chunk_len + 12  # Length (4) + Type (4) + Data (chunk_len) + CRC (4)
        
        # Verify required chunks
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
    """
    # Try using exiftool if available
    try:
        result = subprocess.run(['exiftool', '-m', '-p', '$Error', file_path], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return False, f"Exiftool error: {result.stdout.strip()}"
            
        # Check with identify (ImageMagick) if available
        result = subprocess.run(['identify', '-verbose', file_path], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return False, "ImageMagick identify failed to read the image"
            
        return True, "Passed external tool validation"
    except (subprocess.SubprocessError, FileNotFoundError):
        # External tools not available or failed
        return True, "External tools check skipped"

def try_full_decode_check(file_path):
    """
    Try to fully decode the image to a temporary file.
    This catches more subtle corruption that might otherwise be missed.
    """
    try:
        # For JPEGs, try to decode and re-encode the image
        with Image.open(file_path) as img:
            # Create a temporary file for testing
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                # Try to save a decoded copy
                img.save(tmp.name, format="BMP")
                
                # If we get here, the image data could be fully decoded
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
            # Get image dimensions
            width, height = img.size
            total_pixels = width * height
            
            # Convert to RGB to ensure consistent analysis
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Sample the image (analyzing every pixel would be too slow)
            # We'll create a grid of sample points - we'll use more samples for more accuracy
            sample_step = max(1, min(width, height) // 150)  # Adjust based on image size
            
            # Track unique colors and their counts
            color_counts = {}
            total_samples = 0
            
            # Sample the image
            for y in range(0, height, sample_step):
                for x in range(0, width, sample_step):
                    total_samples += 1
                    pixel = img.getpixel((x, y))
                    
                    # Round pixel values to reduce sensitivity to minor variations
                    rounded_pixel = (
                        pixel[0] // uniform_threshold * uniform_threshold,
                        pixel[1] // uniform_threshold * uniform_threshold,
                        pixel[2] // uniform_threshold * uniform_threshold
                    )
                    
                    if rounded_pixel in color_counts:
                        color_counts[rounded_pixel] += 1
                    else:
                        color_counts[rounded_pixel] = 1
            
            # Find the most common color
            most_common_color = max(color_counts.items(), key=lambda x: x[1])
            most_common_percentage = most_common_color[1] / total_samples
            
            # Check for large blocks of uniform color (potential corruption)
            if most_common_percentage > block_threshold:
                # Calculate approximate percentage of the image affected
                affected_pct = most_common_percentage * 100
                color_value = most_common_color[0]
                
                # Determine if this is likely corruption
                # Gray/black areas are common in corruption
                is_dark = sum(color_value) < 3 * uniform_threshold  # Very dark areas
                
                # Check if it's a gray area (equal R,G,B values)
                is_gray = abs(color_value[0] - color_value[1]) < uniform_threshold and \
                          abs(color_value[1] - color_value[2]) < uniform_threshold and \
                          abs(color_value[0] - color_value[2]) < uniform_threshold
                
                # Only consider mid-range grays as corruption indicators (not white/black)
                is_mid_gray = is_gray and 30 < sum(color_value)/3 < 220
                
                # Special case: almost pure white is often legitimate content
                is_white = color_value[0] > 240 and color_value[1] > 240 and color_value[2] > 240
                
                # Determine likelihood of corruption based on color and percentage
                if (is_dark or is_mid_gray) and not is_white:
                    # Higher threshold for white areas since they're common in legitimate images
                    white_threshold = 0.4  # 40% of image
                    if is_white and most_common_percentage < white_threshold:
                        return False, f"Large white area ({affected_pct:.1f}%) but likely not corruption"
                    
                    # More likely to be corruption
                    return True, f"Visual corruption detected: {affected_pct:.1f}% of image is uniform {color_value}"
                else:
                    # Could be a legitimate image with a uniform background
                    return False, f"Large uniform area ({affected_pct:.1f}%) but likely not corruption"
            
            # Check for other telltale signs of corruption - but only in strict mode
            if strict_mode:
                # 1. Excessive color blocks (fragmentation) - this works well for detecting noise
                if len(color_counts) > total_samples * 0.85 and total_samples > 200:
                    return True, f"Excessive color fragmentation detected ({len(color_counts)} colors in {total_samples} samples)"
                
                # 2. Check for very specific corruption patterns
                # Analyze distribution of colors to look for unusual patterns
                if total_samples > 500:  # Only for larger images with enough samples
                    # Check if there's an unnatural color distribution
                    # Normal photos have a more gradual distribution rather than spikes
                    sorted_counts = sorted(color_counts.values(), reverse=True)
                    
                    # Calculate the color distribution ratio
                    if len(sorted_counts) > 5:
                        top5_ratio = sum(sorted_counts[:5]) / sum(sorted_counts)
                        # Usually, the top 5 colors shouldn't dominate more than 80% of the image
                        # unless it's a graphic or very simple image
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
    # Basic PIL validation first (fast check)
    try:
        with Image.open(file_path) as img:
            # verify() checks the file header
            img.verify()
            
            # Additional step: try to load the image data
            # This catches more corruption issues
            with Image.open(file_path) as img2:
                img2.load()
                
            # If check_visual is enabled, analyze the image content
            if check_visual:
                # Set thresholds based on strictness level
                if visual_strictness == 'low':
                    # More permissive - only detect very obvious corruption
                    block_threshold = 0.3  # 30% of the image must be uniform
                    uniform_threshold = 5  # Smaller color variations are allowed
                elif visual_strictness == 'high':
                    # Most strict - catches subtle corruption but may have false positives
                    block_threshold = 0.15  # Only 15% of the image needs to be uniform
                    uniform_threshold = 15  # Larger color variations are considered uniform
                else:  # medium (default)
                    block_threshold = 0.20  # 20% threshold
                    uniform_threshold = 10
                
                # Check for visual corruption with appropriate thresholds
                is_visually_corrupt, msg = check_visual_corruption(
                    file_path, 
                    block_threshold=block_threshold, 
                    uniform_threshold=uniform_threshold,
                    # Only use additional detection methods in high strictness mode
                    strict_mode=(visual_strictness == 'high')
                )
                
                if is_visually_corrupt:
                    logging.debug(f"Visual corruption detected in {file_path}: {msg}")
                    return False
                
            # If thorough checking is disabled, return after basic check
            if not thorough or sensitivity == 'low':
                return True
                
            # For JPEG files, do additional structure checking
            if file_path.lower().endswith(tuple(SUPPORTED_FORMATS['JPEG'])):
                # Check JPEG structure
                is_valid, error_msg = check_jpeg_structure(file_path)
                if not is_valid:
                    # If ignore_eof is enabled and the only issue is missing EOI marker, consider it valid
                    if ignore_eof and error_msg == "Missing EOI marker at end of file":
                        logging.debug(f"Ignoring missing EOI marker for {file_path} as requested")
                    else:
                        logging.debug(f"JPEG structure invalid for {file_path}: {error_msg}")
                        return False
                
                # Try full decode test (catches subtle corruption)
                is_valid, error_msg = try_full_decode_check(file_path)
                if not is_valid:
                    logging.debug(f"Full decode test failed for {file_path}: {error_msg}")
                    return False
                
                # Try external tools if applicable
                is_valid, error_msg = try_external_tools(file_path)
                if not is_valid:
                    logging.debug(f"External tool validation failed for {file_path}: {error_msg}")
                    return False
            
            # For PNG files, do additional structure checking
            elif file_path.lower().endswith(tuple(SUPPORTED_FORMATS['PNG'])):
                # Check PNG structure
                is_valid, error_msg = check_png_structure(file_path)
                if not is_valid:
                    logging.debug(f"PNG structure invalid for {file_path}: {error_msg}")
                    return False
                
                # Try full decode test (catches subtle corruption)
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
    # Create backup if requested
    if backup_dir:
        backup_path = os.path.join(backup_dir, os.path.basename(file_path) + ".bak")
        try:
            shutil.copy2(file_path, backup_path)
            logging.debug(f"Created backup at {backup_path}")
        except Exception as e:
            logging.warning(f"Could not create backup: {str(e)}")
    
    try:
        # First, diagnose the issue
        issue_type, details = diagnose_image_issue(file_path)
        logging.debug(f"Diagnosis for {file_path}: {issue_type} - {details}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Check if file format is supported for repair
        format_supported = False
        for fmt in REPAIRABLE_FORMATS:
            if file_ext in SUPPORTED_FORMATS[fmt]:
                format_supported = True
                break
                
        if not format_supported:
            return False, f"Format not supported for repair ({file_ext})", None, None
        
        # Try to open and resave the image with PIL's error forgiveness
        # This works for many truncated files
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                format = img.format
                
                # Create a buffer for the fixed image
                buffer = io.BytesIO()
                img.save(buffer, format=format)
                
                # Write the repaired image back to the original file
                with open(file_path, 'wb') as f:
                    f.write(buffer.getvalue())
                
                # Verify the repaired image
                if is_valid_image(file_path):
                    return True, f"Repaired {issue_type} issue", width, height
                else:
                    # If verification fails, try again with JPEG specific options for JPEG files
                    if format == 'JPEG':
                        with Image.open(file_path) as img:
                            buffer = io.BytesIO()
                            # Use optimize=True and quality=85 for better repair chances
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

def process_file(args):
    """Process a single image file."""
    file_path, repair_mode, repair_dir, thorough_check, sensitivity, ignore_eof, check_visual, visual_strictness = args
    
    # Check if the image is valid
    is_valid = is_valid_image(file_path, thorough=thorough_check, sensitivity=sensitivity, 
                             ignore_eof=ignore_eof, check_visual=check_visual, visual_strictness=visual_strictness)
    
    if not is_valid and repair_mode:
        # Try to repair the file
        repair_success, repair_msg, width, height = attempt_repair(file_path, repair_dir)
        
        if repair_success:
            # File was repaired
            return file_path, True, 0, "repaired", repair_msg, (width, height)
        else:
            # File is still corrupt
            size = os.path.getsize(file_path)
            return file_path, False, size, "repair_failed", repair_msg, None
    else:
        # No repair attempted or file is valid
        size = os.path.getsize(file_path) if not is_valid else 0
        return file_path, is_valid, size, "not_repaired", None, None

def get_session_id(directory, formats, recursive):
    """Generate a unique session ID based on scan parameters."""
    # Create a unique identifier for this scan session
    dir_path = str(directory).encode('utf-8')
    formats_str = ",".join(sorted(formats)).encode('utf-8')
    recursive_str = str(recursive).encode('utf-8')
    
    # Create a hash of the parameters
    hash_obj = hashlib.md5()
    hash_obj.update(dir_path)
    hash_obj.update(formats_str)
    hash_obj.update(recursive_str)
    
    return hash_obj.hexdigest()[:12]  # Use first 12 chars of hash

def save_progress(session_id, directory, formats, recursive, processed_files, 
                 bad_files, repaired_files, progress_dir=DEFAULT_PROGRESS_DIR):
    """Save the current progress to a file."""
    # Create progress directory if it doesn't exist
    if not os.path.exists(progress_dir):
        os.makedirs(progress_dir, exist_ok=True)
    
    # Create a progress state object
    progress_state = {
        'version': VERSION,
        'timestamp': datetime.now().isoformat(),
        'directory': str(directory),
        'formats': formats,
        'recursive': recursive,
        'processed_files': processed_files,
        'bad_files': bad_files,
        'repaired_files': repaired_files
    }
    
    # Save to file
    progress_file = os.path.join(progress_dir, f"session_{session_id}.progress")
    with open(progress_file, 'wb') as f:
        pickle.dump(progress_state, f)
    
    logging.debug(f"Progress saved to {progress_file}")
    return progress_file

def load_progress(session_id, progress_dir=DEFAULT_PROGRESS_DIR):
    """Load progress from a saved session."""
    progress_file = os.path.join(progress_dir, f"session_{session_id}.progress")
    
    if not os.path.exists(progress_file):
        return None
    
    try:
        with open(progress_file, 'rb') as f:
            progress_state = pickle.load(f)
            
        # Check version compatibility
        if progress_state.get('version', '0.0.0') != VERSION:
            logging.warning("Progress file was created with a different version. Some incompatibilities may exist.")
            
        logging.info(f"Loaded progress from {progress_file}")
        return progress_state
    except Exception as e:
        logging.error(f"Failed to load progress: {str(e)}")
        return None

def list_saved_sessions(progress_dir=DEFAULT_PROGRESS_DIR):
    """List all saved sessions with their details."""
    if not os.path.exists(progress_dir):
        return []
    
    sessions = []
    for filename in os.listdir(progress_dir):
        if filename.endswith('.progress'):
            try:
                filepath = os.path.join(progress_dir, filename)
                with open(filepath, 'rb') as f:
                    progress_state = pickle.load(f)
                
                session_info = {
                    'id': filename.replace('session_', '').replace('.progress', ''),
                    'timestamp': progress_state.get('timestamp', 'Unknown'),
                    'directory': progress_state.get('directory', 'Unknown'),
                    'formats': progress_state.get('formats', []),
                    'processed_count': len(progress_state.get('processed_files', [])),
                    'bad_count': len(progress_state.get('bad_files', [])),
                    'repaired_count': len(progress_state.get('repaired_files', [])),
                    'filepath': filepath
                }
                sessions.append(session_info)
            except Exception as e:
                logging.debug(f"Failed to load session from {filename}: {str(e)}")
    
    # Sort by timestamp, newest first
    sessions.sort(key=lambda x: x['timestamp'], reverse=True)
    return sessions

def get_extensions_for_formats(formats):
    """Get all file extensions for the specified formats."""
    extensions = []
    for fmt in formats:
        if fmt in SUPPORTED_FORMATS:
            extensions.extend(SUPPORTED_FORMATS[fmt])
    return tuple(extensions)

def find_image_files(directory, formats, recursive=True):
    """Find all image files of specified formats in a directory."""
    image_files = []
    extensions = get_extensions_for_formats(formats)
    
    if not extensions:
        logging.warning("No valid image formats specified!")
        return []
    
    format_names = ", ".join(formats)
    if recursive:
        logging.info(f"Recursively scanning for {format_names} files...")
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(extensions):
                    image_files.append(os.path.join(root, file))
    else:
        logging.info(f"Scanning for {format_names} files in {directory} (non-recursive)...")
        for file in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, file)) and file.lower().endswith(extensions):
                image_files.append(os.path.join(directory, file))
    
    logging.info(f"Found {len(image_files)} image files")
    return image_files

def process_images(directory, formats, dry_run=True, repair=False, 
                  max_workers=None, recursive=True, move_to=None, repair_dir=None,
                  save_progress_interval=5, resume_session=None, progress_dir=DEFAULT_PROGRESS_DIR,
                  thorough_check=False, sensitivity='medium', ignore_eof=False, check_visual=False,
                  visual_strictness='medium'):
    """Find corrupt image files and optionally repair, delete, or move them."""
    start_time = time.time()
    
    # Generate session ID for this scan
    session_id = get_session_id(directory, formats, recursive)
    processed_files = []
    bad_files = []
    repaired_files = []
    total_size_saved = 0
    last_progress_save = time.time()
    
    # If resuming, load previous progress
    if resume_session:
        try:
            progress = load_progress(resume_session, progress_dir)
            if progress and progress['directory'] == str(directory) and progress['formats'] == formats:
                processed_files = progress['processed_files']
                bad_files = progress['bad_files']
                repaired_files = progress['repaired_files']
                logging.info(f"Resuming session: {len(processed_files)} files already processed")
            else:
                if progress:
                    logging.warning("Session parameters don't match current parameters. Starting fresh scan.")
                else:
                    logging.warning(f"Couldn't find session {resume_session}. Starting fresh scan.")
        except Exception as e:
            logging.error(f"Error loading session: {str(e)}. Starting fresh scan.")
    
    # Find all image files
    image_files = find_image_files(directory, formats, recursive)
    if not image_files:
        logging.warning("No image files found!")
        return [], [], 0
    
    # Filter out already processed files if resuming
    if processed_files:
        remaining_files = [f for f in image_files if f not in processed_files]
        skipped_count = len(image_files) - len(remaining_files)
        image_files = remaining_files
        logging.info(f"Skipping {skipped_count} already processed files")
        
    if not image_files:
        logging.info("All files have already been processed in the previous session!")
        return bad_files, repaired_files, total_size_saved
        
    # Create directories if they don't exist
    if move_to and not os.path.exists(move_to):
        os.makedirs(move_to)
        logging.info(f"Created directory for corrupt files: {move_to}")
    
    if repair and repair_dir and not os.path.exists(repair_dir):
        os.makedirs(repair_dir)
        logging.info(f"Created directory for backup files: {repair_dir}")
    
    # Prepare input arguments for workers
    input_args = [(file_path, repair, repair_dir, thorough_check, sensitivity, ignore_eof, check_visual, visual_strictness) for file_path in image_files]
    
    # Process files in parallel
    logging.info("Processing files in parallel...")
    
    # Create a custom progress bar class that saves progress periodically
    class ProgressSavingBar(tqdm_auto.tqdm):
        def update(self, n=1):
            nonlocal last_progress_save, processed_files
            result = super().update(n)
            
            # Save progress periodically
            current_time = time.time()
            if save_progress_interval > 0 and current_time - last_progress_save >= save_progress_interval * 60:
                # Get processed files up to the current position
                newly_processed = image_files[:self.n]
                processed_files.extend(newly_processed)
                
                # Save the progress
                save_progress(session_id, directory, formats, recursive, 
                             processed_files, bad_files, repaired_files, progress_dir)
                
                last_progress_save = current_time
                logging.debug(f"Progress saved at {self.n} / {len(image_files)} files")
            
            return result
    
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Colorful progress bar with progress saving
            results = []
            futures = {executor.submit(process_file, arg): arg[0] for arg in input_args}
            
            with ProgressSavingBar(
                total=len(image_files),
                desc=f"{colorama.Fore.BLUE}Checking image files{colorama.Style.RESET_ALL}",
                unit="file",
                bar_format="{desc}: {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                colour="blue"
            ) as pbar:
                for future in concurrent.futures.as_completed(futures):
                    file_path = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        
                        # Track this file as processed for resuming later if needed
                        processed_files.append(file_path)
                        
                        # Update progress for successful or failed processing
                        pbar.update(1)
                        
                        # Update our tracking of bad/repaired files in real-time for progress saving
                        file_path, is_valid, size, repair_status, repair_msg, dimensions = result
                        if repair_status == "repaired":
                            repaired_files.append(file_path)
                        elif not is_valid:
                            bad_files.append(file_path)
                        
                    except Exception as e:
                        logging.error(f"Error processing {file_path}: {str(e)}")
                        pbar.update(1)
    except KeyboardInterrupt:
        # If the user interrupts, save progress before exiting
        logging.warning("Process interrupted by user. Saving progress...")
        save_progress(session_id, directory, formats, recursive, 
                     processed_files, bad_files, repaired_files, progress_dir)
        logging.info(f"Progress saved. You can resume with --resume {session_id}")
        raise
    
    # Process results
    total_size_saved = 0
    for file_path, is_valid, size, repair_status, repair_msg, dimensions in results:
        if repair_status == "repaired":
            # File was successfully repaired (already added to repaired_files during processing)
            width, height = dimensions
            msg = f"Repaired: {file_path} ({width}x{height}) - {repair_msg}"
            logging.info(msg)
        elif not is_valid:
            # File is corrupt and wasn't repaired (or repair failed)
            # (already added to bad_files during processing)
            total_size_saved += size
            
            size_str = humanize.naturalsize(size)
            if repair_status == "repair_failed":
                fail_msg = f"Repair failed: {file_path} ({size_str}) - {repair_msg}"
                logging.warning(fail_msg)
                
            if dry_run:
                msg = f"Would delete: {file_path} ({size_str})"
                logging.info(msg)
            elif move_to:
                # Preserve the subdirectory structure by getting the relative path from the search directory
                try:
                    # Get the relative path from the base directory
                    rel_path = os.path.relpath(file_path, str(directory))
                    # If relpath starts with ".." it means file_path is not within directory
                    # In this case, just use the basename as fallback
                    if rel_path.startswith('..'):
                        dest_path = os.path.join(move_to, os.path.basename(file_path))
                    else:
                        # Create the full destination path preserving subdirectories
                        dest_path = os.path.join(move_to, rel_path)
                        
                    # Create parent directories if they don't exist
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Use shutil.move instead of os.rename to handle cross-device file movements
                    shutil.move(file_path, dest_path)
                    
                    # Add arrow with color
                    arrow = f"{colorama.Fore.CYAN}→{colorama.Style.RESET_ALL}"
                    msg = f"Moved: {file_path} {arrow} {dest_path} ({size_str})"
                    logging.info(msg)
                except Exception as e:
                    logging.error(f"Failed to move {file_path}: {e}")
            else:
                try:
                    os.remove(file_path)
                    msg = f"Deleted: {file_path} ({size_str})"
                    logging.info(msg)
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {e}")
    
    # Final progress save
    save_progress(session_id, directory, formats, recursive, 
                 processed_files, bad_files, repaired_files, progress_dir)
    
    elapsed = time.time() - start_time
    logging.info(f"Processed {len(processed_files)} files in {elapsed:.2f} seconds")
    logging.info(f"Session ID: {session_id} (use --resume {session_id} to resume if needed)")
    
    return bad_files, repaired_files, total_size_saved

def print_banner():
    """Print 2PAC-themed ASCII art banner"""
    banner = r"""
    ██████╗ ██████╗  █████╗  ██████╗
    ╚════██╗██╔══██╗██╔══██╗██╔════╝
     █████╔╝██████╔╝███████║██║     
     ╚═══██╗██╔═══╝ ██╔══██║██║     
    ██████╔╝██║     ██║  ██║╚██████╗
    ╚═════╝ ╚═╝     ╚═╝  ╚═╝ ╚═════╝
    The Picture Analyzer & Corruption killer
    In memory of Jeff Young - Bringing people together & helping others
    """
    
    # Colored version of the banner, highlighting PAC for Picture Analyzer Corruption
    if 'colorama' in sys.modules:
        banner_lines = banner.strip().split('\n')
        
        # Replace the original title line with colorful version
        title_index = -2  # Second to last line
        title_parts = ["The ", "Picture ", "Analyzer ", "& ", "Corruption ", "killer"]
        colored_title = f"{colorama.Fore.WHITE}The " + \
                       f"{colorama.Fore.RED}Picture " + \
                       f"{colorama.Fore.GREEN}Analyzer " + \
                       f"{colorama.Fore.WHITE}& " + \
                       f"{colorama.Fore.BLUE}Corruption " + \
                       f"{colorama.Fore.WHITE}killer{colorama.Style.RESET_ALL}"
        
        # Create colored version of the 2PAC logo (lines 0-5)
        colored_banner = []
        for i, line in enumerate(banner_lines):
            if i == title_index:
                colored_banner.append(colored_title)
            elif i == 0:
                # Colorize the first digit '2'
                new_line = f"{colorama.Fore.WHITE}{line[:5]}{colorama.Style.RESET_ALL}"
                # Colorize 'P'
                new_line += f"{colorama.Fore.RED}{line[5:13]}{colorama.Style.RESET_ALL}"
                # Colorize 'A'
                new_line += f"{colorama.Fore.GREEN}{line[13:21]}{colorama.Style.RESET_ALL}"
                # Colorize 'C'
                new_line += f"{colorama.Fore.BLUE}{line[21:]}{colorama.Style.RESET_ALL}"
                colored_banner.append(new_line)
            elif i == 1:
                # Colorize the first part of second line
                new_line = f"{colorama.Fore.WHITE}{line[:5]}{colorama.Style.RESET_ALL}"
                # Colorize 'P' part
                new_line += f"{colorama.Fore.RED}{line[5:13]}{colorama.Style.RESET_ALL}"
                # Colorize 'A' part
                new_line += f"{colorama.Fore.GREEN}{line[13:21]}{colorama.Style.RESET_ALL}"
                # Colorize 'C' part
                new_line += f"{colorama.Fore.BLUE}{line[21:]}{colorama.Style.RESET_ALL}"
                colored_banner.append(new_line)
            elif i == 2:
                # Colorize the first part of third line
                new_line = f"{colorama.Fore.WHITE}{line[:5]}{colorama.Style.RESET_ALL}"
                # Colorize 'P' part
                new_line += f"{colorama.Fore.RED}{line[5:13]}{colorama.Style.RESET_ALL}"
                # Colorize 'A' part
                new_line += f"{colorama.Fore.GREEN}{line[13:21]}{colorama.Style.RESET_ALL}"
                # Colorize 'C' part
                new_line += f"{colorama.Fore.BLUE}{line[21:]}{colorama.Style.RESET_ALL}"
                colored_banner.append(new_line)
            elif i == 3:
                # Colorize the first part of fourth line
                new_line = f"{colorama.Fore.WHITE}{line[:5]}{colorama.Style.RESET_ALL}"
                # Colorize 'P' part
                new_line += f"{colorama.Fore.RED}{line[5:13]}{colorama.Style.RESET_ALL}"
                # Colorize 'A' part
                new_line += f"{colorama.Fore.GREEN}{line[13:21]}{colorama.Style.RESET_ALL}"
                # Colorize 'C' part
                new_line += f"{colorama.Fore.BLUE}{line[21:]}{colorama.Style.RESET_ALL}"
                colored_banner.append(new_line)
            elif i == 4:
                # Colorize the first part of fifth line
                new_line = f"{colorama.Fore.WHITE}{line[:5]}{colorama.Style.RESET_ALL}"
                # Colorize 'P' part
                new_line += f"{colorama.Fore.RED}{line[5:13]}{colorama.Style.RESET_ALL}"
                # Colorize 'A' part
                new_line += f"{colorama.Fore.GREEN}{line[13:21]}{colorama.Style.RESET_ALL}"
                # Colorize 'C' part
                new_line += f"{colorama.Fore.BLUE}{line[21:]}{colorama.Style.RESET_ALL}"
                colored_banner.append(new_line)
            elif i == 5:
                # Colorize the first part of sixth line
                new_line = f"{colorama.Fore.WHITE}{line[:5]}{colorama.Style.RESET_ALL}"
                # Colorize 'P' part
                new_line += f"{colorama.Fore.RED}{line[5:13]}{colorama.Style.RESET_ALL}"
                # Colorize 'A' part
                new_line += f"{colorama.Fore.GREEN}{line[13:21]}{colorama.Style.RESET_ALL}"
                # Colorize 'C' part
                new_line += f"{colorama.Fore.BLUE}{line[21:]}{colorama.Style.RESET_ALL}"
                colored_banner.append(new_line)
            elif i == len(banner_lines) - 1:  # Last line (tribute)
                colored_banner.append(f"{colorama.Fore.CYAN}{line}{colorama.Style.RESET_ALL}")
            else:
                colored_banner.append(f"{colorama.Fore.YELLOW}{line}{colorama.Style.RESET_ALL}")
        
        print('\n'.join(colored_banner))
    else:
        print(banner)
    print()

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(
        description='2PAC: The Picture Analyzer & Corruption killer',
        epilog='Created by Richard Young - "All Eyez On Your Images" - https://github.com/ricyoung/2pac'
    )
    
    # Main action (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('directory', nargs='?', help='Directory to search for image files')
    action_group.add_argument('--list-sessions', action='store_true', help='List all saved sessions')
    action_group.add_argument('--check-file', type=str, help='Check a specific file for corruption (useful for testing)')
    
    # Basic options
    parser.add_argument('--delete', action='store_true', help='Delete corrupt image files (without this flag, runs in dry-run mode)')
    parser.add_argument('--move-to', type=str, help='Move corrupt files to this directory instead of deleting them')
    parser.add_argument('--workers', type=int, default=None, help='Number of worker processes (default: CPU count)')
    parser.add_argument('--non-recursive', action='store_true', help='Only search in the specified directory, not subdirectories')
    parser.add_argument('--output', type=str, help='Save list of corrupt files to this file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--version', action='version', version=f'Bad Image Finder v{VERSION} by Richard Young')
    
    # Repair options
    repair_group = parser.add_argument_group('Repair options')
    repair_group.add_argument('--repair', action='store_true', help='Attempt to repair corrupt image files')
    repair_group.add_argument('--backup-dir', type=str, help='Directory to store backups of files before repair')
    repair_group.add_argument('--repair-report', type=str, help='Save list of repaired files to this file')
    
    # Format options
    format_group = parser.add_argument_group('Image format options')
    format_group.add_argument('--formats', type=str, nargs='+', choices=SUPPORTED_FORMATS.keys(), 
                             help=f'Image formats to check (default: all formats)')
    format_group.add_argument('--jpeg', action='store_true', help='Check JPEG files only')
    format_group.add_argument('--png', action='store_true', help='Check PNG files only')
    format_group.add_argument('--tiff', action='store_true', help='Check TIFF files only')
    format_group.add_argument('--gif', action='store_true', help='Check GIF files only')
    format_group.add_argument('--bmp', action='store_true', help='Check BMP files only')
    
    # Validation options
    validation_group = parser.add_argument_group('Validation options')
    validation_group.add_argument('--thorough', action='store_true', 
                                 help='Perform thorough image validation (slower but catches more subtle corruption)')
    validation_group.add_argument('--sensitivity', type=str, choices=['low', 'medium', 'high'], default='medium',
                                help='Set validation sensitivity level: low (basic checks), medium (standard checks), high (most strict)')
    validation_group.add_argument('--ignore-eof', action='store_true',
                                help='Ignore missing end-of-file markers (useful for truncated but viewable files)')
    validation_group.add_argument('--check-visual', action='store_true',
                                help='Analyze image content to detect visible corruption like gray/black areas')
    validation_group.add_argument('--visual-strictness', type=str, choices=['low', 'medium', 'high'], default='medium',
                                help='Set strictness level for visual corruption detection: low (most permissive), medium (balanced), high (only clear corruption)')
    
    # Progress saving options
    progress_group = parser.add_argument_group('Progress options')
    progress_group.add_argument('--save-interval', type=int, default=5, 
                              help='Save progress every N minutes (0 to disable progress saving)')
    progress_group.add_argument('--progress-dir', type=str, default=DEFAULT_PROGRESS_DIR,
                               help='Directory to store progress files')
    progress_group.add_argument('--resume', type=str, metavar='SESSION_ID',
                              help='Resume from a previously saved session')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose, args.no_color)
    
    # Handle specific file check mode
    if args.check_file:
        file_path = args.check_file
        if not os.path.exists(file_path):
            logging.error(f"Error: File not found: {file_path}")
            sys.exit(1)
            
        print(f"\n{colorama.Style.BRIGHT}Checking file: {file_path}{colorama.Style.RESET_ALL}\n")
        
        # Basic check
        print(f"{colorama.Fore.CYAN}Basic validation:{colorama.Style.RESET_ALL}")
        try:
            with Image.open(file_path) as img:
                print(f"✓ File can be opened by PIL")
                print(f"  Format: {img.format}")
                print(f"  Mode: {img.mode}")
                print(f"  Size: {img.size[0]}x{img.size[1]}")
                
                try:
                    img.verify()
                    print(f"✓ Header verification passed")
                except Exception as e:
                    print(f"❌ Header verification failed: {str(e)}")
                
                try:
                    with Image.open(file_path) as img2:
                        img2.load()
                    print(f"✓ Data loading test passed")
                except Exception as e:
                    print(f"❌ Data loading test failed: {str(e)}")
        except Exception as e:
            print(f"❌ Cannot open file with PIL: {str(e)}")
        
        # Detailed format-specific checks
        if file_path.lower().endswith(tuple(SUPPORTED_FORMATS['JPEG'])):
            print(f"\n{colorama.Fore.CYAN}JPEG structure checks:{colorama.Style.RESET_ALL}")
            is_valid, msg = check_jpeg_structure(file_path)
            if is_valid:
                print(f"✓ JPEG structure valid: {msg}")
            else:
                print(f"❌ JPEG structure invalid: {msg}")
        elif file_path.lower().endswith(tuple(SUPPORTED_FORMATS['PNG'])):
            print(f"\n{colorama.Fore.CYAN}PNG structure checks:{colorama.Style.RESET_ALL}")
            is_valid, msg = check_png_structure(file_path)
            if is_valid:
                print(f"✓ PNG structure valid: {msg}")
            else:
                print(f"❌ PNG structure invalid: {msg}")
        
        # Decode test
        print(f"\n{colorama.Fore.CYAN}Full decode test:{colorama.Style.RESET_ALL}")
        is_valid, msg = try_full_decode_check(file_path)
        if is_valid:
            print(f"✓ Full decode test passed: {msg}")
        else:
            print(f"❌ Full decode test failed: {msg}")
        
        # External tools check
        print(f"\n{colorama.Fore.CYAN}External tools check:{colorama.Style.RESET_ALL}")
        is_valid, msg = try_external_tools(file_path)
        if is_valid:
            print(f"✓ External tools: {msg}")
        else:
            print(f"❌ External tools: {msg}")
            
        # Visual corruption check
        print(f"\n{colorama.Fore.CYAN}Visual content analysis:{colorama.Style.RESET_ALL}")
        is_visually_corrupt, vis_msg = check_visual_corruption(file_path)
        if not is_visually_corrupt:
            print(f"✓ No visual corruption detected: {vis_msg}")
        else:
            print(f"❌ {vis_msg}")
            
        # Final verdict
        print(f"\n{colorama.Fore.CYAN}Final verdict:{colorama.Style.RESET_ALL}")
        is_valid_basic = is_valid_image(file_path, thorough=False)
        is_valid_thorough = is_valid_image(file_path, thorough=True)
        is_valid_visual = not is_visually_corrupt
        
        if is_valid_basic and is_valid_thorough and is_valid_visual:
            print(f"{colorama.Fore.GREEN}This file appears to be valid by all checks.{colorama.Style.RESET_ALL}")
        elif not is_valid_visual:
            print(f"{colorama.Fore.RED}This file shows visible corruption in the image content.{colorama.Style.RESET_ALL}")
            print(f"Recommendation: Use --check-visual to detect this type of corruption.")
        elif is_valid_basic and not is_valid_thorough:
            print(f"{colorama.Fore.YELLOW}This file passes basic validation but fails thorough checks.{colorama.Style.RESET_ALL}")
            print(f"Recommendation: Use --thorough mode to detect this type of corruption.")
        else:
            print(f"{colorama.Fore.RED}This file is corrupt and would be detected by the basic scan.{colorama.Style.RESET_ALL}")
            
        sys.exit(0)
    
    # Handle session listing mode
    if args.list_sessions:
        sessions = list_saved_sessions(args.progress_dir)
        if sessions:
            print(f"\n{colorama.Style.BRIGHT}Saved Sessions:{colorama.Style.RESET_ALL}")
            for i, session in enumerate(sessions):
                ts = datetime.fromisoformat(session['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n{colorama.Fore.CYAN}Session ID: {session['id']}{colorama.Style.RESET_ALL}")
                print(f"  Created: {ts}")
                print(f"  Directory: {session['directory']}")
                print(f"  Formats: {', '.join(session['formats'])}")
                print(f"  Progress: {session['processed_count']} files processed, "
                      f"{session['bad_count']} corrupt, {session['repaired_count']} repaired")
                
                # Show resume command
                resume_cmd = f"find_bad_images.py --resume {session['id']}"
                if os.path.exists(session['directory']):
                    print(f"  {colorama.Fore.GREEN}Resume command: {resume_cmd}{colorama.Style.RESET_ALL}")
                else:
                    print(f"  {colorama.Fore.YELLOW}Directory no longer exists, cannot resume{colorama.Style.RESET_ALL}")
        else:
            print("No saved sessions found.")
        sys.exit(0)
    
    # Check if directory is specified for a new scan
    if not args.directory and not args.resume:
        logging.error("Error: You must specify a directory to scan or use --resume to continue a session")
        sys.exit(1)
    
    # If we're resuming without a directory, load from previous session
    directory = None
    if args.resume and not args.directory:
        progress = load_progress(args.resume, args.progress_dir)
        if progress:
            directory = Path(progress['directory'])
            logging.info(f"Using directory from saved session: {directory}")
        else:
            logging.error(f"Could not load session {args.resume}")
            sys.exit(1)
    elif args.directory:
        directory = Path(args.directory)
    
    # Verify the directory exists
    if not directory.exists() or not directory.is_dir():
        logging.error(f"Error: {directory} is not a valid directory")
        sys.exit(1)
    
    # Check for incompatible options
    if args.delete and args.move_to:
        logging.error("Error: Cannot use both --delete and --move-to options")
        sys.exit(1)
    
    # Determine which formats to check
    formats = []
    if args.formats:
        formats = args.formats
    elif args.jpeg:
        formats.append('JPEG')
    elif args.png:
        formats.append('PNG')
    elif args.tiff:
        formats.append('TIFF')
    elif args.gif:
        formats.append('GIF')
    elif args.bmp:
        formats.append('BMP')
    else:
        # Default: check all formats
        formats = DEFAULT_FORMATS
    
    dry_run = not (args.delete or args.move_to)
    
    # Colorful mode indicators
    if args.repair:
        mode_str = f"{colorama.Fore.MAGENTA}REPAIR MODE{colorama.Style.RESET_ALL}: Attempting to fix corrupt files"
        logging.info(mode_str)
        
        repairable_formats = [fmt for fmt in formats if fmt in REPAIRABLE_FORMATS]
        if repairable_formats:
            logging.info(f"Repairable formats: {', '.join(repairable_formats)}")
        else:
            logging.warning("None of the selected formats support repair")
    
    if dry_run:
        mode_str = f"{colorama.Fore.YELLOW}DRY RUN MODE{colorama.Style.RESET_ALL}: No files will be deleted or moved"
        logging.info(mode_str)
    elif args.move_to:
        mode_str = f"{colorama.Fore.BLUE}MOVE MODE{colorama.Style.RESET_ALL}: Corrupt files will be moved to {args.move_to}"
        logging.info(mode_str)
    else:
        mode_str = f"{colorama.Fore.RED}DELETE MODE{colorama.Style.RESET_ALL}: Corrupt files will be permanently deleted"
        logging.info(mode_str)
    
    # Add progress saving info
    if args.save_interval > 0:
        save_interval_str = f"{colorama.Fore.CYAN}PROGRESS SAVING{colorama.Style.RESET_ALL}: Every {args.save_interval} minutes"
        logging.info(save_interval_str)
    else:
        logging.info("Progress saving is disabled")
    
    if args.resume:
        resume_str = f"{colorama.Fore.CYAN}RESUMING{colorama.Style.RESET_ALL}: From session {args.resume}"
        logging.info(resume_str)
    
    if args.thorough:
        thorough_str = f"{colorama.Fore.MAGENTA}THOROUGH MODE{colorama.Style.RESET_ALL}: Using deep validation checks (slower but more accurate)"
        logging.info(thorough_str)
        
    # Show sensitivity level
    sensitivity_colors = {
        'low': colorama.Fore.GREEN,
        'medium': colorama.Fore.YELLOW,
        'high': colorama.Fore.RED
    }
    sensitivity_color = sensitivity_colors.get(args.sensitivity, colorama.Fore.YELLOW)
    sensitivity_str = f"{sensitivity_color}SENSITIVITY: {args.sensitivity.upper()}{colorama.Style.RESET_ALL}"
    logging.info(sensitivity_str)
    
    # Show EOF handling
    if args.ignore_eof:
        eof_str = f"{colorama.Fore.CYAN}IGNORING EOF MARKERS{colorama.Style.RESET_ALL}: Allowing truncated but viewable files"
        logging.info(eof_str)
        
    # Show visual corruption checking status
    if args.check_visual:
        strictness_color = {
            'low': colorama.Fore.GREEN,
            'medium': colorama.Fore.YELLOW,
            'high': colorama.Fore.RED
        }.get(args.visual_strictness, colorama.Fore.YELLOW)
        
        visual_str = f"{colorama.Fore.MAGENTA}VISUAL CHECK{colorama.Style.RESET_ALL}: " + \
                     f"Analyzing image content (strictness: {strictness_color}{args.visual_strictness.upper()}{colorama.Style.RESET_ALL})"
        logging.info(visual_str)
    
    # Show which formats we're checking
    format_list = ", ".join(formats)
    logging.info(f"Checking image formats: {format_list}")
    logging.info(f"Searching for corrupt image files in {directory}")
    
    try:
        bad_files, repaired_files, total_size_saved = process_images(
            directory, 
            formats,
            dry_run=dry_run, 
            repair=args.repair,
            max_workers=args.workers,
            recursive=not args.non_recursive,
            move_to=args.move_to,
            repair_dir=args.backup_dir,
            save_progress_interval=args.save_interval,
            resume_session=args.resume,
            progress_dir=args.progress_dir,
            thorough_check=args.thorough,
            sensitivity=args.sensitivity,
            ignore_eof=args.ignore_eof,
            check_visual=args.check_visual,
            visual_strictness=args.visual_strictness
        )
        
        # Colorful summary
        count_color = colorama.Fore.RED if bad_files else colorama.Fore.GREEN
        file_count = f"{count_color}{len(bad_files)}{colorama.Style.RESET_ALL}"
        logging.info(f"Found {file_count} corrupt image files")
        
        if args.repair:
            repair_color = colorama.Fore.GREEN if repaired_files else colorama.Fore.YELLOW
            repair_count = f"{repair_color}{len(repaired_files)}{colorama.Style.RESET_ALL}"
            logging.info(f"Successfully repaired {repair_count} files")
            
            if args.repair_report and repaired_files:
                with open(args.repair_report, 'w') as f:
                    for file_path in repaired_files:
                        f.write(f"{file_path}\n")
                logging.info(f"Saved list of repaired files to {args.repair_report}")
        
        savings_str = humanize.naturalsize(total_size_saved)
        savings_color = colorama.Fore.GREEN if total_size_saved > 0 else colorama.Fore.RESET
        savings_msg = f"Total space savings: {savings_color}{savings_str}{colorama.Style.RESET_ALL}"
        logging.info(savings_msg)
        
        if not args.no_color:
            # Add signature at the end of the run
            signature = f"\n{colorama.Fore.CYAN}2PAC v{VERSION} by Richard Young{colorama.Style.RESET_ALL}"
            quote = f"{colorama.Fore.YELLOW}\"{random.choice(QUOTES)}\"{colorama.Style.RESET_ALL}"
            print(signature)
            print(quote)
        
        # Save list of corrupt files if requested
        if args.output and bad_files:
            with open(args.output, 'w') as f:
                for file_path in bad_files:
                    f.write(f"{file_path}\n")
            logging.info(f"Saved list of corrupt files to {args.output}")
        
        if bad_files and dry_run:
            logging.info("Run with --delete to remove these files or --move-to to relocate them")
            
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()