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

## What You Can Do

### 2PAC (Put Data In)

- Hide text using **LSB steganography** — stable, high capacity, visually imperceptible
- Try **DCT steganography** — frequency-domain, harder to detect, experimental
- **Password-protect** your hidden data
- **Extract** messages from images created by 2PAC
- Load generated demo images directly in the UI

### RAT Finder (Find Problems)

- **Detect steganography** — 7 forensic techniques analyze images for hidden data
- **Check image integrity** — validate JPEG, PNG, GIF, TIFF, BMP, WebP files
- **Batch validate** — upload multiple files and get a status table
- Find corrupt, truncated, and visually damaged images

## Local CLI

```bash
# 2PAC: hide and extract data
python 2pac.py hide --image photo.png --data "secret" --output out.png
python 2pac.py extract --image out.png

# RAT Finder: detect problems
python ratfinder.py detect suspicious.png --sensitivity high
python ratfinder.py check broken.jpg --check-visual
python ratfinder.py scan ./photos --thorough --repair
```

## Notes

- Keep stego output as **PNG**. JPEG recompression destroys hidden data.
- RAT Finder confidence is not proof of a secret message — it means forensic anomalies exist.
- Processing happens in the active session; temporary files are deleted after use.

Created by [Richard Young](https://github.com/ricyoung) | [DeepNeuro.AI](https://deepneuro.ai)

*In memory of Jeff Young. All Eyez On Your Images.*
