"""
Unit tests for UnifiedDockerManager parameter validation.
Prevents regression of the 'environment' parameter bug.

This test ensures that invalid parameter names are properly rejected
and helps prevent similar naming confusion in the future.
"""

import pytest
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType


class TestUnifiedDockerManagerParameterValidation:
    """Test parameter validation for UnifiedDockerManager initialization."""

    def test_invalid_environment_parameter_rejected(self):
        """
        REGRESSION TEST: Ensure 'environment' parameter is rejected.
        
        This test prevents the bug that occurred in tests/e2e/test_agent_pipeline_real.py
        where environment="e2e-test" was incorrectly passed to UnifiedDockerManager.
        """
        with pytest.raises(TypeError, match=r"unexpected keyword argument 'environment'"):
            UnifiedDockerManager(environment="test")

    def test_invalid_environment_with_valid_environment_type_rejected(self):
        """
        REGRESSION TEST: Ensure 'environment' parameter is rejected even with valid environment_type.
        
        This is the exact pattern that was failing in the E2E test:
        UnifiedDockerManager(environment="e2e-test", environment_type=EnvironmentType.DEDICATED)
        """
        with pytest.raises(TypeError, match=r"unexpected keyword argument 'environment'"):
            UnifiedDockerManager(
                environment="e2e-test",
                environment_type=EnvironmentType.DEDICATED
            )

    def test_all_environment_types_accepted(self):
        """Ensure all valid EnvironmentType enum values are accepted."""
        for env_type in EnvironmentType:
            manager = UnifiedDockerManager(environment_type=env_type)
            assert manager.environment_type == env_type

    def test_default_environment_type(self):
        """Test that default environment_type is EnvironmentType.DEDICATED."""
        manager = UnifiedDockerManager()
        assert manager.environment_type == EnvironmentType.DEDICATED

    def test_environment_type_parameter_name_is_correct(self):
        """
        DOCUMENTATION TEST: Verify the correct parameter name.
        
        This test serves as documentation for developers:
        -  PASS:  CORRECT: environment_type=EnvironmentType.TEST
        -  FAIL:  WRONG: environment="test"
        """
        #  PASS:  This should work
        manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        assert manager.environment_type == EnvironmentType.TEST
        
        #  FAIL:  This should fail (already tested above, but included for clarity)
        with pytest.raises(TypeError):
            UnifiedDockerManager(environment="test")

    def test_agent_pipeline_infrastructure_pattern_works(self):
        """
        INTEGRATION TEST: Test the exact pattern used in AgentPipelineInfrastructure.
        
        This simulates the fixed initialization pattern from the E2E test.
        """
        # This is the FIXED pattern that should work
        docker_manager = UnifiedDockerManager(
            environment_type=EnvironmentType.TEST
        )
        
        # Verify it initialized correctly
        assert docker_manager.environment_type == EnvironmentType.TEST
        assert hasattr(docker_manager, 'use_alpine')
        assert hasattr(docker_manager, 'rebuild_images')

    @pytest.mark.parametrize("invalid_param", [
        {"environment": "test"},
        {"environment": "staging"}, 
        {"environment": "production"},
        {"environment": "e2e-test"},  # The exact failing case
    ])
    def test_various_invalid_environment_parameters(self, invalid_param):
        """Test that various 'environment' parameter values all fail."""
        with pytest.raises(TypeError, match=r"unexpected keyword argument 'environment'"):
            UnifiedDockerManager(**invalid_param)

    def test_documentation_examples_work(self):
        """Test examples that should be used in documentation."""
        # Example 1: Basic usage
        manager1 = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        assert manager1.environment_type == EnvironmentType.TEST
        
        # Example 2: E2E testing
        manager2 = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        assert manager2.environment_type == EnvironmentType.DEDICATED
        
        # Example 3: Staging
        manager3 = UnifiedDockerManager(environment_type=EnvironmentType.STAGING)
        assert manager3.environment_type == EnvironmentType.STAGING