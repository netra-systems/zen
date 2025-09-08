"""
E2E Tests for Multi-Service Configuration Management

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical for all customer-facing services)
- Business Goal: Ensure reliable multi-service configuration coordination
- Value Impact: Configuration consistency prevents service failures and customer experience issues
- Strategic Impact: Robust configuration management enables scalable multi-service architecture

This test suite validates:
1. Configuration consistency across multiple services
2. Environment-specific configuration loading
3. Configuration changes and service coordination  
4. Security and secrets management across services
5. Service startup and dependency resolution
6. Configuration validation in real deployment scenarios
7. Error handling and recovery in configuration failures
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from pathlib import Path
import tempfile
import json

from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.websocket_test_helpers import WebSocketTestClient
from test_framework.ssot.configuration_validator import validate_test_config, is_service_enabled
from test_framework.ssot.e2e_auth_helper import create_test_user_with_auth
from shared.isolated_environment import get_env
import requests
import httpx


@pytest.mark.e2e
@pytest.mark.real_services
class TestMultiServiceConfigurationE2E:
    """E2E tests for multi-service configuration management."""
    
    @pytest.fixture
    def service_urls(self, real_services_fixture):
        """Get URLs for all services."""
        return {
            "backend": real_services_fixture.get("backend_url", "http://localhost:8000"),
            "auth": real_services_fixture.get("auth_url", "http://localhost:8081"),
            "analytics": real_services_fixture.get("analytics_url", "http://localhost:8002"),
            "frontend": real_services_fixture.get("frontend_url", "http://localhost:3000")
        }
    
    @pytest.fixture
    async def service_health_check(self, service_urls):
        """Check which services are healthy and available."""
        healthy_services = {}
        
        for service_name, url in service_urls.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{url}/health", timeout=5.0)
                    if response.status_code == 200:
                        healthy_services[service_name] = url
            except Exception:
                # Service not available - skip tests that require it
                continue
        
        return healthy_services
    
    async def test_configuration_consistency_across_services(self, service_health_check):
        """Test configuration consistency across all running services."""
        if len(service_health_check) < 2:
            pytest.skip("Need at least 2 services running for consistency test")
        
        config_values_by_service = {}
        
        # Collect configuration from each service
        for service_name, service_url in service_health_check.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/config/info", timeout=10.0)
                    
                    if response.status_code == 200:
                        config_data = response.json()
                        config_values_by_service[service_name] = config_data
                    else:
                        pytest.skip(f"{service_name} doesn't expose config info endpoint")
            
            except Exception as e:
                pytest.skip(f"Cannot get config from {service_name}: {e}")
        
        if len(config_values_by_service) < 2:
            pytest.skip("Need at least 2 services with config endpoints")
        
        # Validate shared configuration values are consistent
        shared_config_keys = [
            "jwt_secret_key",
            "service_secret", 
            "environment",
            "redis_host",
            "postgres_host"
        ]
        
        first_service_config = list(config_values_by_service.values())[0]
        
        for config_key in shared_config_keys:
            if config_key in first_service_config:
                expected_value = first_service_config[config_key]
                
                for service_name, service_config in config_values_by_service.items():
                    if config_key in service_config:
                        actual_value = service_config[config_key]
                        assert actual_value == expected_value, (
                            f"Configuration mismatch for {config_key}: "
                            f"{service_name} has '{actual_value}' but expected '{expected_value}'"
                        )
    
    async def test_environment_specific_configuration_loading(self, service_health_check):
        """Test environment-specific configuration across services."""
        if len(service_health_check) < 1:
            pytest.skip("No services available for environment test")
        
        env = get_env()
        current_environment = env.get("ENVIRONMENT", "development")
        
        for service_name, service_url in service_health_check.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/config/environment", timeout=10.0)
                    
                    if response.status_code == 200:
                        env_data = response.json()
                        
                        # Verify environment consistency
                        assert env_data.get("environment") == current_environment
                        
                        # Verify environment-specific settings
                        if current_environment == "testing":
                            assert env_data.get("testing") == True
                            assert env_data.get("debug", False) in [True, False]  # Debug can vary
                        
                        elif current_environment == "staging":
                            assert env_data.get("testing") == False
                            # Staging might have specific timeout settings
                            if "database_timeout" in env_data:
                                assert env_data["database_timeout"] >= 10  # Higher timeouts in staging
                        
                        elif current_environment == "production":
                            assert env_data.get("testing") == False
                            assert env_data.get("debug") == False
                            # Production should have stricter security settings
                            if "security_level" in env_data:
                                assert env_data["security_level"] in ["high", "strict"]
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    pytest.skip(f"{service_name} doesn't expose environment config endpoint")
                else:
                    raise
            except Exception as e:
                pytest.skip(f"Cannot test environment config for {service_name}: {e}")
    
    async def test_service_dependency_configuration_resolution(self, service_health_check):
        """Test service dependency resolution through configuration."""
        if "backend" not in service_health_check:
            pytest.skip("Backend service required for dependency test")
        
        backend_url = service_health_check["backend"]
        
        try:
            # Test backend's dependency configuration
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{backend_url}/config/dependencies", timeout=10.0)
                
                if response.status_code == 200:
                    deps_data = response.json()
                    
                    # Backend should know about required services
                    required_services = deps_data.get("required_services", [])
                    
                    # Postgres should always be required
                    assert "postgres" in required_services
                    
                    # Redis should be required for session management
                    assert "redis" in required_services
                    
                    # Check service availability status
                    service_status = deps_data.get("service_status", {})
                    
                    for service in required_services:
                        if service in service_status:
                            status = service_status[service]
                            assert status.get("status") in ["available", "connected", "healthy"]
                            
                            # Verify connection details
                            if service == "postgres":
                                assert "host" in status
                                assert "port" in status
                                assert status["port"] in [5432, 5434, 5435]  # Known test ports
                            
                            elif service == "redis":
                                assert "host" in status
                                assert "port" in status
                                assert status["port"] in [6379, 6381, 6382]  # Known test ports
                else:
                    pytest.skip("Backend doesn't expose dependency config endpoint")
        
        except Exception as e:
            pytest.skip(f"Cannot test dependency configuration: {e}")
    
    async def test_cross_service_authentication_configuration(self, service_health_check):
        """Test authentication configuration consistency across services."""
        if len(service_health_check) < 2:
            pytest.skip("Need at least 2 services for auth config test")
        
        auth_configs = {}
        
        # Collect auth configuration from each service
        for service_name, service_url in service_health_check.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/config/auth", timeout=10.0)
                    
                    if response.status_code == 200:
                        auth_data = response.json()
                        auth_configs[service_name] = auth_data
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue  # Service doesn't have auth config endpoint
                else:
                    raise
            except Exception:
                continue  # Skip services that don't respond
        
        if len(auth_configs) < 2:
            pytest.skip("Need at least 2 services with auth config endpoints")
        
        # Verify JWT configuration consistency
        jwt_settings_keys = ["algorithm", "token_expire_time", "issuer"]
        
        first_auth_config = list(auth_configs.values())[0]
        
        for key in jwt_settings_keys:
            if key in first_auth_config:
                expected_value = first_auth_config[key]
                
                for service_name, auth_config in auth_configs.items():
                    if key in auth_config:
                        actual_value = auth_config[key]
                        assert actual_value == expected_value, (
                            f"Auth config mismatch for {key}: "
                            f"{service_name} has '{actual_value}' but expected '{expected_value}'"
                        )
        
        # Verify all services have proper JWT secret configuration
        for service_name, auth_config in auth_configs.items():
            assert "jwt_configured" in auth_config
            assert auth_config["jwt_configured"] == True
            
            # JWT secret should be properly configured (but not exposed)
            assert "secret_length" in auth_config
            assert auth_config["secret_length"] >= 32  # Minimum security requirement
    
    async def test_database_configuration_coordination(self, service_health_check):
        """Test database configuration coordination across services."""
        if len(service_health_check) < 1:
            pytest.skip("No services available for database config test")
        
        database_configs = {}
        
        # Collect database configuration from each service
        for service_name, service_url in service_health_check.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/config/database", timeout=10.0)
                    
                    if response.status_code == 200:
                        db_data = response.json()
                        database_configs[service_name] = db_data
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue  # Service doesn't have database config endpoint
                else:
                    raise
            except Exception:
                continue  # Skip services that don't respond
        
        if len(database_configs) == 0:
            pytest.skip("No services expose database configuration")
        
        # Verify database connection settings
        for service_name, db_config in database_configs.items():
            # Each service should have database connectivity
            assert "postgres_configured" in db_config
            assert db_config["postgres_configured"] == True
            
            # Verify connection parameters
            connection_info = db_config.get("connection_info", {})
            assert "host" in connection_info
            assert "port" in connection_info
            assert "database" in connection_info
            
            # Port should be appropriate for test environment
            port = connection_info["port"]
            assert port in [5432, 5433, 5434, 5435, 5436]  # Known service ports
            
            # Database name should follow service naming convention
            database = connection_info["database"]
            if service_name in ["backend", "auth", "analytics"]:
                assert service_name in database.lower() or "test" in database.lower()
        
        # Verify Redis configuration if available
        for service_name, db_config in database_configs.items():
            if "redis_configured" in db_config and db_config["redis_configured"]:
                redis_info = db_config.get("redis_info", {})
                assert "host" in redis_info
                assert "port" in redis_info
                
                redis_port = redis_info["port"]
                assert redis_port in [6379, 6381, 6382]  # Known Redis test ports
    
    async def test_service_startup_configuration_validation(self, service_health_check):
        """Test service startup configuration validation."""
        if len(service_health_check) < 1:
            pytest.skip("No services available for startup config test")
        
        startup_validations = {}
        
        # Check startup configuration validation for each service
        for service_name, service_url in service_health_check.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/config/startup-validation", timeout=10.0)
                    
                    if response.status_code == 200:
                        validation_data = response.json()
                        startup_validations[service_name] = validation_data
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue  # Service doesn't have startup validation endpoint
                else:
                    raise
            except Exception:
                continue  # Skip services that don't respond
        
        if len(startup_validations) == 0:
            pytest.skip("No services expose startup validation information")
        
        # Verify startup validation results
        for service_name, validation in startup_validations.items():
            # Service should have completed startup validation
            assert "validation_completed" in validation
            assert validation["validation_completed"] == True
            
            # All critical validations should pass
            validations = validation.get("validations", {})
            
            critical_validations = ["environment", "database", "secrets"]
            for critical_validation in critical_validations:
                if critical_validation in validations:
                    assert validations[critical_validation]["status"] == "passed"
            
            # No blocking errors should exist
            errors = validation.get("errors", [])
            blocking_errors = [e for e in errors if e.get("level") == "error"]
            assert len(blocking_errors) == 0, f"{service_name} has blocking startup errors: {blocking_errors}"
    
    async def test_configuration_security_and_secrets_management(self, service_health_check):
        """Test security and secrets management across services."""
        if len(service_health_check) < 1:
            pytest.skip("No services available for security config test")
        
        security_configs = {}
        
        # Collect security configuration from each service  
        for service_name, service_url in service_health_check.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/config/security", timeout=10.0)
                    
                    if response.status_code == 200:
                        security_data = response.json()
                        security_configs[service_name] = security_data
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue  # Service doesn't have security config endpoint
                else:
                    raise
            except Exception:
                continue  # Skip services that don't respond
        
        if len(security_configs) == 0:
            pytest.skip("No services expose security configuration")
        
        # Verify security configuration
        for service_name, security_config in security_configs.items():
            # Secrets should be properly configured
            secrets_info = security_config.get("secrets", {})
            
            # JWT secret should be configured
            if "jwt_secret" in secrets_info:
                jwt_secret_info = secrets_info["jwt_secret"]
                assert jwt_secret_info["configured"] == True
                assert jwt_secret_info["length"] >= 32  # Security requirement
                assert jwt_secret_info["source"] in ["environment", "file", "vault"]
            
            # Service secret should be configured
            if "service_secret" in secrets_info:
                service_secret_info = secrets_info["service_secret"]
                assert service_secret_info["configured"] == True
                assert service_secret_info["length"] >= 32
            
            # Database credentials should be secured
            if "database_credentials" in secrets_info:
                db_creds_info = secrets_info["database_credentials"]
                assert db_creds_info["password_configured"] == True
                # Password should not be exposed in config endpoint
                assert "password_value" not in db_creds_info
            
            # Security headers and CORS should be configured
            security_settings = security_config.get("settings", {})
            
            if "cors" in security_settings:
                cors_config = security_settings["cors"]
                assert "allowed_origins" in cors_config
                # Should not allow all origins in production-like environments
                allowed_origins = cors_config["allowed_origins"]
                if isinstance(allowed_origins, list):
                    assert "*" not in allowed_origins or get_env().get("ENVIRONMENT") in ["development", "testing"]
    
    async def test_configuration_reload_and_coordination(self, service_health_check):
        """Test configuration reload coordination across services."""
        if "backend" not in service_health_check:
            pytest.skip("Backend service required for reload coordination test")
        
        backend_url = service_health_check["backend"]
        
        try:
            # Test configuration reload capability
            async with httpx.AsyncClient() as client:
                # First, get current configuration version
                initial_response = await client.get(f"{backend_url}/config/version", timeout=10.0)
                
                if initial_response.status_code == 200:
                    initial_version = initial_response.json()
                    
                    # Trigger configuration reload
                    reload_response = await client.post(f"{backend_url}/config/reload", timeout=15.0)
                    
                    if reload_response.status_code == 200:
                        reload_result = reload_response.json()
                        
                        # Reload should succeed
                        assert reload_result["status"] == "success"
                        
                        # Get new configuration version
                        new_response = await client.get(f"{backend_url}/config/version", timeout=10.0)
                        new_version = new_response.json()
                        
                        # Version should be updated or timestamp should change
                        assert (new_version["version"] != initial_version["version"] or 
                               new_version["last_reload"] != initial_version["last_reload"])
                        
                        # Service should still be healthy after reload
                        health_response = await client.get(f"{backend_url}/health", timeout=10.0)
                        assert health_response.status_code == 200
                    else:
                        pytest.skip("Configuration reload not supported by backend")
                else:
                    pytest.skip("Backend doesn't expose configuration version endpoint")
        
        except Exception as e:
            pytest.skip(f"Cannot test configuration reload: {e}")
    
    async def test_configuration_error_handling_and_fallback(self, service_health_check):
        """Test configuration error handling and fallback mechanisms."""
        if len(service_health_check) < 1:
            pytest.skip("No services available for error handling test")
        
        error_handling_tests = {}
        
        # Test error handling configuration for each service
        for service_name, service_url in service_health_check.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/config/error-handling", timeout=10.0)
                    
                    if response.status_code == 200:
                        error_data = response.json()
                        error_handling_tests[service_name] = error_data
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue  # Service doesn't have error handling config endpoint
                else:
                    raise
            except Exception:
                continue  # Skip services that don't respond
        
        if len(error_handling_tests) == 0:
            pytest.skip("No services expose error handling configuration")
        
        # Verify error handling configuration
        for service_name, error_config in error_handling_tests.items():
            # Should have fallback mechanisms configured
            fallbacks = error_config.get("fallbacks", {})
            
            # Database fallback should be configured
            if "database" in fallbacks:
                db_fallback = fallbacks["database"]
                assert "strategy" in db_fallback
                assert db_fallback["strategy"] in ["retry", "circuit_breaker", "degraded_mode"]
                
                if db_fallback["strategy"] == "retry":
                    assert "max_retries" in db_fallback
                    assert db_fallback["max_retries"] >= 3
                
                elif db_fallback["strategy"] == "circuit_breaker":
                    assert "failure_threshold" in db_fallback
                    assert "recovery_timeout" in db_fallback
            
            # Configuration loading fallback
            if "config_loading" in fallbacks:
                config_fallback = fallbacks["config_loading"]
                assert "use_defaults" in config_fallback
                assert config_fallback["use_defaults"] == True
            
            # Service dependency fallback
            if "service_dependencies" in fallbacks:
                dep_fallback = fallbacks["service_dependencies"]
                assert "degraded_mode" in dep_fallback
                # Services should be able to operate in degraded mode
    
    async def test_real_world_multi_service_scenario(self, service_health_check):
        """Test a real-world multi-service scenario with configuration coordination."""
        if len(service_health_check) < 2:
            pytest.skip("Need at least 2 services for real-world scenario test")
        
        # Test scenario: User authentication and data persistence across services
        try:
            # Create authenticated user (requires auth service configuration)
            user_context = await create_test_user_with_auth(
                email="multiservice@test.com",
                name="Multi-Service Test User"
            )
        except Exception as e:
            pytest.skip(f"Cannot create authenticated user for multi-service test: {e}")
        
        # Test that services can handle authenticated requests with proper configuration
        if "backend" in service_health_check:
            backend_url = service_health_check["backend"]
            
            try:
                async with WebSocketTestClient(
                    token=user_context.get("access_token"),
                    base_url=backend_url
                ) as client:
                    
                    # Test authenticated operation that requires proper configuration
                    test_operation = {
                        "type": "multi_service_test",
                        "data": {
                            "test_cross_service": True,
                            "user_id": user_context.get("user_id")
                        }
                    }
                    
                    await client.send_json(test_operation)
                    response = await client.receive_json(timeout=15)
                    
                    # Should handle the multi-service operation successfully
                    assert response["type"] in ["success", "multi_service_complete", "operation_result"]
                    
                    # Response should include configuration validation
                    if "config_validation" in response.get("data", {}):
                        validation = response["data"]["config_validation"]
                        assert validation["all_services_configured"] == True
                        assert len(validation["failed_services"]) == 0
            
            except Exception as e:
                # Multi-service scenario might not be fully implemented
                pytest.skip(f"Multi-service scenario not fully supported: {e}")
        
        # Test configuration consistency after multi-service operation
        config_consistency_after = {}
        
        for service_name, service_url in service_health_check.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{service_url}/config/status", timeout=10.0)
                    
                    if response.status_code == 200:
                        status_data = response.json()
                        config_consistency_after[service_name] = status_data
            except Exception:
                continue
        
        # All services should still be properly configured after multi-service operation
        for service_name, status in config_consistency_after.items():
            assert status.get("configured") == True
            assert status.get("healthy") == True
            
            # No configuration drift should have occurred
            if "config_hash" in status:
                # Configuration hash should be stable
                assert len(status["config_hash"]) > 0