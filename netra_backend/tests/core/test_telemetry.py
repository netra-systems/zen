"""
Comprehensive tests for OpenTelemetry telemetry implementation.

Tests TelemetryManager, AgentTracer, and span creation functionality.
"""

import asyncio
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
from typing import Dict, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Status, StatusCode

from netra_backend.app.core.telemetry import (
    TelemetryManager,
    AgentTracer,
    telemetry_manager,
    agent_tracer
)
from netra_backend.app.core.telemetry_config import (
    TelemetryConfig,
    ExporterType,
    SamplingStrategy,
    get_telemetry_config
)


class TestTelemetryManager:
    """Test suite for TelemetryManager functionality."""
    
    def test_singleton_pattern(self):
        """Test that TelemetryManager follows singleton pattern."""
        manager1 = TelemetryManager()
        manager2 = TelemetryManager()
        assert manager1 is manager2
    
    def test_initialization_disabled(self):
        """Test telemetry initialization when disabled."""
        manager = TelemetryManager()
        manager.init_telemetry(
            service_name="test-service",
            service_version="1.0.0"
        )
        
        # When disabled via environment
        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            manager.init_telemetry()
            assert not manager.enabled
    
    @patch('netra_backend.app.core.telemetry.TracerProvider')
    @patch('netra_backend.app.core.telemetry.trace.set_tracer_provider')
    def test_initialization_with_otlp(self, mock_set_provider, mock_provider_class):
        """Test telemetry initialization with OTLP exporter."""
        manager = TelemetryManager()
        manager._initialized = False  # Reset for test
        
        with patch('netra_backend.app.core.telemetry.OTLPSpanExporter'):
            manager.init_telemetry(
                service_name="test-service",
                service_version="1.0.0",
                otlp_endpoint="localhost:4317",
                enable_console=False
            )
            
            assert manager.enabled
            assert manager.tracer is not None
            mock_set_provider.assert_called_once()
    
    @patch('netra_backend.app.core.telemetry.TracerProvider')
    @patch('netra_backend.app.core.telemetry.trace.set_tracer_provider')
    def test_initialization_with_jaeger(self, mock_set_provider, mock_provider_class):
        """Test telemetry initialization with Jaeger exporter."""
        manager = TelemetryManager()
        manager._initialized = False  # Reset for test
        
        with patch('netra_backend.app.core.telemetry.JaegerExporter'):
            manager.init_telemetry(
                service_name="test-service",
                service_version="1.0.0",
                jaeger_endpoint="localhost:6831",
                enable_console=False
            )
            
            assert manager.enabled
            assert manager.tracer is not None
            mock_set_provider.assert_called_once()
    
    def test_create_agent_span(self):
        """Test agent span creation."""
        manager = TelemetryManager()
        manager.enabled = True
        manager.tracer = Mock()
        
        mock_span = Mock()
        manager.tracer.start_span.return_value = mock_span
        
        span = manager.create_agent_span(
            agent_name="TestAgent",
            operation="execute",
            attributes={"user.id": "123"}
        )
        
        assert span == mock_span
        manager.tracer.start_span.assert_called_once_with("TestAgent.execute", context=None)
        mock_span.set_attribute.assert_any_call("agent.name", "TestAgent")
        mock_span.set_attribute.assert_any_call("agent.operation", "execute")
        mock_span.set_attribute.assert_any_call("user.id", "123")
    
    def test_create_agent_span_disabled(self):
        """Test agent span creation when telemetry is disabled."""
        manager = TelemetryManager()
        manager.enabled = False
        
        span = manager.create_agent_span(
            agent_name="TestAgent",
            operation="execute"
        )
        
        assert span is None
    
    async def test_start_agent_span_context_manager(self):
        """Test agent span context manager."""
        manager = TelemetryManager()
        manager.enabled = True
        manager.tracer = Mock()
        
        mock_span = MagicMock()
        manager.tracer.start_span.return_value = mock_span
        
        async with manager.start_agent_span(
            agent_name="TestAgent",
            operation="execute"
        ) as span:
            assert span == mock_span
        
        mock_span.set_status.assert_called_once()
        mock_span.end.assert_called_once()
    
    async def test_start_agent_span_with_exception(self):
        """Test agent span context manager with exception."""
        manager = TelemetryManager()
        manager.enabled = True
        manager.tracer = Mock()
        
        mock_span = MagicMock()
        manager.tracer.start_span.return_value = mock_span
        
        with pytest.raises(ValueError):
            async with manager.start_agent_span(
                agent_name="TestAgent",
                operation="execute"
            ) as span:
                raise ValueError("Test error")
        
        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called()
        mock_span.end.assert_called_once()
    
    def test_add_event(self):
        """Test adding event to span."""
        manager = TelemetryManager()
        manager.enabled = True
        
        mock_span = Mock()
        manager.add_event(
            mock_span,
            "test_event",
            {"key": "value"}
        )
        
        mock_span.add_event.assert_called_once_with(
            "test_event",
            attributes={"key": "value"}
        )
    
    def test_record_exception(self):
        """Test recording exception in span."""
        manager = TelemetryManager()
        manager.enabled = True
        
        mock_span = Mock()
        error = ValueError("Test error")
        
        manager.record_exception(mock_span, error)
        
        mock_span.record_exception.assert_called_once_with(error)
        mock_span.set_attribute.assert_any_call("error", True)
        mock_span.set_attribute.assert_any_call("error.type", "ValueError")
        mock_span.set_attribute.assert_any_call("error.message", "Test error")
    
    def test_set_status(self):
        """Test setting span status."""
        manager = TelemetryManager()
        manager.enabled = True
        
        mock_span = Mock()
        status = Status(StatusCode.OK)
        
        manager.set_status(mock_span, status)
        
        mock_span.set_status.assert_called_once_with(status)
    
    def test_extract_trace_context(self):
        """Test extracting trace context from carrier."""
        manager = TelemetryManager()
        manager.enabled = True
        
        carrier = {"traceparent": "00-trace-span-01"}
        
        with patch('netra_backend.app.core.telemetry.extract') as mock_extract:
            mock_extract.return_value = "context"
            context = manager.extract_trace_context(carrier)
            
            assert context == "context"
            mock_extract.assert_called_once_with(carrier)
    
    def test_inject_trace_context(self):
        """Test injecting trace context into carrier."""
        manager = TelemetryManager()
        manager.enabled = True
        
        carrier = {}
        
        with patch('netra_backend.app.core.telemetry.inject') as mock_inject:
            manager.inject_trace_context(carrier)
            mock_inject.assert_called_once_with(carrier)
    
    def test_get_current_span(self):
        """Test getting current span."""
        manager = TelemetryManager()
        manager.enabled = True
        
        with patch('netra_backend.app.core.telemetry.trace.get_current_span') as mock_get:
            mock_get.return_value = "current_span"
            span = manager.get_current_span()
            
            assert span == "current_span"
            mock_get.assert_called_once()
    
    def test_shutdown(self):
        """Test telemetry shutdown."""
        manager = TelemetryManager()
        manager.tracer_provider = Mock()
        
        manager.shutdown()
        
        manager.tracer_provider.shutdown.assert_called_once()


