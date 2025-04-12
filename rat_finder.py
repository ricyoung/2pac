#!/usr/bin/env python3
"""
RAT Finder - Beta steganography detection tool for 2PAC

This tool is designed to detect potential steganography in images.
It's part of the 2PAC toolkit but focused on security aspects.

Author: Richard Young
License: MIT
"""

import os
import sys
import argparse
import concurrent.futures
import logging
import numpy as np
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
from scipy import stats
import colorama
from tqdm import tqdm

# Initialize colorama
colorama.init()

# Version
VERSION = "0.2.0"

# Set up logging
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

def print_banner():
    """Print RAT Finder themed ASCII art banner"""
    banner = r"""
    ██████╗  █████╗ ████████╗   ███████╗██╗███╗   ██╗██████╗ ███████╗██████╗ 
    ██╔══██╗██╔══██╗╚══██╔══╝   ██╔════╝██║████╗  ██║██╔══██╗██╔════╝██╔══██╗
    ██████╔╝███████║   ██║█████╗█████╗  ██║██╔██╗ ██║██║  ██║█████╗  ██████╔╝
    ██╔══██╗██╔══██║   ██║╚════╝██╔══╝  ██║██║╚██╗██║██║  ██║██╔══╝  ██╔══██╗
    ██║  ██║██║  ██║   ██║      ██║     ██║██║ ╚████║██████╔╝███████╗██║  ██║
    ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝      ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝╚═╝  ╚═╝
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║ Steganography Detection Tool (v0.2.0) - Part of the 2PAC toolkit       ║
    ║ "What the eyes see and the ears hear, the mind believes"               ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """
    
    if 'colorama' in sys.modules:
        banner_lines = banner.strip().split('\n')
        colored_banner = []
        
        # Color the RAT part in red, the FINDER part in blue
        for i, line in enumerate(banner_lines):
            if i < 6:  # The logo lines
                # Add the RAT part in red
                part1 = line[:24]
                # Add the FINDER part in blue
                part2 = line[24:]
                colored_line = f"{colorama.Fore.RED}{part1}{colorama.Fore.BLUE}{part2}{colorama.Style.RESET_ALL}"
                colored_banner.append(colored_line)
            elif i >= 6 and i <= 9:  # The box with text
                colored_banner.append(f"{colorama.Fore.YELLOW}{line}{colorama.Style.RESET_ALL}")
            else:
                colored_banner.append(f"{colorama.Fore.WHITE}{line}{colorama.Style.RESET_ALL}")
        
        print('\n'.join(colored_banner))
    else:
        print(banner)
    print()

#------------------------------------------------------------------------------
# STEGANOGRAPHY DETECTION TECHNIQUES
#------------------------------------------------------------------------------

def perform_ela_analysis(image_path, quality=75):
    """
    Performs Error Level Analysis (ELA) to detect manipulated areas in an image.
    
    ELA works by intentionally resaving an image at a known quality level and
    analyzing the differences between the original and resaved versions.
    Areas that have been manipulated often show up as having different error levels.
    
    Args:
        image_path: Path to the image
        quality: JPEG quality level to use for recompression (default: 75)
        
    Returns:
        (is_suspicious, confidence, details)
    """
    try:
        # Only perform ELA on JPEG images
        if not image_path.lower().endswith(('.jpg', '.jpeg', '.jfif')):
            return False, 0, {"error": "ELA is only effective for JPEG images"}
            
        with Image.open(image_path) as original_img:
            # Convert to RGB if needed
            if original_img.mode != 'RGB':
                original_img = original_img.convert('RGB')
                
            # Create a temporary file for the resaved image
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=True)
            resaved_path = temp_file.name
                
            # Save the image with the specified quality
            original_img.save(resaved_path, quality=quality)
            
            # Read the resaved image
            with Image.open(resaved_path) as resaved_img:
                # Convert both to numpy arrays
                original_array = np.array(original_img).astype('int32')
                resaved_array = np.array(resaved_img).astype('int32')
                
                # Calculate absolute difference
                diff = np.abs(original_array - resaved_array)
                
                # Calculate statistics from the difference
                mean_diff = np.mean(diff)
                std_diff = np.std(diff)
                max_diff = np.max(diff)
                
                # Scale the differences to make them more visible (for visualization)
                diff_scaled = diff * 10
                
                # Look for suspicious patterns
                # 1. High variance in error levels can indicate manipulation
                # 2. Localized areas with significantly different error levels are suspicious
                # 3. Unnaturally low error in complex areas can indicate steganography
                
                # Calculate local variation using sliding window approach
                # We're looking for areas where the difference between neighboring pixels
                # has unusually high or low variance
                
                # Use a simple method - check variance in blocks
                block_size = 8  # 8x8 blocks, common in JPEG
                shape = diff.shape
                block_variance = []
                
                # Sample blocks throughout the image
                for i in range(0, shape[0] - block_size, block_size):
                    for j in range(0, shape[1] - block_size, block_size):
                        # Extract block for each channel
                        for c in range(3):  # RGB channels
                            block = diff[i:i+block_size, j:j+block_size, c]
                            block_var = np.var(block)
                            if block_var > 0:  # Avoid divisions by zero
                                block_variance.append(block_var)
                
                if not block_variance:
                    return False, 0, {"error": "Could not calculate block variance"}
                    
                # Calculate statistics on block variances
                mean_block_var = np.mean(block_variance)
                max_block_var = np.max(block_variance)
                std_block_var = np.std(block_variance)
                
                # What we're looking for:
                # 1. Unusually high block variance in some areas (significantly above the mean)
                # 2. Unusually consistent error levels (too perfect - could indicate manipulation)
                
                # Determine suspiciousness based on these factors
                # Calculate a normalized ratio of max variance to mean variance
                if mean_block_var > 0:
                    var_ratio = max_block_var / mean_block_var
                else:
                    var_ratio = 0
                    
                # Calculate coefficient of variation for block variances
                if mean_block_var > 0:
                    coeff_var = std_block_var / mean_block_var
                else:
                    coeff_var = 0
                
                # Heuristics based on ELA characteristics
                # Unusually high variation ratio can indicate manipulation
                is_suspicious_var_ratio = var_ratio > 50
                
                # High coefficient of variation indicates inconsistent error levels
                is_suspicious_coeff_var = coeff_var > 2.0
                
                # Unusually high mean difference can indicate manipulation
                is_suspicious_mean_diff = mean_diff > 15
                
                # Combine factors
                is_suspicious = (is_suspicious_var_ratio or 
                                is_suspicious_coeff_var or 
                                is_suspicious_mean_diff)
                
                # Calculate confidence based on these factors
                confidence = 0
                if is_suspicious_var_ratio:
                    # Scale based on how extreme the ratio is
                    confidence += min(40, var_ratio / 2)
                if is_suspicious_coeff_var:
                    # Scale based on coefficient of variation
                    confidence += min(30, coeff_var * 10)
                if is_suspicious_mean_diff:
                    # Scale based on mean difference
                    confidence += min(30, mean_diff)
                    
                # Cap confidence at 90%
                confidence = min(confidence, 90)
                
                # Save results for return
                details = {
                    "mean_diff": float(mean_diff),
                    "max_diff": float(max_diff),
                    "var_ratio": float(var_ratio),
                    "coeff_var": float(coeff_var),
                    "diff_image": diff_scaled.astype(np.uint8),  # For visualization
                    "quality_used": quality
                }
                
                return is_suspicious, confidence, details
                
    except Exception as e:
        logging.debug(f"Error performing ELA on {image_path}: {str(e)}")
        return False, 0, {"error": str(e)}

