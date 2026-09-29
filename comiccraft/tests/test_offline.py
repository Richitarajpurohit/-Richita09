"""Offline smoke test: no API keys, no GPU, no downloads.

Run from the project root:   python -m tests.test_offline
It checks the layout builder, placeholder image generation and PDF export.
"""
import os

os.environ["USE_PLACEHOLDER_IMAGES"] = "true"   # must be set before importing the app modules

from app.exporters import save_pdf                    # noqa: E402
from app.image_generator import generate_image        # noqa: E402
from app.layout_builder import build_comic_layout     # noqa: E402

OUTLINE = [
    {"panel": i, "title": f"Scene {i}", "scene_description": f"Something happens in scene {i}.",
     "image_prompt": f"A brave red fox, forest, scene {i}"}
    for i in range(1, 6)
]
STORY = "\n\n".join(
    f'**Panel {i}: Scene {i}**\nCAPTION: Caption {i}.\nNARRATION: Narration for panel {i}.\n'
    f'DIALOGUE:\nFinn: "Line {i}!"\nOwl: "Hoo {i}."'
    for i in range(1, 6)
)


def main():
    images = [generate_image(p["image_prompt"]) for p in OUTLINE]
    assert all(os.path.exists(p) for p in images), "placeholder images were not created"

    layout = build_comic_layout(images, STORY, OUTLINE)
    assert len(layout) == 5 and layout[0]["caption"] == "Caption 1."
    assert layout[4]["dialogue"] == ['Finn: "Line 5!"', 'Owl: "Hoo 5."']

    pdf_path = save_pdf(layout)
    assert os.path.getsize(pdf_path) > 5000, "PDF looks empty"
    print("OK - offline pipeline works. PDF written to:", pdf_path)


if __name__ == "__main__":
    main()
