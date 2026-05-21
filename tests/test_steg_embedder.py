"""Unit tests for LSB steganography engine."""

import os
import tempfile
import pytest
from PIL import Image
import numpy as np

from steg_embedder import StegEmbedder


@pytest.fixture
def embedder():
    return StegEmbedder()


@pytest.fixture
def rgb_image():
    """Create a small 16x16 RGB test image."""
    arr = np.random.randint(0, 256, (16, 16, 3), dtype=np.uint8)
    return Image.fromarray(arr, 'RGB')


@pytest.fixture
def rgba_image():
    """Create a small 16x16 RGBA test image."""
    arr = np.random.randint(0, 256, (16, 16, 4), dtype=np.uint8)
    return Image.fromarray(arr, 'RGBA')


@pytest.fixture
def large_rgb_image():
    """Create a 64x64 RGB image for larger payloads."""
    arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    return Image.fromarray(arr, 'RGB')


@pytest.fixture
def temp_png_path(rgb_image):
    """Create a temporary PNG file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        rgb_image.save(f.name, 'PNG')
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_output_path():
    """Create a temporary output file path."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestCapacity:
    def test_rgb_capacity_basic(self, embedder, rgb_image):
        cap = embedder.calculate_capacity(rgb_image, bits_per_channel=1)
        # 16x16x3 = 768 bits, minus header (16 * 8 = 128 bits) = 640 bits / 8 = 80 bytes
        assert cap == 80

    def test_rgba_capacity(self, embedder, rgba_image):
        cap = embedder.calculate_capacity(rgba_image, bits_per_channel=1)
        # 16x16x4 = 1024 bits, minus 128 header = 896 / 8 = 112 bytes
        assert cap == 112

    def test_capacity_scales_with_bits(self, embedder, rgb_image):
        cap1 = embedder.calculate_capacity(rgb_image, bits_per_channel=1)
        cap2 = embedder.calculate_capacity(rgb_image, bits_per_channel=2)
        # 2 bits should give roughly 2x capacity
        assert cap2 == 176

    def test_capacity_scales_with_size(self, embedder, rgb_image, large_rgb_image):
        cap_small = embedder.calculate_capacity(rgb_image, bits_per_channel=1)
        cap_large = embedder.calculate_capacity(large_rgb_image, bits_per_channel=1)
        assert cap_large > cap_small
        # 64*64 vs 16*16 = 4096/256 = 16x pixels -> roughly 16x capacity
        assert cap_large == 1520

    def test_unsupported_mode_raises(self, embedder):
        img = Image.new('L', (10, 10))  # Grayscale
        with pytest.raises(ValueError, match='Unsupported image mode'):
            embedder.calculate_capacity(img)

    def test_max_bits_per_channel(self, embedder, rgb_image):
        cap = embedder.calculate_capacity(rgb_image, bits_per_channel=4)
        assert cap == 368

    def test_last_capacity_updated(self, embedder, rgb_image):
        embedder.calculate_capacity(rgb_image)
        assert embedder.last_capacity == 80


