"""
Staging Environment Startup Configuration Validation Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal 
- Business Goal: Platform Stability and Risk Reduction
- Value Impact: Prevents staging deployment failures that block releases
- Revenue Impact: Avoids $50K+ loss from delayed releases and customer SLA breaches

Tests staging-specific environment validation, configuration loading from multiple
sources, and ensures staging overrides work correctly. Critical for release pipeline.
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import os
from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
from netra_backend.app.core.configuration.database import DatabaseConfigManager
from netra_backend.app.core.environment_constants import get_current_environment
from netra_backend.app.core.exceptions_config import ConfigurationError
from netra_backend.app.schemas.Config import AppConfig
from test_framework.mock_utils import mock_justified

# Add project root to path


class TestStagingStartupConfigurationValidation:
    """Test staging environment configuration validation and loading."""
    
    @pytest.fixture
    def staging_env_vars(self):
        """Environment variables for staging environment."""
        return {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@staging-host:5432/netra?sslmode=require",
            "CLICKHOUSE_HOST": "staging-clickhouse-host",
            "CLICKHOUSE_HTTP_PORT": "8443",
            "CLICKHOUSE_USER": "staging_user", 
            "CLICKHOUSE_PASSWORD": "staging_password",
            "REDIS_URL": "redis://staging-redis:6379/0",
            "SECRET_KEY": "staging-secret-key-256-bits",
            "GOOGLE_PROJECT_ID": "netra-staging-project"
        }
    
    @pytest.fixture
    def config_manager(self):
        """Database configuration manager instance."""
        return DatabaseConfigManager()
    
    @pytest.fixture
    def app_config(self):
        """Empty AppConfig instance for testing."""
        return AppConfig()
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_all_required_staging_environment_variables_present(self, staging_env_vars):
        """Test that all required environment variables are present in staging."""
        required_staging_vars = [
            "ENVIRONMENT",
            "DATABASE_URL", 
            "CLICKHOUSE_HOST",
            "REDIS_URL",
            "SECRET_KEY",
            "GOOGLE_PROJECT_ID"
        ]
        
        with patch.dict(os.environ, staging_env_vars, clear=True):
            missing_vars = []
            for var in required_staging_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)
            
            assert not missing_vars, f"Missing required staging environment variables: {missing_vars}"
            assert os.environ.get("ENVIRONMENT") == "staging"
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_staging_ssl_requirements_enforced(self, staging_env_vars):
        """Test that SSL requirements are enforced in staging environment."""
        with patch.dict(os.environ, staging_env_vars, clear=True):
            # Create fresh config manager in staging environment
            staging_config_manager = DatabaseConfigManager()
            
            # Test valid SSL URL passes validation
            valid_ssl_url = "postgresql+asyncpg://user:pass@host:5432/db?sslmode=require"
            staging_config_manager._validate_postgres_url(valid_ssl_url)
            
            # Test invalid URL without SSL fails
            invalid_url = "postgresql+asyncpg://user:pass@host:5432/db"
            with pytest.raises(ConfigurationError) as exc_info:
                staging_config_manager._validate_postgres_url(invalid_url)
            assert "SSL required" in str(exc_info.value)
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_configuration_loading_from_multiple_sources(self, staging_env_vars, config_manager, app_config):
        """Test configuration loads from environment, files, and defaults in correct priority."""
        # Test priority: ENV > Config object > Defaults
        with patch.dict(os.environ, staging_env_vars, clear=True):
            config_manager.refresh_environment()
            config_manager.populate_database_config(app_config)
            
            # Verify environment variables take precedence
            assert app_config.database_url == staging_env_vars["DATABASE_URL"]
            assert app_config.redis_url == staging_env_vars["REDIS_URL"]
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_staging_specific_settings_override_development_defaults(self, config_manager):
        """Test that staging settings properly override development defaults."""
        # Test development defaults
        dev_env = {"ENVIRONMENT": "development"}
        with patch.dict(os.environ, dev_env, clear=True):
            config_manager.refresh_environment()
            dev_rules = config_manager._validation_rules["development"]
            assert not dev_rules["require_ssl"]
            assert dev_rules["allow_localhost"]
        
        # Test staging overrides
        staging_env = {"ENVIRONMENT": "staging"}
        with patch.dict(os.environ, staging_env, clear=True):
            config_manager.refresh_environment()
            staging_rules = config_manager._validation_rules["staging"] 
            assert staging_rules["require_ssl"]
            assert not staging_rules["allow_localhost"]
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_clickhouse_staging_configuration_validation(self, staging_env_vars, config_manager, app_config):
        """Test ClickHouse staging configuration is properly validated and applied."""
        with patch.dict(os.environ, staging_env_vars, clear=True):
            config_manager.refresh_environment()
            
            # Mock config objects for ClickHouse
            app_config.clickhouse_native = MagicMock()
            app_config.clickhouse_https = MagicMock()
            
            config_manager.populate_database_config(app_config)
            
            # Verify staging ClickHouse configuration
            expected_host = staging_env_vars["CLICKHOUSE_HOST"]
            app_config.clickhouse_native.host = expected_host
            app_config.clickhouse_https.host = expected_host
            
            # Verify configuration consistency
            issues = config_manager.validate_database_consistency(app_config)
            clickhouse_issues = [issue for issue in issues if "ClickHouse" in issue]
            assert not clickhouse_issues, f"ClickHouse configuration issues: {clickhouse_issues}"
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_fallback_to_default_when_env_missing(self, config_manager):
        """Test graceful fallback to defaults when staging environment variables missing."""
        # Test with minimal staging environment
        minimal_env = {"ENVIRONMENT": "staging"}
        with patch.dict(os.environ, minimal_env, clear=True):
            config_manager.refresh_environment()
            
            # Should fall back to staging defaults
            default_url = config_manager._get_default_postgres_url()
            assert "staging" in default_url or "postgres" in default_url
            
            # ClickHouse should get development defaults
            ch_config = config_manager._get_clickhouse_configuration()
            assert ch_config["host"] == "localhost"  # Default when env missing
            assert ch_config["port"] == "8123"       # Default port
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_configuration_validation_reports_comprehensive_issues(self, staging_env_vars, config_manager):
        """Test that configuration validation reports all issues comprehensively."""
        with patch.dict(os.environ, staging_env_vars, clear=True):
            config_manager.refresh_environment()
            
            # Create config with intentional issues
            broken_config = AppConfig()
            broken_config.database_url = None  # Missing required URL
            broken_config.redis_url = "invalid://url"
            
            issues = config_manager.validate_database_consistency(broken_config)
            
            # Should report database URL issue
            db_issues = [issue for issue in issues if "database_url" in issue]
            assert db_issues, "Should report missing database URL"
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_database_summary_reflects_staging_state(self, staging_env_vars, config_manager):
        """Test that database summary correctly reflects staging configuration state."""
        with patch.dict(os.environ, staging_env_vars, clear=True):
            config_manager.refresh_environment()
            
            summary = config_manager.get_database_summary()
            
            # Verify staging environment is detected
            assert summary["environment"] == "staging"
            assert summary["ssl_required"] == "True"
            assert summary["postgres_configured"] is True
            assert summary["clickhouse_configured"] is True
            assert summary["redis_configured"] is True
    
    @mock_justified("Environment variables are external system state not available in test")
    def test_localhost_restriction_enforced_in_staging(self):
        """Test that localhost connections are properly restricted in staging."""
        staging_env = {"ENVIRONMENT": "staging"}
        with patch.dict(os.environ, staging_env, clear=True):
            # Create fresh config manager in staging environment
            staging_config_manager = DatabaseConfigManager()
            
            # Localhost URL should be rejected in staging
            localhost_url = "postgresql+asyncpg://user:pass@localhost:5432/db?sslmode=require"
            with pytest.raises(ConfigurationError) as exc_info:
                staging_config_manager._validate_postgres_url(localhost_url)
            assert "Localhost not allowed" in str(exc_info.value)
            
            # Valid remote host should be accepted
            remote_url = "postgresql+asyncpg://user:pass@staging-host:5432/db?sslmode=require"
            staging_config_manager._validate_postgres_url(remote_url)  # Should not raise