from __future__ import annotations

from repo_intelligence.models.system_model import SystemModel


def generate_api_doc(system_model: SystemModel) -> str:
    lines = ["# API Inventory", ""]
    if not system_model.apis:
        lines.append("No APIs detected.")
        return "\n".join(lines) + "\n"

    grouped: dict[str, list[str]] = {}
    for endpoint in system_model.apis:
        grouped.setdefault(endpoint.service, []).append(
            f"- {endpoint.method} {endpoint.path} ({endpoint.framework}, confidence: {endpoint.confidence:.2f}, file: {endpoint.file})"
        )

    for service, entries in sorted(grouped.items()):
        lines.append(f"## {service}")
        lines.extend(entries)
        lines.append("")

    return "\n".join(lines)
