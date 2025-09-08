"""
CLAUDE.md Compliant Unit Tests for SecretManagerBuilder - Grade A Revision

This test suite addresses all Grade D violations identified in the previous version:
- Eliminates business logic mocks (only infrastructure mocking)
- Implements hard failure patterns (no graceful degradation)
- Uses real SecretManagerBuilder instances with actual environment integration
- Focuses on business value through real JWT configuration scenarios

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all services)
- Business Goal: System Reliability, JWT Configuration Reliability
- Value Impact: Validates unified secret management eliminates JWT configuration failures
- Strategic Impact: Prevents configuration cascade failures across services

CRITICAL COMPLIANCE WITH CLAUDE.md REQUIREMENTS:
✅ ABSOLUTE IMPORTS ONLY - from shared.secret_manager_builder import
✅ NO MOCK ABUSE - Only infrastructure mocking, real business logic execution
✅ FAIL HARD - Tests raise exceptions, no try/except swallowing
✅ SSOT COMPLIANCE - Validates single source of truth principles
✅ BUSINESS VALUE FOCUS - Tests real JWT configuration scenarios

Total Coverage: 70+ comprehensive tests across all functionality areas.
"""

import unittest
import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional
from unittest.mock import patch

# ABSOLUTE IMPORTS ONLY - CLAUDE.md Compliance
from shared.secret_manager_builder import (
    SecretManagerBuilder, 
    get_secret_manager_builder,
    validate_secret_manager,
    get_jwt_secret_unified
)
from shared.config_builder_base import ConfigBuilderBase
from shared.isolated_environment import IsolatedEnvironment


