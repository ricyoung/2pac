#!/usr/bin/env python3
"""
2PAC: Picture Analyzer & Corruption Killer - Hugging Face Space UI.

Two user-facing tools:
  - Stego Tool: hide, extract, and detect hidden data
  - 2PAC Scan: validate and diagnose image corruption
"""

import os
import tempfile

import gradio as gr
import numpy as np
from PIL import Image, ImageDraw

from dct_steg import DctStegEmbedder
import find_bad_images
import rat_finder
from steg_embedder import StegEmbedder
from utils import slider_to_sensitivity


lsb = StegEmbedder()
dct = DctStegEmbedder()


def _save_numpy_image(image, suffix='.png'):
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        Image.fromarray(image).save(tmp.name, 'PNG')
        return tmp.name


def _cleanup(*paths):
    for path in paths:
        if path and os.path.exists(path):
            os.unlink(path)


def _badge(label, tone):
    colors = {
        'green': '#0f766e',
        'yellow': '#a16207',
        'red': '#b91c1c',
        'blue': '#1d4ed8',
        'purple': '#7e22ce',
    }
    color = colors.get(tone, '#374151')
    return f"<span style='background:{color};color:white;padding:0.25rem 0.55rem;border-radius:999px;font-weight:700'>{label}</span>"


def _format_issues(issues):
    if not issues:
        return "Image failed validation but no specific issue was identified."
    if isinstance(issues, dict):
        return "\n".join(f"- **{key}:** {value}" for key, value in issues.items())
    if isinstance(issues, tuple) and len(issues) == 2:
        return f"- **{issues[0]}:** {issues[1]}"
    return f"- {issues}"


def _file_path(file_obj):
    if file_obj is None:
        return None
    if isinstance(file_obj, str):
        return file_obj
    return getattr(file_obj, 'name', None) or getattr(file_obj, 'path', None)


# Generated samples avoid committing binary assets, which Hugging Face rejects
# unless the repo is configured for Xet/LFS storage.
def sample_clean_image():
    width, height = 320, 220
    x = np.linspace(30, 230, width, dtype=np.uint8)
    y = np.linspace(20, 180, height, dtype=np.uint8)
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:, :, 0] = x[None, :]
    arr[:, :, 1] = y[:, None]
    arr[:, :, 2] = 160
    img = Image.fromarray(arr, 'RGB')
    draw = ImageDraw.Draw(img)
    draw.ellipse((34, 42, 138, 146), outline=(255, 255, 255), width=5)
    draw.rectangle((170, 60, 288, 160), outline=(80, 20, 180), width=5)
    draw.text((34, 178), "2PAC clean sample", fill=(255, 255, 255))
    return np.array(img)


def sample_damaged_image():
    img = Image.fromarray(sample_clean_image(), 'RGB')
    draw = ImageDraw.Draw(img)
    draw.rectangle((190, 32, 300, 95), fill=(128, 128, 128))
    draw.rectangle((0, 165, 320, 220), fill=(18, 18, 18))
    draw.text((18, 18), "visual damage sample", fill=(255, 240, 120))
    return np.array(img)


def sample_lsb_stego_image():
    input_path = output_path = None
    try:
        image = sample_clean_image()
        input_path = _save_numpy_image(image)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            output_path = tmp.name
        ok, _, _ = lsb.embed_data(input_path, "sample secret from 2PAC", output_path, bits_per_channel=1)
        if not ok:
            return image
        return np.array(Image.open(output_path).convert('RGB'))
    finally:
        _cleanup(input_path, output_path)


