"""Integration Tests - Split from test_cross_service_integration.py"""

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
from datetime import datetime
from dev_launcher.config import LauncherConfig
import os
import os

    def health_monitor(self):
        """Create test health monitor."""
        return HealthMonitor(check_interval=1)

    def test_service_discovery_integration(self, health_monitor, service_discovery):
        """Test health monitor integrates with service discovery."""
        health_monitor.set_service_discovery(service_discovery)
        
        assert hasattr(health_monitor, '_service_discovery')
        assert health_monitor._service_discovery is service_discovery

    def test_service_discovery_integration_in_launcher(self, launcher_config):
        """Test service discovery is properly integrated in launcher."""
        launcher = DevLauncher(launcher_config)
        
        assert launcher.service_discovery is not None
        assert hasattr(launcher.service_discovery, 'get_all_service_origins')
        assert hasattr(launcher.service_discovery, 'get_cross_service_auth_token')
