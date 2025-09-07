"""
ULTRA COMPREHENSIVE Unit Tests for IsolatedEnvironment - MOST CRITICAL SSOT CLASS
Business Value Justification (BVJ):
- Segment: Platform/Internal - FOUNDATION INFRASTRUCTURE
- Business Goal: ZERO-FAILURE environment management across ALL services 
- Value Impact: 100% system stability - ALL services depend on this SINGLE SOURCE OF TRUTH
- Strategic Impact: Platform exists or fails based on this module working correctly

CRITICAL MISSION: This is the MOST IMPORTANT module in the entire platform.
Every service, every test, every configuration depends on IsolatedEnvironment.
ANY bug in this class cascades to COMPLETE SYSTEM FAILURE.

Testing Coverage Goals:
✓ 100% line coverage - Every single line must be tested
✓ 100% branch coverage - Every conditional path must be validated  
✓ 100% business logic coverage - Every business scenario must pass
✓ Performance critical paths - Validated with benchmarks
✓ Thread safety under heavy load - Concurrent access validation
✓ Error handling - All failure modes tested
✓ Windows compatibility - UTF-8 encoding support
✓ Multi-user system support - Service independence verified

ULTRA CRITICAL IMPORTANCE: 
- Singleton pattern MUST be thread-safe under ALL conditions
- Environment isolation MUST prevent configuration drift 
- Source tracking MUST work for debugging production issues
- Sensitive value masking MUST protect secrets in logs
- Test context detection MUST work for proper test isolation
- File loading MUST handle all .env file formats correctly
- Database URL sanitization MUST preserve credentials integrity
- Shell expansion MUST be secure and controllable
- All convenience functions MUST maintain backward compatibility
- Performance MUST scale to 10K+ environment variables
"""

import pytest
import os
import threading
import time
import tempfile
import subprocess
import concurrent.futures
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable, Union
from unittest.mock import patch, Mock, MagicMock
from dataclasses import dataclass, field
import sys
import re
from urllib.parse import urlparse

# ABSOLUTE IMPORTS per SSOT requirements - CLAUDE.md compliance
from shared.isolated_environment import (
    IsolatedEnvironment,
    get_env,
    ValidationResult,
    _mask_sensitive_value,
    setenv,
    getenv,
    delenv,
    get_subprocess_env,
    load_secrets,
    SecretLoader,
    EnvironmentValidator,
    get_environment_manager
)

# Test framework imports
from test_framework.isolated_environment_fixtures import STANDARD_TEST_CONFIG

# Set up logging for detailed test diagnostics
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestIsolatedEnvironmentSingletonAdvanced:
    """Advanced singleton pattern testing - MISSION CRITICAL for platform stability."""
    
    def test_singleton_memory_consistency(self):
        """Test singleton maintains consistent memory address across all access patterns."""
        # Get instance via all possible methods
        instance_direct = IsolatedEnvironment()
        instance_class_method = IsolatedEnvironment.get_instance()
        instance_function = get_env()
        
        # Memory addresses MUST be identical
        memory_id = id(instance_direct)
        assert id(instance_class_method) == memory_id, f"Class method returned different instance: {id(instance_class_method)} vs {memory_id}"
        assert id(instance_function) == memory_id, f"Function returned different instance: {id(instance_function)} vs {memory_id}"
        
        # Object identity MUST be maintained
        assert instance_direct is instance_class_method is instance_function, "Singleton identity violation"
        
    def test_singleton_double_initialization_protection(self):
        """Test singleton prevents double initialization of internal state."""
        env = get_env()
        env.reset()  # Clean state
        
        # Initialize state
        env.enable_isolation()
        env.set("DOUBLE_INIT_TEST", "original", "test_init")
        original_value = env.get("DOUBLE_INIT_TEST")
        
        # Attempt re-initialization via __init__ 
        env.__init__()  # This should be protected
        
        # State MUST be preserved (not reset)
        preserved_value = env.get("DOUBLE_INIT_TEST")
        assert preserved_value == original_value, "Double initialization corrupted state"
        assert env.is_isolated(), "Isolation state lost during re-initialization"
        
        env.reset()
        
    def test_singleton_thread_safety_stress_test(self):
        """Stress test singleton under extreme concurrent access - PERFORMANCE CRITICAL."""
        instances = []
        exceptions = []
        
        def high_frequency_access():
            """Rapidly access singleton multiple ways."""
            try:
                for _ in range(100):  # High frequency
                    # Mix access patterns to stress test
                    instance1 = IsolatedEnvironment()
                    instance2 = get_env()
                    instance3 = IsolatedEnvironment.get_instance()
                    
                    # Verify all are same
                    if not (instance1 is instance2 is instance3):
                        raise ValueError(f"Singleton violation in thread {threading.current_thread().name}")
                    
                    instances.append(instance1)
                    
            except Exception as e:
                exceptions.append(f"Thread {threading.current_thread().name}: {str(e)}")
        
        # Create many threads for maximum contention
        threads = []
        for i in range(20):  # High concurrency
            thread = threading.Thread(target=high_frequency_access, name=f"stress_{i}")
            threads.append(thread)
        
        start_time = time.time()
        
        # Start all simultaneously
        for thread in threads:
            thread.start()
            
        # Wait with timeout
        for thread in threads:
            thread.join(timeout=10.0)
            if thread.is_alive():
                raise AssertionError(f"Thread {thread.name} didn't complete - possible deadlock")
        
        end_time = time.time()
        
        # HARD FAILURE CONDITIONS
        if exceptions:
            raise AssertionError(f"Thread safety violations: {exceptions}")
            
        # Performance requirement - should complete quickly
        elapsed = end_time - start_time
        if elapsed > 5.0:
            raise AssertionError(f"Singleton access too slow under load: {elapsed:.2f}s")
        
        # Verify all instances are identical
        if instances:
            first_instance = instances[0]
            different_instances = [id(inst) for inst in instances if inst is not first_instance]
            if different_instances:
                raise AssertionError(f"Found {len(different_instances)} different instances during stress test")


