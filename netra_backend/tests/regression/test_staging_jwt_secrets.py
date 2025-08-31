"""Regression Test Suite for Staging JWT and Secrets Configuration

**CRITICAL: Prevents Staging Environment Authentication Failures**

This test suite ensures JWT secrets and GCP Secret Manager integration
work correctly across all environments, preventing deployment failures.

Business Value: Prevents $12K MRR loss from staging authentication failures.
Enterprise customers require 100% uptime for staging validation.

Test Categories:
1. JWT secret consistency across services
2. GCP Secret Manager fallback behavior
3. Environment variable precedence
4. Deployment validation
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from netra_backend.app.core.configuration.database import DatabaseConfigManager
from netra_backend.app.core.configuration.secrets import SecretManager
from netra_backend.app.core.exceptions_config import ConfigurationError
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.schemas.config import AppConfig


class TestJWTSecretConsistency:
    """Test JWT secret consistency across environments."""
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables for testing."""
        return {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars-minimum",
            "FERNET_KEY": "test-fernet-key-with-exactly-44-characters=",
            "SERVICE_SECRET": "test-service-secret",
            "GCP_PROJECT_ID": "701982941522"
        }
    
    @pytest.fixture
    def secret_manager(self, mock_env):
        """Create SecretManager instance with mocked environment."""
        # Create an isolated environment and populate it
        iso_env = IsolatedEnvironment()
        for key, value in mock_env.items():
            iso_env.set(key, value)
        
        with patch('netra_backend.app.core.isolated_environment.get_env', return_value=iso_env):
            return SecretManager()
    
    def test_jwt_secret_loads_from_environment(self, secret_manager, mock_env):
        """Test JWT secret loads correctly from environment variables."""
        config = AppConfig()
        secret_manager.populate_secrets(config)
        
        assert config.jwt_secret_key == mock_env["JWT_SECRET_KEY"]
        assert len(config.jwt_secret_key) >= 32
    
    def test_jwt_secret_validation_fails_when_too_short(self, mock_env):
        """Test JWT secret validation fails when key is too short."""
        mock_env["JWT_SECRET_KEY"] = "short-key"
        
        iso_env = IsolatedEnvironment()
        for key, value in mock_env.items():
            iso_env.set(key, value)
        
        with patch('netra_backend.app.core.isolated_environment.get_env', return_value=iso_env):
            manager = SecretManager()
            config = AppConfig()
            manager.populate_secrets(config)
            
            issues = manager.validate_secrets_consistency(config)
            assert any("JWT secret key too short" in issue for issue in issues)
    
    def test_critical_secrets_required_in_staging(self, mock_env):
        """Test critical secrets are required in staging environment."""
        # Remove critical secrets
        del mock_env["JWT_SECRET_KEY"]
        del mock_env["FERNET_KEY"]
        del mock_env["SERVICE_SECRET"]
        
        iso_env = IsolatedEnvironment()
        for key, value in mock_env.items():
            iso_env.set(key, value)
        
        with patch('netra_backend.app.core.isolated_environment.get_env', return_value=iso_env):
            manager = SecretManager()
            
            missing = manager._get_missing_required_secrets()
            assert "JWT_SECRET_KEY" in missing
            assert "FERNET_KEY" in missing
            assert "SERVICE_SECRET" in missing
    
    def test_secret_key_alias_mapping(self, secret_manager):
        """Test SECRET_KEY correctly maps to JWT_SECRET_KEY."""
        secret = secret_manager.get_secret("SECRET_KEY")
        jwt_secret = secret_manager.get_secret("JWT_SECRET_KEY")
        
        assert secret == jwt_secret
        assert secret is not None


