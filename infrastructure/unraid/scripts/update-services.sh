#!/bin/bash
# Update OctoLLM services on Unraid

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

cd "$(dirname "$0")/.."

echo -e "${BLUE}Updating OctoLLM services...${NC}"

# Pull latest images
echo "Pulling latest images..."
docker-compose pull

# Rebuild custom images
echo "Rebuilding custom images..."
docker-compose build --pull

# Restart services with new images
echo "Restarting services..."
docker-compose up -d

# Wait for health checks
echo "Waiting for services to become healthy..."
sleep 30

# Show status
docker-compose ps

echo -e "${GREEN}Update complete!${NC}"
