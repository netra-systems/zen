"""
Integration tests for authentication resilience middleware and API routes.

Tests the complete auth resilience system including:
- Middleware integration with FastAPI
- API route functionality
- End-to-end request handling
- Circuit breaker behavior in HTTP context
- Fallback mechanism activation
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
from netra_backend.app.routes.auth_resilience import router
from netra_backend.app.clients.auth_resilience_service import (
    AuthResilienceMode,
    AuthOperationType,
    get_auth_resilience_service,
)


class TestAuthResilienceMiddleware:
    """Test authentication resilience middleware integration."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with auth resilience middleware."""
        app = FastAPI()
        
        # Add auth middleware
        app.add_middleware(FastAPIAuthMiddleware)
        
        # Add test route
        @app.get("/protected")
        async def protected_route(request):
            return {
                "message": "Protected content",
                "auth_mode": request.state.auth_resilience_mode,
                "fallback_used": request.state.auth_fallback_used,
                "user_id": request.state.user_id
            }
        
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def async_client(self, app):
        """Create async test client."""
        return AsyncClient(app=app, base_url="http://test")

    def test_successful_auth_request(self, client):
        """Test successful authentication through middleware."""
        mock_validation_result = {
            "success": True,
            "valid": True,
            "user_id": "test_user_123",
            "permissions": ["read", "write"],
            "resilience_mode": "normal",
            "source": "auth_service",
            "fallback_used": False
        }
        
        with patch('netra_backend.app.middleware.fastapi_auth_middleware.validate_token_with_resilience') as mock_validate:
            mock_validate.return_value = asyncio.create_task(asyncio.coroutine(lambda: mock_validation_result)())
            
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer valid_token_123"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "test_user_123"
            assert data["auth_mode"] == "normal"
            assert data["fallback_used"] is False
            
            # Check resilience headers
            assert response.headers["X-Auth-Resilience-Mode"] == "normal"

    def test_fallback_auth_request(self, client):
        """Test authentication using fallback mechanisms."""
        mock_validation_result = {
            "success": True,
            "valid": True,
            "user_id": "cached_user_456",
            "permissions": ["read"],
            "resilience_mode": "cached_fallback",
            "source": "cache",
            "fallback_used": True,
            "cache_age_seconds": 150
        }
        
        with patch('netra_backend.app.middleware.fastapi_auth_middleware.validate_token_with_resilience') as mock_validate:
            mock_validate.return_value = asyncio.create_task(asyncio.coroutine(lambda: mock_validation_result)())
            
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer cached_token_456"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "cached_user_456"
            assert data["auth_mode"] == "cached_fallback"
            assert data["fallback_used"] is True
            
            # Check resilience headers
            assert response.headers["X-Auth-Resilience-Mode"] == "cached_fallback"
            assert response.headers["X-Auth-Fallback-Source"] == "cache"

    def test_degraded_mode_auth_request(self, client):
        """Test authentication in degraded mode."""
        mock_validation_result = {
            "success": True,
            "valid": True,
            "user_id": "degraded_user",
            "permissions": ["read"],
            "resilience_mode": "degraded",
            "source": "degraded_mode",
            "fallback_used": True,
            "warning": "Operating in degraded mode"
        }
        
        with patch('netra_backend.app.middleware.fastapi_auth_middleware.validate_token_with_resilience') as mock_validate:
            mock_validate.return_value = asyncio.create_task(asyncio.coroutine(lambda: mock_validation_result)())
            
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer any_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "degraded_user"
            assert data["auth_mode"] == "degraded"
            assert data["fallback_used"] is True
            
            # Check resilience headers
            assert response.headers["X-Auth-Resilience-Mode"] == "degraded"
            assert response.headers["X-Auth-Fallback-Source"] == "degraded_mode"

    def test_failed_auth_request(self, client):
        """Test authentication failure when all mechanisms fail."""
        mock_validation_result = {
            "success": False,
            "valid": False,
            "error": "Authentication unavailable: Service down",
            "resilience_mode": "normal",
            "fallback_used": True
        }
        
        with patch('netra_backend.app.middleware.fastapi_auth_middleware.validate_token_with_resilience') as mock_validate:
            mock_validate.return_value = asyncio.create_task(asyncio.coroutine(lambda: mock_validation_result)())
            
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer invalid_token"}
            )
            
            assert response.status_code == 401
            assert "authentication_failed" in response.json()["detail"]["error"]

    def test_operation_type_detection(self, client):
        """Test that middleware correctly detects operation types."""
        mock_validation_result = {
            "success": True,
            "valid": True,
            "user_id": "health_user",
            "permissions": ["read"],
            "resilience_mode": "normal",
            "source": "auth_service",
            "fallback_used": False
        }
        
        # Test health endpoint detection
        with patch('netra_backend.app.middleware.fastapi_auth_middleware.validate_token_with_resilience') as mock_validate:
            mock_validate.return_value = asyncio.create_task(asyncio.coroutine(lambda: mock_validation_result)())
            
            # Add health endpoint to test app
            from fastapi import Request
            
            @client.app.get("/health")
            async def health_endpoint(request: Request):
                return {"status": "healthy"}
            
            response = client.get(
                "/health",
                headers={"Authorization": "Bearer health_token"}
            )
            
            # Verify that health check operation type was used
            mock_validate.assert_called()
            call_args = mock_validate.call_args
            assert call_args[0][1] == AuthOperationType.HEALTH_CHECK

    def test_missing_token(self, client):
        """Test request without authorization token."""
        response = client.get("/protected")
        
        assert response.status_code == 401
        assert "No authorization header" in str(response.json())

    def test_malformed_token(self, client):
        """Test request with malformed authorization header."""
        response = client.get(
            "/protected",
            headers={"Authorization": "InvalidFormat token"}
        )
        
        assert response.status_code == 401
        assert "Invalid authorization format" in str(response.json())

    @pytest.mark.asyncio
    async def test_async_client_integration(self, async_client):
        """Test async client integration with auth resilience."""
        mock_validation_result = {
            "success": True,
            "valid": True,
            "user_id": "async_user",
            "permissions": ["read"],
            "resilience_mode": "normal",
            "source": "auth_service",
            "fallback_used": False
        }
        
        with patch('netra_backend.app.middleware.fastapi_auth_middleware.validate_token_with_resilience') as mock_validate:
            mock_validate.return_value = mock_validation_result
            
            response = await async_client.get(
                "/protected",
                headers={"Authorization": "Bearer async_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "async_user"


class TestAuthResilienceAPIRoutes:
    """Test authentication resilience API routes."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with auth resilience routes."""
        app = FastAPI()
        app.include_router(router, prefix="/api")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test auth resilience health endpoint."""
        mock_health = {
            "service": "authentication_resilience",
            "status": "healthy",
            "current_mode": "normal",
            "auth_service_available": True,
            "emergency_bypass_active": False,
            "metrics": {
                "total_attempts": 100,
                "success_rate": 0.95,
                "cache_hit_rate": 0.75,
                "consecutive_failures": 0
            }
        }
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_health') as mock_get_health:
            mock_get_health.return_value = asyncio.create_task(asyncio.coroutine(lambda: mock_health)())
            
            response = client.get("/auth-resilience/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "authentication_resilience"
            assert data["status"] == "healthy"
            assert data["current_mode"] == "normal"

    def test_status_endpoint(self, client):
        """Test auth resilience status endpoint."""
        mock_service = MagicMock()
        mock_service.get_health_status = AsyncMock(return_value={
            "service": "authentication_resilience",
            "status": "healthy",
            "current_mode": "normal"
        })
        mock_service.get_metrics = AsyncMock(return_value=MagicMock(
            total_auth_attempts=50,
            successful_auth_operations=47,
            failed_auth_operations=3,
            cache_hits=25,
            cache_misses=10,
            fallback_activations=2,
            emergency_bypasses=0,
            mode_changes=1,
            consecutive_failures=0,
            recovery_attempts=0,
            successful_recoveries=0,
            current_mode=AuthResilienceMode.NORMAL,
            circuit_breaker_state="closed",
            auth_service_health=True,
            last_mode_change=None
        ))
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.get("/auth-resilience/status")
            
            assert response.status_code == 200
            data = response.json()
            assert "service_info" in data
            assert "health" in data
            assert "metrics" in data
            assert "current_state" in data
            assert data["metrics"]["total_auth_attempts"] == 50

    def test_circuit_breaker_endpoint(self, client):
        """Test circuit breaker status endpoint."""
        mock_service = MagicMock()
        mock_circuit_status = {
            "name": "auth_service",
            "state": "closed",
            "is_healthy": True,
            "last_state_change": 1234567890,
            "sliding_window_size": 10,
            "metrics": {"total_calls": 100, "failed_calls": 5},
            "config": {"failure_threshold": 5, "recovery_timeout": 30},
            "health": {"has_health_checker": False}
        }
        mock_service.circuit_breaker.get_status.return_value = mock_circuit_status
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.get("/auth-resilience/circuit-breaker")
            
            assert response.status_code == 200
            data = response.json()
            assert "circuit_breaker" in data
            assert data["circuit_breaker"]["state"] == "closed"
            assert data["circuit_breaker"]["is_healthy"] is True

    def test_manual_recovery_endpoint(self, client):
        """Test manual recovery trigger endpoint."""
        mock_service = MagicMock()
        mock_service.current_mode = AuthResilienceMode.DEGRADED
        mock_service._attempt_mode_recovery = AsyncMock()
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.post("/auth-resilience/recovery/manual")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Recovery attempt triggered" in data["message"]
            mock_service._attempt_mode_recovery.assert_called_once()

    def test_force_mode_endpoint(self, client):
        """Test force mode endpoint."""
        mock_service = MagicMock()
        mock_service.current_mode = AuthResilienceMode.NORMAL
        mock_service.force_mode = AsyncMock()
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.post("/auth-resilience/mode/force?mode=degraded")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "degraded" in data["message"]
            mock_service.force_mode.assert_called_once_with(AuthResilienceMode.DEGRADED)

    def test_force_emergency_mode_requires_confirmation(self, client):
        """Test that emergency mode requires confirmation."""
        response = client.post("/auth-resilience/mode/force?mode=emergency")
        
        assert response.status_code == 400
        assert "confirmation" in response.json()["detail"].lower()

    def test_force_emergency_mode_with_confirmation(self, client):
        """Test emergency mode with confirmation."""
        mock_service = MagicMock()
        mock_service.current_mode = AuthResilienceMode.NORMAL
        mock_service.force_mode = AsyncMock()
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.post("/auth-resilience/mode/force?mode=emergency&confirm=true")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_service.force_mode.assert_called_once_with(AuthResilienceMode.EMERGENCY)

    def test_reset_circuit_breaker_endpoint(self, client):
        """Test circuit breaker reset endpoint."""
        mock_service = MagicMock()
        mock_service.circuit_breaker.state.value = "open"
        mock_service.circuit_breaker.reset = AsyncMock()
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.post("/auth-resilience/circuit-breaker/reset")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "reset" in data["message"].lower()
            mock_service.circuit_breaker.reset.assert_called_once()

    def test_force_circuit_breaker_open(self, client):
        """Test forcing circuit breaker open."""
        mock_service = MagicMock()
        mock_service.circuit_breaker.state.value = "closed"
        mock_service.circuit_breaker.force_open = AsyncMock()
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.post("/auth-resilience/circuit-breaker/force-open?confirm=true")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_service.circuit_breaker.force_open.assert_called_once()

    def test_reset_metrics_endpoint(self, client):
        """Test metrics reset endpoint."""
        mock_service = MagicMock()
        mock_service.reset_metrics = MagicMock()
        mock_service.metrics.last_mode_change = None
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.post("/auth-resilience/metrics/reset")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_service.reset_metrics.assert_called_once()

    def test_validate_token_test_endpoint(self, client):
        """Test token validation test endpoint."""
        mock_service = MagicMock()
        mock_service.validate_token_with_resilience = AsyncMock(return_value={
            "success": True,
            "valid": True,
            "user_id": "test_user",
            "resilience_mode": "normal",
            "source": "auth_service"
        })
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.get("/auth-resilience/test/validate-token?token=test_token")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["test_mode"] is True
            assert data["user_id"] == "test_user"

    def test_validate_token_force_failure(self, client):
        """Test token validation with forced failure."""
        response = client.get("/auth-resilience/test/validate-token?token=test&force_failure=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["test_mode"] is True
        assert "Simulated failure" in data["error"]

    def test_config_endpoint(self, client):
        """Test configuration endpoint."""
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.circuit_breaker_failure_threshold = 5
        mock_config.circuit_breaker_recovery_timeout = 30.0
        mock_config.cache_ttl_seconds = 300
        mock_config.max_retry_attempts = 3
        mock_config.allow_read_only_operations = True
        mock_config.emergency_bypass_enabled = True
        mock_config.read_only_endpoints = {"/health", "/status"}
        mock_config.emergency_bypass_endpoints = {"/health", "/metrics"}
        mock_service.config = mock_config
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.get("/auth-resilience/config")
            
            assert response.status_code == 200
            data = response.json()
            assert "circuit_breaker" in data
            assert "cache" in data
            assert "retry" in data
            assert "degraded_mode" in data
            assert "emergency_bypass" in data
            assert data["circuit_breaker"]["failure_threshold"] == 5

    def test_invalid_operation_type(self, client):
        """Test invalid operation type in test endpoint."""
        response = client.get("/auth-resilience/test/validate-token?token=test&operation_type=invalid")
        
        assert response.status_code == 400
        assert "Invalid operation type" in response.json()["detail"]

    def test_invalid_mode_in_force_endpoint(self, client):
        """Test invalid mode in force mode endpoint."""
        response = client.post("/auth-resilience/mode/force?mode=invalid_mode")
        
        assert response.status_code == 400
        assert "Invalid mode" in response.json()["detail"]


@pytest.mark.integration
class TestEndToEndAuthResilience:
    """End-to-end integration tests for the complete auth resilience system."""

    @pytest.fixture
    def full_app(self):
        """Create complete FastAPI app with all auth resilience components."""
        app = FastAPI()
        
        # Add auth middleware
        app.add_middleware(FastAPIAuthMiddleware)
        
        # Add auth resilience routes
        app.include_router(router, prefix="/api")
        
        # Add test routes
        @app.get("/protected/normal")
        async def normal_route(request):
            return {
                "message": "Normal protected content",
                "user_id": request.state.user_id,
                "auth_mode": request.state.auth_resilience_mode
            }
        
        @app.get("/health")
        async def health_route():
            return {"status": "healthy"}
        
        return app

    @pytest.fixture
    def client(self, full_app):
        """Create test client for full app."""
        return TestClient(full_app)

    def test_complete_resilience_flow(self, client):
        """Test complete resilience flow from normal to fallback to recovery."""
        # Mock service to control behavior throughout the test
        mock_service = get_auth_resilience_service()
        
        with patch.object(mock_service, 'validate_token_with_resilience') as mock_validate:
            # Test 1: Normal operation
            mock_validate.return_value = asyncio.create_task(asyncio.coroutine(lambda: {
                "success": True,
                "valid": True,
                "user_id": "normal_user",
                "resilience_mode": "normal",
                "source": "auth_service",
                "fallback_used": False
            })())
            
            response = client.get("/protected/normal", headers={"Authorization": "Bearer normal_token"})
            assert response.status_code == 200
            assert response.json()["auth_mode"] == "normal"
            
            # Test 2: Fallback operation
            mock_validate.return_value = asyncio.create_task(asyncio.coroutine(lambda: {
                "success": True,
                "valid": True,
                "user_id": "cached_user",
                "resilience_mode": "cached_fallback",
                "source": "cache",
                "fallback_used": True
            })())
            
            response = client.get("/protected/normal", headers={"Authorization": "Bearer cached_token"})
            assert response.status_code == 200
            assert response.json()["auth_mode"] == "cached_fallback"
            assert "X-Auth-Fallback-Source" in response.headers

    def test_health_endpoint_resilience(self, client):
        """Test that health endpoints work even during auth failures."""
        # Health endpoints should be accessible even with auth issues
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_monitoring_endpoints(self, client):
        """Test monitoring and management endpoints."""
        # Test health endpoint
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_health') as mock_health:
            mock_health.return_value = asyncio.create_task(asyncio.coroutine(lambda: {"status": "healthy"})())
            
            response = client.get("/auth-resilience/health")
            assert response.status_code == 200
        
        # Test status endpoint
        mock_service = MagicMock()
        mock_service.get_health_status = AsyncMock(return_value={"status": "healthy"})
        mock_service.get_metrics = AsyncMock(return_value=MagicMock(
            total_auth_attempts=0,
            successful_auth_operations=0,
            failed_auth_operations=0,
            cache_hits=0,
            cache_misses=0,
            fallback_activations=0,
            emergency_bypasses=0,
            mode_changes=0,
            consecutive_failures=0,
            recovery_attempts=0,
            successful_recoveries=0,
            current_mode=AuthResilienceMode.NORMAL,
            circuit_breaker_state="closed",
            auth_service_health=True,
            last_mode_change=None
        ))
        
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_service', return_value=mock_service):
            response = client.get("/auth-resilience/status")
            assert response.status_code == 200

    def test_error_handling_in_routes(self, client):
        """Test error handling in auth resilience routes."""
        # Test health endpoint with service error
        with patch('netra_backend.app.routes.auth_resilience.get_auth_resilience_health', side_effect=Exception("Service error")):
            response = client.get("/auth-resilience/health")
            assert response.status_code == 500
            assert "Health check failed" in response.json()["detail"]