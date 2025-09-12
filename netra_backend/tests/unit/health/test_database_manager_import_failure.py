"""
Unit Test: Database Manager Import Failure in Deep Health Checks

Purpose: Prove the import issue exists in deep_checks.py line 44
Issue #572: Database manager unavailable for health checks

This test MUST FAIL initially to prove the issue exists.
"""
import pytest
import sys
import importlib
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

# Import required base test case
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestDatabaseManagerImportFailure(SSotBaseTestCase):
    """Test cases to prove database manager import failure in deep health checks."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        # Clear any cached modules to ensure fresh imports
        modules_to_clear = [
            'netra_backend.app.services.health.deep_checks',
            'shared.database.core_database_manager'
        ]
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]
    
    def test_deep_checks_import_failure_reproduction(self):
        """
        CRITICAL: This test MUST FAIL to prove Issue #572 exists.
        
        This test reproduces the exact import failure:
        "No module named 'shared.database.core_database_manager'"
        """
        # Test 1: Verify the broken import path fails
        with pytest.raises(ImportError, match="No module named 'shared.database.core_database_manager'"):
            from shared.database.core_database_manager import get_database_manager
        
        # Test 2: Verify the correct import path works
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            # This should succeed
            assert DatabaseManager is not None
        except ImportError as e:
            pytest.fail(f"Correct import path should work but failed: {e}")
    
    def test_deep_checks_initialization_with_broken_import(self):
        """
        CRITICAL: This test MUST FAIL to prove deep_checks.py has broken import.
        
        This test verifies that deep_checks.py fails on initialization due to the import error.
        """
        # Import deep_checks module
        from netra_backend.app.services.health.deep_checks import DeepHealthChecks
        
        # Create instance and try to initialize
        deep_checks = DeepHealthChecks()
        
        # This should fail due to the broken import in line 44
        # The initialize method contains the broken import that will fail
        import asyncio
        
        async def test_init():
            # This should trigger the broken import and log a warning
            await deep_checks.initialize()
            
            # The initialization should set _initialized to False due to the import error
            # If this assertion fails, it means the issue is NOT present
            assert deep_checks._initialized is False, "Deep checks should fail to initialize due to broken import"
            assert deep_checks.db_manager is None, "Database manager should be None due to import failure"
        
        # Run the async test
        asyncio.run(test_init())
    
    def test_correct_import_path_validation(self):
        """
        This test verifies the correct import path works.
        This should PASS even when the main issue exists.
        """
        # Test that the correct import path works
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            # Verify we can instantiate it (basic validation)
            db_manager_class = DatabaseManager
            assert db_manager_class is not None
            assert hasattr(db_manager_class, '__init__')
            
        except ImportError as e:
            pytest.fail(f"Correct import path should work: {e}")
    
    def test_shared_database_path_does_not_exist(self):
        """
        This test proves the broken import path doesn't exist in the codebase.
        This should PASS and confirms the path is invalid.
        """
        # Try to find the supposedly correct path in the filesystem
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Check if the broken path exists
        broken_path = os.path.join(project_root, "shared", "database", "core_database_manager.py")
        
        # This should NOT exist, proving the import is wrong
        assert not os.path.exists(broken_path), f"Broken import path should not exist: {broken_path}"
        
        # Check if the correct path exists
        correct_path = os.path.join(project_root, "netra_backend", "app", "db", "database_manager.py")
        assert os.path.exists(correct_path), f"Correct import path should exist: {correct_path}"
    
    def test_deep_checks_fallback_behavior(self):
        """
        Test that deep_checks handles the import failure gracefully.
        This verifies the current fallback behavior works.
        """
        from netra_backend.app.services.health.deep_checks import DeepHealthChecks
        
        deep_checks = DeepHealthChecks()
        
        import asyncio
        
        async def test_fallback():
            # Initialize without external dependencies
            await deep_checks.initialize()
            
            # Should have fallback behavior due to import failure
            # The db_manager should be None due to the broken import
            assert deep_checks.db_manager is None, "Should fallback to None due to import error"
            
            # Try to run database health check - should return unavailable
            result = await deep_checks.check_database_depth()
            
            # Should return an unavailable result due to missing db_manager
            assert result.component_name == "database_deep"
            assert "not initialized" in result.message.lower() or "unavailable" in result.message.lower()
            assert result.status == "unhealthy"  # Should be unhealthy due to unavailable dependency
        
        asyncio.run(test_fallback())


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])