# Phase 6: Production Readiness

**Status**: Not Started
**Duration**: 8-10 weeks
**Team Size**: 4-5 engineers (1 SRE, 1 ML engineer, 1 Python, 1 Rust, 1 DevOps)
**Prerequisites**: Phase 5 complete (security hardening)
**Start Date**: TBD
**Target Completion**: TBD

---

## Overview

Phase 6 prepares OctoLLM for production deployment at scale with autoscaling, cost optimization, compliance implementation, advanced performance tuning, and multi-tenancy support.

**Key Deliverables**:
1. Autoscaling - HorizontalPodAutoscaler with custom metrics, VPA, cluster autoscaling
2. Cost Optimization - Right-sizing, spot instances, reserved capacity, LLM cost reduction
3. Compliance - SOC 2 Type II, ISO 27001, GDPR, CCPA, HIPAA readiness
4. Advanced Performance - Rust rewrites, model fine-tuning, advanced caching, speculative execution
5. Multi-Tenancy - Tenant isolation, authentication, data isolation, usage-based billing

**Success Criteria**:
- ✅ Autoscaling handles 10x traffic spikes without degradation
- ✅ Cost per task reduced by 50% vs Phase 5
- ✅ SOC 2 Type II audit passed
- ✅ P99 latency <10s for critical tasks (vs <30s in Phase 1)
- ✅ Multi-tenant isolation tested and verified
- ✅ Production SLA: 99.9% uptime, <15s P95 latency
- ✅ Zero customer-impacting security incidents in first 90 days

**Reference**: `docs/doc_phases/PHASE-6-COMPLETE-SPECIFICATIONS.md` (14,000+ lines)

---

## Sprint 6.1: Autoscaling [Week 33-34]

**Duration**: 2 weeks
**Team**: 2 engineers (1 SRE, 1 DevOps)
**Prerequisites**: Phase 3 complete (Kubernetes deployment)
**Priority**: HIGH

### Sprint Goals

- Implement HorizontalPodAutoscaler (HPA) for all services
- Configure VerticalPodAutoscaler (VPA) for right-sizing
- Set up cluster autoscaling for node pools
- Create custom metrics for LLM workload scaling
- Test autoscaling under load
- Document scaling policies and runbooks

### Architecture Decisions

**Scaling Strategy**: Hybrid approach (HPA for replicas, VPA for resource requests, cluster autoscaler for nodes)
**Metrics**: CPU, memory, custom (queue depth, task latency, LLM token rate)
**Target Utilization**: 70% CPU/memory (allows headroom for spikes)
**Scale-Up Policy**: Aggressive (30s stabilization)
**Scale-Down Policy**: Conservative (5 minutes stabilization to prevent flapping)
**Min/Max Replicas**: Service-dependent (orchestrator: 3-20, arms: 2-10)

### Tasks

#### HorizontalPodAutoscaler Setup (10 hours)

- [ ] **Install Metrics Server** (1 hour)
  - Deploy metrics-server in kube-system namespace
  - Verify metric collection
  - Code example:
    ```bash
    # Install metrics-server
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

    # Verify metrics available
    kubectl top nodes
    kubectl top pods -n octollm
    ```
  - Files to create: `k8s/monitoring/metrics-server.yaml`

- [ ] **Create HPA for Orchestrator** (2 hours)
  - Scale based on CPU and custom metrics (task queue depth)
  - Aggressive scale-up, conservative scale-down
  - Code example:
    ```yaml
    # k8s/autoscaling/orchestrator-hpa.yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: orchestrator-hpa
      namespace: octollm
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: orchestrator
      minReplicas: 3
      maxReplicas: 20
      metrics:
      # CPU-based scaling
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70

      # Memory-based scaling
      - type: Resource
        resource:
          name: memory
          target:
            type: Utilization
            averageUtilization: 75

      # Custom metric: task queue depth
      - type: Pods
        pods:
          metric:
            name: task_queue_depth
          target:
            type: AverageValue
            averageValue: "10"  # Scale up if >10 tasks per pod

      behavior:
        scaleUp:
          stabilizationWindowSeconds: 30
          policies:
          - type: Percent
            value: 100  # Double replicas
            periodSeconds: 30
          - type: Pods
            value: 4  # Or add 4 pods
            periodSeconds: 30
          selectPolicy: Max  # Choose most aggressive

        scaleDown:
          stabilizationWindowSeconds: 300  # 5 minutes
          policies:
          - type: Percent
            value: 50  # Remove 50% of pods
            periodSeconds: 60
          - type: Pods
            value: 2  # Or remove 2 pods
            periodSeconds: 60
          selectPolicy: Min  # Choose most conservative
    ```
  - Files to create: `k8s/autoscaling/orchestrator-hpa.yaml`

- [ ] **Create HPAs for All Arms** (4 hours)
  - Planner Arm: Scale on CPU + task decomposition requests
  - Executor Arm: Scale on CPU + active executions
  - Coder Arm: Scale on CPU + code generation requests
  - Judge Arm: Scale on CPU + validation requests
  - Safety Guardian Arm: Scale on CPU + PII detection requests
  - Retriever Arm: Scale on CPU + search requests
  - Code example (Executor Arm):
    ```yaml
    # k8s/autoscaling/executor-arm-hpa.yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: executor-arm-hpa
      namespace: octollm
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: executor-arm
      minReplicas: 2
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70

      - type: Pods
        pods:
          metric:
            name: active_executions
          target:
            type: AverageValue
            averageValue: "3"  # Max 3 concurrent executions per pod

      behavior:
        scaleUp:
          stabilizationWindowSeconds: 30
          policies:
          - type: Percent
            value: 100
            periodSeconds: 30
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Pods
            value: 1
            periodSeconds: 60
    ```
  - Files to create: `k8s/autoscaling/executor-arm-hpa.yaml`, similar for other arms

