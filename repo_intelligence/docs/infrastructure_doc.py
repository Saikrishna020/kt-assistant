from __future__ import annotations

from repo_intelligence.models.system_model import SystemModel


def generate_infrastructure_doc(system_model: SystemModel) -> str:
    lines = ["# Infrastructure", "", "## Declarative Signals"]
    if not system_model.infrastructure:
        lines.append("- No infrastructure descriptors detected.")
        return "\n".join(lines) + "\n"

    grouped: dict[str, dict[str, object]] = {}
    for signal in system_model.infrastructure:
        item = grouped.setdefault(
            signal.service,
            {
                "confidence": signal.confidence,
                "paths": set(),
                "sources": set(),
                "kinds": set(),
            },
        )
        item["confidence"] = max(float(item["confidence"]), signal.confidence)
        item["paths"].add(signal.path)
        item["sources"].add(signal.source)
        kind = str(signal.metadata.get("kind", ""))
        if kind:
            item["kinds"].add(kind)

    for service_name in sorted(grouped.keys()):
        item = grouped[service_name]
        paths = ", ".join(sorted(item["paths"]))
        kinds = ", ".join(sorted(item["kinds"])) or "unknown"
        source_count = len(item["sources"])
        lines.append(
            f"- Service: {service_name}, kinds: {kinds}, paths: {paths}, confidence: {float(item['confidence']):.2f}, sources: {source_count}"
        )

        for source in sorted(item["sources"]):
            lines.append(f"  - source: {source}")

    return "\n".join(lines) + "\n"
