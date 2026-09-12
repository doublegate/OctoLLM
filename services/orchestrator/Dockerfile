# syntax=docker/dockerfile:1
# Orchestrator Service Dockerfile - Multi-stage build for production
FROM python:3.14.7-slim AS builder

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
FROM python:3.14.7-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 octollm && \
    useradd -m -u 1000 -g 1000 octollm && \
    mkdir -p /app && \
    chown -R octollm:octollm /app

WORKDIR /app

# Copy installed packages from builder.
# Copy all of /usr/local/lib rather than a hardcoded python3.X/site-packages path:
# builder and runtime share the same base image, so the rest of the tree is identical,
# and a future base-image bump cannot silently break the COPY.
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=octollm:octollm services/orchestrator ./services/orchestrator
COPY --chown=octollm:octollm shared/python ./shared/python

# Numeric, per hadolint DL3066: a name need not resolve on the host.
USER 1000:1000

# The application package is `app`, rooted at services/orchestrator/, and its modules
# import each other as `from app.config import ...`. Run from there so that resolves.
WORKDIR /app/services/orchestrator

# The shared arm framework. The orchestrator imports `octollm_common` for the arm
# roster, the contract models its registry publishes, and the error envelope every
# service now shares -- the same seam the arms import their FastAPI models from, which
# is what makes a field rename a type error rather than a 422 in production.
ENV PYTHONPATH=/app/shared/python

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health"]

# Expose port
EXPOSE 8000

# Run application
# The FastAPI app is services/orchestrator/app/main.py. The previous target,
# services.orchestrator.src.api.main, does not exist -- services/orchestrator/src/
# holds only .gitkeep placeholders -- so the container started uvicorn and then died
# on ModuleNotFoundError. No CI job builds or runs these images, so it went unseen.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