- [ ] **Implement Custom Metrics Exporter** (3 hours)
  - Expose application metrics for HPA (task queue depth, active executions)
  - Use Prometheus adapter
  - Code example:
    ```python
    # orchestrator/metrics/custom_metrics.py
    from prometheus_client import Gauge
    from typing import Dict, Any

    # Define custom metrics for autoscaling
    task_queue_depth_gauge = Gauge(
        'task_queue_depth',
        'Number of tasks waiting in queue per pod',
        ['pod_name']
    )

    active_tasks_gauge = Gauge(
        'active_tasks',
        'Number of tasks currently being processed',
        ['pod_name']
    )

    class CustomMetricsExporter:
        """Export custom metrics for HPA."""

        def __init__(self, pod_name: str):
            self.pod_name = pod_name

        def update_queue_depth(self, depth: int):
            """Update task queue depth metric."""
            task_queue_depth_gauge.labels(pod_name=self.pod_name).set(depth)

        def update_active_tasks(self, count: int):
            """Update active task count metric."""
            active_tasks_gauge.labels(pod_name=self.pod_name).set(count)
    ```

    ```yaml
    # k8s/monitoring/prometheus-adapter-config.yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: prometheus-adapter-config
      namespace: monitoring
    data:
      config.yaml: |
        rules:
        - seriesQuery: 'task_queue_depth{namespace="octollm"}'
          resources:
            overrides:
              namespace: {resource: "namespace"}
              pod_name: {resource: "pod"}
          name:
            matches: "^(.*)$"
            as: "task_queue_depth"
          metricsQuery: 'avg_over_time(task_queue_depth{<<.LabelMatchers>>}[1m])'

        - seriesQuery: 'active_executions{namespace="octollm"}'
          resources:
            overrides:
              namespace: {resource: "namespace"}
              pod_name: {resource: "pod"}
          name:
            matches: "^(.*)$"
            as: "active_executions"
          metricsQuery: 'avg_over_time(active_executions{<<.LabelMatchers>>}[1m])'
    ```
  - Files to create: `orchestrator/metrics/custom_metrics.py`, `k8s/monitoring/prometheus-adapter-config.yaml`

#### VerticalPodAutoscaler Setup (4 hours)

- [ ] **Install VPA** (1 hour)
  - Deploy VPA components (recommender, updater, admission controller)
  - Code example:
    ```bash
    # Install VPA
    git clone https://github.com/kubernetes/autoscaler.git
    cd autoscaler/vertical-pod-autoscaler
    ./hack/vpa-up.sh
    ```
  - Files to create: `k8s/autoscaling/vpa-install.sh`

- [ ] **Create VPA Policies** (2 hours)
  - Recommendation-only mode for initial analysis
  - Auto mode for non-critical services
  - Code example:
    ```yaml
    # k8s/autoscaling/orchestrator-vpa.yaml
    apiVersion: autoscaling.k8s.io/v1
    kind: VerticalPodAutoscaler
    metadata:
      name: orchestrator-vpa
      namespace: octollm
    spec:
      targetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: orchestrator
      updatePolicy:
        updateMode: "Auto"  # Auto, Recreate, Initial, or Off
      resourcePolicy:
        containerPolicies:
        - containerName: orchestrator
          minAllowed:
            cpu: 500m
            memory: 1Gi
          maxAllowed:
            cpu: 8000m
            memory: 16Gi
          controlledResources:
          - cpu
          - memory
    ```
  - Files to create: `k8s/autoscaling/orchestrator-vpa.yaml`

- [ ] **Monitor VPA Recommendations** (1 hour)
  - Analyze recommendations for all services
  - Adjust resource requests based on data
  - Code example:
    ```bash
    # scripts/analyze_vpa_recommendations.sh
    #!/bin/bash
    set -e

    echo "=== VPA Recommendations Analysis ==="

    for deployment in orchestrator planner-arm executor-arm coder-arm judge-arm safety-guardian-arm retriever-arm; do
        echo "\n--- $deployment ---"

        # Get VPA recommendations
        kubectl get vpa ${deployment}-vpa -n octollm -o json | \
            jq -r '.status.recommendation.containerRecommendations[] |
                   "Container: \(.containerName)\n  Current CPU: \(.target.cpu)\n  Recommended CPU: \(.upperBound.cpu)\n  Current Memory: \(.target.memory)\n  Recommended Memory: \(.upperBound.memory)"'
    done
    ```
  - Files to create: `scripts/analyze_vpa_recommendations.sh`

#### Cluster Autoscaler Setup (4 hours)

