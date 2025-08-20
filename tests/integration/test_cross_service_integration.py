"""
Integration tests for cross-service functionality.

Tests CORS middleware enhancements, service discovery integration,
and health monitoring improvements.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response

from app.core.middleware_setup import CustomCORSMiddleware, setup_cors_middleware
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.health_monitor import HealthMonitor, HealthStatus, ServiceState
from dev_launcher.launcher import DevLauncher


class TestCORSEnhancements:
    """Test enhanced CORS middleware functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.options("/test")
        async def test_options():
            return Response(status_code=200)
        
        return app
    
    @pytest.fixture
    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            # Register test services
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
            discovery.write_auth_info({
                'port': 8081,
                'url': 'http://localhost:8081',
                'api_url': 'http://localhost:8081/api'
            })
            yield discovery
    
    def test_cors_middleware_initialization(self, app, service_discovery):
        """Test CORS middleware initializes with service discovery."""
        middleware = CustomCORSMiddleware(
            app,
            service_discovery=service_discovery,
            enable_metrics=True
        )
        
        assert middleware._service_discovery is service_discovery
        assert middleware._metrics_enabled is True
        assert middleware._cors_metrics is not None
        assert 'requests_processed' in middleware._cors_metrics
    
    def test_service_discovery_origins(self, service_discovery):
        """Test service discovery provides correct origins."""
        origins = service_discovery.get_all_service_origins()
        
        expected_origins = [
            'http://localhost:8000',  # backend api_url
            'http://localhost:3000',  # frontend url
            'http://localhost:8081',  # auth url
            'http://localhost:8081/api'  # auth api_url
        ]
        
        for expected in expected_origins:
            assert expected in origins
    
    @pytest.mark.asyncio
    async def test_preflight_with_service_discovery(self, app, service_discovery):
        """Test preflight requests work with service discovery."""
        middleware = CustomCORSMiddleware(
            app,
            service_discovery=service_discovery,
            enable_metrics=True
        )
        
        # Mock request
        request = Mock(spec=Request)
        request.method = "OPTIONS"
        request.headers = {"origin": "http://localhost:3000"}
        
        # Test preflight handling
        response = await middleware._handle_preflight_request(request)
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert "X-Service-ID" in response.headers["Access-Control-Allow-Headers"]
    
    @pytest.mark.asyncio
    async def test_cors_metrics_collection(self, app, service_discovery):
        """Test CORS metrics are collected properly."""
        middleware = CustomCORSMiddleware(
            app,
            service_discovery=service_discovery,
            enable_metrics=True
        )
        
        # Mock request and call_next
        request = Mock(spec=Request)
        request.method = "GET"
        request.headers = {"origin": "http://localhost:3000"}
        
        async def mock_call_next(req):
            return Response(content="test")
        
        # Process request
        await middleware.dispatch(request, mock_call_next)
        
        metrics = middleware.get_cors_metrics()
        assert metrics['requests_processed'] == 1
        assert "http://localhost:3000" in metrics['origins_allowed']
    
    def test_cross_service_auth_token_generation(self, service_discovery):
        """Test cross-service auth token generation."""
        # Initially no token
        assert service_discovery.get_cross_service_auth_token() is None
        
        # Set token
        test_token = "test-token-12345"
        service_discovery.set_cross_service_auth_token(test_token)
        
        # Verify token retrieval
        assert service_discovery.get_cross_service_auth_token() == test_token
    
    def test_service_cors_config(self, service_discovery):
        """Test service CORS configuration registration."""
        service_info = {
            'port': 8000,
            'url': 'http://localhost:8000'
        }
        
        service_discovery.register_service_for_cors('backend', service_info)
        cors_config = service_discovery.get_service_cors_config('backend')
        
        assert cors_config is not None
        assert cors_config['service_id'] == 'netra-backend'
        assert cors_config['supports_cross_service'] is True


