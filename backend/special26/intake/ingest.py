"""Turn uploaded files into text, eml headers and image artifacts (FR-02 to FR-06)."""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from special26.errors import PayloadTooLarge, UnsupportedMedia, ValidationError
from special26.intake import ocr
from special26.intake.eml import parse_eml
from special26.intake.images import normalise
from special26.intake.pdf import parse_pdf

MAX_FILES, MAX_BYTES = 4, 5 * 1024 * 1024
ROLES = ("offer_pdf", "offer_image", "eml", "hr_photo")


@dataclass
class Upload:
    filename: str
    content_type: str
    data: bytes


@dataclass
class Ingested:
    text_parts: list[str] = field(default_factory=list)
    eml: dict | None = None
    images: list[tuple[int, str]] = field(default_factory=list)       # (artifact_id, role)
    warnings: list[str] = field(default_factory=list)


def sniff(u: Upload) -> str:
    """Detect pdf/png/jpeg/eml by magic bytes, falling back to name and declared type. FR-02."""
    d, name, ct = u.data, u.filename.lower(), (u.content_type or "").lower()
    if d.startswith(b"%PDF"):
        return "application/pdf"
    if d.startswith(b"\x89PNG"):
        return "image/png"
    if d.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if name.endswith(".eml") or ct == "message/rfc822":
        head = d[:4096].decode("utf-8", "ignore").lower()
        if any(h in head for h in ("from:", "received:", "subject:", "authentication-results:")):
            return "message/rfc822"
    raise UnsupportedMedia("We can read PDF, PNG, JPG and .eml files.", {"file": u.filename})


def default_role(mime: str) -> str:
    return {"application/pdf": "offer_pdf", "message/rfc822": "eml"}.get(mime, "offer_image")   # FR-03


def validate(uploads: list[Upload], roles: list[str] | None) -> list[tuple[Upload, str, str]]:
    if len(uploads) > MAX_FILES:
        raise PayloadTooLarge("At most 4 files.", {"max_files": MAX_FILES})
    out = []
    for i, u in enumerate(uploads):
        if len(u.data) > MAX_BYTES:
            raise PayloadTooLarge("That file is over 5 MB. Try a screenshot of the first page.",
                                  {"file": u.filename, "max_bytes": MAX_BYTES})
        mime = sniff(u)
        role = roles[i] if roles and i < len(roles) and roles[i] else default_role(mime)
        if role not in ROLES:
            raise ValidationError(f"unknown file role {role}", {"field": "file_roles"})
        out.append((u, mime, role))
    return out


def ingest(repo, check_id: str, files: list[tuple[Upload, str, str]], uploads_dir: str) -> Ingested:
    out = Ingested()
    folder = Path(uploads_dir) / check_id          # outside the static root (NFR-07)
    folder.mkdir(parents=True, exist_ok=True)

    def store_image(raw: bytes, role: str, derived_from: int | None = None) -> None:
        n = normalise(raw)
        path = folder / f"{n['sha256']}.jpg"
        path.write_bytes(n["bytes"])
        aid = repo.add_artifact(check_id, role, "image/jpeg", len(n["bytes"]), n["sha256"], str(path), n["phash"],
                                n["width"], n["height"], derived_from)
        out.images.append((aid, role))
        if role == "offer_image":
            if not ocr.available():
                if "OCR_UNAVAILABLE" not in out.warnings:
                    out.warnings.append("OCR_UNAVAILABLE")
            elif text := ocr.ocr(n["bytes"]):
                out.text_parts.append(text)

    for u, mime, role in files:
        sha = hashlib.sha256(u.data).hexdigest()
        if mime.startswith("image/"):
            store_image(u.data, role)
            continue
        path = folder / f"{sha}.{'pdf' if mime == 'application/pdf' else 'eml'}"
        path.write_bytes(u.data)
        aid = repo.add_artifact(check_id, role, mime, len(u.data), sha, str(path))
        if mime == "application/pdf":
            text, images = parse_pdf(u.data)
            out.text_parts.append(text)
            for img in images[:2]:
                store_image(img, "offer_image", derived_from=aid)
        else:
            out.eml = parse_eml(u.data)
            out.text_parts.append(out.eml["body"])
    return out