def hide_lsb(image, secret_text, password, bits_per_channel):
    if image is None:
        return None, "Upload an image first."
    if not secret_text or not secret_text.strip():
        return None, "Enter text to hide."

    input_path = output_path = None
    try:
        input_path = _save_numpy_image(image)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            output_path = tmp.name

        img = Image.open(input_path)
        capacity = lsb.calculate_capacity(img, bits_per_channel)
        data_size = len(secret_text.encode('utf-8'))

        if data_size > capacity:
            return None, (
                f"{_badge('TOO LARGE', 'red')}\n\n"
                f"Payload is **{data_size:,} bytes**, but this image can hold **{capacity:,} bytes**.\n\n"
                "Use a larger image or increase bits/channel."
            )

        pwd = password if password else None
        ok, msg, stats = lsb.embed_data(input_path, secret_text, output_path,
                                        password=pwd, bits_per_channel=bits_per_channel)
        if not ok:
            return None, f"{_badge('ERROR', 'red')}\n\n{msg}"

        result_img = Image.open(output_path).convert('RGB')
        result = (
            f"{_badge('LSB EMBEDDED', 'green')}\n\n"
            f"- **Payload:** {stats['data_size']:,} bytes\n"
            f"- **Encryption:** {'Yes' if stats['encrypted'] else 'No'}\n"
            f"- **Bits/channel:** {stats['bits_per_channel']}\n"
            f"- **Capacity used:** {stats['utilization']}\n\n"
            "Download the output image and keep it as PNG."
        )
        return result_img, result
    except Exception as e:
        return None, f"{_badge('ERROR', 'red')}\n\n{str(e)}"
    finally:
        _cleanup(input_path, output_path)


def hide_dct(image, secret_text, password):
    if image is None:
        return None, "Upload an image first."
    if not secret_text or not secret_text.strip():
        return None, "Enter text to hide."

    input_path = output_path = None
    try:
        input_path = _save_numpy_image(image)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            output_path = tmp.name

        pwd = password if password else None
        ok, msg, stats = dct.embed_data(input_path, secret_text, output_path, password=pwd)
        if not ok:
            return None, f"{_badge('DCT ERROR', 'red')}\n\n{msg}"

        result_img = Image.open(output_path).convert('RGB')
        result = (
            f"{_badge('DCT EXPERIMENTAL', 'purple')}\n\n"
            "DCT embeds in frequency coefficients and is harder for LSB analysis to see, "
            "but extraction reliability is still under active development. Use LSB for critical data.\n\n"
            f"- **Payload:** {stats['data_size']:,} bytes\n"
            f"- **Encryption:** {'Yes' if stats['encrypted'] else 'No'}\n"
            f"- **Blocks used:** {stats['blocks_used']}/{stats['total_blocks']}\n"
        )
        return result_img, result
    except Exception as e:
        return None, f"{_badge('ERROR', 'red')}\n\n{str(e)}"
    finally:
        _cleanup(input_path, output_path)


def extract_data(image, password, bits_per_channel, method):
    if image is None:
        return "Upload an image first."

    image_path = None
    try:
        image_path = _save_numpy_image(image)
        pwd = password if password else None

        if method == 'LSB':
            ok, msg, data = lsb.extract_data(image_path, password=pwd,
                                             bits_per_channel=bits_per_channel)
        else:
            ok, msg, data = dct.extract_data(image_path, password=pwd)

        if not ok:
            return (
                f"{_badge('NOT EXTRACTED', 'yellow')}\n\n"
                f"{msg}\n\n"
                "Check method, password, bits/channel, and whether the image was re-saved."
            )

        return f"{_badge('EXTRACTED', 'green')}\n\n```text\n{data}\n```"
    except Exception as e:
        return f"{_badge('ERROR', 'red')}\n\n{str(e)}"
    finally:
        _cleanup(image_path)


def detect_stego(image, sensitivity):
    if image is None:
        return None, "Upload an image to analyze."

    image_path = None
    try:
        image_path = _save_numpy_image(image)
        sens = slider_to_sensitivity(sensitivity)
        is_suspicious, confidence, details = rat_finder.analyze_image(image_path, sensitivity=sens)
        ela_suspicious, ela_conf, ela_details = rat_finder.perform_ela_analysis(image_path)

        if confidence >= 70:
            badge = _badge('HIGH SUSPICION', 'red')
        elif confidence >= 40:
            badge = _badge('MODERATE SUSPICION', 'yellow')
        else:
            badge = _badge('LOW SUSPICION', 'green')

        lines = [f"{badge}\n", f"**Confidence:** {confidence:.1f}%", "", "**Signals:**"]
        for key, result in details.items():
            if isinstance(result, dict):
                susp = result.get('suspicious', False)
                conf = result.get('confidence', 0)
                det = result.get('details', '')
                status = "suspicious" if susp else "clean"
                lines.append(f"- **{key}:** {conf:.0f}% — {status} — {det}")
            else:
                lines.append(f"- **{key}:** {result}")
        lines.extend([
            "",
            "**Interpretation:** RAT Finder answers: *Does this image look like it contain hidden data?*",
            "A high score means forensic anomalies exist; it is not proof of a secret message."
        ])

        ela_img = None
        if isinstance(ela_details, dict) and 'diff_image' in ela_details:
            ela_img = ela_details['diff_image']
        return ela_img, '\n'.join(lines)
    except Exception as e:
        return None, f"{_badge('ERROR', 'red')}\n\n{str(e)}"
    finally:
        _cleanup(image_path)


