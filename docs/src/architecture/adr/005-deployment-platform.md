# ADR-005: Deployment Platform

**Status**: Accepted
**Date**: 2025-11-10
**Decision Makers**: Architecture Team, DevOps Team
**Consulted**: Engineering Team, Operations Team

## Context

OctoLLM requires a deployment platform that supports:
- **Multi-component orchestration**: Orchestrator, multiple Arms, Reflex Layer, Memory systems
- **Scalability**: Horizontal scaling for Arms, vertical scaling for databases
- **Service discovery**: Components need to find each other dynamically
- **Health monitoring**: Automatic restarts, health checks, readiness probes
- **Resource management**: CPU/memory limits, quotas, efficient allocation
- **Rolling updates**: Zero-downtime deployments
- **Configuration management**: Environment-specific configs, secrets
- **Development parity**: Local development should mirror production
- **Cloud agnostic**: No vendor lock-in, portable across providers

Deployment requirements:
- **Production**: High availability, auto-scaling, monitoring, observability
- **Staging**: Production-like environment for testing
- **Development**: Fast iteration, easy debugging, minimal resource usage
- **CI/CD**: Automated builds, tests, deployments

Environment characteristics:
- **Local Dev**: Docker Compose, single machine, easy setup
- **Staging**: Kubernetes cluster, production-like, testing
- **Production**: Kubernetes cluster, multi-region (future), HA databases

## Decision

We will use **Kubernetes for production** and **Docker Compose for development** with a cloud-agnostic architecture:

### 1. Production Deployment (Kubernetes)

**Platform**: Kubernetes 1.28+
**Distribution**: Any CNCF-certified (EKS, GKE, AKS, or self-hosted)
**Approach**: Cloud-agnostic, no vendor-specific services

**Why Kubernetes**:
- Industry-standard container orchestration
- Rich ecosystem (Helm, Kustomize, operators)
- Excellent service discovery and load balancing
- Horizontal Pod Autoscaler (HPA) for auto-scaling
- Rolling updates with zero downtime
- Self-healing (automatic restarts)
- Resource management and quotas
- Multi-cloud portability

**Architecture**:
```yaml
# Namespace organization
octollm-system/      # System components (monitoring, ingress)
octollm-production/  # Production workloads
octollm-staging/     # Staging workloads

# Components
- Deployment: orchestrator (3 replicas)
- Deployment: coder-arm (5 replicas, HPA)
- Deployment: judge-arm (3 replicas, HPA)
- Deployment: executor-arm (5 replicas, HPA)
- Deployment: planner-arm (3 replicas, HPA)
- Deployment: retriever-arm (3 replicas, HPA)
- DaemonSet: reflex-layer (1 per node)
- StatefulSet: postgresql (3 replicas, HA)
- StatefulSet: qdrant (3 replicas)
- StatefulSet: redis (3 replicas, sentinel)
```

**Example Deployment**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  namespace: octollm-production
  labels:
    app: orchestrator
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
    spec:
      serviceAccountName: orchestrator
      containers:
      - name: orchestrator
        image: octollm/orchestrator:v1.0.0
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: octollm-production
spec:
  type: ClusterIP
  selector:
    app: orchestrator
  ports:
  - name: http
    port: 8000
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
  namespace: octollm-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 2
        periodSeconds: 30
      selectPolicy: Max
```

**Arm Deployment Example**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coder-arm
  namespace: octollm-production
spec:
  replicas: 5
  selector:
    matchLabels:
      app: coder-arm
  template:
    metadata:
      labels:
        app: coder-arm
    spec:
      containers:
      - name: coder-arm
        image: octollm/coder-arm:v1.0.0
        ports:
        - containerPort: 8102
        env:
        - name: ARM_TYPE
          value: "coder"
        - name: LLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-credentials
              key: api-key
        resources:
          requests:
            cpu: "1000m"
            memory: "1Gi"
          limits:
            cpu: "4000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8102
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8102
          initialDelaySeconds: 10
          periodSeconds: 5
```