class TestIsolatedEnvironmentBusinessLogicValidation:
    """Test business logic that powers platform stability - REVENUE IMPACT."""
    
    def test_configuration_drift_prevention(self):
        """Test core business value - preventing configuration drift across services."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Simulate service A setting configuration
        env.set("DATABASE_URL", "postgresql://service-a-config", "service_a")
        env.set("API_ENDPOINT", "https://service-a.api.com", "service_a")
        
        # Simulate service B trying to modify shared config (should be isolated)
        service_b_env = get_env()  # Same instance due to singleton
        service_b_env.set("DATABASE_URL", "postgresql://service-b-config", "service_b")
        
        # Configuration should be overridden (last writer wins) but tracked
        current_db_url = env.get("DATABASE_URL")
        assert current_db_url == "postgresql://service-b-config", "Configuration not updated"
        
        # But source tracking should show the change
        source = env.get_variable_source("DATABASE_URL")
        assert source == "service_b", "Source tracking failed - critical for debugging config issues"
        
        # Service A's other config should remain unchanged
        assert env.get("API_ENDPOINT") == "https://service-a.api.com", "Unrelated config affected"
        
        env.reset()
    
    def test_service_independence_validation(self):
        """Test that services maintain independence through isolation - ARCHITECTURE CRITICAL."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Simulate multiple services with independent configurations
        services_config = {
            "netra_backend": {
                "SERVICE_NAME": "netra_backend",
                "PORT": "8000",
                "DATABASE_URL": "postgresql://backend:pass@localhost:5434/backend_db"
            },
            "auth_service": {
                "SERVICE_NAME": "auth_service", 
                "PORT": "8081",
                "DATABASE_URL": "postgresql://auth:pass@localhost:5434/auth_db"
            },
            "analytics_service": {
                "SERVICE_NAME": "analytics_service",
                "PORT": "8002", 
                "DATABASE_URL": "clickhouse://analytics:pass@localhost:8123/analytics_db"
            }
        }
        
        # Load configurations
        for service_name, config in services_config.items():
            for key, value in config.items():
                env.set(key, value, source=service_name)
        
        # Verify final state reflects last service's config (as expected)
        assert env.get("SERVICE_NAME") == "analytics_service", "Service configuration not applied"
        assert env.get("PORT") == "8002", "Port configuration not applied"
        
        # But verify source tracking maintains service attribution
        service_name_source = env.get_variable_source("SERVICE_NAME") 
        port_source = env.get_variable_source("PORT")
        database_source = env.get_variable_source("DATABASE_URL")
        
        assert service_name_source == "analytics_service", "Service name source tracking failed"
        assert port_source == "analytics_service", "Port source tracking failed"
        assert database_source == "analytics_service", "Database source tracking failed"
        
        env.reset()
    
    def test_multi_user_context_isolation(self):
        """Test multi-user system requirements - USER ISOLATION CRITICAL."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Simulate user-specific environment contexts
        user_contexts = {
            "user_123": {
                "USER_ID": "123",
                "API_QUOTA": "1000",
                "SUBSCRIPTION_TIER": "enterprise"
            },
            "user_456": {
                "USER_ID": "456", 
                "API_QUOTA": "100",
                "SUBSCRIPTION_TIER": "free"
            }
        }
        
        # Test context switching capability
        for user_id, context in user_contexts.items():
            # Clear previous context
            env.clear()
            
            # Load user context
            for key, value in context.items():
                env.set(key, value, source=f"user_context_{user_id}")
            
            # Verify isolation
            assert env.get("USER_ID") == context["USER_ID"], f"User ID isolation failed for {user_id}"
            assert env.get("API_QUOTA") == context["API_QUOTA"], f"API quota isolation failed for {user_id}"
            
            # Verify no bleed from previous context
            other_user_id = "123" if user_id == "user_456" else "456"
            if other_user_id in ["123", "456"]:  # Avoid setting from previous iteration
                other_context = user_contexts.get(f"user_{other_user_id}")
                if other_context and env.get("USER_ID") == other_context["USER_ID"]:
                    raise AssertionError(f"Context bleed detected: {user_id} has {other_user_id}'s context")
        
        env.reset()
    
    def test_secret_management_business_logic(self):
        """Test secret management critical for security - SECURITY BUSINESS VALUE."""
        env = get_env() 
        env.reset()
        env.enable_isolation()
        
        # Test sensitive values masking in logs
        sensitive_secrets = {
            "JWT_SECRET_KEY": "super-secret-jwt-key-32-characters-long",
            "ANTHROPIC_API_KEY": "sk-ant-1234567890abcdef",
            "DATABASE_PASSWORD": "ultra-secure-db-password-123",
            "OAUTH_CLIENT_SECRET": "oauth-secret-abcdef123456",
            "FERNET_KEY": "encryption-key-for-fernet-32-bytes-long=="
        }
        
        for key, secret_value in sensitive_secrets.items():
            # Set secret
            env.set(key, secret_value, "security_test")
            
            # Verify secret is stored correctly
            retrieved = env.get(key)
            assert retrieved == secret_value, f"Secret {key} corrupted during storage"
            
            # Verify masking works
            masked = _mask_sensitive_value(key, secret_value)
            assert masked != secret_value, f"Secret {key} not masked"
            assert len(masked) < len(secret_value), f"Masked value {key} not shortened"
            assert masked.endswith("***"), f"Masked value {key} missing *** suffix"
        
        env.reset()


class TestIsolatedEnvironmentPerformanceCriticalPaths:
    """Performance testing for critical paths - SCALABILITY REQUIREMENTS."""
    
    def test_high_volume_variable_management(self):
        """Test handling thousands of variables - ENTERPRISE SCALE."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Generate large dataset
        num_vars = 5000  # Enterprise scale
        large_dataset = {f"VAR_{i:04d}": f"value_{i}" for i in range(num_vars)}
        
        # Time bulk operations
        start_time = time.time()
        results = env.update(large_dataset, "performance_test")
        set_time = time.time() - start_time
        
        # Verify all succeeded
        success_count = sum(1 for success in results.values() if success)
        assert success_count == num_vars, f"Only {success_count}/{num_vars} variables set successfully"
        
        # Performance requirement - should handle 5K vars in under 3 seconds
        assert set_time < 3.0, f"Bulk set operation too slow: {set_time:.2f}s for {num_vars} variables"
        
        # Time bulk retrieval
        start_time = time.time()
        for i in range(num_vars):
            value = env.get(f"VAR_{i:04d}")
            assert value == f"value_{i}", f"Variable VAR_{i:04d} corrupted"
        get_time = time.time() - start_time
        
        # Performance requirement - retrieval should be fast
        assert get_time < 2.0, f"Bulk get operations too slow: {get_time:.2f}s for {num_vars} variables"
        
        # Test get_all performance
        start_time = time.time()
        all_vars = env.get_all()
        get_all_time = time.time() - start_time
        
        assert len(all_vars) >= num_vars, f"get_all() returned insufficient variables"
        assert get_all_time < 1.0, f"get_all() too slow: {get_all_time:.2f}s for {num_vars} variables"
        
        env.reset()
    
    def test_concurrent_performance_under_load(self):
        """Test performance under concurrent load - PRODUCTION SIMULATION."""
        env = get_env()
        env.reset() 
        env.enable_isolation()
        
        operations_completed = {"set": 0, "get": 0, "delete": 0}
        errors = []
        
        def concurrent_worker(worker_id: int):
            """Worker thread performing mixed operations."""
            try:
                for i in range(50):  # 50 operations per worker
                    var_name = f"WORKER_{worker_id}_VAR_{i}"
                    
                    # Set
                    result = env.set(var_name, f"worker_{worker_id}_value_{i}", f"worker_{worker_id}")
                    if result:
                        operations_completed["set"] += 1
                    
                    # Get
                    value = env.get(var_name)
                    if value == f"worker_{worker_id}_value_{i}":
                        operations_completed["get"] += 1
                    
                    # Delete
                    if env.delete(var_name, f"worker_{worker_id}"):
                        operations_completed["delete"] += 1
                        
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Run concurrent workers
        workers = []
        num_workers = 10
        
        start_time = time.time()
        
        for i in range(num_workers):
            worker = threading.Thread(target=concurrent_worker, args=(i,))
            workers.append(worker)
            worker.start()
        
        # Wait for completion
        for worker in workers:
            worker.join(timeout=10.0)
            if worker.is_alive():
                raise AssertionError("Worker thread timed out - possible deadlock")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify no errors
        if errors:
            raise AssertionError(f"Concurrent operation errors: {errors}")
        
        # Verify operations completed
        expected_ops = num_workers * 50
        assert operations_completed["set"] == expected_ops, f"Set operations: {operations_completed['set']}/{expected_ops}"
        assert operations_completed["get"] == expected_ops, f"Get operations: {operations_completed['get']}/{expected_ops}"
        assert operations_completed["delete"] == expected_ops, f"Delete operations: {operations_completed['delete']}/{expected_ops}"
        
        # Performance requirement
        total_operations = sum(operations_completed.values())
        ops_per_second = total_operations / total_time
        assert ops_per_second > 500, f"Performance too low: {ops_per_second:.2f} ops/sec"
        
        env.reset()