def validate_image(image, sensitivity, check_visual):
    if image is None:
        return "Upload an image to check."

    image_path = None
    try:
        image_path = _save_numpy_image(image)
        sens = slider_to_sensitivity(sensitivity)
        valid = find_bad_images.is_valid_image(image_path, thorough=True,
                                               sensitivity=sens,
                                               check_visual=check_visual)
        issues = find_bad_images.diagnose_image_issue(image_path)

        if valid:
            return (
                f"{_badge('VALID IMAGE', 'green')}\n\n"
                "The image passed structure, decode, metadata, and selected visual checks.\n\n"
                "**Recommendation:** Safe to use."
            )

        return (
            f"{_badge('ISSUES DETECTED', 'red')}\n\n"
            f"{_format_issues(issues)}\n\n"
            "**Recommendation:** Re-download from source or use repair tooling if this is an important archive image."
        )
    except Exception as e:
        return f"{_badge('ERROR', 'red')}\n\n{str(e)}"
    finally:
        _cleanup(image_path)


def batch_validate(files, sensitivity, check_visual):
    if not files:
        return [], "Upload one or more image files."

    rows = []
    sens = slider_to_sensitivity(sensitivity)
    for file_obj in files:
        path = _file_path(file_obj)
        name = os.path.basename(path) if path else "unknown"
        try:
            valid = find_bad_images.is_valid_image(path, thorough=True,
                                                   sensitivity=sens,
                                                   check_visual=check_visual)
            issues = find_bad_images.diagnose_image_issue(path)
            if valid:
                rows.append([name, "Valid", "None", "Safe to use"])
            else:
                issue_text = _format_issues(issues).replace('\n', ' ')
                rows.append([name, "Issues detected", issue_text, "Re-download or repair"])
        except Exception as e:
            rows.append([name, "Error", str(e), "Check file format"])

    summary = f"Checked **{len(rows)}** file(s)."
    return rows, summary


HEADER = """
# 2PAC: Picture Analyzer & Corruption Killer

Hide messages inside images. Detect hidden data. Find and repair corrupt files.
"""


def _build_stego_cmd(subcommand, image_path, data, output, password, dct, bits, sensitivity, non_recursive, workers, visual_reports, reports_dir):
    parts = ["python 2pac_stego.py", subcommand]
    if subcommand == "hide":
        if image_path:
            parts.append(f"--image {image_path}")
        if data:
            parts.append(f'--data "{data}"')
        if output:
            parts.append(f"--output {output}")
        if password:
            parts.append(f"--password ****")
        if dct:
            parts.append("--dct")
        if bits and not dct:
            parts.append(f"--bits {bits}")
    elif subcommand == "extract":
        if image_path:
            parts.append(f"--image {image_path}")
        if password:
            parts.append(f"--password ****")
        if dct:
            parts.append("--dct")
        if bits and not dct:
            parts.append(f"--bits {bits}")
    elif subcommand == "detect":
        if image_path:
            parts.append(image_path)
        if sensitivity != "medium":
            parts.append(f"--sensitivity {sensitivity}")
        if non_recursive:
            parts.append("--non-recursive")
        if workers and workers != 1:
            parts.append(f"--workers {workers}")
        if visual_reports:
            parts.append("--visual-reports")
        if reports_dir:
            parts.append(f"--reports-dir {reports_dir}")
    return " \\\n  ".join(parts) if len(parts) > 3 else " ".join(parts)