**Reflex Layer (DaemonSet)**:
```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: reflex-layer
  namespace: octollm-production
spec:
  selector:
    matchLabels:
      app: reflex-layer
  template:
    metadata:
      labels:
        app: reflex-layer
    spec:
      hostNetwork: true  # For low-latency
      containers:
      - name: reflex-layer
        image: octollm/reflex-layer:v1.0.0
        ports:
        - containerPort: 8080
          hostPort: 8080
        resources:
          requests:
            cpu: "2000m"
            memory: "512Mi"
          limits:
            cpu: "4000m"
            memory: "1Gi"
        securityContext:
          capabilities:
            add:
            - NET_BIND_SERVICE
```

**StatefulSet for PostgreSQL**:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql
  namespace: octollm-production
spec:
  serviceName: postgresql
  replicas: 3
  selector:
    matchLabels:
      app: postgresql
  template:
    metadata:
      labels:
        app: postgresql
    spec:
      containers:
      - name: postgresql
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          value: octollm
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgresql-credentials
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgresql-credentials
              key: password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: "2000m"
            memory: "4Gi"
          limits:
            cpu: "4000m"
            memory: "8Gi"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          initialDelaySeconds: 10
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 100Gi
```

### 2. Development Deployment (Docker Compose)

**Platform**: Docker Compose 2.x
**Environment**: Local development machines
**Purpose**: Fast iteration, easy debugging

**docker-compose.yml**:
```yaml
version: '3.9'

services:
  # Databases
  postgresql:
    image: postgres:15-alpine
    container_name: octollm-postgres
    environment:
      POSTGRES_DB: octollm
      POSTGRES_USER: octollm
      POSTGRES_PASSWORD: development
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U octollm"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: octollm-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.7.0
    container_name: octollm-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Reflex Layer
  reflex-layer:
    build:
      context: ./reflex_layer
      dockerfile: Dockerfile.dev
    container_name: octollm-reflex
    ports:
      - "8080:8080"
    environment:
      - RUST_LOG=debug
      - RATE_LIMIT_ENABLED=true
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Orchestrator
  orchestrator:
    build:
      context: ./orchestrator
      dockerfile: Dockerfile.dev
    container_name: octollm-orchestrator
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
      - DATABASE_URL=postgresql://octollm:development@postgresql:5432/octollm
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./orchestrator:/app
      - /app/.venv  # Don't override venv
    depends_on:
      postgresql:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      reflex-layer:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Arms
  coder-arm:
    build:
      context: ./arms/coder
      dockerfile: Dockerfile.dev
    container_name: octollm-coder-arm
    ports:
      - "8102:8102"
    environment:
      - ARM_TYPE=coder
      - LOG_LEVEL=DEBUG
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./arms/coder:/app
      - /app/.venv
    depends_on:
      orchestrator:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8102 --reload

  judge-arm:
    build:
      context: ./arms/judge
      dockerfile: Dockerfile.dev
    container_name: octollm-judge-arm
    ports:
      - "8103:8103"
    environment:
      - ARM_TYPE=judge
      - LOG_LEVEL=DEBUG
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./arms/judge:/app
      - /app/.venv
    depends_on:
      orchestrator:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8103 --reload

  executor-arm:
    build:
      context: ./arms/executor
      dockerfile: Dockerfile.dev
    container_name: octollm-executor-arm
    ports:
      - "8104:8104"
    environment:
      - ARM_TYPE=executor
      - LOG_LEVEL=DEBUG
    volumes:
      - ./arms/executor:/app
      - /app/.venv
    depends_on:
      orchestrator:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8104 --reload

  planner-arm:
    build:
      context: ./arms/planner
      dockerfile: Dockerfile.dev
    container_name: octollm-planner-arm
    ports:
      - "8105:8105"
    environment:
      - ARM_TYPE=planner
      - LOG_LEVEL=DEBUG
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./arms/planner:/app
      - /app/.venv
    depends_on:
      orchestrator:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8105 --reload

  retriever-arm:
    build:
      context: ./arms/retriever
      dockerfile: Dockerfile.dev
    container_name: octollm-retriever-arm
    ports:
      - "8106:8106"
    environment:
      - ARM_TYPE=retriever
      - LOG_LEVEL=DEBUG
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./arms/retriever:/app
      - /app/.venv
    depends_on:
      orchestrator:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8106 --reload

  # Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: octollm-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    container_name: octollm-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  prometheus_data:
  grafana_data:
