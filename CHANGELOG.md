# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Vector embedding generation
- Vector database integration (Chroma/Pinecone)
- LLM enhancement (Claude/GPT)
- RAG query engine
- Chat interface

## [0.1.0] - 2026-03-20

### Added
- Initial public release
- Repository scanning and analysis
- Infrastructure parsing (Docker, Kubernetes, CI/CD)
- Knowledge extraction and service detection
- Service dependency graph generation
- Graph database export (Neo4j format)
- Automatic documentation generation
  - System overview documentation
  - Service documentation
  - Deployment documentation
- Command-line interface
- Comprehensive test suite (100% passing)
- Support for multiple code languages (Python, Java, TypeScript)
- Support for infrastructure formats (Docker, YAML, JSON, OpenAPI)
- Rate limiting and optimization utilities

### Features
- Full 7-stage pipeline:
  1. Repository Scanner
  2. Parser (Docker, YAML, JSON, OpenAPI)
  3. Knowledge Extractor
  4. System Understanding
  5. Graph Builder
  6. Knowledge Store Export
  7. Documentation Generator

### Why 0.1.0?
This is the first public release representing completion of Phase 0-3 (architecture detection and documentation generation). Phase 4 (RAG and LLM integration) is planned for future releases.

---

## Release 0.0.0 Phases (Internal Development)

### Phase 0: Foundation ✅
- Core data models and domain logic
- Basic repository scanning
- Infrastructure detection

### Phase 1: Parsing ✅
- Docker file parsing
- YAML/JSON parsing
- OpenAPI spec parsing
- CI/CD configuration parsing

### Phase 2: Intelligence ✅
- Service extraction
- Database detection
- API endpoint discovery
- Dependency building

### Phase 3: Output ✅
- Graph generation
- Knowledge store export
- Markdown documentation
- Vector-seed documents

### Phase 4: RAG & LLM (In Development)
- Vector embeddings
- Vector database integration
- LLM enhancement
- Chat interface

---

## How to Update This Changelog

When making changes:
1. Add entries under `[Unreleased]` first
2. When releasing a version, create new section with date
3. Follow:
   - Added (new features)
   - Changed (changes)
   - Deprecated (soon-to-be removed)
   - Removed (gone)
   - Fixed (bugs)
   - Security (security fixes)

Example:
```markdown
## [0.2.0] - 2026-04-20

### Added
- Vector embedding support
- Chroma integration

### Fixed
- Rate limiting issue in scanner
```