class TestIsolatedEnvironmentErrorHandlingComprehensive:
    """Comprehensive error handling tests - FAULT TOLERANCE CRITICAL."""
    
    def test_invalid_input_handling_comprehensive(self):
        """Test handling of all invalid input types."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test various invalid inputs
        invalid_inputs = [
            None,           # None value
            123,           # Integer
            123.45,        # Float
            True,          # Boolean
            False,         # Boolean False
            [],            # List
            {},            # Dict
            set(),         # Set
            object(),      # Generic object
        ]
        
        for i, invalid_input in enumerate(invalid_inputs):
            var_name = f"INVALID_INPUT_{i}"
            
            # Should handle gracefully by converting to string
            result = env.set(var_name, invalid_input, "invalid_input_test")
            assert result is True, f"Failed to handle invalid input {type(invalid_input)}"
            
            # Should retrieve as string representation
            retrieved = env.get(var_name)
            assert isinstance(retrieved, str), f"Invalid input not converted to string: {type(retrieved)}"
            assert retrieved == str(invalid_input), f"String conversion incorrect for {type(invalid_input)}"
        
        env.reset()
    
    def test_extreme_value_handling(self):
        """Test handling of extreme values - EDGE CASE COVERAGE."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test extremely long values
        very_long_value = "x" * 10000  # 10K characters
        env.set("VERY_LONG_VAR", very_long_value, "extreme_test")
        retrieved = env.get("VERY_LONG_VAR")
        assert retrieved == very_long_value, "Very long value corrupted"
        
        # Test empty string
        env.set("EMPTY_VAR", "", "extreme_test")
        assert env.get("EMPTY_VAR") == "", "Empty string not preserved"
        
        # Test whitespace-only (note: control characters like \t, \n, \r are sanitized for security)
        whitespace_value = "   \t\n\r   "
        env.set("WHITESPACE_VAR", whitespace_value, "extreme_test")
        retrieved_whitespace = env.get("WHITESPACE_VAR")
        # Control characters are removed by security sanitization, so check spaces are preserved
        assert "   " in retrieved_whitespace, "Space characters should be preserved"
        assert len(retrieved_whitespace.strip()) == 0, "Should only contain whitespace after sanitization"
        
        # Test special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?~`"
        env.set("SPECIAL_CHARS_VAR", special_chars, "extreme_test")
        assert env.get("SPECIAL_CHARS_VAR") == special_chars, "Special characters corrupted"
        
        # Test Unicode characters
        unicode_value = "Hello 世界 🌍 café naïve résumé"
        env.set("UNICODE_VAR", unicode_value, "extreme_test")
        assert env.get("UNICODE_VAR") == unicode_value, "Unicode characters corrupted"
        
        env.reset()
    
    def test_file_loading_error_scenarios(self):
        """Test all file loading error scenarios - FILE HANDLING ROBUSTNESS."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test non-existent file
        loaded_count, errors = env.load_from_file("/definitely/does/not/exist.env")
        assert loaded_count == 0, "Non-existent file should load 0 variables"
        assert len(errors) > 0, "Non-existent file should produce error"
        assert "not found" in errors[0].lower(), "Error should mention file not found"
        
        # Test permission denied file (simulate)
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            loaded_count, errors = env.load_from_file("fake_file.env")
            assert loaded_count == 0, "Permission denied should load 0 variables"
            assert len(errors) > 0, "Permission denied should produce error"
        
        # Test corrupted file content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, encoding='utf-8') as f:
            # Write corrupted content
            f.write("VALID_VAR=valid_value\n")
            f.write("INVALID_LINE_1\n")           # No equals
            f.write("=NO_KEY_NAME\n")             # No key
            f.write("ANOTHER_VALID=another_value\n")
            f.write("INVALID_LINE_2=value=with=multiple=equals\n")  # Multiple equals (should work)
            corrupted_file = f.name
        
        try:
            loaded_count, errors = env.load_from_file(corrupted_file)
            
            # Should load valid lines
            assert loaded_count >= 3, f"Should load at least valid lines, got {loaded_count}"
            
            # Should report errors for invalid lines
            assert len(errors) >= 2, f"Should report errors for invalid lines, got {len(errors)}"
            
            # Valid variables should be loaded
            assert env.get("VALID_VAR") == "valid_value", "Valid variable not loaded"
            assert env.get("ANOTHER_VALID") == "another_value", "Another valid variable not loaded"
            assert env.get("INVALID_LINE_2") == "value=with=multiple=equals", "Multiple equals not handled"
            
        finally:
            try:
                os.unlink(corrupted_file)
            except (OSError, PermissionError):
                pass
        
        env.reset()
    
    def test_callback_error_resilience(self):
        """Test system resilience to callback failures - CALLBACK SAFETY."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Create callbacks that fail in different ways
        def callback_exception(key, old_val, new_val):
            raise Exception("Callback intentional failure")
        
        def callback_type_error(key, old_val, new_val):
            raise TypeError("Type error in callback")
        
        def callback_runtime_error(key, old_val, new_val):
            raise RuntimeError("Runtime error in callback")
        
        def callback_success(key, old_val, new_val):
            self.callback_success_calls.append((key, old_val, new_val))
        
        # Track successful callback
        self.callback_success_calls = []
        
        # Add all callbacks
        env.add_change_callback(callback_exception)
        env.add_change_callback(callback_type_error)
        env.add_change_callback(callback_runtime_error) 
        env.add_change_callback(callback_success)
        
        # Operations should succeed despite failing callbacks
        result = env.set("CALLBACK_ERROR_TEST", "test_value", "error_test")
        assert result is True, "Variable setting failed due to callback errors"
        
        # Variable should be set correctly
        assert env.get("CALLBACK_ERROR_TEST") == "test_value", "Variable value corrupted by callback errors"
        
        # Successful callback should have been called
        assert len(self.callback_success_calls) == 1, "Successful callback not called"
        assert self.callback_success_calls[0] == ("CALLBACK_ERROR_TEST", None, "test_value"), "Callback parameters incorrect"
        
        # Update should also work
        result = env.set("CALLBACK_ERROR_TEST", "updated_value", "error_test")
        assert result is True, "Variable update failed due to callback errors"
        assert env.get("CALLBACK_ERROR_TEST") == "updated_value", "Variable update corrupted by callback errors"
        
        # Delete should also work
        result = env.delete("CALLBACK_ERROR_TEST", "error_test")
        assert result is True, "Variable deletion failed due to callback errors"
        assert env.get("CALLBACK_ERROR_TEST") is None, "Variable not deleted due to callback errors"
        
        env.reset()


