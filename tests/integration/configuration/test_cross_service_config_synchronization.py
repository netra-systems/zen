"""
Integration Tests: Cross-Service Configuration Synchronization

CRITICAL: Tests configuration synchronization across multiple services and environments.
Validates shared components work correctly and prevent configuration drift.

Business Value: Platform/Internal - Prevents service communication failures and data inconsistency
Test Coverage: Cross-service config sync, shared component validation, environment consistency
"""
import pytest
import asyncio
import os
import time
import threading
from unittest.mock import patch, Mock
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.database_url_builder import DatabaseURLBuilder
from shared.jwt_secret_manager import SharedJWTSecretManager
from shared.port_discovery import PortDiscovery


@pytest.mark.integration
class TestCrossServiceConfigSynchronization:
    """Test configuration synchronization across services to prevent drift and conflicts."""

    @pytest.fixture(autouse=True)
    def setup_sync_environment(self):
        """Set up environment for cross-service synchronization testing."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Store original state
        self.original_env = self.env.get_all()
        
        yield
        
        # Cleanup
        self.env.clear()
        for key, value in self.original_env.items():
            self.env.set(key, value, "restore_original")

    def test_shared_jwt_secret_consistency_across_services(self):
        """
        CRITICAL: Test JWT secret consistency across all services.
        
        PREVENTS: JWT token validation failures due to secret mismatches
        CASCADE FAILURE: Authentication breakdown, user session invalidation
        """
        # Set up JWT configuration
        jwt_config = {
            "JWT_SECRET_KEY": "cross-service-jwt-secret-32-characters-minimum",
            "SERVICE_SECRET": "cross-service-secret-32-characters-minimum",
            "ENVIRONMENT": "test"
        }
        
        for key, value in jwt_config.items():
            self.env.set(key, value, "jwt_consistency_test")
        
        # Simulate multiple services accessing JWT secret
        service_jwt_secrets = []
        
        # Backend service JWT access
        backend_jwt = SharedJWTSecretManager.get_jwt_secret()
        service_jwt_secrets.append(("backend", backend_jwt))
        
        # Auth service JWT access
        auth_jwt = SharedJWTSecretManager.get_jwt_secret()
        service_jwt_secrets.append(("auth", auth_jwt))
        
        # Simulated additional service JWT access
        for i in range(3):
            service_jwt = SharedJWTSecretManager.get_jwt_secret()
            service_jwt_secrets.append((f"service_{i}", service_jwt))
        
        # Verify all services get the same JWT secret
        expected_jwt = jwt_config["JWT_SECRET_KEY"]
        for service_name, service_jwt in service_jwt_secrets:
            assert service_jwt == expected_jwt, f"{service_name} JWT secret mismatch: {service_jwt}"
        
        # Verify JWT secret consistency across multiple calls per service
        for service_name, _ in service_jwt_secrets:
            jwt_1 = SharedJWTSecretManager.get_jwt_secret()
            jwt_2 = SharedJWTSecretManager.get_jwt_secret()
            assert jwt_1 == jwt_2, f"JWT secret inconsistent for {service_name}"

    def test_database_url_consistency_across_services(self):
        """
        CRITICAL: Test database URL consistency across services using DatabaseURLBuilder SSOT.
        
        PREVENTS: Services connecting to different databases
        CASCADE FAILURE: Data inconsistency, service isolation breakdown
        """
        # Set up database configuration
        db_config = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5434",
            "POSTGRES_USER": "netra_test",
            "POSTGRES_PASSWORD": "netra_test_password",
            "POSTGRES_DB": "netra_test",
            "ENVIRONMENT": "test"
        }
        
        for key, value in db_config.items():
            self.env.set(key, value, "db_sync_test")
        
        # Simulate multiple services using DatabaseURLBuilder
        service_database_urls = []
        
        # Backend service database access
        backend_builder = DatabaseURLBuilder(self.env.get_all())
        backend_url = backend_builder.get_url_for_environment(sync=False)
        service_database_urls.append(("backend", backend_url))
        
        # Auth service database access
        auth_builder = DatabaseURLBuilder(self.env.get_all())
        auth_url = auth_builder.get_url_for_environment(sync=True)
        service_database_urls.append(("auth", auth_url))
        
        # Additional services database access
        for i in range(3):
            service_builder = DatabaseURLBuilder(self.env.get_all())
            service_url = service_builder.get_url_for_environment(sync=(i % 2 == 0))
            service_database_urls.append((f"service_{i}", service_url))
        
        # Verify all services connect to same database (different drivers allowed)
        for service_name, service_url in service_database_urls:
            assert "postgresql://" in service_url, f"{service_name} should use PostgreSQL: {service_url}"
            assert "localhost" in service_url, f"{service_name} should use localhost: {service_url}"
            assert "5434" in service_url, f"{service_name} should use port 5434: {service_url}"
            assert "netra_test" in service_url, f"{service_name} should use test database: {service_url}"
        
        # Verify database connection consistency (extracting database name)
        database_names = []
        for service_name, service_url in service_database_urls:
            # Extract database name from URL (after last /)
            db_name = service_url.split("/")[-1].split("?")[0]
            database_names.append(db_name)
        
        # All services should connect to same database
        unique_databases = set(database_names)
        assert len(unique_databases) == 1, f"Services using different databases: {unique_databases}"
        assert "netra_test" in unique_databases, f"Should all use netra_test database: {unique_databases}"

    def test_port_discovery_service_consistency(self):
        """
        CRITICAL: Test port discovery consistency across services.
        
        PREVENTS: Services using wrong ports causing connection failures
        CASCADE FAILURE: Inter-service communication breakdown
        """
        # Set up port configuration for services
        port_config = {
            "ENVIRONMENT": "test",
            "SERVER_PORT": "8000",
            "AUTH_PORT": "8081",
            "FRONTEND_PORT": "3000",
            "WEBSOCKET_PORT": "8000"  # Same as server for WebSocket endpoint
        }
        
        for key, value in port_config.items():
            self.env.set(key, value, "port_discovery_test")
        
        # Test PortDiscovery consistency across services
        services = ["backend", "auth", "frontend"]
        
        # Simulate multiple services discovering service URLs
        service_discoveries = {}
        
        for discovering_service in services:
            service_discoveries[discovering_service] = {}
            
            for target_service in services:
                if target_service != discovering_service:
                    # Each service discovers other services
                    discovered_url = PortDiscovery.get_service_url(target_service, environment="test")
                    service_discoveries[discovering_service][target_service] = discovered_url
        
        # Verify consistency - all services should discover same URLs for each target
        for target_service in services:
            discovered_urls = []
            for discovering_service in services:
                if target_service in service_discoveries[discovering_service]:
                    url = service_discoveries[discovering_service][target_service]
                    discovered_urls.append(url)
            
            # All discovered URLs for a target service should be identical
            if discovered_urls:
                unique_urls = set(discovered_urls)
                assert len(unique_urls) == 1, (
                    f"Inconsistent discovery for {target_service}: {unique_urls}"
                )
                
                # Verify URL format
                consistent_url = discovered_urls[0]
                assert consistent_url.startswith("http://"), f"{target_service} URL should use http://: {consistent_url}"
                assert "localhost" in consistent_url, f"{target_service} URL should use localhost: {consistent_url}"

    def test_environment_variable_synchronization_across_threads(self):
        """
        CRITICAL: Test environment variable synchronization across multiple threads.
        
        PREVENTS: Race conditions causing configuration inconsistencies
        CASCADE FAILURE: Different threads using different configurations
        """
        # Shared configuration that multiple threads will access
        shared_config = {
            "SHARED_SECRET": "thread-safe-secret-32-characters-minimum",
            "SHARED_DATABASE_URL": "postgresql://localhost:5434/thread_test",
            "SHARED_JWT_KEY": "thread-safe-jwt-key-32-characters-minimum",
            "ENVIRONMENT": "test"
        }
        
        for key, value in shared_config.items():
            self.env.set(key, value, "thread_sync_test")
        
        # Results storage for thread validation
        thread_results = {}
        thread_errors = []
        
        def thread_config_access(thread_id):
            """Function for threads to access configuration."""
            try:
                # Each thread gets environment instance and accesses config
                thread_env = get_env()  # Should return same singleton
                
                thread_config = {}
                for key in shared_config:
                    value = thread_env.get(key)
                    thread_config[key] = value
                
                # Store results
                thread_results[thread_id] = thread_config
                
                # Test configuration operations
                test_key = f"THREAD_{thread_id}_TEST"
                test_value = f"thread-{thread_id}-value"
                
                success = thread_env.set(test_key, test_value, f"thread_{thread_id}")
                if success:
                    retrieved_value = thread_env.get(test_key)
                    thread_results[thread_id]["thread_test"] = (test_value, retrieved_value)
                
            except Exception as e:
                thread_errors.append(f"Thread {thread_id}: {e}")
        
        # Create and start multiple threads
        threads = []
        num_threads = 5
        
        for i in range(num_threads):
            thread = threading.Thread(target=thread_config_access, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        # Verify no thread errors
        assert not thread_errors, f"Thread errors occurred: {thread_errors}"
        
        # Verify all threads got same shared configuration
        assert len(thread_results) == num_threads, f"Expected {num_threads} thread results, got {len(thread_results)}"
        
        # Check configuration consistency across threads
        first_thread_config = thread_results[0]
        for thread_id, thread_config in thread_results.items():
            for key, expected_value in shared_config.items():
                actual_value = thread_config.get(key)
                assert actual_value == expected_value, (
                    f"Thread {thread_id} config mismatch for {key}: {actual_value} != {expected_value}"
                )


@pytest.mark.integration  
class TestConfigurationDriftPrevention:
    """Test prevention of configuration drift across service updates and deployments."""

    @pytest.fixture(autouse=True)
    def setup_drift_environment(self):
        """Set up environment for configuration drift testing."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Store original state
        self.original_env = self.env.get_all()
        
        yield
        
        # Cleanup
        self.env.clear()
        for key, value in self.original_env.items():
            self.env.set(key, value, "restore_original")

    def test_configuration_version_consistency(self):
        """
        CRITICAL: Test configuration version consistency prevents drift.
        
        PREVENTS: Different services using different configuration versions
        CASCADE FAILURE: Feature incompatibilities, API mismatches
        """
        # Set up versioned configuration
        config_version = "2.0.0"
        versioned_config = {
            "CONFIG_VERSION": config_version,
            "FEATURE_FLAGS_VERSION": "2.0.0",
            "API_VERSION": "v2",
            "ENVIRONMENT": "test"
        }
        
        for key, value in versioned_config.items():
            self.env.set(key, value, "version_consistency_test")
        
        # Simulate multiple services checking configuration version
        services = ["backend", "auth", "frontend", "websocket"]
        service_versions = {}
        
        for service in services:
            # Each service reads configuration version
            service_config_version = self.env.get("CONFIG_VERSION")
            service_api_version = self.env.get("API_VERSION")
            service_feature_version = self.env.get("FEATURE_FLAGS_VERSION")
            
            service_versions[service] = {
                "config": service_config_version,
                "api": service_api_version,
                "features": service_feature_version
            }
        
        # Verify all services see same configuration version
        for service, versions in service_versions.items():
            assert versions["config"] == config_version, f"{service} config version mismatch: {versions['config']}"
            assert versions["api"] == "v2", f"{service} API version mismatch: {versions['api']}"
            assert versions["features"] == "2.0.0", f"{service} feature version mismatch: {versions['features']}"
        
        # Verify version consistency across services
        all_config_versions = [v["config"] for v in service_versions.values()]
        unique_config_versions = set(all_config_versions)
        assert len(unique_config_versions) == 1, f"Configuration version drift detected: {unique_config_versions}"

    def test_shared_secret_rotation_synchronization(self):
        """
        CRITICAL: Test shared secret rotation synchronization across services.
        
        PREVENTS: Services using different secrets after rotation
        CASCADE FAILURE: Authentication failures, service communication breakdown
        """
        # Initial shared secrets
        initial_secrets = {
            "JWT_SECRET_KEY": "initial-jwt-secret-32-characters-minimum",
            "SERVICE_SECRET": "initial-service-secret-32-chars-min",
            "ENCRYPTION_KEY": "initial-encryption-key-32-chars-min"
        }
        
        for key, value in initial_secrets.items():
            self.env.set(key, value, "initial_secrets")
        
        # Verify all services start with same secrets
        services = ["backend", "auth", "websocket"]
        initial_service_secrets = {}
        
        for service in services:
            service_secrets = {}
            for secret_key in initial_secrets:
                service_secrets[secret_key] = self.env.get(secret_key)
            initial_service_secrets[service] = service_secrets
        
        # Verify initial consistency
        for service, secrets in initial_service_secrets.items():
            for secret_key, secret_value in secrets.items():
                expected_value = initial_secrets[secret_key]
                assert secret_value == expected_value, f"{service} initial {secret_key} mismatch"
        
        # Simulate secret rotation
        rotated_secrets = {
            "JWT_SECRET_KEY": "rotated-jwt-secret-32-characters-minimum",
            "SERVICE_SECRET": "rotated-service-secret-32-chars-min", 
            "ENCRYPTION_KEY": "rotated-encryption-key-32-chars-min"
        }
        
        # Rotate secrets atomically
        for key, value in rotated_secrets.items():
            success = self.env.set(key, value, "secret_rotation")
            assert success, f"Failed to rotate secret: {key}"
        
        # Verify all services see rotated secrets immediately
        for service in services:
            for secret_key, expected_value in rotated_secrets.items():
                actual_value = self.env.get(secret_key)
                assert actual_value == expected_value, (
                    f"{service} failed to get rotated {secret_key}: {actual_value}"
                )
        
        # Verify no service still has old secrets
        for service in services:
            for secret_key, old_value in initial_secrets.items():
                current_value = self.env.get(secret_key)
                assert current_value != old_value, f"{service} still using old {secret_key}"

    def test_environment_transition_config_consistency(self):
        """
        CRITICAL: Test configuration consistency during environment transitions.
        
        PREVENTS: Mixed environment configurations causing system instability
        CASCADE FAILURE: Wrong APIs called, data corruption, security breaches
        """
        # Test environment transition scenarios
        environment_transitions = [
            ("development", "staging"),
            ("staging", "production"),
            ("test", "development")
        ]
        
        for from_env, to_env in environment_transitions:
            self.env.clear()
            
            # Set up source environment configuration
            from_config = self._get_environment_config(from_env)
            for key, value in from_config.items():
                self.env.set(key, value, f"{from_env}_config")
            
            # Verify source environment is properly configured
            assert self.env.get("ENVIRONMENT") == from_env
            self._validate_environment_consistency(from_env)
            
            # Simulate environment transition
            to_config = self._get_environment_config(to_env)
            
            # Transition should be atomic - all configs updated together
            for key, value in to_config.items():
                self.env.set(key, value, f"{to_env}_transition")
            
            # Verify target environment is properly configured
            assert self.env.get("ENVIRONMENT") == to_env
            self._validate_environment_consistency(to_env)
            
            # Verify no configuration leakage from source environment
            self._verify_no_environment_leakage(from_env, to_env)

    def _get_environment_config(self, environment):
        """Get standard configuration for an environment."""
        configs = {
            "development": {
                "ENVIRONMENT": "development",
                "DEBUG": "true",
                "DATABASE_URL": "postgresql://localhost:5432/netra_dev",
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",
                "LOG_LEVEL": "DEBUG"
            },
            "staging": {
                "ENVIRONMENT": "staging",
                "DEBUG": "false", 
                "DATABASE_URL": "postgresql://staging-db.gcp:5432/netra_staging",
                "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
                "LOG_LEVEL": "INFO"
            },
            "production": {
                "ENVIRONMENT": "production",
                "DEBUG": "false",
                "DATABASE_URL": "postgresql://prod-db.gcp:5432/netra_production",
                "NEXT_PUBLIC_API_URL": "https://api.netrasystems.ai",
                "LOG_LEVEL": "WARNING"
            },
            "test": {
                "ENVIRONMENT": "test",
                "DEBUG": "true",
                "DATABASE_URL": "postgresql://localhost:5434/netra_test",
                "NEXT_PUBLIC_API_URL": "http://localhost:8000",
                "LOG_LEVEL": "DEBUG"
            }
        }
        return configs[environment]

    def _validate_environment_consistency(self, environment):
        """Validate environment configuration is internally consistent."""
        api_url = self.env.get("NEXT_PUBLIC_API_URL")
        db_url = self.env.get("DATABASE_URL")
        debug = self.env.get("DEBUG", "false").lower()
        
        if environment == "development":
            assert "localhost" in api_url, f"Development should use localhost API: {api_url}"
            assert debug == "true", f"Development should have debug enabled: {debug}"
        elif environment in ["staging", "production"]:
            assert "localhost" not in api_url, f"{environment} should not use localhost: {api_url}"
            assert api_url.startswith("https://"), f"{environment} should use HTTPS: {api_url}"
            if environment == "staging":
                assert "staging" in api_url, f"Staging should have staging domain: {api_url}"
            else:  # production
                assert "staging" not in api_url, f"Production should not have staging domain: {api_url}"

    def _verify_no_environment_leakage(self, from_env, to_env):
        """Verify no configuration leaked from source to target environment."""
        current_api_url = self.env.get("NEXT_PUBLIC_API_URL")
        current_db_url = self.env.get("DATABASE_URL")
        
        # Check for environment-specific leakage patterns
        if from_env == "development" and to_env in ["staging", "production"]:
            assert "localhost" not in current_api_url, f"Localhost leaked from {from_env} to {to_env}"
        
        if from_env == "staging" and to_env == "production":
            assert "staging" not in current_api_url, f"Staging domain leaked to production"
            assert "staging" not in current_db_url, f"Staging database leaked to production"
        
        if from_env in ["staging", "production"] and to_env == "development":
            assert "localhost" in current_api_url, f"Remote API URL leaked from {from_env} to development"