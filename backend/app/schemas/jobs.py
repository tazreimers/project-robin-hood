from typing import Any

from pydantic import BaseModel, Field


class JobStatusRead(BaseModel):
    task_id: str
    state: str
    ready: bool
    successful: bool
    result: dict[str, Any] | None = Field(default=None)
    error: str | None = Field(default=None)
