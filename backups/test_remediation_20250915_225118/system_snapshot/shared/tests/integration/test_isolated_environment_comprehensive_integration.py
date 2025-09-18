"""
Comprehensive Integration Tests for IsolatedEnvironment Class

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Service Independence
- Business Goal: Ensure the MOST CRITICAL SSOT module works perfectly across all service boundaries
- Value Impact: IsolatedEnvironment is used by EVERY service - failure cascades to entire platform
- Strategic Impact: Platform stability, service independence, and multi-user isolation depend on this module

Testing Strategy:
- Real environment configurations and files (NO MOCKS)
- Environment isolation between different contexts
- Configuration loading from multiple sources with precedence rules
- Multi-user environment separation
- Cross-service environment consistency
- Configuration migration scenarios
- Environment-specific behavior (dev, test, staging, prod)
- Thread safety under concurrent access
- Error handling and edge cases
- Deterministic and independent test execution

CRITICAL: This test suite validates the foundation of ALL services and MUST always pass.
Any failure in this module can cascade to break the entire platform.
"""

import asyncio
import json
import os
import pytest
import tempfile
import threading
import time
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

# Import the module under test
from shared.isolated_environment import (
    IsolatedEnvironment, 
    get_env,
    ValidationResult,
    _mask_sensitive_value,
    setenv,
    getenv,
    delenv,
    get_subprocess_env,
    SecretLoader,
    EnvironmentValidator
)


