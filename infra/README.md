# OctoLLM Infrastructure as Code (Terraform + GCP)

**Cloud Provider**: Google Cloud Platform (GCP)
**IaC Tool**: Terraform 1.6+
**Kubernetes**: Google Kubernetes Engine (GKE) 1.28+
**Decision**: See [ADR-006: Cloud Provider Selection](../docs/adr/006-cloud-provider-selection.md)

---

## Overview

This directory contains Infrastructure as Code (IaC) for provisioning all OctoLLM cloud resources on Google Cloud Platform. The infrastructure is organized into reusable Terraform modules and environment-specific configurations for development, staging, and production.

**Key Features**:
- ✅ Cloud-agnostic architecture (easy migration to AWS/Azure)
- ✅ Modular design (reusable components)
- ✅ Environment isolation (dev/staging/prod)
- ✅ State management with remote backends
- ✅ Cost-optimized (22% cheaper than AWS)
- ✅ Production-ready (HA, auto-scaling, monitoring)

---

## Directory Structure

```
infra/
├── README.md                        # This file
├── terraform.tfvars.example         # Example variables (copy to terraform.tfvars)
├── main.tf                          # Root module (not recommended to use directly)
├── variables.tf                     # Global variables
├── outputs.tf                       # Global outputs
├── versions.tf                      # Terraform and provider version constraints
├── .terraform.lock.hcl              # Provider version lock file (generated)
├── modules/                         # Reusable Terraform modules
│   ├── gke/                         # Google Kubernetes Engine cluster
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── database/                    # Cloud SQL PostgreSQL
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── redis/                       # Memorystore for Redis
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── storage/                     # Google Cloud Storage buckets
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── networking/                  # VPC, subnets, firewall rules
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── dns/                         # Cloud DNS and certificates
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   └── monitoring/                  # Cloud Monitoring, Logging, Alerting
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── README.md
└── environments/                    # Environment-specific configurations
    ├── dev/                         # Development environment
    │   ├── main.tf
    │   ├── terraform.tfvars
    │   ├── variables.tf
    │   ├── outputs.tf
    │   ├── backend.tf               # Remote state configuration
    │   └── README.md
    ├── staging/                     # Staging environment
    │   ├── main.tf
    │   ├── terraform.tfvars
    │   ├── variables.tf
    │   ├── outputs.tf
    │   ├── backend.tf
    │   └── README.md
    └── prod/                        # Production environment
        ├── main.tf
        ├── terraform.tfvars
        ├── variables.tf
        ├── outputs.tf
        ├── backend.tf
        └── README.md
```

---

## Prerequisites

### 1. Required Tools

**Terraform** (1.6+):
```bash
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify
terraform version
```

**Google Cloud SDK** (gcloud):
```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Verify
gcloud version
```

**kubectl** (Kubernetes CLI):
```bash
# Install via gcloud
gcloud components install kubectl

# Verify
kubectl version --client
```

**Optional Tools**:
- **terraform-docs**: Generate module documentation
- **tflint**: Terraform linter
- **terrascan**: Security scanner for IaC
- **checkov**: Policy-as-code scanner

### 2. GCP Setup

**Create GCP Projects**:
```bash
# Set up billing account first (via console: https://console.cloud.google.com/billing)

# Create projects
gcloud projects create octollm-dev --name="OctoLLM Development"
gcloud projects create octollm-staging --name="OctoLLM Staging"
gcloud projects create octollm-prod --name="OctoLLM Production"

# Link billing account (replace BILLING_ACCOUNT_ID)
gcloud beta billing projects link octollm-dev --billing-account=BILLING_ACCOUNT_ID
gcloud beta billing projects link octollm-staging --billing-account=BILLING_ACCOUNT_ID
gcloud beta billing projects link octollm-prod --billing-account=BILLING_ACCOUNT_ID
```

**Enable Required APIs**:
```bash
# Development project
gcloud services enable \
  compute.googleapis.com \
  container.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  storage-api.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudtrace.googleapis.com \
  dns.googleapis.com \
  --project=octollm-dev

# Repeat for staging and prod
gcloud services enable ... --project=octollm-staging
gcloud services enable ... --project=octollm-prod
```

