"""Style discovery service - manages the style preference workflow."""
from __future__ import annotations

import base64
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.core.color_params import ColorParams, sanitize_ai_params
from app.models.user import User
from app.models.style import StyleSession, StyleRound, StyleOption, UserStyleProfile
from app.services.ai_provider import AIProvider
from app.services.image_processor import ImageProcessor


class StyleService:
    def __init__(self, db: Session, ai_provider: AIProvider | None = None):
        self.db = db
        self.ai = ai_provider
        self.processor = ImageProcessor()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(self, user_id: str | None = None) -> StyleSession:
        if user_id is None:
            user = User(id=str(uuid.uuid4()))
            self.db.add(user)
            self.db.flush()
            user_id = user.id
        else:
            user = self.db.get(User, user_id)
            if user is None:
                user = User(id=user_id)
                self.db.add(user)
                self.db.flush()

        session = StyleSession(id=str(uuid.uuid4()), user_id=user_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str) -> StyleSession | None:
        return self.db.get(StyleSession, session_id)

    def get_session_rounds(self, session_id: str) -> list[StyleRound]:
        return (
            self.db.query(StyleRound)
            .filter(StyleRound.session_id == session_id)
            .order_by(StyleRound.created_at)
            .all()
        )

    # ------------------------------------------------------------------
    # Round management
    # ------------------------------------------------------------------

    def create_round(
        self,
        session_id: str,
        image_path: str,
        scene_type: str | None = None,
        time_of_day: str | None = None,
        weather: str | None = None,
    ) -> StyleRound:
        round_obj = StyleRound(
            id=str(uuid.uuid4()),
            session_id=session_id,
            scene_type=scene_type,
            time_of_day=time_of_day,
            weather=weather,
            original_image_path=image_path,
        )
        self.db.add(round_obj)
        self.db.commit()
        self.db.refresh(round_obj)
        return round_obj

    def get_round_options(self, round_id: str) -> list[StyleOption]:
        return (
            self.db.query(StyleOption)
            .filter(StyleOption.round_id == round_id)
            .all()
        )

    async def generate_options_for_round(
        self, round_obj: StyleRound, num_styles: int = 4
    ) -> list[StyleOption]:
        """Use AI to analyze the image and generate style options."""
        image_path = Path(round_obj.original_image_path)
        img = self.processor.load_image(image_path)
        preview = self.processor.generate_preview(img)

        # Encode for AI
        import io
        from PIL import Image as PILImage
        preview_uint8 = (preview * 255).astype("uint8")
        pil_img = PILImage.fromarray(preview_uint8, "RGB")
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        image_b64 = base64.b64encode(buf.getvalue()).decode()

        # Step 1: Analyze scene
        scene_info = await self.ai.analyze_scene(image_b64)

        # Update round with scene info
        round_obj.scene_type = round_obj.scene_type or scene_info.get("scene_type")
        round_obj.time_of_day = round_obj.time_of_day or scene_info.get("time_of_day")
        round_obj.weather = round_obj.weather or scene_info.get("weather")

        # Step 2: Generate style options
        style_data = await self.ai.generate_style_options(image_b64, scene_info, num_styles)

        # Step 3: Create preview images and save options
        options = []
        for item in style_data:
            params = ColorParams(**sanitize_ai_params(item["parameters"]))
            # Generate preview
            graded = self.processor.apply_params(preview, params)
            preview_id = str(uuid.uuid4())
            preview_path = settings.PREVIEW_DIR / f"{preview_id}.jpg"
            self.processor.save_image(graded, preview_path, fmt="JPEG")

            option = StyleOption(
                id=str(uuid.uuid4()),
                round_id=round_obj.id,
                style_name=item.get("style_name", "Untitled"),
                parameters=params.model_dump(),
                preview_image_path=str(preview_path),
            )
            self.db.add(option)
            options.append(option)

        self.db.commit()
        for opt in options:
            self.db.refresh(opt)
        return options

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select_option(self, round_id: str, option_id: str) -> StyleOption:
        # Deselect all for this round
        self.db.query(StyleOption).filter(
            StyleOption.round_id == round_id
        ).update({"is_selected": False})

        option = self.db.get(StyleOption, option_id)
        if option is None or option.round_id != round_id:
            raise ValueError(f"Option {option_id} not found in round {round_id}")
        option.is_selected = True
        self.db.commit()
        self.db.refresh(option)
        return option

    # ------------------------------------------------------------------
    # Preference analysis
    # ------------------------------------------------------------------

    def get_selections_summary(self, session_id: str) -> list[dict]:
        """Gather all selected styles across rounds for analysis."""
        rounds = self.get_session_rounds(session_id)
        selections = []
        for r in rounds:
            selected = (
                self.db.query(StyleOption)
                .filter(StyleOption.round_id == r.id, StyleOption.is_selected == True)
                .first()
            )
            if selected:
                all_options = self.get_round_options(r.id)
                selections.append({
                    "round": {
                        "scene_type": r.scene_type,
                        "time_of_day": r.time_of_day,
                        "weather": r.weather,
                    },
                    "selected_style": selected.style_name,
                    "selected_parameters": selected.parameters,
                    "all_options": [
                        {"style_name": o.style_name, "was_selected": o.is_selected}
                        for o in all_options
                    ],
                })
        return selections

    async def analyze_preferences(self, session_id: str) -> UserStyleProfile:
        """Analyze all selections and create user style profile."""
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        selections = self.get_selections_summary(session_id)
        if not selections:
            raise ValueError("No selections found in session")

        profile_data = await self.ai.analyze_preferences(selections)

        profile = UserStyleProfile(
            id=str(uuid.uuid4()),
            user_id=session.user_id,
            session_id=session_id,
            profile_data=profile_data,
        )
        self.db.add(profile)

        session.status = "completed"
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_profile(self, profile_id: str) -> UserStyleProfile | None:
        return self.db.get(UserStyleProfile, profile_id)
