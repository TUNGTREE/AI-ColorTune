"""Sample scene image provider for style discovery.

Downloads real photographs from Unsplash for each scene, matched to the
scene type and time of day.  Falls back to generating abstract images
if download fails.  Images are 800x533 JPEG, cached in the samples/ directory.
"""
from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scene definitions — each has an Unsplash photo ID verified to match
# ---------------------------------------------------------------------------

SAMPLES: list[dict] = [
    {
        "id": "street_sunrise",
        "scene_type": "street",
        "time_of_day": "sunrise",
        "label_zh": "街道 · 日出",
        "label_en": "Street · Sunrise",
        "unsplash_id": "A50wotF426U",  # City skyline at sunrise, golden light
    },
    {
        "id": "city_night",
        "scene_type": "city",
        "time_of_day": "night",
        "label_zh": "城市 · 夜晚",
        "label_en": "City · Night",
        "unsplash_id": "SdJ6LRWFg_Q",  # Vibrant cityscape at night
    },
    {
        "id": "grassland_noon",
        "scene_type": "grassland",
        "time_of_day": "noon",
        "label_zh": "草原 · 正午",
        "label_en": "Grassland · Noon",
        "unsplash_id": "PjNRxr0WpeQ",  # Green grass field
    },
    {
        "id": "ocean_sunset",
        "scene_type": "ocean",
        "time_of_day": "sunset",
        "label_zh": "海洋 · 日落",
        "label_en": "Ocean · Sunset",
        "unsplash_id": "baUCQY1pz40",  # Sun setting over ocean
    },
    {
        "id": "desert_golden_hour",
        "scene_type": "desert",
        "time_of_day": "golden_hour",
        "label_zh": "沙漠 · 黄金时刻",
        "label_en": "Desert · Golden Hour",
        "unsplash_id": "BhtjXDK_4V8",  # Golden sunlight on desert sand dunes
    },
    {
        "id": "forest_blue_hour",
        "scene_type": "forest",
        "time_of_day": "blue_hour",
        "label_zh": "森林 · 蓝调时刻",
        "label_en": "Forest · Blue Hour",
        "unsplash_id": "XVqzf6OG61k",  # Forest trees at blue hour
    },
    {
        "id": "snowy_mountain_dawn",
        "scene_type": "snowy_mountain",
        "time_of_day": "dawn",
        "label_zh": "雪山 · 清晨",
        "label_en": "Snowy Mountain · Dawn",
        "unsplash_id": "B0mydNIV-sI",  # Mount Kazbek at dawn
    },
    {
        "id": "indoor_evening",
        "scene_type": "indoor",
        "time_of_day": "evening",
        "label_zh": "室内 · 傍晚",
        "label_en": "Indoor · Evening",
        "unsplash_id": "TIO35YHf0ik",  # Cozy dimly-lit corner with warm lamp
    },
    {
        "id": "beach_noon",
        "scene_type": "beach",
        "time_of_day": "noon",
        "label_zh": "海滩 · 正午",
        "label_en": "Beach · Noon",
        "unsplash_id": "V1hb2SLP-80",  # Beach with turquoise water, El Nido
    },
    {
        "id": "lake_sunrise",
        "scene_type": "lake",
        "time_of_day": "sunrise",
        "label_zh": "湖泊 · 日出",
        "label_en": "Lake · Sunrise",
        "unsplash_id": "fT1d2SXi1R8",  # Mountain reflection in lake at sunrise
    },
    {
        "id": "valley_sunset",
        "scene_type": "valley",
        "time_of_day": "sunset",
        "label_zh": "山谷 · 日落",
        "label_en": "Valley · Sunset",
        "unsplash_id": "7gL6x-DUz1Q",  # Valley with mountains, Italy sunset
    },
    {
        "id": "skyline_blue_hour",
        "scene_type": "skyline",
        "time_of_day": "blue_hour",
        "label_zh": "天际线 · 蓝调时刻",
        "label_en": "Skyline · Blue Hour",
        "unsplash_id": "Gb4pnnlVRxk",  # Beijing skyline at dusk
    },
]

