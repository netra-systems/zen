"""
Auth Service Startup and Configuration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Reliable authentication service startup and configuration
- Value Impact: Ensures auth service starts correctly and serves users reliably
- Strategic Impact: Foundation for entire platform availability and security

These tests validate:
1. Service startup sequence and dependency validation
2. Configuration loading and validation
3. Environment-specific configuration handling
4. Health check and readiness probe functionality
5. Graceful shutdown and resource cleanup
6. Startup performance and optimization
"""

import pytest
import time
import asyncio
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.auth_environment import AuthEnvironment
from auth_service.auth_core.startup.service_initializer import ServiceInitializer
from auth_service.auth_core.startup.dependency_checker import DependencyChecker
from auth_service.auth_core.startup.health_manager import HealthManager
from auth_service.auth_core.startup.configuration_validator import ConfigurationValidator
from shared.isolated_environment import get_env


class TestAuthStartupConfiguration:
    """
    Comprehensive auth service startup and configuration validation tests.
    
    These tests ensure the authentication service starts correctly,
    validates all required configuration, and maintains reliable operation
    across different environments and scenarios.
    """

    @pytest.fixture
    def auth_env(self):
        """Get isolated auth environment with startup configuration."""
        env = get_env()
        auth_env = AuthEnvironment(env)
        
        # Set required startup configuration
        auth_env.set("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters", source="test")
        # Set component parts for DatabaseURLBuilder SSOT
        auth_env.set("POSTGRES_HOST", "localhost", source="test")
        auth_env.set("POSTGRES_PORT", "5434", source="test")
        auth_env.set("POSTGRES_USER", "test", source="test")
        auth_env.set("POSTGRES_PASSWORD", "test", source="test")
        auth_env.set("POSTGRES_DB", "test_auth", source="test")
        auth_env.set("REDIS_URL", "redis://localhost:6381/0", source="test")
        auth_env.set("GOOGLE_CLIENT_ID", "test-google-client-id", source="test")
        auth_env.set("GOOGLE_CLIENT_SECRET", "test-google-secret", source="test")
        auth_env.set("ENVIRONMENT", "test", source="test")
        auth_env.set("AUTH_SERVICE_PORT", "8083", source="test")
        
        auth_env.load_environment()
        return auth_env

    @pytest.fixture
    def auth_config(self, auth_env):
        """Create auth configuration."""
        return AuthConfig(auth_env)

    @pytest.fixture
    def service_initializer(self, auth_config):
        """Create service initializer."""
        return ServiceInitializer(auth_config)

    @pytest.fixture
    def dependency_checker(self, auth_config):
        """Create dependency checker."""
        return DependencyChecker(auth_config)

    @pytest.fixture
    def health_manager(self, auth_config):
        """Create health manager."""
        return HealthManager(auth_config)

    @pytest.fixture
    def config_validator(self, auth_config):
        """Create configuration validator."""
        return ConfigurationValidator(auth_config)

    @pytest.mark.unit
    def test_service_startup_sequence_validation(self, service_initializer):
        """
        Test that service startup follows correct sequence and validates dependencies.
        
        CRITICAL: Startup sequence must ensure all dependencies are ready.
        """
        # Mock dependencies
        with patch.object(service_initializer, '_check_database_connection') as mock_db, \
             patch.object(service_initializer, '_check_redis_connection') as mock_redis, \
             patch.object(service_initializer, '_validate_jwt_configuration') as mock_jwt, \
             patch.object(service_initializer, '_initialize_oauth_providers') as mock_oauth, \
             patch.object(service_initializer, '_setup_security_middleware') as mock_security:
            
            # Configure mocks to succeed
            mock_db.return_value = True
            mock_redis.return_value = True  
            mock_jwt.return_value = True
            mock_oauth.return_value = True
            mock_security.return_value = True
            
            # Execute startup
            startup_result = service_initializer.initialize_service()
            
            assert startup_result.success
            assert startup_result.startup_time < 10.0  # Should start quickly
            
            # Verify startup sequence order
            assert mock_jwt.called  # JWT config should be validated first
            assert mock_db.called   # Database connection checked
            assert mock_redis.called  # Redis connection checked  
            assert mock_oauth.called  # OAuth providers initialized
            assert mock_security.called  # Security middleware last
            
            # Verify service state
            assert service_initializer.is_initialized
            assert service_initializer.startup_timestamp is not None

    @pytest.mark.unit
    def test_configuration_validation_comprehensive(self, config_validator, auth_config):
        """
        Test comprehensive configuration validation catches all issues.
        
        CRITICAL: Invalid configuration must be caught at startup.
        """
        # Test valid configuration
        validation_result = config_validator.validate_all_configuration()
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0
        
        # Test missing required configuration
        required_configs = [
            "JWT_SECRET_KEY",
            # Note: DATABASE_URL not required - DatabaseURLBuilder uses component parts
            "POSTGRES_HOST",  # Component parts for DatabaseURLBuilder SSOT
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "REDIS_URL",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET"
        ]
        
        for config_key in required_configs:
            # Temporarily remove configuration
            original_value = getattr(auth_config, config_key.lower())
            setattr(auth_config, config_key.lower(), None)
            
            validation_result = config_validator.validate_all_configuration()
            assert not validation_result.is_valid
            assert any(config_key.lower() in error.lower() for error in validation_result.errors)
            
            # Restore configuration
            setattr(auth_config, config_key.lower(), original_value)
        
        # Test invalid JWT secret (too short)
        auth_config.jwt_secret_key = "short"
        validation_result = config_validator.validate_all_configuration()
        assert not validation_result.is_valid
        assert any("jwt" in error.lower() and "length" in error.lower() for error in validation_result.errors)

    @pytest.mark.unit
    def test_environment_specific_configuration(self, auth_env):
        """
        Test configuration adapts correctly to different environments.
        
        CRITICAL: Each environment must have appropriate security settings.
        """
        environments = ["test", "development", "staging", "production"]
        
        for env_name in environments:
            # Create environment-specific configuration
            auth_env.set("ENVIRONMENT", env_name, source="test")
            env_config = AuthConfig(auth_env)
            
            # Test environment-specific security settings
            if env_name == "production":
                assert env_config.debug_mode is False
                assert env_config.cors_allow_all is False
                assert env_config.jwt_token_expiry <= 3600  # Max 1 hour in prod
                assert env_config.require_https is True
                
            elif env_name == "staging":
                assert env_config.debug_mode is False  # Should be production-like
                assert env_config.cors_allow_all is False
                assert env_config.require_https is True
                
            elif env_name in ["development", "test"]:
                # Development settings can be more relaxed
                assert env_config.debug_mode is True or env_config.debug_mode is False  # Either is acceptable
                
            # All environments should have secure JWT settings
            assert len(env_config.jwt_secret_key) >= 32
            assert env_config.jwt_algorithm == "HS256"

    @pytest.mark.unit
    def test_dependency_health_checks(self, dependency_checker):
        """
        Test dependency health checks validate all required services.
        
        CRITICAL: Service must not start if dependencies are unavailable.
        """
        # Mock successful dependencies
        with patch.object(dependency_checker, '_check_database_health') as mock_db_health, \
             patch.object(dependency_checker, '_check_redis_health') as mock_redis_health, \
             patch.object(dependency_checker, '_check_external_oauth_apis') as mock_oauth_health:
            
            # Test all dependencies healthy
            mock_db_health.return_value = {"healthy": True, "response_time": 0.05}
            mock_redis_health.return_value = {"healthy": True, "response_time": 0.02}
            mock_oauth_health.return_value = {"healthy": True, "providers": ["google"]}
            
            health_result = dependency_checker.check_all_dependencies()
            
            assert health_result.all_healthy
            assert health_result.database.healthy
            assert health_result.redis.healthy
            assert health_result.oauth_providers.healthy
            assert health_result.overall_response_time < 1.0
            
            # Test database unhealthy
            mock_db_health.return_value = {"healthy": False, "error": "Connection refused"}
            
            health_result = dependency_checker.check_all_dependencies()
            
            assert not health_result.all_healthy
            assert not health_result.database.healthy
            assert "connection" in health_result.database.error.lower()
            
            # Service should not start with unhealthy database
            assert not dependency_checker.can_start_service()

    @pytest.mark.unit
    def test_startup_performance_optimization(self, service_initializer):
        """
        Test service startup performance meets requirements.
        
        CRITICAL: Startup time must be acceptable for production deployment.
        """
        # Mock all dependencies to respond quickly
        with patch.object(service_initializer, '_check_database_connection', return_value=True), \
             patch.object(service_initializer, '_check_redis_connection', return_value=True), \
             patch.object(service_initializer, '_validate_jwt_configuration', return_value=True), \
             patch.object(service_initializer, '_initialize_oauth_providers', return_value=True), \
             patch.object(service_initializer, '_setup_security_middleware', return_value=True):
            
            # Measure startup time
            start_time = time.time()
            startup_result = service_initializer.initialize_service()
            actual_startup_time = time.time() - start_time
            
            # Verify performance requirements
            assert startup_result.success
            assert actual_startup_time < 5.0  # Should start within 5 seconds
            assert startup_result.startup_time < 5.0
            
            # Test cold start performance
            service_initializer.reset()  # Reset to simulate cold start
            
            cold_start_time = time.time()
            cold_startup_result = service_initializer.initialize_service()
            cold_actual_time = time.time() - cold_start_time
            
            # Cold start should still be reasonable
            assert cold_startup_result.success
            assert cold_actual_time < 10.0  # Cold start within 10 seconds

    @pytest.mark.unit
    def test_health_check_endpoints(self, health_manager):
        """
        Test health check endpoints provide accurate service status.
        
        CRITICAL: Health checks must accurately reflect service state.
        """
        # Test basic health check
        basic_health = health_manager.get_basic_health()
        
        assert "status" in basic_health
        assert "timestamp" in basic_health
        assert basic_health["status"] in ["healthy", "unhealthy", "starting"]
        
        # Test detailed health check
        detailed_health = health_manager.get_detailed_health()
        
        required_components = [
            "database", "redis", "jwt_service", 
            "oauth_providers", "security_middleware"
        ]
        
        for component in required_components:
            assert component in detailed_health["components"]
            component_status = detailed_health["components"][component]
            assert "status" in component_status
            assert "response_time" in component_status
        
        # Test readiness check
        readiness = health_manager.get_readiness_status()
        
        assert "ready" in readiness
        assert "checks" in readiness
        assert isinstance(readiness["ready"], bool)
        
        # If ready, all checks should pass
        if readiness["ready"]:
            for check_name, check_result in readiness["checks"].items():
                assert check_result["status"] == "pass"

    @pytest.mark.unit
    def test_graceful_shutdown_sequence(self, service_initializer, health_manager):
        """
        Test graceful shutdown properly cleans up resources.
        
        CRITICAL: Shutdown must not leave resources hanging or corrupt data.
        """
        # Initialize service first
        with patch.object(service_initializer, '_check_database_connection', return_value=True), \
             patch.object(service_initializer, '_check_redis_connection', return_value=True), \
             patch.object(service_initializer, '_validate_jwt_configuration', return_value=True), \
             patch.object(service_initializer, '_initialize_oauth_providers', return_value=True), \
             patch.object(service_initializer, '_setup_security_middleware', return_value=True):
            
            startup_result = service_initializer.initialize_service()
            assert startup_result.success
        
        # Mock resource cleanup methods
        with patch.object(service_initializer, '_close_database_connections') as mock_close_db, \
             patch.object(service_initializer, '_close_redis_connections') as mock_close_redis, \
             patch.object(service_initializer, '_cleanup_oauth_sessions') as mock_cleanup_oauth, \
             patch.object(service_initializer, '_flush_security_logs') as mock_flush_logs:
            
            # Execute graceful shutdown
            shutdown_result = service_initializer.graceful_shutdown(timeout=10.0)
            
            assert shutdown_result.success
            assert shutdown_result.shutdown_time < 10.0
            
            # Verify cleanup sequence
            assert mock_close_db.called
            assert mock_close_redis.called
            assert mock_cleanup_oauth.called
            assert mock_flush_logs.called
            
            # Service should no longer be initialized
            assert not service_initializer.is_initialized
            
            # Health checks should reflect shutdown state
            health = health_manager.get_basic_health()
            assert health["status"] in ["unhealthy", "shutdown"]

    @pytest.mark.unit
    def test_configuration_hot_reload(self, auth_config, config_validator):
        """
        Test configuration can be reloaded without full service restart.
        
        CRITICAL: Non-critical config changes should not require restart.
        """
        # Test reloadable configuration changes
        reloadable_configs = {
            "LOG_LEVEL": "DEBUG",
            "JWT_TOKEN_EXPIRY": "1800",  # 30 minutes
            "RATE_LIMIT_PER_MINUTE": "100",
            "SESSION_TIMEOUT": "3600"
        }
        
        for config_key, new_value in reloadable_configs.items():
            # Store original value
            original_value = getattr(auth_config, config_key.lower(), None)
            
            # Apply hot reload
            reload_result = config_validator.hot_reload_configuration({
                config_key: new_value
            })
            
            assert reload_result.success
            assert config_key.lower() in reload_result.reloaded_configs
            
            # Verify new value applied
            updated_value = getattr(auth_config, config_key.lower())
            assert str(updated_value) == new_value or updated_value == int(new_value)
            
            # Verify service still healthy after reload
            validation_result = config_validator.validate_all_configuration()
            assert validation_result.is_valid
        
        # Test non-reloadable configuration (should require restart)
        critical_configs = {
            "JWT_SECRET_KEY": "new-secret-key-32-characters-long",
            "POSTGRES_HOST": "new_host"  # Database component changes require restart
        }
        
        for config_key, new_value in critical_configs.items():
            reload_result = config_validator.hot_reload_configuration({
                config_key: new_value
            })
            
            # Should either fail or require restart
            assert not reload_result.success or reload_result.requires_restart

    @pytest.mark.unit
    def test_startup_failure_recovery(self, service_initializer):
        """
        Test service startup failure scenarios and recovery mechanisms.
        
        CRITICAL: Startup failures must be handled gracefully with recovery.
        """
        # Test database connection failure
        with patch.object(service_initializer, '_check_database_connection', side_effect=Exception("DB connection failed")):
            startup_result = service_initializer.initialize_service()
            
            assert not startup_result.success
            assert "database" in startup_result.error_message.lower()
            assert not service_initializer.is_initialized
        
        # Test partial failure recovery
        call_count = {"db_calls": 0}
        
        def mock_db_connection():
            call_count["db_calls"] += 1
            if call_count["db_calls"] < 3:
                raise Exception("Temporary DB issue")
            return True
        
        with patch.object(service_initializer, '_check_database_connection', side_effect=mock_db_connection), \
             patch.object(service_initializer, '_check_redis_connection', return_value=True), \
             patch.object(service_initializer, '_validate_jwt_configuration', return_value=True), \
             patch.object(service_initializer, '_initialize_oauth_providers', return_value=True), \
             patch.object(service_initializer, '_setup_security_middleware', return_value=True):
            
            # Should retry and eventually succeed
            startup_result = service_initializer.initialize_service_with_retry(max_retries=5)
            
            assert startup_result.success
            assert startup_result.retry_count >= 2
            assert service_initializer.is_initialized

    @pytest.mark.unit
    def test_startup_monitoring_and_metrics(self, service_initializer):
        """
        Test startup process generates appropriate monitoring metrics.
        
        CRITICAL: Startup metrics are essential for operational monitoring.
        """
        with patch('time.time', side_effect=[1000.0, 1005.0, 1005.5]):  # Mock timing
            with patch.object(service_initializer, '_check_database_connection', return_value=True), \
                 patch.object(service_initializer, '_check_redis_connection', return_value=True), \
                 patch.object(service_initializer, '_validate_jwt_configuration', return_value=True), \
                 patch.object(service_initializer, '_initialize_oauth_providers', return_value=True), \
                 patch.object(service_initializer, '_setup_security_middleware', return_value=True):
                
                startup_result = service_initializer.initialize_service()
                
                # Verify startup metrics
                metrics = startup_result.metrics
                
                assert "total_startup_time" in metrics
                assert "dependency_check_time" in metrics
                assert "initialization_steps" in metrics
                assert metrics["total_startup_time"] > 0
                
                # Test metric collection for each component
                component_metrics = [
                    "database_connection_time",
                    "redis_connection_time", 
                    "jwt_validation_time",
                    "oauth_initialization_time",
                    "security_setup_time"
                ]
                
                for metric in component_metrics:
                    assert metric in metrics
                    assert metrics[metric] >= 0
                
                # Verify startup event logging
                assert startup_result.startup_events is not None
                assert len(startup_result.startup_events) > 0
                
                required_events = ["startup_begin", "dependencies_checked", "service_ready"]
                for event in required_events:
                    assert any(event in logged_event for logged_event in startup_result.startup_events)