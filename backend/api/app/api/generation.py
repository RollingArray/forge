"""
File: generation.py
Purpose: FORGE generation API endpoints.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from csv import DictReader
from pathlib import Path



from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from app.core.authentication_dependency import get_authenticated_user
from app.constants.activity import ActivityType
from app.repositories.json_data_model_repository import JsonDataModelRepository
from app.services.activity_service import ActivityService
from app.interfaces.auth_user import AuthUser
from app.models.generation_model import (
    GenerationArtifactPreviewResponse,
    GenerationArtifactPageResponse,
    GenerationArtifactResponse,
    GenerationJobResponse,
    GenerationJobStatus,
    GenerationReadinessResponse,
)
from app.models.generation_log_model import GenerationLogEntryResponse, GenerationLogResponse
from app.core.ai_settings import load_ai_configuration
from app.services.ai_service import AIService
from app.services.data_model_access_service import DataModelAccessService
from app.services.generation_service import GenerationService
from app.services.generation_event_broker import GenerationEventBroker
from app.services.generation_checkpoint_store import GenerationCheckpointStore
from app.services.generation.artifact_writer import GenerationArtifactWriter
from app.services.ollama_ai_provider import OllamaAIProvider


def _count_csv_data_rows(path: Path) -> int:
    with path.open("r", newline="", encoding="utf-8") as file:
        return sum(1 for _ in DictReader(file))



router = APIRouter(
    prefix="/data-models",
    tags=["Generation"],
)

ai_service = AIService(
    provider=OllamaAIProvider(
        configuration=load_ai_configuration(),
    ),
)

generation_event_broker = GenerationEventBroker()

generation_service = GenerationService(
    ai_service=ai_service,
    event_broker=generation_event_broker,
)

data_model_access_service = DataModelAccessService()
activity_service = ActivityService()
data_model_repository = JsonDataModelRepository()
artifact_writer = GenerationArtifactWriter()
checkpoint_store = GenerationCheckpointStore()


def _execute_generation_job_and_record_activity(
    data_model_id: str,
    job_id: str,
    actor_user_id: str,
) -> None:
    """Execute a generation job and record its persisted terminal outcome."""

    try:
        generation_service.execute_job(data_model_id, job_id)
    except Exception:
        # The worker normally persists its own terminal status. If an
        # unexpected exception escapes, inspect that persisted status rather
        # than manufacturing a completion or failure activity.
        pass

    job = generation_service.get_job(
        data_model_id=data_model_id,
        job_id=job_id,
    )
    if job is None:
        return

    terminal_types = {
        GenerationJobStatus.COMPLETED,
        GenerationJobStatus.PARTIALLY_COMPLETED,
        GenerationJobStatus.FAILED,
    }
    if job.status not in terminal_types:
        return

    data_model = data_model_repository.get_by_id_any(data_model_id)
    if data_model is None:
        return

    is_failed = job.status == GenerationJobStatus.FAILED
    is_partial = job.status == GenerationJobStatus.PARTIALLY_COMPLETED

    activity_type = (
        ActivityType.GENERATION_FAILED
        if is_failed
        else ActivityType.GENERATION_PARTIALLY_COMPLETED
        if is_partial
        else ActivityType.GENERATION_COMPLETED
    )
    title = (
        "Generation failed"
        if is_failed
        else "Generation partially completed"
        if is_partial
        else "Generation completed"
    )
    description = (
        f"Generation for data model '{data_model.name}' "
        f"{'failed' if is_failed else 'partially completed' if is_partial else 'completed'}: "
        f"{job.total_generated_rows} of {job.total_target_rows} rows generated."
    )

    activity_service.record(
        owner_user_id=data_model.owner_user_id,
        actor_user_id=actor_user_id,
        activity_type=activity_type,
        title=title,
        description=description,
        data_model_id=data_model_id,
        job_id=job.job_id,
        metadata={
            "status": job.status.value,
            "generated_rows": job.total_generated_rows,
            "requested_rows": job.total_target_rows,
            "progress": job.progress,
            "elapsed_seconds": job.elapsed_seconds,
            "error": job.error,
        },
    )


@router.get(
    "/{data_model_id}/generation/readiness",
    response_model=GenerationReadinessResponse,
    status_code=status.HTTP_200_OK,
)
async def get_generation_readiness(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> GenerationReadinessResponse:
    """Return generation readiness for a Data Model."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        readiness = generation_service.get_readiness(
            data_model_id=data_model_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if readiness is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return readiness


