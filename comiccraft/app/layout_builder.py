"""Step 4 - match every image with its story text and build the comic layout."""
import re
from pathlib import Path

_HEADER_RE = re.compile(r"^\W*panel\s*(\d+)\b\s*[:\-.\u2013\u2014]?\s*(.*)$", re.IGNORECASE)
_LABEL_RE = re.compile(
    r"^\s*[-\u2022]?\s*(caption|narration|narrator|dialogue|dialogues|dialog)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_FIELD_OF = {
    "caption": "caption", "narration": "narration", "narrator": "narration",
    "dialogue": "dialogue", "dialogues": "dialogue", "dialog": "dialogue",
}


def _clean(text: str) -> str:
    """Remove markdown emphasis markers and surrounding whitespace."""
    return text.replace("**", "").replace("*", "").strip()


def _split_story(story: str, expected: int) -> list:
    """Split the full story into per-panel (title, lines) segments."""
    segments, current = [], None
    for raw in story.splitlines():
        match = _HEADER_RE.match(raw)
        if match:
            current = {"title": _clean(match.group(2)).strip(" :-"), "lines": []}
            segments.append(current)
        elif current is not None:
            current["lines"].append(raw)

    if segments:
        return segments

    # Fallback: the model ignored the format - spread paragraphs across the panels.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", story) if p.strip()]
    if not paragraphs:
        return []
    size = max(1, -(-len(paragraphs) // max(1, expected)))
    return [
        {"title": "", "lines": "\n\n".join(paragraphs[i:i + size]).splitlines()}
        for i in range(0, len(paragraphs), size)
    ]


def _parse_segment(lines: list) -> dict:
    fields = {"caption": [], "narration": [], "dialogue": []}
    current = "narration"
    for raw in lines:
        line = re.sub(r"^[-\u2022]\s+", "", _clean(raw))  # drop list bullets
        if not line:
            continue
        label = _LABEL_RE.match(line)
        if label:
            current = _FIELD_OF[label.group(1).lower()]
            line = label.group(2).strip()
            if not line:
                continue
        fields[current].append(line)
    return {
        "caption": " ".join(fields["caption"]),
        "narration": " ".join(fields["narration"]),
        "dialogue": fields["dialogue"],
    }


def build_comic_layout(image_paths: list, full_story: str, outline: list) -> list:
    """Return a list of dicts: panel number, title, image path/url, story text and parts."""
    segments = _split_story(full_story or "", len(image_paths))
    layout = []

    for idx, image in enumerate(image_paths, start=1):
        info = outline[idx - 1] if idx - 1 < len(outline) else {}
        if not isinstance(info, dict):
            info = {"scene_description": str(info)}
        segment = segments[idx - 1] if idx - 1 < len(segments) else {"title": "", "lines": []}
        parts = _parse_segment(segment["lines"])

        text_blocks = []
        if parts["caption"]:
            text_blocks.append(f"CAPTION: {parts['caption']}")
        if parts["narration"]:
            text_blocks.append(f"NARRATION: {parts['narration']}")
        if parts["dialogue"]:
            text_blocks.append("DIALOGUE:\n" + "\n".join(parts["dialogue"]))

        layout.append({
            "panel": idx,
            "title": info.get("title") or segment["title"] or f"Panel {idx}",
            "image_path": str(image),
            "image_url": f"/static/panels/{Path(str(image)).name}",
            "scene_description": info.get("scene_description", ""),
            "image_prompt": info.get("image_prompt", ""),
            "caption": parts["caption"],
            "narration": parts["narration"],
            "dialogue": parts["dialogue"],
            "text": "\n\n".join(text_blocks),
        })
    return layout
