from __future__ import annotations

from pydantic import BaseModel


class APIEndpoint(BaseModel):
    service: str
    path: str
    method: str
    file: str
    framework: str
    confidence: float
