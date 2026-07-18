from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class NodeRunEvent(BaseModel):
    case_id: str
    node_id: str
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "SKIPPED"]
    engine: str
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
