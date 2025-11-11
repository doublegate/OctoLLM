# Tests

Comprehensive test suite for OctoLLM covering unit, integration, end-to-end, performance, and security testing.

## Structure

```
tests/
├── integration/        # Cross-service integration tests
├── e2e/                # End-to-end workflow tests
├── performance/        # Load testing and benchmarks
└── security/           # Security testing (penetration, fuzzing)
```

## Integration Tests

Test interactions between multiple services:

```bash
# Start services
docker-compose -f infrastructure/docker-compose/docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v --maxfail=1

# Teardown
docker-compose -f infrastructure/docker-compose/docker-compose.test.yml down
```

Example tests:
- Orchestrator → Planner → Executor workflow
- Cache hit/miss scenarios
- Error propagation across services
- Timeout and retry behavior

## End-to-End Tests

Full user workflows from API request to final response:

```bash
pytest tests/e2e/ -v --slow
```

Example scenarios:
- "Write Python script to analyze CSV" (Planner → Coder → Executor → Judge)
- "Search documentation for deployment steps" (Retriever only)
- "Scan target for vulnerabilities" (Planner → Executor with nmap/nikto)

## Performance Tests

Load testing and latency benchmarks:

```bash
# Install k6
brew install k6  # or docker pull grafana/k6

# Run load tests
k6 run tests/performance/load_test.js

# Benchmarks
pytest tests/performance/ -v --benchmark-only
```

Targets:
- Orchestrator: 100 req/s sustained, <200ms P95 latency
- Reflex Layer: 10,000 req/s, <10ms P95 latency
- Arms: 50 concurrent tasks per instance

## Security Tests

Automated security testing:

```bash
# Vulnerability scanning
pytest tests/security/test_vulnerabilities.py -v

# Penetration testing (requires pentesting container)
docker-compose -f tests/security/docker-compose.pentest.yml up
pytest tests/security/test_pentest.py -v

# Fuzzing (AFL++ or libFuzzer)
cd tests/security/fuzzing
./run_fuzzer.sh reflex-layer
```

Test categories:
- SQL injection attempts
- Command injection attempts
- Prompt injection attempts
- PII leakage detection
- XSS/CSRF vulnerabilities
- Authentication/authorization bypass

## Coverage Requirements

- Python services: 85%+ line coverage
- Rust services: 80%+ line coverage
- Integration tests: Cover all critical paths
- E2E tests: Cover all user-facing workflows

## CI/CD Integration

All tests run automatically on:
- Pull requests (unit + integration)
- Merges to main (full suite including e2e)
- Nightly (performance + security)

## References

- [Testing Strategy](../docs/testing/strategy.md)
- [Security Testing](../docs/security/security-testing.md)
- [Performance Tuning](../docs/operations/performance-tuning.md)
