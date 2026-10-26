# syntax=docker/dockerfile:1
# Memory / Curator Arm - Multi-stage build for Python service
FROM python:3.14.8-slim AS builder

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

# Install dependencies (no dev). The root manifest already carries sqlalchemy,
# psycopg, qdrant-client and alembic -- this arm adds no dependency the stack did not
# already declare, which is why there is no second install step here.
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# Runtime stage
FROM python:3.14.8-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
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

# Application code. The alembic tree comes along because this same image runs the
# migration one-shot in compose -- one image, so the migration and the service can
# never be built from different revisions of the schema.
COPY --chown=octollm:octollm services/arms/memory ./services/arms/memory
COPY --chown=octollm:octollm shared/python ./shared/python

# Numeric, per hadolint DL3066: a name need not resolve on the host.
USER 1000:1000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8007/health"]

EXPOSE 8007

# The module path is resolved from the service directory rather than from /app. The
# five arm containers that crash-looped for an entire phase did so on a CMD naming a
# package chain of __init__.py files that never existed.
WORKDIR /app/services/arms/memory

# The shared arm framework lives here: the app factory, the error envelope, the
# contract models, the capability gate, the Neural Ring and the roster.
ENV PYTHONPATH=/app/shared/python

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8007"]