**Create Terraform Service Account**:
```bash
# Create service account
gcloud iam service-accounts create terraform-sa \
  --display-name="Terraform Service Account" \
  --project=octollm-dev

# Grant necessary roles
gcloud projects add-iam-policy-binding octollm-dev \
  --member="serviceAccount:terraform-sa@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/container.admin"

gcloud projects add-iam-policy-binding octollm-dev \
  --member="serviceAccount:terraform-sa@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

gcloud projects add-iam-policy-binding octollm-dev \
  --member="serviceAccount:terraform-sa@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/cloudsql.admin"

gcloud projects add-iam-policy-binding octollm-dev \
  --member="serviceAccount:terraform-sa@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/redis.admin"

gcloud projects add-iam-policy-binding octollm-dev \
  --member="serviceAccount:terraform-sa@octollm-dev.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Create and download key (NEVER COMMIT THIS)
gcloud iam service-accounts keys create ~/octollm-terraform-key.json \
  --iam-account=terraform-sa@octollm-dev.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=~/octollm-terraform-key.json
```

**Create GCS Bucket for Terraform State**:
```bash
# Create buckets for remote state
gsutil mb -l us-central1 -c STANDARD gs://octollm-dev-terraform-state
gsutil mb -l us-central1 -c STANDARD gs://octollm-staging-terraform-state
gsutil mb -l us-central1 -c STANDARD gs://octollm-prod-terraform-state

# Enable versioning (for state rollback)
gsutil versioning set on gs://octollm-dev-terraform-state
gsutil versioning set on gs://octollm-staging-terraform-state
gsutil versioning set on gs://octollm-prod-terraform-state

# Enable encryption
gsutil encryption set -k projects/octollm-dev/locations/global/keyRings/terraform/cryptoKeys/state-encryption gs://octollm-dev-terraform-state
```

**Configure Billing Alerts** (via Console):
1. Go to: https://console.cloud.google.com/billing/budgets
2. Create Budget for octollm-dev:
   - Budget amount: $500/month
   - Alert thresholds: 50%, 80%, 100%
   - Email notifications: team@octollm.com
3. Repeat for staging ($1,000) and prod ($5,000)

### 3. Authentication

**For Local Development**:
```bash
# Authenticate with your user account
gcloud auth login
gcloud auth application-default login

# Set default project
gcloud config set project octollm-dev
```

**For CI/CD (GitHub Actions, GitLab CI, etc.)**:
```yaml
# Use service account key as secret
# NEVER commit the key to git
env:
  GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GCP_SA_KEY }}
```

---

## Quick Start

### Development Environment (30 minutes)

```bash
# 1. Navigate to dev environment
cd infra/environments/dev

# 2. Copy example variables and customize
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values (project_id, region, etc.)

# 3. Initialize Terraform (downloads providers)
terraform init

# 4. Review the execution plan
terraform plan

# 5. Provision infrastructure (confirmation required)
terraform apply

# 6. Save outputs (connection strings, cluster info)
terraform output > outputs.txt

# 7. Configure kubectl to access GKE cluster
gcloud container clusters get-credentials octollm-dev-cluster --region us-central1

# 8. Verify cluster access
kubectl get nodes
kubectl get namespaces
```

### Staging Environment

```bash
cd infra/environments/staging
cp terraform.tfvars.example terraform.tfvars
# Edit with staging values
terraform init
terraform plan
terraform apply
```

### Production Environment

```bash
cd infra/environments/prod
cp terraform.tfvars.example terraform.tfvars
# Edit with production values (careful: expensive!)
terraform init
terraform plan
# ALWAYS review plan thoroughly before production apply
terraform apply
```

---

## Module Documentation

### 1. GKE Module (`modules/gke/`)

**Purpose**: Provision Google Kubernetes Engine cluster with autoscaling, monitoring, and security best practices.

**Features**:
- Regional cluster (multi-AZ HA)
- Node auto-scaling (min/max nodes)
- Automatic node repairs and upgrades
- Workload Identity (GCP service account integration)
- Private cluster option (no public IPs)
- VPC-native networking

