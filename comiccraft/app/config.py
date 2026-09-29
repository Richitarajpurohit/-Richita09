"""Central configuration: paths, environment variables and tunables."""
import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
PANELS_DIR = STATIC_DIR / "panels"
EXPORTS_DIR = STATIC_DIR / "exports"
FONTS_DIR = STATIC_DIR / "fonts"

for _d in (TEMPLATES_DIR, STATIC_DIR, PANELS_DIR, EXPORTS_DIR, FONTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    try:
        return int((os.getenv(name) or "").strip() or default)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float((os.getenv(name) or "").strip() or default)
    except ValueError:
        return default


# ---- Gemini ----
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
GEMINI_FLASH_MODEL = (os.getenv("GEMINI_FLASH_MODEL") or "gemini-2.5-flash").strip()
GEMINI_PRO_MODEL = (os.getenv("GEMINI_PRO_MODEL") or "gemini-2.5-pro").strip()

# Each list is tried in order until one works (protects against renamed/retired models
# and free-tier quota limits on the Pro model).
FLASH_CANDIDATES = [GEMINI_FLASH_MODEL, "gemini-flash-latest"]
PRO_CANDIDATES = [GEMINI_PRO_MODEL, "gemini-pro-latest", *FLASH_CANDIDATES]

# ---- Stable Diffusion ----
HF_TOKEN = (os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN") or "").strip()
SD_MODEL_ID = (os.getenv("SD_MODEL_ID") or "stable-diffusion-v1-5/stable-diffusion-v1-5").strip()
IMAGE_SIZE = max(256, (_get_int("IMAGE_SIZE", 512) // 8) * 8)  # must be a multiple of 8
INFERENCE_STEPS = max(5, _get_int("INFERENCE_STEPS", 25))
GUIDANCE_SCALE = _get_float("GUIDANCE_SCALE", 7.5)
USE_PLACEHOLDER_IMAGES = _get_bool("USE_PLACEHOLDER_IMAGES", False)
ALLOW_PLACEHOLDER_FALLBACK = _get_bool("ALLOW_PLACEHOLDER_FALLBACK", True)

PANEL_COUNT = 5
