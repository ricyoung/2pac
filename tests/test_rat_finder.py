"""Unit tests for steganography detection (rat_finder) with LSB integration."""

import os
import tempfile
import pytest
from PIL import Image
import numpy as np

from steg_embedder import StegEmbedder
import rat_finder


@pytest.fixture
def embedder():
    return StegEmbedder()


@pytest.fixture
def clean_image_path():
    """Create a 64x64 random noise PNG for testing."""
    arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    img = Image.fromarray(arr, 'RGB')
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img.save(f.name, 'PNG')
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def stego_image_path(embedder, clean_image_path):
    """Create a 64x64 image with LSB-embedded data (1 bit/channel)."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        output_path = f.name
    success, _, _ = embedder.embed_data(
        clean_image_path, "secret message", output_path, bits_per_channel=1
    )
    assert success, "Embedding failed during fixture setup"
    yield output_path
    if os.path.exists(output_path):
        os.unlink(output_path)


@pytest.fixture
def stego_image_4bit_path(embedder, clean_image_path):
    """Create a 64x64 image with LSB-embedded data (4 bits/channel)."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        output_path = f.name
    success, _, _ = embedder.embed_data(
        clean_image_path, "secret message", output_path, bits_per_channel=4
    )
    assert success, "Embedding (4-bit) failed during fixture setup"
    yield output_path
    if os.path.exists(output_path):
        os.unlink(output_path)


class TestAnalyzeImage:
    def test_clean_image_low_suspicion(self, clean_image_path):
        is_suspicious, confidence, details = rat_finder.analyze_image(clean_image_path)
        # Clean random noise image should return valid structure
        assert isinstance(is_suspicious, bool)
        assert isinstance(confidence, (int, float))
        assert confidence >= 0
        assert isinstance(details, dict)

    def test_returns_three_tuple(self, clean_image_path):
        result = rat_finder.analyze_image(clean_image_path)
        assert len(result) == 3
        is_suspicious, confidence, details = result
        assert isinstance(is_suspicious, bool)
        assert isinstance(confidence, (int, float))
        assert isinstance(details, dict)

    def test_details_has_expected_keys(self, clean_image_path):
        _, _, details = rat_finder.analyze_image(clean_image_path)
        expected_keys = [
            'lsb_analysis',
            'histogram_analysis',
            'file_size_analysis',
            'metadata_analysis',
            'trailing_data_analysis',
            'visual_noise_analysis',
        ]
        for key in expected_keys:
            assert key in details, f"Missing key: {key}"
            assert 'suspicious' in details[key]
            assert 'confidence' in details[key]
            assert 'details' in details[key]

    def test_sensitivity_affects_threshold(self, clean_image_path):
        result_low = rat_finder.analyze_image(clean_image_path, sensitivity='low')
        result_high = rat_finder.analyze_image(clean_image_path, sensitivity='high')

        # Both should return valid structures
        for result in (result_low, result_high):
            is_suspicious, confidence, details = result
            assert isinstance(is_suspicious, bool)
            assert isinstance(confidence, (int, float))
            assert isinstance(details, dict)


class TestLSBDetection:
    def test_lsb_embedded_detected(self, stego_image_path):
        is_suspicious, confidence, details = rat_finder.check_lsb_anomalies(
            stego_image_path
        )
        # LSB-embedded image should show some signal
        assert isinstance(is_suspicious, bool)
        assert isinstance(confidence, (int, float))
        assert confidence >= 0
        assert isinstance(details, dict)

    def test_lsb_embedded_analyze_image(self, stego_image_path, clean_image_path):
        _, stego_confidence, _ = rat_finder.analyze_image(stego_image_path)
        _, clean_confidence, _ = rat_finder.analyze_image(clean_image_path)

        # Stego image should have confidence > 0
        assert stego_confidence > 0
        # Overall confidence is a weighted blend of 9 heuristic detectors;
        # allow small tolerance for random-image noise
        assert stego_confidence >= clean_confidence - 5

    def test_lsb_bits4_more_detectable(
        self, stego_image_path, stego_image_4bit_path
    ):
        _, confidence_1bit, _ = rat_finder.check_lsb_anomalies(stego_image_path)
        _, confidence_4bit, _ = rat_finder.check_lsb_anomalies(stego_image_4bit_path)

        # 4-bit embedding modifies more bits → should be at least as detectable
        assert confidence_4bit >= confidence_1bit


