"""Run probes by dependency, with timeouts and statuses (05 §8, D-03). FR-24, FR-25, NFR-05."""
import asyncio
import logging
import time
from collections.abc import Callable

from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError
from special26.probes.base import Probe, ProbeContext, ProbeResult

log = logging.getLogger(__name__)
Emit = Callable[[str, dict], None]


async def run_probes(base: dict, probes: list[type[Probe]], emit: Emit | None = None,
                     on_result: Callable[[ProbeResult], None] | None = None) -> dict[str, ProbeResult]:
    """base: ProbeContext fields except upstream. Each probe waits only for its own dependencies.
    on_result runs before probe.finished is emitted, so a client refetch sees the findings (D-16)."""
    emit = emit or (lambda *_: None)
    results: dict[str, ProbeResult] = {}
    ids = {P.id for P in probes}
    tasks: dict[str, asyncio.Task] = {}

    async def run_one(P: type[Probe]) -> None:
        deps = [d for d in P.depends_on if d in ids]
        await asyncio.gather(*(tasks[d] for d in deps))
        ctx = ProbeContext(**base, upstream={d: results[d] for d in deps})
        p = P()
        skip = p.applicable(ctx)
        if skip:
            res = ProbeResult(probe_id=P.id, status=skip)
        else:
            emit("probe.started", {"probe_id": P.id, "engine": P.engine})
            t0 = time.monotonic()
            status = None
            try:
                res = await asyncio.wait_for(p.run(ctx), timeout=P.timeout_s)
            except TimeoutError:
                status = "timeout"
            except BudgetExhausted:
                status = "skipped_budget"
            except ReplayMiss:
                status = "skipped_replay_miss"
            except UpstreamError as e:
                log.warning("probe_upstream", extra={"check_id": base.get("check_id"), "probe_id": P.id,
                                                     "error": str(e)})
                status = "error"
            except Exception:
                log.exception("probe_error", extra={"check_id": base.get("check_id"), "probe_id": P.id})
                status = "error"
            if status:
                res = ProbeResult(probe_id=P.id, status=status, credits_used=p.credits_used, cache_hits=p.cache_hits)
            res.duration_ms = int((time.monotonic() - t0) * 1000)
        results[P.id] = res
        if on_result:
            on_result(res)
        emit("probe.finished", res.summary())

    for P in probes:
        tasks[P.id] = asyncio.ensure_future(run_one(P))
    await asyncio.gather(*tasks.values())
    return {P.id: results[P.id] for P in probes}


TERMINAL = ("done", "failed", "expired")


async def run_check(state, check_id: str) -> None:
    """Probes -> score -> persist -> verdict.ready; raw data purged at the end (05 §8, NFR-06)."""
    from datetime import datetime

    from special26.claims.models import ClaimSet
    from special26.probes.registry import PROBES
    from special26.scoring.aggregate import score
    from special26.scoring.nextsteps import official_contacts

    repo, events, s = state.repo, state.events, state.settings
    check = repo.get_check(check_id)
    try:
        claims = ClaimSet(claims=repo.claims(check_id), warnings=check["warnings"])
        events.publish(check_id, "check.running", {"probes_planned": len(PROBES), "budget": s.credit_budget_per_check})
        base = {"check_id": check_id, "claims": claims, "redacted_text": check["redacted_text"] or "",
                "created_at": datetime.fromisoformat(check["created_at"]),
                "serp": state.serp, "settings": s, "repo": repo}
        warned = False

        def on_result(res):
            nonlocal warned
            repo.save_probe_result(check_id, res)
            used = repo.credits_for_check(check_id)[0]
            if not warned and check["mode"] == "live" and s.credit_budget_per_check - used <= 2:
                warned = True
                events.publish(check_id, "budget.warning", {"remaining": max(0, s.credit_budget_per_check - used)})

        results = await run_probes(base, PROBES, lambda t, d: events.publish(check_id, t, d), on_result)
        repo.update_check(check_id, status="scoring")
        v = score(results)
        findings = [f for pid in sorted(results) for f in results[pid].findings]
        repo.set_effective([(f.id, w) for f, w in zip(findings, v.effective)])
        repo.save_verdict(check_id, v, official_contacts(results))
        repo.update_check(check_id, status="done")
        events.publish(check_id, "verdict.ready", {"tier": v.tier, "red_kind": v.red_kind, "campaign_id": None})
    except Exception:
        log.exception("check_failed", extra={"check_id": check_id})
        repo.update_check(check_id, status="failed", error_code="INTERNAL")
        events.publish(check_id, "check.failed", {"code": "INTERNAL", "message": "The check could not finish."})
    finally:
        repo.purge_raw(check_id)
