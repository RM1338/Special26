"""GET /public/img/{token}: short-lived image URL for Google Lens (04 §6, D-25). NFR-07."""
import base64
import hashlib
import hmac
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from special26.errors import NotFound

router = APIRouter()
TTL = 600                                    # 10 minutes (NFR-07)


def _mac(salt: str, msg: str) -> str:
    return hmac.new(salt.encode(), msg.encode(), hashlib.sha256).hexdigest()


def sign(salt: str, sha256: str, now: float | None = None) -> str:
    msg = f"{sha256}.{int((now or time.time()) + TTL)}"
    return base64.urlsafe_b64encode(f"{msg}.{_mac(salt, msg)}".encode()).decode().rstrip("=")


def verify(salt: str, token: str, now: float | None = None) -> str | None:
    """Returns the image sha256 if the token is genuine and unexpired."""
    try:
        sha, exp, mac = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode().split(".")
    except (ValueError, UnicodeDecodeError):
        return None
    if not hmac.compare_digest(mac, _mac(salt, f"{sha}.{exp}")) or int(exp) < (now or time.time()):
        return None
    return sha


@router.get("/public/img/{token}")
async def public_img(token: str, request: Request):
    st = request.app.state.s26
    sha = verify(st.settings.share_salt, token)
    row = st.repo.db.execute("SELECT storage_path FROM artifacts WHERE sha256 = ? AND storage_path IS NOT NULL",
                             (sha,)).fetchone() if sha else None
    if not row or not Path(row[0]).is_file():
        raise NotFound("Image not available.")
    return FileResponse(row[0], media_type="image/jpeg", headers={"Cache-Control": "no-store"})
