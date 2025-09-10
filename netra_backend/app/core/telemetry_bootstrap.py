"""
OpenTelemetry Bootstrap Module - AUTOMATIC INSTRUMENTATION ONLY

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Observability and Performance Monitoring
- Value Impact: Enables distributed tracing with <5% performance overhead
- Strategic Impact: Provides end-to-end visibility across microservices

This module provides AUTOMATIC instrumentation setup for OpenTelemetry, integrated
with the Netra backend's SSOT configuration patterns. It follows the principle of
automatic instrumentation without manual span creation.

Key Features:
- Environment-based configuration only
- Automatic FastAPI, Redis, SQLAlchemy, and HTTP instrumentation
- GCP Cloud Trace integration for production
- Performance optimized with minimal overhead
- SSOT configuration integration
"""

import os
import logging
from typing import Optional, Dict, Any

# Import configuration using SSOT patterns - minimal dependencies
from shared.isolated_environment import get_env


def _get_current_environment(env) -> str:
    """Get current environment from environment variables."""
    # Check for pytest context
    if env.get("PYTEST_CURRENT_TEST") or env.get("TESTING"):
        return "testing"
    
    # Check explicit environment setting
    env_name = env.get("ENVIRONMENT", "").lower()
    if env_name in ["development", "staging", "production", "testing"]:
        return env_name
    
    # Default to development
    return "development"


def bootstrap_telemetry() -> bool:
    """
    Bootstrap OpenTelemetry automatic instrumentation.
    
    Returns:
        bool: True if successfully initialized, False otherwise
        
    Environment Variables:
        OTEL_ENABLED: Enable/disable telemetry (default: false for testing, true otherwise)
        OTEL_SERVICE_NAME: Service name (default: netra-backend)
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint for traces
        OTEL_RESOURCE_ATTRIBUTES: Additional resource attributes
        GOOGLE_CLOUD_PROJECT: GCP project for Cloud Trace
    """
    try:
        # Check if telemetry is enabled via environment
        env = get_env()
        current_env = _get_current_environment(env)
        
        # Default to disabled for testing, enabled for other environments
        otel_enabled_default = "false" if current_env == "testing" else "true"
        otel_enabled = env.get("OTEL_ENABLED", otel_enabled_default).lower() == "true"
        
        if not otel_enabled:
            logging.debug("OpenTelemetry disabled via OTEL_ENABLED=false")
            return False
            
        # Import OpenTelemetry packages
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        
        # Configure resource with service information
        resource_attributes = _get_resource_attributes(env, current_env)
        resource = Resource.create(resource_attributes)
        
        # Create and configure tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Configure and add span exporters
        _configure_span_exporters(tracer_provider, env, current_env)
        
        # Enable automatic instrumentation
        _enable_automatic_instrumentation(env)
        
        # Log successful initialization
        service_name = resource_attributes.get("service.name", "netra-backend")
        logging.info(f"OpenTelemetry automatic instrumentation initialized for {service_name} in {current_env}")
        
        return True
        
    except ImportError as e:
        logging.warning(f"OpenTelemetry packages not available: {e}")
        return False
    except Exception as e:
        logging.error(f"Failed to initialize OpenTelemetry: {e}")
        return False


def _get_resource_attributes(env, current_env: str) -> Dict[str, Any]:
    """Get resource attributes for the service."""
    service_name = env.get("OTEL_SERVICE_NAME", f"netra-backend-{current_env}")
    
    # Base resource attributes
    attributes = {
        "service.name": service_name,
        "service.version": env.get("OTEL_SERVICE_VERSION", "1.0.0"),
        "deployment.environment": current_env,
        "service.namespace": "netra",
    }
    
    # Add GCP-specific attributes if available
    gcp_project = env.get("GOOGLE_CLOUD_PROJECT") or env.get("GCP_PROJECT_ID")
    if gcp_project:
        attributes["gcp.project_id"] = gcp_project
    
    # Add Cloud Run attributes if available
    k_service = env.get("K_SERVICE")
    if k_service:
        attributes["faas.name"] = k_service
        attributes["cloud.provider"] = "gcp"
        attributes["cloud.platform"] = "gcp_cloud_run"
    
    k_revision = env.get("K_REVISION")
    if k_revision:
        attributes["faas.version"] = k_revision
    
    # Add custom resource attributes from environment
    custom_attrs = env.get("OTEL_RESOURCE_ATTRIBUTES", "")
    if custom_attrs:
        try:
            for attr in custom_attrs.split(","):
                if "=" in attr:
                    key, value = attr.split("=", 1)
                    attributes[key.strip()] = value.strip()
        except Exception as e:
            logging.warning(f"Failed to parse OTEL_RESOURCE_ATTRIBUTES: {e}")
    
    return attributes


def _configure_span_exporters(tracer_provider, env, current_env: str) -> None:
    """Configure span exporters based on environment and configuration."""
    exporters_configured = 0
    
    # Try to configure OTLP exporter (preferred for production/staging)
    if _configure_otlp_exporter(tracer_provider, env):
        exporters_configured += 1
    
    # Try to configure Google Cloud Trace exporter
    if _configure_cloud_trace_exporter(tracer_provider, env):
        exporters_configured += 1
    
    # Configure console exporter for development/debugging
    if _configure_console_exporter(tracer_provider, env, current_env):
        exporters_configured += 1
    
    if exporters_configured == 0:
        logging.warning("No telemetry exporters configured - traces will not be exported")


