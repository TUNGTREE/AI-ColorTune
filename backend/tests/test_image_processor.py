"""Tests for image_ops.py and ImageProcessor."""
import time

import numpy as np
import pytest

from app.core import image_ops
from app.core.color_params import ColorParams, BasicParams, ColorAdjustParams, EffectsParams
from app.services.image_processor import ImageProcessor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_image():
    """Create a 100x100 test image with a color gradient."""
    img = np.zeros((100, 100, 3), dtype=np.float32)
    # Horizontal gradient: dark to light
    for x in range(100):
        img[:, x, :] = x / 99.0
    return img


@pytest.fixture
def color_image():
    """Create a 100x100 image with diverse colors."""
    img = np.zeros((100, 100, 3), dtype=np.float32)
    # Red quadrant
    img[:50, :50, 0] = 0.8
    # Green quadrant
    img[:50, 50:, 1] = 0.8
    # Blue quadrant
    img[50:, :50, 2] = 0.8
    # Yellow quadrant
    img[50:, 50:, 0] = 0.8
    img[50:, 50:, 1] = 0.8
    return img


@pytest.fixture
def large_image():
    """Create a 1600x1200 image for performance testing."""
    rng = np.random.default_rng(42)
    return rng.random((1200, 1600, 3), dtype=np.float32)


# ---------------------------------------------------------------------------
# Identity tests
# ---------------------------------------------------------------------------

def test_identity_all_ops(sample_image):
    """Applying zero/default params should return identical image."""
    params = ColorParams.identity()
    result = ImageProcessor.apply_params(sample_image, params)
    np.testing.assert_array_almost_equal(result, sample_image, decimal=5)


# ---------------------------------------------------------------------------
# Individual operation tests
# ---------------------------------------------------------------------------

class TestExposure:
    def test_zero(self, sample_image):
        result = image_ops.adjust_exposure(sample_image, 0)
        np.testing.assert_array_equal(result, sample_image)

    def test_positive(self, sample_image):
        result = image_ops.adjust_exposure(sample_image, 1.0)
        assert result.mean() > sample_image.mean()

    def test_negative(self, sample_image):
        result = image_ops.adjust_exposure(sample_image, -1.0)
        assert result.mean() < sample_image.mean()

    def test_range_valid(self, sample_image):
        result = image_ops.adjust_exposure(sample_image, 3.0)
        assert result.min() >= 0.0 and result.max() <= 1.0


class TestContrast:
    def test_zero(self, sample_image):
        result = image_ops.adjust_contrast(sample_image, 0)
        np.testing.assert_array_almost_equal(result, sample_image)

    def test_positive_increases_range(self, sample_image):
        result = image_ops.adjust_contrast(sample_image, 50)
        # Higher contrast = greater spread from midpoint
        orig_std = sample_image.std()
        result_std = result.std()
        assert result_std > orig_std * 0.9  # should generally increase

    def test_negative_decreases_range(self, sample_image):
        result = image_ops.adjust_contrast(sample_image, -80)
        orig_std = sample_image.std()
        result_std = result.std()
        assert result_std < orig_std


class TestHighlightsShadows:
    def test_highlights_zero(self, sample_image):
        result = image_ops.adjust_highlights(sample_image, 0)
        np.testing.assert_array_equal(result, sample_image)

    def test_shadows_zero(self, sample_image):
        result = image_ops.adjust_shadows(sample_image, 0)
        np.testing.assert_array_equal(result, sample_image)

    def test_highlights_positive_brightens_bright_areas(self, sample_image):
        result = image_ops.adjust_highlights(sample_image, 50)
        # Right side (bright pixels) should increase
        bright_orig = sample_image[:, 80:, :].mean()
        bright_result = result[:, 80:, :].mean()
        assert bright_result > bright_orig

    def test_shadows_positive_brightens_dark_areas(self, sample_image):
        result = image_ops.adjust_shadows(sample_image, 50)
        dark_orig = sample_image[:, :20, :].mean()
        dark_result = result[:, :20, :].mean()
        assert dark_result > dark_orig


class TestTemperature:
    def test_neutral(self, sample_image):
        result = image_ops.adjust_temperature(sample_image, 6500)
        np.testing.assert_array_equal(result, sample_image)

    def test_warm(self, color_image):
        result = image_ops.adjust_temperature(color_image, 9000)
        # Warmer = more red, less blue
        assert result[..., 0].mean() >= color_image[..., 0].mean()

    def test_cool(self, color_image):
        result = image_ops.adjust_temperature(color_image, 3000)
        # Cooler = less red, more blue
        assert result[..., 2].mean() >= color_image[..., 2].mean()


class TestSaturation:
    def test_zero(self, color_image):
        result = image_ops.adjust_saturation(color_image, 0)
        np.testing.assert_array_almost_equal(result, color_image)

    def test_desaturate(self, color_image):
        result = image_ops.adjust_saturation(color_image, -100)
        # Fully desaturated: all channels should be equal (grayscale)
        np.testing.assert_array_almost_equal(
            result[..., 0], result[..., 1], decimal=4
        )

    def test_increase(self, color_image):
        result = image_ops.adjust_saturation(color_image, 50)
        # Standard deviation across channels should increase
        orig_channel_std = color_image.std(axis=2).mean()
        result_channel_std = result.std(axis=2).mean()
        assert result_channel_std >= orig_channel_std * 0.9


