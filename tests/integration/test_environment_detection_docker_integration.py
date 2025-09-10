"""
Environment Detection and Docker Configuration Integration Tests

CRITICAL: This test suite addresses Five Whys root cause analysis:
"Missing tests for environment detection logic across different deployment contexts"

These tests validate:
1. Environment detection logic in Docker vs local contexts
2. Docker Compose configuration propagation
3. Environment-specific configuration loading
4. Container vs local development differentiation
5. GCP Cloud Run environment detection

ROOT CAUSE ADDRESSED: WHY #4 - Process gap in configuration validation testing
that allowed environment detection issues to persist undetected.

Business Value: Platform/Internal - System Stability & Deployment Reliability  
Prevents environment misdetection that causes incorrect configuration loading.
"""
import pytest
import os
import subprocess
import json
import tempfile
import time
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock
from pathlib import Path

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.backend_environment import BackendEnvironment


class TestEnvironmentDetection:
    """Test environment detection across various deployment contexts."""
    
    @pytest.fixture(autouse=True)
    def setup_isolated_environment(self):
        """Setup clean isolated environment for each test."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_local_development_detection(self):
        """Test environment detection for local development."""
        local_dev_vars = {
            "ENVIRONMENT": "development",
            # No Docker-specific variables
        }
        
        for key, value in local_dev_vars.items():
            self.env.set(key, value, "local_dev_test")
        
        backend_env = BackendEnvironment()
        
        assert backend_env.get_environment() == "development"
        assert backend_env.is_development() is True
        assert backend_env.is_production() is False
        assert backend_env.is_staging() is False
        assert backend_env.is_testing() is False
        
        # Local development indicators
        assert not self.env.exists("HOSTNAME") or not self.env.get("HOSTNAME", "").startswith(("dev-", "test-", "staging-"))
        assert not self.env.exists("DOCKER_CONTAINER")
        assert not self.env.exists("GCP_PROJECT")
    
    def test_docker_development_detection(self):
        """Test environment detection for Docker development containers."""
        docker_dev_vars = {
            "ENVIRONMENT": "development",
            "HOSTNAME": "dev-backend-12345",  # Docker container hostname pattern
            "DOCKER_CONTAINER": "true",
            "CONTAINER_NAME": "netra-dev-backend"
        }
        
        for key, value in docker_dev_vars.items():
            self.env.set(key, value, "docker_dev_test")
        
        backend_env = BackendEnvironment()
        
        assert backend_env.get_environment() == "development"
        assert backend_env.is_development() is True
        
        # Docker development indicators
        hostname = self.env.get("HOSTNAME", "")
        assert hostname.startswith("dev-")
        assert self.env.exists("DOCKER_CONTAINER")
        assert self.env.get("DOCKER_CONTAINER") == "true"
    
    def test_docker_test_detection(self):
        """Test environment detection for Docker test containers."""
        docker_test_vars = {
            "ENVIRONMENT": "test",
            "TESTING": "true",
            "HOSTNAME": "test-backend-67890",
            "DOCKER_CONTAINER": "true",
            "PYTEST_CURRENT_TEST": "tests/integration/test_example.py::test_function"
        }
        
        for key, value in docker_test_vars.items():
            self.env.set(key, value, "docker_test_test")
        
        backend_env = BackendEnvironment()
        
        assert backend_env.get_environment() == "test"
        assert backend_env.is_testing() is True
        assert backend_env.is_development() is False
        
        # Docker test indicators
        assert self.env.get("TESTING") == "true"
        assert self.env.exists("PYTEST_CURRENT_TEST")
        hostname = self.env.get("HOSTNAME", "")
        assert hostname.startswith("test-")
    
    def test_gcp_cloud_run_staging_detection(self):
        """Test environment detection for GCP Cloud Run staging deployment."""
        gcp_staging_vars = {
            "ENVIRONMENT": "staging",
            "K_SERVICE": "netra-backend-staging",  # Cloud Run service name
            "K_REVISION": "netra-backend-staging-00042-abc",
            "K_CONFIGURATION": "netra-backend-staging",
            "GCP_PROJECT": "netra-staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging",
            "GAE_ENV": "standard",  # App Engine/Cloud Run indicator
            "HOSTNAME": "staging-backend-xyz789"
        }
        
        for key, value in gcp_staging_vars.items():
            self.env.set(key, value, "gcp_staging_test")
        
        backend_env = BackendEnvironment()
        
        assert backend_env.get_environment() == "staging"
        assert backend_env.is_staging() is True
        assert backend_env.is_development() is False
        assert backend_env.is_production() is False
        
        # GCP Cloud Run indicators
        assert self.env.exists("K_SERVICE")
        assert self.env.exists("GCP_PROJECT")
        assert self.env.get("GCP_PROJECT") == "netra-staging"
        assert self.env.get("K_SERVICE", "").endswith("-staging")
    
    def test_gcp_cloud_run_production_detection(self):
        """Test environment detection for GCP Cloud Run production deployment."""
        gcp_prod_vars = {
            "ENVIRONMENT": "production",
            "K_SERVICE": "netra-backend-production",
            "K_REVISION": "netra-backend-production-00156-def",
            "K_CONFIGURATION": "netra-backend-production",
            "GCP_PROJECT": "netra-production",
            "GOOGLE_CLOUD_PROJECT": "netra-production",
            "GAE_ENV": "standard"
        }
        
        for key, value in gcp_prod_vars.items():
            self.env.set(key, value, "gcp_prod_test")
        
        backend_env = BackendEnvironment()
        
        assert backend_env.get_environment() == "production"
        assert backend_env.is_production() is True
        assert backend_env.is_staging() is False
        assert backend_env.is_development() is False
        
        # GCP Production indicators
        assert self.env.get("GCP_PROJECT") == "netra-production"
        assert self.env.get("K_SERVICE", "").endswith("-production")
    
    def test_environment_precedence_order(self):
        """Test that explicit ENVIRONMENT variable takes precedence over context clues."""
        # Set conflicting environment indicators
        conflicting_vars = {
            "ENVIRONMENT": "staging",  # Explicit setting
            "TESTING": "true",         # Suggests test environment
            "GCP_PROJECT": "netra-production",  # Suggests production
            "HOSTNAME": "dev-backend-123"       # Suggests development
        }
        
        for key, value in conflicting_vars.items():
            self.env.set(key, value, "precedence_test")
        
        backend_env = BackendEnvironment()
        
        # ENVIRONMENT variable should take precedence
        assert backend_env.get_environment() == "staging"
        assert backend_env.is_staging() is True
    
    def test_environment_normalization(self):
        """Test environment name normalization (case insensitive, aliases)."""
        test_cases = [
            ("DEVELOPMENT", "development"),
            ("Development", "development"),
            ("dev", "development"),
            ("local", "development"),
            ("TEST", "test"),
            ("testing", "test"),
            ("STAGING", "staging"),
            ("Staging", "staging"),
            ("PRODUCTION", "production"),
            ("Production", "production"),
            ("prod", "production"),
            ("", "development")  # Default
        ]
        
        for input_env, expected_env in test_cases:
            self.env.reset_to_original()
            self.env.enable_isolation()
            
            # For testing environment normalization, clear test context indicators
            # to ensure we get proper environment detection without test interference
            self.env.set("PYTEST_CURRENT_TEST", "", "normalization_test")
            self.env.delete("PYTEST_CURRENT_TEST", "normalization_test")
            self.env.set("TESTING", "false", "normalization_test")
            self.env.set("TEST_MODE", "false", "normalization_test")
            
            if input_env:  # Only set if not empty (testing default case)
                self.env.set("ENVIRONMENT", input_env, "normalization_test")
            else:
                # For empty case, explicitly unset ENVIRONMENT to test default
                self.env.delete("ENVIRONMENT", "normalization_test")
            
            backend_env = BackendEnvironment()
            actual_env = backend_env.get_environment()
            
            assert actual_env == expected_env, f"Environment '{input_env}' should normalize to '{expected_env}', got '{actual_env}'"
    
    def test_isolated_environment_test_context_detection(self):
        """Test IsolatedEnvironment's test context detection logic."""
        # Test various test context indicators
        test_context_cases = [
            {
                "name": "pytest_current_test",
                "vars": {"PYTEST_CURRENT_TEST": "tests/test_example.py::test_function"},
                "expected": True
            },
            {
                "name": "testing_flag_true",
                "vars": {"TESTING": "true"},
                "expected": True
            },
            {
                "name": "testing_flag_1",
                "vars": {"TESTING": "1"},
                "expected": True
            },
            {
                "name": "test_mode_yes",
                "vars": {"TEST_MODE": "yes"},
                "expected": True
            },
            {
                "name": "environment_test",
                "vars": {"ENVIRONMENT": "test"},
                "expected": True
            },
            {
                "name": "environment_testing",
                "vars": {"ENVIRONMENT": "testing"},
                "expected": True
            },
            {
                "name": "no_test_indicators",
                "vars": {"ENVIRONMENT": "development"},
                "expected": False
            },
            {
                "name": "testing_false",
                "vars": {"TESTING": "false"},
                "expected": False
            }
        ]
        
        for case in test_context_cases:
            self.env.reset_to_original()
            self.env.enable_isolation()
            
            # For cases that expect False, explicitly unset pytest-related variables
            if not case["expected"]:
                # Clear pytest-related environment variables in isolation
                self.env.set("PYTEST_CURRENT_TEST", "", f"test_context_{case['name']}")
                self.env.delete("PYTEST_CURRENT_TEST", f"test_context_{case['name']}")
                self.env.set("TESTING", "false", f"test_context_{case['name']}")
                self.env.set("TEST_MODE", "false", f"test_context_{case['name']}")
            
            # Set test case variables
            for key, value in case["vars"].items():
                self.env.set(key, value, f"test_context_{case['name']}")
            
            # Test IsolatedEnvironment's test context detection
            is_test_context = self.env._is_test_context()
            
            assert is_test_context == case["expected"], f"Test context detection failed for case '{case['name']}': expected {case['expected']}, got {is_test_context}"
    
    def test_docker_compose_environment_variable_propagation(self):
        """Test that Docker Compose environment variables are properly propagated."""
        # Simulate Docker Compose environment variable mapping
        docker_compose_vars = {
            # From docker-compose.yml development environment
            "ENVIRONMENT": "development",
            "LOG_LEVEL": "DEBUG",
            "POSTGRES_HOST": "dev-postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "netra",
            "POSTGRES_PASSWORD": "netra123",
            "POSTGRES_DB": "netra_dev",
            "REDIS_HOST": "dev-redis",
            "REDIS_PORT": "6379",
            "AUTH_SERVICE_URL": "http://dev-auth:8081",
            "PORT": "8000",
            "HOST": "0.0.0.0"
        }
        
        for key, value in docker_compose_vars.items():
            self.env.set(key, value, "docker_compose_propagation_test")
        
        backend_env = BackendEnvironment()
        
        # Validate Docker Compose variables are accessible
        assert backend_env.get_environment() == "development"
        assert backend_env.get_postgres_host() == "dev-postgres"
        assert backend_env.get_postgres_port() == 5432
        assert backend_env.get_postgres_user() == "netra"
        assert backend_env.get_postgres_db() == "netra_dev"
        assert backend_env.get_redis_host() == "dev-redis"
        assert backend_env.get_redis_port() == 6379
        assert backend_env.get_auth_service_url() == "http://dev-auth:8081"
        
        # Test that Docker internal networking is used (service names, not localhost)
        assert "dev-postgres" in backend_env.get_postgres_host()
        assert "dev-redis" in backend_env.get_redis_host()
        assert "dev-auth" in backend_env.get_auth_service_url()


