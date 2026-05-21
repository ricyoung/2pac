---
title: 2PAC Picture Analyzer & Corruption Killer
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

# 2PAC: Picture Analyzer & Corruption Killer

**Hide messages inside images. Detect hidden data. Find and repair corrupt image files.**

2PAC is a self-contained image security toolkit with two specialized tools, a browser UI, and full CLI automation. Everything runs locally — no cloud APIs, no data leaves your machine.

```
pip install -r requirements.txt
python app.py                        # browser UI
python 2pac_stego.py hide ...        # CLI: hide data
python 2pac_scan.py ./photos ...     # CLI: scan for corruption
```

**Try it live:** [richardyoung-2pac.hf.space](https://richardyoung-2pac.hf.space)

---

## Why Two Tools?

These are fundamentally different problems that people often confuse:

| | Stego Tool (`2pac_stego.py`) | 2PAC Scan (`2pac_scan.py`) |
|---|---|---|
| **Question it answers** | *"Is there a hidden message inside this image?"* | *"Is this image file broken or corrupted?"* |
| **What it detects** | LSB patterns, frequency-domain anomalies, histogram irregularities, EXIF tool signatures | Truncated files, bad headers, decoder errors, visual corruption (gray/black blocks) |
| **What it can do** | Hide messages, extract them, or just detect signs of steganography | Validate, diagnose, and attempt repair of damaged image files |
| **Formats** | PNG input/output (JPEG destroys hidden data) | JPEG, PNG, GIF, TIFF, BMP, WebP, HEIC, ICO |
| **Best for** | Security research, CTF challenges, privacy | Photo archives, downloaded collections, data recovery |

---

## Quick Start

### Web UI

```bash
python app.py
```

Opens a browser interface with four tabs:

| Tab | What you can do |
|---|---|
| **Start Here** | Learn which tool to use and see CLI equivalents |
| **Stego Tool** | Hide text in images (LSB or DCT), extract hidden text, run forensic detection |
| **2PAC Scan** | Validate single images or batch-upload files to check for corruption |
| **CLI** | Local command examples for automation and scripting |

### CLI — Hide a Message

```bash
# Basic: hide text in an image
python 2pac_stego.py hide --image photo.png --data "secret message" --output stego.png

# Encrypted: add a password
python 2pac_stego.py hide --image photo.png --data "secret message" --password hunter2 --output stego.png

# More capacity at the cost of subtlety (1-4 bits per channel)
python 2pac_stego.py hide --image photo.png --data "longer message..." --bits 2 --output stego.png

# DCT mode: hides in frequency domain instead of pixel values
python 2pac_stego.py hide --image photo.png --data "hidden" --dct --output stego.png
```

### CLI — Extract a Message

```bash
python 2pac_stego.py extract --image stego.png
python 2pac_stego.py extract --image stego.png --password hunter2
python 2pac_stego.py extract --image stego.png --dct          # if embedded with DCT
python 2pac_stego.py extract --image stego.png --bits 2       # must match embed settings
```

### CLI — Detect Steganography (RAT Finder)

```bash
# Scan a single file
python 2pac_stego.py detect suspicious.png

# Scan a directory with high sensitivity
python 2pac_stego.py detect ./downloads --sensitivity high --workers 8

# Generate visual forensic reports
python 2pac_stego.py detect suspicious.png --visual-reports --reports-dir ./reports
```

### CLI — Scan for Corrupt Images

```bash
# Dry run: report problems without changing anything (default)
python 2pac_scan.py ./photos --thorough

# Move bad files to a quarantine folder and attempt repair
python 2pac_scan.py ./photos --move-to ./quarantine --repair --backup-dir ./backups

# Delete corrupt files (use with caution)
python 2pac_scan.py ./photos --delete

# Check a single file with visual corruption detection
python 2pac_scan.py --check-file questionable.jpg --check-visual

# Resume an interrupted scan
python 2pac_scan.py ./photos --resume abc123
```

---

## How Steganography Works

### LSB (Least Significant Bit) — Primary Method

Every pixel in a digital image is stored as numbers. In an RGB PNG, each pixel has three channels (red, green, blue), each ranging from 0 to 255 — that's 8 binary bits per channel.

LSB steganography modifies only the **last bit** (the least significant bit) of each channel value. The change is invisible to the human eye:

```
Original pixel:  R=156  G=89   B=201
In binary:       10011100 01011001 11001001
                                     ^-- this bit becomes 0 or 1 to store your data
Modified pixel:  R=156  G=88   B=201    (89 → 88, invisible difference)
```

**Capacity:** A 1000×1000 RGB image with 1 bit/channel can hide ~375 KB of data. Increasing to 2-4 bits/channel multiplies capacity but becomes statistically detectable.

**Strengths:** Fast, high capacity, visually identical to the original.
**Weaknesses:** Detected by chi-squared analysis and histogram examination. Destroyed by any lossy compression (JPEG, WebP).

### DCT (Discrete Cosine Transform) — Experimental Method

Instead of modifying pixel values directly, DCT steganography operates on the **frequency domain**. The image is divided into 8×8 pixel blocks, and each block is transformed using the same DCT math that JPEG compression uses. Data is hidden by adjusting the parity (even/odd) of mid-frequency coefficients.

```
Spatial domain (what you see):    Frequency domain (what DCT sees):
┌──────────────────┐              ┌──────────────────┐
│  pixel values     │    DCT      │  frequency coeffs │
│  156 89 201 ...   │  ──────►   │  low-freq → high  │
│  changes visible  │             │  changes hidden   │
└──────────────────┘              └──────────────────┘
```

**Capacity:** Very low — approximately 1 bit per 64 pixels (one 8×8 block). A 256×256 image holds ~116 bytes.

**Strengths:** Much harder to detect with LSB-based forensic tools. Survives some statistical tests that catch LSB embedding.
**Weaknesses:** Very low capacity. DCT→integer→DCT round-trip introduces rounding errors that can corrupt data. Still experimental — not reliable for critical data.

### Encryption

Both methods support optional password-based encryption:

- Your password is hashed with SHA-256 to produce a 32-byte key
- The data is XOR-encrypted with this key before embedding
- Extraction requires the same password to recover the original text
- Without the password, you get garbled bytes

> **Note:** This is not military-grade encryption. It's an obfuscation layer. The primary security of steganography is that the hidden data *exists at all* is undetectable.

---

## How Detection Works — RAT Finder

RAT Finder runs **seven forensic techniques** and combines their results into a weighted confidence score:

| # | Technique | Weight | What it looks for |
|---|---|---|---|
| 1 | **LSB Chi-Squared Analysis** | 25% | Statistical randomness in the least significant bits. Natural images have structured LSBs; steganography makes them uniformly random. Uses scipy's chi-squared test and Shannon entropy measurement. |
| 2 | **Histogram Analysis** | 20% | "Comb patterns" in color histograms — when LSBs are systematically modified, even and odd color values become suspiciously similar, creating a distinctive sawtooth pattern. |
| 3 | **Error Level Analysis (ELA)** | 20% | Re-saves the image at a known quality level and measures pixel differences. Edited or modified regions show different error levels than the rest of the image. JPEG-only. |
| 4 | **Visual Noise Analysis** | 15% | Compares noise levels across color channels. Steganography that embeds more data in one channel creates an imbalance detectable by comparing adjacent-pixel differences. |
| 5 | **Metadata Inspection** | 10% | Scans EXIF metadata for known steganography tool signatures (OutGuess, StegHide, JSteg, F5, etc.) and flags suspiciously large metadata blocks. |
| 6 | **File Size Anomalies** | 10% | Compares actual file size against expected ranges for the image dimensions and format. Embedded payloads bloat the file; some tools also strip metadata to compensate, creating unusual sizes. |
| 7 | **Trailing Data Detection** | 10% | Checks for data appended after the file's official end-of-file marker (JPEG `FF D9` or PNG `IEND`). A common lazy steganography technique. |

**Scoring:** Each technique returns a 0-100 confidence. The final score is the weighted average. A score ≥ 70% triggers HIGH SUSPICION, 40-70% is MODERATE, below 40% is LOW.

**Sensitivity levels:**
- `low` — More sensitive, catches subtle embedding but increases false positives
- `medium` — Balanced (default)
- `high` — Stricter thresholds, fewer false positives, may miss subtle embedding

---

## How Image Validation Works — 2PAC Scan

### What Can Go Wrong With an Image File?

Image files break in many ways:

| Problem | Example cause |
|---|---|
| **Truncated file** | Download interrupted, disk full during save |
| **Corrupt header** | Bad transfer encoding, bit rot on old storage |
| **Invalid JPEG markers** | Camera firmware bug, file system corruption |
| **Broken PNG chunks** | Incomplete write, SD card failure |
| **Decoder errors** | Pixel data doesn't match header dimensions |
| **Visual corruption** | Gray/black blocks where image data should be — common in recovered/degraded files |
| **Format mismatch** | File extension says `.jpg` but actual content is PNG |

### The Validation Pipeline

When you run a scan, each image passes through up to six checks:

```
┌─────────────────────┐
│ 1. Header verify    │  PIL's built-in header check (fast)
├─────────────────────┤
│ 2. Full pixel decode│  Reads every pixel — catches truncation
├─────────────────────┤
│ 3. Visual check     │  Detects gray/black corrupted regions (optional)
├─────────────────────┤
│ 4. Structure audit  │  JPEG marker chain or PNG chunk validation
├─────────────────────┤
│ 5. Re-encode test   │  Re-encodes to BMP to catch subtle decoder issues
├─────────────────────┤
│ 6. External tools   │  Runs exiftool and ImageMagick if installed
└─────────────────────┘
```

Steps 4-6 only run in `--thorough` mode. For large collections, the basic pipeline (steps 1-2) is usually sufficient and much faster.

### Visual Corruption Detection

2PAC Scan can detect images that *technically* decode without errors but contain visible corruption — large gray or black blocks where real image data should be. This happens with:

- Partially recovered files from damaged storage
- Images from failing memory cards
- Incomplete downloads that happened to have valid headers
- Camera sensor failures

The algorithm samples pixel colors across the image and flags files where a single uniform color dominates an abnormally large area.

### Repair

When `--repair` is enabled, 2PAC Scan attempts to fix corrupt files by:

1. Re-reading the original file
2. Re-saving it in the correct format (JPEG, PNG, or GIF)
3. For JPEG: optimized re-encoding at quality 85
4. Backing up originals to a `--backup-dir` before any modifications

Repair works for files with corrupt internal structure but intact pixel data. It cannot recover from truncation (missing data) or complete header destruction.

### Supported Formats

| Format | Extensions | Detects corruption | Repairable |
|---|---|---|---|
| JPEG | `.jpg .jpeg .jpe .jfif` | Yes — marker chain analysis | Yes |
| PNG | `.png` | Yes — chunk validation | Yes |
| GIF | `.gif` | Yes | Yes |
| TIFF | `.tiff .tif` | Yes | No |
| BMP | `.bmp .dib` | Yes | No |
| WebP | `.webp` | Yes | No |
| HEIC | `.heic` | Yes | No |
| ICO | `.ico` | Yes | No |

---

## Important Things to Know

### Use PNG for steganography

JPEG is a lossy format — it throws away data to compress the image. Every time a JPEG is saved, pixel values change. This **destroys** hidden LSB data. Always use PNG output and never re-save stego images as JPEG.

### Capacity vs. stealth

The `--bits` parameter (1-4) controls how many bits per color channel are used for embedding:

| Bits/channel | Max pixel change | Capacity (1000×1000 image) | Detection risk |
|---|---|---|---|
| 1 | ±1 (invisible) | ~375 KB | Low |
| 2 | ±3 (barely visible on smooth areas) | ~750 KB | Medium |
| 3 | ±7 (visible on gradients) | ~1.1 MB | High |
| 4 | ±15 (noticeable) | ~1.5 MB | Very high |

### Sensitivity is a trade-off

Higher sensitivity catches more subtle embedding but also flags more innocent images. For most purposes, `medium` is the right choice. Use `high` when you're specifically looking for steganography and can tolerate false positives.

### Security model

- All processing happens locally in your browser session or on your machine
- Images are never uploaded to external servers (except when using the Hugging Face Space, where images are processed in the Space's container)
- Temporary files are deleted after each operation
- Passwords and hidden data are never stored or logged
- 2PAC Scan enforces a 100 MB file size limit and path traversal protection to prevent denial-of-service attacks

### Test suite

44 tests across two test files:

- **35 LSB tests** — capacity calculation, embed/extract round-trips, password encryption, Unicode, error handling, edge cases
- **9 DCT tests** — transform precision, capacity, embed/extract (experimental — some round-trip tests are expected to fail due to DCT/IDCT rounding)

```bash
pytest tests/ -v
```

---

## Full CLI Reference

### `2pac_stego.py` — Steganography Tool

```
python 2pac_stego.py hide    --image IMG --data "text" [--output OUT] [--password PWD] [--dct] [--bits N] [--quality N]
python 2pac_stego.py extract --image IMG [--password PWD] [--dct] [--bits N]
python 2pac_stego.py detect  PATH [--sensitivity low|medium|high] [--non-recursive] [--workers N] [--visual-reports] [--reports-dir DIR]
```

### `2pac_scan.py` — Image Corruption Scanner

```
python 2pac_scan.py DIRECTORY [--thorough] [--check-visual] [--sensitivity low|medium|high]
                              [--delete | --move-to DIR] [--repair] [--backup-dir DIR]
                              [--formats JPEG PNG ...] [--workers N]
                              [--output FILE] [--resume SESSION]
                              [--security-checks] [--max-file-size N] [--max-pixels N]

python 2pac_scan.py --check-file FILE [--check-visual] [--thorough]
python 2pac_scan.py --list-sessions
```

---

## Project Structure

```
2pac/
├── app.py                  # Gradio web UI (Hugging Face Space)
├── steg_embedder.py        # LSB steganography engine
├── dct_steg.py             # DCT steganography engine (experimental)
├── rat_finder.py           # Steganography detection — 7 forensic techniques
├── find_bad_images/        # Image corruption scanner package
│   ├── config.py           # Format definitions and settings
│   ├── security.py         # File validation, path traversal prevention
│   ├── validation.py       # Image integrity checks and visual corruption
│   ├── processing.py       # Batch scanning, repair, session management
│   └── cli.py              # Command-line interface
├── find_bad_images.py      # Backward-compatible CLI wrapper
├── 2pac_stego.py           # Unified steganography CLI
├── 2pac_scan.py            # Unified scanner CLI
├── utils.py                # Shared logging, sensitivity mapping, temp files
├── quotes.py               # Themed quotes for scanner output
├── tests/
│   ├── test_steg_embedder.py  # 35 LSB tests
│   └── test_dct_steg.py       # 9 DCT tests
├── requirements.txt
└── README.md
```

---

## About

Created by [Richard Young](https://github.com/ricyoung) | Part of [DeepNeuro.AI](https://deepneuro.ai)

In memory of Jeff Young. *"All Eyez On Your Images"*

---

[GitHub](https://github.com/ricyoung/2pac) | [Hugging Face Space](https://huggingface.co/spaces/richardyoung/2pac) | [DeepNeuro.AI](https://deepneuro.ai)