- [ ] **Configure Cluster Autoscaler** (2 hours)
  - Set up node pools with min/max sizes
  - Configure autoscaler for each cloud provider
  - Code example (GKE):
    ```yaml
    # k8s/autoscaling/cluster-autoscaler-gke.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: cluster-autoscaler
      namespace: kube-system
    spec:
      replicas: 1
      template:
        spec:
          serviceAccountName: cluster-autoscaler
          containers:
          - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.28.0
            name: cluster-autoscaler
            command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=gce
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=mig:namePrefix=octollm-node-pool
            - --balance-similar-node-groups
            - --skip-nodes-with-system-pods=false
            - --scale-down-delay-after-add=5m
            - --scale-down-unneeded-time=5m
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRole
    metadata:
      name: cluster-autoscaler
    rules:
    - apiGroups: [""]
      resources: ["events", "endpoints"]
      verbs: ["create", "patch"]
    - apiGroups: [""]
      resources: ["pods/eviction"]
      verbs: ["create"]
    - apiGroups: [""]
      resources: ["pods/status"]
      verbs: ["update"]
    - apiGroups: [""]
      resources: ["endpoints"]
      resourceNames: ["cluster-autoscaler"]
      verbs: ["get", "update"]
    - apiGroups: [""]
      resources: ["nodes"]
      verbs: ["watch", "list", "get", "update"]
    - apiGroups: [""]
      resources: ["pods", "services", "replicationcontrollers", "persistentvolumeclaims", "persistentvolumes"]
      verbs: ["watch", "list", "get"]
    - apiGroups: ["extensions"]
      resources: ["replicasets", "daemonsets"]
      verbs: ["watch", "list", "get"]
    - apiGroups: ["policy"]
      resources: ["poddisruptionbudgets"]
      verbs: ["watch", "list"]
    - apiGroups: ["apps"]
      resources: ["statefulsets", "replicasets", "daemonsets"]
      verbs: ["watch", "list", "get"]
    - apiGroups: ["storage.k8s.io"]
      resources: ["storageclasses", "csinodes", "csidrivers", "csistoragecapacities"]
      verbs: ["watch", "list", "get"]
    - apiGroups: ["batch", "extensions"]
      resources: ["jobs"]
      verbs: ["get", "list", "watch", "patch"]
    - apiGroups: ["coordination.k8s.io"]
      resources: ["leases"]
      verbs: ["create"]
    - apiGroups: ["coordination.k8s.io"]
      resourceNames: ["cluster-autoscaler"]
      resources: ["leases"]
      verbs: ["get", "update"]
    ```
  - Files to create: `k8s/autoscaling/cluster-autoscaler-gke.yaml`

- [ ] **Create Node Pools with Labels** (1 hour)
  - Separate pools for CPU-intensive and memory-intensive workloads
  - Use node affinity to schedule arms appropriately
  - Code example:
    ```yaml
    # terraform/gke-node-pools.tf
    resource "google_container_node_pool" "cpu_optimized" {
      name       = "cpu-optimized-pool"
      cluster    = google_container_cluster.octollm.name
      node_count = 2

      autoscaling {
        min_node_count = 2
        max_node_count = 20
      }

      node_config {
        machine_type = "n2-highcpu-16"  # 16 vCPU, 16 GB RAM

        labels = {
          workload-type = "cpu-optimized"
        }

        taint {
          key    = "workload-type"
          value  = "cpu-optimized"
          effect = "NO_SCHEDULE"
        }
      }
    }

    resource "google_container_node_pool" "memory_optimized" {
      name       = "memory-optimized-pool"
      cluster    = google_container_cluster.octollm.name
      node_count = 2

      autoscaling {
        min_node_count = 2
        max_node_count = 10
      }

      node_config {
        machine_type = "n2-highmem-8"  # 8 vCPU, 64 GB RAM

        labels = {
          workload-type = "memory-optimized"
        }

        taint {
          key    = "workload-type"
          value  = "memory-optimized"
          effect = "NO_SCHEDULE"
        }
      }
    }
    ```
  - Files to create: `terraform/gke-node-pools.tf`

- [ ] **Test Cluster Autoscaling** (1 hour)
  - Simulate load spike
  - Verify nodes added automatically
  - Verify nodes removed after scale-down
  - Files to create: `scripts/test_cluster_autoscaling.sh`

#### Load Testing (4 hours)

- [ ] **Create Load Test Suite** (2 hours)
  - Use k6 or Locust for load generation
  - Simulate realistic traffic patterns
  - Code example:
    ```javascript
    // tests/load/autoscaling_test.js
    import http from 'k6/http';
    import { check, sleep } from 'k6';
    import { Rate } from 'k6/metrics';

    const failureRate = new Rate('failed_requests');

    export let options = {
      stages: [
        { duration: '2m', target: 10 },   // Ramp up to 10 users
        { duration: '5m', target: 10 },   // Steady state
        { duration: '2m', target: 50 },   // Spike to 50 users
        { duration: '5m', target: 50 },   // Hold spike
        { duration: '2m', target: 100 },  // Extreme spike
        { duration: '5m', target: 100 },  // Hold extreme spike
        { duration: '5m', target: 0 },    // Ramp down
      ],
      thresholds: {
        'failed_requests': ['rate<0.01'],  // <1% failure rate
        'http_req_duration': ['p(95)<15000'],  // P95 latency <15s
      },
    };

    const BASE_URL = 'http://octollm-gateway.octollm.svc.cluster.local';

    export default function () {
      // Submit a task
      const payload = JSON.stringify({
        goal: 'Analyze this code for security vulnerabilities',
        constraints: {
          max_cost_tokens: 10000,
          max_time_seconds: 300
        },
        context: {
          code: 'def login(username, password):\n    query = f"SELECT * FROM users WHERE username=\'{username}\' AND password=\'{password}\'"'
        }
      });

      const params = {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token-123'
        },
      };

      const response = http.post(`${BASE_URL}/tasks`, payload, params);

      check(response, {
        'status is 201': (r) => r.status === 201,
        'has task_id': (r) => r.json('task_id') !== undefined,
      }) || failureRate.add(1);

      sleep(1);
    }
    ```
  - Files to create: `tests/load/autoscaling_test.js`

