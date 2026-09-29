"""ComicCraft - FastAPI entry point.  Run with:  uvicorn app.main:app --reload"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .routes import router

app = FastAPI(
    title="ComicCraft",
    description="Generate comic stories with Gemini and Stable Diffusion, then export them as PDF.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(router)