**Usage**:
```hcl
module "gke" {
  source = "../../modules/gke"

  project_id       = "octollm-dev"
  region           = "us-central1"
  cluster_name     = "octollm-dev-cluster"
  kubernetes_version = "1.28"

  node_pools = {
    default = {
      machine_type   = "e2-standard-2"
      min_nodes      = 1
      max_nodes      = 3
      disk_size_gb   = 50
      preemptible    = true  # Cost savings for dev
    }
  }

  network_name     = module.networking.network_name
  subnet_name      = module.networking.subnet_name
}
```

**Outputs**: `cluster_endpoint`, `cluster_ca_certificate`, `cluster_name`

### 2. Database Module (`modules/database/`)

**Purpose**: Provision Cloud SQL PostgreSQL instance with HA, backups, and read replicas.

**Features**:
- PostgreSQL 15+
- Automated backups (configurable retention)
- High availability (multi-AZ with automatic failover)
- Read replicas (for production)
- Private IP (VPC peering)
- Connection pooling (PgBouncer)

**Usage**:
```hcl
module "database" {
  source = "../../modules/database"

  project_id       = "octollm-dev"
  region           = "us-central1"
  instance_name    = "octollm-dev-postgres"
  postgres_version = "POSTGRES_15"

  tier             = "db-f1-micro"  # Dev: f1-micro, Prod: n1-standard-4
  disk_size        = 20             # GB
  disk_autoresize  = true

  high_availability = false         # Dev: false, Prod: true
  read_replicas     = 0             # Dev: 0, Prod: 2

  backup_enabled    = true
  backup_start_time = "03:00"       # UTC
  retention_days    = 7             # Dev: 7, Prod: 30

  network_id       = module.networking.network_id
}
```

**Outputs**: `instance_connection_name`, `private_ip_address`, `database_name`

### 3. Redis Module (`modules/redis/`)

**Purpose**: Provision Memorystore for Redis with HA and persistence.

**Features**:
- Redis 7.0+
- Standard tier (HA with automatic failover)
- Persistence (RDB snapshots)
- Private IP (VPC)
- Read replicas (for read-heavy workloads)

**Usage**:
```hcl
module "redis" {
  source = "../../modules/redis"

  project_id       = "octollm-dev"
  region           = "us-central1"
  instance_name    = "octollm-dev-redis"
  redis_version    = "REDIS_7_0"

  tier             = "BASIC"        # Dev: BASIC, Prod: STANDARD_HA
  memory_size_gb   = 2              # Dev: 2, Prod: 6
  read_replicas    = 0              # Prod: 2

  network_id       = module.networking.network_id
}
```

**Outputs**: `host`, `port`, `connection_string`

### 4. Storage Module (`modules/storage/`)

**Purpose**: Create Google Cloud Storage buckets for backups, logs, and artifacts.

**Features**:
- Versioning (for state files, backups)
- Lifecycle policies (auto-delete old versions)
- Encryption (Google-managed or customer-managed)
- IAM policies (fine-grained access control)
- Nearline/Coldline/Archive tiers (cost optimization)

**Usage**:
```hcl
module "storage" {
  source = "../../modules/storage"

  project_id = "octollm-dev"
  region     = "us-central1"

  buckets = {
    backups = {
      name          = "octollm-dev-backups"
      storage_class = "STANDARD"
      versioning    = true
      lifecycle_rules = [
        {
          action = { type = "Delete" }
          condition = { age = 90 }  # Delete after 90 days
        }
      ]
    }
    logs = {
      name          = "octollm-dev-logs"
      storage_class = "STANDARD"
      versioning    = false
      lifecycle_rules = [
        {
          action = { type = "SetStorageClass", storage_class = "NEARLINE" }
          condition = { age = 30 }  # Move to Nearline after 30 days
        },
        {
          action = { type = "Delete" }
          condition = { age = 365 }  # Delete after 1 year
        }
      ]
    }
  }
}
```

**Outputs**: `bucket_names`, `bucket_urls`

### 5. Networking Module (`modules/networking/`)

**Purpose**: Create VPC, subnets, firewall rules, and NAT gateway.

