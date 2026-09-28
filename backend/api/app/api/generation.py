"""
File: generation.py
Purpose: FORGE generation API endpoints.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.generation_model import (
    GenerationJobResponse,
    GenerationReadinessResponse,
)
from app.core.ai_settings import load_ai_configuration
from app.services.ai_service import AIService
from app.services.data_model_access_service import DataModelAccessService
from app.services.generation_service import GenerationService
from app.services.ollama_ai_provider import OllamaAIProvider


router = APIRouter(
    prefix="/data-models",
    tags=["Generation"],
)

ai_service = AIService(
    provider=OllamaAIProvider(
        configuration=load_ai_configuration(),
    ),
)

generation_service = GenerationService(
    ai_service=ai_service,
)

data_model_access_service = DataModelAccessService()


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

    job = generation_service.get_job(job_id)

    if job is None or job.data_model_id != data_model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job not found.",
        )

    return job


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

    background_tasks.add_task(
        generation_service.execute_job,
        data_model_id,
        job_id,
    )

    return job

