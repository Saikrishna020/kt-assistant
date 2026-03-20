from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repo_intelligence.ast import analyze_code_ast
from repo_intelligence.core import scan_repository
from repo_intelligence.export import export_graph, export_knowledge_store
from repo_intelligence.graph import build_graph
from repo_intelligence.infra import parse_cicd, parse_docker, parse_kubernetes, parse_openapi
from repo_intelligence.knowledge import build_dependencies, classify_services, detect_communications, detect_services
from repo_intelligence.models.system_model import SystemModel

NON_RUNTIME_DIR_TOKENS = {
    "test",
    "tests",
    "__tests__",
    "spec",
    "examples",
    "example",
    "docs",
    "documentation",
    "fixtures",
    "samples",
    "benchmarks",
}


def _is_runtime_candidate(file_path: Path, repo_root: Path) -> bool:
    rel = file_path.relative_to(repo_root)
    parts = {part.lower() for part in rel.parts}
    if parts.intersection(NON_RUNTIME_DIR_TOKENS):
        return False
    lowered_name = file_path.name.lower()
    if lowered_name.startswith("test_") or lowered_name.endswith("_test.py"):
        return False
    return True


def _filter_database_signals(ast_signal, known_services: set[str]) -> int:
    filtered_databases: list[dict[str, str | float]] = []
    dropped = 0
    for item in ast_signal.databases:
        confidence = float(item.get("confidence", 0.0))
        file_path = str(item.get("file", ""))
        if not file_path:
            dropped += 1
            continue
        service_name = Path(file_path).parts[0].lower().replace("_", "-") if Path(file_path).parts else ""
        if service_name not in known_services:
            dropped += 1
            continue
        if confidence < 0.7:
            dropped += 1
            continue
        filtered_databases.append(item)
    ast_signal.databases = filtered_databases
    return dropped


def _canonicalize_infra_signals(infra_signals):
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for signal in infra_signals:
        kind = str(signal.metadata.get("kind", ""))
        key = (signal.service.lower().replace("_", "-"), kind)
        entry = grouped.setdefault(
            key,
            {
                "service": signal.service.lower().replace("_", "-"),
                "path": signal.path,
                "confidence": signal.confidence,
                "metadata": dict(signal.metadata),
                "sources": set(),
            },
        )
        entry["confidence"] = max(float(entry["confidence"]), signal.confidence)
        entry["sources"].add(signal.source)
        if len(signal.path) < len(str(entry["path"])):
            entry["path"] = signal.path

        metadata = entry["metadata"]
        for key_name in {"env_targets", "images"}:
            existing = metadata.get(key_name, [])
            incoming = signal.metadata.get(key_name, [])
            existing_values = set(existing) if isinstance(existing, list) else set()
            incoming_values = set(incoming) if isinstance(incoming, list) else set()
            metadata[key_name] = sorted(existing_values.union(incoming_values))

    from repo_intelligence.models.system_model import InfrastructureSignal

    canonical: list[InfrastructureSignal] = []
    for _, entry in grouped.items():
        sources = sorted(entry["sources"])
        weighted_confidence = min(0.99, float(entry["confidence"]) + min(0.05, (len(sources) - 1) * 0.01))
        metadata = dict(entry["metadata"])
        metadata["sources"] = sources
        canonical.append(
            InfrastructureSignal(
                service=str(entry["service"]),
                path=str(entry["path"]),
                source=sources[0] if sources else "",
                confidence=weighted_confidence,
                metadata=metadata,
            )
        )

    return sorted(canonical, key=lambda item: (item.service, str(item.metadata.get("kind", ""))))


def _dedup_apis(api_list):
    unique = {}
    for endpoint in api_list:
        key = (endpoint.service.lower(), endpoint.method.upper(), endpoint.path)
        existing = unique.get(key)
        if existing is None or endpoint.confidence > existing.confidence:
            unique[key] = endpoint
    return sorted(unique.values(), key=lambda item: (item.service, item.path, item.method))


@dataclass
class PipelineOutput:
    output_root: Path
    knowledge_store: dict[str, Path]


def run_pipeline(repo_source: str, output_root: Path) -> PipelineOutput:
    output_root = output_root.resolve()
    workspace_root = output_root / "workspace"

    # 1) Scan repository.
    repo_metadata, files, repo_root = scan_repository(repo_source, workspace_root)
    runtime_files = [file_path for file_path in files if _is_runtime_candidate(file_path, repo_root)]

    # 2) Analyze infrastructure and OpenAPI.
    docker_signals = parse_docker(runtime_files, repo_root)
    k8s_signals = parse_kubernetes(runtime_files, repo_root)
    infra_signals = _canonicalize_infra_signals([*docker_signals, *k8s_signals])
    cicd_signals = parse_cicd(files, repo_root)
    openapi_endpoints = parse_openapi(runtime_files, repo_root)

    # 3) AST code analysis.
    ast_signal = analyze_code_ast(runtime_files, repo_root)

    # 4) Service detection and dependency understanding.
    services = detect_services(infra_signals, ast_signal, runtime_files, repo_root, openapi_endpoints)
    services = classify_services(services)
    service_names = {service.name for service in services}
    dropped_db_signals = _filter_database_signals(ast_signal, service_names)
    comm_edges = detect_communications(ast_signal, infra_signals, service_names)
    dependencies = build_dependencies(services, ast_signal, comm_edges)

    # Enrich services with their dependencies from the detected edges
    dep_map: dict[str, set[str]] = {}
    for dep in dependencies:
        if dep.source_service not in dep_map:
            dep_map[dep.source_service] = set()
        dep_map[dep.source_service].add(dep.target)

    for service in services:
        if service.name in dep_map:
            service.dependencies = sorted(list(dep_map[service.name]))

    apis = _dedup_apis([*openapi_endpoints, *ast_signal.apis])

    system_model = SystemModel(
        repository=repo_metadata,
        services=services,
        apis=apis,
        dependencies=dependencies,
        infrastructure=infra_signals,
        observations={
            "cicd": [str(entry.get("path", "")) for entry in cicd_signals],
            "ast": [
                f"apis={len(ast_signal.apis)}",
                f"apis_deduped={len(apis)}",
                f"database_signals={len(ast_signal.databases)}",
                f"database_signals_dropped={dropped_db_signals}",
                f"service_calls={len(ast_signal.service_calls)}",
                f"imports={len(ast_signal.imports)}",
            ],
        },
    )

    # 5) Graph and export.
    graph = build_graph(system_model)
    graph_json = export_graph(graph)
    output_files = export_knowledge_store(output_root, system_model, graph_json)

    return PipelineOutput(output_root=output_root, knowledge_store=output_files)
