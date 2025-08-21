"""Core_3 Tests - Split from test_startup_system.py"""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from dev_launcher.config import LauncherConfig
from dev_launcher.database_connector import (
    ConnectionStatus,
    DatabaseConnector,
    DatabaseType,
)
from dev_launcher.environment_validator import EnvironmentValidator, ValidationResult
from dev_launcher.launcher import DevLauncher
from netra_backend.app.core.network_constants import (
    DatabaseConstants,
    HostConstants,
    ServicePorts,
)


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def test_error_handling(self):
        """Test error handling in startup system."""
        with patch('signal.signal'):
            launcher = DevLauncher(self.config)
            
            # Test that methods don't crash with invalid input
            try:
                launcher._print("🔍", "TEST", "Testing error handling")
                # Should not raise exception
                assert True
            except Exception:
                pytest.fail("Basic printing should not raise exception")

    def test_service_ports(self):
        """Test service port constants."""
        assert ServicePorts.POSTGRES_DEFAULT == 5432
        assert ServicePorts.POSTGRES_TEST == 5433
        assert ServicePorts.REDIS_DEFAULT == 6379
        assert ServicePorts.CLICKHOUSE_HTTP == 8123
        assert ServicePorts.BACKEND_DEFAULT == 8000
        assert ServicePorts.FRONTEND_DEFAULT == 3000

    def test_host_constants(self):
        """Test host constants."""
        assert HostConstants.LOCALHOST == "localhost"
        assert HostConstants.LOCALHOST_IP == "127.0.0.1"
        assert HostConstants.ANY_HOST == "0.0.0.0"

    def test_database_constants(self):
        """Test database constants."""
        assert DatabaseConstants.POSTGRES_SCHEME == "postgresql"
        assert DatabaseConstants.POSTGRES_ASYNC_SCHEME == "postgresql+asyncpg"
        assert DatabaseConstants.REDIS_SCHEME == "redis"
        assert DatabaseConstants.CLICKHOUSE_SCHEME == "clickhouse"

    def test_url_building(self):
        """Test URL building with constants."""
        # Test PostgreSQL URL building
        url = DatabaseConstants.build_postgres_url(
            user="test_user",
            password="test_pass", 
            host=HostConstants.LOCALHOST,
            port=ServicePorts.POSTGRES_TEST,
            database="test_db",
            async_driver=True
        )
        expected = "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_db"
        assert url == expected
        
        # Test Redis URL building
        redis_url = DatabaseConstants.build_redis_url(
            host=HostConstants.LOCALHOST,
            port=ServicePorts.REDIS_DEFAULT,
            database=DatabaseConstants.REDIS_DEFAULT_DB
        )
        expected = "redis://localhost:6379/0"
        assert redis_url == expected

    def test_environment_validation_real(self):
        """Test environment validation with real environment."""
        validator = EnvironmentValidator()
        
        result = validator.validate_all()
        
        # Should complete and return valid result
        assert isinstance(result, ValidationResult)
        
        # Print results for debugging
        validator.print_validation_summary(result)
        
        # Environment should be mostly valid (may have warnings)
        assert isinstance(result.is_valid, bool)

    def test_startup_constants_consistency(self):
        """Test that startup system uses constants consistently."""
        connector = DatabaseConnector(use_emoji=False)
        
        # Check that discovered connections use proper constants
        for name, conn in connector.connections.items():
            if conn.db_type == DatabaseType.POSTGRESQL:
                # URL should contain either postgresql or postgresql+asyncpg scheme
                assert DatabaseConstants.POSTGRES_SCHEME in conn.url or DatabaseConstants.POSTGRES_ASYNC_SCHEME in conn.url
            elif conn.db_type == DatabaseType.REDIS:
                assert DatabaseConstants.REDIS_SCHEME in conn.url
            elif conn.db_type == DatabaseType.CLICKHOUSE:
                assert DatabaseConstants.CLICKHOUSE_SCHEME in conn.url
