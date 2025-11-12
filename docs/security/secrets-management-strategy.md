# Secrets Management Strategy

**Status**: Approved
**Decision Date**: 2025-11-12
**Related**: [ADR-006](../adr/006-cloud-provider-selection.md), Sprint 0.7

---

## Executive Summary

OctoLLM uses **Google Cloud Secret Manager** as the primary secrets backend, integrated with Kubernetes via **External Secrets Operator**. This strategy ensures secure storage, automated rotation, and least-privilege access to all sensitive credentials.

**Key Decisions**:
- ✅ GCP Secret Manager (cloud-native, cost-effective)
- ✅ External Secrets Operator (K8s integration)
- ✅ Workload Identity (no service account keys)
- ✅ Automated rotation where possible
- ✅ Audit logging enabled

---

## Secrets Inventory

### 1. LLM API Keys

| Secret | Description | Rotation | Access |
|--------|-------------|----------|--------|
| `openai-api-key` | OpenAI GPT-4 API key | 90 days (manual) | orchestrator, planner-arm |
| `anthropic-api-key` | Anthropic Claude API key | 90 days (manual) | orchestrator, coder-arm |

**Storage**: GCP Secret Manager (`projects/octollm-{env}/secrets/`)
**Risk**: High (cost impact if compromised, rate limits, data exposure)
**Mitigation**: IP allowlisting (OpenAI), usage monitoring, cost alerts

### 2. Database Credentials

| Secret | Description | Rotation | Access |
|--------|-------------|----------|--------|
| `postgres-admin-password` | PostgreSQL admin password | 30 days (automated) | database-operators only |
| `postgres-app-password` | PostgreSQL application password | 30 days (automated) | all services |
| `redis-auth-string` | Redis authentication token | 30 days (automated) | all services |

**Storage**: GCP Secret Manager + Cloud SQL managed rotation
**Risk**: High (full database access)
**Mitigation**: Connection limits, private IPs, SSL enforcement, read-only replicas

### 3. TLS Certificates

| Secret | Description | Rotation | Access |
|--------|-------------|----------|--------|
| `letsencrypt-prod` | Let's Encrypt TLS cert | Automated (cert-manager) | ingress-controller |

**Storage**: Kubernetes Secrets (cert-manager managed)
**Risk**: Medium (service outage if expired)
**Mitigation**: cert-manager auto-renewal (30 days before expiry), alerts

### 4. Service Account Keys

| Secret | Description | Rotation | Access |
|--------|-------------|----------|--------|
| `gcp-terraform-sa-key` | Terraform GCP service account | 90 days (manual) | CI/CD only |

**Storage**: GitHub Secrets / GitLab Variables
**Risk**: High (infrastructure access)
**Mitigation**: Minimal permissions, separate SA per environment, IP restrictions

### 5. Monitoring & Alerting

| Secret | Description | Rotation | Access |
|--------|-------------|----------|--------|
| `slack-webhook-url` | Slack alerts webhook | As needed (manual) | monitoring-system |
| `pagerduty-api-key` | PagerDuty integration | 90 days (manual) | alertmanager |

**Storage**: GCP Secret Manager
**Risk**: Low (notification channel only)
**Mitigation**: Webhook URL obfuscation, rate limiting

---

## Chosen Solution: GCP Secret Manager

### Why GCP Secret Manager?

**Pros**:
- ✅ Native GCP integration (Workload Identity)
- ✅ Automatic replication across regions
- ✅ Versioning and rollback
- ✅ Audit logging (Cloud Audit Logs)
- ✅ Fine-grained IAM policies
- ✅ Encryption at rest (Google-managed keys)
- ✅ Cost-effective ($0.06 per 10,000 access operations)
- ✅ Kubernetes integration via External Secrets Operator

**Cons**:
- ❌ Vendor lock-in (mitigated: External Secrets supports multiple backends)
- ❌ No built-in UI for secret creation (use gcloud or console)

### Alternatives Considered

**HashiCorp Vault** (self-hosted):
- Pros: Cloud-agnostic, dynamic secrets, rich plugin ecosystem
- Cons: Operational overhead, higher cost (infrastructure + maintenance)
- Decision: Overkill for current scale, reevaluate at 100+ services

