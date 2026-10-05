"""Image normalisation: max 1024 px, EXIF stripped, pHash (04 §6, 08 §8)."""
import hashlib
import io

import imagehash
from PIL import Image, ImageOps

MAX_SIDE = 1024
LENS_MAX_BYTES = 500_000          # SerpApi upload limit (D-27)


def normalise(raw: bytes) -> dict:
    """Returns {bytes (JPEG, no EXIF), sha256, phash (16 hex), width, height}."""
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    out = _jpeg(im, 90)
    return {"bytes": out, "sha256": hashlib.sha256(out).hexdigest(), "phash": str(imagehash.phash(im)),
            "width": im.width, "height": im.height}


def for_lens(jpeg: bytes) -> bytes:
    """Re-encode until it fits SerpApi's 500 KB upload limit."""
    if len(jpeg) <= LENS_MAX_BYTES:
        return jpeg
    im = Image.open(io.BytesIO(jpeg))
    for q in (80, 70, 60, 50, 40):
        out = _jpeg(im, q)
        if len(out) <= LENS_MAX_BYTES:
            return out
    im.thumbnail((640, 640))
    return _jpeg(im, 60)


def _jpeg(im: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)     # a fresh save carries no EXIF
    return buf.getvalue()
