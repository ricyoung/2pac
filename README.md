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

# 2PAC: Picture Analyzer & Corruption Killer

**Advanced image security toolkit: hide messages, detect steganography, validate image integrity.**

---

## Two Tools

2PAC has **two CLIs** for different jobs, plus a **Gradio web app** that exposes both.

### `2pac_stego.py` — Steganography (hide, extract, detect)

| Subcommand | Purpose |
|---|---|
| `hide` | Embed text in an image (LSB or DCT) |
| `extract` | Recover hidden text from an image |
| `detect` | Scan images for signs of steganography (RAT Finder) |

```bash
# Hide a message
python 2pac_stego.py hide --image photo.png --data "secret" --output out.png

# Hide with DCT (harder to detect, lower capacity)
python 2pac_stego.py hide --image photo.png --data "secret" --dct

# Extract
python 2pac_stego.py extract --image out.png

# Detect steganography in a file or directory
python 2pac_stego.py detect suspicious.png
python 2pac_stego.py detect ./photos --sensitivity high --workers 8
```

### `2pac_scan.py` — Image Corruption Scanner

| Mode | Purpose |
|---|---|
| Batch scan | Find corrupt images in a directory |
| Single check | Diagnose one file |
| Repair | Attempt to fix damaged images |

```bash
# Scan a directory (dry run by default)
python 2pac_scan.py ./images --thorough

# Delete corrupt files
python 2pac_scan.py ./images --delete

# Move bad files + attempt repair
python 2pac_scan.py ./images --move-to ./bad --repair

# Check a single file
python 2pac_scan.py --check-file broken.jpg --check-visual

# Resume a saved session
python 2pac_scan.py ./images --resume <session_id>
```

### How They Differ

| | RAT Finder (`2pac_stego.py detect`) | 2PAC Scan (`2pac_scan.py`) |
|---|---|---|
| **What** | Detects steganography — hidden messages in images | Detects corruption — broken/damaged image files |
| **Looks for** | Suspicious LSB patterns, ELA artifacts, histogram anomalies | Truncated files, bad JPEG/PNG headers, visual damage, decoder errors |
| **Use case** | "Does this image contain a secret message?" | "Is this image file corrupted?" |
| **Repair** | No | Yes — JPEG/PNG/GIF repair |
| **Output** | Confidence score + forensic details | Bad file list + repair results + move/delete actions |

### Gradio Web App / Hugging Face Space

Run `python app.py` for the browser-based interface, or use the Hugging Face Space. The UI is organized around the same two-tool model:

| Tab | Purpose |
|---|---|
| **Start Here** | Explains RAT Finder vs 2PAC Scan and shows CLI equivalents |
| **Stego Tool** | Hide, extract, and detect hidden data |
| **2PAC Scan** | Single-image validation, batch validation, repair guidance |
| **CLI** | Local command examples for automation |

The Space includes generated sample images and batch validation without storing binary image assets in the repository.

---

## Steganography Methods

### LSB (Least Significant Bit)
Hides data in the lowest bits of pixel values. Fast, high capacity, visually imperceptible.

```
Original: RGB(156, 89, 201) → 10011100 01011001 11001001
Bit 0 →   RGB(156, 88, 201) → 10011100 01011000 11001001  (89→88, invisible)
```

### DCT (Frequency Domain)
Hides data in mid-frequency DCT coefficients of 8×8 pixel blocks. Much harder to detect with LSB-based analysis since modifications are in the frequency domain.

---

## RAT Finder — Steganography Detection

Seven forensic techniques with weighted confidence scoring:

| # | Technique | Weight | What it detects |
|---|---|---|---|
| 1 | **ELA** (Error Level Analysis) | 20% | Compression inconsistencies from tampering |
| 2 | **LSB Analysis** | 25% | Statistical randomness in pixel LSBs |
| 3 | **Histogram Analysis** | 20% | Color distribution anomalies |
| 4 | **Metadata Inspection** | 15% | EXIF tool signatures, editing history |
| 5 | **File Size Analysis** | 10% | Suspiciously large or small files |
| 6 | **Visual Noise** | 5% | Channel noise imbalances |
| 7 | **Trailing Data** | 5% | Appended data after EOF markers |

Confidence ≥ 70% = HIGH SUSPICION.

---

## 2PAC Scan — Validation & Repair

Comprehensive image integrity checks:

- Format validation (JPEG, PNG, GIF, TIFF, BMP, WebP, HEIC, ICO)
- JPEG marker chain analysis
- PNG chunk validation
- Visual corruption detection (gray/black blocks, color distribution)
- Full decode testing
- External tool integration (exiftool, identify)
- Repair via re-encoding (JPEG, PNG, GIF)
- Session progress saving + resuming
- Security: DoS prevention (100MB limit, 50MP limit), path traversal protection

---

## Usage Tips

- **Use PNG** for stego output — JPEG compression destroys hidden data
- **1-2 bits/channel** is undetectable; 3-4 gives more capacity
- **DCT mode** is harder to detect but stores less data per image
- **Higher sensitivity** on detection catches more but increases false positives
- **Enable visual checks** on 2PAC Scan for physically damaged photos

---

## About

Created by [Richard Young](https://github.com/ricyoung) | Part of [DeepNeuro.AI](https://deepneuro.ai)

In memory of Jeff Young. *"All Eyez On Your Images"*

---

🔗 [github.com/ricyoung/2pac](https://github.com/ricyoung/2pac)  |  🌐 [demo.deepneuro.ai](https://demo.deepneuro.ai)

## Security & Privacy

- All processing happens in your browser session
- Images are not stored or logged
- Temporary files deleted after processing
- Passwords and hidden data never saved
