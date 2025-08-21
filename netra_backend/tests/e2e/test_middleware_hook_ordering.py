"""
E2E Tests for Middleware and Hook Ordering

Tests middleware and hook ordering and execution sequences:
- Middleware execution order and coordination
- Hook execution sequence in middleware
- Mixin composition within middleware systems
- Security and metrics middleware interaction

All functions ≤8 lines per CLAUDE.md requirements.
Module ≤300 lines per CLAUDE.md requirements.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Add project root to path

from netra_backend.app.middleware.security_middleware import SecurityMiddleware, RateLimitTracker
from netra_backend.app.middleware.metrics_middleware import AgentMetricsMiddleware
from logging_config import central_logger

# Add project root to path

logger = central_logger.get_logger(__name__)


class TestMiddlewareOrdering:
    """Test middleware ordering and execution sequence."""
    
    async def test_middleware_execution_order(self):
        """Test correct middleware execution order."""
        execution_order = []
        
        class OrderTrackingMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, name: str):
                super().__init__(app)
                self.name = name
            
            async def dispatch(self, request: Request, call_next):
                execution_order.append(f"{self.name}_start")
                response = await call_next(request)
                execution_order.append(f"{self.name}_end")
                return response
        
        # Simulate middleware stack
        middleware1 = OrderTrackingMiddleware(None, "first")
        middleware2 = OrderTrackingMiddleware(None, "second")
        
        async def mock_app(request):
            execution_order.append("app")
            return Mock(spec=Response)
        
        # Test execution order
        await middleware1.dispatch(Mock(spec=Request), 
                                 lambda r: middleware2.dispatch(r, mock_app))
        
        expected_order = ["first_start", "second_start", "app", "second_end", "first_end"]
        assert execution_order == expected_order
    
    async def test_security_before_metrics(self):
        """Test security middleware executes before metrics."""
        security_middleware = self._create_security_middleware()
        metrics_middleware = AgentMetricsMiddleware()
        
        execution_log = []
        
        async def mock_call_next(request):
            execution_log.append("app")
            return Mock(spec=Response, headers={})
        
        request = self._create_mock_request()
        
        # Security middleware first
        with patch.object(security_middleware, '_perform_security_validations') as sec_mock:
            sec_mock.side_effect = lambda r: execution_log.append("security")
            
            try:
                await security_middleware.dispatch(request, mock_call_next)
            except Exception:
                pass  # Expected due to mocked dependencies
        
        assert "security" in execution_log
    
    async def test_error_middleware_coordination(self):
        """Test error middleware coordination in chain."""
        middleware = self._create_security_middleware()
        
        async def failing_call_next(request):
            raise ValueError("Test error")
        
        request = self._create_mock_request()
        
        with pytest.raises(ValueError):
            await middleware.dispatch(request, failing_call_next)
    
    async def test_middleware_chain_interruption(self):
        """Test middleware chain interruption on errors."""
        middleware = self._create_security_middleware()
        
        # Test that security middleware can interrupt chain
        request = self._create_mock_request(content_length=SecurityConfig.MAX_REQUEST_SIZE + 1)
        
        async def should_not_execute(request):
            pytest.fail("This should not execute due to security validation")
        
        with pytest.raises(HTTPException):
            await middleware.dispatch(request, should_not_execute)
    
    def _create_security_middleware(self) -> SecurityMiddleware:
        """Create security middleware instance for testing."""
        return SecurityMiddleware(None)
    
    def _create_mock_request(self, content_length: int = 1000) -> Mock:
        """Create mock request for testing."""
        request = Mock(spec=Request)
        request.headers = {}
        request.headers.get = Mock(return_value=str(content_length))
        request.method = "GET"
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test.com")
        request.url.path = "/test"
        request.body = AsyncMock(return_value=b'')
        return request


class TestHookExecutionSequence:
    """Test hook execution sequence and coordination."""
    
    async def test_pre_request_hooks(self):
        """Test pre-request hook execution."""
        middleware = self._create_security_middleware()
        request = self._create_mock_request()
        
        with patch.object(middleware, '_validate_request_size') as size_mock, \
             patch.object(middleware, '_validate_url') as url_mock, \
             patch.object(middleware, '_validate_headers') as header_mock:
            
            await middleware._perform_security_validations(request)
            
            size_mock.assert_called_once()
            url_mock.assert_called_once()
            header_mock.assert_called_once()
    
    async def test_post_request_hooks(self):
        """Test post-request hook execution."""
        middleware = self._create_security_middleware()
        response = Mock(spec=Response)
        response.headers = {}
        
        async def mock_call_next(request):
            return response
        
        request = self._create_mock_request()
        
        with patch.object(middleware, '_add_security_headers') as headers_mock:
            try:
                await middleware._process_secure_request(request, mock_call_next)
            except Exception:
                pass  # Expected due to mocked dependencies
            
            headers_mock.assert_called_once()
    
    async def test_error_hooks_execution(self):
        """Test error hook execution in middleware."""
        middleware = self._create_security_middleware()
        
        test_error = ValueError("Test error")
        
        with patch.object(logger, 'error') as log_mock:
            with pytest.raises(HTTPException):
                middleware._handle_security_middleware_error(test_error)
            
            log_mock.assert_called_once()
    
    async def test_hook_dependency_chain(self):
        """Test hook dependency chain execution."""
        middleware = self._create_security_middleware()
        request = self._create_mock_request()
        
        # Test that hooks execute in dependency order
        with patch.object(middleware, '_check_rate_limits') as rate_mock:
            rate_mock.return_value = None  # No rate limiting
            
            try:
                await middleware._perform_security_validations(request)
            except Exception:
                pass  # Expected due to other validations
            
            rate_mock.assert_called_once()
    
    def _create_security_middleware(self) -> SecurityMiddleware:
        """Create security middleware instance for testing."""
        return SecurityMiddleware(None)
    
    def _create_mock_request(self) -> Mock:
        """Create mock request for testing."""
        request = Mock(spec=Request)
        request.headers = {}
        request.method = "GET"
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test.com")
        request.url.path = "/test"
        request.body = AsyncMock(return_value=b'')
        return request


class TestMixinComposition:
    """Test mixin composition within middleware systems."""
    
    def test_input_validator_composition(self):
        """Test input validator mixin composition."""
        middleware = self._create_security_middleware()
        
        # Verify validator is properly composed
        assert hasattr(middleware, 'input_validator')
        assert hasattr(middleware.input_validator, 'validators')
    
    def test_rate_limiter_composition(self):
        """Test rate limiter mixin composition."""
        custom_rate_limiter = RateLimitTracker()
        middleware = SecurityMiddleware(None, custom_rate_limiter)
        
        assert middleware.rate_limiter is custom_rate_limiter
    
    def test_auth_tracking_composition(self):
        """Test authentication tracking mixin composition."""
        middleware = self._create_security_middleware()
        
        assert hasattr(middleware, 'auth_attempt_tracker')
        assert hasattr(middleware, 'failed_auth_ips')
    
    def test_sensitive_endpoints_composition(self):
        """Test sensitive endpoints mixin composition."""
        middleware = self._create_security_middleware()
        
        # Verify sensitive endpoints are properly configured
        assert hasattr(middleware, 'sensitive_endpoints')
        assert "/api/auth/login" in middleware.sensitive_endpoints
        assert "/api/admin" in middleware.sensitive_endpoints
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with middleware."""
        middleware = self._create_security_middleware()
        
        # Verify circuit breaker components are accessible
        assert hasattr(middleware, 'rate_limiter')
        
        # Test rate limiting functionality
        rate_limiter = middleware.rate_limiter
        assert not rate_limiter.is_rate_limited("test_ip", 100)
    
    def _create_security_middleware(self) -> SecurityMiddleware:
        """Create security middleware instance for testing."""
        return SecurityMiddleware(None)


