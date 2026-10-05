"""Optional OCR with Tesseract (FR-05). Missing binary -> None, caller adds OCR_UNAVAILABLE."""
import io
import shutil
from functools import lru_cache

from PIL import Image


@lru_cache
def available() -> bool:
    return shutil.which("tesseract") is not None


@lru_cache
def _langs() -> str:
    import pytesseract
    have = set(pytesseract.get_languages(config=""))
    return "+".join(lang for lang in ("eng", "hin") if lang in have) or "eng"


def ocr(jpeg: bytes) -> str | None:
    if not available():
        return None
    import pytesseract
    return pytesseract.image_to_string(Image.open(io.BytesIO(jpeg)), lang=_langs(), timeout=10).strip()
