# syntax=docker/dockerfile:1
# Planner Arm Dockerfile - Multi-stage build for Python service
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./
COPY shared/python ./shared/python

# Install dependencies (no dev)
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 octollm && \
    mkdir -p /app && \
    chown -R octollm:octollm /app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=octollm:octollm services/arms/planner ./services/arms/planner
COPY --chown=octollm:octollm shared/python ./shared/python

USER octollm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "services.arms.planner.src.main:app", "--host", "0.0.0.0", "--port", "8001"]
