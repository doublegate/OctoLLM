#!/bin/bash
# Test OctoLLM service health checks

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Source environment
if [ -f .env.unraid ]; then
    set -a
    # shellcheck source=/dev/null
    source .env.unraid
    set +a
else
    echo -e "${RED}[ERROR]${NC} .env.unraid not found"
    exit 1
fi

HOST_IP=${HOST_IP:-192.168.4.6}

SERVICES=(
    "orchestrator:$HOST_IP:3000:/health"
    "reflex-layer:$HOST_IP:3001:/health"
    "planner-arm:$HOST_IP:6001:/health"
    "executor-arm:$HOST_IP:6002:/health"
    "retriever-arm:$HOST_IP:6003:/health"
    "coder-arm:$HOST_IP:6004:/health"
    "judge-arm:$HOST_IP:6005:/health"
    "safety-guardian-arm:$HOST_IP:6006:/health"
    "prometheus:$HOST_IP:9090:/-/healthy"
    "grafana:$HOST_IP:3030:/api/health"
)

echo "Testing OctoLLM service health..."
echo ""

PASS=0
FAIL=0

for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r name host port path <<< "$service_info" || true

    if curl -sf "http://$host:$port$path" > /dev/null 2>&1; then
        echo -e "${GREEN}[PASS]${NC} $name is healthy"
        ((PASS++))
    else
        echo -e "${RED}[FAIL]${NC} $name is not responding"
        ((FAIL++))
    fi
done

echo ""
echo "============================================================================"
echo "Summary: $PASS passed, $FAIL failed"
echo "============================================================================"

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All services are healthy!${NC}"
    exit 0
else
    echo -e "${RED}Some services are not responding.${NC}"
    exit 1
fi
