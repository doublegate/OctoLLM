# Deployment Guide

OctoLLM supports multiple deployment options: Docker Compose for local development, Kubernetes for production, and Unraid for home lab environments.

## Deployment Options

### Docker Compose

**Best for**: Local development, testing, small deployments

[Docker Compose Setup Guide](./docker-compose-setup.md)

### Kubernetes

**Best for**: Production deployments, auto-scaling, high availability

[Kubernetes Deployment Guide](./kubernetes-deployment.md)

### Unraid

**Best for**: Home lab deployments, personal infrastructure

[Unraid Deployment Guide](./unraid-deployment-guide.md)

## Quick Comparison

| Feature | Docker Compose | Kubernetes | Unraid |
|---------|---------------|------------|---------|
| Setup Complexity | Low | High | Medium |
| Scaling | Manual | Automatic | Manual |
| High Availability | No | Yes | No |
| Monitoring | Basic | Advanced | Medium |
| Best Use Case | Development | Production | Home Lab |

## See Also

- [Operations Overview](./monitoring-alerting.md)
- [Scaling Guide](./scaling.md)
- [Performance Tuning](./performance-tuning.md)