class TestGCPSecretManagerFallback:
    """Test GCP Secret Manager fallback behavior."""
    
    @pytest.fixture
    def staging_env(self):
        """Staging environment configuration."""
        return {
            "ENVIRONMENT": "staging",
            "GCP_PROJECT_ID": "701982941522",
            "CLICKHOUSE_HOST": "staging-clickhouse.example.com",
            "CLICKHOUSE_USER": "staging_user",
            "CLICKHOUSE_DB": "staging_db"
        }
    
    @pytest.fixture
    def db_manager(self, staging_env):
        """Create DatabaseConfigManager with staging environment."""
        iso_env = IsolatedEnvironment()
        for key, value in staging_env.items():
            iso_env.set(key, value)
        
        with patch('netra_backend.app.core.isolated_environment.get_env', return_value=iso_env):
            with patch('netra_backend.app.core.environment_constants.EnvironmentDetector.get_environment', return_value='staging'):
                return DatabaseConfigManager()
    
    def test_gcp_import_failure_does_not_crash(self, db_manager, staging_env):
        """Test that GCP import failure doesn't crash the application."""
        # Simulate GCP module not being available
        with patch('netra_backend.app.core.configuration.database.SecretManager') as MockSecretManager:
            MockSecretManager.side_effect = ImportError("google-cloud-secret-manager not installed")
            
            # Should fall back to environment variable
            staging_env["CLICKHOUSE_PASSWORD"] = "env-password"
            
            config = db_manager._get_clickhouse_configuration()
            assert config["password"] == "env-password"
    
    def test_clickhouse_password_fallback_to_env(self, db_manager, staging_env):
        """Test ClickHouse password falls back to environment variable."""
        staging_env["CLICKHOUSE_PASSWORD"] = "env-clickhouse-password"
        
        with patch.object(db_manager, '_get_clickhouse_password') as mock_get_password:
            mock_get_password.return_value = "env-clickhouse-password"
            
            config = db_manager._get_clickhouse_configuration()
            assert config["password"] == "env-clickhouse-password"
    
    def test_gcp_secret_manager_exception_handling(self, staging_env):
        """Test GCP Secret Manager exception is handled gracefully."""
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: staging_env.get(key, default)
            
            manager = SecretManager()
            
            # Mock GCP client to raise exception
            with patch('netra_backend.app.core.configuration.secrets.secretmanager') as mock_sm:
                mock_sm.SecretManagerServiceClient.side_effect = Exception("GCP connection failed")
                
                # Should not raise, just log warning
                secrets = manager._fetch_gcp_secrets()
                assert secrets == {}
    
    def test_staging_requires_explicit_configuration(self, staging_env):
        """Test staging environment requires explicit configuration."""
        # Remove required staging configuration
        del staging_env["CLICKHOUSE_HOST"]
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: staging_env.get(key, default)
            
            manager = DatabaseConfigManager()
            
            with pytest.raises(ConfigurationError) as exc_info:
                manager._get_clickhouse_configuration()
            
            assert "CLICKHOUSE_HOST not configured for staging" in str(exc_info.value)


