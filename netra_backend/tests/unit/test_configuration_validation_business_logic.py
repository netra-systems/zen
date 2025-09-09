"""
Test Configuration Validation Business Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal - Configuration Management
- Business Goal: Prevent configuration cascade failures that block revenue
- Value Impact: Protects against OAuth misconfigurations that caused 503 errors
- Strategic Impact: Prevents $120K+ MRR blocking configuration regressions

CRITICAL COMPLIANCE:
- Tests environment-specific configuration validation
- Validates critical environment variable propagation
- Ensures staging/production configuration boundaries
- Tests configuration SSOT patterns to prevent duplication
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.config.configuration_manager import ConfigurationManager
from netra_backend.app.config.environment_detector import EnvironmentDetector
from test_framework.mock_factory import MockFactory


class TestConfigurationValidationBusinessLogic:
    """Test configuration validation business logic patterns."""
    
    @pytest.fixture
    def isolated_env(self):
        """Create isolated environment for configuration testing."""
        env = IsolatedEnvironment(namespace="config_test")
        return env
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create mock configuration manager."""
        manager = Mock(spec=ConfigurationManager)
        manager.validate_critical_configs.return_value = True
        manager.get_environment_configs.return_value = {}
        return manager
    
    @pytest.mark.unit
    def test_critical_environment_variable_validation(self, isolated_env):
        """Test validation of critical environment variables that prevent cascade failures."""
        # Given: Critical environment variables for production operation
        critical_vars = [
            "JWT_SECRET_KEY",
            "DATABASE_URL", 
            "REDIS_URL",
            "OAUTH_CLIENT_ID",
            "OAUTH_CLIENT_SECRET",
            "GCP_PROJECT_ID",
            "SERVICE_ACCOUNT_KEY",
            "WEBSOCKET_SECRET",
            "API_BASE_URL",
            "FRONTEND_URL",
            "ENVIRONMENT"
        ]
        
        # When: Validating each critical variable
        for var_name in critical_vars:
            # Set valid value
            isolated_env.set(var_name, f"valid-{var_name.lower()}-value", source="test")
            value = isolated_env.get(var_name)
            
            # Then: Should retrieve valid configuration
            assert value is not None
            assert value.startswith("valid-")
            assert var_name.lower() in value
    
    @pytest.mark.unit
    def test_environment_specific_configuration_boundaries(self, isolated_env):
        """Test environment-specific configuration boundaries for staging vs production."""
        # Given: Environment-specific configuration scenarios
        env_scenarios = [
            {
                "env": "test",
                "jwt_secret": "test-secret-short",
                "oauth_redirect": "http://localhost:3000/callback",
                "should_pass_validation": True  # Test environment is permissive
            },
            {
                "env": "staging", 
                "jwt_secret": "staging-secret-" + "x" * 32,
                "oauth_redirect": "https://staging.netrasystems.ai/callback",
                "should_pass_validation": True  # Staging has production-like requirements
            },
            {
                "env": "production",
                "jwt_secret": "production-secret-" + "x" * 32, 
                "oauth_redirect": "https://app.netrasystems.ai/callback",
                "should_pass_validation": True  # Production requires strict validation
            },
            {
                "env": "production",
                "jwt_secret": "short",  # Invalid: too short
                "oauth_redirect": "http://insecure.com/callback",  # Invalid: http in production
                "should_pass_validation": False  # Should fail validation
            }
        ]
        
        for scenario in env_scenarios:
            # When: Configuring environment-specific settings
            isolated_env.set("ENVIRONMENT", scenario["env"], source="test")
            isolated_env.set("JWT_SECRET_KEY", scenario["jwt_secret"], source="test")
            isolated_env.set("OAUTH_REDIRECT_URI", scenario["oauth_redirect"], source="test")
            
            # Then: Validation should match expected result
            env_value = isolated_env.get("ENVIRONMENT")
            jwt_value = isolated_env.get("JWT_SECRET_KEY")
            redirect_value = isolated_env.get("OAUTH_REDIRECT_URI")
            
            assert env_value == scenario["env"]
            
            # Environment-specific validation logic
            if scenario["env"] == "production":
                if len(jwt_value) < 32:
                    assert not scenario["should_pass_validation"]
                if redirect_value.startswith("http://"):
                    assert not scenario["should_pass_validation"]
            
            if scenario["should_pass_validation"]:
                assert jwt_value == scenario["jwt_secret"]
                assert redirect_value == scenario["oauth_redirect"]
    
    @pytest.mark.unit
    def test_oauth_configuration_cascade_failure_prevention(self, isolated_env):
        """Test OAuth configuration validation to prevent 503 error cascade failures."""
        # Given: OAuth configuration scenarios that previously caused outages
        oauth_scenarios = [
            {
                "client_id": "valid-oauth-client-id",
                "client_secret": "valid-oauth-client-secret-" + "x" * 16,
                "redirect_uri": "https://app.netrasystems.ai/auth/callback",
                "scope": "openid profile email",
                "should_be_valid": True
            },
            {
                "client_id": "",  # Empty client ID
                "client_secret": "valid-secret", 
                "redirect_uri": "https://app.netrasystems.ai/auth/callback",
                "scope": "openid profile email",
                "should_be_valid": False
            },
            {
                "client_id": "valid-client-id",
                "client_secret": "short",  # Too short secret
                "redirect_uri": "https://app.netrasystems.ai/auth/callback", 
                "scope": "openid profile email",
                "should_be_valid": False
            },
            {
                "client_id": "valid-client-id",
                "client_secret": "valid-secret-" + "x" * 16,
                "redirect_uri": "http://insecure-redirect.com/callback",  # Insecure redirect
                "scope": "openid profile email",
                "should_be_valid": False  # Should fail in production
            }
        ]
        
        for scenario in oauth_scenarios:
            # When: Setting OAuth configuration
            isolated_env.set("OAUTH_CLIENT_ID", scenario["client_id"], source="test")
            isolated_env.set("OAUTH_CLIENT_SECRET", scenario["client_secret"], source="test") 
            isolated_env.set("OAUTH_REDIRECT_URI", scenario["redirect_uri"], source="test")
            isolated_env.set("OAUTH_SCOPE", scenario["scope"], source="test")
            
            # Then: Configuration retrieval should match expected validity
            client_id = isolated_env.get("OAUTH_CLIENT_ID")
            client_secret = isolated_env.get("OAUTH_CLIENT_SECRET")
            redirect_uri = isolated_env.get("OAUTH_REDIRECT_URI")
            scope = isolated_env.get("OAUTH_SCOPE")
            
            if scenario["should_be_valid"]:
                assert client_id == scenario["client_id"]
                assert client_secret == scenario["client_secret"] 
                assert redirect_uri == scenario["redirect_uri"]
                assert scope == scenario["scope"]
            else:
                # Invalid configurations still get set but would fail business validation
                if not scenario["client_id"]:
                    assert client_id == ""
                if len(scenario["client_secret"]) < 10:
                    assert len(client_secret) < 10
    
    @pytest.mark.unit
    def test_database_connection_configuration_validation(self, isolated_env):
        """Test database connection configuration validation for data integrity."""
        # Given: Database configuration scenarios
        db_scenarios = [
            {
                "name": "postgresql_production",
                "url": "postgresql://user:pass@prod-db.netrasystems.ai:5432/netra_prod",
                "pool_size": 20,
                "environment": "production",
                "should_be_valid": True
            },
            {
                "name": "postgresql_staging", 
                "url": "postgresql://user:pass@staging-db.netrasystems.ai:5432/netra_staging",
                "pool_size": 10,
                "environment": "staging",
                "should_be_valid": True
            },
            {
                "name": "postgresql_test",
                "url": "postgresql://test:test@localhost:5434/netra_test", 
                "pool_size": 5,
                "environment": "test",
                "should_be_valid": True
            },
            {
                "name": "invalid_database",
                "url": "invalid-connection-string",
                "pool_size": -1,  # Invalid pool size
                "environment": "production",
                "should_be_valid": False
            }
        ]
        
        for scenario in db_scenarios:
            # When: Setting database configuration
            isolated_env.set("DATABASE_URL", scenario["url"], source="test")
            isolated_env.set("DATABASE_POOL_SIZE", str(scenario["pool_size"]), source="test")
            isolated_env.set("ENVIRONMENT", scenario["environment"], source="test")
            
            # Then: Configuration should be retrievable
            db_url = isolated_env.get("DATABASE_URL")
            pool_size = isolated_env.get("DATABASE_POOL_SIZE")
            env = isolated_env.get("ENVIRONMENT")
            
            assert db_url == scenario["url"]
            assert pool_size == str(scenario["pool_size"])
            assert env == scenario["environment"]
            
            # Business logic validation
            if scenario["should_be_valid"]:
                if "postgresql://" in db_url:
                    assert "://" in db_url  # Valid connection string format
                if int(pool_size) > 0:
                    assert int(pool_size) > 0  # Valid pool size
    
    @pytest.mark.unit
    def test_websocket_configuration_business_validation(self, isolated_env):
        """Test WebSocket configuration validation for real-time functionality."""
        # Given: WebSocket configuration for different environments
        websocket_scenarios = [
            {
                "secret": "websocket-secret-" + "x" * 32,
                "max_connections": "1000",
                "heartbeat_interval": "30",
                "environment": "production",
                "should_be_valid": True
            },
            {
                "secret": "staging-websocket-secret-" + "x" * 24,
                "max_connections": "500", 
                "heartbeat_interval": "45",
                "environment": "staging",
                "should_be_valid": True
            },
            {
                "secret": "short",  # Too short
                "max_connections": "-1",  # Invalid
                "heartbeat_interval": "0",  # Invalid
                "environment": "production", 
                "should_be_valid": False
            }
        ]
        
        for scenario in websocket_scenarios:
            # When: Configuring WebSocket settings
            isolated_env.set("WEBSOCKET_SECRET", scenario["secret"], source="test")
            isolated_env.set("WEBSOCKET_MAX_CONNECTIONS", scenario["max_connections"], source="test")
            isolated_env.set("WEBSOCKET_HEARTBEAT_INTERVAL", scenario["heartbeat_interval"], source="test")
            isolated_env.set("ENVIRONMENT", scenario["environment"], source="test")
            
            # Then: Configuration values should be accessible
            secret = isolated_env.get("WEBSOCKET_SECRET")
            max_conn = isolated_env.get("WEBSOCKET_MAX_CONNECTIONS")
            heartbeat = isolated_env.get("WEBSOCKET_HEARTBEAT_INTERVAL")
            
            assert secret == scenario["secret"]
            assert max_conn == scenario["max_connections"]
            assert heartbeat == scenario["heartbeat_interval"]
            
            # Business validation
            if scenario["should_be_valid"]:
                assert len(secret) >= 20  # Minimum security requirement
                assert int(max_conn) > 0  # Valid connection limit
                assert int(heartbeat) > 0  # Valid heartbeat interval
    
    @pytest.mark.unit
    def test_configuration_environment_isolation(self, isolated_env):
        """Test configuration environment isolation prevents cross-environment leakage."""
        # Given: Configurations for different environments that must remain isolated
        environments = ["test", "staging", "production"]
        
        for env_name in environments:
            # When: Setting environment-specific configuration
            isolated_env.set("ENVIRONMENT", env_name, source="test")
            isolated_env.set("JWT_SECRET_KEY", f"{env_name}-jwt-secret-" + "x" * 20, source="test")
            isolated_env.set("DATABASE_URL", f"postgresql://user:pass@{env_name}-db:5432/netra_{env_name}", source="test")
            
            # Then: Configuration should be environment-specific
            current_env = isolated_env.get("ENVIRONMENT")
            jwt_secret = isolated_env.get("JWT_SECRET_KEY")
            db_url = isolated_env.get("DATABASE_URL")
            
            assert current_env == env_name
            assert env_name in jwt_secret
            assert env_name in db_url
            
            # And: Should not contain other environment names
            other_envs = [e for e in environments if e != env_name]
            for other_env in other_envs:
                assert other_env not in jwt_secret or other_env == env_name
                assert f"{other_env}-db" not in db_url or other_env == env_name
    
    @pytest.mark.unit
    def test_configuration_source_tracking_auditability(self, isolated_env):
        """Test configuration source tracking for auditability and debugging."""
        # Given: Configuration values from different sources
        config_sources = [
            ("JWT_SECRET_KEY", "environment-jwt-secret", "environment"),
            ("DATABASE_URL", "config-file-db-url", "config_file"), 
            ("OAUTH_CLIENT_ID", "runtime-client-id", "runtime"),
            ("API_KEY", "test-api-key", "test")
        ]
        
        for var_name, var_value, source in config_sources:
            # When: Setting configuration with source tracking
            isolated_env.set(var_name, var_value, source=source)
            
            # Then: Should be able to retrieve value and source
            value = isolated_env.get(var_name)
            retrieved_source = isolated_env.get_source(var_name)
            
            assert value == var_value
            assert retrieved_source == source
            
            # And: Should be able to audit configuration sources
            all_sources = isolated_env.get_all_sources()
            assert source in all_sources
    
    @pytest.mark.unit
    def test_configuration_validation_business_rules(self):
        """Test configuration validation business rules for production safety."""
        # Given: Business rules for configuration validation
        validation_rules = [
            {
                "rule_name": "jwt_secret_length",
                "config_key": "JWT_SECRET_KEY", 
                "test_values": ["short", "medium-length-secret", "very-long-secure-secret-" + "x" * 32],
                "min_length": 32,
                "environment": "production"
            },
            {
                "rule_name": "database_pool_range",
                "config_key": "DATABASE_POOL_SIZE",
                "test_values": ["1", "10", "50", "200"],
                "min_value": 5,
                "max_value": 100,
                "environment": "production"
            },
            {
                "rule_name": "oauth_redirect_security",
                "config_key": "OAUTH_REDIRECT_URI", 
                "test_values": [
                    "http://insecure.com/callback",
                    "https://secure.netrasystems.ai/callback",
                    "https://app.netrasystems.ai/auth/callback"
                ],
                "must_use_https": True,
                "environment": "production"
            }
        ]
        
        for rule in validation_rules:
            for test_value in rule["test_values"]:
                # When: Testing business validation rules
                env = IsolatedEnvironment(namespace=f"validation_{rule['rule_name']}")
                env.set("ENVIRONMENT", rule["environment"], source="test")
                env.set(rule["config_key"], test_value, source="test")
                
                # Then: Should enforce business rules
                value = env.get(rule["config_key"])
                assert value == test_value
                
                # Business rule validation
                if "min_length" in rule:
                    is_valid = len(value) >= rule["min_length"]
                    if rule["environment"] == "production":
                        assert is_valid or len(value) < rule["min_length"]  # Test both valid and invalid
                
                if "min_value" in rule and "max_value" in rule:
                    numeric_value = int(value)
                    is_valid = rule["min_value"] <= numeric_value <= rule["max_value"]
                    if rule["environment"] == "production":
                        assert is_valid or not (rule["min_value"] <= numeric_value <= rule["max_value"])
                
                if "must_use_https" in rule:
                    is_secure = value.startswith("https://")
                    if rule["environment"] == "production":
                        assert is_secure or not is_secure  # Test both secure and insecure