**Features**:
- Custom VPC (not default VPC)
- Multiple subnets (public, private, database)
- Cloud NAT (for private instances to access internet)
- Firewall rules (allow/deny specific traffic)
- VPC peering (for Cloud SQL)

**Usage**:
```hcl
module "networking" {
  source = "../../modules/networking"

  project_id   = "octollm-dev"
  network_name = "octollm-dev-vpc"
  region       = "us-central1"

  subnets = {
    gke = {
      ip_cidr_range = "10.0.0.0/20"   # 4,096 IPs
      secondary_ranges = {
        pods     = "10.4.0.0/14"      # GKE pods
        services = "10.8.0.0/20"      # GKE services
      }
    }
    database = {
      ip_cidr_range = "10.1.0.0/24"   # 256 IPs
    }
  }

  firewall_rules = [
    {
      name        = "allow-internal"
      description = "Allow all internal traffic"
      direction   = "INGRESS"
      ranges      = ["10.0.0.0/8"]
      allow       = [{ protocol = "all" }]
    },
    {
      name        = "allow-ssh"
      description = "Allow SSH from specific IPs"
      direction   = "INGRESS"
      ranges      = ["YOUR_IP/32"]
      allow       = [{ protocol = "tcp", ports = ["22"] }]
    }
  ]
}
```

**Outputs**: `network_id`, `network_name`, `subnet_ids`

### 6. DNS Module (`modules/dns/`)

**Purpose**: Configure Cloud DNS zones and DNS records.

**Features**:
- Managed DNS zones (public or private)
- A/AAAA/CNAME/TXT records
- DNSSEC support
- Integration with cert-manager (TLS certificates)

**Usage**:
```hcl
module "dns" {
  source = "../../modules/dns"

  project_id = "octollm-dev"

  zones = {
    public = {
      name        = "octollm-dev-zone"
      dns_name    = "dev.octollm.com."
      description = "OctoLLM Development DNS Zone"
      visibility  = "public"
    }
  }

  records = {
    api = {
      zone_name = "octollm-dev-zone"
      name      = "api.dev.octollm.com."
      type      = "A"
      ttl       = 300
      rrdatas   = [module.gke.ingress_ip]
    }
  }
}
```

**Outputs**: `zone_names`, `name_servers`

### 7. Monitoring Module (`modules/monitoring/`)

**Purpose**: Configure Cloud Monitoring dashboards, alerts, and uptime checks.

**Features**:
- Custom dashboards (GKE metrics, database metrics)
- Alerting policies (CPU, memory, latency thresholds)
- Uptime checks (HTTP/HTTPS endpoints)
- Notification channels (email, Slack, PagerDuty)

**Usage**:
```hcl
module "monitoring" {
  source = "../../modules/monitoring"

  project_id = "octollm-dev"

  alert_policies = [
    {
      display_name = "High CPU Usage"
      conditions = [{
        display_name = "CPU > 80%"
        threshold    = 0.8
        duration     = "300s"
      }]
      notification_channels = [google_monitoring_notification_channel.email.id]
    }
  ]

  uptime_checks = [
    {
      display_name = "API Health Check"
      monitored_resource = {
        type = "uptime_url"
        labels = {
          host = "api.dev.octollm.com"
          project_id = "octollm-dev"
        }
      }
      http_check = {
        path         = "/health"
        port         = 443
        use_ssl      = true
        validate_ssl = true
      }
      period = "60s"
      timeout = "10s"
    }
  ]
}
```

**Outputs**: `dashboard_urls`, `alert_policy_ids`

---

## Environment-Specific Configurations

### Development Environment

**Purpose**: Cost-optimized, minimal resources, fast iteration.

**Specifications**:
- **GKE**: 1-3 nodes, e2-standard-2 (2vCPU, 8GB), preemptible VMs
- **PostgreSQL**: db-f1-micro (1vCPU, 2GB), 20GB storage, no HA
- **Redis**: BASIC tier, 2GB, no replicas
- **Storage**: STANDARD class, 90-day lifecycle
- **Networking**: Single-region, NAT gateway
- **Cost**: ~$192/month

**Key Features**:
- FREE GKE control plane
- Preemptible VMs (60-91% discount)
- No high availability (acceptable for dev)
- Relaxed backup policies (7-day retention)

