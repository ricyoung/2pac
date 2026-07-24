#!/usr/bin/env python3
"""
2PAC + RAT Finder - Hugging Face Space UI.

Two tools:
  - 2PAC: hide and extract secret data in images
  - RAT Finder: detect steganography, find corrupt images
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


def _gauge(confidence):
    if confidence >= 70:
        color = '#dc2626'
        label = 'HIGH'
    elif confidence >= 40:
        color = '#d97706'
        label = 'MODERATE'
    else:
        color = '#059669'
        label = 'LOW'
    pct = min(confidence, 100)
    bar_bg = '#1f2937'
    return (
        f"<div style='margin:8px 0'>"
        f"<div style='background:{bar_bg};border-radius:8px;overflow:hidden;height:28px;position:relative'>"
        f"<div style='background:{color};height:100%;width:{pct}%;transition:width 0.5s;border-radius:8px'></div>"
        f"<span style='position:absolute;top:3px;left:12px;color:white;font-weight:700;font-size:14px'>"
        f"{label} - {confidence:.1f}%</span></div></div>"
    )


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


def sample_clean_image():
    width, height = 320, 240
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    sky = np.linspace(135, 200, width, dtype=np.uint8)
    arr[:140, :, 0] = sky[None, :] - 40
    arr[:140, :, 1] = sky[None, :] - 10
    arr[:140, :, 2] = sky[None, :] + 30
    arr[140:, :, 0] = 34
    arr[140:, :, 1] = 120
    arr[140:, :, 2] = 50
    arr[140:160, :, 0] = 80
    arr[140:160, :, 1] = 160
    arr[140:160, :, 2] = 70
    img = Image.fromarray(arr, 'RGB')
    draw = ImageDraw.Draw(img)
    draw.ellipse((220, 20, 280, 80), fill=(255, 220, 80))
    draw.polygon([(40, 140), (60, 100), (80, 140)], fill=(20, 60, 20))
    draw.polygon([(100, 140), (115, 110), (130, 140)], fill=(30, 70, 25))
    draw.polygon([(200, 140), (225, 90), (250, 140)], fill=(25, 55, 20))
    draw.rectangle((50, 160, 120, 200), fill=(180, 150, 100))
    draw.polygon([(45, 160), (85, 130), (125, 160)], fill=(140, 50, 40))
    draw.rectangle((75, 175, 95, 200), fill=(100, 70, 40))
    draw.text((10, 210), "2PAC sample - clean image", fill=(255, 255, 255))
    return np.array(img)


def sample_damaged_image():
    img = Image.fromarray(sample_clean_image(), 'RGB')
    draw = ImageDraw.Draw(img)
    draw.rectangle((130, 60, 320, 140), fill=(128, 128, 128))
    draw.rectangle((0, 180, 320, 240), fill=(18, 18, 18))
    draw.rectangle((50, 160, 120, 180), fill=(128, 128, 128))
    draw.text((10, 195), "CORRUPTED REGION", fill=(255, 80, 80))
    draw.text((10, 210), "2PAC sample - damaged image", fill=(255, 255, 255))
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


def visualize_bit_layers(image, channel):
    """Extract and display all 8 bit planes for a selected channel."""
    if image is None:
        return None, "Upload an image first."

    channel_idx = {'Red': 0, 'Green': 1, 'Blue': 2}.get(channel, 1)
    channel_name = channel.lower()

    arr = np.array(image)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    ch = arr[:, :, channel_idx]

    h, w = ch.shape
    cell_h, cell_w = h, w
    grid = np.zeros((cell_h * 2, cell_w * 4, 3), dtype=np.uint8)

    labels = []
    for bit in range(8):
        plane = ((ch >> bit) & 1) * 255
        plane_rgb = np.stack([plane] * 3, axis=-1).astype(np.uint8)
        row = bit // 4
        col = bit % 4
        grid[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w] = plane_rgb
        labels.append(f"Bit {bit}")

    info = (
        f"**{channel.capitalize()} channel — 8 bit planes**\n\n"
        f"Each image shows one bit plane (bit 0 = LSB, bit 7 = MSB).\n"
        f"White pixels = bit is 1, black = bit is 0.\n\n"
        f"**Bit 0 (LSB)** is where 2PAC hides data at 1 bit/channel. "
        f"Notice how it looks like random noise — that's what makes LSB steganography hard to see.\n\n"
        f"Higher bits show the actual image structure. "
        f"Bits 6–7 carry most of the visual information."
    )
    return grid, info


def hide_lsb(image, secret_text, password, bits_per_channel):
    if image is None:
        return None, None, "Upload an image first."
    if not secret_text or not secret_text.strip():
        return None, None, "Enter text to hide."

    input_path = output_path = None
    try:
        input_path = _save_numpy_image(image)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            output_path = tmp.name

        img = Image.open(input_path)
        capacity = lsb.calculate_capacity(img, bits_per_channel)
        data_size = len(secret_text.encode('utf-8'))

        if data_size > capacity:
            return None, None, (
                f"{_badge('TOO LARGE', 'red')}\n\n"
                f"Payload is **{data_size:,} bytes**, but this image can hold **{capacity:,} bytes**.\n\n"
                "Use a larger image or increase bits/channel."
            )

        pwd = password if password else None
        ok, msg, stats = lsb.embed_data(input_path, secret_text, output_path,
                                        password=pwd, bits_per_channel=bits_per_channel)
        if not ok:
            return None, None, f"{_badge('ERROR', 'red')}\n\n{msg}"

        result_img = Image.open(output_path).convert('RGB')
        result = (
            f"{_badge('LSB EMBEDDED', 'green')}\n\n"
            f"- **Payload:** {stats['data_size']:,} bytes\n"
            f"- **Encryption:** {'Yes' if stats['encrypted'] else 'No'}\n"
            f"- **Bits/channel:** {stats['bits_per_channel']}\n"
            f"- **Capacity used:** {stats['utilization']}\n\n"
            "Download the output image and keep it as PNG."
        )
        return image, result_img, result
    except Exception as e:
        return image, None, f"{_badge('ERROR', 'red')}\n\n{str(e)}"
    finally:
        _cleanup(input_path, output_path)


def hide_dct(image, secret_text, password):
    if image is None:
        return None, None, "Upload an image first."
    if not secret_text or not secret_text.strip():
        return None, None, "Enter text to hide."

    input_path = output_path = None
    try:
        input_path = _save_numpy_image(image)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            output_path = tmp.name

        pwd = password if password else None
        ok, msg, stats = dct.embed_data(input_path, secret_text, output_path, password=pwd)
        if not ok:
            return None, None, f"{_badge('DCT ERROR', 'red')}\n\n{msg}"

        result_img = Image.open(output_path).convert('RGB')
        result = (
            f"{_badge('DCT EXPERIMENTAL', 'purple')}\n\n"
            "DCT embeds in frequency coefficients and is harder for LSB analysis to see, "
            "but extraction reliability is still under active development. Use LSB for critical data.\n\n"
            f"- **Payload:** {stats['data_size']:,} bytes\n"
            f"- **Encryption:** {'Yes' if stats['encrypted'] else 'No'}\n"
            f"- **Blocks used:** {stats['blocks_used']}/{stats['total_blocks']}\n"
        )
        return image, result_img, result
    except Exception as e:
        return image, None, f"{_badge('ERROR', 'red')}\n\n{str(e)}"
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
        return None, None, "Upload an image to analyze."

    image_path = None
    try:
        image_path = _save_numpy_image(image)
        sens = slider_to_sensitivity(sensitivity)
        is_suspicious, confidence, details = rat_finder.analyze_image(image_path, sensitivity=sens)
        ela_suspicious, ela_conf, ela_details = rat_finder.perform_ela_analysis(image_path)

        badge = _badge('HIGH SUSPICION', 'red') if confidence >= 70 else (
            _badge('MODERATE SUSPICION', 'yellow') if confidence >= 40 else
            _badge('LOW SUSPICION', 'green')
        )

        lines = [f"{badge}\n", _gauge(confidence), "", "**Signals:**"]
        for key, result in details.items():
            if isinstance(result, dict):
                susp = result.get('suspicious', False)
                conf = result.get('confidence', 0)
                det = result.get('details', '')
                status = "suspicious" if susp else "clean"
                lines.append(f"- **{key}:** {conf:.0f}% - {status} - {det}")
            else:
                lines.append(f"- **{key}:** {result}")
        lines.extend([
            "",
            "**Interpretation:** RAT Finder answers: *Does this image contain hidden data?*",
            "A high score means forensic anomalies exist; it is not proof of a secret message."
        ])

        ela_img = None
        if isinstance(ela_details, dict) and 'diff_image' in ela_details:
            ela_img = ela_details['diff_image']
        return image, ela_img, '\n'.join(lines)
    except Exception as e:
        return None, None, f"{_badge('ERROR', 'red')}\n\n{str(e)}"
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


def _build_stego_cmd(subcommand, image_path, data, output, password, dct_flag, bits, quality):
    parts = ["python 2pac.py", subcommand]
    if subcommand == "hide":
        if image_path:
            parts.append(f"--image {image_path}")
        if data:
            parts.append(f'--data "{data}"')
        if output:
            parts.append(f"--output {output}")
        if password:
            parts.append("--password ****")
        if dct_flag:
            parts.append("--dct")
            if quality and quality != 95:
                parts.append(f"--quality {quality}")
        else:
            if bits and bits != 1:
                parts.append(f"--bits {bits}")
    elif subcommand == "extract":
        if image_path:
            parts.append(f"--image {image_path}")
        if password:
            parts.append("--password ****")
        if dct_flag:
            parts.append("--dct")
        else:
            if bits and bits != 1:
                parts.append(f"--bits {bits}")
    return " \\\n  ".join(parts) if len(parts) > 3 else " ".join(parts)


def _build_ratfinder_cmd(subcommand, path, sensitivity, non_recursive, workers,
                        visual_reports, reports_dir, thorough, check_visual, repair,
                        backup_dir, move_to, delete, formats, resume, output):
    parts = ["python ratfinder.py", subcommand]
    if subcommand == "detect":
        if path:
            parts.append(path)
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
    elif subcommand == "scan":
        if path:
            parts.append(path)
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
        if move_to:
            parts.append(f"--move-to {move_to}")
        elif delete:
            parts.append("--delete")
        if formats:
            parts.append(f"--formats {' '.join(formats)}")
        if workers and workers != 1:
            parts.append(f"--workers {workers}")
        if resume:
            parts.append(f"--resume {resume}")
        if output:
            parts.append(f"--output {output}")
    elif subcommand == "check":
        if path:
            parts.append(path)
        if check_visual:
            parts.append("--check-visual")
        if sensitivity != "medium":
            parts.append(f"--sensitivity {sensitivity}")
    return " \\\n  ".join(parts) if len(parts) > 3 else " ".join(parts)


HEADER = """
# 2PAC + RAT Finder

