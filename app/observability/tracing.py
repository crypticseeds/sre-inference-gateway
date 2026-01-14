"""OpenTelemetry tracing setup."""

import logging
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = logging.getLogger(__name__)


def setup_tracing() -> None:
    """Setup OpenTelemetry tracing."""
    # Create resource
    resource = Resource.create(
        {
            "service.name": "sre-inference-gateway",
            "service.version": "0.1.0",
        }
    )

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Add console exporter for development
    console_exporter = ConsoleSpanExporter()
    console_processor = BatchSpanProcessor(console_exporter)
    tracer_provider.add_span_processor(console_processor)

    # TODO: Add OTLP exporter for production when needed
    # from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    # otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:14250")
    # otlp_processor = BatchSpanProcessor(otlp_exporter)
    # tracer_provider.add_span_processor(otlp_processor)

    logger.info("OpenTelemetry tracing initialized")


def get_tracer(name: str) -> trace.Tracer:
    """Get tracer instance.

    Args:
        name: Tracer name

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
