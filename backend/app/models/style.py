import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, JSON

from app.database import Base


class StyleSession(Base):
    __tablename__ = "style_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="in_progress")
    created_at = Column(DateTime, default=datetime.utcnow)


class StyleRound(Base):
    __tablename__ = "style_rounds"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("style_sessions.id"), nullable=False)
    scene_type = Column(String)
    time_of_day = Column(String)
    weather = Column(String)
    original_image_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class StyleOption(Base):
    __tablename__ = "style_options"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    round_id = Column(String, ForeignKey("style_rounds.id"), nullable=False)
    style_name = Column(String)
    parameters = Column(JSON)
    preview_image_path = Column(String)
    is_selected = Column(Boolean, default=False)


class UserStyleProfile(Base):
    __tablename__ = "user_style_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, ForeignKey("style_sessions.id"), nullable=False)
    profile_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