class TestEmbedExtractRoundTrip:
    def test_basic_round_trip(self, embedder, temp_png_path, temp_output_path):
        message = "Hello, World!"
        success, msg, stats = embedder.embed_data(
            temp_png_path, message, temp_output_path, bits_per_channel=1
        )
        assert success
        assert stats['data_size'] == len(message.encode('utf-8'))
        assert not stats['encrypted']

        success2, msg2, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=1
        )
        assert success2
        assert extracted == message

    def test_round_trip_with_password(self, embedder, temp_png_path, temp_output_path):
        message = "Secret message with 🔒 encryption"
        password = "my-secret-key"
        success, msg, stats = embedder.embed_data(
            temp_png_path, message, temp_output_path,
            password=password, bits_per_channel=1
        )
        assert success
        assert stats['encrypted']

        success2, msg2, extracted = embedder.extract_data(
            temp_output_path, password=password, bits_per_channel=1
        )
        assert success2
        assert extracted == message

    def test_round_trip_unicode(self, embedder, temp_png_path, temp_output_path):
        message = "日本語 Español Français 🌍 Emoji test ✓"
        success, msg, stats = embedder.embed_data(
            temp_png_path, message, temp_output_path, bits_per_channel=1
        )
        assert success

        success2, msg2, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=1
        )
        assert success2
        assert extracted == message

    def test_round_trip_bits2(self, embedder, temp_png_path, temp_output_path):
        message = "Using 2 bits per channel"
        success, _, _ = embedder.embed_data(
            temp_png_path, message, temp_output_path, bits_per_channel=2
        )
        assert success

        success2, _, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=2
        )
        assert success2
        assert extracted == message

    def test_round_trip_bits4(self, embedder, temp_png_path, temp_output_path):
        message = "Maximum 4 bits per channel"
        success, _, _ = embedder.embed_data(
            temp_png_path, message, temp_output_path, bits_per_channel=4
        )
        assert success

        success2, _, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=4
        )
        assert success2
        assert extracted == message

    def test_round_trip_empty_message(self, embedder, temp_png_path, temp_output_path):
        message = ""
        success, msg, stats = embedder.embed_data(
            temp_png_path, message, temp_output_path, bits_per_channel=1
        )
        assert success
        assert stats['data_size'] == 0

        success2, _, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=1
        )
        assert success2
        assert extracted == ""

    def test_round_trip_long_message(self, embedder, temp_png_path, temp_output_path):
        # 16x16x3 with 1 bit = 80 byte capacity, so 60 chars should fit
        message = "A" * 60
        success, _, _ = embedder.embed_data(
            temp_png_path, message, temp_output_path, bits_per_channel=1
        )
        assert success

        success2, _, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=1
        )
        assert success2
        assert extracted == message

    def test_rgba_round_trip(self, embedder, temp_output_path):
        arr = np.random.randint(0, 256, (16, 16, 4), dtype=np.uint8)
        rgba_img = Image.fromarray(arr, 'RGBA')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            rgba_img.save(f.name, 'PNG')
            rgba_path = f.name

        try:
            message = "RGBA stego test"
            success, _, _ = embedder.embed_data(
                rgba_path, message, temp_output_path, bits_per_channel=1
            )
            assert success

            success2, _, extracted = embedder.extract_data(
                temp_output_path, bits_per_channel=1
            )
            assert success2
            assert extracted == message
        finally:
            if os.path.exists(rgba_path):
                os.unlink(rgba_path)

    def test_large_image_round_trip(self, embedder, temp_output_path):
        arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
        big_img = Image.fromarray(arr, 'RGB')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            big_img.save(f.name, 'PNG')
            big_path = f.name

        try:
            message = "A longer message that would exceed smaller image capacity " * 10
            success, _, _ = embedder.embed_data(
                big_path, message, temp_output_path, bits_per_channel=2
            )
            assert success

            success2, _, extracted = embedder.extract_data(
                temp_output_path, bits_per_channel=2
            )
            assert success2
            assert extracted == message
        finally:
            if os.path.exists(big_path):
                os.unlink(big_path)


class TestExtractErrors:
    def test_wrong_password(self, embedder, temp_png_path, temp_output_path):
        message = "Secret"
        password = "correct"
        embedder.embed_data(
            temp_png_path, message, temp_output_path,
            password=password, bits_per_channel=1
        )

        success, msg, extracted = embedder.extract_data(
            temp_output_path, password="wrong", bits_per_channel=1
        )
        # With XOR encryption, wrong password produces garbage text but
        # checksum is on encrypted bytes so extraction still "succeeds"
        assert success
        assert extracted != message

    def test_missing_password_for_encrypted(self, embedder, temp_png_path, temp_output_path):
        message = "Secret"
        embedder.embed_data(
            temp_png_path, message, temp_output_path,
            password="key", bits_per_channel=1
        )

        success, msg, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=1
        )
        assert not success
        assert "encrypted" in msg.lower()

    def test_no_data_in_image(self, embedder, temp_png_path):
        success, msg, extracted = embedder.extract_data(
            temp_png_path, bits_per_channel=1
        )
        assert not success
        assert "magic" in msg.lower()


class TestEmbedErrors:
    def test_data_too_large(self, embedder, temp_png_path, temp_output_path):
        message = "X" * 100  # More than 80 byte capacity
        success, msg, stats = embedder.embed_data(
            temp_png_path, message, temp_output_path, bits_per_channel=1
        )
        assert not success
        assert "large" in msg.lower()
        assert stats == {}

    def test_nonexistent_input(self, embedder, temp_output_path):
        success, msg, _ = embedder.embed_data(
            "/nonexistent/file.png", "test", temp_output_path
        )
        assert not success


