"""
Critical test to expose StartupCheckResult import issue in environment_checks.py

This test exposes the critical bug where environment_checks.py imports StartupCheckResult
from the wrong module (apex_optimizer_agent.models) instead of startup_checks.models.

The two StartupCheckResult classes have incompatible signatures:
- startup_checks.models: __init__(name, success, message, critical=True, duration_ms=0)
- apex_optimizer_agent.models: __init__(success=True, message="", details=None)

This causes a runtime error: "StartupCheckResult.__init__() got an unexpected keyword argument 'name'"

Business Value Justification (BVJ):
- Segment: All (Free to Enterprise)
- Business Goal: Stability
- Value Impact: Prevents complete startup failure that blocks all operations
- Revenue Impact: Prevents 100% service outage affecting all customers
"""

from test_framework import setup_test_path

setup_test_path()

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestStartupCheckResultImportIssue:
    """Test that exposes the critical StartupCheckResult import issue"""
    
    def test_environment_checks_imports_wrong_startup_check_result(self):
        """
        Test that environment_checks.py imports the wrong StartupCheckResult class.
        
        This test will FAIL until the import is fixed in environment_checks.py.
        The error demonstrates the exact issue seen in production.
        """
        # Import the EnvironmentChecker which has the wrong import
        from netra_backend.app.services.apex_optimizer_agent.models import (
            StartupCheckResult as WrongModel,
        )
        from netra_backend.app.startup_checks.environment_checks import (
            EnvironmentChecker,
        )

        # Import the correct StartupCheckResult for comparison
        from netra_backend.app.startup_checks.models import (
            StartupCheckResult as CorrectModel,
        )
        
        # Create an instance
        checker = EnvironmentChecker()
        
        # Test that the imported StartupCheckResult in environment_checks.py is wrong
        # This is done by checking the signature
        try:
            # Try to create a result using the pattern from _create_success_result
            # This should fail with the wrong import
            result = checker._create_success_result([])
            
            # If we get here, check the result has the expected attributes
            assert hasattr(result, 'name'), "StartupCheckResult should have 'name' attribute"
            assert result.name == "environment_variables"
            
        except TypeError as e:
            # This is what we expect with the wrong import
            assert "unexpected keyword argument 'name'" in str(e) or "missing" in str(e), \
                f"Expected error about 'name' parameter, got: {e}"
            pytest.fail(f"EnvironmentChecker is using wrong StartupCheckResult: {e}")
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_fails_with_wrong_import(self):
        """
        Test that check_environment_variables fails due to wrong StartupCheckResult import.
        
        This directly tests the method that fails in production.
        """
        from netra_backend.app.startup_checks.environment_checks import (
            EnvironmentChecker,
        )
        
        checker = EnvironmentChecker()
        
        # Mock the environment to be valid
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://test',
            'SECRET_KEY': 'a' * 32
        }):
            # This should fail with TypeError due to wrong StartupCheckResult
            with pytest.raises(TypeError) as exc_info:
                await checker.check_environment_variables()
            
            # Verify the specific error
            error_message = str(exc_info.value)
            assert "unexpected keyword argument 'name'" in error_message or \
                   "missing 1 required positional argument: 'name'" in error_message, \
                   f"Expected error about 'name' parameter, got: {error_message}"
    
    def test_startup_check_result_signature_mismatch(self):
        """
        Test that demonstrates the signature mismatch between the two StartupCheckResult classes.
        """
        from netra_backend.app.services.apex_optimizer_agent.models import (
            StartupCheckResult as WrongModel,
        )
        from netra_backend.app.startup_checks.models import (
            StartupCheckResult as CorrectModel,
        )
        
        # Test correct model accepts name as first positional argument
        correct_result = CorrectModel(
            name="test",
            success=True,
            message="Test message"
        )
        assert correct_result.name == "test"
        
        # Test wrong model does NOT accept name
        with pytest.raises(TypeError) as exc_info:
            wrong_result = WrongModel(
                name="test",  # This will fail
                success=True,
                message="Test message"
            )
        
        assert "unexpected keyword argument 'name'" in str(exc_info.value)
    
    def test_all_startup_check_modules_use_correct_import(self):
        """
        Test that all startup check modules import the correct StartupCheckResult.
        
        This comprehensive test checks all modules in startup_checks package.
        """
        import importlib
        import inspect
        from pathlib import Path
        
        # Get the startup_checks directory
        startup_checks_dir = Path(__file__).parent.parent.parent / "app" / "startup_checks"
        
        # Check each Python file in the directory
        failed_modules = []
        for py_file in startup_checks_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            module_name = f"netra_backend.app.startup_checks.{py_file.stem}"
            
            try:
                module = importlib.import_module(module_name)
                
                # Check if the module has StartupCheckResult imported
                if hasattr(module, 'StartupCheckResult'):
                    result_class = getattr(module, 'StartupCheckResult')
                    
                    # Check if it's the correct one by checking the module path
                    if result_class.__module__ != "netra_backend.app.startup_checks.models":
                        failed_modules.append({
                            'module': module_name,
                            'imported_from': result_class.__module__,
                            'should_be': "netra_backend.app.startup_checks.models"
                        })
                        
                # Also check for direct imports in the source
                source = py_file.read_text()
                if "from app.services.apex_optimizer_agent.models import StartupCheckResult" in source:
                    failed_modules.append({
                        'module': module_name,
                        'issue': 'Direct import from apex_optimizer_agent.models found in source'
                    })
                    
            except ImportError as e:
                # Skip modules that can't be imported in test environment
                pass
        
        # Report all modules with wrong imports
        if failed_modules:
            import json
            pytest.fail(f"Modules with wrong StartupCheckResult import:\n{json.dumps(failed_modules, indent=2)}")


class TestStartupCheckIntegration:
    """Integration tests to ensure startup checks work correctly"""
    
    @pytest.mark.asyncio
    async def test_full_startup_check_sequence(self):
        """
        Test the full startup check sequence to ensure it can complete.
        
        This test will fail if any startup check module has the wrong import.
        """
        from unittest.mock import AsyncMock, MagicMock

        from netra_backend.app.startup_checks.checker import StartupChecker
        
        # Create a mock app
        app = MagicMock()
        
        # Create the checker
        checker = StartupChecker(app)
        
        # Mock external dependencies
        with patch('netra_backend.app.startup_checks.database_checks.DatabaseChecker') as mock_db:
            with patch('netra_backend.app.startup_checks.service_checks.ServiceChecker') as mock_service:
                # Setup mocks to return valid results
                mock_db_instance = mock_db.return_value
                mock_db_instance.check_postgres = AsyncMock(return_value=MagicMock(
                    success=True, critical=False
                ))
                mock_db_instance.check_clickhouse = AsyncMock(return_value=MagicMock(
                    success=True, critical=False
                ))
                
                mock_service_instance = mock_service.return_value
                mock_service_instance.check_redis = AsyncMock(return_value=MagicMock(
                    success=True, critical=False
                ))
                mock_service_instance.check_llm_providers = AsyncMock(return_value=MagicMock(
                    success=True, critical=False
                ))
                
                # Run all checks - this will fail if imports are wrong
                try:
                    results = await checker.run_all_checks()
                    
                    # Verify we got results
                    assert results is not None
                    assert 'success' in results
                    
                except TypeError as e:
                    if "unexpected keyword argument 'name'" in str(e):
                        pytest.fail(f"Startup checks failed due to wrong StartupCheckResult import: {e}")
                    raise


if __name__ == "__main__":
    # Run the tests directly
    pytest.main([__file__, "-v", "--tb=short"])