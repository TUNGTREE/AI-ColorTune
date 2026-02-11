"""Tests for color_params.py"""
import pytest
from pydantic import ValidationError

from app.core.color_params import ColorParams, BasicParams, ColorAdjustParams


def test_identity_params():
    params = ColorParams.identity()
    assert params.basic.exposure == 0.0
    assert params.basic.contrast == 0
    assert params.color.temperature == 6500
    assert params.color.saturation == 0
    assert params.effects.grain == 0


def test_valid_params():
    params = ColorParams(
        basic=BasicParams(exposure=1.5, contrast=50),
        color=ColorAdjustParams(temperature=8000, saturation=-30),
    )
    assert params.basic.exposure == 1.5
    assert params.color.temperature == 8000


def test_exposure_out_of_range():
    with pytest.raises(ValidationError):
        BasicParams(exposure=5.0)


def test_contrast_out_of_range():
    with pytest.raises(ValidationError):
        BasicParams(contrast=200)


def test_temperature_out_of_range():
    with pytest.raises(ValidationError):
        ColorAdjustParams(temperature=500)


def test_full_json_roundtrip():
    params = ColorParams(basic=BasicParams(exposure=0.7, contrast=-20))
    json_str = params.model_dump_json()
    restored = ColorParams.model_validate_json(json_str)
    assert restored.basic.exposure == 0.7
    assert restored.basic.contrast == -20
