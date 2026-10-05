"""Probe contract and evidence models (05 §2, §3). FR-20, FR-27."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from special26.claims.models import ClaimSet
from special26.scoring.copy import COPY, DECISIVE_COPY, render

Family = Literal["identity", "process", "reputation", "artifact", "existence"]
ProbeStatus = Literal["ok", "skipped_no_input", "skipped_no_official_domain", "skipped_budget", "skipped_replay_miss",
                      "skipped_no_public_url", "skipped_forwarded", "unsupported", "timeout", "error"]
RULES = Path(__file__).resolve().parents[1] / "rules/weights.yaml"


class Receipt(BaseModel):
    kind: Literal["serp", "rule", "rdap", "local_memory"]
    engine: str | None = None
    query: str | None = None
    position: int | None = None
    title: str | None = None
    link: str | None = None
    snippet: str | None = None
    serp_cache_key: str | None = None
    rule_id: str | None = None
    extra: dict = {}


class Finding(BaseModel):
    id: int | None = None      # set once persisted; reasons cite it (07 §4)
    probe_id: str
    code: str
    family: Family
    weight: float
    decisive_flag: str | None = None
    message: str
    claim_ids: list[str] = []
    receipt: Receipt
    vars: dict = {}            # message variables, reused by decisive-rule copy; not persisted


class ProbeResult(BaseModel):
    probe_id: str
    status: ProbeStatus
    findings: list[Finding] = []
    credits_used: int = 0
    cache_hits: int = 0
    duration_ms: int = 0
    outputs: dict = {}

    def summary(self) -> dict:
        return {"probe_id": self.probe_id, "status": self.status, "findings": len(self.findings),
                "credits_used": self.credits_used, "cache_hits": self.cache_hits, "duration_ms": self.duration_ms}


class ProbeContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    check_id: str | None
    claims: ClaimSet
    created_at: datetime
    upstream: dict[str, ProbeResult] = {}
    serp: Any = None
    settings: Any = None
    redacted_text: str = ""
    repo: Any = None
    reserved_calls: int = 0                  # sum of max_calls of applicable probes (05 §8, P09 letter rule)

    @property
    def official(self) -> list[str]:
        p01 = self.upstream.get("P01_ENTITY")
        return list(p01.outputs.get("official_domains", [])) if p01 else []


class WeightRow(BaseModel):
    weight: float
    family: Family


@lru_cache
def rules() -> dict:
    return yaml.safe_load(RULES.read_text())


@lru_cache
def weights() -> dict[str, WeightRow]:
    return {k: WeightRow(**v) for k, v in rules()["codes"].items()}


def code_order() -> dict[str, int]:
    return {c: i for i, c in enumerate(rules()["codes"])}


def validate_ruleset() -> None:
    """Refuse to start if a finding code lacks a weight or copy (T1.6)."""
    w, r = set(weights()), rules()
    problems = [f"no copy for {c}" for c in w - set(COPY)] + [f"copy without weight: {c}" for c in set(COPY) - w]
    problems += [f"no copy for {d}" for d in r["decisive"] if d not in DECISIVE_COPY]
    if problems:
        raise RuntimeError("ruleset invalid: " + "; ".join(sorted(problems)))


class Probe(ABC):
    id: ClassVar[str]
    engine: ClassVar[str | None] = None      # primary engine for the probe.started event
    depends_on: ClassVar[tuple[str, ...]] = ()
    max_calls: ClassVar[int] = 0
    timeout_s: ClassVar[float] = 12.0        # FR-25 for local probes; SerpApi probes 25 s, P09 35 s (D-29, D-34)

    def __init__(self):
        self.credits_used = 0
        self.cache_hits = 0
        self._t0 = time.monotonic()

    @abstractmethod
    def applicable(self, ctx: ProbeContext) -> ProbeStatus | None:
        """A skipped_* status if not applicable, None if it should run."""

    @abstractmethod
    async def run(self, ctx: ProbeContext) -> ProbeResult: ...

    async def search(self, ctx: ProbeContext, params: dict) -> tuple[dict, str]:
        data, key, hit = await ctx.serp.search(ctx.check_id, params)
        if hit:
            self.cache_hits += 1
        else:
            self.credits_used += 1
        return data, key

    def result(self, findings: list[Finding], outputs: dict | None = None) -> ProbeResult:
        return ProbeResult(probe_id=self.id, status="ok", findings=findings, credits_used=self.credits_used,
                           cache_hits=self.cache_hits, outputs=outputs or {})

    def finding(self, code: str, receipt: Receipt, claim_ids=(), decisive_flag: str | None = None,
                **message_vars) -> Finding:
        w = weights()[code]                  # KeyError if yaml and code disagree
        return Finding(probe_id=self.id, code=code, family=w.family, weight=w.weight, decisive_flag=decisive_flag,
                       message=render(COPY[code], **message_vars), claim_ids=list(claim_ids), receipt=receipt,
                       vars=message_vars)


def rule_receipt(rule_id: str, **extra) -> Receipt:
    from special26.scoring.copy import RULE_COPY
    return Receipt(kind="rule", rule_id=rule_id, extra={"text": RULE_COPY.get(rule_id), **extra})


def serp_receipt(engine: str, query: str, key: str, r: dict | None = None, **extra) -> Receipt:
    r = r or {}
    return Receipt(kind="serp", engine=engine, query=query, position=r.get("position"), title=r.get("title"),
                   link=r.get("link"), snippet=r.get("snippet"), serp_cache_key=key, extra=extra)