```

**Development Scripts**:

**scripts/dev.sh**:
```bash
#!/bin/bash
set -e

# Start development environment
echo "Starting OctoLLM development environment..."

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
    exit 1
fi

# Start services
docker compose up -d postgresql redis qdrant

# Wait for databases
echo "Waiting for databases to be ready..."
sleep 5

# Run migrations
echo "Running database migrations..."
docker compose run --rm orchestrator alembic upgrade head

# Start all services
echo "Starting all services..."
docker compose up -d

# Show logs
echo "Services started! Tailing logs (Ctrl+C to stop)..."
docker compose logs -f
```

**scripts/test.sh**:
```bash
#!/bin/bash
set -e

# Run tests in development environment
echo "Running OctoLLM tests..."

# Start dependencies
docker compose up -d postgresql redis qdrant

# Wait for databases
sleep 5

# Run Python tests
echo "Running orchestrator tests..."
docker compose run --rm orchestrator pytest -v

echo "Running arm tests..."
docker compose run --rm coder-arm pytest -v
docker compose run --rm judge-arm pytest -v

# Run Rust tests
echo "Running reflex layer tests..."
cd reflex_layer && cargo test && cd ..

echo "All tests passed! ✅"
```

### 3. Configuration Management

**Kubernetes ConfigMaps**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: orchestrator-config
  namespace: octollm-production
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  ARM_REGISTRY_URL: "http://orchestrator:8000/registry"
  RATE_LIMIT_ENABLED: "true"
  RATE_LIMIT_REQUESTS: "1000"
  RATE_LIMIT_WINDOW: "60"
```

**Kubernetes Secrets**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: database-credentials
  namespace: octollm-production
type: Opaque
stringData:
  url: postgresql://octollm:PASSWORD@postgresql:5432/octollm
  username: octollm
  password: SECURE_PASSWORD_HERE
---
apiVersion: v1
kind: Secret
metadata:
  name: llm-credentials
  namespace: octollm-production
type: Opaque
stringData:
  api-key: sk-YOUR-API-KEY-HERE
```

**Environment-Specific Configs (Kustomize)**:

**base/kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - hpa.yaml
  - configmap.yaml

commonLabels:
  app: octollm
  managed-by: kustomize
```

**overlays/production/kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

namespace: octollm-production

replicas:
  - name: orchestrator
    count: 3
  - name: coder-arm
    count: 5

images:
  - name: octollm/orchestrator
    newTag: v1.0.0
  - name: octollm/coder-arm
    newTag: v1.0.0

patches:
  - path: production-resources.yaml
```

**overlays/staging/kustomization.yaml**:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

namespace: octollm-staging

replicas:
  - name: orchestrator
    count: 1
  - name: coder-arm
    count: 2

images:
  - name: octollm/orchestrator
    newTag: latest
  - name: octollm/coder-arm
    newTag: latest
```

### 4. Helm Charts (Alternative to Kustomize)

**Chart.yaml**:
```yaml
apiVersion: v2
name: octollm
description: OctoLLM Multi-Agent System
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - llm
  - multi-agent
  - orchestration
maintainers:
  - name: OctoLLM Team
    email: team@octollm.io
```

