from __future__ import annotations

from dataclasses import dataclass

from kt_ai.domain.models import KnowledgeBase


@dataclass
class SystemView:
    services: dict[str, dict[str, list[str] | str]]
    service_dependencies: list[tuple[str, str]]
    service_dependency_details: list[dict[str, str | float]]


def build_system_understanding(knowledge: KnowledgeBase) -> SystemView:
    service_views: dict[str, dict[str, list[str] | str]] = {}
    edges: set[tuple[str, str]] = set()
    edge_details: list[dict[str, str | float]] = []

    service_names = set(knowledge.services.keys())

    for service_name, service in knowledge.services.items():
        inferred_calls: list[str] = []
        evidence_sources = sorted({e.source for e in service.evidence})
        for dep in service.dependencies:
            dep_name = dep.lower().replace("-", "_")
            for candidate in service_names:
                if candidate == service_name:
                    continue
                candidate_norm = candidate.lower().replace("-", "_")
                if dep_name in candidate_norm or candidate_norm in dep_name:
                    inferred_calls.append(candidate)
                    edges.add((service_name, candidate))
                    edge_details.append(
                        {
                            "source": service_name,
                            "target": candidate,
                            "confidence": 0.65,
                            "evidence": f"Dependency token match: {dep}",
                        }
                    )

        for dep in service.dependencies:
            if dep in knowledge.databases or dep in knowledge.queues:
                continue
            if dep in knowledge.services and dep != service_name:
                inferred_calls.append(dep)
                edges.add((service_name, dep))
                edge_details.append(
                    {
                        "source": service_name,
                        "target": dep,
                        "confidence": 0.88,
                        "evidence": "Explicit dependency name matches known service",
                    }
                )

        service_views[service_name] = {
            "runtime": service.runtime_hints,
            "apis": service.apis,
            "infra": service.infra,
            "dependencies": service.dependencies,
            "calls": sorted(set(inferred_calls)),
            "deployable": "yes" if service.deployable else "no",
            "deployable_source": service.deployable_source,
            "confidence": f"{service.confidence:.2f}",
            "evidence_sources": evidence_sources,
        }

    return SystemView(
        services=service_views,
        service_dependencies=sorted(edges),
        service_dependency_details=edge_details,
    )
