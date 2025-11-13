#!/bin/bash
# Test GPU availability and Docker GPU passthrough

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Testing GPU availability..."

# Test nvidia-smi
if ! nvidia-smi &> /dev/null; then
    echo -e "${RED}[FAIL]${NC} nvidia-smi not working"
    exit 1
fi

echo -e "${GREEN}[PASS]${NC} nvidia-smi working"
nvidia-smi

# Test Docker GPU access
echo ""
echo "Testing Docker GPU passthrough..."

if docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi; then
    echo -e "${GREEN}[PASS]${NC} Docker GPU passthrough working"
else
    echo -e "${RED}[FAIL]${NC} Docker GPU passthrough not working"
    exit 1
fi

echo ""
echo -e "${GREEN}All GPU tests passed!${NC}"