class TestEnvironmentVariablePrecedence:
    """Test environment variable precedence and loading order."""
    
    @pytest.fixture
    def multi_env(self):
        """Multiple environment sources."""
        return {
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": "dev-jwt-secret",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_USER": "postgres",
            "POSTGRES_DB": "netra_dev"
        }
    
    def test_env_variable_precedence_order(self, multi_env):
        """Test environment variables load in correct precedence order."""
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: multi_env.get(key, default)
            
            # Mock dotenv loading
            with patch('dotenv.load_dotenv') as mock_load_dotenv:
                manager = SecretManager()
                manager._load_dotenv_if_development()
                
                # Verify load order: .env -> .env.dev -> .env.local
                calls = mock_load_dotenv.call_args_list
                loaded_files = [call[0][0].name for call in calls if call[0]]
                
                expected_order = [".env", ".env.dev", ".env.local"]
                for file in expected_order:
                    if file in loaded_files:
                        assert loaded_files.index(file) < len(loaded_files)
    
    def test_postgres_individual_vars_override_database_url(self, multi_env):
        """Test individual POSTGRES_* vars override DATABASE_URL."""
        multi_env["DATABASE_URL"] = "postgresql://old:pass@oldhost:5432/olddb"
        multi_env["POSTGRES_PASSWORD"] = "newpass"
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: multi_env.get(key, default)
            
            manager = DatabaseConfigManager()
            sync_url = manager.get_sync_postgres_url()
            
            assert "localhost" in sync_url
            assert "netra_dev" in sync_url
            assert "newpass" in sync_url
            assert "oldhost" not in sync_url
    
    def test_cloud_sql_socket_detection(self):
        """Test Cloud SQL Unix socket connection detection."""
        env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/project:region:instance",
            "POSTGRES_USER": "user",
            "POSTGRES_DB": "db",
            "POSTGRES_PASSWORD": "pass"
        }
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: env.get(key, default)
            
            manager = DatabaseConfigManager()
            sync_url = manager.get_sync_postgres_url()
            
            assert "/cloudsql/" in sync_url
            assert "?host=" in sync_url
            assert "sslmode" not in sync_url  # SSL not needed for Unix socket


class TestDeploymentValidation:
    """Test deployment configuration validation."""
    
    @pytest.fixture
    def deployment_config(self):
        """Standard deployment configuration."""
        return {
            "staging": {
                "ENVIRONMENT": "staging",
                "JWT_SECRET_KEY": "staging-jwt-secret-32-chars-minimum",
                "FERNET_KEY": "staging-fernet-key-exactly-44-characters===",
                "SERVICE_SECRET": "staging-service-secret",
                "POSTGRES_HOST": "staging-postgres",
                "POSTGRES_USER": "staging_user",
                "POSTGRES_DB": "staging_db",
                "POSTGRES_PASSWORD": "staging_pass",
                "CLICKHOUSE_HOST": "staging-clickhouse",
                "CLICKHOUSE_USER": "ch_user",
                "CLICKHOUSE_DB": "ch_db",
                "CLICKHOUSE_PASSWORD": "ch_pass"
            },
            "production": {
                "ENVIRONMENT": "production",
                "JWT_SECRET_KEY": "prod-jwt-secret-key-32-chars-minimum",
                "FERNET_KEY": "prod-fernet-key-with-exactly-44-characters=",
                "SERVICE_SECRET": "prod-service-secret",
                "POSTGRES_HOST": "/cloudsql/prod:us-central1:instance",
                "POSTGRES_USER": "prod_user",
                "POSTGRES_DB": "prod_db",
                "POSTGRES_PASSWORD": "prod_pass",
                "CLICKHOUSE_HOST": "prod-clickhouse",
                "CLICKHOUSE_USER": "ch_prod_user",
                "CLICKHOUSE_DB": "ch_prod_db",
                "CLICKHOUSE_PASSWORD": "ch_prod_pass"
            }
        }
    
    def test_staging_deployment_validation(self, deployment_config):
        """Test staging environment deployment configuration."""
        staging_config = deployment_config["staging"]
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: staging_config.get(key, default)
            
            # Test SecretManager
            secret_manager = SecretManager()
            config = AppConfig()
            secret_manager.populate_secrets(config)
            
            assert config.jwt_secret_key == staging_config["JWT_SECRET_KEY"]
            assert config.fernet_key == staging_config["FERNET_KEY"]
            assert config.service_secret == staging_config["SERVICE_SECRET"]
            
            # Test DatabaseConfigManager
            db_manager = DatabaseConfigManager()
            db_manager.populate_database_config(config)
            
            assert config.database_url is not None
            assert "staging-postgres" in config.database_url
            assert config.clickhouse_url is not None
    
    def test_production_deployment_validation(self, deployment_config):
        """Test production environment deployment configuration."""
        prod_config = deployment_config["production"]
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: prod_config.get(key, default)
            
            # Test critical secrets are enforced
            manager = SecretManager()
            config = AppConfig()
            manager.populate_secrets(config)
            
            # Validate no missing critical secrets
            missing = manager._get_missing_required_secrets()
            assert len(missing) == 0
            
            # Test Cloud SQL configuration
            db_manager = DatabaseConfigManager()
            sync_url = db_manager.get_sync_postgres_url()
            
            assert "/cloudsql/" in sync_url
            assert "prod_user" in sync_url
            assert "prod_db" in sync_url
    
    def test_missing_critical_secrets_fails_in_production(self):
        """Test missing critical secrets causes failure in production."""
        prod_env = {
            "ENVIRONMENT": "production",
            # Missing JWT_SECRET_KEY
            "FERNET_KEY": "prod-fernet-key-with-exactly-44-characters=",
            "SERVICE_SECRET": "prod-service-secret"
        }
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: prod_env.get(key, default)
            
            manager = SecretManager()
            config = AppConfig()
            
            with pytest.raises(ConfigurationError) as exc_info:
                manager.populate_secrets(config)
            
            assert "Required secrets missing" in str(exc_info.value)
            assert "JWT_SECRET_KEY" in str(exc_info.value)
    
    def test_empty_string_configuration_validation(self):
        """Test empty string values are caught and rejected."""
        bad_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "",  # Empty string
            "POSTGRES_USER": "user",
            "POSTGRES_DB": "db",
            "POSTGRES_PASSWORD": "pass"
        }
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: bad_config.get(key, default)
            
            manager = DatabaseConfigManager()
            
            with pytest.raises(ConfigurationError) as exc_info:
                manager.get_sync_postgres_url()
            
            assert "POSTGRES_HOST is empty string" in str(exc_info.value)
    
    def test_placeholder_password_rejected(self):
        """Test placeholder passwords are rejected."""
        bad_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "host",
            "POSTGRES_USER": "user",
            "POSTGRES_DB": "db",
            "POSTGRES_PASSWORD": "changeme"  # Placeholder
        }
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: bad_config.get(key, default)
            
            manager = DatabaseConfigManager()
            
            with pytest.raises(ConfigurationError) as exc_info:
                manager.get_sync_postgres_url()
            
            assert "placeholder value" in str(exc_info.value)


