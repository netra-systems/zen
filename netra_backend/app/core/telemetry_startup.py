"""
Telemetry Startup Integration

Handles OpenTelemetry initialization during application startup.
"""

import os
import logging

logger = logging.getLogger(__name__)


def initialize_telemetry():
    """
    Initialize telemetry based on environment configuration.
    
    Checks for GCP Cloud Trace or standard OTLP configuration.
    """
    try:
        # Check if telemetry is enabled
        if not os.getenv("OTEL_ENABLED", "false").lower() == "true":
            logger.info("OpenTelemetry is disabled")
            return
        
        # Check for GCP Cloud Trace
        if os.getenv("OTEL_EXPORTER_GCP_TRACE", "false").lower() == "true":
            logger.info("Initializing GCP Cloud Trace")
            from netra_backend.app.core.telemetry_gcp import (
                init_gcp_tracing_from_env,
                auto_instrument_for_gcp
            )
            
            # Initialize GCP tracing
            tracer_provider = init_gcp_tracing_from_env()
            if tracer_provider:
                # Auto-instrument libraries
                auto_instrument_for_gcp()
                logger.info("GCP Cloud Trace initialization complete")
            else:
                logger.warning("GCP Cloud Trace initialization failed")
        
        # Otherwise use standard OTLP configuration
        else:
            logger.info("Initializing standard OpenTelemetry")
            from netra_backend.app.core.telemetry import telemetry_manager
            
            # Initialize with environment configuration
            telemetry_manager.init_telemetry(
                service_name=os.getenv("OTEL_SERVICE_NAME", "netra-backend"),
                otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
                jaeger_endpoint=os.getenv("JAEGER_ENDPOINT"),
                enable_console=os.getenv("OTEL_CONSOLE_EXPORTER", "false").lower() == "true"
            )
            
            if telemetry_manager.enabled:
                logger.info("OpenTelemetry initialization complete")
            else:
                logger.warning("OpenTelemetry initialization failed")
                
    except Exception as e:
        logger.error(f"Failed to initialize telemetry: {e}")
        # Don't fail startup if telemetry fails
        pass