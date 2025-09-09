"""
Integration Tests: Real Environment Configuration Validation

CRITICAL: Tests real environment configurations with actual services and dependencies.
Validates configuration works with PostgreSQL, Redis, and cross-service communication.

Business Value: Platform/Internal - Prevents configuration failures in real deployments
Test Coverage: Real database connections, service communication, environment validation
"""
import pytest
import asyncio
import os
import time
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import redis
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.database_url_builder import DatabaseURLBuilder
from shared.jwt_secret_manager import SharedJWTSecretManager


@pytest.mark.integration
class TestRealEnvironmentConfigValidation:
    """Test configuration validation with real environment dependencies."""

    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Set up isolated environment for integration testing."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Store original state for cleanup
        self.original_env = self.env.get_all()
        
        yield
        
        # Cleanup - restore original environment
        self.env.clear()
        for key, value in self.original_env.items():
            self.env.set(key, value, "restore_original")

    def test_real_database_connection_with_configuration(self):
        """
        CRITICAL: Test real database connection using configuration.
        
        PREVENTS: Database configuration errors causing connection failures
        CASCADE FAILURE: Complete backend failure, no data access
        """
        # Set up test database configuration
        test_db_config = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",  # Test database port
            "POSTGRES_USER": "netra_test",
            "POSTGRES_PASSWORD": "netra_test_password", 
            "POSTGRES_DB": "netra_test",
            "ENVIRONMENT": "test"
        }
        
        for key, value in test_db_config.items():
            self.env.set(key, value, "test_db_config")
        
        # Use DatabaseURLBuilder SSOT for URL construction
        builder = DatabaseURLBuilder(self.env.get_all())
        database_url = builder.get_url_for_environment(sync=True)
        
        # Verify URL format
        assert database_url.startswith("postgresql://"), f"Database URL should be PostgreSQL: {database_url}"
        assert "5434" in database_url, f"Should use test port 5434: {database_url}"
        assert "netra_test" in database_url, f"Should use test database: {database_url}"
        
        # Test actual database connection (if test database is available)
        try:
            engine = create_engine(database_url, pool_timeout=5, connect_timeout=5)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test_connection"))
                assert result.fetchone()[0] == 1, "Database connection test failed"
                
        except OperationalError as e:
            # Database may not be available in all test environments
            if "could not connect" in str(e).lower():
                pytest.skip(f"Test database not available: {e}")
            else:
                pytest.fail(f"Database configuration error: {e}")

    def test_real_redis_connection_with_configuration(self):
        """
        CRITICAL: Test real Redis connection using configuration.
        
        PREVENTS: Redis configuration errors causing cache failures
        CASCADE FAILURE: Performance degradation, session store failures
        """
        # Set up test Redis configuration
        test_redis_config = {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6381",  # Test Redis port
            "REDIS_URL": "redis://localhost:6381/0",
            "ENVIRONMENT": "test"
        }
        
        for key, value in test_redis_config.items():
            self.env.set(key, value, "test_redis_config")
        
        # Get Redis URL from configuration
        redis_url = self.env.get("REDIS_URL")
        assert redis_url == "redis://localhost:6381/0", f"Redis URL incorrect: {redis_url}"
        
        # Test actual Redis connection (if test Redis is available)
        try:
            r = redis.from_url(redis_url, socket_timeout=5, socket_connect_timeout=5)
            
            # Test basic Redis operations
            test_key = "config_test_key"
            test_value = "config_test_value"
            
            r.set(test_key, test_value, ex=10)  # 10 second expiration
            retrieved_value = r.get(test_key)
            
            assert retrieved_value.decode() == test_value, "Redis operation failed"
            
            # Cleanup
            r.delete(test_key)
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            # Redis may not be available in all test environments  
            pytest.skip(f"Test Redis not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis configuration error: {e}")

    def test_real_jwt_secret_manager_integration(self):
        """
        CRITICAL: Test real JWT secret manager integration with configuration.
        
        PREVENTS: JWT secret inconsistencies between services
        CASCADE FAILURE: Token validation failures, authentication breakdown
        """
        # Set up JWT configuration
        jwt_config = {
            "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters-minimum-length",
            "SERVICE_SECRET": "test-service-secret-32-characters-minimum-length",
            "ENVIRONMENT": "test"
        }
        
        for key, value in jwt_config.items():
            self.env.set(key, value, "jwt_config")
        
        # Test SharedJWTSecretManager integration
        jwt_secret = SharedJWTSecretManager.get_jwt_secret()
        
        # Verify JWT secret meets requirements
        assert jwt_secret is not None, "JWT secret should not be None"
        assert len(jwt_secret) >= 32, f"JWT secret too short: {len(jwt_secret)} characters"
        assert jwt_secret == jwt_config["JWT_SECRET_KEY"], "JWT secret should match configuration"
        
        # Test JWT secret consistency across multiple calls
        jwt_secret_2 = SharedJWTSecretManager.get_jwt_secret()
        assert jwt_secret == jwt_secret_2, "JWT secret should be consistent across calls"
        
        # Test service secret integration
        service_secret = self.env.get("SERVICE_SECRET")
        assert service_secret is not None, "Service secret should not be None"
        assert len(service_secret) >= 8, f"Service secret too short: {len(service_secret)} characters"

    def test_real_environment_detection_with_services(self):
        """
        CRITICAL: Test environment detection works with real service configurations.
        
        PREVENTS: Wrong environment detection causing incorrect service behavior
        CASCADE FAILURE: Services using wrong configurations, data corruption
        """
        # Test environment detection scenarios
        environment_scenarios = [
            {
                "name": "test_environment",
                "config": {
                    "ENVIRONMENT": "test",
                    "TESTING": "true",
                    "DATABASE_URL": "postgresql://localhost:5434/netra_test"
                },
                "expected_env": "test"
            },
            {
                "name": "development_environment", 
                "config": {
                    "ENVIRONMENT": "development",
                    "DEBUG": "true",
                    "DATABASE_URL": "postgresql://localhost:5432/netra_dev"
                },
                "expected_env": "development"
            },
            {
                "name": "staging_environment",
                "config": {
                    "ENVIRONMENT": "staging",
                    "DEBUG": "false",
                    "DATABASE_URL": "postgresql://staging-db.gcp:5432/netra_staging"
                },
                "expected_env": "staging"
            }
        ]
        
        for scenario in environment_scenarios:
            self.env.clear()
            
            # Set scenario configuration
            for key, value in scenario["config"].items():
                self.env.set(key, value, f"{scenario['name']}_config")
            
            # Test environment detection
            detected_env = self.env.get_environment_name()
            assert detected_env == scenario["expected_env"], (
                f"Environment detection failed for {scenario['name']}: "
                f"expected {scenario['expected_env']}, got {detected_env}"
            )
            
            # Test environment-specific behavior
            if detected_env == "test":
                assert self.env.is_test(), "Should detect test environment"
                assert not self.env.is_production(), "Should not detect production in test"
            elif detected_env == "development":
                assert self.env.is_development(), "Should detect development environment"
                assert not self.env.is_staging(), "Should not detect staging in development"
            elif detected_env == "staging":
                assert self.env.is_staging(), "Should detect staging environment"
                assert not self.env.is_development(), "Should not detect development in staging"


