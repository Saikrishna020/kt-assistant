from __future__ import annotations

import json
from pathlib import Path

from kt_ai.docs.llm_doc_generator import (
    GeminiClient,
    GroqClient,
    LLMClient,
    build_llm_context,
    build_prompt,
    generate_documentation,
    generate_llm_docs,
    save_docs,
)
from kt_ai.metrics import TokenMetrics
from kt_ai.pipeline.extractor import extract_knowledge
from kt_ai.pipeline.parser import parse_repository
from kt_ai.pipeline.scanner import scan_repository
from kt_ai.pipeline.understanding import build_system_understanding


class FakeLLMClient(LLMClient):
    def __init__(self, response_text: str, token_metrics: TokenMetrics | None = None) -> None:
        self.response_text = response_text
        self.token_metrics = token_metrics or TokenMetrics(
            prompt_tokens=100,
            cached_input_tokens=0,
            candidates_tokens=50,
            total_tokens=150,
        )
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> tuple[str, TokenMetrics | None]:
        self.prompts.append(prompt)
        return self.response_text, self.token_metrics


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_repo(repo_root: Path) -> None:
    _write(
        repo_root / "order" / "package.json",
        json.dumps(
            {
                "name": "order",
                "dependencies": {"redis": "^4.0.0", "kafka-node": "^5.0.0"},
                "scripts": {"start": "node app.js"},
            }
        ),
    )
    _write(repo_root / "order" / "Dockerfile", "FROM node:20\nEXPOSE 8080\n")
    _write(repo_root / "order" / "openapi.yaml", "openapi: 3.0.0\npaths:\n  /orders:\n    get: {}\n")
    _write(
        repo_root / "order" / "k8s.yaml",
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: order\n",
    )
    _write(repo_root / ".github" / "workflows" / "ci.yaml", "name: ci\n")


def _build_knowledge(tmp_path: Path):
    repo_root = tmp_path / "repo"
    _create_repo(repo_root)
    repo = scan_repository(str(repo_root), tmp_path / "workspace")
    artifacts = parse_repository(repo)
    knowledge = extract_knowledge(repo, artifacts)
    system_view = build_system_understanding(knowledge)
    return knowledge, system_view


def test_build_llm_context_contains_expected_sections(tmp_path: Path) -> None:
    knowledge, system_view = _build_knowledge(tmp_path)

    context = build_llm_context(knowledge, system_view)

    assert "repository" in context
    assert "languages" in context
    assert "services" in context
    assert "artifacts" in context
    assert "service_dependencies" in context
    assert "databases" in context
    assert "queues" in context
    assert "ci_cd" in context


def test_build_prompt_has_strict_instructions(tmp_path: Path) -> None:
    knowledge, system_view = _build_knowledge(tmp_path)
    context = build_llm_context(knowledge, system_view)

    prompt = build_prompt(context)

    assert "Senior Software Architect" in prompt
    assert "Technical Writer" in prompt
    assert "Platform Engineer" in prompt
    assert "Do not hallucinate" in prompt
    assert "=== README.md ===" in prompt
    assert "=== architecture.md ===" in prompt


def test_save_docs_parses_marked_files_and_persists(tmp_path: Path) -> None:
    llm_markdown = "\n".join(
        [
            "=== README.md ===",
            "# Repo",
            "",
            "=== architecture.md ===",
            "# Architecture",
            "",
            "=== services.md ===",
            "# Services",
            "",
            "=== deployment.md ===",
            "# Deployment",
            "",
            "=== development.md ===",
            "# Development",
        ]
    )

    saved = save_docs(tmp_path, llm_markdown)

    assert (tmp_path / "docs" / "README.md").exists()
    assert (tmp_path / "docs" / "architecture.md").exists()
    assert (tmp_path / "docs" / "services.md").exists()
    assert (tmp_path / "docs" / "deployment.md").exists()
    assert (tmp_path / "docs" / "development.md").exists()
    assert len(saved) == 5