class TestIsolatedEnvironmentSecurityValidation:
    """Security validation tests - SECURITY BUSINESS VALUE."""
    
    def test_sensitive_value_masking_comprehensive(self):
        """Comprehensive test of sensitive value masking patterns."""
        # Test all sensitive patterns from source code
        sensitive_patterns = [
            'password', 'secret', 'key', 'token', 'auth', 'credential',
            'private', 'cert', 'api_key', 'jwt', 'oauth', 'fernet'
        ]
        
        for pattern in sensitive_patterns:
            # Test lowercase
            masked = _mask_sensitive_value(pattern, "sensitive_value_123")
            assert masked == "sen***", f"Lowercase pattern {pattern} not masked correctly"
            
            # Test uppercase
            masked = _mask_sensitive_value(pattern.upper(), "SENSITIVE_VALUE_123")
            assert masked == "SEN***", f"Uppercase pattern {pattern} not masked correctly"
            
            # Test mixed case
            mixed_pattern = pattern.capitalize()
            masked = _mask_sensitive_value(mixed_pattern, "MixedValue123")
            assert masked == "Mix***", f"Mixed case pattern {pattern} not masked correctly"
            
            # Test as part of longer key name
            compound_key = f"APP_{pattern.upper()}_PROD"
            masked = _mask_sensitive_value(compound_key, "compound_sensitive_value")
            assert masked == "com***", f"Compound key {compound_key} not masked correctly"
        
    def test_database_url_credential_protection(self):
        """Test database URL credential protection during sanitization."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test various database URL formats with special characters in passwords
        test_urls = [
            "postgresql://user:p@ssw0rd!@localhost:5432/dbname",
            "postgresql://user:p%40ss%21w0rd@localhost:5432/dbname",  # URL encoded
            "mysql://user:complex$password@host.com:3306/database?ssl=true",
            "clickhouse://user:click@house#pass@clickhouse.example.com:8123/analytics",
            "redis://user:redis$pass!@redis.com:6379/0",
        ]
        
        for i, test_url in enumerate(test_urls):
            var_name = f"DATABASE_URL_{i}"
            env.set(var_name, test_url, "security_test")
            
            retrieved_url = env.get(var_name)
            
            # URL structure should be preserved
            original_parsed = urlparse(test_url)
            retrieved_parsed = urlparse(retrieved_url)
            
            assert original_parsed.scheme == retrieved_parsed.scheme, f"URL scheme corrupted for {test_url}"
            assert original_parsed.hostname == retrieved_parsed.hostname, f"Hostname corrupted for {test_url}"
            assert original_parsed.port == retrieved_parsed.port, f"Port corrupted for {test_url}"
            assert original_parsed.path == retrieved_parsed.path, f"Path corrupted for {test_url}"
            
            # Password should be preserved (even with special chars)
            assert original_parsed.password == retrieved_parsed.password, f"Password corrupted for {test_url}"
            assert original_parsed.username == retrieved_parsed.username, f"Username corrupted for {test_url}"
        
        env.reset()
    
    def test_control_character_sanitization(self):
        """Test removal of control characters for security."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test various control characters
        control_chars = [
            "\x00",  # Null byte
            "\x01",  # Start of heading
            "\x02",  # Start of text
            "\x1f",  # Unit separator
            "\x7f",  # Delete
            "\r",    # Carriage return
            "\n",    # Line feed
            "\t",    # Tab
        ]
        
        for i, control_char in enumerate(control_chars):
            test_value = f"before{control_char}after"
            var_name = f"CONTROL_CHAR_TEST_{i}"
            
            env.set(var_name, test_value, "security_test")
            sanitized_value = env.get(var_name)
            
            # Control character should be removed
            assert control_char not in sanitized_value, f"Control character {repr(control_char)} not removed"
            assert sanitized_value == "beforeafter", f"Text corrupted during sanitization of {repr(control_char)}"
        
        env.reset()


class TestIsolatedEnvironmentValidationComprehensive:
    """Comprehensive validation testing - DATA INTEGRITY CRITICAL."""
    
    def test_validation_result_dataclass_comprehensive(self):
        """Test ValidationResult dataclass with all field combinations."""
        # Test basic creation
        result = ValidationResult(
            is_valid=True,
            errors=["error1", "error2"],
            warnings=["warning1"],
            missing_optional=["optional1", "optional2"]
        )
        
        assert result.is_valid is True
        assert result.errors == ["error1", "error2"]
        assert result.warnings == ["warning1"]
        assert result.missing_optional == ["optional1", "optional2"]
        
        # Test post-init defaults
        assert result.fallback_applied == []
        assert result.suggestions == []
        assert result.missing_optional_by_category == {}
        
        # Test with custom post-init values
        result_custom = ValidationResult(
            is_valid=False,
            errors=["critical_error"],
            warnings=[],
            missing_optional=[],
            fallback_applied=["fallback1"],
            suggestions=["suggestion1", "suggestion2"],
            missing_optional_by_category={"db": ["db_opt1"], "api": ["api_opt1"]}
        )
        
        assert result_custom.fallback_applied == ["fallback1"]
        assert result_custom.suggestions == ["suggestion1", "suggestion2"]
        assert result_custom.missing_optional_by_category == {"db": ["db_opt1"], "api": ["api_opt1"]}
    
    def test_staging_database_validation_comprehensive(self):
        """Comprehensive staging database validation with all edge cases."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test valid staging configuration
        valid_config = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "staging-db.example.com",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "secure_staging_password_with_32_chars",
            "POSTGRES_DB": "netra_staging"
        }
        env.update(valid_config, "validation_test")
        
        result = env.validate_staging_database_credentials()
        assert result["valid"] is True, f"Valid config should pass validation: {result}"
        assert len(result["issues"]) == 0, f"Valid config should have no issues: {result['issues']}"
        
        # Test all invalid scenarios
        invalid_scenarios = [
            # Localhost host (invalid for staging)
            {
                "POSTGRES_HOST": "localhost",
                "expected_issue": "localhost"
            },
            # Invalid user pattern
            {
                "POSTGRES_USER": "user_pr-4",
                "expected_issue": "Invalid POSTGRES_USER"
            },
            # Weak passwords
            {
                "POSTGRES_PASSWORD": "weak",
                "expected_issue": "too short"
            },
            {
                "POSTGRES_PASSWORD": "password",
                "expected_issue": "using insecure default"
            },
            {
                "POSTGRES_PASSWORD": "123456",
                "expected_issue": "using insecure default"
            },
            {
                "POSTGRES_PASSWORD": "admin",
                "expected_issue": "using insecure default"
            },
            {
                "POSTGRES_PASSWORD": "wrong_password",
                "expected_issue": "using insecure default"
            },
            # Numeric-only short password
            {
                "POSTGRES_PASSWORD": "12345678",
                "expected_issue": "needs complexity"
            },
        ]
        
        for scenario in invalid_scenarios:
            # Reset to valid config
            env.update(valid_config, "validation_test")
            
            # Apply invalid change
            for key, value in scenario.items():
                if key != "expected_issue":
                    env.set(key, value, "validation_test")
            
            result = env.validate_staging_database_credentials()
            
            assert result["valid"] is False, f"Invalid scenario should fail validation: {scenario}"
            assert len(result["issues"]) > 0, f"Invalid scenario should have issues: {scenario}"
            
            # Check specific issue is detected
            issues_text = " ".join(result["issues"]).lower()
            expected_issue = scenario["expected_issue"].lower()
            assert expected_issue in issues_text, f"Expected issue '{expected_issue}' not found in: {result['issues']}"
        
        # Test with a non-staging environment (should produce warnings, not errors)
        env.clear()  
        env.set("ENVIRONMENT", "production", "validation_test")  # Not staging
        
        result = env.validate_staging_database_credentials()
        # Should have warnings about not being in staging environment
        assert len(result["warnings"]) > 0, "Non-staging environment should produce warnings"
        assert "staging" in " ".join(result["warnings"]).lower(), "Warning should mention staging"
        
        env.reset()
    
    def test_environment_detection_normalization(self):
        """Test environment name detection and normalization logic."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test all supported environment mappings
        environment_mappings = [
            # Development variations
            ("development", "development"),
            ("dev", "development"),
            ("local", "development"),
            ("", "development"),  # Default when empty
            (None, "development"),  # Default when None
            
            # Test variations
            ("test", "test"),
            ("testing", "test"),
            
            # Staging
            ("staging", "staging"),
            
            # Production variations
            ("production", "production"),
            ("prod", "production"),
            
            # Unknown defaults to development
            ("unknown_env", "development"),
            ("invalid", "development"),
        ]
        
        for env_value, expected_name in environment_mappings:
            if env_value is not None:
                env.set("ENVIRONMENT", env_value, "environment_test")
            else:
                env.delete("ENVIRONMENT", "environment_test")  # Test None case
            
            detected_name = env.get_environment_name()
            assert detected_name == expected_name, f"Environment '{env_value}' should map to '{expected_name}', got '{detected_name}'"
            
            # Test boolean methods
            expected_is_dev = (expected_name == "development")
            expected_is_test = (expected_name == "test")
            expected_is_staging = (expected_name == "staging")
            expected_is_prod = (expected_name == "production")
            
            assert env.is_development() == expected_is_dev, f"is_development() failed for {env_value}"
            assert env.is_test() == expected_is_test, f"is_test() failed for {env_value}"
            assert env.is_staging() == expected_is_staging, f"is_staging() failed for {env_value}"
            assert env.is_production() == expected_is_prod, f"is_production() failed for {env_value}"
        
        env.reset()


