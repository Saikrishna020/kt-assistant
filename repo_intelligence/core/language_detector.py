from __future__ import annotations

from pathlib import Path

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
    ".tf": "terraform",
    ".sql": "sql",
    ".sh": "shell",
}


def detect_languages(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for file_path in files:
        language = LANGUAGE_BY_SUFFIX.get(file_path.suffix.lower())
        if not language:
            continue
        counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))
