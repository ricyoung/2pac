#!/usr/bin/env python3
"""
2PAC: Picture Analyzer & Corruption Killer - Gradio Web Interface

Two unified tools:
  python 2pac_stego.py hide|extract|detect ...
  python 2pac_scan.py ...
"""

import os
import tempfile
import gradio as gr
from PIL import Image
import io
import base64
import numpy as np

from steg_embedder import StegEmbedder
from dct_steg import DctStegEmbedder
import rat_finder
import find_bad_images
from utils import slider_to_sensitivity


lsb = StegEmbedder()
dct = DctStegEmbedder()


# ── LSB Embed ──────────────────────────────────────────────────────────

def hide_lsb(image, secret_text, password, bits_per_channel):
    if image is None:
        return None, "Upload an image first"
    if not secret_text or not secret_text.strip():
        return None, "Enter text to hide"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            Image.fromarray(image).save(tmp.name, 'PNG')
            input_path = tmp.name
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            output_path = tmp.name

        img = Image.open(input_path)
        capacity = lsb.calculate_capacity(img, bits_per_channel)
        data_size = len(secret_text.encode('utf-8'))

        if data_size > capacity:
            os.unlink(input_path)
            return None, f"**Data too large**\n\n{data_size:,} bytes > {capacity:,} byte capacity\n\nUse a larger image or more bits per channel."

        pwd = password if password else None
        ok, msg, stats = lsb.embed_data(input_path, secret_text, output_path,
                                        password=pwd, bits_per_channel=bits_per_channel)
        os.unlink(input_path)

        if not ok:
            if os.path.exists(output_path):
                os.unlink(output_path)
            return None, f"**Error:** {msg}"

        result_img = Image.open(output_path)
        result = (
            f"**Embedded {stats['data_size']:,} bytes** | "
            f"{'Encrypted' if stats['encrypted'] else 'Plaintext'} | "
            f"{stats['bits_per_channel']} bit(s)/channel | "
            f"Utilization: {stats['utilization']}"
        )
        return result_img, result
    except Exception as e:
        return None, f"**Error:** {str(e)}"


# ── DCT Embed ──────────────────────────────────────────────────────────

def hide_dct(image, secret_text, password):
    if image is None:
        return None, "Upload an image first"
    if not secret_text or not secret_text.strip():
        return None, "Enter text to hide"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            Image.fromarray(image).save(tmp.name, 'PNG')
            input_path = tmp.name
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            output_path = tmp.name

        pwd = password if password else None
        ok, msg, stats = dct.embed_data(input_path, secret_text, output_path, password=pwd)
        os.unlink(input_path)

        if not ok:
            if os.path.exists(output_path):
                os.unlink(output_path)
            return None, f"**Error:** {msg}"

        result_img = Image.open(output_path)
        result = (
            f"**Embedded {stats['data_size']:,} bytes** | "
            f"{'Encrypted' if stats['encrypted'] else 'Plaintext'} | "
            f"DCT domain | "
            f"Blocks: {stats['blocks_used']}/{stats['total_blocks']}"
        )
        return result_img, result
    except Exception as e:
        return None, f"**Error:** {str(e)}"


# ── Extract (LSB + DCT) ───────────────────────────────────────────────

def extract_data(image, password, bits_per_channel, method):
    if image is None:
        return "Upload an image first"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            Image.fromarray(image).save(tmp.name, 'PNG')
            image_path = tmp.name

        pwd = password if password else None

        if method == 'LSB':
            ok, msg, data = lsb.extract_data(image_path, password=pwd,
                                             bits_per_channel=bits_per_channel)
        else:
            ok, msg, data = dct.extract_data(image_path, password=pwd)

        os.unlink(image_path)

        if not ok:
            return f"**{msg}**\n\nPossible: wrong password, wrong method, wrong bits, or no hidden data."

        return f"**Extracted {len(data)} chars:**\n\n```\n{data}\n```"
    except Exception as e:
        return f"**Error:** {str(e)}"


# ── Detect ─────────────────────────────────────────────────────────────

def detect_stego(image, sensitivity):
    if image is None:
        return None, "Upload an image to analyze"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            Image.fromarray(image).save(tmp.name, 'PNG')
            image_path = tmp.name

        sens = slider_to_sensitivity(sensitivity)
        confidence, details = rat_finder.analyze_image(image_path, sensitivity=sens)
        ela = rat_finder.perform_ela_analysis(image_path)
        os.unlink(image_path)

        if confidence >= 70:
            label = "⚠ HIGH SUSPICION"
        elif confidence >= 40:
            label = "⚡ MODERATE"
        else:
            label = "✓ LOW SUSPICION"

        lines = [f"## {label}  ({confidence:.1f}%)", ""]
        for d in details:
            lines.append(f"- {d}")
        lines.extend(["", "*High confidence = anomalies exist, not necessarily hidden data.*"])

        ela_img = ela['ela_image'] if ela['success'] else None
        return ela_img, '\n'.join(lines)
    except Exception as e:
        return None, f"**Error:** {str(e)}"


# ── Validate ───────────────────────────────────────────────────────────

