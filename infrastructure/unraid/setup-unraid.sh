#!/bin/bash
# OctoLLM Unraid Setup Script
# Automatically configures OctoLLM for local development on Unraid 7.2.0
#
# Hardware Requirements:
# - Unraid 7.2.0+
# - NVIDIA GPU with Docker support
# - Docker & Docker Compose
# - Minimum: 16GB RAM, 4 cores, 50GB disk
# - Recommended: 64GB RAM, 16 cores, 200GB disk, Tesla P40 GPU
#
# Usage: bash setup-unraid.sh

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APPDATA_ROOT="/mnt/user/appdata/octollm"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.unraid.yml"
ENV_FILE="$SCRIPT_DIR/.env.unraid"
ENV_EXAMPLE="$SCRIPT_DIR/.env.unraid.example"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        return 1
    fi
    return 0
}

generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# ============================================================================
# Prerequisites Check
# ============================================================================

log_info "Checking prerequisites..."

# Check if running on Unraid
if [ ! -f /etc/unraid-version ]; then
    log_warning "This script is optimized for Unraid, but may work on other systems."
fi

# Check Docker
if ! check_command docker; then
    log_error "Docker is not installed. Install Docker first."
    exit 1
fi
log_success "Docker is installed: $(docker --version)"

# Check Docker Compose
if ! check_command docker-compose && ! docker compose version &> /dev/null; then
    log_error "Docker Compose is not installed."
    exit 1
fi
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    log_success "Docker Compose V2 is installed: $(docker compose version)"
else
    COMPOSE_CMD="docker-compose"
    log_success "Docker Compose is installed: $(docker-compose --version)"
fi

# Check NVIDIA driver
if ! check_command nvidia-smi; then
    log_warning "nvidia-smi not found. GPU acceleration will not be available."
    log_warning "Install NVIDIA Driver Plugin from Unraid Community Applications."
    GPU_AVAILABLE=false
else
    log_success "NVIDIA driver is installed: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader)"
    GPU_AVAILABLE=true

    # Check GPU details
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader)
    GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader)
    log_info "Detected GPU: $GPU_NAME with $GPU_MEMORY VRAM"
fi

# Check Docker NVIDIA runtime
if $GPU_AVAILABLE; then
    if docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        log_success "Docker NVIDIA runtime is working"
    else
        log_warning "Docker NVIDIA runtime is not working properly"
        log_warning "Try: docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi"
    fi
fi

# Check available resources
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
TOTAL_CPU=$(nproc)
log_info "System resources: ${TOTAL_CPU} CPU cores, ${TOTAL_RAM}GB RAM"

if [ "$TOTAL_RAM" -lt 16 ]; then
    log_warning "Less than 16GB RAM detected. OctoLLM requires at least 16GB."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ============================================================================
# Directory Structure
# ============================================================================

log_info "Creating directory structure in $APPDATA_ROOT..."

