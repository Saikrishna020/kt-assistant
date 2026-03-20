from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from groq import Groq

from kt_ai.domain.models import KnowledgeBase
from kt_ai.metrics import InferenceLog, TokenMetrics, print_token_summary, save_inference_log
from kt_ai.optimization import RateLimitConfig, RateLimiter
from kt_ai.pipeline.understanding import SystemView

MAX_LANGUAGES = 20
MAX_SERVICES = 60
MAX_SERVICE_LIST_ITEMS = 20
MAX_ARTIFACTS = 250
MAX_CI_PIPELINES = 40
MAX_DEPENDENCY_EDGES = 300

DOC_FILENAMES = {
    "README.md",
    "architecture.md",
    "services.md",
    "deployment.md",
    "development.md",
}


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> tuple[str, TokenMetrics | None]:
        """Generate text from prompt. Returns (text, token_metrics) or (text, None) if not tracked."""
        raise NotImplementedError


class GeminiClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
        rate_limit_config: RateLimitConfig | None = None,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())

    def generate(self, prompt: str) -> tuple[str, TokenMetrics | None]:
        """Generate text using Gemini API with automatic rate limiting and retries."""

        def _make_request() -> tuple[str, TokenMetrics | None]:
            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
                f"?key={self.api_key}"
            )
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ]
            }

            req = request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with request.urlopen(req, timeout=self.rate_limiter.config.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
            except error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"Gemini API HTTP error {exc.code}: {details}") from exc
            except error.URLError as exc:
                raise RuntimeError(f"Gemini API request failed: {exc.reason}") from exc

            response_json = json.loads(body)
            candidates = response_json.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini API returned no candidates.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise RuntimeError("Gemini API returned an empty response.")

            text = "".join(str(part.get("text", "")) for part in parts)
            if not text.strip():
                raise RuntimeError("Gemini API returned blank text.")

            # Extract token usage metrics
            token_metrics = None
            usage = response_json.get("usageMetadata", {})
            if usage:
                token_metrics = TokenMetrics(
                    prompt_tokens=int(usage.get("promptTokenCount", 0)),
                    cached_input_tokens=int(usage.get("cachedContentInputTokenCount", 0)),
                    candidates_tokens=int(usage.get("candidatesTokenCount", 0)),
                    total_tokens=int(usage.get("totalTokenCount", 0)),
                )

            return text, token_metrics

        # Execute with automatic rate limiting and retry logic
        return self.rate_limiter.execute_with_retries(_make_request, operation_name="Gemini API call")


class GroqClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model_name: str = "llama-3.3-70b-versatile",
        rate_limit_config: RateLimitConfig | None = None,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.client = Groq(api_key=api_key)

    def generate(self, prompt: str) -> tuple[str, TokenMetrics | None]:
        """Generate text using Groq Chat Completions API with retries."""

        def _make_request() -> tuple[str, TokenMetrics | None]:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    temperature=0.2,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )
            except Exception as exc:  # pragma: no cover - depends on remote API state
                raise RuntimeError(f"Groq API request failed: {exc}") from exc

            choices = getattr(response, "choices", None) or []
            if not choices:
                raise RuntimeError("Groq API returned no choices.")

            message = choices[0].message
            text = str(getattr(message, "content", "") or "")
            if not text.strip():
                raise RuntimeError("Groq API returned blank text.")

            usage = getattr(response, "usage", None)
            token_metrics = None
            if usage:
                token_metrics = TokenMetrics(
                    prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                    cached_input_tokens=0,
                    candidates_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
                    total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
                )

            return text, token_metrics

        return self.rate_limiter.execute_with_retries(_make_request, operation_name="Groq API call")


def _trim_list(items: list[str], max_items: int) -> list[str]:
    return [str(item) for item in items[:max_items]]


