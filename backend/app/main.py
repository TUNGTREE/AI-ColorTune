from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_tables
from app.api.upload import router as upload_router
from app.api.ai_config import router as ai_config_router
from app.api.style import router as style_router
from app.api.grading import router as grading_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup
    create_tables()
    # Ensure samples directory exists and generate sample images
    samples_dir = Path(settings.UPLOAD_DIR).parent / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown (nothing to clean up for now)


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure storage directories exist
for d in [settings.UPLOAD_DIR, settings.PREVIEW_DIR, settings.EXPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Samples directory
_samples_dir = Path(settings.UPLOAD_DIR).parent / "samples"
_samples_dir.mkdir(parents=True, exist_ok=True)

# Mount static file directories
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")
app.mount("/previews", StaticFiles(directory=str(settings.PREVIEW_DIR)), name="previews")
app.mount("/exports", StaticFiles(directory=str(settings.EXPORT_DIR)), name="exports")
app.mount("/samples", StaticFiles(directory=str(_samples_dir)), name="samples")

# Routers
app.include_router(upload_router, prefix="/api")
app.include_router(ai_config_router)
app.include_router(style_router)
app.include_router(grading_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