class TestHealthMonitorEnhancements:
    """Test enhanced health monitoring functionality."""
    
    @pytest.fixture
    def health_monitor(self):
        """Create test health monitor."""
        return HealthMonitor(check_interval=1)
    
    @pytest.fixture
    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
            yield discovery
    
    def test_service_discovery_integration(self, health_monitor, service_discovery):
        """Test health monitor integrates with service discovery."""
        health_monitor.set_service_discovery(service_discovery)
        
        assert hasattr(health_monitor, '_service_discovery')
        assert health_monitor._service_discovery is service_discovery
    
    def test_cross_service_health_status(self, health_monitor, service_discovery):
        """Test cross-service health status reporting."""
        health_monitor.set_service_discovery(service_discovery)
        
        # Register a test service
        health_monitor.register_service(
            "backend", 
            lambda: True,  # Always healthy
            grace_period_seconds=30
        )
        
        status_report = health_monitor.get_cross_service_health_status()
        
        assert 'services' in status_report
        assert 'cross_service_integration' in status_report
        assert status_report['cross_service_integration']['service_discovery_active'] is True
    
    def test_cross_service_connectivity_verification(self, health_monitor, service_discovery):
        """Test cross-service connectivity verification."""
        # Set up service discovery with auth token
        service_discovery.set_cross_service_auth_token("test-token")
        health_monitor.set_service_discovery(service_discovery)
        
        # Mock the accessibility check to return success
        with patch.object(health_monitor, '_check_service_origin_accessibility', return_value=True):
            connectivity_ok = health_monitor.verify_cross_service_connectivity()
            assert connectivity_ok is True
    
    def test_health_status_cross_service_updates(self):
        """Test health status cross-service status updates."""
        from datetime import datetime
        
        status = HealthStatus(
            is_healthy=True,
            last_check=datetime.now(),
            consecutive_failures=0,
            startup_time=datetime.now()
        )
        
        # Update cross-service status
        status.update_cross_service_status(cors_enabled=True, service_discovery_active=True)
        
        assert hasattr(status, 'cross_service_status')
        assert status.cross_service_status['cors_enabled'] is True
        assert status.cross_service_status['service_discovery_active'] is True


