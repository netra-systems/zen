"""
Minimal Parameter Fix Validation Test

This test validates that the FIVE WHYS parameter standardization fix is working
correctly without requiring Docker services. It focuses specifically on the
websocket_client_id vs websocket_connection_id parameter fix.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestParameterStandardizationFix:
    """
    Test the specific parameter standardization fix from the FIVE WHYS analysis.
    
    Validates that UserExecutionContext:
    1. Accepts websocket_client_id parameter (FIXED)
    2. Rejects websocket_connection_id parameter in constructor (DEPRECATED) 
    3. Provides websocket_connection_id as backward compatibility property
    """
    
    def test_user_execution_context_accepts_websocket_client_id(self):
        """Test that UserExecutionContext accepts the corrected websocket_client_id parameter."""
        # Create mock database session
        mock_db_session = AsyncMock()
        
        user_id = "user_123456789012345678901234567890"  # Long enough to avoid validation issues
        thread_id = "thread_67890123456789012345678901234567890"
        run_id = "run_abcde123456789012345678901234567890"
        websocket_client_id = "ws_client_connection_xyz"
        
        # This should work with the corrected parameter name
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            websocket_client_id=websocket_client_id,  # CORRECTED PARAMETER
            db_session=mock_db_session
        )
        
        # Validate successful creation
        assert user_context.user_id == user_id
        assert user_context.thread_id == thread_id
        assert user_context.run_id == run_id
        assert user_context.websocket_client_id == websocket_client_id
        
        print(f" PASS:  UserExecutionContext accepts websocket_client_id parameter")
    
    def test_user_execution_context_rejects_websocket_connection_id_in_constructor(self):
        """Test that UserExecutionContext rejects the deprecated websocket_connection_id in constructor."""
        mock_db_session = AsyncMock()
        
        user_id = "test_user_12345"
        thread_id = "test_thread_67890" 
        run_id = "test_run_abcde"
        websocket_connection_id = "ws_connection_deprecated_xyz"
        
        # This should fail with the deprecated parameter name
        with pytest.raises(TypeError, match="unexpected keyword.*websocket_connection_id"):
            UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                websocket_connection_id=websocket_connection_id,  # DEPRECATED PARAMETER
                db_session=mock_db_session
            )
        
        print(f" PASS:  UserExecutionContext properly rejects deprecated websocket_connection_id in constructor")
    
    def test_backward_compatibility_property_works(self):
        """Test that websocket_connection_id property provides backward compatibility."""
        mock_db_session = AsyncMock()
        
        user_id = "user_compatibility_12345678901234567890"
        thread_id = "thread_compatibility_67890123456789012345678901234567890"
        run_id = "run_compatibility_abcde123456789012345678901234567890" 
        websocket_client_id = "ws_client_compatibility_test"
        
        # Create context with corrected parameter
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            websocket_client_id=websocket_client_id,
            db_session=mock_db_session
        )
        
        # Backward compatibility property should work
        assert user_context.websocket_connection_id == websocket_client_id
        assert user_context.websocket_connection_id == user_context.websocket_client_id
        
        print(f" PASS:  Backward compatibility property websocket_connection_id works correctly")
    
    def test_parameter_interface_consistency(self):
        """Test that the parameter interface is consistent and follows FIVE WHYS fix."""
        mock_db_session = AsyncMock()
        
        # Test data
        test_user_id = "user_105945141827451681156"  # From original error
        test_thread_id = "thread_consistency_test"
        test_run_id = "run_consistency_test" 
        test_websocket_id = "ws_consistency_test_12345"
        
        # Create context using the FIXED parameter interface
        context = UserExecutionContext(
            user_id=test_user_id,
            thread_id=test_thread_id,
            run_id=test_run_id,
            websocket_client_id=test_websocket_id,  # FIVE WHYS FIX: standardized parameter
            db_session=mock_db_session
        )
        
        # Validate all aspects of the parameter fix
        # 1. Primary parameter works
        assert context.websocket_client_id == test_websocket_id
        
        # 2. Backward compatibility property works
        assert context.websocket_connection_id == test_websocket_id
        
        # 3. Both refer to the same value
        assert context.websocket_client_id == context.websocket_connection_id
        
        # 4. Context is properly initialized
        assert context.user_id == test_user_id
        assert context.thread_id == test_thread_id
        assert context.run_id == test_run_id
        
        # 5. Context can be converted to dict (serialization test)
        context_dict = context.to_dict()
        assert 'websocket_client_id' in context_dict
        assert 'websocket_connection_id' in context_dict  # Backward compatibility
        assert context_dict['websocket_client_id'] == test_websocket_id
        assert context_dict['websocket_connection_id'] == test_websocket_id
        
        print(f" PASS:  Parameter interface consistency validated")
        print(f" PASS:  FIVE WHYS fix working: websocket_client_id = {test_websocket_id}")
        print(f" PASS:  Backward compatibility maintained: websocket_connection_id property works")
        
    def test_original_error_scenario_parameter_fix(self):
        """Test that the specific scenario from the original error report works."""
        mock_db_session = AsyncMock()
        
        # Use data from original error report
        original_error_user_id = "105945141827451681156"
        test_thread_id = "original_error_thread_test"
        test_run_id = "original_error_run_test"
        test_connection_id = "ws_10594514_1757335346_19513def"  # Pattern from original error
        
        # This should now work (was failing before the FIVE WHYS fix)
        context = UserExecutionContext(
            user_id=original_error_user_id,
            thread_id=test_thread_id,
            run_id=test_run_id,
            websocket_client_id=test_connection_id,  # CRITICAL FIX: using websocket_client_id
            db_session=mock_db_session
        )
        
        # Validate the fix resolved the original issue
        assert context.user_id == original_error_user_id
        assert context.websocket_client_id == test_connection_id
        assert context.websocket_connection_id == test_connection_id  # Backward compatibility
        
        print(f" PASS:  Original error scenario RESOLVED")
        print(f" PASS:  User {original_error_user_id} context creation successful")
        print(f" PASS:  Connection ID {test_connection_id} properly handled")


if __name__ == "__main__":
    # Run the tests directly
    import os
    os.system("python -m pytest " + __file__ + " -v --tb=short")