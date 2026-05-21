"""
DCT-based steganography for 2PAC.

Hides data in mid-frequency DCT coefficients by modifying coefficient
parity with a large step to survive DCT/IDCT cross-interference.
Much harder to detect than pixel-level LSB steganography.
"""

import hashlib
import struct
from typing import Tuple, Optional

import numpy as np
from PIL import Image
from scipy.fftpack import dct, idct


JPEG_LUM_QUANT = np.array([
    [16, 11, 10, 16,  24,  40,  51,  61],
    [12, 12, 14, 19,  26,  58,  60,  55],
    [14, 13, 16, 24,  40,  57,  69,  56],
    [14, 17, 22, 29,  51,  87,  80,  62],
    [18, 22, 37, 56,  68, 109, 103,  77],
    [24, 35, 55, 64,  81, 104, 113,  92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103,  99],
], dtype=np.float32)

MAGIC_NUMBER = b'DPAC'
HEADER_SIZE = 12
PARITY_STEP = 3
MAX_CORRECTIONS = 5
SAFE_MARGIN = 4  # Coefficients with |val| < this are unstable after roundtrip


def _dct2d(block):
    return dct(dct(block.T, type=2, norm='ortho').T, type=2, norm='ortho')


def _idct2d(block):
    return idct(idct(block.T, type=2, norm='ortho').T, type=2, norm='ortho')


