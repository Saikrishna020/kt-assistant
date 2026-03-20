from __future__ import annotations

from repo_intelligence.models.dependency import Dependency
from repo_intelligence.models.service import Service
from repo_intelligence.models.system_model import ASTSignal


DATABASE_TYPES = {"postgres", "mysql", "mongodb", "redis", "neo4j", "cassandra", "dynamodb"}


def build_dependencies(services: list[Service], ast_signal: ASTSignal, communication_edges: list[Dependency]) -> list[Dependency]:
    dependencies = list(communication_edges)
    service_index = {service.name: service for service in services}

    for service in services:
        for db in service.databases:
            dependencies.append(
                Dependency(
                    source_service=service.name,
                    target=db,
                    type="DATABASE" if db in DATABASE_TYPES else "QUEUE",
                    confidence=0.83,
                    evidence="database extraction from source code",
                )
            )

    for edge in ast_signal.imports:
        source = str(edge.get("source", "")).lower().replace("_", "-")
        target = str(edge.get("target", "")).lower().replace("_", "-")
        if source in service_index and target in service_index and source != target:
            dependencies.append(
                Dependency(
                    source_service=source,
                    target=target,
                    type="INTERNAL_IMPORT",
                    confidence=float(edge.get("confidence", 0.65)),
                    evidence=str(edge.get("evidence", "")),
                )
            )

    unique: dict[tuple[str, str, str], Dependency] = {}
    for dep in dependencies:
        key = (dep.source_service, dep.target, dep.type)
        if key not in unique or dep.confidence > unique[key].confidence:
            unique[key] = dep

    return sorted(unique.values(), key=lambda item: (item.source_service, item.target, item.type))
