"""Unit tests for the Reversible Data Hiding (RDH) embedder."""

import os
import tempfile

import numpy as np
import pytest
from PIL import Image

from rdh_embedder import RdhEmbedder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def embedder():
    return RdhEmbedder()


def _make_rdh_image(size: int, peak_value: int = 128, peak_fraction: float = 0.5):
    """Create an RGB image whose green channel has a strong histogram peak
    and guaranteed empty bins above the peak (required for RDH reversibility).

    A controlled peak gives predictable RDH capacity.  The red and blue
    channels are random noise (never touched by the embedder).
    """
    n_pixels = size * size
    arr = np.random.randint(0, 256, (size, size, 3), dtype=np.uint8)

    # Force a dominant peak in the green channel
    n_peak = int(n_pixels * peak_fraction)
    flat_green = arr[:, :, 1].ravel()
    flat_green[:n_peak] = peak_value
    # Non-peak pixels use values in [0, peak_value-1] so that bins
    # peak_value+1 .. 255 are guaranteed empty → valid zero points.
    flat_green[n_peak:] = np.random.randint(0, peak_value, size=n_pixels - n_peak)
    arr[:, :, 1] = flat_green.reshape(size, size)

    return Image.fromarray(arr, 'RGB')


@pytest.fixture
def rdh_image():
    """64×64 RGB image with ~2048 green pixels at 128 → capacity ≈ 230+ bytes."""
    return _make_rdh_image(64)


@pytest.fixture
def small_rdh_image():
    """32×32 RGB image with ~512 green pixels at 128 → capacity ≈ 47 bytes."""
    return _make_rdh_image(32)


@pytest.fixture
def large_rdh_image():
    """128×128 RGB image with ~8192 green pixels at 128 → capacity ≈ 1000+ bytes."""
    return _make_rdh_image(128)


@pytest.fixture
def temp_png_path(rdh_image):
    """Save the default RDH test image to a temporary PNG."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        rdh_image.save(f.name, 'PNG')
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_output_path():
    """Provide a temporary output path (cleaned up after the test)."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


# ---------------------------------------------------------------------------
# TestCapacity
# ---------------------------------------------------------------------------

class TestCapacity:
    def test_capacity_positive(self, embedder, rdh_image):
        cap = embedder.calculate_capacity(rdh_image)
        assert cap > 0

    def test_capacity_scales_with_image_size(self, embedder, small_rdh_image, rdh_image, large_rdh_image):
        cap_small = embedder.calculate_capacity(small_rdh_image)
        cap_medium = embedder.calculate_capacity(rdh_image)
        cap_large = embedder.calculate_capacity(large_rdh_image)
        assert cap_small < cap_medium < cap_large

    def test_capacity_last_capacity_updated(self, embedder, rdh_image):
        cap = embedder.calculate_capacity(rdh_image)
        assert embedder.last_capacity == cap

    def test_tiny_image_zero_capacity(self, embedder):
        """An image too small for the header has zero capacity."""
        arr = np.full((4, 4, 3), 128, dtype=np.uint8)
        img = Image.fromarray(arr, 'RGB')
        cap = embedder.calculate_capacity(img)
        # 16 peak pixels < 136 header bits → 0 bytes
        assert cap == 0


# ---------------------------------------------------------------------------
# TestEmbedExtract
# ---------------------------------------------------------------------------