class TestAgentTracer:
    """Test suite for AgentTracer functionality."""
    
    def test_initialization(self):
        """Test AgentTracer initialization."""
        tracer = AgentTracer()
        assert tracer.telemetry is not None
        assert isinstance(tracer.telemetry, TelemetryManager)
    
    def test_start_agent_span(self):
        """Test starting agent span with context."""
        tracer = AgentTracer()
        tracer.telemetry = Mock()
        
        context = {
            "agent_id": "agent-123",
            "user_id": "user-456",
            "thread_id": "thread-789",
            "session_id": "session-000"
        }
        
        tracer.start_agent_span("TestAgent", context)
        
        tracer.telemetry.create_agent_span.assert_called_once_with(
            agent_name="TestAgent",
            operation="execute",
            attributes={
                "agent.id": "agent-123",
                "user.id": "user-456",
                "thread.id": "thread-789",
                "session.id": "session-000"
            }
        )
    
    def test_start_agent_span_filters_none(self):
        """Test that start_agent_span filters out None values."""
        tracer = AgentTracer()
        tracer.telemetry = Mock()
        
        context = {
            "agent_id": "agent-123",
            "user_id": None,
            "thread_id": "thread-789",
            "session_id": None
        }
        
        tracer.start_agent_span("TestAgent", context)
        
        tracer.telemetry.create_agent_span.assert_called_once_with(
            agent_name="TestAgent",
            operation="execute",
            attributes={
                "agent.id": "agent-123",
                "thread.id": "thread-789"
            }
        )
    
    def test_add_event(self):
        """Test adding event to span."""
        tracer = AgentTracer()
        tracer.telemetry = Mock()
        
        mock_span = Mock()
        tracer.add_event(mock_span, "test_event", {"key": "value"})
        
        tracer.telemetry.add_event.assert_called_once_with(
            mock_span,
            "test_event",
            {"key": "value"}
        )
    
    def test_record_exception(self):
        """Test recording exception in span."""
        tracer = AgentTracer()
        tracer.telemetry = Mock()
        
        mock_span = Mock()
        error = ValueError("Test error")
        
        tracer.record_exception(mock_span, error)
        
        tracer.telemetry.record_exception.assert_called_once_with(mock_span, error)
    
    def test_set_status(self):
        """Test setting span status."""
        tracer = AgentTracer()
        tracer.telemetry = Mock()
        
        mock_span = Mock()
        status = Status(StatusCode.OK)
        
        tracer.set_status(mock_span, status)
        
        tracer.telemetry.set_status.assert_called_once_with(mock_span, status)


