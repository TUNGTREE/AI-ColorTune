"""Image processing service - applies ColorParams to images."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.core.color_params import ColorParams
from app.core import image_ops
from app.config import settings


class ImageProcessor:
    """Loads an image, applies color grading parameters, outputs result."""

    @staticmethod
    def load_image(path: str | Path) -> np.ndarray:
        """Load image as float32 RGB numpy array in [0, 1] range."""
        img = Image.open(path).convert("RGB")
        return np.array(img, dtype=np.float32) / 255.0

    @staticmethod
    def save_image(img: np.ndarray, path: str | Path, fmt: str = "JPEG", quality: int = 95) -> Path:
        """Save float32 RGB array to file."""
        path = Path(path)
        img_uint8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        pil_img = Image.fromarray(img_uint8, "RGB")
        save_kwargs = {}
        if fmt.upper() in ("JPEG", "JPG"):
            save_kwargs["quality"] = quality
        pil_img.save(path, format=fmt, **save_kwargs)
        return path

    @staticmethod
    def generate_preview(img: np.ndarray, max_width: int | None = None) -> np.ndarray:
        """Resize image for preview (maintains aspect ratio)."""
        if max_width is None:
            max_width = settings.PREVIEW_MAX_WIDTH
        h, w = img.shape[:2]
        if w <= max_width:
            return img
        scale = max_width / w
        new_w = max_width
        new_h = int(h * scale)
        img_uint8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        pil_img = Image.fromarray(img_uint8, "RGB")
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
        return np.array(pil_img, dtype=np.float32) / 255.0

    @staticmethod
    def apply_params(img: np.ndarray, params: ColorParams) -> np.ndarray:
        """Apply all color grading parameters to an image."""
        result = img.copy()

        # 1. Basic adjustments
        b = params.basic
        result = image_ops.adjust_exposure(result, b.exposure)
        result = image_ops.adjust_contrast(result, b.contrast)
        result = image_ops.adjust_highlights(result, b.highlights)
        result = image_ops.adjust_shadows(result, b.shadows)
        result = image_ops.adjust_whites(result, b.whites)
        result = image_ops.adjust_blacks(result, b.blacks)

        # 2. Color adjustments
        c = params.color
        result = image_ops.adjust_temperature(result, c.temperature)
        result = image_ops.adjust_tint(result, c.tint)
        result = image_ops.adjust_vibrance(result, c.vibrance)
        result = image_ops.adjust_saturation(result, c.saturation)

        # 3. Tone curve
        tc = params.tone_curve
        result = image_ops.apply_tone_curve(
            result, tc.points,
            red=tc.red, green=tc.green, blue=tc.blue,
        )

        # 4. HSL adjustments
        hsl_dict = params.hsl.model_dump()
        result = image_ops.adjust_hsl(result, hsl_dict)

        # 5. Color grading (3-way split toning)
        st = params.split_toning
        result = image_ops.apply_split_toning_3way(
            result,
            st.highlights.hue, st.highlights.saturation,
            st.midtones.hue, st.midtones.saturation,
            st.shadows.hue, st.shadows.saturation,
            st.balance,
        )

        # 6. Effects
        e = params.effects
        result = image_ops.adjust_clarity(result, e.clarity)
        result = image_ops.adjust_texture(result, e.texture)
        result = image_ops.adjust_dehaze(result, e.dehaze)
        result = image_ops.apply_fade(result, e.fade)
        result = image_ops.apply_sharpening(result, e.sharpening, e.sharpen_radius)
        result = image_ops.apply_vignette(result, e.vignette)
        result = image_ops.apply_grain(result, e.grain)

        return np.clip(result, 0.0, 1.0)

    @staticmethod
    def create_selection_mask(
        h: int, w: int,
        region_type: str,
        x: float, y: float,
        width: float, height: float,
        feather: float = 20,
    ) -> np.ndarray:
        """Create a feathered selection mask from normalized coordinates.

        Returns a float32 mask of shape (h, w) with values in [0, 1].
        """
        mask = np.zeros((h, w), dtype=np.float32)

        # Convert normalized coords to pixel coords
        px = int(x * w)
        py = int(y * h)
        pw = int(width * w)
        ph = int(height * h)

        if region_type == 'rect':
            mask[py:py + ph, px:px + pw] = 1.0
        elif region_type == 'ellipse':
            cy = py + ph / 2.0
            cx = px + pw / 2.0
            ry = ph / 2.0
            rx = pw / 2.0
            if rx < 1 or ry < 1:
                return mask
            yy, xx = np.ogrid[:h, :w]
            ellipse_dist = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
            mask[ellipse_dist <= 1.0] = 1.0

        # Apply feathering via Gaussian blur
        if feather > 0:
            blur_size = max(int(feather / 100.0 * min(h, w) * 0.1), 1)
            # Ensure odd kernel size
            blur_size = blur_size * 2 + 1
            mask = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)

        return mask

    @staticmethod
    def apply_local_adjustments(
        img: np.ndarray,
        global_result: np.ndarray,
        local_adjustments: list[dict],
    ) -> np.ndarray:
        """Apply local adjustments on top of the globally-graded image.

        Each local adjustment specifies a region and partial ColorParams.
        The local params are applied to the original image, then blended
        with the global result using the feathered selection mask.
        """
        if not local_adjustments:
            return global_result

        h, w = img.shape[:2]
        result = global_result.copy()

        for adj in local_adjustments:
            region = adj.get("region", {})
            params_dict = adj.get("parameters", {})

            # Build a ColorParams with the local overrides merged onto defaults
            from app.core.color_params import ColorParams as CP
            local_params = CP(**params_dict)

            # Create the feathered mask
            mask = ImageProcessor.create_selection_mask(
                h, w,
                region_type=region.get("type", "rect"),
                x=region.get("x", 0),
                y=region.get("y", 0),
                width=region.get("width", 0),
                height=region.get("height", 0),
                feather=region.get("feather", 20),
            )

            # Apply local params to original image
            local_result = ImageProcessor.apply_params(img, local_params)

            # Blend: result = mask * local_result + (1 - mask) * global_result
            mask_3d = mask[..., np.newaxis]
            result = mask_3d * local_result + (1.0 - mask_3d) * result

        return np.clip(result, 0.0, 1.0)
