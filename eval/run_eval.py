"""Evaluation harness (11 §3 to §7).

  python -m eval.run_eval --split holdout --mode replay --replay-db data/eval.db \
         --systems S26,B0,B3 --ablate google,google_lens,google_maps,google_jobs,google_news+google_forums \
         --out eval/report.md

Recording (spends credits): --mode live --record-to data/eval.db --systems S26
"""
import argparse
import asyncio
import json
import math
import statistics
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from special26.claims.extract import extract_claims
from special26.claims.redact import redact
from special26.config import Settings
from special26.main import State
from special26.pipeline.events import Events
from special26.pipeline.runner import run_check
from special26.probes.base import rules
from special26.serp.client import SerpClient
from special26.storage.db import connect, connect_replay, migrate
from special26.storage.repo import Repo
from special26.storage.retention import seed_known_entities, seed_templates

ENGINES = ["google", "google_news", "google_forums", "google_jobs", "google_maps", "google_lens"]
TIERS = ["red", "amber", "green", "grey"]


def load_cases(split: str) -> list[dict]:
    cases = [json.loads(p.read_text()) for p in sorted((ROOT / "eval/cases").glob("*.json"))]
    return [c for c in cases if split == "all" or c["split"] == split]


def b0(case: dict) -> dict:
    """B0 fee keyword rule: red if any amount with payer=candidate, else amber (11 §4)."""
    claims = extract_claims(redact(case["text"])[0])
    pays = any(c.value.get("payer") == "candidate" for c in claims.all("amount"))
    return {"tier": "red" if pays else "amber", "score": 0.0, "coverage": 0.0, "credits": 0, "latency_ms": 0,
            "reasons": []}


async def run_system(cases: list[dict], mode: str, replay_db: str | None, masked: list[str],
                     record_to: str | None) -> dict[str, dict]:
    """Every case through the production pipeline, in case_id order, on a fresh DB (memory builds up as in prod)."""
    tmp = tempfile.mkdtemp(prefix="s26eval-")
    s = Settings(_env_file=ROOT / ".env", mode=mode, db_path=f"{tmp}/run.db", demo_db=replay_db or f"{tmp}/none.db",
                 record_to=record_to, uploads_dir=f"{tmp}/uploads", masked_engines=masked, share_salt="eval")
    conn = connect(s.db_path)
    migrate(conn)
    repo = Repo(conn, replay=connect_replay(s.demo_db) if mode == "replay" else None,
                record=connect_replay(record_to) if record_to else None)
    seed_known_entities(conn)
    seed_templates(repo)
    out = {}
    async with httpx.AsyncClient() as http:
        state = State(s, repo, SerpClient(s, repo, http), Events(repo), http)
        for case in cases:
            cid = "chk_" + case["case_id"].lower().replace("-", "")
            red, _ = redact(case["text"])
            repo.create_check(cid, mode, None, case["text"], red, False, [])
            repo.save_claims(cid, extract_claims(red).claims, confirmed=True)
            repo.update_check(cid, status="running")
            t0 = time.monotonic()
            await run_check(state, cid)
            v = repo.verdict(cid)
            out[case["case_id"]] = {
                "tier": v["tier"] if v else "error", "score": v["score"] if v else 0.0,
                "coverage": v["coverage"] if v else 0.0, "credits": repo.credits_for_check(cid)[0],
                "latency_ms": int((time.monotonic() - t0) * 1000), "reasons": v["reasons"] if v else [],
                "campaign": repo.campaign_of(cid)}
    return out


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def metrics(cases: list[dict], res: dict[str, dict]) -> dict:
    lab = {c["case_id"]: c for c in cases}
    fr = [i for i in res if lab[i]["label"] == "fraud"]
    ge = [i for i in res if lab[i]["label"] == "genuine"]
    red = [i for i in res if res[i]["tier"] == "red"]
    green = [i for i in res if res[i]["tier"] == "green"]
    ge_core = [i for i in ge if lab[i]["category"] != "small_startup"]
    k = lambda xs, f: sum(1 for i in xs if f(i))
    return {
        "red_precision": wilson(k(red, lambda i: lab[i]["label"] == "fraud"), len(red)),
        "red_recall": wilson(k(fr, lambda i: res[i]["tier"] == "red"), len(fr)),
        "catch_rate": wilson(k(fr, lambda i: res[i]["tier"] in ("red", "amber")), len(fr)),
        "false_red_rate": wilson(k(ge, lambda i: res[i]["tier"] == "red"), len(ge)),
        "green_precision": wilson(k(green, lambda i: lab[i]["label"] == "genuine"), len(green)),
        "green_yield": wilson(k(ge_core, lambda i: res[i]["tier"] == "green"), len(ge_core)),
    }


