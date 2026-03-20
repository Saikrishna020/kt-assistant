from __future__ import annotations

from repo_intelligence.models.system_model import SystemModel


def generate_services_doc(system_model: SystemModel) -> str:
    lines = ["# Services", ""]
    grouped: dict[str, list] = {}
    for service in system_model.services:
        grouped.setdefault(service.component_type, []).append(service)

    ordered_types = [
        "business_service",
        "supporting_component",
        "infrastructure_component",
        "deployment_variant",
        "unknown_artifact",
    ]

    for component_type in ordered_types:
        services = grouped.get(component_type, [])
        if not services:
            continue
        lines.append(f"## {component_type}")
        lines.append("")
        for service in sorted(services, key=lambda item: item.name):
            lines.append(f"### {service.name}")
            lines.append(f"- Path: {service.path}")
            lines.append(f"- Runtime: {service.runtime}")
            lines.append(f"- Detection source: {service.source}")
            lines.append(f"- Confidence: {service.confidence:.2f}")
            lines.append(
                f"- Classification confidence: {service.classification_confidence:.2f} ({service.classification_reason or 'n/a'})"
            )
            lines.append(f"- APIs: {', '.join(service.apis) if service.apis else 'N/A'}")
            lines.append(f"- Databases: {', '.join(service.databases) if service.databases else 'N/A'}")
            lines.append(f"- Dependencies: {', '.join(service.dependencies) if service.dependencies else 'N/A'}")
            lines.append("")
    return "\n".join(lines)