def _configure_otlp_exporter(tracer_provider, env) -> bool:
    """Configure OTLP exporter if endpoint is available."""
    otlp_endpoint = env.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        return False
        
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        
        # Parse headers if provided
        headers = {}
        otlp_headers = env.get("OTEL_EXPORTER_OTLP_HEADERS", "")
        if otlp_headers:
            for header in otlp_headers.split(","):
                if "=" in header:
                    key, value = header.split("=", 1)
                    headers[key.strip()] = value.strip()
        
        # Create OTLP exporter
        insecure = env.get("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() == "true"
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=headers if headers else None,
            insecure=insecure
        )
        
        # Add batch span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        logging.info(f"OTLP exporter configured: {otlp_endpoint}")
        return True
        
    except ImportError:
        logging.warning("OTLP exporter not available")
        return False
    except Exception as e:
        logging.error(f"Failed to configure OTLP exporter: {e}")
        return False


def _configure_cloud_trace_exporter(tracer_provider, env) -> bool:
    """Configure Google Cloud Trace exporter if GCP project is available."""
    gcp_project = env.get("GOOGLE_CLOUD_PROJECT") or env.get("GCP_PROJECT_ID")
    if not gcp_project:
        logging.debug("No GCP project configured, skipping Cloud Trace exporter")
        return False
        
    try:
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        
        # Create Cloud Trace exporter
        cloud_trace_exporter = CloudTraceSpanExporter(project_id=gcp_project)
        
        # Add batch span processor
        span_processor = BatchSpanProcessor(cloud_trace_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        logging.info(f"Google Cloud Trace exporter configured for project: {gcp_project}")
        return True
        
    except ImportError:
        logging.debug("Google Cloud Trace exporter not available - install google-cloud-trace")
        return False
    except Exception as e:
        logging.error(f"Failed to configure Cloud Trace exporter: {e}")
        return False


def _configure_console_exporter(tracer_provider, env, current_env: str) -> bool:
    """Configure console exporter for development and debugging."""
    # Enable console exporter for development or when explicitly requested
    enable_console = (
        current_env == "development" or
        env.get("OTEL_CONSOLE_EXPORTER", "false").lower() == "true"
    )
    
    if not enable_console:
        return False
        
    try:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
        
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        logging.debug("Console span exporter configured")
        return True
        
    except ImportError:
        logging.warning("Console exporter not available")
        return False
    except Exception as e:
        logging.error(f"Failed to configure console exporter: {e}")
        return False


def _enable_automatic_instrumentation(env) -> None:
    """Enable automatic instrumentation for supported libraries."""
    try:
        # FastAPI instrumentation
        if env.get("OTEL_INSTRUMENT_FASTAPI", "true").lower() == "true":
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            
            # Configure excluded URLs to reduce noise - pass as string, not list
            excluded_urls = env.get("OTEL_EXCLUDED_URLS", "/health,/metrics,/docs,/openapi.json")
            
            FastAPIInstrumentor().instrument(excluded_urls=excluded_urls)
            logging.debug("FastAPI automatic instrumentation enabled")
            
    except ImportError:
        logging.debug("FastAPI instrumentation not available")
    except Exception as e:
        logging.warning(f"Failed to enable FastAPI instrumentation: {e}")
    
    try:
        # Requests instrumentation
        if env.get("OTEL_INSTRUMENT_REQUESTS", "true").lower() == "true":
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            RequestsInstrumentor().instrument()
            logging.debug("Requests automatic instrumentation enabled")
            
    except ImportError:
        logging.debug("Requests instrumentation not available")
    except Exception as e:
        logging.warning(f"Failed to enable Requests instrumentation: {e}")
    
    try:
        # SQLAlchemy instrumentation
        if env.get("OTEL_INSTRUMENT_SQLALCHEMY", "true").lower() == "true":
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument()
            logging.debug("SQLAlchemy automatic instrumentation enabled")
            
    except ImportError:
        logging.debug("SQLAlchemy instrumentation not available")
    except Exception as e:
        logging.warning(f"Failed to enable SQLAlchemy instrumentation: {e}")
    
    try:
        # Redis instrumentation
        if env.get("OTEL_INSTRUMENT_REDIS", "true").lower() == "true":
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            RedisInstrumentor().instrument()
            logging.debug("Redis automatic instrumentation enabled")
            
    except ImportError:
        logging.debug("Redis instrumentation not available")
    except Exception as e:
        logging.warning(f"Failed to enable Redis instrumentation: {e}")


def is_telemetry_enabled() -> bool:
    """Check if telemetry is enabled."""
    try:
        env = get_env()
        current_env = _get_current_environment(env)
        
        # Default to disabled for testing, enabled for other environments
        otel_enabled_default = "false" if current_env == "testing" else "true"
        return env.get("OTEL_ENABLED", otel_enabled_default).lower() == "true"
        
    except Exception:
        return False


def get_telemetry_status() -> Dict[str, Any]:
    """Get current telemetry status for health checks."""
    try:
        from opentelemetry import trace
        
        tracer_provider = trace.get_tracer_provider()
        
        return {
            "enabled": is_telemetry_enabled(),
            "tracer_provider_configured": tracer_provider is not None,
            "instrumentation_active": True  # If we get here, instrumentation worked
        }
        
    except ImportError:
        return {
            "enabled": False,
            "tracer_provider_configured": False,
            "instrumentation_active": False,
            "error": "OpenTelemetry packages not available"
        }
    except Exception as e:
        return {
            "enabled": is_telemetry_enabled(),
            "tracer_provider_configured": False,
            "instrumentation_active": False,
            "error": str(e)
        }


# Export key functions
__all__ = [
    "bootstrap_telemetry",
    "is_telemetry_enabled", 
    "get_telemetry_status"
]