# Create main directories
directories=(
    "$APPDATA_ROOT"
    "$APPDATA_ROOT/postgres/data"
    "$APPDATA_ROOT/postgres/init"
    "$APPDATA_ROOT/redis/data"
    "$APPDATA_ROOT/qdrant/storage"
    "$APPDATA_ROOT/qdrant/snapshots"
    "$APPDATA_ROOT/ollama/models"
    "$APPDATA_ROOT/prometheus/config"
    "$APPDATA_ROOT/prometheus/data"
    "$APPDATA_ROOT/grafana/data"
    "$APPDATA_ROOT/grafana/provisioning/datasources"
    "$APPDATA_ROOT/grafana/provisioning/dashboards"
    "$APPDATA_ROOT/grafana/dashboards"
    "$APPDATA_ROOT/loki/config"
    "$APPDATA_ROOT/loki/data"
    "$APPDATA_ROOT/logs"
    "$APPDATA_ROOT/certs"
    "$APPDATA_ROOT/backups"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        log_success "Created directory: $dir"
    else
        log_info "Directory already exists: $dir"
    fi
done

# Set Unraid permissions (nobody:users = 99:100)
log_info "Setting permissions (nobody:users)..."
chown -R 99:100 "$APPDATA_ROOT"
chmod -R 755 "$APPDATA_ROOT"
log_success "Permissions set successfully"

# ============================================================================
# Environment Configuration
# ============================================================================

log_info "Setting up environment configuration..."

if [ -f "$ENV_FILE" ]; then
    log_warning ".env.unraid already exists. Backing up to .env.unraid.backup"
    cp "$ENV_FILE" "$ENV_FILE.backup"
fi

# Copy example and generate secure passwords
cp "$ENV_EXAMPLE" "$ENV_FILE"

# Generate secure passwords
POSTGRES_PASSWORD=$(generate_password)
REDIS_PASSWORD=$(generate_password)
QDRANT_API_KEY=$(generate_password)
GRAFANA_PASSWORD=$(generate_password)

# Replace placeholders
sed -i "s|CHANGE_ME_POSTGRES_PASSWORD_HERE|$POSTGRES_PASSWORD|g" "$ENV_FILE"
sed -i "s|CHANGE_ME_REDIS_PASSWORD_HERE|$REDIS_PASSWORD|g" "$ENV_FILE"
sed -i "s|CHANGE_ME_QDRANT_API_KEY_HERE|$QDRANT_API_KEY|g" "$ENV_FILE"
sed -i "s|CHANGE_ME_GRAFANA_PASSWORD_HERE|$GRAFANA_PASSWORD|g" "$ENV_FILE"

# Update HOST_IP with actual IP if available
if command -v hostname &> /dev/null; then
    HOST_IP=$(hostname -I | awk '{print $1}')
    if [ -n "$HOST_IP" ]; then
        sed -i "s|HOST_IP=192.168.4.6|HOST_IP=$HOST_IP|g" "$ENV_FILE"
        log_success "Set HOST_IP to $HOST_IP"
    fi
fi

log_success "Environment file created: $ENV_FILE"
log_info "Secure passwords generated. Save these credentials:"
echo -e "${GREEN}PostgreSQL Password:${NC} $POSTGRES_PASSWORD"
echo -e "${GREEN}Redis Password:${NC} $REDIS_PASSWORD"
echo -e "${GREEN}Qdrant API Key:${NC} $QDRANT_API_KEY"
echo -e "${GREEN}Grafana Admin Password:${NC} $GRAFANA_PASSWORD"
echo ""
log_warning "These passwords are stored in $ENV_FILE"
log_warning "Keep this file secure and never commit it to version control!"

# Prompt for optional API keys
echo ""
log_info "Optional: Configure cloud LLM APIs (press Enter to skip)"
read -p "OpenAI API Key (optional, for fallback): " OPENAI_KEY
if [ -n "$OPENAI_KEY" ]; then
    sed -i "s|OPENAI_API_KEY=|OPENAI_API_KEY=$OPENAI_KEY|g" "$ENV_FILE"
    log_success "OpenAI API key configured"
fi

read -p "Anthropic API Key (optional, for Claude): " ANTHROPIC_KEY
if [ -n "$ANTHROPIC_KEY" ]; then
    sed -i "s|ANTHROPIC_API_KEY=|ANTHROPIC_API_KEY=$ANTHROPIC_KEY|g" "$ENV_FILE"
    log_success "Anthropic API key configured"
fi

# ============================================================================
# PostgreSQL Initialization
# ============================================================================

log_info "Creating PostgreSQL initialization script..."

cat > "$APPDATA_ROOT/postgres/init/01-init-octollm.sql" << 'EOF'
-- OctoLLM Database Initialization Script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS orchestrator;
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA orchestrator TO octollm;
GRANT ALL PRIVILEGES ON SCHEMA memory TO octollm;
GRANT ALL PRIVILEGES ON SCHEMA audit TO octollm;

-- Create task history table
CREATE TABLE IF NOT EXISTS orchestrator.task_history (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    result JSONB,
    metadata JSONB
);

-- Create memory table
CREATE TABLE IF NOT EXISTS memory.global_memory (
    memory_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    embedding_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    metadata JSONB
);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit.api_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    user_id VARCHAR(255),
    ip_address INET,
    metadata JSONB
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_task_history_status ON orchestrator.task_history(status);
CREATE INDEX IF NOT EXISTS idx_task_history_created_at ON orchestrator.task_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_accessed_at ON memory.global_memory(accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit.api_logs(timestamp DESC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to task_history
DROP TRIGGER IF EXISTS update_task_history_updated_at ON orchestrator.task_history;
CREATE TRIGGER update_task_history_updated_at
    BEFORE UPDATE ON orchestrator.task_history
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert test data (development only)
INSERT INTO orchestrator.task_history (goal, status, result)
VALUES
    ('Test task - setup verification', 'completed', '{"message": "Database initialization successful"}'::jsonb)
ON CONFLICT DO NOTHING;
EOF

chmod 644 "$APPDATA_ROOT/postgres/init/01-init-octollm.sql"
log_success "PostgreSQL initialization script created"

# ============================================================================
# Prometheus Configuration
# ============================================================================

log_info "Creating Prometheus configuration..."

cat > "$APPDATA_ROOT/prometheus/config/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'octollm-unraid'
    environment: 'development'

# Alerting configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

# Load alert rules
rule_files:
  - 'alerts.yml'

# Scrape configurations
scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # OctoLLM services
  - job_name: 'orchestrator'
    static_configs:
      - targets: ['orchestrator:8000']
    metrics_path: '/metrics'

  - job_name: 'reflex-layer'
    static_configs:
      - targets: ['reflex-layer:3001']
    metrics_path: '/metrics'

  # Arms
  - job_name: 'planner-arm'
    static_configs:
      - targets: ['planner-arm:6001']
    metrics_path: '/metrics'

  - job_name: 'executor-arm'
    static_configs:
      - targets: ['executor-arm:6002']
    metrics_path: '/metrics'

  - job_name: 'retriever-arm'
    static_configs:
      - targets: ['retriever-arm:6003']
    metrics_path: '/metrics'

  - job_name: 'coder-arm'
    static_configs:
      - targets: ['coder-arm:6004']
    metrics_path: '/metrics'

  - job_name: 'judge-arm'
    static_configs:
      - targets: ['judge-arm:6005']
    metrics_path: '/metrics'

  - job_name: 'safety-guardian-arm'
    static_configs:
      - targets: ['safety-guardian-arm:6006']
    metrics_path: '/metrics'

  # Infrastructure exporters
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']

  # NVIDIA GPU metrics
  - job_name: 'nvidia-dcgm'
    static_configs:
      - targets: ['nvidia-dcgm-exporter:9400']
EOF

chmod 644 "$APPDATA_ROOT/prometheus/config/prometheus.yml"
log_success "Prometheus configuration created"

# ============================================================================
# Grafana Provisioning
# ============================================================================

log_info "Creating Grafana provisioning configuration..."

# Datasource provisioning
cat > "$APPDATA_ROOT/grafana/provisioning/datasources/datasources.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true
EOF

# Dashboard provisioning
cat > "$APPDATA_ROOT/grafana/provisioning/dashboards/dashboards.yml" << 'EOF'
apiVersion: 1

providers:
  - name: 'OctoLLM'
    orgId: 1
    folder: 'OctoLLM'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
EOF

log_success "Grafana provisioning configured"

# ============================================================================
# Loki Configuration
# ============================================================================

log_info "Creating Loki configuration..."

cat > "$APPDATA_ROOT/loki/config/local-config.yaml" << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 744h  # 31 days
EOF

chmod 644 "$APPDATA_ROOT/loki/config/local-config.yaml"
log_success "Loki configuration created"

# ============================================================================
# GPU Setup and Model Download
# ============================================================================

if $GPU_AVAILABLE; then
    log_info "Setting up GPU and downloading Ollama models..."
    log_warning "This may take 15-30 minutes depending on your internet speed."

    # Start only Ollama first to download models
    cd "$SCRIPT_DIR"
    $COMPOSE_CMD up -d ollama

    # Wait for Ollama to be ready
    log_info "Waiting for Ollama to start..."
    sleep 10

    # Pull models
    MODELS=("llama3.1:8b" "mixtral:8x7b" "codellama:13b" "nomic-embed-text")

    for model in "${MODELS[@]}"; do
        log_info "Pulling model: $model"
        if docker exec octollm-ollama ollama pull "$model"; then
            log_success "Model $model downloaded successfully"
        else
            log_error "Failed to download model: $model"
        fi
    done

    # Stop Ollama for now
    $COMPOSE_CMD stop ollama

    log_success "Ollama models downloaded successfully"
else
    log_warning "Skipping Ollama model download (GPU not available)"
fi

# ============================================================================
# Build Docker Images
# ============================================================================

log_info "Building Docker images..."
log_warning "This may take 10-20 minutes for the first build."

cd "$SCRIPT_DIR"

# Check if Dockerfiles exist (they may not in documentation-only repo)
if [ ! -f "$PROJECT_ROOT/services/orchestrator/Dockerfile" ]; then
    log_warning "Dockerfiles not found. This is expected for documentation-only repository."
    log_info "Skipping Docker image build. You'll need to implement services first."
    SKIP_BUILD=true
else
    SKIP_BUILD=false
    # Build images
    if $COMPOSE_CMD build --parallel; then
        log_success "Docker images built successfully"
    else
        log_error "Failed to build Docker images"
        exit 1
    fi
fi

# ============================================================================
# Start Services
# ============================================================================

if [ "$SKIP_BUILD" = false ]; then
    log_info "Starting OctoLLM services..."

    cd "$SCRIPT_DIR"
    if $COMPOSE_CMD up -d; then
        log_success "OctoLLM services started successfully"
    else
        log_error "Failed to start services"
        exit 1
    fi

    # Wait for health checks
    log_info "Waiting for services to become healthy..."
    sleep 30

    # Check service health
    log_info "Checking service health..."
    $COMPOSE_CMD ps
else
    log_info "Skipping service startup (no services to start yet)"
fi

# ============================================================================
# Summary and Next Steps
# ============================================================================

echo ""
echo "============================================================================"
log_success "OctoLLM Unraid Setup Complete!"
echo "============================================================================"
echo ""

# Get actual HOST_IP from env file
HOST_IP=$(grep "^HOST_IP=" "$ENV_FILE" | cut -d'=' -f2)

echo -e "${GREEN}Access URLs:${NC}"
echo "  Orchestrator API:    http://${HOST_IP}:3000"
echo "  Orchestrator Docs:   http://${HOST_IP}:3000/docs"
echo "  Reflex Layer API:    http://${HOST_IP}:3001"
echo "  Grafana Dashboard:   http://${HOST_IP}:3030"
echo "  Prometheus:          http://${HOST_IP}:9090"
echo "  Ollama API:          http://${HOST_IP}:3014"
echo ""

echo -e "${GREEN}Credentials:${NC}"
echo "  Grafana:"
echo "    Username: admin"
echo "    Password: $GRAFANA_PASSWORD"
echo ""

echo -e "${GREEN}Useful Commands:${NC}"
echo "  View logs:           docker logs -f octollm-orchestrator"
echo "  Stop services:       cd $SCRIPT_DIR && $COMPOSE_CMD stop"
echo "  Start services:      cd $SCRIPT_DIR && $COMPOSE_CMD start"
echo "  Restart services:    cd $SCRIPT_DIR && $COMPOSE_CMD restart"
echo "  View status:         cd $SCRIPT_DIR && $COMPOSE_CMD ps"
echo "  GPU monitoring:      nvidia-smi -l 1"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Access Grafana at http://${HOST_IP}:3030 and import dashboards"
echo "  2. Test Orchestrator API at http://${HOST_IP}:3000/docs"
echo "  3. Check GPU usage: nvidia-smi"
echo "  4. Review logs: docker logs octollm-orchestrator"
echo "  5. Read deployment guide: docs/operations/unraid-deployment-guide.md"
echo ""

if [ "$SKIP_BUILD" = true ]; then
    echo -e "${YELLOW}Important:${NC}"
    echo "  This repository is currently documentation-only."
    echo "  Implement services before running docker-compose up."
    echo "  See docs/implementation/getting-started.md for details."
    echo ""
fi

echo -e "${GREEN}Configuration Files:${NC}"
echo "  Docker Compose:      $COMPOSE_FILE"
echo "  Environment:         $ENV_FILE"
echo "  App Data:            $APPDATA_ROOT"
echo ""

log_success "Setup complete! Enjoy using OctoLLM on Unraid!"
