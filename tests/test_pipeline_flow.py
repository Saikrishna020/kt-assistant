from __future__ import annotations

import json
from pathlib import Path

from kt_ai.pipeline.doc_generator import generate_documents
from kt_ai.pipeline.extractor import extract_knowledge
from kt_ai.pipeline.graph_builder import build_knowledge_graph
from kt_ai.pipeline.orchestrator import run_pipeline
from kt_ai.pipeline.parser import parse_repository
from kt_ai.pipeline.scanner import scan_repository
from kt_ai.pipeline.store import persist_knowledge
from kt_ai.pipeline.understanding import build_system_understanding


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_sample_repo(repo_root: Path) -> None:
    _write(
        repo_root / "checkout" / "package.json",
        json.dumps(
            {
                "name": "checkout",
                "dependencies": {
                    "redis": "^4.0.0",
                    "kafka-node": "^5.0.0",
                },
                "scripts": {"start": "node index.js"},
            }
        ),
    )

    _write(repo_root / "checkout" / "Dockerfile", "FROM node:20\nEXPOSE 8080\n")

    _write(
        repo_root / "checkout" / "openapi.yaml",
        """
openapi: 3.0.0
paths:
  /checkout:
    get:
      responses:
        '200':
          description: ok
""".strip()
        + "\n",
    )

    _write(
        repo_root / "checkout" / "k8s.yaml",
        """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: checkout
""".strip()
        + "\n",
    )

    _write(
        repo_root / "payment" / "requirements.txt",
        "redis==5.0.1\n",
    )

    _write(repo_root / ".github" / "workflows" / "pipeline.yaml", "name: ci\n")


def test_scan_repository_detects_languages_and_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    create_sample_repo(repo_root)

    result = scan_repository(str(repo_root), tmp_path / "workspace")

    assert result.local_path == repo_root.resolve()
    assert result.detected_languages["json"] >= 1
    assert result.detected_languages["yaml"] >= 1
    assert any(p.name == "Dockerfile" for p in result.files)


def test_parse_repository_extracts_expected_artifacts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    create_sample_repo(repo_root)
    repo = scan_repository(str(repo_root), tmp_path / "workspace")

    artifacts = parse_repository(repo)
    kinds = [a.kind for a in artifacts]

    assert "dockerfile" in kinds
    assert "build_manifest" in kinds
    assert "k8s_deployment" in kinds
    assert "api_spec" in kinds
    assert "ci_cd" in kinds


def test_extract_knowledge_infers_services_dependencies_and_infra(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    create_sample_repo(repo_root)
    repo = scan_repository(str(repo_root), tmp_path / "workspace")

    artifacts = parse_repository(repo)
    knowledge = extract_knowledge(repo, artifacts)

    assert "checkout" in knowledge.services
    checkout = knowledge.services["checkout"]
    assert "node:20" in checkout.runtime_hints
    assert "/checkout" in checkout.apis
    assert "kubernetes:deployment" in checkout.infra
    assert "redis" in knowledge.databases
    assert "kafka" in knowledge.queues
    assert any("pipeline.yaml" in p for p in knowledge.ci_pipelines)


def test_understanding_graph_store_and_docs_generation(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    create_sample_repo(repo_root)
    repo = scan_repository(str(repo_root), tmp_path / "workspace")
    artifacts = parse_repository(repo)
    knowledge = extract_knowledge(repo, artifacts)

    system_view = build_system_understanding(knowledge)
    graph = build_knowledge_graph(knowledge, system_view)

    output_root = tmp_path / "output"
    store_paths = persist_knowledge(output_root, knowledge, system_view, graph)
    doc_paths = generate_documents(output_root, knowledge, system_view)

    assert any(n.node_type == "Repository" for n in graph.nodes)
    assert any(n.node_type == "Service" for n in graph.nodes)
    assert any(e.relationship == "CONTAINS" for e in graph.edges)

    for path in [*store_paths.values(), *doc_paths.values()]:
        assert path.exists()

    overview = (output_root / "docs" / "system-overview.md").read_text(encoding="utf-8")
    assert "# System Overview" in overview
    assert "Services detected" in overview


def test_orchestrator_runs_end_to_end(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    create_sample_repo(repo_root)

    output_root = tmp_path / "generated"
    result = run_pipeline(str(repo_root), output_root)

    assert result.output_root == output_root
    assert result.docs["overview"].exists()
    assert result.docs["services"].exists()
    assert result.docs["deployment"].exists()
    assert result.knowledge_store["graph"].exists()
    assert result.knowledge_store["vector_seed"].exists()
    assert result.knowledge_store["understanding"].exists()
