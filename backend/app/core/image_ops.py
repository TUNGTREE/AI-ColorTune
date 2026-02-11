"""Image adjustment operations.

Each function takes a numpy float32 image (0-1 range, RGB) and returns the
adjusted image in the same format.  All operations are non-destructive and
composable.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy.interpolate import CubicSpline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(img: np.ndarray) -> np.ndarray:
    return np.clip(img, 0.0, 1.0)


def _srgb_to_linear(img: np.ndarray) -> np.ndarray:
    return np.where(img <= 0.04045, img / 12.92, ((img + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(img: np.ndarray) -> np.ndarray:
    return np.where(img <= 0.0031308, img * 12.92, 1.055 * np.power(np.maximum(img, 0), 1 / 2.4) - 0.055)


def _rgb_to_hsl(img: np.ndarray) -> np.ndarray:
    """Convert RGB (0-1) to HSL (H: 0-360, S: 0-1, L: 0-1)."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    # Lightness
    l = (cmax + cmin) / 2.0

    # Saturation
    s = np.where(delta == 0, 0.0, delta / (1.0 - np.abs(2.0 * l - 1.0) + 1e-10))

    # Hue
    h = np.zeros_like(l)
    mask_r = (cmax == r) & (delta > 0)
    mask_g = (cmax == g) & (delta > 0)
    mask_b = (cmax == b) & (delta > 0)
    h[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / (delta[mask_r] + 1e-10)) % 6)
    h[mask_g] = 60.0 * (((b[mask_g] - r[mask_g]) / (delta[mask_g] + 1e-10)) + 2)
    h[mask_b] = 60.0 * (((r[mask_b] - g[mask_b]) / (delta[mask_b] + 1e-10)) + 4)
    h = h % 360

    return np.stack([h, s, l], axis=-1)


def _hsl_to_rgb(hsl: np.ndarray) -> np.ndarray:
    """Convert HSL (H: 0-360, S: 0-1, L: 0-1) back to RGB (0-1)."""
    h, s, l = hsl[..., 0], hsl[..., 1], hsl[..., 2]
    c = (1.0 - np.abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - np.abs((h / 60.0) % 2 - 1.0))
    m = l - c / 2.0

    h_sector = (h / 60.0).astype(int) % 6
    r = np.zeros_like(h)
    g = np.zeros_like(h)
    b = np.zeros_like(h)

    for sector, (rv, gv, bv) in enumerate(
        [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0)]
    ):
        # Map sector -> (r1,g1,b1) using c and x
        pass

    # Direct approach for clarity
    mask = h_sector == 0
    r[mask], g[mask], b[mask] = c[mask], x[mask], 0
    mask = h_sector == 1
    r[mask], g[mask], b[mask] = x[mask], c[mask], 0
    mask = h_sector == 2
    r[mask], g[mask], b[mask] = 0, c[mask], x[mask]
    mask = h_sector == 3
    r[mask], g[mask], b[mask] = 0, x[mask], c[mask]
    mask = h_sector == 4
    r[mask], g[mask], b[mask] = x[mask], 0, c[mask]
    mask = h_sector == 5
    r[mask], g[mask], b[mask] = c[mask], 0, x[mask]

    return _clamp(np.stack([r + m, g + m, b + m], axis=-1))


# ---------------------------------------------------------------------------
# Basic adjustments
# ---------------------------------------------------------------------------

def adjust_exposure(img: np.ndarray, ev: float) -> np.ndarray:
    """Adjust exposure by EV stops. Operates in linear space."""
    if ev == 0:
        return img
    linear = _srgb_to_linear(img)
    linear = linear * (2.0 ** ev)
    return _clamp(_linear_to_srgb(linear))


def adjust_contrast(img: np.ndarray, amount: float) -> np.ndarray:
    """Adjust contrast. amount in [-100, 100]."""
    if amount == 0:
        return img
    factor = (amount + 100) / 100.0  # maps -100->0, 0->1, 100->2
    return _clamp(0.5 + factor * (img - 0.5))


