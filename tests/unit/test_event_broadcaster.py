"""Unit tests for the SSE EventBroadcaster subsystem."""

import json

import pytest

from repopilot.server.event_broadcaster import EventBroadcaster


@pytest.mark.asyncio
async def test_event_broadcaster_publish_and_subscribe() -> None:
    broadcaster = EventBroadcaster()
    task_id = "test_stream_01"

    # Publish an event
    await broadcaster.publish(
        task_id=task_id, event_type="test:event", data={"foo": "bar", "is_terminal": True}
    )

    # Subscribe and verify received event
    stream = broadcaster.subscribe(task_id)
    first_event = await anext(stream)

    assert first_event["event"] == "test:event"
    payload = json.loads(first_event["data"])
    assert payload["foo"] == "bar"


@pytest.mark.asyncio
async def test_event_broadcaster_history_replay() -> None:
    broadcaster = EventBroadcaster()
    task_id = "test_history_02"

    await broadcaster.publish(task_id=task_id, event_type="e1", data={"step": 1})
    await broadcaster.publish(
        task_id=task_id, event_type="e2", data={"step": 2, "is_terminal": True}
    )

    collected = []
    async for event in broadcaster.subscribe(task_id):
        collected.append(event)

    assert len(collected) == 2
    assert collected[0]["event"] == "e1"
    assert collected[1]["event"] == "e2"
