import asyncio
import threading

from app.services.generation_event_broker import GenerationEventBroker


class FailingQueue(asyncio.Queue):
    def put_nowait(self, item) -> None:
        raise RuntimeError("simulated subscriber failure")


def test_publish_delivers_from_worker_thread_to_async_subscriber() -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker(diagnostics_enabled=True)
        queue = broker.subscribe("MODEL-1", "JOB-1")

        def publish_from_worker() -> None:
            broker.publish(
                data_model_id="MODEL-1",
                job_id="JOB-1",
                event_type="GENERATION_ACTIVITY",
                data={"stage": "ENTITY_GENERATION"},
            )

        worker = threading.Thread(target=publish_from_worker)
        worker.start()

        event = await asyncio.wait_for(queue.get(), timeout=2.0)
        worker.join(timeout=2.0)

        assert not worker.is_alive()
        assert event.event_type == "GENERATION_ACTIVITY"
        assert event.data == {"stage": "ENTITY_GENERATION"}

        broker.unsubscribe("MODEL-1", "JOB-1", queue)

    asyncio.run(scenario())


def test_publish_continues_after_one_subscriber_fails(caplog) -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker(diagnostics_enabled=True)
        loop = asyncio.get_running_loop()
        failing_queue = FailingQueue()
        healthy_queue = asyncio.Queue()

        # Register both queues against this test's owning event loop.
        with broker._lock:
            broker._subscribers[("MODEL-1", "JOB-1")].update(
                {
                    failing_queue: loop,
                    healthy_queue: loop,
                }
            )

        broker.publish(
            data_model_id="MODEL-1",
            job_id="JOB-1",
            event_type="CHUNK_COMMITTED",
            data={"entity_name": "CUSTOMER", "chunk_number": 1},
        )

        delivered = await asyncio.wait_for(
            healthy_queue.get(),
            timeout=2.0,
        )

        assert delivered.event_type == "CHUNK_COMMITTED"
        assert delivered.data == {
            "entity_name": "CUSTOMER",
            "chunk_number": 1,
        }

        # Let the failing subscriber's scheduled callback execute.
        await asyncio.sleep(0)

        assert any(
            "Failed to deliver generation event" in record.message
            for record in caplog.records
        )

        diagnostics = broker.diagnostics_snapshot(
            data_model_id="MODEL-1",
            job_id="JOB-1",
        )
        assert diagnostics["queued_by_type"] == {
            "CHUNK_COMMITTED": 1,
        }
        assert diagnostics["delivery_failed_by_type"] == {
            "CHUNK_COMMITTED": 1,
        }
        assert diagnostics["queued_by_entity"] == {
            "CUSTOMER": {"CHUNK_COMMITTED": 1},
        }
        assert diagnostics["delivery_failed_by_entity"] == {
            "CUSTOMER": {"CHUNK_COMMITTED": 1},
        }

    asyncio.run(scenario())


def test_publish_delivers_to_multiple_subscribers() -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker(diagnostics_enabled=True)
        first_queue = broker.subscribe("MODEL-1", "JOB-2")
        second_queue = broker.subscribe("MODEL-1", "JOB-2")

        broker.publish(
            data_model_id="MODEL-1",
            job_id="JOB-2",
            event_type="GENERATION_ACTIVITY",
            data={"stage": "ENTITY_GENERATION"},
        )

        first_event, second_event = await asyncio.gather(
            asyncio.wait_for(first_queue.get(), timeout=2.0),
            asyncio.wait_for(second_queue.get(), timeout=2.0),
        )

        assert first_event == second_event
        assert first_event.event_type == "GENERATION_ACTIVITY"

        broker.unsubscribe("MODEL-1", "JOB-2", first_queue)
        broker.unsubscribe("MODEL-1", "JOB-2", second_queue)

    asyncio.run(scenario())


def test_publish_without_subscribers_is_safe() -> None:
    broker = GenerationEventBroker(diagnostics_enabled=True)

    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-3",
        event_type="GENERATION_COMPLETED",
        data={"status": "COMPLETED"},
    )



def test_diagnostics_count_published_and_scheduled_events() -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker(diagnostics_enabled=True)
        first_queue = broker.subscribe("MODEL-1", "JOB-2")
        second_queue = broker.subscribe("MODEL-1", "JOB-2")

        broker.publish(
            data_model_id="MODEL-1",
            job_id="JOB-2",
            event_type="GENERATION_ACTIVITY",
            data={"stage": "ENTITY_GENERATION"},
        )

        await asyncio.gather(
            asyncio.wait_for(first_queue.get(), timeout=2.0),
            asyncio.wait_for(second_queue.get(), timeout=2.0),
        )

        diagnostics = broker.diagnostics_snapshot(
            data_model_id="MODEL-1",
            job_id="JOB-2",
        )

        assert diagnostics["published_by_type"] == {
            "GENERATION_ACTIVITY": 1,
        }
        assert diagnostics["scheduled_by_type"] == {
            "GENERATION_ACTIVITY": 2,
        }
        assert diagnostics["published_by_entity"] == {
            "JOB": {"GENERATION_ACTIVITY": 1},
        }
        assert diagnostics["scheduled_by_entity"] == {
            "JOB": {"GENERATION_ACTIVITY": 2},
        }

        broker.unsubscribe("MODEL-1", "JOB-2", first_queue)
        broker.unsubscribe("MODEL-1", "JOB-2", second_queue)

    asyncio.run(scenario())


