"""Asynchronous Server-Sent Events (SSE) broadcaster with sub-50ms dispatch latency."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any


class EventBroadcaster:
    """Manages real-time event streaming subscriptions for active migration tasks."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, task_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast an event payload to all active subscribers for the specified task."""
        packet = {
            "task_id": task_id,
            "event": event_type,
            "data": data,
        }

        async with self._lock:
            self._history[task_id].append(packet)
            queues = list(self._subscribers[task_id])

        for q in queues:
            await q.put(packet)

    async def subscribe(self, task_id: str) -> AsyncGenerator[dict[str, str], None]:
        """Subscribe to live event stream for a given task ID."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async with self._lock:
            # Replay existing history first
            for past_event in self._history[task_id]:
                await q.put(past_event)
            self._subscribers[task_id].append(q)

        try:
            while True:
                packet = await q.get()
                yield {
                    "event": packet["event"],
                    "data": json.dumps(packet["data"]),
                }
                # Check if terminal event
                if packet["data"].get("is_terminal", False):
                    break
        finally:
            async with self._lock:
                if q in self._subscribers[task_id]:
                    self._subscribers[task_id].remove(q)
