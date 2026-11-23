"""
File: generation_event_broker.py
Purpose: In-process event delivery for live generation progress.
"""

import asyncio
import logging
import os
import threading
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

SSE_DIAGNOSTICS_ENABLED = os.getenv(
    "FORGE_SSE_DIAGNOSTICS", ""
).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GenerationEvent:
    """One live generation event."""

    event_type: str
    data: dict[str, Any]


class GenerationEventBroker:
    """Publish generation events safely across worker and event-loop threads."""

    def __init__(
        self,
        *,
        diagnostics_enabled: bool = False,
        max_diagnostic_jobs: int = 256,
    ) -> None:
        if max_diagnostic_jobs < 1:
            raise ValueError("max_diagnostic_jobs must be at least 1")

        self._subscribers: dict[
            tuple[str, str],
            dict[
                asyncio.Queue[GenerationEvent],
                asyncio.AbstractEventLoop,
            ],
        ] = defaultdict(dict)

        self._lock = threading.Lock()
        self._diagnostics_enabled = diagnostics_enabled
        self._max_diagnostic_jobs = max_diagnostic_jobs
        self._diagnostics: OrderedDict[
            tuple[str, str],
            dict[str, dict[str, Any]],
        ] = OrderedDict()
        self._active_diagnostic_jobs: dict[tuple[str, str], int] = {}

    @property
    def diagnostics_enabled(self) -> bool:
        """Whether diagnostic collection is enabled for this broker."""
        return self._diagnostics_enabled

    def _trim_completed_diagnostics_locked(self) -> None:
        """Evict oldest completed diagnostics while over the retention limit."""

        completed_count = sum(
            key not in self._active_diagnostic_jobs
            for key in self._diagnostics
        )

        while completed_count > self._max_diagnostic_jobs:
            completed_key = next(
                (
                    key
                    for key in self._diagnostics
                    if key not in self._active_diagnostic_jobs
                ),
                None,
            )

            if completed_key is None:
                return

            self._diagnostics.pop(completed_key, None)
            completed_count -= 1

    def begin_job_diagnostics(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> None:
        """Protect a running job's counters from completed-job eviction."""

        if not self._diagnostics_enabled:
            return

        key = (data_model_id, job_id)

        with self._lock:
            self._active_diagnostic_jobs[key] = (
                self._active_diagnostic_jobs.get(key, 0) + 1
            )

            if key in self._diagnostics:
                self._diagnostics.move_to_end(key)

    def end_job_diagnostics(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> None:
        """Release active protection and enforce completed-job retention."""

        if not self._diagnostics_enabled:
            return

        key = (data_model_id, job_id)

        with self._lock:
            active_count = self._active_diagnostic_jobs.get(key, 0)

            if active_count <= 1:
                self._active_diagnostic_jobs.pop(key, None)
            else:
                self._active_diagnostic_jobs[key] = active_count - 1

            if key in self._diagnostics:
                self._diagnostics.move_to_end(key)

            self._trim_completed_diagnostics_locked()

    @staticmethod
    def _new_diagnostics() -> dict[str, dict[str, Any]]:
        return {
            "published_by_type": {},
            "scheduled_by_type": {},
            "schedule_failed_by_type": {},
            "queued_by_type": {},
            "delivery_failed_by_type": {},
            "published_by_entity": {},
            "scheduled_by_entity": {},
            "queued_by_entity": {},
            "delivery_failed_by_entity": {},
        }

    @staticmethod
    def _increment(bucket: dict[str, int], key: str) -> None:
        bucket[key] = bucket.get(key, 0) + 1

    def _record_diagnostic_locked(
        self,
        *,
        data_model_id: str,
        job_id: str,
        metric: str,
        event_type: str,
        entity_name: str,
    ) -> None:
        if not self._diagnostics_enabled:
            return

        key = (data_model_id, job_id)
        diagnostics = self._diagnostics.get(key)

        if diagnostics is None:
            diagnostics = self._new_diagnostics()
            self._diagnostics[key] = diagnostics
        else:
            self._diagnostics.move_to_end(key)

        self._increment(diagnostics[f"{metric}_by_type"], event_type)

        entity_bucket = diagnostics.get(f"{metric}_by_entity")
        if entity_bucket is not None:
            entity_counts = entity_bucket.setdefault(entity_name, {})
            self._increment(entity_counts, event_type)

        # Trim only after recording the event. This preserves the new entry
        # when older entries are active, while enforcing normal retention
        # whenever completed entries can be evicted.
        self._trim_completed_diagnostics_locked()

    def diagnostics_snapshot(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Return a consistent copy of aggregate broker counters."""

        if not self._diagnostics_enabled:
            return self._new_diagnostics()

        key = (data_model_id, job_id)
        with self._lock:
            diagnostics = self._diagnostics.get(
                key,
                self._new_diagnostics(),
            )
            return {
                "published_by_type": dict(diagnostics["published_by_type"]),
                "scheduled_by_type": dict(diagnostics["scheduled_by_type"]),
                "schedule_failed_by_type": dict(
                    diagnostics["schedule_failed_by_type"]
                ),
                "queued_by_type": dict(diagnostics["queued_by_type"]),
                "delivery_failed_by_type": dict(
                    diagnostics["delivery_failed_by_type"]
                ),
                "published_by_entity": {
                    entity: dict(counts)
                    for entity, counts
                    in diagnostics["published_by_entity"].items()
                },
                "scheduled_by_entity": {
                    entity: dict(counts)
                    for entity, counts
                    in diagnostics["scheduled_by_entity"].items()
                },
                "queued_by_entity": {
                    entity: dict(counts)
                    for entity, counts
                    in diagnostics["queued_by_entity"].items()
                },
                "delivery_failed_by_entity": {
                    entity: dict(counts)
                    for entity, counts
                    in diagnostics["delivery_failed_by_entity"].items()
                },
            }

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

            if self._diagnostics_enabled:
                entity_name = str(data.get("entity_name") or "JOB")
                self._record_diagnostic_locked(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    metric="published",
                    event_type=event_type,
                    entity_name=entity_name,
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
                if self._diagnostics_enabled:
                    with self._lock:
                        self._record_diagnostic_locked(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            metric="scheduled",
                            event_type=event_type,
                            entity_name=entity_name,
                        )
            except RuntimeError:
                if self._diagnostics_enabled:
                    with self._lock:
                        self._record_diagnostic_locked(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            metric="schedule_failed",
                            event_type=event_type,
                            entity_name=entity_name,
                        )
                logger.warning(
                    "Unable to schedule generation event for closed "
                    "subscriber event loop data_model_id=%s job_id=%s "
                    "event_type=%s",
                    data_model_id,
                    job_id,
                    event_type,
                )

    def _deliver(
        self,
        queue: asyncio.Queue[GenerationEvent],
        event: GenerationEvent,
        data_model_id: str,
        job_id: str,
    ) -> None:
        """Deliver an event on the queue's owning event loop."""

        try:
            queue.put_nowait(event)
        except Exception:
            if self._diagnostics_enabled:
                entity_name = str(event.data.get("entity_name") or "JOB")
                with self._lock:
                    self._record_diagnostic_locked(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        metric="delivery_failed",
                        event_type=event.event_type,
                        entity_name=entity_name,
                    )
            logger.exception(
                "Failed to deliver generation event "
                "data_model_id=%s job_id=%s event_type=%s",
                data_model_id,
                job_id,
                event.event_type,
            )
        else:
            if self._diagnostics_enabled:
                entity_name = str(event.data.get("entity_name") or "JOB")
                with self._lock:
                    self._record_diagnostic_locked(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        metric="queued",
                        event_type=event.event_type,
                        entity_name=entity_name,
                    )
