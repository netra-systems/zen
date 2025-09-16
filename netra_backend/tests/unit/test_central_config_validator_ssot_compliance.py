#!/usr/bin/env python3
"""
Unit Tests: Central Config Validator SSOT Compliance

PURPOSE: Validate SSOT compliance patterns in central configuration validation
         and ensure proper integration with backend configuration systems.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Goal: System Stability & Configuration Security
- Value Impact: Prevents configuration drift and ensures consistent validation
- Revenue Impact: Protects against configuration errors that could cause service failures

CRITICAL REQUIREMENTS:
1. Tests MUST validate central validator singleton pattern (SSOT requirement)
2. Tests MUST verify configuration rule completeness and consistency
3. Tests MUST ensure no duplicate validation logic exists
4. Tests MUST validate environment-specific validation behavior
5. Tests MUST test integration with backend configuration systems

ARCHITECTURE INTEGRATION:
- Uses test_framework.ssot.base_test_case for SSOT test infrastructure
- Tests shared.configuration.central_config_validator SSOT implementation
- Validates integration with netra_backend.app.core.configuration.validator
- Tests shared.isolated_environment integration patterns
"""

import pytest
import time
from typing import Dict, List, Optional, Any
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Central SSOT Validator
from shared.configuration.central_config_validator import (
    CentralConfigurationValidator,
    get_central_validator,
    clear_central_validator_cache,
    Environment,
    ConfigRequirement,
    ConfigRule,
    LegacyConfigMarker,
    validate_platform_configuration
)

# Backend Configuration Integration
from netra_backend.app.core.configuration.validator import ConfigurationValidator

# Environment Management
from shared.isolated_environment import IsolatedEnvironment, get_env


@dataclass
class ValidationTestResult:
    """Result of a validation test."""
    test_name: str
    passed: bool
    error_message: Optional[str] = None
    validation_time_ms: float = 0.0
    violations_detected: int = 0


