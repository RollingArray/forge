"""
File: main.py
Purpose: FastAPI application entry point for the FORGE backend.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as authentication_router
from app.api.ai import router as ai_router
from app.api.data_models import router as data_models_router
from app.api.data_model_access import router as data_model_access_router
from app.api.specification import router as specification_router
from app.api.workspace import router as workspace_router
from app.api.users import router as users_router


app = FastAPI(
    title="FORGE API",
    version="0.1.0",
    description="Backend API for the FORGE synthetic data generation platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    authentication_router,
    prefix="/api/v1",
)

app.include_router(
    data_models_router,
    prefix="/api/v1",
)

app.include_router(
    data_model_access_router,
    prefix="/api/v1",
)

app.include_router(
    specification_router,
    prefix="/api/v1",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the current API health status."""

    return {"status": "ok"}


app.include_router(
    workspace_router,
    prefix="/api/v1",
)

app.include_router(
    users_router,
    prefix="/api/v1",
)

app.include_router(
    ai_router,
    prefix="/api/v1",
)
