"""Core_1 Tests - Split from test_cross_service_integration.py"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response
from netra_backend.app.core.middleware_setup import CustomCORSMiddleware, setup_cors_middleware
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.health_monitor import HealthMonitor, HealthStatus, ServiceState
from dev_launcher.launcher import DevLauncher
from datetime import datetime
from dev_launcher.config import LauncherConfig
import os
import os


class TestSyntaxFix:
    """Test class for orphaned methods"""

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

    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
            yield discovery

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

    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
            yield discovery

    def health_monitor(self):
        """Create test health monitor."""
        return HealthMonitor(check_interval=1)

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

    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
            yield discovery

    def health_monitor(self):
        """Create test health monitor."""
        return HealthMonitor(check_interval=1)

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

    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
            yield discovery

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

    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
            yield discovery

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

    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
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

    def test_real_cors_with_running_services(self):
        """Test CORS with actual running services."""
        # This test would require actual running backend/frontend services
        # Enable when doing full integration testing
        pass

    def test_real_health_checks_with_services(self):
        """Test health checks with actual running services."""
        # This test would require actual running services
        # Enable when doing full integration testing
        pass

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