def check_lsb_anomalies(image_path, threshold=0.03):
    """
    Detect potential LSB steganography by analyzing bit plane patterns.
    
    Args:
        image_path: Path to the image
        threshold: Threshold for statistical anomaly detection
    
    Returns:
        (is_suspicious, confidence, details)
    """
    try:
        with Image.open(image_path) as img:
            # Convert to RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Get image data as numpy array
            img_array = np.array(img)
            
            # Extract least significant bits from each channel
            red_lsb = img_array[:,:,0] % 2
            green_lsb = img_array[:,:,1] % 2
            blue_lsb = img_array[:,:,2] % 2
            
            # Calculate statistics
            # Chi-square test to detect non-random patterns in LSB
            red_chi = stats.chisquare(np.bincount(red_lsb.flatten()))[1]
            green_chi = stats.chisquare(np.bincount(green_lsb.flatten()))[1]
            blue_chi = stats.chisquare(np.bincount(blue_lsb.flatten()))[1]
            
            # Calculate entropy of the LSB plane
            red_entropy = stats.entropy(np.bincount(red_lsb.flatten()))
            green_entropy = stats.entropy(np.bincount(green_lsb.flatten()))
            blue_entropy = stats.entropy(np.bincount(blue_lsb.flatten()))
            
            # Suspicious if chi-square test shows non-random distribution
            # or if entropy is too high (close to 1 for random, lower for non-random)
            chi_suspicious = min(red_chi, green_chi, blue_chi) < threshold
            entropy_suspicious = abs(np.mean([red_entropy, green_entropy, blue_entropy]) - 1.0) > 0.1
            
            # Calculate a confidence score (0-100%)
            confidence = 0
            if chi_suspicious:
                confidence += 50
            if entropy_suspicious:
                confidence += 30
                
            # Additional checks for common LSB steganography patterns
            # Check for abnormal color distributions
            color_distribution = np.std([np.std(red_lsb), np.std(green_lsb), np.std(blue_lsb)])
            if color_distribution < 0.1:  # Suspicious if too uniform
                confidence += 20
                
            is_suspicious = confidence > 50
            
            details = {
                "chi_square_values": [red_chi, green_chi, blue_chi],
                "entropy_values": [red_entropy, green_entropy, blue_entropy],
                "color_distribution": color_distribution
            }
            
            return is_suspicious, confidence, details
    except Exception as e:
        logging.debug(f"Error analyzing LSB in {image_path}: {str(e)}")
        return False, 0, {"error": str(e)}