**2PAC** hides data inside images. **RAT Finder** catches the rats - people sneaking hidden data through your images, or corrupt files breaking your collection.
"""


MEMORIAL = """
*In memory of Jeff Young. All Eyez On Your Images.*
"""


INTRO_SECTION = """
### Two tools, two jobs.

**2PAC** - You want to put data in. Someone is sneaking information to the feds, hiding messages inside vacation photos, or exfiltrating data through image attachments. That's what 2PAC does - it hides text inside images so nobody knows it's there. You can also extract it back out.

**RAT Finder** - You want to catch a RAT. Someone sent you an image that looks normal but might have a secret payload hidden inside. Or you have a folder of images and some of them are corrupt - broken headers, truncated files, gray blocks where the photo should be. RAT Finder detects both: steganography and corruption. Use a RAT to catch a RAT.
"""


HOW_STEGO_WORKS = """
### How does steganography work?

Every pixel in a digital image is stored as numbers - three channels (red, green, blue), each 0–255. That's 8 binary bits per channel.

LSB steganography changes only the **last bit** - the least significant bit. The visual change is invisible:

```
Original pixel:   R=156   G=89    B=201
Binary:           10011100 01011001 11001001
                                            ^--- this bit stores your secret
Modified pixel:   R=156   G=88    B=201     (89→88, undetectable to the eye)
```

