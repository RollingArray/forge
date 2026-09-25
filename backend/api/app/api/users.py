"""
File: users.py
Purpose: FORGE user directory API.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import APIRouter, Depends, Query, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.user_search_result_model import UserSearchResultModel
from app.services.json_user_repository import JsonUserRepository


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

user_repository = JsonUserRepository()


@router.get(
    "/search",
    response_model=list[UserSearchResultModel],
    status_code=status.HTTP_200_OK,
)
async def search_users(
    q: str = Query(
        min_length=1,
        max_length=100,
    ),
    user: AuthUser = Depends(get_authenticated_user),
) -> list[UserSearchResultModel]:
    users = user_repository.search(
        query=q,
        limit=20,
    )

    return [
        UserSearchResultModel(
            user_id=search_user.user_id,
            email=search_user.email,
            display_name=search_user.display_name,
        )
        for search_user in users
        if search_user.user_id != user.user_id
    ]