W, H = 800, 533

_SAMPLES_VERSION = 3  # Bump to force re-download (v1=abstract, v2=picsum, v3=unsplash)


def _samples_dir() -> Path:
    """Return the samples directory, creating it if needed."""
    d = Path(settings.UPLOAD_DIR).parent / "samples"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download_photo(sample: dict) -> Path | None:
    """Download a photo from Unsplash. Returns path or None on failure."""
    import httpx

    unsplash_id = sample.get("unsplash_id")
    if not unsplash_id:
        return None

    url = f"https://unsplash.com/photos/{unsplash_id}/download?w={W}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30, headers=headers)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        # Crop to exact dimensions
        img = img.resize((W, H), Image.LANCZOS)
        path = _samples_dir() / f"{sample['id']}.jpg"
        img.save(path, "JPEG", quality=92)
        logger.info("Downloaded sample photo for %s (unsplash #%s)", sample["id"], unsplash_id)
        return path
    except Exception as e:
        logger.warning("Failed to download photo for %s: %s", sample["id"], e)
        return None


def _generate_fallback(sample: dict) -> Path:
    """Generate an abstract fallback image when download fails."""
    rng = np.random.RandomState(
        int(hashlib.md5(sample["id"].encode()).hexdigest()[:8], 16)
    )
    palette = [
        (rng.randint(50, 255), rng.randint(50, 255), rng.randint(50, 255))
        for _ in range(4)
    ]

    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    c0, c1 = palette[0], palette[1]
    for y in range(H):
        t = y / H
        r = int(c0[0] * (1 - t) + c1[0] * t)
        g = int(c0[1] * (1 - t) + c1[1] * t)
        b = int(c0[2] * (1 - t) + c1[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    for _ in range(rng.randint(6, 12)):
        sc = palette[rng.randint(0, len(palette))]
        cx, cy = rng.randint(0, W), rng.randint(0, H)
        rx, ry = rng.randint(60, 250), rng.randint(40, 200)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(overlay).ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry],
            fill=(*sc, rng.randint(60, 160)),
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    img = img.filter(ImageFilter.GaussianBlur(radius=8))
    path = _samples_dir() / f"{sample['id']}.jpg"
    img.save(path, "JPEG", quality=90)
    return path


def _ensure_generated() -> None:
    """Download / generate all sample images if they don't exist or are outdated."""
    samples_dir = _samples_dir()
    version_file = samples_dir / ".version"

    # Check version — if outdated, delete all cached images
    current_version = 0
    if version_file.exists():
        try:
            current_version = int(version_file.read_text().strip())
        except (ValueError, OSError):
            current_version = 0

    if current_version < _SAMPLES_VERSION:
        for sample in SAMPLES:
            p = samples_dir / f"{sample['id']}.jpg"
            if p.exists():
                p.unlink()
        logger.info("Cleared outdated sample images (v%s → v%s)", current_version, _SAMPLES_VERSION)

    for sample in SAMPLES:
        path = samples_dir / f"{sample['id']}.jpg"
        if not path.exists():
            downloaded = _download_photo(sample)
            if downloaded is None:
                _generate_fallback(sample)

    # Write version marker
    version_file.write_text(str(_SAMPLES_VERSION))


def get_sample_list() -> list[dict]:
    """Return list of available sample scene metadata."""
    _ensure_generated()
    return [
        {
            "id": s["id"],
            "scene_type": s["scene_type"],
            "time_of_day": s["time_of_day"],
            "label_zh": s["label_zh"],
            "label_en": s["label_en"],
            "thumbnail_url": f"/samples/{s['id']}.jpg",
        }
        for s in SAMPLES
    ]


def get_sample_image_path(sample_id: str) -> Path | None:
    """Return the file path for a sample image, or None if not found."""
    _ensure_generated()
    for s in SAMPLES:
        if s["id"] == sample_id:
            path = _samples_dir() / f"{s['id']}.jpg"
            if path.exists():
                return path
    return None
