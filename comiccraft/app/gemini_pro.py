"""Step 2 - Gemini Pro writes narration and dialogue for every panel."""
from .config import PRO_CANDIDATES
from .errors import ComicGenerationError
from .gemini_client import generate_text

_PROMPT = """You're a comic book writer.

Given the panel breakdown below, write a comic-style story with engaging narration and
character dialogue for each panel.

Main character: __CHARACTER__
Tone: __TONE__

Panel outline:
__OUTLINE__

Guidelines:
- Use a fun and engaging tone, like an actual comic book, matching the requested tone.
- Keep each panel self-contained but part of a cohesive story with a clear ending.
- Keep the same number of panels, in the same order.
- Keep every panel short enough to fit under an illustration.

Format EXACTLY like this for every panel, with no introduction and no closing remarks:

**Panel 1: <panel title>**
CAPTION: <one short caption sentence>
NARRATION: <one to three sentences>
DIALOGUE:
<Character name>: "<spoken line>"
<Character name>: "<spoken line>"
"""


def _format_outline(outline: list) -> str:
    lines = []
    for i, item in enumerate(outline, start=1):
        if isinstance(item, dict):
            lines.append(f"{i}. {item.get('title', f'Panel {i}')}: {item.get('scene_description', '')}")
        else:
            lines.append(f"{i}. {item}")
    return "\n".join(lines)


def generate_story(outline: list, tone: str = "", character_name: str = "") -> str:
    """Return one formatted text block that contains the story for all panels."""
    prompt = (
        _PROMPT.replace("__CHARACTER__", character_name or "the hero")
        .replace("__TONE__", tone or "fun")
        .replace("__OUTLINE__", _format_outline(outline))
    )
    story = generate_text(PRO_CANDIDATES, prompt, temperature=0.9)
    if not story.strip():
        raise ComicGenerationError("Gemini returned an empty story.")
    return story
