from __future__ import annotations

from pathlib import Path

from kt_ai.domain.models import APIEndpoint, Evidence, KnowledgeBase, ParsedArtifact, RepositoryInfo, Service

SERVICE_HINT_FILES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pom.xml",
    "go.mod",
    "Cargo.toml",
    "build.gradle",
}

DATABASE_KEYWORDS = {"postgres", "mysql", "mongodb", "redis", "cassandra", "dynamodb", "neo4j"}
QUEUE_KEYWORDS = {"kafka", "rabbitmq", "sqs", "pubsub", "nats", "activemq"}

SERVICE_CONFIDENCE = {
    "compose_service": 1.0,
    "k8s_deployment": 0.95,
    "k8s_statefulset": 0.95,
    "k8s_daemonset": 0.95,
    "k8s_job": 0.9,
    "k8s_cronjob": 0.9,
    "k8s_service": 0.88,
    "build_manifest": 0.7,
    "path_heuristic": 0.45,
}

API_CONFIDENCE = {
    "api_spec": 0.98,
    "framework_routes": 0.72,
}


def _infer_service_name(path: Path, repo_root: Path) -> str:
    rel = path.relative_to(repo_root)
    if len(rel.parts) == 1:
        return repo_root.name
    return rel.parts[0]


def _get_or_create_service(services: dict[str, Service], service_name: str) -> Service:
    if service_name not in services:
        services[service_name] = Service(name=service_name)
    return services[service_name]


def _push_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _add_evidence(
    service: Service,
    source: str,
    file_path: Path,
    detail: str,
    confidence: float,
    deployable: bool = False,
) -> None:
    service.evidence.append(
        Evidence(
            source=source,
            file_path=file_path,
            detail=detail,
            confidence=confidence,
        )
    )
    if confidence > service.confidence:
        service.confidence = confidence
    if deployable and confidence >= service.confidence:
        service.deployable = True
        service.deployable_source = source


def _service_name_from_artifact(artifact: ParsedArtifact, repo: RepositoryInfo) -> str:
    if artifact.kind == "compose_service":
        service_name = str(artifact.metadata.get("service_name", "")).strip()
        if service_name:
            return service_name

    if artifact.kind.startswith("k8s_"):
        metadata_name = str(artifact.metadata.get("name", "")).strip()
        if metadata_name:
            return metadata_name

    return _infer_service_name(artifact.file_path, repo.local_path)