class TestIsolatedEnvironmentShellExpansionComprehensive:
    """Comprehensive shell expansion testing - SECURITY AND FUNCTIONALITY."""
    
    def test_shell_expansion_patterns_comprehensive(self):
        """Test all shell expansion patterns and security measures."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # All shell expansion should be disabled during tests
        shell_patterns = [
            "$(echo 'hello')",
            "`echo 'hello'`",
            "${HOME}/path",
            "$(whoami)",
            "`date`",
            "prefix_$(echo 'middle')_suffix",
            "multiple_$(echo 'first')_and_$(echo 'second')",
        ]
        
        for pattern in shell_patterns:
            env.set("SHELL_TEST", pattern, "shell_expansion_test")
            
            # During tests, expansion should be disabled
            result = env.get("SHELL_TEST")
            assert result == pattern, f"Shell expansion should be disabled in tests, but {pattern} was modified to {result}"
        
        env.reset()
    
    def test_shell_expansion_error_conditions(self):
        """Test shell expansion error handling."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Mock subprocess to simulate various error conditions
        with patch('shared.isolated_environment.subprocess.run') as mock_run:
            # Test timeout
            from subprocess import TimeoutExpired
            mock_run.side_effect = TimeoutExpired('test_command', 5)
            
            result = env._expand_shell_commands("test_$(timeout_command)_test")
            # Should return original on timeout
            assert result == "test_$(timeout_command)_test"
        
        with patch('shared.isolated_environment.subprocess.run') as mock_run:
            # Test command failure
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Command not found"
            
            result = env._expand_shell_commands("test_$(invalid_command)_test")
            # Should return original on failure
            assert result == "test_$(invalid_command)_test"
        
        with patch('shared.isolated_environment.subprocess.run') as mock_run:
            # Test general exception
            mock_run.side_effect = Exception("Subprocess error")
            
            result = env._expand_shell_commands("test_$(exception_command)_test")
            # Should return original on exception
            assert result == "test_$(exception_command)_test"
        
        env.reset()
    
    def test_shell_expansion_disable_flags(self):
        """Test shell expansion disable mechanisms."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test with DISABLE_SHELL_EXPANSION flag
        env.set("DISABLE_SHELL_EXPANSION", "true", "test_flag")
        env.set("SHELL_DISABLED_TEST", "$(echo 'should_not_expand')", "test")
        
        result = env.get("SHELL_DISABLED_TEST")
        assert result == "$(echo 'should_not_expand')", "Shell expansion should be disabled by flag"
        
        # Test with flag set to false (would enable expansion in production)
        env.set("DISABLE_SHELL_EXPANSION", "false", "test_flag")
        env.set("SHELL_ENABLED_TEST", "$(echo 'might_expand')", "test")
        
        result = env.get("SHELL_ENABLED_TEST")
        # Still disabled in test context
        assert result == "$(echo 'might_expand')", "Shell expansion should still be disabled in test context"
        
        env.reset()


class TestIsolatedEnvironmentLegacyCompatibility:
    """Test all legacy compatibility functions and classes."""
    
    def test_secret_loader_comprehensive(self):
        """Comprehensive test of SecretLoader legacy compatibility."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test with default env manager
        loader = SecretLoader()
        assert loader.env_manager is not None, "SecretLoader should have default env manager"
        
        # Test with custom env manager
        custom_loader = SecretLoader(env_manager=env)
        assert custom_loader.env_manager is env, "SecretLoader should use custom env manager"
        
        # Test load_secrets method
        result = loader.load_secrets()
        assert result is True, "load_secrets should always return True"
        
        # Test secret setting and getting
        set_result = loader.set_secret("SECRET_LOADER_TEST", "secret_value", "secret_loader_test")
        assert set_result is True, "set_secret should return True on success"
        
        get_result = loader.get_secret("SECRET_LOADER_TEST")
        assert get_result == "secret_value", "get_secret should return correct value"
        
        # Test get_secret with default
        default_result = loader.get_secret("NONEXISTENT_SECRET", "default_secret")
        assert default_result == "default_secret", "get_secret should return default for nonexistent secret"
        
        # Test get_secret without default
        none_result = loader.get_secret("ANOTHER_NONEXISTENT")
        assert none_result is None, "get_secret should return None when no default provided"
        
        env.reset()
    
    def test_environment_validator_comprehensive(self):
        """Comprehensive test of EnvironmentValidator legacy compatibility."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test validator creation with parameters
        validator = EnvironmentValidator(enable_fallbacks=True, development_mode=True)
        assert validator.enable_fallbacks is True, "enable_fallbacks parameter not stored"
        assert validator.development_mode is True, "development_mode parameter not stored"
        assert validator.env is not None, "EnvironmentValidator should have env reference"
        
        # Set up test environment for validation
        test_config = {
            "DATABASE_URL": "postgresql://test:password@localhost:5432/testdb",
            "JWT_SECRET_KEY": "test-jwt-secret-key-with-minimum-32-characters",
            "SECRET_KEY": "test-secret-key-for-application-sessions"
        }
        env.update(test_config, "validator_test")
        
        # Test validate_all
        result = validator.validate_all()
        assert isinstance(result, ValidationResult), "validate_all should return ValidationResult"
        assert result.is_valid is True, "Validation should pass with valid config"
        
        # Test validate_with_fallbacks (alias)
        fallback_result = validator.validate_with_fallbacks()
        assert isinstance(fallback_result, ValidationResult), "validate_with_fallbacks should return ValidationResult"
        
        # Test print_validation_summary (should not raise)
        try:
            validator.print_validation_summary(result)
        except Exception as e:
            pytest.fail(f"print_validation_summary should not raise exceptions: {e}")
        
        # Test get_fix_suggestions
        suggestions = validator.get_fix_suggestions(result)
        assert isinstance(suggestions, list), "get_fix_suggestions should return list"
        
        # Test with failing validation
        env.delete("DATABASE_URL", "validator_test")
        failing_result = validator.validate_all()
        assert failing_result.is_valid is False, "Validation should fail with missing DATABASE_URL"
        
        failing_suggestions = validator.get_fix_suggestions(failing_result)
        assert isinstance(failing_suggestions, list), "get_fix_suggestions should return list for failures"
        assert len(failing_suggestions) > 0, "Should provide suggestions for failures"
        
        env.reset()
    
    def test_convenience_functions_comprehensive(self):
        """Comprehensive test of all convenience functions."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test setenv
        setenv_result = setenv("CONVENIENCE_SETENV", "setenv_value", "convenience_test")
        assert setenv_result is True, "setenv should return True on success"
        assert env.get("CONVENIENCE_SETENV") == "setenv_value", "setenv should set value correctly"
        
        # Test getenv
        getenv_result = getenv("CONVENIENCE_SETENV")
        assert getenv_result == "setenv_value", "getenv should return correct value"
        
        # Test getenv with default
        getenv_default = getenv("NONEXISTENT_CONVENIENCE", "default_value")
        assert getenv_default == "default_value", "getenv should return default for nonexistent variable"
        
        # Test getenv without default
        getenv_none = getenv("ANOTHER_NONEXISTENT")
        assert getenv_none is None, "getenv should return None when no default provided"
        
        # Test delenv
        delenv_result = delenv("CONVENIENCE_SETENV")
        assert delenv_result is True, "delenv should return True on successful deletion"
        assert getenv("CONVENIENCE_SETENV") is None, "Variable should be deleted after delenv"
        
        # Test delenv on nonexistent variable
        delenv_nonexistent = delenv("NEVER_EXISTED")
        assert delenv_nonexistent is False, "delenv should return False for nonexistent variable"
        
        # Test get_subprocess_env convenience function
        env.set("SUBPROCESS_CONVENIENCE", "subprocess_value", "convenience_test")
        subprocess_env = get_subprocess_env({"ADDITIONAL": "additional_value"})
        
        assert isinstance(subprocess_env, dict), "get_subprocess_env should return dict"
        assert "SUBPROCESS_CONVENIENCE" in subprocess_env, "Should include existing variables"
        assert "ADDITIONAL" in subprocess_env, "Should include additional variables"
        assert subprocess_env["SUBPROCESS_CONVENIENCE"] == "subprocess_value", "Should have correct existing value"
        assert subprocess_env["ADDITIONAL"] == "additional_value", "Should have correct additional value"
        
        # Test load_secrets convenience function
        load_secrets_result = load_secrets()
        assert load_secrets_result is True, "load_secrets should always return True for compatibility"
        
        env.reset()
    
    def test_get_environment_manager_legacy(self):
        """Test legacy get_environment_manager function."""
        # Test without isolation_mode parameter
        manager1 = get_environment_manager()
        assert isinstance(manager1, IsolatedEnvironment), "Should return IsolatedEnvironment instance"
        
        # Test with isolation_mode=True
        manager2 = get_environment_manager(isolation_mode=True)
        assert isinstance(manager2, IsolatedEnvironment), "Should return IsolatedEnvironment instance"
        assert manager2.is_isolated() is True, "Should enable isolation when requested"
        
        # Test with isolation_mode=False
        manager3 = get_environment_manager(isolation_mode=False)
        assert isinstance(manager3, IsolatedEnvironment), "Should return IsolatedEnvironment instance"
        assert manager3.is_isolated() is False, "Should disable isolation when requested"
        
        # Test with isolation_mode=None
        manager4 = get_environment_manager(isolation_mode=None)
        assert isinstance(manager4, IsolatedEnvironment), "Should return IsolatedEnvironment instance"
        # Isolation state should be unchanged from previous test
        
        # All should be the same singleton instance
        assert manager1 is manager2 is manager3 is manager4, "Should return same singleton instance"
        
        # Reset for other tests
        manager1.reset()