def validate_image(image, sensitivity, check_visual):
    if image is None:
        return "Upload an image to check"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            Image.fromarray(image).save(tmp.name, 'PNG')
            image_path = tmp.name

        sens = slider_to_sensitivity(sensitivity)
        valid = find_bad_images.is_valid_image(image_path, thorough=True,
                                               sensitivity=sens,
                                               check_visual=check_visual)
        issues = find_bad_images.diagnose_image_issue(image_path)
        os.unlink(image_path)

        if valid:
            return (
                "## ✓ Image is valid\n\n"
                "File structure, headers, metadata, and visual content all check out.\n\n"
                "*Safe to use.*"
            )
        else:
            lines = ["## ✗ Issues detected", ""]
            if issues:
                for issue_type, desc in issues.items():
                    lines.append(f"**{issue_type}:** {desc}")
            else:
                lines.append("Image failed validation.")
            lines.extend(["", "*Try re-downloading the file or repairing it.*"])
            return '\n'.join(lines)
    except Exception as e:
        return f"**Error:** {str(e)}"


# ── UI ─────────────────────────────────────────────────────────────────

HEADER = """
# 2PAC: Picture Analyzer & Corruption Killer

**Hide messages in images. Detect hidden data. Validate image integrity.**
"""

FOOTER = """
---

**[GitHub](https://github.com/ricyoung/2pac)**  |  **DeepNeuro.AI**
"""

with gr.Blocks(title="2PAC") as demo:

    gr.Markdown(HEADER)

    with gr.Tabs():

        # ═══ HIDE ══════════════════════════════════════════════════════

        with gr.Tab("Hide Data"):

            with gr.Tabs():
                with gr.Tab("LSB (fast, high capacity)"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            lsb_in = gr.Image(label="Source image", type="numpy", height=280)
                            lsb_text = gr.Textbox(label="Text to hide", lines=4, placeholder="Type your secret...")
                            with gr.Row():
                                lsb_pass = gr.Textbox(label="Password", type="password", placeholder="optional")
                                lsb_bits = gr.Slider(1, 4, value=1, step=1, label="Bits/channel",
                                                     info="1=subtle  ·  4=max capacity")
                            lsb_btn = gr.Button("Embed with LSB", variant="primary")

                        with gr.Column(scale=1):
                            lsb_out = gr.Image(label="Stego image (download this)", height=280)
                            lsb_info = gr.Markdown()

                    lsb_btn.click(fn=hide_lsb, inputs=[lsb_in, lsb_text, lsb_pass, lsb_bits],
                                  outputs=[lsb_out, lsb_info])

                with gr.Tab("DCT (harder to detect, lower capacity)"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            dct_in = gr.Image(label="Source image", type="numpy", height=280)
                            dct_text = gr.Textbox(label="Text to hide", lines=4, placeholder="Type your secret...")
                            dct_pass = gr.Textbox(label="Password", type="password", placeholder="optional")
                            dct_btn = gr.Button("Embed with DCT", variant="primary")

                        with gr.Column(scale=1):
                            dct_out = gr.Image(label="Stego image (download this)", height=280)
                            dct_info = gr.Markdown()

                    dct_btn.click(fn=hide_dct, inputs=[dct_in, dct_text, dct_pass],
                                  outputs=[dct_out, dct_info])

            gr.Markdown("**Tip:** Save output as PNG. JPEG recompression destroys hidden data.")

        # ═══ EXTRACT ════════════════════════════════════════════════════

        with gr.Tab("Extract Data"):
            with gr.Row():
                with gr.Column(scale=1):
                    ext_in = gr.Image(label="Image with hidden data", type="numpy", height=280)
                    with gr.Row():
                        ext_pass = gr.Textbox(label="Password", type="password", placeholder="if encrypted")
                        ext_bits = gr.Slider(1, 4, value=1, step=1, label="Bits/channel (LSB only)")
                    ext_method = gr.Radio(['LSB', 'DCT'], value='LSB', label="Method")
                    ext_btn = gr.Button("Extract", variant="primary")

                with gr.Column(scale=1):
                    ext_out = gr.Markdown()

            ext_btn.click(fn=extract_data, inputs=[ext_in, ext_pass, ext_bits, ext_method],
                          outputs=[ext_out])

        # ═══ DETECT ═════════════════════════════════════════════════════

        with gr.Tab("Detect"):
            with gr.Row():
                with gr.Column(scale=1):
                    det_in = gr.Image(label="Image to analyze", type="numpy", height=280)
                    det_sens = gr.Slider(1, 10, value=5, step=1, label="Sensitivity")
                    det_btn = gr.Button("Analyze", variant="primary")

                with gr.Column(scale=1):
                    det_img = gr.Image(label="ELA visualization", height=280)
                    det_out = gr.Markdown()

            det_btn.click(fn=detect_stego, inputs=[det_in, det_sens],
                          outputs=[det_img, det_out])

        # ═══ VALIDATE ═══════════════════════════════════════════════════

        with gr.Tab("Validate"):
            with gr.Row():
                with gr.Column(scale=1):
                    val_in = gr.Image(label="Image to check", type="numpy", height=280)
                    with gr.Row():
                        val_sens = gr.Slider(1, 10, value=5, step=1, label="Sensitivity")
                        val_vis = gr.Checkbox(value=True, label="Visual corruption check")
                    val_btn = gr.Button("Check Integrity", variant="primary")

                with gr.Column(scale=1):
                    val_out = gr.Markdown()

            val_btn.click(fn=validate_image, inputs=[val_in, val_sens, val_vis],
                          outputs=[val_out])

    gr.Markdown(FOOTER)


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(primary_hue="violet", secondary_hue="blue"))
