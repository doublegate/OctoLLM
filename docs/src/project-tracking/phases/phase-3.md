# Phase 3: Operations & Deployment

**Status**: Not Started
**Duration**: 4-6 weeks (parallel with Phase 4)
**Team Size**: 2-3 SREs
**Prerequisites**: Phase 2 complete
**Start Date**: TBD
**Target Completion**: TBD

---

## Overview

Phase 3 establishes production-grade operations infrastructure including comprehensive monitoring, alert

ing, troubleshooting playbooks, disaster recovery, and performance optimization. This phase ensures the OctoLLM system can be reliably operated in production.

**Key Deliverables**:
1. Monitoring Stack - Prometheus, Grafana, Loki, Jaeger
2. Alerting System - Alertmanager with PagerDuty integration
3. Troubleshooting Playbooks - 10+ comprehensive runbooks
4. Disaster Recovery - Automated backups and restoration procedures
5. Performance Tuning - Database, application, and cache optimization

**Success Criteria**:
- ✅ Monitoring stack operational with 30-day retention
- ✅ Alerts firing correctly for simulated incidents
- ✅ Backups tested and verified (RTO <4 hours, RPO <1 hour)
- ✅ Load tests passing at scale (1,000 concurrent tasks)
- ✅ Runbooks tested by on-call team

**Reference**: `docs/doc_phases/PHASE-3-COMPLETE-SPECIFICATIONS.md` (12,600+ lines)

---

## Sprint 3.1: Monitoring Stack [Week 17-18]

**Duration**: 2 weeks
**Team**: 1-2 SREs
**Prerequisites**: Kubernetes deployment complete
**Priority**: CRITICAL

### Sprint Goals

- Deploy complete observability stack (Prometheus, Grafana, Loki, Jaeger)
- Instrument all services with metrics
- Create pre-built Grafana dashboards (5+ dashboards)
- Achieve 100% service coverage for metrics collection
- 30-day metrics retention

### Tasks

#### Prometheus Deployment (8 hours)

- [ ] **Deploy Prometheus Operator** (3 hours)
  - Install Prometheus Operator via Helm
  - Configure ServiceMonitors for auto-discovery
  - Set up 30-day retention
  - Code example:
    ```yaml
    # k8s/monitoring/prometheus.yaml
    apiVersion: monitoring.coreos.com/v1
    kind: Prometheus
    metadata:
      name: octollm-prometheus
      namespace: octollm
    spec:
      replicas: 2
      retention: 30d
      storage:
        volumeClaimTemplate:
          spec:
            accessModes: ["ReadWriteOnce"]
            resources:
              requests:
                storage: 100Gi
      serviceMonitorSelector:
        matchLabels:
          app: octollm
      resources:
        requests:
          memory: "4Gi"
          cpu: "2000m"
        limits:
          memory: "8Gi"
          cpu: "4000m"
    ```
  - Files to create: `k8s/monitoring/prometheus.yaml`
  - Reference: `docs/operations/monitoring-alerting.md`

- [ ] **Create ServiceMonitors** (3 hours)
  - ServiceMonitor for Orchestrator
  - ServiceMonitor for Reflex Layer
  - ServiceMonitor for all Arms
  - ServiceMonitor for databases
  - Code example:
    ```yaml
    # k8s/monitoring/servicemonitor-orchestrator.yaml
    apiVersion: monitoring.coreos.com/v1
    kind: ServiceMonitor
    metadata:
      name: orchestrator
      namespace: octollm
      labels:
        app: octollm
    spec:
      selector:
        matchLabels:
          app: orchestrator
      endpoints:
      - port: metrics
        path: /metrics
        interval: 30s
        scrapeTimeout: 10s
    ```
  - Files to create: `k8s/monitoring/servicemonitor-*.yaml`

- [ ] **Configure Prometheus Rules** (2 hours)
  - Recording rules for aggregations
  - Alert rules (covered in Sprint 3.2)
  - Files to create: `k8s/monitoring/prometheus-rules.yaml`

#### Application Metrics Implementation (10 hours)

