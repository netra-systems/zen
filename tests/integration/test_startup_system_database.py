"""Database Tests - Split from test_startup_system.py"""

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

    def test_database_url_validation(self):
        """Test database URL validation."""
        validator = EnvironmentValidator()
        
        # Test valid PostgreSQL URL
        valid_url = "postgresql://user:pass@localhost:5433/db"
        result = validator._validate_database_url(valid_url)
        assert result.is_valid
        assert len(result.errors) == 0
        
        # Test invalid URL  
        invalid_url = "invalid-url"
        result = validator._validate_database_url(invalid_url)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_database_constants(self):
        """Test database constants."""
        assert DatabaseConstants.POSTGRES_SCHEME == "postgresql"
        assert DatabaseConstants.POSTGRES_ASYNC_SCHEME == "postgresql+asyncpg"
        assert DatabaseConstants.REDIS_SCHEME == "redis"
        assert DatabaseConstants.CLICKHOUSE_SCHEME == "clickhouse"
