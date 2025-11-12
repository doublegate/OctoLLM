# ADR-006: Cloud Provider Selection

**Status**: Accepted
**Date**: 2025-11-12
**Decision Makers**: Architecture Team, DevOps Team, Finance Team
**Consulted**: Engineering Team, Security Team, Operations Team

## Context

OctoLLM requires a cloud infrastructure provider to host production, staging, and development environments. As established in **ADR-005 (Deployment Platform)**, we have decided to use **Kubernetes for production** with a cloud-agnostic architecture. This ADR focuses on selecting the specific cloud provider for managed services while maintaining portability.

### Infrastructure Requirements

**Core Services Needed**:
1. **Kubernetes Service**: Managed Kubernetes cluster (1.28+)
2. **Managed PostgreSQL**: PostgreSQL 15+ with HA, read replicas, automated backups
3. **Managed Redis**: Redis 7+ with cluster mode, persistence, automatic failover
4. **Object Storage**: S3-compatible storage for backups, logs, artifacts
5. **Secrets Management**: Secure storage for API keys, certificates, passwords
6. **Load Balancing**: Layer 7 load balancers with TLS termination
7. **DNS Management**: Managed DNS with health checks
8. **Monitoring & Logging**: Metrics, logs, distributed tracing capabilities

**Deployment Environments**:
- **Development**: Minimal resources, cost-optimized, single-region
- **Staging**: Production-like, scaled down 50%, multi-AZ
- **Production**: Full HA, multi-AZ, auto-scaling, 99.95% SLA

**Resource Specifications** (from MASTER-TODO.md Sprint 0.7):

| Environment | Kubernetes Nodes | PostgreSQL | Redis | Monthly Est. |
|-------------|------------------|------------|-------|--------------|
| Development | 3 nodes (2vCPU, 8GB) | 1vCPU, 2GB, 20GB | 2GB single | $200-400 |
| Staging | 4 nodes (4vCPU, 16GB) | 2vCPU, 8GB, 100GB | 3GB cluster | $600-1,000 |
| Production | 5-15 nodes (8vCPU, 32GB) | 4vCPU, 16GB, 200GB + 2 replicas | 3 masters + 3 replicas @ 6GB | $2,500-5,000 |

**Key Decision Criteria**:
1. **Cost**: Total cost of ownership (TCO) across all environments
2. **Kubernetes Maturity**: Feature set, stability, ecosystem integration
3. **Database Performance**: PostgreSQL and Redis managed service quality
4. **Developer Experience**: Ease of setup, documentation, tooling
5. **Security & Compliance**: SOC 2, ISO 27001, GDPR capabilities
6. **Geographic Coverage**: Low-latency access for target users
7. **Free Tier**: Development and experimentation capabilities
8. **Migration Path**: Ease of multi-cloud or exit strategy
9. **Monitoring & Observability**: Native tools for metrics, logs, traces
10. **Community & Support**: Documentation quality, community size, support options

### Evaluation Constraints

- **Budget**: Target $500/month for dev + staging, $3,000/month for production
- **Timeline**: Infrastructure must be provisionable within 1 week
- **Skills**: Team has moderate cloud experience, strong Kubernetes knowledge
- **Compliance**: Must support future SOC 2 Type II certification
- **Portability**: Infrastructure must be cloud-agnostic (use standard APIs)

## Research & Analysis

### 1. Amazon Web Services (AWS)

**Kubernetes Service**: Amazon Elastic Kubernetes Service (EKS)
**Managed PostgreSQL**: Amazon RDS for PostgreSQL
**Managed Redis**: Amazon ElastiCache for Redis
**Object Storage**: Amazon S3
**Secrets Management**: AWS Secrets Manager

#### Strengths

**Kubernetes (EKS)**:
- Mature service (GA since 2018)
- Excellent control plane HA (99.95% SLA)
- Native integration with AWS services (IAM, CloudWatch, ELB)
- Fargate support for serverless node pools
- Managed node groups with auto-scaling
- EKS Anywhere for hybrid/on-prem (portability)
- Extensive ecosystem (add-ons, operators)

**Database (RDS PostgreSQL)**:
- PostgreSQL 15+ support
- Automated backups (35-day retention max)
- Multi-AZ deployments with automatic failover (<2 min)
- Read replicas (up to 15) with cross-region support
- Performance Insights for query optimization
- Aurora PostgreSQL option (5x performance, higher cost)
- Proxy support (RDS Proxy) for connection pooling

**Redis (ElastiCache)**:
- Redis 7.0+ support
- Cluster mode with auto-sharding (up to 500 nodes)
- Multi-AZ with automatic failover
- Daily backups with point-in-time recovery
- Encryption at rest and in transit
- Global Datastore for multi-region replication

**Storage (S3)**:
- Industry-leading 99.999999999% durability (11 nines)
- Lifecycle policies for cost optimization
- Versioning, replication, encryption
- Glacier for long-term archival (lowest cost)
- S3 Express One Zone for ultra-low latency

