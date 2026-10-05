"""Seed files under data/seeds (06 §4). Part of the ruleset; loaded once."""
import json
import os
from functools import lru_cache
from pathlib import Path

import yaml

DIR = Path(os.environ.get("SPECIAL26_SEEDS_DIR", Path(__file__).resolve().parents[2] / "data/seeds"))


@lru_cache
def lines(name: str) -> tuple[str, ...]:
    out = []
    for raw in (DIR / name).read_text().splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return tuple(out)


@lru_cache
def lexicons() -> dict:
    return yaml.safe_load((DIR / "lexicons.yaml").read_text())


@lru_cache
def entities() -> tuple[dict, ...]:
    """known_entities.json with 1-based `entity_id` in file order (seed_db inserts in the same order)."""
    return tuple({**e, "entity_id": i} for i, e in enumerate(json.loads((DIR / "known_entities.json").read_text()), 1))


@lru_cache
def platform_hosts() -> tuple[tuple[str, str], ...]:
    return tuple(tuple(line.split("\t")) for line in lines("platform_hosts.txt"))
