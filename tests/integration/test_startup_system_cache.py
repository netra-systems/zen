"""Cache Tests - Split from test_startup_system.py"""

import os
import pytest
import asyncio
import tempfile
import time
from unittest.mock import patch
from pathlib import Path
from typing import Dict, Any
from dev_launcher.database_connector import DatabaseConnector, DatabaseType, ConnectionStatus
from dev_launcher.environment_validator import EnvironmentValidator, ValidationResult
from dev_launcher.launcher import DevLauncher
from dev_launcher.config import LauncherConfig
from netra_backend.app.core.network_constants import DatabaseConstants, ServicePorts, HostConstants


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def test_redis_url_building(self):
        """Test Redis URL building with constants.""" 
        connector = DatabaseConnector(use_emoji=False)
        
        # Test without existing REDIS_URL
        with patch.dict(os.environ, {
            'REDIS_HOST': 'testhost',
            'REDIS_PORT': '6380',
            'REDIS_PASSWORD': 'testpass',
            'REDIS_DB': '2'
        }, clear=False):
            # Remove REDIS_URL if it exists
            if 'REDIS_URL' in os.environ:
                del os.environ['REDIS_URL']
                
            url = connector._construct_redis_url_from_env()
            expected = "redis://:testpass@testhost:6380/2"
            assert url == expected
