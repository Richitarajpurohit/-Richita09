"""All FastAPI routes for ComicCraft."""
import traceback
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import (
    EXPORTS_DIR, GEMINI_API_KEY, GEMINI_FLASH_MODEL, GEMINI_PRO_MODEL, SD_MODEL_ID,
    TEMPLATES_DIR, USE_PLACEHOLDER_IMAGES,
)
from .errors import ComicGenerationError
from .exporters import save_pdf
from .gemini_flash import generate_outline
from .gemini_pro import generate_story
from .image_generator import generate_image
from .layout_builder import build_comic_layout

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

STYLE_HINTS = {
    "anime": "anime style, vibrant colors, clean line art, cel shading",
    "pixel art": "pixel art, 16-bit retro video game style",
    "comic book": "classic comic book style, bold ink outlines, halftone shading, vivid colors",
    "realistic": "realistic digital painting, highly detailed, cinematic lighting",
}


class PromptRequest(BaseModel):
    """JSON body for /generate-comic/json."""
    prompt: str = Field(..., min_length=3, examples=["A brave fox exploring an enchanted forest."])
    character_name: str = Field("Hero", examples=["Finn"])
    setting: str = Field("forest", examples=["forest"])
    tone: str = Field("dramatic", examples=["dramatic"])
    style: str = Field("comic book", examples=["comic book"])


def run_pipeline(prompt: str, character_name: str, setting: str, tone: str, style: str):
    """outline -> story -> images -> layout -> PDF.  Returns (layout, pdf_path)."""
    full_prompt = (
        f"{prompt.strip()}\n"
        f"The main character is {character_name}. "
        f"The setting is a {setting}. "
        f"The tone is {tone}. The art style is {style}."
    )

    outline = generate_outline(full_prompt)                                   # Gemini Flash
    story = generate_story(outline, tone=tone, character_name=character_name)  # Gemini Pro

    style_hint = STYLE_HINTS.get(style.strip().lower(), f"{style} style")
    image_paths = [
        generate_image(f"{style_hint}, {panel['image_prompt']}, {setting} setting")  # Stable Diffusion
        for panel in outline
    ]

    layout = build_comic_layout(image_paths, story, outline)
    pdf_path = save_pdf(layout)
    return layout, pdf_path


def _pdf_urls(pdf_path: str):
    name = Path(pdf_path).name
    return name, f"/static/exports/{name}"


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"error": None, "form": {}})


@router.post("/generate", response_class=HTMLResponse)
def generate_comic(
    request: Request,
    prompt: str = Form(...),
    character_name: str = Form(...),
    setting: str = Form(...),
    tone: str = Form(...),
    style: str = Form(...),
):
    # Plain `def` on purpose: FastAPI runs it in a worker thread, so the slow AI calls
    # do not block the server.
    form = {"prompt": prompt, "character_name": character_name, "setting": setting,
            "tone": tone, "style": style}
    try:
        layout, pdf_path = run_pipeline(prompt, character_name, setting, tone, style)
        pdf_filename, web_pdf_path = _pdf_urls(pdf_path)
        return templates.TemplateResponse(request=request, name="comic_preview.html", context={
            "layout": layout, "pdf_path": web_pdf_path, "pdf_filename": pdf_filename,
        })
    except ComicGenerationError as exc:
        return templates.TemplateResponse(request=request, name="index.html", status_code=502,
                                          context={"error": str(exc), "form": form})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return templates.TemplateResponse(request=request, name="index.html", status_code=500,
                                          context={"error": f"Unexpected error: {exc}", "form": form})


@router.post("/generate-comic/json")
def generate_comic_json(payload: PromptRequest):
    try:
        layout, pdf_path = run_pipeline(payload.prompt, payload.character_name,
                                        payload.setting, payload.tone, payload.style)
    except ComicGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))

    pdf_filename, web_pdf_path = _pdf_urls(pdf_path)
    public_layout = [{**panel, "image_path": panel["image_url"]} for panel in layout]  # hide server paths
    return {
        "panel_count": len(public_layout),
        "layout": public_layout,
        "pdf_path": web_pdf_path,
        "pdf_download": f"/download/{pdf_filename}",
    }


@router.get("/download/{filename}")
def download_pdf(filename: str):
    safe = Path(filename).name
    path = EXPORTS_DIR / safe
    if safe != filename or not safe.lower().endswith(".pdf") or not path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found.")
    return FileResponse(str(path), media_type="application/pdf", filename=safe)


@router.get("/export-success", response_class=HTMLResponse)
def export_success(request: Request, pdf_path: str = ""):
    pdf_filename = Path(pdf_path).name if pdf_path else ""
    if pdf_filename and not (EXPORTS_DIR / pdf_filename).is_file():
        pdf_filename = ""
    return templates.TemplateResponse(request=request, name="export_success.html",
                                      context={"pdf_path": pdf_path, "pdf_filename": pdf_filename})


@router.get("/test-image")
def test_image(prompt: str = "A futuristic city at sunset, sci-fi, cinematic, artstation"):
    try:
        image_path = generate_image(prompt)
        return {"message": "Image generated successfully",
                "path": f"/static/panels/{Path(image_path).name}"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_key_configured": bool(GEMINI_API_KEY),
        "gemini_flash_model": GEMINI_FLASH_MODEL,
        "gemini_pro_model": GEMINI_PRO_MODEL,
        "image_model": SD_MODEL_ID,
        "placeholder_images_only": USE_PLACEHOLDER_IMAGES,
    }