**Secrets (Secrets Manager)**:
- Automatic rotation for RDS, Redshift, DocumentDB
- Fine-grained IAM policies
- Encryption with KMS
- Cross-region replication
- Versioning and rollback

**Monitoring**:
- CloudWatch for metrics (1-minute resolution, 15-month retention)
- CloudWatch Logs for centralized logging
- X-Ray for distributed tracing
- Container Insights for EKS-specific metrics

**Developer Experience**:
- AWS CLI (mature, feature-complete)
- eksctl for simplified EKS operations
- AWS CDK for infrastructure as code (TypeScript/Python)
- Extensive Terraform modules (community-maintained)
- Copilot CLI for containerized apps
- Comprehensive documentation (best-in-class)

**Geographic Coverage**:
- 32 regions, 102 availability zones (as of 2024)
- Excellent global coverage (US, EU, Asia-Pacific, Middle East, South America)
- Low-latency access for most OctoLLM users (US-based initially)

**Free Tier**:
- 750 hours/month EC2 t2.micro (12 months)
- 20GB RDS PostgreSQL (12 months)
- 5GB S3 storage (always free)
- 1 million Lambda requests/month (always free)
- **No free tier for EKS** ($0.10/hour = $73/month per cluster)

**Compliance**:
- SOC 2 Type II certified
- ISO 27001, 27017, 27018
- GDPR, HIPAA, PCI DSS compliant
- 143 compliance certifications (most comprehensive)

#### Weaknesses

**Cost**:
- EKS control plane: $0.10/hour ($73/month per cluster)
- More expensive than GCP/Azure for compute (10-15% higher)
- Data transfer costs can be significant (egress: $0.09/GB)
- RDS pricing higher than CloudSQL/Azure Database

**Complexity**:
- Steeper learning curve (vast service catalog)
- IAM complexity (policies, roles, users, groups)
- Networking setup more involved (VPC, subnets, route tables, NAT)

**Vendor Lock-in Risk**:
- Easy to use AWS-specific services (DynamoDB, Lambda)
- Proprietary APIs (CloudWatch, X-Ray)
- Aurora PostgreSQL not portable

#### Cost Estimate (per month)

**Development Environment**:
- EKS cluster: $73 (control plane)
- EC2 nodes: 3 × t3.large (2vCPU, 8GB): $150
- RDS PostgreSQL: db.t3.micro (1vCPU, 2GB): $30
- ElastiCache Redis: cache.t3.micro (2GB): $35
- S3: 50GB + requests: $5
- Data transfer: $10
- **Total: ~$303/month**

**Staging Environment**:
- EKS cluster: $73
- EC2 nodes: 4 × t3.xlarge (4vCPU, 16GB): $400
- RDS PostgreSQL: db.t3.medium (2vCPU, 8GB): $120
- ElastiCache Redis: cache.r6g.large (3GB cluster): $150
- S3: 200GB + requests: $15
- Data transfer: $30
- **Total: ~$788/month**

**Production Environment**:
- EKS cluster: $73
- EC2 nodes: 5-10 × m6i.2xlarge (8vCPU, 32GB): $2,400 (avg 7.5 nodes)
- RDS PostgreSQL: db.r6g.xlarge (4vCPU, 16GB) + 2 read replicas: $900
- ElastiCache Redis: cache.r6g.xlarge (6GB) × 6 (cluster): $900
- S3: 1TB + requests: $50
- Load Balancer (ALB): $30
- NAT Gateway: $90
- Data transfer: $200
- **Total: ~$4,643/month**

**Total All Environments**: ~$5,734/month

---

### 2. Google Cloud Platform (GCP)

**Kubernetes Service**: Google Kubernetes Engine (GKE)
**Managed PostgreSQL**: Cloud SQL for PostgreSQL
**Managed Redis**: Memorystore for Redis
**Object Storage**: Google Cloud Storage (GCS)
**Secrets Management**: Secret Manager

#### Strengths

**Kubernetes (GKE)**:
- **Best-in-class Kubernetes** (Google created Kubernetes)
- Autopilot mode: fully managed, serverless, pay-per-pod
- Standard mode: flexible, full control
- Automatic node repairs and upgrades
- Built-in container security (Binary Authorization, GKE Sandbox)
- Multi-cluster Ingress (traffic routing across clusters)
- Workload Identity (native Kubernetes service account integration)
- **Free control plane for Standard mode** (below 3 zones)
- GKE Enterprise (formerly Anthos) for multi-cloud/hybrid

**Database (Cloud SQL PostgreSQL)**:
- PostgreSQL 15+ support
- High availability with automatic failover (<60 seconds)
- Up to 10 read replicas
- Automated backups (365-day retention max)
- Point-in-time recovery (7 days)
- Connection pooling built-in (PgBouncer)
- Query Insights for performance analysis
- **15-25% cheaper than RDS** (similar specs)

**Redis (Memorystore)**:
- Redis 7.0+ support
- High availability with automatic failover
- **Extremely low latency** (<1ms within region)
- Read replicas for read-heavy workloads
- Import/export capabilities
- **No cluster mode** (scaling limited to 300GB per instance)

