# Contributing to OctoLLM

**Last Updated**: 2025-11-10

Thank you for considering contributing to OctoLLM! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Community](#community)

---

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive Behavior**:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards others

**Unacceptable Behavior**:
- Trolling, insulting comments, or personal attacks
- Public or private harassment
- Publishing others' private information
- Other conduct which could be considered inappropriate

### Enforcement

Instances of abusive behavior may be reported to conduct@octollm.com. All complaints will be reviewed and investigated promptly and fairly.

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports:
1. **Check existing issues** to avoid duplicates
2. **Verify the bug** in the latest version
3. **Gather information** about your environment

**Bug Report Template**:
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OctoLLM version:
- Python version:
- OS:
- Deployment: (Docker/Kubernetes/Local)

**Logs**
```
Paste relevant logs here
```

**Additional context**
Any other context about the problem.
```

### Suggesting Enhancements

**Enhancement Template**:
```markdown
**Is your feature request related to a problem?**
A clear description of what the problem is. Ex. I'm frustrated when [...]

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Mockups, diagrams, or examples.
```

### Your First Code Contribution

**Good First Issues**:
- Look for issues labeled `good first issue`
- These are beginner-friendly tasks
- Great for getting familiar with the codebase

**Getting Started**:
1. Fork the repository
2. Clone your fork
3. Set up development environment
4. Find an issue to work on
5. Create a branch
6. Make your changes
7. Submit a pull request

---

## Development Setup

### Prerequisites

- **Python 3.11+** with Poetry
- **Rust 1.75+** (for Reflex Layer)
- **Docker** and Docker Compose
- **Git**

### Setup Steps

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/octollm.git
cd octollm

# 2. Add upstream remote
git remote add upstream https://github.com/octollm/octollm.git

# 3. Install Python dependencies
poetry install
poetry shell

# 4. Install pre-commit hooks
pre-commit install

# 5. Start development services
docker compose up -d postgres redis qdrant

# 6. Run migrations
alembic upgrade head

# 7. Run tests to verify setup
pytest tests/unit/ -v
```

### Running the Application

```bash
# Start orchestrator
cd orchestrator
uvicorn app.main:app --reload --port 8000

# Start reflex layer
cd reflex-layer
cargo run --release

# Start specific arm
cd arms/coder
uvicorn app.main:app --reload --port 8102
```

---

## Pull Request Process

### Before Submitting

1. **Create an issue** first (unless it's a trivial fix)
2. **Discuss approach** in the issue
3. **Get approval** from maintainers
4. **Create a branch** from main
5. **Make changes** following coding standards
6. **Write tests** for new functionality
7. **Update documentation** as needed
8. **Run full test suite**
9. **Run linters** and formatters

### Submitting PR

```bash
# 1. Push your branch
git push origin feature/123-my-feature

# 2. Open PR on GitHub
# 3. Fill in PR template
# 4. Link related issue
# 5. Request review
```

### PR Template

```markdown
## Description
Brief description of what this PR does.

Closes #<issue-number>

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature breaking existing functionality)
- [ ] Documentation update

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe how you tested your changes:
1. Test step 1
2. Test step 2

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] Any dependent changes have been merged

## Screenshots (if applicable)
Add screenshots for UI changes.

## Breaking Changes
List any breaking changes and migration steps.
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by at least one maintainer
3. **Address feedback** from reviewers
4. **Get approval** from required reviewers
5. **Squash and merge** (maintainer will do this)

---

## Coding Standards

### Python

- Follow **PEP 8** with 100 character line length
- Use **type hints** for all functions
- Write **docstrings** (Google style)
- Use **async/await** for I/O operations
- Format with **Black** and **isort**
- Lint with **Ruff**
- Type check with **mypy**

**Example**:
```python
from typing import Optional

async def get_task(task_id: str) -> Optional[TaskContract]:
    """Retrieve a task by ID.

    Args:
        task_id: The unique task identifier

    Returns:
        Task contract if found, None otherwise

    Raises:
        DatabaseError: If database query fails
    """
    try:
        task = await db.fetch_one(
            "SELECT * FROM tasks WHERE id = $1",
            task_id
        )
        return TaskContract(**task) if task else None
    except asyncpg.PostgresError as e:
        logger.error("Database query failed", error=str(e))
        raise DatabaseError("Failed to retrieve task") from e
```

### Rust

- Follow **Rust style guide**
- Use **rustfmt** for formatting
- Use **clippy** for linting
- Document public APIs
- Use `Result` for error handling
- No `unwrap()` in production code

**Example**:
```rust
/// Process incoming request through reflex layer.
///
/// # Arguments
///
/// * `input` - Raw request input
/// * `config` - Reflex layer configuration
///
/// # Returns
///
/// Sanitized input ready for orchestrator
///
/// # Errors
///
/// Returns `ReflexError::PiiDetected` if PII is found.
pub async fn preprocess(
    input: &str,
    config: &Config,
) -> Result<String, ReflexError> {
    let sanitized = detect_pii(input)?;
    rate_limiter.check()?;
    Ok(sanitized)
}
```

### General

- **Keep functions small**: < 50 lines preferred
- **Single responsibility**: One function, one purpose
- **No magic numbers**: Use named constants
- **Error handling**: Always handle errors properly
- **Comments**: Explain why, not what

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation only
- **style**: Formatting (no code change)
- **refactor**: Code restructuring
- **perf**: Performance improvement
- **test**: Adding/updating tests
- **chore**: Build/tooling changes

### Examples

```bash
# Simple fix
git commit -m "fix(orchestrator): handle null task description"

# Feature with body
git commit -m "feat(arms): add weather arm for location queries

Implement new weather arm that fetches current weather and forecasts
using OpenWeatherMap API. Includes caching and rate limiting.

Closes #123"

# Breaking change
git commit -m "feat(api)!: change task priority scale from 1-5 to 1-10

BREAKING CHANGE: Task priority now uses 1-10 scale instead of 1-5.
Existing tasks will be migrated automatically. Client code needs update."
```

---

## Testing Requirements

### Coverage Targets

- **Unit tests**: 80-95% coverage for new code
- **Integration tests**: Critical paths covered
- **E2E tests**: Key workflows covered

### Running Tests

```bash
# Unit tests
pytest tests/unit/ -v --cov=octollm

# Integration tests
pytest tests/integration/ -v

# E2E tests
pytest tests/e2e/ -v

# All tests
pytest -v --cov=octollm --cov-report=html
```

### Writing Tests

```python
import pytest
from octollm.orchestrator import Orchestrator

class TestOrchestrator:
    """Test orchestrator functionality."""

    @pytest.fixture
    def orchestrator(self):
        """Provide orchestrator for tests."""
        return Orchestrator(config=test_config)

    async def test_route_simple_task(self, orchestrator):
        """Test routing for simple tasks."""
        # Arrange
        task = TaskContract(description="List files")

        # Act
        arm = await orchestrator.route(task)

        # Assert
        assert arm.name == "executor"
```

---

## Documentation

### What to Document

- **New features**: User-facing documentation
- **API changes**: Update API reference
- **Configuration**: Update environment variables
- **Breaking changes**: Update migration guide
- **Examples**: Add usage examples

### Documentation Types

**Code Documentation**:
- Docstrings for classes and functions
- Inline comments for complex logic
- README for each module

**User Documentation**:
- Feature documentation in `docs/`
- API reference updates
- Tutorial updates
- Examples and recipes

**Developer Documentation**:
- Architecture decision records (ADRs)
- Implementation guides
- Contributing guidelines

---

## Community

### Getting Help

- **Documentation**: https://docs.octollm.com
- **GitHub Discussions**: Ask questions, share ideas
- **Discord**: https://discord.gg/octollm
- **Stack Overflow**: Tag with `octollm`

### Staying Updated

- **Watch repository** for updates
- **Join Discord** for announcements
- **Follow** on Twitter: @octollm
- **Subscribe** to release notes

### Recognition

Contributors are recognized in:
- **CONTRIBUTORS.md**: All contributors listed
- **Release notes**: Significant contributions highlighted
- **Hall of Fame**: Top contributors featured

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing:
- **Check documentation**: https://docs.octollm.com
- **Ask in discussions**: https://github.com/octollm/octollm/discussions
- **Join Discord**: https://discord.gg/octollm
- **Email**: contributors@octollm.com

---

**Thank you for contributing to OctoLLM!**

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly)
**Owner**: Community Team
