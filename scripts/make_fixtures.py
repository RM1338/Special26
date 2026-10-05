"""Build intake fixtures deterministically: tm_offer.pdf (FR-04), *.eml (FR-06). Constructed data only."""
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend/tests/fixtures/intake"
G1 = (ROOT / "backend/tests/golden/inputs/g1.txt").read_text()


def pdf_with_text_and_image(lines: list[str], jpeg: bytes, size=(200, 200)) -> bytes:
    esc = [ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for ln in lines]
    content = "BT /F1 11 Tf 50 780 Td 14 TL " + " ".join(f"({ln}) Tj T*" for ln in esc) + " ET\n"
    content += f"q {size[0]} 0 0 {size[1]} 50 300 cm /Im1 Do Q\n"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> "
        b"/XObject << /Im1 5 0 R >> >> /Contents 6 0 R >>"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Type /XObject /Subtype /Image /Width {size[0]} /Height {size[1]} /ColorSpace /DeviceRGB "
        f"/BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpeg)} >>\nstream\n".encode() + jpeg + b"\nendstream",
        f"<< /Length {len(content)} >>\nstream\n{content}endstream".encode(),
    ]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, body in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for o in offsets:
        out.write(f"{o:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def jpeg(color=(30, 90, 160), size=(200, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG", quality=85)
    return buf.getvalue()


EML_GENUINE = """\
Authentication-Results: mx.google.com;
       dkim=pass header.i=@acme-example.com header.s=s1 header.b=abc;
       spf=pass (google.com: domain of talent@acme-example.com designates 1.2.3.4 as permitted sender) smtp.mailfrom=talent@acme-example.com;
       dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=acme-example.com
Authentication-Results: relay.acme-example.com; dkim=none
From: Acme Talent Team <talent@acme-example.com>
To: Student <student@example.edu>
Subject: Offer of internship: Software Engineering Intern
Date: Mon, 05 Oct 2026 10:00:00 +0530
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="b1"

--b1
Content-Type: text/plain; charset=utf-8

Dear Student,

We are pleased to offer you the position of Software Engineering Intern at Acme Example Pvt Ltd,
Bengaluru, with a stipend of Rs 40,000 per month.

Regards,
Meera Nair
Talent Acquisition Manager
--b1
Content-Type: text/html; charset=utf-8

<p>Dear Student,</p><p>HTML version</p>
--b1--
"""

EML_FORWARDED = """\
Authentication-Results: mx.google.com; dkim=pass header.i=@gmail.com; spf=pass smtp.mailfrom=student@gmail.com
From: Student <student@gmail.com>
Subject: Fwd: Selected for Data Analyst Intern
Content-Type: text/html; charset=utf-8

<div>---------- Forwarded message ---------<br>From: hr.onboarding@techmahindra-careers.in<br>Pay Rs. 2,000/-</div>
"""

EML_FAIL = """\
Authentication-Results: mx.google.com; dkim=fail header.i=@techmahindra.com; spf=fail smtp.mailfrom=x@bulk.example; dmarc=fail header.from=techmahindra.com
From: "Tech Mahindra HR" <hr@techmahindra.com>
Reply-To: techm.hr.desk@gmail.com
Subject: Offer letter
Content-Type: text/plain

Pay Rs 2,000 for verification.
"""

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tm_offer.pdf").write_bytes(pdf_with_text_and_image(G1.splitlines(), jpeg()))
    (OUT / "genuine_dkim.eml").write_text(EML_GENUINE)
    (OUT / "forwarded.eml").write_text(EML_FORWARDED)
    (OUT / "auth_fail.eml").write_text(EML_FAIL)
    print("written", sorted(p.name for p in OUT.iterdir()))
