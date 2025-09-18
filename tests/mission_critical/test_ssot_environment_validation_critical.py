#!/usr/bin/env python3
"""
"""
MISSION CRITICAL: SSOT Environment Validation Tests

"""
"""
PURPOSE: Prevent revenue loss from configuration errors by validating SSOT compliance
         in environment management and configuration validation patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Goal: System Stability & Revenue Protection  
- Value Impact: Prevents $500K+ ARR loss from configuration cascade failures
- Revenue Impact: Critical infrastructure tests protecting Golden Path user flow

CRITICAL REQUIREMENTS:
1. Tests MUST fail when SSOT violations exist in environment management
2. Tests MUST validate that startup integration works properly
3. Tests MUST catch configuration errors that could cause revenue loss
4. Tests MUST use real test framework patterns (no mocks for integration parts)
5. Tests MUST validate Central Configuration Validator SSOT compliance

ARCHITECTURE INTEGRATION:
- Uses test_framework.ssot.base_test_case for SSOT compliance
- Validates shared.configuration.central_config_validator SSOT patterns
- Tests environment isolation via shared.isolated_environment
- Validates startup integration via netra_backend.app.core.startup_validator
"
"

import pytest
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from unittest.mock import patch, MagicMock

# SSOT Test Framework Imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SsotTestMetrics

# Central SSOT Validator Import
from shared.configuration.central_config_validator import ()
    CentralConfigurationValidator,
    get_central_validator,
    validate_platform_configuration,
    Environment,
    ConfigRequirement,
    ConfigRule,
    clear_central_validator_cache
)

# Environment Management Imports
from shared.isolated_environment import IsolatedEnvironment, get_env

# Backend Configuration Validator
from netra_backend.app.core.configuration.validator import ConfigurationValidator

# Startup Validator
from netra_backend.app.core.startup_validator import StartupValidator


@dataclass
class SsotValidationResult:
    "SSOT compliance validation result."
    component: str
    is_compliant: bool
    violations: List[str]
    critical_issues: List[str]
    environment_consistency: bool
    validation_time_ms: float


