# syntax=docker/dockerfile:1
# Executor Arm Dockerfile - Multi-stage build for Rust service (security-critical)
FROM rust:1.75-slim as builder

# Install dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy workspace files
COPY Cargo.toml Cargo.lock ./
COPY shared/rust ./shared/rust
COPY services/arms/executor ./services/arms/executor

# Build release binary
RUN cargo build --release --package executor-arm

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 octollm && \
    mkdir -p /app && \
    chown -R octollm:octollm /app

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/executor-arm ./executor-arm

# Set ownership
RUN chown octollm:octollm executor-arm

USER octollm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# Expose port
EXPOSE 8006

# Run application
CMD ["./executor-arm"]
