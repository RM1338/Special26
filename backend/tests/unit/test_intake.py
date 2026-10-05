"""FR-04, FR-05, FR-06."""
import io
from pathlib import Path

from PIL import Image

from special26.intake import ocr
from special26.intake.eml import parse_auth, parse_eml
from special26.intake.images import LENS_MAX_BYTES, for_lens, normalise
from special26.intake.pdf import parse_pdf

FIX = Path(__file__).parents[1] / "fixtures/intake"


def test_pdf_text_and_image():  # FR-04
    text, images = parse_pdf((FIX / "tm_offer.pdf").read_bytes())
    assert "Tech Mahindra" in text and "techm.hr@ybl" in text
    assert len(images) == 1


def test_eml_genuine():  # FR-06
    e = parse_eml((FIX / "genuine_dkim.eml").read_bytes())
    assert e["from_address"] == "talent@acme-example.com" and e["from_display"] == "Acme Talent Team"
    assert e["auth"]["dkim"]["result"] == "pass" and e["auth"]["dkim"]["header.i"] == "@acme-example.com"
    assert e["auth"]["dmarc"] == {"result": "pass", "header.from": "acme-example.com"}
    assert len(e["auth_results"]) == 2 and "Software Engineering Intern" in e["body"]
    assert "HTML version" not in e["body"]                       # text/plain preferred


def test_eml_html_body_and_reply_to():
    fwd = parse_eml((FIX / "forwarded.eml").read_bytes())
    assert fwd["subject"].startswith("Fwd:") and "techmahindra-careers.in" in fwd["body"] and "<div>" not in fwd["body"]
    bad = parse_eml((FIX / "auth_fail.eml").read_bytes())
    assert bad["reply_to"] == "techm.hr.desk@gmail.com" and bad["auth"]["dmarc"]["result"] == "fail"


def test_parse_auth_header_d():
    a = parse_auth("mx.google.com; dkim=pass header.d=tcs.com header.s=x; spf=softfail smtp.mailfrom=a@b.com")
    assert a["dkim"]["header.d"] == "tcs.com" and a["spf"] == {"result": "softfail", "smtp.mailfrom": "a@b.com"}


def test_normalise_resizes_and_strips_exif():
    buf = io.BytesIO()
    im = Image.new("RGB", (3000, 1500), (200, 10, 10))
    exif = Image.Exif()
    exif[0x010F] = "SecretCam"
    im.save(buf, "JPEG", exif=exif)
    n = normalise(buf.getvalue())
    assert (n["width"], n["height"]) == (1024, 512) and len(n["phash"]) == 16
    assert b"SecretCam" not in n["bytes"] and not Image.open(io.BytesIO(n["bytes"])).getexif()


def test_for_lens_under_limit():
    buf = io.BytesIO()
    Image.effect_noise((1024, 1024), 100).convert("RGB").save(buf, "JPEG", quality=100)
    assert len(buf.getvalue()) > LENS_MAX_BYTES and len(for_lens(buf.getvalue())) <= LENS_MAX_BYTES


def test_ocr_unavailable(monkeypatch):  # FR-05
    monkeypatch.setattr(ocr, "available", lambda: False)
    assert ocr.ocr(b"x") is None
