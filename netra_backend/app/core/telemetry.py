"""
Comprehensive OpenTelemetry Manager for Netra Platform

SSOT for distributed tracing with proper OTLP export configuration.
Instruments all agent executions with spans for observability.
"""

import logging
from typing import Dict, Optional, Any, Callable
from contextlib import contextmanager
import os

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.propagate import extract, inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Exporters
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from netra_backend.app.core.config import get_config
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
config = get_config()


class TelemetryManager:
    """Manages OpenTelemetry SDK initialization and span creation for distributed tracing."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern for global telemetry manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize telemetry manager with lazy setup."""
        if not self._initialized:
            self.tracer: Optional[trace.Tracer] = None
            self.tracer_provider: Optional[TracerProvider] = None
            self.propagator = TraceContextTextMapPropagator()
            self.enabled = True
            self._initialized = True
    
    def init_telemetry(
        self, 
        service_name: Optional[str] = None,
        service_version: Optional[str] = None,
        otlp_endpoint: Optional[str] = None,
        jaeger_endpoint: Optional[str] = None,
        enable_console: bool = False
    ) -> None:
        """
        Initialize OpenTelemetry SDK with proper configuration.
        
        Args:
            service_name: Name of the service for tracing
            service_version: Version of the service
            otlp_endpoint: OTLP exporter endpoint
            jaeger_endpoint: Jaeger exporter endpoint
            enable_console: Whether to enable console exporter for debugging
        """
        try:
            # Get configuration from environment or defaults
            service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "netra-backend")
            service_version = service_version or os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
            otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
            jaeger_endpoint = jaeger_endpoint or os.getenv("JAEGER_ENDPOINT", "localhost:6831")
            
            # Check if telemetry should be enabled
            self.enabled = os.getenv("OTEL_ENABLED", "true").lower() == "true"
            if not self.enabled:
                logger.info("OpenTelemetry is disabled via configuration")
                return
            
            # Create resource with service information
            resource = Resource.create({
                SERVICE_NAME: service_name,
                SERVICE_VERSION: service_version,
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
                "service.namespace": "netra",
            })
            
            # Initialize TracerProvider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)
            
            # Add OTLP exporter if endpoint is configured
            if otlp_endpoint and otlp_endpoint != "none":
                try:
                    otlp_exporter = OTLPSpanExporter(
                        endpoint=otlp_endpoint,
                        insecure=True,  # Use insecure for local development
                    )
                    self.tracer_provider.add_span_processor(
                        BatchSpanProcessor(otlp_exporter)
                    )
                    logger.info(f"OTLP exporter configured: {otlp_endpoint}")
                except Exception as e:
                    logger.warning(f"Failed to configure OTLP exporter: {e}")
            
            # Add Jaeger exporter if endpoint is configured
            if jaeger_endpoint and jaeger_endpoint != "none":
                try:
                    jaeger_exporter = JaegerExporter(
                        agent_host_name=jaeger_endpoint.split(":")[0],
                        agent_port=int(jaeger_endpoint.split(":")[1]) if ":" in jaeger_endpoint else 6831,
                        udp_split_oversized_batches=True,
                    )
                    self.tracer_provider.add_span_processor(
                        BatchSpanProcessor(jaeger_exporter)
                    )
                    logger.info(f"Jaeger exporter configured: {jaeger_endpoint}")
                except Exception as e:
                    logger.warning(f"Failed to configure Jaeger exporter: {e}")
            
            # Add console exporter for debugging if enabled
            if enable_console or os.getenv("OTEL_CONSOLE_EXPORTER", "false").lower() == "true":
                console_exporter = ConsoleSpanExporter()
                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(console_exporter)
                )
                logger.info("Console exporter enabled for debugging")
            
            # Get tracer
            self.tracer = trace.get_tracer(
                instrumenting_module_name=__name__,
                instrumenting_library_version="1.0.0"
            )
            
            # Auto-instrument libraries
            self._instrument_libraries()
            
            logger.info(f"OpenTelemetry initialized for service: {service_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            self.enabled = False
    
    def _instrument_libraries(self) -> None:
        """Auto-instrument common libraries for automatic span creation."""
        try:
            # Instrument FastAPI for automatic HTTP span creation
            FastAPIInstrumentor.instrument(
                excluded_urls="/health,/metrics"
            )
            
            # Instrument HTTP client requests
            RequestsInstrumentor().instrument()
            
            # Instrument Redis operations
            RedisInstrumentor().instrument()
            
            # Note: SQLAlchemy instrumentation should be done with the engine instance
            # SQLAlchemyInstrumentor().instrument(engine=engine)
            
            logger.info("Automatic instrumentation configured for FastAPI, Requests, Redis")
            
        except Exception as e:
            logger.warning(f"Failed to configure automatic instrumentation: {e}")
    
    def create_agent_span(
        self, 
        agent_name: str, 
        operation: str,
        parent_span: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Create a span for agent execution.
        
        Args:
            agent_name: Name of the agent
            operation: Operation being performed
            parent_span: Optional parent span for nested operations
            attributes: Optional attributes to add to the span
        
        Returns:
            The created span
        """
        if not self.enabled or not self.tracer:
            return None
        
        span_name = f"{agent_name}.{operation}"
        
        # Create span with optional parent context
        context = trace.set_span_in_context(parent_span) if parent_span else None
        span = self.tracer.start_span(span_name, context=context)
        
        # Set default attributes
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("agent.operation", operation)
        
        # Add custom attributes if provided
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        logger.debug(f"Created span: {span_name}")
        return span
    
    @contextmanager
    def start_agent_span(
        self,
        agent_name: str,
        operation: str,
        parent_span: Optional[Span] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for agent span lifecycle.
        
        Args:
            agent_name: Name of the agent
            operation: Operation being performed
            parent_span: Optional parent span
            attributes: Optional span attributes
        
        Yields:
            The created span
        """
        if not self.enabled or not self.tracer:
            yield None
            return
        
        span = self.create_agent_span(agent_name, operation, parent_span, attributes)
        
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            self.record_exception(span, e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            if span:
                span.end()
    
    def add_event(
        self, 
        span: Optional[Span], 
        event_name: str, 
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an event to a span.
        
        Args:
            span: The span to add event to
            event_name: Name of the event
            attributes: Optional event attributes
        """
        if not span or not self.enabled:
            return
        
        try:
            span.add_event(event_name, attributes=attributes or {})
            logger.debug(f"Added event '{event_name}' to span")
        except Exception as e:
            logger.warning(f"Failed to add event to span: {e}")
    
    def record_exception(self, span: Optional[Span], exception: Exception) -> None:
        """
        Record an exception in a span.
        
        Args:
            span: The span to record exception in
            exception: The exception to record
        """
        if not span or not self.enabled:
            return
        
        try:
            span.record_exception(exception)
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(exception).__name__)
            span.set_attribute("error.message", str(exception))
            logger.debug(f"Recorded exception in span: {exception}")
        except Exception as e:
            logger.warning(f"Failed to record exception in span: {e}")
    
    def set_status(self, span: Optional[Span], status: Status) -> None:
        """
        Set the status of a span.
        
        Args:
            span: The span to set status for
            status: The status to set
        """
        if not span or not self.enabled:
            return
        
        try:
            span.set_status(status)
        except Exception as e:
            logger.warning(f"Failed to set span status: {e}")
    
    def extract_trace_context(self, carrier: Dict[str, str]) -> Any:
        """
        Extract trace context from carrier (e.g., HTTP headers).
        
        Args:
            carrier: Dictionary containing trace context
        
        Returns:
            Extracted context
        """
        if not self.enabled:
            return None
        
        return extract(carrier)
    
    def inject_trace_context(self, carrier: Dict[str, str]) -> None:
        """
        Inject trace context into carrier (e.g., HTTP headers).
        
        Args:
            carrier: Dictionary to inject trace context into
        """
        if not self.enabled:
            return
        
        inject(carrier)
    
    def get_current_span(self) -> Optional[Span]:
        """Get the currently active span."""
        if not self.enabled:
            return None
        
        return trace.get_current_span()
    
    def shutdown(self) -> None:
        """Shutdown telemetry and flush all pending spans."""
        if self.tracer_provider:
            try:
                self.tracer_provider.shutdown()
                logger.info("OpenTelemetry shutdown successfully")
            except Exception as e:
                logger.error(f"Error shutting down OpenTelemetry: {e}")


class AgentTracer:
    """High-level interface for agent tracing operations."""
    
    def __init__(self, telemetry_manager: Optional[TelemetryManager] = None):
        """Initialize agent tracer with telemetry manager."""
        self.telemetry = telemetry_manager or TelemetryManager()
    
    def start_agent_span(
        self, 
        agent_name: str, 
        context: Dict[str, Any]
    ) -> Span:
        """
        Start a span for agent execution.
        
        Args:
            agent_name: Name of the agent
            context: Execution context with metadata
        
        Returns:
            The created span
        """
        attributes = {
            "agent.id": context.get("agent_id"),
            "user.id": context.get("user_id"),
            "thread.id": context.get("thread_id"),
            "session.id": context.get("session_id"),
        }
        
        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}
        
        return self.telemetry.create_agent_span(
            agent_name=agent_name,
            operation="execute",
            attributes=attributes
        )
    
    def add_event(
        self, 
        span: Span, 
        event_name: str, 
        attributes: Dict[str, Any]
    ) -> None:
        """Add an event to the span."""
        self.telemetry.add_event(span, event_name, attributes)
    
    def record_exception(self, span: Span, exception: Exception) -> None:
        """Record an exception in the span."""
        self.telemetry.record_exception(span, exception)
    
    def set_status(self, span: Span, status: Status) -> None:
        """Set the status of the span."""
        self.telemetry.set_status(span, status)


# Global telemetry manager instance
telemetry_manager = TelemetryManager()

# Global agent tracer instance
agent_tracer = AgentTracer(telemetry_manager)