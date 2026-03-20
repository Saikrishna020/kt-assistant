from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

SERVICE_CALL_PATTERNS = [
    re.compile(r"requests\.(?:get|post|put|patch|delete)\(\s*[\"'](https?://[^\"']+)", re.IGNORECASE),
    re.compile(r"axios\.(?:get|post|put|patch|delete)\(\s*[\"'](https?://[^\"']+)", re.IGNORECASE),
    re.compile(r"grpc\.insecure_channel\(\s*[\"']([^\"']+)", re.IGNORECASE),
    re.compile(r"http[s]?://([a-zA-Z0-9._:-]+)", re.IGNORECASE),
]

INVALID_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "["}


def _normalize_target(raw_target: str) -> str | None:
    value = raw_target.strip().strip("'\"")
    if not value:
        return None

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        host = (parsed.hostname or "").strip().lower()
    else:
        host = value.split("/")[0].split(":")[0].strip().lower()

    if not host or host in INVALID_HOSTS:
        return None
    if any(ch in host for ch in "[]{}()"):
        return None

    host = host.replace("_", "-")
    if "." in host and not host.endswith(".svc") and not host.endswith(".local"):
        # Likely an external domain; keep only likely internal service tokens.
        token = host.split(".")[0]
        if token.endswith("-service"):
            return token
        return None

    return host


def extract_service_calls(file_path: Path, repo_root: Path, content: str) -> list[dict[str, str | float]]:
    source_service = file_path.parent.name
    rel = str(file_path.relative_to(repo_root))
    calls: list[dict[str, str | float]] = []

    for pattern in SERVICE_CALL_PATTERNS:
        for match in pattern.finditer(content):
            target = _normalize_target(match.group(1))
            if not target:
                continue
            calls.append(
                {
                    "source": source_service,
                    "target": target,
                    "file": rel,
                    "confidence": 0.74,
                    "evidence": match.group(0)[:120],
                }
            )

    unique: dict[str, dict[str, str | float]] = {}
    for call in calls:
        key = f"{call['source']}->{call['target']}"
        if key not in unique:
            unique[key] = call
    return list(unique.values())
