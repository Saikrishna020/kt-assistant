from __future__ import annotations

from pathlib import Path

from kt_ai.domain.models import KnowledgeBase
from kt_ai.pipeline.understanding import SystemView


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _overview_doc(knowledge: KnowledgeBase, system_view: SystemView) -> str:
    service_count = len(knowledge.services)
    db_count = len(knowledge.databases)
    queue_count = len(knowledge.queues)

    languages = ", ".join(f"{k} ({v})" for k, v in knowledge.repository.detected_languages.items()) or "Unknown"

    lines = [
        "# System Overview",
        "",
        f"- Repository source: `{knowledge.repository.source}`",
        f"- Local path: `{knowledge.repository.local_path}`",
        f"- Detected languages: {languages}",
        f"- Services detected: {service_count}",
        f"- Databases inferred: {db_count}",
        f"- Queues inferred: {queue_count}",
        "",
        "## Service Communication",
        "",
    ]

    if system_view.service_dependencies:
        for source, target in system_view.service_dependencies:
            lines.append(f"- `{source}` calls `{target}`")
    else:
        lines.append("- No explicit service-to-service calls inferred yet.")

    return "\n".join(lines)


def _services_doc(knowledge: KnowledgeBase, system_view: SystemView) -> str:
    lines = ["# Services", ""]

    for service_name in sorted(knowledge.services.keys()):
        details = system_view.services.get(service_name, {})
        lines.append(f"## {service_name}")
        lines.append("")
        lines.append(f"- Runtime hints: {', '.join(details.get('runtime', [])) or 'N/A'}")
        lines.append(f"- APIs: {', '.join(details.get('apis', [])) or 'N/A'}")
        lines.append(f"- Dependencies: {', '.join(details.get('dependencies', [])) or 'N/A'}")
        lines.append(f"- Infrastructure: {', '.join(details.get('infra', [])) or 'N/A'}")
        lines.append(f"- Deployable: {details.get('deployable', 'no')} (source: {details.get('deployable_source', 'unknown')})")
        lines.append(f"- Confidence: {details.get('confidence', '0.00')}")
        lines.append(f"- Evidence sources: {', '.join(details.get('evidence_sources', [])) or 'N/A'}")
        lines.append(f"- Calls: {', '.join(details.get('calls', [])) or 'N/A'}")
        lines.append("")

    return "\n".join(lines)


def _deployment_doc(knowledge: KnowledgeBase) -> str:
    lines = ["# Deployment and Delivery", ""]

    dockerfiles = [a for a in knowledge.artifacts if a.kind == "dockerfile"]
    k8s_resources = [a for a in knowledge.artifacts if a.kind.startswith("k8s_")]

    lines.append("## Docker Build")
    lines.append("")
    if dockerfiles:
        for artifact in dockerfiles:
            lines.append(f"- `{artifact.file_path}`")
    else:
        lines.append("- No Dockerfiles detected.")

    lines.append("")
    lines.append("## Kubernetes Deployment")
    lines.append("")
    if k8s_resources:
        for artifact in k8s_resources:
            resource_name = artifact.metadata.get("name", "")
            lines.append(f"- `{artifact.kind}` in `{artifact.file_path}` (name: `{resource_name}`)")
    else:
        lines.append("- No Kubernetes resources detected.")

    lines.append("")
    lines.append("## CI/CD Pipelines")
    lines.append("")
    if knowledge.ci_pipelines:
        for ci in sorted(knowledge.ci_pipelines):
            lines.append(f"- `{ci}`")
    else:
        lines.append("- No CI/CD pipelines detected.")

    return "\n".join(lines)


def generate_documents(output_root: Path, knowledge: KnowledgeBase, system_view: SystemView) -> dict[str, Path]:
    docs_root = output_root / "docs"

    overview_path = docs_root / "system-overview.md"
    services_path = docs_root / "services.md"
    deployment_path = docs_root / "deployment.md"
    readme_path = docs_root / "README.generated.md"

    _write(overview_path, _overview_doc(knowledge, system_view))
    _write(services_path, _services_doc(knowledge, system_view))
    _write(deployment_path, _deployment_doc(knowledge))

    _write(
        readme_path,
        "\n".join(
            [
                "# Generated Documentation Index",
                "",
                "- [System Overview](./system-overview.md)",
                "- [Services](./services.md)",
                "- [Deployment and Delivery](./deployment.md)",
            ]
        ),
    )

    return {
        "overview": overview_path,
        "services": services_path,
        "deployment": deployment_path,
        "index": readme_path,
    }
