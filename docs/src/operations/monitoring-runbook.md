# OctoLLM Monitoring Runbook

**Last Updated**: 2025-11-12
**Version**: 1.0.0
**Status**: Active
**Audience**: Site Reliability Engineers, DevOps, On-Call Engineers

## Table of Contents

1. [Overview](#overview)
2. [Quick Access](#quick-access)
3. [Grafana Usage](#grafana-usage)
4. [Prometheus Usage](#prometheus-usage)
5. [Loki Log Queries](#loki-log-queries)
6. [Jaeger Trace Analysis](#jaeger-trace-analysis)
7. [Alert Investigation](#alert-investigation)
8. [Common Troubleshooting Scenarios](#common-troubleshooting-scenarios)
9. [Escalation Procedures](#escalation-procedures)
10. [Appendix](#appendix)

---

## Overview

This runbook provides step-by-step procedures for using the OctoLLM monitoring stack to investigate issues, analyze performance, and respond to alerts.

### Monitoring Stack Components

| Component | Purpose | Access URL | Port |
|-----------|---------|------------|------|
| **Grafana** | Visualization and dashboards | https://grafana.octollm.dev | 3000 |
| **Prometheus** | Metrics collection and alerts | Port-forward only (prod) | 9090 |
| **Loki** | Log aggregation | Via Grafana datasource | 3100 |
| **Jaeger** | Distributed tracing | https://jaeger.octollm.dev | 16686 |
| **Alertmanager** | Alert routing | Port-forward only | 9093 |

### Key Metrics

| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| **P99 Latency** | < 30s | > 30s |
| **Error Rate** | < 1% | > 10% |
| **CPU Usage** | < 60% | > 80% |
| **Memory Usage** | < 70% | > 85% |
| **Cache Hit Rate** | > 60% | < 40% |

---

## Quick Access

### Access Grafana (Production)

```bash
# Via browser (recommended)
open https://grafana.octollm.dev

# Default credentials (change immediately!)
Username: admin
Password: (stored in Kubernetes secret)
```

### Access Prometheus (Port-Forward)

```bash
# Production environment
kubectl port-forward -n octollm-monitoring svc/prometheus 9090:9090

# Access at http://localhost:9090
```

### Access Jaeger UI

```bash
# Via browser
open https://jaeger.octollm.dev
```

### Access Alertmanager (Port-Forward)

```bash
kubectl port-forward -n octollm-monitoring svc/alertmanager 9093:9093

# Access at http://localhost:9093
```

---

## Grafana Usage

### Available Dashboards

OctoLLM provides 6 comprehensive dashboards:

1. **GKE Cluster Overview** (`octollm-gke-cluster`)
   - Cluster-level CPU and memory usage
   - Node count and pod status
   - Resource utilization by namespace

2. **Development Namespace** (`octollm-namespace-dev`)
   - Per-pod CPU and memory usage
   - Container restart counts
   - Request/limit utilization

3. **Staging Namespace** (`octollm-namespace-staging`)
   - Similar to dev, focused on staging environment

4. **Production Namespace** (`octollm-namespace-prod`)
   - Similar to dev, focused on production environment

5. **Service Health** (`octollm-service-health`)
   - Request rates by service
   - Error rates (5xx responses)
   - P50/P95/P99 latency
   - Database and Redis connections

6. **Logs Overview** (`octollm-logs`)
   - Log volume by service
   - Error rate visualization
   - Top 10 error messages
   - Live log stream

### How to Navigate Dashboards

1. **Open Grafana**: https://grafana.octollm.dev
2. **Navigate to Dashboards**: Click the "Dashboards" icon (four squares) in the left sidebar
3. **Select OctoLLM Folder**: All OctoLLM dashboards are in the "OctoLLM" folder
4. **Time Range**: Use the time picker (top-right) to adjust the time range
   - Default: Last 1 hour
   - Recommended for troubleshooting: Last 6 hours or Last 24 hours
5. **Refresh Rate**: Set auto-refresh (top-right dropdown)
   - Recommended: 30s for live monitoring

### Common Dashboard Tasks

#### Check Overall System Health

1. Open **GKE Cluster Overview** dashboard
2. Check the gauge panels:
   - CPU Usage < 80%? ✅ Healthy
   - Memory Usage < 85%? ✅ Healthy
   - All pods Running? ✅ Healthy
3. Scroll to "Resource Utilization" row
4. Check time series graphs for trends (spikes, sustained high usage)

#### Investigate High Error Rate

1. Open **Service Health** dashboard
2. Locate "Error Rate by Service (5xx)" panel
3. Identify which service has elevated errors
4. Note the timestamp when errors started
5. Jump to **Logs Overview** dashboard
6. Filter logs by service and error level
7. Review "Top 10 Error Messages" for patterns

#### Analyze Service Latency

1. Open **Service Health** dashboard
2. Scroll to "Latency Metrics" row
3. Compare P50, P95, and P99 latency panels
4. Identify services exceeding thresholds:
   - P95 > 2s → Warning
   - P99 > 10s → Warning
   - P99 > 30s → Critical
5. If latency is high, jump to Jaeger for trace analysis

#### Monitor Database Connections

1. Open **Service Health** dashboard
2. Scroll to "Database Connections" row
3. Check PostgreSQL connection pool usage:
   - Active connections < 10 (max 15) → Healthy
   - If active ≥ 10 → Investigate slow queries
4. Check Redis connection pool:
   - Active + Idle < 20 → Healthy

#### View Namespace-Specific Metrics

1. Open the appropriate namespace dashboard:
   - `octollm-dev` for development
   - `octollm-staging` for staging
   - `octollm-prod` for production
2. Review "Pod Status" panel:
   - All Running? ✅
   - Any Failed or Pending? Investigate
3. Check "CPU Usage by Pod" and "Memory Usage by Pod"
4. Identify resource-hungry pods
5. Review "Container Restarts" panel:
   - 0 restarts → Healthy
   - 1-2 restarts → Monitor
   - 3+ restarts → Investigate (likely CrashLoopBackOff)

### Creating Custom Dashboards

If you need to create a custom dashboard:

1. Click "+" in the left sidebar
2. Select "Dashboard"
3. Click "Add new panel"
4. Select datasource: Prometheus, Loki, or Jaeger
5. Write PromQL, LogQL, or trace query
6. Configure visualization (time series, gauge, table, etc.)
7. Save dashboard with descriptive name and tags

---

## Prometheus Usage

### Accessing Prometheus UI

Prometheus is not exposed publicly for security. Use port-forwarding:

```bash
# Forward Prometheus port
kubectl port-forward -n octollm-monitoring svc/prometheus 9090:9090

# Access at http://localhost:9090
```

### Writing PromQL Queries

#### CPU Usage Query

```promql
# Average CPU usage across all nodes
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# CPU usage by specific service
sum(rate(container_cpu_usage_seconds_total{namespace="octollm-prod",pod=~"orchestrator.*"}[5m]))
```

#### Memory Usage Query

```promql
# Memory usage percentage
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))

# Memory usage by pod
sum(container_memory_working_set_bytes{namespace="octollm-prod",pod=~"orchestrator.*"})
```

#### Request Rate Query

```promql
# Total request rate across all services
sum(rate(http_requests_total{namespace=~"octollm.*"}[5m]))

# Request rate by service
sum(rate(http_requests_total{namespace=~"octollm.*"}[5m])) by (job)
```

#### Error Rate Query

```promql
# Error rate (5xx responses) as percentage
(
  sum(rate(http_requests_total{status=~"5..",namespace=~"octollm.*"}[5m]))
  /
  sum(rate(http_requests_total{namespace=~"octollm.*"}[5m]))
) * 100
```

#### Latency Query (P95, P99)

```promql
# P95 latency by service
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{namespace=~"octollm.*"}[5m])) by (job, le))

# P99 latency by service
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{namespace=~"octollm.*"}[5m])) by (job, le))
```

#### Database Connection Pool Query

```promql
# Active database connections
sum(db_connections_active) by (job)

# Connection pool usage percentage
(db_connections_active / (db_connections_active + db_connections_idle)) * 100
```

### Checking Alert Rules

1. In Prometheus UI, click "Alerts" in the top menu
2. View all configured alert rules
3. Check status:
   - **Inactive** (green) → Rule condition not met, no alert
   - **Pending** (yellow) → Rule condition met, waiting for `for` duration
   - **Firing** (red) → Alert is active, sent to Alertmanager
4. Click on an alert name to see:
   - Full alert query
   - Current value
   - Labels and annotations
   - Active alerts (if firing)

### Checking Alertmanager Status

Port-forward Alertmanager:

```bash
kubectl port-forward -n octollm-monitoring svc/alertmanager 9093:9093
```

Access http://localhost:9093:

1. **Alerts Tab**: View all active alerts
2. **Silences Tab**: View and create alert silences
3. **Status Tab**: View Alertmanager configuration

### Creating Alert Silences

If you need to temporarily suppress alerts (e.g., during maintenance):

1. Access Alertmanager UI (port-forward)
2. Click "Silences" tab
3. Click "New Silence"
4. Fill in:
   - **Matchers**: `alertname="HighCPUUsage"` OR `namespace="octollm-prod"`
   - **Start**: Now
   - **Duration**: 1h, 4h, 24h, etc.
   - **Creator**: Your name/email
   - **Comment**: Reason for silence (e.g., "Planned maintenance")
5. Click "Create"

---

## Loki Log Queries

### Accessing Loki via Grafana

1. Open Grafana: https://grafana.octollm.dev
2. Click "Explore" (compass icon) in left sidebar
3. Select "Loki" datasource from dropdown (top-left)
4. Write LogQL queries

### LogQL Syntax Basics

```logql
# Basic log stream selector
{namespace="octollm-prod"}

# Filter by pod
{namespace="octollm-prod", pod=~"orchestrator.*"}

# Filter by log level
{namespace="octollm-prod", level="error"}

# Filter by service label
{service="orchestrator", level="error"}

# Combine multiple filters
{namespace="octollm-prod", service="orchestrator", level=~"error|warn"}
```

### Common Log Queries

#### View All Logs from a Service

```logql
{namespace="octollm-prod", service="orchestrator"}
```

#### View Error Logs Only

```logql
{namespace="octollm-prod", level="error"}
```

#### Search for Specific Text in Logs

```logql
{namespace="octollm-prod"} |= "database connection failed"
```

#### Filter Out Specific Text

```logql
{namespace="octollm-prod"} != "health check"
```

#### Parse JSON Logs and Filter by Field

```logql
{namespace="octollm-prod"} | json | status_code >= 500
```

#### Count Error Rate Over Time

```logql
sum(rate({namespace="octollm-prod", level="error"}[1m])) by (service)
```

#### Top 10 Error Messages

```logql
topk(10, sum(count_over_time({namespace="octollm-prod", level="error"}[1h])) by (message))
```

#### Find Slow Requests (>1s)

```logql
{namespace="octollm-prod"} | json | duration > 1.0
```

### Investigating Errors with Logs

**Scenario**: You receive an alert for high error rate in the `orchestrator` service.

1. **Open Grafana Explore**
2. **Select Loki datasource**
3. **Query error logs**:
   ```logql
   {namespace="octollm-prod", service="orchestrator", level="error"}
   ```
4. **Adjust time range** to when the alert started (e.g., last 1 hour)
5. **Review log messages** for patterns:
   - Database connection errors?
   - LLM API errors (rate limiting, timeouts)?
   - Internal exceptions?
6. **Identify the error message** that appears most frequently
7. **Click on a log line** to expand full details:
   - Trace ID (if available) → Jump to Jaeger
   - Request ID → Correlate with other logs
   - Stack trace → Identify code location
8. **Check surrounding logs** (context) by clicking "Show Context"

---

## Jaeger Trace Analysis

### Accessing Jaeger UI

```bash
# Via browser
open https://jaeger.octollm.dev
```

### Searching for Traces

1. **Service Dropdown**: Select service (e.g., `orchestrator`)
2. **Operation Dropdown**: Select operation (e.g., `/api/v1/tasks`)
3. **Tags**: Add filters (e.g., `http.status_code=500`)
4. **Lookback**: Select time range (e.g., last 1 hour)
5. **Click "Find Traces"**

### Understanding Trace Visualizations

#### Trace Timeline View

- **Horizontal bars**: Each bar is a span (operation)
- **Bar length**: Duration of operation
- **Vertical position**: Parent-child relationships (nested = child span)
- **Color**: Service name (different services have different colors)

#### Trace Details

Click on a trace to view details:

1. **Trace Summary** (top):
   - Total duration
   - Number of spans
   - Service count
   - Errors (if any)

2. **Span List** (left):
   - Hierarchical view of all spans
   - Duration and start time for each span

3. **Span Details** (right, when clicked):
   - Operation name
   - Tags (metadata): `http.method`, `http.url`, `http.status_code`, etc.
   - Logs (events within span)
   - Process info: Service name, instance ID

### Common Trace Analysis Scenarios

#### Investigate High Latency

**Scenario**: P99 latency for `/api/v1/tasks` exceeds 10 seconds.

1. Open Jaeger UI
2. Select service: `orchestrator`
3. Select operation: `/api/v1/tasks` (or `POST /api/v1/tasks`)
4. Set lookback: Last 1 hour
5. Sort by: Duration (descending)
6. Click on the slowest trace
7. **Analyze the trace**:
   - Which span took the longest?
   - Database query? (look for spans with `db.*` tags)
   - LLM API call? (look for spans with `llm.*` tags)
   - Network call? (look for spans with `http.client.*` tags)
8. **Drill down** into the slow span:
   - Check tags for query parameters, request size, etc.
   - Check logs for error messages or warnings
9. **Compare with fast traces**:
   - Find a trace with normal latency
   - Compare span durations to identify the bottleneck

#### Find Errors in Traces

1. Open Jaeger UI
2. Select service
3. Add tag filter: `error=true`
4. Click "Find Traces"
5. Click on a trace with errors (marked with red icon)
6. **Identify error span**:
   - Look for red bar in timeline
   - Check span tags for `error.message` or `exception.type`
   - Check span logs for stack trace
7. **Understand error context**:
   - What was the request?
   - Which service/operation failed?
   - Was it a client error (4xx) or server error (5xx)?

#### Trace End-to-End Request Flow

**Scenario**: Understand the complete flow of a request through all services.

1. Open Jaeger UI
2. Select service: `orchestrator`
3. Find a recent successful trace
4. Click on the trace
5. **Analyze the flow**:
   - **Orchestrator** receives request
   - **Reflex Layer** preprocesses (fast, <10ms)
   - **Planner Arm** decomposes task
   - **Executor Arm** performs actions
   - **Judge Arm** validates output
   - **Orchestrator** returns response
6. **Check each span**:
   - Duration (is it reasonable?)
   - Tags (what data was passed?)
   - Logs (were there any warnings?)

### Correlating Traces with Logs

If a trace has a `trace_id`, you can find related logs:

1. Copy the `trace_id` from Jaeger span
2. Open Grafana Explore with Loki datasource
3. Query:
   ```logql
   {namespace="octollm-prod"} | json | trace_id="<PASTE_TRACE_ID>"
   ```
4. View all logs related to that trace

---

## Alert Investigation

### Alert Severity Levels

| Severity | Response Time | Notification | Escalation |
|----------|---------------|--------------|------------|
| **Critical** | < 15 minutes | PagerDuty + Slack | Immediate |
| **Warning** | < 1 hour | Slack | After 4 hours |
| **Info** | Best effort | Slack (optional) | None |

### Critical Alerts

#### PodCrashLoopBackOff

**Alert**: Pod `<namespace>/<pod>` is crash looping (>3 restarts in 10 minutes).

**Investigation Steps**:

1. **Check pod status**:
   ```bash
   kubectl get pods -n <namespace>
   kubectl describe pod <pod-name> -n <namespace>
   ```

2. **View pod logs**:
   ```bash
   kubectl logs <pod-name> -n <namespace> --previous
   ```

3. **Common causes**:
   - Application startup failure (missing env vars, config errors)
   - OOMKilled (check `kubectl describe pod` for `Reason: OOMKilled`)
   - Liveness probe failure (misconfigured health check)

4. **Resolution**:
   - If OOMKilled: Increase memory limit
   - If config error: Fix ConfigMap/Secret and restart
   - If code bug: Rollback deployment

#### NodeNotReady

**Alert**: Kubernetes node `<node>` is not ready for >5 minutes.

**Investigation Steps**:

1. **Check node status**:
   ```bash
   kubectl get nodes
   kubectl describe node <node-name>
   ```

2. **Check node conditions**:
   - `Ready=False` → Node is down
   - `MemoryPressure=True` → Node is out of memory
   - `DiskPressure=True` → Node is out of disk space

3. **Check node logs** (requires SSH access):
   ```bash
   gcloud compute ssh <node-name>
   journalctl -u kubelet -n 100
   ```

4. **Resolution**:
   - If `MemoryPressure`: Drain node, evict pods, add more nodes
   - If `DiskPressure`: Clear disk space, expand volume
   - If node unresponsive: Replace node

#### HighErrorRate

**Alert**: Service `<service>` has error rate >10% for 5 minutes.

**Investigation Steps**:

1. **Open Grafana Service Health dashboard**
2. **Identify the service with high errors**
3. **Check recent deployments**:
   ```bash
   kubectl rollout history deployment/<service> -n <namespace>
   ```

4. **View error logs**:
   ```logql
   {namespace="<namespace>", service="<service>", level="error"}
   ```

5. **Common causes**:
   - Recent deployment introduced bug
   - Downstream service failure (database, LLM API)
   - Configuration change

6. **Resolution**:
   - If recent deployment: Rollback
     ```bash
     kubectl rollout undo deployment/<service> -n <namespace>
     ```
   - If downstream failure: Check dependent services
   - If config issue: Fix ConfigMap/Secret

#### ServiceDown

**Alert**: Service `<service>` is unreachable for >2 minutes.

**Investigation Steps**:

1. **Check pod status**:
   ```bash
   kubectl get pods -n <namespace> -l app=<service>
   ```

2. **Check service endpoints**:
   ```bash
   kubectl get endpoints <service> -n <namespace>
   ```

3. **Check recent events**:
   ```bash
   kubectl get events -n <namespace> --sort-by='.lastTimestamp'
   ```

4. **Resolution**:
   - If no pods running: Check deployment spec, resource quotas
   - If pods running but unhealthy: Check liveness/readiness probes
   - If service misconfigured: Fix service selector

#### DatabaseConnectionPoolExhausted

**Alert**: Database connection pool >95% utilization for 5 minutes.

**Investigation Steps**:

1. **Check active connections in Grafana**
2. **Identify which service is using most connections**
3. **Check for connection leaks**:
   - Are connections being properly closed?
   - Are there long-running queries?

4. **View slow queries** (PostgreSQL):
   ```sql
   SELECT pid, now() - query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active'
   ORDER BY duration DESC;
   ```

5. **Resolution**:
   - Kill slow/stuck queries
   - Increase connection pool size (temporary)
   - Fix connection leak in code

### Warning Alerts

#### HighNodeCPUUsage

**Alert**: Node CPU usage >80% for 10 minutes.

**Investigation Steps**:

1. **Identify resource-hungry pods**:
   ```bash
   kubectl top pods -n <namespace> --sort-by=cpu
   ```

2. **Check for CPU throttling**:
   ```promql
   rate(container_cpu_cfs_throttled_seconds_total{namespace="<namespace>"}[5m])
   ```

3. **Resolution**:
   - Scale down non-critical workloads
   - Increase CPU limits for pods
   - Add more cluster nodes (HorizontalPodAutoscaler)

#### HighNodeMemoryUsage

**Alert**: Node memory usage >85% for 10 minutes.

**Investigation Steps**:

1. **Identify memory-hungry pods**:
   ```bash
   kubectl top pods -n <namespace> --sort-by=memory
   ```

2. **Check for memory leaks**:
   - Review application logs for OOM warnings
   - Check memory usage trend (gradual increase = leak)

3. **Resolution**:
   - Restart pods with memory leaks
   - Increase memory limits
   - Add more cluster nodes

---

## Common Troubleshooting Scenarios

### Scenario 1: Sudden Spike in Latency

**Symptoms**:
- P99 latency increased from 5s to 30s
- No increase in error rate
- Request rate unchanged

**Investigation**:

1. **Check Grafana Service Health dashboard**
   - Identify which service has high latency
2. **Open Jaeger, find slow traces**
   - Identify bottleneck span (database query, LLM call, etc.)
3. **Check database performance**:
   ```promql
   rate(db_query_duration_seconds_sum[5m]) / rate(db_query_duration_seconds_count[5m])
   ```
4. **Check LLM API latency**:
   ```logql
   {namespace="octollm-prod"} | json | llm_duration_seconds > 10
   ```

**Resolution**:
- If database slow: Check for missing indexes, slow queries
- If LLM slow: Check provider status, implement caching

### Scenario 2: Service Keeps Restarting

**Symptoms**:
- Pod restart count increasing
- No obvious errors in logs
- Service health checks failing

**Investigation**:

1. **Check pod events**:
   ```bash
   kubectl describe pod <pod-name> -n <namespace>
   ```

2. **Check for OOMKilled**:
   - Look for `Reason: OOMKilled` in pod status
   - Memory limit too low

3. **Check liveness probe**:
   - Is probe misconfigured (timeout too short)?
   - Is health endpoint actually healthy?

4. **View logs from previous container**:
   ```bash
   kubectl logs <pod-name> -n <namespace> --previous
   ```

**Resolution**:
- If OOMKilled: Increase memory limit
- If liveness probe: Adjust probe settings or fix health endpoint
- If application crash: Fix code bug

### Scenario 3: Certificate Expiration

**Symptoms**:
- Alert: Certificate expiring in <7 days
- HTTPS services may be affected

**Investigation**:

1. **Check certificate expiration**:
   ```bash
   kubectl get certificate -n <namespace>
   ```

2. **Check cert-manager logs**:
   ```bash
   kubectl logs -n cert-manager deployment/cert-manager
   ```

3. **Check certificate renewal attempts**:
   ```bash
   kubectl describe certificate <cert-name> -n <namespace>
   ```

**Resolution**:
- If cert-manager renewal failed: Check DNS, ACME challenge logs
- If manual renewal needed:
  ```bash
  kubectl delete certificate <cert-name> -n <namespace>
  # cert-manager will automatically create new certificate
  ```

---

## Escalation Procedures

### When to Escalate

Escalate to the next level if:

1. **Critical alert** not resolved within **15 minutes**
2. **Multiple critical alerts** firing simultaneously
3. **Data loss** or **security incident** suspected
4. **Root cause** unclear after 30 minutes of investigation
5. **Infrastructure issue** beyond application scope (GCP outage, network failure)

### Escalation Contacts

| Level | Contact | Response Time | Scope |
|-------|---------|---------------|-------|
| **L1** | On-Call Engineer | < 15 min | Application-level issues |
| **L2** | Senior SRE | < 30 min | Complex infrastructure issues |
| **L3** | Platform Lead | < 1 hour | Critical system-wide incidents |
| **L4** | CTO | < 2 hours | Business-critical outages |

### Escalation Process

1. **Gather information**:
   - Alert name and severity
   - Time alert started
   - Services affected
   - Investigation steps taken so far
   - Current hypothesis

2. **Contact next level**:
   - PagerDuty (for critical alerts)
   - Slack #incidents channel
   - Phone (for P0/P1 incidents)

3. **Provide context**:
   - Share Grafana dashboard links
   - Share relevant logs/traces
   - Describe impact (users affected, data loss risk)

4. **Continue investigation** while waiting for response

5. **Update incident channel** with progress

---

## Appendix

### Useful kubectl Commands

```bash
# Get all pods in namespace
kubectl get pods -n octollm-prod

# Describe pod (detailed info)
kubectl describe pod <pod-name> -n octollm-prod

# View pod logs
kubectl logs <pod-name> -n octollm-prod

# View logs from previous container (if restarted)
kubectl logs <pod-name> -n octollm-prod --previous

# Follow logs in real-time
kubectl logs -f <pod-name> -n octollm-prod

# Execute command in pod
kubectl exec -it <pod-name> -n octollm-prod -- /bin/bash

# Port-forward to pod
kubectl port-forward -n octollm-prod <pod-name> 8000:8000

# Get events in namespace
kubectl get events -n octollm-prod --sort-by='.lastTimestamp'

# Get top pods by CPU/memory
kubectl top pods -n octollm-prod --sort-by=cpu
kubectl top pods -n octollm-prod --sort-by=memory

# Rollback deployment
kubectl rollout undo deployment/<service> -n octollm-prod

# Scale deployment
kubectl scale deployment/<service> -n octollm-prod --replicas=5

# Delete pod (will be recreated by deployment)
kubectl delete pod <pod-name> -n octollm-prod
```

### Useful PromQL Aggregations

```promql
# Sum
sum(metric_name) by (label)

# Average
avg(metric_name) by (label)

# Count
count(metric_name) by (label)

# Min/Max
min(metric_name) by (label)
max(metric_name) by (label)

# Top K
topk(10, metric_name)

# Bottom K
bottomk(10, metric_name)

# Rate (per-second)
rate(metric_name[5m])

# Increase (total over time)
increase(metric_name[1h])

# Histogram quantile (P95, P99)
histogram_quantile(0.95, rate(metric_bucket[5m]))
```

### Useful LogQL Patterns

```logql
# Stream selector
{label="value"}

# Multiple labels
{label1="value1", label2="value2"}

# Regex match
{label=~"regex"}

# Negative regex
{label!~"regex"}

# Contains text
{label="value"} |= "search text"

# Doesn't contain text
{label="value"} != "exclude text"

# Regex filter
{label="value"} |~ "regex"

# JSON parsing
{label="value"} | json

# Rate (logs per second)
rate({label="value"}[1m])

# Count over time
count_over_time({label="value"}[1h])

# Aggregations
sum(count_over_time({label="value"}[1h])) by (service)
```

### GCP Commands

```bash
# List GKE clusters
gcloud container clusters list

# Get cluster credentials
gcloud container clusters get-credentials octollm-prod --region us-central1

# List nodes
gcloud compute instances list

# SSH to node
gcloud compute ssh <node-name>

# View GCS buckets (for Loki logs)
gsutil ls gs://octollm-loki-logs

# View bucket contents
gsutil ls -r gs://octollm-loki-logs

# Check Cloud SQL instances
gcloud sql instances list

# Check Redis instances
gcloud redis instances list --region us-central1
```

---

**End of Runbook**

For additional assistance, contact:
- Slack: #octollm-sre
- PagerDuty: octollm-oncall
- Email: sre@octollm.dev
