from __future__ import annotations

from repo_intelligence.models.dependency import Dependency
from repo_intelligence.models.system_model import ASTSignal, InfrastructureSignal

QUEUE_HINTS = {"kafka", "rabbitmq", "sqs", "pubsub", "nats", "activemq"}
IGNORED_TARGETS = {"localhost", "127.0.0.1", "0.0.0.0", "default", ""}


def _normalize(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _is_valid_target(target: str, known_services: set[str]) -> bool:
    if target in IGNORED_TARGETS:
        return False
    if target in known_services:
        return True
    if target.endswith("-service"):
        return True
    if any(queue in target for queue in QUEUE_HINTS):
        return True
    return False


def detect_communications(
    ast_signal: ASTSignal,
    infra_signals: list[InfrastructureSignal],
    known_services: set[str],
) -> list[Dependency]:
    dependencies: list[Dependency] = []

    for call in ast_signal.service_calls:
        source = _normalize(str(call.get("source", "")))
        target = _normalize(str(call.get("target", "")))
        if not source or not target:
            continue
        if not _is_valid_target(target, known_services):
            continue
        dep_type = "HTTP"
        if any(queue in target for queue in QUEUE_HINTS):
            dep_type = "QUEUE"
        dependencies.append(
            Dependency(
                source_service=source,
                target=target,
                type=dep_type,
                confidence=float(call.get("confidence", 0.7)),
                evidence=str(call.get("evidence", "")),
            )
        )

    for signal in infra_signals:
        depends_on = signal.metadata.get("depends_on", [])
        if not isinstance(depends_on, list):
            continue
        source = signal.service.lower().replace("_", "-")
        for target in depends_on:
            normalized_target = str(target).lower().replace("_", "-")
            if not _is_valid_target(normalized_target, known_services):
                continue
            dependencies.append(
                Dependency(
                    source_service=source,
                    target=normalized_target,
                    type="INTERNAL_IMPORT",
                    confidence=0.9,
                    evidence=f"compose depends_on in {signal.source}",
                )
            )

        env_targets = signal.metadata.get("env_targets", [])
        if isinstance(env_targets, list):
            for target in env_targets:
                normalized_target = _normalize(str(target))
                if not _is_valid_target(normalized_target, known_services):
                    continue
                dependencies.append(
                    Dependency(
                        source_service=source,
                        target=normalized_target,
                        type="HTTP",
                        confidence=0.78,
                        evidence=f"k8s env var reference in {signal.source}",
                    )
                )

    # Keep only high-value communication edges with known source services.
    unique: dict[tuple[str, str, str], Dependency] = {}
    for dep in dependencies:
        if dep.source_service not in known_services:
            continue
        key = (dep.source_service, dep.target, dep.type)
        if key not in unique or dep.confidence > unique[key].confidence:
            unique[key] = dep

    return sorted(unique.values(), key=lambda item: (item.source_service, item.target, item.type))
