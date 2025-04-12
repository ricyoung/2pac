# RAT Finder: Steganography Detection Tool

<div align="center">

![Version](https://img.shields.io/badge/version-0.2.0-red.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**"Finding what's hidden in plain sight" - Part of the 2PAC toolkit**

</div>

## 🔍 Overview

RAT Finder is a powerful steganography detection tool designed to identify hidden data in images. As a critical security component of the 2PAC toolkit, it helps users detect potential malicious data concealed within seemingly innocent images.

> **Note:** RAT Finder is currently in beta. While it provides comprehensive detection capabilities, it may produce false positives and continues to be refined for greater accuracy.

## 🚀 Features

- **Multi-technique Detection:** Employs five different analysis methods to catch varied steganographic techniques
- **Confidence-based Reporting:** Assigns confidence scores to help prioritize suspicious files
- **Visual Analysis Reports:** Generates detailed visual reports for suspicious images
- **Adjustable Sensitivity:** Customize detection thresholds to balance false positives and negatives
- **Parallel Processing:** Fast scanning with multi-core support
- **Command-line Interface:** Easy to use and integrate into security workflows

## 🔎 Supported Detection Methods

### 1. LSB (Least Significant Bit) Analysis

<table>
<tr>
<td width="60%" valign="top">

**What it detects:**
- LSB insertion steganography (most common technique)
- Subtle bit manipulations in image pixels
- Unnatural bit patterns and distributions

**Implementation details:**
- Chi-square statistical testing
- Entropy calculation of LSB plane
- Color distribution analysis across channels

</td>
<td width="40%">

```
LSB insertion modifies the lowest 
significant bits of pixel values:

Original: 10101100 10111010 10101011
Hidden A: 10101101 10111011 10101010
         (changes)  ↑      ↑      ↑
```

</td>
</tr>
</table>

### 2. Error Level Analysis (ELA)

<table>
<tr>
<td width="60%" valign="top">

**What it detects:**
- Image manipulation in JPEG compression
- Areas with different error levels than the rest of the image
- Potential data hiding in DCT (Discrete Cosine Transform) domains
- Suspicious artifacts from multiple compressions

**Implementation details:**
- Recompresses images at a known quality level
- Analyzes differences between original and recompressed images
- Block-based variance analysis to detect inconsistencies
- Coefficient of variation measurements across image blocks
- Especially effective for detecting steganography in JPEG images

</td>
<td width="40%">

```
Original: JPEG (quality 90)
                    ┌─────────┐
                    │ Resave  │
                    │ at q=75 │
                    └────┬────┘
                         ▼
Differences:  ┌──────────────────┐
              │ Analyze variance │
              │ patterns in      │
              │ 8x8 pixel blocks │
              └──────────────────┘
                         ▼
Manipulated areas show different
error levels than natural areas
```

</td>
</tr>
</table>

### 3. Histogram Analysis

<table>
<tr>
<td width="60%" valign="top">

**What it detects:**
- DCT-based steganography (used in JPEG)
- Palette-based steganography
- Statistical anomalies from frequency manipulation

**Implementation details:**
- Detection of comb patterns in histograms
- Even/odd pixel value ratio analysis
- Histogram smoothness measurement
- Detection of unnatural spikes and distributions

</td>
<td width="40%">

```
Normal histogram:
    ___
   /   \
__/     \___

Suspicious histogram:
   _   _   _
  / | / | / |
_/  |/  |/  |_
   (comb pattern)
```

</td>
</tr>
</table>

### 4. File Size & Format Analysis

<table>
<tr>
<td width="60%" valign="top">

**What it detects:**
- Appended data after file end
- Unusually large files for their dimensions
- Format-specific anomalies

**Implementation details:**
- Pixel count vs. file size ratio analysis
- Format-appropriate size expectations
- Dimension vs. compression ratio verification

</td>
<td width="40%">

```
Suspiciously large file:

Expected size:  120KB
Actual size:    350KB
Difference:     230KB (potential hidden data)
```

</td>
</tr>
</table>

### 5. Metadata Analysis

<table>
<tr>
<td width="60%" valign="top">

**What it detects:**
- Hidden data in metadata fields
- Steganography software markers/signatures
- Suspiciously large or numerous metadata entries

**Implementation details:**
- EXIF, IPTC, and XMP metadata parsing
- Known steganography software signature detection
- Metadata size and count anomaly detection

</td>
<td width="40%">

```
Suspicious metadata:

Software: "OutGuess 1.3"
Comment: "s*3G@n0f1l3..."
ExifTool: [unusual length data]
```

</td>
</tr>
</table>

### 6. Visual Noise Analysis

<table>
<tr>
<td width="60%" valign="top">

**What it detects:**
- Spread spectrum steganography
- Watermark-based methods
- Noise pattern anomalies between color channels

**Implementation details:**
- Channel-specific noise level calculation
- Noise pattern comparison across color channels
- Differential analysis of adjacent pixels
- Detection of systematic vs. random noise patterns

</td>
<td width="40%">

```
Channel noise comparison:

Red:    12.3 (normal)
Green:  11.8 (normal)
Blue:   37.6 (suspicious!)

Normal images have similar noise 
levels across channels.
```

</td>
</tr>
</table>

## 📊 Confidence Scoring

RAT Finder uses a weighted confidence scoring system:

| Detection Method | Weight | Description |
|------------------|--------|-------------|
| LSB Analysis | 25% | Detects the most common techniques |
| Error Level Analysis (ELA) | 20% | Effective for JPEG manipulations |
| Histogram Analysis | 20% | Effective for DCT and statistical anomalies |
| Visual Noise Analysis | 15% | Good for detecting spread spectrum methods |
| File Size Analysis | 10% | Identifies appended data and size anomalies |
| Metadata Analysis | 10% | Finds hidden content in file metadata |

The overall confidence score is calculated as a weighted sum of individual detection methods. Images with scores above the threshold (dependent on sensitivity setting) are flagged as suspicious.

Note: For non-JPEG files, the ELA weight is redistributed proportionally among the other methods.

## 🖼️ Visual Reports

For suspicious images, RAT Finder can generate detailed visual reports that include:

1. **Original Image:** The file being analyzed
2. **LSB Visualization:** Visual representation of the least significant bits
3. **Error Level Analysis (ELA):** Highlights areas with suspicious error levels
4. **Color Channel Histograms:** Distribution of pixel values in each channel
5. **Even/Odd Ratio Analysis:** Visualization of potential LSB manipulation
6. **Noise Level Analysis:** Channel-specific noise measurements
7. **File Size Comparison:** Actual vs. expected file size visualization
8. **Metadata Summary:** Overview of metadata findings
9. **Confidence Breakdown:** Method-by-method detection confidence

## 💻 Usage

### Basic Usage

```bash
# Scan a directory for steganography
./rat_finder.py /path/to/images

# Quick exit
./rat_finder.py q

# Scan with high sensitivity (fewer false negatives, more false positives)
./rat_finder.py /path/to/images --sensitivity low

# Scan with low sensitivity (fewer false positives, more false negatives)
./rat_finder.py /path/to/images --sensitivity high

# Generate visual reports for suspicious images
./rat_finder.py /path/to/images --visual-reports /path/to/reports
```

### Analyzing a Single File

```bash
# Check a specific file for steganography
./rat_finder.py --check-file /path/to/suspicious.jpg

# Check a file and generate a visual report
./rat_finder.py --check-file /path/to/suspicious.jpg --visual-reports /path/for/report
```

### Advanced Options

```bash
# Use a specific number of CPU cores
./rat_finder.py /path/to/images --workers 4

# Non-recursive scan (only the specified directory, not subdirectories)
./rat_finder.py /path/to/images --non-recursive

# Save list of suspicious files to a text file
./rat_finder.py /path/to/images --output suspicious_files.txt

# Enable verbose logging
./rat_finder.py /path/to/images --verbose
```

## 📋 Requirements

- Python 3.6+
- NumPy
- SciPy
- Matplotlib
- Pillow (PIL)
- Colorama

## 📌 Detection Effectiveness

The following table shows RAT Finder's effectiveness against various steganography methods:

| Steganography Technique | Detection Effectiveness | Detection Methods Used |
|-------------------------|-------------------------|------------------------|
| **LSB Insertion** | ★★★★☆ (High) | LSB Analysis, Histogram Analysis |
| **DCT Domain Embedding** | ★★★★☆ (High) | Error Level Analysis, Histogram Analysis |
| **JPEG Manipulation** | ★★★★☆ (High) | Error Level Analysis, Visual Noise Analysis |
| **Palette-Based** | ★★★☆☆ (Moderate) | Histogram Analysis, File Size Analysis |
| **Metadata/Header** | ★★★★★ (Very High) | Metadata Analysis |
| **Appended Data** | ★★★★★ (Very High) | File Size Analysis |
| **Spread Spectrum** | ★★☆☆☆ (Low) | Visual Noise Analysis |
| **Error-Correcting Code** | ★★☆☆☆ (Low) | LSB Analysis, Histogram Analysis |

## 🔄 Future Improvements

- Machine learning-based detection
- Support for video file analysis
- Detection of audio steganography
- Additional format-specific checks
- Better handling of false positives
- Support for encrypted steganography detection

## 🔗 Integration with 2PAC

RAT Finder is designed to complement the 2PAC image corruption detection toolkit:

- 2PAC finds and repairs corrupt images
- RAT Finder detects images with hidden data
- Use both tools for comprehensive image security

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

Created by Richard Young, author of 2PAC.

---

<div align="center">

*"What the eyes see and the ears hear, the mind believes." - In memory of Jeff Young*

</div>