**Storage (GCS)**:
- 99.999999999% durability (same as S3)
- Multi-region and dual-region options
- Lifecycle management
- Object versioning
- Nearline/Coldline/Archive for cost optimization
- Signed URLs for temporary access

**Secrets (Secret Manager)**:
- Automatic versioning
- IAM integration
- Encryption with Cloud KMS
- Audit logging with Cloud Audit Logs
- **Simpler than AWS Secrets Manager** (less feature-rich but easier)

**Monitoring**:
- Cloud Monitoring (formerly Stackdriver)
- Cloud Logging (centralized logs, 30-day default retention)
- Cloud Trace (distributed tracing)
- GKE observability built-in (metrics, logs, traces)
- **Better integration than AWS** (single pane of glass)

**Developer Experience**:
- gcloud CLI (well-designed, intuitive)
- GKE-specific commands (gcloud container)
- Google Cloud Console (modern UI, fastest)
- Terraform support (official provider, well-maintained)
- **Excellent documentation** (clear, concise)
- Cloud Shell (browser-based development environment)

**Geographic Coverage**:
- 40 regions, 121 zones (as of 2024)
- **Best regional expansion** (new regions frequently)
- Strong Asia-Pacific presence
- Multi-region resources (Cloud SQL, GCS)

**Free Tier**:
- **GKE Standard: FREE control plane** (autopilot mode free for <18 hours/month)
- $300 free credit for 90 days (new accounts)
- Always free: 1 non-preemptible e2-micro VM
- Always free: 5GB Cloud Storage (regional)
- **Best free tier for Kubernetes experimentation**

**Compliance**:
- SOC 2 Type II certified
- ISO 27001, 27017, 27018
- GDPR, HIPAA, PCI DSS compliant
- 80+ compliance certifications

#### Weaknesses

**Kubernetes**:
- Autopilot mode limitations (less control, some add-ons unsupported)
- Fewer managed add-ons than EKS (no Fargate equivalent)

**Redis**:
- **No cluster mode** (major limitation for high-scale workloads)
- Maximum 300GB per instance (ElastiCache supports terabytes)
- Fewer sharding options

**Ecosystem**:
- Smaller community than AWS (fewer third-party integrations)
- Less enterprise adoption (compared to AWS/Azure)

**Support**:
- Support plans more expensive than AWS (for similar tiers)
- Fewer certified partners for consulting/implementation

**Vendor Lock-in Risk**:
- BigQuery, Pub/Sub, Cloud Functions (proprietary)
- GKE Autopilot tight coupling

#### Cost Estimate (per month)

**Development Environment**:
- GKE cluster: **$0** (free control plane for <3 zones)
- Compute Engine: 3 × e2-standard-2 (2vCPU, 8GB): $120
- Cloud SQL PostgreSQL: db-f1-micro (1vCPU, 3.75GB): $25
- Memorystore Redis: Basic tier (2GB): $40
- Cloud Storage: 50GB: $2
- Data transfer: $5
- **Total: ~$192/month** (36% cheaper than AWS)

**Staging Environment**:
- GKE cluster: **$0**
- Compute Engine: 4 × e2-standard-4 (4vCPU, 16GB): $340
- Cloud SQL PostgreSQL: db-n1-standard-2 (2vCPU, 7.5GB): $100
- Memorystore Redis: Standard tier (3GB): $120
- Cloud Storage: 200GB: $8
- Data transfer: $20
- **Total: ~$588/month** (25% cheaper than AWS)

**Production Environment**:
- GKE cluster: $73 (3+ zones = paid)
- Compute Engine: 5-10 × n2-standard-8 (8vCPU, 32GB): $2,000 (avg 7.5 nodes)
- Cloud SQL PostgreSQL: db-n1-standard-4 (4vCPU, 15GB) + 2 replicas: $700
- Memorystore Redis: Standard tier (6GB) × 3 (manual sharding): $650
- Cloud Storage: 1TB: $40
- Load Balancer: $25
- Cloud NAT: $45
- Data transfer: $150
- **Total: ~$3,683/month** (21% cheaper than AWS)

**Total All Environments**: ~$4,463/month (22% cheaper than AWS)

---

### 3. Microsoft Azure

**Kubernetes Service**: Azure Kubernetes Service (AKS)
**Managed PostgreSQL**: Azure Database for PostgreSQL Flexible Server
**Managed Redis**: Azure Cache for Redis
**Object Storage**: Azure Blob Storage
**Secrets Management**: Azure Key Vault

#### Strengths

**Kubernetes (AKS)**:
- **Free control plane** (no hourly charge)
- Azure CNI for native VNet integration
- Azure AD integration for RBAC
- Virtual nodes (ACI for serverless pods)
- Dev Spaces for collaborative development
- Azure Policy for governance
- Excellent Windows container support
- Azure Arc for multi-cloud Kubernetes management