def check_file_size_anomalies(image_path):
    """
    Check if file size is suspicious compared to image dimensions.
    
    Args:
        image_path: Path to the image
        
    Returns:
        (is_suspicious, confidence, details)
    """
    try:
        # Get file size
        file_size = os.path.getsize(image_path)
        
        with Image.open(image_path) as img:
            width, height = img.size
            pixel_count = width * height
            
            # Calculate expected file size range based on image type
            expected_size = 0
            if image_path.lower().endswith('.png'):
                # PNG files have variable compression but generally follow a pattern
                # This is a very rough estimate
                expected_min = pixel_count * 0.1  # Minimum expected size
                expected_max = pixel_count * 3    # Maximum expected size
            elif image_path.lower().endswith(('.jpg', '.jpeg')):
                # JPEG files are typically smaller due to compression
                expected_min = pixel_count * 0.05  # Minimum for very compressed JPEG
                expected_max = pixel_count * 1.5   # Maximum for high quality JPEG
            else:
                # For other formats, use a more generic range
                expected_min = pixel_count * 0.1
                expected_max = pixel_count * 4
            
            # Check if file size is within expected range
            is_too_small = file_size < expected_min
            is_too_large = file_size > expected_max
            is_suspicious = is_too_small or is_too_large
            
            # Calculate confidence
            confidence = 0
            if is_too_large:
                # More likely to contain hidden data if too large
                ratio = file_size / expected_max
                confidence = min(int((ratio - 1) * 100), 90)  # Cap at 90%
            elif is_too_small:
                # Less likely but still suspicious if too small
                ratio = expected_min / file_size
                confidence = min(int((ratio - 1) * 50), 70)   # Cap at 70%
            
            details = {
                "file_size": file_size,
                "expected_min": expected_min,
                "expected_max": expected_max,
                "pixel_count": pixel_count,
                "width": width,
                "height": height
            }
            
            return is_suspicious, confidence, details
    except Exception as e:
        logging.debug(f"Error analyzing file size in {image_path}: {str(e)}")
        return False, 0, {"error": str(e)}

def check_histogram_anomalies(image_path):
    """
    Analyze image histogram for unusual patterns that might indicate steganography.
    
    Args:
        image_path: Path to the image
        
    Returns:
        (is_suspicious, confidence, details)
    """
    try:
        with Image.open(image_path) as img:
            # Convert to RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Get image data as numpy array
            img_array = np.array(img)
            
            # Calculate histograms for each color channel
            hist_r = np.histogram(img_array[:,:,0], bins=256, range=(0, 256))[0]
            hist_g = np.histogram(img_array[:,:,1], bins=256, range=(0, 256))[0]
            hist_b = np.histogram(img_array[:,:,2], bins=256, range=(0, 256))[0]
            
            # Normalize histograms
            pixel_count = img_array.shape[0] * img_array.shape[1]
            hist_r = hist_r / pixel_count
            hist_g = hist_g / pixel_count
            hist_b = hist_b / pixel_count
            
            # Analyze histogram characteristics
            # 1. Check for comb patterns (alternating peaks/valleys) which can indicate LSB steganography
            comb_pattern_r = np.sum(np.abs(np.diff(np.diff(hist_r))))
            comb_pattern_g = np.sum(np.abs(np.diff(np.diff(hist_g))))
            comb_pattern_b = np.sum(np.abs(np.diff(np.diff(hist_b))))
            
            # 2. Check for unusual peaks at specific values
            # LSB steganography often causes unusual spikes at even or odd values
            even_odd_ratio_r = np.sum(hist_r[::2]) / np.sum(hist_r[1::2]) if np.sum(hist_r[1::2]) > 0 else 1
            even_odd_ratio_g = np.sum(hist_g[::2]) / np.sum(hist_g[1::2]) if np.sum(hist_g[1::2]) > 0 else 1
            even_odd_ratio_b = np.sum(hist_b[::2]) / np.sum(hist_b[1::2]) if np.sum(hist_b[1::2]) > 0 else 1
            
            # Calculate an evenness score - how far from 1.0 (perfect balance) are we?
            even_odd_deviation = max(
                abs(even_odd_ratio_r - 1.0),
                abs(even_odd_ratio_g - 1.0),
                abs(even_odd_ratio_b - 1.0)
            )
            
            # 3. Calculate histogram smoothness (natural images tend to have smoother histograms)
            smoothness_r = np.mean(np.abs(np.diff(hist_r)))
            smoothness_g = np.mean(np.abs(np.diff(hist_g)))
            smoothness_b = np.mean(np.abs(np.diff(hist_b)))
            
            # Suspicious if large even/odd ratio deviation or high comb pattern values
            is_suspicious_comb = max(comb_pattern_r, comb_pattern_g, comb_pattern_b) > 0.015
            is_suspicious_even_odd = even_odd_deviation > 0.1
            is_suspicious_smoothness = max(smoothness_r, smoothness_g, smoothness_b) > 0.01
            
            is_suspicious = is_suspicious_comb or is_suspicious_even_odd or is_suspicious_smoothness
            
            # Calculate confidence
            confidence = 0
            if is_suspicious_comb:
                confidence += 30
            if is_suspicious_even_odd:
                confidence += 40
            if is_suspicious_smoothness:
                confidence += 20
                
            # Cap confidence at 90%
            confidence = min(confidence, 90)
            
            details = {
                "comb_pattern_values": [comb_pattern_r, comb_pattern_g, comb_pattern_b],
                "even_odd_ratios": [even_odd_ratio_r, even_odd_ratio_g, even_odd_ratio_b],
                "smoothness_values": [smoothness_r, smoothness_g, smoothness_b],
                "even_odd_deviation": even_odd_deviation
            }
            
            return is_suspicious, confidence, details
    except Exception as e:
        logging.debug(f"Error analyzing histogram in {image_path}: {str(e)}")
        return False, 0, {"error": str(e)}