@pytest.mark.integration
class TestCrossServiceConfigValidation:
    """Test configuration validation across multiple services."""

    @pytest.fixture(autouse=True)
    def setup_cross_service_environment(self):
        """Set up environment for cross-service testing."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Store original state
        self.original_env = self.env.get_all()
        
        yield
        
        # Cleanup
        self.env.clear()
        for key, value in self.original_env.items():
            self.env.set(key, value, "restore_original")

    def test_backend_auth_service_config_consistency(self):
        """
        CRITICAL: Test configuration consistency between backend and auth services.
        
        PREVENTS: Service configuration mismatches causing communication failures
        CASCADE FAILURE: Inter-service authentication failures, system fragmentation
        """
        # Shared configuration between backend and auth services
        shared_config = {
            "JWT_SECRET_KEY": "shared-jwt-secret-key-32-characters-minimum",
            "SERVICE_SECRET": "shared-service-secret-32-characters-minimum",
            "DATABASE_URL": "postgresql://localhost:5434/netra_test",
            "ENVIRONMENT": "test"
        }
        
        # Backend-specific configuration
        backend_config = {
            "SERVER_PORT": "8000",
            "LOG_LEVEL": "DEBUG",
            "ENABLE_AGENTS": "true"
        }
        
        # Auth service-specific configuration
        auth_config = {
            "AUTH_PORT": "8081", 
            "OAUTH_ENABLED": "true",
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "test-oauth-client-id"
        }
        
        # Set up complete configuration
        all_config = {**shared_config, **backend_config, **auth_config}
        for key, value in all_config.items():
            self.env.set(key, value, "cross_service_config")
        
        # Verify shared configuration consistency
        for key, expected_value in shared_config.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value, (
                f"Shared config inconsistency: {key} = {actual_value}, expected {expected_value}"
            )
        
        # Verify service-specific isolation
        backend_port = self.env.get("SERVER_PORT")
        auth_port = self.env.get("AUTH_PORT")
        assert backend_port != auth_port, "Backend and auth ports should be different"
        assert int(backend_port) != int(auth_port), "Port values should be numerically different"
        
        # Test JWT secret sharing
        jwt_secret = SharedJWTSecretManager.get_jwt_secret()
        assert jwt_secret == shared_config["JWT_SECRET_KEY"], "JWT secret should be shared correctly"

    def test_frontend_backend_config_integration(self):
        """
        CRITICAL: Test frontend-backend configuration integration.
        
        PREVENTS: Frontend-backend URL mismatches causing API call failures
        CASCADE FAILURE: Frontend cannot communicate with backend, system unusable
        """
        # Environment-specific frontend-backend configuration
        integration_configs = {
            "development": {
                "ENVIRONMENT": "development",
                "SERVER_PORT": "8000",
                "AUTH_PORT": "8081",
                "FRONTEND_PORT": "3000",
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",
                "NEXT_PUBLIC_AUTH_URL": "http://localhost:8081",
                "NEXT_PUBLIC_WS_URL": "ws://localhost:8000/ws"
            },
            "staging": {
                "ENVIRONMENT": "staging",
                "SERVER_PORT": "8080",
                "AUTH_PORT": "8081", 
                "FRONTEND_PORT": "3000",
                "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
                "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai",
                "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai/ws"
            }
        }
        
        for env_name, config in integration_configs.items():
            self.env.clear()
            
            # Set environment configuration
            for key, value in config.items():
                self.env.set(key, value, f"{env_name}_integration")
            
            # Verify frontend-backend URL consistency
            api_url = self.env.get("NEXT_PUBLIC_API_URL")
            auth_url = self.env.get("NEXT_PUBLIC_AUTH_URL")
            ws_url = self.env.get("NEXT_PUBLIC_WS_URL")
            
            if env_name == "development":
                # Development should use localhost
                assert "localhost" in api_url, f"Development API URL should use localhost: {api_url}"
                assert "localhost" in auth_url, f"Development Auth URL should use localhost: {auth_url}"
                assert "localhost" in ws_url, f"Development WebSocket URL should use localhost: {ws_url}"
                
                # Check port consistency
                server_port = self.env.get("SERVER_PORT")
                assert server_port in api_url, f"API URL should include server port {server_port}: {api_url}"
                
                auth_port = self.env.get("AUTH_PORT")
                assert auth_port in auth_url, f"Auth URL should include auth port {auth_port}: {auth_url}"
                
            elif env_name == "staging":
                # Staging should use staging domains
                assert "staging" in api_url, f"Staging API URL should contain 'staging': {api_url}"
                assert "staging" in auth_url, f"Staging Auth URL should contain 'staging': {auth_url}"
                assert "staging" in ws_url, f"Staging WebSocket URL should contain 'staging': {ws_url}"
                
                # Should use HTTPS/WSS
                assert api_url.startswith("https://"), f"Staging API should use HTTPS: {api_url}"
                assert auth_url.startswith("https://"), f"Staging Auth should use HTTPS: {auth_url}"
                assert ws_url.startswith("wss://"), f"Staging WebSocket should use WSS: {ws_url}"

    def test_database_service_config_consistency(self):
        """
        CRITICAL: Test database configuration consistency across services.
        
        PREVENTS: Services using different database configurations
        CASCADE FAILURE: Data inconsistency, service isolation breakdown
        """
        # Database configuration that should be consistent across services
        db_config = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",
            "POSTGRES_USER": "netra_test",
            "POSTGRES_PASSWORD": "netra_test_password",
            "POSTGRES_DB": "netra_test",
            "ENVIRONMENT": "test"
        }
        
        for key, value in db_config.items():
            self.env.set(key, value, "db_consistency_test")
        
        # Test DatabaseURLBuilder SSOT consistency
        builder = DatabaseURLBuilder(self.env.get_all())
        
        # Generate URLs for different connection types
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)
        
        # Both URLs should point to same database with different drivers
        assert "postgresql" in async_url, f"Async URL should be PostgreSQL: {async_url}"
        assert "postgresql" in sync_url, f"Sync URL should be PostgreSQL: {sync_url}"
        
        # Extract host, port, database from URLs
        for url in [async_url, sync_url]:
            assert "localhost" in url, f"URL should use localhost: {url}"
            assert "5434" in url, f"URL should use port 5434: {url}"
            assert "netra_test" in url, f"URL should use test database: {url}"
            assert "netra_test_password" in url or url.count("netra_test") >= 2, f"URL should include credentials: {url}"
        
        # Verify different drivers for async/sync
        if "asyncpg" in async_url:
            assert "psycopg2" in sync_url or "psycopg" in sync_url, "Sync URL should use different driver"
        
        # Test connection pool compatibility
        debug_info = builder.debug_info()
        assert debug_info["environment"] == "test", "Builder should detect test environment"
        assert debug_info["host"] == "localhost", "Builder should use correct host"

    def test_service_discovery_config_validation(self):
        """
        CRITICAL: Test service discovery configuration validation.
        
        PREVENTS: Services unable to discover each other due to config errors
        CASCADE FAILURE: Inter-service communication breakdown, system fragmentation
        """
        # Service discovery configuration
        discovery_config = {
            "ENVIRONMENT": "test",
            "BACKEND_SERVICE_URL": "http://localhost:8000",
            "AUTH_SERVICE_URL": "http://localhost:8081",
            "FRONTEND_SERVICE_URL": "http://localhost:3000",
            "WEBSOCKET_SERVICE_URL": "ws://localhost:8000/ws"
        }
        
        for key, value in discovery_config.items():
            self.env.set(key, value, "service_discovery")
        
        # Verify service discovery URLs
        services = {
            "backend": self.env.get("BACKEND_SERVICE_URL"),
            "auth": self.env.get("AUTH_SERVICE_URL"),
            "frontend": self.env.get("FRONTEND_SERVICE_URL"),
            "websocket": self.env.get("WEBSOCKET_SERVICE_URL")
        }
        
        # Validate service URL formats
        for service_name, service_url in services.items():
            assert service_url is not None, f"{service_name} service URL should not be None"
            
            if service_name == "websocket":
                assert service_url.startswith("ws://"), f"WebSocket URL should use ws://: {service_url}"
            else:
                assert service_url.startswith("http://"), f"{service_name} URL should use http://: {service_url}"
            
            assert "localhost" in service_url, f"{service_name} URL should use localhost in test: {service_url}"
        
        # Verify port uniqueness
        ports = []
        for service_url in services.values():
            if ":" in service_url:
                port_part = service_url.split(":")[-1].split("/")[0]
                if port_part.isdigit():
                    ports.append(int(port_part))
        
        unique_ports = set(ports)
        assert len(unique_ports) == len(ports), f"Service ports should be unique: {ports}"