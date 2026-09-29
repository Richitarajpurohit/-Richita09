"""Step 5 - compile the comic into a multi-page PDF using FPDF (fpdf2)."""
import os
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from .config import EXPORTS_DIR, FONTS_DIR

_REGULAR_FONTS = [
    FONTS_DIR / "DejaVuSans.ttf",
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
]
_BOLD_FONTS = [
    FONTS_DIR / "DejaVuSans-Bold.ttf",
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]
_QUOTES = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u2026": "..."}


def _first_existing(paths):
    return next((p for p in paths if p.exists()), None)


def save_pdf(layout: list) -> str:
    """Write the comic to static/exports/comic_<timestamp>.pdf and return the file path."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)

    font, bold, unicode_ok = "Helvetica", "B", False
    regular_path = _first_existing(_REGULAR_FONTS)
    if regular_path:
        try:
            pdf.add_font("ComicFont", "", str(regular_path))
            font, bold, unicode_ok = "ComicFont", "", True
            bold_path = _first_existing(_BOLD_FONTS)
            if bold_path:
                pdf.add_font("ComicFont", "B", str(bold_path))
                bold = "B"
        except Exception as exc:  # noqa: BLE001
            print(f"[exporters] Could not load unicode font, using Helvetica: {exc}")
            font, bold, unicode_ok = "Helvetica", "B", False

    def t(text) -> str:
        text = str(text or "")
        for src, dst in _QUOTES.items():
            text = text.replace(src, dst)
        text = "".join(ch for ch in text if ord(ch) <= 0xFFFF)  # drop emoji
        if not unicode_ok:
            text = text.encode("latin-1", "replace").decode("latin-1")
        return text

    def block(label: str, body: str):
        if not body:
            return
        pdf.set_font(font, bold, 11)
        pdf.cell(0, 6, t(label), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(font, "", 11)
        pdf.multi_cell(0, 5.5, t(body), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    for panel in layout:
        pdf.add_page()
        pdf.set_font(font, bold, 16)
        pdf.multi_cell(0, 9, t(f"Panel {panel['panel']}: {panel['title']}"),
                       align="C", new_x="LMARGIN", new_y="NEXT")

        image_size = 110
        y_image = max(pdf.get_y() + 4, 30)
        image_path = panel.get("image_path", "")
        if image_path and os.path.exists(image_path):
            pdf.image(image_path, x=(pdf.w - image_size) / 2, y=y_image, w=image_size, h=image_size)
        else:
            pdf.set_y(y_image)
            pdf.set_font(font, "", 11)
            pdf.multi_cell(0, 8, t(f"Image missing: {image_path}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(y_image + image_size + 8)

        block("Scene", panel.get("scene_description", ""))
        if panel.get("caption") or panel.get("narration") or panel.get("dialogue"):
            block("Caption", panel.get("caption", ""))
            block("Narration", panel.get("narration", ""))
            block("Dialogue", "\n".join(panel.get("dialogue", [])))
        else:
            block("Story", panel.get("text", ""))

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"comic_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf_path = EXPORTS_DIR / filename
    pdf.output(str(pdf_path))
    return str(pdf_path)