- [ ] **Run Load Tests** (2 hours)
  - Execute load tests against staging environment
  - Monitor autoscaling behavior
  - Verify SLA compliance (99.9% uptime, <15s P95 latency)
  - Generate load test report
  - Code example:
    ```bash
    # scripts/run_load_test.sh
    #!/bin/bash
    set -e

    echo "Starting autoscaling load test..."

    # Run k6 load test
    k6 run --out json=load_test_results.json tests/load/autoscaling_test.js

    # Analyze results
    python scripts/analyze_load_test.py load_test_results.json

    # Check HPA events
    echo "\n=== HPA Events ==="
    kubectl get events -n octollm --field-selector involvedObject.kind=HorizontalPodAutoscaler

    # Check pod scaling timeline
    echo "\n=== Pod Count Timeline ==="
    kubectl get pods -n octollm -l app=orchestrator --watch

    echo "Load test complete. Review load_test_results.json for detailed metrics."
    ```
  - Files to create: `scripts/run_load_test.sh`, `scripts/analyze_load_test.py`

### Testing Requirements

#### Unit Tests
- [ ] HPA configuration validation (5 test cases)
- [ ] VPA policy validation (5 test cases)
- [ ] Custom metrics exporter (10 test cases)

#### Integration Tests
- [ ] HPA scaling behavior (scale up, scale down, flapping prevention)
- [ ] VPA resource adjustment
- [ ] Cluster autoscaler node provisioning
- [ ] End-to-end autoscaling under load

#### Performance Tests
- [ ] Load test: 10x traffic spike (verify autoscaling handles without degradation)
- [ ] Stress test: 100x traffic spike (verify graceful degradation)
- [ ] Soak test: 24-hour sustained load (verify no memory leaks or resource drift)

### Documentation Deliverables

- [ ] Autoscaling architecture diagram
- [ ] HPA configuration guide
- [ ] VPA tuning guide
- [ ] Cluster autoscaler runbook
- [ ] Load testing procedures
- [ ] Troubleshooting guide (scaling issues)

### Success Criteria

- [ ] HPA scales services within 60 seconds of load increase
- [ ] VPA recommendations reduce resource waste by >30%
- [ ] Cluster autoscaler provisions nodes within 5 minutes
- [ ] Load test passes with <1% failure rate and P95 latency <15s
- [ ] Cost per task unchanged despite autoscaling overhead

### Common Pitfalls

1. **HPA Flapping**: Too aggressive scale-down causes constant scaling up/down—use longer stabilization windows
2. **VPA Disruption**: Auto mode restarts pods—use recommendation mode for critical services
3. **Node Affinity Conflicts**: Pods can't schedule if no matching nodes—ensure default node pool
4. **Custom Metrics Lag**: Prometheus scrape interval causes scaling delays—reduce to 15s for autoscaling metrics
5. **Resource Limits**: HPA can't scale if pods hit resource limits—ensure limits > requests

### Estimated Effort

- Development: 22 hours
- Testing: 6 hours
- Documentation: 3 hours
- **Total**: 31 hours (~2 weeks for 2 engineers)

### Dependencies

- **Prerequisites**: Phase 3 complete (Kubernetes deployment, monitoring stack)
- **Blocking**: None
- **Blocked By**: None

---

## Sprint 6.2: Cost Optimization [Week 35-36]

**Duration**: 2 weeks
**Team**: 3 engineers (1 SRE, 1 ML engineer, 1 Python)
**Prerequisites**: Sprint 6.1 complete (autoscaling)
**Priority**: HIGH

### Sprint Goals

- Right-size all services based on actual usage
- Implement spot/preemptible instances for non-critical workloads
- Purchase reserved capacity for baseline load
- Optimize LLM costs (prompt caching, smaller models, fine-tuning)
- Implement request batching and deduplication
- Reduce cost per task by 50% vs Phase 5

### Architecture Decisions

**Compute**: Mix of on-demand (20%), spot instances (60%), reserved capacity (20%)
**LLM Strategy**: Use cheapest model per task type (GPT-3.5 for simple, GPT-4 for complex)
**Caching**: Aggressive prompt caching with semantic similarity matching
**Batching**: Batch similar requests to reduce LLM API overhead
**Fine-Tuning**: Fine-tune smaller models (Mistral 7B) to replace GPT-3.5 for common patterns

### Tasks

#### Right-Sizing (8 hours)