**values.yaml**:
```yaml
global:
  environment: production
  logLevel: INFO
  imageRegistry: docker.io
  imagePullSecrets: []

orchestrator:
  replicaCount: 3
  image:
    repository: octollm/orchestrator
    tag: v1.0.0
    pullPolicy: IfNotPresent
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
  service:
    type: ClusterIP
    port: 8000

arms:
  coder:
    replicaCount: 5
    image:
      repository: octollm/coder-arm
      tag: v1.0.0
    resources:
      requests:
        cpu: 1000m
        memory: 1Gi
      limits:
        cpu: 4000m
        memory: 4Gi
    autoscaling:
      enabled: true
      minReplicas: 5
      maxReplicas: 20
      targetCPUUtilizationPercentage: 70

  judge:
    replicaCount: 3
    image:
      repository: octollm/judge-arm
      tag: v1.0.0
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 2000m
        memory: 2Gi

postgresql:
  enabled: true
  auth:
    database: octollm
    username: octollm
  primary:
    persistence:
      enabled: true
      size: 100Gi
      storageClass: fast-ssd
  resources:
    requests:
      cpu: 2000m
      memory: 4Gi
    limits:
      cpu: 4000m
      memory: 8Gi

redis:
  enabled: true
  architecture: replication
  master:
    persistence:
      enabled: true
      size: 10Gi
  replica:
    replicaCount: 2

qdrant:
  enabled: true
  replicaCount: 3
  persistence:
    enabled: true
    size: 50Gi
```

**values-staging.yaml**:
```yaml
global:
  environment: staging
  logLevel: DEBUG

orchestrator:
  replicaCount: 1
  autoscaling:
    enabled: false

arms:
  coder:
    replicaCount: 2
    autoscaling:
      enabled: false
```

**Installation Commands**:
```bash
# Install production
helm install octollm ./charts/octollm \
  --namespace octollm-production \
  --create-namespace \
  --values ./charts/octollm/values.yaml

# Install staging
helm install octollm-staging ./charts/octollm \
  --namespace octollm-staging \
  --create-namespace \
  --values ./charts/octollm/values-staging.yaml

# Upgrade
helm upgrade octollm ./charts/octollm \
  --namespace octollm-production \
  --values ./charts/octollm/values.yaml

# Rollback
helm rollback octollm 1 --namespace octollm-production
```

### 5. CI/CD Pipeline

**GitHub Actions - Build and Test**:

**.github/workflows/ci.yml**:
```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test-python:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install poetry
          cd orchestrator && poetry install

      - name: Run tests
        run: |
          cd orchestrator && poetry run pytest -v --cov=.

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  test-rust:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          components: rustfmt, clippy

      - name: Run tests
        run: |
          cd reflex_layer
          cargo fmt -- --check
          cargo clippy -- -D warnings
          cargo test

  build-images:
    runs-on: ubuntu-latest
    needs: [test-python, test-rust]
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push orchestrator
        uses: docker/build-push-action@v5
        with:
          context: ./orchestrator
          push: true
          tags: |
            octollm/orchestrator:latest
            octollm/orchestrator:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push reflex-layer
        uses: docker/build-push-action@v5
        with:
          context: ./reflex_layer
          push: true
          tags: |
            octollm/reflex-layer:latest
            octollm/reflex-layer:${{ github.sha }}
```

**GitHub Actions - Deploy**:

**.github/workflows/deploy.yml**:
```yaml
name: Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}

      - name: Deploy to staging
        run: |
          kubectl apply -k overlays/staging
          kubectl rollout status deployment/orchestrator -n octollm-staging

      - name: Run smoke tests
        run: |
          ./scripts/smoke-tests.sh staging

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG_PRODUCTION }}

      - name: Deploy to production
        run: |
          kubectl apply -k overlays/production
          kubectl rollout status deployment/orchestrator -n octollm-production

      - name: Run smoke tests
        run: |
          ./scripts/smoke-tests.sh production

      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployed ${{ github.ref }} to production'
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 6. Ingress and Load Balancing

**Nginx Ingress Controller**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: octollm-ingress
  namespace: octollm-production
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.octollm.io
    secretName: octollm-tls
  rules:
  - host: api.octollm.io
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: reflex-layer
            port:
              number: 8080
      - path: /api/orchestrator
        pathType: Prefix
        backend:
          service:
            name: orchestrator
            port:
              number: 8000
```