- [ ] **Instrument Orchestrator** (3 hours)
  - HTTP request metrics (rate, duration, errors by endpoint)
  - Task lifecycle metrics (created, completed, failed, duration)
  - LLM API metrics (calls, tokens, cost, duration, errors)
  - Code example:
    ```python
    # orchestrator/metrics.py
    from prometheus_client import Counter, Histogram, Gauge, generate_latest
    from fastapi import FastAPI, Response

    # HTTP metrics
    http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )

    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration',
        ['method', 'endpoint']
    )

    # Task metrics
    tasks_created_total = Counter(
        'tasks_created_total',
        'Total tasks created',
        ['task_type']
    )

    tasks_completed_total = Counter(
        'tasks_completed_total',
        'Total tasks completed',
        ['task_type', 'status']
    )

    task_duration_seconds = Histogram(
        'task_duration_seconds',
        'Task execution duration',
        ['task_type'],
        buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300]
    )

    tasks_in_progress = Gauge(
        'tasks_in_progress',
        'Tasks currently in progress',
        ['task_type']
    )

    # LLM metrics
    llm_api_calls_total = Counter(
        'llm_api_calls_total',
        'Total LLM API calls',
        ['provider', 'model']
    )

    llm_api_tokens_total = Counter(
        'llm_api_tokens_total',
        'Total LLM API tokens used',
        ['provider', 'model', 'type']  # type: prompt, completion
    )

    llm_api_cost_total = Counter(
        'llm_api_cost_total',
        'Total LLM API cost in USD',
        ['provider', 'model']
    )

    llm_api_duration_seconds = Histogram(
        'llm_api_duration_seconds',
        'LLM API call duration',
        ['provider', 'model']
    )

    # Metrics endpoint
    @app.get("/metrics")
    async def metrics():
        return Response(content=generate_latest(), media_type="text/plain")
    ```
  - Files to create: `orchestrator/metrics.py`

- [ ] **Instrument Arms** (4 hours)
  - Arm-specific metrics (requests, availability, latency, success rate)
  - Memory metrics (operations, query duration, cache hits/misses)
  - Similar pattern to Orchestrator for each arm
  - Files to create: `arms/{arm_name}/metrics.py`

- [ ] **Instrument Reflex Layer** (2 hours)
  - PII detection metrics (detections, types, redactions)
  - Injection detection metrics (attempts blocked)
  - Cache metrics (hits, misses, hit rate, evictions)
  - Code example (Rust):
    ```rust
    // reflex-layer/src/metrics.rs
    use prometheus::{IntCounter, IntCounterVec, HistogramVec, Registry};
    use lazy_static::lazy_static;

    lazy_static! {
        pub static ref HTTP_REQUESTS_TOTAL: IntCounterVec = IntCounterVec::new(
            prometheus::opts!("http_requests_total", "Total HTTP requests"),
            &["method", "endpoint", "status"]
        ).unwrap();

        pub static ref PII_DETECTIONS_TOTAL: IntCounterVec = IntCounterVec::new(
            prometheus::opts!("pii_detections_total", "Total PII detections"),
            &["pii_type"]
        ).unwrap();

        pub static ref INJECTION_BLOCKS_TOTAL: IntCounter = IntCounter::new(
            "injection_blocks_total",
            "Total prompt injection attempts blocked"
        ).unwrap();

        pub static ref CACHE_HITS_TOTAL: IntCounter = IntCounter::new(
            "cache_hits_total",
            "Total cache hits"
        ).unwrap();

        pub static ref CACHE_MISSES_TOTAL: IntCounter = IntCounter::new(
            "cache_misses_total",
            "Total cache misses"
        ).unwrap();
    }

    pub fn register_metrics(registry: &Registry) {
        registry.register(Box::new(HTTP_REQUESTS_TOTAL.clone())).unwrap();
        registry.register(Box::new(PII_DETECTIONS_TOTAL.clone())).unwrap();
        registry.register(Box::new(INJECTION_BLOCKS_TOTAL.clone())).unwrap();
        registry.register(Box::new(CACHE_HITS_TOTAL.clone())).unwrap();
        registry.register(Box::new(CACHE_MISSES_TOTAL.clone())).unwrap();
    }
    ```
  - Files to create: `reflex-layer/src/metrics.rs`

- [ ] **Database Metrics** (1 hour)
  - PostgreSQL exporter configuration
  - Redis exporter configuration
  - Qdrant built-in metrics
  - Files to create: `k8s/monitoring/postgres-exporter.yaml`, `k8s/monitoring/redis-exporter.yaml`

#### Grafana Setup (6 hours)

- [ ] **Deploy Grafana** (2 hours)
  - Helm installation
  - Configure Prometheus datasource
  - Set up authentication (OIDC or basic auth)
  - Persistent storage for dashboards
  - Files to create: `k8s/monitoring/grafana.yaml`

