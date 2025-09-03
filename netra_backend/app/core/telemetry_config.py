"""
Telemetry Configuration Module

Centralized configuration for OpenTelemetry settings and exporters.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.core.config import get_config

config = get_config()


class ExporterType(Enum):
    """Supported telemetry exporter types."""
    OTLP = "otlp"
    JAEGER = "jaeger"
    CONSOLE = "console"
    NONE = "none"


class SamplingStrategy(Enum):
    """Sampling strategies for trace collection."""
    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    TRACE_ID_RATIO = "trace_id_ratio"
    PARENT_BASED = "parent_based"


@dataclass
class TelemetryConfig:
    """Configuration for OpenTelemetry telemetry."""
    
    # Basic settings
    enabled: bool = True
    service_name: str = "netra-backend"
    service_version: str = "1.0.0"
    environment: str = "development"
    
    # Exporter configuration
    otlp_endpoint: Optional[str] = None
    otlp_headers: Dict[str, str] = field(default_factory=dict)
    otlp_insecure: bool = True
    
    jaeger_endpoint: Optional[str] = None
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6831
    
    # Sampling configuration
    sampling_strategy: SamplingStrategy = SamplingStrategy.ALWAYS_ON
    sampling_rate: float = 1.0  # For TRACE_ID_RATIO strategy
    
    # Console exporter (for debugging)
    enable_console_exporter: bool = False
    
    # Instrumentation settings
    instrument_fastapi: bool = True
    instrument_requests: bool = True
    instrument_redis: bool = True
    instrument_sqlalchemy: bool = True
    excluded_urls: str = "/health,/metrics,/docs,/openapi.json"
    
    # Span processor settings
    batch_span_processor_max_queue_size: int = 2048
    batch_span_processor_max_export_batch_size: int = 512
    batch_span_processor_schedule_delay: int = 5000  # milliseconds
    batch_span_processor_export_timeout: int = 30000  # milliseconds
    
    # Resource attributes
    resource_attributes: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_environment(cls) -> "TelemetryConfig":
        """Create configuration from environment variables."""
        config = cls()
        
        # Basic settings
        config.enabled = os.getenv("OTEL_ENABLED", "true").lower() == "true"
        config.service_name = os.getenv("OTEL_SERVICE_NAME", "netra-backend")
        config.service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
        config.environment = os.getenv("ENVIRONMENT", "development")
        
        # OTLP configuration
        config.otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if os.getenv("OTEL_EXPORTER_OTLP_HEADERS"):
            # Parse headers from format: key1=value1,key2=value2
            headers_str = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
            config.otlp_headers = dict(
                header.split("=", 1) for header in headers_str.split(",") 
                if "=" in header
            )
        config.otlp_insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"
        
        # Jaeger configuration
        config.jaeger_endpoint = os.getenv("JAEGER_ENDPOINT")
        if config.jaeger_endpoint and ":" in config.jaeger_endpoint:
            parts = config.jaeger_endpoint.split(":")
            config.jaeger_agent_host = parts[0]
            config.jaeger_agent_port = int(parts[1])
        else:
            config.jaeger_agent_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
            config.jaeger_agent_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))
        
        # Sampling configuration
        sampling_strategy_str = os.getenv("OTEL_SAMPLING_STRATEGY", "always_on")
        try:
            config.sampling_strategy = SamplingStrategy(sampling_strategy_str)
        except ValueError:
            config.sampling_strategy = SamplingStrategy.ALWAYS_ON
        
        config.sampling_rate = float(os.getenv("OTEL_SAMPLING_RATE", "1.0"))
        
        # Console exporter
        config.enable_console_exporter = os.getenv(
            "OTEL_CONSOLE_EXPORTER", "false"
        ).lower() == "true"
        
        # Instrumentation settings
        config.instrument_fastapi = os.getenv(
            "OTEL_INSTRUMENT_FASTAPI", "true"
        ).lower() == "true"
        config.instrument_requests = os.getenv(
            "OTEL_INSTRUMENT_REQUESTS", "true"
        ).lower() == "true"
        config.instrument_redis = os.getenv(
            "OTEL_INSTRUMENT_REDIS", "true"
        ).lower() == "true"
        config.instrument_sqlalchemy = os.getenv(
            "OTEL_INSTRUMENT_SQLALCHEMY", "true"
        ).lower() == "true"
        config.excluded_urls = os.getenv(
            "OTEL_EXCLUDED_URLS", 
            "/health,/metrics,/docs,/openapi.json"
        )
        
        # Span processor settings
        config.batch_span_processor_max_queue_size = int(
            os.getenv("OTEL_BSP_MAX_QUEUE_SIZE", "2048")
        )
        config.batch_span_processor_max_export_batch_size = int(
            os.getenv("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512")
        )
        config.batch_span_processor_schedule_delay = int(
            os.getenv("OTEL_BSP_SCHEDULE_DELAY", "5000")
        )
        config.batch_span_processor_export_timeout = int(
            os.getenv("OTEL_BSP_EXPORT_TIMEOUT", "30000")
        )
        
        # Add default resource attributes
        config.resource_attributes = {
            "deployment.environment": config.environment,
            "service.namespace": "netra",
            "host.name": os.getenv("HOSTNAME", "unknown"),
        }
        
        # Add custom resource attributes from environment
        custom_attrs = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
        if custom_attrs:
            for attr in custom_attrs.split(","):
                if "=" in attr:
                    key, value = attr.split("=", 1)
                    config.resource_attributes[key] = value
        
        return config
    
    def get_exporter_type(self) -> ExporterType:
        """Determine which exporter type to use based on configuration."""
        if not self.enabled:
            return ExporterType.NONE
        
        if self.otlp_endpoint:
            return ExporterType.OTLP
        elif self.jaeger_endpoint or self.jaeger_agent_host:
            return ExporterType.JAEGER
        elif self.enable_console_exporter:
            return ExporterType.CONSOLE
        else:
            return ExporterType.NONE
    
    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.enabled:
            return True
        
        # Check if at least one exporter is configured
        if (not self.otlp_endpoint and 
            not self.jaeger_endpoint and 
            not self.jaeger_agent_host and 
            not self.enable_console_exporter):
            return False
        
        # Validate sampling rate
        if self.sampling_strategy == SamplingStrategy.TRACE_ID_RATIO:
            if not 0.0 <= self.sampling_rate <= 1.0:
                return False
        
        return True


# Default configuration presets for different environments
TELEMETRY_PRESETS = {
    "development": TelemetryConfig(
        enabled=True,
        service_name="netra-backend-dev",
        environment="development",
        jaeger_agent_host="localhost",
        jaeger_agent_port=6831,
        enable_console_exporter=True,
        sampling_strategy=SamplingStrategy.ALWAYS_ON,
    ),
    "staging": TelemetryConfig(
        enabled=True,
        service_name="netra-backend-staging",
        environment="staging",
        otlp_endpoint="otel-collector.staging.netra.io:4317",
        otlp_insecure=True,
        sampling_strategy=SamplingStrategy.TRACE_ID_RATIO,
        sampling_rate=0.1,
    ),
    "production": TelemetryConfig(
        enabled=True,
        service_name="netra-backend",
        environment="production",
        otlp_endpoint="otel-collector.netra.io:4317",
        otlp_insecure=False,
        sampling_strategy=SamplingStrategy.TRACE_ID_RATIO,
        sampling_rate=0.01,
        enable_console_exporter=False,
    ),
    "testing": TelemetryConfig(
        enabled=False,  # Disabled by default for tests
        service_name="netra-backend-test",
        environment="testing",
        enable_console_exporter=True,
        sampling_strategy=SamplingStrategy.ALWAYS_OFF,
    ),
}


def get_telemetry_config(preset: Optional[str] = None) -> TelemetryConfig:
    """
    Get telemetry configuration.
    
    Args:
        preset: Optional preset name to use as base configuration
    
    Returns:
        TelemetryConfig instance
    """
    # Start with preset if provided
    if preset and preset in TELEMETRY_PRESETS:
        config = TELEMETRY_PRESETS[preset]
    else:
        # Default to environment-based configuration
        config = TelemetryConfig.from_environment()
    
    # Override with environment variables
    env_config = TelemetryConfig.from_environment()
    
    # Merge configurations (env variables take precedence)
    if os.getenv("OTEL_SERVICE_NAME"):
        config.service_name = env_config.service_name
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        config.otlp_endpoint = env_config.otlp_endpoint
    if os.getenv("JAEGER_ENDPOINT"):
        config.jaeger_endpoint = env_config.jaeger_endpoint
    
    return config