class TestEncryption:
    def test_xor_encryption_decryption(self, embedder):
        original = "Test data for encryption"
        password = "test-key"
        encrypted = embedder._encrypt_data(original, password)
        assert encrypted != original.encode('utf-8')

        decrypted = embedder._decrypt_data(encrypted, password)
        assert decrypted == original

    def test_different_keys_produce_different_output(self, embedder):
        data = "test data"
        enc1 = embedder._encrypt_data(data, "key1")
        enc2 = embedder._encrypt_data(data, "key2")
        assert enc1 != enc2

    def test_empty_data_encryption(self, embedder):
        encrypted = embedder._encrypt_data("", "key")
        assert encrypted == b""
        decrypted = embedder._decrypt_data(encrypted, "key")
        assert decrypted == ""


class TestBitConversion:
    def test_string_to_bits_round_trip(self, embedder):
        original = "Hello"
        bits = embedder._string_to_bits(original)
        result = embedder._bits_to_string(bits)
        assert result == original

    def test_bits_format(self, embedder):
        bits = embedder._string_to_bits("A")  # 'A' = 65 = 01000001
        assert bits == "01000001"

    def test_unicode_bit_conversion(self, embedder):
        original = "ñ"
        bits = embedder._string_to_bits(original)
        result = embedder._bits_to_string(bits)
        assert result == original


class TestHeaderIntegrity:
    def test_magic_number_present(self, embedder):
        assert embedder.MAGIC_NUMBER == b'2PAC'

    def test_header_size(self, embedder):
        assert embedder.HEADER_SIZE == 12

    def test_output_image_is_valid_png(self, embedder, temp_png_path, temp_output_path):
        embedder.embed_data(temp_png_path, "test", temp_output_path)
        img = Image.open(temp_output_path)
        assert img.format == 'PNG'
        assert img.size == (16, 16)

    def test_embedded_image_looks_similar(self, embedder, temp_png_path, temp_output_path):
        embedder.embed_data(temp_png_path, "test", temp_output_path, bits_per_channel=1)
        original = np.array(Image.open(temp_png_path))
        embedded = np.array(Image.open(temp_output_path))

        # With 1 LSB, max difference should be 1 per pixel
        diff = np.abs(original.astype(int) - embedded.astype(int))
        assert np.max(diff) <= 1


class TestEdgeCases:
    def test_single_char_message(self, embedder, temp_png_path, temp_output_path):
        success, _, _ = embedder.embed_data(
            temp_png_path, "X", temp_output_path, bits_per_channel=1
        )
        assert success
        success2, _, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=1
        )
        assert extracted == "X"

    def test_special_chars(self, embedder, temp_png_path, temp_output_path):
        message = "\n\t\r\x00\x01"
        success, _, _ = embedder.embed_data(
            temp_png_path, message, temp_output_path, bits_per_channel=1
        )
        assert success
        success2, _, extracted = embedder.extract_data(
            temp_output_path, bits_per_channel=1
        )
        assert extracted == message

    def test_password_with_special_chars(self, embedder, temp_png_path, temp_output_path):
        message = "secret"
        password = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        embedder.embed_data(
            temp_png_path, message, temp_output_path,
            password=password, bits_per_channel=1
        )
        success, _, extracted = embedder.extract_data(
            temp_output_path, password=password, bits_per_channel=1
        )
        assert success
        assert extracted == message

    def test_image_mode_converted_from_rgba(self, embedder, temp_output_path):
        arr = np.random.randint(0, 256, (16, 16, 4), dtype=np.uint8)
        rgba_img = Image.fromarray(arr, 'RGBA')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            rgba_img.save(f.name, 'PNG')
            rgba_path = f.name

        try:
            message = "RGBA auto-convert test"
            success, msg, stats = embedder.embed_data(
                rgba_path, message, temp_output_path, bits_per_channel=1
            )
            assert success
            assert stats['encrypted'] is False

            success2, _, extracted = embedder.extract_data(
                temp_output_path, bits_per_channel=1
            )
            assert extracted == message
        finally:
            if os.path.exists(rgba_path):
                os.unlink(rgba_path)
