"""
OpenTelemetry Instrumentation for OctoLLM Orchestrator

This module configures distributed tracing with Jaeger using OpenTelemetry.
Automatically instruments FastAPI and adds custom spans for LLM calls and database queries.

Usage:
    from app.telemetry import init_telemetry

    # Initialize at application startup
    init_telemetry(service_name="orchestrator", environment="production")

Environment Variables:
    JAEGER_ENDPOINT: Jaeger collector endpoint (default: http://jaeger-collector.octollm-monitoring.svc.cluster.local:4317)
    OTEL_SAMPLING_RATE: Sampling rate 0.0-1.0 (default: 0.10 for prod, 1.0 for dev)
    ENVIRONMENT: dev/staging/prod (default: dev)
"""

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased


def init_telemetry(
    service_name: str = "orchestrator",
    environment: str | None = None,
    jaeger_endpoint: str | None = None,
    sampling_rate: float | None = None,
) -> None:
    """
    Initialize OpenTelemetry tracing with Jaeger exporter.

    Args:
        service_name: Name of the service (default: "orchestrator")
        environment: Deployment environment (dev/staging/prod)
        jaeger_endpoint: Jaeger collector OTLP endpoint
        sampling_rate: Trace sampling rate (0.0-1.0)
    """
    # Get configuration from environment
    environment = environment or os.getenv("ENVIRONMENT", "dev")
    jaeger_endpoint = jaeger_endpoint or os.getenv(
        "JAEGER_ENDPOINT",
        "http://jaeger-collector.octollm-monitoring.svc.cluster.local:4317",
    )

    # Set sampling rate based on environment
    if sampling_rate is None:
        sampling_rate = 1.0 if environment == "dev" else 0.10

    # Create resource with service metadata
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "octollm",
            "service.instance.id": os.getenv("HOSTNAME", "unknown"),
            "deployment.environment": environment,
            "service.version": os.getenv("APP_VERSION", "0.9.0"),
        }
    )

    # Configure tracer provider with sampling
    sampler = ParentBasedTraceIdRatioBased(sampling_rate)
    provider = TracerProvider(resource=resource, sampler=sampler)

    # Configure OTLP exporter to Jaeger
    otlp_exporter = OTLPSpanExporter(
        endpoint=jaeger_endpoint,
        insecure=True,  # Use TLS in production
    )

    # Add batch span processor for efficient export
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument()

    # Auto-instrument HTTP client (for LLM API calls)
    HTTPXClientInstrumentor.instrument()

    # Auto-instrument database
    Psycopg2Instrumentor().instrument()

    # Auto-instrument Redis
    RedisInstrumentor().instrument()

    logging.info(
        "OpenTelemetry initialized: %s (sampling: %.1f%%)", service_name, sampling_rate * 100
    )


def get_tracer(name: str = __name__) -> trace.Tracer:
    """
    Get a tracer for creating custom spans.

    Args:
        name: Tracer name (typically __name__)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


# Example usage for custom spans:
#
# from app.telemetry import get_tracer
#
# tracer = get_tracer(__name__)
#
# # Add custom span for LLM call
# with tracer.start_as_current_span("llm_call") as span:
#     span.set_attribute("llm.provider", "openai")
#     span.set_attribute("llm.model", "gpt-4")
#     span.set_attribute("llm.prompt_tokens", 150)
#     span.set_attribute("llm.completion_tokens", 50)
#     result = call_llm(prompt)
#     return result
