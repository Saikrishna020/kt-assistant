from __future__ import annotations

import os
import stat
import shutil
from pathlib import Path

from git import Repo

from repo_intelligence.core.language_detector import detect_languages
from repo_intelligence.models.system_model import RepoMetadata

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "target",
    ".venv",
    "venv",
    "site-packages",
    "vendor",
    "__pycache__",
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
    ".woff",
    ".woff2",
    ".ttf",
}


def _is_remote_repo(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://") or source.endswith(".git")


def _clone_repo(source: str, working_dir: Path) -> Path:
    target = working_dir / Path(source.rstrip("/").split("/")[-1].replace(".git", ""))

    def _on_remove_error(func, path, exc_info):  # type: ignore[no-untyped-def]
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass

    if target.exists():
        shutil.rmtree(target, onexc=_on_remove_error)
    Repo.clone_from(source, target, depth=1)
    return target


def _is_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:1024]
    except OSError:
        return True
    return b"\x00" in sample


def scan_repository(source: str, working_dir: Path) -> tuple[RepoMetadata, list[Path], Path]:
    working_dir.mkdir(parents=True, exist_ok=True)
    if _is_remote_repo(source):
        repo_root = _clone_repo(source, working_dir)
    else:
        repo_root = Path(source).expanduser().resolve()
        if not repo_root.exists() or not repo_root.is_dir():
            raise FileNotFoundError(f"Repository path not found: {repo_root}")

    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part.lower() in EXCLUDED_DIRS for part in path.parts):
            continue
        if _is_binary(path):
            continue
        files.append(path)

    metadata = RepoMetadata(
        source=source,
        local_path=str(repo_root),
        file_count=len(files),
        languages=detect_languages(files),
    )
    return metadata, files, repo_root