def extract_knowledge(repo: RepositoryInfo, artifacts: list[ParsedArtifact]) -> KnowledgeBase:
    services: dict[str, Service] = {}
    databases: set[str] = set()
    queues: set[str] = set()
    ci_pipelines: set[str] = set()

    # Stage 1: explicit deployable units from declarative infrastructure.
    for artifact in artifacts:
        if artifact.kind not in {
            "compose_service",
            "k8s_deployment",
            "k8s_statefulset",
            "k8s_daemonset",
            "k8s_job",
            "k8s_cronjob",
            "k8s_service",
        }:
            continue
        service_name = _service_name_from_artifact(artifact, repo)
        service = _get_or_create_service(services, service_name)
        if artifact.file_path not in service.paths:
            service.paths.append(artifact.file_path)
        confidence = SERVICE_CONFIDENCE.get(artifact.kind, 0.5)
        _add_evidence(
            service,
            source=artifact.kind,
            file_path=artifact.file_path,
            detail=f"Declared as {artifact.kind}",
            confidence=confidence,
            deployable=True,
        )

    # Stage 2: build manifests and service hint files.
    for file_path in repo.files:
        if file_path.name in SERVICE_HINT_FILES:
            service_name = _infer_service_name(file_path, repo.local_path)
            service = _get_or_create_service(services, service_name)
            if file_path not in service.paths:
                service.paths.append(file_path)
            _add_evidence(
                service,
                source="build_manifest",
                file_path=file_path,
                detail=f"Service hint file: {file_path.name}",
                confidence=SERVICE_CONFIDENCE["build_manifest"],
                deployable=False,
            )

    # Stage 3: artifact enrichment and fallback mapping.
    for artifact in artifacts:
        service_name = _service_name_from_artifact(artifact, repo)
        service = _get_or_create_service(services, service_name)

        if artifact.file_path not in service.paths:
            service.paths.append(artifact.file_path)

        if artifact.kind == "dockerfile":
            base_images = artifact.metadata.get("base_images", [])
            if isinstance(base_images, list):
                for image in base_images:
                    _push_unique(service.runtime_hints, str(image))
                _add_evidence(
                    service,
                    source="dockerfile",
                    file_path=artifact.file_path,
                    detail="Runtime inferred from base image",
                    confidence=0.78,
                    deployable=False,
                )

        if artifact.kind == "api_spec":
            endpoints = artifact.metadata.get("endpoints", [])
            if isinstance(endpoints, list):
                for endpoint in endpoints:
                    endpoint_text = str(endpoint)
                    _push_unique(service.apis, endpoint_text)
                    method = endpoint_text.split(" ", 1)[0] if " " in endpoint_text else "ANY"
                    path = endpoint_text.split(" ", 1)[1] if " " in endpoint_text else endpoint_text
                    service.api_endpoints.append(
                        APIEndpoint(
                            path=path,
                            method=method,
                            source="openapi",
                            confidence=API_CONFIDENCE["api_spec"],
                            file_path=artifact.file_path,
                        )
                    )
                _add_evidence(
                    service,
                    source="api_spec",
                    file_path=artifact.file_path,
                    detail="API endpoints declared in OpenAPI/Swagger",
                    confidence=API_CONFIDENCE["api_spec"],
                    deployable=False,
                )

        if artifact.kind == "framework_routes":
            endpoints = artifact.metadata.get("endpoints", [])
            if isinstance(endpoints, list):
                for endpoint in endpoints:
                    endpoint_text = str(endpoint)
                    _push_unique(service.apis, endpoint_text)
                    method = endpoint_text.split(" ", 1)[0] if " " in endpoint_text else "ANY"
                    path = endpoint_text.split(" ", 1)[1] if " " in endpoint_text else endpoint_text
                    service.api_endpoints.append(
                        APIEndpoint(
                            path=path,
                            method=method,
                            source="framework_route",
                            confidence=API_CONFIDENCE["framework_routes"],
                            file_path=artifact.file_path,
                        )
                    )
                _add_evidence(
                    service,
                    source="framework_routes",
                    file_path=artifact.file_path,
                    detail="Endpoints inferred from framework-aware route patterns",
                    confidence=API_CONFIDENCE["framework_routes"],
                    deployable=False,
                )

        if artifact.kind in {"json_manifest", "build_manifest"}:
            dependencies = artifact.metadata.get("dependencies", [])
            if isinstance(dependencies, list):
                for dep in dependencies:
                    dep_lower = str(dep).lower()
                    for db in DATABASE_KEYWORDS:
                        if db in dep_lower:
                            databases.add(db)
                            _push_unique(service.dependencies, db)
                    for queue in QUEUE_KEYWORDS:
                        if queue in dep_lower:
                            queues.add(queue)
                            _push_unique(service.dependencies, queue)
                _add_evidence(
                    service,
                    source=artifact.kind,
                    file_path=artifact.file_path,
                    detail="Dependencies inferred from build manifest",
                    confidence=0.75,
                    deployable=False,
                )

        if artifact.kind.startswith("k8s_"):
            _push_unique(service.infra, artifact.kind.replace("k8s_", "kubernetes:"))

        if artifact.kind == "ci_cd":
            ci_pipelines.add(str(artifact.file_path.relative_to(repo.local_path)))

    for service_name, service in services.items():
        if service.confidence <= 0.0:
            service.confidence = SERVICE_CONFIDENCE["path_heuristic"]
            _add_evidence(
                service,
                source="path_heuristic",
                file_path=service.paths[0] if service.paths else repo.local_path,
                detail=f"Fallback service inferred by path for {service_name}",
                confidence=SERVICE_CONFIDENCE["path_heuristic"],
                deployable=False,
            )

    return KnowledgeBase(
        repository=repo,
        artifacts=artifacts,
        services=services,
        databases=databases,
        queues=queues,
        ci_pipelines=ci_pipelines,
    )
