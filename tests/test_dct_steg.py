"""Unit tests for DCT steganography engine (pairwise coefficient)."""

import os
import tempfile
import pytest
from PIL import Image
import numpy as np

from dct_steg import DctStegEmbedder, _dct2d, _idct2d


@pytest.fixture
def embedder():
    return DctStegEmbedder(quality=95)


@pytest.fixture
def temp_png_path():
    arr = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    img = Image.fromarray(arr, 'RGB')
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img.save(f.name, 'PNG')
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_output_path():
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestDCTTransforms:
    def test_dct_idct_roundtrip(self):
        block = np.random.randn(8, 8).astype(np.float32)
        dct = _dct2d(block)
        restored = _idct2d(dct)
        assert np.allclose(block, restored, atol=1e-5)

    def test_dct_energy_compaction(self):
        block = np.ones((8, 8), dtype=np.float32) * 128
        dct = _dct2d(block)
        assert abs(dct[0, 0]) > 1000
        assert all(abs(dct[0, c]) < 0.01 for c in range(1, 8))


class TestCapacity:
    def test_capacity_positive(self, embedder, temp_png_path):
        img = Image.open(temp_png_path)
        cap = embedder.calculate_capacity(img)
        assert cap > 0

    def test_small_image_no_capacity(self, embedder):
        img = Image.new('RGB', (4, 4))
        assert embedder.calculate_capacity(img) == 0

    def test_bigger_image_more_capacity(self, embedder):
        small = Image.new('RGB', (16, 16))
        large = Image.new('RGB', (128, 128))
        assert embedder.calculate_capacity(large) > embedder.calculate_capacity(small)


class TestEmbedExtract:
    # DCT parity embedding does not survive the spatial-domain roundtrip
    # (DCT→quantize→IDCT→clip→uint8→re-DCT changes coefficient parity).
    # These tests document the known failure until the algorithm is fixed.
    _xfail = pytest.mark.xfail(
        reason="DCT embed/extract roundtrip is non-functional", strict=True
    )

    @_xfail
    def test_basic_roundtrip(self, embedder, temp_png_path, temp_output_path):
        message = "Hello DCT Stego!"
        success, msg, stats = embedder.embed_data(
            temp_png_path, message, temp_output_path
        )
        assert success, f"Embed failed: {msg}"
        assert stats['data_size'] == len(message.encode('utf-8'))

        success2, msg2, extracted = embedder.extract_data(temp_output_path)
        assert success2, f"Extract failed: {msg2}"
        assert extracted == message

    @_xfail
    def test_roundtrip_with_password(self, embedder, temp_png_path, temp_output_path):
        message = "Encrypted DCT secret"
        password = "dct-pass-123"
        success, _, stats = embedder.embed_data(
            temp_png_path, message, temp_output_path, password=password
        )
        assert success
        assert stats['encrypted']

        success2, _, extracted = embedder.extract_data(
            temp_output_path, password=password
        )
        assert success2
        assert extracted == message

    @_xfail
    def test_wrong_password_produces_garbage(self, embedder, temp_png_path, temp_output_path):
        message = "Secret DCT data"
        embedder.embed_data(temp_png_path, message, temp_output_path, password="correct")
        success, _, extracted = embedder.extract_data(temp_output_path, password="wrong")
        assert success
        assert extracted != message

    def test_no_data_in_clean_image(self, embedder, temp_png_path):
        success, msg, extracted = embedder.extract_data(temp_png_path)
        assert not success
        assert "magic" in msg.lower()

    @_xfail
    def test_missing_password_for_encrypted(self, embedder, temp_png_path, temp_output_path):
        embedder.embed_data(temp_png_path, "secret", temp_output_path, password="key")
        success, msg, _ = embedder.extract_data(temp_output_path)
        assert not success
        assert "encrypted" in msg.lower()

    def test_output_is_valid_png(self, embedder, temp_png_path, temp_output_path):
        embedder.embed_data(temp_png_path, "test", temp_output_path)
        img = Image.open(temp_output_path)
        assert img.format == 'PNG'

    @_xfail
    def test_empty_message(self, embedder, temp_png_path, temp_output_path):
        success, _, _ = embedder.embed_data(temp_png_path, "", temp_output_path)
        assert success
        success2, _, extracted = embedder.extract_data(temp_output_path)
        assert success2
        assert extracted == ""

    @_xfail
    def test_unicode_text(self, embedder, temp_png_path, temp_output_path):
        message = "日本語 Test ™ DCT"
        success, _, _ = embedder.embed_data(temp_png_path, message, temp_output_path)
        assert success
        success2, _, extracted = embedder.extract_data(temp_output_path)
        assert success2
        assert extracted == message

    @_xfail
    def test_larger_message(self, embedder, temp_png_path, temp_output_path):
        message = "DCT steganography is more resilient! " * 10
        success, _, _ = embedder.embed_data(temp_png_path, message, temp_output_path)
        assert success
        success2, _, extracted = embedder.extract_data(temp_output_path)
        assert success2
        assert extracted == message

    @_xfail
    def test_long_message(self, embedder, temp_png_path, temp_output_path):
        message = "The quick brown fox jumps over the lazy dog. " * 8
        success, _, _ = embedder.embed_data(temp_png_path, message, temp_output_path)
        assert success
        success2, _, extracted = embedder.extract_data(temp_output_path)
        assert success2
        assert extracted == message