### 7. Monitoring and Observability

**Prometheus ServiceMonitor**:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: octollm-metrics
  namespace: octollm-production
spec:
  selector:
    matchLabels:
      app: octollm
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

**Grafana Dashboard ConfigMap**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  namespace: octollm-system
data:
  octollm-overview.json: |
    {
      "dashboard": {
        "title": "OctoLLM Overview",
        "panels": [
          {
            "title": "Request Rate",
            "targets": [
              {
                "expr": "rate(http_requests_total[5m])"
              }
            ]
          },
          {
            "title": "Error Rate",
            "targets": [
              {
                "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
              }
            ]
          }
        ]
      }
    }
```

### 8. Disaster Recovery

**Backup Strategy**:
```yaml
# Velero backup schedule
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: octollm-daily-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  template:
    includedNamespaces:
    - octollm-production
    storageLocation: default
    volumeSnapshotLocations:
    - default
    ttl: 720h  # 30 days
```

**Restore Procedure**:
```bash
# Restore from backup
velero restore create octollm-restore \
  --from-backup octollm-daily-backup-20251110 \
  --namespace-mappings octollm-production:octollm-production-restored

# Verify restore
kubectl get all -n octollm-production-restored

# Promote to production
kubectl label namespace octollm-production-restored environment=production
```

## Consequences

### Positive

1. **Kubernetes Production Benefits**:
   - Auto-scaling handles variable load
   - Self-healing reduces downtime
   - Rolling updates enable zero-downtime deployments
   - Resource quotas prevent runaway costs
   - Industry-standard platform

2. **Docker Compose Development Benefits**:
   - Fast startup (<2 minutes)
   - Easy debugging with volume mounts
   - Minimal resource usage
   - Production parity with same images
   - Simple onboarding for new developers

3. **Cloud Agnostic**:
   - No vendor lock-in
   - Can deploy to any K8s cluster
   - Easy migration between clouds
   - Cost optimization through competition
   - Multi-cloud strategy possible

4. **Operational Efficiency**:
   - Automated deployments via CI/CD
   - Consistent environments (dev/staging/prod)
   - Infrastructure as code
   - Easy rollbacks
   - Comprehensive monitoring

5. **Scalability**:
   - Horizontal scaling for stateless services
   - Vertical scaling for databases
   - HPA automatically adjusts replicas
   - Can handle 10x traffic spikes
   - Resource-efficient

### Negative

1. **Kubernetes Complexity**:
   - Steep learning curve
   - Many concepts to understand
   - Complex YAML configurations
   - Debugging can be challenging
   - Requires specialized expertise

2. **Operational Overhead**:
   - Need to manage K8s cluster
   - Monitoring infrastructure required
   - More moving parts
   - Complex troubleshooting
   - Higher ops burden

3. **Resource Requirements**:
   - K8s control plane overhead
   - Need multiple worker nodes
   - Development setup is heavyweight
   - More expensive infrastructure
   - Minimum cluster size costs

4. **Development-Production Gap**:
   - Docker Compose != Kubernetes
   - Some issues only appear in K8s
   - Different networking models
   - Debugging differs between environments
   - Need staging environment

### Mitigation Strategies

1. **Complexity**:
   - Comprehensive documentation
   - Helm charts for easier deployment
   - Training for team members
   - Start with simple deployments
   - Gradually adopt advanced features

2. **Operational Overhead**:
   - Managed Kubernetes (EKS/GKE/AKS)
   - Automated monitoring setup
   - Runbooks for common issues
   - On-call rotation
   - Regular operational reviews

3. **Resource Requirements**:
   - Right-size cluster for workload
   - Use spot instances where possible
   - Optimize resource requests/limits
   - Auto-scaling to minimize waste
   - Cost monitoring and alerts

4. **Dev-Prod Gap**:
   - Maintain staging environment
   - Test in K8s before production
   - Document K8s-specific behaviors
   - Use same images everywhere
   - Comprehensive integration tests

## Alternatives Considered

### 1. Docker Swarm

**Pros**:
- Simpler than Kubernetes
- Built into Docker
- Easier to learn
- Less resource overhead

**Cons**:
- Less ecosystem support
- Fewer features than K8s
- Not as widely adopted
- Limited scaling capabilities
- Weaker community

**Why Rejected**: Kubernetes has better ecosystem, more features, and industry adoption.

### 2. HashiCorp Nomad

**Pros**:
- Simpler than Kubernetes
- Multi-workload (containers, VMs, binaries)
- Good for hybrid deployments
- Easier operations

**Cons**:
- Smaller ecosystem
- Less tooling available
- Fewer managed options
- Weaker community
- Less familiar to team

**Why Rejected**: Kubernetes has better ecosystem and more deployment options.

### 3. Serverless (Lambda/Cloud Functions)

**Pros**:
- No infrastructure management
- Pay per use
- Auto-scaling built-in
- Simple deployment

**Cons**:
- Cold start latency
- Vendor lock-in
- Limited runtime duration
- Harder to debug
- Cost unpredictable at scale

**Why Rejected**: Need consistent latency and want cloud-agnostic approach.

### 4. Single VM Deployment

**Pros**:
- Simplest setup
- Easy to understand
- Low cost
- Easy debugging

**Cons**:
- No auto-scaling
- Single point of failure
- Manual updates
- Limited capacity
- No high availability

**Why Rejected**: Doesn't meet production requirements for scaling and availability.

### 5. Cloud-Specific Services (ECS/Cloud Run)

**Pros**:
- Simpler than K8s
- Managed by provider
- Good integration with cloud
- Lower learning curve

**Cons**:
- Vendor lock-in
- Migration difficult
- Cloud-specific knowledge
- Limited portability

**Why Rejected**: Want cloud-agnostic solution to avoid vendor lock-in.

## Implementation Guidelines

### Development Workflow

```bash
# Clone repository
git clone https://github.com/your-org/octollm.git
cd octollm

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Start development environment
./scripts/dev.sh

