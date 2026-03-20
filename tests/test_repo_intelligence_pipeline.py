from __future__ import annotations

from pathlib import Path

from repo_intelligence.pipeline.pipeline_runner import run_pipeline


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_repo(repo_root: Path) -> None:
    _write(
        repo_root / "docker-compose.yml",
        """
services:
  user-service:
    build: ./user-service
    depends_on:
      - payment-service
  payment-service:
    build: ./payment-service
""".strip()
        + "\n",
    )
    _write(
        repo_root / "user-service" / "openapi.yaml",
        """
openapi: 3.0.0
paths:
  /users:
    get:
      responses:
        '200':
          description: ok
""".strip()
        + "\n",
    )
    _write(
        repo_root / "user-service" / "app.py",
        """
from fastapi import FastAPI
import requests
import psycopg2

app = FastAPI()

@app.get('/users')
def users():
    requests.get('http://payment-service/pay')
    psycopg2.connect('postgresql://localhost/test')
    return {"ok": True}
""".strip()
        + "\n",
    )
    _write(repo_root / "user-service" / "requirements.txt", "fastapi\npsycopg2\n")


def test_repo_intelligence_pipeline_generates_knowledge_store(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _create_repo(repo_root)

    output_root = tmp_path / "output"
    result = run_pipeline(str(repo_root), output_root)

    graph_path = result.knowledge_store["graph"]
    vector_path = result.knowledge_store["vector_seed"]
    understanding_path = result.knowledge_store["understanding"]
    docs_path = result.knowledge_store["docs"]

    assert graph_path.exists()
    assert vector_path.exists()
    assert understanding_path.exists()
    assert docs_path.exists()

    assert (docs_path / "architecture.md").exists()
    assert (docs_path / "services.md").exists()
    assert (docs_path / "apis.md").exists()
    assert (docs_path / "infrastructure.md").exists()