class TestIsolatedEnvironmentWindowsCompatibility:
    """Test Windows-specific functionality - WINDOWS ENCODING SUPPORT."""
    
    def test_utf8_encoding_support(self):
        """Test UTF-8 encoding support for Windows compatibility."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test various UTF-8 characters that might cause issues on Windows
        utf8_test_cases = [
            ("UTF8_ENGLISH", "Hello World", "Basic English text"),
            ("UTF8_FRENCH", "Café naïve résumé", "French accented characters"),
            ("UTF8_GERMAN", "Größe Straße Mädchen", "German umlauts and eszett"),
            ("UTF8_CHINESE", "你好世界", "Chinese characters"),
            ("UTF8_JAPANESE", "こんにちは世界", "Japanese hiragana"),
            ("UTF8_KOREAN", "안녕하세요 세계", "Korean hangul"),
            ("UTF8_EMOJI", "Hello 🌍 World 🚀", "Emoji characters"),
            ("UTF8_SYMBOLS", "©®™€£¥§", "Various symbols"),
            ("UTF8_MIXED", "Testing 测试 тест テスト 🔥", "Mixed scripts and emoji"),
        ]
        
        for var_name, utf8_value, description in utf8_test_cases:
            # Set UTF-8 value
            result = env.set(var_name, utf8_value, "utf8_test")
            assert result is True, f"Failed to set UTF-8 value: {description}"
            
            # Retrieve and verify
            retrieved = env.get(var_name)
            assert retrieved == utf8_value, f"UTF-8 corruption for {description}: expected '{utf8_value}', got '{retrieved}'"
            
            # Test source tracking with UTF-8
            source = env.get_variable_source(var_name)
            assert source == "utf8_test", f"Source tracking failed for UTF-8 variable: {description}"
        
        env.reset()
    
    def test_windows_path_handling(self):
        """Test Windows path handling in file operations."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test Windows-style paths
        if os.name == 'nt':  # Only on Windows
            windows_paths = [
                r"C:\Program Files\MyApp\config.env",
                r"C:\Users\UserName\Documents\.env",
                r"\\NetworkShare\Config\.secrets",
                r"D:\Development\Project\.env.local",
            ]
            
            for win_path in windows_paths:
                # Test path normalization (even for non-existent files)
                path_obj = Path(win_path)
                
                # Should handle without error
                loaded_count, errors = env.load_from_file(win_path)
                assert loaded_count == 0, f"Non-existent Windows path should load 0 variables"
                assert len(errors) == 1, f"Non-existent Windows path should produce 1 error"
                assert "not found" in errors[0].lower(), f"Error should mention file not found for {win_path}"
        
        env.reset()