class TestTelemetryConfig:
    """Test suite for TelemetryConfig."""
    
    def test_default_config(self):
        """Test default telemetry configuration."""
        config = TelemetryConfig()
        
        assert config.enabled is True
        assert config.service_name == "netra-backend"
        assert config.service_version == "1.0.0"
        assert config.environment == "development"
        assert config.sampling_strategy == SamplingStrategy.ALWAYS_ON
    
    def test_config_from_environment(self):
        """Test configuration from environment variables."""
        env_vars = {
            "OTEL_ENABLED": "false",
            "OTEL_SERVICE_NAME": "test-service",
            "OTEL_SERVICE_VERSION": "2.0.0",
            "ENVIRONMENT": "production",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "otel-collector:4317",
            "OTEL_SAMPLING_STRATEGY": "trace_id_ratio",
            "OTEL_SAMPLING_RATE": "0.5"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = TelemetryConfig.from_environment()
            
            assert config.enabled is False
            assert config.service_name == "test-service"
            assert config.service_version == "2.0.0"
            assert config.environment == "production"
            assert config.otlp_endpoint == "otel-collector:4317"
            assert config.sampling_strategy == SamplingStrategy.TRACE_ID_RATIO
            assert config.sampling_rate == 0.5
    
    def test_get_exporter_type(self):
        """Test determining exporter type based on configuration."""
        config = TelemetryConfig()
        
        # Test with OTLP endpoint
        config.otlp_endpoint = "localhost:4317"
        assert config.get_exporter_type() == ExporterType.OTLP
        
        # Test with Jaeger endpoint
        config.otlp_endpoint = None
        config.jaeger_endpoint = "localhost:6831"
        assert config.get_exporter_type() == ExporterType.JAEGER
        
        # Test with console exporter
        config.jaeger_endpoint = None
        config.enable_console_exporter = True
        assert config.get_exporter_type() == ExporterType.CONSOLE
        
        # Test with no exporter
        config.enable_console_exporter = False
        assert config.get_exporter_type() == ExporterType.NONE
        
        # Test when disabled
        config.enabled = False
        assert config.get_exporter_type() == ExporterType.NONE
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = TelemetryConfig()
        
        # Valid configuration with OTLP
        config.otlp_endpoint = "localhost:4317"
        assert config.validate() is True
        
        # Valid configuration with Jaeger
        config.otlp_endpoint = None
        config.jaeger_endpoint = "localhost:6831"
        assert config.validate() is True
        
        # Valid configuration with console
        config.jaeger_endpoint = None
        config.enable_console_exporter = True
        assert config.validate() is True
        
        # Invalid configuration (no exporter)
        config.enable_console_exporter = False
        assert config.validate() is False
        
        # Invalid sampling rate
        config.enable_console_exporter = True
        config.sampling_strategy = SamplingStrategy.TRACE_ID_RATIO
        config.sampling_rate = 1.5  # Invalid rate > 1.0
        assert config.validate() is False
        
        # Valid sampling rate
        config.sampling_rate = 0.5
        assert config.validate() is True
        
        # Disabled configuration is always valid
        config.enabled = False
        assert config.validate() is True


class TestGlobalInstances:
    """Test global telemetry instances."""
    
    def test_global_telemetry_manager(self):
        """Test global telemetry_manager instance."""
        assert telemetry_manager is not None
        assert isinstance(telemetry_manager, TelemetryManager)
    
    def test_global_agent_tracer(self):
        """Test global agent_tracer instance."""
        assert agent_tracer is not None
        assert isinstance(agent_tracer, AgentTracer)
        assert agent_tracer.telemetry is telemetry_manager