def test_generate_llm_docs_end_to_end_with_fake_client(tmp_path: Path) -> None:
    knowledge, system_view = _build_knowledge(tmp_path)

    response = "\n".join(
        [
            "=== README.md ===",
            "# Overview",
            "",
            "=== architecture.md ===",
            "# Architecture",
            "```mermaid",
            "graph TD",
            "order --> redis",
            "```",
            "",
            "=== services.md ===",
            "# Services",
            "",
            "=== deployment.md ===",
            "# Deployment",
            "",
            "=== development.md ===",
            "# Development",
        ]
    )
    client = FakeLLMClient(response)

    saved, log_file = generate_llm_docs(tmp_path / "generated", knowledge, system_view, llm_client=client)

    assert len(client.prompts) == 1
    assert "Context JSON" in client.prompts[0]
    assert (tmp_path / "generated" / "docs" / "README.md").exists()
    assert saved["README.md"].exists()


def test_generate_documentation_calls_client_once(tmp_path: Path) -> None:
    knowledge, system_view = _build_knowledge(tmp_path)
    context = build_llm_context(knowledge, system_view)

    client = FakeLLMClient("=== README.md ===\n# OK")
    markdown, token_metrics = generate_documentation(context, client)

    assert markdown.startswith("=== README.md ===")
    assert len(client.prompts) == 1
    assert token_metrics is not None
    assert token_metrics.total_tokens == 150


def test_generate_llm_docs_with_token_logging(tmp_path: Path) -> None:
    knowledge, system_view = _build_knowledge(tmp_path)

    response = "\n".join(
        [
            "=== README.md ===",
            "# Overview",
            "",
            "=== architecture.md ===",
            "# Architecture",
        ]
    )
    token_metrics = TokenMetrics(
        prompt_tokens=500, cached_input_tokens=100, candidates_tokens=250, total_tokens=850
    )
    client = FakeLLMClient(response, token_metrics=token_metrics)

    saved, log_file = generate_llm_docs(
        tmp_path / "generated",
        knowledge,
        system_view,
        llm_client=client,
        log_root=tmp_path / "logs",
    )

    assert log_file is not None
    assert log_file.exists()
    assert (tmp_path / "logs" / "inference_logs.jsonl").exists()

    log_content = log_file.read_text(encoding="utf-8")
    assert "850" in log_content  # total tokens


def test_generate_llm_docs_defaults_to_groq_provider(tmp_path: Path, monkeypatch) -> None:
    knowledge, system_view = _build_knowledge(tmp_path)

    monkeypatch.setenv("KT_AI_LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    def _fake_groq_generate(self, prompt: str) -> tuple[str, TokenMetrics | None]:
        return "=== README.md ===\n# Groq OK", TokenMetrics(1, 0, 1, 2)

    monkeypatch.setattr(GroqClient, "generate", _fake_groq_generate)

    saved, _ = generate_llm_docs(tmp_path / "generated", knowledge, system_view)

    assert saved["README.md"].exists()
    assert "Groq OK" in saved["README.md"].read_text(encoding="utf-8")


def test_generate_llm_docs_supports_gemini_provider(tmp_path: Path, monkeypatch) -> None:
    knowledge, system_view = _build_knowledge(tmp_path)

    monkeypatch.setenv("KT_AI_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    def _fake_gemini_generate(self, prompt: str) -> tuple[str, TokenMetrics | None]:
        return "=== README.md ===\n# Gemini OK", TokenMetrics(1, 0, 1, 2)

    monkeypatch.setattr(GeminiClient, "generate", _fake_gemini_generate)

    saved, _ = generate_llm_docs(tmp_path / "generated", knowledge, system_view)

    assert saved["README.md"].exists()
    assert "Gemini OK" in saved["README.md"].read_text(encoding="utf-8")
