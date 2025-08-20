"""Utilities Tests - Split from test_startup_system.py"""

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

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = LauncherConfig(
            backend_port=8000,
            frontend_port=3000,
            project_root=Path(self.temp_dir),
            verbose=False,
            no_browser=True
        )