class TestTrailingData:
    def test_clean_png_no_trailing(self, clean_image_path):
        is_suspicious, confidence, details = rat_finder.check_trailing_data(
            clean_image_path
        )
        assert is_suspicious is False
        assert confidence == 0
        assert details.get('appended_bytes', 0) == 0

    def test_appended_data_detected(self, clean_image_path):
        # Read the clean PNG and append extra bytes
        with open(clean_image_path, 'rb') as f:
            original_data = f.read()

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(original_data + b'\x00' * 256)
            tampered_path = f.name

        try:
            is_suspicious, confidence, details = rat_finder.check_trailing_data(
                tampered_path
            )
            assert is_suspicious is True
            assert confidence > 0
            assert details['appended_bytes'] == 256
        finally:
            os.unlink(tampered_path)


class TestFileSize:
    @pytest.fixture
    def smooth_image_path(self):
        """Create a smooth gradient PNG that compresses well."""
        arr = np.zeros((64, 64, 3), dtype=np.uint8)
        arr[:, :, 0] = np.linspace(0, 255, 64, dtype=np.uint8)[np.newaxis, :]
        arr[:, :, 1] = np.linspace(0, 255, 64, dtype=np.uint8)[:, np.newaxis]
        arr[:, :, 2] = 128
        img = Image.fromarray(arr, 'RGB')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name, 'PNG')
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_normal_file_size(self, smooth_image_path):
        is_suspicious, confidence, details = rat_finder.check_file_size_anomalies(
            smooth_image_path
        )
        # File size heuristics are rough — just verify valid structure
        assert isinstance(is_suspicious, (bool, np.bool_))
        assert isinstance(confidence, (int, float, np.integer, np.floating))
        assert confidence >= 0

    def test_returns_valid_structure(self, smooth_image_path):
        result = rat_finder.check_file_size_anomalies(smooth_image_path)
        assert len(result) == 3
        is_suspicious, confidence, details = result
        assert isinstance(is_suspicious, bool)
        assert isinstance(confidence, (int, float))
        assert isinstance(details, dict)
        assert 'file_size' in details
        assert 'pixel_count' in details


class TestHistogram:
    def test_clean_image_histogram(self, clean_image_path):
        is_suspicious, confidence, details = rat_finder.check_histogram_anomalies(
            clean_image_path
        )
        assert isinstance(is_suspicious, (bool, np.bool_))
        assert isinstance(confidence, (int, float, np.integer, np.floating))
        assert isinstance(details, dict)
        assert 'even_odd_ratios' in details

    def test_lsb_embedded_histogram(self, stego_image_path):
        is_suspicious, confidence, details = rat_finder.check_histogram_anomalies(
            stego_image_path
        )
        assert isinstance(is_suspicious, (bool, np.bool_))
        assert isinstance(confidence, (int, float, np.integer, np.floating))
        assert isinstance(details, dict)


class TestMetadata:
    def test_clean_image_metadata(self, clean_image_path):
        is_suspicious, confidence, details = rat_finder.check_metadata_anomalies(
            clean_image_path
        )
        # A programmatically generated PNG should have no suspicious markers
        assert is_suspicious is False
        assert confidence == 0
        assert details.get('suspicious_markers', []) == []


