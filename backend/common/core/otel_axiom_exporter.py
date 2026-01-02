from typing import Dict, Optional
import functools
import asyncio
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import ConsoleLogExporter
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from common.core.config import settings

# Configure logging at module level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # This ensures it overrides any existing configuration
)


# Global flag to ensure initialization only happens once
_initialized = False
axiom_tracer = None
propagator = None


def _initialize_telemetry():
    """Initialize telemetry once and only once."""
    global _initialized, axiom_tracer, propagator

    if _initialized:
        return

    # Your existing setup code here...
    SERVICE = settings.otel_service_name
    resource = Resource(attributes={SERVICE_NAME: settings.otel_service_name})

    # TRACING SETUP
    provider = TracerProvider(resource=resource)
    otlp_trace_exporter = OTLPSpanExporter(
        endpoint="https://api.axiom.co/v1/traces",
        headers={
            "Authorization": f"Bearer {settings.axiom_token}",
            "X-Axiom-Dataset": settings.axiom_dataset,
        },
    )
    processor = BatchSpanProcessor(otlp_trace_exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    axiom_tracer = trace.get_tracer(SERVICE)
    propagator = TraceContextTextMapPropagator()

    # LOGGING SETUP
    logger_provider = LoggerProvider(resource=resource)
    otlp_log_exporter = OTLPLogExporter(
        endpoint="https://api.axiom.co/v1/logs",
        headers={
            "Authorization": f"Bearer {settings.axiom_token}",
            "X-Axiom-Dataset": settings.axiom_dataset,
        },
    )

    console_exporter = ConsoleLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(console_exporter))
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
    set_logger_provider(logger_provider)

    # Configure logging handler
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

    # Add to root logger
    root_logger = logging.getLogger()

    # TODO: for now turning this off since it doesn't actually export to axiom properly
    # root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Instrument logging
    # LoggingInstrumentor().instrument(set_logging_format=True)

    _initialized = True
    print("Telemetry initialized successfully")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance. Ensures telemetry is initialized.
    Use this instead of logging.getLogger() directly.
    """
    if not _initialized:
        _initialize_telemetry()
    return logging.getLogger(name)


# Custom decorator for automatic span naming
def trace_span(func):
    """Decorator that automatically creates a span with the function name."""

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        # Get the span name from function
        span_name = func.__name__
        if args and hasattr(args[0], "__class__"):
            # If it's a method, include class name
            span_name = f"{args[0].__class__.__name__}.{func.__name__}"

        with axiom_tracer.start_as_current_span(span_name):
            return func(*args, **kwargs)

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Get the span name from function
        span_name = func.__name__
        if args and hasattr(args[0], "__class__"):
            # If it's a method, include class name
            span_name = f"{args[0].__class__.__name__}.{func.__name__}"

        with axiom_tracer.start_as_current_span(span_name):
            return await func(*args, **kwargs)

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Utility functions for trace context propagation (used in Temporal activities)
def create_span_with_context(
    span_name: str, trace_headers: Optional[Dict[str, str]] = None
):
    """
    Create a span with trace context from headers.
    If trace_headers is provided, extract context and create a child span.
    Otherwise, create a new root span.
    """
    if trace_headers:
        # Extract trace context from headers
        ctx = propagator.extract(trace_headers)
        # Start span as child of extracted context
        return axiom_tracer.start_as_current_span(span_name, context=ctx)
    else:
        # Start a new root span
        return axiom_tracer.start_as_current_span(span_name)


def inject_trace_context() -> Dict[str, str]:
    """
    Inject current trace context into headers for propagation.
    """
    headers = {}
    propagator.inject(headers)
    return headers


# Helper function to log within current span context
def log_span_event(message: str, attributes: Optional[Dict[str, any]] = None):
    """
    Log a message as an event in the current span.
    This will make the log appear in the trace view in Axiom.
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.add_event(message, attributes=attributes or {})

    # Also log normally so it appears in logs
    logger = get_logger(__name__)
    logger.info(message, extra=attributes)