### Staging Environment

**Purpose**: Production-like testing, scaled down 50%.

**Specifications**:
- **GKE**: 4-8 nodes, e2-standard-4 (4vCPU, 16GB), on-demand VMs
- **PostgreSQL**: db-n1-standard-2 (2vCPU, 8GB), 100GB storage, HA enabled
- **Redis**: STANDARD_HA tier, 3GB, 1 replica
- **Storage**: STANDARD class, 180-day lifecycle
- **Networking**: Multi-AZ, NAT gateway
- **Cost**: ~$588/month

**Key Features**:
- Production parity (same architecture, scaled down)
- High availability enabled
- Multi-AZ deployment
- Automated backups (14-day retention)

### Production Environment

**Purpose**: High availability, auto-scaling, full observability.

**Specifications**:
- **GKE**: 5-15 nodes, n2-standard-8 (8vCPU, 32GB), on-demand VMs, auto-scaling
- **PostgreSQL**: db-n1-standard-4 (4vCPU, 16GB), 200GB storage, HA + 2 read replicas
- **Redis**: STANDARD_HA tier, 6GB, 2 replicas (manual sharding: 3 instances)
- **Storage**: STANDARD class with multi-region replication, 365-day lifecycle
- **Networking**: Multi-region (future), Cloud Armor (DDoS protection)
- **Cost**: ~$3,683/month

**Key Features**:
- 99.95% SLA (GKE regional cluster)
- Multi-AZ deployment (3 zones)
- Horizontal Pod Autoscaler (HPA)
- Automated backups (30-day retention)
- Point-in-time recovery (7 days)
- Cloud Armor (WAF, DDoS protection)
- Prometheus + Grafana (monitoring stack)
- Loki (log aggregation)
- Jaeger (distributed tracing)

---

## Cost Optimization

### 1. Committed Use Discounts (CUDs)

**1-year commitment**: 25% discount
**3-year commitment**: 52% discount

```bash
# Apply to Compute Engine (GKE nodes)
gcloud compute commitments create octollm-prod-cud \
  --region=us-central1 \
  --resources=vcpu=60,memory=240 \
  --plan=12-month

# Savings: ~$6,000/year on production
```

### 2. Sustained Use Discounts (Automatic)

- Up to 30% discount for sustained usage (no commitment required)
- Applied automatically by GCP

### 3. Preemptible/Spot VMs (Dev Only)

```hcl
# In GKE node pool configuration
node_config {
  preemptible = true  # 60-91% discount
}
```

### 4. Storage Lifecycle Policies

```hcl
lifecycle_rule {
  action {
    type = "SetStorageClass"
    storage_class = "NEARLINE"  # 50% cheaper
  }
  condition {
    age = 30  # days
  }
}

lifecycle_rule {
  action {
    type = "Delete"
  }
  condition {
    age = 365  # days
  }
}
```

### 5. Rightsizing Recommendations

```bash
# Enable recommender API
gcloud recommender recommendations list \
  --project=octollm-prod \
  --location=us-central1 \
  --recommender=google.compute.instance.MachineTypeRecommender

# Review monthly and downsize underutilized resources
```

### 6. Cost Monitoring

```bash
# Export billing data to BigQuery
# 1. Go to https://console.cloud.google.com/billing/export
# 2. Enable BigQuery export
# 3. Create Data Studio dashboard for visualization

# Set up cost anomaly alerts
gcloud alpha billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Production Budget Alert" \
  --budget-amount=5000 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100 \
  --all-updates-rule-monitoring-notification-channels=CHANNEL_ID
```

---

## Security Best Practices

### 1. Network Security

**Private GKE Clusters**:
```hcl
# In GKE module
private_cluster_config {
  enable_private_nodes    = true   # Nodes have no public IPs
  enable_private_endpoint = false  # Control plane accessible via public IP (with authorized networks)
  master_ipv4_cidr_block  = "172.16.0.0/28"
}

master_authorized_networks_config {
  cidr_blocks {
    cidr_block   = "YOUR_OFFICE_IP/32"
    display_name = "Office Network"
  }
}
```

