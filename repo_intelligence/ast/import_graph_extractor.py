from __future__ import annotations

import ast
import re
from pathlib import Path

JS_IMPORT_PATTERN = re.compile(r"(?:import\s+.+?\s+from\s+[\"']([^\"']+)[\"']|require\([\"']([^\"']+)[\"']\))")


def extract_imports(file_path: Path, repo_root: Path, content: str) -> list[dict[str, str | float]]:
    rel = str(file_path.relative_to(repo_root))
    source = file_path.stem
    edges: list[dict[str, str | float]] = []

    if file_path.suffix.lower() == ".py":
        try:
            tree = ast.parse(content)
        except SyntaxError:
            tree = None
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        module = name.name.split(".")[0]
                        edges.append(
                            {
                                "source": source,
                                "target": module,
                                "file": rel,
                                "confidence": 0.7,
                                "evidence": f"import {name.name}",
                            }
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module.split(".")[0]
                    edges.append(
                        {
                            "source": source,
                            "target": module,
                            "file": rel,
                            "confidence": 0.7,
                            "evidence": f"from {node.module} import ...",
                        }
                    )
    elif file_path.suffix.lower() in {".js", ".ts", ".tsx"}:
        for match in JS_IMPORT_PATTERN.finditer(content):
            module = match.group(1) or match.group(2)
            if not module:
                continue
            edges.append(
                {
                    "source": source,
                    "target": module,
                    "file": rel,
                    "confidence": 0.66,
                    "evidence": match.group(0)[:120],
                }
            )

    unique: dict[str, dict[str, str | float]] = {}
    for edge in edges:
        key = f"{edge['source']}->{edge['target']}"
        if key not in unique:
            unique[key] = edge
    return list(unique.values())