A 1000×1000 image can hide roughly **375 KB** of text this way. What does that mean?

| Reference | Size |
|---|---|
| A text message | ~100 bytes |
| A typical email | ~2–5 KB |
| The US Constitution | ~46 KB |
| A 20-page research paper | ~150 KB |
| A full novel (~60,000 words) | ~360 KB |

So a single 1000×1000 photo can hide roughly **a full novel**. A 4K phone photo (4000×3000) can hide ~4.5 MB - about twelve novels.

Add a password and the data is XOR-encrypted before embedding.

2PAC also offers **DCT mode** (experimental) which hides data in the frequency domain instead of pixel values - harder to detect but with much lower capacity.
"""


HOW_DETECTION_WORKS = """
### How does RAT Finder detect steganography?

Seven forensic techniques combined into a weighted confidence score:

- **LSB Chi-Squared** - Natural images have structured LSBs. Steganography makes them uniformly random. A statistical test catches this.
- **Histogram Analysis** - Systematic LSB modification creates a distinctive "comb pattern" in color histograms.
- **Error Level Analysis** - Re-saves the image and measures pixel differences. Edited regions show different error levels.
- **Visual Noise** - Compares noise levels across color channels. Steganography creates a detectable imbalance.
- **Metadata Inspection** - Scans EXIF data for known steganography tool signatures (OutGuess, StegHide, JSteg, F5).
- **File Size Anomalies** - Compares file size against expected ranges. Embedded payloads bloat files.
- **Trailing Data** - Checks for data appended after the file's official end-of-file marker.

