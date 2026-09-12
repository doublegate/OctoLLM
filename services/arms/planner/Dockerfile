# syntax=docker/dockerfile:1
# Planner Arm Dockerfile - Multi-stage build for Python service
FROM python:3.14.7-slim AS builder

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
FROM python:3.14.7-slim

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

# Copy application code
COPY --chown=octollm:octollm services/arms/planner ./services/arms/planner
COPY --chown=octollm:octollm shared/python ./shared/python

# Numeric, per hadolint DL3066: a name need not resolve on the host.
USER 1000:1000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8001/health"]

# Expose port
EXPOSE 8001

# Run application
# The module path is resolved from the service directory rather than from /app.
# The previous CMD was `uvicorn services.arms.<arm>.src.main:app`, which needs a
# package chain of __init__.py files that never existed -- and for the safety
# guardian it could never work at all, because `safety-guardian` is not a legal
# Python identifier. Every one of these five containers crash-looped.
WORKDIR /app/services/arms/planner

# The shared arm framework lives here: the app factory, the error envelope, the
# contract models and the roster this arm reads its own declaration from.
ENV PYTHONPATH=/app/shared/python

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
