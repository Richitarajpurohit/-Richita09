"""Step 3 - Stable Diffusion (Hugging Face Diffusers) creates one image per panel."""
import re
import textwrap
import threading
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import (
    ALLOW_PLACEHOLDER_FALLBACK, FONTS_DIR, GUIDANCE_SCALE, HF_TOKEN, IMAGE_SIZE,
    INFERENCE_STEPS, PANELS_DIR, SD_MODEL_ID, USE_PLACEHOLDER_IMAGES,
)
from .errors import ComicGenerationError

NEGATIVE_PROMPT = (
    "text, letters, words, watermark, signature, speech bubble, caption, "
    "blurry, low quality, deformed, extra limbs, bad anatomy"
)

_pipe = None
_pipe_error = None
_lock = threading.Lock()  # one generation at a time (protects GPU/CPU memory)


def sanitize_filename(prompt: str) -> str:
    """Turn a prompt into a safe, unique .png filename."""
    base = re.sub(r"[^a-zA-Z0-9]+", "_", prompt).strip("_")[:40] or "panel"
    return f"{base}_{uuid.uuid4().hex[:8]}.png"


def _load_pipeline():
    """Load Stable Diffusion once (first call downloads ~4 GB of model files)."""
    global _pipe
    if _pipe is not None:
        return _pipe

    import torch
    from diffusers import StableDiffusionPipeline

    if torch.cuda.is_available():
        device, dtype = "cuda", torch.float16
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device, dtype = "mps", torch.float32
    else:
        device, dtype = "cpu", torch.float32

    kwargs = {"torch_dtype": dtype}
    if HF_TOKEN:
        kwargs["token"] = HF_TOKEN

    print(f"[image_generator] Loading {SD_MODEL_ID} on {device} (first run downloads the model)...")
    pipe = StableDiffusionPipeline.from_pretrained(SD_MODEL_ID, **kwargs)
    pipe = pipe.to(device)
    pipe.enable_attention_slicing()
    _pipe = pipe
    print("[image_generator] Model ready.")
    return _pipe


def _placeholder_image(prompt: str):
    """Draw a simple gradient panel so the rest of the app can be tested without a GPU."""
    size = IMAGE_SIZE
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        draw.line([(0, y), (size, y)], fill=(int(40 + 90 * t), int(70 + 60 * t), int(190 - 80 * t)))

    try:
        font = ImageFont.truetype(str(FONTS_DIR / "DejaVuSans.ttf"), max(14, size // 32))
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()

    margin = size // 12
    draw.rectangle([margin // 2, margin // 2, size - margin // 2, size - margin // 2],
                   outline=(255, 255, 255), width=4)
    draw.text((margin, margin), "Placeholder panel", fill=(255, 213, 0), font=font)
    wrapped = textwrap.fill(prompt, width=max(20, size // 14))[:600]
    draw.multiline_text((margin, margin * 2), wrapped, fill=(255, 255, 255), font=font, spacing=4)
    return img


def generate_image(prompt: str, filename: str = None) -> str:
    """Generate an image for `prompt`, save it in static/panels and return the file path."""
    global _pipe_error
    if not filename:
        filename = sanitize_filename(prompt)
    if not filename.lower().endswith(".png"):
        filename += ".png"
    filename = Path(filename).name  # never allow path traversal
    path = PANELS_DIR / filename
    PANELS_DIR.mkdir(parents=True, exist_ok=True)

    image = None
    if not USE_PLACEHOLDER_IMAGES:
        try:
            with _lock:
                pipe = _load_pipeline()
                image = pipe(
                    prompt,
                    negative_prompt=NEGATIVE_PROMPT,
                    num_inference_steps=INFERENCE_STEPS,
                    guidance_scale=GUIDANCE_SCALE,
                    height=IMAGE_SIZE,
                    width=IMAGE_SIZE,
                ).images[0]
        except Exception as exc:  # noqa: BLE001
            _pipe_error = str(exc)
            print(f"[image_generator] Stable Diffusion failed: {exc}")
            if not ALLOW_PLACEHOLDER_FALLBACK:
                raise ComicGenerationError(f"Image generation failed: {exc}") from exc
            print("[image_generator] Using a placeholder image instead.")

    if image is None:
        image = _placeholder_image(prompt)

    image.save(path)
    return str(path)