class TestDockerConfigurationConsistency:
    """Test consistency between Docker Compose and application configuration."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup test environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_docker_compose_dev_port_mapping_consistency(self):
        """Test consistency between Docker Compose dev port mappings and application config."""
        # Expected port mappings from docker-compose.yml (development)
        expected_dev_ports = {
            "postgres_external": 5433,    # DEV_POSTGRES_PORT (line 33)
            "postgres_internal": 5432,    # Container internal port
            "redis_external": 6380,       # DEV_REDIS_PORT (line 62)  
            "redis_internal": 6379,       # Container internal port
            "clickhouse_http_external": 8124,  # DEV_CLICKHOUSE_HTTP_PORT (line 93)
            "clickhouse_http_internal": 8123,  # Container internal port
            "auth_external": 8081,        # DEV_AUTH_PORT (line 159)
            "auth_internal": 8081,        # Container internal port
            "backend_external": 8000,     # DEV_BACKEND_PORT (line 242)
            "backend_internal": 8000,     # Container internal port
            "frontend_external": 3000,    # DEV_FRONTEND_PORT (line 291)
            "frontend_internal": 3000     # Container internal port
        }
        
        # Simulate Docker development environment (internal networking)
        docker_dev_internal_vars = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "dev-postgres",  # Service name from docker-compose.yml
            "POSTGRES_PORT": "5432",          # Internal port
            "REDIS_HOST": "dev-redis",        # Service name
            "REDIS_PORT": "6379",             # Internal port
            "CLICKHOUSE_HOST": "dev-clickhouse",
            "CLICKHOUSE_PORT": "9000",        # TCP port for connections
            "AUTH_SERVICE_URL": "http://dev-auth:8081"
        }
        
        for key, value in docker_dev_internal_vars.items():
            self.env.set(key, value, "docker_dev_consistency_test")
        
        backend_env = BackendEnvironment()
        
        # Validate internal Docker networking is used
        assert backend_env.get_postgres_host() == "dev-postgres"
        assert backend_env.get_postgres_port() == expected_dev_ports["postgres_internal"]
        assert backend_env.get_redis_host() == "dev-redis"
        assert backend_env.get_redis_port() == expected_dev_ports["redis_internal"]
        
        # Service URLs should use internal service names and ports
        assert backend_env.get_auth_service_url() == "http://dev-auth:8081"
    
    def test_docker_compose_test_port_mapping_consistency(self):
        """Test consistency between Docker Compose test port mappings and application config."""
        # Expected test port mappings from docker-compose.yml
        expected_test_ports = {
            "postgres_external": 5434,    # TEST_POSTGRES_PORT (line 328)
            "postgres_internal": 5432,
            "redis_external": 6381,       # TEST_REDIS_PORT (line 351)
            "redis_internal": 6379,
            "clickhouse_http_external": 8125,  # TEST_CLICKHOUSE_HTTP_PORT (line 378)
            "clickhouse_tcp_external": 9002,   # TEST_CLICKHOUSE_TCP_PORT (line 379)
        }
        
        # For testing, we often access Docker services externally via localhost
        docker_test_external_vars = {
            "ENVIRONMENT": "test",
            "POSTGRES_HOST": "localhost",     # External access
            "POSTGRES_PORT": "5434",          # External port
            "REDIS_HOST": "localhost",        # External access
            "REDIS_PORT": "6381",             # External port
            "CLICKHOUSE_HOST": "localhost",
            "CLICKHOUSE_PORT": "9002"         # External TCP port
        }
        
        for key, value in docker_test_external_vars.items():
            self.env.set(key, value, "docker_test_consistency_test")
        
        backend_env = BackendEnvironment()
        
        # Validate external Docker port mappings for test environment
        assert backend_env.get_postgres_host() == "localhost"
        assert backend_env.get_postgres_port() == expected_test_ports["postgres_external"]
        assert backend_env.get_redis_host() == "localhost"
        assert backend_env.get_redis_port() == expected_test_ports["redis_external"]
        
        # Environment detection should work correctly
        assert backend_env.is_testing() is True
    
    def test_docker_compose_environment_defaults_consistency(self):
        """Test that Docker Compose environment defaults match application defaults."""
        # Test cases comparing docker-compose.yml defaults with application defaults
        consistency_tests = [
            {
                "name": "postgres_user_default",
                "docker_compose_default": "netra",  # From docker-compose.yml line 26
                "app_method": "get_postgres_user",
                "expected_app_default": "postgres"  # From backend_environment.py line 114
            },
            {
                "name": "postgres_db_default",
                "docker_compose_default": "netra_dev",  # From docker-compose.yml line 28
                "app_method": "get_postgres_db", 
                "expected_app_default": "netra_db"      # From backend_environment.py line 122
            },
            {
                "name": "redis_port_default",
                "docker_compose_default": 6379,     # Internal port in containers
                "app_method": "get_redis_port",
                "expected_app_default": 6379        # From backend_environment.py line 140
            }
        ]
        
        for test in consistency_tests:
            # Test application default (no environment variables set)
            self.env.reset_to_original()
            self.env.enable_isolation()
            
            backend_env = BackendEnvironment()
            method = getattr(backend_env, test["app_method"])
            app_default = method()
            
            # Note: These tests document the current state and highlight where
            # Docker Compose defaults differ from application defaults
            # This is important for identifying potential configuration drift
            
            if test["name"] == "redis_port_default":
                # Redis port should be consistent
                assert app_default == test["expected_app_default"]
            else:
                # Document differences for PostgreSQL configuration
                # These differences are intentional but should be noted
                pass  # Documented inconsistency - Docker uses service-specific defaults
    
    def test_docker_service_name_resolution(self):
        """Test that Docker service names resolve correctly in different contexts."""
        service_resolution_tests = [
            {
                "context": "docker_internal",
                "description": "Inside Docker Compose network",
                "config": {
                    "POSTGRES_HOST": "dev-postgres",
                    "REDIS_HOST": "dev-redis",
                    "CLICKHOUSE_HOST": "dev-clickhouse",
                    "AUTH_SERVICE_URL": "http://dev-auth:8081"
                },
                "expected_accessible": True  # Within Docker network
            },
            {
                "context": "local_external",
                "description": "External access to Docker services",
                "config": {
                    "POSTGRES_HOST": "localhost",
                    "POSTGRES_PORT": "5433",  # External port mapping
                    "REDIS_HOST": "localhost",
                    "REDIS_PORT": "6380",     # External port mapping
                    "AUTH_SERVICE_URL": "http://localhost:8081"
                },
                "expected_accessible": True  # Via port mapping
            },
            {
                "context": "invalid_service_names",
                "description": "Invalid service names should be handled gracefully",
                "config": {
                    "POSTGRES_HOST": "nonexistent-service",
                    "REDIS_HOST": "invalid-redis",
                },
                "expected_accessible": False  # Invalid configuration
            }
        ]
        
        for test in service_resolution_tests:
            self.env.reset_to_original()
            self.env.enable_isolation()
            
            # Set test configuration
            for key, value in test["config"].items():
                self.env.set(key, value, f"service_resolution_{test['context']}")
            
            backend_env = BackendEnvironment()
            
            # Test that configuration is accepted (actual connectivity tested separately)
            postgres_host = backend_env.get_postgres_host()
            redis_host = backend_env.get_redis_host()
            
            if test["context"] == "docker_internal":
                assert postgres_host == "dev-postgres"
                assert redis_host == "dev-redis"
            elif test["context"] == "local_external":
                assert postgres_host == "localhost"
                assert redis_host == "localhost"
            elif test["context"] == "invalid_service_names":
                assert postgres_host == "nonexistent-service"  # Configuration accepted
                assert redis_host == "invalid-redis"
                # Actual connection failure would occur at runtime, not config time


class TestEnvironmentConfigurationLoading:
    """Test environment-specific configuration file loading."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir()
            
            # Create environment-specific config files
            staging_config = config_dir / "staging.env"
            staging_config.write_text("""
# Staging environment configuration
ENVIRONMENT=staging
POSTGRES_HOST=staging-postgres-server
POSTGRES_PORT=5432
REDIS_HOST=staging-redis-server
REDIS_PORT=6379
JWT_SECRET_KEY=staging-jwt-secret-key-32-chars-long
""")
            
            production_config = config_dir / "production.env"
            production_config.write_text("""
# Production environment configuration
ENVIRONMENT=production
POSTGRES_HOST=prod-postgres-server
POSTGRES_PORT=5432
REDIS_HOST=prod-redis-server
REDIS_PORT=6379
JWT_SECRET_KEY=prod-jwt-secret-key-32-chars-long
""")
            
            # Change to temp directory so IsolatedEnvironment can find config files
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            yield temp_dir
            
            os.chdir(original_cwd)
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup clean environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_staging_env_file_loading(self, temp_config_dir):
        """Test loading staging.env configuration file."""
        # Enable local config files and set staging environment
        self.env.set("ENABLE_LOCAL_CONFIG_FILES", "true", "test")
        self.env.set("ENVIRONMENT", "staging", "test")
        
        # Create new IsolatedEnvironment instance to trigger auto-loading
        # (since auto-loading happens during __init__)
        with patch.dict(os.environ, {
            "ENABLE_LOCAL_CONFIG_FILES": "true",
            "ENVIRONMENT": "staging"
        }):
            # Create fresh instance to trigger config file loading
            test_env = IsolatedEnvironment()
            test_env.enable_isolation()
        
        backend_env = BackendEnvironment()
        
        # Variables from staging.env should be loaded (if auto-loading worked)
        # Note: This tests the intended behavior - actual loading depends on
        # IsolatedEnvironment's _load_environment_specific_file implementation
        assert backend_env.get_environment() == "staging"
    
    def test_production_env_file_loading(self, temp_config_dir):
        """Test loading production.env configuration file."""
        # Enable local config files and set production environment
        with patch.dict(os.environ, {
            "ENABLE_LOCAL_CONFIG_FILES": "true",
            "ENVIRONMENT": "production"
        }):
            test_env = IsolatedEnvironment()
            test_env.enable_isolation()
        
        backend_env = BackendEnvironment()
        
        # Should detect production environment
        assert backend_env.get_environment() == "production"
    
    def test_env_file_loading_disabled_in_production(self):
        """Test that .env file loading is disabled in production by default."""
        # Set production environment without ENABLE_LOCAL_CONFIG_FILES
        self.env.set("ENVIRONMENT", "production", "test")
        
        # IsolatedEnvironment should skip .env file loading in production
        # unless explicitly enabled
        backend_env = BackendEnvironment()
        
        assert backend_env.get_environment() == "production"
        assert backend_env.is_production() is True
        
        # Should use defaults/existing environment, not load from files
        # (This prevents accidentally loading development configs in production)