class TestSsotEnvironmentValidationCritical(SSotAsyncTestCase):
    """
    Mission-critical tests for SSOT environment validation.
    
    These tests protect the Golden Path by ensuring configuration validation
    maintains SSOT compliance and prevents revenue-threatening cascade failures.
    
    
    @classmethod
    def setup_class(cls):
        ""Class-level setup for mission-critical SSOT validation tests."
        super().setup_class()
        cls.logger.info(Initializing mission-critical SSOT environment validation tests)"
        cls.logger.info(Initializing mission-critical SSOT environment validation tests)"
        cls._test_environments = [development", staging, production, test]"
        cls._critical_config_keys = [
            JWT_SECRET_STAGING", JWT_SECRET_PRODUCTION, JWT_SECRET_KEY,"
            POSTGRES_PASSWORD, POSTGRES_HOST", REDIS_PASSWORD, REDIS_HOST,"
            GEMINI_API_KEY, SERVICE_SECRET, "FERNET_KEY"
        ]
    
    def setup_method(self, method):
        Setup for each SSOT validation test."
        Setup for each SSOT validation test."
        super().setup_method(method)
        
        # Clear any cached validator state to ensure clean test environment
        clear_central_validator_cache()
        
        # Initialize test metrics for business value tracking
        self.record_metric("test_start_time, time.time())"
        self.record_metric(critical_validations_performed, 0)
        self.record_metric("ssot_violations_detected, 0)"
        self.record_metric(revenue_protection_checks, 0)
    
    def test_central_validator_ssot_compliance(self):
    """
        CRITICAL: Validate Central Configuration Validator SSOT compliance.
        
        This test ensures the central validator maintains SSOT patterns and
        prevents duplicate validation logic that could cause configuration drift.
        
        BUSINESS IMPACT: Prevents configuration errors that could cause $500K+ ARR loss.
        
        start_time = time.time()
        validation_errors = []
        
        try:
            # Test 1: Verify singleton pattern (SSOT requirement)
            validator1 = get_central_validator()
            validator2 = get_central_validator()
            
            if validator1 is not validator2:
                validation_errors.append(Central validator not using singleton pattern - SSOT violation)"
                validation_errors.append(Central validator not using singleton pattern - SSOT violation)"
            
            # Test 2: Verify environment detection consistency
            with self.temp_env_vars(ENVIRONMENT="staging):"
                env1 = validator1.get_environment()
                env2 = validator2.get_environment()
                
                if env1 != env2:
                    validation_errors.append(fEnvironment detection inconsistent: {env1} != {env2})
                
                if env1 != Environment.STAGING:
                    validation_errors.append(f"Environment detection failed: expected STAGING, got {env1})"
            
            # Test 3: Validate configuration rules are comprehensive
            required_environments = {Environment.STAGING, Environment.PRODUCTION, Environment.DEVELOPMENT, Environment.TEST}
            environments_covered = set()
            
            for rule in validator1.CONFIGURATION_RULES:
                environments_covered.update(rule.environments)
            
            missing_envs = required_environments - environments_covered
            if missing_envs:
                validation_errors.append(fConfiguration rules missing for environments: {missing_envs}")"
            
            # Test 4: Verify critical secrets have proper validation (deployment pattern aware)
            critical_vars = [JWT_SECRET_STAGING, JWT_SECRET_PRODUCTION, "REDIS_PASSWORD]"
            postgres_vars = [POSTGRES_PASSWORD]  # Special handling for deployment pattern detection
            rules_by_var = {rule.env_var: rule for rule in validator1.CONFIGURATION_RULES}
            
            # Check standard critical variables
            for var in critical_vars:
                if var not in rules_by_var:
                    validation_errors.append(fCritical variable {var} missing from validation rules)
                elif rules_by_var[var].requirement not in [ConfigRequirement.REQUIRED, ConfigRequirement.REQUIRED_SECURE]:
                    validation_errors.append(fCritical variable {var} not marked as required/secure")"
            
            # Check POSTGRES_PASSWORD with deployment pattern awareness
            for var in postgres_vars:
                if var not in rules_by_var:
                    validation_errors.append(fCritical variable {var} missing from validation rules)
                elif rules_by_var[var].requirement not in [ConfigRequirement.REQUIRED, ConfigRequirement.REQUIRED_SECURE, ConfigRequirement.OPTIONAL]:
                    validation_errors.append(fDatabase variable {var} must be REQUIRED, REQUIRED_SECURE, or OPTIONAL for deployment pattern flexibility)
                # POSTGRES_PASSWORD can be OPTIONAL for DATABASE_URL deployments, so this is acceptable
            
            # Test 5: Verify no dangerous defaults exist
            with self.temp_env_vars(ENVIRONMENT="production):"
                clear_central_validator_cache()
                validator = get_central_validator()
                
                # Clear all critical environment variables
                critical_vars_to_clear = [
                    JWT_SECRET_PRODUCTION, POSTGRES_PASSWORD, REDIS_PASSWORD, "
                    JWT_SECRET_PRODUCTION, POSTGRES_PASSWORD, REDIS_PASSWORD, "
                    "SERVICE_SECRET, FERNET_KEY, GEMINI_API_KEY"
                ]
                
                original_values = {}
                for var in critical_vars_to_clear:
                    original_values[var] = self.get_env_var(var)
                    self.delete_env_var(var)
                
                try:
                    # Should fail hard - no dangerous defaults allowed
                    validator.validate_all_requirements()
                    validation_errors.append(Central validator allowed missing critical secrets in production - DANGEROUS")"
                except ValueError as e:
                    # Expected behavior - validator should fail hard
                    error_msg = str(e)
                    if required not in error_msg.lower():
                        validation_errors.append(fCentral validator error message unclear: {error_msg})"
                        validation_errors.append(fCentral validator error message unclear: {error_msg})"
                except Exception as e:
                    validation_errors.append(f"Unexpected exception type from central validator: {type(e).__name__}: {e})"
                finally:
                    # Restore original values
                    for var, value in original_values.items():
                        if value is not None:
                            self.set_env_var(var, value)
            
            # Record metrics
            validation_time = (time.time() - start_time) * 1000
            self.record_metric(central_validator_validation_time_ms, validation_time)
            self.record_metric(critical_validations_performed, 5)"
            self.record_metric(critical_validations_performed, 5)"
            
            if validation_errors:
                self.record_metric(ssot_violations_detected", len(validation_errors))"
                self.fail(fCentral Configuration Validator SSOT compliance failed:\n + 
                         \n.join(f"  - {error} for error in validation_errors))"
            
            self.logger.info(fCentral validator SSOT compliance validated in {validation_time:.1f}ms)"
            self.logger.info(fCentral validator SSOT compliance validated in {validation_time:.1f}ms)"
            
        except Exception as e:
            self.record_metric(ssot_validation_critical_error, 1)
            self.fail(fCritical error in central validator SSOT compliance test: {e})"
            self.fail(fCritical error in central validator SSOT compliance test: {e})"
    
    def test_environment_isolation_ssot_consistency(self):
        """
    "
        CRITICAL: Validate environment isolation maintains SSOT consistency.
        
        This test ensures IsolatedEnvironment maintains consistent state and
        prevents environment variable leakage that could cause security issues.
        "
        "
        validation_errors = []
        start_time = time.time()
        
        try:
            # Test 1: Verify environment isolation works correctly
            original_test_var = self.get_env_var(TEST_ISOLATION_VAR")"
            
            # Set test variable in isolation
            self.set_env_var(TEST_ISOLATION_VAR, test_value_1)
            
            # Create new environment instance and verify isolation
            new_env = get_env()
            if new_env.get("TEST_ISOLATION_VAR) != test_value_1:"
                validation_errors.append(Environment isolation not working - variables not accessible)
            
            # Test 2: Verify environment changes don't leak between tests'
            with self.temp_env_vars(TEST_TEMP_VAR=temp_value):"
            with self.temp_env_vars(TEST_TEMP_VAR=temp_value):"
                if self.get_env_var("TEST_TEMP_VAR) != temp_value:"
                    validation_errors.append(Temporary environment variables not working)
            
            # After context manager, temp var should be gone
            if self.get_env_var(TEST_TEMP_VAR") is not None:"
                validation_errors.append(Temporary environment variables not cleaned up - memory leak risk)
            
            # Test 3: Verify environment detection consistency across validators
            env_consistency_errors = self._test_environment_consistency()
            validation_errors.extend(env_consistency_errors)
            
            # Test 4: Verify environment variable validation patterns
            ssot_pattern_errors = self._test_ssot_env_patterns()
            validation_errors.extend(ssot_pattern_errors)
            
            # Record metrics
            validation_time = (time.time() - start_time) * 1000
            self.record_metric(environment_isolation_validation_time_ms, validation_time)"
            self.record_metric(environment_isolation_validation_time_ms, validation_time)"
            self.record_metric("revenue_protection_checks, 4)"
            
            if validation_errors:
                self.record_metric(environment_isolation_violations, len(validation_errors))
                self.fail(f"Environment isolation SSOT consistency failed:\n +"
                         \n".join(f  - {error} for error in validation_errors))"
            
            self.logger.info(fEnvironment isolation SSOT consistency validated in {validation_time:.1f}ms)
            
        except Exception as e:
            self.record_metric(environment_isolation_critical_error, 1)"
            self.record_metric(environment_isolation_critical_error, 1)"
            self.fail(fCritical error in environment isolation SSOT test: {e}")"
        finally:
            # Cleanup
            if original_test_var is not None:
                self.set_env_var(TEST_ISOLATION_VAR, original_test_var)
            else:
                self.delete_env_var(TEST_ISOLATION_VAR")"
    
    def test_startup_validator_ssot_integration(self):
        pass
        CRITICAL: Validate startup validator integrates with SSOT configuration patterns.
        
        This test ensures startup validation properly uses SSOT validators and
        prevents startup with invalid configurations that could cause revenue loss.
        ""
        validation_errors = []
        start_time = time.time()
        
        try:
            # Test 1: Verify startup validator uses SSOT patterns
            startup_validator = StartupValidator()
            
            # Test configuration validation integration
            config_validation_result = startup_validator._validate_configuration()
            if not config_validation_result[0]:  # success, message format
                validation_errors.append(fStartup validator configuration check failed: {config_validation_result[1]})
            
            # Test 2: Verify startup validator catches critical configuration issues
            with self.temp_env_vars(ENVIRONMENT=staging):"
            with self.temp_env_vars(ENVIRONMENT=staging):"
                # Clear critical configuration
                with self.temp_env_vars(JWT_SECRET_STAGING="):"
                    try:
                        # Create new validator to test startup integration
                        test_validator = get_central_validator()
                        clear_central_validator_cache()
                        
                        # This should fail due to missing JWT secret
                        test_validator.validate_startup_requirements()
                        validation_errors.append(Startup validator allowed missing JWT secret in staging)
                    except ValueError:
                        # Expected - startup should fail with missing critical config
                        pass
                    except Exception as e:
                        validation_errors.append(fUnexpected startup validation error: {e}")"
            
            # Test 3: Verify import integrity validation
            import_result = startup_validator._validate_imports()
            if not import_result[0]:
                validation_errors.append(fStartup validator import check failed: {import_result[1]})
            
            # Test 4: Verify method signature validation  
            signature_result = startup_validator._validate_method_signatures()
            if not signature_result[0]:
                validation_errors.append(fStartup validator signature check failed: {signature_result[1]})
            
            # Record metrics
            validation_time = (time.time() - start_time) * 1000
            self.record_metric("startup_validator_validation_time_ms, validation_time)"
            self.record_metric(critical_validations_performed, self.get_metric(critical_validations_performed, 0) + 4)
            
            if validation_errors:
                self.record_metric(startup_validator_violations, len(validation_errors))"
                self.record_metric(startup_validator_violations, len(validation_errors))"
                self.fail(f"Startup validator SSOT integration failed:\n +"
                         \n.join(f  - {error} for error in validation_errors))
            
            self.logger.info(fStartup validator SSOT integration validated in {validation_time:.1f}ms)
            
        except Exception as e:
            self.record_metric("startup_validator_critical_error, 1)"
            self.fail(fCritical error in startup validator SSOT integration test: {e})
    
    def test_backend_configuration_validator_ssot_compliance(self):
    """
        CRITICAL: Validate backend configuration validator SSOT compliance.
        
        This test ensures the backend's ConfigurationValidator properly delegates'
        to the central SSOT validator and doesn't duplicate validation logic.'
        
        validation_errors = []
        start_time = time.time()
        
        try:
            # Test 1: Verify backend validator exists and can be instantiated
            try:
                backend_validator = ConfigurationValidator()
            except Exception as e:
                validation_errors.append(fBackend ConfigurationValidator instantiation failed: {e})"
                validation_errors.append(fBackend ConfigurationValidator instantiation failed: {e})"
                # Early return if we can't even create the validator'
                self.fail(f"Backend ConfigurationValidator critical instantiation failure: {e})"
                return
            
            # Test 2: Verify backend validator has proper environment detection
            backend_env = backend_validator._get_environment()
            if backend_env not in [development, testing, staging, "production]:"
                validation_errors.append(fBackend validator returned invalid environment: {backend_env}")"
            
            # Test 3: Verify backend validator uses SSOT configuration patterns
            validation_rules = backend_validator._validation_rules
            if not validation_rules:
                validation_errors.append(Backend validator has no validation rules - SSOT violation)
            
            # Test 4: Test environment variable validation without creating config objects
            env_dict = {
                ENVIRONMENT": test,"
                JWT_SECRET_KEY: test-secret-32-characters-long-123456
            }
            
            env_validation_result = backend_validator.validate_environment_variables(env_dict)
            if not env_validation_result.is_valid:
                # Check if failures are reasonable
                for error in env_validation_result.errors:
                    if JWT_SECRET_KEY in error:"
                    if JWT_SECRET_KEY in error:"
                        validation_errors.append(f"Backend validator improperly rejected valid test environment: {error})"
            
            # Test 5: Test production environment validation (should be strict)
            prod_env_dict = {
                ENVIRONMENT: production
                # Missing critical variables intentionally
            }
            
            prod_validation_result = backend_validator.validate_environment_variables(prod_env_dict)
            if prod_validation_result.is_valid:
                validation_errors.append(Backend validator improperly allowed missing production variables)"
                validation_errors.append(Backend validator improperly allowed missing production variables)"
            
            # Record metrics
            validation_time = (time.time() - start_time) * 1000
            self.record_metric("backend_validator_validation_time_ms, validation_time)"
            self.record_metric(critical_validations_performed, self.get_metric(critical_validations_performed, 0) + 5)
            
            if validation_errors:
                self.record_metric(backend_validator_violations", len(validation_errors))"
                self.fail(fBackend configuration validator SSOT compliance failed:\n + 
                         \n.join(f  - {error} for error in validation_errors))
            
            self.logger.info(fBackend configuration validator SSOT compliance validated in {validation_time:.1f}ms)"
            self.logger.info(fBackend configuration validator SSOT compliance validated in {validation_time:.1f}ms)"
            
        except Exception as e:
            self.record_metric("backend_validator_critical_error, 1)"
            self.fail(fCritical error in backend configuration validator SSOT test: {e})
    
    def test_cross_environment_validation_consistency(self):
    """
        CRITICAL: Validate cross-environment validation consistency.
        
        This test ensures validation behavior is consistent across all environments
        and prevents environment-specific configuration drift.
        
        validation_errors = []
        start_time = time.time()
        environments_tested = 0
        
        try:
            for env_name in self._test_environments:
                environments_tested += 1
                
                with self.temp_env_vars(ENVIRONMENT=env_name):
                    clear_central_validator_cache()
                    validator = get_central_validator()
                    
                    try:
                        detected_env = validator.get_environment()
                        
                        # Map environment names to expected enum values
                        expected_env_mapping = {
                            development": Environment.DEVELOPMENT,"
                            testing: Environment.TEST,
                            staging: Environment.STAGING,"
                            staging: Environment.STAGING,"
                            "production: Environment.PRODUCTION"
                        }
                        
                        expected_env = expected_env_mapping.get(env_name)
                        if detected_env != expected_env:
                            validation_errors.append(
                                fEnvironment detection inconsistent for {env_name}: 
                                f"expected {expected_env}, got {detected_env}"
                            )
                        
                        # Test environment-specific validation behavior
                        if env_name in [staging", production]:"
                            # Should have strict requirements
                            self._test_strict_environment_validation(validator, env_name, validation_errors)
                        else:
                            # Should allow development defaults
                            self._test_permissive_environment_validation(validator, env_name, validation_errors)
                        
                    except Exception as e:
                        validation_errors.append(fEnvironment validation failed for {env_name}: {e})
            
            # Record metrics
            validation_time = (time.time() - start_time) * 1000
            self.record_metric("cross_environment_validation_time_ms, validation_time)"
            self.record_metric(environments_validated, environments_tested)
            self.record_metric(revenue_protection_checks, self.get_metric(revenue_protection_checks", 0) + environments_tested)"
            
            if validation_errors:
                self.record_metric("cross_environment_violations, len(validation_errors))"
                self.fail(fCross-environment validation consistency failed:\n + 
                         \n.join(f  - {error}" for error in validation_errors))"
            
            self.logger.info(f"Cross-environment validation consistency validated in {validation_time:.1f}ms)"
            
        except Exception as e:
            self.record_metric(cross_environment_critical_error, 1)
            self.fail(fCritical error in cross-environment validation test: {e})
    
    # Helper methods for comprehensive validation
    
    def _test_environment_consistency(self) -> List[str]:
        ""Test environment detection consistency across validators."
        errors = []
        
        try:
            # Test consistency between different validator instances
            central_validator = get_central_validator()
            backend_validator = ConfigurationValidator()
            
            central_env = central_validator.get_environment()
            backend_env = backend_validator._get_environment()
            
            # Map environments for comparison (central uses enum, backend uses string)
            env_map = {
                Environment.DEVELOPMENT: development,"
                Environment.DEVELOPMENT: development,"
                Environment.TEST: testing","
                Environment.STAGING: staging,
                Environment.PRODUCTION: production""
            }
            
            mapped_central_env = env_map.get(central_env, str(central_env))
            if mapped_central_env != backend_env:
                errors.append(fEnvironment detection inconsistent: central={mapped_central_env}, backend={backend_env})
                
        except Exception as e:
            errors.append(fEnvironment consistency test failed: {e})
        
        return errors
    
    def _test_ssot_env_patterns(self) -> List[str]:
        "Test SSOT environment variable patterns."
        errors = []
        
        try:
            # Test that all environment access goes through IsolatedEnvironment
            env = self.get_env()
            
            # Verify it's the correct type'
            if not isinstance(env, IsolatedEnvironment):
                errors.append(fEnvironment not using IsolatedEnvironment: {type(env)})"
                errors.append(fEnvironment not using IsolatedEnvironment: {type(env)})"
            
            # Test environment variable setting and getting
            test_key = "SSOT_PATTERN_TEST"
            test_value = ssot_test_value
            
            self.set_env_var(test_key, test_value)
            retrieved_value = self.get_env_var(test_key)
            
            if retrieved_value != test_value:
                errors.append(f"Environment variable roundtrip failed: set={test_value}, got={retrieved_value})"
            
            # Cleanup
            self.delete_env_var(test_key)
            
        except Exception as e:
            errors.append(fSSOT environment pattern test failed: {e}")"
        
        return errors
    
    def _test_strict_environment_validation(self, validator: CentralConfigurationValidator, env_name: str, errors: List[str):
        Test strict validation for production/staging environments.""
        try:
            # Test that missing critical secrets cause hard failure
            original_jwt_secret = self.get_env_var(fJWT_SECRET_{env_name.upper()})
            
            # Clear critical secret
            self.delete_env_var(fJWT_SECRET_{env_name.upper()})
            
            try:
                validator.validate_all_requirements()
                errors.append(fStrict environment {env_name} allowed missing JWT secret")"
            except ValueError:
                # Expected behavior
                pass
            except Exception as e:
                errors.append(fUnexpected error in strict validation for {env_name}: {e})
            finally:
                # Restore if it existed
                if original_jwt_secret:
                    self.set_env_var(fJWT_SECRET_{env_name.upper()}, original_jwt_secret)
                    
        except Exception as e:
            errors.append(f"Strict environment validation test failed for {env_name}: {e})"
    
    def _test_permissive_environment_validation(self, validator: CentralConfigurationValidator, env_name: str, errors: List[str):
        "Test permissive validation for development/test environments."
        try:
            # Test that development/test environments allow reasonable defaults
            if env_name == "development:"
                # Should allow missing some secrets if JWT_SECRET_KEY is provided
                with self.temp_env_vars(JWT_SECRET_KEY=dev-secret-32-characters-long-for-testing):
                    try:
                        validator.validate_all_requirements()
                        # Should succeed with minimal configuration
                    except ValueError as e:
                        # Check if it's a reasonable failure'
                        if JWT_SECRET_KEY in str(e):"
                        if JWT_SECRET_KEY in str(e):"
                            errors.append(fDevelopment environment improperly rejected valid JWT_SECRET_KEY: {e}")"
                    except Exception as e:
                        errors.append(fUnexpected error in permissive validation for {env_name}: {e})
                        
        except Exception as e:
            errors.append(fPermissive environment validation test failed for {env_name}: {e})"
            errors.append(fPermissive environment validation test failed for {env_name}: {e})"
    
    def teardown_method(self, method):
        "Cleanup after each test with metrics recording."
        try:
            # Record final metrics
            test_duration = time.time() - self.get_metric(test_start_time", time.time())"
            self.record_metric(total_test_duration_seconds, test_duration)
            
            # Log test completion with metrics
            metrics = self.get_all_metrics()
            self.logger.info(
                fSSOT validation test completed: {method.__name__ if method else 'unknown'} "
                fSSOT validation test completed: {method.__name__ if method else 'unknown'} "
                f"Duration: {test_duration:.3f}s,"
                fCritical validations: {metrics.get('critical_validations_performed', 0)}, 
                fViolations detected: {metrics.get('ssot_violations_detected', 0)}, 
                fRevenue protection checks: {metrics.get('revenue_protection_checks', 0)}""
            )
            
        except Exception as e:
            self.logger.warning(fError recording test metrics: {e})
        finally:
            # Always call parent teardown
            super().teardown_method(method)


# Mission-critical test markers
pytestmark = [
    pytest.mark.mission_critical,
    pytest.mark.ssot_compliance,
    pytest.mark.environment_validation,
    pytest.mark.revenue_protection
]


if __name__ == __main__:
    # Allow running tests directly for development
    pytest.main([__file__, "-v, --tb=short)"
)))