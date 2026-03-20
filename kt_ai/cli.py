from __future__ import annotations

import argparse
import os
from pathlib import Path

from repo_intelligence.pipeline.pipeline_runner import run_pipeline as run_repo_intelligence_pipeline
from repo_intelligence.docs.llm_enhancer import enhance_docs_with_llm

from kt_ai.docs.llm_doc_generator import generate_llm_docs
from kt_ai.pipeline.orchestrator import run_pipeline
from kt_ai.pipeline.orchestrator import run_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KT AI - Repository intelligence and documentation platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_cmd = subparsers.add_parser("analyze", help="Run heuristic pipeline docs and knowledge store generation")
    analyze_cmd.add_argument("repo", help="Git repository URL or local path")
    analyze_cmd.add_argument(
        "--output",
        default="kt_ai/output/generated",
        help="Output directory for docs and knowledge store",
    )

    generate_docs_cmd = subparsers.add_parser("generate-docs", help="Run analysis + LLM-powered documentation generation")
    generate_docs_cmd.add_argument("repo", help="Git repository URL or local folder path")
    generate_docs_cmd.add_argument(
        "--output",
        default="kt_ai/output/generated",
        help="Output directory for docs and knowledge store",
    )
    generate_docs_cmd.add_argument(
        "--provider",
        choices=["groq", "gemini"],
        default="groq",
        help="LLM provider to use (default: groq)",
    )
    generate_docs_cmd.add_argument(
        "--model",
        default="",
        help="Model name override for selected provider",
    )

    intelligence_cmd = subparsers.add_parser(
        "intelligence",
        help="Run deterministic repository intelligence pipeline (infra + AST + graph + docs)",
    )
    intelligence_cmd.add_argument("repo", help="Git repository URL or local folder path")
    intelligence_cmd.add_argument(
        "--output",
        default="kt_ai/output/intelligence",
        help="Output directory containing knowledge_store and docs",
    )

    intelligence_llm_cmd = subparsers.add_parser(
        "intelligence-llm-docs",
        help="Run intelligence pipeline and then enhance docs with Groq LLM + knowledge gaps",
    )
    intelligence_llm_cmd.add_argument("repo", help="Git repository URL or local folder path")
    intelligence_llm_cmd.add_argument(
        "--output",
        default="kt_ai/output/intelligence",
        help="Output directory containing knowledge_store and docs",
    )
    intelligence_llm_cmd.add_argument(
        "--model",
        default="llama-3.3-70b-versatile",
        help="Groq model name for documentation enhancement",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "generate-docs":
        os.environ["KT_AI_LLM_PROVIDER"] = args.provider
        if args.model:
            if args.provider == "groq":
                os.environ["GROQ_MODEL"] = args.model
            elif args.provider == "gemini":
                os.environ["GEMINI_MODEL"] = args.model

        output_root = Path(args.output).resolve()
        analysis = run_analysis(args.repo, output_root)
        log_root = output_root / "logs"
        docs, log_file = generate_llm_docs(output_root, analysis.knowledge, analysis.system_view, log_root=log_root)
        print("LLM documentation generation completed successfully.")
        print(f"Output root: {output_root}")
        print("Generated docs:")
        for filename, path in docs.items():
            print(f"  - {filename}: {path}")
        if log_file:
            print(f"Token log: {log_file}")
        return

    if args.command == "analyze":
        output_root = Path(args.output).resolve()
        result = run_pipeline(args.repo, output_root)
        print("Pipeline completed successfully.")
        print(f"Output root: {result.output_root}")
        print("Generated docs:")
        for key, path in result.docs.items():
            print(f"  - {key}: {path}")
        print("Knowledge store files:")
        for key, path in result.knowledge_store.items():
            print(f"  - {key}: {path}")
        return

    if args.command == "intelligence":
        output_root = Path(args.output).resolve()
        result = run_repo_intelligence_pipeline(args.repo, output_root)
        print("Repository intelligence pipeline completed successfully.")
        print(f"Output root: {result.output_root}")
        print("Knowledge store files:")
        for key, path in result.knowledge_store.items():
            print(f"  - {key}: {path}")
        return

    if args.command == "intelligence-llm-docs":
        output_root = Path(args.output).resolve()
        result = run_repo_intelligence_pipeline(args.repo, output_root)
        enhanced_docs = enhance_docs_with_llm(output_root, model=args.model)

        print("Repository intelligence + LLM documentation completed successfully.")
        print(f"Output root: {result.output_root}")
        print("Knowledge store files:")
        for key, path in result.knowledge_store.items():
            print(f"  - {key}: {path}")
        print("Enhanced docs:")
        for filename, path in enhanced_docs.items():
            print(f"  - {filename}: {path}")
        return


if __name__ == "__main__":
    main()
