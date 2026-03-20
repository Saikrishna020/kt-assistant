from __future__ import annotations

from pathlib import Path

import yaml

from repo_intelligence.models.system_model import InfrastructureSignal


def parse_kubernetes(files: list[Path], repo_root: Path) -> list[InfrastructureSignal]:
    signals: list[InfrastructureSignal] = []
    for file_path in files:
        if file_path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        try:
            docs = [doc for doc in yaml.safe_load_all(file_path.read_text(encoding="utf-8", errors="ignore")) if doc]
        except yaml.YAMLError:
            continue

        for doc in docs:
            if not isinstance(doc, dict):
                continue
            kind = str(doc.get("kind", "")).lower()
            if kind not in {"deployment", "statefulset", "daemonset", "service", "job", "cronjob"}:
                continue
            name = str(doc.get("metadata", {}).get("name", "")).strip()
            if not name:
                continue
            confidence = 0.92 if kind in {"deployment", "statefulset", "daemonset"} else 0.88

            metadata: dict[str, str | list[str]] = {
                "kind": kind,
                "apiVersion": str(doc.get("apiVersion", "")),
            }

            if kind in {"deployment", "statefulset", "daemonset", "job", "cronjob"}:
                template = doc.get("spec", {}).get("template", {}) if isinstance(doc.get("spec"), dict) else {}
                pod_spec = template.get("spec", {}) if isinstance(template, dict) else {}
                containers = pod_spec.get("containers", []) if isinstance(pod_spec, dict) else []
                images: list[str] = []
                env_targets: list[str] = []
                for container in containers:
                    if not isinstance(container, dict):
                        continue
                    image = str(container.get("image", "")).strip()
                    if image:
                        images.append(image)
                    env_vars = container.get("env", [])
                    if not isinstance(env_vars, list):
                        continue
                    for env in env_vars:
                        if not isinstance(env, dict):
                            continue
                        value = str(env.get("value", "")).strip().lower()
                        if "service" in value and ":" in value:
                            value = value.split(":", 1)[0]
                        if value.endswith("service") or "-service" in value:
                            env_targets.append(value.replace("_", "-"))
                metadata["images"] = sorted(set(images))
                metadata["env_targets"] = sorted(set(env_targets))

            signals.append(
                InfrastructureSignal(
                    service=name,
                    path=str(file_path.parent.relative_to(repo_root)),
                    source=str(file_path.relative_to(repo_root)),
                    confidence=confidence,
                    metadata=metadata,
                )
            )
    return signals