- [ ] **Create System Overview Dashboard** (1 hour)
  - Task success rate (gauge + graph)
  - Overall latency (P50, P95, P99)
  - Cost per day/week/month
  - Error rate by service
  - JSON export in repository
  - Files to create: `k8s/monitoring/dashboards/system-overview.json`

- [ ] **Create Service Health Dashboard** (1 hour)
  - Availability per service (uptime %)
  - Error rate by endpoint
  - Latency distributions
  - Request volume
  - Files to create: `k8s/monitoring/dashboards/service-health.json`

- [ ] **Create Resource Usage Dashboard** (1 hour)
  - CPU usage by pod
  - Memory usage by pod
  - Disk I/O
  - Network traffic
  - Files to create: `k8s/monitoring/dashboards/resource-usage.json`

- [ ] **Create LLM Cost Tracking Dashboard** (1 hour)
  - Tokens used per day/week/month
  - Cost breakdown by model
  - Cost per task
  - Budget tracking with alerts
  - Files to create: `k8s/monitoring/dashboards/llm-costs.json`

### Success Criteria

- [ ] Prometheus scraping all services (100% coverage)
- [ ] Grafana dashboards display real-time data
- [ ] Metrics retention 30 days
- [ ] All critical metrics instrumented
- [ ] Dashboard JSON exported to repository

### Estimated Effort

- Development: 24 hours
- Testing: 4 hours
- Documentation: 2 hours
- **Total**: 30 hours (~2 weeks for 1 SRE)

---

## Sprint 3.2: Alerting and Runbooks [Week 18-19]

**Duration**: 1 week
**Team**: 1-2 SREs
**Prerequisites**: Monitoring stack deployed
**Priority**: CRITICAL

### Sprint Goals

- Deploy Alertmanager with notification routing
- Define 20+ alert rules across all services
- Create 10+ comprehensive runbooks
- Set up on-call rotation and escalation
- Test alerts with simulated incidents

### Tasks

#### Alertmanager Setup (6 hours)

- [ ] **Deploy Alertmanager** (2 hours)
  - Helm installation
  - Configure notification channels (Slack, PagerDuty, email)
  - Set up alert grouping and routing
  - Code example:
    ```yaml
    # k8s/monitoring/alertmanager-config.yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: alertmanager-config
      namespace: octollm
    data:
      alertmanager.yml: |
        global:
          resolve_timeout: 5m
          slack_api_url: '{{ .SlackWebhookURL }}'

        route:
          group_by: ['alertname', 'cluster', 'service']
          group_wait: 10s
          group_interval: 10s
          repeat_interval: 12h
          receiver: 'default'
          routes:
          - match:
              severity: critical
            receiver: 'pagerduty'
            continue: true
          - match:
              severity: warning
            receiver: 'slack'

        receivers:
        - name: 'default'
          email_configs:
          - to: 'team@octollm.io'
            from: 'alerts@octollm.io'
            smarthost: 'smtp.gmail.com:587'

        - name: 'slack'
          slack_configs:
          - channel: '#octollm-alerts'
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

        - name: 'pagerduty'
          pagerduty_configs:
          - service_key: '{{ .PagerDutyServiceKey }}'
            description: '{{ .GroupLabels.alertname }}'
    ```
  - Files to create: `k8s/monitoring/alertmanager-config.yaml`

- [ ] **Configure Notification Channels** (2 hours)
  - Slack webhook integration
  - PagerDuty service key setup
  - Email SMTP configuration
  - Test notifications

- [ ] **Set Up Alert Routing** (2 hours)
  - Route critical alerts to PagerDuty
  - Route warnings to Slack
  - Route info to email
  - Configure inhibit rules (suppress redundant alerts)

#### Alert Rules Definition (8 hours)

- [ ] **Service Availability Alerts** (2 hours)
  - Service down (>1 minute)
  - High error rate (>5% for 5 minutes)
  - Low uptime (<95% over 24 hours)
  - Code example:
    ```yaml
    # k8s/monitoring/alert-rules/service-availability.yaml
    apiVersion: monitoring.coreos.com/v1
    kind: PrometheusRule
    metadata:
      name: service-availability
      namespace: octollm
    spec:
      groups:
      - name: service_availability
        interval: 30s
        rules:
        - alert: ServiceDown
          expr: up{job=~"orchestrator|reflex-layer|.*-arm"} == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "Service {{ $labels.job }} is down"
            description: "{{ $labels.job }} has been down for more than 1 minute"

        - alert: HighErrorRate
          expr: |
            (
              sum(rate(http_requests_total{status=~"5.."}[5m])) by (job)
              /
              sum(rate(http_requests_total[5m])) by (job)
            ) > 0.05
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "High error rate on {{ $labels.job }}"
            description: "{{ $labels.job }} has >5% error rate for 5 minutes"

        - alert: LowUptime
          expr: avg_over_time(up{job=~"orchestrator|reflex-layer|.*-arm"}[24h]) < 0.95
          labels:
            severity: warning
          annotations:
            summary: "Low uptime for {{ $labels.job }}"
            description: "{{ $labels.job }} uptime <95% over last 24 hours"
    ```
  - Files to create: `k8s/monitoring/alert-rules/service-availability.yaml`