- [ ] **Analyze Resource Usage** (3 hours)
  - Use VPA recommendations and Prometheus metrics
  - Identify over-provisioned services
  - Code example:
    ```python
    # scripts/analyze_resource_usage.py
    import requests
    from datetime import datetime, timedelta
    from typing import Dict, List, Any

    class ResourceAnalyzer:
        """Analyze resource usage and identify optimization opportunities."""

        def __init__(self, prometheus_url: str):
            self.prometheus_url = prometheus_url

        def analyze_service(
            self,
            service_name: str,
            days_lookback: int = 30
        ) -> Dict[str, Any]:
            """Analyze resource usage for a service."""

            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_lookback)

            # Query CPU usage
            cpu_query = f'''
                avg_over_time(
                    rate(container_cpu_usage_seconds_total{{
                        namespace="octollm",
                        pod=~"{service_name}-.*"
                    }}[5m])[{days_lookback}d:5m]
                )
            '''

            cpu_usage = self._query_prometheus(cpu_query)

            # Query memory usage
            memory_query = f'''
                avg_over_time(
                    container_memory_working_set_bytes{{
                        namespace="octollm",
                        pod=~"{service_name}-.*"
                    }}[{days_lookback}d:5m]
                )
            '''

            memory_usage = self._query_prometheus(memory_query)

            # Get current resource requests
            current_requests = self._get_current_requests(service_name)

            # Calculate waste
            cpu_waste_percent = (
                (current_requests['cpu'] - cpu_usage['p95']) /
                current_requests['cpu'] * 100
            )

            memory_waste_percent = (
                (current_requests['memory'] - memory_usage['p95']) /
                current_requests['memory'] * 100
            )

            return {
                'service': service_name,
                'current_cpu_request': current_requests['cpu'],
                'p95_cpu_usage': cpu_usage['p95'],
                'cpu_waste_percent': cpu_waste_percent,
                'current_memory_request': current_requests['memory'],
                'p95_memory_usage': memory_usage['p95'],
                'memory_waste_percent': memory_waste_percent,
                'recommendation': self._generate_recommendation(
                    current_requests,
                    cpu_usage,
                    memory_usage
                )
            }

        def _query_prometheus(self, query: str) -> Dict[str, float]:
            """Query Prometheus and return percentile statistics."""
            # Implementation: Call Prometheus API, calculate percentiles
            pass

        def _get_current_requests(self, service_name: str) -> Dict[str, float]:
            """Get current resource requests from Kubernetes."""
            # Implementation: Call Kubernetes API
            pass

        def _generate_recommendation(
            self,
            current: Dict[str, float],
            cpu_usage: Dict[str, float],
            memory_usage: Dict[str, float]
        ) -> str:
            """Generate right-sizing recommendation."""

            # Add 20% buffer to P95 usage for headroom
            recommended_cpu = cpu_usage['p95'] * 1.2
            recommended_memory = memory_usage['p95'] * 1.2

            if recommended_cpu < current['cpu'] * 0.8:
                return f"Reduce CPU request to {recommended_cpu:.2f} cores"
            elif recommended_cpu > current['cpu'] * 1.2:
                return f"Increase CPU request to {recommended_cpu:.2f} cores"

            if recommended_memory < current['memory'] * 0.8:
                return f"Reduce memory request to {recommended_memory / 1e9:.2f} GB"
            elif recommended_memory > current['memory'] * 1.2:
                return f"Increase memory request to {recommended_memory / 1e9:.2f} GB"

            return "Current sizing is appropriate"
    ```
  - Files to create: `scripts/analyze_resource_usage.py`

- [ ] **Apply Right-Sizing** (2 hours)
  - Update resource requests/limits for all services
  - Deploy changes incrementally
  - Monitor for performance regressions
  - Files to update: All deployment YAML files

- [ ] **Calculate Cost Savings** (1 hour)
  - Compare costs before/after right-sizing
  - Generate cost savings report
  - Files to create: `docs/cost-optimization/right-sizing-report.md`

- [ ] **Set Up Cost Monitoring Dashboard** (2 hours)
  - Grafana dashboard for cost tracking
  - Alert on cost anomalies
  - Code example:
    ```json
    {
      "dashboard": {
        "title": "OctoLLM Cost Monitoring",
        "panels": [
          {
            "title": "Total Monthly Cost",
            "type": "graph",
            "targets": [
              {
                "expr": "sum(kube_pod_container_resource_requests{namespace='octollm'} * on(node) group_left() node_cost_hourly) * 730"
              }
            ]
          },
          {
            "title": "Cost by Service",
            "type": "piechart",
            "targets": [
              {
                "expr": "sum by (pod) (kube_pod_container_resource_requests{namespace='octollm'} * on(node) group_left() node_cost_hourly) * 730"
              }
            ]
          },
          {
            "title": "LLM API Costs",
            "type": "graph",
            "targets": [
              {
                "expr": "sum(llm_cost_usd_total)"
              }
            ]
          }
        ]
      }
    }
    ```
  - Files to create: `k8s/monitoring/grafana-dashboards/cost-monitoring.json`

#### Spot Instances (6 hours)

- [ ] **Create Spot Instance Node Pool** (2 hours)
  - Configure with appropriate labels and taints
  - Set up fallback to on-demand if spot unavailable
  - Code example:
    ```yaml
    # terraform/gke-spot-node-pool.tf
    resource "google_container_node_pool" "spot_pool" {
      name       = "spot-pool"
      cluster    = google_container_cluster.octollm.name
      node_count = 5

      autoscaling {
        min_node_count = 3
        max_node_count = 50
      }

      node_config {
        machine_type = "n2-standard-8"
        spot         = true  # Preemptible/spot instance

        labels = {
          workload-type = "spot"
        }

        taint {
          key    = "workload-type"
          value  = "spot"
          effect = "NO_SCHEDULE"
        }

        metadata = {
          disable-legacy-endpoints = "true"
        }
      }
    }
    ```
  - Files to create: `terraform/gke-spot-node-pool.tf`

- [ ] **Configure Services for Spot Tolerance** (3 hours)
  - Add node affinity to prefer spot instances
  - Implement graceful shutdown for preemption
  - Add PodDisruptionBudgets to ensure availability
  - Code example:
    ```yaml
    # k8s/arms/executor-deployment.yaml (updated for spot)
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: executor-arm
      namespace: octollm
    spec:
      replicas: 5
      template:
        spec:
          # Prefer spot instances, fallback to on-demand
          affinity:
            nodeAffinity:
              preferredDuringSchedulingIgnoredDuringExecution:
              - weight: 100
                preference:
                  matchExpressions:
                  - key: workload-type
                    operator: In
                    values:
                    - spot

          tolerations:
          - key: workload-type
            operator: Equal
            value: spot
            effect: NoSchedule

          # Graceful shutdown for preemption
          terminationGracePeriodSeconds: 60

          containers:
          - name: executor-arm
            lifecycle:
              preStop:
                exec:
                  command: ["/bin/sh", "-c", "sleep 30"]  # Drain connections
    ---
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: executor-arm-pdb
      namespace: octollm
    spec:
      minAvailable: 2  # Ensure at least 2 replicas always available
      selector:
        matchLabels:
          app: executor-arm
    ```
  - Files to update: All arm deployment YAML files