def check_metadata_anomalies(image_path):
    """
    Look for unusual metadata or metadata inconsistencies that could indicate steganography.
    
    Args:
        image_path: Path to the image
    
    Returns:
        (is_suspicious, confidence, details)
    """
    try:
        with Image.open(image_path) as img:
            # Extract metadata (EXIF, etc)
            metadata = {}
            if hasattr(img, '_getexif') and img._getexif() is not None:
                metadata = {k: v for k, v in img._getexif().items()}
                
            # Check for known steganography software markers
            steganography_markers = [
                'outguess', 'stegano', 'steghide', 'jsteg', 'f5', 'secret',
                'hidden', 'conceal', 'invisible', 'steganography'
            ]
            
            found_markers = []
            for key, value in metadata.items():
                if isinstance(value, str):
                    value_lower = value.lower()
                    for marker in steganography_markers:
                        if marker in value_lower:
                            found_markers.append((key, marker, value))
            
            # Check for unusual metadata structure
            is_suspicious = len(found_markers) > 0
            confidence = min(len(found_markers) * 30, 90) if is_suspicious else 0
            
            # Check for metadata size anomalies
            if len(metadata) > 30:  # Unusually large metadata
                is_suspicious = True
                confidence = max(confidence, 50)
                
            details = {
                "metadata_count": len(metadata),
                "suspicious_markers": found_markers
            }
            
            return is_suspicious, confidence, details
    except Exception as e:
        logging.debug(f"Error analyzing metadata in {image_path}: {str(e)}")
        return False, 0, {"error": str(e)}

def check_visual_noise_anomalies(image_path):
    """
    Analyze visual noise patterns to detect potential steganography.
    
    Args:
        image_path: Path to the image
    
    Returns:
        (is_suspicious, confidence, details)
    """
    try:
        with Image.open(image_path) as img:
            # Convert to RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Resize if image is too large for faster processing
            width, height = img.size
            if width > 1000 or height > 1000:
                ratio = min(1000 / width, 1000 / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height))
            
            # Get image data as numpy array
            img_array = np.array(img)
            
            # Apply noise detection
            # Calculate noise in each channel by looking at differences between adjacent pixels
            red_noise = np.mean(np.abs(np.diff(img_array[:,:,0], axis=0))) + np.mean(np.abs(np.diff(img_array[:,:,0], axis=1)))
            green_noise = np.mean(np.abs(np.diff(img_array[:,:,1], axis=0))) + np.mean(np.abs(np.diff(img_array[:,:,1], axis=1)))
            blue_noise = np.mean(np.abs(np.diff(img_array[:,:,2], axis=0))) + np.mean(np.abs(np.diff(img_array[:,:,2], axis=1)))
            
            # Calculate noise ratio between channels
            # In natural images, noise should be roughly similar across channels
            # Large differences might indicate steganographic content
            avg_noise = (red_noise + green_noise + blue_noise) / 3
            noise_diffs = [abs(red_noise - avg_noise), abs(green_noise - avg_noise), abs(blue_noise - avg_noise)]
            max_diff_ratio = max(noise_diffs) / avg_noise if avg_noise > 0 else 0
            
            # Suspicious if significant differences between channels
            is_suspicious = max_diff_ratio > 0.2
            confidence = min(int(max_diff_ratio * 100), 90) if is_suspicious else 0
            
            details = {
                "red_noise": red_noise,
                "green_noise": green_noise,
                "blue_noise": blue_noise,
                "max_diff_ratio": max_diff_ratio
            }
            
            return is_suspicious, confidence, details
    except Exception as e:
        logging.debug(f"Error analyzing visual noise in {image_path}: {str(e)}")
        return False, 0, {"error": str(e)}

