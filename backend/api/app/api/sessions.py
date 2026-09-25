"""
File: sessions.py
Purpose: Session API endpoints for FORGE.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import APIRouter, Depends, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.session_model import (
    CreateSessionRequestModel,
    SessionModel,
)
from app.services.session_service import SessionService


router = APIRouter(
    prefix="/sessions",
    tags=["Sessions"],
)

session_service = SessionService()


@router.post(
    "",
    response_model=SessionModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: CreateSessionRequestModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> SessionModel:
    """Create a new authenticated user's FORGE session."""

    session = session_service.create_session(
        owner_user_id=user.user_id,
        name=request.name,
    )

    return SessionModel(
        session_id=session.session_id,
        owner_user_id=session.owner_user_id,
        name=session.name,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get(
    "",
    response_model=list[SessionModel],
    status_code=status.HTTP_200_OK,
)
async def get_sessions(
    user: AuthUser = Depends(get_authenticated_user),
) -> list[SessionModel]:
    """Return the authenticated user's FORGE sessions."""

    sessions = session_service.get_sessions(
        owner_user_id=user.user_id,
    )

    return [
        SessionModel(
            session_id=session.session_id,
            owner_user_id=session.owner_user_id,
            name=session.name,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        for session in sessions
    ]
