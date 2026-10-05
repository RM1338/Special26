"""GET /api/health (07 §8). NFR-09."""
from fastapi import APIRouter, Request

from special26.intake import ocr
from special26.probes.base import rules

router = APIRouter(prefix="/api")


@router.get("/health")
async def health(request: Request):
    st = request.app.state.s26
    try:
        st.repo.db.execute("SELECT 1").fetchone()
        db = "ok"
    except Exception:  # noqa: BLE001  health must answer even when the DB does not
        db = "error"
    recorded = None
    if st.repo.replay is not None:
        row = st.repo.replay.execute("SELECT MAX(recorded_at) FROM recording").fetchone()
        recorded = row[0] if row else None
    return {"status": "ok" if db == "ok" else "degraded", "mode": st.settings.mode, "db": db,
            "ruleset_version": rules()["ruleset_version"],
            "credits_today": {"used": st.repo.credits_today(), "cap": st.settings.daily_credit_cap},
            "replay_recorded_at": recorded, "ocr": ocr.available(), "llm": st.settings.llm_provider}
