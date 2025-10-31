---
title: 2PAC Picture Analyzer & Corruption Killer
emoji: 🔫
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# 🔫 2PAC: Picture Analyzer & Corruption Killer

**Advanced image security and steganography toolkit**

## Features

### 🔒 Hide Secret Data
Invisibly hide text messages inside images using **LSB (Least Significant Bit) steganography**:
- Hide text of any length (capacity depends on image size)
- Optional password encryption for added security
- Adjustable LSB depth (1-4 bits per channel)
- PNG output preserves hidden data perfectly

### 🔍 Detect & Extract Hidden Data
Advanced steganography detection using **RAT Finder** technology:
- **ELA (Error Level Analysis)** - Highlights compression artifacts
- **LSB Analysis** - Detects randomness in least significant bits
- **Histogram Analysis** - Finds statistical anomalies
- **Metadata Inspection** - Checks EXIF data for suspicious tools
- **Extract Data** - Recover messages hidden with this tool

### 🛡️ Check Image Integrity
Comprehensive image validation and corruption detection:
- File format validation (JPEG, PNG, GIF, TIFF, BMP, WebP, HEIC)
- Header integrity checks
- Data completeness verification
- Visual corruption detection (black/gray regions)
- Structure validation

## How It Works

### LSB Steganography
The tool hides data in the **least significant bits** of pixel values. Since changing the last 1-2 bits of a pixel value (e.g., changing 200 to 201) is imperceptible to the human eye, we can encode arbitrary data without visible changes to the image.

**Example:**
- Original pixel: RGB(156, 89, 201) = `10011100, 01011001, 11001001`
- After hiding bit '1': RGB(156, 89, 201) = `10011100, 01011001, 11001001` (last bit already 1)
- After hiding bit '0': RGB(156, 88, 201) = `10011100, 01011000, 11001001` (89→88)

This allows hiding hundreds to thousands of bytes in a typical photo!

### Steganography Detection
The RAT Finder uses multiple forensic techniques:

1. **ELA (Error Level Analysis)**: Re-saves the image at a known quality and compares compression artifacts. Hidden data or manipulation shows as bright areas.

2. **LSB Analysis**: Statistical tests check if the least significant bits are too random (hidden data) or too uniform (natural image).

3. **Histogram Analysis**: Analyzes color distribution for anomalies typical of steganography.

4. **Metadata Forensics**: Checks EXIF data for steganography tools or suspicious editing history.

## Usage Tips

### For Hiding Data:
- ✅ Use **PNG** images (JPEG compression destroys hidden data)
- ✅ Larger images = more capacity
- ✅ Use 1-2 bits per channel for undetectable hiding
- ✅ Add password encryption for sensitive data
- ⚠️ Don't re-save or edit the output image!

### For Detection:
- 🔍 Higher sensitivity = more thorough but more false positives
- 📊 Check the ELA image for bright spots (potential hiding)
- 💡 High confidence doesn't guarantee hidden data (could be compression artifacts)
- 🔓 Use "Extract Data" tab if you suspect LSB steganography

### For Corruption Checking:
- 🛡️ Enable visual corruption check for damaged photos
- ⚙️ Higher sensitivity for stricter validation
- 📁 Useful before archiving important photo collections

## About

**2PAC** combines three powerful tools:
- **LSB Steganography** engine (new!)
- **RAT Finder** - Advanced steg detection
- **Image Validator** - Corruption checker

Created by [Richard Young](https://github.com/ricyoung) | Part of [DeepNeuro.AI](https://deepneuro.ai)

🔗 **GitHub Repository:** [github.com/ricyoung/2pac](https://github.com/ricyoung/2pac)
🌐 **More Tools:** [demo.deepneuro.ai](https://demo.deepneuro.ai)

## Security & Privacy

- ✅ All processing happens in your browser session (Hugging Face Space)
- ✅ Images are not stored or logged
- ✅ Temporary files are deleted after processing
- ✅ Your hidden data and passwords are never saved

---

*"All Eyez On Your Images" 👁️*
