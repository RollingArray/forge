import asyncio
import threading

from app.services.generation_event_broker import GenerationEventBroker


class FailingQueue(asyncio.Queue):
    def put_nowait(self, item) -> None:
        raise RuntimeError("simulated subscriber failure")


def test_publish_delivers_from_worker_thread_to_async_subscriber() -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker()
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
        broker = GenerationEventBroker()
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
            data={"chunk_number": 1},
        )

        delivered = await asyncio.wait_for(
            healthy_queue.get(),
            timeout=2.0,
        )

        assert delivered.event_type == "CHUNK_COMMITTED"
        assert delivered.data == {"chunk_number": 1}

        # Let the failing subscriber's scheduled callback execute.
        await asyncio.sleep(0)

        assert any(
            "Failed to deliver generation event" in record.message
            for record in caplog.records
        )

    asyncio.run(scenario())


def test_publish_delivers_to_multiple_subscribers() -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker()
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
    broker = GenerationEventBroker()

    broker.publish(
        data_model_id="MODEL-1",
        job_id="JOB-3",
        event_type="GENERATION_COMPLETED",
        data={"status": "COMPLETED"},
    )


def test_unsubscribe_removes_subscriber() -> None:
    async def scenario() -> None:
        broker = GenerationEventBroker()
        queue = broker.subscribe("MODEL-1", "JOB-4")

        broker.unsubscribe("MODEL-1", "JOB-4", queue)

        with broker._lock:
            assert ("MODEL-1", "JOB-4") not in broker._subscribers

    asyncio.run(scenario())