- [ ] **Test Spot Instance Preemption** (1 hour)
  - Simulate preemption events
  - Verify graceful failover
  - Files to create: `scripts/test_spot_preemption.sh`

#### LLM Cost Optimization (10 hours)

- [ ] **Implement Prompt Caching** (4 hours)
  - Cache LLM responses with semantic similarity matching
  - Use vector embeddings to find similar prompts
  - Code example:
    ```python
    # orchestrator/llm/cached_client.py
    from openai import AsyncOpenAI
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer
    from typing import Dict, Any, Optional, List
    import hashlib
    import json

    class CachedLLMClient:
        """LLM client with semantic caching."""

        def __init__(
            self,
            openai_client: AsyncOpenAI,
            qdrant_client: QdrantClient,
            embedding_model: SentenceTransformer,
            similarity_threshold: float = 0.95,
            collection_name: str = "llm_cache"
        ):
            self.openai = openai_client
            self.qdrant = qdrant_client
            self.embedding_model = embedding_model
            self.similarity_threshold = similarity_threshold
            self.collection_name = collection_name

            # Create collection if not exists
            self._init_collection()

        def _init_collection(self):
            """Initialize Qdrant collection for cache."""
            from qdrant_client.models import Distance, VectorParams

            try:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 embedding size
                        distance=Distance.COSINE
                    )
                )
            except Exception:
                pass  # Collection already exists

        async def chat_completion(
            self,
            messages: List[Dict[str, str]],
            model: str = "gpt-4-turbo-preview",
            temperature: float = 0.0,
            **kwargs
        ) -> Dict[str, Any]:
            """Create chat completion with semantic caching."""

            # Create cache key from messages
            prompt = self._messages_to_text(messages)
            cache_key = self._create_cache_key(prompt, model, temperature)

            # Check exact match cache first (fast)
            exact_match = await self._check_exact_cache(cache_key)
            if exact_match:
                return exact_match

            # Check semantic similarity cache (slower)
            if temperature == 0.0:  # Only use semantic cache for deterministic requests
                semantic_match = await self._check_semantic_cache(prompt, model)
                if semantic_match:
                    return semantic_match

            # Cache miss - call LLM
            response = await self.openai.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                **kwargs
            )

            # Store in cache
            await self._store_in_cache(cache_key, prompt, model, response)

            return response.model_dump()

        def _messages_to_text(self, messages: List[Dict[str, str]]) -> str:
            """Convert messages to single text for embedding."""
            return "\n".join(f"{m['role']}: {m['content']}" for m in messages)

        def _create_cache_key(
            self,
            prompt: str,
            model: str,
            temperature: float
        ) -> str:
            """Create deterministic cache key."""
            key_input = f"{prompt}|{model}|{temperature}"
            return hashlib.sha256(key_input.encode()).hexdigest()

        async def _check_exact_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
            """Check Redis for exact cache hit."""
            # Implementation: Query Redis
            pass

        async def _check_semantic_cache(
            self,
            prompt: str,
            model: str
        ) -> Optional[Dict[str, Any]]:
            """Check Qdrant for semantically similar cached responses."""

            # Generate embedding
            embedding = self.embedding_model.encode(prompt).tolist()

            # Search for similar prompts
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=1,
                score_threshold=self.similarity_threshold,
                query_filter={
                    "must": [
                        {"key": "model", "match": {"value": model}}
                    ]
                }
            )

            if results and results[0].score >= self.similarity_threshold:
                # Cache hit
                cached_response = results[0].payload["response"]
                return json.loads(cached_response)

            return None

        async def _store_in_cache(
            self,
            cache_key: str,
            prompt: str,
            model: str,
            response: Any
        ):
            """Store response in both exact and semantic caches."""

            # Store in Redis (exact match)
            # Implementation: Store in Redis with TTL

            # Store in Qdrant (semantic similarity)
            embedding = self.embedding_model.encode(prompt).tolist()

            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    {
                        "id": cache_key,
                        "vector": embedding,
                        "payload": {
                            "prompt": prompt,
                            "model": model,
                            "response": json.dumps(response.model_dump()),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                ]
            )
    ```
  - Files to create: `orchestrator/llm/cached_client.py`

- [ ] **Implement Model Selection Strategy** (3 hours)
  - Route to cheapest model capable of solving task
  - Use complexity classifier to determine required model
  - Code example:
    ```python
    # orchestrator/llm/model_selector.py
    from typing import Dict, Any, List
    import re

    class ModelSelector:
        """Select cheapest LLM model for a given task."""

        # Cost per 1M tokens (input/output)
        MODEL_COSTS = {
            "gpt-4-turbo-preview": (10.00, 30.00),
            "gpt-4": (30.00, 60.00),
            "gpt-3.5-turbo": (0.50, 1.50),
            "mistral-7b-instruct": (0.20, 0.20),  # Self-hosted
        }

        # Model capabilities
        MODEL_CAPABILITIES = {
            "gpt-4-turbo-preview": {"reasoning": 10, "coding": 9, "knowledge": 10},
            "gpt-4": {"reasoning": 10, "coding": 10, "knowledge": 10},
            "gpt-3.5-turbo": {"reasoning": 7, "coding": 7, "knowledge": 8},
            "mistral-7b-instruct": {"reasoning": 6, "coding": 6, "knowledge": 6},
        }

        def select_model(
            self,
            task_description: str,
            required_capability: str = "reasoning",
            min_capability_score: int = 7
        ) -> str:
            """Select cheapest model meeting requirements."""

            # Determine task complexity
            complexity = self._assess_complexity(task_description)

            # Filter models by capability
            suitable_models = [
                model for model, capabilities in self.MODEL_CAPABILITIES.items()
                if capabilities.get(required_capability, 0) >= min(complexity, min_capability_score)
            ]

            if not suitable_models:
                # Fallback to most capable model
                return "gpt-4-turbo-preview"

            # Select cheapest suitable model
            cheapest = min(
                suitable_models,
                key=lambda m: sum(self.MODEL_COSTS[m])
            )

            return cheapest

        def _assess_complexity(self, task_description: str) -> int:
            """Assess task complexity (1-10 scale)."""

            complexity_indicators = {
                # High complexity
                r"multi-step|complex|advanced|intricate": 9,
                r"requires.*reasoning|logical.*deduction": 8,
                r"analyze|evaluate|compare": 7,

                # Medium complexity
                r"explain|describe|summarize": 6,
                r"translate|convert|transform": 5,

                # Low complexity
                r"list|enumerate|identify": 4,
                r"yes|no|true|false": 3,
                r"simple|basic|straightforward": 2,
            }

            max_complexity = 5  # Default medium complexity
            for pattern, score in complexity_indicators.items():
                if re.search(pattern, task_description, re.IGNORECASE):
                    max_complexity = max(max_complexity, score)

            return max_complexity
    ```
  - Files to create: `orchestrator/llm/model_selector.py`

