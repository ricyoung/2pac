#!/usr/bin/env python3
"""
2PAC: Picture Analyzer & Corruption Killer - Gradio Web Interface
Steganography, image corruption detection, and security analysis
"""

import os
import tempfile
import gradio as gr
from PIL import Image
import matplotlib.pyplot as plt
import io
import base64

# Import 2PAC modules
from steg_embedder import StegEmbedder
import rat_finder
import find_bad_images


# Initialize embedder
embedder = StegEmbedder()


def hide_data_in_image(image, secret_text, password, bits_per_channel):
    """
    Tab 1: Hide data in an image using LSB steganography
    """
    if image is None:
        return None, "⚠️ Please upload an image first"

    if not secret_text or len(secret_text.strip()) == 0:
        return None, "⚠️ Please enter text to hide"

    try:
        # Save uploaded image to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_input:
            img = Image.fromarray(image)
            img.save(tmp_input.name, 'PNG')
            input_path = tmp_input.name

        # Create output file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_output:
            output_path = tmp_output.name

        # Calculate capacity first
        img = Image.open(input_path)
        capacity = embedder.calculate_capacity(img, bits_per_channel)

        # Check if data fits
        data_size = len(secret_text.encode('utf-8'))
        if data_size > capacity:
            os.unlink(input_path)
            return None, f"❌ **Error:** Data too large!\n\n" \
                        f"- **Data size:** {data_size:,} bytes\n" \
                        f"- **Maximum capacity:** {capacity:,} bytes\n" \
                        f"- **Overflow:** {data_size - capacity:,} bytes\n\n" \
                        f"💡 Try: Shorter text, larger image, or more bits per channel"

        # Embed data
        pwd = password if password and len(password) > 0 else None
        success, message, stats = embedder.embed_data(
            input_path,
            secret_text,
            output_path,
            password=pwd,
            bits_per_channel=bits_per_channel
        )

        # Clean up input
        os.unlink(input_path)

        if not success:
            if os.path.exists(output_path):
                os.unlink(output_path)
            return None, f"❌ **Error:** {message}"

        # Load result image
        result_img = Image.open(output_path)

        # Format success message
        result_message = f"""
✅ **Successfully Hidden!**

📊 **Statistics:**
- **Data hidden:** {stats['data_size']:,} bytes ({len(secret_text):,} characters)
- **Image capacity:** {stats['capacity']:,} bytes
- **Utilization:** {stats['utilization']}
- **Encryption:** {"🔒 Yes" if stats['encrypted'] else "🔓 No"}
- **LSB depth:** {stats['bits_per_channel']} bit(s) per channel
- **Image dimensions:** {stats['image_size']}

💾 **Download the image below** - your data is invisible to the naked eye!

⚠️ **Important:**
- Save as PNG (not JPEG - will destroy hidden data)
- Keep your password safe if you used encryption
"""

        return result_img, result_message

    except Exception as e:
        if 'input_path' in locals() and os.path.exists(input_path):
            os.unlink(input_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.unlink(output_path)
        return None, f"❌ **Error:** {str(e)}"


def detect_hidden_data(image, sensitivity):
    """
    Tab 2: Detect steganography using RAT Finder analysis
    """
    if image is None:
        return None, "⚠️ Please upload an image to analyze"

    try:
        # Save uploaded image to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            img = Image.fromarray(image)
            img.save(tmp.name, 'PNG')
            image_path = tmp.name

        # Map slider to sensitivity
        sens_map = {1: 'low', 2: 'low', 3: 'low', 4: 'medium', 5: 'medium',
                   6: 'medium', 7: 'high', 8: 'high', 9: 'high', 10: 'high'}
        sensitivity_str = sens_map.get(sensitivity, 'medium')

        # Perform analysis
        confidence, details = rat_finder.analyze_image(image_path, sensitivity=sensitivity_str)

        # Generate ELA visualization
        ela_result = rat_finder.perform_ela_analysis(image_path)

        # Clean up
        os.unlink(image_path)

        # Create confidence indicator
        if confidence >= 70:
            confidence_emoji = "🚨"
            confidence_label = "HIGH SUSPICION"
        elif confidence >= 40:
            confidence_emoji = "⚠️"
            confidence_label = "MODERATE SUSPICION"
        else:
            confidence_emoji = "✅"
            confidence_label = "LOW SUSPICION"

        # Format results
        result_text = f"""
{confidence_emoji} **{confidence_label}**

📊 **Confidence Score:** {confidence:.1f}%

🔍 **Analysis Details:**
"""

        for detail in details:
            result_text += f"\n• {detail}"

        result_text += f"""

---

**What does this mean?**

- **ELA (Error Level Analysis):** Highlights areas with different compression levels
  - Bright areas = potential manipulation or hidden data
  - Uniform appearance = likely unmodified

- **LSB Analysis:** Checks randomness in least significant bits
- **Histogram Analysis:** Looks for statistical anomalies
- **Metadata:** Examines EXIF data for suspicious tools
- **File Structure:** Checks for trailing data

💡 **High confidence doesn't mean data is hidden** - just that anomalies exist.
Use the "Extract Data" tab if you suspect LSB steganography!
"""

        # Return ELA plot if available
        if ela_result['success'] and ela_result['ela_image']:
            return ela_result['ela_image'], result_text

        return None, result_text

    except Exception as e:
        if 'image_path' in locals() and os.path.exists(image_path):
            os.unlink(image_path)
        return None, f"❌ **Error:** {str(e)}"


def extract_hidden_data(image, password, bits_per_channel):
    """
    Tab 2b: Extract data hidden with LSB steganography
    """
    if image is None:
        return "⚠️ Please upload an image"

    try:
        # Save uploaded image to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            img = Image.fromarray(image)
            img.save(tmp.name, 'PNG')
            image_path = tmp.name

        # Attempt extraction
        pwd = password if password and len(password) > 0 else None
        success, message, extracted_data = embedder.extract_data(
            image_path,
            password=pwd,
            bits_per_channel=bits_per_channel
        )

        # Clean up
        os.unlink(image_path)

        if not success:
            return f"❌ **{message}**\n\nPossible reasons:\n" \
                   f"• No data hidden in this image\n" \
                   f"• Wrong password (if encrypted)\n" \
                   f"• Wrong bits-per-channel setting\n" \
                   f"• Image was modified/re-saved"

        result = f"""
✅ **Data Successfully Extracted!**

📝 **Hidden Message:**

---
{extracted_data}
---

📊 **Extraction Info:**
- **Data size:** {len(extracted_data)} characters
- **Decryption:** {"🔒 Used" if pwd else "🔓 Not needed"}
- **LSB depth:** {bits_per_channel} bit(s) per channel

💡 Copy the message above - it has been successfully recovered from the image!
"""
        return result

    except Exception as e:
        if 'image_path' in locals() and os.path.exists(image_path):
            os.unlink(image_path)
        return f"❌ **Error:** {str(e)}"


def check_image_corruption(image, sensitivity, check_visual):
    """
    Tab 3: Check for image corruption and validate integrity
    """
    if image is None:
        return "⚠️ Please upload an image to check"

    try:
        # Save uploaded image to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            img = Image.fromarray(image)
            img.save(tmp.name, 'PNG')
            image_path = tmp.name

        # Map slider to sensitivity
        sens_map = {1: 'low', 2: 'low', 3: 'low', 4: 'medium', 5: 'medium',
                   6: 'medium', 7: 'high', 8: 'high', 9: 'high', 10: 'high'}
        sensitivity_str = sens_map.get(sensitivity, 'medium')

        # Validate image
        is_valid = find_bad_images.is_valid_image(
            image_path,
            thorough=True,
            sensitivity=sensitivity_str,
            check_visual=check_visual
        )

        # Get diagnostic details
        issues = find_bad_images.diagnose_image_issue(image_path)

        # Clean up
        os.unlink(image_path)

        # Format results
        if is_valid:
            result = f"""
✅ **IMAGE IS VALID**

The image passed all validation checks:
- ✅ File structure is intact
- ✅ Headers are valid
- ✅ No truncation detected
- ✅ Metadata is consistent
"""
            if check_visual:
                result += "- ✅ No visual corruption detected\n"

            result += "\n💚 **This image is safe to use!**"

        else:
            result = f"""
⚠️ **ISSUES DETECTED**

The image has validation problems:

"""
            if issues:
                for issue_type, issue_desc in issues.items():
                    result += f"**{issue_type}:**\n{issue_desc}\n\n"
            else:
                result += "❌ Image failed validation but no specific issues identified.\n\n"

            result += """
---

**What to do:**
- Image may be corrupted or incomplete
- Try re-downloading the original file
- Check if the file was properly transferred
- Use image repair tools if needed
"""

        return result

    except Exception as e:
        if 'image_path' in locals() and os.path.exists(image_path):
            os.unlink(image_path)
        return f"❌ **Error:** {str(e)}"


# Create Gradio interface
with gr.Blocks(
    title="2PAC: Picture Analyzer & Corruption Killer",
    theme=gr.themes.Soft(
        primary_hue="violet",
        secondary_hue="blue",
    )
) as demo:

    gr.Markdown("""
# 🔫 2PAC: Picture Analyzer & Corruption Killer

**Advanced image security and steganography toolkit**

Hide secret messages in images, detect hidden data, and validate image integrity.
    """)

    with gr.Tabs():

        # TAB 1: Hide Data
        with gr.Tab("🔒 Hide Secret Data"):
            gr.Markdown("""
## Hide Data in Image (LSB Steganography)

Invisibly hide text inside an image using Least Significant Bit encoding.
The image will look identical to the naked eye, but contains your secret message!
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    hide_input_image = gr.Image(
                        label="Upload Image",
                        type="numpy",
                        height=300
                    )
                    hide_secret_text = gr.Textbox(
                        label="Secret Text to Hide",
                        placeholder="Enter your secret message here...",
                        lines=5,
                        max_lines=10
                    )
                    with gr.Row():
                        hide_password = gr.Textbox(
                            label="Password (Optional - for encryption)",
                            placeholder="Leave empty for no encryption",
                            type="password"
                        )
                        hide_bits = gr.Slider(
                            minimum=1,
                            maximum=4,
                            value=1,
                            step=1,
                            label="LSB Depth (higher = more capacity, less subtle)",
                            info="1=subtle, 4=maximum capacity"
                        )

                    hide_button = gr.Button("🔒 Hide Data in Image", variant="primary", size="lg")

                with gr.Column(scale=1):
                    hide_output_image = gr.Image(label="Result Image (Download This!)", height=300)
                    hide_output_text = gr.Markdown(label="Status")

            hide_button.click(
                fn=hide_data_in_image,
                inputs=[hide_input_image, hide_secret_text, hide_password, hide_bits],
                outputs=[hide_output_image, hide_output_text]
            )

            gr.Markdown("""
---
**💡 Tips:**
- Use PNG images for best results (JPEG will destroy hidden data!)
- Larger images can hold more data
- Password encryption adds extra security layer
- LSB depth: 1-2 bits is undetectable, 3-4 bits provides more capacity
            """)

        # TAB 2: Detect & Extract
        with gr.Tab("🔍 Detect & Extract Hidden Data"):
            gr.Markdown("""
## Detect Steganography & Extract Hidden Data

Use advanced analysis techniques to detect hidden data in images, or extract data hidden with this tool.
            """)

            with gr.Tabs():

                # Sub-tab: Detection
                with gr.Tab("🔎 Detect (Analysis)"):
                    gr.Markdown("""
### Steganography Detection (RAT Finder)

Analyzes images for signs of hidden data using multiple techniques:
ELA, LSB analysis, histogram analysis, metadata inspection, and more.
                    """)

                    with gr.Row():
                        with gr.Column(scale=1):
                            detect_input_image = gr.Image(
                                label="Upload Image to Analyze",
                                type="numpy",
                                height=300
                            )
                            detect_sensitivity = gr.Slider(
                                minimum=1,
                                maximum=10,
                                value=5,
                                step=1,
                                label="Detection Sensitivity",
                                info="Higher = more thorough but more false positives"
                            )
                            detect_button = gr.Button("🔍 Analyze for Hidden Data", variant="primary", size="lg")

                        with gr.Column(scale=1):
                            detect_output_image = gr.Image(label="ELA Visualization", height=300)
                            detect_output_text = gr.Markdown(label="Analysis Results")

                    detect_button.click(
                        fn=detect_hidden_data,
                        inputs=[detect_input_image, detect_sensitivity],
                        outputs=[detect_output_image, detect_output_text]
                    )

                # Sub-tab: Extraction
                with gr.Tab("📤 Extract Data"):
                    gr.Markdown("""
### Extract Hidden Data (LSB Extraction)

If you have an image created with the "Hide Data" tool, extract the hidden message here.
                    """)

                    with gr.Row():
                        with gr.Column(scale=1):
                            extract_input_image = gr.Image(
                                label="Upload Image with Hidden Data",
                                type="numpy",
                                height=300
                            )
                            with gr.Row():
                                extract_password = gr.Textbox(
                                    label="Password (if encrypted)",
                                    placeholder="Leave empty if not encrypted",
                                    type="password"
                                )
                                extract_bits = gr.Slider(
                                    minimum=1,
                                    maximum=4,
                                    value=1,
                                    step=1,
                                    label="LSB Depth (must match encoding)",
                                    info="Use same value as when hiding"
                                )
                            extract_button = gr.Button("📤 Extract Hidden Data", variant="primary", size="lg")

                        with gr.Column(scale=1):
                            extract_output_text = gr.Markdown(label="Extracted Data")

                    extract_button.click(
                        fn=extract_hidden_data,
                        inputs=[extract_input_image, extract_password, extract_bits],
                        outputs=[extract_output_text]
                    )

        # TAB 3: Check Corruption
        with gr.Tab("🛡️ Check Image Integrity"):
            gr.Markdown("""
## Image Corruption & Validation

Thoroughly validate image files for corruption, truncation, and structural issues.
Detects damaged headers, incomplete data, and visual artifacts.
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    check_input_image = gr.Image(
                        label="Upload Image to Validate",
                        type="numpy",
                        height=300
                    )
                    with gr.Row():
                        check_sensitivity = gr.Slider(
                            minimum=1,
                            maximum=10,
                            value=5,
                            step=1,
                            label="Validation Sensitivity",
                            info="Higher = more strict validation"
                        )
                        check_visual = gr.Checkbox(
                            label="Check for Visual Corruption",
                            value=True,
                            info="Slower but detects visual artifacts"
                        )
                    check_button = gr.Button("🛡️ Validate Image", variant="primary", size="lg")

                with gr.Column(scale=1):
                    check_output_text = gr.Markdown(label="Validation Results")

            check_button.click(
                fn=check_image_corruption,
                inputs=[check_input_image, check_sensitivity, check_visual],
                outputs=[check_output_text]
            )

            gr.Markdown("""
---
**🔍 Checks Performed:**
- ✅ File format validation (JPEG, PNG, GIF, etc.)
- ✅ Header integrity
- ✅ Data completeness
- ✅ Metadata consistency
- ✅ Visual corruption detection (black/gray regions)
- ✅ Structure validation
            """)

    gr.Markdown("""
---

## About 2PAC

**2PAC** (Picture Analyzer & Corruption Killer) is a comprehensive image security toolkit combining:
- **LSB Steganography**: Hide and extract secret messages in images
- **RAT Finder**: Advanced steganography detection using 7+ analysis techniques
- **Image Validation**: Detect corruption and structural issues

🔗 **GitHub:** [github.com/ricyoung/2pac](https://github.com/ricyoung/2pac)
🌐 **More Tools:** [demo.deepneuro.ai](https://demo.deepneuro.ai)

---

*Built with ❤️ by DeepNeuro.AI | Powered by Gradio & Hugging Face Spaces*
    """)


if __name__ == "__main__":
    demo.launch()
