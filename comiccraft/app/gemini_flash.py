"""Step 1 - Gemini Flash creates the structured 5-panel comic outline."""
import json
import re

from .config import FLASH_CANDIDATES, PANEL_COUNT
from .errors import ComicGenerationError
from .gemini_client import generate_text

_PROMPT = """You are a professional AI comic planner.

Create a comic of exactly __COUNT__ panels for the story idea below.

STORY: "__STORY__"

Return a JSON array with __COUNT__ objects. Each object must have:
- "panel" (integer, starting at 1)
- "title" (string, short)
- "scene_description" (string, 1-2 sentences describing what happens)
- "image_prompt" (string, a detailed visual prompt for Stable Diffusion: subject, action,
  camera angle, lighting, mood. In EVERY image_prompt re-describe the main character's
  appearance in the same words so the character looks consistent across panels.
  Do not ask for text, letters or speech bubbles in the image.)

Respond ONLY with the valid JSON array. No explanations, no markdown.
"""

_REQUIRED = ("panel", "title", "scene_description", "image_prompt")


def _extract_json(text: str):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _normalise(data) -> list:
    if isinstance(data, dict):
        data = data.get("panels") or next((v for v in data.values() if isinstance(v, list)), None)
    if not isinstance(data, list) or not data:
        raise ValueError("Gemini response is not a non-empty list.")

    panels = []
    for index, item in enumerate(data[:PANEL_COUNT], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid panel format: {item!r}")
        scene = str(item.get("scene_description") or item.get("description") or "").strip()
        image_prompt = str(item.get("image_prompt") or scene).strip()
        if not image_prompt:
            raise ValueError(f"Panel {index} is missing an image prompt.")
        panels.append({
            "panel": index,
            "title": str(item.get("title") or f"Panel {index}").strip(),
            "scene_description": scene,
            "image_prompt": image_prompt,
        })
    return panels


def generate_outline(user_prompt: str) -> list:
    """Return a list of panel dictionaries: panel, title, scene_description, image_prompt."""
    prompt = _PROMPT.replace("__COUNT__", str(PANEL_COUNT)).replace("__STORY__", user_prompt)

    last_error = None
    for attempt in range(2):  # one retry if the model returns malformed JSON
        text = generate_text(FLASH_CANDIDATES, prompt, json_mode=True, temperature=0.8)
        try:
            return _normalise(_extract_json(text))
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            print(f"[gemini_flash] attempt {attempt + 1} returned invalid outline: {exc}")
    raise ComicGenerationError(f"Could not parse the comic outline from Gemini: {last_error}")
