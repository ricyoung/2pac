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

**Two image-security tools in one Space:**

| Tool | Question it answers |
|---|---|
| **Stego Tool** | Does this image hide a secret message? Can I hide or extract one? |
| **2PAC Scan** | Is this image damaged, truncated, corrupt, or visually broken? |

The web app is organized around those two jobs so RAT Finder and 2PAC Scan are not confused.

## What You Can Do In The Space

### Stego Tool

- Hide text using **LSB steganography**: stable, high capacity, best for reliable extraction
- Try **DCT steganography**: frequency-domain, harder to detect, experimental extraction reliability
- Extract messages created by 2PAC
- Run **RAT Finder** to detect signs of hidden data
- Load generated demo images directly in the UI, with no binary files stored in the repo

### 2PAC Scan

- Validate one image for corruption, bad headers, truncation, and visual damage
- Batch-check multiple uploads and return a status table
- See CLI repair guidance for local repair/move/delete workflows

## RAT Finder vs 2PAC Scan

| | RAT Finder (`2pac_stego.py detect`) | 2PAC Scan (`2pac_scan.py`) |
|---|---|---|
| **What** | Detects steganography: hidden messages in images | Detects corruption: broken/damaged image files |
| **Looks for** | Suspicious LSB patterns, ELA artifacts, histogram anomalies | Truncated files, bad JPEG/PNG headers, visual damage, decoder errors |
| **Use case** | "Does this image contain a secret message?" | "Is this image file corrupted or safe to use?" |
| **Repair** | No | Yes, for JPEG/PNG/GIF in CLI mode |
| **Output** | Confidence score + forensic details | Bad file list + repair results + move/delete actions |

## Local CLI

```bash
# Stego Tool
python 2pac_stego.py hide --image photo.png --data "secret" --output out.png
python 2pac_stego.py extract --image out.png
python 2pac_stego.py detect suspicious.png --sensitivity high

# 2PAC Scan
python 2pac_scan.py ./images --thorough
python 2pac_scan.py --check-file broken.jpg --check-visual
python 2pac_scan.py ./images --move-to ./bad --repair
```

## Notes

- Keep stego output as **PNG**. JPEG recompression destroys hidden data.
- RAT Finder confidence is not proof of a secret message. It means forensic anomalies exist.
- The Space diagnoses images. Full repair workflows are available through the CLI.
- Processing happens in the active Space session; temporary files are deleted after use.

Created by [Richard Young](https://github.com/ricyoung) | DeepNeuro.AI

In memory of Jeff Young. *All Eyez On Your Images.*