def adjust_highlights(img: np.ndarray, amount: float) -> np.ndarray:
    """Adjust highlights (bright areas). amount in [-100, 100]."""
    if amount == 0:
        return img
    strength = amount / 100.0
    luminance = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    # Weight: affects pixels with luminance > 0.5, smoothly
    weight = np.clip((luminance - 0.5) * 2.0, 0, 1) ** 2
    weight = weight[..., np.newaxis]
    adjustment = strength * weight * 0.5
    return _clamp(img + adjustment)


def adjust_shadows(img: np.ndarray, amount: float) -> np.ndarray:
    """Adjust shadows (dark areas). amount in [-100, 100]."""
    if amount == 0:
        return img
    strength = amount / 100.0
    luminance = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    weight = np.clip((0.5 - luminance) * 2.0, 0, 1) ** 2
    weight = weight[..., np.newaxis]
    adjustment = strength * weight * 0.5
    return _clamp(img + adjustment)


def adjust_whites(img: np.ndarray, amount: float) -> np.ndarray:
    """Adjust white point. amount in [-100, 100]."""
    if amount == 0:
        return img
    strength = amount / 200.0  # Subtle effect
    luminance = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    weight = np.clip((luminance - 0.7) * 3.3, 0, 1)
    weight = weight[..., np.newaxis]
    return _clamp(img + strength * weight)


def adjust_blacks(img: np.ndarray, amount: float) -> np.ndarray:
    """Adjust black point. amount in [-100, 100]."""
    if amount == 0:
        return img
    strength = amount / 200.0
    luminance = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    weight = np.clip((0.3 - luminance) * 3.3, 0, 1)
    weight = weight[..., np.newaxis]
    return _clamp(img + strength * weight)


# ---------------------------------------------------------------------------
# Color adjustments
# ---------------------------------------------------------------------------

def adjust_temperature(img: np.ndarray, kelvin: float) -> np.ndarray:
    """Adjust color temperature. kelvin=6500 is neutral (no change)."""
    if kelvin == 6500:
        return img
    # Shift relative to neutral 6500K
    # Warmer (>6500): increase red, decrease blue
    # Cooler (<6500): decrease red, increase blue
    shift = (kelvin - 6500) / 5500.0  # Normalized to roughly [-1, 1]
    strength = shift * 0.15  # Keep subtle
    result = img.copy()
    result[..., 0] = img[..., 0] + strength       # Red
    result[..., 2] = img[..., 2] - strength        # Blue
    return _clamp(result)


def adjust_tint(img: np.ndarray, amount: float) -> np.ndarray:
    """Adjust green-magenta tint. amount in [-100, 100]."""
    if amount == 0:
        return img
    strength = amount / 100.0 * 0.1
    result = img.copy()
    result[..., 1] = img[..., 1] - strength  # Green
    result[..., 0] = img[..., 0] + strength * 0.5  # slight red push for magenta
    result[..., 2] = img[..., 2] + strength * 0.5  # slight blue push for magenta
    return _clamp(result)


def adjust_vibrance(img: np.ndarray, amount: float) -> np.ndarray:
    """Adjust vibrance (selective saturation boost for less-saturated colors)."""
    if amount == 0:
        return img
    strength = amount / 100.0
    hsl = _rgb_to_hsl(img)
    s = hsl[..., 1]
    # Boost less saturated colors more
    boost = strength * (1.0 - s) * 0.5
    hsl[..., 1] = np.clip(s + boost, 0, 1)
    return _hsl_to_rgb(hsl)


def adjust_saturation(img: np.ndarray, amount: float) -> np.ndarray:
    """Adjust global saturation. amount in [-100, 100]."""
    if amount == 0:
        return img
    factor = (amount + 100) / 100.0
    gray = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    gray = gray[..., np.newaxis]
    return _clamp(gray + factor * (img - gray))


# ---------------------------------------------------------------------------
# Tone curve
# ---------------------------------------------------------------------------

