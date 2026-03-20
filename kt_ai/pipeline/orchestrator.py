from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kt_ai.domain.models import KnowledgeBase
from kt_ai.pipeline.doc_generator import generate_documents
from kt_ai.pipeline.extractor import extract_knowledge
from kt_ai.pipeline.graph_builder import build_knowledge_graph
from kt_ai.pipeline.parser import parse_repository
from kt_ai.pipeline.scanner import scan_repository
from kt_ai.pipeline.store import persist_knowledge
from kt_ai.pipeline.understanding import SystemView, build_system_understanding


@dataclass
class PipelineResult:
    output_root: Path
    docs: dict[str, Path]
    knowledge_store: dict[str, Path]


@dataclass
class AnalysisResult:
    knowledge: KnowledgeBase
    system_view: SystemView


def run_analysis(repo_source: str, output_root: Path) -> AnalysisResult:
    working_root = output_root / "workspace"
    repo_info = scan_repository(repo_source, working_root)

    artifacts = parse_repository(repo_info)
    knowledge = extract_knowledge(repo_info, artifacts)
    system_view = build_system_understanding(knowledge)

    return AnalysisResult(knowledge=knowledge, system_view=system_view)


def run_pipeline(repo_source: str, output_root: Path) -> PipelineResult:
    analysis = run_analysis(repo_source, output_root)
    knowledge = analysis.knowledge
    system_view = analysis.system_view
    graph = build_knowledge_graph(knowledge, system_view)

    knowledge_store_paths = persist_knowledge(output_root, knowledge, system_view, graph)
    doc_paths = generate_documents(output_root, knowledge, system_view)

    return PipelineResult(output_root=output_root, docs=doc_paths, knowledge_store=knowledge_store_paths)
