"""
Unit tests for GitHub issue #135: Database import failure reproduction.

Tests directly reproduce the import failure when trying to import `get_db_session_factory`
from netra_backend.app.db.session module.

EXPECTED BEHAVIOR: These tests MUST FAIL to reproduce the issue.
"""

import pytest
from unittest.mock import patch


class TestSessionImportFailure:
    """Test class to reproduce the import failure from GitHub issue #135."""
    
    def test_direct_get_db_session_factory_import_fails(self):
        """
        Test that directly importing get_db_session_factory fails.
        
        This test reproduces the exact import failure reported in GitHub issue #135.
        The import should fail because get_db_session_factory doesn't exist in the session module.
        
        EXPECTED: This test should FAIL with ImportError
        """
        with pytest.raises(ImportError, match="cannot import name 'get_db_session_factory'"):
            from netra_backend.app.db.session import get_db_session_factory
    
    def test_websocket_manager_factory_failing_import(self):
        """
        Test that reproduces the WebSocket manager factory import failure.
        
        This simulates the code path in websocket_manager_factory.py that tries to import
        get_db_session_factory and fails.
        
        EXPECTED: This test should FAIL with ImportError
        """
        # Simulate the exact import pattern from websocket_manager_factory.py
        with pytest.raises(ImportError):
            try:
                from netra_backend.app.db.session import get_db_session_factory
                db_factory = get_db_session_factory()
                # If we reach here, the import succeeded (unexpected)
                pytest.fail("Import should have failed but succeeded")
            except ImportError as e:
                # This is expected - re-raise to validate the test
                assert "get_db_session_factory" in str(e)
                raise
    
    def test_available_functions_in_session_module(self):
        """
        Test to document what functions are actually available in the session module.
        
        This test will help identify what should be used instead of get_db_session_factory.
        
        EXPECTED: This test should PASS and show available functions
        """
        import netra_backend.app.db.session as session_module
        
        # Get all public functions/attributes
        available_functions = [name for name in dir(session_module) 
                             if not name.startswith('_') and callable(getattr(session_module, name))]
        
        print(f"Available functions in session module: {available_functions}")
        
        # Verify expected functions exist
        expected_functions = [
            'get_session',
            'get_async_session', 
            'get_session_from_factory',
            'init_database',
            'close_database',
            'get_database_manager'
        ]
        
        for func_name in expected_functions:
            assert hasattr(session_module, func_name), f"Expected function {func_name} not found"
        
        # Verify the problematic function does NOT exist
        assert not hasattr(session_module, 'get_db_session_factory'), \
            "get_db_session_factory should not exist but was found"
    
    def test_import_all_from_session_module(self):
        """
        Test importing everything from session module to see what's exported.
        
        EXPECTED: This test should PASS and help identify the correct imports
        """
        # Test that we can import the module without issues
        import netra_backend.app.db.session as session_module
        
        # Check the __all__ export list
        all_exports = getattr(session_module, '__all__', [])
        print(f"Exported functions via __all__: {all_exports}")
        
        # Verify get_db_session_factory is NOT in the exports
        assert 'get_db_session_factory' not in all_exports, \
            "get_db_session_factory should not be in __all__ exports"
        
        # Verify that safe_session_context and handle_session_error are in __all__ 
        # but might not actually exist (potential discrepancy)
        expected_missing = ['safe_session_context', 'handle_session_error']
        for missing_func in expected_missing:
            if missing_func in all_exports:
                # Check if the function actually exists
                has_function = hasattr(session_module, missing_func)
                print(f"Function {missing_func} is in __all__ but exists: {has_function}")


class TestWebSocketManagerFactoryImportReproduction:
    """Tests that reproduce the specific failure in WebSocket manager factory creation."""
    
    def test_health_check_database_import_failure(self):
        """
        Reproduce the exact failure path in WebSocket manager factory health check.
        
        This simulates the code in websocket_manager_factory.py that fails during
        health check when trying to import get_db_session_factory.
        
        EXPECTED: This test should FAIL with ImportError
        """
        health_result = {
            "service_details": {},
            "component_details": {}
        }
        
        # Simulate the exact code path from websocket_manager_factory.py
        with pytest.raises(ImportError):
            # Check 3: Database session factory (from the factory code)
            try:
                from netra_backend.app.db.session import get_db_session_factory
                db_factory = get_db_session_factory()
                if not db_factory:
                    raise Exception("Database session factory is None")
                health_result["service_details"]["database"] = "healthy"
            except ImportError as e:
                print(f"Import error reproduced: {e}")
                raise
            except Exception as e:
                health_result["service_details"]["database"] = f"unhealthy: {str(e)}"
                raise
    
    def test_component_database_connectivity_failure(self):
        """
        Reproduce the Component 2: Database Connectivity failure.
        
        This simulates the second location in websocket_manager_factory.py where
        the same import fails.
        
        EXPECTED: This test should FAIL with ImportError  
        """
        health_result = {
            "component_details": {}
        }
        
        # Simulate Component 2: Database Connectivity code path
        with pytest.raises(ImportError):
            try:
                from netra_backend.app.db.session import get_db_session_factory
                db_factory = get_db_session_factory()
                if db_factory is None:
                    raise Exception("Database session factory is None")
                health_result["component_details"]["database"] = {
                    "status": "healthy",
                    "factory": "available"
                }
            except ImportError as e:
                print(f"Component database connectivity import error: {e}")
                raise
            except Exception as e:
                health_result["component_details"]["database"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                raise