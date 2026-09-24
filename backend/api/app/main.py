"""
File: main.py
Purpose: FastAPI application entry point for the FORGE backend.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as authentication_router


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


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the current API health status."""

    return {"status": "ok"}
