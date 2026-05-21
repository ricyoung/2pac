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

What does 375 KB of text look like?

| Reference | Approximate size |
|---|---|
| A single text message | ~100 bytes |
| A typical email | ~2–5 KB |
| The US Constitution | ~46 KB |
| A 20-page research paper | ~150 KB |
| A full novel (~60,000 words) | ~360 KB |
| **1 megapixel image at 1 bit/channel** | **~375 KB** |

So a single 1000×1000 photo can hide roughly a full novel's worth of text. A 4K phone photo (4000×3000) can hide ~4.5 MB — about twelve novels.

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

## Future Directions

### Advanced Steganography Methods

2PAC currently implements LSB and DCT embedding. Several more sophisticated approaches exist that could be added:

| Method | How it works | Advantage |
|---|---|---|
| **Adaptive steganography** | Embeds more data in noisy/complex regions (edges, textures) and less in smooth areas (sky, walls). Uses visual saliency models to decide where to hide bits. | Much harder to detect — changes are concentrated where the human eye and statistical tests expect variation. |
| **Matrix embedding (F5-style)** | Uses Hamming codes to minimize the number of pixel changes needed for a given payload. Instead of flipping one bit per data bit, it finds the optimal set of changes. | Fewer modifications means less statistical evidence for detectors. Can embed the same data with ~30% fewer changes. |
| **Spread spectrum** | Spreads the hidden signal across the entire image using a pseudo-random noise sequence keyed to a password. The signal is below the noise floor of the image. | Extremely resistant to detection and partially survives lossy compression, cropping, and resizing. Used in digital watermarking. |
| **Palette-based (GIF/PNG-8)** | For indexed-color images, reorders the color palette or modifies palette entries. The pixel indices don't change — only the color table does. | Works on formats that LSB can't touch. Invisible because the displayed image is identical. |
| **Wavelet-domain embedding** | Operates on wavelet coefficients instead of DCT blocks. Wavelet transforms capture both frequency and spatial information simultaneously. | Better capacity than DCT with similar detectability. Used in JPEG 2000 and some watermarking standards. |
| **Deep learning steganography** | Neural networks trained as encoder/decoder pairs. The encoder learns to produce stego images that are visually and statistically indistinguishable from clean images. | Potentially resistant to all known statistical detectors because the network learns to evade them during training. Still an active research area. |
| **Generative steganography** | Instead of modifying an existing image, generates an entirely new image that contains the hidden data. The image never existed before — there's no "original" to compare against. | Eliminates the embedding-detection arms race entirely. Forensic tools that look for modifications find nothing because the image was born with the data inside it. |

### Detection Improvements

- **Deep learning detectors** — Train CNNs on pairs of clean/stego images to catch embedding that evades statistical tests
- **Calibration-based analysis** — Compare the image against a recalibrated version to detect subtle manipulation
- **Compression-resilient detection** — Methods that still detect steganography even after the image has been re-compressed or resized

### Image Validation Improvements

- **HEIC/AVIF support** — Add repair capability for modern formats
- **AI-based visual corruption** — Detect subtle artifacts (banding, color shifts, compression damage) that pixel-threshold checks miss
- **Archive health monitoring** — Periodic scanning with diff reports to catch bit rot early

---

## About

Created by [Richard Young](https://github.com/ricyoung) | [DeepNeuro.AI](https://deepneuro.ai)

*In memory of Jeff Young. All Eyez On Your Images.*

---

[GitHub](https://github.com/ricyoung/2pac) | [Hugging Face Space](https://huggingface.co/spaces/richardyoung/2pac) | [DeepNeuro.AI](https://deepneuro.ai)
