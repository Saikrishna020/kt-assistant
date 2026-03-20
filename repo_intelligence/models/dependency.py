from __future__ import annotations

from pydantic import BaseModel


class Dependency(BaseModel):
    source_service: str
    target: str
    type: str
    confidence: float = 0.0
    evidence: str = ""