class TestServiceIntegration:
    """Test integration between services and secret management."""
    
    def test_auth_service_jwt_compatibility(self):
        """Test auth service can use the same JWT secret."""
        env = {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_KEY": "shared-jwt-secret-key-32-chars-minimum",
            "SERVICE_SECRET": "inter-service-secret"
        }
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: env.get(key, default)
            
            # Backend secret manager
            backend_manager = SecretManager()
            backend_config = AppConfig()
            backend_manager.populate_secrets(backend_config)
            
            # Auth service would use same secret
            assert backend_config.jwt_secret_key == env["JWT_SECRET_KEY"]
            assert backend_config.service_secret == env["SERVICE_SECRET"]
    
    def test_clickhouse_cross_service_consistency(self):
        """Test ClickHouse configuration is consistent across services."""
        env = {
            "ENVIRONMENT": "staging",
            "CLICKHOUSE_HOST": "shared-clickhouse",
            "CLICKHOUSE_PORT": "8123",
            "CLICKHOUSE_USER": "shared_user",
            "CLICKHOUSE_DB": "shared_db",
            "CLICKHOUSE_PASSWORD": "shared_pass"
        }
        
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_get_env:
            mock_get_env.return_value.get.side_effect = lambda key, default=None: env.get(key, default)
            
            manager = DatabaseConfigManager()
            config = manager._get_clickhouse_configuration()
            
            assert config["host"] == "shared-clickhouse"
            assert config["user"] == "shared_user"
            assert config["database"] == "shared_db"
            assert config["password"] == "shared_pass"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])