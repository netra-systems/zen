"""
Unit tests for enhanced environment detection logic - Issue #586.

Tests the core environment detection improvements for GCP optimization and
WebSocket race condition prevention with environment-aware timeout configuration.

Business Value Justification (BVJ):
- Segment: Platform/All Users
- Business Goal: Performance Optimization & Platform Reliability  
- Value Impact: Validates environment detection accuracy critical for performance 
  optimization while maintaining $500K+ ARR protection through reliable WebSocket connections
- Strategic Impact: Environment-aware system provides optimal performance per deployment context

This test suite validates:
1. Accurate GCP Cloud Run detection via K_SERVICE environment variable
2. Staging vs production vs development environment differentiation  
3. Fallback behavior for ambiguous environment detection
4. Integration with IsolatedEnvironment SSOT patterns
"""

import pytest
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.environment_constants import (
    EnvironmentDetector,
    Environment, 
    EnvironmentVariables
)


class TestEnvironmentDetectorEnhancement(SSotBaseTestCase):
    """
    Test enhanced environment detection logic for GCP optimization.
    
    These tests validate the core environment detection logic that enables
    environment-aware timeout optimization for WebSocket race condition prevention.
    """
    
    def setup_method(self, method):
        """Set up test environment with isolated environment access."""
        super().setup_method(method)
        self.record_metric("test_category", "environment_detection_unit")
        
        # Clear any existing environment variables that might affect detection
        env_vars_to_clear = [
            "ENVIRONMENT", "TESTING", "PYTEST_CURRENT_TEST",
            "K_SERVICE", "K_REVISION", "GAE_ENV", "GAE_APPLICATION"
        ]
        for var in env_vars_to_clear:
            if self.get_env_var(var):
                self.delete_env_var(var)
    
    def test_gcp_cloud_run_detection_via_k_service(self):
        """
        Test GCP Cloud Run detection via K_SERVICE environment variable.
        
        CRITICAL: This test validates the core GCP detection logic that determines
        whether to use optimized timeout configuration for Cloud Run environments.
        
        Should initially fail if K_SERVICE detection logic is incomplete or incorrect.
        """
        # Test Case 1: K_SERVICE present indicates Cloud Run environment
        with self.temp_env_vars(K_SERVICE="netra-backend-staging"):
            # Test detection method directly
            is_cloud_run = EnvironmentDetector.is_cloud_run()
            self.assertTrue(
                is_cloud_run,
                "Failed to detect Cloud Run environment when K_SERVICE is set"
            )
            
            # Test environment detection includes Cloud Run detection
            detected_env = EnvironmentDetector.detect_cloud_environment()
            self.assertIsNotNone(
                detected_env,
                "Cloud environment detection failed when K_SERVICE present"
            )
            
            self.record_metric("k_service_detection", "success")
        
        # Test Case 2: K_SERVICE absent means not Cloud Run
        # (Environment should be cleared from setup_method)
        is_cloud_run = EnvironmentDetector.is_cloud_run() 
        self.assertFalse(
            is_cloud_run,
            "Incorrectly detected Cloud Run when K_SERVICE not set"
        )
        
        self.record_metric("non_cloud_run_detection", "success")
    
    def test_gcp_staging_environment_detection(self):
        """
        Test staging environment detection in GCP Cloud Run context.
        
        CRITICAL: This test validates staging environment detection which determines
        the 0.7x timeout multiplier for balanced performance and safety.
        
        Should initially fail if staging detection logic incomplete.
        """
        # Test Case 1: Staging service name should detect staging environment
        with self.temp_env_vars(K_SERVICE="netra-backend-staging"):
            detected_env = EnvironmentDetector.get_cloud_run_environment()
            self.assertEqual(
                detected_env,
                Environment.STAGING.value,
                f"Failed to detect staging environment from service name, got: {detected_env}"
            )
            
            self.record_metric("staging_service_detection", "success")
        
        # Test Case 2: PR-based staging detection
        with self.temp_env_vars(K_SERVICE="netra-backend-pr-123", PR_NUMBER="123"):
            detected_env = EnvironmentDetector.get_cloud_run_environment()
            self.assertEqual(
                detected_env,
                Environment.STAGING.value,
                f"Failed to detect PR-based staging environment, got: {detected_env}"
            )
            
            self.record_metric("pr_staging_detection", "success")
        
        # Test Case 3: Production service name should NOT be staging
        with self.temp_env_vars(K_SERVICE="netra-backend-prod"):
            detected_env = EnvironmentDetector.get_cloud_run_environment()
            self.assertEqual(
                detected_env,
                Environment.PRODUCTION.value,
                f"Incorrectly detected staging for production service, got: {detected_env}"
            )
            
            self.record_metric("production_service_detection", "success")
    
    def test_local_development_environment_detection(self):
        """
        Test local development environment detection.
        
        CRITICAL: This test validates development environment detection which determines
        the 0.3x timeout multiplier for very fast development feedback.
        
        Should initially fail if development detection doesn't prioritize explicit setting.
        """
        # Test Case 1: Explicit ENVIRONMENT=development should be detected
        with self.temp_env_vars(ENVIRONMENT="development"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.DEVELOPMENT.value,
                f"Failed to detect explicit development environment, got: {detected_env}"
            )
            
            self.record_metric("explicit_development_detection", "success")
        
        # Test Case 2: No explicit environment should default to development
        # (All environment variables cleared in setup_method)
        detected_env = EnvironmentDetector.get_environment()
        self.assertEqual(
            detected_env,
            Environment.DEVELOPMENT.value,
            f"Failed to default to development environment, got: {detected_env}"
        )
        
        self.record_metric("default_development_detection", "success")
        
        # Test Case 3: Development should not be detected when in Cloud Run without explicit setting
        with self.temp_env_vars(K_SERVICE="netra-backend-staging"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertNotEqual(
                detected_env,
                Environment.DEVELOPMENT.value,
                "Incorrectly detected development in Cloud Run environment"
            )
            
            self.record_metric("cloud_run_not_development", "success")
    
    def test_production_environment_detection(self):
        """
        Test production environment detection with conservative settings.
        
        CRITICAL: This test validates production environment detection which determines
        the 1.0x timeout multiplier for maximum reliability and safety.
        
        Should initially fail if production detection logic incomplete.
        """
        # Test Case 1: Production service name in Cloud Run
        with self.temp_env_vars(K_SERVICE="netra-backend-prod"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.PRODUCTION.value,
                f"Failed to detect production environment from Cloud Run service, got: {detected_env}"
            )
            
            self.record_metric("production_cloud_run_detection", "success")
        
        # Test Case 2: Explicit ENVIRONMENT=production should override
        with self.temp_env_vars(ENVIRONMENT="production", K_SERVICE="netra-backend-staging"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.PRODUCTION.value,
                f"Explicit ENVIRONMENT=production should override Cloud Run detection, got: {detected_env}"
            )
            
            self.record_metric("explicit_production_override", "success")
        
        # Test Case 3: Kubernetes should default to production
        with self.temp_env_vars(KUBERNETES_SERVICE_HOST="10.0.0.1"):
            detected_env = EnvironmentDetector.detect_cloud_environment()
            self.assertEqual(
                detected_env,
                Environment.PRODUCTION.value,
                f"Failed to detect production for Kubernetes environment, got: {detected_env}"
            )
            
            self.record_metric("kubernetes_production_detection", "success")
    
    def test_testing_environment_detection(self):
        """
        Test testing environment detection and priority handling.
        
        CRITICAL: This test validates testing environment detection which should
        bypass most optimizations for test stability and consistency.
        """
        # Test Case 1: TESTING=true should be detected
        with self.temp_env_vars(TESTING="true"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.TESTING.value,
                f"Failed to detect testing environment with TESTING=true, got: {detected_env}"
            )
            
            is_testing = EnvironmentDetector.is_testing_context()
            self.assertTrue(
                is_testing,
                "Failed to identify testing context when TESTING=true"
            )
            
            self.record_metric("testing_flag_detection", "success")
        
        # Test Case 2: PYTEST_CURRENT_TEST should indicate testing
        with self.temp_env_vars(PYTEST_CURRENT_TEST="tests/unit/test_example.py::test_function"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.TESTING.value,
                f"Failed to detect testing environment with PYTEST_CURRENT_TEST, got: {detected_env}"
            )
            
            is_testing = EnvironmentDetector.is_testing_context()
            self.assertTrue(
                is_testing,
                "Failed to identify testing context when PYTEST_CURRENT_TEST set"
            )
            
            self.record_metric("pytest_testing_detection", "success")
        
        # Test Case 3: Explicit ENVIRONMENT should override testing detection
        with self.temp_env_vars(ENVIRONMENT="staging", TESTING="true"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.STAGING.value,
                f"Explicit ENVIRONMENT should override TESTING flag, got: {detected_env}"
            )
            
            is_testing = EnvironmentDetector.is_testing_context()
            self.assertFalse(
                is_testing,
                "Testing context should be False when ENVIRONMENT explicitly overrides"
            )
            
            self.record_metric("explicit_environment_override_testing", "success")
    
    def test_environment_fallback_behavior(self):
        """
        Test fallback behavior when environment detection is ambiguous.
        
        CRITICAL: This test validates the system gracefully handles edge cases
        and provides sensible defaults that don't break functionality.
        
        Should initially fail if fallback logic incomplete or incorrect.
        """
        # Test Case 1: Invalid ENVIRONMENT value should fall back to development
        with self.temp_env_vars(ENVIRONMENT="invalid_environment"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.DEVELOPMENT.value,
                f"Invalid environment should fallback to development, got: {detected_env}"
            )
            
            self.record_metric("invalid_environment_fallback", "success")
        
        # Test Case 2: Empty ENVIRONMENT value should fall back to development
        with self.temp_env_vars(ENVIRONMENT=""):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.DEVELOPMENT.value,
                f"Empty environment should fallback to development, got: {detected_env}"
            )
            
            self.record_metric("empty_environment_fallback", "success")
        
        # Test Case 3: Unknown cloud platform should not break detection
        with self.temp_env_vars(UNKNOWN_CLOUD_VAR="some_value"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertIn(
                detected_env,
                Environment.values(),
                f"Unknown cloud platform should not break environment detection, got: {detected_env}"
            )
            
            self.record_metric("unknown_cloud_platform_handling", "success")
        
        # Test Case 4: Multiple conflicting cloud indicators should be handled gracefully
        with self.temp_env_vars(
            K_SERVICE="cloud-run-service",
            GAE_ENV="standard",
            AWS_EXECUTION_ENV="AWS_ECS_FARGATE"
        ):
            detected_env = EnvironmentDetector.get_environment()
            # Should prioritize K_SERVICE (Cloud Run) as it's checked first
            cloud_env = EnvironmentDetector.detect_cloud_environment()
            self.assertIsNotNone(
                cloud_env,
                "Multiple cloud indicators should not break detection"
            )
            
            self.record_metric("multiple_cloud_indicators_handling", "success")
    
    def test_environment_detection_priority_order(self):
        """
        Test environment detection follows correct priority order.
        
        CRITICAL: This test validates the priority order documented in the code:
        1. Explicit ENVIRONMENT variable (highest priority)
        2. Testing environment detection (TESTING variable or pytest context)  
        3. Cloud platform detection
        4. Default to development
        
        Should initially fail if priority order implementation is incorrect.
        """
        # Test Priority 1: Explicit ENVIRONMENT should override everything
        with self.temp_env_vars(
            ENVIRONMENT="production",
            TESTING="true", 
            PYTEST_CURRENT_TEST="test_example.py::test_func",
            K_SERVICE="staging-service"
        ):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.PRODUCTION.value,
                "Explicit ENVIRONMENT should have highest priority"
            )
            
            self.record_metric("priority_1_explicit_environment", "success")
        
        # Test Priority 2: Testing detection should override cloud detection (when ENVIRONMENT not set)
        with self.temp_env_vars(
            TESTING="true",
            K_SERVICE="production-service"
        ):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.TESTING.value,
                "Testing detection should override cloud detection when ENVIRONMENT not set"
            )
            
            self.record_metric("priority_2_testing_over_cloud", "success")
        
        # Test Priority 3: Cloud detection should override default development
        with self.temp_env_vars(K_SERVICE="staging-service"):
            detected_env = EnvironmentDetector.get_environment()
            self.assertEqual(
                detected_env,
                Environment.STAGING.value,
                "Cloud detection should override default development"
            )
            
            self.record_metric("priority_3_cloud_over_default", "success")
        
        # Test Priority 4: Default to development when nothing else applies
        # (All environment variables cleared in setup_method)
        detected_env = EnvironmentDetector.get_environment()
        self.assertEqual(
            detected_env,
            Environment.DEVELOPMENT.value,
            "Should default to development when no other indicators present"
        )
        
        self.record_metric("priority_4_default_development", "success")
    
    def test_unified_config_integration_compatibility(self):
        """
        Test compatibility with unified configuration system.
        
        CRITICAL: This test validates that enhanced environment detection works
        correctly with the existing unified configuration system.
        
        Should initially fail if integration points are broken.
        """
        # Test bootstrap method behavior (used during config system initialization)
        with self.temp_env_vars(ENVIRONMENT="staging"):
            bootstrap_env = EnvironmentDetector.get_environment()
            unified_env = EnvironmentDetector.get_environment_unified()
            
            # Both methods should return the same result
            self.assertEqual(
                bootstrap_env,
                unified_env,
                f"Bootstrap and unified methods should return same result: {bootstrap_env} vs {unified_env}"
            )
            
            self.record_metric("bootstrap_unified_consistency", "success")
        
        # Test Cloud Run detection compatibility
        with self.temp_env_vars(K_SERVICE="staging-service"):
            bootstrap_cloud_run = EnvironmentDetector.is_cloud_run()
            unified_cloud_run = EnvironmentDetector.is_cloud_run_unified()
            
            self.assertEqual(
                bootstrap_cloud_run,
                unified_cloud_run,
                f"Bootstrap and unified Cloud Run detection should match: {bootstrap_cloud_run} vs {unified_cloud_run}"
            )
            
            self.record_metric("cloud_run_detection_consistency", "success")
        
        # Test testing context detection compatibility
        with self.temp_env_vars(TESTING="true"):
            bootstrap_testing = EnvironmentDetector.is_testing_context()
            unified_testing = EnvironmentDetector.is_testing_context_unified()
            
            self.assertEqual(
                bootstrap_testing,
                unified_testing,
                f"Bootstrap and unified testing detection should match: {bootstrap_testing} vs {unified_testing}"
            )
            
            self.record_metric("testing_context_consistency", "success")
    
    def teardown_method(self, method):
        """Clean up test environment and record final metrics."""
        # Record test completion metrics
        execution_time = self.get_metrics().execution_time
        self.record_metric("test_execution_time", execution_time)
        
        # Log test metrics for analysis
        metrics = self.get_all_metrics()
        if execution_time > 1.0:  # Log if test is slow
            print(f"PERFORMANCE WARNING: {method.__name__} took {execution_time:.3f}s")
        
        super().teardown_method(method)


if __name__ == "__main__":
    # Allow running individual test file for debugging
    pytest.main([__file__, "-v", "--tb=short"])