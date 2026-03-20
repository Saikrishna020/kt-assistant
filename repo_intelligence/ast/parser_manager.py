from __future__ import annotations

from pathlib import Path

from repo_intelligence.ast.api_extractor import extract_api_endpoints
from repo_intelligence.ast.db_extractor import extract_databases
from repo_intelligence.ast.import_graph_extractor import extract_imports
from repo_intelligence.ast.service_call_extractor import extract_service_calls
from repo_intelligence.models.system_model import ASTSignal

SUPPORTED_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".go", ".java", ".cs", ".rb", ".php", ".proto"}


def _read_text(file_path: Path, max_chars: int = 150_000) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return ""


def _tree_sitter_status() -> str:
    try:
        import tree_sitter  # type: ignore  # noqa: F401

        return "available"
    except Exception:
        return "not-configured"


def analyze_code_ast(files: list[Path], repo_root: Path) -> ASTSignal:
    signal = ASTSignal()
    parser_status = _tree_sitter_status()

    for file_path in files:
        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        content = _read_text(file_path)
        if not content:
            continue

        signal.apis.extend(extract_api_endpoints(file_path, repo_root, content))
        signal.databases.extend(extract_databases(file_path, repo_root, content))
        signal.service_calls.extend(extract_service_calls(file_path, repo_root, content))
        signal.imports.extend(extract_imports(file_path, repo_root, content))

    signal.imports.append(
        {
            "source": "_meta",
            "target": f"tree_sitter:{parser_status}",
            "file": "",
            "confidence": 1.0,
            "evidence": "parser_manager",
        }
    )
    return signal
