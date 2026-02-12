from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "ColorTune"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./colortune.db"
    UPLOAD_DIR: Path = Path(__file__).resolve().parent.parent.parent / "uploads"
    PREVIEW_DIR: Path = Path(__file__).resolve().parent.parent.parent / "previews"
    EXPORT_DIR: Path = Path(__file__).resolve().parent.parent.parent / "exports"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    PREVIEW_MAX_WIDTH: int = 800
    ALLOWED_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "tiff", "tif", "bmp", "webp"}

    # AI Provider settings
    CLAUDE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""  # Custom base URL for OpenAI-compatible APIs (e.g. DashScope)
    DEEPSEEK_API_KEY: str = ""
    GLM_API_KEY: str = ""
    DEFAULT_AI_PROVIDER: str = "openai"
    DEFAULT_AI_MODEL: str = ""  # Default model name (e.g. qwen-vl-plus)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
