"""
GCP Cloud Trace OpenTelemetry Integration

Configures OpenTelemetry to export traces to GCP Cloud Trace.
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

logger = logging.getLogger(__name__)


def init_gcp_tracing(
    project_id: Optional[str] = None,
    service_name: str = "netra-backend",
    environment: str = "staging",
    sampling_rate: float = 0.1
) -> Optional[TracerProvider]:
    """
    Initialize OpenTelemetry with GCP Cloud Trace exporter.
    
    Args:
        project_id: GCP project ID (defaults to environment variable)
        service_name: Name of the service
        environment: Environment name (staging/production)
        sampling_rate: Sampling rate for traces (0.0 to 1.0)
    
    Returns:
        TracerProvider instance or None if initialization fails
    """
    try:
        # Check if GCP tracing is enabled
        if not os.getenv("OTEL_EXPORTER_GCP_TRACE", "false").lower() == "true":
            logger.info("GCP Cloud Trace exporter not enabled")
            return None
        
        # Import GCP exporter (optional dependency)
        try:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
            from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
        except ImportError:
            logger.warning(
                "GCP Cloud Trace exporter not installed. "
                "Install with: pip install opentelemetry-exporter-gcp-trace"
            )
            return None
        
        # Get project ID
        project_id = project_id or os.getenv("GCP_PROJECT_ID", "netra-staging")
        
        # Create resource with service information
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: os.getenv("SERVICE_VERSION", "1.0.0"),
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: environment,
            "cloud.provider": "gcp",
            "cloud.platform": "gcp_cloud_run",
            "cloud.region": os.getenv("CLOUD_REGION", "us-central1"),
            "gcp.project_id": project_id,
        })
        
        # Create tracer provider with sampling
        sampler = TraceIdRatioBased(sampling_rate)
        tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler
        )
        
        # Create Cloud Trace exporter
        cloud_trace_exporter = CloudTraceSpanExporter(
            project_id=project_id
        )
        
        # Add batch span processor
        span_processor = BatchSpanProcessor(
            cloud_trace_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
        tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        logger.info(
            f"GCP Cloud Trace initialized for project {project_id} "
            f"with sampling rate {sampling_rate}"
        )
        
        return tracer_provider
        
    except Exception as e:
        logger.error(f"Failed to initialize GCP Cloud Trace: {e}")
        return None


def init_gcp_tracing_from_env() -> Optional[TracerProvider]:
    """
    Initialize GCP Cloud Trace using environment variables.
    
    Environment variables:
        - GCP_PROJECT_ID: GCP project ID
        - OTEL_SERVICE_NAME: Service name
        - ENVIRONMENT: Environment (staging/production)
        - OTEL_SAMPLING_RATE: Sampling rate (0.0 to 1.0)
    
    Returns:
        TracerProvider instance or None if initialization fails
    """
    return init_gcp_tracing(
        project_id=os.getenv("GCP_PROJECT_ID"),
        service_name=os.getenv("OTEL_SERVICE_NAME", "netra-backend"),
        environment=os.getenv("ENVIRONMENT", "staging"),
        sampling_rate=float(os.getenv("OTEL_SAMPLING_RATE", "0.1"))
    )


# Auto-instrument popular libraries for GCP
def auto_instrument_for_gcp():
    """
    Auto-instrument popular libraries for GCP Cloud Trace.
    """
    try:
        # FastAPI instrumentation
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor().instrument()
            logger.info("FastAPI auto-instrumented for GCP Cloud Trace")
        except ImportError:
            pass
        
        # Requests instrumentation
        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            RequestsInstrumentor().instrument()
            logger.info("Requests auto-instrumented for GCP Cloud Trace")
        except ImportError:
            pass
        
        # SQLAlchemy instrumentation
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument()
            logger.info("SQLAlchemy auto-instrumented for GCP Cloud Trace")
        except ImportError:
            pass
        
        # Redis instrumentation
        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            RedisInstrumentor().instrument()
            logger.info("Redis auto-instrumented for GCP Cloud Trace")
        except ImportError:
            pass
            
    except Exception as e:
        logger.warning(f"Auto-instrumentation failed: {e}")