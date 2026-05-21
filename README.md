---
title: 2PAC + RAT Finder
emoji: 🔫
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 6.14.0
app_file: app.py
python_version: 3.11
pinned: false
license: mit
---

# 2PAC + RAT Finder

**2PAC** hides secret data inside images. **RAT Finder** catches problems — hidden data, corrupt files, broken images.

You want to put data in — use **2PAC**. You want to find out if it's bad — use **RAT Finder**.

```
pip install -r requirements.txt

# Put data in
python 2pac.py hide --image photo.png --data "secret" --output out.png

# Find out if it's bad
python ratfinder.py detect suspicious.png --sensitivity high
python ratfinder.py check broken.jpg --check-visual
```

**Try it live:** [richardyoung-2pac.hf.space](https://richardyoung-2pac.hf.space)

---

## Two Tools

### 2PAC — Put Data In

2PAC is a steganography tool. It hides text inside images using two methods:

| Method | How it works | Capacity | Status |
|---|---|---|---|
| **LSB** | Modifies the least significant bit of pixel values — invisible to the eye | ~375 KB per megapixel | Stable |
| **DCT** | Hides data in frequency-domain coefficients — harder to detect | ~116 bytes per 256×256 image | Experimental |

```bash
# Hide a message
python 2pac.py hide --image photo.png --data "secret message" --output out.png

# Encrypted
python 2pac.py hide --image photo.png --data "secret" --password hunter2 --output out.png

# Extract
python 2pac.py extract --image out.png
python 2pac.py extract --image out.png --password hunter2
```

**Key details:**
- Output is always PNG — JPEG compression destroys hidden data
- Optional XOR encryption with SHA-256 password hashing
- 1–4 bits per channel: 1 is undetectable, 4 gives more capacity but is visible in smooth areas
- A 1000×1000 image with 1 bit/channel hides ~375 KB

### RAT Finder — Find Problems

RAT Finder detects two kinds of image problems:

**Steganography detection** — Seven forensic techniques that analyze an image for signs of hidden data:

| # | Technique | What it detects |
|---|---|---|
| 1 | LSB Chi-Squared | Statistical randomness in least-significant bits |
| 2 | Histogram Analysis | "Comb patterns" from systematic LSB modification |
| 3 | Error Level Analysis | Compression inconsistencies from tampering |
| 4 | Visual Noise | Channel-specific noise imbalances from data embedding |
| 5 | Metadata Inspection | Known steganography tool signatures in EXIF |
| 6 | File Size Anomalies | Suspiciously large or small files |
| 7 | Trailing Data | Data appended after end-of-file markers |

**Image validation** — Multi-step pipeline that checks for structural corruption:

| Step | What it checks |
|---|---|
| Header verify | File format header is valid |
| Full pixel decode | Every pixel can be decoded — catches truncation |
| Visual corruption | Detects gray/black blocks from damaged storage |
| Structure audit | JPEG marker chain or PNG chunk validation |
| Re-encode test | Subtle decoder errors that pass basic checks |
| External tools | Runs exiftool and ImageMagick if installed |

```bash
# Detect steganography
python ratfinder.py detect suspicious.png
python ratfinder.py detect ./downloads --sensitivity high --workers 8

# Check a single image for corruption
python ratfinder.py check broken.jpg --check-visual

# Scan a directory (dry run)
python ratfinder.py scan ./photos --thorough

# Scan and repair
python ratfinder.py scan ./photos --thorough --repair --backup-dir ./backups

# Move bad files
python ratfinder.py scan ./photos --move-to ./quarantine
```

**Supported formats:** JPEG, PNG, GIF (repairable). TIFF, BMP, WebP, HEIC, ICO (detectable).

---

## How Steganography Works

Every pixel in a digital image is stored as numbers. In an RGB PNG, each pixel has three channels (red, green, blue), each 0–255 — 8 binary bits per channel.

LSB steganography modifies only the **last bit** (least significant bit) of each channel. The change is invisible:

```
Original:  R=156  G=89   B=201   →   10011100 01011001 11001001
                                                   ^-- becomes 0 or 1
Modified:  R=156  G=88   B=201   →   (89→88, invisible)
```

A 1000×1000 image can hide ~375 KB of text this way.

DCT steganography operates on the frequency domain (8×8 pixel blocks) instead of pixel values directly. Much harder to detect with LSB-based forensic tools, but very low capacity (~1 bit per 64 pixels).

---

## Quick Start

```bash
git clone https://github.com/ricyoung/2pac.git
cd 2pac
pip install -r requirements.txt
python app.py              # Browser UI at http://localhost:7860
```

Or use the web UI: [richardyoung-2pac.hf.space](https://richardyoung-2pac.hf.space)

---

## Project Structure

```
2pac/
├── 2pac.py                 # CLI: hide + extract data
├── ratfinder.py            # CLI: detect stego + scan corrupt images
├── app.py                  # Gradio web UI
├── steg_embedder.py        # LSB steganography engine
├── dct_steg.py             # DCT steganography engine (experimental)
├── rat_finder.py           # Steganography detection — 7 forensic techniques
├── find_bad_images/        # Image corruption scanner
│   ├── config.py           # Format definitions
│   ├── security.py         # File validation, path traversal prevention
│   ├── validation.py       # Integrity checks and visual corruption
│   ├── processing.py       # Batch scanning, repair, sessions
│   └── cli.py              # Internal CLI logic
├── utils.py                # Shared logging, sensitivity mapping
├── tests/
│   ├── test_steg_embedder.py  # 35 LSB tests
│   └── test_dct_steg.py       # 9 DCT tests
└── requirements.txt
```

---

## About

Created by [Richard Young](https://github.com/ricyoung) | [DeepNeuro.AI](https://deepneuro.ai)

*In memory of Jeff Young. All Eyez On Your Images.*

---

[GitHub](https://github.com/ricyoung/2pac) | [Hugging Face Space](https://huggingface.co/spaces/richardyoung/2pac) | [DeepNeuro.AI](https://deepneuro.ai)
