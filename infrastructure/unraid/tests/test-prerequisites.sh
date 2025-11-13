#!/bin/bash
# Test Prerequisites for OctoLLM Unraid Deployment
# Checks if all required software and hardware is available

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo "============================================================================"
echo "OctoLLM Unraid Prerequisites Check"
echo "============================================================================"
echo ""

# Check Unraid
if [ -f /etc/unraid-version ]; then
    UNRAID_VERSION=$(cat /etc/unraid-version)
    check_pass "Unraid detected: $UNRAID_VERSION"
else
    check_warn "Not running on Unraid (may still work)"
fi

# Check Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    check_pass "Docker installed: $DOCKER_VERSION"
else
    check_fail "Docker not installed"
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | tr -d ',')
    check_pass "Docker Compose installed: $COMPOSE_VERSION"
elif docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short)
    check_pass "Docker Compose V2 installed: $COMPOSE_VERSION"
else
    check_fail "Docker Compose not installed"
fi

# Check NVIDIA driver
if command -v nvidia-smi &> /dev/null; then
    NVIDIA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader)
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader)
    GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader)
    check_pass "NVIDIA driver installed: $NVIDIA_VERSION"
    check_pass "GPU detected: $GPU_NAME ($GPU_MEMORY)"
else
    check_warn "NVIDIA driver not found (GPU features unavailable)"
fi

# Check Docker NVIDIA runtime
if command -v nvidia-smi &> /dev/null; then
    if docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        check_pass "Docker NVIDIA runtime working"
    else
        check_fail "Docker NVIDIA runtime not working"
    fi
fi

# Check system resources
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
TOTAL_CPU=$(nproc)

if [ "$TOTAL_RAM" -ge 16 ]; then
    check_pass "RAM: ${TOTAL_RAM}GB (recommended: 16GB+)"
else
    check_fail "RAM: ${TOTAL_RAM}GB (minimum 16GB required)"
fi

if [ "$TOTAL_CPU" -ge 8 ]; then
    check_pass "CPU cores: $TOTAL_CPU (recommended: 8+)"
else
    check_warn "CPU cores: $TOTAL_CPU (recommended: 8+)"
fi

# Check disk space
APPDATA_SPACE=$(df -BG /mnt/user/appdata 2>/dev/null | awk 'NR==2 {print $4}' | tr -d 'G' || echo "0")
if [ "$APPDATA_SPACE" -ge 50 ]; then
    check_pass "Appdata space: ${APPDATA_SPACE}GB available (recommended: 50GB+)"
else
    check_warn "Appdata space: ${APPDATA_SPACE}GB available (recommended: 50GB+)"
fi

# Check network connectivity
if ping -c 1 8.8.8.8 &> /dev/null; then
    check_pass "Internet connectivity available"
else
    check_fail "No internet connectivity"
fi

# Check required ports
REQUIRED_PORTS=(3000 3001 3010 3011 3012 3014 6001 6002 6003 6004 6005 6006 9090 3030)
for port in "${REQUIRED_PORTS[@]}"; do
    if ! ss -tuln | grep -q ":$port "; then
        check_pass "Port $port available"
    else
        check_warn "Port $port already in use"
    fi
done

echo ""
echo "============================================================================"
echo "Summary: $PASS passed, $FAIL failed"
echo "============================================================================"

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All critical checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Some critical checks failed. Fix issues before proceeding.${NC}"
    exit 1
fi
