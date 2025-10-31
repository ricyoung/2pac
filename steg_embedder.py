#!/usr/bin/env python3
"""
LSB Steganography Embedder for 2PAC
Hides and extracts data in images using Least Significant Bit technique
"""

import io
import hashlib
import struct
from typing import Tuple, Optional
from PIL import Image
import numpy as np


class StegEmbedder:
    """
    LSB (Least Significant Bit) Steganography implementation
    Hides data in the least significant bits of image pixels
    """

    HEADER_SIZE = 12  # 4 bytes for data length + 8 bytes for checksum
    MAGIC_NUMBER = b'2PAC'  # Signature to identify embedded data

    def __init__(self):
        self.last_capacity = 0
        self.last_used = 0

    def calculate_capacity(self, image: Image.Image, bits_per_channel: int = 1) -> int:
        """
        Calculate how many bytes can be hidden in the image

        Args:
            image: PIL Image object
            bits_per_channel: Number of LSBs to use per color channel (1-4)

        Returns:
            Maximum bytes that can be hidden
        """
        if image.mode not in ['RGB', 'RGBA']:
            raise ValueError(f"Unsupported image mode: {image.mode}. Use RGB or RGBA.")

        width, height = image.size
        channels = len(image.mode)  # 3 for RGB, 4 for RGBA

        # Total bits available
        total_bits = width * height * channels * bits_per_channel

        # Account for header (magic number + length + checksum)
        header_bits = (len(self.MAGIC_NUMBER) + self.HEADER_SIZE) * 8

        available_bits = total_bits - header_bits
        capacity = available_bits // 8  # Convert to bytes

        self.last_capacity = capacity
        return capacity

    def _string_to_bits(self, data: str) -> str:
        """Convert string to binary representation"""
        return ''.join(format(byte, '08b') for byte in data.encode('utf-8'))

    def _bits_to_string(self, bits: str) -> str:
        """Convert binary representation back to string"""
        chars = []
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            if len(byte) == 8:
                chars.append(chr(int(byte, 2)))
        return ''.join(chars)

    def _encrypt_data(self, data: str, password: str) -> bytes:
        """Simple XOR encryption with password-derived key"""
        key = hashlib.sha256(password.encode()).digest()
        data_bytes = data.encode('utf-8')

        encrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key[i % len(key)])

        return bytes(encrypted)

    def _decrypt_data(self, encrypted_data: bytes, password: str) -> str:
        """Decrypt XOR-encrypted data"""
        key = hashlib.sha256(password.encode()).digest()

        decrypted = bytearray()
        for i, byte in enumerate(encrypted_data):
            decrypted.append(byte ^ key[i % len(key)])

        return bytes(decrypted).decode('utf-8', errors='replace')

    def embed_data(
        self,
        image_path: str,
        data: str,
        output_path: str,
        password: Optional[str] = None,
        bits_per_channel: int = 1
    ) -> Tuple[bool, str, dict]:
        """
        Hide data in an image using LSB steganography

        Args:
            image_path: Path to input image
            data: Text data to hide
            output_path: Path for output image (will be PNG)
            password: Optional password for encryption
            bits_per_channel: LSBs to use per channel (1=subtle, 2-4=more capacity)

        Returns:
            Tuple of (success, message, stats_dict)
        """
        try:
            # Load image
            img = Image.open(image_path)
            if img.mode not in ['RGB', 'RGBA']:
                img = img.convert('RGB')

            # Calculate capacity
            capacity = self.calculate_capacity(img, bits_per_channel)

            # Encrypt data if password provided
            if password:
                data_bytes = self._encrypt_data(data, password)
                is_encrypted = True
            else:
                data_bytes = data.encode('utf-8')
                is_encrypted = False

            data_length = len(data_bytes)

            if data_length > capacity:
                return False, f"Data too large! Maximum: {capacity} bytes, Provided: {data_length} bytes", {}

            # Create header: MAGIC + encrypted_flag + length + checksum
            checksum = hashlib.md5(data_bytes).digest()[:8]
            encrypted_flag = b'\x01' if is_encrypted else b'\x00'
            header = self.MAGIC_NUMBER + encrypted_flag + struct.pack('<I', data_length) + checksum

            # Combine header and data
            full_data = header + data_bytes

            # Convert to bit string
            bit_string = ''.join(format(byte, '08b') for byte in full_data)

            # Embed in image
            img_array = np.array(img, dtype=np.uint8)
            flat_array = img_array.flatten()

            bit_index = 0
            for i in range(len(flat_array)):
                if bit_index >= len(bit_string):
                    break

                # Clear LSBs and set new bits
                pixel = flat_array[i]
                for bit in range(bits_per_channel):
                    if bit_index >= len(bit_string):
                        break
                    # Clear bit
                    pixel = (pixel & ~(1 << bit))
                    # Set new bit
                    if bit_string[bit_index] == '1':
                        pixel = pixel | (1 << bit)
                    bit_index += 1

                flat_array[i] = pixel

            # Reshape and save
            steg_img_array = flat_array.reshape(img_array.shape)
            steg_img = Image.fromarray(steg_img_array, img.mode)

            # Save as PNG to preserve data
            steg_img.save(output_path, 'PNG', optimize=False)

            self.last_used = data_length

            stats = {
                'data_size': data_length,
                'capacity': capacity,
                'utilization': f"{(data_length / capacity * 100):.1f}%",
                'encrypted': is_encrypted,
                'bits_per_channel': bits_per_channel,
                'image_size': f"{img.width}x{img.height}"
            }

            return True, f"Successfully embedded {data_length} bytes", stats

        except Exception as e:
            return False, f"Error embedding data: {str(e)}", {}

    def extract_data(
        self,
        image_path: str,
        password: Optional[str] = None,
        bits_per_channel: int = 1
    ) -> Tuple[bool, str, str]:
        """
        Extract hidden data from a steganographic image

        Args:
            image_path: Path to image with hidden data
            password: Password if data is encrypted
            bits_per_channel: LSBs used per channel (must match embedding)

        Returns:
            Tuple of (success, message, extracted_data)
        """
        try:
            # Load image
            img = Image.open(image_path)
            img_array = np.array(img, dtype=np.uint8)
            flat_array = img_array.flatten()

            # Extract header first
            header_bits = (len(self.MAGIC_NUMBER) + 1 + 4 + 8) * 8
            extracted_bits = []

            bit_index = 0
            for i in range(len(flat_array)):
                if bit_index >= header_bits:
                    break
                pixel = flat_array[i]
                for bit in range(bits_per_channel):
                    if bit_index >= header_bits:
                        break
                    extracted_bits.append(str((pixel >> bit) & 1))
                    bit_index += 1

            # Convert bits to bytes
            header_bytes = bytearray()
            for i in range(0, len(extracted_bits), 8):
                byte_bits = ''.join(extracted_bits[i:i+8])
                if len(byte_bits) == 8:
                    header_bytes.append(int(byte_bits, 2))

            # Verify magic number
            magic = bytes(header_bytes[:len(self.MAGIC_NUMBER)])
            if magic != self.MAGIC_NUMBER:
                return False, "No hidden data found (invalid magic number)", ""

            # Parse header
            offset = len(self.MAGIC_NUMBER)
            is_encrypted = header_bytes[offset] == 1
            offset += 1

            data_length = struct.unpack('<I', bytes(header_bytes[offset:offset+4]))[0]
            offset += 4

            stored_checksum = bytes(header_bytes[offset:offset+8])
            offset += 8

            # Extract data
            total_bits_needed = (len(self.MAGIC_NUMBER) + 1 + 4 + 8 + data_length) * 8
            extracted_bits = []

            bit_index = 0
            for i in range(len(flat_array)):
                if bit_index >= total_bits_needed:
                    break
                pixel = flat_array[i]
                for bit in range(bits_per_channel):
                    if bit_index >= total_bits_needed:
                        break
                    extracted_bits.append(str((pixel >> bit) & 1))
                    bit_index += 1

            # Convert to bytes
            data_bytes = bytearray()
            for i in range(0, len(extracted_bits), 8):
                byte_bits = ''.join(extracted_bits[i:i+8])
                if len(byte_bits) == 8:
                    data_bytes.append(int(byte_bits, 2))

            # Skip header and get data
            data_bytes = bytes(data_bytes[offset:offset+data_length])

            # Verify checksum
            calculated_checksum = hashlib.md5(data_bytes).digest()[:8]
            if calculated_checksum != stored_checksum:
                return False, "Data corruption detected (checksum mismatch)", ""

            # Decrypt if needed
            if is_encrypted:
                if not password:
                    return False, "Data is encrypted but no password provided", ""
                try:
                    data_str = self._decrypt_data(data_bytes, password)
                except Exception as e:
                    return False, f"Decryption failed (wrong password?): {str(e)}", ""
            else:
                data_str = data_bytes.decode('utf-8', errors='replace')

            return True, f"Successfully extracted {data_length} bytes", data_str

        except Exception as e:
            return False, f"Error extracting data: {str(e)}", ""


def main():
    """Command-line interface for testing"""
    import argparse

    parser = argparse.ArgumentParser(description='LSB Steganography Tool')
    parser.add_argument('mode', choices=['embed', 'extract'], help='Operation mode')
    parser.add_argument('image', help='Input image path')
    parser.add_argument('--data', help='Data to embed (for embed mode)')
    parser.add_argument('--output', help='Output image path (for embed mode)')
    parser.add_argument('--password', help='Encryption password (optional)')
    parser.add_argument('--bits', type=int, default=1, help='Bits per channel (1-4)')

    args = parser.parse_args()

    embedder = StegEmbedder()

    if args.mode == 'embed':
        if not args.data or not args.output:
            print("Error: --data and --output required for embed mode")
            return

        success, message, stats = embedder.embed_data(
            args.image, args.data, args.output, args.password, args.bits
        )
        print(message)
        if success:
            print(f"Stats: {stats}")

    elif args.mode == 'extract':
        success, message, data = embedder.extract_data(
            args.image, args.password, args.bits
        )
        print(message)
        if success:
            print(f"Extracted data:\n{data}")


if __name__ == '__main__':
    main()