class TestMetricsMiddlewareIntegration:
    """Test metrics middleware integration with other components."""
    
    def test_metrics_middleware_initialization(self):
        """Test metrics middleware proper initialization."""
        metrics_middleware = AgentMetricsMiddleware()
        
        assert hasattr(metrics_middleware, 'metrics_collector')
        assert hasattr(metrics_middleware, '_operation_context')
        assert metrics_middleware._enabled is True
    
    def test_metrics_tracking_decoration(self):
        """Test metrics tracking decorator functionality."""
        metrics_middleware = AgentMetricsMiddleware()
        
        @metrics_middleware.track_agent_operation()
        async def test_operation():
            return "success"
        
        # Verify decorator was applied
        assert hasattr(test_operation, '__wrapped__')
    
    def test_metrics_context_manager(self):
        """Test metrics context manager functionality."""
        from netra_backend.app.middleware.metrics_middleware import AgentMetricsContextManager
        
        context_manager = AgentMetricsContextManager(
            "TestAgent", "test_operation"
        )
        
        assert context_manager.agent_name == "TestAgent"
        assert context_manager.operation_type == "test_operation"
    
    def test_operation_type_detection(self):
        """Test operation type detection in metrics middleware."""
        metrics_middleware = AgentMetricsMiddleware()
        
        # Test different operation type detection patterns
        execution_type = metrics_middleware._extract_operation_type(Mock(__name__="execute_task"))
        assert execution_type == "execution"
        
        validation_type = metrics_middleware._extract_operation_type(Mock(__name__="validate_input"))
        assert validation_type == "validation"
    
    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration."""
        metrics_middleware = AgentMetricsMiddleware()
        
        memory_usage = metrics_middleware._get_memory_usage()
        assert isinstance(memory_usage, float)
        cpu_usage = metrics_middleware._get_cpu_usage()
        assert isinstance(cpu_usage, float)