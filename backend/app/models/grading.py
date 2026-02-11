import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, JSON, Integer

from app.database import Base


class GradingTask(Base):
    __tablename__ = "grading_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    profile_id = Column(String, ForeignKey("user_style_profiles.id"), nullable=True)
    original_image_path = Column(String)
    status = Column(String, default="uploaded")
    created_at = Column(DateTime, default=datetime.utcnow)


class GradingSuggestion(Base):
    __tablename__ = "grading_suggestions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("grading_tasks.id"), nullable=False)
    suggestion_name = Column(String)
    parameters = Column(JSON)
    preview_image_path = Column(String)
    is_selected = Column(Boolean, default=False)


class Export(Base):
    __tablename__ = "exports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("grading_tasks.id"), nullable=False)
    final_parameters = Column(JSON)
    output_image_path = Column(String)
    export_format = Column(String)
    quality = Column(Integer, default=95)
    created_at = Column(DateTime, default=datetime.utcnow)