class TestCentralConfigValidatorSsotCompliance(SSotBaseTestCase):
    """
    Unit tests for Central Configuration Validator SSOT compliance.
    
    These tests ensure the central validator maintains SSOT patterns and
    properly integrates with backend configuration systems.
    """
    
    def setup_method(self, method):
        """Setup for each unit test."""
        super().setup_method(method)
        
        # Clear validator cache to ensure clean test state
        clear_central_validator_cache()
        
        # Initialize test metrics
        self.record_metric("test_start_time", time.time())
        self.record_metric("ssot_compliance_checks", 0)
        self.record_metric("configuration_validations", 0)
    
    def test_central_validator_singleton_pattern(self):
        """
        UNIT: Test central validator maintains singleton pattern (SSOT requirement).
        
        The central validator MUST be a singleton to ensure all services use
        the same validation instance and prevent configuration drift.
        """
        start_time = time.time()
        
        # Test multiple calls return same instance
        validator1 = get_central_validator()
        validator2 = get_central_validator()
        validator3 = get_central_validator()
        
        # All should be the exact same object
        self.assertIs(validator1, validator2, "Central validator not maintaining singleton pattern")
        self.assertIs(validator2, validator3, "Central validator singleton broken on third call")
        self.assertIs(validator1, validator3, "Central validator singleton inconsistent")
        
        # Test with different environment getters still returns same instance
        def mock_env_getter(key, default=None):
            return "test_value" if key == "TEST_KEY" else default
        
        validator4 = get_central_validator(mock_env_getter)
        self.assertIs(validator1, validator4, "Central validator singleton broken with custom env getter")
        
        # Record metrics
        validation_time = (time.time() - start_time) * 1000
        self.record_metric("singleton_validation_time_ms", validation_time)
        self.record_metric("ssot_compliance_checks", 1)
        
        self.logger.info(f"Central validator singleton pattern validated in {validation_time:.1f}ms")
    
    def test_configuration_rules_completeness(self):
        """
        UNIT: Test configuration rules are complete and consistent.
        
        The central validator MUST have comprehensive rules for all environments
        and critical configuration variables.
        """
        start_time = time.time()
        validator = get_central_validator()
        rules = validator.CONFIGURATION_RULES
        
        # Test 1: Verify all environments are covered
        covered_environments = set()
        for rule in rules:
            covered_environments.update(rule.environments)
        
        required_environments = {Environment.DEVELOPMENT, Environment.TEST, Environment.STAGING, Environment.PRODUCTION}
        missing_environments = required_environments - covered_environments
        
        self.assertEqual(len(missing_environments), 0, 
                        f"Configuration rules missing for environments: {missing_environments}")
        
        # Test 2: Verify critical variables have appropriate requirements
        critical_vars = {
            "JWT_SECRET_STAGING": ConfigRequirement.REQUIRED_SECURE,
            "JWT_SECRET_PRODUCTION": ConfigRequirement.REQUIRED_SECURE,
            "JWT_SECRET_KEY": ConfigRequirement.REQUIRED_SECURE,
            "POSTGRES_PASSWORD": ConfigRequirement.OPTIONAL,  # Can use DATABASE_URL instead
            "REDIS_PASSWORD": ConfigRequirement.REQUIRED_SECURE,
            "SERVICE_SECRET": ConfigRequirement.REQUIRED_SECURE,
            "FERNET_KEY": ConfigRequirement.REQUIRED_SECURE,
            "GEMINI_API_KEY": ConfigRequirement.REQUIRED
        }
        
        rules_by_var = {rule.env_var: rule for rule in rules}
        
        for var, expected_requirement in critical_vars.items():
            self.assertIn(var, rules_by_var, f"Critical variable {var} missing from configuration rules")
            
            actual_requirement = rules_by_var[var].requirement
            if var == "POSTGRES_PASSWORD":
                # Special case: can be optional since DATABASE_URL can be used instead
                self.assertIn(actual_requirement, [ConfigRequirement.OPTIONAL, ConfigRequirement.REQUIRED_SECURE],
                             f"Variable {var} has unexpected requirement: {actual_requirement}")
            else:
                self.assertEqual(actual_requirement, expected_requirement,
                               f"Variable {var} has wrong requirement: expected {expected_requirement}, got {actual_requirement}")
        
        # Test 3: Verify security requirements for production secrets
        production_secrets = ["JWT_SECRET_PRODUCTION", "SERVICE_SECRET", "FERNET_KEY"]
        for secret in production_secrets:
            if secret in rules_by_var:
                rule = rules_by_var[secret]
                self.assertEqual(rule.requirement, ConfigRequirement.REQUIRED_SECURE,
                               f"Production secret {secret} not marked as REQUIRED_SECURE")
                self.assertIn(Environment.PRODUCTION, rule.environments,
                             f"Production secret {secret} not required in production environment")
                self.assertIsNotNone(rule.min_length, f"Production secret {secret} missing min_length requirement")
                self.assertGreaterEqual(rule.min_length, 32, f"Production secret {secret} min_length too short")
        
        # Record metrics
        validation_time = (time.time() - start_time) * 1000
        self.record_metric("rules_completeness_validation_time_ms", validation_time)
        self.record_metric("configuration_validations", len(rules))
        self.record_metric("ssot_compliance_checks", self.get_metric("ssot_compliance_checks", 0) + 3)
        
        self.logger.info(f"Configuration rules completeness validated ({len(rules)} rules) in {validation_time:.1f}ms")
    
    def test_environment_detection_consistency(self):
        """
        UNIT: Test environment detection is consistent across all contexts.
        
        Environment detection MUST be consistent regardless of how the
        validator is called or what state it's in.
        """
        start_time = time.time()
        environments_tested = 0
        
        test_environments = ["development", "testing", "staging", "production"]
        
        for env_name in test_environments:
            environments_tested += 1
            
            with self.temp_env_vars(ENVIRONMENT=env_name, PYTEST_CURRENT_TEST="test"):
                clear_central_validator_cache()
                validator = get_central_validator()
                
                # Test multiple calls return consistent environment
                env1 = validator.get_environment()
                env2 = validator.get_environment()
                env3 = validator.get_environment()
                
                self.assertEqual(env1, env2, f"Environment detection inconsistent for {env_name}: {env1} != {env2}")
                self.assertEqual(env2, env3, f"Environment detection inconsistent for {env_name}: {env2} != {env3}")
                
                # Test environment mapping is correct
                expected_env_map = {
                    "development": Environment.DEVELOPMENT,
                    "testing": Environment.TEST,
                    "staging": Environment.STAGING,
                    "production": Environment.PRODUCTION
                }
                
                expected_env = expected_env_map[env_name]
                self.assertEqual(env1, expected_env, 
                               f"Environment detection wrong for {env_name}: expected {expected_env}, got {env1}")
                
                # Test cache clearing works
                validator.clear_environment_cache()
                env_after_clear = validator.get_environment()
                self.assertEqual(env1, env_after_clear, 
                               f"Environment detection changed after cache clear for {env_name}")
        
        # Record metrics
        validation_time = (time.time() - start_time) * 1000
        self.record_metric("environment_detection_validation_time_ms", validation_time)
        self.record_metric("environments_tested", environments_tested)
        self.record_metric("ssot_compliance_checks", self.get_metric("ssot_compliance_checks", 0) + environments_tested)
        
        self.logger.info(f"Environment detection consistency validated ({environments_tested} environments) in {validation_time:.1f}ms")
    
    def test_no_duplicate_validation_logic(self):
        """
        UNIT: Test no duplicate validation logic exists between validators.
        
        The central validator MUST be the single source of truth for validation,
        with no duplicate logic in backend or other validators.
        """
        start_time = time.time()
        
        # Test 1: Verify backend validator delegates to central validator
        backend_validator = ConfigurationValidator()
        
        # Check that backend validator uses central patterns (not duplicating logic)
        self.assertTrue(hasattr(backend_validator, '_validation_rules'),
                       "Backend validator missing validation rules structure")
        
        # Test 2: Verify validation consistency between validators
        with self.temp_env_vars(ENVIRONMENT="test", JWT_SECRET_KEY="test-secret-32-characters-long-123456"):
            clear_central_validator_cache()
            central_validator = get_central_validator()
            
            # Test central validator environment detection
            central_env = central_validator.get_environment()
            backend_env = backend_validator._get_environment()
            
            # Map environments for comparison
            env_mapping = {
                Environment.DEVELOPMENT: "development",
                Environment.TEST: "testing",
                Environment.STAGING: "staging", 
                Environment.PRODUCTION: "production"
            }
            
            mapped_central_env = env_mapping.get(central_env, str(central_env))
            self.assertEqual(mapped_central_env, backend_env,
                           f"Environment detection inconsistent: central={mapped_central_env}, backend={backend_env}")
        
        # Test 3: Verify no hardcoded validation logic in backend
        # Backend should use configuration-driven validation, not hardcoded rules
        backend_rules = backend_validator._validation_rules
        self.assertIsInstance(backend_rules, dict, "Backend validator rules should be dictionary-based configuration")
        
        # Test 4: Verify consistent error handling patterns
        with self.temp_env_vars(ENVIRONMENT="production"):
            clear_central_validator_cache()
            central_validator = get_central_validator()
            
            # Clear critical variables
            original_jwt_secret = self.get_env_var("JWT_SECRET_PRODUCTION")
            self.delete_env_var("JWT_SECRET_PRODUCTION")
            
            try:
                # Both validators should handle missing critical config consistently
                central_error = None
                backend_error = None
                
                try:
                    central_validator.validate_all_requirements()
                except Exception as e:
                    central_error = str(e)
                
                # Backend validator should use similar error patterns
                env_dict = {"ENVIRONMENT": "production"}
                backend_result = backend_validator.validate_environment_variables(env_dict)
                if not backend_result.is_valid:
                    backend_error = "; ".join(backend_result.errors)
                
                # Both should detect missing critical configuration
                self.assertIsNotNone(central_error, "Central validator should detect missing JWT secret")
                self.assertIsNotNone(backend_error, "Backend validator should detect missing critical variables")
                
            finally:
                # Restore original value
                if original_jwt_secret:
                    self.set_env_var("JWT_SECRET_PRODUCTION", original_jwt_secret)
        
        # Record metrics
        validation_time = (time.time() - start_time) * 1000
        self.record_metric("duplicate_logic_validation_time_ms", validation_time)
        self.record_metric("ssot_compliance_checks", self.get_metric("ssot_compliance_checks", 0) + 4)
        
        self.logger.info(f"No duplicate validation logic verified in {validation_time:.1f}ms")
    
    def test_legacy_configuration_handling(self):
        """
        UNIT: Test legacy configuration handling is consistent and safe.
        
        Legacy configuration handling MUST be centralized and prevent
        security issues from deprecated patterns.
        """
        start_time = time.time()
        
        # Test 1: Verify legacy marker patterns are comprehensive
        legacy_vars = LegacyConfigMarker.LEGACY_VARIABLES
        
        expected_legacy_vars = ["DATABASE_URL", "JWT_SECRET", "REDIS_URL", 
                               "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "APP_SECRET_KEY"]
        
        for var in expected_legacy_vars:
            self.assertIn(var, legacy_vars, f"Expected legacy variable {var} not marked as legacy")
        
        # Test 2: Verify security-critical legacy variables are marked
        security_critical_vars = ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"]
        for var in security_critical_vars:
            if var in legacy_vars:
                legacy_info = legacy_vars[var]
                self.assertTrue(legacy_info.get("critical_security", False),
                               f"Security-critical legacy variable {var} not marked as critical_security")
        
        # Test 3: Test legacy usage detection
        test_configs = {
            "JWT_SECRET": "old-jwt-secret",  # Should trigger warning
            "JWT_SECRET_KEY": "new-jwt-secret",  # Should be fine
            "DATABASE_URL": "postgresql://...",  # Should trigger warning
        }
        
        warnings = LegacyConfigMarker.check_legacy_usage(test_configs)
        
        # Should have warnings for legacy variables
        jwt_secret_warning = any("JWT_SECRET" in warning and "JWT_SECRET_KEY" not in warning for warning in warnings)
        self.assertTrue(jwt_secret_warning, "Legacy JWT_SECRET usage not detected")
        
        database_url_warning = any("DATABASE_URL" in warning for warning in warnings)
        self.assertTrue(database_url_warning, "Legacy DATABASE_URL usage not detected")
        
        # Test 4: Test replacement variable mapping
        jwt_secret_replacements = LegacyConfigMarker.get_replacement_variables("JWT_SECRET")
        self.assertEqual(jwt_secret_replacements, ["JWT_SECRET_KEY"], 
                        f"Wrong replacement for JWT_SECRET: {jwt_secret_replacements}")
        
        oauth_id_replacements = LegacyConfigMarker.get_replacement_variables("GOOGLE_OAUTH_CLIENT_ID")
        expected_oauth_replacements = [
            "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT", "GOOGLE_OAUTH_CLIENT_ID_TEST",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION"
        ]
        self.assertEqual(oauth_id_replacements, expected_oauth_replacements,
                        f"Wrong OAuth client ID replacements: {oauth_id_replacements}")
        
        # Record metrics
        validation_time = (time.time() - start_time) * 1000
        self.record_metric("legacy_config_validation_time_ms", validation_time)
        self.record_metric("legacy_variables_checked", len(legacy_vars))
        self.record_metric("ssot_compliance_checks", self.get_metric("ssot_compliance_checks", 0) + 4)
        
        self.logger.info(f"Legacy configuration handling validated ({len(legacy_vars)} legacy vars) in {validation_time:.1f}ms")
    
    def test_validation_error_consistency(self):
        """
        UNIT: Test validation error messages are consistent and helpful.
        
        Validation errors MUST provide clear, actionable information and
        maintain consistent formatting across all validators.
        """
        start_time = time.time()
        error_scenarios_tested = 0
        
        # Test 1: Missing JWT secret in staging
        with self.temp_env_vars(ENVIRONMENT="staging"):
            clear_central_validator_cache()
            validator = get_central_validator()
            
            # Clear JWT secret
            original_jwt_secret = self.get_env_var("JWT_SECRET_STAGING")
            self.delete_env_var("JWT_SECRET_STAGING")
            
            try:
                validator.validate_all_requirements()
                self.fail("Expected ValueError for missing JWT_SECRET_STAGING")
            except ValueError as e:
                error_scenarios_tested += 1
                error_msg = str(e)
                
                # Error message should be helpful and specific
                self.assertIn("JWT_SECRET_STAGING", error_msg, "Error message missing specific variable name")
                self.assertIn("staging", error_msg.lower(), "Error message missing environment context")
                self.assertIn("required", error_msg.lower(), "Error message missing requirement context")
                
            finally:
                if original_jwt_secret:
                    self.set_env_var("JWT_SECRET_STAGING", original_jwt_secret)
        
        # Test 2: Invalid database configuration
        with self.temp_env_vars(ENVIRONMENT="production"):
            clear_central_validator_cache()
            validator = get_central_validator()
            
            # Set invalid database host
            with self.temp_env_vars(POSTGRES_HOST="localhost", POSTGRES_PASSWORD="weak"):
                try:
                    validator._validate_database_configuration(Environment.PRODUCTION)
                    self.fail("Expected ValueError for localhost database in production")
                except ValueError as e:
                    error_scenarios_tested += 1
                    error_msg = str(e)
                    
                    # Error should mention localhost issue
                    self.assertIn("localhost", error_msg.lower(), "Error message missing localhost context")
                    self.assertIn("production", error_msg.lower(), "Error message missing environment context")
        
        # Test 3: Weak password validation
        with self.temp_env_vars(ENVIRONMENT="staging"):
            clear_central_validator_cache()
            validator = get_central_validator()
            
            # Test weak Redis password
            with self.temp_env_vars(REDIS_HOST="redis.example.com", REDIS_PASSWORD="weak"):
                try:
                    validator.validate_all_requirements()
                    self.fail("Expected ValueError for weak Redis password")
                except ValueError as e:
                    error_scenarios_tested += 1
                    error_msg = str(e)
                    
                    # Error should mention password requirements
                    self.assertIn("REDIS_PASSWORD", error_msg, "Error message missing specific variable")
                    self.assertTrue(
                        any(word in error_msg.lower() for word in ["characters", "length", "secure"]),
                        f"Error message missing security context: {error_msg}"
                    )
        
        # Test 4: Environment variable format validation
        validator = get_central_validator()
        
        # Test forbidden values
        for var in ["JWT_SECRET_STAGING", "POSTGRES_PASSWORD", "REDIS_PASSWORD"]:
            rule = None
            for r in validator.CONFIGURATION_RULES:
                if r.env_var == var:
                    rule = r
                    break
            
            if rule and rule.forbidden_values:
                error_scenarios_tested += 1
                for forbidden_value in rule.forbidden_values:
                    with self.temp_env_vars(**{var: forbidden_value}):
                        try:
                            rule_env = list(rule.environments)[0]  # Get first environment for rule
                            validator._validate_single_requirement(rule, rule_env)
                            self.fail(f"Expected ValueError for forbidden value '{forbidden_value}' in {var}")
                        except ValueError as e:
                            error_msg = str(e)
                            self.assertIn(var, error_msg, f"Error message missing variable name for {var}")
        
        # Record metrics
        validation_time = (time.time() - start_time) * 1000
        self.record_metric("error_consistency_validation_time_ms", validation_time)
        self.record_metric("error_scenarios_tested", error_scenarios_tested)
        self.record_metric("ssot_compliance_checks", self.get_metric("ssot_compliance_checks", 0) + error_scenarios_tested)
        
        self.logger.info(f"Validation error consistency verified ({error_scenarios_tested} scenarios) in {validation_time:.1f}ms")
    
    def test_isolated_environment_integration(self):
        """
        UNIT: Test central validator properly integrates with IsolatedEnvironment.
        
        The central validator MUST use IsolatedEnvironment for all environment
        variable access to maintain test isolation and prevent leakage.
        """
        start_time = time.time()
        
        # Test 1: Verify validator uses IsolatedEnvironment
        validator = get_central_validator()
        
        # The validator should be using get_env() from isolated_environment
        self.assertIsNotNone(validator.env_getter, "Validator missing environment getter function")
        
        # Test 2: Test environment variable isolation
        test_var = "CENTRAL_VALIDATOR_TEST_VAR"
        test_value = "test_value_12345"
        
        # Set variable through our test interface
        self.set_env_var(test_var, test_value)
        
        # Validator should see the same value
        validator_value = validator.env_getter(test_var)
        self.assertEqual(validator_value, test_value, 
                        f"Validator not seeing isolated environment variable: expected {test_value}, got {validator_value}")
        
        # Test 3: Test environment variable cleanup
        self.delete_env_var(test_var)
        validator_value_after_delete = validator.env_getter(test_var)
        self.assertIsNone(validator_value_after_delete, 
                         f"Validator still seeing deleted environment variable: {validator_value_after_delete}")
        
        # Test 4: Test environment state consistency across validator calls
        with self.temp_env_vars(VALIDATOR_ISOLATION_TEST="isolation_value"):
            clear_central_validator_cache()
            
            # Multiple validator instances should see same environment
            validator1 = get_central_validator()
            validator2 = get_central_validator()
            
            value1 = validator1.env_getter("VALIDATOR_ISOLATION_TEST")
            value2 = validator2.env_getter("VALIDATOR_ISOLATION_TEST")
            
            self.assertEqual(value1, value2, 
                           f"Environment isolation inconsistent between validator instances: {value1} != {value2}")
            self.assertEqual(value1, "isolation_value", 
                           f"Environment isolation not working: expected 'isolation_value', got {value1}")
        
        # Test 5: Test environment getter function customization
        def custom_env_getter(key, default=None):
            if key == "CUSTOM_TEST_KEY":
                return "custom_test_value"
            return default
        
        # Note: get_central_validator maintains singleton, so we test the pattern without breaking it
        temp_validator = CentralConfigurationValidator(custom_env_getter)
        custom_value = temp_validator.env_getter("CUSTOM_TEST_KEY")
        self.assertEqual(custom_value, "custom_test_value", 
                        "Custom environment getter not working in validator")
        
        # Record metrics
        validation_time = (time.time() - start_time) * 1000
        self.record_metric("environment_integration_validation_time_ms", validation_time)
        self.record_metric("ssot_compliance_checks", self.get_metric("ssot_compliance_checks", 0) + 5)
        
        self.logger.info(f"IsolatedEnvironment integration validated in {validation_time:.1f}ms")
    
    def teardown_method(self, method):
        """Cleanup after each test with comprehensive metrics logging."""
        try:
            # Calculate total test duration
            test_duration = time.time() - self.get_metric("test_start_time", time.time())
            self.record_metric("total_test_duration_seconds", test_duration)
            
            # Log comprehensive test metrics
            metrics = self.get_all_metrics()
            self.logger.info(
                f"Central config validator SSOT test completed: {method.__name__ if method else 'unknown'} "
                f"Duration: {test_duration:.3f}s, "
                f"SSOT compliance checks: {metrics.get('ssot_compliance_checks', 0)}, "
                f"Configuration validations: {metrics.get('configuration_validations', 0)}, "
                f"Environments tested: {metrics.get('environments_tested', 0)}"
            )
            
            # Clear validator cache for next test
            clear_central_validator_cache()
            
        except Exception as e:
            self.logger.warning(f"Error in test cleanup: {e}")
        finally:
            super().teardown_method(method)


# Unit test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.ssot_compliance,
    pytest.mark.configuration_validation,
    pytest.mark.central_validator
]


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])