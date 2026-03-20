from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from repo_intelligence.models.system_model import InfrastructureSignal

COMPOSE_FILES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}


def parse_docker(files: list[Path], repo_root: Path) -> list[InfrastructureSignal]:
    signals: list[InfrastructureSignal] = []
    for file_path in files:
        if file_path.name.lower() not in COMPOSE_FILES:
            continue
        try:
            doc = yaml.safe_load(file_path.read_text(encoding="utf-8", errors="ignore")) or {}
        except yaml.YAMLError:
            continue
        services = doc.get("services", {})
        if not isinstance(services, dict):
            continue
        for service_name, payload in services.items():
            info = payload if isinstance(payload, dict) else {}
            signals.append(
                InfrastructureSignal(
                    service=str(service_name),
                    path=str(info.get("build", info.get("context", ""))),
                    source=str(file_path.relative_to(repo_root)),
                    confidence=0.95,
                    metadata={
                        "image": str(info.get("image", "")),
                        "ports": [str(p) for p in info.get("ports", [])] if isinstance(info.get("ports"), list) else [],
                        "depends_on": [str(v) for v in info.get("depends_on", [])] if isinstance(info.get("depends_on"), list) else [],
                    },
                )
            )
    return signals