class TestEmbedExtract:
    def test_basic_round_trip(self, embedder, temp_png_path, temp_output_path):
        message = "Hello, RDH!"
        success, msg, stats = embedder.embed_data(temp_png_path, message, temp_output_path)
        assert success
        assert stats['data_size'] == len(message.encode('utf-8'))
        assert not stats['encrypted']

        success2, msg2, extracted = embedder.extract_data(temp_output_path)
        assert success2
        assert extracted == message

    def test_round_trip_with_password(self, embedder, temp_png_path, temp_output_path):
        message = "Secret RDH message 🔐"
        password = "rdh-key"
        success, _, stats = embedder.embed_data(
            temp_png_path, message, temp_output_path, password=password
        )
        assert success
        assert stats['encrypted']

        success2, _, extracted = embedder.extract_data(temp_output_path, password=password)
        assert success2
        assert extracted == message

    def test_round_trip_unicode(self, embedder, temp_png_path, temp_output_path):
        message = "日本語 Español 🌍 RDH ✓"
        success, _, _ = embedder.embed_data(temp_png_path, message, temp_output_path)
        assert success

        success2, _, extracted = embedder.extract_data(temp_output_path)
        assert success2
        assert extracted == message

    def test_round_trip_empty_message(self, embedder, temp_png_path, temp_output_path):
        success, _, stats = embedder.embed_data(temp_png_path, "", temp_output_path)
        assert success
        assert stats['data_size'] == 0

        success2, _, extracted = embedder.extract_data(temp_output_path)
        assert success2
        assert extracted == ""

    def test_wrong_password(self, embedder, temp_png_path, temp_output_path):
        message = "Secret"
        embedder.embed_data(temp_png_path, message, temp_output_path, password="correct")

        success, _, extracted = embedder.extract_data(temp_output_path, password="wrong")
        # XOR with wrong key → garbage text, but checksum is on encrypted bytes
        # so extraction still "succeeds" with wrong content
        assert success
        assert extracted != message

    def test_missing_password_for_encrypted(self, embedder, temp_png_path, temp_output_path):
        embedder.embed_data(temp_png_path, "Secret", temp_output_path, password="key")

        success, msg, _ = embedder.extract_data(temp_output_path)
        assert not success
        assert "encrypted" in msg.lower()

    def test_no_data_in_image(self, embedder, temp_png_path):
        success, msg, _ = embedder.extract_data(temp_png_path)
        assert not success

    def test_data_too_large(self, embedder, temp_png_path, temp_output_path):
        message = "X" * 5000  # far exceeds capacity
        success, msg, stats = embedder.embed_data(temp_png_path, message, temp_output_path)
        assert not success
        assert "large" in msg.lower()
        assert stats == {}

    def test_nonexistent_input(self, embedder, temp_output_path):
        success, _, _ = embedder.embed_data("/nonexistent/file.png", "test", temp_output_path)
        assert not success

    def test_output_is_valid_png(self, embedder, temp_png_path, temp_output_path):
        embedder.embed_data(temp_png_path, "test", temp_output_path)
        img = Image.open(temp_output_path)
        assert img.format == 'PNG'

    def test_stego_image_visually_similar(self, embedder, temp_png_path, temp_output_path):
        """RDH shifts pixels by at most 1, so the stego image should be very close."""
        embedder.embed_data(temp_png_path, "test", temp_output_path)
        original = np.array(Image.open(temp_png_path))
        stego = np.array(Image.open(temp_output_path))
        diff = np.abs(original.astype(int) - stego.astype(int))
        assert np.max(diff) <= 1


# ---------------------------------------------------------------------------
# TestReversibility  (the defining property of RDH)
# ---------------------------------------------------------------------------