@router.post(
    "/{data_model_id}/generation",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_generation_job(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> GenerationJobResponse:
    """Create a generation job without executing it yet."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        job = generation_service.create_job(
            data_model_id=data_model_id,
            user_id=user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return job

@router.get(
    "/{data_model_id}/generation",
    response_model=list[GenerationJobResponse],
    status_code=status.HTTP_200_OK,
)
async def list_generation_jobs(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> list[GenerationJobResponse]:
    """List generation jobs for a data model the user can generate."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return generation_service.list_jobs(data_model_id=data_model_id)


@router.get(
    "/{data_model_id}/generation/{job_id}",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
async def get_generation_job(
    data_model_id: str,
    job_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> GenerationJobResponse:
    """Return the current execution state of a generation job."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    job = generation_service.get_job(data_model_id=data_model_id, job_id=job_id)

    if job is None or job.data_model_id != data_model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    return job


@router.get(
    "/{data_model_id}/generation/{job_id}/log",
    response_model=GenerationLogResponse,
    status_code=status.HTTP_200_OK,
)
async def get_generation_log(
    data_model_id: str,
    job_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> GenerationLogResponse:
    """Return durable generation activity without internal tracebacks."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    document = generation_service.get_generation_log(
        data_model_id=data_model_id,
        job_id=job_id,
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job or log not found.",
        )

    return GenerationLogResponse(
        data_model_id=document.data_model_id,
        job_id=document.job_id,
        entries=[
            GenerationLogEntryResponse.model_validate(
                entry.model_dump(
                    mode="json",
                    exclude_none=True,
                )
            )
            for entry in document.entries
        ],
    )


@router.get(
    "/{data_model_id}/generation/{job_id}/checkpoint",
    status_code=status.HTTP_200_OK,
)
async def get_generation_checkpoint(
    data_model_id: str,
    job_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Return the durable checkpoint for a generation job."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    job = generation_service.get_job(
        data_model_id=data_model_id,
        job_id=job_id,
    )

    if job is None or job.data_model_id != data_model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    checkpoint = checkpoint_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
    )

    if checkpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation checkpoint not found.",
        )

    return checkpoint


@router.get(
    "/{data_model_id}/generation/{job_id}/events",
    status_code=status.HTTP_200_OK,
)
async def stream_generation_events(
    data_model_id: str,
    job_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> StreamingResponse:
    """Stream live generation events for one generation job."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    job = generation_service.get_job(
        data_model_id=data_model_id,
        job_id=job_id,
    )

    if job is None or job.data_model_id != data_model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    async def event_stream() -> AsyncIterator[str]:
        """Yield the current snapshot followed by live events."""

        yield (
            "event: JOB_SNAPSHOT\n"
            f"data: {job.model_dump_json()}\n\n"
        )

        if job.status in {
            "COMPLETED",
            "PARTIALLY_COMPLETED",
            "FAILED",
            "CANCELLED",
        }:
            return

        queue = generation_event_broker.subscribe(
            data_model_id=data_model_id,
            job_id=job_id,
        )

        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=15.0,
                    )
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                yield (
                    f"event: {event.event_type}\n"
                    f"data: {json.dumps(event.data)}\n\n"
                )

                if event.event_type in {
                    "GENERATION_COMPLETED",
                    "GENERATION_FAILED",
                    "GENERATION_CANCELLED",
                }:
                    return
        finally:
            generation_event_broker.unsubscribe(
                data_model_id=data_model_id,
                job_id=job_id,
                queue=queue,
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{data_model_id}/generation/{job_id}/artifacts",
    response_model=list[GenerationArtifactResponse],
    status_code=status.HTTP_200_OK,
)
async def list_generation_artifacts(
    data_model_id: str,
    job_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> list[GenerationArtifactResponse]:
    """List consolidated CSV artifacts for a generation job."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    job = generation_service.get_job(data_model_id=data_model_id, job_id=job_id)

    if job is None or job.data_model_id != data_model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    artifacts: list[GenerationArtifactResponse] = []

    for entity in job.entities:
        path = artifact_writer.get_entity_csv_path(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity.entity_name,
        )

        if not path.is_file():
            continue

        artifacts.append(
            GenerationArtifactResponse(
                entity_name=entity.entity_name,
                filename=path.name,
                rows=_count_csv_data_rows(path),
                size_bytes=path.stat().st_size,
            )
        )

    return artifacts


@router.get(
    "/{data_model_id}/generation/{job_id}/artifacts/{entity_name}/preview",
    response_model=GenerationArtifactPreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_generation_artifact(
    data_model_id: str,
    job_id: str,
    entity_name: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> GenerationArtifactPreviewResponse:
    """Return a small preview of one generated CSV artifact."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    job = generation_service.get_job(data_model_id=data_model_id, job_id=job_id)

    if job is None or job.data_model_id != data_model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    try:
        path = artifact_writer.get_entity_csv_path(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated artifact not found.",
        )

    preview_limit = 10
    rows: list[dict[str, object]] = []
    columns: list[str] = []
    total_rows = 0

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = DictReader(file)
        columns = reader.fieldnames or []

        for row in reader:
            total_rows += 1

            if len(rows) < preview_limit:
                rows.append(dict(row))

    return GenerationArtifactPreviewResponse(
        entity_name=entity_name,
        filename=path.name,
        columns=columns,
        rows=rows,
        total_rows=total_rows,
        preview_rows=len(rows),
    )


@router.get(
    "/{data_model_id}/generation/{job_id}/artifacts/{entity_name}/data",
    response_model=GenerationArtifactPageResponse,
    status_code=status.HTTP_200_OK,
)
async def get_generation_artifact_data(
    data_model_id: str,
    job_id: str,
    entity_name: str,
    offset: int = 0,
    limit: int = 100,
    search: str = "",
    user: AuthUser = Depends(get_authenticated_user),
) -> GenerationArtifactPageResponse:
    """Return a bounded page of rows from one generated CSV artifact."""

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset must be zero or greater.",
        )

    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 200.",
        )

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    job = generation_service.get_job(
        data_model_id=data_model_id,
        job_id=job_id,
    )

    if job is None or job.data_model_id != data_model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    try:
        path = artifact_writer.get_entity_csv_path(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated artifact not found.",
        )

    normalized_search = search.strip().casefold()
    rows: list[dict[str, object]] = []
    columns: list[str] = []
    matching_rows = 0
    page_end = offset + limit

    entity_progress = next(
        (
            entity
            for entity in job.entities
            if entity.entity_name == entity_name
        ),
        None,
    )

    with path.open("r", newline="", encoding="utf-8") as file:
        reader = DictReader(file)
        columns = reader.fieldnames or []

        for row in reader:
            if normalized_search and not any(
                normalized_search in str(value or "").casefold()
                for value in row.values()
            ):
                continue

            if normalized_search:
                if offset <= matching_rows < page_end:
                    rows.append(dict(row))
                matching_rows += 1
                continue

            if offset <= matching_rows < page_end:
                rows.append(dict(row))

            matching_rows += 1

            if matching_rows >= page_end:
                break

    total_rows = (
        matching_rows
        if normalized_search
        else (
            entity_progress.generated_rows
            if entity_progress is not None
            else matching_rows
        )
    )

    return GenerationArtifactPageResponse(
        entity_name=entity_name,
        filename=path.name,
        columns=columns,
        rows=rows,
        total_rows=total_rows,
        offset=offset,
        limit=limit,
        search=normalized_search,
    )


@router.get(
    "/{data_model_id}/generation/{job_id}/artifacts/{entity_name}/download",
    status_code=status.HTTP_200_OK,
)
async def download_generation_artifact(
    data_model_id: str,
    job_id: str,
    entity_name: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> FileResponse:
    """Download one generated CSV artifact."""

    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    job = generation_service.get_job(data_model_id=data_model_id, job_id=job_id)

    if job is None or job.data_model_id != data_model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    try:
        path = artifact_writer.get_entity_csv_path(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated artifact not found.",
        )

    data_model = data_model_repository.get_by_id_any(data_model_id)
    if data_model is not None:
        activity_service.record(
            owner_user_id=data_model.owner_user_id,
            actor_user_id=user.user_id,
            activity_type=ActivityType.DATASET_EXPORTED,
            title="Dataset exported",
            description=(
                f"Exported generated dataset '{path.name}' "
                f"for data model '{data_model.name}'"
            ),
            data_model_id=data_model_id,
            job_id=job_id,
            metadata={
                "entity_name": entity_name,
                "filename": path.name,
                "format": "csv",
            },
        )

    return FileResponse(
        path=path,
        media_type="text/csv",
        filename=path.name,
    )


@router.post(
    "/{data_model_id}/generation/{job_id}/start",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_200_OK,
)
async def start_generation_job(
    data_model_id: str,
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: AuthUser = Depends(get_authenticated_user),
) -> GenerationJobResponse:
    if not data_model_access_service.can_generate(
        data_model_id=data_model_id,
        user_id=current_user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    previous_job = generation_service.get_job(
        data_model_id=data_model_id,
        job_id=job_id,
    )
    previous_status = previous_job.status if previous_job is not None else None

    try:
        job = generation_service.start_job(
            data_model_id=data_model_id,
            job_id=job_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    if job.status == GenerationJobStatus.RUNNING:
        if previous_status in {
            GenerationJobStatus.CREATED,
            GenerationJobStatus.INTERRUPTED,
        }:
            data_model = data_model_repository.get_by_id_any(data_model_id)
            if data_model is not None:
                activity_service.record(
                    owner_user_id=data_model.owner_user_id,
                    actor_user_id=current_user.user_id,
                    activity_type=ActivityType.GENERATION_STARTED,
                    title="Generation started",
                    description=(
                        f"Started generation for data model '{data_model.name}'"
                    ),
                    data_model_id=data_model_id,
                    job_id=job.job_id,
                    metadata={
                        "status": job.status.value,
                        "requested_rows": job.total_target_rows,
                        "resumed": (
                            previous_status == GenerationJobStatus.INTERRUPTED
                        ),
                    },
                )

        background_tasks.add_task(
            _execute_generation_job_and_record_activity,
            data_model_id,
            job_id,
            current_user.user_id,
        )
    elif job.status == GenerationJobStatus.FAILED:
        data_model = data_model_repository.get_by_id_any(data_model_id)
        if data_model is not None:
            activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=current_user.user_id,
                activity_type=ActivityType.GENERATION_FAILED,
                title="Generation failed",
                description=(
                    f"Generation for data model '{data_model.name}' failed "
                    f"before execution: {job.error or 'Unknown error'}"
                ),
                data_model_id=data_model_id,
                job_id=job.job_id,
                metadata={
                    "status": job.status.value,
                    "requested_rows": job.total_target_rows,
                    "generated_rows": job.total_generated_rows,
                    "error": job.error,
                },
            )

    return job