- [ ] **Performance Alerts** (2 hours)
  - High latency (P95 >30s for tasks)
  - Low throughput (<10 tasks/minute)
  - Task timeout rate (>10%)
  - Files to create: `k8s/monitoring/alert-rules/performance.yaml`

- [ ] **Resource Alerts** (2 hours)
  - High CPU (>80% for 10 minutes)
  - High memory (>90% for 5 minutes)
  - Disk space low (<15% free)
  - Files to create: `k8s/monitoring/alert-rules/resources.yaml`

- [ ] **Database Alerts** (1 hour)
  - Connection pool exhausted
  - Replication lag (>60s)
  - Slow queries (>10s)
  - Files to create: `k8s/monitoring/alert-rules/database.yaml`

- [ ] **LLM Cost Alerts** (1 hour)
  - Daily spend >$500
  - Monthly spend >$10,000
  - Unexpected spike (>2x average)
  - Files to create: `k8s/monitoring/alert-rules/llm-costs.yaml`

#### Runbook Creation (10 hours)

- [ ] **Create Runbook Template** (1 hour)
  - Standard structure (Symptoms, Diagnosis, Resolution, Prevention)
  - Code examples for common commands
  - Files to create: `docs/operations/runbooks/TEMPLATE.md`

- [ ] **Service Unavailable Runbook** (1 hour)
  - Check pod status
  - Review recent deployments
  - Inspect logs
  - Restart procedures
  - Files to create: `docs/operations/runbooks/service-unavailable.md`

- [ ] **High Latency Runbook** (1 hour)
  - Identify bottleneck (database, LLM API, network)
  - Profile slow requests
  - Check resource utilization
  - Optimization steps
  - Files to create: `docs/operations/runbooks/high-latency.md`

- [ ] **Database Connection Issues Runbook** (1 hour)
  - Check connection pool status
  - Verify credentials
  - Test network connectivity
  - Restart database clients
  - Files to create: `docs/operations/runbooks/database-connection.md`

- [ ] **Memory Leak Runbook** (1 hour)
  - Identify leaking service
  - Profile memory usage
  - Restart procedures
  - Long-term fixes
  - Files to create: `docs/operations/runbooks/memory-leak.md`

- [ ] **Task Routing Failure Runbook** (1 hour)
  - Check arm registration
  - Verify capability matching
  - Review routing logs
  - Manual task reassignment
  - Files to create: `docs/operations/runbooks/task-routing-failure.md`

- [ ] **LLM API Failure Runbook** (1 hour)
  - Check API rate limits
  - Verify API keys
  - Test fallback providers
  - Manual retry procedures
  - Files to create: `docs/operations/runbooks/llm-api-failure.md`

- [ ] **Cache Performance Runbook** (1 hour)
  - Check Redis health
  - Analyze eviction rate
  - Warm cache
  - Tune TTL settings
  - Files to create: `docs/operations/runbooks/cache-performance.md`

- [ ] **Resource Exhaustion Runbook** (1 hour)
  - Identify resource-hungry pods
  - Scale up resources
  - Clean up old data
  - Implement limits
  - Files to create: `docs/operations/runbooks/resource-exhaustion.md`

- [ ] **Security Violation Runbook** (1 hour)
  - Review security logs
  - Block malicious IPs
  - Revoke compromised tokens
  - Incident response
  - Files to create: `docs/operations/runbooks/security-violation.md`

#### On-Call Setup (4 hours)

- [ ] **Define On-Call Rotation** (2 hours)
  - Primary, secondary, escalation roles
  - Rotation schedule (weekly)
  - Handoff procedures
  - PagerDuty configuration

