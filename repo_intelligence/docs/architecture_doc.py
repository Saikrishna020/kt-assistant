from __future__ import annotations

from repo_intelligence.models.system_model import SystemModel


def generate_architecture_doc(system_model: SystemModel) -> str:
    lines = ["# System Architecture", "", "## Services"]
    for service in system_model.services:
        lines.append(
            f"- {service.name} (type: {service.component_type}, runtime: {service.runtime}, confidence: {service.confidence:.2f})"
        )

    lines.append("")
    lines.append("## Service Communication")
    for dep in system_model.dependencies:
        if dep.type in {"HTTP", "INTERNAL_IMPORT", "QUEUE"}:
            lines.append(f"- {dep.source_service} -> {dep.target} ({dep.type}, confidence: {dep.confidence:.2f})")

    if len(lines) <= 4:
        lines.append("- No service communication edges detected.")

    return "\n".join(lines) + "\n"
