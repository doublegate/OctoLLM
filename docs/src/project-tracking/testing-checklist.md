# OctoLLM Testing Checklist

**Last Updated**: 2025-11-10
**Reference**: `docs/testing/strategy.md` (1,683 lines)

---

## Overview

Comprehensive testing checklist for OctoLLM components. All components must pass this checklist before merging to main and before production deployment.

**Testing Pyramid**:
- **Unit Tests**: 60% of test effort (fast, isolated, >85% coverage)
- **Integration Tests**: 30% of test effort (multi-component, databases)
- **E2E Tests**: 10% of test effort (full workflows, >95% success rate)

---

## Unit Testing Requirements

### Coverage Targets
- [ ] **Python**: ≥85% statement coverage
- [ ] **Rust**: ≥80% line coverage
- [ ] **Critical paths**: 100% coverage (security, capability checks, PII detection)

### Test Categories
- [ ] **Model validation**: All Pydantic models tested
- [ ] **Business logic**: All core functions tested
- [ ] **Error handling**: All exception paths tested
- [ ] **Edge cases**: Boundary conditions, empty inputs, max sizes

### Tools & Framework
- [ ] **Python**: pytest, pytest-asyncio, pytest-cov, pytest-mock
- [ ] **Rust**: cargo test, mock crate
- [ ] **Mocking**: httpx-mock (HTTP), unittest.mock (Python), wiremock (Rust)

### Example Test Requirements
- [ ] Orchestrator planning logic (10+ test cases)
- [ ] Reflex PII detection (18+ PII types tested)
- [ ] Arm routing accuracy (8+ routing scenarios)
- [ ] Error propagation (retry logic, circuit breaker)

**Reference**: `docs/testing/strategy.md` (Unit Testing section, lines 50-300)

---

## Integration Testing Requirements

### Database Integration
- [ ] **PostgreSQL**: Connection pooling, transactions, rollback
- [ ] **Redis**: Caching, pub/sub, TTL expiration
- [ ] **Qdrant**: Vector search, collection management

### Service Boundaries
- [ ] **Orchestrator → Reflex**: Request preprocessing flow
- [ ] **Orchestrator → Arms**: Task delegation, result retrieval
- [ ] **Arm → Memory**: Query routing, data persistence
- [ ] **Arm → LLM APIs**: OpenAI/Anthropic integration

### Test Environment
- [ ] **Docker Compose**: All services running
- [ ] **Database fixtures**: Clean state per test
- [ ] **Test data**: Synthetic task dataset (100+ diverse tasks)

### Example Integration Tests
- [ ] Task submission → Planner → Executor → Judge → Response (happy path)
- [ ] Arm failure recovery (timeout, retry, fallback)
- [ ] Concurrent task handling (10+ parallel tasks)
- [ ] Memory persistence and retrieval

**Reference**: `docs/testing/strategy.md` (Integration Testing section, lines 300-500)

---

## E2E Testing Requirements

### Workflow Scenarios
- [ ] **Simple task**: Single-step execution (echo command)
- [ ] **Multi-step task**: Plan → Execute → Validate (code generation)
- [ ] **Security task**: PII detection → Redaction → Storage
- [ ] **Complex task**: Multi-arm collaboration (research → code → test)

### Success Metrics
- [ ] **Success rate**: >95% on diverse task set
- [ ] **Latency**: P99 <30s for 2-step tasks, <60s for 4+ step tasks
- [ ] **Cost**: <$0.50 per task on average
- [ ] **Error recovery**: Graceful degradation on arm failure

### Test Dataset
- [ ] 100+ diverse tasks covering:
  - Code generation (20 tasks)
  - Security reconnaissance (15 tasks)
  - Documentation generation (15 tasks)
  - Data analysis (20 tasks)
  - Multi-step workflows (30 tasks)

**Reference**: `docs/testing/strategy.md` (E2E Testing section, lines 500-650)

---

## Performance Testing Requirements

### Load Testing
- [ ] **Progressive load**: 100 → 1,000 → 5,000 concurrent users
- [ ] **Stress test**: Find breaking point (max concurrent tasks)
- [ ] **Soak test**: 24-hour stability run at 50% capacity

### Metrics to Track
- [ ] **Throughput**: Tasks completed per second
- [ ] **Latency**: P50, P95, P99 for each component
- [ ] **Error rate**: Percentage of failed tasks
- [ ] **Resource usage**: CPU, memory, disk I/O per service

### Performance Targets
| Component | P95 Latency | Throughput | Error Rate |
|-----------|-------------|------------|------------|
| Reflex Layer | <10ms | >10,000 req/sec | <0.1% |
| Orchestrator | <30s (2-step) | >100 tasks/sec | <1% |
| Planner Arm | <2s | >50 plans/sec | <2% |
| Executor Arm | <5s | >20 executions/sec | <1% |

### Tools
- [ ] **k6**: Load testing scenarios
- [ ] **Locust**: Distributed load generation
- [ ] **Prometheus**: Metrics collection
- [ ] **Grafana**: Visualization

**Reference**: `docs/testing/performance-tests.md`, `docs/operations/performance-tuning.md` (1,529 lines)

---

## Security Testing Requirements

