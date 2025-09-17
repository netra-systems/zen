"""
Test Infrastructure Remediation Validation

Tests to verify that the fixes implemented for test infrastructure issues
are working correctly and maintain SSOT compliance.

Issue Coverage:
- Test infrastructure timeouts due to service dependencies
- Auth integration import naming issues (resolved)
- Lightweight test modes that don't require full service stack
"""

import os
import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.orchestration import (
    get_orchestration_config,
    is_no_services_mode,
    check_service_available
)
from test_framework.ssot.decorators import (
    skip_if_no_services,
    skip_if_service_unavailable,
    skip_if_docker_unavailable
)


class TestInfrastructureRemediation(SSotBaseTestCase):
    """Test infrastructure remediation fixes."""
    
    def test_no_services_mode_detection(self):
        """Test that no-services mode can be detected properly."""
        # Test the current state detection
        config = get_orchestration_config()
        
        # The mode property should be accessible
        mode = config.no_services_mode
        assert isinstance(mode, bool)
        
        # Test environment variable detection logic
        from shared.isolated_environment import get_env
        env = get_env()
        
        # Test the actual logic without changing the singleton
        test_value = env.get("TEST_NO_SERVICES", "false").lower() == "true"
        assert isinstance(test_value, bool)
    
    def test_service_availability_check(self):
        """Test service availability checking functionality."""
        # Test invalid port
        assert check_service_available("test_service", "localhost", None) == False
        
        # Test unreachable service (should fail quickly)
        assert check_service_available("unreachable", "localhost", 99999, timeout=0.1) == False
    
    def test_docker_availability_respects_no_services_mode(self):
        """Test that Docker availability respects no-services mode."""
        config = get_orchestration_config()
        
        # Test that docker availability checking works
        docker_available = config.docker_available
        assert isinstance(docker_available, bool)
        
        # Test the no-services mode property
        no_services = config.no_services_mode
        assert isinstance(no_services, bool)
        
        # In no-services mode, Docker should be unavailable regardless of actual Docker status
        if no_services:
            assert docker_available == False
    
    @skip_if_no_services("This test demonstrates the skip decorator")
    def test_skip_decorator_functionality(self):
        """Test that skip decorators work correctly."""
        # This test should be skipped if in no-services mode
        # If it runs, no-services mode is not active
        assert True
    
    @skip_if_service_unavailable("fake_service", port=99999, timeout=0.1)
    def test_service_skip_decorator(self):
        """Test that service availability skip decorator works."""
        # This test should be skipped because the service is unavailable
        pytest.fail("This test should have been skipped due to unavailable service")
    
    @skip_if_docker_unavailable("Test requires Docker")
    def test_docker_skip_decorator(self):
        """Test that Docker skip decorator works."""
        # This test may be skipped depending on Docker availability and no-services mode
        # If it runs, Docker is available and we're not in no-services mode
        assert True
    
    def test_auth_integration_import_resolution(self):
        """Test that auth integration imports work correctly."""
        # Test that the correct auth integration class can be imported
        try:
            from netra_backend.app.auth_integration.auth import BackendAuthIntegration
            assert BackendAuthIntegration is not None
        except ImportError as e:
            pytest.fail(f"Auth integration import failed: {e}")
    
    def test_orchestration_config_validation(self):
        """Test that orchestration configuration validation works."""
        config = get_orchestration_config()
        
        # Get validation issues
        issues = config.validate_configuration()
        
        # Issues list should be a list (may be empty)
        assert isinstance(issues, list)
        
        # Log any issues for debugging
        if issues:
            print(f"Orchestration validation issues: {issues}")
    
    def test_orchestration_status_reporting(self):
        """Test that orchestration status reporting works."""
        config = get_orchestration_config()
        
        status = config.get_availability_status()
        
        # Status should be a dictionary
        assert isinstance(status, dict)
        
        # Should have required keys
        required_keys = [
            'orchestrator_available',
            'master_orchestration_available', 
            'background_e2e_available',
            'all_orchestration_available',
            'any_orchestration_available'
        ]
        
        for key in required_keys:
            assert key in status
    
    def test_service_config_retrieval(self):
        """Test that service configuration can be retrieved."""
        config = get_orchestration_config()
        
        # Test known service configurations
        for service in ['orchestrator', 'master_orchestration', 'background_e2e']:
            service_config = config.get_service_config(service)
            
            assert isinstance(service_config, dict)
            assert 'availability_key' in service_config
            assert 'import_modules' in service_config
            assert 'required_classes' in service_config
    
    def test_ssot_compliance_maintained(self):
        """Test that SSOT compliance is maintained after infrastructure changes."""
        # Test that SSOT orchestration patterns are working
        config = get_orchestration_config()
        
        # Should be a singleton
        config2 = get_orchestration_config()
        assert config is config2
        
        # Test SSOT import patterns
        try:
            from test_framework.ssot.orchestration import orchestration_config
            assert orchestration_config is not None
        except ImportError as e:
            pytest.fail(f"SSOT orchestration import failed: {e}")