from __future__ import annotations

import json
from pathlib import Path

from repo_intelligence.docs import (
    generate_api_doc,
    generate_architecture_doc,
    generate_infrastructure_doc,
    generate_services_doc,
)
from repo_intelligence.graph import graph_to_json
from repo_intelligence.models.system_model import SystemModel


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def export_knowledge_store(output_root: Path, system_model: SystemModel, graph_json: dict[str, object]) -> dict[str, Path]:
    knowledge_root = output_root / "knowledge_store"
    docs_root = knowledge_root / "docs"

    graph_path = knowledge_root / "graph.json"
    vector_seed_path = knowledge_root / "vector_seed_documents.json"
    understanding_path = knowledge_root / "system_understanding.json"

    _write_json(graph_path, graph_json)

    vector_docs: list[dict[str, object]] = []
    for service in system_model.services:
        vector_docs.append(
            {
                "id": f"service:{service.name}",
                "title": f"{service.name} service",
                "summary": (
                    f"Service {service.name} runtime={service.runtime} source={service.source} confidence={service.confidence:.2f}."
                ),
                "apis": service.apis,
                "dependencies": service.dependencies,
                "databases": service.databases,
                "metadata": {
                    "type": "service_brief",
                    "path": service.path,
                    "component_type": service.component_type,
                    "classification_confidence": f"{service.classification_confidence:.2f}",
                },
            }
        )

    for endpoint in system_model.apis:
        vector_docs.append(
            {
                "id": f"api:{endpoint.service}:{endpoint.method}:{endpoint.path}",
                "title": f"API {endpoint.method} {endpoint.path}",
                "summary": (
                    f"Endpoint {endpoint.method} {endpoint.path} for service {endpoint.service}."
                    f" framework={endpoint.framework} confidence={endpoint.confidence:.2f}."
                ),
                "metadata": {
                    "type": "api_surface",
                    "service": endpoint.service,
                    "file": endpoint.file,
                },
            }
        )

    for dependency in system_model.dependencies:
        vector_docs.append(
            {
                "id": f"edge:{dependency.source_service}:{dependency.target}:{dependency.type}",
                "title": f"Dependency {dependency.source_service} -> {dependency.target}",
                "summary": (
                    f"{dependency.source_service} depends on {dependency.target} as {dependency.type}."
                    f" confidence={dependency.confidence:.2f}. evidence={dependency.evidence}"
                ),
                "metadata": {"type": "dependency_edge_explanation"},
            }
        )

    _write_json(vector_seed_path, vector_docs)

    _write_json(
        understanding_path,
        {
            "repository": system_model.repository.model_dump(),
            "services": [service.model_dump() for service in system_model.services],
            "apis": [endpoint.model_dump() for endpoint in system_model.apis],
            "dependencies": [dependency.model_dump() for dependency in system_model.dependencies],
            "infrastructure": [infra.model_dump() for infra in system_model.infrastructure],
            "observations": system_model.observations,
        },
    )

    _write_text(docs_root / "architecture.md", generate_architecture_doc(system_model))
    _write_text(docs_root / "services.md", generate_services_doc(system_model))
    _write_text(docs_root / "apis.md", generate_api_doc(system_model))
    _write_text(docs_root / "infrastructure.md", generate_infrastructure_doc(system_model))

    return {
        "graph": graph_path,
        "vector_seed": vector_seed_path,
        "understanding": understanding_path,
        "docs": docs_root,
    }


def export_graph(graph) -> dict[str, object]:
    return graph_to_json(graph)