**Database (Azure Database for PostgreSQL)**:
- PostgreSQL 15+ support (Flexible Server)
- High availability with zone-redundant deployment
- Up to 5 read replicas
- Automated backups (35-day retention)
- Point-in-time recovery
- **Burstable SKUs** (B-series) for cost-effective dev/test
- Hyperscale (Citus) option for distributed PostgreSQL

**Redis (Azure Cache for Redis)**:
- Redis 6.0+ support (7.0 in preview)
- Enterprise tier with Redis Enterprise features
- Clustering support (Premium/Enterprise tiers)
- Active geo-replication (Enterprise)
- Zone redundancy for HA
- **Best Redis integration** (first-party Redis Enterprise)

**Storage (Blob Storage)**:
- 99.999999999% durability (LRS)
- Hot, Cool, Archive tiers
- Immutable storage for compliance
- Soft delete and versioning
- Azure Data Lake Storage Gen2 (big data analytics)

**Secrets (Key Vault)**:
- Secrets, keys, certificates in single service
- HSM-backed keys (Premium tier)
- Managed identity integration
- RBAC and access policies
- Automatic rotation (Azure SQL, Storage Accounts)

**Monitoring**:
- Azure Monitor (unified platform)
- Log Analytics (Kusto Query Language)
- Application Insights (APM for apps)
- Container Insights (AKS-specific)
- Azure Monitor for Prometheus (managed Prometheus)

**Developer Experience**:
- Azure CLI (powerful, consistent)
- Azure Portal (feature-rich, can be overwhelming)
- Bicep for IaC (DSL, simpler than ARM templates)
- Terraform support (official provider)
- **Best Windows/hybrid integration**
- GitHub Actions integration (Microsoft-owned)

**Geographic Coverage**:
- 60+ regions (most of any cloud provider)
- Strong presence in Europe, Asia, US
- Government clouds (Azure Government)
- Azure Stack for on-premises

**Free Tier**:
- $200 Azure credit for 30 days (new accounts)
- 12 months free: 750 hours B1S VM, 5GB Blob Storage
- **AKS: FREE control plane**
- Always free: 10 App Services, 1GB Storage

**Compliance**:
- SOC 2 Type II certified
- ISO 27001, 27017, 27018
- GDPR, HIPAA, PCI DSS compliant
- 100+ compliance certifications
- **Best for government/regulated industries**

#### Weaknesses

**Kubernetes**:
- AKS upgrade process can be disruptive
- Less mature than GKE (created by Google)
- Networking complexity (Azure CNI vs kubenet)

**Database**:
- PostgreSQL 15 released later than AWS/GCP
- Fewer PostgreSQL extensions than RDS
- Connection limits lower than RDS (for same SKU)

**Redis**:
- Redis 7.0 still in preview (as of Nov 2024)
- Enterprise tier very expensive (3-5x Premium tier)
- Basic tier has no SLA

**Ecosystem**:
- Smaller Kubernetes community than GKE/EKS
- Fewer Kubernetes-specific tools and integrations

**Documentation**:
- Quality inconsistent (some areas excellent, others lacking)
- Frequent rebranding causes confusion
- Examples sometimes outdated

**Vendor Lock-in Risk**:
- Azure Functions, Cosmos DB, Service Bus (proprietary)
- Azure AD tight coupling
- ARM templates complex (Bicep mitigates)

#### Cost Estimate (per month)

**Development Environment**:
- AKS cluster: **$0** (free control plane)
- Virtual Machines: 3 × Standard_D2s_v3 (2vCPU, 8GB): $130
- Azure Database PostgreSQL: B1ms (1vCPU, 2GB): $20
- Azure Cache Redis: Basic C1 (1GB): $20 (note: 1GB minimum, not 2GB)
- Blob Storage: 50GB (Hot): $3
- Data transfer: $5
- **Total: ~$178/month** (41% cheaper than AWS, 7% cheaper than GCP)

**Staging Environment**:
- AKS cluster: **$0**
- Virtual Machines: 4 × Standard_D4s_v3 (4vCPU, 16GB): $360
- Azure Database PostgreSQL: GP_Standard_D2s_v3 (2vCPU, 8GB): $110
- Azure Cache Redis: Standard C3 (3GB): $100
- Blob Storage: 200GB (Hot): $10
- Data transfer: $20
- **Total: ~$600/month** (24% cheaper than AWS, 2% more than GCP)

**Production Environment**:
- AKS cluster: **$0**
- Virtual Machines: 5-10 × Standard_D8s_v3 (8vCPU, 32GB): $2,100 (avg 7.5 nodes)
- Azure Database PostgreSQL: GP_Standard_D4s_v3 (4vCPU, 16GB) + 2 replicas: $750
- Azure Cache Redis: Premium P3 (6GB) × 3 nodes (cluster): $750
- Blob Storage: 1TB (Hot): $45
- Load Balancer: $20
- NAT Gateway: $40
- Data transfer: $150
- **Total: ~$3,855/month** (17% cheaper than AWS, 5% more than GCP)

**Total All Environments**: ~$4,633/month (19% cheaper than AWS, 4% more than GCP)

---

## Detailed Comparison Matrix

### Cost Comparison (Monthly)

