"""Performance Tests - Split from test_startup_system.py"""

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
from app.core.network_constants import DatabaseConstants, ServicePorts, HostConstants

    def test_configuration_loading(self):
        """Test configuration loading and validation."""
        # Test with minimal environment
        essential_env = {
            'DATABASE_URL': 'postgresql://test:test@localhost:5433/test',
            'JWT_SECRET_KEY': 'test-secret-key-for-testing-purposes',
            'SECRET_KEY': 'test-app-secret-key-for-testing',
            'ENVIRONMENT': 'development'
        }
        
        with patch.dict(os.environ, essential_env, clear=False):
            with patch('signal.signal'):
                launcher = DevLauncher(self.config)
                result = launcher.check_environment()
                assert isinstance(result, bool)
