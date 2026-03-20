# KT-AI: Repository Intelligence Platform 🚀

An AI-powered platform that automatically analyzes software repositories, extracts architectural intelligence, and generates comprehensive documentation using advanced NLP and graph analysis.

## Overview

**KT-AI** transforms raw repository data into structured intelligence. It scans code, parses infrastructure files, detects service architectures, and generates documentation - all automatically. Perfect for onboarding, code comprehension, and knowledge preservation.

### Key Features

- 🔍 **Repository Scanner** - Analyzes any codebase instantly
- 🏗️ **Architecture Detection** - Automatically identifies services, APIs, and dependencies
- 📊 **Knowledge Graph** - Builds Neo4j-ready dependency graphs
- 📝 **Auto Documentation** - Generates markdown documentation from analysis
- 🧠 **LLM Integration** - Enriches analysis with Claude/GPT insights (Phase 4)
- 🔗 **RAG Ready** - Exports vector-seed documents for knowledge retrieval
- 🧪 **Test Coverage** - 100% passing integration tests

## Quick Start

### Prerequisites

- Python 3.13+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/kt-assistant.git
cd kt-assistant

# Create and activate virtual environment
python -m venv kt-assistant
.\kt-assistant\Scripts\Activate.ps1  # On Windows
source kt-assistant/bin/activate      # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# Analyze current directory
python -m kt_ai.cli . --output output

# Analyze a GitHub repository
python -m kt_ai.cli https://github.com/GoogleCloudPlatform/microservices-demo.git --output output

# Run tests
python -m pytest -v
```

### Output Files

After running the pipeline, you'll get:

```
output/
├── docs/
│   ├── system-overview.md       # Architecture and services
│   ├── services.md              # API and dependency details
│   └── deployment.md            # Docker, K8s, CI/CD configs
└── knowledge_store/
    ├── graph.json               # Neo4j import ready
    ├── vector_seed_documents.json
    └── system_understanding.json
```

## Architecture

### Pipeline Stages

1. **Repository Scanner** - Detects languages and file structure
2. **Parser** - Extracts info from Docker, YAML, JSON, OpenAPI specs
3. **Knowledge Extractor** - Infers services, databases, message queues
4. **System Understanding** - Builds service dependency graph
5. **Graph Builder** - Creates graph database structure
6. **Knowledge Store** - Exports structured intelligence
7. **Doc Generator** - Creates markdown documentation

### Project Structure

```
kt-assistant/
├── kt_ai/                    # Main package
│   ├── cli.py               # Command-line interface
│   ├── pipeline/            # Core pipeline stages
│   │   ├── scanner.py       # File scanning
│   │   ├── parser.py        # Config parsing
│   │   ├── extractor.py     # Knowledge extraction
│   │   ├── understanding.py # System understanding
│   │   ├── graph_builder.py # Graph construction
│   │   ├── store.py         # Knowledge store export
│   │   ├── doc_generator.py # Documentation generation
│   │   └── orchestrator.py  # Pipeline orchestration
│   ├── domain/              # Data models
│   ├── docs/                # Documentation generation
│   ├── optimization/        # Rate limiting & optimization
│   └── metrics/             # Metrics and monitoring
├── repo_intelligence/       # Repository analysis package
│   ├── ast/                 # Code parsing (Python, Java, TypeScript)
│   ├── core/                # Core analysis utilities
│   ├── docs/                # Documentation builders
│   ├── export/              # Export utilities
│   ├── graph/               # Graph analysis
│   ├── infra/               # Infrastructure parsing
│   ├── knowledge/           # Knowledge extraction
│   └── models/              # Data models
├── tests/                   # Integration tests
├── scripts/                 # Utility scripts
├── requirements.txt         # Python dependencies
└── pytest.ini              # Pytest configuration
```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest -v

# Run specific test file
python -m pytest tests/test_pipeline_flow.py -v

# With coverage
python -m pytest --cov=kt_ai --cov=repo_intelligence tests/
```

### Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Write code and tests
3. Run tests: `python -m pytest -v`
4. Commit: `git commit -m "feat: description"`
5. Push: `git push origin feature/my-feature`
6. Create a Pull Request

### Adding Features

- Add pipeline stage → extend `kt_ai/pipeline/`
- Add analysis capability → extend `repo_intelligence/`
- Add tests → create in `tests/`
- Update docs → edit `README.md` or create documentation

## Dependencies

- **PyYAML** - YAML parsing
- **pytest** - Testing framework
- **groq** - LLM integration (Groq API)
- **GitPython** - Git repository handling
- **networkx** - Graph algorithms
- **pydantic** - Data validation
- **openapi-schema-pydantic** - OpenAPI spec parsing
- **tree-sitter** - Code parsing for multiple languages

## Roadmap

### Phase 0-3: ✅ Completed
- Repository scanning and analysis
- Infrastructure parsing (Docker, K8s, CI/CD)
- Knowledge extraction and service detection
- Graph generation and export
- Documentation generation

### Phase 4: 🚧 In Progress
- [ ] Vector embedding generation
- [ ] Vector database integration (Chroma/Pinecone)
- [ ] LLM enhancement (Claude/GPT integration)
- [ ] RAG query engine
- [ ] Chat interface for knowledge retrieval

## Contributing

We love contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Steps

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Authors

- **You** - [Your GitHub Profile](https://github.com/yourusername)
- **Friend** - [Their GitHub Profile](https://github.com/friendusername)

## Support

- 📖 [Documentation](./README.md)
- 🐛 [Issue Tracker](https://github.com/yourusername/kt-assistant/issues)
- 💬 [Discussions](https://github.com/yourusername/kt-assistant/discussions)

## Acknowledgments

Built with Python, powered by intelligent repository analysis and LLM integration.

---

**Ready to automate your repository intelligence?** Start analyzing! 🎯
