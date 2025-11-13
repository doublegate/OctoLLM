# Alert Response Procedures

**Document Version**: 1.0.0
**Last Updated**: 2025-11-12
**Owner**: OctoLLM Operations Team
**Status**: Production

## Table of Contents

1. [Overview](#overview)
2. [Response Workflow](#response-workflow)
3. [Critical Alert Procedures](#critical-alert-procedures)
4. [Warning Alert Procedures](#warning-alert-procedures)
5. [Informational Alert Procedures](#informational-alert-procedures)
6. [Multi-Alert Scenarios](#multi-alert-scenarios)
7. [Escalation Decision Trees](#escalation-decision-trees)
8. [Post-Incident Actions](#post-incident-actions)

---

## Overview

This document provides step-by-step procedures for responding to alerts from the OctoLLM monitoring system. Each procedure includes:

- **Detection**: How the alert is triggered
- **Impact**: What this means for users and the system
- **Investigation Steps**: How to diagnose the issue
- **Remediation Actions**: How to fix the problem
- **Escalation Criteria**: When to involve senior engineers or management

**Alert Severity Levels**:
- **Critical**: Immediate action required, user-impacting, PagerDuty notification
- **Warning**: Action required within 1 hour, potential user impact, Slack notification
- **Info**: No immediate action required, informational only, logged to Slack

**Response Time SLAs**:
- **Critical**: Acknowledge within 5 minutes, resolve within 1 hour
- **Warning**: Acknowledge within 30 minutes, resolve within 4 hours
- **Info**: Review within 24 hours

---

## Response Workflow

### General Alert Response Process

```
1. ACKNOWLEDGE
   └─> Acknowledge alert in PagerDuty/Slack
   └─> Note start time in incident tracker

2. ASSESS
   └─> Check alert details (service, namespace, severity)
   └─> Review recent deployments or changes
   └─> Check for related alerts

3. INVESTIGATE
   └─> Follow specific alert procedure (see sections below)
   └─> Gather logs, metrics, traces
   └─> Identify root cause

4. REMEDIATE
   └─> Apply fix (restart, scale, rollback, etc.)
   └─> Verify fix with metrics/logs
   └─> Monitor for 10-15 minutes

5. DOCUMENT
   └─> Update incident tracker with resolution
   └─> Create post-incident review if critical
   └─> Update runbooks if new issue discovered

6. CLOSE
   └─> Resolve alert in PagerDuty/Slack
   └─> Confirm no related alerts remain
```

### Tools Quick Reference

- **Grafana**: https://grafana.octollm.dev
- **Prometheus**: https://prometheus.octollm.dev
- **Jaeger**: https://jaeger.octollm.dev
- **Alertmanager**: https://alertmanager.octollm.dev
- **kubectl**: CLI access to Kubernetes cluster

---

## Critical Alert Procedures

### 1. PodCrashLoopBackOff

**Alert Definition**:
```yaml
alert: PodCrashLoopBackOff
expr: rate(kube_pod_container_status_restarts_total{namespace=~"octollm.*"}[10m]) > 0.3
for: 5m
severity: critical
```

**Impact**: Service degradation or complete outage. Users may experience errors or timeouts.

#### Investigation Steps

**Step 1: Identify the crashing pod**
```bash
# List pods with high restart counts
kubectl get pods -n <namespace> --sort-by=.status.containerStatuses[0].restartCount

# Example output:
# NAME                          READY   STATUS             RESTARTS   AGE
# orchestrator-7d9f8c-xk2p9     0/1     CrashLoopBackOff   12         30m
```

**Step 2: Check pod logs**
```bash
# Get recent logs from crashing container
kubectl logs -n <namespace> <pod-name> --tail=100

# Get logs from previous container instance
kubectl logs -n <namespace> <pod-name> --previous

# Common error patterns:
# - "Connection refused" → Dependency unavailable
# - "Out of memory" → Resource limits too low
# - "Panic: runtime error" → Code bug
# - "Permission denied" → RBAC or volume mount issue
```

**Step 3: Check pod events**
```bash
kubectl describe pod -n <namespace> <pod-name>

# Look for events like:
# - "Back-off restarting failed container"
# - "Error: ErrImagePull"
# - "FailedMount"
# - "OOMKilled"
```

**Step 4: Check resource usage**
```bash
# Check if pod is OOMKilled
kubectl get pod -n <namespace> <pod-name> -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}'

# Check resource requests/limits
kubectl get pod -n <namespace> <pod-name> -o jsonpath='{.spec.containers[0].resources}'
```

**Step 5: Check configuration**
```bash
# Verify environment variables
kubectl get pod -n <namespace> <pod-name> -o jsonpath='{.spec.containers[0].env}'

# Check ConfigMap/Secret mounts
kubectl describe configmap -n <namespace> <configmap-name>
kubectl describe secret -n <namespace> <secret-name>
```

#### Remediation Actions

**If: Connection refused to dependency (DB, Redis, etc.)**
```bash
# 1. Check if dependency service is healthy
kubectl get pods -n <namespace> -l app=<dependency>

# 2. Test connectivity from within cluster
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# Inside pod: nc -zv <service-name> <port>

# 3. Check service endpoints
kubectl get endpoints -n <namespace> <service-name>

# 4. If dependency is down, restart it first
kubectl rollout restart deployment/<dependency-name> -n <namespace>

# 5. Wait for dependency to be ready, then restart affected pod
kubectl delete pod -n <namespace> <pod-name>
```

**If: Out of memory (OOMKilled)**
```bash
# 1. Check current memory usage in Grafana
# Query: container_memory_usage_bytes{pod="<pod-name>"}

# 2. Increase memory limits
kubectl edit deployment -n <namespace> <deployment-name>
# Increase resources.limits.memory (e.g., from 512Mi to 1Gi)

# 3. Monitor memory usage after restart
```

**If: Image pull error**
```bash
# 1. Check image name and tag
kubectl get pod -n <namespace> <pod-name> -o jsonpath='{.spec.containers[0].image}'

# 2. Verify image exists in registry
gcloud container images list --repository=gcr.io/<project-id>

# 3. Check image pull secrets
kubectl get secrets -n <namespace> | grep gcr

# 4. If image is wrong, update deployment
kubectl set image deployment/<deployment-name> <container-name>=<correct-image> -n <namespace>
```

**If: Configuration error**
```bash
# 1. Validate ConfigMap/Secret exists and has correct data
kubectl get configmap -n <namespace> <configmap-name> -o yaml

# 2. If config is wrong, update it
kubectl edit configmap -n <namespace> <configmap-name>

# 3. Restart pods to pick up new config
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

**If: Code bug (panic, runtime error)**
```bash
# 1. Check Jaeger for traces showing error
# Navigate to https://jaeger.octollm.dev
# Search for service: <service-name>, operation: <failing-operation>

# 2. Identify commit that introduced bug
kubectl get deployment -n <namespace> <deployment-name> -o jsonpath='{.spec.template.spec.containers[0].image}'

# 3. Rollback to previous version
kubectl rollout undo deployment/<deployment-name> -n <namespace>

# 4. Verify rollback
kubectl rollout status deployment/<deployment-name> -n <namespace>

# 5. Create incident ticket with logs/traces
# Subject: "CrashLoopBackOff in <service> due to <error>"
# Include: logs, traces, reproduction steps
```

**If: Persistent volume mount failure**
```bash
# 1. Check PVC status
kubectl get pvc -n <namespace>

# 2. Check PVC events
kubectl describe pvc -n <namespace> <pvc-name>

# 3. If PVC is pending, check storage class
kubectl get storageclass

# 4. If PVC is lost, restore from backup (see backup-restore.md)
```

#### Escalation Criteria

**Escalate to Senior Engineer if**:
- Root cause not identified within 15 minutes
- Multiple pods crashing across different services
- Rollback does not resolve the issue
- Data loss suspected

**Escalate to Engineering Lead if**:
- Critical service (orchestrator, reflex-layer) down for >30 minutes
- Root cause requires code fix (cannot be resolved via config/restart)

**Escalate to VP Engineering if**:
- Complete outage (all services down)
- Data corruption suspected
- Estimated resolution time >2 hours

---

### 2. NodeNotReady

**Alert Definition**:
```yaml
alert: NodeNotReady
expr: kube_node_status_condition{condition="Ready",status="false"} == 1
for: 5m
severity: critical
```

**Impact**: Reduced cluster capacity. Pods on the node are evicted and rescheduled. Possible service degradation.

#### Investigation Steps

**Step 1: Identify unhealthy node**
```bash
# List all nodes with status
kubectl get nodes -o wide

# Example output:
# NAME                     STATUS     ROLES    AGE   VERSION
# gke-cluster-pool-1-abc   Ready      <none>   10d   v1.28.3
# gke-cluster-pool-1-def   NotReady   <none>   10d   v1.28.3  ← Problem node
```

**Step 2: Check node conditions**
```bash
kubectl describe node <node-name>

# Look for conditions:
# - Ready: False
# - MemoryPressure: True
# - DiskPressure: True
# - PIDPressure: True
# - NetworkUnavailable: True
```

**Step 3: Check node resource usage**
```bash
# Check node metrics
kubectl top node <node-name>

# Query in Grafana:
# CPU: node_cpu_seconds_total{instance="<node-name>"}
# Memory: node_memory_MemAvailable_bytes{instance="<node-name>"}
# Disk: node_filesystem_avail_bytes{instance="<node-name>"}
```

**Step 4: Check kubelet logs (if SSH access available)**
```bash
# SSH to node (GKE nodes)
gcloud compute ssh <node-name> --zone=<zone>

# Check kubelet status
sudo systemctl status kubelet

# Check kubelet logs
sudo journalctl -u kubelet --since "30 minutes ago"
```

**Step 5: Check pods on the node**
```bash
# List pods running on the node
kubectl get pods --all-namespaces --field-selector spec.nodeName=<node-name>

# Check if critical pods are affected
kubectl get pods -n octollm-prod --field-selector spec.nodeName=<node-name>
```

#### Remediation Actions

**If: Disk pressure (disk full)**
```bash
# 1. Check disk usage on node
gcloud compute ssh <node-name> --zone=<zone> --command "df -h"

# 2. Identify large files/directories
gcloud compute ssh <node-name> --zone=<zone> --command "du -sh /var/lib/docker/containers/* | sort -rh | head -20"

# 3. Clean up old container logs
gcloud compute ssh <node-name> --zone=<zone> --command "sudo find /var/lib/docker/containers -name '*-json.log' -type f -mtime +7 -delete"

# 4. Clean up unused Docker images
gcloud compute ssh <node-name> --zone=<zone> --command "sudo docker system prune -a -f"

# 5. If still full, cordon and drain the node
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# 6. Delete and recreate node (GKE auto-repairs)
# Node will be automatically replaced by GKE
```

**If: Memory pressure**
```bash
# 1. Check memory usage
kubectl top node <node-name>

# 2. Identify memory-hungry pods
kubectl top pods --all-namespaces --field-selector spec.nodeName=<node-name> --sort-by=memory

# 3. Check if any pods have memory leaks
# Use Grafana to view memory trends over time
# Query: container_memory_usage_bytes{node="<node-name>"}

# 4. Evict non-critical pods to free memory
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force

# 5. Wait for pods to be rescheduled
kubectl get pods --all-namespaces -o wide | grep <node-name>

# 6. Uncordon node if memory stabilizes
kubectl uncordon <node-name>

# 7. If memory pressure persists, replace node
# Delete node and let GKE auto-repair create new one
```

**If: Network unavailable**
```bash
# 1. Check network connectivity from node
gcloud compute ssh <node-name> --zone=<zone> --command "ping -c 5 8.8.8.8"

# 2. Check CNI plugin status (GKE uses kubenet or Calico)
gcloud compute ssh <node-name> --zone=<zone> --command "sudo systemctl status kubenet"

# 3. Check for network plugin errors
gcloud compute ssh <node-name> --zone=<zone> --command "sudo journalctl -u kubenet --since '30 minutes ago'"

# 4. Restart network services (risky - only if node is already unusable)
gcloud compute ssh <node-name> --zone=<zone> --command "sudo systemctl restart kubenet"

# 5. If network issue persists, cordon and drain
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force

# 6. Delete node and let GKE replace it
gcloud compute instances delete <node-name> --zone=<zone>
```

**If: Kubelet not responding**
```bash
# 1. Check kubelet process
gcloud compute ssh <node-name> --zone=<zone> --command "sudo systemctl status kubelet"

# 2. Restart kubelet
gcloud compute ssh <node-name> --zone=<zone> --command "sudo systemctl restart kubelet"

# 3. Wait 2 minutes and check node status
kubectl get node <node-name>

# 4. If node returns to Ready, uncordon
kubectl uncordon <node-name>

# 5. If kubelet fails to start, check logs
gcloud compute ssh <node-name> --zone=<zone> --command "sudo journalctl -u kubelet -n 100"

# 6. If cannot resolve, cordon, drain, and delete node
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force
gcloud compute instances delete <node-name> --zone=<zone>
```

**If: Hardware failure (rare in GKE)**
```bash
# 1. Check for hardware errors in system logs
gcloud compute ssh <node-name> --zone=<zone> --command "dmesg | grep -i error"

# 2. Check for I/O errors
gcloud compute ssh <node-name> --zone=<zone> --command "dmesg | grep -i 'i/o error'"

# 3. Cordon and drain immediately
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force

# 4. Delete node - GKE will create replacement
gcloud compute instances delete <node-name> --zone=<zone>

# 5. Monitor new node creation
kubectl get nodes -w
```

#### Escalation Criteria

**Escalate to Senior Engineer if**:
- Multiple nodes NotReady simultaneously
- Node cannot be drained (pods stuck in terminating state)
- Network issues affecting entire node pool

**Escalate to Engineering Lead if**:
- >30% of nodes NotReady
- Node failure pattern suggests cluster-wide issue
- Auto-repair not creating replacement nodes

**Escalate to VP Engineering + GCP Support if**:
- Complete cluster failure (all nodes NotReady)
- GKE control plane unreachable
- Suspected GCP infrastructure issue

---

### 3. HighErrorRate

**Alert Definition**:
```yaml
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.1
for: 5m
severity: critical
```

**Impact**: Users experiencing errors (500, 502, 503, 504). Service availability degraded.

#### Investigation Steps

**Step 1: Identify affected service**
```bash
# Check error rate in Grafana
# Dashboard: GKE Service Health
# Panel: "Error Rate (5xx) by Service"
# Identify which service has >10% error rate
```

**Step 2: Check recent deployments**
```bash
# List recent rollouts
kubectl rollout history deployment/<deployment-name> -n <namespace>

# Check when error rate started
# Compare with deployment timestamp in Grafana
```

**Step 3: Analyze error patterns**
```bash
# Query Loki for error logs
# LogQL: {namespace="<namespace>", service="<service>", level="error"} |= "5xx" | json

# Look for patterns:
# - Specific endpoints failing
# - Common error messages
# - Correlation with other services
```

**Step 4: Check dependencies**
```bash
# Check if errors are due to downstream dependencies
# Use Jaeger to trace requests
# Navigate to https://jaeger.octollm.dev
# Search for service: <service-name>
# Filter by error status: error=true

# Common dependency issues:
# - Database connection pool exhausted
# - Redis timeout
# - External API rate limiting
# - Inter-service timeout
```

**Step 5: Check resource utilization**
```bash
# Check if service is resource-constrained
kubectl top pods -n <namespace> -l app=<service>

# Query CPU/memory in Grafana:
# CPU: rate(container_cpu_usage_seconds_total{pod=~"<service>.*"}[5m])
# Memory: container_memory_usage_bytes{pod=~"<service>.*"}
```

#### Remediation Actions

**If: Error rate increased after recent deployment**
```bash
# 1. Verify deployment timing matches error spike
kubectl rollout history deployment/<deployment-name> -n <namespace>

# 2. Check logs from new pods
kubectl logs -n <namespace> -l app=<service> --tail=100 | grep -i error

# 3. Rollback to previous version
kubectl rollout undo deployment/<deployment-name> -n <namespace>

# 4. Monitor error rate after rollback
# Should decrease within 2-5 minutes

# 5. Verify rollback success
kubectl rollout status deployment/<deployment-name> -n <namespace>

# 6. Create incident ticket with error logs
# Block new deployment until issue is resolved
```

**If: Database connection pool exhausted**
```bash
# 1. Verify in Grafana
# Query: db_pool_active_connections{service="<service>"} / db_pool_max_connections{service="<service>"}

# 2. Check for connection leaks
# Look for long-running queries in database
# PostgreSQL: SELECT * FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes';

# 3. Restart service to clear connections
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# 4. If issue persists, increase connection pool size
kubectl edit configmap -n <namespace> <service>-config
# Increase DB_POOL_SIZE (e.g., from 20 to 40)

# 5. Restart to apply new config
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# 6. Monitor connection pool usage
# Should stay below 80% of max
```

**If: Downstream service timeout**
```bash
# 1. Identify failing dependency from Jaeger traces
# Look for spans with error=true and long duration

# 2. Check health of downstream service
kubectl get pods -n <namespace> -l app=<downstream-service>

# 3. Check latency of downstream service
# Grafana query: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="<downstream-service>"}[5m]))

# 4. If downstream is slow, scale it up
kubectl scale deployment/<downstream-service> -n <namespace> --replicas=<new-count>

# 5. Increase timeout in calling service (if downstream is legitimately slow)
kubectl edit configmap -n <namespace> <service>-config
# Increase timeout (e.g., from 5s to 10s)

# 6. Restart calling service
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

**If: External API rate limiting**
```bash
# 1. Verify in logs
kubectl logs -n <namespace> -l app=<service> | grep -i "rate limit\|429\|too many requests"

# 2. Check rate limit configuration
kubectl get configmap -n <namespace> <service>-config -o yaml | grep -i rate

# 3. Reduce request rate (add caching, implement backoff)
# Short-term: Reduce replica count to lower total requests
kubectl scale deployment/<deployment-name> -n <namespace> --replicas=<reduced-count>

# 4. Implement circuit breaker (code change required)
# Long-term fix: Add circuit breaker to prevent cascading failures

# 5. Contact external API provider for rate limit increase
# Document current usage and justification for higher limits
```

**If: Memory leak causing OOM errors**
```bash
# 1. Identify memory trend in Grafana
# Query: container_memory_usage_bytes{pod=~"<service>.*"}
# Look for steady increase over time

# 2. Restart pods to free memory (temporary fix)
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# 3. Increase memory limits (short-term mitigation)
kubectl edit deployment -n <namespace> <deployment-name>
# Increase resources.limits.memory

# 4. Enable heap profiling (if supported)
# Add profiling endpoint to service
# Analyze heap dumps to identify leak

# 5. Create high-priority bug ticket
# Attach memory graphs and profiling data
# Assign to owning team
```

#### Escalation Criteria

**Escalate to Senior Engineer if**:
- Error rate >20% for >10 minutes
- Rollback does not resolve issue
- Root cause unclear after 15 minutes of investigation

**Escalate to Engineering Lead if**:
- Error rate >50% (severe outage)
- Multiple services affected
- Estimated resolution time >1 hour

**Escalate to VP Engineering if**:
- Complete service outage (100% error rate)
- Customer-reported errors trending on social media
- Revenue-impacting outage

---

### 4. DatabaseConnectionPoolExhausted

**Alert Definition**:
```yaml
alert: DatabaseConnectionPoolExhausted
expr: db_pool_active_connections / db_pool_max_connections > 0.95
for: 5m
severity: critical
```

**Impact**: Services unable to query database. Users experience errors or timeouts.

#### Investigation Steps

**Step 1: Verify pool exhaustion**
```bash
# Check current pool usage in Grafana
# Query: db_pool_active_connections{service="<service>"} / db_pool_max_connections{service="<service>"}

# Check which service is affected
# Multiple services may share the same database
```

**Step 2: Check for long-running queries**
```bash
# Connect to database
kubectl exec -it -n <namespace> <postgres-pod> -- psql -U octollm

# List active connections by service
SELECT application_name, COUNT(*)
FROM pg_stat_activity
WHERE state = 'active'
GROUP BY application_name;

# List long-running queries (>5 minutes)
SELECT pid, application_name, query_start, state, query
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < NOW() - INTERVAL '5 minutes'
ORDER BY query_start;
```

**Step 3: Check for connection leaks**
```bash
# List idle connections
SELECT application_name, COUNT(*)
FROM pg_stat_activity
WHERE state = 'idle'
GROUP BY application_name;

# If idle count is very high for a service, there's likely a connection leak
# (Idle connections should be returned to pool)
```

**Step 4: Check application logs for connection errors**
```bash
# Query Loki
# LogQL: {namespace="<namespace>", service="<service>"} |= "connection" |= "error|timeout|exhausted"

# Common error messages:
# - "unable to acquire connection from pool"
# - "connection pool timeout"
# - "too many clients already"
```

**Step 5: Check database resource usage**
```bash
# Check database CPU/memory
kubectl top pod -n <namespace> <postgres-pod>

# Check database metrics in Grafana
# CPU: rate(container_cpu_usage_seconds_total{pod="<postgres-pod>"}[5m])
# Memory: container_memory_usage_bytes{pod="<postgres-pod>"}
# Disk I/O: rate(container_fs_reads_bytes_total{pod="<postgres-pod>"}[5m])
```

#### Remediation Actions

**If: Long-running queries blocking connections**
```bash
# 1. Identify problematic queries
SELECT pid, application_name, query_start, query
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < NOW() - INTERVAL '5 minutes';

# 2. Terminate long-running queries (careful!)
# Only terminate if you're sure it's safe
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <pid>;

# 3. Monitor connection pool recovery
# Check Grafana: pool usage should drop below 95%

# 4. Investigate why queries are slow
# Use EXPLAIN ANALYZE to check query plans
# Look for missing indexes or inefficient joins

# 5. Optimize slow queries (code change)
# Create ticket with slow query details
# Add indexes if needed
```

**If: Connection leak in application**
```bash
# 1. Identify service with high idle connection count
SELECT application_name, COUNT(*)
FROM pg_stat_activity
WHERE state = 'idle'
GROUP BY application_name;

# 2. Restart affected service to release connections
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# 3. Monitor connection pool after restart
# Usage should drop significantly

# 4. Check application code for connection handling
# Ensure connections are properly closed in finally blocks
# Example (Python):
# try:
#     conn = pool.get_connection()
#     # Use connection
# finally:
#     conn.close()  # Must always close!

# 5. Implement connection timeout in pool config
# Add to service ConfigMap:
# DB_POOL_TIMEOUT: 30s
# DB_CONN_MAX_LIFETIME: 1h  # Force connection recycling
```

**If: Pool size too small for load**
```bash
# 1. Check current pool configuration
kubectl get configmap -n <namespace> <service>-config -o yaml | grep DB_POOL

# 2. Calculate required pool size
# Formula: (avg concurrent requests) * (avg query time in seconds) * 1.5
# Example: 100 req/s * 0.1s * 1.5 = 15 connections

# 3. Increase pool size
kubectl edit configmap -n <namespace> <service>-config
# Update DB_POOL_SIZE (e.g., from 20 to 40)

# 4. Verify database can handle more connections
# PostgreSQL max_connections setting (typically 100-200)
kubectl exec -it -n <namespace> <postgres-pod> -- psql -U octollm -c "SHOW max_connections;"

# 5. If database max_connections is too low, increase it
# Edit PostgreSQL ConfigMap or StatefulSet
# Requires database restart

# 6. Restart service to use new pool size
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# 7. Monitor pool usage
# Target: <80% utilization under normal load
```

**If: Database is resource-constrained**
```bash
# 1. Check database CPU/memory
kubectl top pod -n <namespace> <postgres-pod>

# 2. If database CPU >80%, check for expensive queries
# Connect to database
kubectl exec -it -n <namespace> <postgres-pod> -- psql -U octollm

# Find most expensive queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

# 3. If database memory >90%, increase memory limits
kubectl edit statefulset -n <namespace> postgres
# Increase resources.limits.memory

# 4. If database disk I/O high, consider:
# - Adding indexes to reduce table scans
# - Increasing disk IOPS (resize persistent disk)
# - Enabling query result caching

# 5. Scale database vertically (larger instance)
# For managed databases (Cloud SQL), increase machine type
# For self-hosted, increase resource limits and restart
```

**If: Too many services connecting to same database**
```bash
# 1. Identify which services are using most connections
SELECT application_name, COUNT(*), MAX(query_start)
FROM pg_stat_activity
GROUP BY application_name
ORDER BY COUNT(*) DESC;

# 2. Implement connection pooling at database level
# Deploy PgBouncer between services and database
# PgBouncer multiplexes connections, reducing load on database

# 3. Configure PgBouncer
# pool_mode: transaction (default) or session
# max_client_conn: 1000 (much higher than database limit)
# default_pool_size: 20 (connections to actual database per pool)

# 4. Update service connection strings to point to PgBouncer
kubectl edit configmap -n <namespace> <service>-config
# Change DB_HOST from postgres:5432 to pgbouncer:6432

# 5. Restart services
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# 6. Monitor PgBouncer metrics
# Check connection multiplexing ratio
```

#### Escalation Criteria

**Escalate to Senior Engineer if**:
- Pool exhaustion persists after restarting services
- Cannot identify source of connection leak
- Database max_connections needs to be increased significantly

**Escalate to Database Admin if**:
- Database CPU/memory consistently >90%
- Slow queries cannot be optimized with indexes
- Need to implement replication or sharding

**Escalate to Engineering Lead if**:
- Database outage suspected
- Need to migrate to larger database instance
- Estimated resolution time >1 hour

---

### 5. HighLatency

**Alert Definition**:
```yaml
alert: HighLatency
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
for: 10m
severity: critical
```

**Impact**: Slow response times for users. Degraded user experience. Possible timeout errors.

#### Investigation Steps

**Step 1: Identify affected service and endpoints**
```bash
# Check latency by service in Grafana
# Dashboard: GKE Service Health
# Panel: "Request Latency (P50/P95/P99)"
# Identify which service has P95 >1s

# Check latency by endpoint
# Query: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="<service>"}[5m])) by (handler)
```

**Step 2: Check for recent changes**
```bash
# List recent deployments
kubectl rollout history deployment/<deployment-name> -n <namespace>

# Check when latency increased
# Compare with deployment timestamp in Grafana
```

**Step 3: Analyze slow requests with Jaeger**
```bash
# Navigate to https://jaeger.octollm.dev
# 1. Search for service: <service-name>
# 2. Filter by min duration: >1s
# 3. Sort by longest duration
# 4. Click on slowest trace to see span breakdown

# Look for:
# - Which span is slowest (database query, external API call, internal processing)
# - Spans with errors
# - Multiple spans to same service (N+1 query problem)
```

**Step 4: Check resource utilization**
```bash
# Check if service is CPU-constrained
kubectl top pods -n <namespace> -l app=<service>

# Query CPU in Grafana:
# rate(container_cpu_usage_seconds_total{pod=~"<service>.*"}[5m])

# If CPU near limit, service may be throttled
```

**Step 5: Check dependencies**
```bash
# Check if downstream services are slow
# Use Jaeger to identify which dependency is slow

# Check database query performance
# Connect to database and check slow query log

# Check cache hit rate (Redis)
# Grafana query: redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)
```

#### Remediation Actions

**If: Slow database queries**
```bash
# 1. Identify slow queries from Jaeger traces
# Look for database spans with duration >500ms

# 2. Connect to database and analyze query
kubectl exec -it -n <namespace> <postgres-pod> -- psql -U octollm

# 3. Use EXPLAIN ANALYZE to check query plan
EXPLAIN ANALYZE <slow-query>;

# 4. Look for sequential scans (bad - should use index)
# Look for "Seq Scan on <table>" in output

# 5. Create missing indexes
CREATE INDEX CONCURRENTLY idx_<table>_<column> ON <table>(<column>);
# CONCURRENTLY allows index creation without locking table

# 6. Monitor query performance after index creation
# Should see immediate improvement in latency

# 7. Update query to use index (if optimizer doesn't automatically)
# Sometimes need to rewrite query to use indexed columns
```

**If: Low cache hit rate**
```bash
# 1. Check cache hit rate in Grafana
# Query: redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)
# Target: >80% hit rate

# 2. Check cache size
kubectl exec -it -n <namespace> <redis-pod> -- redis-cli INFO memory

# 3. If cache is too small, increase memory
kubectl edit statefulset -n <namespace> redis
# Increase resources.limits.memory

# 4. Check cache TTL settings
# If TTL too short, increase it
kubectl get configmap -n <namespace> <service>-config -o yaml | grep CACHE_TTL

# 5. Increase cache TTL
kubectl edit configmap -n <namespace> <service>-config
# CACHE_TTL: 600s → 1800s (10m → 30m)

# 6. Restart service to use new TTL
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# 7. Consider implementing cache warming
# Pre-populate cache with frequently accessed data
```

**If: CPU-constrained (throttled)**
```bash
# 1. Check CPU usage in Grafana
# Query: rate(container_cpu_usage_seconds_total{pod=~"<service>.*"}[5m])
# Compare with CPU limit

# 2. If usage near limit, increase CPU allocation
kubectl edit deployment -n <namespace> <deployment-name>
# Increase resources.limits.cpu (e.g., from 500m to 1000m)

# 3. Monitor latency after change
# Should improve within 2-5 minutes

# 4. If latency persists, consider horizontal scaling
kubectl scale deployment/<deployment-name> -n <namespace> --replicas=<new-count>

# 5. Enable HPA for automatic scaling
kubectl autoscale deployment/<deployment-name> -n <namespace> \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

**If: External API slow**
```bash
# 1. Identify slow external API from Jaeger
# Look for HTTP client spans with long duration

# 2. Check if external API has status page
# Navigate to status page (e.g., status.openai.com)

# 3. Implement timeout and circuit breaker
# Prevent one slow API from blocking all requests
# Example circuit breaker config:
# - Failure threshold: 50%
# - Timeout: 5s
# - Cool-down period: 30s

# 4. Add caching for external API responses
# Cache responses for 5-15 minutes if data doesn't change frequently

# 5. Implement fallback mechanism
# Return cached/default data if external API is slow
# Example: Use stale cache data if API timeout

# 6. Contact external API provider
# Request status update or escalation
```

**If: N+1 query problem**
```bash
# 1. Identify N+1 pattern in Jaeger
# Multiple sequential database queries in a loop
# Example: 1 query to get list + N queries to get details

# 2. Check application code
# Look for loops that execute queries
# Example (bad):
# users = fetch_users()
# for user in users:
#     user.posts = fetch_posts(user.id)  # N queries!

# 3. Implement eager loading / batch fetching
# Fetch all related data in one query
# Example (good):
# users = fetch_users_with_posts()  # Single join query

# 4. Deploy fix and verify
# Check Jaeger - should see single query instead of N+1

# 5. Monitor latency improvement
# Should see significant reduction in P95/P99 latency
```

**If: Latency increased after deployment**
```bash
# 1. Verify timing correlation
kubectl rollout history deployment/<deployment-name> -n <namespace>

# 2. Check recent code changes
git log --oneline --since="2 hours ago"

# 3. Rollback deployment
kubectl rollout undo deployment/<deployment-name> -n <namespace>

# 4. Verify latency returns to normal
# Check Grafana - should improve within 5 minutes

# 5. Create incident ticket with details
# - Deployment that caused regression
# - Latency metrics before/after
# - Affected endpoints

# 6. Block deployment until fix is available
# Review code changes to identify performance regression
```

#### Escalation Criteria

**Escalate to Senior Engineer if**:
- Latency >2s (P95) for >15 minutes
- Root cause not identified within 20 minutes
- Rollback does not resolve issue

**Escalate to Database Admin if**:
- Database queries slow despite proper indexes
- Need to optimize database configuration
- Considering read replicas or sharding

**Escalate to Engineering Lead if**:
- Latency affecting multiple services
- Need architectural changes (caching layer, async processing)
- Customer complaints or revenue impact

---

### 6. CertificateExpiringInSevenDays

**Alert Definition**:
```yaml
alert: CertificateExpiringInSevenDays
expr: (certmanager_certificate_expiration_timestamp_seconds - time()) < 604800
for: 1h
severity: critical
```

**Impact**: If certificate expires, users will see TLS errors and cannot access services via HTTPS.

#### Investigation Steps

**Step 1: Identify expiring certificate**
```bash
# List all certificates
kubectl get certificate --all-namespaces

# Check expiring certificates
kubectl get certificate --all-namespaces -o json | \
  jq -r '.items[] | select(.status.notAfter != null) |
  [.metadata.namespace, .metadata.name, .status.notAfter] | @tsv'

# Example output:
# octollm-monitoring  grafana-tls-cert  2025-12-05T10:30:00Z
# octollm-prod        api-tls-cert      2025-12-12T14:20:00Z
```

**Step 2: Check certificate status**
```bash
kubectl describe certificate -n <namespace> <cert-name>

# Look for:
# Status: Ready
# Renewal Time: (should be set)
# Events: Check for renewal attempts
```

**Step 3: Check cert-manager logs**
```bash
# Get cert-manager controller pod
kubectl get pods -n cert-manager

# Check logs for renewal attempts
kubectl logs -n cert-manager <cert-manager-pod> | grep <cert-name>

# Look for errors:
# - "rate limit exceeded" (Let's Encrypt)
# - "challenge failed" (DNS/HTTP validation failed)
# - "unable to connect to ACME server"
```

**Step 4: Check ClusterIssuer status**
```bash
# List ClusterIssuers
kubectl get clusterissuer

# Check issuer details
kubectl describe clusterissuer letsencrypt-prod

# Look for:
# Status: Ready
# ACME account registered: True
```

**Step 5: Check DNS/Ingress for challenge**
```bash
# For DNS-01 challenge (wildcard certs)
# Verify DNS provider credentials are valid
kubectl get secret -n cert-manager <dns-provider-secret>

# For HTTP-01 challenge
# Verify ingress is accessible
curl -I https://<domain>/.well-known/acme-challenge/test
```

#### Remediation Actions

**If: Certificate not auto-renewing (cert-manager issue)**
```bash
# 1. Check cert-manager is running
kubectl get pods -n cert-manager

# 2. If pods are not running, check for issues
kubectl describe pods -n cert-manager <cert-manager-pod>

# 3. Restart cert-manager if needed
kubectl rollout restart deployment -n cert-manager cert-manager
kubectl rollout restart deployment -n cert-manager cert-manager-webhook
kubectl rollout restart deployment -n cert-manager cert-manager-cainjector

# 4. Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -n cert-manager -l app=cert-manager --timeout=2m

# 5. Trigger manual renewal
kubectl delete certificaterequest -n <namespace> $(kubectl get certificaterequest -n <namespace> -o name)

# 6. Check renewal progress
kubectl describe certificate -n <namespace> <cert-name>

# 7. Monitor events for successful renewal
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep -i certificate
```

**If: Let's Encrypt rate limit exceeded**
```bash
# 1. Check error message in cert-manager logs
kubectl logs -n cert-manager <cert-manager-pod> | grep "rate limit"

# Error example: "too many certificates already issued for: octollm.dev"

# 2. Let's Encrypt limits:
# - 50 certificates per registered domain per week
# - 5 duplicate certificates per week

# 3. Wait for rate limit to reset (1 week)
# No immediate fix - must wait

# 4. Temporary workaround: Use staging issuer
kubectl edit certificate -n <namespace> <cert-name>
# Change issuerRef.name: letsencrypt-prod → letsencrypt-staging

# 5. Staging cert will be issued (browsers will show warning)
# Acceptable for dev/staging, not for prod

# 6. For prod: Request rate limit increase from Let's Encrypt
# Email: limit-increases@letsencrypt.org
# Provide: domain, business justification, expected cert volume

# 7. Long-term: Reduce cert renewals
# Use wildcard certificates to cover multiple subdomains
# Increase cert lifetime (Let's Encrypt is 90 days, cannot change)
```

**If: DNS challenge failing (DNS-01)**
```bash
# 1. Check DNS provider credentials
kubectl get secret -n cert-manager <dns-provider-secret> -o yaml

# 2. Verify secret has correct keys
# For Google Cloud DNS:
# - key.json (service account key)
# For Cloudflare:
# - api-token

# 3. Test DNS provider access manually
# For Google Cloud DNS:
gcloud dns record-sets list --zone=<zone-name>

# For Cloudflare:
curl -X GET "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer <token>"

# 4. If credentials are invalid, update secret
kubectl delete secret -n cert-manager <dns-provider-secret>
kubectl create secret generic -n cert-manager <dns-provider-secret> \
  --from-file=key.json=<path-to-new-key>

# 5. Restart cert-manager to pick up new credentials
kubectl rollout restart deployment -n cert-manager cert-manager

# 6. Trigger certificate renewal
kubectl delete certificaterequest -n <namespace> $(kubectl get certificaterequest -n <namespace> -o name)

# 7. Check certificate status
kubectl describe certificate -n <namespace> <cert-name>
```

**If: HTTP challenge failing (HTTP-01)**
```bash
# 1. Check if ingress is accessible
curl -I https://<domain>/.well-known/acme-challenge/test

# 2. Verify ingress controller is running
kubectl get pods -n ingress-nginx  # or kube-system for GKE

# 3. Check if challenge path is reachable
kubectl get ingress -n <namespace>

# 4. Check ingress events
kubectl describe ingress -n <namespace> <ingress-name>

# 5. Verify DNS points to correct load balancer
nslookup <domain>
# Should resolve to ingress load balancer IP

# 6. Check firewall rules allow HTTP (port 80)
# Let's Encrypt requires HTTP for challenge, even for HTTPS certs
gcloud compute firewall-rules list --filter="name~'.*allow-http.*'"

# 7. If firewall blocks HTTP, create allow rule
gcloud compute firewall-rules create allow-http \
  --allow tcp:80 \
  --source-ranges 0.0.0.0/0

# 8. Retry certificate issuance
kubectl delete certificaterequest -n <namespace> $(kubectl get certificaterequest -n <namespace> -o name)
```

**If: Manual certificate renewal needed (last resort)**
```bash
# 1. Generate new certificate manually with certbot
certbot certonly --manual --preferred-challenges dns \
  -d <domain> -d *.<domain>

# 2. Update DNS TXT record as instructed by certbot
# Wait for DNS propagation (1-5 minutes)

# 3. Complete certbot challenge
# Certbot will save certificate to /etc/letsencrypt/live/<domain>/

# 4. Create Kubernetes secret with new certificate
kubectl create secret tls <cert-name> -n <namespace> \
  --cert=/etc/letsencrypt/live/<domain>/fullchain.pem \
  --key=/etc/letsencrypt/live/<domain>/privkey.pem

# 5. Update ingress to use new secret
kubectl edit ingress -n <namespace> <ingress-name>
# Verify spec.tls[].secretName matches new secret name

# 6. Verify HTTPS is working
curl -I https://<domain>

# 7. Fix cert-manager issue to prevent manual renewals in future
# This is a temporary workaround only!
```

#### Escalation Criteria

**Escalate to Senior Engineer if**:
- Certificate expires in <3 days and not renewing
- cert-manager issues persist after restart
- DNS provider integration broken

**Escalate to Engineering Lead if**:
- Certificate expires in <24 hours
- Multiple certificates failing to renew
- Need to switch certificate provider

**Escalate to VP Engineering + Legal if**:
- Production certificate expired (causing outage)
- Customer data exposure risk due to TLS issues
- Need to purchase commercial certificates (e.g., DigiCert)

---

## Warning Alert Procedures

### 7. HighNodeCPUUsage

**Alert Definition**:
```yaml
alert: HighNodeCPUUsage
expr: (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)) > 0.80
for: 10m
severity: warning
```

**Impact**: Node under high load. May affect performance. Pods may be throttled.

#### Investigation Steps

1. **Identify affected node**
```bash
kubectl top nodes
```

2. **Check pod CPU usage on the node**
```bash
kubectl top pods --all-namespaces --field-selector spec.nodeName=<node-name> --sort-by=cpu
```

3. **Check for CPU-intensive processes**
```bash
# Use metrics in Grafana
# Query: topk(10, rate(container_cpu_usage_seconds_total{node="<node-name>"}[5m]))
```

#### Remediation Actions

**Option 1: Scale application horizontally**
```bash
# Add more replicas to distribute load
kubectl scale deployment/<deployment-name> -n <namespace> --replicas=<new-count>

# Or enable HPA
kubectl autoscale deployment/<deployment-name> -n <namespace> \
  --cpu-percent=70 --min=2 --max=10
```

**Option 2: Increase node CPU limits**
```bash
# Edit deployment to increase CPU limits
kubectl edit deployment -n <namespace> <deployment-name>
# Increase resources.limits.cpu
```

**Option 3: Add more nodes to cluster**
```bash
# For GKE, resize node pool
gcloud container clusters resize <cluster-name> \
  --node-pool=<pool-name> \
  --num-nodes=<new-count> \
  --zone=<zone>
```

#### Escalation Criteria

- Escalate if CPU >90% for >30 minutes
- Escalate if performance degradation reported by users

---

### 8. HighNodeMemoryUsage

**Alert Definition**:
```yaml
alert: HighNodeMemoryUsage
expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.85
for: 10m
severity: warning
```

**Impact**: Node running out of memory. May trigger OOM kills.

#### Investigation Steps

1. **Identify affected node**
```bash
kubectl top nodes
```

2. **Check pod memory usage on the node**
```bash
kubectl top pods --all-namespaces --field-selector spec.nodeName=<node-name> --sort-by=memory
```

3. **Check for memory leaks**
```bash
# Use Grafana to view memory trends
# Query: container_memory_usage_bytes{node="<node-name>"}
# Look for steadily increasing memory over time
```

#### Remediation Actions

**Option 1: Restart memory-leaking pods**
```bash
kubectl delete pod -n <namespace> <pod-name>
# Or rollout restart
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

**Option 2: Increase memory limits**
```bash
kubectl edit deployment -n <namespace> <deployment-name>
# Increase resources.limits.memory
```

**Option 3: Scale horizontally**
```bash
kubectl scale deployment/<deployment-name> -n <namespace> --replicas=<new-count>
```

#### Escalation Criteria

- Escalate if memory >95% for >15 minutes
- Escalate if OOMKilled events detected

---

### 9. HighRequestLatency

**Alert Definition**:
```yaml
alert: HighRequestLatency
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
for: 10m
severity: warning
```

**Impact**: Slow responses. Users experiencing delays.

**See detailed procedure in Critical Alert #5 (HighLatency)** - same investigation and remediation steps apply.

---

### 10. PodOOMKilled

**Alert Definition**:
```yaml
alert: PodOOMKilled
expr: kube_pod_container_status_terminated_reason{reason="OOMKilled"} > 0
for: 1m
severity: warning
```

**Impact**: Container killed due to out-of-memory. Service may be unavailable briefly.

#### Investigation Steps

1. **Identify OOMKilled pod**
```bash
kubectl get pods --all-namespaces -o json | \
  jq -r '.items[] | select(.status.containerStatuses[]?.lastState.terminated.reason == "OOMKilled") |
  [.metadata.namespace, .metadata.name] | @tsv'
```

2. **Check memory limits**
```bash
kubectl get pod -n <namespace> <pod-name> -o jsonpath='{.spec.containers[0].resources}'
```

3. **Check memory usage before OOM**
```bash
# Query in Grafana:
# container_memory_usage_bytes{pod="<pod-name>"}
```

#### Remediation Actions

**Increase memory limits**
```bash
kubectl edit deployment -n <namespace> <deployment-name>
# Increase resources.limits.memory (e.g., 512Mi → 1Gi)
```

**Check for memory leaks**
```bash
# If memory increases steadily over time, likely a leak
# Enable heap profiling and investigate
```

#### Escalation Criteria

- Escalate if OOMKilled repeatedly (>3 times in 1 hour)
- Escalate if memory leak suspected

---

### 11. PersistentVolumeClaimPending

**Alert Definition**:
```yaml
alert: PersistentVolumeClaimPending
expr: kube_persistentvolumeclaim_status_phase{phase="Pending"} == 1
for: 5m
severity: warning
```

**Impact**: Pod cannot start due to unbound PVC. Service may be unavailable.

#### Investigation Steps

1. **Identify pending PVC**
```bash
kubectl get pvc --all-namespaces | grep Pending
```

2. **Check PVC details**
```bash
kubectl describe pvc -n <namespace> <pvc-name>
```

3. **Check storage class**
```bash
kubectl get storageclass
kubectl describe storageclass <storage-class-name>
```

#### Remediation Actions

**If: No storage class exists**
```bash
# Create storage class (example for GKE)
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/gce-pd
parameters:
  type: pd-ssd
EOF

# Update PVC to use storage class
kubectl edit pvc -n <namespace> <pvc-name>
# Set storageClassName: fast-ssd
```

**If: Storage quota exceeded**
```bash
# Check quota
kubectl get resourcequota -n <namespace>

# Increase quota if needed
kubectl edit resourcequota -n <namespace> <quota-name>
```

**If: Node affinity preventing binding**
```bash
# Check if PV has node affinity that doesn't match any node
kubectl get pv | grep Available
kubectl describe pv <pv-name>

# May need to delete PV and recreate without affinity
```

#### Escalation Criteria

- Escalate if PVC pending for >15 minutes
- Escalate if quota increase needed

---

### 12. DeploymentReplicasMismatch

**Alert Definition**:
```yaml
alert: DeploymentReplicasMismatch
expr: kube_deployment_spec_replicas != kube_deployment_status_replicas_available
for: 15m
severity: warning
```

**Impact**: Deployment not at desired replica count. May affect availability or capacity.

#### Investigation Steps

1. **Identify affected deployment**
```bash
kubectl get deployments --all-namespaces
# Look for deployments where READY != DESIRED
```

2. **Check pod status**
```bash
kubectl get pods -n <namespace> -l app=<deployment-name>
```

3. **Check for pod errors**
```bash
kubectl describe pod -n <namespace> <pod-name>
```

#### Remediation Actions

**If: Pods pending due to resources**
```bash
# Check pending reason
kubectl describe pod -n <namespace> <pod-name> | grep -A 5 Events

# If "Insufficient cpu" or "Insufficient memory":
# - Add more nodes, or
# - Reduce resource requests
```

**If: Image pull error**
```bash
# Fix image name or credentials
kubectl set image deployment/<deployment-name> <container>=<correct-image> -n <namespace>
```

**If: Pods crashing**
```bash
# See PodCrashLoopBackOff procedure (Critical Alert #1)
```

#### Escalation Criteria

- Escalate if mismatch persists for >30 minutes
- Escalate if related to resource capacity issues

---

### 13. LowCacheHitRate

**Alert Definition**:
```yaml
alert: LowCacheHitRate
expr: redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) < 0.50
for: 15m
severity: warning
```

**Impact**: Increased latency and load on database due to cache misses.

#### Investigation Steps

1. **Check cache hit rate in Grafana**
```bash
# Query: redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)
```

2. **Check cache size and memory**
```bash
kubectl exec -it -n <namespace> <redis-pod> -- redis-cli INFO memory
```

3. **Check cache eviction rate**
```bash
kubectl exec -it -n <namespace> <redis-pod> -- redis-cli INFO stats | grep evicted_keys
```

#### Remediation Actions

**If: Cache too small (frequent evictions)**
```bash
# Increase Redis memory
kubectl edit statefulset -n <namespace> redis
# Increase resources.limits.memory

# Restart Redis
kubectl delete pod -n <namespace> <redis-pod>
```

**If: Cache TTL too short**
```bash
# Increase TTL in application config
kubectl edit configmap -n <namespace> <service>-config
# Increase CACHE_TTL value

# Restart service
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

**If: Data access patterns changed**
```bash
# Implement cache warming
# Pre-populate cache with frequently accessed data

# Adjust cache strategy (e.g., cache-aside vs. write-through)
```

#### Escalation Criteria

- Escalate if hit rate <30% for >1 hour
- Escalate if causing user-facing latency issues

---

## Informational Alert Procedures

### 14. NewDeploymentDetected

**Alert Definition**:
```yaml
alert: NewDeploymentDetected
expr: changes(kube_deployment_status_observed_generation[5m]) > 0
severity: info
```

**Impact**: Informational. No immediate action required.

#### Actions

1. **Verify deployment in kubectl**
```bash
kubectl rollout status deployment/<deployment-name> -n <namespace>
```

2. **Monitor for related alerts** (errors, crashes, latency)
```bash
# Check Alertmanager for any new critical/warning alerts
```

3. **Document in change log** if significant deployment

---

### 15. HPAScaledUp / HPAScaledDown

**Alert Definition**:
```yaml
alert: HPAScaledUp
expr: changes(kube_horizontalpodautoscaler_status_current_replicas[5m]) > 0
severity: info
```

**Impact**: Informational. HPA adjusted replica count based on load.

#### Actions

1. **Verify scaling event in Grafana**
```bash
# Query: kube_horizontalpodautoscaler_status_current_replicas{hpa="<hpa-name>"}
```

2. **Check if scaling is expected** (e.g., during peak hours)

3. **If scaling too frequent**, adjust HPA thresholds:
```bash
kubectl edit hpa -n <namespace> <hpa-name>
# Adjust targetCPUUtilizationPercentage
```

---

### 16. ConfigMapChanged

**Alert Definition**:
```yaml
alert: ConfigMapChanged
expr: changes(kube_configmap_info[5m]) > 0
severity: info
```

**Impact**: Informational. ConfigMap updated.

#### Actions

1. **Identify changed ConfigMap**
```bash
kubectl get configmap --all-namespaces --sort-by=.metadata.creationTimestamp
```

2. **Verify change was intentional**

3. **Restart pods if needed** to pick up new config:
```bash
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

---

## Multi-Alert Scenarios

### Scenario 1: Multiple Pods Crashing + Node NotReady

**Symptoms**:
- Alert: PodCrashLoopBackOff (multiple pods)
- Alert: NodeNotReady (1 node)

**Root Cause**: Node failure causing all pods on that node to crash.

**Investigation**:
1. Identify which pods are on the failing node
2. Check node status (see NodeNotReady procedure)

**Remediation**:
1. Cordon and drain the failing node
2. Pods will be rescheduled to healthy nodes
3. Replace the failed node

---

### Scenario 2: High Error Rate + Database Connection Pool Exhausted

**Symptoms**:
- Alert: HighErrorRate (>10% 5xx errors)
- Alert: DatabaseConnectionPoolExhausted (>95% pool usage)

**Root Cause**: Connection pool exhaustion causing service errors.

**Investigation**:
1. Check if error rate corresponds to pool exhaustion timing
2. Check for long-running database queries

**Remediation**:
1. Restart service to release connections
2. Increase connection pool size
3. Optimize slow queries

---

### Scenario 3: High Latency + Low Cache Hit Rate + High Database Load

**Symptoms**:
- Alert: HighLatency (P95 >1s)
- Alert: LowCacheHitRate (<50%)
- Observation: High database CPU

**Root Cause**: Cache ineffectiveness causing excessive database load and slow queries.

**Investigation**:
1. Check cache hit rate timeline
2. Check database query volume
3. Identify cache misses by key pattern

**Remediation**:
1. Increase cache size
2. Increase cache TTL
3. Implement cache warming for common queries
4. Add database indexes for frequent queries

---

## Escalation Decision Trees

### Decision Tree 1: Service Outage

```
Service completely unavailable (100% error rate)?
├─ YES → CRITICAL - Page on-call engineer
│   ├─ Multiple services down?
│   │   ├─ YES → Page Engineering Lead + VP Eng
│   │   └─ NO → Continue troubleshooting
│   └─ Customer-reported on social media?
│       ├─ YES → Notify VP Eng + Customer Success
│       └─ NO → Continue troubleshooting
└─ NO → Check error rate
    ├─ >50% error rate?
    │   ├─ YES → Page on-call engineer
    │   └─ NO → Assign to on-call engineer (Slack)
    └─ <10% error rate?
        └─ YES → Create ticket, no immediate page
```

### Decision Tree 2: Performance Degradation

```
Users reporting slow performance?
├─ YES → Check latency metrics
│   ├─ P95 >2s?
│   │   ├─ YES → CRITICAL - Page on-call engineer
│   │   └─ NO → Assign to on-call engineer
│   └─ P95 >1s but <2s?
│       ├─ YES → WARNING - Notify on-call engineer (Slack)
│       └─ NO → Create ticket for investigation
└─ NO → Proactive monitoring
    └─ P95 >1s for >15m?
        ├─ YES → Investigate proactively
        └─ NO → Continue monitoring
```

### Decision Tree 3: Infrastructure Issue

```
Node or infrastructure alert?
├─ NodeNotReady?
│   ├─ Single node?
│   │   ├─ YES → Cordon, drain, replace
│   │   └─ NO → Multiple nodes - Page Engineering Lead
│   └─ >30% of nodes affected?
│       └─ YES → CRITICAL - Page VP Eng + GCP Support
└─ Disk/Memory pressure?
    ├─ Can be resolved with cleanup?
    │   ├─ YES → Clean up and monitor
    │   └─ NO → Page on-call engineer for node replacement
```

---

## Post-Incident Actions

### After Resolving Critical Alerts

1. **Document resolution** in incident tracker
   - Root cause
   - Actions taken
   - Time to resolution
   - Services affected

2. **Create post-incident review** (PIR) for critical incidents
   - Timeline of events
   - Impact assessment
   - Contributing factors
   - Action items to prevent recurrence

3. **Update runbooks** if new issue discovered
   - Add new troubleshooting steps
   - Update remediation procedures
   - Document lessons learned

4. **Implement preventive measures**
   - Add monitoring for early detection
   - Improve alerting thresholds
   - Automate remediation where possible

5. **Communicate to stakeholders**
   - Internal: Engineering team, leadership
   - External: Customers (if user-impacting)
   - Status page update

### Post-Incident Review Template

```markdown
# Post-Incident Review: <Incident Title>

**Date**: YYYY-MM-DD
**Severity**: Critical / Warning
**Duration**: X hours Y minutes
**Services Affected**: <list>

## Summary

<1-2 sentence summary of incident>

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 14:00 | Alert triggered: HighErrorRate |
| 14:05 | On-call engineer acknowledged |
| 14:10 | Root cause identified: database connection pool exhausted |
| 14:15 | Mitigation applied: restarted service |
| 14:20 | Incident resolved: error rate returned to normal |

## Root Cause

<Detailed explanation of what caused the incident>

## Impact

- **User Impact**: X% of requests resulted in errors
- **Revenue Impact**: $Y estimated lost revenue
- **Duration**: X hours Y minutes

## Resolution

<What was done to resolve the incident>

## Contributing Factors

1. Factor 1
2. Factor 2

## Action Items

1. [ ] Increase connection pool size (Owner: @engineer, Due: YYYY-MM-DD)
2. [ ] Add alert for connection pool usage (Owner: @engineer, Due: YYYY-MM-DD)
3. [ ] Update runbook with new procedure (Owner: @engineer, Due: YYYY-MM-DD)

## Lessons Learned

- What went well
- What could be improved
- What we learned
```

---

## Summary

This alert response procedures document provides detailed, step-by-step guidance for responding to all alerts in the OctoLLM monitoring system. Key points:

- **Critical alerts** require immediate action (acknowledge within 5 minutes, resolve within 1 hour)
- **Warning alerts** require timely action (acknowledge within 30 minutes, resolve within 4 hours)
- **Info alerts** are informational and require no immediate action

Each procedure includes:
- Alert definition and impact
- Investigation steps with commands
- Remediation actions with code examples
- Escalation criteria

**For all incidents**:
1. Follow the general response workflow (acknowledge → assess → investigate → remediate → document → close)
2. Use the escalation decision trees to determine when to involve senior engineers or leadership
3. Complete post-incident reviews for critical incidents
4. Update runbooks with lessons learned

**Related Documents**:
- Monitoring Runbook: `/home/parobek/Code/OctoLLM/docs/operations/monitoring-runbook.md`
- Deployment Guide: `/home/parobek/Code/OctoLLM/docs/deployment-guide.md`
- Backup and Restore: `/home/parobek/Code/OctoLLM/docs/operations/backup-restore.md`
