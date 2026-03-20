from __future__ import annotations

import re
from pathlib import Path

from repo_intelligence.models.api import APIEndpoint

ROUTE_PATTERNS = [
    ("fastapi", re.compile(r"@(?:app|router)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']", re.IGNORECASE)),
    ("flask", re.compile(r"@(?:app|bp|blueprint)\.route\(\s*[\"']([^\"']+)[\"'](?:\s*,\s*methods=\[([^\]]+)\])?", re.IGNORECASE)),
    ("express", re.compile(r"(?:app|router)\.(get|post|put|patch|delete|all)\(\s*[\"']([^\"']+)[\"']", re.IGNORECASE)),
]

PROTO_SERVICE_BLOCK_PATTERN = re.compile(r"service\s+([A-Za-z0-9_]+)\s*\{(.*?)\}", re.DOTALL)
PROTO_RPC_PATTERN = re.compile(r"^\s*rpc\s+([A-Za-z0-9_]+)\s*\(.*?\)\s*returns\s*\(.*?\)", re.MULTILINE)
GRPC_REGISTER_PATTERN = re.compile(r"Register([A-Za-z0-9_]+)Server\(", re.IGNORECASE)

GENERIC_DIR_NAMES = {
    "src",
    "app",
    "apps",
    "service",
    "services",
    "cmd",
    "internal",
    "pkg",
    "lib",
    "proto",
    "protos",
    "genproto",
    "grpc",
    "v1",
    "v2",
}


def _infer_service_name(file_path: Path, repo_root: Path) -> str:
    rel = file_path.relative_to(repo_root)
    parts = [part for part in rel.parts[:-1] if part.lower() not in GENERIC_DIR_NAMES]
    if parts:
        return parts[-1]
    return file_path.parent.name


def extract_api_endpoints(file_path: Path, repo_root: Path, content: str) -> list[APIEndpoint]:
    endpoints: list[APIEndpoint] = []
    service_name = _infer_service_name(file_path, repo_root)
    rel = str(file_path.relative_to(repo_root))

    if any(token in file_path.name.lower() for token in {".pb.", "generated", "_generated"}):
        return []

    if file_path.suffix.lower() == ".proto":
        for service_match in PROTO_SERVICE_BLOCK_PATTERN.finditer(content):
            proto_service = service_match.group(1)
            service_block = service_match.group(2)
            proto_service_name = f"{proto_service.lower()}"
            if not proto_service_name.endswith("service"):
                proto_service_name = f"{proto_service_name}-service"
            for rpc_match in PROTO_RPC_PATTERN.finditer(service_block):
                rpc = rpc_match.group(1)
                endpoints.append(
                    APIEndpoint(
                        service=proto_service_name,
                        path=f"/{proto_service}/{rpc}",
                        method="RPC",
                        file=rel,
                        framework="grpc-proto",
                        confidence=0.92,
                    )
                )
        return endpoints

    for framework, pattern in ROUTE_PATTERNS:
        for match in pattern.finditer(content):
            if framework == "flask":
                path = match.group(1)
                methods = match.group(2)
                if methods:
                    method_list = [m.strip().strip("'\"") for m in methods.split(",")]
                else:
                    method_list = ["GET"]
                for method in method_list:
                    endpoints.append(
                        APIEndpoint(
                            service=service_name,
                            path=path,
                            method=method.upper(),
                            file=rel,
                            framework=framework,
                            confidence=0.78,
                        )
                    )
            else:
                method = match.group(1).upper().replace("ALL", "ANY")
                path = match.group(2)
                endpoints.append(
                    APIEndpoint(
                        service=service_name,
                        path=path,
                        method=method,
                        file=rel,
                        framework=framework,
                        confidence=0.75,
                    )
                )

    for match in GRPC_REGISTER_PATTERN.finditer(content):
        grpc_service = match.group(1)
        endpoints.append(
            APIEndpoint(
                service=service_name,
                path=f"/{grpc_service}/*",
                method="RPC",
                file=rel,
                framework="grpc-register",
                confidence=0.82,
            )
        )

    unique: dict[tuple[str, str], APIEndpoint] = {}
    for endpoint in endpoints:
        key = (endpoint.method, endpoint.path)
        if key not in unique:
            unique[key] = endpoint
    return list(unique.values())
