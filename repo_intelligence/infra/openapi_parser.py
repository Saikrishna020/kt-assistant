from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from repo_intelligence.models.api import APIEndpoint


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _read_structured(file_path: Path) -> dict[str, Any]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    if file_path.suffix.lower() == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return {}
    return doc if isinstance(doc, dict) else {}


def parse_openapi(files: list[Path], repo_root: Path) -> list[APIEndpoint]:
    endpoints: list[APIEndpoint] = []
    for file_path in files:
        lower_name = file_path.name.lower()
        if file_path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        if "openapi" not in lower_name and "swagger" not in lower_name:
            continue

        doc = _read_structured(file_path)
        if not any(key in doc for key in {"openapi", "swagger", "paths"}):
            continue

        paths = doc.get("paths", {})
        if not isinstance(paths, dict):
            continue

        service_name = file_path.parent.name
        for path_value, operations in paths.items():
            if not isinstance(path_value, str):
                continue
            if isinstance(operations, dict):
                for method in operations.keys():
                    if str(method).lower() in HTTP_METHODS:
                        endpoints.append(
                            APIEndpoint(
                                service=service_name,
                                path=path_value,
                                method=str(method).upper(),
                                file=str(file_path.relative_to(repo_root)),
                                framework="openapi",
                                confidence=0.99,
                            )
                        )
            else:
                endpoints.append(
                    APIEndpoint(
                        service=service_name,
                        path=path_value,
                        method="ANY",
                        file=str(file_path.relative_to(repo_root)),
                        framework="openapi",
                        confidence=0.95,
                    )
                )
    return endpoints