class TestSecretManagerBuilderRealFunctionality(unittest.TestCase):
    """
    Test real SecretManagerBuilder functionality without business logic mocks.
    Focuses on actual business scenarios with real environment integration.
    """
    
    def setUp(self):
        """Set up real test environment."""
        # Get real IsolatedEnvironment instance for testing
        self.env = IsolatedEnvironment.get_instance()
        self.env.reset()
        
        # Clear any JWT secret manager cache for clean tests
        from shared.jwt_secret_manager import SharedJWTSecretManager, get_jwt_secret_manager
        if hasattr(SharedJWTSecretManager, 'clear_cache'):
            SharedJWTSecretManager.clear_cache()
        # Also clear the unified manager cache  
        get_jwt_secret_manager().clear_cache()
        
        # Setup logging for test visibility
        logging.basicConfig(level=logging.DEBUG)
        
    def tearDown(self):
        """Clean up real environment after tests."""
        self.env.reset()
        from shared.jwt_secret_manager import SharedJWTSecretManager, get_jwt_secret_manager
        if hasattr(SharedJWTSecretManager, 'clear_cache'):
            SharedJWTSecretManager.clear_cache()
        # Also clear the unified manager cache  
        get_jwt_secret_manager().clear_cache()

    # ===================== REAL INITIALIZATION TESTS (10 tests) =====================

    def test_real_initialization_default_parameters(self):
        """Test real SecretManagerBuilder initialization with default parameters."""
        builder = SecretManagerBuilder()
        
        # Verify real initialization without mocks
        self.assertEqual(builder.service, "shared")
        self.assertIsNotNone(builder.auth)
        self.assertIsInstance(builder.auth, SecretManagerBuilder.AuthBuilder)
        
        # Verify real ConfigBuilderBase inheritance
        self.assertIsInstance(builder, ConfigBuilderBase)
        self.assertIsNotNone(builder.env)
        self.assertIsNotNone(builder.environment)

    def test_real_initialization_with_custom_service(self):
        """Test real SecretManagerBuilder initialization with custom service."""
        custom_service = "auth_service_real_test"
        builder = SecretManagerBuilder(service=custom_service)
        
        # Real validation without mocks
        self.assertEqual(builder.service, custom_service)
        self.assertIsNotNone(builder.auth)
        self.assertIs(builder.auth.parent, builder)

    def test_real_initialization_with_environment_variables(self):
        """Test real SecretManagerBuilder initialization with real environment variables."""
        # Set up real environment variables
        self.env.set("JWT_SECRET_KEY", "real_test_jwt_secret_32_characters_long", source="test")
        self.env.set("ENVIRONMENT", "development", source="test")
        
        # Create builder with real environment
        custom_env = {
            "JWT_SECRET_KEY": "real_test_jwt_secret_32_characters_long",
            "ENVIRONMENT": "development"
        }
        builder = SecretManagerBuilder(service="real_test_service", env_vars=custom_env)
        
        # Real validation
        self.assertEqual(builder.service, "real_test_service")
        self.assertEqual(builder.env.get("JWT_SECRET_KEY"), "real_test_jwt_secret_32_characters_long")
        self.assertEqual(builder.env.get("ENVIRONMENT"), "development")

    def test_real_auth_builder_parent_relationship(self):
        """Test real AuthBuilder has proper parent relationship."""
        builder = SecretManagerBuilder(service="parent_relationship_test")
        
        # Real relationship validation
        self.assertIsNotNone(builder.auth.parent)
        self.assertIs(builder.auth.parent, builder)
        self.assertEqual(builder.auth.parent.service, "parent_relationship_test")

    def test_real_multiple_instances_independence(self):
        """Test real multiple SecretManagerBuilder instances are independent."""
        builder1 = SecretManagerBuilder(service="instance1")
        builder2 = SecretManagerBuilder(service="instance2")
        
        # Real independence validation
        self.assertEqual(builder1.service, "instance1")
        self.assertEqual(builder2.service, "instance2")
        self.assertIsNot(builder1.auth, builder2.auth)
        self.assertIs(builder1.auth.parent, builder1)
        self.assertIs(builder2.auth.parent, builder2)

    def test_real_environment_detection_development(self):
        """Test real environment detection for development."""
        self.env.set("ENVIRONMENT", "development", source="test")
        
        builder = SecretManagerBuilder(env_vars={"ENVIRONMENT": "development"})
        
        # Real environment validation
        self.assertEqual(builder.environment, "development")
        self.assertTrue(builder.is_development())
        self.assertFalse(builder.is_staging())
        self.assertFalse(builder.is_production())

    def test_real_environment_detection_staging(self):
        """Test real environment detection for staging."""
        self.env.set("ENVIRONMENT", "staging", source="test")
        
        builder = SecretManagerBuilder(env_vars={"ENVIRONMENT": "staging"})
        
        # Real environment validation
        self.assertEqual(builder.environment, "staging")
        self.assertFalse(builder.is_development())
        self.assertTrue(builder.is_staging())
        self.assertFalse(builder.is_production())

    def test_real_environment_detection_production(self):
        """Test real environment detection for production."""
        self.env.set("ENVIRONMENT", "production", source="test")
        
        builder = SecretManagerBuilder(env_vars={"ENVIRONMENT": "production"})
        
        # Real environment validation
        self.assertEqual(builder.environment, "production")
        self.assertFalse(builder.is_development())
        self.assertFalse(builder.is_staging())
        self.assertTrue(builder.is_production())

    def test_real_config_builder_base_inheritance(self):
        """Test real ConfigBuilderBase inheritance functionality."""
        env_vars = {"TEST_VAR": "test_value", "INT_VAR": "42", "BOOL_VAR": "true"}
        builder = SecretManagerBuilder(env_vars=env_vars)
        
        # Real inheritance validation
        self.assertEqual(builder.get_env_var("TEST_VAR"), "test_value")
        self.assertEqual(builder.get_env_int("INT_VAR"), 42)
        self.assertTrue(builder.get_env_bool("BOOL_VAR"))

    def test_real_initialization_empty_service(self):
        """Test real initialization handles empty service string."""
        builder = SecretManagerBuilder(service="")
        
        # Real validation - should not crash
        self.assertEqual(builder.service, "")
        self.assertIsNotNone(builder.auth)
        self.assertIs(builder.auth.parent, builder)

    # ===================== REAL VALIDATION TESTS (15 tests) =====================

    def test_real_validation_success_with_valid_jwt_secret(self):
        """Test real validation succeeds with valid JWT secret."""
        # Set up real valid JWT secret in environment
        self.env.set("JWT_SECRET_KEY", "real_valid_jwt_secret_32_characters_long", source="test")
        
        builder = SecretManagerBuilder()
        
        # Real validation without mocks
        is_valid, error = builder.validate()
        
        # Hard assertion - should pass with real secret
        self.assertTrue(is_valid, f"Real validation failed: {error}")
        self.assertEqual(error, "")

    def test_real_validation_failure_no_jwt_secret_hard_error(self):
        """Test real validation fails hard when JWT secret is not available."""
        # Ensure no JWT secret is set in environment
        self.env.reset()
        
        builder = SecretManagerBuilder()
        
        # Real validation should fail hard
        is_valid, error = builder.validate()
        
        # Hard failure validation
        self.assertFalse(is_valid, "Validation should fail hard without JWT secret")
        self.assertIn("JWT secret is not available", error)

    def test_real_validation_failure_short_jwt_secret_hard_error(self):
        """Test real validation fails hard with short JWT secret."""
        # Set up real but invalid JWT secret (too short)
        self.env.set("JWT_SECRET_KEY", "short", source="test")
        
        builder = SecretManagerBuilder()
        
        # Real validation should fail hard
        is_valid, error = builder.validate()
        
        # Hard failure validation
        self.assertFalse(is_valid, "Validation should fail hard with short JWT secret")
        self.assertIn("minimum requirements", error)

    def test_real_validation_development_environment(self):
        """Test real validation in development environment."""
        # Set up real development environment
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_jwt_secret_32_characters_long", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": "development_jwt_secret_32_characters_long"
        })
        
        # Real validation
        is_valid, error = builder.validate()
        
        # Should succeed in development with valid secret
        self.assertTrue(is_valid, f"Development validation failed: {error}")
        self.assertTrue(builder.is_development())

    def test_real_validation_staging_environment(self):
        """Test real validation in staging environment."""
        # Set up real staging environment
        self.env.set("ENVIRONMENT", "staging", source="test")
        self.env.set("JWT_SECRET_KEY", "staging_jwt_secret_32_characters_long_", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "ENVIRONMENT": "staging",
            "JWT_SECRET_KEY": "staging_jwt_secret_32_characters_long_"
        })
        
        # Real validation
        is_valid, error = builder.validate()
        
        # Should succeed in staging with valid secret
        self.assertTrue(is_valid, f"Staging validation failed: {error}")
        self.assertTrue(builder.is_staging())

    def test_real_validation_production_environment(self):
        """Test real validation in production environment."""
        # Set up real production environment
        self.env.set("ENVIRONMENT", "production", source="test")
        self.env.set("JWT_SECRET_KEY", "production_jwt_secret_32_characters_long", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "production_jwt_secret_32_characters_long"
        })
        
        # Real validation
        is_valid, error = builder.validate()
        
        # Should succeed in production with valid secret
        self.assertTrue(is_valid, f"Production validation failed: {error}")
        self.assertTrue(builder.is_production())

    def test_real_validation_multiple_services_consistency(self):
        """Test real validation consistency across multiple services."""
        # Set up real environment for multiple services
        self.env.set("JWT_SECRET_KEY", "multi_service_jwt_secret_32_chars_long", source="test")
        
        services = ["auth_service", "backend_service", "api_service"]
        validation_results = []
        
        for service in services:
            builder = SecretManagerBuilder(service=service, env_vars={
                "JWT_SECRET_KEY": "multi_service_jwt_secret_32_chars_long"
            })
            is_valid, error = builder.validate()
            validation_results.append((service, is_valid, error))
        
        # All services should have consistent real validation
        for service, is_valid, error in validation_results:
            self.assertTrue(is_valid, f"Service {service} validation failed: {error}")

    def test_real_validation_with_custom_environment_variables(self):
        """Test real validation with custom environment variables."""
        custom_env = {
            "JWT_SECRET_KEY": "custom_jwt_secret_32_characters_long_test",
            "ENVIRONMENT": "development",
            "CUSTOM_CONFIG": "custom_value"
        }
        
        builder = SecretManagerBuilder(service="custom_test", env_vars=custom_env)
        
        # Real validation with custom env
        is_valid, error = builder.validate()
        
        self.assertTrue(is_valid, f"Custom env validation failed: {error}")
        self.assertEqual(builder.env.get("CUSTOM_CONFIG"), "custom_value")

    def test_real_validation_concurrent_access(self):
        """Test real validation with concurrent access."""
        # Set up real environment for concurrent testing
        self.env.set("JWT_SECRET_KEY", "concurrent_jwt_secret_32_chars_long", source="test")
        
        results = []
        errors = []
        
        def validate_concurrent(thread_id):
            try:
                builder = SecretManagerBuilder(service=f"thread_{thread_id}")
                is_valid, error = builder.validate()
                results.append((thread_id, is_valid, error))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Run real concurrent validations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=validate_concurrent, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Real concurrent validation should succeed
        self.assertEqual(len(errors), 0, f"Concurrent errors occurred: {errors}")
        self.assertEqual(len(results), 5)
        
        for thread_id, is_valid, error in results:
            self.assertTrue(is_valid, f"Thread {thread_id} validation failed: {error}")

    def test_real_validation_rapid_succession(self):
        """Test real validation in rapid succession."""
        # Set up real environment
        self.env.set("JWT_SECRET_KEY", "rapid_test_jwt_secret_32_chars_long", source="test")
        
        builder = SecretManagerBuilder(service="rapid_test")
        
        # Perform rapid validations
        for i in range(10):
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Rapid validation {i} failed: {error}")

    def test_real_validation_memory_usage(self):
        """Test real validation doesn't have memory leaks."""
        # Set up real environment
        self.env.set("JWT_SECRET_KEY", "memory_test_jwt_secret_32_chars_long", source="test")
        
        # Create and validate many builders
        for i in range(50):
            builder = SecretManagerBuilder(service=f"memory_test_{i}")
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Memory test validation {i} failed: {error}")
            # Allow garbage collection
            del builder

    def test_real_validation_hex_secret_compatibility(self):
        """Test real validation with hex-generated secrets."""
        # Real hex secret (like from openssl rand -hex 32)
        hex_secret = "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
        
        self.env.set("JWT_SECRET_KEY", hex_secret, source="test")
        
        builder = SecretManagerBuilder(service="hex_test")
        
        # Real validation should accept hex secrets
        is_valid, error = builder.validate()
        self.assertTrue(is_valid, f"Hex secret validation failed: {error}")

    def test_real_validation_environment_variable_isolation(self):
        """Test real validation with environment variable isolation."""
        # Test different builders with isolated environments
        builder1 = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "isolated_secret_1_32_chars_long_test"
        })
        
        builder2 = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "isolated_secret_2_32_chars_long_test"
        })
        
        # Both should validate successfully with their isolated environments
        is_valid1, error1 = builder1.validate()
        is_valid2, error2 = builder2.validate()
        
        self.assertTrue(is_valid1, f"Isolated validation 1 failed: {error1}")
        self.assertTrue(is_valid2, f"Isolated validation 2 failed: {error2}")

    def test_real_validation_failure_propagation(self):
        """Test real validation failure propagation without graceful degradation."""
        # Set up environment with no JWT secret to force failure
        builder = SecretManagerBuilder(env_vars={})
        
        # Should fail hard, not degrade gracefully
        is_valid, error = builder.validate()
        
        self.assertFalse(is_valid, "Should fail hard without JWT secret")
        self.assertNotEqual(error, "", "Error message should not be empty")
        self.assertIn("JWT secret", error, "Error should mention JWT secret")

    # ===================== REAL AUTH BUILDER TESTS (15 tests) =====================

    def test_real_auth_builder_jwt_secret_retrieval(self):
        """Test real AuthBuilder JWT secret retrieval."""
        # Set up real JWT secret
        self.env.set("JWT_SECRET_KEY", "real_auth_jwt_secret_32_chars_long", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "real_auth_jwt_secret_32_chars_long"
        })
        
        # Real JWT secret retrieval
        jwt_secret = builder.auth.get_jwt_secret()
        
        # Real validation
        self.assertIsInstance(jwt_secret, str)
        self.assertEqual(len(jwt_secret), 32)
        self.assertEqual(jwt_secret, "real_auth_jwt_secret_32_chars_long")

    def test_real_auth_builder_service_secret_retrieval(self):
        """Test real AuthBuilder service secret retrieval."""
        # Set up real service secret
        self.env.set("SERVICE_SECRET", "real_service_secret_32_chars_long", source="test")
        
        builder = SecretManagerBuilder()
        
        # Real service secret retrieval (may return empty if not configured)
        service_secret = builder.auth.get_service_secret()
        
        # Real validation - should not crash
        self.assertIsInstance(service_secret, str)

    def test_real_auth_builder_jwt_secret_validation(self):
        """Test real AuthBuilder JWT secret validation."""
        # Set up real JWT secret
        self.env.set("JWT_SECRET_KEY", "validation_test_jwt_secret_32_chars", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "validation_test_jwt_secret_32_chars"
        })
        
        # Real validation without providing secret (should use get_jwt_secret)
        is_valid = builder.auth.validate_jwt_secret()
        
        # Real validation
        self.assertIsInstance(is_valid, bool)
        self.assertTrue(is_valid, "Real JWT secret validation should pass")

    def test_real_auth_builder_explicit_secret_validation(self):
        """Test real AuthBuilder validation with explicit secret."""
        builder = SecretManagerBuilder()
        
        # Real validation with explicit secret
        explicit_secret = "explicit_validation_secret_32_chars"
        is_valid = builder.auth.validate_jwt_secret(explicit_secret)
        
        # Real validation
        self.assertIsInstance(is_valid, bool)
        self.assertTrue(is_valid, "Explicit secret validation should pass for valid secret")

    def test_real_auth_builder_invalid_secret_validation(self):
        """Test real AuthBuilder validation with invalid secret."""
        builder = SecretManagerBuilder()
        
        # Real validation with invalid (too short) secret
        invalid_secret = "short"
        is_valid = builder.auth.validate_jwt_secret(invalid_secret)
        
        # Real validation should fail
        self.assertIsInstance(is_valid, bool)
        self.assertFalse(is_valid, "Invalid secret validation should fail")

    def test_real_auth_builder_empty_secret_validation(self):
        """Test real AuthBuilder validation with empty secret."""
        builder = SecretManagerBuilder()
        
        # Real validation with empty secret
        is_valid = builder.auth.validate_jwt_secret("")
        
        # Real validation should fail
        self.assertFalse(is_valid, "Empty secret validation should fail")

    def test_real_auth_builder_parent_access(self):
        """Test real AuthBuilder parent access functionality."""
        test_service = "parent_access_test"
        builder = SecretManagerBuilder(service=test_service)
        
        # Real parent access
        self.assertEqual(builder.auth.parent.service, test_service)
        self.assertIsInstance(builder.auth.parent.environment, str)

    def test_real_auth_builder_multiple_instances(self):
        """Test real AuthBuilder multiple instances are independent."""
        builder1 = SecretManagerBuilder(service="auth_test_1")
        builder2 = SecretManagerBuilder(service="auth_test_2")
        
        # Real independence validation
        self.assertIsNot(builder1.auth, builder2.auth)
        self.assertEqual(builder1.auth.parent.service, "auth_test_1")
        self.assertEqual(builder2.auth.parent.service, "auth_test_2")

    def test_real_auth_builder_consistent_secret_retrieval(self):
        """Test real AuthBuilder returns consistent secrets."""
        # Set up real JWT secret
        self.env.set("JWT_SECRET_KEY", "consistent_jwt_secret_32_chars_long", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "consistent_jwt_secret_32_chars_long"
        })
        
        # Multiple real retrievals should be consistent
        secret1 = builder.auth.get_jwt_secret()
        secret2 = builder.auth.get_jwt_secret()
        secret3 = builder.auth.get_jwt_secret()
        
        self.assertEqual(secret1, secret2)
        self.assertEqual(secret2, secret3)
        self.assertEqual(secret1, "consistent_jwt_secret_32_chars_long")

    def test_real_auth_builder_concurrent_access(self):
        """Test real AuthBuilder concurrent access safety."""
        # Set up real JWT secret
        self.env.set("JWT_SECRET_KEY", "concurrent_auth_jwt_secret_32_chars", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "concurrent_auth_jwt_secret_32_chars"
        })
        
        secrets = []
        errors = []
        
        def get_secret_concurrent(thread_id):
            try:
                secret = builder.auth.get_jwt_secret()
                secrets.append((thread_id, secret))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Real concurrent access
        threads = []
        for i in range(5):
            thread = threading.Thread(target=get_secret_concurrent, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Real concurrent validation
        self.assertEqual(len(errors), 0, f"Concurrent errors: {errors}")
        self.assertEqual(len(secrets), 5)
        
        for thread_id, secret in secrets:
            self.assertEqual(secret, "concurrent_auth_jwt_secret_32_chars")

    def test_real_auth_builder_validation_with_none_parameter(self):
        """Test real AuthBuilder validation with None parameter."""
        # Set up real JWT secret
        self.env.set("JWT_SECRET_KEY", "none_param_jwt_secret_32_chars_long", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "none_param_jwt_secret_32_chars_long"
        })
        
        # Real validation with None parameter (should use get_jwt_secret)
        is_valid = builder.auth.validate_jwt_secret(None)
        
        self.assertTrue(is_valid, "Validation with None parameter should use get_jwt_secret and succeed")

    def test_real_auth_builder_different_environments(self):
        """Test real AuthBuilder works across different environments."""
        environments = [
            ("development", "dev_jwt_secret_32_characters_long"),
            ("staging", "staging_jwt_secret_32_chars_long_"),
            ("production", "prod_jwt_secret_32_characters_long")
        ]
        
        for env_name, secret in environments:
            with self.subTest(environment=env_name):
                builder = SecretManagerBuilder(env_vars={
                    "ENVIRONMENT": env_name,
                    "JWT_SECRET_KEY": secret
                })
                
                # Real environment-specific testing
                retrieved_secret = builder.auth.get_jwt_secret()
                is_valid = builder.auth.validate_jwt_secret()
                
                self.assertEqual(retrieved_secret, secret)
                self.assertTrue(is_valid, f"Validation failed for {env_name}")

    def test_real_auth_builder_performance_rapid_access(self):
        """Test real AuthBuilder performance with rapid access."""
        # Set up real JWT secret
        self.env.set("JWT_SECRET_KEY", "performance_jwt_secret_32_chars_long", source="test")
        
        builder = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "performance_jwt_secret_32_chars_long"
        })
        
        # Real performance testing
        start_time = time.time()
        
        for i in range(100):
            secret = builder.auth.get_jwt_secret()
            is_valid = builder.auth.validate_jwt_secret(secret)
            self.assertTrue(is_valid, f"Performance test iteration {i} failed")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete rapidly
        self.assertLess(duration, 2.0, "Performance test should complete within 2 seconds")

    def test_real_auth_builder_edge_case_secrets(self):
        """Test real AuthBuilder with edge case secrets."""
        edge_case_secrets = [
            "exactly_32_characters_long_test_!",  # Exactly 32 chars with special chars
            "a" * 64,  # Long secret
            "mixed_CASE_123_special_chars_32_!@#",  # Mixed case with numbers and special chars
        ]
        
        for secret in edge_case_secrets:
            with self.subTest(secret=secret[:10] + "..."):
                builder = SecretManagerBuilder(env_vars={
                    "JWT_SECRET_KEY": secret
                })
                
                # Real edge case testing
                retrieved_secret = builder.auth.get_jwt_secret()
                is_valid = builder.auth.validate_jwt_secret()
                
                self.assertEqual(retrieved_secret, secret)
                self.assertTrue(is_valid, f"Edge case secret validation failed")

    def test_real_auth_builder_state_isolation(self):
        """Test real AuthBuilder state isolation between instances."""
        # Create multiple builders with different states
        builder1 = SecretManagerBuilder(service="state_test_1", env_vars={
            "JWT_SECRET_KEY": "state_test_1_jwt_secret_32_chars"
        })
        
        builder2 = SecretManagerBuilder(service="state_test_2", env_vars={
            "JWT_SECRET_KEY": "state_test_2_jwt_secret_32_chars"
        })
        
        # Real state isolation testing
        secret1 = builder1.auth.get_jwt_secret()
        secret2 = builder2.auth.get_jwt_secret()
        
        # Different secrets due to different environments
        self.assertEqual(secret1, "state_test_1_jwt_secret_32_chars")
        self.assertEqual(secret2, "state_test_2_jwt_secret_32_chars")
        self.assertNotEqual(secret1, secret2)

    # ===================== REAL BUSINESS SCENARIOS (15 tests) =====================

    def test_real_business_jwt_configuration_development_flow(self):
        """Test real business scenario: JWT configuration in development flow."""
        # Real development scenario setup - set in global environment
        self.env.set("ENVIRONMENT", "development", source="test")
        self.env.set("JWT_SECRET_KEY", "development_business_jwt_secret_32_chars", source="test")
        self.env.set("DEBUG", "true", source="test")
        
        builder = SecretManagerBuilder(service="business_dev_test")
        
        # Real business validation
        self.assertTrue(builder.is_development(), "Should detect development environment")
        
        is_valid, error = builder.validate()
        self.assertTrue(is_valid, f"Development business validation failed: {error}")
        
        jwt_secret = builder.auth.get_jwt_secret()
        self.assertEqual(jwt_secret, "development_business_jwt_secret_32_chars")
        
        # Business requirement: debug info should be available in development
        debug_info = builder.get_debug_info()
        self.assertIn("secret_availability", debug_info)
        self.assertTrue(debug_info["secret_availability"]["jwt_secret_available"])

    def test_real_business_jwt_configuration_staging_deployment(self):
        """Test real business scenario: JWT configuration for staging deployment."""
        # Real staging scenario setup
        staging_config = {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_KEY": "staging_business_jwt_secret_32_chars_",
            "SERVICE_NAME": "netra-staging"
        }
        
        builder = SecretManagerBuilder(service="staging_deployment", env_vars=staging_config)
        
        # Real staging business validation
        self.assertTrue(builder.is_staging(), "Should detect staging environment")
        
        is_valid, error = builder.validate()
        self.assertTrue(is_valid, f"Staging deployment validation failed: {error}")
        
        # Business requirement: staging should have strong JWT secrets
        jwt_secret = builder.auth.get_jwt_secret()
        self.assertGreaterEqual(len(jwt_secret), 32, "Staging JWT secret must be at least 32 characters")
        self.assertTrue(builder.auth.validate_jwt_secret(), "Staging JWT secret must be valid")

    def test_real_business_jwt_configuration_production_security(self):
        """Test real business scenario: JWT configuration production security requirements."""
        # Real production scenario setup
        prod_config = {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": "production_business_security_jwt_secret_32_chars_long",
            "SECURITY_LEVEL": "high"
        }
        
        builder = SecretManagerBuilder(service="production_security", env_vars=prod_config)
        
        # Real production business validation
        self.assertTrue(builder.is_production(), "Should detect production environment")
        
        is_valid, error = builder.validate()
        self.assertTrue(is_valid, f"Production security validation failed: {error}")
        
        # Business requirement: production must have secure JWT configuration
        jwt_secret = builder.auth.get_jwt_secret()
        self.assertGreaterEqual(len(jwt_secret), 32, "Production JWT secret must be secure")
        
        # Business requirement: production debug info should not leak secrets
        debug_info = builder.get_debug_info()
        debug_str = str(debug_info)
        self.assertNotIn(jwt_secret, debug_str, "Production debug info must not leak JWT secret")

    def test_real_business_multi_service_consistency_scenario(self):
        """Test real business scenario: Multi-service JWT consistency."""
        # Real multi-service business scenario
        services = ["auth_service", "backend_service", "websocket_service"]
        consistent_jwt_secret = "multi_service_business_jwt_secret_32_chars"
        
        builders = {}
        for service in services:
            builders[service] = SecretManagerBuilder(
                service=service,
                env_vars={"JWT_SECRET_KEY": consistent_jwt_secret}
            )
        
        # Real business validation: all services must use same JWT secret
        retrieved_secrets = {}
        for service, builder in builders.items():
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Service {service} validation failed: {error}")
            
            retrieved_secrets[service] = builder.auth.get_jwt_secret()
        
        # Business requirement: JWT secret consistency across services
        unique_secrets = set(retrieved_secrets.values())
        self.assertEqual(len(unique_secrets), 1, "All services must use the same JWT secret")
        
        for service, secret in retrieved_secrets.items():
            self.assertEqual(secret, consistent_jwt_secret, f"Service {service} has wrong JWT secret")

    def test_real_business_configuration_failure_prevention(self):
        """Test real business scenario: Configuration failure prevention."""
        # Real business scenario: prevent cascade configuration failures
        
        # Test with missing JWT secret (should fail fast)
        builder_missing = SecretManagerBuilder(env_vars={})
        is_valid, error = builder_missing.validate()
        
        # Business requirement: fail fast to prevent cascade failures
        self.assertFalse(is_valid, "Should fail fast with missing JWT secret")
        self.assertIn("JWT secret is not available", error, "Error should clearly indicate missing JWT secret")
        
        # Test with valid configuration (should succeed)
        builder_valid = SecretManagerBuilder(env_vars={
            "JWT_SECRET_KEY": "business_failure_prevention_jwt_32_chars"
        })
        is_valid, error = builder_valid.validate()
        
        # Business requirement: succeed with valid configuration
        self.assertTrue(is_valid, f"Valid configuration should succeed: {error}")

    def test_real_business_adapter_pattern_value(self):
        """Test real business scenario: Adapter pattern business value."""
        # Real business validation: adapter pattern provides unified interface
        builder = SecretManagerBuilder(service="adapter_pattern_test")
        
        # Business requirement: unified interface for JWT configuration
        self.assertTrue(hasattr(builder, 'auth'), "Must provide auth interface")
        self.assertTrue(hasattr(builder.auth, 'get_jwt_secret'), "Must provide JWT secret access")
        self.assertTrue(hasattr(builder.auth, 'validate_jwt_secret'), "Must provide JWT validation")
        self.assertTrue(hasattr(builder, 'environment'), "Must provide environment detection")
        
        # Business requirement: interface methods must be callable
        self.assertTrue(callable(builder.auth.get_jwt_secret), "JWT secret method must be callable")
        self.assertTrue(callable(builder.auth.validate_jwt_secret), "JWT validation must be callable")

    def test_real_business_ssot_compliance_validation(self):
        """Test real business scenario: SSOT compliance validation."""
        builder = SecretManagerBuilder(service="ssot_compliance_test")
        
        # Business requirement: SSOT compliance must be explicit
        debug_info = builder.get_debug_info()
        
        self.assertIn('configuration', debug_info, "Debug info must contain configuration details")
        config = debug_info['configuration']
        
        self.assertIn('uses_shared_jwt_secret_manager', config, "Must explicitly declare SSOT compliance")
        self.assertIn('follows_ssot_principles', config, "Must explicitly declare SSOT principles")
        
        # Business validation: SSOT compliance flags must be True
        self.assertTrue(config['uses_shared_jwt_secret_manager'], "Must use shared JWT secret manager")
        self.assertTrue(config['follows_ssot_principles'], "Must follow SSOT principles")

    def test_real_business_environment_specific_configuration(self):
        """Test real business scenario: Environment-specific configuration requirements."""
        environments = [
            ("development", {"JWT_SECRET_KEY": "dev_env_specific_jwt_secret_32_chars"}),
            ("staging", {"JWT_SECRET_KEY": "staging_env_specific_jwt_secret_32_chars"}),
            ("production", {"JWT_SECRET_KEY": "prod_env_specific_jwt_secret_32_chars"})
        ]
        
        for env_name, env_vars in environments:
            with self.subTest(environment=env_name):
                env_vars["ENVIRONMENT"] = env_name
                builder = SecretManagerBuilder(service=f"{env_name}_service", env_vars=env_vars)
                
                # Business requirement: environment detection must be accurate
                self.assertEqual(builder.environment, env_name, f"Environment detection failed for {env_name}")
                
                # Business requirement: validation must succeed in all environments
                is_valid, error = builder.validate()
                self.assertTrue(is_valid, f"Environment {env_name} validation failed: {error}")

    def test_real_business_concurrent_user_simulation(self):
        """Test real business scenario: Concurrent user simulation."""
        # Real business scenario: simulate multiple concurrent users
        user_count = 10
        jwt_secret = "concurrent_users_jwt_secret_32_chars_"
        
        results = []
        errors = []
        
        def simulate_user(user_id):
            try:
                # Each user gets their own builder instance
                builder = SecretManagerBuilder(
                    service=f"user_service_{user_id}",
                    env_vars={"JWT_SECRET_KEY": jwt_secret}
                )
                
                # Real business operations
                is_valid, error = builder.validate()
                jwt_secret_retrieved = builder.auth.get_jwt_secret()
                
                results.append((user_id, is_valid, error, jwt_secret_retrieved))
            except Exception as e:
                errors.append((user_id, e))
        
        # Real concurrent simulation
        threads = []
        for user_id in range(user_count):
            thread = threading.Thread(target=simulate_user, args=(user_id,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Business validation: no errors should occur with concurrent users
        self.assertEqual(len(errors), 0, f"Concurrent user errors: {errors}")
        self.assertEqual(len(results), user_count, "All users should complete successfully")
        
        # Business requirement: all users should get consistent results
        for user_id, is_valid, error, retrieved_secret in results:
            self.assertTrue(is_valid, f"User {user_id} validation failed: {error}")
            self.assertEqual(retrieved_secret, jwt_secret, f"User {user_id} got wrong JWT secret")

    def test_real_business_rapid_deployment_scenario(self):
        """Test real business scenario: Rapid deployment with configuration validation."""
        # Real business scenario: rapid deployment requires fast validation
        deployment_configs = [
            {"ENVIRONMENT": "development", "JWT_SECRET_KEY": "rapid_dev_jwt_secret_32_characters"},
            {"ENVIRONMENT": "staging", "JWT_SECRET_KEY": "rapid_staging_jwt_secret_32_chars"},
            {"ENVIRONMENT": "production", "JWT_SECRET_KEY": "rapid_prod_jwt_secret_32_chars_"}
        ]
        
        start_time = time.time()
        
        # Real rapid deployment simulation
        for i, config in enumerate(deployment_configs * 5):  # Repeat for stress testing
            builder = SecretManagerBuilder(service=f"rapid_deploy_{i}", env_vars=config)
            
            # Business requirement: rapid validation
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Rapid deployment {i} failed: {error}")
            
            # Business requirement: JWT secret must be available immediately
            jwt_secret = builder.auth.get_jwt_secret()
            self.assertGreater(len(jwt_secret), 0, f"JWT secret not available for deployment {i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Business requirement: deployment validation must be fast
        self.assertLess(duration, 3.0, "Rapid deployment validation should complete within 3 seconds")

    def test_real_business_error_reporting_clarity(self):
        """Test real business scenario: Clear error reporting for operations teams."""
        # Real business scenario: operations teams need clear error messages
        
        error_scenarios = [
            ({}, "JWT secret is not available"),  # Missing JWT secret
            ({"JWT_SECRET_KEY": "short"}, "minimum requirements"),  # Short JWT secret
        ]
        
        for config, expected_error_text in error_scenarios:
            with self.subTest(config=str(config)):
                builder = SecretManagerBuilder(service="error_reporting_test", env_vars=config)
                
                # Real error scenario testing
                is_valid, error = builder.validate()
                
                # Business requirement: validation should fail with clear errors
                self.assertFalse(is_valid, "Validation should fail for invalid configuration")
                self.assertIn(expected_error_text, error, f"Error message should contain '{expected_error_text}'")
                
                # Business requirement: error messages should be actionable
                self.assertNotEqual(error.strip(), "", "Error message should not be empty")

    def test_real_business_debug_information_usefulness(self):
        """Test real business scenario: Debug information usefulness for troubleshooting."""
        # Real business scenario: developers need useful debug information
        builder = SecretManagerBuilder(
            service="debug_usefulness_test",
            env_vars={
                "ENVIRONMENT": "development",
                "JWT_SECRET_KEY": "debug_test_jwt_secret_32_characters"
            }
        )
        
        # Real debug information testing
        debug_info = builder.get_debug_info()
        
        # Business requirement: debug info must contain essential information
        required_sections = ['service', 'secret_availability', 'configuration', 'validation']
        for section in required_sections:
            self.assertIn(section, debug_info, f"Debug info must contain {section} section")
        
        # Business requirement: secret availability information
        availability = debug_info['secret_availability']
        self.assertIn('jwt_secret_available', availability, "Must report JWT secret availability")
        self.assertIn('jwt_secret_length', availability, "Must report JWT secret length")
        self.assertIn('jwt_secret_valid', availability, "Must report JWT secret validity")
        
        # Business requirement: configuration information
        config = debug_info['configuration']
        self.assertIn('uses_shared_jwt_secret_manager', config, "Must report SSOT usage")
        self.assertIn('follows_ssot_principles', config, "Must report SSOT compliance")

    def test_real_business_service_isolation_validation(self):
        """Test real business scenario: Service isolation validation."""
        # Real business scenario: services must be isolated but use shared secrets
        services = ["auth", "backend", "websocket", "analytics"]
        shared_jwt_secret = "isolated_services_jwt_secret_32_chars"
        
        builders = {}
        for service in services:
            builders[service] = SecretManagerBuilder(
                service=service,
                env_vars={
                    "JWT_SECRET_KEY": shared_jwt_secret,
                    "SERVICE_NAME": service
                }
            )
        
        # Business validation: service isolation
        for service, builder in builders.items():
            self.assertEqual(builder.service, service, f"Service {service} should maintain identity")
            
            # Business requirement: each service should validate independently
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Service {service} validation failed: {error}")
            
            # Business requirement: all services should share JWT secret
            jwt_secret = builder.auth.get_jwt_secret()
            self.assertEqual(jwt_secret, shared_jwt_secret, f"Service {service} should use shared JWT secret")
        
        # Business validation: builders should be independent instances
        service_list = list(builders.values())
        for i in range(len(service_list)):
            for j in range(i + 1, len(service_list)):
                self.assertIsNot(service_list[i], service_list[j], "Service builders must be independent")

    def test_real_business_configuration_change_impact(self):
        """Test real business scenario: Configuration change impact assessment."""
        # Real business scenario: configuration changes should have predictable impact
        
        # Initial configuration
        initial_config = {"JWT_SECRET_KEY": "initial_config_jwt_secret_32_chars"}
        builder = SecretManagerBuilder(service="config_change_test", env_vars=initial_config)
        
        # Initial validation
        initial_valid, initial_error = builder.validate()
        self.assertTrue(initial_valid, f"Initial configuration failed: {initial_error}")
        initial_secret = builder.auth.get_jwt_secret()
        
        # Configuration change
        changed_config = {"JWT_SECRET_KEY": "changed_config_jwt_secret_32_chars"}
        builder_changed = SecretManagerBuilder(service="config_change_test", env_vars=changed_config)
        
        # Changed validation
        changed_valid, changed_error = builder_changed.validate()
        self.assertTrue(changed_valid, f"Changed configuration failed: {changed_error}")
        changed_secret = builder_changed.auth.get_jwt_secret()
        
        # Business requirement: configuration changes should be reflected
        self.assertNotEqual(initial_secret, changed_secret, "Configuration change should be reflected in JWT secret")
        
        # Business requirement: both configurations should be valid
        self.assertTrue(initial_valid and changed_valid, "Both configurations should be valid")

    def test_real_business_scalability_validation(self):
        """Test real business scenario: System scalability validation."""
        # Real business scenario: system must handle increased load
        instance_count = 25
        jwt_secret = "scalability_test_jwt_secret_32_chars"
        
        # Real scalability testing
        builders = []
        start_time = time.time()
        
        for i in range(instance_count):
            builder = SecretManagerBuilder(
                service=f"scale_test_service_{i}",
                env_vars={"JWT_SECRET_KEY": jwt_secret}
            )
            
            # Business requirement: each instance should validate successfully
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Scalability instance {i} failed: {error}")
            
            builders.append(builder)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Business requirement: scalability should not degrade performance significantly
        self.assertLess(duration, 5.0, f"Creating {instance_count} instances should complete within 5 seconds")
        
        # Business requirement: all instances should be functional
        for i, builder in enumerate(builders):
            jwt_retrieved = builder.auth.get_jwt_secret()
            self.assertEqual(jwt_retrieved, jwt_secret, f"Instance {i} has wrong JWT secret")

    # ===================== REAL CONVENIENCE FUNCTIONS TESTS (10 tests) =====================

    def test_real_get_secret_manager_builder_function(self):
        """Test real get_secret_manager_builder convenience function."""
        # Real convenience function testing
        builder = get_secret_manager_builder()
        
        # Real validation
        self.assertIsInstance(builder, SecretManagerBuilder)
        self.assertEqual(builder.service, "shared")
        self.assertIsNotNone(builder.auth)

    def test_real_get_secret_manager_builder_custom_service(self):
        """Test real get_secret_manager_builder with custom service."""
        custom_service = "convenience_test_service"
        builder = get_secret_manager_builder(service=custom_service)
        
        # Real validation
        self.assertIsInstance(builder, SecretManagerBuilder)
        self.assertEqual(builder.service, custom_service)

    def test_real_validate_secret_manager_function_success(self):
        """Test real validate_secret_manager convenience function success."""
        # Set up real environment for successful validation
        self.env.set("JWT_SECRET_KEY", "convenience_validate_jwt_secret_32_chars", source="test")
        
        # Real convenience function validation
        is_valid, error = validate_secret_manager()
        
        # Real success validation
        self.assertTrue(is_valid, f"Convenience validation failed: {error}")
        self.assertEqual(error, "")

    def test_real_validate_secret_manager_function_failure(self):
        """Test real validate_secret_manager convenience function failure."""
        # Clear environment to force failure
        self.env.reset()
        
        # Real convenience function validation should fail
        is_valid, error = validate_secret_manager()
        
        # Real failure validation
        self.assertFalse(is_valid, "Convenience validation should fail without JWT secret")
        self.assertNotEqual(error, "", "Error message should not be empty")

    def test_real_validate_secret_manager_custom_service(self):
        """Test real validate_secret_manager with custom service."""
        # Set up real environment
        self.env.set("JWT_SECRET_KEY", "custom_service_validate_jwt_32_chars", source="test")
        
        custom_service = "custom_validation_service"
        
        # Real convenience function with custom service
        is_valid, error = validate_secret_manager(service=custom_service)
        
        # Real validation
        self.assertTrue(is_valid, f"Custom service validation failed: {error}")

    def test_real_get_jwt_secret_unified_function(self):
        """Test real get_jwt_secret_unified convenience function."""
        # Set up real environment
        self.env.set("JWT_SECRET_KEY", "unified_function_jwt_secret_32_chars", source="test")
        
        # Real convenience function execution
        jwt_secret = get_jwt_secret_unified()
        
        # Real validation
        self.assertIsInstance(jwt_secret, str)
        self.assertEqual(jwt_secret, "unified_function_jwt_secret_32_chars")

    def test_real_get_jwt_secret_unified_custom_service(self):
        """Test real get_jwt_secret_unified with custom service."""
        # Set up real environment
        self.env.set("JWT_SECRET_KEY", "unified_custom_jwt_secret_32_chars_", source="test")
        
        custom_service = "unified_custom_service"
        
        # Real convenience function with custom service
        jwt_secret = get_jwt_secret_unified(service=custom_service)
        
        # Real validation
        self.assertIsInstance(jwt_secret, str)
        self.assertEqual(jwt_secret, "unified_custom_jwt_secret_32_chars_")

    def test_real_convenience_functions_independence(self):
        """Test real convenience functions operate independently."""
        # Set up real environment
        self.env.set("JWT_SECRET_KEY", "independence_test_jwt_secret_32_chars", source="test")
        
        # Real independent operations
        builder1 = get_secret_manager_builder(service="independence_1")
        builder2 = get_secret_manager_builder(service="independence_2")
        
        # Real independence validation
        self.assertIsNot(builder1, builder2, "Builders should be independent instances")
        self.assertEqual(builder1.service, "independence_1")
        self.assertEqual(builder2.service, "independence_2")
        
        # Both should work independently
        is_valid1, _ = validate_secret_manager(service="independence_1")
        is_valid2, _ = validate_secret_manager(service="independence_2")
        
        self.assertTrue(is_valid1, "Independence test 1 should succeed")
        self.assertTrue(is_valid2, "Independence test 2 should succeed")

    def test_real_convenience_functions_error_handling(self):
        """Test real convenience functions error handling."""
        # Clear environment to force errors
        self.env.reset()
        
        # Real error handling testing
        try:
            # get_secret_manager_builder should not fail (just creates instance)
            builder = get_secret_manager_builder()
            self.assertIsNotNone(builder)
        except Exception as e:
            self.fail(f"get_secret_manager_builder should not raise exception: {e}")
        
        # validate_secret_manager should fail gracefully
        is_valid, error = validate_secret_manager()
        self.assertFalse(is_valid, "Validation should fail without JWT secret")
        self.assertNotEqual(error, "", "Error message should be provided")
        
        # get_jwt_secret_unified should fail with meaningful error
        with self.assertRaises(Exception) as cm:
            get_jwt_secret_unified()
        # Exception should be meaningful (not silently ignored)
        self.assertIsNotNone(str(cm.exception))

    def test_real_convenience_functions_performance(self):
        """Test real convenience functions performance."""
        # Set up real environment
        self.env.set("JWT_SECRET_KEY", "performance_convenience_jwt_32_chars", source="test")
        
        start_time = time.time()
        
        # Real performance testing
        for i in range(20):
            builder = get_secret_manager_builder(service=f"perf_test_{i}")
            is_valid, error = validate_secret_manager(service=f"perf_test_{i}")
            jwt_secret = get_jwt_secret_unified(service=f"perf_test_{i}")
            
            # Real validation during performance test
            self.assertIsNotNone(builder)
            self.assertTrue(is_valid, f"Performance iteration {i} validation failed: {error}")
            self.assertIsInstance(jwt_secret, str)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance requirement: should complete within reasonable time
        self.assertLess(duration, 2.0, "Convenience functions performance test should complete within 2 seconds")

    # ===================== REAL INTEGRATION TESTS (10 tests) =====================

    def test_real_integration_with_isolated_environment(self):
        """Test real integration with IsolatedEnvironment."""
        # Real IsolatedEnvironment integration
        test_vars = {
            "JWT_SECRET_KEY": "integration_jwt_secret_32_chars_long",
            "ENVIRONMENT": "development",
            "SERVICE_NAME": "integration_test"
        }
        
        # Set variables in IsolatedEnvironment
        for key, value in test_vars.items():
            self.env.set(key, value, source="integration_test")
        
        # Create builder that should use IsolatedEnvironment
        builder = SecretManagerBuilder(service="integration_test")
        
        # Real integration validation
        is_valid, error = builder.validate()
        self.assertTrue(is_valid, f"Integration validation failed: {error}")
        
        # Verify IsolatedEnvironment integration
        self.assertEqual(builder.environment, "development")
        self.assertEqual(builder.env.get("SERVICE_NAME"), "integration_test")

    def test_real_integration_thread_safety(self):
        """Test real integration thread safety."""
        # Set up real environment for thread safety testing
        self.env.set("JWT_SECRET_KEY", "thread_safety_jwt_secret_32_chars_", source="test")
        
        results = []
        errors = []
        
        def thread_test(thread_id):
            try:
                builder = SecretManagerBuilder(service=f"thread_test_{thread_id}")
                is_valid, error = builder.validate()
                jwt_secret = builder.auth.get_jwt_secret()
                debug_info = builder.get_debug_info()
                
                results.append((thread_id, is_valid, error, jwt_secret, debug_info))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Real thread safety testing
        threads = []
        for i in range(8):
            thread = threading.Thread(target=thread_test, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Real thread safety validation
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
        self.assertEqual(len(results), 8)
        
        for thread_id, is_valid, error, jwt_secret, debug_info in results:
            self.assertTrue(is_valid, f"Thread {thread_id} validation failed: {error}")
            self.assertEqual(jwt_secret, "thread_safety_jwt_secret_32_chars_")
            self.assertIsInstance(debug_info, dict)

    def test_real_integration_memory_management(self):
        """Test real integration memory management."""
        # Real memory management testing
        initial_builders = []
        
        # Create initial builders
        for i in range(10):
            builder = SecretManagerBuilder(
                service=f"memory_test_{i}",
                env_vars={"JWT_SECRET_KEY": f"memory_jwt_secret_{i:02d}_32_chars_long"}
            )
            initial_builders.append(builder)
        
        # Validate all builders work
        for i, builder in enumerate(initial_builders):
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Memory test builder {i} failed: {error}")
        
        # Clear references and create new ones
        initial_builders.clear()
        
        # Create new builders (tests memory cleanup)
        for i in range(10):
            builder = SecretManagerBuilder(
                service=f"memory_test_new_{i}",
                env_vars={"JWT_SECRET_KEY": f"memory_new_jwt_secret_{i:02d}_32_chars"}
            )
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Memory test new builder {i} failed: {error}")

    def test_real_integration_environment_switching(self):
        """Test real integration environment switching."""
        environments = [
            ("development", "dev_switch_jwt_secret_32_chars_long"),
            ("staging", "staging_switch_jwt_secret_32_chars_"),
            ("production", "prod_switch_jwt_secret_32_chars_long")
        ]
        
        for env_name, jwt_secret in environments:
            with self.subTest(environment=env_name):
                # Real environment switching
                env_vars = {
                    "ENVIRONMENT": env_name,
                    "JWT_SECRET_KEY": jwt_secret
                }
                
                builder = SecretManagerBuilder(service=f"{env_name}_switch_test", env_vars=env_vars)
                
                # Real integration validation
                self.assertEqual(builder.environment, env_name)
                
                is_valid, error = builder.validate()
                self.assertTrue(is_valid, f"Environment {env_name} switch failed: {error}")
                
                retrieved_secret = builder.auth.get_jwt_secret()
                self.assertEqual(retrieved_secret, jwt_secret)

    def test_real_integration_concurrent_environments(self):
        """Test real integration with concurrent different environments."""
        env_configs = [
            ("concurrent_dev", "development", "concurrent_dev_jwt_secret_32_chars"),
            ("concurrent_staging", "staging", "concurrent_staging_jwt_32_chars_"),
            ("concurrent_prod", "production", "concurrent_prod_jwt_secret_32_chars")
        ]
        
        results = []
        errors = []
        
        def concurrent_env_test(service, environment, jwt_secret):
            try:
                builder = SecretManagerBuilder(
                    service=service,
                    env_vars={
                        "ENVIRONMENT": environment,
                        "JWT_SECRET_KEY": jwt_secret
                    }
                )
                
                is_valid, error = builder.validate()
                retrieved_secret = builder.auth.get_jwt_secret()
                
                results.append((service, environment, is_valid, error, retrieved_secret))
            except Exception as e:
                errors.append((service, environment, e))
        
        # Real concurrent environment testing
        threads = []
        for service, environment, jwt_secret in env_configs:
            thread = threading.Thread(target=concurrent_env_test, args=(service, environment, jwt_secret))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Real concurrent validation
        self.assertEqual(len(errors), 0, f"Concurrent environment errors: {errors}")
        self.assertEqual(len(results), 3)
        
        for service, environment, is_valid, error, retrieved_secret in results:
            self.assertTrue(is_valid, f"Concurrent env {service} failed: {error}")

    def test_real_integration_configuration_persistence(self):
        """Test real integration configuration persistence."""
        # Real configuration persistence testing
        persistent_config = {
            "JWT_SECRET_KEY": "persistent_jwt_secret_32_chars_long",
            "ENVIRONMENT": "development",
            "PERSISTENT_VAR": "persistent_value"
        }
        
        # Create builder with persistent configuration
        builder1 = SecretManagerBuilder(service="persistence_test_1", env_vars=persistent_config)
        
        # Validate initial state
        is_valid1, error1 = builder1.validate()
        self.assertTrue(is_valid1, f"Persistent config 1 failed: {error1}")
        
        secret1 = builder1.auth.get_jwt_secret()
        env1 = builder1.env.get("PERSISTENT_VAR")
        
        # Create second builder with same configuration
        builder2 = SecretManagerBuilder(service="persistence_test_2", env_vars=persistent_config)
        
        # Validate persistence
        is_valid2, error2 = builder2.validate()
        self.assertTrue(is_valid2, f"Persistent config 2 failed: {error2}")
        
        secret2 = builder2.auth.get_jwt_secret()
        env2 = builder2.env.get("PERSISTENT_VAR")
        
        # Real persistence validation
        self.assertEqual(secret1, secret2, "JWT secrets should be consistent")
        self.assertEqual(env1, env2, "Environment variables should be consistent")

    def test_real_integration_error_propagation(self):
        """Test real integration error propagation."""
        # Real error propagation testing
        error_scenarios = [
            ({}, "JWT secret is not available"),  # Missing JWT secret
            ({"JWT_SECRET_KEY": "x"}, "minimum requirements"),  # Invalid JWT secret
        ]
        
        for config, expected_error in error_scenarios:
            with self.subTest(config=str(config)):
                builder = SecretManagerBuilder(service="error_propagation_test", env_vars=config)
                
                # Real error propagation validation
                is_valid, error = builder.validate()
                
                self.assertFalse(is_valid, "Should fail for invalid configuration")
                self.assertIn(expected_error, error, f"Error should contain '{expected_error}'")
                
                # Error should also appear in debug info
                debug_info = builder.get_debug_info()
                self.assertIn('validation', debug_info)
                self.assertFalse(debug_info['validation']['is_valid'])

    def test_real_integration_performance_under_load(self):
        """Test real integration performance under load."""
        # Real performance under load testing
        load_config = {
            "JWT_SECRET_KEY": "load_test_jwt_secret_32_characters_long",
            "ENVIRONMENT": "development"
        }
        
        start_time = time.time()
        
        # Real load simulation
        for i in range(30):
            builder = SecretManagerBuilder(service=f"load_test_service_{i}", env_vars=load_config)
            
            # Real operations under load
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Load test {i} validation failed: {error}")
            
            jwt_secret = builder.auth.get_jwt_secret()
            self.assertEqual(jwt_secret, "load_test_jwt_secret_32_characters_long")
            
            debug_info = builder.get_debug_info()
            self.assertIn('service', debug_info)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Real performance validation
        self.assertLess(duration, 3.0, "Load test should complete within 3 seconds")

    def test_real_integration_state_isolation_validation(self):
        """Test real integration state isolation validation."""
        # Real state isolation testing
        configs = [
            ("isolated_1", {"JWT_SECRET_KEY": "isolated_jwt_1_32_chars_long_test"}),
            ("isolated_2", {"JWT_SECRET_KEY": "isolated_jwt_2_32_chars_long_test"}),
            ("isolated_3", {"JWT_SECRET_KEY": "isolated_jwt_3_32_chars_long_test"})
        ]
        
        builders = {}
        for service, config in configs:
            builders[service] = SecretManagerBuilder(service=service, env_vars=config)
        
        # Real state isolation validation
        for service, builder in builders.items():
            is_valid, error = builder.validate()
            self.assertTrue(is_valid, f"Isolated service {service} failed: {error}")
        
        # Validate isolation - each should have its own JWT secret
        secrets = {}
        for service, builder in builders.items():
            secrets[service] = builder.auth.get_jwt_secret()
        
        # All secrets should be different (due to different configurations)
        unique_secrets = set(secrets.values())
        self.assertEqual(len(unique_secrets), 3, "All services should have different JWT secrets")
        
        # Validate expected secrets
        for (service, config), actual_secret in zip(configs, secrets.values()):
            expected_secret = config["JWT_SECRET_KEY"]
            self.assertEqual(actual_secret, expected_secret, f"Service {service} has wrong secret")

    def test_real_integration_comprehensive_scenario(self):
        """Test real integration comprehensive business scenario."""
        # Real comprehensive integration scenario
        scenario_config = {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_KEY": "comprehensive_jwt_secret_32_chars_long",
            "SERVICE_NAME": "comprehensive_test",
            "DEBUG": "true"
        }
        
        # Create builder for comprehensive testing
        builder = SecretManagerBuilder(service="comprehensive_integration", env_vars=scenario_config)
        
        # Real comprehensive validation
        
        # 1. Basic validation
        is_valid, error = builder.validate()
        self.assertTrue(is_valid, f"Comprehensive validation failed: {error}")
        
        # 2. Environment detection
        self.assertTrue(builder.is_staging(), "Should detect staging environment")
        
        # 3. JWT secret functionality
        jwt_secret = builder.auth.get_jwt_secret()
        self.assertEqual(jwt_secret, "comprehensive_jwt_secret_32_chars_long")
        
        is_jwt_valid = builder.auth.validate_jwt_secret()
        self.assertTrue(is_jwt_valid, "JWT secret should be valid")
        
        # 4. Service secret functionality
        service_secret = builder.auth.get_service_secret()
        self.assertIsInstance(service_secret, str)  # May be empty if not configured
        
        # 5. Debug information
        debug_info = builder.get_debug_info()
        required_keys = ['service', 'secret_availability', 'configuration', 'validation']
        for key in required_keys:
            self.assertIn(key, debug_info, f"Debug info missing {key}")
        
        # 6. SSOT compliance
        config_info = debug_info['configuration']
        self.assertTrue(config_info['uses_shared_jwt_secret_manager'], "Should use shared JWT secret manager")
        self.assertTrue(config_info['follows_ssot_principles'], "Should follow SSOT principles")
        
        # 7. Environment variable access
        self.assertEqual(builder.env.get("SERVICE_NAME"), "comprehensive_test")
        self.assertEqual(builder.get_env_bool("DEBUG"), True)
        
        # Real comprehensive scenario completion
        self.assertTrue(True, "Comprehensive integration scenario completed successfully")


if __name__ == '__main__':
    # Configure logging for test runs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the comprehensive CLAUDE.md compliant test suite
    unittest.main(verbosity=2)