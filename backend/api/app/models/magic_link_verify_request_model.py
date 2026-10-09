"""Request model for passwordless sign-in verification."""

from pydantic import BaseModel, Field


class MagicLinkVerifyRequestModel(BaseModel):
    token: str = Field(min_length=20, max_length=512)
