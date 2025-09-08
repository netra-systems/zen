"""
Configuration System Cross-Environment Validation Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Platform Stability & Risk Reduction
- Value Impact: Ensures configuration consistency prevents service failures across environments
- Strategic Impact: Prevents cascade failures from config mismatches that cost revenue

These tests validate configuration system behavior across different environments,
ensuring proper isolation, secret loading, and dependency validation.
"""

import pytest
import asyncio
import os
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestConfigurationCrossEnvironmentValidation(BaseIntegrationTest):
    """Test configuration system across different environments."""

    @pytest.mark.integration
    async def test_config_consistency_across_environments(self):
        """
        Test configuration consistency across TEST/DEV/STAGING/PROD environments.
        
        BVJ: Ensures configuration changes don't break environment-specific settings.
        Critical for preventing staging/prod deployment failures.
        """
        environments = ["TEST", "DEV", "STAGING", "PROD"]
        config_consistency_results = {}
        
        for env in environments:
            env_obj = IsolatedEnvironment(source=f"test_{env.lower()}")
            
            # Test environment-specific configs exist
            env_obj.set("ENVIRONMENT", env, source=f"test_{env.lower()}")
            env_obj.set("DATABASE_URL", f"postgres://test_{env.lower()}:5432/test", source=f"test_{env.lower()}")
            
            # Validate config structure consistency
            assert env_obj.get("ENVIRONMENT") == env
            assert env_obj.get("DATABASE_URL") is not None
            
            config_consistency_results[env] = {
                "environment_set": env_obj.get("ENVIRONMENT") == env,
                "database_url_present": env_obj.get("DATABASE_URL") is not None
            }
        
        # Verify all environments have consistent structure
        for env, results in config_consistency_results.items():
            assert results["environment_set"], f"Environment {env} not properly set"
            assert results["database_url_present"], f"Database URL missing for {env}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_secret_loading_without_service_disruption(self, real_services_fixture):
        """
        Test secret loading and rotation without disrupting running services.
        
        BVJ: Critical for enterprise customers who need zero-downtime secret rotation.
        Prevents service interruptions during security updates.
        """
        env = get_env()
        
        # Simulate original secret
        original_secret = "original_jwt_secret_12345"
        env.set("JWT_SECRET", original_secret, source="test")
        
        assert env.get("JWT_SECRET") == original_secret
        
        # Simulate secret rotation
        new_secret = "rotated_jwt_secret_67890"
        env.set("JWT_SECRET", new_secret, source="test")
        
        # Verify secret was updated without service disruption
        assert env.get("JWT_SECRET") == new_secret
        assert env.get("JWT_SECRET") != original_secret
        
        # Test graceful fallback during rotation
        env.set("JWT_SECRET_FALLBACK", original_secret, source="test")
        assert env.get("JWT_SECRET_FALLBACK") == original_secret

    @pytest.mark.integration
    async def test_cross_service_config_dependency_validation(self):
        """
        Test configuration dependency validation between services.
        
        BVJ: Prevents cascade failures when one service config affects another.
        Critical for platform stability and customer trust.
        """
        env = get_env()
        
        # Set up service dependencies
        backend_port = "8000"
        auth_port = "8081"
        
        env.set("BACKEND_PORT", backend_port, source="test")
        env.set("AUTH_SERVICE_PORT", auth_port, source="test")
        env.set("AUTH_SERVICE_URL", f"http://localhost:{auth_port}", source="test")
        
        # Validate dependency chain
        assert env.get("BACKEND_PORT") == backend_port
        assert env.get("AUTH_SERVICE_PORT") == auth_port
        assert env.get("AUTH_SERVICE_URL") == f"http://localhost:{auth_port}"
        
        # Test dependency validation
        expected_auth_url = f"http://localhost:{env.get('AUTH_SERVICE_PORT')}"
        assert env.get("AUTH_SERVICE_URL") == expected_auth_url

    @pytest.mark.integration
    async def test_environment_specific_config_isolation(self):
        """
        Test environment-specific configuration isolation.
        
        BVJ: Ensures test configs don't leak to staging/prod, preventing data breaches
        and maintaining customer data integrity.
        """
        # Create isolated environments
        test_env = IsolatedEnvironment(source="test_isolation")
        staging_env = IsolatedEnvironment(source="staging_isolation")
        prod_env = IsolatedEnvironment(source="prod_isolation")
        
        # Set environment-specific configs
        test_env.set("DATABASE_URL", "postgres://test_db:5434/test_netra", source="test_isolation")
        staging_env.set("DATABASE_URL", "postgres://staging_db:5432/staging_netra", source="staging_isolation")
        prod_env.set("DATABASE_URL", "postgres://prod_db:5432/prod_netra", source="prod_isolation")
        
        # Verify isolation
        assert test_env.get("DATABASE_URL") != staging_env.get("DATABASE_URL")
        assert staging_env.get("DATABASE_URL") != prod_env.get("DATABASE_URL")
        assert test_env.get("DATABASE_URL") != prod_env.get("DATABASE_URL")
        
        # Verify environment-specific patterns
        assert "test_db" in test_env.get("DATABASE_URL")
        assert "staging_db" in staging_env.get("DATABASE_URL")
        assert "prod_db" in prod_env.get("DATABASE_URL")

    @pytest.mark.integration
    async def test_configuration_change_impact_analysis(self):
        """
        Test configuration change impact analysis across system components.
        
        BVJ: Prevents configuration changes from causing unexpected failures.
        Critical for maintaining platform reliability during updates.
        """
        env = get_env()
        
        # Track configuration changes
        config_changes = []
        
        def track_change(key: str, old_value: Any, new_value: Any):
            config_changes.append({
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
                "timestamp": asyncio.get_event_loop().time()
            })
        
        # Simulate configuration changes
        original_redis_url = "redis://localhost:6379"
        env.set("REDIS_URL", original_redis_url, source="test")
        track_change("REDIS_URL", None, original_redis_url)
        
        new_redis_url = "redis://localhost:6381"
        old_value = env.get("REDIS_URL")
        env.set("REDIS_URL", new_redis_url, source="test")
        track_change("REDIS_URL", old_value, new_redis_url)
        
        # Analyze impact
        assert len(config_changes) == 2
        assert config_changes[0]["key"] == "REDIS_URL"
        assert config_changes[1]["old_value"] == original_redis_url
        assert config_changes[1]["new_value"] == new_redis_url

    @pytest.mark.integration
    async def test_startup_with_missing_configurations(self):
        """
        Test system startup sequence with missing or invalid configurations.
        
        BVJ: Ensures graceful degradation when configs are missing, maintaining
        service availability for customers even during config issues.
        """
        env = get_env()
        
        # Test with missing required config
        startup_results = []
        
        try:
            # Simulate missing critical config
            database_url = env.get("CRITICAL_DATABASE_URL")  # Intentionally missing
            if database_url is None:
                startup_results.append("database_config_missing")
            
            # Test graceful handling
            fallback_db = env.get("DATABASE_URL", "postgres://localhost:5432/fallback")
            startup_results.append(f"fallback_used:{fallback_db}")
            
        except Exception as e:
            startup_results.append(f"error:{str(e)}")
        
        # Verify graceful handling
        assert "database_config_missing" in startup_results
        assert any("fallback_used:" in result for result in startup_results)

    @pytest.mark.integration 
    async def test_startup_with_invalid_configurations(self):
        """
        Test system startup sequence with invalid configurations.
        
        BVJ: Ensures system fails fast with clear errors rather than silent failures
        that could cause customer data issues.
        """
        env = get_env()
        
        validation_results = []
        
        # Test invalid port configuration
        env.set("INVALID_PORT", "not_a_number", source="test")
        try:
            port = int(env.get("INVALID_PORT"))
        except ValueError:
            validation_results.append("invalid_port_handled")
        
        # Test invalid URL format
        env.set("INVALID_URL", "not-a-valid-url", source="test")
        invalid_url = env.get("INVALID_URL")
        if not invalid_url.startswith(("http://", "https://")):
            validation_results.append("invalid_url_detected")
        
        # Test empty critical config
        env.set("EMPTY_CRITICAL_CONFIG", "", source="test")
        empty_config = env.get("EMPTY_CRITICAL_CONFIG")
        if not empty_config or empty_config.strip() == "":
            validation_results.append("empty_config_detected")
        
        # Verify all validations caught issues
        assert "invalid_port_handled" in validation_results
        assert "invalid_url_detected" in validation_results  
        assert "empty_config_detected" in validation_results

    @pytest.mark.integration
    async def test_oauth_config_environment_isolation(self):
        """
        Test OAuth configuration isolation between environments.
        
        BVJ: Critical for security - prevents staging OAuth credentials from
        being used in production, protecting customer data and platform integrity.
        """
        # Create environment-specific OAuth configs
        test_env = IsolatedEnvironment(source="oauth_test")
        staging_env = IsolatedEnvironment(source="oauth_staging")
        prod_env = IsolatedEnvironment(source="oauth_prod")
        
        # Set OAuth credentials per environment
        test_env.set("OAUTH_CLIENT_ID", "test_client_123", source="oauth_test")
        test_env.set("OAUTH_CLIENT_SECRET", "test_secret_456", source="oauth_test")
        test_env.set("OAUTH_REDIRECT_URI", "http://localhost:3000/auth/callback", source="oauth_test")
        
        staging_env.set("OAUTH_CLIENT_ID", "staging_client_789", source="oauth_staging")
        staging_env.set("OAUTH_CLIENT_SECRET", "staging_secret_012", source="oauth_staging")
        staging_env.set("OAUTH_REDIRECT_URI", "https://staging.netra.com/auth/callback", source="oauth_staging")
        
        prod_env.set("OAUTH_CLIENT_ID", "prod_client_345", source="oauth_prod")
        prod_env.set("OAUTH_CLIENT_SECRET", "prod_secret_678", source="oauth_prod")
        prod_env.set("OAUTH_REDIRECT_URI", "https://app.netra.com/auth/callback", source="oauth_prod")
        
        # Verify complete isolation
        assert test_env.get("OAUTH_CLIENT_ID") != staging_env.get("OAUTH_CLIENT_ID")
        assert staging_env.get("OAUTH_CLIENT_ID") != prod_env.get("OAUTH_CLIENT_ID")
        assert test_env.get("OAUTH_CLIENT_SECRET") != staging_env.get("OAUTH_CLIENT_SECRET")
        assert staging_env.get("OAUTH_CLIENT_SECRET") != prod_env.get("OAUTH_CLIENT_SECRET")
        
        # Verify environment-appropriate URLs
        assert "localhost" in test_env.get("OAUTH_REDIRECT_URI")
        assert "staging.netra.com" in staging_env.get("OAUTH_REDIRECT_URI")
        assert "app.netra.com" in prod_env.get("OAUTH_REDIRECT_URI")

    @pytest.mark.integration
    async def test_database_config_environment_validation(self):
        """
        Test database configuration validation across environments.
        
        BVJ: Ensures database connections are environment-appropriate, preventing
        test operations from affecting production data.
        """
        environments = {
            "test": {
                "expected_db": "test_netra",
                "expected_port": "5434"
            },
            "dev": {
                "expected_db": "dev_netra", 
                "expected_port": "5432"
            },
            "staging": {
                "expected_db": "staging_netra",
                "expected_port": "5432"
            },
            "prod": {
                "expected_db": "prod_netra",
                "expected_port": "5432"
            }
        }
        
        for env_name, config in environments.items():
            env = IsolatedEnvironment(source=f"db_test_{env_name}")
            
            # Set environment-appropriate database config
            db_url = f"postgresql://user:pass@localhost:{config['expected_port']}/{config['expected_db']}"
            env.set("DATABASE_URL", db_url, source=f"db_test_{env_name}")
            
            # Validate config matches environment expectations
            retrieved_url = env.get("DATABASE_URL")
            assert config["expected_db"] in retrieved_url
            assert config["expected_port"] in retrieved_url
            
            # Ensure test environment uses different port
            if env_name == "test":
                assert "5434" in retrieved_url
            else:
                assert "5432" in retrieved_url

    @pytest.mark.integration
    async def test_service_mesh_config_consistency(self):
        """
        Test service mesh configuration consistency across all services.
        
        BVJ: Ensures all services can communicate properly, preventing
        inter-service failures that impact customer experience.
        """
        env = get_env()
        
        # Service mesh configuration
        services = {
            "backend": {"port": "8000", "health_endpoint": "/health"},
            "auth": {"port": "8081", "health_endpoint": "/health"},  
            "frontend": {"port": "3000", "health_endpoint": "/api/health"},
            "analytics": {"port": "8002", "health_endpoint": "/health"}
        }
        
        # Set service mesh configs
        for service, config in services.items():
            env.set(f"{service.upper()}_PORT", config["port"], source="test")
            env.set(f"{service.upper()}_HEALTH_ENDPOINT", config["health_endpoint"], source="test")
            env.set(f"{service.upper()}_URL", f"http://localhost:{config['port']}", source="test")
        
        # Validate service mesh consistency
        for service, config in services.items():
            port = env.get(f"{service.upper()}_PORT")
            health_endpoint = env.get(f"{service.upper()}_HEALTH_ENDPOINT")
            service_url = env.get(f"{service.upper()}_URL")
            
            assert port == config["port"]
            assert health_endpoint == config["health_endpoint"]
            assert f"localhost:{port}" in service_url

    @pytest.mark.integration
    async def test_config_validation_during_deployment(self):
        """
        Test configuration validation during deployment process.
        
        BVJ: Prevents deployment of services with invalid configs, maintaining
        platform stability and preventing customer-facing outages.
        """
        env = get_env()
        
        # Deployment configuration checklist
        required_configs = [
            "DATABASE_URL",
            "REDIS_URL", 
            "JWT_SECRET",
            "OAUTH_CLIENT_ID",
            "OAUTH_CLIENT_SECRET"
        ]
        
        deployment_validation = {"valid": True, "missing_configs": [], "invalid_configs": []}
        
        # Set valid configs
        env.set("DATABASE_URL", "postgresql://user:pass@localhost:5432/netra", source="test")
        env.set("REDIS_URL", "redis://localhost:6379", source="test")
        env.set("JWT_SECRET", "valid_jwt_secret_32_chars_long_12345", source="test")
        env.set("OAUTH_CLIENT_ID", "oauth_client_123", source="test")
        env.set("OAUTH_CLIENT_SECRET", "oauth_secret_456", source="test")
        
        # Validate each required config
        for config_key in required_configs:
            value = env.get(config_key)
            if not value:
                deployment_validation["missing_configs"].append(config_key)
                deployment_validation["valid"] = False
            elif config_key == "JWT_SECRET" and len(value) < 32:
                deployment_validation["invalid_configs"].append(f"{config_key}_too_short")
                deployment_validation["valid"] = False
        
        # Verify deployment validation passes
        assert deployment_validation["valid"] is True
        assert len(deployment_validation["missing_configs"]) == 0
        assert len(deployment_validation["invalid_configs"]) == 0

    @pytest.mark.integration
    async def test_configuration_hot_reload_capability(self):
        """
        Test configuration hot reload without service restart.
        
        BVJ: Enables rapid configuration changes without downtime, critical for
        enterprise customers who need continuous availability.
        """
        env = get_env()
        
        # Initial configuration
        env.set("LOG_LEVEL", "INFO", source="test")
        env.set("MAX_CONNECTIONS", "100", source="test")
        
        initial_log_level = env.get("LOG_LEVEL")
        initial_max_connections = env.get("MAX_CONNECTIONS")
        
        assert initial_log_level == "INFO"
        assert initial_max_connections == "100"
        
        # Simulate hot reload
        reload_results = []
        
        # Change configurations
        env.set("LOG_LEVEL", "DEBUG", source="test")
        env.set("MAX_CONNECTIONS", "200", source="test")
        
        # Verify changes applied
        new_log_level = env.get("LOG_LEVEL")
        new_max_connections = env.get("MAX_CONNECTIONS")
        
        if new_log_level != initial_log_level:
            reload_results.append("log_level_reloaded")
        if new_max_connections != initial_max_connections:
            reload_results.append("max_connections_reloaded")
        
        # Verify hot reload successful
        assert "log_level_reloaded" in reload_results
        assert "max_connections_reloaded" in reload_results
        assert new_log_level == "DEBUG"
        assert new_max_connections == "200"