- [ ] **Fine-Tune Specialist Models** (3 hours)
  - Collect training data from task logs
  - Fine-tune Mistral 7B for common patterns
  - Replace GPT-3.5 calls with fine-tuned model
  - Code example:
    ```python
    # scripts/fine_tune_specialist.py
    from datasets import Dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer
    )
    from typing import List, Dict, Any
    import json

    class SpecialistModelTrainer:
        """Fine-tune specialist models for common tasks."""

        def __init__(self, base_model: str = "mistralai/Mistral-7B-Instruct-v0.2"):
            self.base_model = base_model
            self.tokenizer = AutoTokenizer.from_pretrained(base_model)
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model,
                load_in_4bit=True,  # QLoRA for efficient fine-tuning
                device_map="auto"
            )

        def prepare_training_data(
            self,
            task_logs_path: str,
            task_type: str
        ) -> Dataset:
            """Prepare training data from task logs."""

            # Load task logs
            with open(task_logs_path) as f:
                logs = [json.loads(line) for line in f]

            # Filter by task type
            relevant_logs = [
                log for log in logs
                if log.get("task_type") == task_type
            ]

            # Format for instruction tuning
            training_examples = []
            for log in relevant_logs:
                training_examples.append({
                    "instruction": log["input_prompt"],
                    "output": log["llm_response"]
                })

            return Dataset.from_list(training_examples)

        def fine_tune(
            self,
            dataset: Dataset,
            output_dir: str,
            num_epochs: int = 3
        ):
            """Fine-tune model on dataset."""

            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=num_epochs,
                per_device_train_batch_size=4,
                gradient_accumulation_steps=4,
                learning_rate=2e-5,
                warmup_steps=100,
                logging_steps=10,
                save_steps=100,
                evaluation_strategy="steps",
                eval_steps=100,
                load_best_model_at_end=True
            )

            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=dataset,
                tokenizer=self.tokenizer
            )

            trainer.train()
            trainer.save_model(output_dir)

    if __name__ == "__main__":
        trainer = SpecialistModelTrainer()

        # Fine-tune for code review task
        dataset = trainer.prepare_training_data(
            task_logs_path="logs/task_logs.jsonl",
            task_type="code_review"
        )

        trainer.fine_tune(
            dataset=dataset,
            output_dir="models/mistral-7b-code-review"
        )
    ```
  - Files to create: `scripts/fine_tune_specialist.py`

#### Request Optimization (4 hours)

- [ ] **Implement Request Batching** (2 hours)
  - Batch similar requests to reduce API overhead
  - Use async processing with batch windows
  - Files to create: `orchestrator/llm/batch_processor.py`

- [ ] **Implement Request Deduplication** (2 hours)
  - Detect duplicate requests in flight
  - Return cached result to duplicate requesters
  - Files to create: `orchestrator/middleware/deduplication.py`

### Testing Requirements

#### Unit Tests
- [ ] Resource analyzer calculations (10 test cases)
- [ ] Model selector logic (15 test cases)
- [ ] Prompt caching (20 test cases)
- [ ] Request batching (10 test cases)

#### Integration Tests
- [ ] End-to-end cost tracking
- [ ] Spot instance failover
- [ ] LLM cost reduction verification
- [ ] Fine-tuned model accuracy vs base model

#### Performance Tests
- [ ] Cost per task benchmark (before/after optimization)
- [ ] Cache hit rate measurement (target >60%)
- [ ] Fine-tuned model latency vs GPT-3.5

### Documentation Deliverables

- [ ] Cost optimization strategy guide
- [ ] Right-sizing procedures
- [ ] Spot instance configuration guide
- [ ] LLM cost reduction techniques
- [ ] Fine-tuning runbooks

### Success Criteria

- [ ] Cost per task reduced by 50% vs Phase 5
- [ ] Resource waste reduced by >30%
- [ ] LLM cache hit rate >60%
- [ ] Fine-tuned models achieve >95% accuracy of GPT-3.5 on target tasks
- [ ] Zero performance degradation from cost optimizations

### Common Pitfalls

1. **Over-Optimization**: Aggressive right-sizing causes OOM kills—maintain 20% buffer
2. **Spot Instance Unavailability**: Spot capacity shortages in peak hours—keep on-demand fallback
3. **Cache Staleness**: Cached responses become outdated—implement TTL and versioning
4. **Fine-Tuning Overfitting**: Model only works on training distribution—use diverse dataset
5. **Premature Optimization**: Optimize before understanding usage patterns—collect 30+ days data first

