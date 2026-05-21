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
        confidence, details = rat_finder.analyze_image(image_path, sensitivity=sens)
        ela = rat_finder.perform_ela_analysis(image_path)

        if confidence >= 70:
            badge = _badge('HIGH SUSPICION', 'red')
        elif confidence >= 40:
            badge = _badge('MODERATE SUSPICION', 'yellow')
        else:
            badge = _badge('LOW SUSPICION', 'green')

        lines = [f"{badge}\n", f"**Confidence:** {confidence:.1f}%", "", "**Signals:**"]
        lines.extend(f"- {detail}" for detail in details)
        lines.extend([
            "",
            "**Interpretation:** RAT Finder answers: *Does this image look like it contains hidden data?*",
            "A high score means forensic anomalies exist; it is not proof of a secret message."
        ])

        ela_img = ela['ela_image'] if ela['success'] else None
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

2PAC has **two jobs**: the **Stego Tool** hides or detects secret data, and **2PAC Scan** checks whether image files are damaged.
"""


DIFFERENCE_TABLE = """
| | RAT Finder (`2pac_stego.py detect`) | 2PAC Scan (`2pac_scan.py`) |
|---|---|---|
| **What** | Detects steganography: hidden messages in images | Detects corruption: broken/damaged image files |
| **Looks for** | LSB patterns, ELA artifacts, histogram anomalies | Truncated files, bad headers, visual damage, decoder errors |
| **Use case** | "Does this image contain a secret message?" | "Is this image file corrupted or safe to use?" |
| **Repair** | No | Yes, for JPEG/PNG/GIF in CLI mode |
| **Output** | Confidence score + forensic details | Bad file list + repair/move/delete options |
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


with gr.Blocks(title="2PAC", theme=gr.themes.Soft(primary_hue="violet", secondary_hue="blue")) as demo:
    gr.Markdown(HEADER)

    with gr.Tabs():
        with gr.Tab("Start Here"):
            gr.Markdown("## Choose the right tool")
            gr.Markdown(DIFFERENCE_TABLE)
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
            gr.Markdown("## CLI equivalents")
            gr.Markdown(CLI_REFERENCE)

        with gr.Tab("Stego Tool"):
            with gr.Tabs():
                with gr.Tab("Hide"):
                    method = gr.Radio(['LSB - stable, high capacity', 'DCT - experimental, lower capacity'],
                                      value='LSB - stable, high capacity', label="Method")
                    with gr.Row():
                        with gr.Column(scale=1):
                            hide_in = gr.Image(label="Source image", type="numpy", height=300)
                            with gr.Row():
                                gr.Button("Load clean sample").click(fn=sample_clean_image, outputs=[hide_in])
                                gr.Button("Load visual-damage sample").click(fn=sample_damaged_image, outputs=[hide_in])
                            hide_text = gr.Textbox(label="Text to hide", lines=5, placeholder="Type your secret message")
                            hide_pass = gr.Textbox(label="Password", type="password", placeholder="optional")
                            hide_bits = gr.Slider(1, 4, value=1, step=1, label="Bits/channel (LSB only)")
                            hide_btn = gr.Button("Embed", variant="primary")
                        with gr.Column(scale=1):
                            hide_out_img = gr.Image(label="Output image", height=300)
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
                            ext_in = gr.Image(label="Image with hidden data", type="numpy", height=300)
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
                            det_in = gr.Image(label="Image to analyze", type="numpy", height=300)
                            with gr.Row():
                                gr.Button("Load clean sample").click(fn=sample_clean_image, outputs=[det_in])
                                gr.Button("Load LSB stego sample").click(fn=sample_lsb_stego_image, outputs=[det_in])
                            det_sens = gr.Slider(1, 10, value=5, step=1, label="Sensitivity")
                            det_btn = gr.Button("Run RAT Finder", variant="primary")
                        with gr.Column(scale=1):
                            det_img = gr.Image(label="ELA visualization", height=300)
                            det_out = gr.Markdown()
                    det_btn.click(fn=detect_stego, inputs=[det_in, det_sens], outputs=[det_img, det_out])

        with gr.Tab("2PAC Scan"):
            with gr.Tabs():
                with gr.Tab("Single Image Check"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            val_in = gr.Image(label="Image to validate", type="numpy", height=300)
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

        with gr.Tab("CLI"):
            gr.Markdown("## Local command-line usage")
            gr.Markdown(CLI_REFERENCE)
            gr.Markdown(
                "The web app is for interactive use. The CLI is better for large folders, repair actions, resuming scans, and automation."
            )

    gr.Markdown("---\n[GitHub](https://github.com/ricyoung/2pac) | DeepNeuro.AI | All Eyez On Your Images")


if __name__ == "__main__":
    demo.launch()