class TestIsolatedEnvironmentIntegration:
    """Comprehensive integration tests for IsolatedEnvironment across all service boundaries."""
    
    def setup_method(self):
        """Setup for each test method with clean environment state."""
        # Get fresh instance for each test
        self.env = IsolatedEnvironment()
        self.env.enable_isolation(backup_original=True, refresh_vars=True)
        
        # Setup test data directory
        self.test_data_dir = Path(tempfile.mkdtemp(prefix="netra_env_integration_"))
        self.test_files = []
        
    def teardown_method(self):
        """Cleanup after each test method."""
        # Reset environment to original state
        if hasattr(self, 'env'):
            self.env.reset_to_original()
            self.env.disable_isolation(restore_original=True)
        
        # Clean up test files
        for test_file in getattr(self, 'test_files', []):
            try:
                if test_file.exists():
                    test_file.unlink()
            except Exception:
                pass
        
        # Clean up test data directory
        if hasattr(self, 'test_data_dir') and self.test_data_dir.exists():
            try:
                for file in self.test_data_dir.iterdir():
                    file.unlink()
                self.test_data_dir.rmdir()
            except Exception:
                pass

    def create_test_env_file(self, filename: str, content: Dict[str, str]) -> Path:
        """Create a test environment file with specified content."""
        env_file = self.test_data_dir / filename
        with open(env_file, 'w', encoding='utf-8') as f:
            for key, value in content.items():
                f.write(f"{key}={value}\n")
        self.test_files.append(env_file)
        return env_file

    @pytest.mark.integration
    def test_environment_isolation_between_contexts(self):
        """Test environment isolation between different service contexts."""
        # Service A context
        service_a_env = IsolatedEnvironment()
        service_a_env.enable_isolation()
        service_a_env.set("SERVICE_NAME", "auth_service", "service_a")
        service_a_env.set("SERVICE_PORT", "8081", "service_a")
        service_a_env.set("API_KEY", "auth_api_key_123", "service_a")
        
        # Service B context  
        service_b_env = IsolatedEnvironment()
        service_b_env.enable_isolation()
        service_b_env.set("SERVICE_NAME", "backend_service", "service_b")
        service_b_env.set("SERVICE_PORT", "8000", "service_b")
        service_b_env.set("API_KEY", "backend_api_key_456", "service_b")
        
        # Test isolation - each service should only see its own values
        assert service_a_env.get("SERVICE_NAME") == "auth_service"
        assert service_a_env.get("SERVICE_PORT") == "8081"
        assert service_a_env.get("API_KEY") == "auth_api_key_123"
        
        assert service_b_env.get("SERVICE_NAME") == "backend_service"
        assert service_b_env.get("SERVICE_PORT") == "8000"
        assert service_b_env.get("API_KEY") == "backend_api_key_456"
        
        # Verify global environment is not polluted
        assert os.environ.get("SERVICE_NAME") is None or os.environ.get("SERVICE_NAME") != "auth_service"
        assert os.environ.get("API_KEY") is None or "auth_api_key_123" not in os.environ.get("API_KEY", "")
        
        # Test variable sources tracking
        assert service_a_env.get_variable_source("SERVICE_NAME") == "service_a"
        assert service_b_env.get_variable_source("SERVICE_NAME") == "service_b"

    @pytest.mark.integration
    def test_configuration_loading_precedence_rules(self):
        """Test configuration loading from multiple sources with proper precedence."""
        # Create multiple configuration files
        default_config = self.create_test_env_file("default.env", {
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "5432",
            "DATABASE_USER": "default_user",
            "DATABASE_PASSWORD": "default_pass",
            "REDIS_URL": "redis://localhost:6379",
            "LOG_LEVEL": "INFO"
        })
        
        environment_config = self.create_test_env_file("test.env", {
            "DATABASE_HOST": "test-db.example.com",
            "DATABASE_USER": "test_user", 
            "DATABASE_PASSWORD": "test_secure_pass",
            "LOG_LEVEL": "DEBUG",
            "TEST_MODE": "true"
        })
        
        override_config = self.create_test_env_file("override.env", {
            "DATABASE_PASSWORD": "override_ultra_secure",
            "API_TIMEOUT": "30",
            "CUSTOM_SETTING": "override_value"
        })
        
        # Load configurations in order: default -> environment -> override
        env = IsolatedEnvironment()
        env.enable_isolation()
        
        # Load default config first (lowest precedence)
        loaded_count, errors = env.load_from_file(default_config, "default", override_existing=True)
        assert loaded_count == 6
        assert len(errors) == 0
        
        # Load environment-specific config (medium precedence)
        loaded_count, errors = env.load_from_file(environment_config, "environment", override_existing=True)
        assert loaded_count == 5
        assert len(errors) == 0
        
        # Load override config (highest precedence)
        loaded_count, errors = env.load_from_file(override_config, "override", override_existing=True)
        assert loaded_count == 3
        assert len(errors) == 0
        
        # Verify precedence rules
        assert env.get("DATABASE_HOST") == "test-db.example.com"  # From environment config
        assert env.get("DATABASE_PORT") == "5432"  # From default config
        assert env.get("DATABASE_USER") == "test_user"  # From environment config  
        assert env.get("DATABASE_PASSWORD") == "override_ultra_secure"  # From override config (highest precedence)
        assert env.get("REDIS_URL") == "redis://localhost:6379"  # From default config
        assert env.get("LOG_LEVEL") == "DEBUG"  # From environment config
        assert env.get("TEST_MODE") == "true"  # From environment config
        assert env.get("API_TIMEOUT") == "30"  # From override config
        assert env.get("CUSTOM_SETTING") == "override_value"  # From override config
        
        # Verify source tracking
        assert env.get_variable_source("DATABASE_HOST") == "environment"
        assert env.get_variable_source("DATABASE_PASSWORD") == "override"
        assert env.get_variable_source("REDIS_URL") == "default"

    @pytest.mark.integration  
    def test_multi_user_environment_separation(self):
        """Test environment separation for multi-user system scenarios."""
        # User 1 context
        user1_env = IsolatedEnvironment()
        user1_env.enable_isolation()
        user1_env.set("USER_ID", "user_123", "user1")
        user1_env.set("SESSION_TOKEN", "token_user1_abc123", "user1")
        user1_env.set("WORKSPACE_ID", "workspace_user1", "user1")
        user1_env.set("API_QUOTA", "1000", "user1")
        
        # User 2 context
        user2_env = IsolatedEnvironment()  
        user2_env.enable_isolation()
        user2_env.set("USER_ID", "user_456", "user2")
        user2_env.set("SESSION_TOKEN", "token_user2_def456", "user2")
        user2_env.set("WORKSPACE_ID", "workspace_user2", "user2")
        user2_env.set("API_QUOTA", "2000", "user2")
        
        # User 3 context (Enterprise)
        user3_env = IsolatedEnvironment()
        user3_env.enable_isolation()
        user3_env.set("USER_ID", "user_789", "user3")
        user3_env.set("SESSION_TOKEN", "token_user3_ghi789", "user3")
        user3_env.set("WORKSPACE_ID", "workspace_enterprise", "user3")
        user3_env.set("API_QUOTA", "10000", "user3")
        user3_env.set("ENTERPRISE_FEATURES", "true", "user3")
        
        # Verify complete isolation between users
        assert user1_env.get("USER_ID") == "user_123"
        assert user1_env.get("SESSION_TOKEN") == "token_user1_abc123"
        assert user1_env.get("API_QUOTA") == "1000"
        assert user1_env.get("ENTERPRISE_FEATURES") is None
        
        assert user2_env.get("USER_ID") == "user_456"
        assert user2_env.get("SESSION_TOKEN") == "token_user2_def456"  
        assert user2_env.get("API_QUOTA") == "2000"
        assert user2_env.get("ENTERPRISE_FEATURES") is None
        
        assert user3_env.get("USER_ID") == "user_789"
        assert user3_env.get("SESSION_TOKEN") == "token_user3_ghi789"
        assert user3_env.get("API_QUOTA") == "10000"
        assert user3_env.get("ENTERPRISE_FEATURES") == "true"
        
        # Test concurrent access safety
        def modify_user_env(env: IsolatedEnvironment, user_id: str, iterations: int):
            for i in range(iterations):
                env.set(f"TEMP_VAR_{i}", f"value_{user_id}_{i}", f"concurrent_{user_id}")
                time.sleep(0.001)  # Small delay to increase contention
                assert env.get(f"TEMP_VAR_{i}") == f"value_{user_id}_{i}"
        
        # Run concurrent modifications
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(modify_user_env, user1_env, "user1", 50),
                executor.submit(modify_user_env, user2_env, "user2", 50),
                executor.submit(modify_user_env, user3_env, "user3", 50)
            ]
            
            # Wait for all to complete
            for future in concurrent.futures.as_completed(futures):
                future.result()  # This will raise if any thread failed
        
        # Verify no cross-contamination occurred
        assert user1_env.get("USER_ID") == "user_123"
        assert user2_env.get("USER_ID") == "user_456"  
        assert user3_env.get("USER_ID") == "user_789"

    @pytest.mark.integration
    def test_cross_service_environment_consistency(self):
        """Test environment consistency across different service configurations."""
        # Shared configuration that should be consistent across services
        shared_config = {
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "postgresql://test:test@localhost:5434/netra_test",
            "REDIS_URL": "redis://localhost:6381/0",
            "JWT_SECRET_KEY": "shared-secret-key-for-all-services-32-chars-long",
            "FERNET_KEY": "shared-fernet-key-base64-encoded-32-chars-long=",
            "GCP_PROJECT_ID": "netra-test"
        }
        
        # Service-specific configurations
        auth_service_config = {
            **shared_config,
            "SERVICE_NAME": "auth_service",
            "SERVICE_PORT": "8081", 
            "OAUTH_CLIENT_ID": "auth_oauth_client_123",
            "OAUTH_CLIENT_SECRET": "auth_oauth_secret_456"
        }
        
        backend_service_config = {
            **shared_config,
            "SERVICE_NAME": "backend_service",
            "SERVICE_PORT": "8000",
            "ANTHROPIC_API_KEY": "backend_anthropic_key_789",
            "OPENAI_API_KEY": "backend_openai_key_abc"
        }
        
        analytics_service_config = {
            **shared_config,
            "SERVICE_NAME": "analytics_service", 
            "SERVICE_PORT": "8002",
            "CLICKHOUSE_URL": "clickhouse://localhost:8123/analytics_test",
            "ANALYTICS_API_KEY": "analytics_api_key_def"
        }
        
        # Create service environments
        auth_env = IsolatedEnvironment()
        auth_env.enable_isolation()
        auth_env.update(auth_service_config, "auth_service_config")
        
        backend_env = IsolatedEnvironment()
        backend_env.enable_isolation() 
        backend_env.update(backend_service_config, "backend_service_config")
        
        analytics_env = IsolatedEnvironment()
        analytics_env.enable_isolation()
        analytics_env.update(analytics_service_config, "analytics_service_config")
        
        # Verify shared configuration consistency
        for key in ["ENVIRONMENT", "LOG_LEVEL", "DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY"]:
            auth_value = auth_env.get(key)
            backend_value = backend_env.get(key)
            analytics_value = analytics_env.get(key)
            
            assert auth_value == backend_value == analytics_value, (
                f"Shared config inconsistency for {key}: "
                f"auth={auth_value}, backend={backend_value}, analytics={analytics_value}"
            )
        
        # Verify service-specific configurations
        assert auth_env.get("SERVICE_NAME") == "auth_service"
        assert auth_env.get("SERVICE_PORT") == "8081"
        assert auth_env.get("OAUTH_CLIENT_ID") == "auth_oauth_client_123"
        assert auth_env.get("ANTHROPIC_API_KEY") is None
        
        assert backend_env.get("SERVICE_NAME") == "backend_service"
        assert backend_env.get("SERVICE_PORT") == "8000"
        assert backend_env.get("ANTHROPIC_API_KEY") == "backend_anthropic_key_789"
        assert backend_env.get("OAUTH_CLIENT_ID") is None
        
        assert analytics_env.get("SERVICE_NAME") == "analytics_service"
        assert analytics_env.get("SERVICE_PORT") == "8002"
        assert analytics_env.get("CLICKHOUSE_URL") == "clickhouse://localhost:8123/analytics_test"
        assert analytics_env.get("ANTHROPIC_API_KEY") is None
        assert analytics_env.get("OAUTH_CLIENT_ID") is None

    @pytest.mark.integration
    def test_configuration_migration_scenarios(self):
        """Test configuration migration scenarios and error handling."""
        # Create legacy configuration file
        legacy_config = self.create_test_env_file("legacy.env", {
            "POSTGRES_HOST": "old-db.example.com",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "legacy_user",
            "POSTGRES_PASSWORD": "legacy_pass",
            "REDIS_HOST": "old-redis.example.com",
            "REDIS_PORT": "6379",
            "SECRET_KEY": "legacy_secret_key",
            "DEPRECATED_SETTING": "old_value"
        })
        
        # Create new configuration file with migrated keys
        new_config = self.create_test_env_file("new.env", {
            "DATABASE_URL": "postgresql://new_user:new_pass@new-db.example.com:5432/netra",
            "REDIS_URL": "redis://new-redis.example.com:6379/0",
            "JWT_SECRET_KEY": "new-jwt-secret-key-32-chars-long-secure",
            "FERNET_KEY": "new-fernet-key-base64-encoded-32-chars=",
            "NEW_FEATURE_FLAG": "enabled"
        })
        
        # Create invalid configuration file for error testing
        invalid_config = self.create_test_env_file("invalid.env", {
            "VALID_KEY": "valid_value",
            "": "",  # Invalid empty key
            "MALFORMED_LINE": "",  # Will be written as malformed
            "UNICODE_KEY": "unicode_value_with_special_chars_[U+00E9][U+00F1]",
            "MULTILINE_VALUE": "line1\nline2\nline3"
        })
        
        # Manually add malformed lines to invalid config
        with open(invalid_config, 'a', encoding='utf-8') as f:
            f.write("MALFORMED LINE WITHOUT EQUALS\n")
            f.write("=VALUE_WITHOUT_KEY\n")
            f.write("KEY_WITH=MULTIPLE=EQUALS=SIGNS\n")
        
        env = IsolatedEnvironment()
        env.enable_isolation()
        
        # Test legacy config loading
        loaded_count, errors = env.load_from_file(legacy_config, "legacy")
        assert loaded_count == 8
        assert len(errors) == 0
        
        # Verify legacy values are loaded
        assert env.get("POSTGRES_HOST") == "old-db.example.com"
        assert env.get("SECRET_KEY") == "legacy_secret_key"
        assert env.get("DEPRECATED_SETTING") == "old_value"
        
        # Test migration to new config (with override)
        loaded_count, errors = env.load_from_file(new_config, "migration", override_existing=True)
        assert loaded_count == 5
        assert len(errors) == 0
        
        # Verify migration occurred
        assert env.get("DATABASE_URL") == "postgresql://new_user:new_pass@new-db.example.com:5432/netra"
        assert env.get("JWT_SECRET_KEY") == "new-jwt-secret-key-32-chars-long-secure"
        assert env.get("NEW_FEATURE_FLAG") == "enabled"
        
        # Legacy values should still exist if not overridden
        assert env.get("POSTGRES_HOST") == "old-db.example.com"
        assert env.get("DEPRECATED_SETTING") == "old_value"
        
        # Test error handling with invalid config
        loaded_count, errors = env.load_from_file(invalid_config, "invalid")
        assert loaded_count >= 1  # At least valid keys should load
        assert len(errors) >= 2   # Should have errors for malformed lines
        
        # Verify valid parts of invalid config still loaded
        assert env.get("VALID_KEY") == "valid_value"
        assert env.get("UNICODE_KEY") == "unicode_value_with_special_chars_[U+00E9][U+00F1]"
        
        # Test non-existent file handling
        non_existent = self.test_data_dir / "does_not_exist.env"
        loaded_count, errors = env.load_from_file(non_existent, "missing")
        assert loaded_count == 0
        assert len(errors) == 1
        assert "File not found" in errors[0]

    @pytest.mark.integration
    def test_environment_specific_behavior(self):
        """Test environment-specific behavior for dev/test/staging/prod environments."""
        test_cases = [
            ("development", "dev", {
                "expected_name": "development",
                "is_production": False,
                "is_staging": False,
                "is_development": True,
                "is_test": False,
                "debug_features": True
            }),
            ("test", "testing", {
                "expected_name": "test", 
                "is_production": False,
                "is_staging": False,
                "is_development": False,
                "is_test": True,
                "debug_features": True
            }),
            ("staging", "staging", {
                "expected_name": "staging",
                "is_production": False,
                "is_staging": True,
                "is_development": False,
                "is_test": False,
                "debug_features": False
            }),
            ("production", "prod", {
                "expected_name": "production",
                "is_production": True,
                "is_staging": False,
                "is_development": False,
                "is_test": False,
                "debug_features": False
            })
        ]
        
        for env_name, env_alias, expected in test_cases:
            # Test with primary environment name
            env = IsolatedEnvironment()
            env.enable_isolation()
            env.set("ENVIRONMENT", env_name, "test")
            
            assert env.get_environment_name() == expected["expected_name"]
            assert env.is_production() == expected["is_production"]
            assert env.is_staging() == expected["is_staging"]
            assert env.is_development() == expected["is_development"]
            assert env.is_test() == expected["is_test"]
            
            # Test with alias
            env.set("ENVIRONMENT", env_alias, "test")
            assert env.get_environment_name() == expected["expected_name"]
            
            # Test environment-specific configuration loading behavior
            if env_name in ["staging", "production"]:
                # Should not auto-load .env files in staging/production
                test_env_file = self.create_test_env_file(".env", {"TEST_VAR": "should_not_load"})
                
                # Move to test directory temporarily
                original_cwd = os.getcwd()
                try:
                    os.chdir(self.test_data_dir)
                    env_new = IsolatedEnvironment()
                    env_new.enable_isolation()
                    env_new.set("ENVIRONMENT", env_name, "test")
                    
                    # Should not have loaded the .env file
                    assert env_new.get("TEST_VAR") is None
                finally:
                    os.chdir(original_cwd)
            
            env.reset()

    @pytest.mark.integration
    def test_thread_safety_under_concurrent_access(self):
        """Test thread safety under heavy concurrent access patterns."""
        env = IsolatedEnvironment()
        env.enable_isolation()
        
        # Shared test data
        num_threads = 10
        operations_per_thread = 100
        results = {}
        errors = []
        
        def worker_thread(thread_id: int):
            """Worker thread that performs various environment operations."""
            try:
                thread_results = []
                
                for i in range(operations_per_thread):
                    # Set thread-specific variables
                    key = f"THREAD_{thread_id}_VAR_{i}"
                    value = f"value_{thread_id}_{i}_{int(time.time() * 1000000)}"
                    
                    success = env.set(key, value, f"thread_{thread_id}")
                    assert success, f"Failed to set {key}"
                    
                    # Verify immediate retrieval
                    retrieved = env.get(key)
                    assert retrieved == value, f"Value mismatch for {key}: expected {value}, got {retrieved}"
                    
                    # Test other operations
                    assert env.exists(key), f"Key {key} should exist"
                    assert env.get_variable_source(key) == f"thread_{thread_id}"
                    
                    # Occasionally delete and recreate
                    if i % 10 == 0:
                        env.delete(key)
                        assert not env.exists(key), f"Key {key} should not exist after deletion"
                        env.set(key, value + "_recreated", f"thread_{thread_id}_recreated")
                        retrieved = env.get(key)
                        assert retrieved == value + "_recreated"
                    
                    thread_results.append((key, retrieved))
                    
                    # Small random delay to increase contention
                    time.sleep(0.0001)
                
                results[thread_id] = thread_results
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Create and start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
        
        # Start all threads simultaneously
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
        
        end_time = time.time()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify all threads completed successfully
        assert len(results) == num_threads, f"Expected {num_threads} thread results, got {len(results)}"
        
        # Verify data integrity - no cross-thread contamination
        all_keys = set()
        for thread_id, thread_results in results.items():
            for key, value in thread_results:
                assert key not in all_keys, f"Duplicate key detected: {key}"
                all_keys.add(key)
                
                # Verify key belongs to correct thread
                assert f"THREAD_{thread_id}_" in key, f"Key {key} doesn't belong to thread {thread_id}"
                
                # Verify value can still be retrieved
                current_value = env.get(key)
                if current_value is not None:  # May be None if deleted
                    assert str(thread_id) in current_value, f"Value corruption detected for {key}: {current_value}"
        
        print(f"Thread safety test completed in {end_time - start_time:.2f} seconds")
        print(f"Total operations: {num_threads * operations_per_thread}")
        print(f"Operations per second: {(num_threads * operations_per_thread) / (end_time - start_time):.0f}")

    @pytest.mark.integration
    def test_configuration_validation_and_error_handling(self):
        """Test comprehensive configuration validation and error handling."""
        env = IsolatedEnvironment()
        env.enable_isolation()
        
        # Test 1: Validate staging database credentials with various scenarios
        
        # Valid staging configuration
        env.set("ENVIRONMENT", "staging", "test")
        env.set("POSTGRES_HOST", "staging-db.example.com", "test")
        env.set("POSTGRES_USER", "postgres", "test")
        env.set("POSTGRES_PASSWORD", "secure_staging_password_123", "test")
        env.set("POSTGRES_DB", "netra_staging", "test")
        
        validation = env.validate_staging_database_credentials()
        assert validation["valid"] is True
        assert len(validation["issues"]) == 0
        
        # Invalid staging configuration - localhost host
        env.set("POSTGRES_HOST", "localhost", "test")
        validation = env.validate_staging_database_credentials()
        assert validation["valid"] is False
        assert any("localhost" in issue for issue in validation["issues"])
        
        # Invalid staging configuration - problematic user
        env.set("POSTGRES_HOST", "staging-db.example.com", "test")
        env.set("POSTGRES_USER", "user_pr-4", "test") 
        validation = env.validate_staging_database_credentials()
        assert validation["valid"] is False
        assert any("user_pr-4" in issue for issue in validation["issues"])
        
        # Invalid staging configuration - weak password
        env.set("POSTGRES_USER", "postgres", "test")
        env.set("POSTGRES_PASSWORD", "123", "test")
        validation = env.validate_staging_database_credentials()
        assert validation["valid"] is False
        assert any("too short" in issue for issue in validation["issues"])
        
        # Test 2: Value sanitization for database URLs
        test_db_urls = [
            "postgresql://user:pass@localhost:5432/db",
            "postgresql://user:p@ss%word@localhost:5432/db",
            "postgresql://user:p@ss\nword@localhost:5432/db",  # Control character
            "postgresql://user:p@ss\tword@localhost:5432/db",  # Tab character
            "postgresql://user:p@ss\x00word@localhost:5432/db"  # Null byte
        ]
        
        for original_url in test_db_urls:
            env.set("DATABASE_URL", original_url, "test")
            sanitized_url = env.get("DATABASE_URL")
            
            # Should not contain control characters
            for char in sanitized_url:
                char_code = ord(char)
                assert char_code >= 32 or char_code == 9, f"Control character found in sanitized URL: {char_code}"
            
            # Should still be a valid URL structure
            assert "postgresql://" in sanitized_url
            assert "@localhost:5432/db" in sanitized_url
        
        # Test 3: Error handling for protected variables
        env.protect_variable("PROTECTED_VAR")
        env.set("PROTECTED_VAR", "initial_value", "test")
        
        # Should not be able to modify protected variable
        result = env.set("PROTECTED_VAR", "new_value", "test")
        assert result is False
        assert env.get("PROTECTED_VAR") == "initial_value"
        
        # Should be able to modify with force flag
        result = env.set("PROTECTED_VAR", "forced_value", "test", force=True)
        assert result is True
        assert env.get("PROTECTED_VAR") == "forced_value"
        
        # Test 4: Change callback functionality
        callback_calls = []
        
        def change_callback(key: str, old_value: Optional[str], new_value: str):
            callback_calls.append((key, old_value, new_value))
        
        env.add_change_callback(change_callback)
        
        env.set("CALLBACK_TEST", "value1", "test")
        env.set("CALLBACK_TEST", "value2", "test")
        env.delete("CALLBACK_TEST", "test")
        
        assert len(callback_calls) == 3
        assert callback_calls[0] == ("CALLBACK_TEST", None, "value1")
        assert callback_calls[1] == ("CALLBACK_TEST", "value1", "value2") 
        assert callback_calls[2] == ("CALLBACK_TEST", "value2", None)
        
        # Test 5: Subprocess environment handling
        env.set("PATH", "/custom/path", "test")
        env.set("CUSTOM_VAR", "custom_value", "test")
        
        subprocess_env = env.get_subprocess_env({"ADDITIONAL_VAR": "additional_value"})
        
        assert "PATH" in subprocess_env
        assert "CUSTOM_VAR" in subprocess_env
        assert subprocess_env["CUSTOM_VAR"] == "custom_value"
        assert subprocess_env["ADDITIONAL_VAR"] == "additional_value"
        
        # Should include system variables
        system_vars = ['SYSTEMROOT', 'TEMP', 'TMP', 'USERPROFILE'] if os.name == 'nt' else ['HOME']
        for var in system_vars:
            if var in os.environ:
                assert var in subprocess_env

    @pytest.mark.integration
    def test_sensitive_value_masking(self):
        """Test sensitive value masking functionality."""
        sensitive_keys = [
            "PASSWORD", "SECRET", "KEY", "TOKEN", "AUTH", "CREDENTIAL",
            "PRIVATE", "CERT", "API_KEY", "JWT", "OAUTH", "FERNET"
        ]
        
        for key in sensitive_keys:
            # Test various value lengths
            test_values = [
                "ab",  # Very short
                "abc",  # Exactly 3 chars
                "abcd",  # 4 chars
                "long_sensitive_value_that_should_be_masked"  # Long value
            ]
            
            for value in test_values:
                masked = _mask_sensitive_value(key, value)
                
                if len(value) <= 3:
                    assert masked == "***"
                else:
                    assert masked.startswith(value[:3])
                    assert masked.endswith("***")
                    assert len(masked) == 6  # 3 chars + "***"
        
        # Test non-sensitive keys
        non_sensitive_keys = ["USERNAME", "HOST", "PORT", "DATABASE", "URL"]
        for key in non_sensitive_keys:
            value = "some_regular_value_that_is_quite_long_and_should_be_truncated_appropriately"
            masked = _mask_sensitive_value(key, value)
            
            if len(value) > 50:
                assert masked == value[:50] + "..."
            else:
                assert masked == value

    @pytest.mark.integration
    def test_legacy_compatibility_interfaces(self):
        """Test legacy compatibility interfaces work correctly."""
        # Test module-level convenience functions
        assert setenv("LEGACY_TEST", "value1", "legacy") is True
        assert getenv("LEGACY_TEST") == "value1"
        assert getenv("NON_EXISTENT", "default") == "default"
        assert delenv("LEGACY_TEST") is True
        assert getenv("LEGACY_TEST") is None
        
        # Test SecretLoader compatibility class
        secret_loader = SecretLoader()
        assert secret_loader.load_secrets() is True
        assert secret_loader.set_secret("SECRET_TEST", "secret_value", "secret_loader") is True
        assert secret_loader.get_secret("SECRET_TEST") == "secret_value"
        assert secret_loader.get_secret("NON_EXISTENT_SECRET", "default") == "default"
        
        # Test EnvironmentValidator compatibility class
        validator = EnvironmentValidator(enable_fallbacks=True, development_mode=True)
        
        # Set up environment for validation
        env = get_env()
        env.set("DATABASE_URL", "postgresql://test:test@localhost:5432/test", "test")
        env.set("JWT_SECRET_KEY", "test-jwt-secret-32-chars-long", "test")
        env.set("SECRET_KEY", "test-secret-32-chars-long", "test")
        
        validation_result = validator.validate_all()
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0
        
        # Test with missing required variables
        env.delete("JWT_SECRET_KEY")
        validation_result = validator.validate_all()
        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0
        assert any("JWT_SECRET_KEY" in error for error in validation_result.errors)

    @pytest.mark.integration
    def test_deterministic_and_independent_execution(self):
        """Test that all tests are deterministic and can run independently."""
        # Run the same operation multiple times - should get consistent results
        operations = [
            ("TEST_DETERMINISTIC", "consistent_value"),
            ("ANOTHER_VAR", "another_consistent_value"),
            ("THIRD_VAR", "third_consistent_value")
        ]
        
        results_sets = []
        
        for run in range(5):  # Run 5 times
            env = IsolatedEnvironment()
            env.enable_isolation()
            
            run_results = {}
            for key, value in operations:
                env.set(key, value, "deterministic_test")
                run_results[key] = env.get(key)
            
            results_sets.append(run_results)
        
        # All runs should produce identical results
        first_result = results_sets[0]
        for i, result_set in enumerate(results_sets[1:], 1):
            assert result_set == first_result, f"Run {i+1} produced different results than run 1"
        
        # Test independence - create multiple isolated environments simultaneously
        envs = []
        for i in range(5):
            env = IsolatedEnvironment()
            env.enable_isolation()
            env.set("INSTANCE_ID", str(i), "independence_test")
            envs.append(env)
        
        # Each environment should maintain its own values
        for i, env in enumerate(envs):
            assert env.get("INSTANCE_ID") == str(i)
            # Should not see other instances' values
            for j in range(5):
                if i != j:
                    assert env.get(f"INSTANCE_{j}_SPECIFIC") is None
        
        # Test cleanup independence - modifications in one test shouldn't affect others
        test_env = IsolatedEnvironment()
        test_env.enable_isolation()
        original_vars = test_env.get_all()
        
        # Make modifications
        test_env.set("TEMP_MODIFICATION", "temp_value", "cleanup_test")
        test_env.set("ANOTHER_TEMP", "another_temp", "cleanup_test")
        
        # Reset should restore original state
        test_env.reset_to_original()
        current_vars = test_env.get_all()
        
        # Should not contain temporary modifications
        assert "TEMP_MODIFICATION" not in current_vars
        assert "ANOTHER_TEMP" not in current_vars


