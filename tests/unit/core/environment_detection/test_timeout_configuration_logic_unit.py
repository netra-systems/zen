"""
Unit tests for environment-aware timeout configuration logic - Issue #586.

Tests the timeout calculation and optimization logic for different environments
that enables WebSocket race condition prevention with environment-specific performance.

Business Value Justification (BVJ):
- Segment: Platform/All Users
- Business Goal: Performance Optimization & Platform Reliability
- Value Impact: Validates performance optimizations that improve user experience 
  (up to 97% faster in dev) while maintaining $500K+ ARR protection
- Strategic Impact: Environment-aware timeout optimization provides optimal performance
  per deployment context without compromising race condition prevention

This test suite validates:
1. Environment-specific timeout multiplier calculations (0.3x dev, 0.7x staging, 1.0x prod)
2. Cloud Run minimum safety timeout enforcement (>= 0.5s)  
3. Performance optimization effectiveness across environments
4. Safety guarantee preservation for WebSocket race condition prevention
"""

import pytest
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    create_gcp_websocket_validator
)


class TestTimeoutConfigurationLogic(SSotBaseTestCase):
    """
    Test timeout configuration calculations for environment optimization.
    
    These tests validate the environment-aware timeout calculation logic that
    enables performance optimization while maintaining WebSocket race condition protection.
    """
    
    def setup_method(self, method):
        """Set up test environment with timeout configuration testing context."""
        super().setup_method(method)
        self.record_metric("test_category", "timeout_configuration_unit")
        
        # Clear environment variables that affect timeout configuration
        env_vars_to_clear = [
            "ENVIRONMENT", "K_SERVICE", "K_REVISION", "TESTING"
        ]
        for var in env_vars_to_clear:
            if self.get_env_var(var):
                self.delete_env_var(var)
        
        # Create mock app_state for validator testing
        self.mock_app_state = MagicMock()
        self.mock_app_state.startup_phase = "services"
    
    def test_development_timeout_optimization(self):
        """
        Test aggressive timeout optimization for development environment.
        
        CRITICAL: This test validates the 0.3x timeout multiplier that provides
        very fast feedback in development (up to 70% faster connections).
        
        Should initially fail if development optimization not implemented correctly.
        """
        # Set up development environment
        with self.temp_env_vars(ENVIRONMENT="development"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Test development environment detection
            self.assertEqual(
                validator.environment,
                "development", 
                "Failed to detect development environment for timeout optimization"
            )
            
            # Test timeout multiplier for development (should be 0.3x)
            base_timeout = 10.0
            optimized_timeout = validator._get_optimized_timeout(base_timeout)
            
            # Development should use 0.3x multiplier with no safety margin (1.0x) 
            expected_timeout = base_timeout * 0.3 * 1.0  # = 3.0s
            self.assertAlmostEqual(
                optimized_timeout,
                expected_timeout,
                delta=0.1,
                msg=f"Development timeout optimization incorrect: expected ~{expected_timeout}, got {optimized_timeout}"
            )
            
            # Test that development uses very fast max timeout
            self.assertLessEqual(
                optimized_timeout,
                validator.max_total_timeout,  # Should be 3.0s for development
                "Development timeout should respect fast max timeout limit"
            )
            
            self.record_metric("development_timeout_multiplier", validator.timeout_multiplier)
            self.record_metric("development_optimized_timeout", optimized_timeout)
            self.record_metric("development_max_timeout", validator.max_total_timeout)
    
    def test_staging_timeout_balance(self):
        """
        Test balanced timeout configuration for staging environment.
        
        CRITICAL: This test validates the 0.7x timeout multiplier that balances
        speed and safety in staging (30% faster than production).
        
        Should initially fail if staging balance not implemented correctly.
        """
        # Set up staging environment with Cloud Run
        with self.temp_env_vars(ENVIRONMENT="staging", K_SERVICE="netra-backend-staging"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Test staging environment detection
            self.assertEqual(
                validator.environment,
                "staging",
                "Failed to detect staging environment for timeout optimization"
            )
            
            # Test that staging is recognized as GCP environment
            self.assertTrue(
                validator.is_gcp_environment,
                "Staging should be recognized as GCP environment"
            )
            
            # Test timeout multiplier for staging (should be 0.7x)
            base_timeout = 10.0
            optimized_timeout = validator._get_optimized_timeout(base_timeout)
            
            # Staging should use 0.7x multiplier with 10% safety margin (1.1x)
            expected_timeout = base_timeout * 0.7 * 1.1  # = 7.7s
            self.assertAlmostEqual(
                optimized_timeout,
                expected_timeout,
                delta=0.1,
                msg=f"Staging timeout optimization incorrect: expected ~{expected_timeout}, got {optimized_timeout}"
            )
            
            # Test that staging uses balanced max timeout
            self.assertEqual(
                validator.max_total_timeout,
                5.0,  # Staging max timeout
                "Staging should use balanced max timeout"
            )
            
            self.record_metric("staging_timeout_multiplier", validator.timeout_multiplier)
            self.record_metric("staging_safety_margin", validator.safety_margin)
            self.record_metric("staging_optimized_timeout", optimized_timeout)
    
    def test_production_timeout_safety(self):
        """
        Test conservative timeout configuration for production environment.
        
        CRITICAL: This test validates the 1.0x timeout multiplier that prioritizes
        reliability and safety in production (baseline performance).
        
        Should initially fail if production safety configuration incomplete.
        """
        # Set up production environment with Cloud Run
        with self.temp_env_vars(ENVIRONMENT="production", K_SERVICE="netra-backend-prod"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Test production environment detection
            self.assertEqual(
                validator.environment,
                "production",
                "Failed to detect production environment for timeout configuration"
            )
            
            # Test that production is recognized as GCP environment
            self.assertTrue(
                validator.is_gcp_environment,
                "Production should be recognized as GCP environment"
            )
            
            # Test timeout multiplier for production (should be 1.0x)
            base_timeout = 10.0
            optimized_timeout = validator._get_optimized_timeout(base_timeout)
            
            # Production should use 1.0x multiplier with 20% safety margin (1.2x)
            expected_timeout = base_timeout * 1.0 * 1.2  # = 12.0s
            self.assertAlmostEqual(
                optimized_timeout,
                expected_timeout,
                delta=0.1,
                msg=f"Production timeout should prioritize safety: expected ~{expected_timeout}, got {optimized_timeout}"
            )
            
            # Test that production uses conservative max timeout
            self.assertEqual(
                validator.max_total_timeout,
                8.0,  # Production max timeout
                "Production should use conservative max timeout"
            )
            
            self.record_metric("production_timeout_multiplier", validator.timeout_multiplier)
            self.record_metric("production_safety_margin", validator.safety_margin)
            self.record_metric("production_optimized_timeout", optimized_timeout)
    
    def test_cloud_run_minimum_safety_timeout(self):
        """
        Test minimum timeout enforcement for Cloud Run race condition protection.
        
        CRITICAL: This test validates that Cloud Run environments always maintain
        >= 0.5s minimum timeout to prevent WebSocket race conditions regardless
        of environment optimization settings.
        
        Should initially fail if minimum safety timeout not enforced.
        """
        # Test with very aggressive optimization that could go below safety minimum
        with self.temp_env_vars(ENVIRONMENT="development", K_SERVICE="test-service"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Verify this is detected as Cloud Run
            self.assertTrue(
                validator.is_cloud_run,
                "Should detect Cloud Run environment for minimum safety testing"
            )
            
            # Test with very small base timeout that would optimize to below safety minimum
            very_small_base_timeout = 0.1  # 100ms base
            optimized_timeout = validator._get_optimized_timeout(very_small_base_timeout)
            
            # Should be enforced to at least 0.5s for Cloud Run safety
            self.assertGreaterEqual(
                optimized_timeout,
                0.5,
                f"Cloud Run minimum safety timeout not enforced: got {optimized_timeout}s, expected >= 0.5s"
            )
            
            # Verify the minimum is actually being applied
            expected_before_minimum = very_small_base_timeout * validator.timeout_multiplier * validator.safety_margin
            if expected_before_minimum < 0.5:
                self.assertEqual(
                    optimized_timeout,
                    0.5,
                    "Minimum timeout should be exactly 0.5s when optimization would go below"
                )
            
            self.record_metric("cloud_run_min_timeout_enforced", optimized_timeout)
            self.record_metric("cloud_run_safety_minimum", validator.min_cloud_run_timeout)
        
        # Test that non-Cloud Run environments don't have minimum timeout restriction
        with self.temp_env_vars(ENVIRONMENT="development"):  # No K_SERVICE
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Verify this is NOT detected as Cloud Run
            self.assertFalse(
                validator.is_cloud_run,
                "Should not detect Cloud Run without K_SERVICE"
            )
            
            # Test with small base timeout - should optimize normally without minimum
            small_base_timeout = 0.1
            optimized_timeout = validator._get_optimized_timeout(small_base_timeout)
            
            # Should follow normal optimization without minimum enforcement
            expected_timeout = small_base_timeout * validator.timeout_multiplier * validator.safety_margin
            self.assertAlmostEqual(
                optimized_timeout,
                expected_timeout,
                delta=0.01,
                msg=f"Non-Cloud Run timeout should not have minimum enforcement: expected {expected_timeout}, got {optimized_timeout}"
            )
            
            self.record_metric("non_cloud_run_no_minimum", optimized_timeout)
    
    def test_timeout_multiplier_calculation_accuracy(self):
        """
        Test timeout multiplier calculation accuracy across different base values.
        
        CRITICAL: This test validates mathematical accuracy of timeout calculations
        ensures consistent behavior across different timeout base values.
        
        Should initially fail if calculation logic has mathematical errors.
        """
        test_cases = [
            # (environment, expected_multiplier, expected_safety_margin, expected_max)
            ("development", 0.3, 1.0, 3.0),
            ("staging", 0.7, 1.1, 5.0), 
            ("production", 1.0, 1.2, 8.0),
            ("testing", 0.3, 1.0, 2.0),  # Testing uses very fast settings
        ]
        
        base_timeouts = [0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0]
        
        for env_name, expected_multiplier, expected_safety, expected_max in test_cases:
            with self.temp_env_vars(ENVIRONMENT=env_name):
                validator = create_gcp_websocket_validator(self.mock_app_state)
                
                # Verify configuration values
                self.assertAlmostEqual(
                    validator.timeout_multiplier,
                    expected_multiplier,
                    delta=0.01,
                    msg=f"Environment {env_name} should have multiplier {expected_multiplier}, got {validator.timeout_multiplier}"
                )
                
                self.assertAlmostEqual(
                    validator.safety_margin,
                    expected_safety,
                    delta=0.01,
                    msg=f"Environment {env_name} should have safety margin {expected_safety}, got {validator.safety_margin}"
                )
                
                self.assertEqual(
                    validator.max_total_timeout,
                    expected_max,
                    msg=f"Environment {env_name} should have max timeout {expected_max}, got {validator.max_total_timeout}"
                )
                
                # Test calculations across different base timeouts
                for base_timeout in base_timeouts:
                    optimized_timeout = validator._get_optimized_timeout(base_timeout)
                    
                    # Calculate expected result
                    expected_calc = base_timeout * expected_multiplier * expected_safety
                    expected_result = min(expected_calc, expected_max)
                    
                    # For non-Cloud Run environments, no minimum enforcement
                    # For Cloud Run environments, enforce 0.5s minimum
                    if validator.is_cloud_run:
                        expected_result = max(expected_result, 0.5)
                    
                    self.assertAlmostEqual(
                        optimized_timeout,
                        expected_result,
                        delta=0.01,
                        msg=f"Environment {env_name}, base {base_timeout}s: expected {expected_result}s, got {optimized_timeout}s"
                    )
                    
                    # Record calculation accuracy for analysis
                    self.record_metric(f"{env_name}_base_{base_timeout}_accuracy", abs(optimized_timeout - expected_result))
    
    def test_service_specific_timeout_optimization(self):
        """
        Test service-specific timeout optimization uses environment-aware configuration.
        
        CRITICAL: This test validates that individual service readiness checks
        (database, Redis, auth, etc.) use environment-optimized timeout values.
        
        Should initially fail if service-specific timeouts don't reflect environment optimization.
        """
        # Test staging environment service timeouts
        with self.temp_env_vars(ENVIRONMENT="staging", K_SERVICE="staging-service"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Verify service readiness checks have environment-appropriate timeouts
            service_checks = validator.readiness_checks
            
            # Database should use staging timeout (3.0s for GCP staging)
            database_check = service_checks.get("database")
            self.assertIsNotNone(database_check, "Database readiness check should be configured")
            self.assertEqual(
                database_check.timeout_seconds,
                3.0,  # Staging GCP timeout for database
                f"Database timeout should be optimized for staging: expected 3.0s, got {database_check.timeout_seconds}s"
            )
            
            # Redis should use staging timeout (1.5s for GCP staging) 
            redis_check = service_checks.get("redis")
            self.assertIsNotNone(redis_check, "Redis readiness check should be configured")
            self.assertEqual(
                redis_check.timeout_seconds,
                1.5,  # Staging GCP timeout for Redis
                f"Redis timeout should be optimized for staging: expected 1.5s, got {redis_check.timeout_seconds}s"
            )
            
            # Agent supervisor should use staging timeout (2.0s for GCP staging)
            agent_check = service_checks.get("agent_supervisor")
            self.assertIsNotNone(agent_check, "Agent supervisor readiness check should be configured")
            self.assertEqual(
                agent_check.timeout_seconds,
                2.0,  # Staging GCP timeout for agent supervisor
                f"Agent supervisor timeout should be optimized for staging: expected 2.0s, got {agent_check.timeout_seconds}s"
            )
            
            self.record_metric("staging_service_timeout_optimization", "verified")
        
        # Test development environment service timeouts (non-GCP)
        with self.temp_env_vars(ENVIRONMENT="development"):  # No K_SERVICE = non-GCP
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Verify service readiness checks use development (non-GCP) timeouts
            service_checks = validator.readiness_checks
            
            # Database should use development timeout (5.0s for non-GCP)
            database_check = service_checks.get("database")
            self.assertEqual(
                database_check.timeout_seconds,
                5.0,  # Non-GCP timeout for database
                f"Database timeout should use non-GCP setting for development: expected 5.0s, got {database_check.timeout_seconds}s"
            )
            
            # Redis should use development timeout (3.0s for non-GCP)
            redis_check = service_checks.get("redis")
            self.assertEqual(
                redis_check.timeout_seconds,
                3.0,  # Non-GCP timeout for Redis
                f"Redis timeout should use non-GCP setting for development: expected 3.0s, got {redis_check.timeout_seconds}s"
            )
            
            self.record_metric("development_service_timeout_configuration", "verified")
    
    def test_environment_configuration_update_behavior(self):
        """
        Test environment configuration update and service check re-registration.
        
        CRITICAL: This test validates that timeout configuration correctly updates
        when environment is changed, ensuring tests can properly override environments.
        
        Should initially fail if environment update doesn't re-configure timeouts.
        """
        # Start with development environment
        with self.temp_env_vars(ENVIRONMENT="development"):
            validator = create_gcp_websocket_validator(self.mock_app_state)
            
            # Record initial configuration  
            initial_multiplier = validator.timeout_multiplier
            initial_service_timeout = validator.readiness_checks["database"].timeout_seconds
            
            self.assertEqual(initial_multiplier, 0.3, "Should start with development multiplier")
            
            # Update environment configuration to staging
            validator.update_environment_configuration("staging", True)  # is_gcp=True
            
            # Verify configuration updated
            self.assertEqual(
                validator.environment,
                "staging",
                "Environment should update to staging"
            )
            
            self.assertTrue(
                validator.is_gcp_environment,
                "Should recognize as GCP environment after update"
            )
            
            # Verify timeout multiplier updated
            updated_multiplier = validator.timeout_multiplier
            self.assertNotEqual(
                updated_multiplier,
                initial_multiplier,
                "Timeout multiplier should change when environment updated"
            )
            
            # Verify service checks re-registered with new timeouts
            updated_service_timeout = validator.readiness_checks["database"].timeout_seconds
            self.assertNotEqual(
                updated_service_timeout,
                initial_service_timeout,
                "Service timeout should update when environment configuration changes"
            )
            
            self.record_metric("environment_update_multiplier_change", updated_multiplier - initial_multiplier)
            self.record_metric("environment_update_service_timeout_change", updated_service_timeout - initial_service_timeout)
    
    def teardown_method(self, method):
        """Clean up test environment and record timeout optimization metrics."""
        # Record test completion and performance metrics
        execution_time = self.get_metrics().execution_time
        self.record_metric("test_execution_time", execution_time)
        
        # Analyze timeout calculation performance if needed
        metrics = self.get_all_metrics()
        calculation_metrics = {k: v for k, v in metrics.items() if "accuracy" in k}
        if calculation_metrics:
            max_error = max(calculation_metrics.values())
            self.record_metric("max_calculation_error", max_error)
            if max_error > 0.1:  # Log if calculation errors are significant
                print(f"ACCURACY WARNING: Maximum calculation error: {max_error:.4f}s")
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Allow running individual test file for debugging
    pytest.main([__file__, "-v", "--tb=short"])