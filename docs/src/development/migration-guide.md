# Migration Guide

**Last Updated**: 2025-11-10
**Target Audience**: Developers, DevOps Engineers
**Purpose**: Guide for migrating between OctoLLM versions

## Overview

This guide provides instructions for migrating OctoLLM installations between versions, including database schema changes, configuration updates, and code modifications required for breaking changes.

## Table of Contents

- [General Migration Process](#general-migration-process)
- [Version-Specific Migrations](#version-specific-migrations)
- [Database Migrations](#database-migrations)
- [Configuration Migrations](#configuration-migrations)
- [API Migrations](#api-migrations)
- [Rollback Procedures](#rollback-procedures)

---

## General Migration Process

### Pre-Migration Checklist

- [ ] **Review release notes** for version changes
- [ ] **Backup database** and configuration
- [ ] **Test migration** in staging environment
- [ ] **Plan maintenance window** if needed
- [ ] **Prepare rollback plan**
- [ ] **Notify users** of scheduled downtime

### Migration Steps

1. **Backup Current State**
   ```bash
   # Backup database
   pg_dump octollm > octollm_backup_$(date +%Y%m%d_%H%M%S).sql

   # Backup configuration
   cp .env .env.backup
   tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz config/

   # Backup volumes
   docker run --rm -v octollm_postgres_data:/data \
     -v $(pwd):/backup ubuntu \
     tar czf /backup/postgres_data_backup.tar.gz /data
   ```

2. **Stop Services**
   ```bash
   # Docker Compose
   docker compose down

   # Kubernetes
   kubectl scale deployment --all --replicas=0 -n octollm
   ```

3. **Update Code**
   ```bash
   # Pull new version
   git fetch --tags
   git checkout v0.2.0

   # Update dependencies
   poetry lock
   poetry install

   # Build new images
   docker compose build
   ```

4. **Run Database Migrations**
   ```bash
   # Review migration
   alembic history
   alembic current

   # Run migrations
   alembic upgrade head

   # Verify
   alembic current
   ```

5. **Update Configuration**
   ```bash
   # Compare .env.example with your .env
   diff .env.example .env

   # Add new required variables
   vim .env
   ```

6. **Start Services**
   ```bash
   # Docker Compose
   docker compose up -d

   # Kubernetes
   kubectl apply -f k8s/
   kubectl rollout status deployment -n octollm
   ```

7. **Verify Migration**
   ```bash
   # Check service health
   curl http://localhost:8000/health

   # Run smoke tests
   pytest tests/smoke/ -v

   # Check logs for errors
   docker compose logs --tail=100
   ```

---

## Version-Specific Migrations

### v0.1.0 → v0.2.0 (Example)

**Release Date**: 2025-12-01
**Type**: Minor (New features, backward compatible)

#### Breaking Changes
None

#### New Features
- Parallel task execution
- Enhanced caching layer
- New performance metrics

#### Migration Steps

1. **Update Configuration**
   ```bash
   # Add new cache configuration
   cat >> .env <<EOF
   # Cache Configuration (v0.2.0+)
   CACHE_L1_SIZE=1000
   CACHE_L1_TTL=60
   CACHE_L2_TTL=3600
   EOF
   ```

2. **Database Migration**
   ```bash
   # New indexes for performance
   alembic upgrade head

   # This adds:
   # - idx_tasks_status_priority
   # - idx_task_history_created_brin
   ```

3. **Update Docker Compose**
   ```yaml
   # docker-compose.yml - Update orchestrator service
   orchestrator:
     image: octollm/orchestrator:0.2.0  # Updated version
     environment:
       - CACHE_L1_SIZE=1000  # New config
       - CACHE_L1_TTL=60
   ```

4. **No Code Changes Required**
   - API remains backward compatible
   - Existing clients continue to work

### v0.1.0 → v1.0.0 (Example - Breaking Changes)

**Release Date**: 2026-01-01
**Type**: Major (Breaking changes)

#### Breaking Changes
- ⚠️ API endpoint paths changed (`/tasks` → `/api/v1/tasks`)
- ⚠️ Task priority scale changed (1-5 → 1-10)
- ⚠️ Removed deprecated `/execute` endpoint

#### Migration Steps

1. **Update Client Code**
   ```python
   # Before (v0.x)
   response = await client.post(
       "http://localhost:8000/tasks",
       json={"description": "...", "priority": 3}
   )

   # After (v1.0)
   response = await client.post(
       "http://localhost:8000/api/v1/tasks",
       json={"description": "...", "priority": 6}  # 3 * 2
   )
   ```

2. **Database Migration**
   ```bash
   # Migrate priority values
   alembic upgrade head

   # This runs:
   # UPDATE tasks SET priority = priority * 2;
   ```

3. **Update Configuration**
   ```bash
   # Update webhook URLs
   vim .env
   # WEBHOOK_URL=https://example.com/octollm/v1/webhook
   ```

4. **Update Integration Tests**
   ```python
   # Update all API endpoint URLs
   find tests/ -name "*.py" -exec sed -i 's|/tasks|/api/v1/tasks|g' {} \;
   ```

---

## Database Migrations

### Running Migrations

```bash
# Check current version
alembic current

# View migration history
alembic history --verbose

# Upgrade to specific version
alembic upgrade <revision>

# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision>
```

### Creating Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "add_task_priority_index"

# Create empty migration
alembic revision -m "custom_data_migration"

# Edit migration
vim alembic/versions/xxx_add_task_priority_index.py
```

### Example Migration

```python
"""add_task_priority_index

Revision ID: abc123
Revises: def456
Create Date: 2025-11-10 10:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade database schema."""
    # Create index concurrently (doesn't block reads/writes)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_status_priority
        ON tasks(status, priority DESC)
    """)

def downgrade():
    """Rollback database schema."""
    op.execute("""
        DROP INDEX IF EXISTS idx_tasks_status_priority
    """)
```

### Large Data Migrations

For large datasets, use batching:

```python
def upgrade():
    """Migrate task priority from 1-5 to 1-10 scale."""
    connection = op.get_bind()

    # Process in batches to avoid long locks
    batch_size = 1000
    offset = 0

    while True:
        result = connection.execute(
            sa.text("""
                UPDATE tasks
                SET priority = priority * 2
                WHERE id IN (
                    SELECT id FROM tasks
                    WHERE priority < 6  -- Old scale
                    LIMIT :batch_size OFFSET :offset
                )
            """),
            {"batch_size": batch_size, "offset": offset}
        )

        if result.rowcount == 0:
            break

        offset += batch_size
        print(f"Migrated {offset} tasks...")
```

---

## Configuration Migrations

### Environment Variables

**Deprecated Variables**:
```bash
# v0.1.0 (deprecated in v0.2.0)
CACHE_ENABLED=true
CACHE_TTL=3600

# v0.2.0+ (new format)
CACHE_L1_ENABLED=true
CACHE_L1_SIZE=1000
CACHE_L1_TTL=60
CACHE_L2_ENABLED=true
CACHE_L2_TTL=3600
```

**Migration Script**:
```bash
#!/bin/bash
# migrate_env.sh - Migrate .env from v0.1.0 to v0.2.0

# Backup
cp .env .env.v010.backup

# Add new variables
if grep -q "CACHE_ENABLED" .env; then
    CACHE_ENABLED=$(grep CACHE_ENABLED .env | cut -d '=' -f2)
    CACHE_TTL=$(grep CACHE_TTL .env | cut -d '=' -f2)

    cat >> .env <<EOF

# Cache Configuration (v0.2.0+)
CACHE_L1_ENABLED=${CACHE_ENABLED}
CACHE_L1_SIZE=1000
CACHE_L1_TTL=60
CACHE_L2_ENABLED=${CACHE_ENABLED}
CACHE_L2_TTL=${CACHE_TTL}
EOF

    # Comment out old variables
    sed -i 's/^CACHE_ENABLED/#CACHE_ENABLED (deprecated)/' .env
    sed -i 's/^CACHE_TTL/#CACHE_TTL (deprecated)/' .env

    echo "✅ Migrated cache configuration"
fi
```

### Docker Compose

**v0.1.0**:
```yaml
services:
  orchestrator:
    image: octollm/orchestrator:0.1.0
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
```

**v0.2.0**:
```yaml
services:
  orchestrator:
    image: octollm/orchestrator:0.2.0
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CACHE_L1_SIZE=${CACHE_L1_SIZE}  # New
      - CACHE_L1_TTL=${CACHE_L1_TTL}    # New
```

---

## API Migrations

### Client Code Updates

**SDK Updates**:
```bash
# Update OctoLLM SDK
pip install --upgrade octollm-sdk

# Or with specific version
pip install octollm-sdk==1.0.0
```

**API Changes**:

**Before (v0.x)**:
```python
from octollm import Client

client = Client(base_url="http://localhost:8000")

# Submit task
task = client.tasks.create(
    description="Write Python code",
    priority=3  # 1-5 scale
)

# Get status
status = client.tasks.get(task.id)
```

**After (v1.0)**:
```python
from octollm import Client

client = Client(
    base_url="http://localhost:8000/api/v1"  # Updated path
)

# Submit task
task = client.tasks.create(
    description="Write Python code",
    priority=6  # 1-10 scale (3 * 2)
)

# Get status
status = client.tasks.get(task.id)
```

---

## Rollback Procedures

### Database Rollback

```bash
# Rollback to previous version
alembic downgrade -1

# Rollback to specific version
alembic downgrade abc123

# Verify rollback
alembic current
```

### Application Rollback

**Docker Compose**:
```bash
# Stop current version
docker compose down

# Restore backup
docker run --rm -v octollm_postgres_data:/data \
  -v $(pwd):/backup ubuntu \
  tar xzf /backup/postgres_data_backup.tar.gz -C /

# Restore configuration
cp .env.backup .env

# Start previous version
git checkout v0.1.0
docker compose up -d
```

**Kubernetes**:
```bash
# Rollback deployment
kubectl rollout undo deployment orchestrator -n octollm

# Rollback to specific revision
kubectl rollout undo deployment orchestrator --to-revision=2 -n octollm

# Check status
kubectl rollout status deployment orchestrator -n octollm
```

### Data Rollback

```bash
# Restore database from backup
docker compose down
docker volume rm octollm_postgres_data

# Restore from backup
psql octollm < octollm_backup_20251110_120000.sql

# Verify
psql octollm -c "SELECT COUNT(*) FROM tasks;"
```

---

## Testing Migrations

### Staging Environment

```bash
# 1. Clone production data to staging
pg_dump production_db | psql staging_db

# 2. Run migration on staging
alembic upgrade head

# 3. Run integration tests
pytest tests/integration/ -v

# 4. Performance test
k6 run tests/load/migration_test.js

# 5. Verify data integrity
python scripts/verify_migration.py
```

### Verification Script

```python
# scripts/verify_migration.py
import asyncio
from octollm.database import Database

async def verify_migration():
    """Verify migration completed successfully."""
    db = Database()

    # Check task counts
    before_count = 1000  # Known value before migration
    after_count = await db.fetch_one(
        "SELECT COUNT(*) FROM tasks"
    )
    assert after_count == before_count, "Task count mismatch"

    # Check priority values
    invalid_priorities = await db.fetch_one("""
        SELECT COUNT(*) FROM tasks
        WHERE priority < 1 OR priority > 10
    """)
    assert invalid_priorities == 0, "Invalid priorities found"

    # Check indexes exist
    indexes = await db.fetch_all("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'tasks'
    """)
    required = ['idx_tasks_status_priority']
    for idx in required:
        assert any(i['indexname'] == idx for i in indexes), \
            f"Missing index: {idx}"

    print("✅ Migration verified successfully")

if __name__ == "__main__":
    asyncio.run(verify_migration())
```

---

## Best Practices

1. **Always backup** before migration
2. **Test in staging** first
3. **Plan maintenance window** for large migrations
4. **Monitor closely** during and after migration
5. **Document rollback** procedure before starting
6. **Communicate** with users about downtime
7. **Keep backups** for at least 30 days
8. **Run verification** scripts after migration

---

## Support

For migration help:
- **Documentation**: https://docs.octollm.com
- **Issues**: https://github.com/octollm/octollm/issues
- **Discord**: https://discord.gg/octollm
- **Email**: support@octollm.com

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly)
**Owner**: Engineering Team
