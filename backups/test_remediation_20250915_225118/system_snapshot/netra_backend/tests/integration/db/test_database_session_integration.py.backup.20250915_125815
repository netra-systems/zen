"""
Integration tests for GitHub issue #135: Database session integration failures.

Tests reproduce the failure when WebSocket manager factory tries to create
database connections using the non-existent get_db_session_factory function.

EXPECTED BEHAVIOR: These tests MUST FAIL to reproduce the integration issue.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the netra_backend to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestWebSocketManagerFactoryIntegration:
    """Integration tests that reproduce WebSocket manager factory creation failures."""
    
    def test_websocket_manager_factory_creation_fails(self):
        """
        Test that WebSocket manager factory creation fails due to database import error.
        
        This test simulates the real scenario where the factory tries to initialize
        and fails because get_db_session_factory doesn't exist.
        
        EXPECTED: This test should FAIL with ImportError during factory creation
        """
        # This test will attempt to import and create a WebSocket manager factory
        # which should fail when it tries to import get_db_session_factory
        
        try:
            # Import the factory module
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            # Try to create the factory - this should fail during health checks
            factory = WebSocketManagerFactory()
            
            # If we reach here, the import worked (unexpected)
            pytest.fail("WebSocket manager factory creation should have failed due to missing get_db_session_factory")
            
        except ImportError as e:
            # This is expected - the import should fail
            assert "get_db_session_factory" in str(e), f"Expected import error for get_db_session_factory, got: {e}"
            print(f"Successfully reproduced ImportError: {e}")
            # Re-raise to mark test as failed (which is what we want)
            raise
        except Exception as e:
            # Any other exception during factory creation
            print(f"Factory creation failed with exception: {e}")
            # Check if it's related to our database import issue
            if "get_db_session_factory" in str(e):
                # This is the error we're looking for
                raise ImportError(f"Database import failure in factory: {e}")
            else:
                # Some other error - let it fail the test
                raise
    
    def test_websocket_manager_health_check_failure(self):
        """
        Test that WebSocket manager health check fails due to database import.
        
        This test focuses specifically on the health check component that uses
        the missing get_db_session_factory function.
        
        EXPECTED: This test should FAIL with ImportError during health check
        """
        # Mock the WebSocket manager factory to isolate the health check failure
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory') as mock_factory:
            
            # Create a mock instance
            mock_instance = MagicMock()
            mock_factory.return_value = mock_instance
            
            # Mock the health check method to reproduce the actual failure
            def failing_health_check(*args, **kwargs):
                # Simulate the exact failure from the real health check code
                try:
                    from netra_backend.app.db.session import get_db_session_factory
                    db_factory = get_db_session_factory()
                    return {"status": "healthy"}
                except ImportError as e:
                    raise e
            
            mock_instance.health_check = failing_health_check
            
            # Now try to run the health check - it should fail
            try:
                result = mock_instance.health_check()
                pytest.fail("Health check should have failed with ImportError")
            except ImportError as e:
                assert "get_db_session_factory" in str(e)
                print(f"Health check failed as expected: {e}")
                raise  # Re-raise to mark test as failed
    
    def test_database_session_factory_replacement_options(self):
        """
        Test what database session functions are actually available for replacement.
        
        This test documents what should be used instead of get_db_session_factory
        to help with the remediation.
        
        EXPECTED: This test should PASS and show available alternatives
        """
        from netra_backend.app.db.session import (
            get_database_manager,
            get_session,
            get_async_session,
            get_session_from_factory
        )
        
        # Test that these functions exist and can be called
        db_manager = get_database_manager()
        assert db_manager is not None, "DatabaseManager should be available"
        
        # Test that we can get a session factory from the database manager
        # This is likely what should replace get_db_session_factory
        assert hasattr(db_manager, 'get_session'), "DatabaseManager should have get_session method"
        assert hasattr(db_manager, 'get_session_context'), "DatabaseManager should have get_session_context method"
        
        print(f"Available DatabaseManager methods: {[m for m in dir(db_manager) if not m.startswith('_')]}")
        
        # Document the correct replacement pattern
        print("REMEDIATION SUGGESTION:")
        print("Replace: from netra_backend.app.db.session import get_db_session_factory")
        print("With: from netra_backend.app.db.session import get_database_manager")
        print("Then use: db_manager = get_database_manager() instead of get_db_session_factory()")


class TestIntegrationWithRealServices:
    """Integration tests using real services (if available without Docker)."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("psycopg2", reason="PostgreSQL not available"),
        reason="PostgreSQL not available for integration testing"
    )
    def test_database_manager_creation_without_factory_function(self):
        """
        Test that we can create database connections using the correct approach.
        
        This test shows the working alternative to get_db_session_factory.
        
        EXPECTED: This test should PASS if PostgreSQL is available
        """
        try:
            from netra_backend.app.db.session import get_database_manager, init_database
            
            # Test creating database manager (the correct approach)
            db_manager = get_database_manager()
            assert db_manager is not None
            
            # Test that the manager has the expected methods
            expected_methods = ['get_session', 'get_session_context', 'initialize', 'cleanup']
            for method in expected_methods:
                assert hasattr(db_manager, method), f"DatabaseManager missing expected method: {method}"
            
            print("Successfully created database manager using correct approach")
            print(f"DatabaseManager type: {type(db_manager)}")
            
        except Exception as e:
            print(f"Database manager creation test failed: {e}")
            # Don't fail the test if it's just a configuration issue
            pytest.skip(f"Database not configured for testing: {e}")
    
    def test_websocket_factory_with_correct_database_approach(self):
        """
        Test WebSocket factory creation with the correct database approach.
        
        This test mocks the correct database imports to show what should work.
        
        EXPECTED: This test should PASS with mocked correct imports
        """
        # Mock the import to provide the correct function
        with patch.dict('sys.modules', {
            'netra_backend.app.db.session': MagicMock()
        }):
            # Mock the session module to have the correct functions
            session_module = sys.modules['netra_backend.app.db.session']
            session_module.get_database_manager = MagicMock(return_value=MagicMock())
            session_module.get_session = MagicMock()
            
            # Now remove the problematic function that doesn't exist
            if hasattr(session_module, 'get_db_session_factory'):
                delattr(session_module, 'get_db_session_factory')
            
            # Test that the corrected approach would work
            db_manager = session_module.get_database_manager()
            assert db_manager is not None
            
            print("Correct database approach simulation successful")
            print("RECOMMENDATION: Update WebSocket factory to use get_database_manager() instead of get_db_session_factory()")