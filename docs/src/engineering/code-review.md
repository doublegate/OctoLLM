# Code Review Checklist

**Last Updated**: 2025-11-10
**Status**: Production Standard
**Applies To**: All pull requests

## Overview

This document provides a comprehensive code review checklist for OctoLLM pull requests. Both authors and reviewers should use this checklist to ensure code quality, security, and maintainability.

## Table of Contents

- [Author Checklist](#author-checklist)
- [Reviewer Checklist](#reviewer-checklist)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Security](#security)
- [Performance](#performance)
- [Documentation](#documentation)
- [Deployment](#deployment)

---

## Author Checklist

### Before Submitting PR

- [ ] **Code compiles/runs without errors**
  - Python: `python -m pytest`
  - Rust: `cargo test`

- [ ] **All tests pass**
  - Unit tests: ≥80% coverage for new code
  - Integration tests for new features
  - E2E tests for user-facing changes

- [ ] **Linting and formatting pass**
  - Python: `black . && isort . && ruff check . && mypy .`
  - Rust: `cargo fmt --check && cargo clippy -- -D warnings`

- [ ] **No sensitive information committed**
  - No API keys, passwords, or secrets
  - No PII or customer data
  - No internal URLs or endpoints

- [ ] **Branch is up to date with main**
  - `git pull origin main` and resolve conflicts

- [ ] **Commit messages follow conventions**
  - Format: `type(scope): description`
  - Types: feat, fix, docs, refactor, test, chore
  - Clear and descriptive

- [ ] **Self-reviewed the code**
  - Read through all changes
  - Removed debug code and comments
  - Checked for obvious issues

### PR Description

- [ ] **Clear title** describing the change
- [ ] **Description includes**:
  - What changed and why
  - Link to related issue
  - How to test the change
  - Screenshots for UI changes
  - Migration notes if needed
  - Breaking changes highlighted

- [ ] **Appropriate labels** applied
  - Type: feature, bug, enhancement, etc.
  - Priority: low, medium, high, critical
  - Component: orchestrator, arm, reflex, etc.

---

## Reviewer Checklist

### Initial Review

- [ ] **PR size is reasonable** (< 500 lines preferred)
- [ ] **Title and description are clear**
- [ ] **Related issue exists** and is linked
- [ ] **CI checks pass** (tests, linting, build)
- [ ] **No conflicts** with main branch

### Code Review Areas

- [ ] **Code quality** (see [Code Quality](#code-quality))
- [ ] **Testing** (see [Testing](#testing))
- [ ] **Security** (see [Security](#security))
- [ ] **Performance** (see [Performance](#performance))
- [ ] **Documentation** (see [Documentation](#documentation))
- [ ] **Deployment** (see [Deployment](#deployment))

### Final Steps

- [ ] **All comments addressed** or discussed
- [ ] **Requested changes implemented**
- [ ] **Approved by required reviewers** (minimum 1)
- [ ] **Ready to merge**

---

## Code Quality

### General

- [ ] **Code follows style guide**
  - Python: PEP 8 compliance
  - Rust: Rust style guide compliance
  - Consistent formatting

- [ ] **Names are clear and descriptive**
  - Variables: `task_id` not `tid`
  - Functions: `process_task()` not `process()`
  - Classes: `TaskRouter` not `Router`

- [ ] **Functions are focused and small**
  - Single responsibility
  - < 50 lines preferred
  - < 100 lines maximum

- [ ] **Code is DRY (Don't Repeat Yourself)**
  - No duplicated logic
  - Common functionality extracted

- [ ] **Complexity is reasonable**
  - Cyclomatic complexity < 10
  - Nesting depth < 4 levels
  - Clear and easy to understand

### Python-Specific

- [ ] **Type hints are present**
  ```python
  # Good
  async def get_task(task_id: str) -> Optional[TaskContract]:
      ...

  # Bad
  async def get_task(task_id):
      ...
  ```

- [ ] **Async/await used correctly**
  - I/O operations are async
  - `await` not missing
  - No blocking calls in async functions

- [ ] **Error handling is proper**
  - Specific exceptions caught
  - Context preserved (`raise ... from e`)
  - Errors logged with context

- [ ] **Imports are organized**
  - Standard library first
  - Third-party second
  - Local last
  - Alphabetically sorted

### Rust-Specific

- [ ] **Ownership and borrowing correct**
  - No unnecessary clones
  - Lifetimes are clear
  - No memory leaks

- [ ] **Error handling uses Result**
  - `?` operator for propagation
  - Errors are informative
  - Custom error types used

- [ ] **No `unwrap()` in production code**
  - Use `?` or `match` instead
  - Document any necessary `expect()`

- [ ] **Traits used appropriately**
  - Generic code where beneficial
  - Trait bounds are clear

---

## Testing

### Test Coverage

- [ ] **New code has tests**
  - Unit tests: 80-95% coverage
  - Integration tests for new features
  - E2E tests for user workflows

- [ ] **Existing tests still pass**
  - No tests removed without justification
  - Flaky tests fixed or documented

- [ ] **Edge cases covered**
  - Null/None values
  - Empty collections
  - Boundary conditions
  - Error conditions

### Test Quality

- [ ] **Tests are independent**
  - No test dependencies
  - Can run in any order
  - Clean state between tests

- [ ] **Tests are readable**
  - Clear test names: `test_<what>_<condition>_<expected>`
  - Arrange-Act-Assert pattern
  - Comments for complex setup

- [ ] **Mocks are appropriate**
  - External services mocked
  - Database calls mocked in unit tests
  - Mock behavior documented

### Example Test Structure

```python
class TestOrchestrator:
    """Test orchestrator functionality."""

    @pytest.fixture
    def orchestrator(self):
        """Provide orchestrator instance."""
        return Orchestrator(config=test_config)

    async def test_route_task_finds_matching_arm(
        self,
        orchestrator
    ):
        """Test routing finds arm with matching capabilities."""
        # Arrange
        task = TaskContract(description="Write Python code")

        # Act
        arm = await orchestrator.route(task)

        # Assert
        assert arm.name == "coder"
        assert "python" in arm.capabilities
```

---

## Security

### Input Validation

- [ ] **All inputs validated**
  - Pydantic models for API requests
  - SQL parameters escaped
  - File paths sanitized

- [ ] **No injection vulnerabilities**
  - SQL: Use parameterized queries
  - Command: Avoid shell execution
  - Path: Validate and sanitize paths

```python
# Good - parameterized
await db.execute(
    "SELECT * FROM tasks WHERE id = $1",
    task_id
)

# Bad - string formatting
await db.execute(
    f"SELECT * FROM tasks WHERE id = '{task_id}'"
)
```

### Authentication & Authorization

- [ ] **Authentication required** for sensitive operations
- [ ] **Authorization checked** before access
- [ ] **JWT tokens validated** properly
- [ ] **Capability tokens enforced** for arm access

### Data Protection

- [ ] **PII detection enabled** for user input
- [ ] **No secrets in code**
  - Use environment variables
  - Secrets manager integration
  - No hardcoded credentials

- [ ] **Sensitive data encrypted**
  - TLS for network traffic
  - Encryption at rest for sensitive fields
  - Secure key management

### Audit Logging

- [ ] **Security events logged**
  - Authentication failures
  - Authorization denials
  - PII detections
  - Suspicious activity

```python
logger.warning(
    "authentication.failed",
    user_id=user_id,
    ip_address=request.client.host,
    reason="invalid_token"
)
```

---

## Performance

### Database Queries

- [ ] **No N+1 queries**
  - Use joins instead of loops
  - Batch operations when possible

- [ ] **Indexes exist** for query columns
- [ ] **Query limits** applied for large results
- [ ] **Connection pooling** configured

### Async Operations

- [ ] **I/O operations are async**
- [ ] **Concurrent execution** where possible
  - `asyncio.gather()` for parallel ops
  - Avoid sequential awaits

- [ ] **Semaphores** for concurrency control
  - Limit database connections
  - Limit external API calls

### Caching

- [ ] **Expensive operations cached**
  - LLM capabilities
  - User permissions
  - Configuration

- [ ] **Cache invalidation** handled
  - Clear on updates
  - TTL set appropriately

### Resource Usage

- [ ] **Memory usage reasonable**
  - No memory leaks
  - Large datasets streamed
  - Generators for iteration

- [ ] **No blocking operations** in async code
  - CPU-intensive work in thread pool
  - File I/O is async

---

## Documentation

### Code Documentation

- [ ] **Public APIs documented**
  - Docstrings for classes
  - Docstrings for public functions
  - Parameter descriptions
  - Return value descriptions
  - Example usage

```python
async def route_task(
    task: TaskContract,
    available_arms: List[ArmCapability]
) -> Optional[ArmCapability]:
    """Route task to most suitable arm.

    Args:
        task: Task to route
        available_arms: List of available arms

    Returns:
        Best matching arm, or None if no match

    Raises:
        ValidationError: If task is invalid

    Example:
        >>> task = TaskContract(description="Write code")
        >>> arm = await route_task(task, arms)
        >>> assert arm.name == "coder"
    """
    ...
```

- [ ] **Complex logic explained**
  - Comments for non-obvious code
  - Algorithm explanations
  - Performance considerations

- [ ] **TODOs tracked**
  - TODO comments have issue numbers
  - `# TODO(#123): Implement caching`

### User Documentation

- [ ] **README updated** if needed
  - New features documented
  - Installation steps current
  - Usage examples updated

- [ ] **API docs updated** for API changes
- [ ] **Migration guide** for breaking changes
- [ ] **CHANGELOG updated** with changes

---

## Deployment

### Configuration

- [ ] **Environment variables documented**
  - Required variables listed
  - Default values specified
  - Examples provided

- [ ] **Configuration validated** at startup
- [ ] **Secrets management** configured
  - No secrets in code
  - Vault/KMS integration

### Database Changes

- [ ] **Migrations provided** for schema changes
  - Forward migration
  - Rollback migration
  - Tested on production-like data

- [ ] **Migrations are idempotent**
  - Can run multiple times safely
  - `CREATE INDEX CONCURRENTLY`

- [ ] **Data migrations** handled
  - Backfill scripts provided
  - Performance tested

### Deployment Safety

- [ ] **Backward compatible** or breaking changes documented
- [ ] **Feature flags** for risky changes
- [ ] **Rollback plan** documented
- [ ] **Monitoring alerts** configured for new code

### Docker/Kubernetes

- [ ] **Dockerfile optimized**
  - Multi-stage builds
  - Minimal base image
  - Layer caching optimized

- [ ] **Health checks defined**
  - Liveness probe
  - Readiness probe

- [ ] **Resource limits set**
  - CPU limits
  - Memory limits
  - Appropriate for workload

---

## Review Comments

### Providing Feedback

**Good Feedback**:
```
**Issue**: This query could cause N+1 problem

**Suggestion**: Consider using a join instead:
```python
tasks = await db.fetch("""
    SELECT t.*, u.name
    FROM tasks t
    JOIN users u ON t.user_id = u.id
""")
```

**Reason**: Reduces database roundtrips from N+1 to 1
```

**Poor Feedback**:
```
This is slow
```

### Comment Prefixes

- **[Nit]**: Minor style/formatting issue
- **[Question]**: Need clarification
- **[Suggestion]**: Optional improvement
- **[Issue]**: Must be addressed
- **[Critical]**: Security/correctness issue

### Example Comments

```
[Issue] Missing error handling
This function doesn't handle the case where the database connection fails.
Consider adding try/except with proper logging.

[Suggestion] Consider caching
This function is called frequently. Consider caching the result
with a TTL of 5 minutes to reduce database load.

[Question] Why async here?
This function doesn't perform any async operations. Should it be sync?

[Nit] Line too long
This line exceeds 100 characters. Consider breaking it up.
```

---

## Review Approval

### Before Approving

- [ ] All checklist items reviewed
- [ ] Comments addressed or discussed
- [ ] CI checks passing
- [ ] No security concerns
- [ ] Code meets quality standards
- [ ] Documentation sufficient
- [ ] Tests adequate

### Approval Comments

**Good Approval**:
```
LGTM! Nice improvements to the routing logic.

Minor suggestions:
- Consider adding a cache for arm capabilities
- Could extract the scoring logic to a separate function

But these can be done in a follow-up PR.
```

**Request Changes**:
```
Requesting changes for:
1. Security: Missing input validation (see inline comments)
2. Testing: No tests for error cases
3. Performance: N+1 query in get_tasks_with_users()

Please address these before merging.
```

---

## Merge Checklist

Before merging, ensure:

- [ ] ≥1 approval from reviewer
- [ ] All conversations resolved
- [ ] CI checks passing
- [ ] Branch up to date with main
- [ ] Squash commits if needed
- [ ] Merge commit message clear

---

## References

- [OctoLLM Coding Standards](./coding-standards.md)
- [OctoLLM Error Handling](./error-handling.md)
- [OctoLLM Testing Strategy](../testing/strategy.md)
- [OctoLLM Security Overview](../security/overview.md)

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly)
**Owner**: Engineering Team
