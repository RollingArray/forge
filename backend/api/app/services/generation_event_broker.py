"""
File: generation_event_broker.py
Purpose: In-process event delivery for live generation progress.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GenerationEvent:
    """One live generation event."""

    event_type: str
    data: dict[str, Any]


class GenerationEventBroker:
    """Publish generation events to connected subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[
            tuple[str, str],
            set[asyncio.Queue[GenerationEvent]],
        ] = defaultdict(set)

    def subscribe(
        self,
        data_model_id: str,
        job_id: str,
    ) -> asyncio.Queue[GenerationEvent]:
        """Create and register a subscriber queue."""

        queue: asyncio.Queue[GenerationEvent] = asyncio.Queue()

        self._subscribers[(data_model_id, job_id)].add(queue)

        return queue

    def unsubscribe(
        self,
        data_model_id: str,
        job_id: str,
        queue: asyncio.Queue[GenerationEvent],
    ) -> None:
        """Remove a subscriber queue."""

        subscribers = self._subscribers.get(
            (data_model_id, job_id),
        )

        if subscribers is None:
            return

        subscribers.discard(queue)

        if not subscribers:
            self._subscribers.pop(
                (data_model_id, job_id),
                None,
            )

    def publish(
        self,
        data_model_id: str,
        job_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Publish one event to all connected subscribers."""

        event = GenerationEvent(
            event_type=event_type,
            data=data,
        )

        for queue in tuple(
            self._subscribers.get(
                (data_model_id, job_id),
                set(),
            )
        ):
            queue.put_nowait(event)