def _build_scan_cmd(directory, action, move_to, check_file, thorough, check_visual, sensitivity,
                    repair, backup_dir, formats, workers, delete, resume):
    if check_file:
        parts = ["python 2pac_scan.py", f"--check-file {check_file}"]
    else:
        parts = ["python 2pac_scan.py", directory or "./images"]
    if action == "move" and move_to:
        parts.append(f"--move-to {move_to}")
    elif action == "delete":
        parts.append("--delete")
    if thorough:
        parts.append("--thorough")
    if check_visual:
        parts.append("--check-visual")
    if sensitivity != "medium":
        parts.append(f"--sensitivity {sensitivity}")
    if repair:
        parts.append("--repair")
    if backup_dir:
        parts.append(f"--backup-dir {backup_dir}")
    if formats:
        parts.append(f"--formats {' '.join(formats)}")
    if workers and workers != 1:
        parts.append(f"--workers {workers}")
    if resume:
        parts.append(f"--resume {resume}")
    return " \\\n  ".join(parts) if len(parts) > 3 else " ".join(parts)


INTRO_SECTION = """
### Images can hide secrets — and they can also break.

Every digital image is just a grid of numbers. 2PAC gives you two independent tools to work with those numbers:

**Stego Tool** — Hide text inside an image so no one else can see it, extract hidden text, or run forensic analysis to detect whether an image has been tampered with.

**2PAC Scan** — Check whether image files are structurally intact, detect corrupted or truncated files, and attempt repairs.

These are different problems. A perfectly valid image can contain a hidden message, and a corrupt image might not contain anything at all. Pick the tool that matches your question.
"""


TOOL_COMPARISON = """
### Which tool do I need?

| | **Stego Tool** | **2PAC Scan** |
|---|---|---|
| **Your question** | *"Is there a hidden message in this image?"* | *"Is this image file broken?"* |
| **What it finds** | LSB patterns, frequency anomalies, histogram irregularities, stego tool signatures in metadata | Truncated files, bad headers, decoder errors, gray/black corrupted regions |
| **What it can do** | Hide text, extract it, or just detect signs of steganography | Validate integrity, diagnose problems, attempt repair |
| **Formats** | PNG only (JPEG destroys hidden data) | JPEG, PNG, GIF, TIFF, BMP, WebP, HEIC, ICO |
| **Best for** | Security research, CTF challenges, privacy | Photo archives, downloaded collections, data recovery |
"""


HOW_STEGO_WORKS = """
### How does image steganography work?

Every pixel in a digital image is stored as numbers — three channels (red, green, blue), each 0–255. That's 8 binary bits per channel.

LSB steganography changes only the **last bit** — the least significant bit. The visual change is invisible:

```
Original pixel:   R=156   G=89    B=201
Binary:           10011100 01011001 11001001
                                            ^--- this bit stores your secret
Modified pixel:   R=156   G=88    B=201     (89→88, undetectable to the eye)
```

A 1000×1000 image can hide roughly **375 KB** of text this way. Add a password and the data is XOR-encrypted before embedding.

2PAC also offers **DCT mode** (experimental) which hides data in the frequency domain instead of pixel values — harder to detect but with much lower capacity.
"""


HOW_DETECTION_WORKS = """
### How does steganography detection work?

RAT Finder runs **seven forensic techniques** and combines them into a confidence score:

- **LSB Chi-Squared** — Natural images have structured least-significant bits. Steganography makes them uniformly random. A statistical test catches this.
- **Histogram Analysis** — Systematic LSB modification creates a distinctive "comb pattern" in color histograms where even and odd values become suspiciously similar.
- **Error Level Analysis** — Re-saves the image and measures pixel differences. Edited or modified regions show different error levels.
- **Visual Noise** — Compares noise levels across color channels. Steganography that embeds more data in one channel creates a detectable imbalance.
- **Metadata Inspection** — Scans EXIF data for known steganography tool signatures (OutGuess, StegHide, JSteg, F5, etc.).
- **File Size Anomalies** — Compares file size against expected ranges for the image dimensions. Embedded payloads bloat files.
- **Trailing Data** — Checks for data appended after the file's official end-of-file marker.

A confidence score ≥ 70% means HIGH SUSPICION. The tool answers *"does this image show forensic signs of hidden data?"* — it does not prove a message exists.
"""


