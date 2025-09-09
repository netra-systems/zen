from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Auth Tests - Split from test_cross_service_integration.py"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

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
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


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
        
        # Use SSOT environment access per CLAUDE.md
        env = get_env()
        
        # Clear existing token to test generation
        original_token = env.get('CROSS_SERVICE_AUTH_TOKEN')
        if original_token:
            env.remove('CROSS_SERVICE_AUTH_TOKEN')
        
        try:
            launcher = DevLauncher(launcher_config)
            
            # Force cache miss to trigger environment setup
            launcher.cache_manager.clear()
            
            # Trigger environment check which sets up tokens
            launcher.check_environment()
            
            # Check that cross-service auth token is generated via SSOT environment
            token = env.get('CROSS_SERVICE_AUTH_TOKEN')
            assert token is not None, "Cross-service auth token should be generated during environment check"
            assert len(token) > 10, f"Token should be meaningful (got length {len(token) if token else 0})"
            
            # Verify it's stored in service discovery too
            stored_token = launcher.service_discovery.get_cross_service_auth_token()
            assert stored_token == token, f"Service discovery token ({stored_token}) should match environment token ({token})"
        finally:
            # Restore original value using SSOT environment
            if original_token is not None:
                env.set('CROSS_SERVICE_AUTH_TOKEN', original_token, source="test_restore")
