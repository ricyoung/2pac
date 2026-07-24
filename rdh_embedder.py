#!/usr/bin/env python3
"""
Reversible Data Hiding (RDH) Embedder for 2PAC

Hides and extracts data in images using histogram shifting on the green
channel.  Unlike LSB steganography, RDH is *lossless*: after the hidden
data is extracted the original image can be perfectly restored.

Algorithm (histogram shifting):
  1. Build the histogram of the green channel.
  2. Find the *peak* (most frequent pixel value) and *zero* (least
     frequent pixel value).
  3. Shift every histogram bin between peak and zero by ±1 to create a
     one-pixel gap next to the peak.
  4. Embed data bits at peak-value pixels: bit 1 → shift the pixel into
     the gap; bit 0 → leave it unchanged.
  5. Extraction reads the peak / gap pixels, then reverses the histogram
     shift to recover the original image exactly.

Peak and zero values are stored in PNG text metadata so the extractor
can locate the embedded bits without access to the original image.
"""

import hashlib
import struct
from typing import Optional, Tuple

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo


class RdhEmbedder:
    """Reversible Data Hiding via histogram shifting (green channel)."""

    MAGIC_NUMBER = b'RPAC'
    # Header layout in the bit-stream:
    #   MAGIC (4 B) | encrypted_flag (1 B) | data_length (4 B LE) | checksum (8 B)
    HEADER_SIZE = 12  # data_length (4) + checksum (8)
    _HEADER_BYTES = 4 + 1 + 4 + 8  # magic + flag + length + checksum = 17
    _HEADER_BITS = _HEADER_BYTES * 8  # 136

    def __init__(self):
        self.last_capacity: int = 0
        self.last_used: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_capacity(self, image: Image.Image) -> int:
        """Return the maximum payload size in bytes for *image*.

        Capacity equals the number of peak-value pixels in the green
        channel minus the header overhead, divided by 8.
        """
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')

        green = np.array(image, dtype=np.uint8)[:, :, 1]
        hist = np.bincount(green.ravel(), minlength=256)
        peak_count = int(hist.max())

        capacity = max(0, (peak_count - self._HEADER_BITS) // 8)
        self.last_capacity = capacity
        return capacity

    def embed_data(
        self,
        image_path: str,
        data: str,
        output_path: str,
        password: Optional[str] = None,
    ) -> Tuple[bool, str, dict]:
        """Embed *data* into the image at *image_path* using RDH.

        Returns ``(success, message, stats_dict)``.
        """
        try:
            img = Image.open(image_path)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')

            img_array = np.array(img, dtype=np.uint8)
            green = img_array[:, :, 1].copy()

            # --- locate peak / zero ------------------------------------
            peak, zero = self._find_peak_zero(green)
            if peak == zero:
                return False, "Image has no histogram variance; cannot embed", {}

            peak_count = int(np.sum(green == peak))
            capacity = max(0, (peak_count - self._HEADER_BITS) // 8)

            # --- prepare payload ---------------------------------------
            if password:
                data_bytes = self._encrypt_data(data, password)
                is_encrypted = True
            else:
                data_bytes = data.encode('utf-8')
                is_encrypted = False

            data_length = len(data_bytes)
            if data_length > capacity:
                return (
                    False,
                    f"Data too large! Maximum: {capacity} bytes, "
                    f"Provided: {data_length} bytes",
                    {},
                )

            checksum = hashlib.md5(data_bytes).digest()[:8]
            encrypted_flag = b'\x01' if is_encrypted else b'\x00'
            header = (
                self.MAGIC_NUMBER
                + encrypted_flag
                + struct.pack('<I', data_length)
                + checksum
            )
            full_payload = header + data_bytes
            bit_string = ''.join(format(b, '08b') for b in full_payload)

            # --- histogram shift + embedding ---------------------------
            self._shift_histogram(green, peak, zero)
            self._embed_bits(green, peak, zero, bit_string)

            # --- save --------------------------------------------------
            img_array[:, :, 1] = green
            out_img = Image.fromarray(img_array, img.mode)

            meta = PngInfo()
            meta.add_text('rdh_peak', str(peak))
            meta.add_text('rdh_zero', str(zero))
            out_img.save(output_path, 'PNG', pnginfo=meta)

            self.last_used = data_length
            stats = {
                'data_size': data_length,
                'capacity': capacity,
                'utilization': f"{data_length / capacity * 100:.1f}%"
                if capacity
                else "0.0%",
                'encrypted': is_encrypted,
                'peak': peak,
                'zero': zero,
                'image_size': f"{img.width}x{img.height}",
            }
            return True, f"Successfully embedded {data_length} bytes", stats

        except Exception as exc:
            return False, f"Error embedding data: {exc}", {}

    def extract_data(
        self,
        image_path: str,
        password: Optional[str] = None,
        restore_path: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        """Extract hidden data from an RDH stego image.

        If *restore_path* is given the perfectly restored image is also
        written there (the key reversibility guarantee of RDH).

        Returns ``(success, message, extracted_data)``.
        """
        try:
            img = Image.open(image_path)

            # Read side-information from PNG metadata
            try:
                peak = int(img.text['rdh_peak'])
                zero = int(img.text['rdh_zero'])
            except (KeyError, TypeError, ValueError):
                return False, "No RDH data found (missing metadata)", ""

            img_array = np.array(img, dtype=np.uint8)
            green = img_array[:, :, 1].copy()

            # --- extract bits ------------------------------------------
            total_bits_needed = self._HEADER_BITS  # start with header
            bit_string = self._extract_bits(green, peak, zero, total_bits_needed)

            if len(bit_string) < self._HEADER_BITS:
                return False, "Not enough peak pixels to read header", ""

            # Parse header
            header_bytes = self._bits_to_bytes(bit_string[: self._HEADER_BITS])
            magic = bytes(header_bytes[:4])
            if magic != self.MAGIC_NUMBER:
                return False, "No hidden data found (invalid magic number)", ""

            offset = 4
            is_encrypted = header_bytes[offset] == 1
            offset += 1
            data_length = struct.unpack(
                '<I', bytes(header_bytes[offset : offset + 4])
            )[0]
            offset += 4
            stored_checksum = bytes(header_bytes[offset : offset + 8])

            # Now extract the full payload (header + data)
            total_bits_needed = (self._HEADER_BYTES + data_length) * 8
            bit_string = self._extract_bits(green, peak, zero, total_bits_needed)

            all_bytes = self._bits_to_bytes(bit_string)
            data_bytes = bytes(
                all_bytes[self._HEADER_BYTES : self._HEADER_BYTES + data_length]
            )

            # Verify checksum
            if hashlib.md5(data_bytes).digest()[:8] != stored_checksum:
                return False, "Data corruption detected (checksum mismatch)", ""

            # --- reverse histogram shift (restore image) ----------------
            self._reverse_shift(green, peak, zero)

            if restore_path:
                img_array[:, :, 1] = green
                restored = Image.fromarray(img_array, img.mode)
                restored.save(restore_path, 'PNG')

            # --- decrypt / decode --------------------------------------
            if is_encrypted:
                if not password:
                    return (
                        False,
                        "Data is encrypted but no password provided",
                        "",
                    )
                try:
                    data_str = self._decrypt_data(data_bytes, password)
                except Exception as exc:
                    return (
                        False,
                        f"Decryption failed (wrong password?): {exc}",
                        "",
                    )
            else:
                data_str = data_bytes.decode('utf-8', errors='replace')

            return True, f"Successfully extracted {data_length} bytes", data_str

        except Exception as exc:
            return False, f"Error extracting data: {exc}", ""

    # ------------------------------------------------------------------
    # Histogram helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_peak_zero(green: np.ndarray) -> Tuple[int, int]:
        """Return ``(peak, zero)`` pixel values for histogram shifting.

        *peak* is the most frequent value.  *zero* is a value with
        **exactly 0 pixels** on whichever side of the peak allows a
        valid shift (i.e. won't push pixel values outside 0-255).
        A true zero-count bin is required for perfect reversibility.
        If no such bin exists, returns ``(peak, peak)`` → capacity 0.
        """
        hist = np.bincount(green.ravel(), minlength=256)
        peak = int(np.argmax(hist))

        # Candidate on the right: zero > peak, need zero <= 254
        right_zero: Optional[int] = None
        if peak < 254:
            candidates = np.where(hist[peak + 1 : 255] == 0)[0]
            if len(candidates) > 0:
                right_zero = peak + 1 + int(candidates[0])

        # Candidate on the left: zero < peak, need zero >= 1
        left_zero: Optional[int] = None
        if peak > 1:
            candidates = np.where(hist[1:peak] == 0)[0]
            if len(candidates) > 0:
                # Pick the one closest to peak for minimal shift distance
                left_zero = 1 + int(candidates[-1])

        if right_zero is not None and left_zero is not None:
            # Prefer the closer zero point (less histogram distortion)
            if (right_zero - peak) <= (peak - left_zero):
                return peak, right_zero
            return peak, left_zero
        if right_zero is not None:
            return peak, right_zero
        if left_zero is not None:
            return peak, left_zero

        # No zero-count bin found → cannot guarantee reversibility
        return peak, peak

    @staticmethod
    def _shift_histogram(green: np.ndarray, peak: int, zero: int) -> None:
        """Shift histogram bins between *peak* and *zero* to create a gap.

        Mutates *green* in place.
        """
        if zero > peak:
            # Shift bins (peak, zero] up by 1 → gap at peak+1
            # Process from high to low to avoid double-shifting.
            for v in range(zero, peak, -1):
                green[green == v] = v + 1
        else:
            # Shift bins [zero, peak) down by 1 → gap at peak-1
            # Process from low to high to avoid double-shifting.
            for v in range(zero, peak):
                green[green == v] = v - 1

    @staticmethod
    def _embed_bits(
        green: np.ndarray, peak: int, zero: int, bit_string: str
    ) -> None:
        """Embed *bit_string* into peak-value pixels of *green* (in place).

        bit 1 → shift pixel into the gap (peak±1); bit 0 → leave as-is.
        Pixels are scanned in row-major (C) order.
        """
        gap = peak + 1 if zero > peak else peak - 1
        flat = green.ravel()
        bit_idx = 0
        for i in range(flat.size):
            if bit_idx >= len(bit_string):
                break
            if flat[i] == peak:
                if bit_string[bit_idx] == '1':
                    flat[i] = gap
                bit_idx += 1

    @staticmethod
    def _extract_bits(
        green: np.ndarray, peak: int, zero: int, count: int
    ) -> str:
        """Read up to *count* bits from peak / gap pixels (row-major)."""
        gap = peak + 1 if zero > peak else peak - 1
        flat = green.ravel()
        bits: list[str] = []
        for i in range(flat.size):
            if len(bits) >= count:
                break
            if flat[i] == peak:
                bits.append('0')
            elif flat[i] == gap:
                bits.append('1')
        return ''.join(bits)

    @staticmethod
    def _reverse_shift(green: np.ndarray, peak: int, zero: int) -> None:
        """Undo the histogram shift **and** the embedding, restoring the
        original pixel values.  Mutates *green* in place.

        Order matters:
        1. Move gap pixels back to peak (undo embedding).
        2. Shift the displaced bins back (undo histogram shift).

        The loop ranges deliberately exclude the far boundary (zero ± 1)
        because the zero-count bin contributed no pixels during the
        forward shift, so the neighbouring bin is untouched.
        """
        if zero > peak:
            # gap = peak+1; displaced bins are peak+2 .. zero
            green[green == peak + 1] = peak
            for v in range(peak + 2, zero + 1):
                green[green == v] = v - 1
        else:
            # gap = peak-1; displaced bins are zero .. peak-2
            green[green == peak - 1] = peak
            for v in range(peak - 2, zero - 1, -1):
                green[green == v] = v + 1

    # ------------------------------------------------------------------
    # Encryption (same XOR scheme as StegEmbedder)
    # ------------------------------------------------------------------

    @staticmethod
    def _encrypt_data(data: str, password: str) -> bytes:
        """XOR-encrypt *data* with a SHA-256-derived key."""
        key = hashlib.sha256(password.encode()).digest()
        data_bytes = data.encode('utf-8')
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data_bytes))

    @staticmethod
    def _decrypt_data(encrypted_data: bytes, password: str) -> str:
        """Decrypt XOR-encrypted data."""
        key = hashlib.sha256(password.encode()).digest()
        decrypted = bytes(
            b ^ key[i % len(key)] for i, b in enumerate(encrypted_data)
        )
        return decrypted.decode('utf-8', errors='replace')

    # ------------------------------------------------------------------
    # Bit / byte helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bits_to_bytes(bit_string: str) -> bytearray:
        out = bytearray()
        for i in range(0, len(bit_string), 8):
            chunk = bit_string[i : i + 8]
            if len(chunk) == 8:
                out.append(int(chunk, 2))
        return out
