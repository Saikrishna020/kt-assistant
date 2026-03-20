# Contributing to KT-AI

First off, thank you for considering contributing to KT-AI! It's people like you that make KT-AI such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by a Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots and animated GIFs if possible**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and the expected behavior**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in the required template
* Follow the Python style guide (PEP 8)
* Include appropriate test cases
* Update documentation as needed
* End all files with a newline

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repo on GitHub, then clone your fork
git clone https://github.com/yourusername/kt-assistant.git
cd kt-assistant
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv kt-assistant
.\kt-assistant\Scripts\Activate.ps1

# macOS/Linux
python -m venv kt-assistant
source kt-assistant/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

## Development Workflow

### Writing Code

1. **Follow PEP 8** - Use `black` or similar tools for formatting
2. **Add Tests** - Every feature needs tests
3. **Add Docstrings** - Document your functions and classes
4. **Type Hints** - Add type annotations where possible

### Running Tests

```bash
# Run all tests
python -m pytest -v

# Run specific test
python -m pytest tests/test_pipeline_flow.py -v

# Run with coverage
python -m pytest --cov=kt_ai --cov=repo_intelligence tests/
```

### Commit Messages

We follow conventional commits:

* `feat:` - New feature
* `fix:` - Bug fix
* `docs:` - Documentation updates
* `test:` - Test additions or updates
* `refactor:` - Code refactoring
* `perf:` - Performance improvements
* `chore:` - Build, dependencies, tooling

Example: `git commit -m "feat: add vector embedding support"`

### Code Style

```python
# Good
def analyze_repository(repo_path: str) -> dict:
    """Analyze a repository and return intelligence data.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Dictionary containing analysis results
    """
    pass

# Bad
def analyze_repository(repo_path):
    pass
```

## Submission Process

1. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request**
   - Use a clear title
   - Reference any related issues (#123)
   - Describe what changes you made
   - Explain why you made them

3. **Review Process**
   - Maintainers will review your code
   - Address any requested changes
   - Once approved, your PR will be merged!

## Areas We Need Help With

### Phase 4: RAG Assistant (High Priority)
- Vector embedding implementation
- Vector database integration
- LLM integration (Claude/GPT)
- Chat interface development

### Documentation
- Expand API documentation
- Add more examples
- Improve inline comments
- Create video tutorials

### Testing
- Add more edge case tests
- Improve error handling tests
- Add performance benchmarks

### Features
- Support for additional languages
- Support for additional frameworks
- Performance optimizations
- Additional export formats

## Questions?

Don't hesitate to open a discussion or ask in the issues section!

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

---

Thank you for contributing to KT-AI! 🎉
