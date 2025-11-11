# OctoLLM Infrastructure

This directory contains infrastructure as code (IaC) for deploying OctoLLM across different environments.

## Structure

```
infrastructure/
├── terraform/           # Terraform modules and configurations
│   ├── modules/        # Reusable Terraform modules
│   │   ├── vpc/        # VPC networking
│   │   ├── eks/        # Kubernetes cluster
│   │   ├── rds/        # PostgreSQL database
│   │   ├── elasticache/# Redis cache
│   │   ├── s3/         # Object storage
│   │   └── iam/        # IAM roles and policies
│   └── environments/   # Environment-specific configurations
│       ├── dev/        # Development
│       ├── staging/    # Staging
│       └── prod/       # Production
├── kubernetes/         # Kubernetes manifests
│   ├── base/          # Base Kustomize configurations
│   ├── overlays/      # Environment overlays
│   └── charts/        # Helm charts
└── docker-compose/    # Docker Compose for local development
```

## Usage

### Local Development (Docker Compose)

```bash
cd docker-compose
docker-compose up -d
```

### Terraform (AWS Infrastructure)

```bash
cd terraform/environments/dev
terraform init
terraform plan
terraform apply
```

### Kubernetes Deployment

```bash
cd kubernetes
kubectl apply -k overlays/dev/
```

## References

- [Deployment Guide](../docs/operations/deployment-guide.md)
- [Infrastructure Design](../docs/architecture/infrastructure-design.md)
- [Terraform Modules](../docs/operations/terraform-modules.md)
