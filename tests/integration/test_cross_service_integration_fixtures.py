"""Fixtures Tests - Split from test_cross_service_integration.py"""

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

    def health_monitor(self):
        """Create test health monitor."""
        return HealthMonitor(check_interval=1)

    def service_discovery(self):
        """Create test service discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            discovery = ServiceDiscovery(Path(temp_dir))
            discovery.write_backend_info(8000)
            discovery.write_frontend_info(3000)
            yield discovery

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