class TestDevLauncherIntegration:
    """Test dev launcher integration with enhanced features."""
    
    @pytest.fixture
    def launcher_config(self):
        """Create test launcher config."""
        from dev_launcher.config import LauncherConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create required directory structure for LauncherConfig validation
            project_root = Path(temp_dir)
            (project_root / "app").mkdir()
            (project_root / "dev_launcher").mkdir()
            (project_root / "frontend").mkdir()
            (project_root / "auth_service").mkdir()
            
            # Create minimal required files
            (project_root / "app" / "__init__.py").touch()
            (project_root / "app" / "main.py").touch()
            
            config = LauncherConfig(project_root=project_root)
            config.load_secrets = False
            config.verbose = False
            config.silent_mode = True
            yield config
    
    def test_cors_environment_variable_setup(self, launcher_config):
        """Test CORS environment variables are set correctly."""
        import os
        
        # Clear CORS_ORIGINS first to test default setting
        original_cors = os.environ.get('CORS_ORIGINS')
        if 'CORS_ORIGINS' in os.environ:
            del os.environ['CORS_ORIGINS']
        
        try:
            launcher = DevLauncher(launcher_config)
            
            # Force cache miss to trigger environment setup
            launcher.cache_manager.invalidate_environment_cache()
            
            # Trigger environment check which sets defaults
            launcher.check_environment()
            
            # Check that CORS_ORIGINS is set to wildcard for development
            assert os.environ.get('CORS_ORIGINS') == '*'
        finally:
            # Restore original value
            if original_cors is not None:
                os.environ['CORS_ORIGINS'] = original_cors
    
    def test_cross_service_auth_token_setup(self, launcher_config):
        """Test cross-service auth token is set up during launcher initialization."""
        import os
        
        # Clear existing token to test generation
        original_token = os.environ.get('CROSS_SERVICE_AUTH_TOKEN')
        if 'CROSS_SERVICE_AUTH_TOKEN' in os.environ:
            del os.environ['CROSS_SERVICE_AUTH_TOKEN']
        
        try:
            launcher = DevLauncher(launcher_config)
            
            # Force cache miss to trigger environment setup
            launcher.cache_manager.invalidate_environment_cache()
            
            # Trigger environment check which sets up tokens
            launcher.check_environment()
            
            # Check that cross-service auth token is generated
            token = os.environ.get('CROSS_SERVICE_AUTH_TOKEN')
            assert token is not None
            assert len(token) > 10  # Should be a meaningful token
            
            # Verify it's stored in service discovery too
            stored_token = launcher.service_discovery.get_cross_service_auth_token()
            assert stored_token == token
        finally:
            # Restore original value
            if original_token is not None:
                os.environ['CROSS_SERVICE_AUTH_TOKEN'] = original_token
    
    def test_service_discovery_integration_in_launcher(self, launcher_config):
        """Test service discovery is properly integrated in launcher."""
        launcher = DevLauncher(launcher_config)
        
        assert launcher.service_discovery is not None
        assert hasattr(launcher.service_discovery, 'get_all_service_origins')
        assert hasattr(launcher.service_discovery, 'get_cross_service_auth_token')


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_cors_service_discovery_flow(self):
        """Test complete CORS + service discovery flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up service discovery
            service_discovery = ServiceDiscovery(Path(temp_dir))
            service_discovery.write_backend_info(8000)
            service_discovery.write_frontend_info(3000)
            service_discovery.set_cross_service_auth_token("test-token-123")
            
            # Create FastAPI app with CORS middleware
            app = FastAPI()
            
            @app.get("/api/test")
            async def test_endpoint():
                return {"status": "ok", "service": "backend"}
            
            # Add enhanced CORS middleware
            cors_middleware = CustomCORSMiddleware(
                app,
                service_discovery=service_discovery,
                enable_metrics=True
            )
            app.add_middleware(type(cors_middleware), **{
                'service_discovery': service_discovery,
                'enable_metrics': True
            })
            
            # Test with TestClient
            with TestClient(app) as client:
                # Test preflight request
                response = client.options(
                    "/api/test",
                    headers={"Origin": "http://localhost:3000"}
                )
                assert response.status_code == 200
                assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
                
                # Test actual request
                response = client.get(
                    "/api/test",
                    headers={"Origin": "http://localhost:3000"}
                )
                assert response.status_code == 200
                assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
                assert response.json()["status"] == "ok"
    
    @pytest.mark.asyncio 
    async def test_health_monitoring_with_cross_service_features(self):
        """Test health monitoring with cross-service features enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up components
            service_discovery = ServiceDiscovery(Path(temp_dir))
            service_discovery.write_backend_info(8000)
            service_discovery.set_cross_service_auth_token("test-token")
            
            health_monitor = HealthMonitor(check_interval=0.1)
            health_monitor.set_service_discovery(service_discovery)
            
            # Register a service
            health_monitor.register_service("backend", lambda: True)
            health_monitor.mark_service_ready("backend")
            
            # Get status report
            status = health_monitor.get_cross_service_health_status()
            
            assert status['services']['backend']['ready_confirmed'] is True
            assert status['cross_service_integration']['service_discovery_active'] is True
            
            # Test connectivity verification with mocked requests
            with patch.object(health_monitor, '_check_service_origin_accessibility', return_value=True):
                connectivity_ok = health_monitor.verify_cross_service_connectivity()
                assert connectivity_ok is True


@pytest.mark.integration
class TestRealServiceIntegration:
    """Tests that require actual service instances (optional, marked as integration)."""
    
    @pytest.mark.skipif(True, reason="Requires running services - enable for full integration testing")
    def test_real_cors_with_running_services(self):
        """Test CORS with actual running services."""
        # This test would require actual running backend/frontend services
        # Enable when doing full integration testing
        pass
    
    @pytest.mark.skipif(True, reason="Requires running services - enable for full integration testing") 
    def test_real_health_checks_with_services(self):
        """Test health checks with actual running services."""
        # This test would require actual running services
        # Enable when doing full integration testing
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])