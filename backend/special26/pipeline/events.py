"""In-process pub/sub for SSE; every event is also stored for Last-Event-ID replay (05 §9). FR-40."""
import asyncio
from collections import defaultdict


class Events:
    def __init__(self, repo):
        self.repo = repo
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def publish(self, check_id: str, type_: str, data: dict) -> int:
        seq = self.repo.add_event(check_id, type_, data)
        for q in list(self._subs.get(check_id, ())):
            q.put_nowait((seq, type_, data))
        return seq

    def subscribe(self, check_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs[check_id].add(q)
        return q

    def unsubscribe(self, check_id: str, q: asyncio.Queue) -> None:
        self._subs[check_id].discard(q)
        if not self._subs[check_id]:
            self._subs.pop(check_id, None)