def apply_tone_curve(img: np.ndarray, points: list[list[int]],
                     red: list[list[int]] | None = None,
                     green: list[list[int]] | None = None,
                     blue: list[list[int]] | None = None) -> np.ndarray:
    """Apply tone curve using cubic spline interpolation.

    points: master curve [[x,y],...] with x,y in [0,255]
    red/green/blue: per-channel overrides (optional)
    """
    def _build_lut(pts: list[list[int]]) -> np.ndarray:
        pts = sorted(pts, key=lambda p: p[0])
        xs = [p[0] / 255.0 for p in pts]
        ys = [p[1] / 255.0 for p in pts]
        if len(xs) < 2:
            return np.linspace(0, 1, 256).astype(np.float32)
        cs = CubicSpline(xs, ys, bc_type='clamped')
        lut_x = np.linspace(0, 1, 256)
        lut_y = np.clip(cs(lut_x), 0, 1)
        return lut_y.astype(np.float32)

    # Check if master curve is identity
    default_pts = [[0, 0], [64, 64], [128, 128], [192, 192], [255, 255]]
    is_identity = (points == default_pts and red is None and green is None and blue is None)
    if is_identity:
        return img

    master_lut = _build_lut(points)
    img_255 = (img * 255).astype(np.uint8)
    result = np.zeros_like(img)

    for ch_idx, ch_pts in enumerate([red, green, blue]):
        ch_data = img_255[..., ch_idx]
        if ch_pts is not None:
            lut = _build_lut(ch_pts)
        else:
            lut = master_lut
        # Apply LUT
        result[..., ch_idx] = lut[ch_data]

    return _clamp(result)


# ---------------------------------------------------------------------------
# HSL per-channel adjustment
# ---------------------------------------------------------------------------

# Hue ranges (center, ±width) for each named color
_HSL_RANGES = {
    "red":     (0, 30),
    "orange":  (30, 30),
    "yellow":  (60, 30),
    "green":   (120, 60),
    "aqua":    (180, 30),
    "blue":    (240, 40),
    "purple":  (280, 30),
    "magenta": (320, 30),
}


def adjust_hsl(img: np.ndarray, hsl_params: dict[str, dict]) -> np.ndarray:
    """Apply per-color HSL adjustments.

    hsl_params: {"red": {"hue": 0, "saturation": 0, "luminance": 0}, ...}
    """
    # Check if all zero (no-op)
    has_adjustment = False
    for color, vals in hsl_params.items():
        if vals.get("hue", 0) != 0 or vals.get("saturation", 0) != 0 or vals.get("luminance", 0) != 0:
            has_adjustment = True
            break
    if not has_adjustment:
        return img

    hsl = _rgb_to_hsl(img)
    h, s, l = hsl[..., 0], hsl[..., 1], hsl[..., 2]

    for color_name, (center, width) in _HSL_RANGES.items():
        params = hsl_params.get(color_name, {})
        dh = params.get("hue", 0)
        ds = params.get("saturation", 0)
        dl = params.get("luminance", 0)
        if dh == 0 and ds == 0 and dl == 0:
            continue

        # Calculate weight based on hue distance from center
        hue_dist = np.minimum(np.abs(h - center), 360 - np.abs(h - center))
        weight = np.clip(1.0 - hue_dist / width, 0, 1)

        # Apply adjustments weighted by proximity
        h = h + dh * weight
        s = np.clip(s + (ds / 100.0) * weight, 0, 1)
        l = np.clip(l + (dl / 100.0) * weight * 0.5, 0, 1)

    h = h % 360
    hsl_out = np.stack([h, s, l], axis=-1)
    return _hsl_to_rgb(hsl_out)


# ---------------------------------------------------------------------------
# Split toning
# ---------------------------------------------------------------------------