def build_llm_context(knowledge: KnowledgeBase, system_view: SystemView) -> dict[str, Any]:
    services_payload: dict[str, dict[str, Any]] = {}

    for service_name in sorted(list(knowledge.services.keys()))[:MAX_SERVICES]:
        service = knowledge.services[service_name]
        view = system_view.services.get(service_name, {})

        paths = [str(path.relative_to(knowledge.repository.local_path)) for path in service.paths[:MAX_SERVICE_LIST_ITEMS]]

        services_payload[service_name] = {
            "paths": paths,
            "runtime_hints": _trim_list(service.runtime_hints, MAX_SERVICE_LIST_ITEMS),
            "apis": _trim_list(service.apis, MAX_SERVICE_LIST_ITEMS),
            "dependencies": _trim_list(service.dependencies, MAX_SERVICE_LIST_ITEMS),
            "infrastructure": _trim_list(service.infra, MAX_SERVICE_LIST_ITEMS),
            "calls": _trim_list(list(view.get("calls", [])), MAX_SERVICE_LIST_ITEMS),
            "deployable": bool(service.deployable),
            "deployable_source": service.deployable_source,
            "confidence": f"{service.confidence:.2f}",
            "evidence_sources": _trim_list(sorted({ev.source for ev in service.evidence}), MAX_SERVICE_LIST_ITEMS),
        }

    artifacts_payload: list[dict[str, Any]] = []
    for artifact in knowledge.artifacts[:MAX_ARTIFACTS]:
        metadata: dict[str, Any] = {}
        for key, value in artifact.metadata.items():
            if isinstance(value, list):
                metadata[str(key)] = _trim_list([str(v) for v in value], 8)
            else:
                metadata[str(key)] = str(value)

        artifacts_payload.append(
            {
                "path": str(artifact.file_path.relative_to(knowledge.repository.local_path)),
                "kind": artifact.kind,
                "metadata": metadata,
            }
        )

    context: dict[str, Any] = {
        "repository": {
            "source": knowledge.repository.source,
            "name": knowledge.repository.local_path.name,
            "local_path": str(knowledge.repository.local_path),
            "file_count": len(knowledge.repository.files),
        },
        "languages": dict(list(knowledge.repository.detected_languages.items())[:MAX_LANGUAGES]),
        "services": services_payload,
        "service_dependencies": [
            {"source": source, "target": target}
            for source, target in system_view.service_dependencies[:MAX_DEPENDENCY_EDGES]
        ],
        "service_dependency_details": system_view.service_dependency_details[:MAX_DEPENDENCY_EDGES],
        "databases": sorted(list(knowledge.databases))[:MAX_SERVICE_LIST_ITEMS],
        "queues": sorted(list(knowledge.queues))[:MAX_SERVICE_LIST_ITEMS],
        "ci_cd": sorted(list(knowledge.ci_pipelines))[:MAX_CI_PIPELINES],
        "artifacts": artifacts_payload,
    }

    return context


def build_prompt(context: dict[str, Any]) -> str:
    context_json = json.dumps(context, indent=2)

    return "\n".join(
        [
            "You are simultaneously acting as a Senior Software Architect, Technical Writer, and Platform Engineer.",
            "Your job is to generate complete developer documentation for a software repository.",
            "",
            "Strict requirements:",
            "1. Use only the JSON context provided below.",
            "2. Do not hallucinate components, services, APIs, databases, queues, infra, or pipelines not in context.",
            "3. If information is missing, explicitly state that it is not detected.",
            "4. Produce clean, practical Markdown for developer onboarding.",
            "5. Explain architecture clearly and include a Mermaid diagram in architecture.md.",
            "6. Focus on how developers run, understand, and operate the system.",
            "",
            "Output format (mandatory):",
            "- Return all files in one response using exact markers:",
            "=== README.md ===",
            "=== architecture.md ===",
            "=== services.md ===",
            "=== deployment.md ===",
            "=== development.md ===",
            "",
            "Each file must be valid Markdown and include:",
            "- README.md: System Overview, Purpose, Major Components, Quick Start",
            "- architecture.md: Architecture explanation, service interactions, Mermaid diagram",
            "- services.md: One section per service with responsibility, runtime, APIs, dependencies, downstream calls",
            "- deployment.md: Docker build, Kubernetes deployment, CI/CD pipelines",
            "- development.md: Local setup, dependencies, build/run/test commands, troubleshooting notes",
            "",
            "Context JSON:",
            context_json,
        ]
    )


