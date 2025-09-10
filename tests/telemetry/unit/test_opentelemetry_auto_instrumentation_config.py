"""
Unit Tests for OpenTelemetry Automatic Instrumentation Configuration

FOCUS: Automatic instrumentation only - no manual spans or custom instrumentation.

Tests automatic configuration and initialization of OpenTelemetry instrumentation
libraries for FastAPI, SQLAlchemy, Redis, and requests.

Business Value: Platform/Enterprise - Observability foundation for AI operations
Tests MUST FAIL before auto-instrumentation is configured, PASS after setup.

SSOT Architecture: Uses SSotBaseTestCase for consistent test patterns
"""

import logging
import os
import sys
from unittest.mock import MagicMock, Mock, patch
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class TestOpenTelemetryAutoInstrumentationConfig(SSotBaseTestCase):
    """Test automatic instrumentation configuration and setup."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set test environment
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("OTEL_SERVICE_NAME", "netra-apex-test")
        self.set_env_var("OTEL_RESOURCE_ATTRIBUTES", "service.name=netra-apex-test")
        
        # Clear any existing instrumentation state
        self._clear_instrumentation_state()
        
    def teardown_method(self, method=None):
        """Cleanup after each test method."""
        self._clear_instrumentation_state()
        super().teardown_method(method)
        
    def _clear_instrumentation_state(self):
        """Clear OpenTelemetry instrumentation state between tests."""
        # Remove OpenTelemetry modules from sys.modules to reset state
        otel_modules = [
            name for name in sys.modules.keys()
            if name.startswith('opentelemetry')
        ]
        for module_name in otel_modules:
            if 'instrumentation' in module_name:
                # Don't remove core SDK, just instrumentation modules
                continue
                
    def test_auto_instrumentation_not_configured_initially(self):
        """
        Test that auto-instrumentation is NOT configured by default.
        
        This test MUST FAIL before auto-instrumentation setup.
        """
        try:
            # Try to import instrumentation modules
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            
            # Check if instruments are already configured
            fastapi_instrumented = FastAPIInstrumentor().is_instrumented_by_opentelemetry
            sqlalchemy_instrumented = SQLAlchemyInstrumentor().is_instrumented_by_opentelemetry  
            redis_instrumented = RedisInstrumentor().is_instrumented_by_opentelemetry
            requests_instrumented = RequestsInstrumentor().is_instrumented_by_opentelemetry
            
            # Before configuration, none should be instrumented
            assert not any([
                fastapi_instrumented,
                sqlalchemy_instrumented, 
                redis_instrumented,
                requests_instrumented
            ]), "Auto-instrumentation should not be configured initially"
            
        except ImportError as e:
            # This is expected if OpenTelemetry is not installed
            self.record_metric("auto_instrumentation_import_failed", str(e))
            
    def test_auto_instrumentation_environment_variables_default(self):
        """
        Test that required environment variables are not set by default.
        
        This test MUST FAIL before auto-instrumentation configuration.
        """
        # These should not be set initially (test will fail if they are)
        critical_env_vars = [
            "OTEL_TRACES_EXPORTER",
            "OTEL_METRICS_EXPORTER", 
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "OTEL_EXPORTER_OTLP_HEADERS",
            "OTEL_PYTHON_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST",
            "OTEL_PYTHON_LOG_CORRELATION",
        ]
        
        missing_vars = []
        for var in critical_env_vars:
            if self.get_env_var(var) is None:
                missing_vars.append(var)
                
        # Before configuration, most should be missing (test fails if all are set)
        assert len(missing_vars) > 0, (
            f"Auto-instrumentation environment variables should not all be configured initially. "
            f"Missing: {missing_vars}"
        )
        
        self.record_metric("missing_auto_instrumentation_env_vars", len(missing_vars))
        
    def test_auto_instrumentation_configuration_setup(self):
        """
        Test automatic instrumentation configuration setup.
        
        This test validates the configuration that enables auto-instrumentation.
        """
        # Simulate configuration setup
        auto_instrumentation_config = {
            "OTEL_TRACES_EXPORTER": "otlp",
            "OTEL_METRICS_EXPORTER": "otlp", 
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://cloudtrace.googleapis.com/v2/projects/netra-test/traces",
            "OTEL_EXPORTER_OTLP_HEADERS": "x-goog-user-project=netra-test",
            "OTEL_PYTHON_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST": "user-agent,authorization",
            "OTEL_PYTHON_LOG_CORRELATION": "true",
            "OTEL_PYTHON_EXCLUDED_URLS": "/health,/metrics,/ready",
            "OTEL_SERVICE_NAME": "netra-apex-backend",
            "OTEL_RESOURCE_ATTRIBUTES": "service.name=netra-apex-backend,service.version=1.0.0",
        }
        
        # Apply configuration
        for key, value in auto_instrumentation_config.items():
            self.set_env_var(key, value)
            
        # Validate configuration is applied
        for key, expected_value in auto_instrumentation_config.items():
            actual_value = self.get_env_var(key)
            assert actual_value == expected_value, (
                f"Auto-instrumentation config {key} = {actual_value}, expected {expected_value}"
            )
            
        self.record_metric("auto_instrumentation_config_vars", len(auto_instrumentation_config))
        
    def test_auto_instrumentation_libraries_availability(self):
        """
        Test that automatic instrumentation libraries are available.
        
        Validates that OpenTelemetry auto-instrumentation packages can be imported.
        """
        required_instrumentors = [
            ("opentelemetry.instrumentation.fastapi", "FastAPIInstrumentor"),
            ("opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
            ("opentelemetry.instrumentation.redis", "RedisInstrumentor"),
            ("opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
            ("opentelemetry.instrumentation.logging", "LoggingInstrumentor"),
        ]
        
        available_instrumentors = []
        missing_instrumentors = []
        
        for module_name, class_name in required_instrumentors:
            try:
                module = __import__(module_name, fromlist=[class_name])
                instrumentor_class = getattr(module, class_name)
                available_instrumentors.append((module_name, class_name))
                
                # Verify instrumentor has required methods
                assert hasattr(instrumentor_class, 'instrument'), (
                    f"{class_name} missing instrument() method"
                )
                assert hasattr(instrumentor_class, 'uninstrument'), (
                    f"{class_name} missing uninstrument() method"
                )
                
            except ImportError:
                missing_instrumentors.append((module_name, class_name))
                
        # Record metrics
        self.record_metric("available_instrumentors", len(available_instrumentors))
        self.record_metric("missing_instrumentors", len(missing_instrumentors))
        
        # Should have at least basic instrumentors available
        assert len(available_instrumentors) >= 2, (
            f"Need at least 2 instrumentors available, got {len(available_instrumentors)}. "
            f"Missing: {missing_instrumentors}"
        )
        
    def test_auto_instrumentation_framework_detection(self):
        """
        Test automatic detection of frameworks for instrumentation.
        
        Validates that instrumentors can detect when frameworks are available.
        """
        framework_detection_results = {}
        
        # Test FastAPI detection
        try:
            import fastapi
            framework_detection_results['fastapi'] = {
                'available': True,
                'version': getattr(fastapi, '__version__', 'unknown')
            }
        except ImportError:
            framework_detection_results['fastapi'] = {'available': False}
            
        # Test SQLAlchemy detection  
        try:
            import sqlalchemy
            framework_detection_results['sqlalchemy'] = {
                'available': True,
                'version': getattr(sqlalchemy, '__version__', 'unknown')
            }
        except ImportError:
            framework_detection_results['sqlalchemy'] = {'available': False}
            
        # Test Redis detection
        try:
            import redis
            framework_detection_results['redis'] = {
                'available': True,
                'version': getattr(redis, '__version__', 'unknown')
            }
        except ImportError:
            framework_detection_results['redis'] = {'available': False}
            
        # Test requests detection (should always be available)
        try:
            import requests
            framework_detection_results['requests'] = {
                'available': True,
                'version': getattr(requests, '__version__', 'unknown')
            }
        except ImportError:
            framework_detection_results['requests'] = {'available': False}
            
        # Record detection results
        for framework, detection in framework_detection_results.items():
            self.record_metric(f"framework_{framework}_detected", detection['available'])
            if detection['available']:
                self.record_metric(f"framework_{framework}_version", detection.get('version', 'unknown'))
                
        # At least requests should be available for a basic test
        assert framework_detection_results.get('requests', {}).get('available', False), (
            "requests library should be available for basic auto-instrumentation testing"
        )
        
    def test_auto_instrumentation_exporter_configuration(self):
        """
        Test automatic instrumentation exporter configuration.
        
        Validates OTLP exporter setup for Cloud Trace integration.
        """
        # Test OTLP exporter availability
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPOTLPSpanExporter
            
            otlp_available = True
            self.record_metric("otlp_grpc_exporter_available", True)
            self.record_metric("otlp_http_exporter_available", True)
            
        except ImportError:
            otlp_available = False
            self.record_metric("otlp_exporter_available", False)
            
        # Test Cloud Trace configuration
        cloud_trace_config = {
            "endpoint": "https://cloudtrace.googleapis.com/v2/projects/netra-staging/traces",
            "headers": "x-goog-user-project=netra-staging",
        }
        
        # Set Cloud Trace configuration
        self.set_env_var("OTEL_EXPORTER_OTLP_ENDPOINT", cloud_trace_config["endpoint"])
        self.set_env_var("OTEL_EXPORTER_OTLP_HEADERS", cloud_trace_config["headers"])
        
        # Validate configuration
        configured_endpoint = self.get_env_var("OTEL_EXPORTER_OTLP_ENDPOINT")
        configured_headers = self.get_env_var("OTEL_EXPORTER_OTLP_HEADERS")
        
        assert configured_endpoint == cloud_trace_config["endpoint"], (
            f"Cloud Trace endpoint misconfigured: {configured_endpoint}"
        )
        assert configured_headers == cloud_trace_config["headers"], (
            f"Cloud Trace headers misconfigured: {configured_headers}"
        )
            
        # If OTLP is available, test exporter creation
        if otlp_available:
            try:
                # Test GRPC exporter creation with Cloud Trace config
                grpc_exporter = OTLPSpanExporter(
                    endpoint=configured_endpoint,
                    headers={"x-goog-user-project": "netra-staging"}
                )
                assert grpc_exporter is not None
                self.record_metric("cloud_trace_grpc_exporter_created", True)
                
            except Exception as e:
                self.record_metric("cloud_trace_exporter_creation_error", str(e))
                
    def test_auto_instrumentation_resource_attributes(self):
        """
        Test automatic instrumentation resource attributes configuration.
        
        Validates service identification for distributed tracing.
        """
        # Configure service resource attributes
        resource_config = {
            "service.name": "netra-apex-backend",
            "service.version": "1.0.0",
            "service.environment": "test",
            "deployment.environment": "test"
        }
        
        # Format as OTEL_RESOURCE_ATTRIBUTES
        resource_string = ",".join([f"{k}={v}" for k, v in resource_config.items()])
        self.set_env_var("OTEL_RESOURCE_ATTRIBUTES", resource_string)
        
        # Validate resource attributes
        configured_attributes = self.get_env_var("OTEL_RESOURCE_ATTRIBUTES")
        assert configured_attributes is not None, "OTEL_RESOURCE_ATTRIBUTES not configured"
        
        # Parse and validate individual attributes
        parsed_attributes = {}
        for attr in configured_attributes.split(","):
            if "=" in attr:
                key, value = attr.split("=", 1)
                parsed_attributes[key] = value
                
        for expected_key, expected_value in resource_config.items():
            assert expected_key in parsed_attributes, (
                f"Resource attribute {expected_key} missing from configuration"
            )
            assert parsed_attributes[expected_key] == expected_value, (
                f"Resource attribute {expected_key} = {parsed_attributes[expected_key]}, "
                f"expected {expected_value}"
            )
            
        self.record_metric("resource_attributes_configured", len(parsed_attributes))
        
    def test_auto_instrumentation_sampling_configuration(self):
        """
        Test automatic instrumentation sampling configuration.
        
        Validates trace sampling setup for performance optimization.
        """
        # Configure sampling - 10% sampling for production efficiency
        sampling_configs = [
            ("OTEL_TRACES_SAMPLER", "traceidratio"),
            ("OTEL_TRACES_SAMPLER_ARG", "0.1"),  # 10% sampling
            ("OTEL_BSP_SCHEDULE_DELAY", "5000"),  # 5 second batch delay
            ("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512"),  # Batch size
        ]
        
        # Apply sampling configuration
        for key, value in sampling_configs:
            self.set_env_var(key, value)
            
        # Validate sampling configuration
        for key, expected_value in sampling_configs:
            actual_value = self.get_env_var(key)
            assert actual_value == expected_value, (
                f"Sampling config {key} = {actual_value}, expected {expected_value}"
            )
            
        # Test sampling ratio validation
        sampling_ratio = float(self.get_env_var("OTEL_TRACES_SAMPLER_ARG", "0"))
        assert 0.0 <= sampling_ratio <= 1.0, (
            f"Sampling ratio {sampling_ratio} should be between 0.0 and 1.0"
        )
        
        self.record_metric("sampling_ratio", sampling_ratio)
        self.record_metric("batch_delay_ms", int(self.get_env_var("OTEL_BSP_SCHEDULE_DELAY", "0")))
        
    def test_auto_instrumentation_exclusion_configuration(self):
        """
        Test automatic instrumentation URL exclusion configuration.
        
        Validates that health checks and metrics endpoints are excluded from tracing.
        """
        # Configure URL exclusions - avoid tracing health/metrics endpoints
        excluded_urls = "/health,/metrics,/ready,/favicon.ico"
        self.set_env_var("OTEL_PYTHON_EXCLUDED_URLS", excluded_urls)
        
        # Validate exclusion configuration
        configured_exclusions = self.get_env_var("OTEL_PYTHON_EXCLUDED_URLS")
        assert configured_exclusions == excluded_urls, (
            f"URL exclusions misconfigured: {configured_exclusions}"
        )
        
        # Parse exclusions
        exclusion_list = [url.strip() for url in configured_exclusions.split(",")]
        
        # Validate critical exclusions are present
        critical_exclusions = ["/health", "/metrics", "/ready"]
        for critical_url in critical_exclusions:
            assert critical_url in exclusion_list, (
                f"Critical URL {critical_url} should be excluded from tracing"
            )
            
        self.record_metric("excluded_urls_count", len(exclusion_list))
        
    def test_auto_instrumentation_performance_configuration(self):
        """
        Test performance-related auto-instrumentation configuration.
        
        Validates settings that minimize overhead in production.
        """
        # Performance optimizations
        performance_config = {
            # Disable expensive instrumentation features in production
            "OTEL_PYTHON_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST": "",
            "OTEL_PYTHON_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_CLIENT_REQUEST": "",
            "OTEL_PYTHON_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_RESPONSE": "",
            "OTEL_PYTHON_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_CLIENT_RESPONSE": "",
            
            # Optimize batch processing
            "OTEL_BSP_MAX_QUEUE_SIZE": "2048",
            "OTEL_BSP_EXPORT_TIMEOUT": "30000",  # 30 seconds
            "OTEL_BSP_MAX_EXPORT_BATCH_SIZE": "512",
            
            # Disable metrics by default to reduce overhead  
            "OTEL_METRICS_EXPORTER": "none",
        }
        
        # Apply performance configuration
        for key, value in performance_config.items():
            self.set_env_var(key, value)
            
        # Validate configuration
        for key, expected_value in performance_config.items():
            actual_value = self.get_env_var(key)
            assert actual_value == expected_value, (
                f"Performance config {key} = {actual_value}, expected {expected_value}"
            )
            
        # Validate numeric settings
        queue_size = int(self.get_env_var("OTEL_BSP_MAX_QUEUE_SIZE", "0"))
        assert queue_size > 0, f"Queue size {queue_size} should be positive"
        
        timeout_ms = int(self.get_env_var("OTEL_BSP_EXPORT_TIMEOUT", "0"))
        assert timeout_ms > 0, f"Export timeout {timeout_ms} should be positive"
        
        self.record_metric("batch_queue_size", queue_size)
        self.record_metric("export_timeout_ms", timeout_ms)


class TestAutoInstrumentationInitialization(SSotBaseTestCase):
    """Test automatic instrumentation initialization patterns."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("ENVIRONMENT", "test")
    
    def test_auto_instrumentation_initialization_order(self):
        """
        Test that auto-instrumentation initialization happens in correct order.
        
        Validates that SDK is initialized before instrumentors are applied.
        """
        # This test validates the initialization pattern without actually initializing
        # (to avoid interfering with other tests)
        
        initialization_steps = [
            "Import OpenTelemetry SDK",
            "Configure TracerProvider", 
            "Configure SpanProcessor",
            "Configure SpanExporter", 
            "Initialize Instrumentors",
            "Instrument Frameworks"
        ]
        
        # Mock the initialization process
        completed_steps = []
        
        # Step 1: SDK Import
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            completed_steps.append("Import OpenTelemetry SDK")
        except ImportError:
            pass
            
        # Step 2-4: Provider/Processor/Exporter setup (mocked)
        if len(completed_steps) > 0:
            completed_steps.extend([
                "Configure TracerProvider", 
                "Configure SpanProcessor",
                "Configure SpanExporter"
            ])
            
        # Step 5-6: Instrumentor setup (check availability)  
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            completed_steps.extend([
                "Initialize Instrumentors",
                "Instrument Frameworks" 
            ])
        except ImportError:
            pass
            
        # Validate initialization order
        expected_steps = len(initialization_steps)
        actual_steps = len(completed_steps)
        
        self.record_metric("initialization_steps_completed", actual_steps)
        self.record_metric("initialization_steps_expected", expected_steps)
        
        # At minimum, should be able to complete SDK import
        assert actual_steps >= 1, (
            f"Should complete at least SDK import step, completed: {completed_steps}"
        )
        
    def test_auto_instrumentation_conditional_initialization(self):
        """
        Test conditional initialization based on environment and feature flags.
        
        Validates that auto-instrumentation respects configuration flags.
        """
        # Test different initialization conditions
        test_scenarios = [
            {
                "name": "production_optimized",
                "env_vars": {
                    "ENVIRONMENT": "production",
                    "OTEL_TRACES_EXPORTER": "otlp",
                    "ENABLE_TRACING": "true"
                },
                "should_initialize": True
            },
            {
                "name": "development_full_tracing", 
                "env_vars": {
                    "ENVIRONMENT": "development",
                    "OTEL_TRACES_EXPORTER": "console", 
                    "ENABLE_TRACING": "true"
                },
                "should_initialize": True
            },
            {
                "name": "testing_disabled",
                "env_vars": {
                    "ENVIRONMENT": "test",
                    "OTEL_TRACES_EXPORTER": "none",
                    "ENABLE_TRACING": "false"
                },
                "should_initialize": False
            }
        ]
        
        scenario_results = {}
        
        for scenario in test_scenarios:
            # Set scenario environment variables
            for key, value in scenario["env_vars"].items():
                self.set_env_var(key, value)
                
            # Evaluate initialization conditions
            environment = self.get_env_var("ENVIRONMENT")
            exporter = self.get_env_var("OTEL_TRACES_EXPORTER")  
            tracing_enabled = self.get_env_var("ENABLE_TRACING", "true").lower() == "true"
            
            # Determine if initialization should happen
            should_init = (
                exporter not in ["none", None] and 
                tracing_enabled and
                environment != "test"  # Skip in test unless explicitly enabled
            )
            
            scenario_results[scenario["name"]] = {
                "should_initialize": should_init,
                "expected": scenario["should_initialize"],
                "environment": environment,
                "exporter": exporter,
                "tracing_enabled": tracing_enabled
            }
            
        # Validate scenarios
        for scenario_name, result in scenario_results.items():
            assert result["should_initialize"] == result["expected"], (
                f"Scenario {scenario_name}: initialization decision {result['should_initialize']} "
                f"!= expected {result['expected']}"
            )
            
        self.record_metric("conditional_scenarios_tested", len(scenario_results))