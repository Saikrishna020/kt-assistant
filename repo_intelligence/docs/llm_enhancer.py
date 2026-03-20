from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from groq import Groq

DOC_NAMES = ["README.md", "architecture.md", "services.md", "apis.md", "infrastructure.md", "knowledge_gap.md"]
MAX_SERVICES_CONTEXT = 80
MAX_APIS_CONTEXT = 250
MAX_DEPENDENCIES_CONTEXT = 250


def _read_text(path: Path, max_chars: int = 150_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def _deterministic_gaps(system_understanding: dict[str, Any]) -> list[str]:
    gaps: list[str] = []

    services = system_understanding.get("services", [])
    dependencies = system_understanding.get("dependencies", [])
    apis = system_understanding.get("apis", [])
    observations = system_understanding.get("observations", {})

    unknown_runtime = [service.get("name", "") for service in services if service.get("runtime") == "unknown"]
    if unknown_runtime:
        gaps.append("Runtime unknown for services: " + ", ".join(sorted(set(str(name) for name in unknown_runtime if name))))

    no_api_services = [service.get("name", "") for service in services if not service.get("apis")]
    if no_api_services:
        gaps.append("No API surface detected for services: " + ", ".join(sorted(set(str(name) for name in no_api_services if name))))

    if not dependencies:
        gaps.append("No service dependency edges detected; communication mapping may be incomplete.")

    if not apis:
        gaps.append("No APIs detected at all; verify route/proto coverage and framework rules.")

    cicd = observations.get("cicd", []) if isinstance(observations, dict) else []
    if not cicd:
        gaps.append("No CI/CD pipelines detected from repository files.")

    unknown_artifacts = [
        service.get("name", "")
        for service in services
        if service.get("component_type") in {"unknown_artifact"}
    ]
    if unknown_artifacts:
        gaps.append(
            "Unknown artifact classification for: "
            + ", ".join(sorted(set(str(name) for name in unknown_artifacts if name)))
        )

    return gaps


def _compact_context(system_understanding: dict[str, Any], docs_payload: dict[str, str]) -> dict[str, Any]:
    services_raw = system_understanding.get("services", [])
    apis_raw = system_understanding.get("apis", [])
    dependencies_raw = system_understanding.get("dependencies", [])

    services = []
    for service in services_raw[:MAX_SERVICES_CONTEXT]:
        if not isinstance(service, dict):
            continue
        services.append(
            {
                "name": service.get("name", ""),
                "component_type": service.get("component_type", "unknown_artifact"),
                "path": service.get("path", ""),
                "runtime": service.get("runtime", "unknown"),
                "confidence": service.get("confidence", 0.0),
                "source": service.get("source", ""),
                "apis": (service.get("apis", []) or [])[:20],
                "databases": (service.get("databases", []) or [])[:20],
            }
        )

    apis = []
    for endpoint in apis_raw[:MAX_APIS_CONTEXT]:
        if not isinstance(endpoint, dict):
            continue
        apis.append(
            {
                "service": endpoint.get("service", ""),
                "method": endpoint.get("method", ""),
                "path": endpoint.get("path", ""),
                "framework": endpoint.get("framework", ""),
                "confidence": endpoint.get("confidence", 0.0),
            }
        )

    dependencies = []
    for dependency in dependencies_raw[:MAX_DEPENDENCIES_CONTEXT]:
        if not isinstance(dependency, dict):
            continue
        dependencies.append(
            {
                "source_service": dependency.get("source_service", ""),
                "target": dependency.get("target", ""),
                "type": dependency.get("type", ""),
                "confidence": dependency.get("confidence", 0.0),
            }
        )

    doc_summaries = {
        name: text[:20_000]
        for name, text in docs_payload.items()
    }

    return {
        "repository": system_understanding.get("repository", {}),
        "services": services,
        "apis": apis,
        "dependencies": dependencies,
        "infrastructure_count": len(system_understanding.get("infrastructure", [])),
        "observations": system_understanding.get("observations", {}),
        "existing_docs": doc_summaries,
    }


def _build_prompt(system_understanding: dict[str, Any], docs_payload: dict[str, str], deterministic_gaps: list[str]) -> str:
    payload = _compact_context(system_understanding, docs_payload)
    payload["deterministic_gaps"] = deterministic_gaps

    return "\n".join(
        [
            "You are a senior software architect and technical writer.",
            "Generate high-quality repository documentation with strict factual grounding.",
            "Use only the context JSON below and existing docs. Do not invent services, APIs, dependencies, files, runtimes, or tools.",
            "If data is missing, explicitly say 'Not detected in current analysis'.",
            "Keep content practical and concise for developers.",
            "Knowledge gaps must include deterministic gaps and any additional evidence-based gaps only.",
            "",
            "Return exactly these markdown files with markers:",
            "=== README.md ===",
            "=== architecture.md ===",
            "=== services.md ===",
            "=== apis.md ===",
            "=== infrastructure.md ===",
            "=== knowledge_gap.md ===",
            "",
            "For knowledge_gap.md include:",
            "- Gap",
            "- Why it matters",
            "- Evidence from context",
            "- Suggested developer action",
            "",
            "Context JSON:",
            json.dumps(payload, indent=2),
        ]
    )


def _parse_marked_docs(markdown: str) -> dict[str, str]:
    marker_pattern = re.compile(r"^===\s*([A-Za-z0-9_.-]+\.md)\s*===\s*$", re.MULTILINE)
    matches = list(marker_pattern.finditer(markdown))

    docs: dict[str, str] = {}
    if not matches:
        return docs

    for index, match in enumerate(matches):
        filename = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        content = markdown[start:end].strip()
        if filename in DOC_NAMES and content:
            docs[filename] = content + "\n"

    return docs


def enhance_docs_with_llm(output_root: Path, model: str = "llama-3.3-70b-versatile") -> dict[str, Path]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required for LLM enhancement.")

    knowledge_root = output_root / "knowledge_store"
    docs_root = knowledge_root / "docs"
    understanding_path = knowledge_root / "system_understanding.json"

    if not understanding_path.exists():
        raise RuntimeError(f"Missing system_understanding.json at {understanding_path}")

    system_understanding = json.loads(_read_text(understanding_path, max_chars=2_000_000) or "{}")

    docs_payload = {
        "architecture.md": _read_text(docs_root / "architecture.md"),
        "services.md": _read_text(docs_root / "services.md"),
        "apis.md": _read_text(docs_root / "apis.md"),
        "infrastructure.md": _read_text(docs_root / "infrastructure.md"),
    }

    deterministic_gaps = _deterministic_gaps(system_understanding)
    prompt = _build_prompt(system_understanding, docs_payload, deterministic_gaps)

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=0.1,
        max_tokens=7000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = str(response.choices[0].message.content or "")
    parsed = _parse_marked_docs(text)

    output_files: dict[str, Path] = {}

    for name in ["README.md", "architecture.md", "services.md", "apis.md", "infrastructure.md", "knowledge_gap.md"]:
        path = docs_root / name
        content = parsed.get(name)
        if not content:
            if name == "knowledge_gap.md":
                gap_lines = ["# Knowledge Gaps", ""]
                if deterministic_gaps:
                    for gap in deterministic_gaps:
                        gap_lines.append(f"- {gap}")
                else:
                    gap_lines.append("- No obvious deterministic knowledge gaps detected.")
                content = "\n".join(gap_lines) + "\n"
            else:
                content = docs_payload.get(name, "") or f"# {name}\n\nNot generated by LLM.\n"
        path.write_text(content, encoding="utf-8")
        output_files[name] = path

    raw_response_path = docs_root / "llm_raw_response.md"
    raw_response_path.write_text(text or "", encoding="utf-8")
    output_files["llm_raw_response.md"] = raw_response_path

    return output_files