| Environment | AWS | GCP | Azure | Winner |
|-------------|-----|-----|-------|--------|
| Development | $303 | **$192** | $178 | **Azure** (-41%) |
| Staging | $788 | **$588** | $600 | **GCP** (-25%) |
| Production | $4,643 | **$3,683** | $3,855 | **GCP** (-21%) |
| **Total** | $5,734 | **$4,463** | $4,633 | **GCP** (-22%) |

**Annual Cost Savings** (vs AWS):
- GCP: **$15,252 saved/year** (22% reduction)
- Azure: **$13,212 saved/year** (19% reduction)

### Feature Comparison

| Feature | AWS | GCP | Azure | Winner |
|---------|-----|-----|-------|--------|
| **Kubernetes Maturity** | 4/5 | **5/5** | 3.5/5 | **GCP** |
| Kubernetes Cost | $73/month | **$0** (free) | **$0** (free) | **GCP/Azure** |
| Kubernetes Features | Excellent | **Best** | Very Good | **GCP** |
| Kubernetes DX | Good | **Excellent** | Good | **GCP** |
| PostgreSQL Performance | Excellent | Very Good | Good | **AWS** |
| PostgreSQL Features | **Most** | Good | Good | **AWS** |
| PostgreSQL Cost | $900 | **$700** | $750 | **GCP** |
| Redis Performance | Excellent | **Excellent** | Very Good | **AWS/GCP** |
| Redis Clustering | Excellent | **Limited** | Good | **AWS** |
| Redis Cost | $900 | **$650** | $750 | **GCP** |
| Object Storage | **S3** (best) | GCS (excellent) | Blob (good) | **AWS** |
| Secrets Management | **Best** | Good | Very Good | **AWS** |
| Monitoring/Observability | Very Good | **Excellent** | Good | **GCP** |
| Documentation Quality | **Excellent** | **Excellent** | Good | **AWS/GCP** |
| CLI Experience | Good | **Excellent** | Good | **GCP** |
| Free Tier (Dev) | Limited | **Best** | Good | **GCP** |
| Geographic Coverage | Very Good | Very Good | **Best** | **Azure** |
| Compliance Certifications | **143** | 80+ | 100+ | **AWS** |
| Community Size | **Largest** | Large | Medium | **AWS** |
| Ecosystem Maturity | **Most Mature** | Mature | Growing | **AWS** |

### Developer Experience Comparison

| Aspect | AWS | GCP | Azure | Winner |
|--------|-----|-----|-------|--------|
| Setup Time (0-1st cluster) | 60 min | **30 min** | 45 min | **GCP** |
| CLI Quality | Good | **Excellent** | Good | **GCP** |
| Web Console | Functional | **Modern** | Feature-rich | **GCP** |
| Terraform Support | **Excellent** | Excellent | Good | **AWS** |
| Documentation Clarity | **Excellent** | **Excellent** | Fair | **AWS/GCP** |
| Local Dev Tools | Good | **Best** | Good | **GCP** |
| Debugging Experience | Good | **Excellent** | Fair | **GCP** |
| Learning Curve | Steep | **Gentle** | Moderate | **GCP** |

### Security & Compliance Comparison

| Aspect | AWS | GCP | Azure | Winner |
|--------|-----|-----|-------|--------|
| Compliance Certs | **143** | 80+ | 100+ | **AWS** |
| SOC 2 Type II | ✅ | ✅ | ✅ | **Tie** |
| ISO 27001 | ✅ | ✅ | ✅ | **Tie** |
| GDPR | ✅ | ✅ | ✅ | **Tie** |
| HIPAA | ✅ | ✅ | ✅ | **Tie** |
| Government Cloud | ✅ AWS GovCloud | ❌ | ✅ **Azure Gov** | **Azure** |
| Identity Management | IAM (complex) | IAM (good) | **Azure AD** (best) | **Azure** |
| Network Security | **Best** | Very Good | Good | **AWS** |
| Encryption at Rest | ✅ | ✅ | ✅ | **Tie** |
| Encryption in Transit | ✅ | ✅ | ✅ | **Tie** |
| Key Management | **KMS** (best) | Cloud KMS (good) | Key Vault (good) | **AWS** |

### Portability & Lock-in Risk

| Aspect | AWS | GCP | Azure | Winner |
|--------|-----|-----|-------|--------|
| Standard Kubernetes | ✅ | ✅ | ✅ | **Tie** |
| Proprietary K8s Features | Moderate | Low | Moderate | **GCP** |
| Standard PostgreSQL | ✅ | ✅ | ✅ | **Tie** |
| Proprietary DB Features | Aurora | Spanner | Cosmos DB | **N/A** |
| Standard Redis | ✅ | ✅ | ✅ | **Tie** |
| S3-Compatible Storage | **S3** (standard) | GCS (compatible) | Blob (compatible) | **AWS** |
| Vendor-Specific APIs | High | Moderate | High | **GCP** |
| Multi-Cloud Tools | EKS Anywhere | **Anthos** | Azure Arc | **GCP** |
| Exit Difficulty | Moderate | **Low** | Moderate | **GCP** |

