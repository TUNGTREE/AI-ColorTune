"""Standardized color grading parameters model."""
from typing import Optional

from pydantic import BaseModel, Field


class BasicParams(BaseModel):
    exposure: float = Field(0.0, ge=-3.0, le=3.0, description="Exposure in EV")
    contrast: float = Field(0, ge=-100, le=100)
    highlights: float = Field(0, ge=-100, le=100)
    shadows: float = Field(0, ge=-100, le=100)
    whites: float = Field(0, ge=-100, le=100)
    blacks: float = Field(0, ge=-100, le=100)


class ColorAdjustParams(BaseModel):
    temperature: float = Field(6500, ge=2000, le=12000, description="Color temp in Kelvin")
    tint: float = Field(0, ge=-100, le=100, description="Green-Magenta tint")
    vibrance: float = Field(0, ge=-100, le=100)
    saturation: float = Field(0, ge=-100, le=100)


class ToneCurveParams(BaseModel):
    points: list[list[int]] = Field(
        default=[[0, 0], [64, 64], [128, 128], [192, 192], [255, 255]],
        description="Master curve control points [[x,y], ...]",
    )
    red: Optional[list[list[int]]] = None
    green: Optional[list[list[int]]] = None
    blue: Optional[list[list[int]]] = None


class HSLChannel(BaseModel):
    hue: float = Field(0, ge=-180, le=180)
    saturation: float = Field(0, ge=-100, le=100)
    luminance: float = Field(0, ge=-100, le=100)


class HSLParams(BaseModel):
    red: HSLChannel = Field(default_factory=HSLChannel)
    orange: HSLChannel = Field(default_factory=HSLChannel)
    yellow: HSLChannel = Field(default_factory=HSLChannel)
    green: HSLChannel = Field(default_factory=HSLChannel)
    aqua: HSLChannel = Field(default_factory=HSLChannel)
    blue: HSLChannel = Field(default_factory=HSLChannel)
    purple: HSLChannel = Field(default_factory=HSLChannel)
    magenta: HSLChannel = Field(default_factory=HSLChannel)


class SplitToneChannel(BaseModel):
    hue: float = Field(0, ge=0, le=360)
    saturation: float = Field(0, ge=0, le=100)


class SplitToningParams(BaseModel):
    highlights: SplitToneChannel = Field(default_factory=SplitToneChannel)
    midtones: SplitToneChannel = Field(default_factory=SplitToneChannel)
    shadows: SplitToneChannel = Field(default_factory=SplitToneChannel)
    balance: float = Field(0, ge=-100, le=100)


class EffectsParams(BaseModel):
    clarity: float = Field(0, ge=-100, le=100)
    dehaze: float = Field(0, ge=-100, le=100)
    vignette: float = Field(0, ge=-100, le=100)
    grain: float = Field(0, ge=0, le=100)
    texture: float = Field(0, ge=-100, le=100, description="Fine detail enhancement")
    fade: float = Field(0, ge=0, le=100, description="Lift black point for faded look")
    sharpening: float = Field(0, ge=0, le=100, description="Sharpening amount")
    sharpen_radius: float = Field(1.0, ge=0.5, le=5.0, description="Sharpening radius")


class ColorParams(BaseModel):
    """Complete color grading parameter set."""
    version: str = "1.0"
    basic: BasicParams = Field(default_factory=BasicParams)
    color: ColorAdjustParams = Field(default_factory=ColorAdjustParams)
    tone_curve: ToneCurveParams = Field(default_factory=ToneCurveParams)
    hsl: HSLParams = Field(default_factory=HSLParams)
    split_toning: SplitToningParams = Field(default_factory=SplitToningParams)
    effects: EffectsParams = Field(default_factory=EffectsParams)

    @classmethod
    def identity(cls) -> "ColorParams":
        """Return default (no-op) parameters."""
        return cls()


# ------------------------------------------------------------------
# Sanitize raw AI output before validation
# ------------------------------------------------------------------

_CLAMP_RULES: dict[str, tuple[float, float]] = {
    "basic.exposure": (-3.0, 3.0),
    "basic.contrast": (-100, 100),
    "basic.highlights": (-100, 100),
    "basic.shadows": (-100, 100),
    "basic.whites": (-100, 100),
    "basic.blacks": (-100, 100),
    "color.temperature": (2000, 12000),
    "color.tint": (-100, 100),
    "color.vibrance": (-100, 100),
    "color.saturation": (-100, 100),
    "effects.clarity": (-100, 100),
    "effects.dehaze": (-100, 100),
    "effects.vignette": (-100, 100),
    "effects.grain": (0, 100),
    "effects.texture": (-100, 100),
    "effects.fade": (0, 100),
    "effects.sharpening": (0, 100),
    "effects.sharpen_radius": (0.5, 5.0),
    "split_toning.balance": (-100, 100),
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def sanitize_ai_params(raw: dict) -> dict:
    """Clamp all numeric values in an AI-generated parameter dict so they
    pass ColorParams validation.  Modifies and returns *raw* in-place.

    Also enforces quality-safe limits: forces grain=0, caps clarity/dehaze
    to reasonable ranges to prevent noise/artifact introduction.
    """
    for dotpath, (lo, hi) in _CLAMP_RULES.items():
        parts = dotpath.split(".")
        obj = raw
        for p in parts[:-1]:
            if not isinstance(obj, dict) or p not in obj:
                break
            obj = obj[p]
        else:
            key = parts[-1]
            if isinstance(obj, dict) and key in obj and isinstance(obj[key], (int, float)):
                obj[key] = _clamp(float(obj[key]), lo, hi)

    # Force grain to 0 — it only degrades image quality
    effects = raw.get("effects")
    if isinstance(effects, dict):
        effects["grain"] = 0
        # Cap clarity and dehaze to safe ranges
        if "clarity" in effects:
            effects["clarity"] = _clamp(float(effects["clarity"]), -30, 30)
        if "dehaze" in effects:
            effects["dehaze"] = _clamp(float(effects["dehaze"]), -20, 25)

    # HSL channels: hue [-180, 180], saturation/luminance [-100, 100]
    hsl = raw.get("hsl")
    if isinstance(hsl, dict):
        for channel in hsl.values():
            if isinstance(channel, dict):
                if "hue" in channel:
                    channel["hue"] = _clamp(float(channel["hue"]), -180, 180)
                if "saturation" in channel:
                    channel["saturation"] = _clamp(float(channel["saturation"]), -100, 100)
                if "luminance" in channel:
                    channel["luminance"] = _clamp(float(channel["luminance"]), -100, 100)

    # Split toning channels: hue [0, 360], saturation [0, 100]
    st = raw.get("split_toning")
    if isinstance(st, dict):
        for key in ("highlights", "midtones", "shadows"):
            ch = st.get(key)
            if isinstance(ch, dict):
                if "hue" in ch:
                    ch["hue"] = _clamp(float(ch["hue"]), 0, 360)
                if "saturation" in ch:
                    ch["saturation"] = _clamp(float(ch["saturation"]), 0, 100)

    # Tone curve points: clamp to [0, 255]
    tc = raw.get("tone_curve")
    if isinstance(tc, dict):
        for curve_key in ("points", "red", "green", "blue"):
            pts = tc.get(curve_key)
            if isinstance(pts, list):
                tc[curve_key] = [
                    [int(_clamp(p[0], 0, 255)), int(_clamp(p[1], 0, 255))]
                    for p in pts
                    if isinstance(p, (list, tuple)) and len(p) >= 2
                ]

    return raw
