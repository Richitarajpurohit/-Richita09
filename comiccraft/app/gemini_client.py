"""Thin wrapper around the google-genai SDK with model fallback."""
from typing import Iterable

from .config import GEMINI_API_KEY
from .errors import ComicGenerationError

_client = None


def get_client():
    global _client
    if not GEMINI_API_KEY:
        raise ComicGenerationError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
            "(free key: https://aistudio.google.com/apikey), then restart the server."
        )
    if _client is None:
        from google import genai  # imported lazily so the app can start without it

        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def generate_text(models: Iterable[str], prompt: str, json_mode: bool = False,
                  temperature: float = 0.9) -> str:
    """Try each model in order and return the first non-empty text response."""
    from google.genai import types

    client = get_client()
    config_kwargs = {"temperature": temperature}
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    config = types.GenerateContentConfig(**config_kwargs)

    tried, errors = set(), []
    for model in models:
        if not model or model in tried:
            continue
        tried.add(model)
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            text = (response.text or "").strip()
            if text:
                return text
            errors.append(f"{model}: empty response")
        except Exception as exc:  # noqa: BLE001 - we want to try the next model
            errors.append(f"{model}: {str(exc)[:300]}")
    raise ComicGenerationError("Gemini request failed. " + " | ".join(errors))