### Support & Community

| Aspect | AWS | GCP | Azure | Winner |
|--------|-----|-----|-------|--------|
| Community Size | **Largest** | Large | Medium | **AWS** |
| Stack Overflow Questions | **500k+** | 200k+ | 300k+ | **AWS** |
| GitHub Stars (tools) | **Highest** | High | Medium | **AWS** |
| Third-Party Integrations | **Most** | Many | Good | **AWS** |
| Training Resources | **Most** | Many | Many | **AWS** |
| Official Certifications | **Most** | Good | Good | **AWS** |
| Support Plans (cost) | Moderate | High | Moderate | **AWS/Azure** |
| Support Response Time | Good | Good | Good | **Tie** |

---

## Decision

**We choose Google Cloud Platform (GCP) as our primary cloud provider for the following reasons:**

### Primary Factors

1. **Cost Efficiency** (Weight: 30%)
   - **22% cheaper than AWS** ($15,252/year savings)
   - **4% cheaper than Azure** ($2,040/year savings)
   - **Free Kubernetes control plane** (saves $876/year vs AWS)
   - Best free tier for development and experimentation

2. **Kubernetes Excellence** (Weight: 25%)
   - **Google created Kubernetes** (unmatched expertise)
   - GKE is the most mature, feature-rich Kubernetes service
   - Autopilot mode for simplified operations
   - Workload Identity (best practice for service accounts)
   - Excellent documentation and tooling

3. **Developer Experience** (Weight: 20%)
   - **Fastest setup time** (30 min to first cluster)
   - **Best CLI** (gcloud intuitive, well-designed)
   - Modern, responsive web console
   - Excellent observability (single pane of glass)
   - Cloud Shell for browser-based development

4. **Portability** (Weight: 15%)
   - **Lowest vendor lock-in risk**
   - Standard Kubernetes (minimal proprietary features)
   - Multi-cloud strategy with Anthos (if needed)
   - Easy migration path to other providers

