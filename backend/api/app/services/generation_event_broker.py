"""
File: generation_event_broker.py
Purpose: In-process event delivery for live generation progress.
"""

import asyncio
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class GenerationEvent:
    """One live generation event."""

    event_type: str
    data: dict[str, Any]


class GenerationEventBroker:
    """Publish generation events safely across worker and event-loop threads."""

    def __init__(self) -> None:
        self._subscribers: dict[
            tuple[str, str],
            dict[
                asyncio.Queue[GenerationEvent],
                asyncio.AbstractEventLoop,
            ],
        ] = defaultdict(dict)
        self._lock = threading.Lock()

    def subscribe(
        self,
        data_model_id: str,
        job_id: str,
    ) -> asyncio.Queue[GenerationEvent]:
        """Register a queue owned by the caller's running event loop."""

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[GenerationEvent] = asyncio.Queue()
        key = (data_model_id, job_id)

        with self._lock:
            self._subscribers[key][queue] = loop

        return queue

    def unsubscribe(
        self,
        data_model_id: str,
        job_id: str,
        queue: asyncio.Queue[GenerationEvent],
    ) -> None:
        """Remove a subscriber safely."""

        key = (data_model_id, job_id)

        with self._lock:
            subscribers = self._subscribers.get(key)

            if subscribers is None:
                return

            subscribers.pop(queue, None)

            if not subscribers:
                self._subscribers.pop(key, None)

    def publish(
        self,
        data_model_id: str,
        job_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Schedule event delivery on each subscriber's owning event loop."""

        event = GenerationEvent(
            event_type=event_type,
            data=data,
        )

        key = (data_model_id, job_id)

        with self._lock:
            subscribers = tuple(
                self._subscribers.get(key, {}).items()
            )

        for queue, loop in subscribers:
            try:
                loop.call_soon_threadsafe(
                    self._deliver,
                    queue,
                    event,
                    data_model_id,
                    job_id,
                )
            except RuntimeError:
                logger.warning(
                    "Unable to schedule generation event for closed "
                    "subscriber event loop data_model_id=%s job_id=%s "
                    "event_type=%s",
                    data_model_id,
                    job_id,
                    event_type,
                )

    @staticmethod
    def _deliver(
        queue: asyncio.Queue[GenerationEvent],
        event: GenerationEvent,
        data_model_id: str,
        job_id: str,
    ) -> None:
        """Deliver an event on the queue's owning event loop."""

        try:
            queue.put_nowait(event)
        except Exception:
            logger.exception(
                "Failed to deliver generation event "
                "data_model_id=%s job_id=%s event_type=%s",
                data_model_id,
                job_id,
                event.event_type,
            )