def campaign_metrics(cases: list[dict], res: dict[str, dict]) -> dict:
    groups = {c["case_id"]: c["template_group"] for c in cases if c["category"] == "campaign_variants"}
    ids = sorted(groups)
    true_pairs = {(a, b) for i, a in enumerate(ids) for b in ids[i + 1:] if groups[a] == groups[b]}
    linked = {(a, b) for a in res for b in res if a < b and res[a].get("campaign")
              and res[a]["campaign"] == res[b].get("campaign")}
    recall = wilson(len(true_pairs & linked), len(true_pairs))
    purity = wilson(len(linked & true_pairs), len(linked))
    return {"campaign_recall": recall, "campaign_purity": purity}


def fmt(m) -> str:
    return "n/a" if m is None else f"{m[0]:.2f} [{m[1]:.2f}, {m[2]:.2f}]"


def confusion(cases, res) -> str:
    lab = {c["case_id"]: c["label"] for c in cases}
    rows = ["| label | " + " | ".join(TIERS) + " |", "|---|" + "---|" * len(TIERS)]
    for label in ("fraud", "genuine"):
        cnt = [sum(1 for i in res if lab[i] == label and res[i]["tier"] == t) for t in TIERS]
        rows.append(f"| {label} | " + " | ".join(map(str, cnt)) + " |")
    return "\n".join(rows)


def report(args, cases, runs: dict[str, dict], ablations: dict[str, dict]) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    n_f = sum(c["label"] == "fraud" for c in cases)
    out = [(f"# Special26 evaluation report\n\nGenerated {now}. Ruleset `{rules()['ruleset_version']}`. Split "
           f"`{args.split}`: {len(cases)} cases ({n_f} fraud, {len(cases) - n_f} genuine). Mode `{args.mode}`."),
           ("\nAll cases are constructed (see `eval/build_cases.py` and `docs/DECISIONS.md` D-49). Intervals are 95% "
           "Wilson intervals; with this many cases they are wide, and that is the honest reading.\n"),
           "## Metrics\n", ("| system | red precision | red recall | catch rate | false red rate | green precision "
           "| green yield |"), "|---|---|---|---|---|---|---|"]
    keys = ["red_precision", "red_recall", "catch_rate", "false_red_rate", "green_precision", "green_yield"]
    allm = {name: metrics(cases, r) for name, r in runs.items()}
    for name, m in allm.items():
        out.append(f"| {name} | " + " | ".join(fmt(m[k]) for k in keys) + " |")
    out.append("\nB1 (EMSCAD TF-IDF) and B2 (LLM only) are stretch baselines (`12` §3) and were not run.\n")
    for name, r in runs.items():
        out += [f"### Confusion: {name}\n", confusion(cases, r), ""]
    if "S26" in runs:
        cm = campaign_metrics(cases, runs["S26"])
        out += ["## Campaigns (S26)\n", f"- Campaign recall: {fmt(cm['campaign_recall'])}",
                f"- Campaign purity: {fmt(cm['campaign_purity'])}", ""]
    if ablations and "S26" in allm:
        out += ["## Ablations (one engine masked at a time)\n", ("| run | masked | red recall Δ | catch rate Δ | "
                "false red rate Δ | green yield Δ |"), "|---|---|---|---|---|---|"]
        base = allm["S26"]
        for name, r in ablations.items():
            m = metrics(cases, r)
            def delta(k, m=m):
                return "n/a" if m[k] is None or base[k] is None else f"{m[k][0] - base[k][0]:+.2f}"
            out.append(f"| {name} | {name.split(':', 1)[1]} | {delta('red_recall')} | {delta('catch_rate')} | "
                       f"{delta('false_red_rate')} | {delta('green_yield')} |")
        out.append("")
    lab = {c["case_id"]: c for c in cases}
    for name, r in runs.items():
        fr = [i for i in r if lab[i]["label"] == "genuine" and r[i]["tier"] == "red"]
        out += [f"## False reds: {name}\n"] + ([f"- `{i}` ({lab[i]['category']}): " + "; ".join(
            f"{x['code']}" for x in r[i]["reasons"][:3]) for i in fr] or ["- none"]) + [""]
    if "S26" in runs:
        r = runs["S26"]
        lat = sorted(x["latency_ms"] for x in r.values())
        cred = [x["credits"] for x in r.values()]
        p95 = lat[min(len(lat) - 1, round(0.95 * (len(lat) - 1)))] if lat else 0
        out += ["## Latency and credits (S26)\n", (f"- p50 latency: {statistics.median(lat) if lat else 0:.0f} ms, "
                f"p95: {p95} ms ({args.mode} mode)"), (f"- Mean uncached SerpApi calls per check: "
                f"{statistics.mean(cred) if cred else 0:.1f}"), ""]
    out += ["## Per case\n", "| case | label | category | expected | " + " | ".join(runs) + " |",
            "|---|---|---|---|" + "---|" * len(runs)]
    for c in cases:
        out.append(f"| {c['case_id']} | {c['label']} | {c['category']} | {c['expected_tier']} | " +
                   " | ".join(runs[n][c["case_id"]]["tier"] for n in runs) + " |")
    return "\n".join(out) + "\n"


