from __future__ import annotations

from pathlib import Path

DB_PATTERNS = {
    "postgres": ["psycopg2.connect", "postgresql://", "create_engine(\"postgres"],
    "mysql": ["mysql.connector.connect", "mysql://", "pymysql.connect"],
    "mongodb": ["mongoose.connect", "mongodb://", "MongoClient("],
    "redis": ["redis.Redis(", "redis://"],
    "neo4j": ["GraphDatabase.driver", "neo4j://"],
}


def extract_databases(file_path: Path, repo_root: Path, content: str) -> list[dict[str, str | float]]:
    rel = str(file_path.relative_to(repo_root))
    results: list[dict[str, str | float]] = []
    lowered = content.lower()

    for db_name, patterns in DB_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in lowered:
                results.append(
                    {
                        "database": db_name,
                        "file": rel,
                        "confidence": 0.8,
                        "evidence": pattern,
                    }
                )
                break
    return results
