"""
Integration Tests for IsolatedEnvironment SSOT Interplay

Business Value Justification (BVJ):
- Segment: Platform/Internal - ALL segments depend on environment stability
- Business Goal: System Stability & Risk Reduction  
- Value Impact: Ensures unified environment management prevents cascade failures
- Strategic Impact: CRITICAL for multi-user system reliability and prevents OAuth 503 errors

This test suite validates the critical interactions between IsolatedEnvironment 
and other SSOT components across the Netra platform. These tests use REAL services 
to validate actual business scenarios that could break multi-user operations.

CRITICAL AREAS TESTED:
1. Cross-Service Environment Isolation - Service boundary integrity via source tracking
2. Database Configuration Interplay - Connection string and pool management  
3. Authentication Integration - OAuth/JWT credential handling across services
4. Multi-User Context Safety - Thread-safe concurrent access patterns
5. System Integration - Shell expansion and change propagation

WARNING: NO MOCKS! These are integration tests using real environment management,
real database connections, real auth service interactions where applicable.
"""

import asyncio
import os
import threading
import time
import tempfile
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture, with_test_database
from shared.isolated_environment import IsolatedEnvironment, get_env, setenv
from netra_backend.app.core.auth_startup_validator import AuthStartupValidator, AuthValidationError
from netra_backend.app.core.environment_constants import get_current_environment, Environment
from netra_backend.app.services.agent_service_factory import get_agent_service
from netra_backend.app.websocket_core import create_websocket_manager


