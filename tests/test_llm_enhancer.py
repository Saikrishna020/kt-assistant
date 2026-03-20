from __future__ import annotations

import json
from pathlib import Path

from repo_intelligence.docs.llm_enhancer import _deterministic_gaps, _parse_marked_docs


def test_deterministic_gaps_detects_missing_runtime_and_dependencies() -> None:
    payload = {
        "services": [
            {"name": "svc-a", "runtime": "unknown", "apis": [], "component_type": "unknown_artifact"},
            {"name": "svc-b", "runtime": "python", "apis": []},
        ],
        "dependencies": [],
        "apis": [],
        "observations": {"cicd": []},
    }

    gaps = _deterministic_gaps(payload)
    joined = "\n".join(gaps)

    assert "Runtime unknown" in joined
    assert "No service dependency edges" in joined
    assert "No APIs detected" in joined
    assert "No CI/CD pipelines" in joined
    assert "Unknown artifact classification" in joined


def test_parse_marked_docs_extracts_expected_files() -> None:
    markdown = "\n".join(
        [
            "=== README.md ===",
            "# Readme",
            "=== services.md ===",
            "# Services",
            "=== knowledge_gap.md ===",
            "# Gaps",
        ]
    )

    parsed = _parse_marked_docs(markdown)

    assert "README.md" in parsed
    assert "services.md" in parsed
    assert "knowledge_gap.md" in parsed
