"""Sample scene image generator for style discovery.

Generates abstract but colorful sample images for different scene/time-of-day
combinations.  Images are 800x533 JPEG, cached in the samples/ directory.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from app.config import settings

# ---------------------------------------------------------------------------
# Scene definitions
# ---------------------------------------------------------------------------

SAMPLES: list[dict] = [
    {
        "id": "street_sunrise",
        "scene_type": "street",
        "time_of_day": "sunrise",
        "label_zh": "街道 - 日出",
        "label_en": "Street - Sunrise",
        "palette": [(255, 160, 80), (120, 140, 170), (200, 120, 60), (80, 90, 120)],
    },
    {
        "id": "city_night",
        "scene_type": "city",
        "time_of_day": "night",
        "label_zh": "城市 - 夜晚",
        "label_en": "City - Night",
        "palette": [(20, 30, 80), (255, 60, 150), (60, 220, 255), (30, 20, 60)],
    },
    {
        "id": "grassland_noon",
        "scene_type": "grassland",
        "time_of_day": "noon",
        "label_zh": "草原 - 正午",
        "label_en": "Grassland - Noon",
        "palette": [(100, 200, 60), (60, 160, 40), (120, 200, 240), (180, 220, 80)],
    },
    {
        "id": "ocean_sunset",
        "scene_type": "ocean",
        "time_of_day": "sunset",
        "label_zh": "海洋 - 日落",
        "label_en": "Ocean - Sunset",
        "palette": [(20, 50, 120), (255, 120, 40), (200, 60, 30), (30, 80, 160)],
    },
    {
        "id": "desert_golden_hour",
        "scene_type": "desert",
        "time_of_day": "golden_hour",
        "label_zh": "沙漠 - 黄金时刻",
        "label_en": "Desert - Golden Hour",
        "palette": [(220, 180, 60), (180, 130, 50), (240, 200, 100), (160, 110, 40)],
    },
    {
        "id": "forest_blue_hour",
        "scene_type": "forest",
        "time_of_day": "blue_hour",
        "label_zh": "森林 - 蓝调时刻",
        "label_en": "Forest - Blue Hour",
        "palette": [(20, 80, 50), (40, 60, 120), (30, 100, 70), (50, 70, 140)],
    },
    {
        "id": "snowy_mountain_dawn",
        "scene_type": "snowy_mountain",
        "time_of_day": "dawn",
        "label_zh": "雪山 - 清晨",
        "label_en": "Snowy Mountain - Dawn",
        "palette": [(230, 230, 250), (200, 180, 220), (180, 200, 240), (240, 210, 230)],
    },
    {
        "id": "indoor_evening",
        "scene_type": "indoor",
        "time_of_day": "evening",
        "label_zh": "室内 - 傍晚",
        "label_en": "Indoor - Evening",
        "palette": [(220, 180, 100), (180, 140, 80), (160, 120, 60), (200, 160, 90)],
    },
    {
        "id": "beach_noon",
        "scene_type": "beach",
        "time_of_day": "noon",
        "label_zh": "海滩 - 正午",
        "label_en": "Beach - Noon",
        "palette": [(40, 200, 180), (240, 220, 140), (60, 180, 200), (220, 200, 120)],
    },
    {
        "id": "lake_sunrise",
        "scene_type": "lake",
        "time_of_day": "sunrise",
        "label_zh": "湖泊 - 日出",
        "label_en": "Lake - Sunrise",
        "palette": [(80, 120, 180), (255, 160, 80), (60, 100, 160), (220, 140, 60)],
    },
    {
        "id": "valley_sunset",
        "scene_type": "valley",
        "time_of_day": "sunset",
        "label_zh": "山谷 - 日落",
        "label_en": "Valley - Sunset",
        "palette": [(180, 60, 100), (60, 120, 50), (200, 80, 120), (40, 100, 60)],
    },
    {
        "id": "skyline_blue_hour",
        "scene_type": "skyline",
        "time_of_day": "blue_hour",
        "label_zh": "城市天际线 - 蓝调时刻",
        "label_en": "Skyline - Blue Hour",
        "palette": [(60, 90, 150), (200, 170, 100), (40, 70, 130), (180, 150, 80)],
    },
]

W, H = 800, 533


def _samples_dir() -> Path:
    """Return the samples directory, creating it if needed."""
    d = Path(settings.UPLOAD_DIR).parent / "samples"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _generate_image(sample: dict) -> Path:
    """Generate an abstract landscape-style image for the given sample definition."""
    rng = np.random.RandomState(int(hashlib.md5(sample["id"].encode()).hexdigest()[:8], 16))
    palette = sample["palette"]

    # Start with a gradient background (sky → ground)
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Sky gradient (top color → mid color)
    top_color = palette[0]
    mid_color = palette[1]
    for y in range(H):
        t = y / H
        r = int(top_color[0] * (1 - t) + mid_color[0] * t)
        g = int(top_color[1] * (1 - t) + mid_color[1] * t)
        b = int(top_color[2] * (1 - t) + mid_color[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Add abstract shapes
    for _ in range(rng.randint(8, 15)):
        shape_color = palette[rng.randint(0, len(palette))]
        alpha = rng.randint(60, 180)
        cx = rng.randint(0, W)
        cy = rng.randint(0, H)
        rx = rng.randint(40, 250)
        ry = rng.randint(30, 200)

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry],
            fill=(*shape_color, alpha),
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Add some horizontal bands for landscape feel
    horizon = int(H * (0.4 + rng.random() * 0.2))
    ground_color = palette[2] if len(palette) > 2 else palette[0]
    accent_color = palette[3] if len(palette) > 3 else palette[1]

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [0, horizon, W, H],
        fill=(*ground_color, 140),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Add wavy pattern
    wave_arr = np.array(img, dtype=np.float32)
    for i in range(3):
        freq = rng.uniform(0.005, 0.02)
        amp = rng.uniform(10, 30)
        phase = rng.uniform(0, 2 * np.pi)
        x_coords = np.arange(W)
        wave = (np.sin(x_coords * freq + phase) * amp).astype(int)
        for x in range(W):
            shift = wave[x]
            col = wave_arr[:, x, :].copy()
            wave_arr[:, x, :] = np.roll(col, shift, axis=0)
    img = Image.fromarray(np.clip(wave_arr, 0, 255).astype(np.uint8))

    # Add subtle light spots
    for _ in range(rng.randint(2, 5)):
        spot_color = accent_color
        sx = rng.randint(0, W)
        sy = rng.randint(0, H)
        sr = rng.randint(80, 200)
        spot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        spot_draw = ImageDraw.Draw(spot)
        spot_draw.ellipse(
            [sx - sr, sy - sr, sx + sr, sy + sr],
            fill=(*spot_color, rng.randint(40, 100)),
        )
        img = Image.alpha_composite(img.convert("RGBA"), spot).convert("RGB")

    # Apply Gaussian blur for a soft, painterly look
    img = img.filter(ImageFilter.GaussianBlur(radius=6))

    # Save
    path = _samples_dir() / f"{sample['id']}.jpg"
    img.save(path, "JPEG", quality=90)
    return path


def _ensure_generated() -> None:
    """Generate all sample images if they don't exist."""
    samples_dir = _samples_dir()
    for sample in SAMPLES:
        path = samples_dir / f"{sample['id']}.jpg"
        if not path.exists():
            _generate_image(sample)


def get_sample_list() -> list[dict]:
    """Return list of available sample scene metadata.

    Returns:
        List of dicts with id, scene_type, time_of_day, label_zh, label_en, thumbnail_url
    """
    _ensure_generated()
    result = []
    for s in SAMPLES:
        result.append({
            "id": s["id"],
            "scene_type": s["scene_type"],
            "time_of_day": s["time_of_day"],
            "label_zh": s["label_zh"],
            "label_en": s["label_en"],
            "thumbnail_url": f"/samples/{s['id']}.jpg",
        })
    return result


def get_sample_image_path(sample_id: str) -> Path | None:
    """Return the file path for a sample image, or None if not found."""
    _ensure_generated()
    for s in SAMPLES:
        if s["id"] == sample_id:
            path = _samples_dir() / f"{s['id']}.jpg"
            if path.exists():
                return path
    return None
