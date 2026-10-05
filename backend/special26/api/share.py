"""Share tokens and the masked share view (07 §6, 09 S7, D-18). FR-42."""
import html

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from special26.api.checks import _load, check_view
from special26.errors import ConflictState, Expired, NotFound
from special26.storage.repo import iso, now

router = APIRouter()


@router.post("/api/checks/{check_id}/share")
async def create_share(check_id: str, request: Request):
    st = request.app.state.s26
    if _load(st, check_id)["status"] != "done":
        raise ConflictState("A check can be shared once its verdict is ready.")
    row = st.repo.share_for(check_id)
    return {"token": row["token"], "url": f"/s/{row['token']}", "expires_at": row["expires_at"]}


def shared_view(st, token: str, count: bool = True) -> dict:
    row = st.repo.share(token)
    if row is None:
        raise NotFound("This shared result does not exist.")
    if row["expires_at"] < iso(now()):
        raise Expired("This shared result has expired.")
    if count:
        st.repo.count_view(token)
    view = check_view(st, row["check_id"], public=True)
    view["shared_on"] = row["created_at"]
    return view


@router.get("/api/share/{token}")
async def get_share(token: str, request: Request):
    return shared_view(request.app.state.s26, token)


def og_page(index_html: str, title: str, description: str) -> HTMLResponse:
    """Server-side Open Graph tags so WhatsApp shows a preview without running JS (D-18)."""
    t, d = html.escape(title, quote=True), html.escape(description, quote=True)
    tags = (f'<meta property="og:title" content="{t}" />\n<meta property="og:description" content="{d}" />\n'
            f'<meta property="og:type" content="website" />\n<meta name="twitter:card" content="summary" />\n')
    return HTMLResponse(index_html.replace("</head>", tags + "</head>", 1))
