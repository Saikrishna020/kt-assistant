from __future__ import annotations

from pydantic import BaseModel, Field

from repo_intelligence.models.api import APIEndpoint
from repo_intelligence.models.dependency import Dependency
from repo_intelligence.models.service import Service


class RepoMetadata(BaseModel):
    source: str
    local_path: str
    file_count: int
    languages: dict[str, int] = Field(default_factory=dict)


class InfrastructureSignal(BaseModel):
    service: str
    path: str
    source: str
    confidence: float
    metadata: dict[str, str | list[str]] = Field(default_factory=dict)


class ASTSignal(BaseModel):
    apis: list[APIEndpoint] = Field(default_factory=list)
    databases: list[dict[str, str | float]] = Field(default_factory=list)
    service_calls: list[dict[str, str | float]] = Field(default_factory=list)
    imports: list[dict[str, str | float]] = Field(default_factory=list)


class SystemModel(BaseModel):
    repository: RepoMetadata
    services: list[Service] = Field(default_factory=list)
    apis: list[APIEndpoint] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    infrastructure: list[InfrastructureSignal] = Field(default_factory=list)
    observations: dict[str, list[str]] = Field(default_factory=dict)