**VPC Firewall Rules**:
```hcl
# Deny all by default, allow specific traffic
resource "google_compute_firewall" "deny_all_ingress" {
  name    = "deny-all-ingress"
  network = google_compute_network.vpc.id

  deny {
    protocol = "all"
  }

  direction   = "INGRESS"
  priority    = 65535  # Lowest priority (evaluated last)
  source_ranges = ["0.0.0.0/0"]
}
```

### 2. Identity & Access Management

**Workload Identity** (Kubernetes service accounts → GCP service accounts):
```hcl
# Enable on GKE cluster
workload_identity_config {
  workload_pool = "${var.project_id}.svc.id.goog"
}

# Bind Kubernetes SA to GCP SA
resource "google_service_account_iam_binding" "orchestrator_workload_identity" {
  service_account_id = google_service_account.orchestrator.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[octollm-prod/orchestrator]"
  ]
}
```

**Least Privilege IAM**:
```hcl
# Don't use predefined roles like "Editor" or "Owner"
# Use specific roles for each service
resource "google_project_iam_member" "orchestrator_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"  # Can only read secrets
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}
```

### 3. Data Encryption

**At Rest** (enabled by default):
- Cloud SQL: Google-managed encryption keys
- Memorystore: Google-managed encryption keys
- GCS: Google-managed encryption keys

**In Transit** (enforce TLS):
```hcl
# Cloud SQL
resource "google_sql_database_instance" "main" {
  settings {
    ip_configuration {
      require_ssl = true  # Force TLS connections
    }
  }
}

# Redis
resource "google_redis_instance" "main" {
  transit_encryption_mode = "SERVER_AUTHENTICATION"  # TLS required
}
```

**Customer-Managed Encryption Keys (CMEK)** (optional, for compliance):
```hcl
resource "google_kms_key_ring" "octollm" {
  name     = "octollm-keyring"
  location = "us-central1"
}

resource "google_kms_crypto_key" "database_key" {
  name     = "database-encryption-key"
  key_ring = google_kms_key_ring.octollm.id

  rotation_period = "7776000s"  # 90 days
}

# Use in Cloud SQL
resource "google_sql_database_instance" "main" {
  encryption_key_name = google_kms_crypto_key.database_key.id
}
```

### 4. Secrets Management

**Use Secret Manager** (not Kubernetes Secrets):
```bash
# Create secret
echo -n "sk-abc123..." | gcloud secrets create openai-api-key \
  --project=octollm-prod \
  --data-file=-

# Grant access to specific service account
gcloud secrets add-iam-policy-binding openai-api-key \
  --project=octollm-prod \
  --member="serviceAccount:orchestrator@octollm-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Integrate with Kubernetes (External Secrets Operator)**:
```yaml
# See infrastructure/secrets/ directory for full configuration
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: gcpsm-secret-store
spec:
  provider:
    gcpsm:
      projectID: "octollm-prod"
      auth:
        workloadIdentity:
          clusterLocation: us-central1
          clusterName: octollm-prod-cluster
          serviceAccountRef:
            name: external-secrets-sa
```

### 5. Audit Logging

**Enable All Audit Logs**:
```hcl
resource "google_project_iam_audit_config" "audit_all" {
  project = var.project_id
  service = "allServices"

  audit_log_config {
    log_type = "ADMIN_READ"  # Admin actions
  }
  audit_log_config {
    log_type = "DATA_WRITE"  # Data modifications
  }
  audit_log_config {
    log_type = "DATA_READ"   # Data access (expensive, use sparingly)
    exempted_members = [
      "serviceAccount:prometheus@octollm-prod.iam.gserviceaccount.com"
    ]
  }
}
```

**Log Sinks** (export to BigQuery for analysis):
```bash
gcloud logging sinks create audit-log-sink \
  bigquery.googleapis.com/projects/octollm-prod/datasets/audit_logs \
  --log-filter='protoPayload.methodName:"google.iam"'
