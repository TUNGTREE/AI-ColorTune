"""Grading service - manages color grading tasks and suggestions."""
from __future__ import annotations

import base64
import io
import uuid
from pathlib import Path

from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.config import settings
from app.core.color_params import ColorParams, sanitize_ai_params
from app.models.grading import GradingTask, GradingSuggestion, Export
from app.models.style import UserStyleProfile
from app.services.ai_provider import AIProvider
from app.services.image_processor import ImageProcessor


class GradingService:
    def __init__(self, db: Session, ai_provider: AIProvider | None = None):
        self.db = db
        self.ai = ai_provider
        self.processor = ImageProcessor()

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def create_task(self, user_id: str, image_path: str, profile_id: str | None = None) -> GradingTask:
        task = GradingTask(
            id=str(uuid.uuid4()),
            user_id=user_id,
            profile_id=profile_id,
            original_image_path=image_path,
            status="uploaded",
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_id: str) -> GradingTask | None:
        return self.db.get(GradingTask, task_id)

    def get_suggestions(self, task_id: str) -> list[GradingSuggestion]:
        return (
            self.db.query(GradingSuggestion)
            .filter(GradingSuggestion.task_id == task_id)
            .all()
        )

    # ------------------------------------------------------------------
    # Suggestion generation
    # ------------------------------------------------------------------

    async def generate_suggestions(self, task: GradingTask, num_suggestions: int = 3, custom_prompt: str | None = None) -> list[GradingSuggestion]:
        """Generate personalized grading suggestions using AI."""
        image_path = Path(task.original_image_path)
        img = self.processor.load_image(image_path)
        preview = self.processor.generate_preview(img)

        # Encode for AI
        preview_uint8 = (preview * 255).astype("uint8")
        pil_img = PILImage.fromarray(preview_uint8, "RGB")
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        image_b64 = base64.b64encode(buf.getvalue()).decode()

        # Get user profile if available
        user_profile = {}
        if task.profile_id:
            profile = self.db.get(UserStyleProfile, task.profile_id)
            if profile and profile.profile_data:
                user_profile = profile.profile_data

        # Generate suggestions via AI
        suggestions_data = await self.ai.generate_grading_suggestions(
            image_b64, user_profile, num_suggestions, custom_prompt=custom_prompt
        )

        # Create preview images and save suggestions
        suggestions = []
        for item in suggestions_data:
            params = ColorParams(**sanitize_ai_params(item["parameters"]))
            graded = self.processor.apply_params(preview, params)
            preview_id = str(uuid.uuid4())
            preview_path = settings.PREVIEW_DIR / f"{preview_id}.jpg"
            self.processor.save_image(graded, preview_path, fmt="JPEG")

            suggestion = GradingSuggestion(
                id=str(uuid.uuid4()),
                task_id=task.id,
                suggestion_name=item.get("suggestion_name", "Untitled"),
                parameters=params.model_dump(),
                preview_image_path=str(preview_path),
            )
            self.db.add(suggestion)
            suggestions.append(suggestion)

        task.status = "suggested"
        self.db.commit()
        for s in suggestions:
            self.db.refresh(s)
        return suggestions

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select_suggestion(self, task_id: str, suggestion_id: str) -> GradingSuggestion:
        self.db.query(GradingSuggestion).filter(
            GradingSuggestion.task_id == task_id
        ).update({"is_selected": False})

        suggestion = self.db.get(GradingSuggestion, suggestion_id)
        if suggestion is None or suggestion.task_id != task_id:
            raise ValueError(f"Suggestion {suggestion_id} not found in task {task_id}")
        suggestion.is_selected = True
        task = self.get_task(task_id)
        if task:
            task.status = "tuning"
        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def generate_preview(self, task: GradingTask, params: ColorParams) -> str:
        """Generate a preview image with custom parameters. Returns preview URL path."""
        image_path = Path(task.original_image_path)
        img = self.processor.load_image(image_path)
        preview = self.processor.generate_preview(img)
        graded = self.processor.apply_params(preview, params)
        preview_id = str(uuid.uuid4())
        preview_path = settings.PREVIEW_DIR / f"{preview_id}.jpg"
        self.processor.save_image(graded, preview_path, fmt="JPEG")
        return f"/previews/{preview_path.name}"

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_image(
        self, task: GradingTask, params: ColorParams, fmt: str = "jpeg", quality: int = 95
    ) -> Export:
        """Apply params at full resolution and export."""
        image_path = Path(task.original_image_path)
        img = self.processor.load_image(image_path)
        graded = self.processor.apply_params(img, params)

        export_id = str(uuid.uuid4())
        ext = {"jpeg": "jpg", "png": "png", "tiff": "tif"}.get(fmt.lower(), "jpg")
        output_path = settings.EXPORT_DIR / f"{export_id}.{ext}"
        pil_fmt = {"jpeg": "JPEG", "png": "PNG", "tiff": "TIFF"}.get(fmt.lower(), "JPEG")
        self.processor.save_image(graded, output_path, fmt=pil_fmt, quality=quality)

        export = Export(
            id=export_id,
            task_id=task.id,
            final_parameters=params.model_dump(),
            output_image_path=str(output_path),
            export_format=fmt.lower(),
            quality=quality,
        )
        self.db.add(export)
        task.status = "exported"
        self.db.commit()
        self.db.refresh(export)
        return export