class DctStegEmbedder:
    """
    DCT-based steganography using coefficient parity.

    Embeds data in mid-frequency DCT coefficients of the green channel
    by enforcing parity (even=0, odd=1) with a large modification step
    to withstand DCT/IDCT rounding errors.
    """

    def __init__(self, quality: int = 85):
        self.quality = quality
        self.last_capacity = 0

    def _usable_positions(self):
        """Single coefficient per block for zero cross-interference."""
        return [(1, 2)]

    def calculate_capacity(self, image: Image.Image) -> int:
        width, height = image.size
        blocks_x = width // 8
        blocks_y = height // 8
        if blocks_x < 1 or blocks_y < 1:
            return 0

        total_blocks = blocks_x * blocks_y
        positions_per_block = len(self._usable_positions())
        total_bits = total_blocks * positions_per_block
        header_bits = (len(MAGIC_NUMBER) + HEADER_SIZE) * 8
        capacity = max(0, (total_bits - header_bits) // 8)
        self.last_capacity = capacity
        return capacity

    def embed_data(
        self,
        image_path: str,
        data: str,
        output_path: str,
        password: Optional[str] = None,
    ) -> Tuple[bool, str, dict]:
        try:
            img = Image.open(image_path)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            width, height = img.size
            blocks_x = width // 8
            blocks_y = height // 8

            if blocks_x < 1 or blocks_y < 1:
                return False, "Image too small (minimum 8x8 pixels)", {}

            r_ch, g, b_ch = img.split()
            g_arr = np.array(g, dtype=np.float32)

            if password:
                data_bytes = self._encrypt_data(data, password)
                is_encrypted = True
            else:
                data_bytes = data.encode('utf-8')
                is_encrypted = False

            data_length = len(data_bytes)

            checksum = hashlib.md5(data_bytes).digest()[:8]
            encrypted_flag = b'\x01' if is_encrypted else b'\x00'
            header = MAGIC_NUMBER + encrypted_flag + struct.pack('<I', data_length) + checksum
            full_data = header + data_bytes
            bit_string = ''.join(format(byte, '08b') for byte in full_data)

            usable = self._usable_positions()
            bits_per_block = len(usable)
            total_blocks = blocks_x * blocks_y
            needed_blocks = (len(bit_string) + bits_per_block - 1) // bits_per_block

            if needed_blocks > total_blocks:
                return False, (
                    f"Data too large! Need {len(bit_string)} bits "
                    f"({needed_blocks} blocks) but only {total_blocks} blocks available"
                ), {}

            g_blocks = self._split_into_blocks(g_arr, blocks_x, blocks_y)
            quant = self._make_quant_table()

            bit_idx = 0
            embedded_blocks = 0

            for by in range(blocks_y):
                for bx in range(blocks_x):
                    if bit_idx >= len(bit_string):
                        break

                    block = g_blocks[by][bx]
                    block_bits = []
                    block_targets = []
                    for r, c in usable:
                        if bit_idx + len(block_bits) >= len(bit_string):
                            break
                        block_targets.append(int(bit_string[bit_idx + len(block_bits)]))
                        block_bits.append(None)

                    if not block_targets:
                        continue

                    num_block_bits = len(block_targets)
                    correction_attempt = 0

                    while correction_attempt < MAX_CORRECTIONS:
                        dct_block = _dct2d(block - 128)
                        quantized = np.round(dct_block / quant)
                        step = PARITY_STEP + correction_attempt

                        all_stable = True
                        for i, (ur, uc) in enumerate(usable[:num_block_bits]):
                            target = block_targets[i]
                            val = int(quantized[ur, uc])
                            current_parity = abs(val) & 1
                            if current_parity != target:
                                all_stable = False
                                if val >= 0:
                                    quantized[ur, uc] = val + step
                                else:
                                    quantized[ur, uc] = val - step
                            elif abs(val) < SAFE_MARGIN:
                                all_stable = False
                                if val >= 0:
                                    quantized[ur, uc] = val + 2
                                else:
                                    quantized[ur, uc] = val - 2

                        if all_stable:
                            break

                        dequantized = quantized * quant
                        spatial = _idct2d(dequantized) + 128
                        spatial = np.clip(spatial, 0, 255)
                        block = spatial
                        correction_attempt += 1

                    g_blocks[by][bx] = block
                    bit_idx += num_block_bits
                    embedded_blocks += 1

                if bit_idx >= len(bit_string):
                    break

            g_out = self._merge_blocks(g_blocks, blocks_x, blocks_y, height, width)
            g_out = g_out.astype(np.uint8)

            g_img = Image.fromarray(g_out, 'L')
            out_rgb = Image.merge('RGB', (r_ch, g_img, b_ch))
            out_rgb.save(output_path, 'PNG')

            self.last_used = data_length

            stats = {
                'data_size': data_length,
                'capacity': self.last_capacity,
                'utilization': (
                    f"{(data_length / self.last_capacity * 100):.1f}%"
                    if self.last_capacity > 0 else "N/A"
                ),
                'encrypted': is_encrypted,
                'blocks_used': embedded_blocks,
                'total_blocks': total_blocks,
                'image_size': f"{width}x{height}",
            }

            return True, f"Successfully embedded {data_length} bytes in DCT coefficients", stats

        except Exception as e:
            return False, f"Error embedding data: {str(e)}", {}

    def extract_data(
        self,
        image_path: str,
        password: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        try:
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            width, height = img.size
            blocks_x = width // 8
            blocks_y = height // 8

            _, g, _ = img.split()
            g_arr = np.array(g, dtype=np.float32)
            g_blocks = self._split_into_blocks(g_arr, blocks_x, blocks_y)
            quant = self._make_quant_table()
            usable = self._usable_positions()

            header_bits_needed = (len(MAGIC_NUMBER) + 1 + 4 + 8) * 8
            header_bits = self._extract_bits(
                g_blocks, blocks_x, blocks_y, quant, usable, header_bits_needed
            )

            header_bytes = self._bits_to_bytes(header_bits)

            magic = bytes(header_bytes[:len(MAGIC_NUMBER)])
            if magic != MAGIC_NUMBER:
                return False, "No hidden data found (invalid magic number)", ""

            offset = len(MAGIC_NUMBER)
            is_encrypted = header_bytes[offset] == 1
            offset += 1

            data_length = struct.unpack('<I', bytes(header_bytes[offset:offset+4]))[0]
            offset += 4

            stored_checksum = bytes(header_bytes[offset:offset+8])

            if data_length < 0 or data_length > 10_000_000:
                return False, "Invalid data length in header", ""

            total_bits_needed = (len(MAGIC_NUMBER) + 1 + 4 + 8 + data_length) * 8
            all_bits = self._extract_bits(
                g_blocks, blocks_x, blocks_y, quant, usable, total_bits_needed
            )

            all_bytes = self._bits_to_bytes(all_bits)
            offset = len(MAGIC_NUMBER) + 1 + 4 + 8
            data_bytes = bytes(all_bytes[offset:offset+data_length])

            if len(data_bytes) != data_length:
                return False, "Incomplete data extraction (truncated image)", ""

            calculated_checksum = hashlib.md5(data_bytes).digest()[:8]
            if calculated_checksum != stored_checksum:
                return False, "Data corruption detected (checksum mismatch)", ""

            if is_encrypted:
                if not password:
                    return False, "Data is encrypted but no password provided", ""
                try:
                    data_str = self._decrypt_data(data_bytes, password)
                except Exception as e:
                    return False, f"Decryption failed: {str(e)}", ""
            else:
                data_str = data_bytes.decode('utf-8', errors='replace')

            return True, f"Successfully extracted {data_length} bytes", data_str

        except Exception as e:
            return False, f"Error extracting data: {str(e)}", ""

    def _extract_bits(self, g_blocks, blocks_x, blocks_y, quant, usable, num_bits):
        bits = []
        for by in range(blocks_y):
            for bx in range(blocks_x):
                if len(bits) >= num_bits:
                    break
                block = g_blocks[by][bx]
                dct_block = _dct2d(block - 128)
                quantized = np.round(dct_block / quant)

                for r, c in usable:
                    if len(bits) >= num_bits:
                        break
                    val = int(quantized[r, c])
                    bits.append(str(abs(val) & 1))

                if len(bits) >= num_bits:
                    break
            if len(bits) >= num_bits:
                break
        return bits

    @staticmethod
    def _bits_to_bytes(bits):
        result = bytearray()
        for i in range(0, len(bits), 8):
            byte_bits = ''.join(bits[i:i+8])
            if len(byte_bits) == 8:
                result.append(int(byte_bits, 2))
        return result

    def _split_into_blocks(self, arr, blocks_x, blocks_y):
        blocks = []
        for by in range(blocks_y):
            row = []
            for bx in range(blocks_x):
                block = arr[by*8:(by+1)*8, bx*8:(bx+1)*8]
                row.append(block.copy())
            blocks.append(row)
        return blocks

    def _merge_blocks(self, blocks, blocks_x, blocks_y, height, width):
        result = np.zeros((blocks_y * 8, blocks_x * 8), dtype=np.float32)
        for by in range(blocks_y):
            for bx in range(blocks_x):
                result[by*8:(by+1)*8, bx*8:(bx+1)*8] = blocks[by][bx]
        return result[:height, :width]

    def _make_quant_table(self):
        if self.quality >= 50:
            scale = (100 - self.quality) / 50.0
        else:
            scale = 50.0 / self.quality
        q = JPEG_LUM_QUANT * scale
        q[q < 1] = 1
        return q

    def _encrypt_data(self, data: str, password: str) -> bytes:
        key = hashlib.sha256(password.encode()).digest()
        data_bytes = data.encode('utf-8')
        encrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key[i % len(key)])
        return bytes(encrypted)

    def _decrypt_data(self, encrypted_data: bytes, password: str) -> str:
        key = hashlib.sha256(password.encode()).digest()
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_data):
            decrypted.append(byte ^ key[i % len(key)])
        return bytes(decrypted).decode('utf-8', errors='replace')
