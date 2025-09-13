"""
Issue #586 Resolution Validation Tests

These tests validate that Issue #586 (GCP startup race condition WebSocket 1011 errors) 
has been properly resolved by testing the ACTUAL timeout configuration implementation.

Unlike the reproduction tests, these tests use the real CloudNativeTimeoutManager
to verify that the fixes are working correctly.

Business Value: Platform/Internal - System Stability
Ensures timeout configurations correctly handle GCP Cloud Run deployment patterns,
preventing WebSocket 1011 failures during service initialization.
"""

import pytest
import os
from unittest.mock import patch, Mock
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.timeout_configuration import (
    CloudNativeTimeoutManager, 
    TimeoutEnvironment,
    get_environment_detection_info,
    get_timeout_hierarchy_info
)


class TestIssue586ResolutionValidation(SSotBaseTestCase):
    """
    Validation tests for Issue #586 resolution using real timeout configuration.
    
    These tests verify that the actual CloudNativeTimeoutManager correctly:
    1. Detects GCP Cloud Run environments with proper precedence
    2. Applies appropriate timeout values with cold start buffers
    3. Handles environment precedence conflicts correctly
    4. Maintains timeout hierarchy for business reliability
    """
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        test_context = self.get_test_context()
        if test_context:
            test_context.test_category = "unit"
            test_context.metadata["issue"] = "586_resolution_validation"
            test_context.metadata["focus"] = "real_implementation_validation"
    
    def test_gcp_cloud_run_staging_environment_detection_resolution(self):
        """
        VALIDATION TEST: GCP Cloud Run staging environment detection works correctly.
        
        Tests that the real CloudNativeTimeoutManager correctly detects staging 
        environment via GCP Cloud Run markers and applies appropriate timeouts.
        
        EXPECTED RESULT: Should PASS - staging environment correctly detected,
        timeout >= 15s with cold start buffer applied.
        """
        
        # GCP Cloud Run staging environment
        staging_env = {
            "K_SERVICE": "netra-backend-staging",
            "K_REVISION": "netra-backend-staging-00001-abc",
            "K_CONFIGURATION": "netra-backend-staging", 
            "GCP_PROJECT_ID": "netra-staging",
            "ENVIRONMENT": "staging",
            "PORT": "8080",
            "GOOGLE_CLOUD_PROJECT": "netra-staging"
        }
        
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: staging_env.get(key, default)
            
            # Test real CloudNativeTimeoutManager
            manager = CloudNativeTimeoutManager()
            config = manager.get_timeout_config()
            
            # Validate environment detection
            assert manager._environment == TimeoutEnvironment.CLOUD_RUN_STAGING, (
                f"Environment detection failed: detected '{manager._environment}' instead of "
                f"'TimeoutEnvironment.CLOUD_RUN_STAGING' with K_SERVICE='{staging_env['K_SERVICE']}' "
                f"and GCP_PROJECT_ID='{staging_env['GCP_PROJECT_ID']}'"
            )
            
            # Validate timeout configuration - should be >= 15s base + cold start buffer
            min_expected_timeout = 15.0  # Base staging timeout
            assert config.websocket_recv_timeout >= min_expected_timeout, (
                f"Staging timeout insufficient: got {config.websocket_recv_timeout}s, "
                f"expected >= {min_expected_timeout}s for Cloud Run staging environment"
            )
            
            # Validate cold start buffer is applied
            gcp_markers = manager._detect_gcp_environment_markers()
            cold_start_buffer = manager._calculate_cold_start_buffer('staging', gcp_markers)
            assert cold_start_buffer > 0, (
                f"Cold start buffer not applied: got {cold_start_buffer}s, "
                f"expected > 0s for Cloud Run deployment"
            )
            
            # Validate timeout hierarchy (WebSocket > Agent)
            hierarchy_valid = config.websocket_recv_timeout > config.agent_execution_timeout
            assert hierarchy_valid, (
                f"Timeout hierarchy broken: WebSocket recv ({config.websocket_recv_timeout}s) "
                f"should be > Agent execution ({config.agent_execution_timeout}s)"
            )
            
            self.record_metric("staging_detected", True)
            self.record_metric("websocket_recv_timeout", config.websocket_recv_timeout)
            self.record_metric("cold_start_buffer", cold_start_buffer)
            self.record_metric("hierarchy_valid", hierarchy_valid)
    
    def test_environment_precedence_conflict_resolution(self):
        """
        VALIDATION TEST: Environment precedence conflicts resolved correctly.
        
        Tests scenarios where ENVIRONMENT variable conflicts with GCP Cloud Run markers,
        verifying that GCP markers take precedence for Cloud Run deployments.
        
        EXPECTED RESULT: Should PASS - GCP markers override conflicting ENVIRONMENT values.
        """
        
        precedence_scenarios = [
            {
                "name": "k_service_staging_vs_env_development",
                "env_vars": {
                    "K_SERVICE": "netra-backend-staging",
                    "ENVIRONMENT": "development",  # Conflicts with K_SERVICE
                    "GCP_PROJECT_ID": "netra-staging"
                },
                "expected_environment": TimeoutEnvironment.CLOUD_RUN_STAGING,
                "min_timeout": 15.0
            },
            {
                "name": "gcp_project_production_vs_env_staging", 
                "env_vars": {
                    "GCP_PROJECT_ID": "netra-production",
                    "ENVIRONMENT": "staging",  # Conflicts with GCP_PROJECT_ID
                    "GOOGLE_CLOUD_PROJECT": "netra-production",
                    "K_SERVICE": "netra-backend-production"
                },
                "expected_environment": TimeoutEnvironment.CLOUD_RUN_PRODUCTION,
                "min_timeout": 25.0
            }
        ]
        
        resolution_results = []
        
        for scenario in precedence_scenarios:
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: scenario["env_vars"].get(key, default)
                
                manager = CloudNativeTimeoutManager()
                config = manager.get_timeout_config()
                
                # Validate environment resolution
                environment_correct = manager._environment == scenario["expected_environment"]
                timeout_adequate = config.websocket_recv_timeout >= scenario["min_timeout"]
                
                resolution_results.append({
                    "scenario": scenario["name"],
                    "environment_correct": environment_correct,
                    "timeout_adequate": timeout_adequate,
                    "detected_environment": manager._environment,
                    "timeout": config.websocket_recv_timeout,
                    "expected_env": scenario["expected_environment"],
                    "min_timeout": scenario["min_timeout"]
                })
                
                # Individual assertions for clear failure messages
                assert environment_correct, (
                    f"Precedence resolution failed for {scenario['name']}: "
                    f"detected {manager._environment}, expected {scenario['expected_environment']} "
                    f"with env_vars {scenario['env_vars']}"
                )
                
                assert timeout_adequate, (
                    f"Timeout inadequate for {scenario['name']}: "
                    f"got {config.websocket_recv_timeout}s, expected >= {scenario['min_timeout']}s"
                )
        
        # All scenarios should pass
        all_resolved = all(r["environment_correct"] and r["timeout_adequate"] for r in resolution_results)
        assert all_resolved, (
            f"Precedence resolution failed for some scenarios: {resolution_results}"
        )
        
        self.record_metric("precedence_scenarios_tested", len(precedence_scenarios))
        self.record_metric("precedence_resolutions_successful", len([r for r in resolution_results if r["environment_correct"]]))
    
    def test_cloud_run_cold_start_buffer_application(self):
        """
        VALIDATION TEST: Cold start buffer correctly applied for Cloud Run deployments.
        
        Tests that cold start buffers are calculated and applied for different
        Cloud Run environments (staging vs production).
        
        EXPECTED RESULT: Should PASS - cold start buffers > 0 for Cloud Run environments.
        """
        
        cold_start_scenarios = [
            {
                "name": "staging_cloud_run",
                "env_vars": {
                    "K_SERVICE": "netra-backend-staging",
                    "GCP_PROJECT_ID": "netra-staging",
                    "ENVIRONMENT": "staging"
                },
                "expected_min_buffer": 2.0,
                "environment": "staging"
            },
            {
                "name": "production_cloud_run", 
                "env_vars": {
                    "K_SERVICE": "netra-backend-production",
                    "GCP_PROJECT_ID": "netra-production",
                    "ENVIRONMENT": "production"
                },
                "expected_min_buffer": 3.0,
                "environment": "production"
            }
        ]
        
        buffer_results = []
        
        for scenario in cold_start_scenarios:
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: scenario["env_vars"].get(key, default)
                
                manager = CloudNativeTimeoutManager()
                gcp_markers = manager._detect_gcp_environment_markers()
                cold_start_buffer = manager._calculate_cold_start_buffer(
                    scenario["environment"], gcp_markers
                )
                
                buffer_adequate = cold_start_buffer >= scenario["expected_min_buffer"]
                cloud_run_detected = gcp_markers['is_gcp_cloud_run']
                
                buffer_results.append({
                    "scenario": scenario["name"],
                    "buffer_adequate": buffer_adequate,
                    "cloud_run_detected": cloud_run_detected,
                    "actual_buffer": cold_start_buffer,
                    "expected_min": scenario["expected_min_buffer"]
                })
                
                # Individual assertions
                assert cloud_run_detected, (
                    f"Cloud Run not detected for {scenario['name']} with "
                    f"K_SERVICE='{scenario['env_vars']['K_SERVICE']}'"
                )
                
                assert buffer_adequate, (
                    f"Cold start buffer inadequate for {scenario['name']}: "
                    f"got {cold_start_buffer}s, expected >= {scenario['expected_min_buffer']}s"
                )
        
        # All scenarios should have adequate buffers
        all_adequate = all(r["buffer_adequate"] for r in buffer_results)
        assert all_adequate, (
            f"Cold start buffer calculation failed for some scenarios: {buffer_results}"
        )
        
        self.record_metric("cold_start_scenarios_tested", len(cold_start_scenarios))
        self.record_metric("cold_start_buffers_adequate", len([r for r in buffer_results if r["buffer_adequate"]]))
    
    def test_timeout_hierarchy_validation_comprehensive(self):
        """
        VALIDATION TEST: Timeout hierarchy maintained across all environments.
        
        Tests that WebSocket timeouts > Agent timeouts in all environment configurations
        to ensure proper timeout coordination and prevent race conditions.
        
        EXPECTED RESULT: Should PASS - timeout hierarchy valid for all environments.
        """
        
        environments_to_test = [
            {
                "name": "local_development",
                "env_vars": {},
                "expected_environment": TimeoutEnvironment.LOCAL_DEVELOPMENT
            },
            {
                "name": "staging_cloud_run",
                "env_vars": {
                    "K_SERVICE": "netra-backend-staging",
                    "GCP_PROJECT_ID": "netra-staging",
                    "ENVIRONMENT": "staging"
                },
                "expected_environment": TimeoutEnvironment.CLOUD_RUN_STAGING
            },
            {
                "name": "production_cloud_run",
                "env_vars": {
                    "K_SERVICE": "netra-backend-production", 
                    "GCP_PROJECT_ID": "netra-production",
                    "ENVIRONMENT": "production"
                },
                "expected_environment": TimeoutEnvironment.CLOUD_RUN_PRODUCTION
            }
        ]
        
        hierarchy_results = []
        
        for env_test in environments_to_test:
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: env_test["env_vars"].get(key, default)
                
                manager = CloudNativeTimeoutManager()
                config = manager.get_timeout_config()
                hierarchy_valid = manager.validate_timeout_hierarchy()
                
                hierarchy_results.append({
                    "environment": env_test["name"],
                    "hierarchy_valid": hierarchy_valid,
                    "websocket_recv": config.websocket_recv_timeout,
                    "agent_execution": config.agent_execution_timeout,
                    "gap": config.websocket_recv_timeout - config.agent_execution_timeout
                })
                
                # Individual assertions
                assert hierarchy_valid, (
                    f"Timeout hierarchy broken for {env_test['name']}: "
                    f"WebSocket recv ({config.websocket_recv_timeout}s) should be > "
                    f"Agent execution ({config.agent_execution_timeout}s)"
                )
        
        # All environments should have valid hierarchies
        all_valid = all(r["hierarchy_valid"] for r in hierarchy_results)
        assert all_valid, (
            f"Timeout hierarchy validation failed: {hierarchy_results}"
        )
        
        self.record_metric("environments_tested", len(environments_to_test))
        self.record_metric("hierarchies_valid", len([r for r in hierarchy_results if r["hierarchy_valid"]]))
    
    def test_environment_detection_info_comprehensive(self):
        """
        VALIDATION TEST: Environment detection info provides comprehensive diagnostics.
        
        Tests the get_environment_detection_info() function to ensure it provides
        complete environment detection diagnostics for debugging.
        
        EXPECTED RESULT: Should PASS - comprehensive environment detection info available.
        """
        
        # Test with simulated Cloud Run environment
        staging_env = {
            "K_SERVICE": "netra-backend-staging",
            "GCP_PROJECT_ID": "netra-staging",
            "ENVIRONMENT": "staging"
        }
        
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: staging_env.get(key, default)
            
            env_info = get_environment_detection_info()
            hierarchy_info = get_timeout_hierarchy_info()
            
            # Validate environment detection info structure
            required_keys = [
                "detected_environment", 
                "environment_sources", 
                "gcp_markers",
                "timeout_values",
                "hierarchy_validation"
            ]
            
            for key in required_keys:
                assert key in env_info, f"Missing required key '{key}' in environment detection info"
            
            # Validate GCP markers detection
            assert "is_gcp_cloud_run" in env_info["gcp_markers"], "Missing GCP Cloud Run detection"
            assert env_info["gcp_markers"]["is_gcp_cloud_run"] == True, "GCP Cloud Run not detected"
            
            # Validate timeout hierarchy info
            assert hierarchy_info["hierarchy_valid"] == True, "Timeout hierarchy not valid"
            assert hierarchy_info["business_impact"] == "$200K+ MRR reliability", "Business impact not documented"
            
            # Validate comprehensive diagnostics
            assert "environment_detection" in hierarchy_info, "Missing environment detection diagnostics"
            assert "gcp_detection" in hierarchy_info["environment_detection"], "Missing GCP detection info"
            
            self.record_metric("env_detection_info_complete", True)
            self.record_metric("hierarchy_info_complete", True)
            self.record_metric("gcp_cloud_run_detected", env_info["gcp_markers"]["is_gcp_cloud_run"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])