def analyze_image(image_path, sensitivity='medium'):
    """
    Perform comprehensive steganography detection on an image.
    
    Args:
        image_path: Path to the image
        sensitivity: 'low', 'medium', or 'high'
        
    Returns:
        (is_suspicious, overall_confidence, detection_details)
    """
    # Set threshold based on sensitivity
    thresholds = {
        'low': 0.01,      # More likely to find steganography but more false positives
        'medium': 0.03,   # Balanced detection
        'high': 0.05      # Fewer false positives but might miss some steganography
    }
    
    confidence_required = {
        'low': 60,       # Lower bar for detection
        'medium': 70,    # Moderate confidence required
        'high': 80       # High confidence required to report
    }
    
    threshold = thresholds.get(sensitivity, 0.03)
    min_confidence = confidence_required.get(sensitivity, 70)
    
    try:
        results = {}
        
        # Run all detection methods
        lsb_result = check_lsb_anomalies(image_path, threshold)
        results['lsb_analysis'] = {
            'suspicious': lsb_result[0],
            'confidence': lsb_result[1],
            'details': lsb_result[2]
        }
        
        size_result = check_file_size_anomalies(image_path)
        results['file_size_analysis'] = {
            'suspicious': size_result[0],
            'confidence': size_result[1],
            'details': size_result[2]
        }
        
        metadata_result = check_metadata_anomalies(image_path)
        results['metadata_analysis'] = {
            'suspicious': metadata_result[0],
            'confidence': metadata_result[1],
            'details': metadata_result[2]
        }
        
        noise_result = check_visual_noise_anomalies(image_path)
        results['visual_noise_analysis'] = {
            'suspicious': noise_result[0],
            'confidence': noise_result[1],
            'details': noise_result[2]
        }
        
        # Add the new histogram analysis
        histogram_result = check_histogram_anomalies(image_path)
        results['histogram_analysis'] = {
            'suspicious': histogram_result[0],
            'confidence': histogram_result[1],
            'details': histogram_result[2]
        }
        
        # Add Error Level Analysis (ELA) for JPEG images
        if image_path.lower().endswith(('.jpg', '.jpeg', '.jfif')):
            ela_result = perform_ela_analysis(image_path)
            results['ela_analysis'] = {
                'suspicious': ela_result[0],
                'confidence': ela_result[1],
                'details': ela_result[2]
            }
        
        # Calculate overall confidence
        # Weight the different tests
        weights = {
            'lsb_analysis': 0.25,           # LSB is a common technique
            'histogram_analysis': 0.20,      # Histogram patterns are strong indicators
            'file_size_analysis': 0.10,      # Size can be indicative
            'metadata_analysis': 0.10,       # Metadata less common but useful indicator
            'visual_noise_analysis': 0.15,   # Visual noise can be a good indicator
            'ela_analysis': 0.20            # Error Level Analysis is effective for JPEG manipulation
        }
        
        # Only include weights for methods that were actually run
        used_weights = {k: v for k, v in weights.items() if k in results}
        
        # Normalize the weights to ensure they sum to 1.0
        weight_sum = sum(used_weights.values())
        if weight_sum > 0:
            used_weights = {k: v/weight_sum for k, v in used_weights.items()}
        
        # Calculate weighted confidence
        overall_confidence = sum(
            results[key]['confidence'] * used_weights[key] for key in used_weights
        )
        
        # Determine if image is suspicious overall
        is_suspicious = overall_confidence >= min_confidence
        
        return is_suspicious, overall_confidence, results
    except Exception as e:
        logging.debug(f"Error analyzing {image_path}: {str(e)}")
        return False, 0, {"error": str(e)}

def process_file(args):
    """Process a single image file."""
    image_path, sensitivity, output_dir = args
    
    try:
        is_suspicious, confidence, details = analyze_image(image_path, sensitivity)
        
        result = {
            'path': image_path,
            'suspicious': is_suspicious,
            'confidence': confidence,
            'details': details
        }
        
        # Create visual report if output directory is specified
        if output_dir and is_suspicious:
            create_visual_report(image_path, confidence, details, output_dir)
        
        return result
    except Exception as e:
        logging.debug(f"Error processing {image_path}: {str(e)}")
        return {
            'path': image_path,
            'suspicious': False,
            'confidence': 0,
            'details': {'error': str(e)}
        }

