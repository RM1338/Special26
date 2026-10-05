"""PDF text (first 10 pages) and embedded images >= 120x120 (FR-04)."""
import io

from PIL import Image
from pypdf import PdfReader

MAX_PAGES = 10
MIN_SIDE = 120


def parse_pdf(raw: bytes) -> tuple[str, list[bytes]]:
    reader = PdfReader(io.BytesIO(raw))
    texts, images = [], []
    for page in reader.pages[:MAX_PAGES]:
        texts.append(page.extract_text() or "")
        for img in getattr(page, "images", []):
            size = _size(img.data)
            if size and min(size) >= MIN_SIDE:
                images.append(img.data)
    return "\n".join(texts).strip(), images


def _size(data: bytes) -> tuple[int, int] | None:
    """None for an embedded image Pillow cannot read: skip it, keep the text."""
    try:
        return Image.open(io.BytesIO(data)).size
    except (OSError, ValueError):
        return None
