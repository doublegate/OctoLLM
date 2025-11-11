# Infrastructure

Infrastructure as Code (IaC) and deployment configurations for OctoLLM.

## Structure

```
infrastructure/
├── terraform/           # Terraform modules for AWS/GCP/Azure
│   ├── modules/         # Reusable modules (VPC, EKS, RDS, etc.)
│   └── environments/    # Environment-specific configs (dev/staging/prod)
├── kubernetes/          # Kubernetes manifests
│   ├── base/            # Base configurations
│   ├── overlays/        # Kustomize overlays per environment
│   └── charts/          # Helm charts
└── docker-compose/      # Local development with Docker Compose
```

## Terraform Modules

- **vpc** - Virtual Private Cloud with public/private subnets
- **eks** - Elastic Kubernetes Service cluster
- **rds** - PostgreSQL database (Multi-AZ)
- **elasticache** - Redis cluster
- **s3** - Object storage for backups/artifacts
- **iam** - Service accounts and IRSA roles

## Kubernetes Resources

- **Namespaces**: octollm-dev, octollm-staging, octollm-prod
- **Deployments**: Orchestrator, Reflex, 6 Arms
- **Services**: ClusterIP for internal, LoadBalancer for ingress
- **ConfigMaps**: Environment-specific configuration
- **Secrets**: External Secrets Operator (AWS Secrets Manager)
- **Ingress**: NGINX with TLS (cert-manager)

## Docker Compose

For local development without Kubernetes:

```bash
cd infrastructure/docker-compose
docker-compose up -d
```

Services:
- orchestrator:8000
- reflex-layer:8080
- planner:8001, executor:8002, retriever:8003, coder:8004, judge:8005, safety-guardian:8006
- postgres:5432, redis:6379, qdrant:6333
- prometheus:9090, grafana:3000

## Development

```bash
# Terraform
cd infrastructure/terraform/environments/dev
terraform init
terraform plan
terraform apply

# Kubernetes
cd infrastructure/kubernetes
kubectl apply -k overlays/dev

# Docker Compose
cd infrastructure/docker-compose
docker-compose up -d
```

## References

- [Deployment Guide](../docs/operations/deployment-guide.md)
- [Kubernetes Deployment](../docs/operations/kubernetes-deployment.md)
- [Docker Compose Setup](../docs/operations/docker-compose-setup.md)
