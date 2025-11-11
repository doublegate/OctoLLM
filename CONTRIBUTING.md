# Contributing to OctoLLM

Thank you for your interest in contributing to OctoLLM! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](./CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to conduct@octollm.org.

## Getting Started

### Prerequisites

- **Python 3.11+** with Poetry for Python services
- **Rust 1.75+** with Cargo for Rust services
- **Docker 24+** and Docker Compose for local development
- **Git** for version control
- **GitHub account** for submitting contributions

### Development Setup

1. **Fork and Clone**:
   ```bash
   # Fork repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/OctoLLM.git
   cd OctoLLM

   # Add upstream remote
   git remote add upstream https://github.com/doublegate/OctoLLM.git
   ```

2. **Start Development Environment**:
   ```bash
   # Start all services with Docker Compose
   docker-compose up -d

   # Verify services are running
   docker-compose ps
   ```

3. **Install Development Dependencies**:
   ```bash
   # Python services
   cd orchestrator
   poetry install
   poetry run pre-commit install

   # Rust services
   cd ../reflex-layer
   cargo build
   ```

See [`docs/implementation/dev-environment.md`](./docs/implementation/dev-environment.md) for detailed setup instructions.

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/amazing-feature
```

**Branch Naming Conventions**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `test/` - Test additions or improvements
- `refactor/` - Code refactoring
- `perf/` - Performance improvements
- `ci/` - CI/CD changes

### 2. Make Your Changes

#### Code Quality Standards

**Python**:
- Follow [PEP 8](https://pep8.org/) style guide
- Use **Black** for formatting: `poetry run black .`
- Use **Ruff** for linting: `poetry run ruff check .`
- Use **mypy** for type checking: `poetry run mypy .`
- Target **85%+ test coverage**

**Rust**:
- Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- Use **rustfmt** for formatting: `cargo fmt`
- Use **Clippy** for linting: `cargo clippy -- -D warnings`
- Write comprehensive tests with `cargo test`

See [`docs/engineering/coding-standards.md`](./docs/engineering/coding-standards.md) for full guidelines.

#### Writing Tests

**All changes must include tests**. We target 85%+ code coverage.

```python
# Python example (pytest)
def test_orchestrator_routes_to_correct_arm():
    """Test that orchestrator selects the appropriate arm for a task."""
    task = TaskContract(goal="Write a Python function", ...)
    arm_id = orchestrator.select_arm(task)
    assert arm_id == "coder"
```

```rust
// Rust example (cargo test)
#[test]
fn test_reflex_cache_hit() {
    let reflex = ReflexLayer::new();
    let request = Request::new("test query");

    // First request (cache miss)
    let result1 = reflex.process(request.clone());
    assert!(result1.cache_hit == false);

    // Second request (cache hit)
    let result2 = reflex.process(request.clone());
    assert!(result2.cache_hit == true);
}
```

See [`docs/implementation/testing-guide.md`](./docs/implementation/testing-guide.md) for comprehensive testing strategies.

#### Writing Documentation

- **Code Comments**: Explain *why*, not *what* (code should be self-explanatory)
- **Docstrings**: All public functions, classes, and modules must have docstrings
- **README Updates**: Update relevant README files when changing functionality
- **Documentation Files**: Update `docs/` for architectural or design changes

**Python Docstring Example**:
```python
def select_arm(self, task: TaskContract) -> str:
    """
    Select the most appropriate arm for executing a task.

    Uses relevance scoring based on arm capabilities, historical
    success rate, and current load. Falls back to default arm if
    no suitable match found.

    Args:
        task: Task contract with goal, constraints, and context

    Returns:
        String identifier of selected arm (e.g., "coder", "planner")

    Raises:
        NoArmAvailableError: If no arms are available or suitable
    """
    # Implementation...
```

### 3. Commit Your Changes

We use **Conventional Commits** for clear, structured commit messages:

```bash
# Format: <type>(<scope>): <subject>
git commit -m "feat(orchestrator): add swarm decision-making support"
git commit -m "fix(reflex): prevent race condition in cache invalidation"
git commit -m "docs(security): update threat model with new attack vectors"
git commit -m "test(arms): add integration tests for arm communication"
```

**Commit Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring without functional changes
- `perf`: Performance improvement
- `ci`: CI/CD changes
- `build`: Build system or dependency changes
- `chore`: Other changes (e.g., updating .gitignore)

**Commit Message Guidelines**:
- Use imperative mood ("add" not "added")
- Keep subject line under 72 characters
- Include body for complex changes
- Reference issues/PRs when applicable

### 4. Run Quality Checks Locally

Before pushing, ensure all checks pass:

```bash
# Python checks
poetry run black .
poetry run ruff check .
poetry run mypy .
poetry run pytest --cov=. --cov-report=term

# Rust checks
cargo fmt --check
cargo clippy -- -D warnings
cargo test
cargo doc --no-deps

# Docker build test
docker-compose build
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/amazing-feature

# Create pull request on GitHub
# Fill out the PR template with all required information
```

## Pull Request Process

### PR Requirements

Your pull request must:
- ✅ Pass all CI/CD checks (linting, tests, security scans)
- ✅ Include tests with 85%+ coverage
- ✅ Update documentation for any changes
- ✅ Follow coding standards (Black, Ruff, Clippy)
- ✅ Have a clear, descriptive title and description
- ✅ Reference related issues (e.g., "Fixes #123")
- ✅ Be signed off by at least 1 maintainer

### PR Template

When creating a PR, the template will ask for:
1. **Description**: What changes does this PR introduce?
2. **Motivation**: Why is this change needed?
3. **Testing**: How was this tested?
4. **Screenshots**: If UI changes, include before/after
5. **Checklist**: All requirements met

### Review Process

1. **Automated Checks**: CI/CD runs linting, tests, security scans
2. **Code Review**: 1+ maintainers review your code
3. **Changes Requested**: Address feedback and push updates
4. **Approval**: Maintainer approves PR
5. **Merge**: Maintainer merges to main branch

**Review Timeline**: Maintainers will review PRs within 3 business days. Complex PRs may take longer.

## Development Guidelines

### Architecture Principles

1. **Distributed Intelligence**: Each arm is autonomous and specialized
2. **Defense in Depth**: Multiple security layers (reflex, capability isolation, PII protection)
3. **Performance First**: Cache aggressively, use cheap models when possible
4. **Fail-Safe Defaults**: System continues operating even when components fail
5. **Observability Built-In**: Comprehensive logging, metrics, tracing

See [`docs/architecture/system-overview.md`](./docs/architecture/system-overview.md) for full architecture.

### Security Considerations

**All contributions must consider security**:
- Never commit secrets (API keys, passwords, certificates)
- Validate all user inputs (prevent injection attacks)
- Sanitize PII before logging or storing
- Follow principle of least privilege
- Document security implications of changes

See [`docs/security/overview.md`](./docs/security/overview.md) for security guidelines.

### Performance Considerations

**Performance is a feature**:
- Profile before optimizing (use cProfile for Python, cargo flamegraph for Rust)
- Cache expensive operations when safe
- Use async/await for I/O-bound operations
- Batch database queries when possible
- Document performance characteristics (Big-O notation)

See [`docs/engineering/performance-optimization.md`](./docs/engineering/performance-optimization.md) for optimization strategies.

## Types of Contributions

### Bug Reports

**Before submitting a bug report**:
- Check existing issues to avoid duplicates
- Verify bug exists in latest main branch
- Gather reproduction steps and environment details

**Good bug report includes**:
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python/Rust version, Docker version)
- Logs and error messages
- Screenshots if applicable

### Feature Requests

**Good feature request includes**:
- Clear use case and motivation
- Proposed solution or design
- Alternatives considered
- Potential impact on performance, security, or complexity

**Note**: Feature requests will be evaluated by maintainers for alignment with project goals.

### Documentation Improvements

Documentation contributions are highly valued:
- Fix typos, grammar, or clarity issues
- Add missing examples or tutorials
- Improve API documentation
- Translate documentation (future)

### Code Contributions

See the development workflow above for code contributions.

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests, Q&A
- **GitHub Discussions**: General discussions, ideas, help
- **Security Issues**: security@octollm.org (private)

### Getting Help

- Check [`docs/`](./docs/) for comprehensive documentation
- Search existing GitHub issues
- Ask in GitHub Discussions
- Join community calls (TBD)

## Recognition

Contributors are recognized in:
- [CONTRIBUTORS.md](./CONTRIBUTORS.md) (alphabetical list)
- Release notes for significant contributions
- GitHub contributors page

## License

By contributing to OctoLLM, you agree that your contributions will be licensed under the [Apache License 2.0](./LICENSE).

---

**Thank you for contributing to OctoLLM!** 🐙

Questions? Contact us at hello@octollm.org or open a GitHub Discussion.