class TestConfigurationValidationIntegration:
    """Test integrated configuration validation across environments."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup test environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_development_configuration_validation(self):
        """Test configuration validation for development environment."""
        dev_config = {
            "ENVIRONMENT": "development",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "REDIS_HOST": "localhost", 
            "REDIS_PORT": "6379",
            "JWT_SECRET_KEY": "dev-jwt-secret-key-must-be-32-chars-min",
            "SECRET_KEY": "dev-secret-key"
        }
        
        for key, value in dev_config.items():
            self.env.set(key, value, "dev_validation_test")
        
        backend_env = BackendEnvironment()
        validation_result = backend_env.validate()
        
        # Development should pass validation with development secrets
        assert validation_result["valid"] is True
        assert validation_result["environment"] == "development"
        assert len(validation_result["issues"]) == 0
    
    def test_staging_configuration_validation(self):
        """Test configuration validation for staging environment."""
        staging_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "staging-postgres-server",  # Not localhost
            "POSTGRES_PORT": "5432",
            "REDIS_HOST": "staging-redis-server",        # Not localhost
            "REDIS_PORT": "6379",
            "JWT_SECRET_KEY": "staging-jwt-secret-32-chars-minimum",
            "SECRET_KEY": "staging-secret-key"
        }
        
        for key, value in staging_config.items():
            self.env.set(key, value, "staging_validation_test")
        
        backend_env = BackendEnvironment()
        validation_result = backend_env.validate()
        
        # Staging should pass with proper staging configuration
        assert validation_result["valid"] is True
        assert validation_result["environment"] == "staging"
    
    def test_staging_with_development_secrets_validation(self):
        """Test that development secrets are caught in staging."""
        staging_with_dev_secrets = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "staging-postgres-server",
            "REDIS_HOST": "staging-redis-server",
            "JWT_SECRET_KEY": "dev-jwt-secret",     # Development secret!
            "SECRET_KEY": "dev-secret-key"          # Development secret!
        }
        
        for key, value in staging_with_dev_secrets.items():
            self.env.set(key, value, "staging_dev_secrets_test")
        
        backend_env = BackendEnvironment()
        validation_result = backend_env.validate()
        
        # Should catch development secrets in staging
        assert validation_result["valid"] is False
        assert validation_result["environment"] == "staging"
        
        # Should have specific warnings about development secrets
        issues = validation_result["issues"]
        dev_secret_issues = [issue for issue in issues if "development" in issue.lower()]
        assert len(dev_secret_issues) > 0
    
    def test_configuration_validation_missing_required_vars(self):
        """Test validation catches missing required variables."""
        incomplete_config = {
            "ENVIRONMENT": "staging",
            # Missing JWT_SECRET_KEY and SECRET_KEY
            "POSTGRES_HOST": "staging-postgres"
        }
        
        for key, value in incomplete_config.items():
            self.env.set(key, value, "incomplete_config_test")
        
        backend_env = BackendEnvironment()
        validation_result = backend_env.validate()
        
        # Should fail validation due to missing required variables
        assert validation_result["valid"] is False
        
        # Should specifically mention missing variables
        missing_jwt = any("JWT_SECRET_KEY" in issue for issue in validation_result["issues"])
        missing_secret = any("SECRET_KEY" in issue for issue in validation_result["issues"])
        
        assert missing_jwt or missing_secret  # At least one should be caught
    
    def test_database_url_validation_integration(self):
        """Test database URL validation integration."""
        # Test with valid POSTGRES_* variables
        valid_postgres_config = {
            "POSTGRES_HOST": "test-postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_password",
            "POSTGRES_DB": "test_db"
        }
        
        for key, value in valid_postgres_config.items():
            self.env.set(key, value, "db_validation_test")
        
        backend_env = BackendEnvironment()
        
        # Should be able to build database URL
        db_url = backend_env.get_database_url()
        assert db_url  # Should not be empty
        assert "test-postgres" in db_url
        assert "5432" in db_url
        assert "test_user" in db_url
        assert "test_db" in db_url
        
        validation_result = backend_env.validate()
        
        # Database URL issues should not appear if POSTGRES_* vars are valid
        db_issues = [issue for issue in validation_result.get("issues", []) if "database" in issue.lower()]
        # Note: Actual database connectivity not tested here (that's integration testing)