**AWS Secrets Manager** (if we chose AWS):
- Pros: Automatic rotation for RDS, Lambda integration
- Cons: Higher cost ($0.40/month per secret + $0.05 per 10,000 API calls)
- Decision: N/A (chose GCP in ADR-006)

**SOPS** (file-based encryption):
- Pros: Git-friendly, version control
- Cons: Manual rotation, no dynamic secrets, GitOps only
- Decision: Good for GitOps, but GCP Secret Manager better for runtime secrets

---

## Architecture

### Secret Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         GCP Secret Manager                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   openai-api │  │  postgres-pw │  │   redis-auth │         │
│  │      key     │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────▲─────────────────────────────────────────┘
                         │ (Workload Identity)
                         │
              ┌──────────▼────────────┐
              │  External Secrets     │
              │      Operator         │
              │  (Sync every 1 hour)  │
              └──────────┬────────────┘
                         │
         ┌───────────────▼───────────────┐
         │    Kubernetes Secrets         │
         │  ┌────────┐  ┌────────┐      │
         │  │ openai │  │postgres│      │
         │  └────────┘  └────────┘      │
         └───────────────┬───────────────┘
                         │
         ┌───────────────▼───────────────┐
         │         Pod                   │
         │  ┌─────────────────────┐     │
         │  │ Env Vars / Volumes  │     │
         │  │  OPENAI_API_KEY=... │     │
         │  └─────────────────────┘     │
         └───────────────────────────────┘
```

### Components

1. **GCP Secret Manager**: Source of truth for secrets
2. **External Secrets Operator**: Syncs secrets to Kubernetes (1-hour refresh)
3. **Kubernetes Secrets**: Ephemeral storage, auto-deleted when pods terminate
4. **Workload Identity**: Binds Kubernetes service accounts to GCP service accounts (no keys!)

---

## Implementation

### Step 1: Create Secrets in GCP

```bash
# Create OpenAI API key secret
echo -n "sk-abc123..." | gcloud secrets create dev-octollm-openai-api-key \
  --project=octollm-dev \
  --replication-policy=automatic \
  --data-file=-

# Add IAM policy (grant access to specific service)
gcloud secrets add-iam-policy-binding dev-octollm-openai-api-key \
  --project=octollm-dev \
  --member="serviceAccount:external-secrets@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Verify
gcloud secrets describe dev-octollm-openai-api-key --project=octollm-dev
```

### Step 2: Install External Secrets Operator

```bash
# Add Helm repo
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

# Install
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace \
  --set installCRDs=true

# Verify
kubectl get pods -n external-secrets-system
```

### Step 3: Configure Workload Identity

```bash
# Create GCP service account for External Secrets
gcloud iam service-accounts create external-secrets \
  --project=octollm-dev

# Grant Secret Manager access
gcloud projects add-iam-policy-binding octollm-dev \
  --member="serviceAccount:external-secrets@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Bind Kubernetes SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding \
  external-secrets@octollm-dev.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:octollm-dev.svc.id.goog[octollm-dev/external-secrets-sa]"

# Annotate Kubernetes SA (see infrastructure/secrets/kubernetes-integration/external-secrets.yaml)
```

### Step 4: Create SecretStore

```yaml
# See infrastructure/secrets/kubernetes-integration/external-secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: gcpsm-secret-store
  namespace: octollm-dev
spec:
  provider:
    gcpsm:
      projectID: "octollm-dev"
      auth:
        workloadIdentity:
          clusterLocation: us-central1
          clusterName: octollm-dev-cluster
          serviceAccountRef:
            name: external-secrets-sa
```

### Step 5: Create ExternalSecret

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: openai-api-key
  namespace: octollm-dev
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: gcpsm-secret-store
  target:
    name: openai-api-key
  data:
  - secretKey: api-key
    remoteRef:
      key: dev-octollm-openai-api-key
```

### Step 6: Use Secret in Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: orchestrator
spec:
  containers:
  - name: orchestrator
    image: octollm/orchestrator:latest
    env:
    - name: OPENAI_API_KEY
      valueFrom:
        secretKeyRef:
          name: openai-api-key
          key: api-key
