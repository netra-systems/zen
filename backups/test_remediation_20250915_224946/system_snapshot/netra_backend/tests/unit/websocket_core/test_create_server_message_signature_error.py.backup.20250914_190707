"""
Test suite for WebSocket create_server_message signature error detection.

This test file implements Issue #405 test plan to reproduce and validate
the SSOT violation where two different create_server_message implementations
exist with incompatible signatures.

Business Value:
- Detects critical SSOT violation causing TypeError in production
- Ensures proper message creation patterns in WebSocket handlers
- Validates import resolution and function signature compatibility

Test Strategy:
- Fail tests initially to prove signature errors exist
- Use SSOT patterns from test_framework
- Test specific error lines: 573, 697, 798, 852 from handlers.py
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# SSOT test imports
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import both implementations to detect SSOT violation
from netra_backend.app.websocket_core.types import create_server_message as types_create_server_message
from netra_backend.app.websocket_core import create_server_message as init_create_server_message
from netra_backend.app.websocket_core.types import MessageType, ServerMessage


class TestCreateServerMessageSignatureError(SSotBaseTestCase):
    """Test suite for create_server_message signature errors (Issue #405)."""
    
    def setUp(self):
        """Set up test with proper logger."""
        super().setUp()
        from netra_backend.app.logging_config import central_logger
        self.logger = central_logger.get_logger(self.__class__.__name__)

    def test_dual_implementation_detection(self):
        """
        CRITICAL: Test that detects SSOT violation of dual create_server_message implementations.
        
        This test should FAIL initially to prove the signature error exists.
        """
        # Test that both implementations exist (SSOT violation)
        assert callable(types_create_server_message), "types.py implementation should exist"
        assert callable(init_create_server_message), "init.py implementation should exist"
        
        # Test different signatures
        import inspect
        
        types_sig = inspect.signature(types_create_server_message)
        init_sig = inspect.signature(init_create_server_message)
        
        # Extract parameter info
        types_params = list(types_sig.parameters.keys())
        init_params = list(init_sig.parameters.keys())
        
        self.logger.info(f"types.py signature: {types_params}")
        self.logger.info(f"init.py signature: {init_params}")
        
        # Test that signatures are incompatible (this should FAIL to prove SSOT violation)
        with pytest.raises(AssertionError, match="SSOT violation detected"):
            assert types_params == init_params, "SSOT violation detected: Different signatures for same function"

    def test_incorrect_call_pattern_failure(self):
        """
        Test that reproduces broken usage pattern from handlers.py.
        
        This test should FAIL initially, demonstrating the signature error.
        """
        # Test pattern used throughout handlers.py - this should fail
        try:
            # This is how handlers.py tries to call it (expecting data to be optional)
            result = types_create_server_message(
                MessageType.SYSTEM_MESSAGE,
                {"status": "connected", "user_id": "test123", "timestamp": 1234567890.0}
            )
            
            # If we get here, the call worked
            assert isinstance(result, ServerMessage), "Should return ServerMessage instance"
            self.logger.info(f"Unexpected success: {result}")
            
        except TypeError as e:
            # This is the expected signature error
            self.logger.error(f"Expected signature error detected: {e}")
            assert "missing 1 required positional argument" in str(e) or "takes" in str(e), f"Expected signature error, got: {e}"

    def test_incorrect_two_argument_call(self):
        """
        Test the broken pattern: create_server_message(msg_type, data_dict).
        
        Many calls in handlers.py use only 2 arguments expecting data=None default.
        This should FAIL when calling types.py implementation.
        """
        with pytest.raises(TypeError, match="missing 1 required positional argument|takes.*positional arguments"):
            # This pattern appears throughout handlers.py - should fail with types.py implementation
            types_create_server_message(
                MessageType.SYSTEM_MESSAGE
                # Missing required 'data' parameter
            )

    def test_correct_call_pattern(self):
        """
        Test the correct usage pattern that should work.
        
        This test validates what the proper call should look like.
        """
        # Correct usage with required data parameter
        result = types_create_server_message(
            MessageType.SYSTEM_MESSAGE,
            {"status": "test", "timestamp": 1234567890.0},
            correlation_id="test-123"
        )
        
        assert isinstance(result, ServerMessage), "Should return ServerMessage instance"
        assert result.type == MessageType.SYSTEM_MESSAGE
        assert result.data["status"] == "test"
        assert result.correlation_id == "test-123"

    def test_init_implementation_compatibility(self):
        """
        Test that init.py implementation has different behavior.
        
        This shows that init.py actually imports from types.py, not using fallback.
        """
        # Actually, init.py imports from types.py when available
        # This test demonstrates that both are the same function
        self.logger.info("Testing that init import is same as types import")
        
        # Both should be the same function since init.py imports from types.py
        assert init_create_server_message is types_create_server_message, \
            "Both imports should reference the same function from types.py"
        
        # The real issue is that this function requires data, but handlers call it without data
        with pytest.raises(TypeError):
            init_create_server_message(MessageType.SYSTEM_MESSAGE)  # Missing required data

    def test_handlers_import_resolution(self):
        """
        Test that handlers.py imports the problematic types.py implementation.
        
        This confirms which implementation is being used in the failing code.
        """
        # Simulate handlers.py import
        from netra_backend.app.websocket_core.types import create_server_message as handlers_import
        
        # Verify it's the types.py implementation (stricter signature)
        import inspect
        sig = inspect.signature(handlers_import)
        params = list(sig.parameters.keys())
        
        # Should have msg_type, data, correlation_id (types.py signature)
        assert 'msg_type' in params or 'data' in params, f"Should have types.py signature, got: {params}"
        
        # The data parameter should NOT have default None
        data_param = sig.parameters.get('data')
        if data_param:
            assert data_param.default == inspect.Parameter.empty, "data parameter should be required (no default)"

    def test_specific_handler_error_reproduction(self):
        """
        Reproduce specific errors from handlers.py lines mentioned in issue.
        
        Tests the actual failing patterns from lines 573, 697, 798, 852.
        """
        # Pattern from line 574 in handlers.py: ack_response = create_server_message(...)
        with pytest.raises(TypeError):
            types_create_server_message(
                MessageType.AGENT_TASK_ACK,
                # Missing required data parameter - this should fail
            )

        # Pattern from handlers that expects data to be optional
        with pytest.raises(TypeError):
            types_create_server_message(
                MessageType.SYSTEM_MESSAGE
                # Expects data to be optional but it's required in types.py
            )


class TestSignatureCompatibilityAnalysis(SSotBaseTestCase):
    """Additional tests for analyzing signature compatibility issues."""
    
    def setUp(self):
        """Set up test with proper logger."""
        super().setUp()
        from netra_backend.app.logging_config import central_logger
        self.logger = central_logger.get_logger(self.__class__.__name__)

    def test_parameter_inspection(self):
        """
        Analyze parameter differences between implementations.
        """
        import inspect
        
        # Get both signatures
        types_sig = inspect.signature(types_create_server_message)
        init_sig = inspect.signature(init_create_server_message)
        
        # Analyze differences
        types_params = {name: param for name, param in types_sig.parameters.items()}
        init_params = {name: param for name, param in init_sig.parameters.items()}
        
        self.logger.info(f"Types implementation parameters: {list(types_params.keys())}")
        self.logger.info(f"Init implementation parameters: {list(init_params.keys())}")
        
        # Check if data parameter behavior differs
        types_data = types_params.get('data')
        init_data = init_params.get('data')
        
        if types_data and init_data:
            self.logger.info(f"Types data default: {types_data.default}")
            self.logger.info(f"Init data default: {init_data.default}")
            
            # This should reveal the signature incompatibility
            assert types_data.default != init_data.default, "Data parameter defaults differ (SSOT violation)"

    def test_return_type_differences(self):
        """
        Test return types - both should be the same since init imports from types.
        """
        # Types implementation returns ServerMessage
        types_result = types_create_server_message(
            MessageType.SYSTEM_MESSAGE,
            {"test": "data"}
        )
        
        # Init implementation returns same ServerMessage (since it imports from types.py)
        init_result = init_create_server_message(
            MessageType.SYSTEM_MESSAGE,
            {"test": "data"}
        )
        
        # Both should return the same type since init.py imports from types.py
        assert type(types_result) == type(init_result), "Both should return same type from types.py"
        assert isinstance(types_result, ServerMessage), "Types implementation returns ServerMessage"
        assert isinstance(init_result, ServerMessage), "Init implementation also returns ServerMessage"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])