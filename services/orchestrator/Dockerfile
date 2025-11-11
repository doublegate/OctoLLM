# syntax=docker/dockerfile:1
# Orchestrator Service Dockerfile - Multi-stage build for production
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
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
    libpq5 \
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
COPY --chown=octollm:octollm services/orchestrator ./services/orchestrator
COPY --chown=octollm:octollm shared/python ./shared/python

USER octollm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "services.orchestrator.src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
