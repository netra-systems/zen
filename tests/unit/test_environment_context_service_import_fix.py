"""
Test for Issue #598 - Environment Context Service Import Fix

This test validates that the import fix for environment_context_service
resolves the staging startup failure caused by incorrect import path.

Business Impact: Prevents $500K+ ARR service startup failures in staging.
"""

import pytest
from typing import Optional


class TestEnvironmentContextServiceImportFix:
    """Test suite for environment context service import path fix."""
    
    def test_environment_context_service_import_path_correct(self):
        """Test that EnvironmentContextService can be imported from correct path."""
        # This import should succeed (the correct path)
        from netra_backend.app.core.environment_context.environment_context_service import EnvironmentContextService
        
        # Should be able to instantiate the class
        service = EnvironmentContextService()
        assert service is not None
        
    def test_environment_context_service_import_failure_old_path(self):
        """Test that old incorrect import path fails as expected."""
        # This import should fail (the old incorrect path)
        with pytest.raises(ModuleNotFoundError) as exc_info:
            from netra_backend.app.services.environment_context_service import EnvironmentContextService
            
        assert "No module named 'netra_backend.app.services.environment_context_service'" in str(exc_info.value)
        
    def test_smd_startup_orchestrator_import_works(self):
        """Test that SMD StartupOrchestrator can be imported without errors."""
        from netra_backend.app.smd import StartupOrchestrator
        
        # Should be able to access the class
        assert StartupOrchestrator is not None
        assert hasattr(StartupOrchestrator, '_initialize_environment_context')
        
    def test_environment_context_service_has_required_interface(self):
        """Test that EnvironmentContextService has the expected interface."""
        from netra_backend.app.core.environment_context.environment_context_service import EnvironmentContextService
        
        service = EnvironmentContextService()
        
        # Check that key methods exist
        expected_methods = [
            'configure_service',
            'get_service_configuration', 
            'register_environment_aware_service',
            'get_environment_context'
        ]
        
        for method_name in expected_methods:
            assert hasattr(service, method_name), f"Expected method {method_name} not found"


if __name__ == "__main__":
    # Quick validation when run directly
    print("Testing environment context service import fix...")
    
    try:
        from netra_backend.app.core.environment_context.environment_context_service import EnvironmentContextService
        print("✅ Correct import path works")
    except Exception as e:
        print(f"❌ Correct import failed: {e}")
        
    try:
        from netra_backend.app.services.environment_context_service import EnvironmentContextService
        print("❌ Old import path should have failed but didn't")
    except ModuleNotFoundError:
        print("✅ Old import path correctly fails")
        
    try:
        from netra_backend.app.smd import StartupOrchestrator
        print("✅ SMD StartupOrchestrator import works")
    except Exception as e:
        print(f"❌ SMD import failed: {e}")
        
    print("Test validation complete!")