def generate_documentation(context: dict[str, Any], llm_client: LLMClient) -> tuple[str, TokenMetrics | None]:
    prompt = build_prompt(context)
    return llm_client.generate(prompt)


def _parse_marked_docs(markdown: str) -> dict[str, str]:
    marker_pattern = re.compile(r"^===\s*([A-Za-z0-9_.-]+\.md)\s*===\s*$", re.MULTILINE)
    matches = list(marker_pattern.finditer(markdown))

    if not matches:
        return {"README.md": markdown.strip() + "\n"}

    docs: dict[str, str] = {}
    for idx, match in enumerate(matches):
        filename = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        content = markdown[start:end].strip()
        if filename in DOC_FILENAMES and content:
            docs[filename] = content + "\n"

    return docs


def save_docs(output_root: Path, markdown: str) -> dict[str, Path]:
    docs_root = output_root / "docs"
    docs_root.mkdir(parents=True, exist_ok=True)

    parsed_docs = _parse_marked_docs(markdown)
    saved: dict[str, Path] = {}

    for filename, content in parsed_docs.items():
        path = docs_root / filename
        path.write_text(content, encoding="utf-8")
        saved[filename] = path

    # Ensure all expected docs exist, even when model misses some markers.
    for filename in DOC_FILENAMES:
        path = docs_root / filename
        if filename not in saved:
            if not path.exists():
                path.write_text(
                    "# Documentation Pending\n\n"
                    "This section was not returned by the LLM in the expected marker format.\n",
                    encoding="utf-8",
                )
            saved[filename] = path

    return saved


def generate_llm_docs(
    output_root: Path,
    knowledge: KnowledgeBase,
    system_view: SystemView,
    llm_client: LLMClient | None = None,
    log_root: Path | None = None,
) -> tuple[dict[str, Path], Path | None]:
    client = llm_client
    if client is None:
        provider = os.getenv("KT_AI_LLM_PROVIDER", "groq").strip().lower()

        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("GROQ_API_KEY is required when provider is 'groq'.")
            model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"
            client = GroqClient(api_key=api_key, model_name=model_name)
        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is required when provider is 'gemini'.")
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
            client = GeminiClient(api_key=api_key, model_name=model_name)
        else:
            raise RuntimeError("KT_AI_LLM_PROVIDER must be either 'groq' or 'gemini'.")

    context = build_llm_context(knowledge, system_view)
    context_json = json.dumps(context, indent=2)
    context_size = len(context_json.encode("utf-8"))

    markdown, token_metrics = generate_documentation(context, client)
    docs = save_docs(output_root, markdown)
    markdown_bytes = len(markdown.encode("utf-8"))

    log_file = None
    if log_root:
        timestamp = datetime.now().isoformat()
        repo_source = knowledge.repository.source
        model_name = getattr(client, "model_name", "unknown")
        doc_count = len(docs)

        token_metrics = token_metrics or TokenMetrics(prompt_tokens=0, cached_input_tokens=0, candidates_tokens=0, total_tokens=0)
        log = InferenceLog(
            timestamp=timestamp,
            repository=repo_source,
            model=model_name,
            tokens=token_metrics,
            context_size=context_size,
            markdown_length=markdown_bytes,
            doc_files=doc_count,
        )
        log_file = save_inference_log(log_root, log)
        print_token_summary(log)

    return docs, log_file
