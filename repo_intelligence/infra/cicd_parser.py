from __future__ import annotations

from pathlib import Path

import yaml


def parse_cicd(files: list[Path], repo_root: Path) -> list[dict[str, str | list[str]]]:
    pipelines: list[dict[str, str | list[str]]] = []
    for file_path in files:
        path_text = file_path.as_posix().lower()
        if ".github/workflows/" not in path_text and "gitlab-ci" not in file_path.name.lower() and "jenkinsfile" not in file_path.name.lower():
            continue
        jobs: list[str] = []
        if file_path.suffix.lower() in {".yaml", ".yml"}:
            try:
                doc = yaml.safe_load(file_path.read_text(encoding="utf-8", errors="ignore")) or {}
            except yaml.YAMLError:
                doc = {}
            if isinstance(doc, dict) and isinstance(doc.get("jobs"), dict):
                jobs = [str(name) for name in doc.get("jobs", {}).keys()]
        pipelines.append(
            {
                "path": str(file_path.relative_to(repo_root)),
                "name": file_path.name,
                "jobs": jobs,
            }
        )
    return pipelines
