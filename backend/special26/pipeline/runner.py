"""Run probes by dependency, with timeouts and statuses (05 §8, D-03). FR-24, FR-25, NFR-05."""
import asyncio
import logging
import time
from collections.abc import Callable

from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError
from special26.probes.base import Probe, ProbeContext, ProbeResult

log = logging.getLogger(__name__)
Emit = Callable[[str, dict], None]


async def run_probes(base: dict, probes: list[type[Probe]], emit: Emit | None = None) -> dict[str, ProbeResult]:
    """base: ProbeContext fields except upstream. Each probe waits only for its own dependencies."""
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
        emit("probe.finished", res.summary())

    for P in probes:
        tasks[P.id] = asyncio.ensure_future(run_one(P))
    await asyncio.gather(*tasks.values())
    return {P.id: results[P.id] for P in probes}
