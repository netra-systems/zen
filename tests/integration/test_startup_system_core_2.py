"""Core_2 Tests - Split from test_startup_system.py"""

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

    def test_connection_status_tracking(self):
        """Test connection status tracking."""
        connector = DatabaseConnector(use_emoji=False)
        
        status = connector.get_connection_status()
        assert isinstance(status, dict)
        
        for name, info in status.items():
            assert 'type' in info
            assert 'status' in info 
            assert 'failure_count' in info
            assert 'retry_count' in info

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

    def test_environment_check_integration(self):
        """Test environment checking integration."""
        with patch('signal.signal'):
            launcher = DevLauncher(self.config)
            
            # Should be able to run environment check
            # This tests the integration between launcher and environment validator
            result = launcher.check_environment()
            assert isinstance(result, bool)

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