### Estimated Effort

- Development: 28 hours
- Testing: 6 hours
- Documentation: 3 hours
- **Total**: 37 hours (~2 weeks for 3 engineers)

### Dependencies

- **Prerequisites**: Sprint 6.1 (autoscaling), Phase 3 (monitoring)
- **Blocking**: None
- **Blocked By**: None

---

## Sprint 6.3: Compliance Implementation [Week 37-38]

**(Abbreviated for space - full version would be 1,200-1,500 lines)**

### Sprint Goals

- Achieve SOC 2 Type II compliance
- Implement ISO 27001 controls
- Ensure GDPR compliance (data protection, right to erasure)
- Ensure CCPA compliance (opt-out, data disclosure)
- HIPAA readiness (encryption, access controls, audit logs)
- Pass external compliance audits

### Key Tasks (Summary)

1. **SOC 2 Type II Preparation** (12 hours)
   - Implement security controls (TSC)
   - Document policies and procedures
   - Conduct internal audit
   - Contract external auditor

2. **ISO 27001 Implementation** (10 hours)
   - Risk assessment and treatment
   - Information security policies
   - Access control procedures
   - Incident management

3. **GDPR Compliance** (8 hours)
   - Data protection impact assessment (DPIA)
   - Consent management
   - Right to erasure implementation
   - Data portability

4. **CCPA Compliance** (6 hours)
   - Consumer rights implementation (opt-out, disclosure)
   - Privacy policy updates
   - Data inventory and mapping

5. **HIPAA Readiness** (6 hours)
   - Encryption at rest and in transit
   - Access controls and audit logs
   - Business associate agreements (BAA)
   - Breach notification procedures

### Estimated Effort: 42 hours (~2 weeks for 2 engineers)

---

## Sprint 6.4: Advanced Performance [Week 39-40]

**(Abbreviated for space - full version would be 1,200-1,500 lines)**

### Sprint Goals

- Rewrite performance-critical components in Rust
- Fine-tune LLM models for specific tasks
- Implement advanced caching strategies (multi-tier, predictive)
- Add speculative execution for anticipated tasks
- Achieve P99 latency <10s (vs <30s in Phase 1)
- Reduce LLM API costs by additional 30%

### Key Tasks (Summary)

1. **Rust Performance Rewrites** (16 hours)
   - Rewrite Planner Arm in Rust (2x faster)
   - Rewrite Judge Arm in Rust (3x faster)
   - Optimize Reflex Layer (target <5ms P95)

2. **Model Fine-Tuning** (12 hours)
   - Fine-tune task decomposition model
   - Fine-tune code generation model
   - Fine-tune validation model
   - Deploy fine-tuned models

3. **Advanced Caching** (10 hours)
   - Multi-tier caching (L1: Redis, L2: Qdrant, L3: S3)
   - Predictive cache warming
   - Cache invalidation strategies

4. **Speculative Execution** (8 hours)
   - Predict next likely task based on patterns
   - Precompute results in background
   - Serve from cache when requested

5. **Performance Benchmarking** (4 hours)
   - Comprehensive performance test suite
   - Compare Phase 6 vs Phase 1 metrics
   - Latency reduction verification

### Estimated Effort: 50 hours (~2.5 weeks for 2 engineers)

---

## Sprint 6.5: Multi-Tenancy [Week 41-42]

**(Abbreviated for space - full version would be 1,200-1,500 lines)**

### Sprint Goals

- Implement tenant isolation (network, storage, compute)
- Add authentication and authorization per tenant
- Implement usage-based billing
- Create tenant management portal
- Test multi-tenant security isolation
- Document multi-tenancy architecture

### Key Tasks (Summary)

1. **Tenant Isolation** (12 hours)
   - Kubernetes namespaces per tenant
   - Network policies for isolation
   - Separate database schemas
   - Qdrant collections per tenant

2. **Authentication and Authorization** (10 hours)
   - Multi-tenant Auth0 integration
   - Tenant-scoped API keys
   - Role-based access control (RBAC) per tenant

3. **Usage-Based Billing** (10 hours)
   - Meter API calls, LLM tokens, compute time
   - Integrate with Stripe for billing
   - Generate invoices and usage reports

4. **Tenant Management Portal** (8 hours)
   - React admin dashboard
   - Tenant provisioning and configuration
   - Usage analytics and billing

5. **Security Testing** (6 hours)
   - Tenant isolation verification
   - Cross-tenant access attempts (should all fail)
   - Data leakage testing

### Estimated Effort: 46 hours (~2.5 weeks for 2 engineers)

---

## Phase 6 Summary

**Total Tasks**: 80+ production readiness tasks across 5 sprints
**Estimated Duration**: 8-10 weeks with 4-5 engineers
**Total Estimated Hours**: ~206 hours development + ~40 hours testing + ~25 hours documentation = 271 hours

**Deliverables**:
- Autoscaling infrastructure (HPA, VPA, cluster autoscaler)
- 50% cost reduction vs Phase 5
- SOC 2 Type II, ISO 27001, GDPR, CCPA compliance
- P99 latency <10s (67% improvement vs Phase 1)
- Multi-tenant production platform

**Completion Checklist**:
- [ ] Autoscaling handles 10x traffic spikes
- [ ] Cost per task reduced by 50%
- [ ] SOC 2 Type II audit passed
- [ ] P99 latency <10s achieved
- [ ] Multi-tenant isolation verified
- [ ] Production SLA: 99.9% uptime, <15s P95 latency
- [ ] Zero security incidents in first 90 days
- [ ] Public API and documentation published

**Next Steps**: Production launch and customer onboarding

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Maintained By**: OctoLLM Production Team
