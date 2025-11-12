# Development Environment

**Environment**: Development
**Cost**: ~$192/month
**Purpose**: Local development, testing, experimentation

## Quick Start

```bash
# 1. Copy example variables
cp terraform.tfvars.example terraform.tfvars

# 2. Edit terraform.tfvars with your project ID
vim terraform.tfvars

# 3. Initialize Terraform
terraform init

# 4. Review plan
terraform plan

# 5. Apply (provision infrastructure)
terraform apply

# 6. Configure kubectl
gcloud container clusters get-credentials octollm-dev-cluster --region us-central1

# 7. Verify
kubectl get nodes
```

## Resources Created

- **GKE Cluster**: 1-3 nodes, e2-standard-2, preemptible
- **PostgreSQL**: db-f1-micro, 20GB, no HA
- **Redis**: BASIC tier, 2GB
- **Storage**: 2 buckets (backups, logs)
- **Network**: VPC with subnets, NAT gateway

## Cost Optimization

- FREE GKE control plane
- Preemptible VMs (60-91% discount)
- Minimal instance sizes
- Short retention policies

## Maintenance

```bash
# Update infrastructure
terraform plan
terraform apply

# Destroy (when done)
terraform destroy
```