class TestToneCurve:
    def test_identity_curve(self, sample_image):
        default_pts = [[0, 0], [64, 64], [128, 128], [192, 192], [255, 255]]
        result = image_ops.apply_tone_curve(sample_image, default_pts)
        np.testing.assert_array_almost_equal(result, sample_image, decimal=2)

    def test_brighten_curve(self, sample_image):
        pts = [[0, 0], [128, 180], [255, 255]]
        result = image_ops.apply_tone_curve(sample_image, pts)
        assert result.mean() > sample_image.mean()

    def test_per_channel(self, color_image):
        default_pts = [[0, 0], [128, 128], [255, 255]]
        red_pts = [[0, 0], [128, 200], [255, 255]]
        result = image_ops.apply_tone_curve(
            color_image, default_pts, red=red_pts,
        )
        # Red channel should be brighter
        assert result[..., 0].mean() > color_image[..., 0].mean()


class TestHSL:
    def test_all_zero(self, color_image):
        hsl_dict = {
            name: {"hue": 0, "saturation": 0, "luminance": 0}
            for name in ["red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"]
        }
        result = image_ops.adjust_hsl(color_image, hsl_dict)
        np.testing.assert_array_almost_equal(result, color_image, decimal=5)

    def test_desaturate_red(self, color_image):
        hsl_dict = {
            name: {"hue": 0, "saturation": 0, "luminance": 0}
            for name in ["red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"]
        }
        hsl_dict["red"]["saturation"] = -80
        result = image_ops.adjust_hsl(color_image, hsl_dict)
        # Red quadrant should be less saturated
        red_quad_orig = color_image[:50, :50, :]
        red_quad_result = result[:50, :50, :]
        orig_sat = red_quad_orig.std(axis=2).mean()
        result_sat = red_quad_result.std(axis=2).mean()
        assert result_sat < orig_sat


class TestSplitToning:
    def test_zero_saturation(self, sample_image):
        result = image_ops.apply_split_toning(sample_image, 0, 0, 0, 0, 0)
        np.testing.assert_array_equal(result, sample_image)

    def test_warm_highlights(self, sample_image):
        result = image_ops.apply_split_toning(
            sample_image, 30, 50, 0, 0, 0
        )
        assert not np.array_equal(result, sample_image)


class TestEffects:
    def test_clarity_zero(self, sample_image):
        result = image_ops.adjust_clarity(sample_image, 0)
        np.testing.assert_array_equal(result, sample_image)

    def test_dehaze_zero(self, sample_image):
        result = image_ops.adjust_dehaze(sample_image, 0)
        np.testing.assert_array_equal(result, sample_image)

    def test_vignette_zero(self, sample_image):
        result = image_ops.apply_vignette(sample_image, 0)
        np.testing.assert_array_equal(result, sample_image)

    def test_grain_zero(self, sample_image):
        result = image_ops.apply_grain(sample_image, 0)
        np.testing.assert_array_equal(result, sample_image)

    def test_vignette_darkens_edges(self):
        # Use uniform mid-tone image so edge darkening is clearly visible
        uniform = np.full((100, 100, 3), 0.5, dtype=np.float32)
        result = image_ops.apply_vignette(uniform, -50)
        center = result[45:55, 45:55, :].mean()
        corner = result[:5, :5, :].mean()
        # Center should remain brighter than darkened corners
        assert center > corner


# ---------------------------------------------------------------------------
# Extreme value tests
# ---------------------------------------------------------------------------

class TestExtremeValues:
    def test_all_max_params(self, sample_image):
        """All params at maximum - should not crash."""
        params = ColorParams(
            basic=BasicParams(exposure=3.0, contrast=100, highlights=100,
                              shadows=100, whites=100, blacks=100),
            color=ColorAdjustParams(temperature=12000, tint=100,
                                    vibrance=100, saturation=100),
            effects=EffectsParams(clarity=100, dehaze=100, vignette=-100, grain=100),
        )
        result = ImageProcessor.apply_params(sample_image, params)
        assert result.shape == sample_image.shape
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_all_min_params(self, sample_image):
        """All params at minimum - should not crash."""
        params = ColorParams(
            basic=BasicParams(exposure=-3.0, contrast=-100, highlights=-100,
                              shadows=-100, whites=-100, blacks=-100),
            color=ColorAdjustParams(temperature=2000, tint=-100,
                                    vibrance=-100, saturation=-100),
            effects=EffectsParams(clarity=-100, dehaze=-100, vignette=100, grain=0),
        )
        result = ImageProcessor.apply_params(sample_image, params)
        assert result.shape == sample_image.shape
        assert result.min() >= 0.0
        assert result.max() <= 1.0


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_combined_adjustments(self, color_image):
        """Multiple combined adjustments should produce valid output."""
        params = ColorParams(
            basic=BasicParams(exposure=0.5, contrast=20, shadows=30),
            color=ColorAdjustParams(temperature=7500, saturation=15),
            effects=EffectsParams(clarity=30, vignette=-20),
        )
        result = ImageProcessor.apply_params(color_image, params)
        assert result.shape == color_image.shape
        assert result.min() >= 0.0
        assert result.max() <= 1.0
        # Should be different from original
        assert not np.allclose(result, color_image)

    def test_preview_generation(self, large_image):
        """Preview of large image should be resized."""
        preview = ImageProcessor.generate_preview(large_image, max_width=800)
        assert preview.shape[1] == 800
        assert preview.shape[0] == 600  # aspect ratio maintained

    def test_preview_speed(self, large_image):
        """Preview generation with params should be < 2 seconds."""
        preview = ImageProcessor.generate_preview(large_image, max_width=800)
        params = ColorParams(
            basic=BasicParams(exposure=0.5, contrast=20),
            color=ColorAdjustParams(temperature=7000, saturation=10),
            effects=EffectsParams(clarity=20),
        )
        start = time.time()
        result = ImageProcessor.apply_params(preview, params)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Preview took {elapsed:.2f}s (limit: 2.0s)"
        assert result.shape == preview.shape
