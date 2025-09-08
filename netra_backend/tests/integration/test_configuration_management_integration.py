"""
Test Configuration Management Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all user segments)
- Business Goal: Ensure configuration consistency and prevent deployment failures
- Value Impact: Configuration errors cause service outages and user experience degradation
- Strategic Impact: Proper config management is critical for multi-environment deployments

This test suite validates configuration management integration:
1. Environment-specific configuration loading and validation
2. Configuration isolation between test/dev/staging/production
3. Dynamic configuration updates without service restart
"""

import asyncio
import uuid
import pytest
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.types.core_types import UserID, ensure_user_id

# Configuration management components
from netra_backend.app.config import Config, DatabaseConfig, RedisConfig
from netra_backend.app.services.configuration_service import (
    ConfigurationService,
    EnvironmentConfigLoader,
    ConfigurationValidator
)
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager as ConfigurationManager


class TestConfigurationManagementIntegration(BaseIntegrationTest):
    """Test configuration management with real environment isolation."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_environment_specific_configuration_loading(self, real_services_fixture, isolated_env):
        """Test loading environment-specific configurations without cross-contamination."""
        
        # Create isolated environment for testing
        test_env = get_env()
        
        # Test configuration scenarios for different environments
        env_configs = {
            "test": {
                "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
                "REDIS_URL": "redis://localhost:6381",
                "JWT_SECRET_KEY": "test_jwt_secret_key_for_integration_testing",
                "LOG_LEVEL": "DEBUG",
                "ENVIRONMENT": "test"
            },
            "development": {
                "DATABASE_URL": "postgresql://dev:dev@localhost:5432/dev_db", 
                "REDIS_URL": "redis://localhost:6379",
                "JWT_SECRET_KEY": "dev_jwt_secret_key_for_development",
                "LOG_LEVEL": "INFO",
                "ENVIRONMENT": "development"
            },
            "staging": {
                "DATABASE_URL": "postgresql://staging_user:staging_pass@staging-db:5432/staging_db",
                "REDIS_URL": "redis://staging-redis:6379",
                "JWT_SECRET_KEY": "staging_jwt_secret_key_hex_string",
                "LOG_LEVEL": "WARNING",
                "ENVIRONMENT": "staging"
            }
        }
        
        # Test each environment configuration
        for env_name, config_values in env_configs.items():
            # Set environment-specific values
            for key, value in config_values.items():
                test_env.set(key, value, source=f"{env_name}_config_test")
            
            # Initialize configuration service for this environment
            config_loader = EnvironmentConfigLoader(environment=env_name)
            config_service = ConfigurationService(config_loader)
            
            # Load configuration
            loaded_config = await config_service.load_configuration()
            
            # Verify environment-specific values are loaded correctly
            assert loaded_config.database.url == config_values["DATABASE_URL"]
            assert loaded_config.redis.url == config_values["REDIS_URL"]
            assert loaded_config.jwt.secret_key == config_values["JWT_SECRET_KEY"]
            assert loaded_config.logging.level == config_values["LOG_LEVEL"]
            assert loaded_config.environment == env_name
            
            # Verify isolation - config should not contain values from other environments
            other_envs = [name for name in env_configs.keys() if name != env_name]
            for other_env in other_envs:
                other_config = env_configs[other_env]
                
                # Current config should not have other environment's database URL
                assert loaded_config.database.url != other_config["DATABASE_URL"], \
                    f"Configuration contaminated with {other_env} database URL"
                
                # Current config should not have other environment's secrets
                assert loaded_config.jwt.secret_key != other_config["JWT_SECRET_KEY"], \
                    f"Configuration contaminated with {other_env} JWT secret"
            
            # Clear environment for next test
            for key in config_values.keys():
                test_env.unset(key)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_configuration_validation_and_error_handling(self, real_services_fixture, isolated_env):
        """Test configuration validation catches invalid configurations."""
        
        test_env = get_env()
        
        # Test invalid configuration scenarios
        invalid_configs = [
            {
                "name": "missing_database_url",
                "config": {
                    "REDIS_URL": "redis://localhost:6379",
                    "JWT_SECRET_KEY": "test_secret",
                    "ENVIRONMENT": "test"
                    # Missing DATABASE_URL
                },
                "expected_error": "DATABASE_URL is required"
            },
            {
                "name": "invalid_database_url_format",
                "config": {
                    "DATABASE_URL": "invalid_database_url_format",
                    "REDIS_URL": "redis://localhost:6379", 
                    "JWT_SECRET_KEY": "test_secret",
                    "ENVIRONMENT": "test"
                },
                "expected_error": "Invalid database URL format"
            },
            {
                "name": "empty_jwt_secret",
                "config": {
                    "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
                    "REDIS_URL": "redis://localhost:6379",
                    "JWT_SECRET_KEY": "",  # Empty secret
                    "ENVIRONMENT": "test"
                },
                "expected_error": "JWT_SECRET_KEY cannot be empty"
            },
            {
                "name": "invalid_log_level",
                "config": {
                    "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
                    "REDIS_URL": "redis://localhost:6379",
                    "JWT_SECRET_KEY": "test_secret",
                    "LOG_LEVEL": "INVALID_LEVEL",  # Invalid log level
                    "ENVIRONMENT": "test"
                },
                "expected_error": "Invalid log level"
            }
        ]
        
        config_validator = ConfigurationValidator()
        
        for invalid_config in invalid_configs:
            # Set invalid configuration
            for key, value in invalid_config["config"].items():
                test_env.set(key, value, source="invalid_config_test")
            
            # Try to load and validate configuration
            config_loader = EnvironmentConfigLoader(environment="test")
            config_service = ConfigurationService(config_loader)
            
            # Configuration loading should fail with appropriate error
            with pytest.raises(ValueError) as exc_info:
                loaded_config = await config_service.load_configuration()
                await config_validator.validate_configuration(loaded_config)
            
            # Verify appropriate error message
            error_message = str(exc_info.value)
            assert invalid_config["expected_error"] in error_message or \
                   any(keyword in error_message.lower() for keyword in invalid_config["expected_error"].lower().split()), \
                   f"Expected error message not found for {invalid_config['name']}: {error_message}"
            
            # Clear invalid configuration
            for key in invalid_config["config"].keys():
                test_env.unset(key)

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_dynamic_configuration_updates(self, real_services_fixture, isolated_env):
        """Test dynamic configuration updates without service restart."""
        
        test_env = get_env()
        
        # Set initial configuration
        initial_config = {
            "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
            "REDIS_URL": "redis://localhost:6379",
            "JWT_SECRET_KEY": "initial_jwt_secret",
            "LOG_LEVEL": "INFO",
            "ENVIRONMENT": "test"
        }
        
        for key, value in initial_config.items():
            test_env.set(key, value, source="dynamic_config_test")
        
        # Initialize configuration manager
        config_manager = ConfigurationManager()
        await config_manager.initialize()
        
        # Load initial configuration
        current_config = await config_manager.get_current_configuration()
        assert current_config.logging.level == "INFO"
        assert current_config.jwt.secret_key == "initial_jwt_secret"
        
        # Create configuration update
        config_updates = {
            "LOG_LEVEL": "DEBUG",
            "JWT_SECRET_KEY": "updated_jwt_secret_key",
            "NEW_FEATURE_FLAG": "enabled"
        }
        
        # Apply configuration updates dynamically
        update_results = []
        for key, new_value in config_updates.items():
            test_env.set(key, new_value, source="dynamic_update")
            result = await config_manager.update_configuration(key, new_value)
            update_results.append((key, result))
        
        # Verify updates were applied
        updated_config = await config_manager.get_current_configuration()
        assert updated_config.logging.level == "DEBUG", "Log level was not updated dynamically"
        assert updated_config.jwt.secret_key == "updated_jwt_secret_key", "JWT secret was not updated"
        
        # Verify configuration change notifications were sent
        change_notifications = await config_manager.get_configuration_changes()
        assert len(change_notifications) >= len(config_updates)
        
        # Check specific change notifications
        change_keys = [change["key"] for change in change_notifications]
        for key in config_updates.keys():
            assert key in change_keys, f"No change notification for {key}"
        
        # Test configuration rollback capability
        rollback_config = {
            "LOG_LEVEL": "INFO",  # Rollback to original
            "JWT_SECRET_KEY": "initial_jwt_secret"  # Rollback to original
        }
        
        for key, rollback_value in rollback_config.items():
            await config_manager.rollback_configuration(key, rollback_value)
        
        # Verify rollback worked
        final_config = await config_manager.get_current_configuration()
        assert final_config.logging.level == "INFO", "Configuration rollback failed for LOG_LEVEL"
        assert final_config.jwt.secret_key == "initial_jwt_secret", "Configuration rollback failed for JWT_SECRET_KEY"
        
        # Cleanup
        for key in list(initial_config.keys()) + list(config_updates.keys()):
            test_env.unset(key)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_service_configuration_consistency(self, real_services_fixture, isolated_env):
        """Test configuration consistency across multiple services (backend, auth, analytics)."""
        
        test_env = get_env()
        
        # Shared configuration that should be consistent across services
        shared_config = {
            "JWT_SECRET_KEY": "shared_jwt_secret_across_services",
            "REDIS_URL": "redis://localhost:6379",
            "LOG_LEVEL": "INFO",
            "ENVIRONMENT": "test"
        }
        
        # Service-specific configurations
        service_configs = {
            "backend": {
                "DATABASE_URL": "postgresql://backend:pass@localhost:5434/backend_db",
                "BACKEND_PORT": "8000",
                "SERVICE_NAME": "netra_backend"
            },
            "auth": {
                "DATABASE_URL": "postgresql://auth:pass@localhost:5434/auth_db",
                "AUTH_PORT": "8081", 
                "SERVICE_NAME": "auth_service"
            },
            "analytics": {
                "CLICKHOUSE_URL": "http://localhost:8123",
                "ANALYTICS_PORT": "8002",
                "SERVICE_NAME": "analytics_service"
            }
        }
        
        # Set shared configuration
        for key, value in shared_config.items():
            test_env.set(key, value, source="shared_config")
        
        # Test configuration consistency across services
        service_config_managers = {}
        
        for service_name, service_specific_config in service_configs.items():
            # Set service-specific configuration
            for key, value in service_specific_config.items():
                test_env.set(key, value, source=f"{service_name}_config")
            
            # Create configuration manager for this service
            config_loader = EnvironmentConfigLoader(
                environment="test",
                service_name=service_name
            )
            config_manager = ConfigurationService(config_loader)
            service_config_managers[service_name] = config_manager
            
            # Load configuration for service
            service_config = await config_manager.load_configuration()
            
            # Verify shared configuration is consistent across services
            assert service_config.jwt.secret_key == shared_config["JWT_SECRET_KEY"], \
                f"JWT secret inconsistent for {service_name}"
            assert service_config.redis.url == shared_config["REDIS_URL"], \
                f"Redis URL inconsistent for {service_name}"
            assert service_config.logging.level == shared_config["LOG_LEVEL"], \
                f"Log level inconsistent for {service_name}"
            
            # Verify service-specific configuration is isolated
            assert service_config.service_name == service_specific_config["SERVICE_NAME"], \
                f"Service name incorrect for {service_name}"
        
        # Test configuration update propagation across services
        updated_shared_value = "updated_shared_jwt_secret"
        test_env.set("JWT_SECRET_KEY", updated_shared_value, source="shared_update")
        
        # Update should propagate to all services
        for service_name, config_manager in service_config_managers.items():
            updated_config = await config_manager.reload_configuration()
            assert updated_config.jwt.secret_key == updated_shared_value, \
                f"Configuration update did not propagate to {service_name}"
        
        # Verify service isolation - changing one service's config doesn't affect others
        test_env.set("BACKEND_PORT", "8001", source="backend_specific_change")
        
        # Reload backend config
        backend_config = await service_config_managers["backend"].reload_configuration()
        auth_config = await service_config_managers["auth"].reload_configuration()
        
        # Backend should see the change, auth should not
        assert backend_config.backend_port == "8001", "Backend config change not applied"
        assert not hasattr(auth_config, 'backend_port'), "Backend config leaked to auth service"
        
        # Cleanup
        all_keys = list(shared_config.keys())
        for service_config in service_configs.values():
            all_keys.extend(service_config.keys())
        
        for key in set(all_keys):
            test_env.unset(key)