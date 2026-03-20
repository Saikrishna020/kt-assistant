from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from kt_ai.domain.models import ParsedArtifact, RepositoryInfo

COMPOSE_FILENAMES = {
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

ROUTE_PATTERNS = [
    re.compile(r"@(?:app|router|blueprint|bp)\.(get|post|put|patch|delete|route)\(['\"]([^'\"]+)['\"]", re.IGNORECASE),
    re.compile(r"(?:app|router)\.(get|post|put|patch|delete|all)\(['\"]([^'\"]+)['\"]", re.IGNORECASE),
    re.compile(r"\[(HttpGet|HttpPost|HttpPut|HttpPatch|HttpDelete)\((?:@?\"([^\"]+)\")?", re.IGNORECASE),
    re.compile(r"(GET|POST|PUT|PATCH|DELETE)\s+(/[^\s\"']+)", re.IGNORECASE),
]


def _read_text(path: Path, max_chars: int = 40_000) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return content[:max_chars]


def _is_openapi_document(doc: dict[str, Any]) -> bool:
    return any(key in doc for key in {"openapi", "swagger", "paths", "webhooks", "components"})


def _parse_dockerfile(path: Path) -> ParsedArtifact:
    content = _read_text(path)
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    base_images = [line.split(maxsplit=1)[1] for line in lines if line.upper().startswith("FROM ") and len(line.split()) > 1]
    exposed_ports = [line.split(maxsplit=1)[1] for line in lines if line.upper().startswith("EXPOSE ") and len(line.split()) > 1]
    return ParsedArtifact(
        file_path=path,
        kind="dockerfile",
        metadata={"base_images": base_images, "exposed_ports": exposed_ports},
    )


def _parse_compose(path: Path, doc: dict[str, Any]) -> list[ParsedArtifact]:
    services = doc.get("services", {})
    if not isinstance(services, dict):
        return []

    artifacts: list[ParsedArtifact] = []
    for service_name, payload in services.items():
        if not isinstance(payload, dict):
            payload = {}
        ports = payload.get("ports", [])
        depends_on = payload.get("depends_on", [])

        artifacts.append(
            ParsedArtifact(
                file_path=path,
                kind="compose_service",
                metadata={
                    "service_name": str(service_name),
                    "image": str(payload.get("image", "")),
                    "build": str(payload.get("build", "")),
                    "ports": [str(p) for p in ports] if isinstance(ports, list) else [],
                    "depends_on": [str(d) for d in depends_on] if isinstance(depends_on, list) else [],
                },
            )
        )
    return artifacts


def _extract_openapi_endpoints(doc: dict[str, Any]) -> list[str]:
    paths = doc.get("paths", {})
    if not isinstance(paths, dict):
        return []

    endpoints: list[str] = []
    for path_value, operations in paths.items():
        if not isinstance(path_value, str):
            continue
        if isinstance(operations, dict):
            methods = [m.upper() for m in operations.keys() if str(m).lower() in HTTP_METHODS]
            if methods:
                for method in methods:
                    endpoints.append(f"{method} {path_value}")
                continue
        endpoints.append(path_value)
    return endpoints[:250]


def _parse_yaml(path: Path) -> list[ParsedArtifact]:
    content = _read_text(path)
    docs: list[Any] = []
    try:
        docs = [d for d in yaml.safe_load_all(content) if d]
    except yaml.YAMLError:
        return []

    artifacts: list[ParsedArtifact] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue

        if path.name.lower() in COMPOSE_FILENAMES and isinstance(doc.get("services"), dict):
            artifacts.extend(_parse_compose(path, doc))

        if _is_openapi_document(doc):
            artifacts.append(
                ParsedArtifact(
                    file_path=path,
                    kind="api_spec",
                    metadata={"endpoints": _extract_openapi_endpoints(doc)},
                )
            )

        kind = str(doc.get("kind", "yaml")).lower()
        metadata: dict[str, str | list[str]] = {
            "name": str(doc.get("metadata", {}).get("name", "")),
            "apiVersion": str(doc.get("apiVersion", "")),
        }

        spec = doc.get("spec", {}) if isinstance(doc.get("spec"), dict) else {}
        if kind == "deployment":
            replicas = spec.get("replicas", "")
            template_spec = spec.get("template", {}).get("spec", {}) if isinstance(spec.get("template"), dict) else {}
            containers = template_spec.get("containers", []) if isinstance(template_spec, dict) else []
            metadata["replicas"] = str(replicas)
            metadata["containers"] = [
                str(container.get("name", ""))
                for container in containers
                if isinstance(container, dict) and container.get("name")
            ]
        if kind == "service":
            ports = spec.get("ports", []) if isinstance(spec, dict) else []
            metadata["ports"] = [
                str(port.get("port", ""))
                for port in ports
                if isinstance(port, dict) and port.get("port")
            ]

        if kind in {"deployment", "service", "ingress", "statefulset", "daemonset", "job", "cronjob"}:
            artifacts.append(ParsedArtifact(file_path=path, kind=f"k8s_{kind}", metadata=metadata))
        elif "pipeline" in path.name.lower() or ".github/workflows" in path.as_posix().lower():
            artifacts.append(ParsedArtifact(file_path=path, kind="ci_cd", metadata=metadata))
        else:
            artifacts.append(ParsedArtifact(file_path=path, kind="yaml", metadata=metadata))

    return artifacts


def _parse_json(path: Path) -> ParsedArtifact | None:
    content = _read_text(path)
    try:
        doc = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(doc, dict):
        return None

    if _is_openapi_document(doc):
        return ParsedArtifact(
            file_path=path,
            kind="api_spec",
            metadata={"endpoints": _extract_openapi_endpoints(doc)},
        )

    name = str(doc.get("name", ""))
    deps = list((doc.get("dependencies") or {}).keys()) if isinstance(doc.get("dependencies"), dict) else []
    scripts = list((doc.get("scripts") or {}).keys()) if isinstance(doc.get("scripts"), dict) else []

    return ParsedArtifact(
        file_path=path,
        kind="build_manifest",
        metadata={
            "manifest_type": "package_json",
            "name": name,
            "dependencies": deps[:150],
            "scripts": scripts[:150],
        },
    )


def _parse_api_spec(path: Path) -> ParsedArtifact | None:
    lowered = path.name.lower()
    if "openapi" not in lowered and "swagger" not in lowered:
        return None

    content = _read_text(path)
    endpoints: list[str] = []

    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            doc = yaml.safe_load(content) or {}
        except yaml.YAMLError:
            doc = {}
        if isinstance(doc, dict):
            paths = doc.get("paths", {})
            if isinstance(paths, dict):
                endpoints = list(paths.keys())[:200]

    return ParsedArtifact(
        file_path=path,
        kind="api_spec",
        metadata={"endpoints": endpoints},
    )


def _parse_build_manifest(path: Path) -> ParsedArtifact | None:
    name = path.name.lower()
    if name == "requirements.txt":
        lines = [line.strip() for line in _read_text(path).splitlines() if line.strip() and not line.startswith("#")]
        deps = [line.split("==")[0].split(">=")[0].split("<=")[0].strip() for line in lines]
        return ParsedArtifact(
            file_path=path,
            kind="build_manifest",
            metadata={"manifest_type": "requirements_txt", "dependencies": deps[:200]},
        )
    if name == "pyproject.toml":
        content = _read_text(path)
        deps = re.findall(r"[\"']([a-zA-Z0-9_.-]+)[\"']", content)
        return ParsedArtifact(
            file_path=path,
            kind="build_manifest",
            metadata={"manifest_type": "pyproject_toml", "dependencies": deps[:200]},
        )
    if name == "go.mod":
        content = _read_text(path)
        deps = re.findall(r"^\s*([a-zA-Z0-9./_-]+)\s+v[0-9]", content, flags=re.MULTILINE)
        return ParsedArtifact(
            file_path=path,
            kind="build_manifest",
            metadata={"manifest_type": "go_mod", "dependencies": deps[:200]},
        )
    if name == "pom.xml":
        content = _read_text(path)
        deps = re.findall(r"<artifactId>([^<]+)</artifactId>", content)
        return ParsedArtifact(
            file_path=path,
            kind="build_manifest",
            metadata={"manifest_type": "pom_xml", "dependencies": deps[:200]},
        )
    return None


def _parse_code_routes(path: Path) -> list[ParsedArtifact]:
    if path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".go", ".java", ".cs", ".rb", ".php"}:
        return []

    content = _read_text(path, max_chars=120_000)
    matches: list[str] = []

    for pattern in ROUTE_PATTERNS:
        for match in pattern.finditer(content):
            method_raw = match.group(1) if match.lastindex and match.lastindex >= 1 else "GET"
            route_raw = match.group(2) if match.lastindex and match.lastindex >= 2 else ""
            method = method_raw.replace("Http", "").replace("route", "GET").replace("all", "ANY").upper()
            route = route_raw or "/"
            if route.startswith("/"):
                matches.append(f"{method} {route}")

    if not matches:
        return []

    unique_routes = sorted(set(matches))[:200]
    return [
        ParsedArtifact(
            file_path=path,
            kind="framework_routes",
            metadata={"endpoints": unique_routes},
        )
    ]


def parse_repository(repo: RepositoryInfo) -> list[ParsedArtifact]:
    artifacts: list[ParsedArtifact] = []

    for file_path in repo.files:
        name_lower = file_path.name.lower()

        if name_lower == "dockerfile" or name_lower.endswith(".dockerfile"):
            artifacts.append(_parse_dockerfile(file_path))
            continue

        if file_path.suffix.lower() in {".yaml", ".yml"}:
            artifacts.extend(_parse_yaml(file_path))
            api_artifact = _parse_api_spec(file_path)
            if api_artifact:
                artifacts.append(api_artifact)
            continue

        if file_path.suffix.lower() == ".json":
            json_artifact = _parse_json(file_path)
            if json_artifact:
                artifacts.append(json_artifact)
            continue

        manifest_artifact = _parse_build_manifest(file_path)
        if manifest_artifact:
            artifacts.append(manifest_artifact)
            continue

        if "jenkinsfile" in name_lower or "gitlab-ci" in name_lower:
            artifacts.append(ParsedArtifact(file_path=file_path, kind="ci_cd", metadata={"name": file_path.name}))

        artifacts.extend(_parse_code_routes(file_path))

    return artifacts