def test_diagnostics_count_events_by_entity_and_type() -> None:
    broker = GenerationEventBroker(diagnostics_enabled=True)

    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-5",
        event_type="CHUNK_COMMITTED",
        data={"entity_name": "CUSTOMER", "chunk_number": 1},
    )
    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-5",
        event_type="CHUNK_COMMITTED",
        data={"entity_name": "CUSTOMER", "chunk_number": 2},
    )
    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-5",
        event_type="ENTITY_COMPLETED",
        data={"entity_name": "CUSTOMER"},
    )
    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-5",
        event_type="CHUNK_COMMITTED",
        data={"entity_name": "PART", "chunk_number": 1},
    )

    diagnostics = broker.diagnostics_snapshot(
        data_model_id="MODEL-1",
        job_id="JOB-5",
    )

    assert diagnostics["published_by_type"] == {
        "CHUNK_COMMITTED": 3,
        "ENTITY_COMPLETED": 1,
    }
    assert diagnostics["published_by_entity"] == {
        "CUSTOMER": {
            "CHUNK_COMMITTED": 2,
            "ENTITY_COMPLETED": 1,
        },
        "PART": {"CHUNK_COMMITTED": 1},
    }


def test_diagnostics_are_isolated_by_model_and_job() -> None:
    broker = GenerationEventBroker(diagnostics_enabled=True)

    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-1",
        event_type="GENERATION_ACTIVITY",
        data={"entity_name": "CUSTOMER"},
    )

    other_job = broker.diagnostics_snapshot(
        data_model_id="MODEL-1",
        job_id="JOB-2",
    )
    other_model = broker.diagnostics_snapshot(
        data_model_id="MODEL-2",
        job_id="JOB-1",
    )

    assert other_job["published_by_type"] == {}
    assert other_model["published_by_type"] == {}


def test_publish_without_subscribers_counts_as_published_only() -> None:
    broker = GenerationEventBroker(diagnostics_enabled=True)

    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-3",
        event_type="GENERATION_COMPLETED",
        data={"status": "COMPLETED"},
    )

    diagnostics = broker.diagnostics_snapshot(
        data_model_id="MODEL-1",
        job_id="JOB-3",
    )

    assert diagnostics["published_by_type"] == {
        "GENERATION_COMPLETED": 1,
    }
    assert diagnostics["scheduled_by_type"] == {}
    assert diagnostics["published_by_entity"] == {
        "JOB": {"GENERATION_COMPLETED": 1},
    }
    assert diagnostics["scheduled_by_entity"] == {}

def test_unsubscribe_removes_subscriber() -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker(diagnostics_enabled=True)
        queue = broker.subscribe("MODEL-1", "JOB-4")

        broker.unsubscribe("MODEL-1", "JOB-4", queue)

        with broker._lock:
            assert ("MODEL-1", "JOB-4") not in broker._subscribers

    asyncio.run(scenario())


def test_diagnostics_are_disabled_by_default() -> None:
    broker = GenerationEventBroker()

    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-1",
        event_type="GENERATION_ACTIVITY",
        data={"entity_name": "CUSTOMER"},
    )

    assert broker._diagnostics == {}

    diagnostics = broker.diagnostics_snapshot(
        data_model_id="MODEL-1",
        job_id="JOB-1",
    )
    assert diagnostics["published_by_type"] == {}


def test_diagnostics_retention_is_bounded() -> None:
    broker = GenerationEventBroker(
        diagnostics_enabled=True,
        max_diagnostic_jobs=2,
    )

    for job_id in ("JOB-1", "JOB-2", "JOB-3"):
        broker.publish(
            data_model_id="MODEL-1",
            job_id=job_id,
            event_type="GENERATION_COMPLETED",
            data={"status": "COMPLETED"},
        )

    assert len(broker._diagnostics) == 2
    assert ("MODEL-1", "JOB-1") not in broker._diagnostics
    assert ("MODEL-1", "JOB-2") in broker._diagnostics
    assert ("MODEL-1", "JOB-3") in broker._diagnostics