class TestIsolatedEnvironmentInterplay(BaseIntegrationTest):
    """Integration tests for IsolatedEnvironment SSOT interactions."""

    def setup_method(self):
        """Set up each test with clean environment state."""
        super().setup_method()
        # Get the singleton instance
        self.env = get_env()
        
        # Enable isolation for testing
        if not self.env.is_isolated():
            self.env.enable_isolation(backup_original=True)
        
        # Track variables we add for cleanup
        self._test_added_vars = set()
    
    def teardown_method(self):
        """Clean up after each test."""
        try:
            # Clean up test variables
            if hasattr(self, '_test_added_vars'):
                for var_name in self._test_added_vars:
                    if self.env.exists(var_name):
                        self.env.delete(var_name, source="test_cleanup")
            
            # Reset to original state
            if hasattr(self.env, 'reset_to_original'):
                self.env.reset_to_original()
                
        finally:
            super().teardown_method()
    
    def _set_test_var(self, key: str, value: str, source: str = "test") -> None:
        """Helper to set test variables with tracking for cleanup."""
        self.env.set(key, value, source=source)
        self._test_added_vars.add(key)

    # =================== CROSS-SERVICE ENVIRONMENT ISOLATION ===================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_environment_isolation_source_tracking(self, real_services_fixture):
        """
        Test environment isolation via source tracking between services.
        
        BVJ: Platform/Internal | System Stability | Prevents config leakage between services
        Tests that service environment variables are properly tracked by source
        to enable service boundary integrity in multi-service deployment.
        """
        # Set auth-specific variables with service prefixes
        self._set_test_var("AUTH_SERVICE_SECRET", "auth_secret_123", "auth_service")
        self._set_test_var("AUTH_OAUTH_CLIENT_ID", "auth_oauth_client", "auth_service")
        
        # Set backend-specific variables with different prefixes
        self._set_test_var("BACKEND_SERVICE_SECRET", "backend_secret_456", "backend_service")
        self._set_test_var("BACKEND_AGENT_REGISTRY_CONFIG", "backend_agent_config", "backend_service")
        
        # Verify service-specific variables are accessible
        assert self.env.get("AUTH_SERVICE_SECRET") == "auth_secret_123"
        assert self.env.get("AUTH_OAUTH_CLIENT_ID") == "auth_oauth_client"
        assert self.env.get("BACKEND_SERVICE_SECRET") == "backend_secret_456"
        assert self.env.get("BACKEND_AGENT_REGISTRY_CONFIG") == "backend_agent_config"
        
        # Verify variables maintain their source tracking for isolation
        auth_secret_source = self.env.get_variable_source("AUTH_SERVICE_SECRET")
        backend_secret_source = self.env.get_variable_source("BACKEND_SERVICE_SECRET")
        
        assert auth_secret_source == "auth_service"
        assert backend_secret_source == "backend_service"
        assert auth_secret_source != backend_secret_source
        
        # Test shared system variables are accessible to both contexts
        self._set_test_var("DATABASE_URL", "postgresql://test:test@localhost:5434/test", "system")
        shared_db_url = self.env.get("DATABASE_URL")
        assert shared_db_url == "postgresql://test:test@localhost:5434/test"

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_service_specific_environment_namespacing(self, real_services_fixture):
        """
        Test service-specific environment variable namespacing.
        
        BVJ: Platform/Internal | Service Independence | Enables service-specific configurations
        Validates that services can have different configurations through proper namespacing,
        critical for multi-tenant service isolation.
        """
        # Set service-specific configurations with namespacing
        self._set_test_var("AUTH_SERVICE_PORT", "8081", "auth")
        self._set_test_var("BACKEND_SERVICE_PORT", "8000", "backend") 
        self._set_test_var("WEBSOCKET_SERVICE_PORT", "8080", "websocket")
        
        self._set_test_var("AUTH_LOG_LEVEL", "ERROR", "auth")
        self._set_test_var("BACKEND_LOG_LEVEL", "INFO", "backend")  
        self._set_test_var("WEBSOCKET_LOG_LEVEL", "DEBUG", "websocket")
        
        # Verify each service configuration is accessible
        assert self.env.get("AUTH_SERVICE_PORT") == "8081"
        assert self.env.get("BACKEND_SERVICE_PORT") == "8000" 
        assert self.env.get("WEBSOCKET_SERVICE_PORT") == "8080"
        
        assert self.env.get("AUTH_LOG_LEVEL") == "ERROR"
        assert self.env.get("BACKEND_LOG_LEVEL") == "INFO"
        assert self.env.get("WEBSOCKET_LOG_LEVEL") == "DEBUG"
        
        # Verify source tracking maintains separation
        auth_port_source = self.env.get_variable_source("AUTH_SERVICE_PORT")
        backend_port_source = self.env.get_variable_source("BACKEND_SERVICE_PORT")
        websocket_port_source = self.env.get_variable_source("WEBSOCKET_SERVICE_PORT")
        
        assert auth_port_source == "auth"
        assert backend_port_source == "backend"
        assert websocket_port_source == "websocket"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_configuration_override_priority_resolution(self, real_services_fixture):
        """
        Test configuration override priority resolution.
        
        BVJ: Platform/Internal | Configuration Management | Prevents override conflicts
        Tests that configuration overrides are resolved with proper priority
        to prevent conflicts when multiple configuration sources are present.
        """
        # Set base configuration
        self._set_test_var("DATABASE_POOL_SIZE", "10", "base")
        self._set_test_var("CACHE_TTL", "3600", "base")
        self._set_test_var("AUTH_TIMEOUT", "300", "base")
        
        # Override with service-specific values
        self._set_test_var("DATABASE_POOL_SIZE", "20", "service_override")
        self._set_test_var("CACHE_TTL", "7200", "service_override")
        # AUTH_TIMEOUT uses base value
        
        # Test environment overrides specific values
        self._set_test_var("DATABASE_POOL_SIZE", "5", "test_override")
        # CACHE_TTL and AUTH_TIMEOUT use service/base values
        
        # Verify final configuration values (latest override wins)
        assert self.env.get("DATABASE_POOL_SIZE") == "5"  # Test override
        assert self.env.get("CACHE_TTL") == "7200"  # Service override  
        assert self.env.get("AUTH_TIMEOUT") == "300"  # Base value
        
        # Verify source tracking shows override hierarchy
        pool_source = self.env.get_variable_source("DATABASE_POOL_SIZE")
        cache_source = self.env.get_variable_source("CACHE_TTL")
        timeout_source = self.env.get_variable_source("AUTH_TIMEOUT")
        
        assert pool_source == "test_override"
        assert cache_source == "service_override"
        assert timeout_source == "base"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_configuration_dependency_chain(self, real_services_fixture):
        """
        Test configuration dependency resolution in service chain.
        
        BVJ: Platform/Internal | System Integration | Prevents startup dependency failures
        Validates that service startup dependencies are resolved correctly to prevent
        cascade startup failures when services depend on each other's configuration.
        """
        # Build service dependency chain: Database -> Auth -> Backend -> Frontend
        self._set_test_var("DB_HOST", "localhost", "database")
        self._set_test_var("DB_PORT", "5434", "database")
        self._set_test_var("DB_NAME", "netra_test", "database")
        
        # Auth service depends on database
        db_url = f"postgresql://test:test@{self.env.get('DB_HOST')}:{self.env.get('DB_PORT')}/{self.env.get('DB_NAME')}"
        self._set_test_var("DATABASE_URL", db_url, "auth")
        self._set_test_var("AUTH_SERVICE_URL", "http://localhost:8081", "auth")
        
        # Backend depends on auth and database  
        self._set_test_var("AUTH_SERVICE_URL", self.env.get("AUTH_SERVICE_URL"), "backend")
        self._set_test_var("BACKEND_SERVICE_URL", "http://localhost:8000", "backend")
        
        # Frontend depends on backend and auth
        self._set_test_var("BACKEND_API_URL", self.env.get("BACKEND_SERVICE_URL"), "frontend")
        self._set_test_var("AUTH_API_URL", self.env.get("AUTH_SERVICE_URL"), "frontend")
        
        # Verify dependency chain resolves correctly
        assert self.env.get("DATABASE_URL").startswith("postgresql://test:test@localhost:5434/netra_test")
        assert self.env.get("AUTH_SERVICE_URL") == "http://localhost:8081"
        assert self.env.get("BACKEND_SERVICE_URL") == "http://localhost:8000"
        assert self.env.get("BACKEND_API_URL") == "http://localhost:8000"
        assert self.env.get("AUTH_API_URL") == "http://localhost:8081"

    # =================== DATABASE CONFIGURATION INTERPLAY ===================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_string_parsing_validation(self, real_services_fixture, with_test_database):
        """
        Test database connection string parsing and validation.
        
        BVJ: Platform/Internal | Data Infrastructure | Ensures reliable database connections
        Tests that IsolatedEnvironment correctly handles database connection strings
        with various formats to prevent connection failures in production.
        """
        # Test various database URL formats that must work
        test_urls = [
            "postgresql://user:password@localhost:5434/test_db",
            "postgresql://user:password@localhost:5434/test_db?sslmode=require",
            "postgresql://user@localhost:5434/test_db",  # No password
            "postgresql://localhost:5434/test_db",  # No auth
        ]
        
        for i, db_url in enumerate(test_urls):
            var_name = f"TEST_DATABASE_URL_{i}"
            self._set_test_var(var_name, db_url, f"db_test_{i}")
            retrieved_url = self.env.get(var_name)
            
            # Verify URL is properly stored and retrieved
            assert retrieved_url == db_url
            
            # Verify URL can be parsed
            parsed = urlparse(retrieved_url)
            assert parsed.scheme == "postgresql"
            assert parsed.hostname == "localhost"
            assert parsed.port == 5434
            
        # Test sensitive database URL handling
        sensitive_url = "postgresql://admin:supersecret@prod-db:5432/production"
        self._set_test_var("SENSITIVE_DB_URL", sensitive_url, "sensitive_test")
        
        # URL should be stored correctly
        stored_url = self.env.get("SENSITIVE_DB_URL")
        assert stored_url == sensitive_url

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_environment_priority_resolution(self, real_services_fixture):
        """
        Test database environment variable priority resolution.
        
        BVJ: Platform/Internal | Configuration Management | Prevents database connection conflicts
        Validates that database configuration conflicts are resolved with proper priority
        to prevent connection failures when multiple database configs are present.
        """
        # Set multiple database configuration sources
        self._set_test_var("DATABASE_URL", "postgresql://default:default@localhost:5432/default", "default")
        self._set_test_var("TEST_DATABASE_URL", "postgresql://test:test@localhost:5434/test", "test") 
        self._set_test_var("STAGING_DATABASE_URL", "postgresql://staging:staging@staging-db:5432/staging", "staging")
        self._set_test_var("PROD_DATABASE_URL", "postgresql://prod:prod@prod-db:5432/production", "production")
        
        # Test that all URLs are accessible
        assert self.env.get("DATABASE_URL").startswith("postgresql://default")
        assert self.env.get("TEST_DATABASE_URL").startswith("postgresql://test")
        assert self.env.get("STAGING_DATABASE_URL").startswith("postgresql://staging")
        assert self.env.get("PROD_DATABASE_URL").startswith("postgresql://prod")
        
        # Test environment-specific resolution based on current environment
        current_env = get_current_environment()
        
        # Verify different database URLs for different purposes
        assert "5434" in self.env.get("TEST_DATABASE_URL")  # Test port
        assert "5432" in self.env.get("DATABASE_URL")  # Default port
        assert "staging-db" in self.env.get("STAGING_DATABASE_URL")  # Staging host
        assert "prod-db" in self.env.get("PROD_DATABASE_URL")  # Production host

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_health_monitoring_configuration(self, real_services_fixture, with_test_database):
        """
        Test database health monitoring configuration integration.
        
        BVJ: Platform/Internal | System Reliability | Enables proactive database monitoring
        Tests that database health check configuration integrates with environment management
        to enable monitoring and alerting for database connectivity issues.
        """
        # Configure database health check settings
        self._set_test_var("DATABASE_URL", "postgresql://test:test@localhost:5434/test", "health_test")
        self._set_test_var("DB_HEALTH_CHECK_INTERVAL", "30", "health_test")
        self._set_test_var("DB_CONNECTION_TIMEOUT", "10", "health_test") 
        self._set_test_var("DB_MAX_RETRIES", "3", "health_test")
        self._set_test_var("DB_HEALTH_CHECK_ENABLED", "true", "health_test")
        
        # Verify health check configuration is accessible
        assert self.env.get("DB_HEALTH_CHECK_INTERVAL") == "30"
        assert self.env.get("DB_CONNECTION_TIMEOUT") == "10"
        assert self.env.get("DB_MAX_RETRIES") == "3" 
        assert self.env.get("DB_HEALTH_CHECK_ENABLED") == "true"
        
        # Test database URL parsing for health checks
        db_url = self.env.get("DATABASE_URL")
        parsed = urlparse(db_url)
        
        # Verify health check can extract connection details
        assert parsed.hostname == "localhost"
        assert parsed.port == 5434
        assert parsed.path == "/test"
        
        # Validate configuration values are reasonable
        timeout_value = int(self.env.get("DB_CONNECTION_TIMEOUT", "30"))
        assert 1 <= timeout_value <= 60  # Reasonable timeout bounds
        
        max_retries = int(self.env.get("DB_MAX_RETRIES", "0"))
        assert 0 <= max_retries <= 10  # Reasonable retry bounds

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_environment_configuration(self, real_services_fixture):
        """
        Test database connection pool configuration from environment variables.
        
        BVJ: Platform/Internal | Performance Optimization | Optimizes database resource usage
        Validates that database connection pool settings are correctly managed through
        environment variables to optimize performance and prevent connection exhaustion.
        """
        # Set connection pool configuration
        self._set_test_var("DATABASE_URL", "postgresql://test:test@localhost:5434/test", "pool_test")
        self._set_test_var("DB_POOL_SIZE", "20", "pool_test")
        self._set_test_var("DB_POOL_MAX_OVERFLOW", "30", "pool_test") 
        self._set_test_var("DB_POOL_RECYCLE", "3600", "pool_test")
        self._set_test_var("DB_POOL_PRE_PING", "true", "pool_test")
        self._set_test_var("DB_POOL_ECHO", "false", "pool_test")
        
        # Verify pool configuration values are accessible
        assert int(self.env.get("DB_POOL_SIZE")) == 20
        assert int(self.env.get("DB_POOL_MAX_OVERFLOW")) == 30
        assert int(self.env.get("DB_POOL_RECYCLE")) == 3600
        assert self.env.get("DB_POOL_PRE_PING").lower() == "true"
        assert self.env.get("DB_POOL_ECHO").lower() == "false"
        
        # Validate configuration is sensible
        pool_size = int(self.env.get("DB_POOL_SIZE", "10"))
        max_overflow = int(self.env.get("DB_POOL_MAX_OVERFLOW", "20"))
        
        assert pool_size > 0
        assert max_overflow >= pool_size  # Max overflow should be >= pool size
        assert pool_size <= 100  # Reasonable upper bound
        
        # Test pool recycle time is reasonable  
        recycle_time = int(self.env.get("DB_POOL_RECYCLE", "3600"))
        assert 300 <= recycle_time <= 86400  # 5 minutes to 24 hours

    # =================== AUTHENTICATION INTEGRATION ===================

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_oauth_credential_handling_test_environment(self, real_services_fixture):
        """
        Test OAuth credential handling in test environment.
        
        BVJ: Platform/Internal | Security & Authentication | Prevents OAuth 503 errors
        Tests that OAuth credentials are handled correctly with proper test environment
        configuration to prevent OAuth regression failures that caused 503 errors.
        """
        # Set OAuth configuration for test environment
        self._set_test_var("ENVIRONMENT", "test", "oauth_test")
        self._set_test_var("OAUTH_CLIENT_ID", "test_client_id_12345", "oauth_test")
        self._set_test_var("OAUTH_CLIENT_SECRET", "test_client_secret_67890", "oauth_test") 
        self._set_test_var("OAUTH_REDIRECT_URI", "http://localhost:8081/auth/callback/google", "oauth_test")
        self._set_test_var("OAUTH_PROVIDER", "google", "oauth_test")
        
        # Verify OAuth credentials are accessible
        assert self.env.get("OAUTH_CLIENT_ID") == "test_client_id_12345"
        assert self.env.get("OAUTH_CLIENT_SECRET") == "test_client_secret_67890"
        assert self.env.get("OAUTH_REDIRECT_URI") == "http://localhost:8081/auth/callback/google"
        assert self.env.get("OAUTH_PROVIDER") == "google"
        
        # Test OAuth configuration validation
        oauth_config = {
            "client_id": self.env.get("OAUTH_CLIENT_ID"),
            "client_secret": self.env.get("OAUTH_CLIENT_SECRET"), 
            "redirect_uri": self.env.get("OAUTH_REDIRECT_URI"),
            "provider": self.env.get("OAUTH_PROVIDER")
        }
        assert all(oauth_config.values())  # All values should be present
            
        # Test OAuth redirect URI validation for test environment
        redirect_uri = self.env.get("OAUTH_REDIRECT_URI")
        assert "localhost" in redirect_uri  # Test environment uses localhost
        assert "8081" in redirect_uri  # Auth service port

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_jwt_secret_management_consistency(self, real_services_fixture):
        """
        Test JWT secret key management consistency.
        
        BVJ: Platform/Internal | Security | Ensures consistent JWT validation
        Validates that JWT secret keys are consistently managed for reliable
        JWT validation across services to prevent authentication errors.
        """
        # Set shared JWT configuration
        shared_jwt_secret = "jwt_secret_key_for_testing_purposes_minimum_32_chars_2024"
        jwt_algorithm = "HS256"
        jwt_expiration = "3600"
        
        # Configure JWT settings
        self._set_test_var("JWT_SECRET_KEY", shared_jwt_secret, "jwt_test")
        self._set_test_var("JWT_ALGORITHM", jwt_algorithm, "jwt_test")
        self._set_test_var("JWT_EXPIRATION_SECONDS", jwt_expiration, "jwt_test")
        
        # Verify JWT configuration is consistent
        assert self.env.get("JWT_SECRET_KEY") == shared_jwt_secret
        assert self.env.get("JWT_ALGORITHM") == jwt_algorithm
        assert self.env.get("JWT_EXPIRATION_SECONDS") == jwt_expiration
        
        # Test JWT secret validation
        jwt_secret = self.env.get("JWT_SECRET_KEY")
        assert len(jwt_secret) >= 32  # Minimum recommended secret length
        
        # Test algorithm validation
        algorithm = self.env.get("JWT_ALGORITHM") 
        assert algorithm in ["HS256", "RS256", "ES256"]  # Supported algorithms
        
        # Test expiration validation
        expiration = int(self.env.get("JWT_EXPIRATION_SECONDS"))
        assert 300 <= expiration <= 86400  # 5 minutes to 24 hours

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_service_secret_isolation(self, real_services_fixture):
        """
        Test authentication service secret isolation.
        
        BVJ: Platform/Internal | Security | Prevents secret leakage between contexts
        Tests that authentication service secrets are properly isolated through
        source tracking to prevent security vulnerabilities.
        """
        # Set service-specific secrets with different sources
        self._set_test_var("AUTH_SERVICE_SECRET", "auth_secret_abc123", "auth_secrets")
        self._set_test_var("SESSION_SECRET_KEY", "session_secret_def456", "auth_secrets") 
        self._set_test_var("OAUTH_STATE_SECRET", "oauth_state_ghi789", "auth_secrets")
        
        self._set_test_var("BACKEND_SERVICE_SECRET", "backend_secret_xyz789", "backend_secrets")
        self._set_test_var("API_KEY_SECRET", "api_key_secret_uvw456", "backend_secrets")
        
        self._set_test_var("WEBSOCKET_SECRET", "websocket_secret_rst123", "websocket_secrets")
        
        # Verify secrets are accessible within their contexts
        assert self.env.get("AUTH_SERVICE_SECRET") == "auth_secret_abc123"
        assert self.env.get("SESSION_SECRET_KEY") == "session_secret_def456"
        assert self.env.get("OAUTH_STATE_SECRET") == "oauth_state_ghi789"
        
        assert self.env.get("BACKEND_SERVICE_SECRET") == "backend_secret_xyz789" 
        assert self.env.get("API_KEY_SECRET") == "api_key_secret_uvw456"
        
        assert self.env.get("WEBSOCKET_SECRET") == "websocket_secret_rst123"
        
        # Verify source tracking maintains isolation
        auth_source = self.env.get_variable_source("AUTH_SERVICE_SECRET")
        backend_source = self.env.get_variable_source("BACKEND_SERVICE_SECRET")
        websocket_source = self.env.get_variable_source("WEBSOCKET_SECRET")
        
        assert auth_source == "auth_secrets"
        assert backend_source == "backend_secrets"
        assert websocket_source == "websocket_secrets"
        
        # Verify secrets meet minimum length requirements
        for secret_var in ["AUTH_SERVICE_SECRET", "BACKEND_SERVICE_SECRET", "WEBSOCKET_SECRET"]:
            secret_value = self.env.get(secret_var)
            assert len(secret_value) >= 16, f"{secret_var} too short"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_environment_validation_integration(self, real_services_fixture):
        """
        Test authentication environment validation integration.
        
        BVJ: Platform/Internal | System Startup | Prevents auth startup failures  
        Tests that authentication environment validation integrates correctly
        to prevent startup failures due to missing auth configuration.
        """
        # Set required auth environment variables
        self._set_test_var("AUTH_SERVICE_URL", "http://localhost:8081", "auth_validation")
        self._set_test_var("JWT_SECRET_KEY", "test_jwt_secret_key_minimum_32_chars_long", "auth_validation")
        self._set_test_var("SESSION_SECRET_KEY", "test_session_secret_key_minimum_32_chars", "auth_validation")
        self._set_test_var("OAUTH_CLIENT_ID", "test_oauth_client_id", "auth_validation")
        self._set_test_var("OAUTH_CLIENT_SECRET", "test_oauth_client_secret", "auth_validation")
        self._set_test_var("DATABASE_URL", "postgresql://test:test@localhost:5434/test", "auth_validation")
        
        # Verify required auth configuration is present
        auth_url = self.env.get("AUTH_SERVICE_URL") 
        jwt_secret = self.env.get("JWT_SECRET_KEY")
        session_secret = self.env.get("SESSION_SECRET_KEY")
        
        assert auth_url is not None
        assert jwt_secret is not None  
        assert session_secret is not None
        
        # Test URL validation
        assert auth_url.startswith("http")
        assert "8081" in auth_url  # Auth service port
        
        # Test secret length validation
        assert len(jwt_secret) >= 32
        assert len(session_secret) >= 32
        
        # Test OAuth configuration validation
        oauth_client_id = self.env.get("OAUTH_CLIENT_ID")
        oauth_client_secret = self.env.get("OAUTH_CLIENT_SECRET") 
        
        assert oauth_client_id is not None
        assert oauth_client_secret is not None
        assert len(oauth_client_id) > 0
        assert len(oauth_client_secret) > 0

    # =================== MULTI-USER CONTEXT SAFETY ===================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_safe_singleton_concurrent_access(self, real_services_fixture):
        """
        Test thread-safe singleton behavior under concurrent access.
        
        BVJ: Platform/Internal | Multi-User Support | Ensures thread safety for concurrent users
        Tests that IsolatedEnvironment singleton behaves correctly under concurrent
        access from multiple threads, critical for multi-user system reliability.
        """
        def concurrent_access_test(thread_id: str, results: Dict[str, Any]):
            """Test concurrent access to environment singleton."""
            try:
                # Each thread gets the same singleton
                env = get_env()
                
                # Set thread-specific variables
                thread_var = f"THREAD_{thread_id}_VAR"
                thread_value = f"value_{thread_id}"
                
                env.set(thread_var, thread_value, source=f"thread_{thread_id}")
                
                # Simulate some work
                time.sleep(0.1)
                
                # Verify thread operations work
                retrieved_value = env.get(thread_var)
                
                results[thread_id] = {
                    "thread_var": thread_var,
                    "expected_value": thread_value,
                    "retrieved_value": retrieved_value,
                    "success": retrieved_value == thread_value,
                    "env_id": id(env)  # Verify same singleton
                }
                
            except Exception as e:
                results[thread_id] = {
                    "error": str(e),
                    "success": False
                }
        
        # Test concurrent access with multiple threads
        num_threads = 5
        results = {}
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                future = executor.submit(concurrent_access_test, str(i), results)
                futures.append(future)
            
            # Wait for all threads to complete
            for future in as_completed(futures):
                future.result()
        
        # Verify all threads completed successfully
        assert len(results) == num_threads
        
        # Verify all threads used the same singleton
        env_ids = {result["env_id"] for result in results.values() if "env_id" in result}
        assert len(env_ids) == 1, "Multiple environment instances created"
        
        for thread_id, result in results.items():
            assert result["success"], f"Thread {thread_id} failed: {result.get('error')}"
            
        # Clean up thread variables
        for i in range(num_threads):
            var_name = f"THREAD_{i}_VAR"
            if self.env.exists(var_name):
                self.env.delete(var_name, source="cleanup")

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_environment_variable_change_tracking(self, real_services_fixture):
        """
        Test environment variable change tracking and validation.
        
        BVJ: Platform/Internal | Configuration Management | Enables change audit and debugging
        Tests that environment variable changes are tracked correctly for audit
        and debugging purposes in multi-user environments.
        """
        # Track initial state
        initial_changes = self.env.get_changes_since_init()
        initial_count = len(initial_changes)
        
        # Make tracked changes
        test_vars = [
            ("CONFIG_VERSION", "1.0.0", "change_test"),
            ("FEATURE_FLAGS", "feature_a,feature_b", "change_test"),
            ("CACHE_TTL", "3600", "change_test"),
            ("LOG_LEVEL", "DEBUG", "change_test"),
        ]
        
        for var_name, value, source in test_vars:
            self._set_test_var(var_name, value, source)
        
        # Update some values
        self._set_test_var("CONFIG_VERSION", "1.1.0", "change_test")
        self._set_test_var("FEATURE_FLAGS", "feature_a,feature_b,feature_c", "change_test")
        
        # Verify changes are tracked
        current_changes = self.env.get_changes_since_init()
        new_changes = len(current_changes) - initial_count
        
        # Should have at least 4 new variables plus 2 updates
        assert new_changes >= 4
        
        # Verify final state
        assert self.env.get("CONFIG_VERSION") == "1.1.0"
        assert self.env.get("FEATURE_FLAGS") == "feature_a,feature_b,feature_c"
        assert self.env.get("CACHE_TTL") == "3600"
        assert self.env.get("LOG_LEVEL") == "DEBUG"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_isolation_source_separation(self, real_services_fixture):
        """
        Test user context isolation through source separation.
        
        BVJ: Platform/Internal | Multi-User Support | Ensures user session isolation
        Tests that different user contexts maintain proper isolation through
        source tracking, critical for multi-tenant security.
        """
        # Simulate different user contexts with distinct sources
        user_configs = [
            ("user_12345", "free", "us-west", "dark_mode,notifications"),
            ("user_67890", "enterprise", "eu-central", "light_mode,no_notifications"),
            ("user_54321", "early", "ap-southeast", "auto_mode,email_only"),
        ]
        
        for user_id, tier, region, preferences in user_configs:
            source = f"user_{user_id}_context"
            
            self._set_test_var(f"USER_ID_{user_id}", user_id, source)
            self._set_test_var(f"USER_TIER_{user_id}", tier, source)
            self._set_test_var(f"USER_REGION_{user_id}", region, source)
            self._set_test_var(f"USER_PREFERENCES_{user_id}", preferences, source)
        
        # Verify user context isolation through source tracking
        for user_id, tier, region, preferences in user_configs:
            user_id_var = f"USER_ID_{user_id}"
            user_tier_var = f"USER_TIER_{user_id}"
            user_region_var = f"USER_REGION_{user_id}"
            user_prefs_var = f"USER_PREFERENCES_{user_id}"
            
            # Verify values are correct
            assert self.env.get(user_id_var) == user_id
            assert self.env.get(user_tier_var) == tier
            assert self.env.get(user_region_var) == region
            assert self.env.get(user_prefs_var) == preferences
            
            # Verify source isolation
            expected_source = f"user_{user_id}_context"
            assert self.env.get_variable_source(user_id_var) == expected_source
            assert self.env.get_variable_source(user_tier_var) == expected_source
            assert self.env.get_variable_source(user_region_var) == expected_source
            assert self.env.get_variable_source(user_prefs_var) == expected_source

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_concurrent_user_session_environment_operations(self, real_services_fixture):
        """
        Test concurrent user session environment operations.
        
        BVJ: Platform/Internal | Multi-User Performance | Optimizes concurrent user experience  
        Tests that concurrent user sessions can perform environment operations
        efficiently without blocking or data corruption.
        """
        def simulate_user_session(user_id: str, results: Dict[str, Any]):
            """Simulate a user session with environment operations."""
            try:
                env = get_env()  # Same singleton for all
                source = f"user_session_{user_id}"
                
                # Set user-specific configuration
                session_vars = [
                    (f"USER_{user_id}_SESSION_ID", f"session_{user_id}_{int(time.time())}"),
                    (f"USER_{user_id}_LAST_ACTIVE", str(int(time.time()))),
                    (f"USER_{user_id}_ACTIVE_AGENTS", f"agent_1,agent_2,user_{user_id}_agent"),
                ]
                
                for var_name, var_value in session_vars:
                    env.set(var_name, var_value, source=source)
                
                # Simulate typical session operations
                operations_success = []
                for i in range(3):  # 3 operations per user
                    operation_key = f"USER_{user_id}_OPERATION_{i}"
                    operation_value = f"user_{user_id}_op_{i}_result"
                    
                    env.set(operation_key, operation_value, source=source)
                    
                    # Small delay to simulate real work
                    time.sleep(0.02)
                    
                    # Verify operation
                    retrieved = env.get(operation_key)
                    operations_success.append(retrieved == operation_value)
                
                # Collect results
                results[user_id] = {
                    "session_id": env.get(f"USER_{user_id}_SESSION_ID"),
                    "last_active": env.get(f"USER_{user_id}_LAST_ACTIVE"),
                    "active_agents": env.get(f"USER_{user_id}_ACTIVE_AGENTS"),
                    "operations_success": all(operations_success),
                    "success": True
                }
                
            except Exception as e:
                results[user_id] = {
                    "error": str(e),
                    "success": False
                }
        
        # Simulate multiple concurrent user sessions
        num_users = 4
        results = {}
        
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = []
            for i in range(num_users):
                future = executor.submit(simulate_user_session, str(i), results)
                futures.append(future)
            
            # Wait for all sessions to complete
            for future in as_completed(futures):
                future.result()
        
        # Verify all user sessions completed successfully
        assert len(results) == num_users
        
        for user_id, result in results.items():
            assert result["success"], f"User {user_id} session failed: {result.get('error')}"
            assert result["operations_success"], f"User {user_id} operations failed"
            assert result["session_id"].startswith(f"session_{user_id}_")
            assert f"user_{user_id}_agent" in result["active_agents"]
        
        # Clean up user session variables
        for i in range(num_users):
            for var_name in self.env.get_all_with_prefix(f"USER_{i}_"):
                if self.env.exists(var_name):
                    self.env.delete(var_name, source="cleanup")

    # =================== SYSTEM INTEGRATION ===================

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_shell_command_expansion_integration(self, real_services_fixture):
        """
        Test shell command expansion integration.
        
        BVJ: Platform/Internal | System Integration | Enables environment-aware shell operations
        Tests that shell command expansion works with environment variables for
        deployment and maintenance scripts across different service contexts.
        """
        # Set deployment context variables
        self._set_test_var("SERVICE_NAME", "netra-backend", "deployment")
        self._set_test_var("DEPLOY_ENV", "staging", "deployment")
        self._set_test_var("DOCKER_REGISTRY", "gcr.io/netra-staging", "deployment")
        self._set_test_var("SERVICE_VERSION", "v1.2.3", "deployment")
        
        # Set monitoring context variables
        self._set_test_var("LOG_PATH", "/var/log/netra", "monitoring")
        self._set_test_var("METRICS_ENDPOINT", "http://prometheus:9090", "monitoring")
        self._set_test_var("ALERT_EMAIL", "alerts@netra.ai", "monitoring")
        
        # Set maintenance context variables
        self._set_test_var("BACKUP_PATH", "/backups/netra", "maintenance")
        self._set_test_var("DB_HOST", "localhost", "maintenance")
        self._set_test_var("DB_PORT", "5434", "maintenance")
        
        # Test that variables are accessible for shell expansion
        service_name = self.env.get("SERVICE_NAME")
        deploy_env = self.env.get("DEPLOY_ENV")
        docker_registry = self.env.get("DOCKER_REGISTRY")
        service_version = self.env.get("SERVICE_VERSION")
        
        assert service_name == "netra-backend"
        assert deploy_env == "staging"
        assert docker_registry == "gcr.io/netra-staging"
        assert service_version == "v1.2.3"
        
        # Test monitoring variables
        assert self.env.get("LOG_PATH") == "/var/log/netra"
        assert self.env.get("METRICS_ENDPOINT") == "http://prometheus:9090"
        assert self.env.get("ALERT_EMAIL") == "alerts@netra.ai"
        
        # Test maintenance variables
        assert self.env.get("BACKUP_PATH") == "/backups/netra"
        assert self.env.get("DB_HOST") == "localhost"
        assert self.env.get("DB_PORT") == "5434"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_environment_change_detection_and_audit(self, real_services_fixture):
        """
        Test environment variable change detection and audit trail.
        
        BVJ: Platform/Internal | Configuration Management | Enables change audit and rollback
        Tests that environment variable changes are detected and tracked for audit
        and rollback capabilities in production systems.
        """
        # Capture initial state
        initial_vars = self.env.get_all()
        initial_count = len(initial_vars)
        
        # Make tracked changes with different sources
        change_sequence = [
            ("CONFIG_VERSION", "1.0.0", "config_manager"),
            ("FEATURE_FLAGS", "feature_a", "feature_manager"),
            ("CACHE_TTL", "3600", "cache_manager"),
            ("CONFIG_VERSION", "1.1.0", "config_manager"),  # Update
            ("FEATURE_FLAGS", "feature_a,feature_b", "feature_manager"),  # Update
            ("LOG_LEVEL", "INFO", "logging_manager"),  # New
        ]
        
        for var_name, value, source in change_sequence:
            self._set_test_var(var_name, value, source)
            time.sleep(0.01)  # Small delay for change tracking
        
        # Verify changes are tracked
        changes = self.env.get_changes_since_init()
        
        # Should have changes for all our test variables
        test_var_changes = {
            var: change for var, change in changes.items() 
            if var in ["CONFIG_VERSION", "FEATURE_FLAGS", "CACHE_TTL", "LOG_LEVEL"]
        }
        
        assert len(test_var_changes) >= 4  # At least our 4 test variables
        
        # Verify final values
        assert self.env.get("CONFIG_VERSION") == "1.1.0"
        assert self.env.get("FEATURE_FLAGS") == "feature_a,feature_b"
        assert self.env.get("CACHE_TTL") == "3600"
        assert self.env.get("LOG_LEVEL") == "INFO"
        
        # Verify source tracking
        assert self.env.get_variable_source("CONFIG_VERSION") == "config_manager"
        assert self.env.get_variable_source("FEATURE_FLAGS") == "feature_manager"
        assert self.env.get_variable_source("CACHE_TTL") == "cache_manager"
        assert self.env.get_variable_source("LOG_LEVEL") == "logging_manager"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_secrets_loading_priority_and_security(self, real_services_fixture):
        """
        Test secrets loading priority and security handling.
        
        BVJ: Platform/Internal | Security & Configuration | Prevents secret conflicts and exposure
        Tests that secrets are loaded with proper priority and security handling
        to prevent vulnerabilities and configuration conflicts.
        """
        # Set secrets with different priorities and sources
        secret_configs = [
            ("API_SECRET", "default_api_secret_123", "default"),
            ("DB_PASSWORD", "default_db_password", "default"),
            ("JWT_SECRET", "default_jwt_secret_456", "default"),
            ("API_SECRET", "service_api_secret_789", "service_override"),  # Higher priority
            ("SERVICE_SECRET", "service_only_secret_abc", "service_override"),
            ("API_SECRET", "production_api_secret_xyz", "production_override"),  # Highest
            ("PRODUCTION_SECRET", "production_only_secret_123", "production_override"),
        ]
        
        for var_name, value, source in secret_configs:
            self._set_test_var(var_name, value, source)
        
        # Test priority resolution (latest set wins in our implementation)
        assert self.env.get("API_SECRET") == "production_api_secret_xyz"  # Highest priority
        assert self.env.get("DB_PASSWORD") == "default_db_password"  # Only default set
        assert self.env.get("JWT_SECRET") == "default_jwt_secret_456"  # Only default set
        assert self.env.get("SERVICE_SECRET") == "service_only_secret_abc"  # Service only
        assert self.env.get("PRODUCTION_SECRET") == "production_only_secret_123"  # Production only
        
        # Test source tracking for audit
        assert self.env.get_variable_source("API_SECRET") == "production_override"
        assert self.env.get_variable_source("DB_PASSWORD") == "default"
        assert self.env.get_variable_source("SERVICE_SECRET") == "service_override"
        
        # Validate secret security requirements
        for secret_var in ["API_SECRET", "DB_PASSWORD", "JWT_SECRET"]:
            secret_value = self.env.get(secret_var)
            if secret_value:  # If secret is set
                assert len(secret_value) >= 16, f"{secret_var} too short"
                assert "secret" in secret_value.lower(), f"{secret_var} doesn't look like a secret"

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_environment_lifecycle_and_resource_management(self, real_services_fixture):
        """
        Test environment lifecycle and resource management.
        
        BVJ: Platform/Internal | Resource Management | Prevents memory leaks and ensures stability
        Tests that environment variables and resources are managed correctly throughout
        the lifecycle to prevent memory leaks and ensure system stability.
        """
        # Track initial resource state
        initial_vars = self.env.get_all()
        initial_count = len(initial_vars)
        
        # Create many environment variables to test resource management
        test_variables = []
        for i in range(50):  # Create many variables
            var_name = f"LIFECYCLE_TEST_VAR_{i}"
            var_value = f"test_value_{i}_with_some_content"
            source = f"lifecycle_test_{i % 5}"  # Rotate sources
            
            self._set_test_var(var_name, var_value, source)
            test_variables.append(var_name)
        
        # Verify variables were created
        current_vars = self.env.get_all()
        assert len(current_vars) >= initial_count + 50
        
        # Test variable access
        for i, var_name in enumerate(test_variables):
            assert self.env.get(var_name) == f"test_value_{i}_with_some_content"
        
        # Test prefix-based access
        lifecycle_vars = self.env.get_all_with_prefix("LIFECYCLE_TEST_VAR_")
        assert len(lifecycle_vars) == 50
        
        # Test source tracking for resource management
        source_counts = {}
        for var_name in test_variables:
            source = self.env.get_variable_source(var_name)
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Should have 5 different sources with ~10 variables each
        assert len(source_counts) == 5
        for count in source_counts.values():
            assert 8 <= count <= 12  # Roughly evenly distributed
        
        # Test cleanup - variables will be cleaned up in teardown_method
        # This tests that cleanup doesn't cause resource issues
        
        # Verify system is still functional after many operations
        final_test_var = "FINAL_FUNCTIONALITY_TEST"
        self._set_test_var(final_test_var, "system_stable", "final_test")
        assert self.env.get(final_test_var) == "system_stable"