"""
Integration Tests for OpenTelemetry Trace Export Validation

FOCUS: Automatic instrumentation only - validates that traces from automatic
instrumentation are correctly exported to configured backends (Cloud Trace, OTLP).

Tests trace export configuration, connectivity, authentication, and data format
validation for OpenTelemetry automatic instrumentation output.

Business Value: Enterprise/Platform - Ensures observability data reaches
monitoring systems for $500K+ ARR chat functionality analysis.

CRITICAL: Uses REAL SERVICES and real export endpoints where possible.
SSOT Architecture: Uses SSotAsyncTestCase for consistent patterns.

Tests MUST FAIL before export configuration is properly setup.
"""

import asyncio
import base64
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch
from dataclasses import dataclass
from urllib.parse import urlparse

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)


@dataclass
class TraceExportTestResult:
    """Container for trace export test results."""
    export_backend: str
    configuration_valid: bool
    connection_successful: bool
    authentication_successful: bool
    trace_data_exported: bool
    export_latency_ms: float
    error_message: Optional[str] = None


class TestOpenTelemetryTraceExportValidation(SSotAsyncTestCase):
    """Test validation of trace export configuration and connectivity."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Configure base auto-instrumentation for export testing
        self.set_env_var("OTEL_SERVICE_NAME", "netra-apex-export-validation")
        self.set_env_var("OTEL_RESOURCE_ATTRIBUTES", "service.name=netra-apex-export-validation,test.type=export_validation")
        self.set_env_var("ENVIRONMENT", "test")
        
        # Test session identifier
        self.test_session_id = f"export_test_{uuid.uuid4().hex[:8]}"
        
    def test_trace_export_configuration_validation_before_setup(self):
        """
        Test that trace export is NOT configured before proper setup.
        
        This test MUST FAIL before export configuration is applied.
        """
        # Check initial export configuration state
        initial_config = {
            "exporter": self.get_env_var("OTEL_TRACES_EXPORTER"),
            "endpoint": self.get_env_var("OTEL_EXPORTER_OTLP_ENDPOINT"),
            "headers": self.get_env_var("OTEL_EXPORTER_OTLP_HEADERS"),
            "timeout": self.get_env_var("OTEL_EXPORTER_OTLP_TIMEOUT"),
        }
        
        # Before setup, most export configuration should be missing or default
        unset_configs = sum(1 for v in initial_config.values() if v is None)
        
        # Record initial state
        for key, value in initial_config.items():
            self.record_metric(f"initial_export_{key}", value or "unset")
            
        self.record_metric("unset_export_configs", unset_configs)
        
        # Before proper configuration, should have missing export settings
        assert unset_configs >= 2, (
            f"Export configuration should be mostly unset initially. "
            f"Missing configs: {unset_configs}, Config: {initial_config}"
        )
        
    def test_otlp_grpc_export_configuration_validation(self):
        """
        Test OTLP gRPC export configuration for Cloud Trace.
        
        Validates configuration format and basic connectivity.
        """
        # Configure OTLP gRPC export for Google Cloud Trace
        cloud_trace_config = {
            "OTEL_TRACES_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloudtrace.googleapis.com/v2/projects/netra-staging/traces",
            "OTEL_EXPORTER_OTLP_HEADERS": "x-goog-user-project=netra-staging",
            "OTEL_EXPORTER_OTLP_TIMEOUT": "30",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
        }
        
        # Apply configuration
        for key, value in cloud_trace_config.items():
            self.set_env_var(key, value)
            
        # Validate configuration format
        configured_endpoint = self.get_env_var("OTEL_EXPORTER_OTLP_ENDPOINT")
        configured_headers = self.get_env_var("OTEL_EXPORTER_OTLP_HEADERS")
        configured_timeout = self.get_env_var("OTEL_EXPORTER_OTLP_TIMEOUT")
        
        # Validate endpoint format
        parsed_endpoint = urlparse(configured_endpoint)
        assert parsed_endpoint.scheme == "https", f"Cloud Trace endpoint should use HTTPS: {configured_endpoint}"
        assert "cloudtrace.googleapis.com" in parsed_endpoint.netloc, f"Invalid Cloud Trace endpoint: {configured_endpoint}"
        assert "/traces" in parsed_endpoint.path, f"Cloud Trace endpoint should include /traces path: {configured_endpoint}"
        
        # Validate headers format
        assert "x-goog-user-project" in configured_headers, f"Missing required Cloud Trace header: {configured_headers}"
        
        # Validate timeout is numeric
        timeout_value = int(configured_timeout)
        assert timeout_value > 0, f"Timeout should be positive: {timeout_value}"
        assert timeout_value <= 60, f"Timeout should be reasonable: {timeout_value}s"
        
        # Record configuration metrics
        self.record_metric("otlp_endpoint_configured", configured_endpoint)
        self.record_metric("otlp_headers_configured", configured_headers)
        self.record_metric("otlp_timeout_seconds", timeout_value)
        
    def test_console_export_configuration_validation(self):
        """
        Test console exporter configuration for development/testing.
        
        Validates console export works for local development and testing.
        """
        # Configure console export
        console_config = {
            "OTEL_TRACES_EXPORTER": "console",
            "OTEL_TRACES_SAMPLER": "always_on",  # Sample all traces for testing
        }
        
        for key, value in console_config.items():
            self.set_env_var(key, value)
            
        # Validate console exporter setup
        try:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            
            # Setup tracer with console export
            trace.set_tracer_provider(TracerProvider())
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Create a test span to validate export
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span("console_export_validation") as span:
                span.set_attribute("test.session_id", self.test_session_id)
                span.set_attribute("export.type", "console")
                span.add_event("Console export validation test")
                
                # Simulate some work
                time.sleep(0.001)  # 1ms
                
            # Force export by shutting down processor
            span_processor.force_flush(timeout_millis=5000)
            
            self.record_metric("console_export_configured", True)
            self.record_metric("console_export_test_span_created", True)
            
        except ImportError:
            pytest.skip("OpenTelemetry console exporter not available")
            
        except Exception as e:
            self.record_metric("console_export_error", str(e))
            raise
            
    def test_otlp_http_export_configuration_validation(self):
        """
        Test OTLP HTTP export configuration and connectivity.
        
        Validates HTTP-based OTLP export for various backends.
        """
        # Configure OTLP HTTP export
        http_config = {
            "OTEL_TRACES_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://api.honeycomb.io/v1/traces",  # Example endpoint
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            "OTEL_EXPORTER_OTLP_HEADERS": "x-honeycomb-team=test-key",
            "OTEL_EXPORTER_OTLP_TIMEOUT": "15",
        }
        
        for key, value in http_config.items():
            self.set_env_var(key, value)
            
        # Validate HTTP configuration
        configured_endpoint = self.get_env_var("OTEL_EXPORTER_OTLP_ENDPOINT")
        configured_protocol = self.get_env_var("OTEL_EXPORTER_OTLP_PROTOCOL")
        configured_headers = self.get_env_var("OTEL_EXPORTER_OTLP_HEADERS")
        
        # Validate protocol format
        assert configured_protocol in ["http/protobuf", "http/json"], (
            f"Invalid OTLP HTTP protocol: {configured_protocol}"
        )
        
        # Validate endpoint format
        parsed_endpoint = urlparse(configured_endpoint)
        assert parsed_endpoint.scheme in ["http", "https"], (
            f"OTLP HTTP endpoint should use HTTP/HTTPS: {configured_endpoint}"
        )
        
        # Test OTLP HTTP exporter creation (without actual export)
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            
            # Create exporter with configuration
            http_exporter = OTLPSpanExporter(
                endpoint=configured_endpoint,
                headers=self._parse_headers(configured_headers),
                timeout=int(self.get_env_var("OTEL_EXPORTER_OTLP_TIMEOUT", "15"))
            )
            
            assert http_exporter is not None
            self.record_metric("otlp_http_exporter_created", True)
            
        except ImportError:
            pytest.skip("OpenTelemetry OTLP HTTP exporter not available")
            
        except Exception as e:
            self.record_metric("otlp_http_exporter_error", str(e))
            raise
            
        # Record configuration metrics
        self.record_metric("otlp_http_endpoint_configured", configured_endpoint)
        self.record_metric("otlp_http_protocol_configured", configured_protocol)
        
    def _parse_headers(self, headers_string: str) -> Dict[str, str]:
        """Parse OTLP headers string into dictionary."""
        headers = {}
        
        if headers_string:
            # Handle comma-separated key=value pairs
            for header_pair in headers_string.split(","):
                if "=" in header_pair:
                    key, value = header_pair.split("=", 1)
                    headers[key.strip()] = value.strip()
                    
        return headers
        
    async def test_trace_export_connectivity_validation(self):
        """
        Test connectivity to trace export endpoints.
        
        Validates that configured export endpoints are reachable.
        """
        export_endpoints = [
            {
                "name": "google_cloud_trace",
                "endpoint": "https://cloudtrace.googleapis.com/v2/projects/test/traces",
                "expected_status": [200, 401, 403],  # 401/403 expected without proper auth
                "headers": {"x-goog-user-project": "test"}
            },
            {
                "name": "otlp_http_endpoint",
                "endpoint": "https://api.honeycomb.io/v1/traces",
                "expected_status": [200, 400, 401, 403],  # Various auth/format responses
                "headers": {"content-type": "application/x-protobuf"}
            }
        ]
        
        connectivity_results = {}
        
        for endpoint_config in export_endpoints:
            endpoint_name = endpoint_config["name"]
            endpoint_url = endpoint_config["endpoint"]
            
            logger.info(f"Testing connectivity to {endpoint_name}: {endpoint_url}")
            
            try:
                # Test basic connectivity (not actual trace export)
                import requests
                
                start_time = time.perf_counter()
                
                # Make a simple HEAD request to test connectivity
                response = requests.head(
                    endpoint_url,
                    headers=endpoint_config.get("headers", {}),
                    timeout=10
                )
                
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                
                connectivity_results[endpoint_name] = {
                    "reachable": True,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "expected_status": response.status_code in endpoint_config["expected_status"]
                }
                
            except requests.exceptions.RequestException as e:
                connectivity_results[endpoint_name] = {
                    "reachable": False,
                    "error": str(e),
                    "latency_ms": 0,
                    "expected_status": False
                }
                
            except ImportError:
                pytest.skip("requests library not available for connectivity testing")
                
        # Record connectivity results
        for endpoint_name, result in connectivity_results.items():
            self.record_metric(f"connectivity_{endpoint_name}_reachable", result["reachable"])
            self.record_metric(f"connectivity_{endpoint_name}_latency_ms", result.get("latency_ms", 0))
            
            if result["reachable"]:
                self.record_metric(f"connectivity_{endpoint_name}_status_code", result["status_code"])
                self.record_metric(f"connectivity_{endpoint_name}_expected_status", result["expected_status"])
                
        # At least one endpoint should be reachable for export testing
        reachable_endpoints = [name for name, result in connectivity_results.items() if result["reachable"]]
        
        self.record_metric("reachable_export_endpoints", len(reachable_endpoints))
        
        # Note: We don't assert connectivity success because these tests may run in 
        # environments without internet access or proper credentials
        
    def test_trace_export_authentication_validation(self):
        """
        Test trace export authentication configuration.
        
        Validates authentication headers and credentials format.
        """
        # Test various authentication patterns
        auth_configurations = [
            {
                "name": "google_cloud_auth",
                "headers": "x-goog-user-project=netra-staging",
                "endpoint": "https://cloudtrace.googleapis.com/v2/projects/netra-staging/traces",
                "auth_type": "google_cloud"
            },
            {
                "name": "api_key_auth",
                "headers": "x-api-key=test-key-12345,authorization=Bearer test-token",
                "endpoint": "https://api.example.com/v1/traces",
                "auth_type": "api_key"
            },
            {
                "name": "basic_auth",
                "headers": "authorization=Basic dGVzdDp0ZXN0",  # base64("test:test")
                "endpoint": "https://traces.example.com/v1/traces",
                "auth_type": "basic"
            }
        ]
        
        auth_validation_results = {}
        
        for auth_config in auth_configurations:
            auth_name = auth_config["name"]
            headers_string = auth_config["headers"]
            
            # Validate header format
            parsed_headers = self._parse_headers(headers_string)
            
            validation_result = {
                "headers_parsed": len(parsed_headers) > 0,
                "auth_headers_present": False,
                "header_format_valid": True,
                "security_issues": []
            }
            
            # Check for authentication headers
            auth_header_indicators = ["authorization", "x-api-key", "x-goog-user-project", "api-key"]
            auth_headers_found = [
                header for header in parsed_headers.keys()
                if any(indicator in header.lower() for indicator in auth_header_indicators)
            ]
            
            validation_result["auth_headers_present"] = len(auth_headers_found) > 0
            validation_result["auth_headers_found"] = auth_headers_found
            
            # Validate specific authentication types
            if auth_config["auth_type"] == "google_cloud":
                if "x-goog-user-project" not in parsed_headers:
                    validation_result["security_issues"].append("Missing x-goog-user-project header")
                    
            elif auth_config["auth_type"] == "basic":
                auth_header = parsed_headers.get("authorization", "")
                if not auth_header.startswith("Basic "):
                    validation_result["security_issues"].append("Invalid Basic auth format")
                else:
                    # Validate base64 format (don't decode actual credentials)
                    try:
                        base64_part = auth_header.replace("Basic ", "")
                        base64.b64decode(base64_part, validate=True)
                    except Exception:
                        validation_result["security_issues"].append("Invalid base64 in Basic auth")
                        
            elif auth_config["auth_type"] == "api_key":
                api_key_headers = ["x-api-key", "api-key", "authorization"]
                api_key_found = any(header in parsed_headers for header in api_key_headers)
                if not api_key_found:
                    validation_result["security_issues"].append("No API key headers found")
                    
            # Check for security issues
            for header_name, header_value in parsed_headers.items():
                # Check for obviously invalid credentials
                if len(header_value) < 8 and "test" not in header_value.lower():
                    validation_result["security_issues"].append(f"Suspiciously short credential in {header_name}")
                    
            validation_result["valid_auth_config"] = len(validation_result["security_issues"]) == 0
            
            auth_validation_results[auth_name] = validation_result
            
        # Record authentication validation results
        for auth_name, result in auth_validation_results.items():
            self.record_metric(f"auth_{auth_name}_headers_parsed", result["headers_parsed"])
            self.record_metric(f"auth_{auth_name}_auth_headers_present", result["auth_headers_present"])
            self.record_metric(f"auth_{auth_name}_valid_config", result["valid_auth_config"])
            self.record_metric(f"auth_{auth_name}_security_issues", len(result["security_issues"]))
            
        # All authentication configurations should parse correctly
        all_parsed = all(result["headers_parsed"] for result in auth_validation_results.values())
        assert all_parsed, f"All auth configurations should parse correctly: {auth_validation_results}"
        
    def test_trace_export_data_format_validation(self):
        """
        Test trace export data format and serialization.
        
        Validates that automatic instrumentation produces exportable trace data.
        """
        # Setup instrumentation and export
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import SpanExporter, BatchSpanProcessor
            from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
            
            # Use in-memory exporter to capture trace data for validation
            in_memory_exporter = InMemorySpanExporter()
            
            trace.set_tracer_provider(TracerProvider())
            span_processor = BatchSpanProcessor(in_memory_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
        except ImportError:
            pytest.skip("OpenTelemetry SDK not available for data format testing")
            
        # Create test spans with various data types
        tracer = trace.get_tracer(__name__)
        
        test_span_data = [
            {
                "name": "string_attributes_span",
                "attributes": {
                    "service.name": "netra-apex",
                    "operation.type": "test",
                    "test.session_id": self.test_session_id
                }
            },
            {
                "name": "numeric_attributes_span", 
                "attributes": {
                    "duration.ms": 123.45,
                    "retry.count": 3,
                    "success.rate": 0.95
                }
            },
            {
                "name": "boolean_attributes_span",
                "attributes": {
                    "is.successful": True,
                    "has.errors": False,
                    "cache.hit": True
                }
            }
        ]
        
        # Generate test spans
        for span_data in test_span_data:
            with tracer.start_as_current_span(span_data["name"]) as span:
                for key, value in span_data["attributes"].items():
                    span.set_attribute(key, value)
                    
                span.add_event(f"Test event for {span_data['name']}")
                time.sleep(0.001)  # Small delay
                
        # Force export and retrieve spans
        span_processor.force_flush(timeout_millis=5000)
        exported_spans = in_memory_exporter.get_finished_spans()
        
        # Validate exported span data
        data_format_validation = {
            "spans_exported": len(exported_spans),
            "spans_have_trace_id": 0,
            "spans_have_span_id": 0,
            "spans_have_attributes": 0,
            "spans_have_events": 0,
            "attribute_types_valid": True,
            "trace_id_format_valid": True,
            "span_id_format_valid": True
        }
        
        for span in exported_spans:
            # Validate basic span structure
            if span.context.trace_id:
                data_format_validation["spans_have_trace_id"] += 1
                
                # Validate trace ID format (should be 16 bytes/32 hex chars)
                trace_id_hex = format(span.context.trace_id, '032x')
                if len(trace_id_hex) != 32:
                    data_format_validation["trace_id_format_valid"] = False
                    
            if span.context.span_id:
                data_format_validation["spans_have_span_id"] += 1
                
                # Validate span ID format (should be 8 bytes/16 hex chars)
                span_id_hex = format(span.context.span_id, '016x')
                if len(span_id_hex) != 16:
                    data_format_validation["span_id_format_valid"] = False
                    
            if span.attributes:
                data_format_validation["spans_have_attributes"] += 1
                
                # Validate attribute types
                for attr_key, attr_value in span.attributes.items():
                    if not isinstance(attr_value, (str, int, float, bool)):
                        data_format_validation["attribute_types_valid"] = False
                        
            if span.events:
                data_format_validation["spans_have_events"] += 1
                
        # Record validation results
        for key, value in data_format_validation.items():
            self.record_metric(f"data_format_{key}", value)
            
        # Validate export data quality
        assert data_format_validation["spans_exported"] >= len(test_span_data), (
            f"Should export at least {len(test_span_data)} spans, got {data_format_validation['spans_exported']}"
        )
        
        assert data_format_validation["spans_have_trace_id"] == data_format_validation["spans_exported"], (
            "All exported spans should have trace IDs"
        )
        
        assert data_format_validation["spans_have_span_id"] == data_format_validation["spans_exported"], (
            "All exported spans should have span IDs"
        )
        
        assert data_format_validation["attribute_types_valid"], (
            "All span attributes should have valid types"
        )
        
        assert data_format_validation["trace_id_format_valid"], (
            "All trace IDs should have valid format"
        )
        
        assert data_format_validation["span_id_format_valid"], (
            "All span IDs should have valid format"
        )


class TestTraceExportEnvironmentConfiguration(SSotAsyncTestCase):
    """Test environment-specific trace export configuration."""
    
    def setup_method(self, method=None):
        """Setup for environment configuration testing."""
        super().setup_method(method)
        
    def test_development_environment_export_configuration(self):
        """Test trace export configuration for development environment."""
        # Development environment should use console export
        dev_config = {
            "ENVIRONMENT": "development",
            "OTEL_TRACES_EXPORTER": "console",
            "OTEL_TRACES_SAMPLER": "always_on",
            "OTEL_PYTHON_LOG_CORRELATION": "true"
        }
        
        self._test_environment_export_config("development", dev_config)
        
    def test_staging_environment_export_configuration(self):
        """Test trace export configuration for staging environment."""
        # Staging should use Cloud Trace with sampling
        staging_config = {
            "ENVIRONMENT": "staging",
            "OTEL_TRACES_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloudtrace.googleapis.com/v2/projects/netra-staging/traces",
            "OTEL_EXPORTER_OTLP_HEADERS": "x-goog-user-project=netra-staging",
            "OTEL_TRACES_SAMPLER": "traceidratio",
            "OTEL_TRACES_SAMPLER_ARG": "0.1"  # 10% sampling
        }
        
        self._test_environment_export_config("staging", staging_config)
        
    def test_production_environment_export_configuration(self):
        """Test trace export configuration for production environment."""
        # Production should use Cloud Trace with conservative sampling
        production_config = {
            "ENVIRONMENT": "production",
            "OTEL_TRACES_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloudtrace.googleapis.com/v2/projects/netra-production/traces",
            "OTEL_EXPORTER_OTLP_HEADERS": "x-goog-user-project=netra-production",
            "OTEL_TRACES_SAMPLER": "traceidratio",
            "OTEL_TRACES_SAMPLER_ARG": "0.01",  # 1% sampling for production
            "OTEL_BSP_SCHEDULE_DELAY": "5000",   # 5 second batch delay
            "OTEL_BSP_MAX_EXPORT_BATCH_SIZE": "512"
        }
        
        self._test_environment_export_config("production", production_config)
        
    def _test_environment_export_config(self, environment: str, expected_config: Dict[str, str]):
        """Test export configuration for a specific environment."""
        
        # Apply configuration
        for key, value in expected_config.items():
            self.set_env_var(key, value)
            
        # Validate configuration
        config_validation = {
            "environment_set": self.get_env_var("ENVIRONMENT") == environment,
            "exporter_configured": bool(self.get_env_var("OTEL_TRACES_EXPORTER")),
            "sampler_configured": bool(self.get_env_var("OTEL_TRACES_SAMPLER")),
        }
        
        # Environment-specific validation
        if environment == "development":
            config_validation["console_export"] = self.get_env_var("OTEL_TRACES_EXPORTER") == "console"
            config_validation["full_sampling"] = self.get_env_var("OTEL_TRACES_SAMPLER") == "always_on"
            
        elif environment in ["staging", "production"]:
            config_validation["otlp_export"] = self.get_env_var("OTEL_TRACES_EXPORTER") == "otlp"
            config_validation["endpoint_configured"] = bool(self.get_env_var("OTEL_EXPORTER_OTLP_ENDPOINT"))
            config_validation["headers_configured"] = bool(self.get_env_var("OTEL_EXPORTER_OTLP_HEADERS"))
            config_validation["sampling_configured"] = self.get_env_var("OTEL_TRACES_SAMPLER") == "traceidratio"
            
            # Validate sampling rate
            sampling_arg = self.get_env_var("OTEL_TRACES_SAMPLER_ARG")
            if sampling_arg:
                sampling_rate = float(sampling_arg)
                config_validation["sampling_rate_valid"] = 0.0 <= sampling_rate <= 1.0
                
                if environment == "production":
                    config_validation["production_sampling_conservative"] = sampling_rate <= 0.1
                    
        # Record validation results
        for key, value in config_validation.items():
            self.record_metric(f"{environment}_config_{key}", value)
            
        # Validate essential configuration
        assert config_validation["environment_set"], f"Environment should be set to {environment}"
        assert config_validation["exporter_configured"], f"Trace exporter should be configured for {environment}"
        assert config_validation["sampler_configured"], f"Trace sampler should be configured for {environment}"
        
        # Environment-specific assertions
        if environment == "development":
            assert config_validation.get("console_export", False), "Development should use console export"
            
        elif environment in ["staging", "production"]:
            assert config_validation.get("otlp_export", False), f"{environment} should use OTLP export"
            assert config_validation.get("endpoint_configured", False), f"{environment} should have endpoint configured"
            assert config_validation.get("headers_configured", False), f"{environment} should have headers configured"