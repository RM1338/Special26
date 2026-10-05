"""Wiring: DB connections, repo and SerpClient from settings."""
import httpx

from special26.config import Settings
from special26.serp.client import SerpClient
from special26.storage.db import connect, connect_replay, migrate
from special26.storage.repo import Repo


def build(settings: Settings, http: httpx.AsyncClient) -> tuple[Repo, SerpClient]:
    conn = connect(settings.db_path)
    migrate(conn)
    replay = connect_replay(settings.demo_db) if settings.mode == "replay" else None
    record = connect_replay(settings.record_to) if settings.record_to else None
    repo = Repo(conn, replay=replay, record=record)
    return repo, SerpClient(settings, repo, http)