HOW_SCAN_WORKS = """
### How does image validation work?

2PAC Scan runs images through a multi-step pipeline:

1. **Header check** — Quick structural validation
2. **Full pixel decode** — Reads every pixel to catch truncation
3. **Visual corruption** *(optional)* — Detects gray/black blocks from damaged storage or incomplete writes
4. **Structure audit** — JPEG marker chain or PNG chunk validation
5. **Re-encode test** — Catches subtle decoder errors
6. **External tools** — Runs `exiftool` and ImageMagick if available

Steps 4–6 only run in thorough mode. For large collections, the basic pipeline is fast and usually sufficient.

When repair is enabled, 2PAC re-saves the image in the correct format (JPEG, PNG, GIF). It works when pixel data is intact but internal structure is broken.
"""


QUICK_START_GUIDE = """
### Quick start

1. Go to **Stego Tool → Hide** and upload an image, type a message, and click Embed
2. Go to **Stego Tool → Extract** and upload the output image to recover your text
3. Go to **Stego Tool → Detect** and upload any image to run RAT Finder's forensic analysis
4. Go to **2PAC Scan** and upload images to check for corruption

Or use the CLI for automation, large folders, and repair workflows:
"""


CLI_REFERENCE = """
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
"""


with gr.Blocks(title="2PAC") as demo:
    gr.Markdown(HEADER)

    with gr.Tabs():
        with gr.Tab("Start Here"):
            gr.Markdown(INTRO_SECTION)
            gr.Markdown(TOOL_COMPARISON)
            with gr.Row():
                with gr.Column():
                    gr.Markdown(
                        "### Stego Tool\n"
                        "Use this when your question is: **Is there hidden data?**\n\n"
                        "- Hide messages with LSB or experimental DCT\n"
                        "- Extract messages created by 2PAC\n"
                        "- Run RAT Finder forensic detection"
                    )
                with gr.Column():
                    gr.Markdown(
                        "### 2PAC Scan\n"
                        "Use this when your question is: **Is this image damaged?**\n\n"
                        "- Validate JPEG/PNG/GIF/TIFF/BMP/WebP\n"
                        "- Detect truncation, bad headers, and visual damage\n"
                        "- Use CLI repair mode for recoverable files"
                    )
            gr.Markdown(HOW_STEGO_WORKS)
            gr.Markdown(HOW_DETECTION_WORKS)
            gr.Markdown(HOW_SCAN_WORKS)
            gr.Markdown(QUICK_START_GUIDE)
            gr.Markdown(CLI_REFERENCE)

        with gr.Tab("Stego Tool"):
            with gr.Tabs():
                with gr.Tab("Hide"):
                    method = gr.Radio(['LSB - stable, high capacity', 'DCT - experimental, lower capacity'],
                                      value='LSB - stable, high capacity', label="Method")
                    with gr.Row():
                        with gr.Column(scale=1):
                            hide_in = gr.Image(label="Source image", type="numpy", height=300, format="png")
                            with gr.Row():
                                gr.Button("Load clean sample").click(fn=sample_clean_image, outputs=[hide_in])
                                gr.Button("Load visual-damage sample").click(fn=sample_damaged_image, outputs=[hide_in])
                            hide_text = gr.Textbox(label="Text to hide", lines=5, placeholder="Type your secret message")
                            hide_pass = gr.Textbox(label="Password", type="password", placeholder="optional")
                            hide_bits = gr.Slider(1, 4, value=1, step=1, label="Bits/channel (LSB only)")
                            hide_btn = gr.Button("Embed", variant="primary")
                        with gr.Column(scale=1):
                            hide_out_img = gr.Image(label="Output image (download as PNG)", height=300, format="png")
                            hide_out_text = gr.Markdown()

                    def _hide_router(method_name, image, text, password, bits):
                        if method_name.startswith('DCT'):
                            return hide_dct(image, text, password)
                        return hide_lsb(image, text, password, bits)

                    hide_btn.click(fn=_hide_router,
                                   inputs=[method, hide_in, hide_text, hide_pass, hide_bits],
                                   outputs=[hide_out_img, hide_out_text])
                    gr.Markdown("**Important:** keep stego output as PNG. JPEG recompression destroys hidden data.")

                with gr.Tab("Extract"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            ext_in = gr.Image(label="Image with hidden data", type="numpy", height=300, format="png")
                            gr.Button("Load LSB stego sample").click(fn=sample_lsb_stego_image, outputs=[ext_in])
                            ext_method = gr.Radio(['LSB', 'DCT'], value='LSB', label="Method")
                            ext_pass = gr.Textbox(label="Password", type="password", placeholder="if encrypted")
                            ext_bits = gr.Slider(1, 4, value=1, step=1, label="Bits/channel (LSB only)")
                            ext_btn = gr.Button("Extract", variant="primary")
                        with gr.Column(scale=1):
                            ext_out = gr.Markdown()
                    ext_btn.click(fn=extract_data, inputs=[ext_in, ext_pass, ext_bits, ext_method], outputs=[ext_out])

                with gr.Tab("Detect Hidden Data"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            det_in = gr.Image(label="Image to analyze", type="numpy", height=300, format="png")
                            with gr.Row():
                                gr.Button("Load clean sample").click(fn=sample_clean_image, outputs=[det_in])
                                gr.Button("Load LSB stego sample").click(fn=sample_lsb_stego_image, outputs=[det_in])
                            det_sens = gr.Slider(1, 10, value=5, step=1, label="Sensitivity")
                            det_btn = gr.Button("Run RAT Finder", variant="primary")
                        with gr.Column(scale=1):
                            det_img = gr.Image(label="ELA visualization", height=300, format="png")
                            det_out = gr.Markdown()
                    det_btn.click(fn=detect_stego, inputs=[det_in, det_sens], outputs=[det_img, det_out])

        with gr.Tab("2PAC Scan"):
            with gr.Tabs():
                with gr.Tab("Single Image Check"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            val_in = gr.Image(label="Image to validate", type="numpy", height=300, format="png")
                            with gr.Row():
                                gr.Button("Load clean sample").click(fn=sample_clean_image, outputs=[val_in])
                                gr.Button("Load damaged sample").click(fn=sample_damaged_image, outputs=[val_in])
                            val_sens = gr.Slider(1, 10, value=5, step=1, label="Validation sensitivity")
                            val_vis = gr.Checkbox(value=True, label="Visual corruption check")
                            val_btn = gr.Button("Check Integrity", variant="primary")
                        with gr.Column(scale=1):
                            val_out = gr.Markdown()
                    val_btn.click(fn=validate_image, inputs=[val_in, val_sens, val_vis], outputs=[val_out])

                with gr.Tab("Batch Check"):
                    gr.Markdown("Upload multiple files to check archive health. The CLI has full move/delete/repair modes.")
                    batch_files = gr.File(label="Upload images", file_count="multiple", type="filepath")
                    with gr.Row():
                        batch_sens = gr.Slider(1, 10, value=5, step=1, label="Validation sensitivity")
                        batch_vis = gr.Checkbox(value=False, label="Visual corruption check")
                    batch_btn = gr.Button("Check Batch", variant="primary")
                    batch_table = gr.Dataframe(headers=["File", "Status", "Issue", "Recommendation"], datatype=["str", "str", "str", "str"])
                    batch_summary = gr.Markdown()
                    batch_btn.click(fn=batch_validate,
                                    inputs=[batch_files, batch_sens, batch_vis],
                                    outputs=[batch_table, batch_summary])

                with gr.Tab("Repair Guidance"):
                    gr.Markdown(
                        "The web Space validates and diagnoses. For actual repair/move/delete workflows, use the CLI:\n\n"
                        "```bash\n"
                        "python 2pac_scan.py ./images --repair --backup-dir ./backups\n"
                        "python 2pac_scan.py ./images --move-to ./bad --check-visual\n"
                        "python 2pac_scan.py ./images --delete --security-checks\n"
                        "```"
                    )

        with gr.Tab("CLI Builder"):
            gr.Markdown(
                "## Command-Line Builder\n\n"
                "Build the command you need, then copy and paste it into your terminal. "
                "[Install 2PAC](https://github.com/ricyoung/2pac) locally to use the CLI."
            )

            with gr.Tabs():
                with gr.Tab("Stego Tool"):
                    stego_sub = gr.Radio(["hide", "extract", "detect"], value="hide", label="Subcommand")
                    with gr.Row():
                        with gr.Column():
                            stego_image = gr.Textbox(label="Image path", placeholder="photo.png")
                            stego_data = gr.Textbox(label="Text to hide", placeholder="secret message", visible=True)
                            stego_output = gr.Textbox(label="Output path", placeholder="out.png")
                            stego_password = gr.Textbox(label="Password", type="password", placeholder="optional")
                        with gr.Column():
                            stego_dct = gr.Checkbox(label="Use DCT mode")
                            stego_bits = gr.Dropdown([1, 2, 3, 4], value=1, label="Bits/channel (LSB only)")
                            stego_sens = gr.Dropdown(["low", "medium", "high"], value="medium", label="Sensitivity (detect only)")
                            stego_workers = gr.Slider(1, 16, value=1, step=1, label="Workers (detect only)")
                            stego_reports = gr.Checkbox(label="Visual reports (detect only)")
                    stego_cmd_out = gr.Code(label="Generated command", language="shell", interactive=False)
                    stego_sub.change(fn=_build_stego_cmd,
                                     inputs=[stego_sub, stego_image, stego_data, stego_output,
                                             stego_password, stego_dct, stego_bits,
                                             stego_sens, gr.State(False), stego_workers,
                                             stego_reports, gr.State("")],
                                     outputs=[stego_cmd_out])
                    for component in [stego_image, stego_data, stego_output, stego_password,
                                      stego_dct, stego_bits, stego_sens, stego_workers, stego_reports]:
                        component.change(fn=_build_stego_cmd,
                                         inputs=[stego_sub, stego_image, stego_data, stego_output,
                                                 stego_password, stego_dct, stego_bits,
                                                 stego_sens, gr.State(False), stego_workers,
                                                 stego_reports, gr.State("")],
                                         outputs=[stego_cmd_out])

                with gr.Tab("2PAC Scan"):
                    with gr.Row():
                        with gr.Column():
                            scan_dir = gr.Textbox(label="Directory to scan", placeholder="./images", value="./images")
                            scan_check_file = gr.Textbox(label="Or check single file", placeholder="leave blank for directory scan")
                            scan_action = gr.Radio(["dry run (report only)", "move", "delete"], value="dry run (report only)", label="Action")
                            scan_move_to = gr.Textbox(label="Move-to directory", placeholder="./quarantine", visible=False)
                        with gr.Column():
                            scan_thorough = gr.Checkbox(label="Thorough mode", value=True)
                            scan_visual = gr.Checkbox(label="Visual corruption check")
                            scan_sens = gr.Dropdown(["low", "medium", "high"], value="medium", label="Sensitivity")
                            scan_repair = gr.Checkbox(label="Attempt repair")
                            scan_backup = gr.Textbox(label="Backup directory", placeholder="./backups")
                    with gr.Row():
                        scan_fmts = gr.CheckboxGroup(["JPEG", "PNG", "GIF", "TIFF", "BMP", "WEBP"], label="Formats")
                        scan_workers = gr.Slider(1, 16, value=1, step=1, label="Workers")
                    scan_cmd_out = gr.Code(label="Generated command", language="shell", interactive=False)
                    for component in [scan_dir, scan_check_file, scan_action, scan_move_to,
                                      scan_thorough, scan_visual, scan_sens, scan_repair,
                                      scan_backup, scan_fmts, scan_workers]:
                        component.change(fn=_build_scan_cmd,
                                         inputs=[scan_dir, scan_action, scan_move_to, scan_check_file,
                                                 scan_thorough, scan_visual, scan_sens,
                                                 scan_repair, scan_backup, scan_fmts, scan_workers,
                                                 gr.State(False), gr.State("")],
                                         outputs=[scan_cmd_out])

    gr.Markdown("---\n[GitHub](https://github.com/ricyoung/2pac) | [DeepNeuro.AI](https://deepneuro.ai) | All Eyez On Your Images")


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(primary_hue="violet", secondary_hue="blue"))