def persist(results_db: str, args, name: str, cases, res) -> None:
    conn = connect(results_db)
    migrate(conn)
    m = metrics(cases, res)
    run_id = conn.execute("INSERT INTO eval_runs (started_at, ruleset_version, split, mode, metrics_json, git_sha)"
                          " VALUES (?, ?, ?, ?, ?, ?)", (datetime.now(UTC).isoformat(), rules()["ruleset_version"],
                                                         args.split, f"{args.mode}:{name}", json.dumps(m), None)).lastrowid
    lab = {c["case_id"]: c["label"] for c in cases}
    conn.executemany("INSERT INTO eval_results VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     [(run_id, i, lab[i], r["tier"], r["score"], r["coverage"], r["credits"], r["latency_ms"])
                      for i, r in res.items()])


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="holdout", choices=["dev", "holdout", "all"])
    ap.add_argument("--mode", default="replay", choices=["replay", "live"])
    ap.add_argument("--replay-db", default=str(ROOT / "data/eval.db"))
    ap.add_argument("--record-to")
    ap.add_argument("--systems", default="S26,B0,B3")
    ap.add_argument("--ablate", default="")
    ap.add_argument("--out", default=str(ROOT / "eval/report.md"))
    ap.add_argument("--results-db", default=str(ROOT / "data/special26.db"))
    args = ap.parse_args()
    cases = load_cases(args.split)
    runs: dict[str, dict] = {}
    for name in args.systems.split(","):
        if name == "B0":
            runs["B0"] = {c["case_id"]: b0(c) for c in cases}
        elif name == "S26":
            runs["S26"] = await run_system(cases, args.mode, args.replay_db, [], args.record_to)
        elif name == "B3":
            runs["B3"] = await run_system(cases, args.mode, args.replay_db, ENGINES, None)
        else:
            print(f"system {name} not implemented (stretch), skipped")
    ablations = {}
    for spec in filter(None, args.ablate.split(",")):
        masked = spec.split("+")
        ablations[f"A:{spec}"] = await run_system(cases, args.mode, args.replay_db, masked, None)
    for name, res in {**runs, **ablations}.items():
        persist(args.results_db, args, name, cases, res)
    Path(args.out).write_text(report(args, cases, runs, ablations))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