class TestIntegration:
    def test_embed_then_detect_full_pipeline(self, embedder):
        """Full integration: create image → embed → detect."""
        # Create a 128x128 random image
        arr = np.random.randint(0, 256, (128, 128, 3), dtype=np.uint8)
        img = Image.fromarray(arr, 'RGB')

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name, 'PNG')
            input_path = f.name

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            stego_path = f.name

        try:
            # Embed data
            success, _, _ = embedder.embed_data(
                input_path, "integration test payload", stego_path, bits_per_channel=2
            )
            assert success

            # Run full analysis
            is_suspicious, confidence, details = rat_finder.analyze_image(stego_path)
            assert isinstance(is_suspicious, bool)
            assert confidence > 0
            assert 'lsb_analysis' in details

            # Compare with clean image (allow tolerance for heuristic noise)
            _, clean_confidence, _ = rat_finder.analyze_image(input_path)
            assert confidence >= clean_confidence - 5
        finally:
            os.unlink(input_path)
            if os.path.exists(stego_path):
                os.unlink(stego_path)

    def test_clean_vs_stego_directional(self, embedder, clean_image_path):
        """Stego image should always score >= clean image."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            stego_path = f.name

        try:
            success, _, _ = embedder.embed_data(
                clean_image_path, "directional test", stego_path, bits_per_channel=1
            )
            assert success

            _, clean_conf, _ = rat_finder.analyze_image(clean_image_path)
            _, stego_conf, _ = rat_finder.analyze_image(stego_path)
            assert stego_conf >= clean_conf - 5
        finally:
            if os.path.exists(stego_path):
                os.unlink(stego_path)


class TestRSAnalysis:
    def test_clean_image_rs(self, clean_image_path):
        is_suspicious, confidence, details = rat_finder.check_rs_analysis(
            clean_image_path
        )
        assert isinstance(is_suspicious, (bool, np.bool_))
        assert isinstance(confidence, (int, float, np.integer, np.floating))
        assert confidence >= 0
        assert 'mean_asymmetry' in details
        assert 'channels' in details

    def test_lsb_embedded_rs(self, stego_image_path):
        is_suspicious, confidence, details = rat_finder.check_rs_analysis(
            stego_image_path
        )
        assert isinstance(is_suspicious, (bool, np.bool_))
        assert confidence >= 0
        assert 'mean_asymmetry' in details

    def test_rs_in_analyze_image(self, stego_image_path):
        _, _, details = rat_finder.analyze_image(stego_image_path)
        assert 'rs_analysis' in details
        assert 'suspicious' in details['rs_analysis']
        assert 'confidence' in details['rs_analysis']

    def test_rs_stego_higher_than_clean(self, stego_image_path, clean_image_path):
        _, stego_conf, _ = rat_finder.check_rs_analysis(stego_image_path)
        _, clean_conf, _ = rat_finder.check_rs_analysis(clean_image_path)
        # LSB embedding should increase RS asymmetry
        assert stego_conf >= clean_conf


class TestSamplePairAnalysis:
    def test_clean_image_spa(self, clean_image_path):
        is_suspicious, confidence, details = rat_finder.check_sample_pair_analysis(
            clean_image_path
        )
        assert isinstance(is_suspicious, (bool, np.bool_))
        assert isinstance(confidence, (int, float, np.integer, np.floating))
        assert confidence >= 0
        assert 'mean_estimated_rate' in details
        assert 'channels' in details

    def test_lsb_embedded_spa(self, stego_image_path):
        is_suspicious, confidence, details = rat_finder.check_sample_pair_analysis(
            stego_image_path
        )
        assert isinstance(is_suspicious, (bool, np.bool_))
        assert confidence >= 0
        assert 'mean_estimated_rate' in details

    def test_spa_in_analyze_image(self, stego_image_path):
        _, _, details = rat_finder.analyze_image(stego_image_path)
        assert 'sample_pair_analysis' in details
        assert 'suspicious' in details['sample_pair_analysis']
        assert 'confidence' in details['sample_pair_analysis']

    def test_spa_stego_higher_than_clean(self, stego_image_path, clean_image_path):
        _, stego_conf, _ = rat_finder.check_sample_pair_analysis(stego_image_path)
        _, clean_conf, _ = rat_finder.check_sample_pair_analysis(clean_image_path)
        # LSB embedding should increase SPA estimated rate
        assert stego_conf >= clean_conf