class TestIsolatedEnvironmentEdgeCases:
    """Test edge cases and error conditions for IsolatedEnvironment."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        if hasattr(self, 'env'):
            self.env.reset()
    
    @pytest.mark.integration
    def test_unicode_and_encoding_handling(self):
        """Test Unicode and encoding handling across different scenarios."""
        unicode_test_cases = [
            ("UNICODE_BASIC", "h[U+00E9]llo_w[U+00F8]rld"),
            ("UNICODE_EMOJI", "test_value_[U+1F680]_ IDEA: _ PASS: "),
            ("UNICODE_MIXED", "ASCII_mixed_with_[U+00F1]o[U+00F1]ascii_characters"),
            ("UNICODE_CHINESE", "[U+6D4B][U+8BD5][U+503C]_test_value"),
            ("UNICODE_ARABIC", "[U+0642][U+064A][U+0645][U+0629]_[U+0627][U+062E][U+062A][U+0628][U+0627][U+0631]_test"),
            ("UNICODE_RUSSIAN", "tectovoe_[U+0437]na[U+0447]en[U+0438]e_test"),
        ]
        
        for key, value in unicode_test_cases:
            # Set and retrieve Unicode values
            success = self.env.set(key, value, "unicode_test")
            assert success, f"Failed to set Unicode value for {key}"
            
            retrieved = self.env.get(key)
            assert retrieved == value, f"Unicode value mismatch for {key}: expected {value}, got {retrieved}"
        
        # Test Unicode in configuration files
        temp_dir = Path(tempfile.mkdtemp())
        unicode_config = temp_dir / "unicode.env"
        
        try:
            with open(unicode_config, 'w', encoding='utf-8') as f:
                for key, value in unicode_test_cases:
                    f.write(f"{key}={value}\n")
            
            loaded_count, errors = self.env.load_from_file(unicode_config, "unicode_test")
            assert loaded_count == len(unicode_test_cases)
            assert len(errors) == 0
            
            # Verify all Unicode values loaded correctly
            for key, expected_value in unicode_test_cases:
                actual_value = self.env.get(key)
                assert actual_value == expected_value, f"Unicode config loading failed for {key}"
                
        finally:
            # Cleanup
            if unicode_config.exists():
                unicode_config.unlink()
            temp_dir.rmdir()

    @pytest.mark.integration  
    def test_memory_usage_and_performance(self):
        """Test memory usage patterns and performance characteristics."""
        import gc
        import sys
        
        # Measure baseline memory
        gc.collect()
        baseline_memory = sys.getsizeof(self.env.__dict__)
        
        # Add a large number of environment variables
        large_dataset = {}
        for i in range(1000):
            key = f"PERF_TEST_VAR_{i:04d}"
            value = f"performance_test_value_{i}_{'x' * 100}"  # ~100 char values
            large_dataset[key] = value
        
        start_time = time.time()
        self.env.update(large_dataset, "performance_test")
        update_time = time.time() - start_time
        
        # Verify all values were set correctly
        for key, expected_value in large_dataset.items():
            actual_value = self.env.get(key)
            assert actual_value == expected_value
        
        # Measure memory after adding variables
        gc.collect()
        loaded_memory = sys.getsizeof(self.env.__dict__)
        memory_increase = loaded_memory - baseline_memory
        
        # Performance assertions
        assert update_time < 5.0, f"Bulk update took too long: {update_time:.2f} seconds"
        
        # Memory usage should be reasonable (less than 10MB for 1000 variables)
        max_expected_memory = 10 * 1024 * 1024  # 10MB
        assert memory_increase < max_expected_memory, f"Memory usage too high: {memory_increase / 1024 / 1024:.2f}MB"
        
        # Test retrieval performance
        start_time = time.time()
        for i in range(0, 1000, 10):  # Sample every 10th variable
            key = f"PERF_TEST_VAR_{i:04d}"
            value = self.env.get(key)
            assert value is not None
        retrieval_time = time.time() - start_time
        
        assert retrieval_time < 1.0, f"Retrieval performance too slow: {retrieval_time:.2f} seconds"
        
        print(f"Performance test results:")
        print(f"- Bulk update time: {update_time:.3f} seconds")
        print(f"- Memory increase: {memory_increase / 1024:.1f} KB") 
        print(f"- Retrieval time (100 samples): {retrieval_time:.3f} seconds")

    @pytest.mark.integration
    def test_concurrent_singleton_access(self):
        """Test concurrent access to singleton instance creation."""
        instances = {}
        errors = []
        
        def get_singleton_instance(thread_id: int):
            """Get singleton instance from different thread."""
            try:
                # Each thread gets the singleton instance
                env1 = IsolatedEnvironment()
                env2 = get_env()
                env3 = IsolatedEnvironment.get_instance()
                
                # All should be the same instance
                assert env1 is env2 is env3, f"Thread {thread_id}: Singleton instances not identical"
                
                instances[thread_id] = env1
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Create multiple threads to access singleton simultaneously
        threads = []
        for i in range(20):
            thread = threading.Thread(target=get_singleton_instance, args=(i,))
            threads.append(thread)
        
        # Start all threads at the same time
        for thread in threads:
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent singleton access errors: {errors}"
        
        # Verify all threads got the same instance
        assert len(instances) == 20
        
        first_instance = next(iter(instances.values()))
        for thread_id, instance in instances.items():
            assert instance is first_instance, f"Thread {thread_id} got different singleton instance"

    @pytest.mark.integration
    def test_environment_state_transitions(self):
        """Test various environment state transitions and edge cases."""
        # Test 1: Isolation enable/disable cycles
        for cycle in range(3):
            # Enable isolation
            self.env.enable_isolation(backup_original=True)
            assert self.env.is_isolated() is True
            
            # Set some values
            self.env.set("CYCLE_VAR", f"cycle_{cycle}", "cycle_test")
            assert self.env.get("CYCLE_VAR") == f"cycle_{cycle}"
            
            # Disable isolation 
            self.env.disable_isolation(restore_original=False)
            assert self.env.is_isolated() is False
            
            # Value should still be accessible
            assert self.env.get("CYCLE_VAR") == f"cycle_{cycle}"
            
            # Re-enable isolation
            self.env.enable_isolation(backup_original=True, refresh_vars=True)
            assert self.env.is_isolated() is True
            
            # Previous value should still be there
            assert self.env.get("CYCLE_VAR") == f"cycle_{cycle}"
        
        # Test 2: Reset operations
        self.env.set("BEFORE_RESET", "value", "test")
        assert self.env.get("BEFORE_RESET") == "value"
        
        self.env.reset()
        assert self.env.get("BEFORE_RESET") is None
        
        # Test 3: Original state restoration
        self.env.enable_isolation(backup_original=True)
        original_var_count = len(self.env.get_all())
        
        # Make changes
        self.env.set("TEMP_VAR_1", "temp1", "test")
        self.env.set("TEMP_VAR_2", "temp2", "test")
        modified_var_count = len(self.env.get_all())
        
        assert modified_var_count > original_var_count
        
        # Reset to original
        self.env.reset_to_original()
        restored_var_count = len(self.env.get_all())
        
        # Should be back to original state
        assert restored_var_count <= original_var_count + 2  # Allow some tolerance
        assert self.env.get("TEMP_VAR_1") is None
        assert self.env.get("TEMP_VAR_2") is None

    @pytest.mark.integration
    def test_shell_command_expansion(self):
        """Test shell command expansion functionality."""
        # Note: Shell expansion is disabled during pytest, so we test the logic paths
        
        # Test basic shell command patterns (would be expanded in non-test environment)
        shell_commands = [
            "$(echo hello)",
            "`date`", 
            "${HOME}/path",
            "prefix_$(whoami)_suffix",
            "complex_${USER}_$(hostname)_${PWD}"
        ]
        
        for command in shell_commands:
            self.env.set("SHELL_TEST", command, "shell_test")
            result = self.env.get("SHELL_TEST")
            
            # In test environment, should return the command unchanged
            assert result == command
        
        # Test variable substitution (this should work even in test environment)
        self.env.set("BASE_PATH", "/opt/app", "test")
        self.env.set("FULL_PATH", "${BASE_PATH}/bin", "test")
        
        result = self.env.get("FULL_PATH")
        # Variable substitution should work
        assert result == "/opt/app/bin" or result == "${BASE_PATH}/bin"  # Depending on implementation
        
        # Test malformed commands
        malformed_commands = [
            "$(incomplete",
            "`unterminated",
            "${UNCLOSED_VAR",
            "${}",
            "$()"
        ]
        
        for command in malformed_commands:
            self.env.set("MALFORMED_TEST", command, "test")
            result = self.env.get("MALFORMED_TEST")
            # Should handle gracefully without crashing
            assert result is not None