# Run tests
./scripts/test.sh

# View logs
docker compose logs -f orchestrator

# Restart specific service
docker compose restart coder-arm

# Stop environment
docker compose down
```

### Production Deployment

```bash
# Build and push images
docker build -t octollm/orchestrator:v1.0.0 ./orchestrator
docker push octollm/orchestrator:v1.0.0

# Deploy to staging
kubectl apply -k overlays/staging
kubectl rollout status deployment/orchestrator -n octollm-staging

# Run smoke tests
./scripts/smoke-tests.sh staging

# Deploy to production
kubectl apply -k overlays/production
kubectl rollout status deployment/orchestrator -n octollm-production

# Monitor rollout
kubectl get pods -n octollm-production -w
kubectl logs -f deployment/orchestrator -n octollm-production

# Rollback if needed
kubectl rollout undo deployment/orchestrator -n octollm-production
```

### Troubleshooting

```bash
# Check pod status
kubectl get pods -n octollm-production

# View pod logs
kubectl logs -f <pod-name> -n octollm-production

# Describe pod (events, resources)
kubectl describe pod <pod-name> -n octollm-production

# Execute command in pod
kubectl exec -it <pod-name> -n octollm-production -- /bin/sh

# Check resource usage
kubectl top pods -n octollm-production

# View events
kubectl get events -n octollm-production --sort-by='.lastTimestamp'
```

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Helm Documentation](https://helm.sh/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [The Twelve-Factor App](https://12factor.net/)
- [Kubernetes Patterns](https://www.redhat.com/en/resources/oreilly-kubernetes-patterns-cloud-native-apps)

---

**Last Review**: 2025-11-10
**Next Review**: 2026-05-10 (6 months)
**Related ADRs**: ADR-001, ADR-002, ADR-003, ADR-004