- [ ] **Document Escalation Procedures** (1 hour)
  - Level 1: On-call Engineer (15 minutes)
  - Level 2: Senior Engineer (30 minutes)
  - Level 3: Engineering Lead (60 minutes)
  - Files to create: `docs/operations/on-call-guide.md`

- [ ] **Create On-Call Runbook Index** (1 hour)
  - Categorized runbook list
  - Quick reference commands
  - Common issue resolutions
  - Files to create: `docs/operations/on-call-quick-reference.md`

### Success Criteria

- [ ] Alertmanager routing alerts correctly
- [ ] All notification channels tested
- [ ] 20+ alert rules defined
- [ ] 10+ runbooks created and tested
- [ ] On-call rotation configured
- [ ] Simulated incidents resolved using runbooks

### Estimated Effort

- Development: 20 hours
- Testing: 4 hours
- Documentation: 4 hours
- **Total**: 28 hours (~1 week for 2 SREs)

---

## Sprint 3.3: Disaster Recovery [Week 19-20]

**(Abbreviated for space - full version would be 1,500-2,000 lines)**

### Sprint Goals

- Implement automated backup systems for all databases
- Create point-in-time recovery (PITR) procedures
- Deploy Velero for cluster backups
- Test disaster recovery scenarios (RTO <4 hours, RPO <1 hour)
- Document and automate restore procedures

### Key Tasks (Summary)

1. PostgreSQL Backups (WAL archiving, pg_basebackup, daily full backups)
2. Qdrant Backups (snapshot-based, 6-hour schedule)
3. Redis Persistence (RDB + AOF)
4. Velero Cluster Backups (daily full, hourly critical)
5. Backup Verification (automated testing)
6. Disaster Scenario Testing (10 scenarios)

**Reference**: `docs/operations/disaster-recovery.md` (2,779 lines)

---

## Sprint 3.4: Performance Tuning [Week 20-22]

**(Abbreviated for space - full version would be 1,200-1,500 lines)**

### Sprint Goals

- Optimize database performance (indexes, query tuning, connection pooling)
- Tune application-level performance (async ops, batching, compression)
- Implement multi-level caching strategies
- Optimize LLM API usage (batching, model selection, streaming)
- Run load tests and identify bottlenecks
- Achieve P95 latency <30s, throughput >1,000 tasks/sec

### Key Tasks (Summary)

1. Database Optimization (PostgreSQL tuning, index optimization)
2. Application Tuning (async operations, request batching)
3. Cache Optimization (L1 in-memory, L2 Redis, cache warming)
4. LLM API Optimization (batching, streaming, model selection)
5. Load Testing (k6 scripts: progressive, stress, soak tests)
6. Profiling and Bottleneck Identification

**Reference**: `docs/operations/performance-tuning.md`

---

## Sprint 3.5: Troubleshooting Automation [Week 21-22]

**(Abbreviated for space - full version would be 800-1,000 lines)**

### Sprint Goals

- Implement health check endpoints with deep health checks
- Create auto-remediation scripts for common issues
- Build diagnostic tools and debug endpoints
- Set up performance dashboards for real-time monitoring
- Automate routine troubleshooting tasks

### Key Tasks (Summary)

1. Deep Health Checks (dependency health, database connectivity)
2. Auto-Remediation Scripts (restart policies, self-healing)
3. Diagnostic Tools (debug endpoints, log aggregation)
4. Performance Dashboards (real-time metrics, SLO tracking)

---

## Phase 3 Summary

**Total Tasks**: 50+ operations tasks across 5 sprints
**Estimated Duration**: 4-6 weeks with 2-3 SREs
**Total Estimated Hours**: ~120 hours development + ~20 hours testing + ~15 hours documentation = 155 hours

**Deliverables**:
- Complete monitoring stack (Prometheus, Grafana, Alertmanager)
- Alerting with runbooks (20+ alerts, 10+ runbooks)
- Automated backups and disaster recovery (RTO <4hr, RPO <1hr)
- Performance tuning and load testing
- Troubleshooting automation

**Completion Checklist**:
- [ ] Monitoring stack operational with 30-day retention
- [ ] Alerts firing correctly for simulated incidents
- [ ] Backups tested and verified (recovery scenarios passed)
- [ ] Load tests passing at scale (1,000 concurrent tasks)
- [ ] Runbooks tested by on-call team
- [ ] Performance targets met (P95 <30s, >1,000 tasks/sec)
- [ ] Documentation complete and up-to-date

**Next Phase**: Phase 5 (Security Hardening) - After Phase 4 complete

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Maintained By**: OctoLLM Project Management Team
