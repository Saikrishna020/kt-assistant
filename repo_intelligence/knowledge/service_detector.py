from __future__ import annotations

import re
from pathlib import Path

from repo_intelligence.models.api import APIEndpoint
from repo_intelligence.models.service import Service
from repo_intelligence.models.system_model import ASTSignal, InfrastructureSignal

SERVICE_HINT_FILES = {"package.json", "pyproject.toml", "requirements.txt", "go.mod", "pom.xml", "Cargo.toml"}
GENERIC_SERVICE_NAMES = {
    "src",
    "app",
    "apps",
    "service",
    "services",
    "code",
    "lib",
    "pkg",
    "internal",
    "cmd",
    "proto",
    "protos",
    "genproto",
    "grpc",
    "v1",
    "v2",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "node",
    ".ts": "node",
    ".tsx": "node",
    ".go": "go",
    ".java": "java",
    ".cs": "dotnet",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
}

NON_SOURCE_PATH_TOKENS = {
    "kubernetes-manifests",
    "kustomize",
    "release",
    ".github",
    "helm",
    "manifests",
    "deploy",
    "deployment",
}


def _normalize(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _runtime_from_path(path_text: str) -> str:
    path = Path(path_text)
    name = path.name.lower()
    if name in {"package.json"}:
        return "node"
    if name in {"requirements.txt", "pyproject.toml"}:
        return "python"
    if name == "go.mod":
        return "go"
    if name == "pom.xml":
        return "java"
    return "unknown"


def _service_token(name: str) -> str:
    token = _normalize(name)
    if token.endswith("-service"):
        return token[: -len("-service")]
    if token.endswith("service") and len(token) > len("service"):
        return token[: -len("service")]
    return token


def _is_likely_service_name(name: str) -> bool:
    if name in GENERIC_SERVICE_NAMES:
        return False
    token = _normalize(name)
    if token.endswith("service") or token.endswith("-service"):
        return True
    return token in {"frontend", "backend", "gateway", "redis", "redis-cart", "loadgenerator"}


def _infer_service_from_rel_path(rel: Path, repo_root: Path) -> str:
    if len(rel.parts) <= 1:
        return _normalize(repo_root.name)
    first = _normalize(rel.parts[0])
    if first in GENERIC_SERVICE_NAMES and len(rel.parts) > 2:
        return _normalize(rel.parts[1])
    return first


def _extract_readme_hints(files: list[Path], repo_root: Path) -> set[str]:
    hints: set[str] = set()
    for file_path in files:
        if file_path.name.lower() not in {"readme.md", "readme"}:
            continue
        rel = file_path.relative_to(repo_root)
        if len(rel.parts) > 1:
            continue
        content = file_path.read_text(encoding="utf-8", errors="ignore")[:300_000]
        for match in re.findall(r"\b([a-zA-Z0-9_-]+service)\b", content):
            hints.add(_normalize(match))
    return hints


def _extract_image_tokens(images: list[str]) -> set[str]:
    tokens: set[str] = set()
    for image in images:
        value = image.strip().lower()
        if not value:
            continue
        tail = value.split("/")[-1].split(":")[0]
        base = _normalize(tail)
        if base:
            tokens.add(base)
            tokens.add(_service_token(base))
        for part in re.split(r"[^a-z0-9]+", base):
            part = part.strip()
            if len(part) > 2:
                tokens.add(part)
    return {token for token in tokens if token and token not in GENERIC_SERVICE_NAMES}


def _collect_source_candidates(files: list[Path], repo_root: Path) -> dict[str, dict[str, object]]:
    candidates: dict[str, dict[str, object]] = {}
    for file_path in files:
        rel = file_path.relative_to(repo_root)
        if len(rel.parts) < 2:
            continue
        if any(token in {part.lower() for part in rel.parts} for token in NON_SOURCE_PATH_TOKENS):
            continue

        for depth in range(1, min(4, len(rel.parts))):
            prefix = Path(*rel.parts[:depth])
            key = str(prefix)
            entry = candidates.setdefault(
                key,
                {
                    "path": key,
                    "tokens": set(),
                    "has_dockerfile": False,
                    "has_service_manifest": False,
                    "code_files": 0,
                },
            )
            entry["tokens"].update({_normalize(part) for part in prefix.parts})
            if file_path.name.lower() == "dockerfile":
                entry["has_dockerfile"] = True
            if file_path.name in SERVICE_HINT_FILES:
                entry["has_service_manifest"] = True
            if file_path.suffix.lower() in LANGUAGE_BY_SUFFIX:
                entry["code_files"] = int(entry["code_files"]) + 1

    return candidates


def _find_service_source_path(
    service_name: str,
    files: list[Path],
    repo_root: Path,
    image_tokens: set[str],
    source_candidates: dict[str, dict[str, object]],
    current_path: str,
) -> str:
    service_token = _service_token(service_name)

    best_path = current_path or service_name
    best_score = -1.0
    best_matched_identity = False

    for key, candidate in source_candidates.items():
        tokens = {str(token) for token in candidate["tokens"]}
        score = 0.0
        matched_identity = False

        if service_name in tokens:
            score += 6.0
            matched_identity = True
        if service_token in tokens:
            score += 5.0
            matched_identity = True
        if any(token in tokens for token in image_tokens):
            score += 4.0
            matched_identity = True
        if candidate.get("has_dockerfile"):
            score += 1.8
        if candidate.get("has_service_manifest"):
            score += 1.6
        code_files = int(candidate.get("code_files", 0))
        score += min(2.5, code_files * 0.04)

        if key.startswith("src"):
            score += 0.8

        if score > best_score:
            best_score = score
            best_path = key
            best_matched_identity = matched_identity

    if best_score < 1.5 or not best_matched_identity:
        return current_path or service_name
    return best_path


def _infer_runtime_from_subtree(service_path: str, files: list[Path], repo_root: Path) -> str:
    subtree = Path(service_path)
    language_counts: dict[str, int] = {}
    for file_path in files:
        rel = file_path.relative_to(repo_root)
        if subtree.parts and rel.parts[: len(subtree.parts)] != subtree.parts:
            continue
        runtime = _runtime_from_path(str(file_path))
        if runtime != "unknown":
            return runtime
        language = LANGUAGE_BY_SUFFIX.get(file_path.suffix.lower())
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1
    if not language_counts:
        return "unknown"
    return sorted(language_counts.items(), key=lambda item: item[1], reverse=True)[0][0]


def _dedup_evidence(items: list[dict[str, str | float]]) -> list[dict[str, str | float]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, str | float]] = []
    for item in items:
        source = str(item.get("source", ""))
        detail = str(item.get("detail", ""))
        confidence = f"{float(item.get('confidence', 0.0)):.2f}"
        key = (source, detail, confidence)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _recompute_confidence(service: Service, readme_hints: set[str]) -> float:
    sources = {str(ev.get("detail", "")) for ev in service.evidence}
    score = 0.0
    if any("infra" in source for source in sources):
        score += 0.62
    if service.apis:
        score += 0.12
    if service.databases:
        score += 0.08
    if service.runtime != "unknown":
        score += 0.08
    if service.name in readme_hints:
        score += 0.08
    if len(service.evidence) >= 3:
        score += 0.06
    return min(0.99, max(service.confidence, score))


