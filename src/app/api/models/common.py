from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class APIResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
