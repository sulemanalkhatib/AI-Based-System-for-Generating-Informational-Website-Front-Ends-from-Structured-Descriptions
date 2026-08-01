"""Per-run event bus: history + live subscribers, replay-on-subscribe.

emit() appends to history and fans out to every subscriber queue in one
synchronous step (no await between the two), so a subscriber that snapshots
history at registration time sees every event exactly once. Payloads carry a
monotonic `seq` so client-side reconnect dedupe is trivial.
"""

import asyncio
import json
from typing import AsyncIterator


class EventBus:
    def __init__(self) -> None:
        self.history: list[dict] = []
        self.subscribers: set[asyncio.Queue] = set()
        self.seq = 0
        self.done = False

    async def emit(self, event: str, data: dict | None = None) -> None:
        self.seq += 1
        payload = {"seq": self.seq, **(data or {})}
        item = {"event": event, "data": json.dumps(payload)}
        self.history.append(item)
        if event == "done":
            self.done = True
        for queue in list(self.subscribers):
            queue.put_nowait(item)

    async def subscribe(self) -> AsyncIterator[dict]:
        queue: asyncio.Queue = asyncio.Queue()
        snapshot = list(self.history)   # events before now → replayed from history
        was_done = self.done
        self.subscribers.add(queue)     # events from now on → arrive via the queue
        try:
            for item in snapshot:
                yield item
            if was_done:
                return
            while True:
                item = await queue.get()
                yield item
                if item["event"] == "done":
                    return
        finally:
            self.subscribers.discard(queue)


_buses: dict[str, EventBus] = {}


def bus(run_id: str) -> EventBus:
    return _buses.setdefault(run_id, EventBus())


def exists(run_id: str) -> bool:
    return run_id in _buses


def evict_later(run_id: str, delay_s: float = 600) -> None:
    """Drop a finished bus after a grace period (reconnects replay from DB after that)."""
    async def _evict() -> None:
        await asyncio.sleep(delay_s)
        _buses.pop(run_id, None)
    asyncio.get_running_loop().create_task(_evict())