5. **Performance** (Weight: 10%)
   - **Best Kubernetes performance** (Google's expertise)
   - Memorystore for Redis: <1ms latency
   - Cloud SQL competitive with RDS
   - Excellent network performance (Google's backbone)

### Trade-offs Accepted

**Limitations vs AWS**:
- Smaller ecosystem (fewer third-party integrations)
- Fewer compliance certifications (143 vs 80+)
- Redis cluster mode limited (300GB max per instance)
- Smaller community (200k+ vs 500k+ Stack Overflow questions)

**Mitigation Strategies**:
- Redis limitation: Use manual sharding (3 instances) for production
- Ecosystem: AWS services available via APIs (e.g., AWS SDK for S3 backups)
- Community: GCP community large enough for OctoLLM needs
- Compliance: 80+ certifications sufficient for current requirements

**Why Not AWS**:
- 22% more expensive ($15,252/year difference)
- Paid Kubernetes control plane ($876/year)
- Steeper learning curve (complexity overkill for OctoLLM)
- Higher vendor lock-in risk (easy to use proprietary services)

**Why Not Azure**:
- 4% more expensive than GCP ($2,040/year)
- Kubernetes less mature than GKE
- PostgreSQL 15 support lagged behind competitors
- Smaller Kubernetes ecosystem
- Documentation quality inconsistent

### Cloud-Agnostic Architecture (Portability Safeguards)

To maintain portability and avoid lock-in, we will:

1. **Use Standard Kubernetes APIs**:
   - No GKE-specific CRDs (Custom Resource Definitions)
   - Avoid GKE Autopilot for production (use Standard mode)
   - Use standard Ingress, not GKE-specific LoadBalancer

2. **Abstract Cloud Services**:
   - PostgreSQL: Standard libpq connection strings
   - Redis: Standard Redis protocol (no GCP-specific features)
   - Object Storage: S3-compatible API (GCS supports this)

3. **Infrastructure as Code (Terraform)**:
   - Use Terraform with provider abstraction
   - Modular design (swap providers by changing modules)
   - No hard-coded GCP resource IDs

4. **Monitoring**: Use Prometheus/Grafana (not Cloud Monitoring alone)

5. **Secrets**: ExternalSecrets Operator (supports multiple backends)

6. **CI/CD**: GitHub Actions (provider-agnostic, not Cloud Build)

### Migration Path (if needed)

If we need to migrate to AWS or Azure:

| Component | Migration Effort | Time Estimate |
|-----------|------------------|---------------|
| Kubernetes manifests | Low | 1-2 days |
| Terraform modules | Moderate | 3-5 days |
| PostgreSQL data | Low | 1 day (dump/restore) |
| Redis data | Low | 1 day (export/import) |
| Object storage | Low | 1-2 days (rclone sync) |
| Secrets | Moderate | 2-3 days |
| DNS/Certificates | Low | 1 day |
| Monitoring | Moderate | 3-5 days |
| **Total** | **Moderate** | **2-3 weeks** |

---

## Consequences

### Positive

1. **Cost Savings**: $15,252/year compared to AWS (22% reduction)
2. **Best Kubernetes**: Leveraging Google's Kubernetes expertise
3. **Fast Development**: Free control plane + excellent DX = faster iteration
4. **Simple Operations**: GKE Autopilot option for less operational overhead
5. **Strong Observability**: Cloud Monitoring/Logging/Trace integrated
6. **Low Lock-in**: Easy migration to other clouds if needed
7. **Scalability**: GKE supports large-scale production workloads
8. **Security**: SOC 2, ISO 27001, 80+ certifications sufficient

### Negative

1. **Smaller Ecosystem**: Fewer third-party tools than AWS (mitigated: sufficient for OctoLLM)
2. **Redis Limitations**: No cluster mode >300GB (mitigated: manual sharding)
3. **Team Learning**: Team needs to learn GCP (mitigated: excellent docs, gentle curve)
4. **Fewer Certifications**: 80+ vs AWS 143 (mitigated: covers all current needs)
5. **Community Size**: Smaller than AWS (mitigated: still large, active community)

### Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Team unfamiliar with GCP | Medium | High | Training plan, excellent docs, Cloud Shell |
| Redis scaling beyond 300GB | High | Low | Manual sharding, monitoring, upgrade to Cloud Memorystore clusters |
| GCP outage | High | Very Low | Multi-AZ deployment, backups to S3 (cross-cloud) |
| Vendor lock-in | Medium | Medium | Cloud-agnostic architecture, Terraform modules |
| Cost overruns | Medium | Low | Billing alerts, budget caps, committed use discounts |
| Compliance gaps | Low | Very Low | 80+ certs cover current needs, audit before new requirements |

---

## Implementation Plan

### Phase 1: GCP Account Setup (Week 1)

1. **Create GCP Organization & Projects**:
   - Organization: `octollm.com`
   - Projects: `octollm-dev`, `octollm-staging`, `octollm-prod`
   - Enable billing account
   - Set up billing alerts: 50% ($250), 80% ($400), 100% ($500) for dev

2. **Configure IAM & Security**:
   - Create service accounts for Terraform
   - Set up IAM roles (least privilege):
     - `Kubernetes Engine Admin` (cluster management)
     - `Cloud SQL Admin` (database management)
     - `Storage Admin` (GCS management)
     - `Secret Manager Admin` (secrets)
   - Enable required APIs:
     - Kubernetes Engine API
     - Cloud SQL Admin API
     - Compute Engine API
     - Cloud Storage API
     - Secret Manager API
     - Cloud Monitoring API
   - Configure organization policies:
     - Require OS Login
     - Disable service account key creation
     - Restrict public IP assignment

3. **Set Up Billing Alerts & Budgets**:
   ```yaml
   # Dev Environment
   budget: $500/month
   alerts:
     - 50%: Email team, Slack notification
     - 80%: Email team + managers, Slack alert
     - 100%: Email team + managers + finance, stop dev resources

   # Staging Environment
   budget: $1,000/month
   alerts:
     - 50%: Email team
     - 80%: Email team + managers
     - 100%: Email team + managers + finance

   # Production Environment
   budget: $5,000/month
   alerts:
     - 50%: Email team
     - 80%: Email team + managers
     - 100%: Email team + managers + finance + executives
   ```

4. **Configure Resource Tagging Strategy**:
   - Labels (GCP terminology):
     - `environment`: dev | staging | prod
     - `project`: octollm
     - `component`: orchestrator | reflex | arm-* | database | cache
     - `owner`: team-backend | team-devops
     - `cost-center`: engineering | infrastructure
     - `managed-by`: terraform | manual

### Phase 2: Development Environment (Week 1)

1. **Provision GKE Cluster** (dev-cluster):
   ```bash
   gcloud container clusters create octollm-dev \
     --region us-central1 \
     --num-nodes 1 --min-nodes 1 --max-nodes 3 \
     --node-locations us-central1-a \
     --machine-type e2-standard-2 \
     --disk-size 50 \
     --enable-autoscaling \
     --enable-autorepair \
     --enable-autoupgrade \
     --no-enable-cloud-logging \
     --no-enable-cloud-monitoring \
     --addons HorizontalPodAutoscaling,HttpLoadBalancing
   ```

2. **Provision Cloud SQL PostgreSQL**:
   ```bash
   gcloud sql instances create octollm-dev-postgres \
     --database-version POSTGRES_15 \
     --tier db-f1-micro \
     --region us-central1 \
     --storage-size 20GB \
     --storage-type SSD \
     --storage-auto-increase \
     --backup-start-time 03:00 \
     --retained-backups-count 7
   ```

3. **Provision Memorystore Redis**:
   ```bash
   gcloud redis instances create octollm-dev-redis \
     --size 2 \
     --region us-central1 \
     --tier basic \
     --redis-version redis_7_0
   ```

4. **Create GCS Buckets**:
   ```bash
   gsutil mb -l us-central1 -c STANDARD gs://octollm-dev-backups
   gsutil mb -l us-central1 -c STANDARD gs://octollm-dev-logs
   ```

### Phase 3: Staging & Production (Week 2)

1. **Staging**: Similar to dev, scaled up (see Sprint 0.7 Task 3)
2. **Production**: Multi-AZ, HA, autoscaling (see Sprint 0.7 Task 3)

### Phase 4: Monitoring & Observability (Week 2)

1. Install Prometheus + Grafana (Helm charts)
2. Configure Cloud Monitoring dashboards
3. Set up alerting policies
4. Configure log retention (Cloud Logging)

---

## Appendix: Detailed Setup Instructions

### Prerequisites

**Required Tools**:
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install kubectl
gcloud components install kubectl

# Install Terraform (for IaC)
brew install terraform  # macOS
# or: wget + install from terraform.io

# Install Helm (for Kubernetes packages)
brew install helm  # macOS
```

**Authentication**:
```bash
# Authenticate with GCP
gcloud auth login

# Set default project
gcloud config set project octollm-dev

# Configure kubectl
gcloud container clusters get-credentials octollm-dev --region us-central1
```

### Cost Optimization Tips

1. **Committed Use Discounts**:
   - 1-year commitment: 25% discount
   - 3-year commitment: 52% discount
   - Apply to Compute Engine, GKE nodes
   - **Savings**: $6,000/year on production (25% discount)

2. **Preemptible/Spot VMs** (dev environment):
   - 60-91% discount vs on-demand
   - Suitable for dev workloads (can tolerate interruptions)
   - **Savings**: $80/month on dev

3. **Sustained Use Discounts** (automatic):
   - Up to 30% discount for sustained usage
   - No commitment required
   - Applied automatically

4. **Rightsizing Recommendations**:
   - Enable recommender API
   - Review monthly (downsize underutilized resources)

5. **Storage Lifecycle Policies**:
   - Move logs to Nearline after 30 days (50% cheaper)
   - Move logs to Coldline after 90 days (70% cheaper)
   - Delete logs after 1 year

### Security Best Practices

1. **Enable Binary Authorization** (GKE):
   - Require signed container images
   - Prevent untrusted images from running

2. **Enable GKE Sandbox** (gVisor):
   - Additional container isolation
   - Recommended for executor-arm (untrusted code)

3. **Configure Workload Identity**:
   - Bind Kubernetes service accounts to GCP service accounts
   - Avoid service account keys (security risk)

4. **Enable Private GKE Clusters**:
   - No public IP addresses for nodes
   - Access via Cloud VPN or bastion host

5. **Enable VPC Service Controls**:
   - Protect against data exfiltration
   - Restrict access to GCP services

6. **Configure Cloud Armor** (production):
   - DDoS protection
   - WAF rules (SQL injection, XSS)

### Compliance & Audit

**Enable Audit Logging**:
```bash
# Enable all audit logs (Admin Activity, Data Access, System Event)
gcloud logging read 'logName="projects/PROJECT_ID/logs/cloudaudit.googleapis.com"' \
  --limit 10 --format json
```

**SOC 2 Requirements**:
- [ ] Enable audit logging (all operations)
- [ ] Configure log retention (1 year minimum)
- [ ] Set up security monitoring alerts
- [ ] Regular access reviews (IAM)
- [ ] Encrypt data at rest (enabled by default)
- [ ] Encrypt data in transit (TLS 1.2+)

**GDPR Requirements**:
- [ ] Data residency (use europe-west1 for EU users)
- [ ] Data processing agreement with Google
- [ ] Right to erasure (document deletion procedures)
- [ ] Data portability (export procedures)

---

## References

1. **GCP Documentation**:
   - GKE Overview: https://cloud.google.com/kubernetes-engine/docs
   - Cloud SQL PostgreSQL: https://cloud.google.com/sql/docs/postgres
   - Memorystore for Redis: https://cloud.google.com/memorystore/docs/redis
   - GCP Pricing Calculator: https://cloud.google.com/products/calculator

2. **OctoLLM Documentation**:
   - ADR-001: Technology Stack Selection
   - ADR-005: Deployment Platform
   - `docs/operations/deployment-guide.md` (2,863 lines)
   - `to-dos/MASTER-TODO.md` (Sprint 0.7 specification)

3. **Competitor Comparisons**:
   - AWS vs GCP vs Azure (Kubernetes): https://cloud.google.com/kubernetes-engine/docs/resources/kubernetes-on-aws-vs-gke
   - Database Comparison: https://db-engines.com/en/system/Amazon+RDS+for+PostgreSQL%3BGoogle+Cloud+SQL+for+PostgreSQL
   - Redis Comparison: ElastiCache vs Memorystore performance benchmarks

4. **Community Resources**:
   - r/googlecloud (Reddit community)
   - GCP Slack community
   - Stack Overflow (gcp tag)

---

**Decision Date**: 2025-11-12
**Next Review**: 2026-11-12 (annual review)
**Approved By**: Architecture Team, DevOps Team, Finance Team
**Implementation Start**: Sprint 0.7 (Infrastructure as Code - Week 1)