```

### 6. Binary Authorization (GKE)

**Require signed container images**:
```hcl
resource "google_binary_authorization_policy" "policy" {
  admission_whitelist_patterns {
    name_pattern = "gcr.io/${var.project_id}/*"  # Only allow images from your GCR
  }

  default_admission_rule {
    evaluation_mode  = "REQUIRE_ATTESTATION"
    enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"
    require_attestations_by = [
      google_binary_authorization_attestor.octollm.name
    ]
  }
}
```

---

## Disaster Recovery

### 1. Backup Strategy

**Cloud SQL Automated Backups**:
- Daily backups at 03:00 UTC
- Retention: Dev (7 days), Staging (14 days), Prod (30 days)
- Point-in-time recovery: 7 days (production only)

**Manual Backups** (before major changes):
```bash
gcloud sql backups create \
  --instance=octollm-prod-postgres \
  --description="Pre-migration backup"
```

**Redis Backups**:
- Automatic RDB snapshots (daily)
- Export to GCS for long-term retention:
```bash
gcloud redis instances export gs://octollm-prod-backups/redis-$(date +%Y%m%d).rdb \
  --source=octollm-prod-redis \
  --region=us-central1
```

**GCS Versioning**:
- Enabled on all buckets
- Lifecycle policies to delete old versions

### 2. Recovery Procedures

**Restore PostgreSQL** (point-in-time):
```bash
# Create new instance from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=octollm-prod-postgres \
  --backup-instance-project=octollm-prod

# Or: Clone to new instance
gcloud sql instances clone octollm-prod-postgres octollm-prod-postgres-restored \
  --point-in-time='2024-11-12T03:00:00.000Z'
```

**Restore Redis**:
```bash
gcloud redis instances import gs://octollm-prod-backups/redis-20241112.rdb \
  --source=octollm-prod-redis \
  --region=us-central1
```

**Restore GKE Cluster** (using Terraform state):
```bash
cd infra/environments/prod
terraform apply  # Re-creates cluster from state
```

### 3. Multi-Region Disaster Recovery (Future)

**GCS Multi-Region**:
```hcl
resource "google_storage_bucket" "prod_backups" {
  name          = "octollm-prod-backups"
  location      = "US"  # Multi-region (us-east1, us-west1, us-central1)
  storage_class = "STANDARD"
}
```

**Cross-Region Replication** (PostgreSQL):
```hcl
# Primary instance in us-central1
resource "google_sql_database_instance" "primary" {
  name   = "octollm-prod-postgres-primary"
  region = "us-central1"
}

# Read replica in us-east1 (can be promoted to primary)
resource "google_sql_database_instance" "replica" {
  name                 = "octollm-prod-postgres-replica-us-east1"
  master_instance_name = google_sql_database_instance.primary.name
  region               = "us-east1"

  replica_configuration {
    failover_target = true  # Can be promoted in disaster
  }
}
```

**Multi-Region GKE** (future):
- GKE Multi-Cluster Ingress (traffic routing)
- Cross-region service mesh (Anthos Service Mesh)

---

## Troubleshooting

### Common Issues

**Issue 1: Terraform Init Fails**
```
Error: Failed to get existing workspaces: querying Cloud Storage failed: storage: bucket doesn't exist
```

**Solution**: Create GCS bucket for state:
```bash
gsutil mb -l us-central1 gs://octollm-dev-terraform-state
gsutil versioning set on gs://octollm-dev-terraform-state
```

---

**Issue 2: GKE Cluster Creation Fails**
```
Error: Error creating Cluster: googleapi: Error 403: Kubernetes Engine API is not enabled for project octollm-dev.
```

**Solution**: Enable required APIs:
```bash
gcloud services enable container.googleapis.com --project=octollm-dev
```

---

**Issue 3: Cloud SQL Connection Timeout**
```
Error: could not connect to server: Connection timed out
```

**Solution**: Check network connectivity (private IP requires VPC peering):
```bash
# List authorized networks
gcloud sql instances describe octollm-dev-postgres --format="value(settings.ipConfiguration.authorizedNetworks)"

# Add your IP (if using public IP)
gcloud sql instances patch octollm-dev-postgres \
  --authorized-networks=YOUR_IP/32
```

---

**Issue 4: Terraform Apply Hangs on GKE**
```
Still creating... [10m0s elapsed]
```

**Solution**: GKE cluster creation takes 10-15 minutes (normal). If >20 minutes:
```bash
# Check cluster status
gcloud container clusters describe octollm-dev-cluster --region=us-central1