class TestIsolatedEnvironmentCoverageCompletion:
    """Tests to ensure 100% code coverage of edge cases and rarely used paths."""
    
    def test_module_level_singleton_consistency(self):
        """Test module-level singleton consistency checking via get_env() function."""
        import shared.isolated_environment as ie_module
        
        # Test singleton consistency checking in get_env() function
        original_module_instance = getattr(ie_module, '_env_instance', None)
        original_class_instance = IsolatedEnvironment._instance
        
        try:
            # Create a fake instance to simulate inconsistency
            fake_instance = object()
            ie_module._env_instance = fake_instance
            
            # Calling get_env() should detect and fix inconsistency
            new_instance = get_env()  # This calls the consistency check in get_env()
            
            # Should have forced consistency
            assert ie_module._env_instance is new_instance, "Module instance should be updated for consistency"
            assert ie_module._env_instance is IsolatedEnvironment._instance, "Module and class instances should be consistent"
            
        finally:
            # Restore original state
            if original_module_instance:
                ie_module._env_instance = original_module_instance
            if original_class_instance:
                IsolatedEnvironment._instance = original_class_instance
    
    def test_test_context_detection_edge_cases(self):
        """Test edge cases in test context detection."""
        env = get_env()
        env.reset()
        
        # Test pytest module detection
        original_modules = dict(sys.modules)
        
        try:
            # Mock pytest module
            mock_pytest = Mock()
            mock_pytest.main = Mock()  # Simulate pytest.main existence
            sys.modules['pytest'] = mock_pytest
            
            # Mock sys._pytest_running
            sys._pytest_running = True
            
            # Should detect as test context
            assert env._is_test_context(), "Should detect pytest with _pytest_running flag"
            
            # Remove _pytest_running flag
            delattr(sys, '_pytest_running')
            
            # Should still detect via PYTEST_CURRENT_TEST
            with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test::example'}):
                assert env._is_test_context(), "Should detect pytest via PYTEST_CURRENT_TEST"
            
        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)
            if hasattr(sys, '_pytest_running'):
                delattr(sys, '_pytest_running')
        
        env.reset()
    
    def test_get_test_environment_defaults_coverage(self):
        """Test get_test_environment_defaults method coverage."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Mock test context to access test defaults
        with patch.object(env, '_is_test_context', return_value=True):
            test_defaults = env._get_test_environment_defaults()
            
            # Verify all expected default categories
            assert "GOOGLE_OAUTH_CLIENT_ID_TEST" in test_defaults, "OAuth test credentials missing"
            assert "GOOGLE_OAUTH_CLIENT_SECRET_TEST" in test_defaults, "OAuth test credentials missing"
            assert "ENVIRONMENT" in test_defaults, "Environment default missing"
            assert test_defaults["ENVIRONMENT"] == "test", "Environment should default to test"
            
            # Verify JWT/security defaults
            jwt_key = test_defaults.get("JWT_SECRET_KEY", "")
            assert len(jwt_key) >= 32, "JWT secret key should be at least 32 characters"
            
            # Verify database defaults
            assert "POSTGRES_HOST" in test_defaults, "Database defaults missing"
            assert "REDIS_HOST" in test_defaults, "Redis defaults missing"
            
            # Test accessing defaults via get() in test context
            env.clear()  # Clear all variables
            
            oauth_client_id = env.get("GOOGLE_OAUTH_CLIENT_ID_TEST")
            assert oauth_client_id is not None, "Should return test default for OAuth client ID"
            assert oauth_client_id == test_defaults["GOOGLE_OAUTH_CLIENT_ID_TEST"], "Test default value mismatch"
        
        env.reset()
    
    def test_auto_load_env_file_scenarios(self):
        """Test auto-load scenarios for coverage completion."""
        env = get_env()
        env.reset()
        
        # Test auto-load disabled in pytest context
        with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test::example'}):
            # Create temp .env file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, encoding='utf-8') as f:
                f.write("AUTO_LOAD_PYTEST_TEST=should_not_load\n")
                env_file = f.name
            
            try:
                # Should not auto-load during pytest
                env._auto_load_env_file()
                assert env.get("AUTO_LOAD_PYTEST_TEST") is None, "Should not auto-load during pytest"
                
            finally:
                try:
                    os.unlink(env_file)
                except (OSError, PermissionError):
                    pass
        
        # Test .secrets file fallback (mocking out pytest check)
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                
                # Create .secrets file (no .env file)
                secrets_file = Path(temp_dir) / ".secrets"
                with open(secrets_file, 'w', encoding='utf-8') as f:
                    f.write("SECRETS_FILE_TEST=secrets_value\n")
                
                # Patch out pytest detection to allow loading
                with patch('sys.modules', {k: v for k, v in sys.modules.items() if k != 'pytest'}):
                    with patch.dict(os.environ, {}, clear=False):
                        # Remove PYTEST_CURRENT_TEST if present
                        if 'PYTEST_CURRENT_TEST' in os.environ:
                            del os.environ['PYTEST_CURRENT_TEST']
                        # Should load .secrets file
                        env._auto_load_env_file()
                        assert env.get("SECRETS_FILE_TEST") == "secrets_value", ".secrets file not loaded"
                
            finally:
                os.chdir(original_cwd)
        
        env.reset()
    
    def test_unset_variable_handling_comprehensive(self):
        """Test explicit unset variable handling (__UNSET__ marker)."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Set a variable
        env.set("UNSET_MARKER_TEST", "original_value", "test")
        assert env.get("UNSET_MARKER_TEST") == "original_value", "Variable not set initially"
        assert env.exists("UNSET_MARKER_TEST"), "Variable should exist initially"
        
        # Delete it (marks as __UNSET__)
        result = env.delete("UNSET_MARKER_TEST", "test")
        assert result is True, "Delete should succeed"
        
        # Variable should not exist
        assert not env.exists("UNSET_MARKER_TEST"), "Variable should not exist after delete"
        assert env.get("UNSET_MARKER_TEST") is None, "Should return None for unset variable"
        assert env.get("UNSET_MARKER_TEST", "default") == "default", "Should return default for unset variable"
        
        # Should not appear in get_all()
        all_vars = env.get_all()
        assert "UNSET_MARKER_TEST" not in all_vars, "Unset variable should not appear in get_all()"
        
        # Should not appear in get_all_with_prefix()
        prefixed_vars = env.get_all_with_prefix("UNSET_")
        assert "UNSET_MARKER_TEST" not in prefixed_vars, "Unset variable should not appear in get_all_with_prefix()"
        
        env.reset()
    
    def test_sanitization_edge_cases(self):
        """Test edge cases in value sanitization."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Test sanitization of None input
        result = env._sanitize_value(None)
        assert result == "None", "None should be converted to string 'None'"
        
        # Test sanitization of non-string input
        result = env._sanitize_value(123)
        assert result == "123", "Integer should be converted to string"
        
        # Test empty string
        result = env._sanitize_value("")
        assert result == "", "Empty string should be preserved"
        
        # Test password sanitization preserving special chars
        password_with_special = "pass@word!#$%^&*()"
        result = env._sanitize_password_preserving_special_chars(password_with_special)
        assert result == password_with_special, "Special characters in password should be preserved"
        
        # Test password with control characters
        password_with_control = "pass\x00word\x1f"
        result = env._sanitize_password_preserving_special_chars(password_with_control)
        assert result == "password", "Control characters should be removed from password"
        
        env.reset()
    
    def test_disabled_isolation_clear_error(self):
        """Test that clear() raises error when isolation is disabled."""
        env = get_env()
        env.reset()
        
        # Ensure isolation is disabled
        env.disable_isolation()
        assert not env.is_isolated(), "Isolation should be disabled"
        
        # clear() should raise RuntimeError
        with pytest.raises(RuntimeError, match="Cannot clear environment variables outside isolation mode"):
            env.clear()
    
    def test_reset_to_original_without_backup(self):
        """Test reset_to_original when no original state was saved."""
        env = get_env()
        env.reset()
        
        # Clear any saved state
        env._original_state = None
        env._original_environ_backup = {}
        
        # Should handle gracefully when no original state exists
        try:
            env.reset_to_original()  # Should not raise exception
        except Exception as e:
            pytest.fail(f"reset_to_original() should handle missing original state gracefully: {e}")


# Integration with STANDARD_TEST_CONFIG
class TestStandardTestConfigIntegration:
    """Test integration with SSOT test framework configuration."""
    
    def test_standard_test_config_compatibility(self):
        """Test compatibility with STANDARD_TEST_CONFIG from test framework."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Load standard test configuration
        results = env.update(STANDARD_TEST_CONFIG, source="standard_test_config")
        
        # All standard config should be set successfully
        failed_vars = [var for var, success in results.items() if not success]
        assert len(failed_vars) == 0, f"Failed to set standard test config variables: {failed_vars}"
        
        # Verify key test variables are properly configured
        assert env.get("TESTING") == "true", "TESTING flag not set correctly"
        assert env.get("ENVIRONMENT") == "test", "ENVIRONMENT not set to test"
        assert env.get("DATABASE_URL") is not None, "DATABASE_URL not configured"
        assert env.get("JWT_SECRET_KEY") is not None, "JWT_SECRET_KEY not configured"
        
        # Verify database URL format
        db_url = env.get("DATABASE_URL")
        assert db_url.startswith("postgresql://"), "Database URL should be PostgreSQL format"
        
        # Verify JWT secret key length
        jwt_key = env.get("JWT_SECRET_KEY")
        assert len(jwt_key) >= 32, "JWT secret key should be at least 32 characters"
        
        # Test validation passes with standard config
        result = env.validate_all()
        assert result.is_valid, f"Standard test config should pass validation: {result.errors}"
        
        env.reset()