```

---

## Rotation Procedures

### Automated Rotation (Cloud SQL, Memorystore)

**Cloud SQL PostgreSQL**:
```bash
# Enable automatic password rotation (via Terraform)
# See infra/modules/database/main.tf

# Manual rotation (if needed)
gcloud sql users set-password octollm \
  --instance=octollm-dev-postgres \
  --password=<new-password>

# Update secret in GCP Secret Manager
echo -n "<new-password>" | gcloud secrets versions add dev-octollm-postgres-password \
  --data-file=-

# External Secrets Operator will sync within 1 hour
# Or: Force sync by deleting Kubernetes secret
kubectl delete secret postgres-credentials -n octollm-dev
```

**Memorystore Redis**:
```bash
# Redis auto-rotates auth string on restart (if enabled)
# Manual rotation:
gcloud redis instances update octollm-dev-redis \
  --region=us-central1 \
  --update-auth-string

# Update GCP Secret Manager
NEW_AUTH=$(gcloud redis instances describe octollm-dev-redis \
  --region=us-central1 \
  --format="value(authString)")
echo -n "$NEW_AUTH" | gcloud secrets versions add dev-octollm-redis-auth \
  --data-file=-
```

### Manual Rotation (API Keys, Service Accounts)

**OpenAI API Key**:
```bash
# 1. Generate new key in OpenAI dashboard

# 2. Store in GCP Secret Manager (creates new version)
echo -n "sk-new-key..." | gcloud secrets versions add dev-octollm-openai-api-key \
  --data-file=-

# 3. External Secrets syncs within 1 hour
#    Or: Force pod restart
kubectl rollout restart deployment/orchestrator -n octollm-dev

# 4. Verify new key works
kubectl logs -l app=orchestrator -n octollm-dev | grep "OpenAI API"

# 5. Revoke old key in OpenAI dashboard (after 24h grace period)
```

**GCP Service Account Key** (CI/CD):
```bash
# 1. Create new key
gcloud iam service-accounts keys create new-key.json \
  --iam-account=terraform-sa@octollm-dev.iam.gserviceaccount.com

# 2. Update GitHub/GitLab secret
# GitHub: Settings > Secrets > Update GCP_SA_KEY
# GitLab: Settings > CI/CD > Variables > Update GCP_SA_KEY

# 3. Test CI/CD pipeline

# 4. Delete old key (after 24h)
gcloud iam service-accounts keys delete <old-key-id> \
  --iam-account=terraform-sa@octollm-dev.iam.gserviceaccount.com
```

### Emergency Rotation (Compromised Secret)

**Immediate Actions**:
```bash
# 1. REVOKE compromised secret immediately
#    - OpenAI: Delete API key in dashboard
#    - Database: Change password
#    - Service Account: Delete key

# 2. Generate new secret

# 3. Update GCP Secret Manager
echo -n "<new-secret>" | gcloud secrets versions add <secret-name> --data-file=-

# 4. Force sync (don't wait 1 hour)
kubectl delete secret <secret-name> -n octollm-dev
kubectl rollout restart deployment/<affected-service> -n octollm-dev

# 5. Verify new secret works
kubectl logs <pod-name> -n octollm-dev

# 6. Audit: Who accessed the secret?
gcloud logging read "protoPayload.serviceName=\"secretmanager.googleapis.com\" AND resource.labels.secret_id=\"<secret-name>\"" \
  --limit=100 \
  --format=json
```

**Post-Incident**:
1. Document incident in security log
2. Review access logs (who, when, what)
3. Update IAM policies if needed
4. Add monitoring/alerting for unusual access patterns
5. Conduct blameless postmortem

---

## Security Best Practices

### 1. Never Commit Secrets to Git

**.gitignore** (already configured):
```gitignore
# Secrets
*.secret
*.key
*.pem
.env
.env.*
terraform.tfvars
credentials.json
service-account-key.json

# Terraform state (may contain secrets)
*.tfstate
*.tfstate.backup
.terraform/
```

**Pre-commit Hook** (gitleaks):
```bash
# Install gitleaks
brew install gitleaks  # macOS

# Scan repository
gitleaks detect --source . --verbose