def apply_split_toning(img: np.ndarray,
                       highlights_hue: float, highlights_sat: float,
                       shadows_hue: float, shadows_sat: float,
                       balance: float) -> np.ndarray:
    """Apply split toning - tint highlights and shadows with different colors."""
    if highlights_sat == 0 and shadows_sat == 0:
        return img

    luminance = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]

    # Balance shifts the midpoint
    midpoint = 0.5 + balance / 200.0

    result = img.copy()

    for hue, sat, is_highlight in [
        (highlights_hue, highlights_sat, True),
        (shadows_hue, shadows_sat, False),
    ]:
        if sat == 0:
            continue
        # Convert hue to RGB tint color
        h_rad = np.deg2rad(hue)
        tint_r = 0.5 + 0.5 * np.cos(h_rad)
        tint_g = 0.5 + 0.5 * np.cos(h_rad - 2.094)  # -120 degrees
        tint_b = 0.5 + 0.5 * np.cos(h_rad + 2.094)  # +120 degrees

        strength = sat / 100.0 * 0.3  # Keep subtle

        if is_highlight:
            weight = np.clip((luminance - midpoint) / (1.0 - midpoint + 1e-10), 0, 1)
        else:
            weight = np.clip((midpoint - luminance) / (midpoint + 1e-10), 0, 1)

        weight = weight[..., np.newaxis]
        tint = np.array([tint_r, tint_g, tint_b], dtype=np.float32)
        result = result + strength * weight * (tint - 0.5)

    return _clamp(result)


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

def adjust_clarity(img: np.ndarray, amount: float) -> np.ndarray:
    """Enhance midtone contrast (clarity) using unsharp mask on luminance.

    Uses a larger blur radius and gentler blending to avoid amplifying noise.
    """
    if amount == 0:
        return img
    strength = amount / 100.0
    # Convert to uint8 for OpenCV operations
    img_u8 = (img * 255).astype(np.uint8)
    gray = cv2.cvtColor(img_u8, cv2.COLOR_RGB2GRAY)
    # Large-radius blur for midtone detail (larger sigma = smoother = less noise)
    blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=20)
    # High-pass = original - blurred
    high_pass = gray.astype(np.float32) - blurred.astype(np.float32)
    high_pass = high_pass / 255.0
    # Suppress noise: only keep significant detail (threshold small values)
    high_pass = np.where(np.abs(high_pass) < 0.02, 0.0, high_pass)
    # Add weighted high-pass back to all channels (reduced strength)
    result = img + strength * 0.3 * high_pass[..., np.newaxis]
    return _clamp(result)


def adjust_dehaze(img: np.ndarray, amount: float) -> np.ndarray:
    """Dehaze using simplified dark channel prior.

    Improved to avoid amplifying noise in dark areas by using a gentler
    recovery and a minimum transmission floor.
    """
    if amount == 0:
        return img
    strength = amount / 100.0

    # Estimate atmospheric light (simplified)
    dark_channel = np.min(img, axis=2)
    # Use top 0.1% brightest pixels in dark channel to estimate A
    flat = dark_channel.flatten()
    num_pixels = max(int(flat.size * 0.001), 1)
    top_indices = np.argpartition(flat, -num_pixels)[-num_pixels:]
    atmospheric = np.mean(img.reshape(-1, 3)[top_indices], axis=0)
    atmospheric = np.maximum(atmospheric, 0.2)

    # Transmission estimate (higher floor to prevent noise amplification)
    normalized = img / atmospheric[np.newaxis, np.newaxis, :]
    transmission = 1.0 - strength * 0.7 * np.min(normalized, axis=2, keepdims=True)
    transmission = np.maximum(transmission, 0.3)  # Higher floor = less noise

    # Recover scene
    result = (img - atmospheric) / transmission + atmospheric
    return _clamp(result)


def apply_vignette(img: np.ndarray, amount: float) -> np.ndarray:
    """Apply vignette effect. Negative = darken edges, positive = lighten edges."""
    if amount == 0:
        return img
    h, w = img.shape[:2]
    y, x = np.ogrid[:h, :w]
    cy, cx = h / 2.0, w / 2.0
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist

    strength = amount / 100.0  # Negative amount = darken edges, positive = lighten
    vignette_mask = 1.0 + strength * (dist ** 2)
    vignette_mask = vignette_mask[..., np.newaxis]
    return _clamp(img * vignette_mask)


def apply_grain(img: np.ndarray, amount: float) -> np.ndarray:
    """Add film grain noise. Capped to very low strength to avoid quality loss."""
    if amount == 0:
        return img
    # Very gentle grain — cap at 5% noise to preserve quality
    strength = min(amount / 100.0, 0.05) * 0.1
    noise = np.random.normal(0, strength, img.shape).astype(np.float32)
    return _clamp(img + noise)
