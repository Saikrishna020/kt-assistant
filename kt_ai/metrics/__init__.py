from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class TokenMetrics:
    prompt_tokens: int
    cached_input_tokens: int
    candidates_tokens: int
    total_tokens: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    def summary_str(self) -> str:
        return (
            f"Prompt: {self.prompt_tokens} | "
            f"Cached: {self.cached_input_tokens} | "
            f"Candidates: {self.candidates_tokens} | "
            f"Total: {self.total_tokens}"
        )


@dataclass
class InferenceLog:
    timestamp: str
    repository: str
    model: str
    tokens: TokenMetrics
    context_size: int
    markdown_length: int
    doc_files: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "repository": self.repository,
            "model": self.model,
            "tokens": self.tokens.to_dict(),
            "context_size": self.context_size,
            "markdown_length": self.markdown_length,
            "doc_files": self.doc_files,
            "error": self.error,
        }


def save_inference_log(log_root: Path, log: InferenceLog) -> Path:
    log_root.mkdir(parents=True, exist_ok=True)

    log_file = log_root / "inference_logs.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log.to_dict()) + "\n")

    return log_file


def print_token_summary(log: InferenceLog) -> None:
    print()
    print("=" * 60)
    print("TOKEN USAGE SUMMARY")
    print("=" * 60)
    print(f"Repository: {log.repository}")
    print(f"Model: {log.model}")
    print(f"Timestamp: {log.timestamp}")
    print()
    print(f"Prompt Tokens:        {log.tokens.prompt_tokens:>10}")
    print(f"Cached Input Tokens:  {log.tokens.cached_input_tokens:>10}")
    print(f"Candidates Tokens:    {log.tokens.candidates_tokens:>10}")
    print(f"─" * 35)
    print(f"Total Tokens:         {log.tokens.total_tokens:>10}")
    print()
    print(f"Context Size (bytes): {log.context_size:>10}")
    print(f"Response Size (bytes):{log.markdown_length:>10}")
    print(f"Generated Doc Files:  {log.doc_files:>10}")
    print("=" * 60)
    print()
