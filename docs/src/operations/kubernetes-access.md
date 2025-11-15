# Kubernetes Access Guide

**Audience**: Developers, DevOps Engineers
**Prerequisites**: gcloud SDK, kubectl installed
**Related**: [Deployment Guide](deployment-guide.md), [ADR-006](../adr/006-cloud-provider-selection.md)

---

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Cluster Access](#cluster-access)
3. [RBAC Configuration](#rbac-configuration)
4. [kubectl Basics](#kubectl-basics)
5. [Port Forwarding](#port-forwarding)
6. [Troubleshooting](#troubleshooting)

---

## Initial Setup

### Install Required Tools

**kubectl** (Kubernetes CLI):
```bash
# Via gcloud
gcloud components install kubectl

# Via package manager
brew install kubectl  # macOS
sudo apt-get install kubectl  # Ubuntu

# Verify
kubectl version --client
```

**gcloud SDK**:
```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Verify
gcloud version
```

**kubectx/kubens** (optional, recommended):
```bash
brew install kubectx  # macOS
# Or: https://github.com/ahmetb/kubectx

# Usage
kubectx  # List contexts
kubens  # List namespaces
```

---

## Cluster Access

### Authenticate with GCP

```bash
# Login
gcloud auth login

# Set default project
gcloud config set project octollm-dev

# Verify
gcloud config list
```

### Configure kubectl

**Development Cluster**:
```bash
gcloud container clusters get-credentials octollm-dev-cluster \
  --region us-central1 \
  --project octollm-dev

# Verify
kubectl cluster-info
kubectl get nodes
```

**Staging Cluster**:
```bash
gcloud container clusters get-credentials octollm-staging-cluster \
  --region us-central1 \
  --project octollm-staging
```

**Production Cluster**:
```bash
gcloud container clusters get-credentials octollm-prod-cluster \
  --region us-central1 \
  --project octollm-prod
```

### Switch Between Clusters

```bash
# List contexts
kubectl config get-contexts

# Switch context
kubectl config use-context gke_octollm-dev_us-central1_octollm-dev-cluster

# Or with kubectx
kubectx  # List
kubectx gke_octollm-dev_us-central1_octollm-dev-cluster  # Switch
```

### Verify Access

```bash
# Check nodes
kubectl get nodes

# Check namespaces
kubectl get namespaces

# Check pods in octollm-dev namespace
kubectl get pods -n octollm-dev

# Check all resources
kubectl get all -n octollm-dev
```

---

## RBAC Configuration

### Service Accounts

**Create Developer Service Account** (for team members):
```bash
# Create service account
kubectl create serviceaccount developer -n octollm-dev

# Create Role (namespace-scoped permissions)
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: octollm-dev
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "pods/log", "pods/exec", "deployments", "services", "configmaps", "jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list"]  # Read-only secrets
EOF

# Create RoleBinding (bind role to service account)
kubectl create rolebinding developer-binding \
  --role=developer \
  --serviceaccount=octollm-dev:developer \
  --namespace=octollm-dev
```

**Create Read-Only Service Account** (for viewers):
```bash
kubectl create serviceaccount viewer -n octollm-dev

cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: viewer
  namespace: octollm-dev
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
EOF

kubectl create rolebinding viewer-binding \
  --role=viewer \
  --serviceaccount=octollm-dev:viewer \
  --namespace=octollm-dev
```

### IAM Integration (Workload Identity)

**Bind Kubernetes SA to GCP SA**:
```bash
# Create GCP service account
gcloud iam service-accounts create octollm-orchestrator \
  --project=octollm-dev

# Grant permissions
gcloud projects add-iam-policy-binding octollm-dev \
  --member="serviceAccount:octollm-orchestrator@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Bind to Kubernetes SA
gcloud iam service-accounts add-iam-policy-binding \
  octollm-orchestrator@octollm-dev.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:octollm-dev.svc.id.goog[octollm-dev/orchestrator]"

# Annotate Kubernetes SA
kubectl annotate serviceaccount orchestrator \
  --namespace octollm-dev \
  iam.gke.io/gcp-service-account=octollm-orchestrator@octollm-dev.iam.gserviceaccount.com
```

---

## kubectl Basics

### Common Commands

**Pods**:
```bash
# List pods
kubectl get pods -n octollm-dev

# Describe pod
kubectl describe pod <pod-name> -n octollm-dev

# View logs
kubectl logs <pod-name> -n octollm-dev
kubectl logs <pod-name> -n octollm-dev --follow  # Stream logs
kubectl logs <pod-name> -c <container-name> -n octollm-dev  # Multi-container pod

# Execute command in pod
kubectl exec -it <pod-name> -n octollm-dev -- /bin/bash
kubectl exec <pod-name> -n octollm-dev -- env  # View environment variables
```

**Deployments**:
```bash
# List deployments
kubectl get deployments -n octollm-dev

# Scale deployment
kubectl scale deployment orchestrator --replicas=3 -n octollm-dev

# Rollout status
kubectl rollout status deployment/orchestrator -n octollm-dev

# Rollout history
kubectl rollout history deployment/orchestrator -n octollm-dev

# Rollback
kubectl rollout undo deployment/orchestrator -n octollm-dev
```

**Services**:
```bash
# List services
kubectl get services -n octollm-dev

# Describe service
kubectl describe service orchestrator -n octollm-dev

# Get endpoints
kubectl get endpoints orchestrator -n octollm-dev
```

**ConfigMaps & Secrets**:
```bash
# List ConfigMaps
kubectl get configmaps -n octollm-dev

# View ConfigMap
kubectl describe configmap app-config -n octollm-dev

# List Secrets
kubectl get secrets -n octollm-dev

# Decode secret
kubectl get secret postgres-credentials -n octollm-dev -o jsonpath='{.data.password}' | base64 --decode
```

**Events**:
```bash
# View events (last 1 hour)
kubectl get events -n octollm-dev --sort-by='.lastTimestamp'

# Watch events in real-time
kubectl get events -n octollm-dev --watch
```

---

## Port Forwarding

### Access Services Locally

**PostgreSQL**:
```bash
# Forward PostgreSQL port (Cloud SQL Proxy)
kubectl port-forward svc/postgres 5432:5432 -n octollm-dev

# Connect
psql -h localhost -U octollm -d octollm
```

**Redis**:
```bash
# Forward Redis port
kubectl port-forward svc/redis 6379:6379 -n octollm-dev

# Connect
redis-cli -h localhost -p 6379 -a <auth-string>
```

**Orchestrator API**:
```bash
# Forward Orchestrator port
kubectl port-forward svc/orchestrator 8000:8000 -n octollm-dev

# Test
curl http://localhost:8000/health
```

**Grafana Dashboard**:
```bash
# Forward Grafana port
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# Open browser
open http://localhost:3000
```

**Multiple Ports** (background):
```bash
# Port-forward multiple services in background
kubectl port-forward svc/orchestrator 8000:8000 -n octollm-dev &
kubectl port-forward svc/postgres 5432:5432 -n octollm-dev &
kubectl port-forward svc/redis 6379:6379 -n octollm-dev &

# List background jobs
jobs

# Kill port-forward
kill %1  # Kill job 1
pkill -f "port-forward"  # Kill all
```

---

## Troubleshooting

### Common Issues

**Issue 1: kubectl Cannot Connect**
```
Unable to connect to the server: dial tcp: lookup <cluster>: no such host
```

**Solution**: Reconfigure kubectl:
```bash
gcloud container clusters get-credentials octollm-dev-cluster \
  --region us-central1 \
  --project octollm-dev
```

---

**Issue 2: Permission Denied**
```
Error from server (Forbidden): pods is forbidden: User "user@example.com" cannot list resource "pods"
```

**Solution**: Check RBAC permissions:
```bash
# Check current user
kubectl auth whoami

# Check permissions
kubectl auth can-i list pods --namespace octollm-dev
kubectl auth can-i create deployments --namespace octollm-dev

# Request permissions from DevOps team
```

---

**Issue 3: Pod CrashLoopBackOff**
```bash
# View pod events
kubectl describe pod <pod-name> -n octollm-dev

# View logs
kubectl logs <pod-name> -n octollm-dev --previous  # Previous container logs

# Common causes:
# - Missing environment variables
# - Incorrect image
# - Resource limits too low
# - Health check failures
```

---

**Issue 4: Service Not Accessible**
```bash
# Check service
kubectl get svc orchestrator -n octollm-dev

# Check endpoints (should list pod IPs)
kubectl get endpoints orchestrator -n octollm-dev

# If no endpoints, check pod selector
kubectl get pods -l app=orchestrator -n octollm-dev

# Check pod logs
kubectl logs -l app=orchestrator -n octollm-dev
```

---

**Issue 5: Slow kubectl Commands**
```bash
# Clear kubectl cache
rm -rf ~/.kube/cache

# Or: Use --v=9 to debug
kubectl get pods --v=9
```

---

## Best Practices

1. **Always specify namespace** (`-n <namespace>`) to avoid mistakes
2. **Use labels** for bulk operations: `kubectl get pods -l app=orchestrator`
3. **Dry-run before apply**: `kubectl apply -f deployment.yaml --dry-run=client`
4. **Use contexts** to switch between clusters safely
5. **Avoid `kubectl delete --all`** without namespace specification
6. **Use `kubectl diff`** to preview changes: `kubectl diff -f deployment.yaml`
7. **Set resource limits** to prevent resource exhaustion
8. **Use liveness and readiness probes** for reliability

---

## Useful Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# kubectl aliases
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kgd='kubectl get deployments'
alias kdp='kubectl describe pod'
alias kl='kubectl logs'
alias kex='kubectl exec -it'
alias kpf='kubectl port-forward'

# Namespace-specific
alias kdev='kubectl -n octollm-dev'
alias kprod='kubectl -n octollm-prod'
```

---

## Additional Resources

- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

---

**Maintained By**: DevOps Team
**Last Updated**: 2025-11-12
**Version**: 1.0.0 (Sprint 0.7)