def test_active_job_diagnostics_are_not_evicted() -> None:
    broker = GenerationEventBroker(
        diagnostics_enabled=True,
        max_diagnostic_jobs=1,
    )

    broker.begin_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="ACTIVE",
    )

    broker.publish(
        data_model_id="MODEL-1",
        job_id="ACTIVE",
        event_type="GENERATION_ACTIVITY",
        data={"entity_name": "CUSTOMER"},
    )

    broker.publish(
        data_model_id="MODEL-1",
        job_id="OTHER",
        event_type="GENERATION_ACTIVITY",
        data={"entity_name": "PART"},
    )

    active = broker.diagnostics_snapshot(
        data_model_id="MODEL-1",
        job_id="ACTIVE",
    )

    assert active["published_by_type"] == {
        "GENERATION_ACTIVITY": 1,
    }

    broker.end_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="ACTIVE",
    )

    broker.publish(
        data_model_id="MODEL-1",
        job_id="NEWER",
        event_type="GENERATION_ACTIVITY",
        data={"entity_name": "ORDER"},
    )

    assert len(broker._diagnostics) == 1
    assert ("MODEL-1", "NEWER") in broker._diagnostics


def test_multiple_active_jobs_can_temporarily_exceed_retention() -> None:
    broker = GenerationEventBroker(
        diagnostics_enabled=True,
        max_diagnostic_jobs=1,
    )

    for job_id in ("ACTIVE-1", "ACTIVE-2"):
        broker.begin_job_diagnostics(
            data_model_id="MODEL-1",
            job_id=job_id,
        )

        broker.publish(
            data_model_id="MODEL-1",
            job_id=job_id,
            event_type="GENERATION_ACTIVITY",
            data={"entity_name": "CUSTOMER"},
        )

    assert len(broker._diagnostics) == 2

    broker.end_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="ACTIVE-1",
    )

    assert len(broker._diagnostics) == 2

    broker.end_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="ACTIVE-2",
    )

    assert len(broker._diagnostics) == 1


def test_new_diagnostic_entry_is_not_evicted_during_active_job_overflow() -> None:
    broker = GenerationEventBroker(
        diagnostics_enabled=True,
        max_diagnostic_jobs=1,
    )

    for job_id in ("ACTIVE-1", "ACTIVE-2"):
        broker.begin_job_diagnostics(
            data_model_id="MODEL-1",
            job_id=job_id,
        )
        broker.publish(
            data_model_id="MODEL-1",
            job_id=job_id,
            event_type="GENERATION_ACTIVITY",
            data={"entity_name": "CUSTOMER"},
        )

    # This event has no active diagnostic scope. The two active entries
    # already exceed retention, so the newly created entry must be protected
    # until its counters have been recorded.
    broker.publish(
        data_model_id="MODEL-1",
        job_id="UNPROTECTED",
        event_type="GENERATION_ACTIVITY",
        data={"entity_name": "PART"},
    )

    unprotected_key = ("MODEL-1", "UNPROTECTED")
    assert unprotected_key in broker._diagnostics

    snapshot = broker.diagnostics_snapshot(
        data_model_id="MODEL-1",
        job_id="UNPROTECTED",
    )
    assert snapshot["published_by_type"]["GENERATION_ACTIVITY"] == 1

    broker.end_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="ACTIVE-1",
    )
    broker.end_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="ACTIVE-2",
    )

    assert len(broker._diagnostics) <= 1


def test_diagnostics_disabled_does_not_record_delivery_metrics() -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker()
        queue = broker.subscribe("MODEL-1", "JOB-1")

        broker.publish(
            data_model_id="MODEL-1",
            job_id="JOB-1",
            event_type="GENERATION_ACTIVITY",
            data={"entity_name": "CUSTOMER"},
        )

        event = await asyncio.wait_for(queue.get(), timeout=2.0)

        assert event.event_type == "GENERATION_ACTIVITY"
        assert broker._diagnostics == {}

        broker.unsubscribe("MODEL-1", "JOB-1", queue)

    asyncio.run(scenario())


def test_nested_active_diagnostic_scopes_require_matching_release() -> None:
    broker = GenerationEventBroker(
        diagnostics_enabled=True,
        max_diagnostic_jobs=1,
    )

    broker.begin_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="NESTED",
    )
    broker.begin_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="NESTED",
    )

    broker.publish(
        data_model_id="MODEL-1",
        job_id="NESTED",
        event_type="GENERATION_ACTIVITY",
        data={"entity_name": "CUSTOMER"},
    )

    broker.end_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="NESTED",
    )

    assert broker._active_diagnostic_jobs[("MODEL-1", "NESTED")] == 1

    broker.publish(
        data_model_id="MODEL-1",
        job_id="OTHER",
        event_type="GENERATION_ACTIVITY",
        data={"entity_name": "PART"},
    )

    assert ("MODEL-1", "NESTED") in broker._diagnostics

    broker.end_job_diagnostics(
        data_model_id="MODEL-1",
        job_id="NESTED",
    )

    assert ("MODEL-1", "NESTED") not in broker._active_diagnostic_jobs
    assert len(broker._diagnostics) == 1
