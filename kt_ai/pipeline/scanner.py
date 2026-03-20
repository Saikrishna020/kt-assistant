from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from kt_ai.domain.models import RepositoryInfo

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".sh": "shell",
    ".tf": "terraform",
    ".sql": "sql",
}

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "target",
    "site-packages",
    "vendor",
    "__pycache__",
    "coverage",
    ".mypy_cache",
    ".pytest_cache",
    "out",
    "bin",
    "obj",
}

BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
    ".jar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
}

DOCS_SUFFIXES = {".md", ".rst", ".txt"}


def _looks_generated(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    if any(part in EXCLUDED_DIRS for part in parts):
        return True
    lower_name = path.name.lower()
    return lower_name.endswith(".min.js") or lower_name.endswith(".bundle.js")


def _is_binary_file(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:1024]
    except OSError:
        return True
    return b"\x00" in sample


def _is_remote_repo(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://") or source.endswith(".git")


def _clone_repo(source: str, working_dir: Path) -> Path:
    repo_name = Path(source.rstrip("/").split("/")[-1].replace(".git", ""))
    target = working_dir / repo_name

    if target.exists():
        shutil.rmtree(target)

    cmd = ["git", "clone", "--depth", "1", source, str(target)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {result.stderr.strip()}")

    return target


def _collect_files(root: Path) -> list[Path]:
    files: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _looks_generated(path):
            continue
        if _is_binary_file(path):
            continue
        if path.suffix.lower() in DOCS_SUFFIXES and "docs" in {part.lower() for part in path.parts}:
            continue
        files.append(path)

    return files


def _detect_languages(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for file_path in files:
        lang = LANGUAGE_BY_SUFFIX.get(file_path.suffix.lower())
        if not lang:
            continue
        counts[lang] = counts.get(lang, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def scan_repository(source: str, workspace: Path) -> RepositoryInfo:
    workspace.mkdir(parents=True, exist_ok=True)

    if _is_remote_repo(source):
        repo_path = _clone_repo(source, workspace)
    else:
        repo_path = Path(source).expanduser().resolve()
        if not repo_path.exists() or not repo_path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    files = _collect_files(repo_path)
    detected_languages = _detect_languages(files)

    return RepositoryInfo(
        source=source,
        local_path=repo_path,
        files=files,
        detected_languages=detected_languages,
    )
