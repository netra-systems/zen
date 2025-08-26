"""Auth Tests - Split from test_cross_service_integration.py"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response

from dev_launcher.config import LauncherConfig
from dev_launcher.health_monitor import HealthMonitor, HealthStatus, ServiceState
from dev_launcher.launcher import DevLauncher
from dev_launcher.service_discovery import ServiceDiscovery
from netra_backend.app.core.middleware_setup import (
    setup_cors_middleware,
)
from fastapi.middleware.cors import CORSMiddleware


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

    def test_cross_service_auth_token_generation(self, service_discovery):
        """Test cross-service auth token generation."""
        # Initially no token
        assert service_discovery.get_cross_service_auth_token() is None
        
        # Set token
        test_token = "test-token-12345"
        service_discovery.set_cross_service_auth_token(test_token)
        
        # Verify token retrieval
        assert service_discovery.get_cross_service_auth_token() == test_token

    def test_cross_service_auth_token_setup(self, launcher_config):
        """Test cross-service auth token is set up during launcher initialization."""
        
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