### SAST (Static Analysis)
- [ ] **Bandit**: Python security issues (HIGH/CRITICAL only)
- [ ] **Semgrep**: Custom rules for prompt injection, capability checks
- [ ] **cargo-audit**: Rust dependency vulnerabilities
- [ ] **cargo-clippy**: Security lints

### DAST (Dynamic Analysis)
- [ ] **OWASP ZAP**: Full scan of all API endpoints
- [ ] **SQL injection**: Test with sqlmap
- [ ] **Prompt injection**: 10+ attack variants
- [ ] **Rate limiting**: Bypass attempts blocked

### Penetration Testing
- [ ] **Scenario 1**: Prompt injection → command execution (BLOCKED)
- [ ] **Scenario 2**: Capability token forgery (BLOCKED)
- [ ] **Scenario 3**: PII exfiltration (BLOCKED)
- [ ] **Scenario 4**: Resource exhaustion DoS (MITIGATED)
- [ ] **Scenario 5**: Privilege escalation (BLOCKED)

### Vulnerability Remediation
- [ ] **Critical**: 0 findings (block release)
- [ ] **High**: <5 findings (must remediate before release)
- [ ] **Medium**: <20 findings (document and plan remediation)
- [ ] **Low**: Document only

**Reference**: `docs/security/security-testing.md` (4,498 lines), `docs/security/threat-model.md` (5,106 lines)

---

## Compliance Testing Requirements

### OWASP ASVS L2
- [ ] **V1**: Architecture, design, and threat modeling
- [ ] **V2**: Authentication
- [ ] **V3**: Session management
- [ ] **V4**: Access control (capability-based)
- [ ] **V5**: Validation, sanitization, encoding
- [ ] **V8**: Data protection (PII, encryption)

### GDPR Compliance
- [ ] **Right to Access**: GET /gdpr/access functional
- [ ] **Right to Erasure**: DELETE /gdpr/erase functional
- [ ] **Right to Portability**: GET /gdpr/export (JSON/CSV/XML)
- [ ] **Consent management**: Database tracking consents

### CCPA Compliance
- [ ] **Right to Know**: GET /ccpa/data functional
- [ ] **Right to Delete**: DELETE /ccpa/delete functional
- [ ] **Opt-out**: POST /ccpa/opt-out functional

**Reference**: `docs/security/compliance.md` (3,948 lines)

---

## CI/CD Integration

### GitHub Actions Workflow
- [ ] **Lint**: Runs on all PRs (Python: ruff, black, mypy; Rust: fmt, clippy)
- [ ] **Test**: Unit + Integration tests with coverage
- [ ] **Security**: SAST, dependency scan, container scan
- [ ] **Build**: Docker images on main merge
- [ ] **Deploy**: Staging deployment on main merge

### Quality Gates
- [ ] **Code coverage**: ≥85% for Python, ≥80% for Rust
- [ ] **Security scan**: No HIGH/CRITICAL findings
- [ ] **Linting**: No errors (warnings allowed)
- [ ] **Tests**: 100% passing

**Reference**: `docs/guides/development-workflow.md`

---

## Manual Testing Checklist (Pre-Release)

### Smoke Tests
- [ ] All services start successfully (docker-compose up)
- [ ] Health endpoints return 200 OK
- [ ] Database connections established
- [ ] Can submit and retrieve tasks

### Functional Tests
- [ ] Task submission flow (API → Reflex → Orchestrator → Arm → Response)
- [ ] PII detection and redaction working
- [ ] Capability tokens required for arm access
- [ ] Error messages user-friendly

### Deployment Tests
- [ ] Kubernetes deployment successful
- [ ] HPA scales under load
- [ ] Monitoring dashboards show data
- [ ] Alerts firing correctly

---

## Test Data Management

### Synthetic Data
- [ ] **Tasks**: 100+ diverse test tasks
- [ ] **PII samples**: 1,000+ examples (all 18 types)
- [ ] **Injection patterns**: OWASP Top 10 variants
- [ ] **Code samples**: 500+ snippets (10 languages)

### Data Privacy
- [ ] **No real PII**: All test data synthetic
- [ ] **Anonymization**: Production data anonymized before testing
- [ ] **Data retention**: Test data purged after 30 days

---

## Testing Timeline

### Phase 1 (POC)
- [ ] Unit tests: 60 hours
- [ ] Integration tests: 30 hours
- [ ] E2E tests: 10 hours
- [ ] **Total**: ~100 hours (2.5 weeks for 1 engineer)

### Phase 2 (Core Capabilities)
- [ ] Unit tests: 80 hours
- [ ] Integration tests: 50 hours
- [ ] Performance tests: 20 hours
- [ ] **Total**: ~150 hours (4 weeks for 1 engineer)

### Phase 5 (Security Hardening)
- [ ] Security tests: 60 hours
- [ ] Penetration testing: 40 hours
- [ ] Compliance verification: 20 hours
- [ ] **Total**: ~120 hours (3 weeks for 2 engineers)

---

## Acceptance Criteria

Before merging to main:
- [ ] All unit tests passing
- [ ] Coverage targets met
- [ ] Integration tests passing
- [ ] No security scan failures
- [ ] Code review approved

Before production release:
- [ ] E2E tests >95% success rate
- [ ] Performance targets met
- [ ] Penetration test passed (0 critical, <5 high)
- [ ] Load test successful (handles target load)
- [ ] Manual smoke tests passed

