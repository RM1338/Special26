"""FR-24 ordering, FR-25 timeout, NFR-05 degradation."""
import asyncio
from datetime import UTC, datetime

from special26.claims.models import ClaimSet
from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError
from special26.pipeline.runner import run_probes
from special26.probes.base import Probe

BASE = {"check_id": None, "claims": ClaimSet(claims=[]), "created_at": datetime(2026, 10, 7, tzinfo=UTC)}


def make(pid, deps=(), behaviour=None, timeout=12.0):
    async def run(self, ctx):
        if behaviour == "sleep":
            await asyncio.sleep(1)
        elif isinstance(behaviour, Exception):
            self.credits_used = 1
            raise behaviour
        elif pid != "P01_ENTITY":
            assert "P01_ENTITY" not in deps or ctx.official == ["x.com"]
        return self.result([], {"official_domains": ["x.com"]} if pid == "P01_ENTITY" else {})
    return type(pid, (Probe,), {"id": pid, "depends_on": deps, "timeout_s": timeout,
                                "applicable": lambda self, ctx: None, "run": run})


async def test_dependents_start_after_p01_finishes():
    events = []
    probes = [make("P02_SENDER", ("P01_ENTITY",)), make("P01_ENTITY"), make("P11_POLICY")]
    res = await run_probes(BASE, probes, lambda t, d: events.append((t, d["probe_id"])))
    assert events.index(("probe.finished", "P01_ENTITY")) < events.index(("probe.started", "P02_SENDER"))
    assert all(r.status == "ok" for r in res.values())


async def test_failures_become_statuses_and_check_continues():
    probes = [make("P01_ENTITY"), make("P05_CHATTER", behaviour=UpstreamError("down")),
              make("P06_IDENTIFIER_TRACE", behaviour=BudgetExhausted("x")), make("P07_ROLE", behaviour=ReplayMiss()),
              make("P08_OFFICE", behaviour=ValueError("bug")), make("P09_IMAGE", behaviour="sleep", timeout=0.05)]
    res = await run_probes(BASE, probes)
    assert {k: r.status for k, r in res.items()} == {
        "P01_ENTITY": "ok", "P05_CHATTER": "error", "P06_IDENTIFIER_TRACE": "skipped_budget",
        "P07_ROLE": "skipped_replay_miss", "P08_OFFICE": "error", "P09_IMAGE": "timeout"}
    assert res["P05_CHATTER"].credits_used == 1
