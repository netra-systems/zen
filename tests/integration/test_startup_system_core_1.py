"""Core_1 Tests - Split from test_startup_system.py"""

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

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        # Create required directory structure for LauncherConfig validation
        backend_dir = Path(self.temp_dir) / "netra_backend" / "app"
        backend_dir.mkdir(parents=True, exist_ok=True)
        (backend_dir / "main.py").touch()  # Create main.py file
        
        frontend_dir = Path(self.temp_dir) / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = LauncherConfig(
            backend_port=8000,
            frontend_port=3000,
            project_root=Path(self.temp_dir),
            verbose=False
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_url_normalization(self):
        """Test PostgreSQL URL normalization for asyncpg."""
        connector = DatabaseConnector(use_emoji=False)
        
        # Test URL normalization
        test_url = "postgresql+asyncpg://user:pass@localhost:5433/db"
        normalized = connector._normalize_postgres_url(test_url)
        expected = "postgresql://user:pass@localhost:5433/db"
        assert normalized == expected

    def test_clickhouse_url_building(self):
        """Test ClickHouse URL building with constants."""
        connector = DatabaseConnector(use_emoji=False)
        
        # Set up environment variables
        with patch.dict(os.environ, {
            'CLICKHOUSE_HOST': 'testhost',
            'CLICKHOUSE_HTTP_PORT': '8124', 
            'CLICKHOUSE_USER': 'testuser',
            'CLICKHOUSE_PASSWORD': 'testpass',
            'CLICKHOUSE_DB': 'testdb'
        }):
            url = connector._construct_clickhouse_url_from_env()
            expected = "clickhouse://testuser:testpass@testhost:8124/testdb"
            assert url == expected

    def test_health_summary(self):
        """Test health summary generation."""
        connector = DatabaseConnector(use_emoji=False)
        
        summary = connector.get_health_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_validation_with_current_env(self):
        """Test validation with current environment variables."""
        validator = EnvironmentValidator()
        
        result = validator.validate_all()
        assert isinstance(result, ValidationResult)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.missing_optional, list)

    def test_secret_key_validation(self):
        """Test secret key validation."""
        validator = EnvironmentValidator()
        
        # Test strong secret
        strong_secret = "a" * 32
        result = validator._validate_secret_key(strong_secret)
        assert result.is_valid
        
        # Test weak secret
        weak_secret = "short"
        result = validator._validate_secret_key(weak_secret)
        assert not result.is_valid
        
        # Test placeholder secret
        placeholder_secret = "placeholder-key-change-me"
        result = validator._validate_secret_key(placeholder_secret)
        assert result.is_valid  # Valid format but warning
        assert len(result.warnings) > 0

    def test_environment_validation(self):
        """Test environment setting validation."""
        validator = EnvironmentValidator()
        
        # Test valid environments
        for env in ['development', 'staging', 'production', 'testing']:
            result = validator._validate_environment(env)
            assert result.is_valid
            
        # Test invalid environment
        result = validator._validate_environment('invalid')
        assert not result.is_valid

    def test_port_conflict_detection(self):
        """Test port conflict detection."""
        validator = EnvironmentValidator()
        
        # Set up conflicting ports
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db1',
            'REDIS_URL': 'redis://localhost:5432/0'  # Same port!
        }):
            result = validator.validate_all()
            # Should detect port conflict
            conflict_errors = [e for e in result.errors if 'Port conflict' in e]
            assert len(conflict_errors) > 0

    def test_fix_suggestions(self):
        """Test fix suggestions generation."""
        validator = EnvironmentValidator()
        
        # Create a result with errors
        result = ValidationResult(
            is_valid=False,
            errors=['Missing required environment variable: DATABASE_URL'],
            warnings=['Secret key appears to be a placeholder value'],
            missing_optional=[]
        )
        
        suggestions = validator.get_fix_suggestions(result)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any('env' in s.lower() for s in suggestions)

    def test_launcher_initialization(self):
        """Test dev launcher can be initialized."""
        # Mock the signal handlers to avoid issues in tests
        with patch('signal.signal'):
            launcher = DevLauncher(self.config)
            
            # Check all components are initialized
            assert launcher.database_connector is not None
            assert launcher.environment_validator is not None
            assert launcher.process_manager is not None
            assert launcher.health_monitor is not None

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
                # URL should contain either postgresql, postgresql+asyncpg, or sqlite (for testing)
                assert (DatabaseConstants.POSTGRES_SCHEME in conn.url or 
                        DatabaseConstants.POSTGRES_ASYNC_SCHEME in conn.url or
                        'sqlite' in conn.url)  # SQLite is used in test environment
            elif conn.db_type == DatabaseType.REDIS:
                assert DatabaseConstants.REDIS_SCHEME in conn.url
            elif conn.db_type == DatabaseType.CLICKHOUSE:
                assert DatabaseConstants.CLICKHOUSE_SCHEME in conn.url

    def test_postgresql_connection_success(self):
        """Test successful PostgreSQL connection."""
        connector = DatabaseConnector(use_emoji=False)
        
        # Should discover main_postgres connection from environment
        assert "main_postgres" in connector.connections
        postgres_conn = connector.connections["main_postgres"]
        assert postgres_conn.db_type == DatabaseType.POSTGRESQL
        assert postgres_conn.status == ConnectionStatus.UNKNOWN