def detect_services(
    infra_signals: list[InfrastructureSignal],
    ast_signal: ASTSignal,
    files: list[Path],
    repo_root: Path,
    openapi_endpoints: list[APIEndpoint],
) -> list[Service]:
    services: dict[str, Service] = {}
    readme_hints = _extract_readme_hints(files, repo_root)
    source_candidates = _collect_source_candidates(files, repo_root)
    service_image_tokens: dict[str, set[str]] = {}

    # Priority 1-3: declarative infrastructure.
    for signal in sorted(infra_signals, key=lambda item: item.confidence, reverse=True):
        name = _normalize(signal.service)
        if not name:
            continue
        if name in GENERIC_SERVICE_NAMES:
            continue
        service = services.get(name)
        if not service:
            service = Service(
                name=name,
                path=signal.path or ".",
                runtime="unknown",
                confidence=signal.confidence,
                source=signal.source,
                evidence=[{"source": signal.source, "confidence": signal.confidence, "detail": "infra declaration"}],
            )
            services[name] = service
        elif signal.confidence > service.confidence:
            service.confidence = signal.confidence
            service.source = signal.source
            service.path = signal.path or service.path
        service.evidence.append({"source": signal.source, "confidence": signal.confidence, "detail": "infra declaration"})

        images = signal.metadata.get("images", [])
        if isinstance(images, list):
            image_tokens = _extract_image_tokens([str(image) for image in images])
            if image_tokens:
                service_image_tokens.setdefault(name, set()).update(image_tokens)

    # Priority 4: repo structure heuristics.
    for file_path in files:
        if file_path.name not in SERVICE_HINT_FILES:
            continue
        rel = file_path.relative_to(repo_root)
        service_name = _infer_service_from_rel_path(rel, repo_root)
        if not service_name:
            continue
        if service_name in GENERIC_SERVICE_NAMES:
            continue
        runtime = _runtime_from_path(str(file_path))
        service = services.get(service_name)
        if not service:
            services[service_name] = Service(
                name=service_name,
                path=str(rel.parent),
                runtime=runtime,
                confidence=0.62,
                source="directory_heuristic",
                evidence=[{"source": str(rel), "confidence": 0.62, "detail": "service hint file"}],
            )
            continue
        service.runtime = runtime if service.runtime == "unknown" else service.runtime
        service.evidence.append({"source": str(rel), "confidence": 0.62, "detail": "service hint file"})

    # Enrich from OpenAPI and AST APIs.
    api_by_service: dict[str, list[str]] = {}
    for endpoint in [*openapi_endpoints, *ast_signal.apis]:
        name = _normalize(endpoint.service)
        if name in GENERIC_SERVICE_NAMES:
            continue
        api_by_service.setdefault(name, []).append(f"{endpoint.method} {endpoint.path}")

    for service_name, endpoints in api_by_service.items():
        service = services.get(service_name)
        if not service:
            if not _is_likely_service_name(service_name):
                continue
            services[service_name] = Service(
                name=service_name,
                path=service_name,
                runtime="unknown",
                confidence=0.58,
                source="api_inference",
                apis=sorted(set(endpoints)),
                evidence=[{"source": "api", "confidence": 0.58, "detail": "service inferred from API"}],
            )
            continue
        service.apis = sorted(set([*service.apis, *endpoints]))

    # Enrich databases from AST detections.
    db_by_service: dict[str, list[str]] = {}
    for db in ast_signal.databases:
        file_path = str(db.get("file", ""))
        if not file_path:
            continue
        service_name = _normalize(Path(file_path).parts[0]) if Path(file_path).parts else ""
        if not service_name:
            continue
        db_by_service.setdefault(service_name, []).append(str(db.get("database", "")))

    for service_name, dbs in db_by_service.items():
        service = services.get(service_name)
        if not service:
            continue
        service.databases = sorted(set([*service.databases, *[db for db in dbs if db]]))

    for service in services.values():
        image_tokens = service_image_tokens.get(service.name, set())
        service.path = _find_service_source_path(
            service.name,
            files,
            repo_root,
            image_tokens=image_tokens,
            source_candidates=source_candidates,
            current_path=service.path,
        )
        if service.runtime == "unknown":
            service.runtime = _infer_runtime_from_subtree(service.path, files, repo_root)
        service.evidence = _dedup_evidence(service.evidence)
        service.confidence = _recompute_confidence(service, readme_hints)

    services = {
        name: service
        for name, service in services.items()
        if name not in GENERIC_SERVICE_NAMES
        and not (name in {"localhost", "default"})
        and not (
            service.source == "api_inference"
            and service.confidence < 0.7
            and (
                (service.runtime == "unknown" and any(token in service.path.lower() for token in {"proto", "protos", "grpc"}))
                or service.name.startswith("health")
                or service.name.endswith("-health")
            )
        )
    }

    return sorted(services.values(), key=lambda item: item.name)
