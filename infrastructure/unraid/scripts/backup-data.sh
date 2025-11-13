#!/bin/bash
# Backup OctoLLM data on Unraid

set -euo pipefail

export APPDATA="/mnt/user/appdata/octollm"
BACKUP_DIR="/mnt/user/backups/octollm"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="octollm_backup_${TIMESTAMP}"

echo "Starting OctoLLM backup..."
echo "Timestamp: $TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop services to ensure consistent backup
echo "Stopping services..."
cd "$(dirname "$0")/.."
docker-compose stop

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker-compose start postgres
sleep 5
docker exec octollm-postgres pg_dumpall -U octollm > "$BACKUP_DIR/${BACKUP_NAME}_postgres.sql"
docker-compose stop postgres

# Backup data directories
echo "Backing up data directories..."
tar -czf "$BACKUP_DIR/${BACKUP_NAME}_data.tar.gz" \
  -C /mnt/user/appdata \
  --exclude='octollm/ollama/models' \
  octollm/

# Calculate sizes
POSTGRES_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}_postgres.sql" | cut -f1)
DATA_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}_data.tar.gz" | cut -f1)

echo "Backup complete!"
echo "  PostgreSQL: $POSTGRES_SIZE"
echo "  Data files: $DATA_SIZE"
echo "  Location: $BACKUP_DIR"

# Restart services
echo "Restarting services..."
docker-compose start

echo "Done!"
