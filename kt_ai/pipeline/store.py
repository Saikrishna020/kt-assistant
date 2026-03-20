from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from kt_ai.domain.models import KnowledgeBase, KnowledgeGraph
from kt_ai.pipeline.understanding import SystemView


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def persist_knowledge(
    output_root: Path,
    knowledge: KnowledgeBase,
    system_view: SystemView,
    graph: KnowledgeGraph,
) -> dict[str, Path]:
    graph_path = output_root / "knowledge_store" / "graph.json"
    vector_seed_path = output_root / "knowledge_store" / "vector_seed_documents.json"
    understanding_path = output_root / "knowledge_store" / "system_understanding.json"

    _write_json(graph_path, {"nodes": [asdict(n) for n in graph.nodes], "edges": [asdict(e) for e in graph.edges]})

    vector_seed_documents = []
    for service_name, service in knowledge.services.items():
        evidence_sources = sorted({e.source for e in service.evidence})
        vector_seed_documents.append(
            {
                "id": f"service:{service_name}",
                "text": (
                    f"Service {service_name} is deployable={service.deployable} (source={service.deployable_source}) "
                    f"with confidence {service.confidence:.2f}. Runtime hints {service.runtime_hints}, "
                    f"infra {service.infra}, dependencies {service.dependencies}, and APIs {service.apis}."
                ),
                "metadata": {
                    "type": "service_brief",
                    "service": service_name,
                    "confidence": f"{service.confidence:.2f}",
                    "evidence_sources": evidence_sources,
                },
            }
        )

        for idx, endpoint in enumerate(service.api_endpoints):
            vector_seed_documents.append(
                {
                    "id": f"api:{service_name}:{idx}",
                    "text": (
                        f"API endpoint {endpoint.method} {endpoint.path} belongs to service {service_name}. "
                        f"Source={endpoint.source} confidence={endpoint.confidence:.2f}."
                    ),
                    "metadata": {
                        "type": "api_surface",
                        "service": service_name,
                        "path": endpoint.path,
                        "method": endpoint.method,
                        "source": endpoint.source,
                        "confidence": f"{endpoint.confidence:.2f}",
                    },
                }
            )

    for idx, edge in enumerate(system_view.service_dependency_details):
        vector_seed_documents.append(
            {
                "id": f"edge:{idx}",
                "text": (
                    f"Service dependency: {edge.get('source')} calls {edge.get('target')}. "
                    f"Evidence={edge.get('evidence')} confidence={edge.get('confidence')}."
                ),
                "metadata": {
                    "type": "dependency_edge_explanation",
                    "source": str(edge.get("source", "")),
                    "target": str(edge.get("target", "")),
                    "confidence": str(edge.get("confidence", "")),
                },
            }
        )

    _write_json(vector_seed_path, vector_seed_documents)
    _write_json(
        understanding_path,
        {
            "services": system_view.services,
            "service_dependencies": [
                {
                    "source": source,
                    "target": target,
                }
                for source, target in system_view.service_dependencies
            ],
            "service_dependency_details": system_view.service_dependency_details,
        },
    )

    return {
        "graph": graph_path,
        "vector_seed": vector_seed_path,
        "understanding": understanding_path,
    }
