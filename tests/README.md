# OctoLLM Tests

This directory contains integration, E2E, performance, and security tests for the OctoLLM system.

## Structure

```
tests/
├── integration/    # Multi-service integration tests
├── e2e/            # End-to-end workflow tests
├── performance/    # Load and performance tests
└── security/       # Security and penetration tests
```

## Test Types

### Integration Tests (`integration/`)
- Multi-service scenarios
- Database interactions
- Cache behavior
- Inter-arm communication

### End-to-End Tests (`e2e/`)
- Complete user workflows
- Full system validation
- Real LLM calls (with mocking option)

### Performance Tests (`performance/`)
- Load testing with k6/Locust
- Latency benchmarks
- Resource utilization
- Scalability tests

### Security Tests (`security/`)
- SAST (Bandit, Semgrep)
- DAST (OWASP ZAP)
- PII detection validation
- Prompt injection tests
- Sandbox escape attempts

## Running Tests

```bash
# Integration tests (requires Docker Compose)
docker-compose up -d
pytest tests/integration/ -v

# E2E tests
pytest tests/e2e/ -v --slow

# Performance tests
k6 run tests/performance/k6_load_test.js

# Security tests
bandit -r services/ -ll
python tests/security/run_security_tests.py
```

## References

- [Testing Strategy](../docs/testing/strategy.md)
- [Test Guidelines](../docs/testing/guidelines.md)
- [CI/CD Integration](../docs/operations/ci-cd.md)