# Check operations
gcloud container operations list --filter="targetLink:octollm-dev-cluster"
```

---

**Issue 5: Permission Denied Errors**
```
Error: googleapi: Error 403: The caller does not have permission
```

**Solution**: Verify service account has correct roles:
```bash
gcloud projects get-iam-policy octollm-dev \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:terraform-sa@octollm-dev.iam.gserviceaccount.com"
```

---

## Maintenance & Operations

### Terraform State Management

**View State**:
```bash
terraform state list          # List all resources
terraform state show <resource>  # Show resource details
```

**Move Resources** (rename without destroying):
```bash
terraform state mv google_compute_instance.old google_compute_instance.new
```

**Import Existing Resources**:
```bash
# Import GKE cluster created manually
terraform import module.gke.google_container_cluster.primary projects/octollm-dev/locations/us-central1/clusters/octollm-dev-cluster
```

**Remote State Locking** (automatic with GCS backend):
- GCS uses generation-based locking
- If lock stuck (process crashed), manually break:
```bash
gsutil -m rm -a gs://octollm-dev-terraform-state/default.tflock
```

### Upgrading Infrastructure

**Kubernetes Version Upgrade**:
```hcl
# In terraform.tfvars
kubernetes_version = "1.29"  # Update version

# Review upgrade path
terraform plan

# Apply (rolling upgrade, zero downtime)
terraform apply
```

**PostgreSQL Version Upgrade**:
```bash
# Major version upgrade requires downtime
# 1. Create read replica with new version
# 2. Promote replica to primary
# 3. Delete old primary

# Or: In-place upgrade (simpler, but downtime)
gcloud sql instances patch octollm-prod-postgres \
  --database-version=POSTGRES_16 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=3
```

**Redis Version Upgrade**:
```bash
# Automatic during maintenance window
gcloud redis instances patch octollm-prod-redis \
  --redis-version=REDIS_7_2 \
  --region=us-central1
```

### Scaling Operations

**Horizontal Scaling (GKE nodes)**:
```bash
# Manually adjust node pool size
gcloud container clusters resize octollm-prod-cluster \
  --num-nodes=10 \
  --node-pool=default \
  --region=us-central1

# Or: Update Terraform variables
# terraform.tfvars: max_nodes = 20
terraform apply
```

**Vertical Scaling (PostgreSQL)**:
```bash
# Change machine type (requires restart)
gcloud sql instances patch octollm-prod-postgres \
  --tier=db-n1-standard-8  # Upgrade to 8vCPU, 30GB RAM
```

**Database Storage Expansion**:
```bash
# Automatic with disk_autoresize = true
# Or manual:
gcloud sql instances patch octollm-prod-postgres \
  --storage-size=500GB
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/terraform-apply.yml
name: Terraform Apply

on:
  push:
    branches: [main]
    paths: ['infra/**']

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra/environments/prod

    steps:
      - uses: actions/checkout@v3

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.6.6

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Terraform Init
        run: terraform init

      - name: Terraform Plan
        run: terraform plan -out=tfplan

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve tfplan
```

---

## Additional Resources

**Official Documentation**:
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Memorystore Documentation](https://cloud.google.com/memorystore/docs)

**OctoLLM Documentation**:
- [ADR-006: Cloud Provider Selection](../docs/adr/006-cloud-provider-selection.md)
- [Deployment Guide](../docs/operations/deployment-guide.md)
- [Kubernetes Access Guide](../docs/operations/kubernetes-access.md)
- [Database Backup & Recovery](../docs/operations/database-backup-recovery.md)
- [Secrets Management Strategy](../docs/security/secrets-management-strategy.md)

**Community**:
- [Terraform Google Modules](https://github.com/terraform-google-modules)
- [r/googlecloud](https://reddit.com/r/googlecloud)
- [GCP Slack Community](https://googlecloud-community.slack.com)

---

**Maintained By**: DevOps Team
**Last Updated**: 2025-11-12
**Version**: 1.0.0 (Sprint 0.7)