class TestReversibility:
    def test_perfect_restore_basic(self, embedder, temp_png_path, temp_output_path):
        """After extraction the restored image must be pixel-identical to the original."""
        message = "Reversible data hiding test"
        success, _, _ = embedder.embed_data(temp_png_path, message, temp_output_path)
        assert success

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            restore_path = f.name

        try:
            success2, _, extracted = embedder.extract_data(
                temp_output_path, restore_path=restore_path
            )
            assert success2
            assert extracted == message

            original = np.array(Image.open(temp_png_path))
            restored = np.array(Image.open(restore_path))
            assert np.array_equal(original, restored), "Restored image differs from original"
        finally:
            if os.path.exists(restore_path):
                os.unlink(restore_path)

    def test_perfect_restore_with_password(self, embedder, temp_png_path, temp_output_path):
        message = "Encrypted reversibility 🔑"
        password = "restore-key"
        embedder.embed_data(temp_png_path, message, temp_output_path, password=password)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            restore_path = f.name

        try:
            success, _, extracted = embedder.extract_data(
                temp_output_path, password=password, restore_path=restore_path
            )
            assert success
            assert extracted == message

            original = np.array(Image.open(temp_png_path))
            restored = np.array(Image.open(restore_path))
            assert np.array_equal(original, restored)
        finally:
            if os.path.exists(restore_path):
                os.unlink(restore_path)

    def test_perfect_restore_empty_message(self, embedder, temp_png_path, temp_output_path):
        embedder.embed_data(temp_png_path, "", temp_output_path)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            restore_path = f.name

        try:
            success, _, _ = embedder.extract_data(temp_output_path, restore_path=restore_path)
            assert success

            original = np.array(Image.open(temp_png_path))
            restored = np.array(Image.open(restore_path))
            assert np.array_equal(original, restored)
        finally:
            if os.path.exists(restore_path):
                os.unlink(restore_path)

    def test_perfect_restore_large_payload(self, embedder, temp_output_path):
        """Reversibility holds even when a large fraction of peak pixels are used."""
        img = _make_rdh_image(128)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name, 'PNG')
            src_path = f.name

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            restore_path = f.name

        try:
            cap = embedder.calculate_capacity(img)
            message = "R" * (cap - 10)  # near-full utilisation
            success, _, _ = embedder.embed_data(src_path, message, temp_output_path)
            assert success

            success2, _, extracted = embedder.extract_data(
                temp_output_path, restore_path=restore_path
            )
            assert success2
            assert extracted == message

            original = np.array(Image.open(src_path))
            restored = np.array(Image.open(restore_path))
            assert np.array_equal(original, restored)
        finally:
            for p in (src_path, restore_path):
                if os.path.exists(p):
                    os.unlink(p)

    def test_green_channel_restored(self, embedder, temp_png_path, temp_output_path):
        """Specifically verify the green channel (the only one modified)."""
        embedder.embed_data(temp_png_path, "green test", temp_output_path)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            restore_path = f.name

        try:
            embedder.extract_data(temp_output_path, restore_path=restore_path)
            orig_green = np.array(Image.open(temp_png_path))[:, :, 1]
            rest_green = np.array(Image.open(restore_path))[:, :, 1]
            assert np.array_equal(orig_green, rest_green)
        finally:
            if os.path.exists(restore_path):
                os.unlink(restore_path)


# ---------------------------------------------------------------------------
# TestEncryption
# ---------------------------------------------------------------------------

class TestEncryption:
    def test_xor_round_trip(self, embedder):
        original = "Test data for encryption"
        password = "test-key"
        encrypted = embedder._encrypt_data(original, password)
        assert encrypted != original.encode('utf-8')
        assert embedder._decrypt_data(encrypted, password) == original

    def test_different_keys_differ(self, embedder):
        data = "test data"
        enc1 = embedder._encrypt_data(data, "key1")
        enc2 = embedder._encrypt_data(data, "key2")
        assert enc1 != enc2

    def test_empty_data(self, embedder):
        encrypted = embedder._encrypt_data("", "key")
        assert encrypted == b""
        assert embedder._decrypt_data(encrypted, "key") == ""


# ---------------------------------------------------------------------------
# TestHeaderIntegrity
# ---------------------------------------------------------------------------

class TestHeaderIntegrity:
    def test_magic_number(self, embedder):
        assert embedder.MAGIC_NUMBER == b'RPAC'

    def test_header_size(self, embedder):
        assert embedder.HEADER_SIZE == 12

    def test_metadata_stored(self, embedder, temp_png_path, temp_output_path):
        embedder.embed_data(temp_png_path, "meta", temp_output_path)
        img = Image.open(temp_output_path)
        assert 'rdh_peak' in img.text
        assert 'rdh_zero' in img.text