# Final comprehensive validation
class TestComprehensiveFinalValidation:
    """Final comprehensive validation of all functionality."""
    
    def test_complete_business_workflow_simulation(self):
        """Simulate complete business workflow using IsolatedEnvironment."""
        env = get_env()
        env.reset()
        env.enable_isolation()
        
        # Simulate service startup configuration
        startup_config = {
            "SERVICE_NAME": "netra_backend",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "postgresql://test:test@localhost:5434/test_db",
            "REDIS_URL": "redis://localhost:6381/0",
            "JWT_SECRET_KEY": "test-jwt-secret-key-for-comprehensive-testing-32-chars",
            "ANTHROPIC_API_KEY": "sk-ant-test-key-for-comprehensive-validation",
        }
        
        # Load startup configuration
        results = env.update(startup_config, source="service_startup")
        assert all(results.values()), "All startup configuration should be loaded successfully"
        
        # Simulate runtime configuration changes
        runtime_changes = {
            "LOG_LEVEL": "INFO",  # Change log level
            "WORKER_PROCESSES": "4",  # Add new config
            "CACHE_TTL": "3600",  # Add cache config
        }
        
        for key, value in runtime_changes.items():
            result = env.set(key, value, source="runtime_config")
            assert result is True, f"Runtime configuration change failed for {key}"
        
        # Simulate user-specific context
        user_context = {
            "USER_ID": "test_user_123",
            "SESSION_ID": "session_abc456",
            "API_QUOTA_REMAINING": "950",
        }
        
        for key, value in user_context.items():
            env.set(key, value, source="user_context")
        
        # Verify complete configuration state
        all_vars = env.get_all()
        
        # Should have all configuration categories
        expected_vars = set(startup_config.keys()) | set(runtime_changes.keys()) | set(user_context.keys())
        actual_vars = set(all_vars.keys())
        missing_vars = expected_vars - actual_vars
        assert len(missing_vars) == 0, f"Missing expected variables: {missing_vars}"
        
        # Verify source tracking for debugging
        # Note: Variables that were overridden will have their new source
        for key in startup_config.keys():
            source = env.get_variable_source(key)
            if key in runtime_changes:
                # This variable was overridden by runtime config
                assert source == "runtime_config", f"Variable {key} should have runtime_config source after override"
            else:
                # This variable should retain its original source
                assert source == "service_startup", f"Variable {key} should have service_startup source"
        
        runtime_sources = [env.get_variable_source(key) for key in runtime_changes.keys()]
        assert all(source == "runtime_config" for source in runtime_sources), "Runtime config source tracking failed"
        
        user_sources = [env.get_variable_source(key) for key in user_context.keys()]
        assert all(source == "user_context" for source in user_sources), "User context source tracking failed"
        
        # Simulate subprocess environment for external tool
        subprocess_env = env.get_subprocess_env({"EXTERNAL_TOOL_CONFIG": "enabled"})
        
        # Should include all environment variables plus additional
        assert "SERVICE_NAME" in subprocess_env, "Subprocess env missing service config"
        assert "USER_ID" in subprocess_env, "Subprocess env missing user context"
        assert "EXTERNAL_TOOL_CONFIG" in subprocess_env, "Subprocess env missing additional config"
        
        # Verify security - sensitive values should be masked in debug info
        debug_info = env.get_debug_info()
        assert "tracked_sources" in debug_info, "Debug info should include source tracking"
        assert debug_info["isolated_vars_count"] > 0, "Should track number of variables"
        
        # Simulate service shutdown cleanup
        protected_vars = ["SERVICE_NAME", "ENVIRONMENT"]
        for var in protected_vars:
            env.protect(var)
        
        # Try to modify protected variable (should fail)
        result = env.set("SERVICE_NAME", "modified", "shutdown", force=False)
        assert result is False, "Protected variable should not be modifiable"
        
        # Force modification should work
        result = env.set("SERVICE_NAME", "modified", "shutdown", force=True)
        assert result is True, "Force modification should work on protected variable"
        
        # Final validation
        final_validation = env.validate_all()
        assert final_validation.is_valid, f"Final validation should pass: {final_validation.errors}"
        
        env.reset()


if __name__ == "__main__":
    # Allow running tests directly for debugging
    pytest.main([__file__, "-v", "--tb=short", "-x"])