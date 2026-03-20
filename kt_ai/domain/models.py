from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepositoryInfo:
    source: str
    local_path: Path
    files: list[Path]
    detected_languages: dict[str, int]


@dataclass
class ParsedArtifact:
    file_path: Path
    kind: str
    metadata: dict[str, str | list[str]]


@dataclass
class Evidence:
    source: str
    file_path: Path
    detail: str
    confidence: float


@dataclass
class APIEndpoint:
    path: str
    method: str
    source: str
    confidence: float
    file_path: Path


@dataclass
class Service:
    name: str
    paths: list[Path] = field(default_factory=list)
    deployable: bool = False
    deployable_source: str = "unknown"
    confidence: float = 0.0
    runtime_hints: list[str] = field(default_factory=list)
    apis: list[str] = field(default_factory=list)
    api_endpoints: list[APIEndpoint] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    infra: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class KnowledgeBase:
    repository: RepositoryInfo
    artifacts: list[ParsedArtifact]
    services: dict[str, Service]
    databases: set[str]
    queues: set[str]
    ci_pipelines: set[str]


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    attributes: dict[str, str | list[str]]


@dataclass
class GraphEdge:
    source_id: str
    relationship: str
    target_id: str
    attributes: dict[str, str | float | list[str]] = field(default_factory=dict)


@dataclass
class KnowledgeGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
