"""Response model for a magic-link request."""

from pydantic import BaseModel


class MagicLinkRequestResponseModel(BaseModel):
    message: str