A confidence score >= 70% means HIGH SUSPICION.
"""


HOW_VALIDATION_WORKS = """
### How does image validation work?

RAT Finder runs images through a multi-step pipeline:

1. **Header check** - Quick structural validation
2. **Full pixel decode** - Reads every pixel to catch truncation
3. **Visual corruption** *(optional)* - Detects gray/black blocks from damaged storage or incomplete writes
4. **Structure audit** - JPEG marker chain or PNG chunk validation
5. **Re-encode test** - Catches subtle decoder errors
6. **External tools** - Runs `exiftool` and ImageMagick if available

Supports JPEG, PNG, GIF, TIFF, BMP, WebP, HEIC, and ICO. Repair is available for JPEG, PNG, and GIF.
"""


dark_noir = gr.themes.Soft(
    primary_hue="violet",
    secondary_hue="blue",
    neutral_hue="stone",
).set(
    body_background_fill="#0d0d0d",
    body_background_fill_dark="#0d0d0d",
    background_fill_primary="#1a1a1a",
    background_fill_primary_dark="#1a1a1a",
    background_fill_secondary="#1f1f1f",
    background_fill_secondary_dark="#1f1f1f",
    border_color_primary="#333333",
    border_color_primary_dark="#333333",
    body_text_color="#e0e0e0",
    body_text_color_dark="#e0e0e0",
    body_text_color_subdued="#a0a0a0",
    body_text_color_subdued_dark="#a0a0a0",
    button_primary_background_fill="#7c3aed",
    button_primary_background_fill_dark="#7c3aed",
    button_primary_text_color="#ffffff",
    button_primary_text_color_dark="#ffffff",
    button_secondary_background_fill="#2a2a2a",
    button_secondary_background_fill_dark="#2a2a2a",
    button_secondary_text_color="#e0e0e0",
    button_secondary_text_color_dark="#e0e0e0",
    input_background_fill="#1a1a1a",
    input_background_fill_dark="#1a1a1a",
    input_border_color="#333333",
    input_border_color_dark="#333333",
    block_background_fill="#1a1a1a",
    block_background_fill_dark="#1a1a1a",
    block_border_color="#333333",
    block_border_color_dark="#333333",
    block_label_text_color="#a0a0a0",
    block_label_text_color_dark="#a0a0a0",
)


with gr.Blocks(title="2PAC + RAT Finder") as demo:
    gr.Markdown(HEADER)
    gr.Markdown(MEMORIAL)

    with gr.Tabs():
        with gr.Tab("Start Here"):
            gr.Markdown(INTRO_SECTION)
            with gr.Row():
                with gr.Column():
                    gr.Markdown(
                        "### 2PAC - Put Data In\n"
                        "You want to **hide data inside an image**.\n\n"
                        "- Hide a message that nobody can see\n"
                        "- Extract hidden messages from images\n"
                        "- Password-protect your secrets\n\n"
                        "Go to the **2PAC** tab to hide or extract data."
                    )
                with gr.Column():
                    gr.Markdown(
                        "### RAT Finder - Catch a RAT\n"
                        "You want to **find out what's wrong with an image**.\n\n"
                        "- Someone sent you a photo - is there a hidden payload?\n"
                        "- Is this JPEG corrupt? Is this PNG truncated?\n"
                        "- Batch-check entire folders for problems\n\n"
                        "Go to the **RAT Finder** tab to analyze images."
                    )
            gr.Markdown(HOW_STEGO_WORKS)
            gr.Markdown(HOW_DETECTION_WORKS)
            gr.Markdown(HOW_VALIDATION_WORKS)

        with gr.Tab("2PAC"):
            with gr.Tabs():
                with gr.Tab("Hide"):
                    method = gr.Radio(['LSB - stable, high capacity'],
                                      value='LSB - stable, high capacity', label="Method")
                    gr.Markdown(
                        "*DCT mode (frequency-domain embedding) is available via the CLI (`--dct` flag) "
                        "but is currently non-functional — extraction does not reliably roundtrip. "
                        "Use LSB for all hiding.*"
                    )
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
                            with gr.Row():
                                hide_orig = gr.Image(label="Original", height=220, format="png", interactive=False)
                                hide_out_img = gr.Image(label="Stego output (download as PNG)", height=220, format="png", interactive=False)
                            hide_out_text = gr.Markdown()

                    def _hide_router(method_name, image, text, password, bits):
                        return hide_lsb(image, text, password, bits)

                    hide_btn.click(fn=_hide_router,
                                   inputs=[method, hide_in, hide_text, hide_pass, hide_bits],
                                   outputs=[hide_orig, hide_out_img, hide_out_text])
                    gr.Markdown("**The two images above should look identical - that's the point.** Keep stego output as PNG. JPEG destroys hidden data.")

                with gr.Tab("Extract"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            ext_in = gr.Image(label="Image with hidden data", type="numpy", height=300, format="png")
                            gr.Button("Load LSB stego sample").click(fn=sample_lsb_stego_image, outputs=[ext_in])
                            ext_method = gr.Radio(['LSB'], value='LSB', label="Method")
                            ext_pass = gr.Textbox(label="Password", type="password", placeholder="if encrypted")
                            ext_bits = gr.Slider(1, 4, value=1, step=1, label="Bits/channel (LSB only)")
                            ext_btn = gr.Button("Extract", variant="primary")
                        with gr.Column(scale=1):
                            ext_out = gr.Markdown()
                    ext_btn.click(fn=extract_data, inputs=[ext_in, ext_pass, ext_bits, ext_method], outputs=[ext_out])

                with gr.Tab("Bit Layers"):
                    gr.Markdown(
                        "### Bit-Plane Visualization\n\n"
                        "Every pixel value is 8 bits. This tool splits each channel into its 8 bit planes "
                        "so you can see exactly where hidden data lives.\n\n"
                        "**Bit 0 (LSB)** looks like random noise — that's where 2PAC embeds data. "
                        "**Bits 6–7** carry the visible image. Modify bit 0 and nobody can tell."
                    )
                    with gr.Row():
                        with gr.Column(scale=1):
                            bit_in = gr.Image(label="Image to analyze", type="numpy", height=300, format="png")
                            with gr.Row():
                                gr.Button("Load clean sample").click(fn=sample_clean_image, outputs=[bit_in])
                                gr.Button("Load LSB stego sample").click(fn=sample_lsb_stego_image, outputs=[bit_in])
                            bit_channel = gr.Radio(['Red', 'Green', 'Blue'], value='Green', label="Channel")
                            bit_btn = gr.Button("Show Bit Layers", variant="primary")
                        with gr.Column(scale=2):
                            bit_out = gr.Image(label="Bit planes (bit 0–3 top row, bit 4–7 bottom row)", height=400, format="png", interactive=False)
                            bit_info = gr.Markdown()
                    bit_btn.click(fn=visualize_bit_layers, inputs=[bit_in, bit_channel], outputs=[bit_out, bit_info])

        with gr.Tab("RAT Finder"):
            with gr.Tabs():
                with gr.Tab("Detect Steganography"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            det_in = gr.Image(label="Image to analyze", type="numpy", height=300, format="png")
                            with gr.Row():
                                gr.Button("Load clean sample").click(fn=sample_clean_image, outputs=[det_in])
                                gr.Button("Load LSB stego sample").click(fn=sample_lsb_stego_image, outputs=[det_in])
                            det_sens = gr.Slider(1, 10, value=5, step=1, label="Sensitivity")
                            det_btn = gr.Button("Run RAT Finder", variant="primary")
                        with gr.Column(scale=1):
                            with gr.Row():
                                det_orig = gr.Image(label="Original", height=220, format="png", interactive=False)
                                det_ela = gr.Image(label="ELA visualization", height=220, format="png", interactive=False)
                            det_out = gr.Markdown()
                    det_btn.click(fn=detect_stego, inputs=[det_in, det_sens], outputs=[det_orig, det_ela, det_out])

                with gr.Tab("Check Image"):
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
                    gr.Markdown("Upload multiple files to check archive health.")
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

        with gr.Tab("CLI Builder"):
            gr.Markdown(
                "## Command-Line Builder\n\n"
                "Build the command you need, then copy and paste it into your terminal. "
                "[Install 2PAC](https://github.com/ricyoung/2pac) locally to use the CLI."
            )
            cli_tool = gr.Radio(["2PAC (hide/extract)", "RAT Finder (detect/scan/check)"],
                                value="2PAC (hide/extract)", label="Select tool")

            with gr.Column(visible=True) as cli_2pac_col:
                stego_sub = gr.Radio(["hide", "extract"], value="hide", label="Subcommand")
                with gr.Row():
                    with gr.Column():
                        stego_image = gr.Textbox(label="--image", placeholder="photo.png")
                        stego_data = gr.Textbox(label="--data (hide only)", placeholder="secret message")
                        stego_output = gr.Textbox(label="--output (hide only)", placeholder="out.png")
                    with gr.Column():
                        stego_password = gr.Textbox(label="--password", type="password", placeholder="optional")
                        stego_dct = gr.Checkbox(label="--dct  (use DCT mode)")
                        stego_bits = gr.Dropdown([1, 2, 3, 4], value=1, label="--bits (LSB bits/channel)")
                        stego_quality = gr.Slider(50, 100, value=95, step=5, label="--quality (DCT only)")
                stego_cmd_out = gr.Code(label="Generated command", language="shell", interactive=False)
                for c in [stego_sub, stego_image, stego_data, stego_output, stego_password, stego_dct, stego_bits, stego_quality]:
                    c.change(fn=_build_stego_cmd,
                             inputs=[stego_sub, stego_image, stego_data, stego_output,
                                     stego_password, stego_dct, stego_bits, stego_quality],
                             outputs=[stego_cmd_out])

            with gr.Column(visible=False) as cli_rat_col:
                rat_sub = gr.Radio(["detect", "scan", "check"], value="detect", label="Subcommand")
                with gr.Row():
                    with gr.Column():
                        rat_path = gr.Textbox(label="File or directory", placeholder="suspicious.png or ./images")
                        rat_sens = gr.Dropdown(["low", "medium", "high"], value="medium", label="--sensitivity")
                        rat_workers = gr.Slider(1, 16, value=1, step=1, label="--workers")
                    with gr.Column():
                        rat_thorough = gr.Checkbox(label="--thorough (scan/check)")
                        rat_visual = gr.Checkbox(label="--check-visual (scan/check)")
                        rat_repair = gr.Checkbox(label="--repair (scan)")
                        rat_delete = gr.Checkbox(label="--delete (scan, overrides --move-to)")
                with gr.Row():
                    rat_move = gr.Textbox(label="--move-to (scan)", placeholder="./quarantine")
                    rat_backup = gr.Textbox(label="--backup-dir (scan)", placeholder="./backups")
                    rat_formats = gr.CheckboxGroup(["JPEG", "PNG", "GIF", "TIFF", "BMP", "WEBP"], label="--formats (scan)")
                with gr.Row():
                    rat_nonrec = gr.Checkbox(label="--non-recursive (detect)")
                    rat_reports = gr.Checkbox(label="--visual-reports (detect)")
                    rat_reports_dir = gr.Textbox(label="--reports-dir (detect)", placeholder="./reports")
                with gr.Row():
                    rat_resume = gr.Textbox(label="--resume session ID (scan)", placeholder="abc123")
                    rat_output_file = gr.Textbox(label="--output results file (scan)", placeholder="results.txt")
                rat_cmd_out = gr.Code(label="Generated command", language="shell", interactive=False)
                for c in [rat_sub, rat_path, rat_sens, rat_workers, rat_thorough, rat_visual,
                          rat_repair, rat_delete, rat_move, rat_backup, rat_formats,
                          rat_nonrec, rat_reports, rat_reports_dir, rat_resume, rat_output_file]:
                    c.change(fn=_build_ratfinder_cmd,
                             inputs=[rat_sub, rat_path, rat_sens, rat_nonrec, rat_workers,
                                     rat_reports, rat_reports_dir, rat_thorough, rat_visual, rat_repair,
                                     rat_backup, rat_move, rat_delete, rat_formats, rat_resume, rat_output_file],
                             outputs=[rat_cmd_out])

            def _toggle_cli(tool):
                if tool.startswith("2PAC"):
                    return gr.update(visible=True), gr.update(visible=False)
                return gr.update(visible=False), gr.update(visible=True)

            cli_tool.change(fn=_toggle_cli, inputs=[cli_tool], outputs=[cli_2pac_col, cli_rat_col])

    gr.Markdown(
        "---\n"
        "[GitHub](https://github.com/ricyoung/2pac) | "
        "[DeepNeuro.AI](https://deepneuro.ai) | "
        "In memory of Jeff Young"
    )


if __name__ == "__main__":
    demo.launch(theme=dark_noir)