# Pre-commit hook (see .pre-commit-config.yaml)
```

### 2. Principle of Least Privilege

**IAM Policy Example**:
```bash
# Grant ONLY secret accessor role (not admin)
gcloud secrets add-iam-policy-binding <secret-name> \
  --member="serviceAccount:orchestrator@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"  # Read-only

# NOT: roles/secretmanager.admin (can delete secrets)
```

### 3. Enable Audit Logging

**View Secret Access Logs**:
```bash
gcloud logging read '
  protoPayload.serviceName="secretmanager.googleapis.com"
  AND protoPayload.methodName="google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion"
' --limit=100 --format=json | jq '.[] | {time: .timestamp, user: .protoPayload.authenticationInfo.principalEmail, secret: .protoPayload.resourceName}'
```

**Set Up Alerts**:
```bash
# Alert on secret access from unexpected service accounts
gcloud alpha monitoring policies create \
  --notification-channels=<channel-id> \
  --display-name="Unexpected Secret Access" \
  --condition-display-name="Secret accessed by unknown SA" \
  --condition-threshold-value=1 \
  --condition-threshold-duration=60s \
  --condition-filter='
    resource.type="secretmanager.googleapis.com/Secret"
    AND protoPayload.authenticationInfo.principalEmail!~"(orchestrator|external-secrets)@octollm-dev.iam.gserviceaccount.com"
  '
```

### 4. Encrypt Secrets in Transit

- ✅ TLS 1.2+ for all API calls (GCP enforces)
- ✅ TLS 1.2+ for database connections (Cloud SQL enforces)
- ✅ TLS for Redis (Memorystore enforces)
- ✅ Kubernetes Secrets mounted as in-memory volumes (not disk)

### 5. Regular Secret Rotation Schedule

| Secret Type | Rotation Frequency | Method |
|-------------|-------------------|--------|
| API Keys | 90 days | Manual |
| Database Passwords | 30 days | Automated (Cloud SQL) |
| Redis Auth | 30 days | Automated (Memorystore) |
| TLS Certs | 90 days | Automated (cert-manager) |
| Service Account Keys | 90 days | Manual |
| Webhooks | As needed | Manual |

---

## Compliance & Audit

### SOC 2 Requirements

- ✅ Secrets encrypted at rest (Google-managed keys)
- ✅ Secrets encrypted in transit (TLS 1.2+)
- ✅ Access logging enabled (Cloud Audit Logs)
- ✅ Principle of least privilege (IAM policies)
- ✅ Regular rotation (automated + manual)
- ✅ No secrets in source code (pre-commit hooks)
- ✅ Quarterly access reviews

### GDPR Requirements

- ✅ Data residency (GCP Secret Manager regional replication)
- ✅ Right to erasure (delete secret versions)
- ✅ Data portability (export via gcloud)
- ✅ Breach notification (incident response plan)

---

## Troubleshooting

### Issue 1: External Secret Not Syncing

```bash
# Check ExternalSecret status
kubectl describe externalsecret openai-api-key -n octollm-dev

# Check External Secrets Operator logs
kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets

# Force sync
kubectl delete externalsecret openai-api-key -n octollm-dev
kubectl apply -f external-secrets.yaml
```

### Issue 2: Permission Denied

```bash
# Check IAM policy
gcloud secrets get-iam-policy dev-octollm-openai-api-key --project=octollm-dev

# Check Workload Identity binding
gcloud iam service-accounts get-iam-policy \
  external-secrets@octollm-dev.iam.gserviceaccount.com
```

### Issue 3: Secret Not Found in Pod

```bash
# Check Kubernetes Secret exists
kubectl get secret openai-api-key -n octollm-dev

# Describe secret (shows keys, not values)
kubectl describe secret openai-api-key -n octollm-dev

# Check pod environment variables
kubectl exec <pod-name> -n octollm-dev -- env | grep OPENAI_API_KEY
```

---

## Additional Resources

- [GCP Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [External Secrets Operator](https://external-secrets.io/)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)

---

**Maintained By**: Security Team, DevOps Team
**Last Updated**: 2025-11-12
**Version**: 1.0.0 (Sprint 0.7)