def create_visual_report(image_path, confidence, details, output_dir):
    """
    Create a visual report showing the analysis of a suspicious image.
    
    Args:
        image_path: Path to the analyzed image
        confidence: Detection confidence
        details: Analysis details
        output_dir: Directory to save report
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a figure with 3x3 subplots to accommodate ELA visualization
        fig, axs = plt.subplots(3, 3, figsize=(15, 15))
        fig.suptitle(f"Steganography Analysis: {os.path.basename(image_path)}\nConfidence: {confidence:.1f}%", fontsize=16)
        
        # Original image
        with Image.open(image_path) as img:
            axs[0, 0].imshow(img)
            axs[0, 0].set_title("Original Image")
            axs[0, 0].axis('off')
            
            # LSB visualization
            img_array = np.array(img.convert('RGB'))
            lsb_img = np.zeros_like(img_array)
            
            # Amplify LSB data by 255 for visibility
            lsb_img[:,:,0] = (img_array[:,:,0] % 2) * 255
            lsb_img[:,:,1] = (img_array[:,:,1] % 2) * 255
            lsb_img[:,:,2] = (img_array[:,:,2] % 2) * 255
            
            axs[0, 1].imshow(lsb_img)
            axs[0, 1].set_title("LSB Visualization")
            axs[0, 1].axis('off')
            
            # ELA visualization (NEW)
            if 'ela_analysis' in details and 'details' in details['ela_analysis']:
                ela_data = details['ela_analysis']['details']
                if 'diff_image' in ela_data and not isinstance(ela_data.get('error', ''), str):
                    # Display the ELA image
                    axs[0, 2].imshow(ela_data['diff_image'])
                    axs[0, 2].set_title("Error Level Analysis (ELA)")
                    axs[0, 2].axis('off')
                    
                    # Add annotation with key metrics
                    metrics = []
                    if 'var_ratio' in ela_data:
                        metrics.append(f"Variance ratio: {ela_data['var_ratio']:.2f}")
                    if 'coeff_var' in ela_data:
                        metrics.append(f"Coefficient of var: {ela_data['coeff_var']:.2f}")
                    if 'mean_diff' in ela_data:
                        metrics.append(f"Mean diff: {ela_data['mean_diff']:.2f}")
                    
                    if metrics:
                        axs[0, 2].text(0.05, 0.05, "\n".join(metrics), transform=axs[0, 2].transAxes, 
                                      fontsize=9, verticalalignment='bottom', 
                                      bbox=dict(boxstyle='round,pad=0.5', 
                                               facecolor='white', alpha=0.7))
                else:
                    axs[0, 2].text(0.5, 0.5, "ELA data not available", 
                                 horizontalalignment='center', verticalalignment='center')
                    axs[0, 2].axis('off')
            else:
                axs[0, 2].text(0.5, 0.5, "ELA analysis not available", 
                             horizontalalignment='center', verticalalignment='center')
                axs[0, 2].axis('off')
                
            # Histogram visualization
            if 'histogram_analysis' in details:
                # Create histograms for each channel
                hist_r = np.histogram(img_array[:,:,0], bins=256, range=(0, 256))[0]
                hist_g = np.histogram(img_array[:,:,1], bins=256, range=(0, 256))[0]
                hist_b = np.histogram(img_array[:,:,2], bins=256, range=(0, 256))[0]
                
                # Plot the histograms
                bin_edges = np.arange(0, 257)
                axs[1, 0].plot(bin_edges[:-1], hist_r, color='red', alpha=0.7)
                axs[1, 0].plot(bin_edges[:-1], hist_g, color='green', alpha=0.7)
                axs[1, 0].plot(bin_edges[:-1], hist_b, color='blue', alpha=0.7)
                axs[1, 0].set_title("Color Channel Histograms")
                axs[1, 0].set_xlabel("Pixel Value")
                axs[1, 0].set_ylabel("Frequency")
                axs[1, 0].legend(['Red', 'Green', 'Blue'])
                
                # Show odd/even distribution analysis
                histogram_data = details['histogram_analysis']['details']
                
                # Get even/odd ratio values
                if 'even_odd_ratios' in histogram_data:
                    even_odd_ratios = histogram_data['even_odd_ratios']
                    
                    # Plot as bar chart
                    axs[1, 1].bar(['Red', 'Green', 'Blue'], even_odd_ratios, 
                                 color=['red', 'green', 'blue'], alpha=0.7)
                    axs[1, 1].axhline(y=1.0, linestyle='--', color='gray')
                    axs[1, 1].set_title("Even/Odd Value Ratios")
                    axs[1, 1].set_ylabel("Ratio (1.0 = balanced)")
                    
                    # Annotate with explanatory text
                    deviation = histogram_data.get('even_odd_deviation', 0)
                    assessment = "SUSPICIOUS" if deviation > 0.1 else "NORMAL"
                    axs[1, 1].annotate(f"Deviation: {deviation:.3f}\nAssessment: {assessment}", 
                                     xy=(0.05, 0.05), xycoords='axes fraction')
                else:
                    axs[1, 1].text(0.5, 0.5, "Histogram ratio data not available", 
                                  horizontalalignment='center', verticalalignment='center')
                    axs[1, 1].axis('off')
            else:
                axs[1, 0].text(0.5, 0.5, "Histogram analysis not available", 
                             horizontalalignment='center', verticalalignment='center')
                axs[1, 0].axis('off')
                axs[1, 1].axis('off')
            
            # Noise visualization
            if 'visual_noise_analysis' in details:
                noise_data = details['visual_noise_analysis']['details']
                noise_values = [noise_data.get('red_noise', 0), 
                                noise_data.get('green_noise', 0), 
                                noise_data.get('blue_noise', 0)]
                
                axs[1, 2].bar(['Red', 'Green', 'Blue'], noise_values, color=['red', 'green', 'blue'])
                axs[1, 2].set_title("Noise Levels by Channel")
                axs[1, 2].set_ylabel("Noise Level")
            else:
                axs[1, 2].text(0.5, 0.5, "Noise analysis not available", 
                              horizontalalignment='center', verticalalignment='center')
                axs[1, 2].axis('off')
            
            # File size analysis visualization
            if 'file_size_analysis' in details and 'details' in details['file_size_analysis']:
                size_data = details['file_size_analysis']['details']
                
                if ('file_size' in size_data and 'expected_min' in size_data 
                        and 'expected_max' in size_data and 'pixel_count' in size_data):
                    
                    # Create a simple bar chart comparing actual vs expected size
                    sizes = [size_data['file_size'], 
                            size_data['expected_min'], 
                            size_data['expected_max']]
                    
                    labels = ['Actual Size', 'Min Expected', 'Max Expected']
                    colors = ['blue', 'green', 'green']
                    
                    axs[2, 0].bar(labels, sizes, color=colors, alpha=0.7)
                    axs[2, 0].set_title("File Size Analysis")
                    axs[2, 0].set_ylabel("Size (bytes)")
                    
                    # Format y-axis to show human-readable sizes
                    axs[2, 0].get_yaxis().set_major_formatter(
                        plt.FuncFormatter(lambda x, loc: f"{x/1024:.1f}KB" if x >= 1024 else f"{x}B"))
                    
                    # Is it suspiciously large?
                    is_too_large = size_data['file_size'] > size_data['expected_max']
                    is_too_small = size_data['file_size'] < size_data['expected_min']
                    
                    if is_too_large:
                        assessment = f"SUSPICIOUS: {(size_data['file_size'] - size_data['expected_max'])/1024:.1f}KB larger than expected"
                    elif is_too_small:
                        assessment = f"SUSPICIOUS: {(size_data['expected_min'] - size_data['file_size'])/1024:.1f}KB smaller than expected"
                    else:
                        assessment = "NORMAL: Size within expected range"
                    
                    axs[2, 0].annotate(assessment, xy=(0.05, 0.05), xycoords='axes fraction', 
                                     fontsize=9, verticalalignment='bottom')
                else:
                    axs[2, 0].text(0.5, 0.5, "Size analysis data not available", 
                                 horizontalalignment='center', verticalalignment='center')
                    axs[2, 0].axis('off')
            else:
                axs[2, 0].text(0.5, 0.5, "Size analysis not available", 
                              horizontalalignment='center', verticalalignment='center')
                axs[2, 0].axis('off')
            
            # Metadata analysis visualization
            if 'metadata_analysis' in details and 'details' in details['metadata_analysis']:
                metadata = details['metadata_analysis']['details']
                
                metadata_text = f"Total metadata entries: {metadata.get('metadata_count', 0)}\n\n"
                
                if 'suspicious_markers' in metadata and metadata['suspicious_markers']:
                    metadata_text += "Suspicious markers found:\n"
                    for key, marker, value in metadata['suspicious_markers'][:3]:  # Show top 3
                        metadata_text += f"- '{marker}' in {key}\n"
                    
                    if len(metadata['suspicious_markers']) > 3:
                        metadata_text += f"...and {len(metadata['suspicious_markers'])-3} more\n"
                else:
                    metadata_text += "No suspicious metadata markers found"
                
                axs[2, 1].text(0.1, 0.5, metadata_text, fontsize=10, 
                             verticalalignment='center', horizontalalignment='left')
                axs[2, 1].set_title("Metadata Analysis")
                axs[2, 1].axis('off')
            else:
                axs[2, 1].text(0.5, 0.5, "Metadata analysis not available", 
                              horizontalalignment='center', verticalalignment='center')
                axs[2, 1].axis('off')
            
            # Overall analysis metrics
            axs[2, 2].axis('off')
            metrics_text = "Detection Confidence by Method:\n\n"
            
            for analysis_type, results in details.items():
                if isinstance(results, dict) and 'confidence' in results:
                    confidence_value = results['confidence']
                    if confidence_value > 70:
                        highlight = " 🚨 HIGH"
                    elif confidence_value > 40:
                        highlight = " ⚠️ MEDIUM"
                    else:
                        highlight = ""
                    metrics_text += f"{analysis_type.replace('_', ' ').title()}: {confidence_value:.1f}%{highlight}\n"
            
            axs[2, 2].text(0.1, 0.5, metrics_text, fontsize=10, verticalalignment='center')
            axs[2, 2].set_title("Overall Analysis Results")
        
        # Adjust layout
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        # Save figure
        report_filename = os.path.join(output_dir, f"steganalysis_{os.path.basename(image_path)}.png")
        plt.savefig(report_filename)
        plt.close()
        
        logging.debug(f"Created visual report: {report_filename}")
        return report_filename
    except Exception as e:
        logging.debug(f"Error creating visual report for {image_path}: {str(e)}")
        return None

def find_image_files(directory, recursive=True):
    """Find all image files in a directory."""
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp')
    image_files = []
    
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(image_extensions):
                    image_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, file)) and file.lower().endswith(image_extensions):
                image_files.append(os.path.join(directory, file))
    
    return image_files

def analyze_images(directory, sensitivity='medium', recursive=True, output_dir=None, max_workers=None):
    """
    Analyze all images in a directory for steganography.
    
    Args:
        directory: Directory to scan
        sensitivity: 'low', 'medium', or 'high'
        recursive: Whether to scan subdirectories
        output_dir: Directory to save visual reports
        max_workers: Number of worker processes
        
    Returns:
        List of suspicious image details
    """
    # Find all image files
    image_files = find_image_files(directory, recursive)
    if not image_files:
        logging.warning("No image files found!")
        return []
    
    logging.info(f"Found {len(image_files)} image files to analyze")
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"Visual reports will be saved to: {output_dir}")
    
    # Prepare input arguments for workers
    input_args = [(file_path, sensitivity, output_dir) for file_path in image_files]
    
    suspicious_images = []
    
    # Process files in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Colorful progress bar
        results = []
        futures = {executor.submit(process_file, arg): arg[0] for arg in input_args}
        
        with tqdm(
            total=len(image_files),
            desc=f"{colorama.Fore.RED}Analyzing images for steganography{colorama.Style.RESET_ALL}",
            unit="file",
            bar_format="{desc}: {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            colour="red"
        ) as pbar:
            for future in concurrent.futures.as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update progress
                    pbar.update(1)
                    
                    # Add to suspicious images if applicable
                    if result['suspicious']:
                        suspicious_images.append(result)
                        logging.info(f"Suspicious image found: {file_path} (confidence: {result['confidence']:.1f}%)")
                except Exception as e:
                    logging.error(f"Error analyzing {file_path}: {str(e)}")
                    pbar.update(1)
    
    # Sort suspicious images by confidence
    suspicious_images.sort(key=lambda x: x['confidence'], reverse=True)
    
    logging.info(f"Analysis complete. Found {len(suspicious_images)} suspicious images")
    return suspicious_images

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(
        description='RAT Finder: Steganography Detection Tool (v0.2.0)',
        epilog='Part of the 2PAC toolkit - Created by Richard Young'
    )
    
    # Main action
    parser.add_argument('directory', nargs='?', help='Directory to search for images')
    parser.add_argument('--check-file', type=str, help='Check a specific file for steganography')
    
    # Options
    parser.add_argument('--sensitivity', type=str, choices=['low', 'medium', 'high'], default='medium',
                       help='Set detection sensitivity level (default: medium)')
    parser.add_argument('--non-recursive', action='store_true', help='Only search in the specified directory, not subdirectories')
    parser.add_argument('--output', type=str, help='Save list of suspicious files to this file')
    parser.add_argument('--visual-reports', type=str, help='Directory to save visual analysis reports')
    parser.add_argument('--workers', type=int, default=None, help='Number of worker processes (default: CPU count)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    parser.add_argument('--version', action='version', version=f'RAT Finder v{VERSION} by Richard Young')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose, args.no_color)
    
    # Handle specific file check mode
    if args.check_file:
        file_path = args.check_file
        if not os.path.exists(file_path):
            logging.error(f"Error: File not found: {file_path}")
            sys.exit(1)
            
        print(f"\n{colorama.Style.BRIGHT}Analyzing file for steganography: {file_path}{colorama.Style.RESET_ALL}\n")
        
        is_suspicious, confidence, details = analyze_image(file_path, args.sensitivity)
        
        # Print results
        if is_suspicious:
            print(f"{colorama.Fore.RED}[!] SUSPICIOUS: This image may contain hidden data{colorama.Style.RESET_ALL}")
            print(f"Confidence: {confidence:.1f}%\n")
        else:
            print(f"{colorama.Fore.GREEN}[✓] No steganography detected in this image{colorama.Style.RESET_ALL}")
            print(f"Confidence: {(100 - confidence):.1f}% clean\n")
        
        # Details of analysis
        print(f"{colorama.Fore.CYAN}Detection Details:{colorama.Style.RESET_ALL}")
        
        for analysis_type, results in details.items():
            if isinstance(results, dict) and 'confidence' in results:
                detection_status = f"{colorama.Fore.RED}[DETECTED]" if results['suspicious'] else f"{colorama.Fore.GREEN}[OK]"
                print(f"{detection_status} {analysis_type.replace('_', ' ').title()}: {results['confidence']:.1f}%{colorama.Style.RESET_ALL}")
                
                # Print specific findings
                if 'details' in results and isinstance(results['details'], dict):
                    for key, value in results['details'].items():
                        if key != 'error':
                            print(f"  - {key}: {value}")
        
        # Create visual report if requested
        if args.visual_reports:
            report_path = create_visual_report(file_path, confidence, details, args.visual_reports)
            if report_path:
                print(f"\n{colorama.Fore.CYAN}Visual report saved to: {report_path}{colorama.Style.RESET_ALL}")
        
        sys.exit(0)
    
    # Check if directory is specified
    if not args.directory:
        logging.error("Error: You must specify a directory to scan or use --check-file for a specific file")
        sys.exit(1)
    
    directory = Path(args.directory)
    
    # Verify the directory exists
    if not directory.exists() or not directory.is_dir():
        logging.error(f"Error: {directory} is not a valid directory")
        sys.exit(1)
    
    # Begin analysis
    logging.info(f"Starting steganography analysis with {args.sensitivity} sensitivity")
    logging.info(f"Scanning for images in {directory}")
    
    try:
        suspicious_images = analyze_images(
            directory,
            sensitivity=args.sensitivity,
            recursive=not args.non_recursive,
            output_dir=args.visual_reports,
            max_workers=args.workers
        )
        
        # Print summary
        if suspicious_images:
            count_str = f"{colorama.Fore.RED}{len(suspicious_images)}{colorama.Style.RESET_ALL}"
            logging.info(f"Found {count_str} suspicious images that may contain hidden data")
            
            # Print top findings
            print("\nTop suspicious images:")
            for i, result in enumerate(suspicious_images[:10]):  # Show top 10
                confidence_color = colorama.Fore.RED if result['confidence'] > 80 else colorama.Fore.YELLOW
                print(f"{i+1}. {result['path']} - Confidence: {confidence_color}{result['confidence']:.1f}%{colorama.Style.RESET_ALL}")
                
            if len(suspicious_images) > 10:
                print(f"... and {len(suspicious_images) - 10} more")
        else:
            logging.info(f"{colorama.Fore.GREEN}No suspicious images found{colorama.Style.RESET_ALL}")
        
        # Save output if requested
        if args.output and suspicious_images:
            with open(args.output, 'w') as f:
                for result in suspicious_images:
                    f.write(f"{result['path']},{result['confidence']:.1f}\n")
            logging.info(f"Saved list of suspicious files to {args.output}")
            
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
        
    # Add signature at the end
    if not args.no_color:
        signature = f"\n{colorama.Fore.RED}RAT Finder v{VERSION} by Richard Young{colorama.Style.RESET_ALL}"
        tagline = f"{colorama.Fore.YELLOW}\"Uncovering what's hidden in plain sight.\"{colorama.Style.RESET_ALL}"
        print(signature)
        print(tagline)

if __name__ == "__main__":
    main()