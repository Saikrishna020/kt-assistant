from __future__ import annotations

from pydantic import BaseModel, Field


class Service(BaseModel):
    name: str
    path: str
    component_type: str = "unknown_artifact"
    classification_confidence: float = 0.0
    classification_reason: str = ""
    runtime: str = "unknown"
    apis: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source: str = "unknown"
    evidence: list[dict[str, str | float]] = Field(default_factory=list)
