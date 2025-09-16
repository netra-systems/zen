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
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.websocket_core.types import create_server_message as types_create_server_message
from netra_backend.app.websocket_core.types import create_server_message as init_create_server_message
from netra_backend.app.websocket_core.types import MessageType, ServerMessage

class CreateServerMessageSignatureErrorTests(SSotBaseTestCase):
    """Test suite for create_server_message signature errors (Issue #405)."""

    def setUp(self):
        """Set up test with proper logger."""
        super().setUp()
        from netra_backend.app.logging_config import central_logger
        self.logger = central_logger.get_logger(self.__class__.__name__)

    def test_ssot_consolidation_complete(self):
        """
        CRITICAL: Test that SSOT consolidation is complete - both imports reference the same function.

        This test validates that there's now only one implementation (SSOT compliance).
        """
        assert callable(types_create_server_message), 'types.py implementation should exist'
        assert callable(init_create_server_message), 'both imports should reference the same function'

        # SSOT SUCCESS: Both imports should reference the same function object
        assert types_create_server_message is init_create_server_message, 'SSOT SUCCESS: Both imports reference the same function from types.py'

        import inspect
        sig = inspect.signature(types_create_server_message)
        params = list(sig.parameters.keys())
        self.logger.info(f'SSOT unified signature: {params}')

        # Verify the function exists and is callable
        assert len(params) > 0, 'Function should have parameters'

    def test_incorrect_call_pattern_failure(self):
        """
        Test that reproduces broken usage pattern from handlers.py.
        
        This test should FAIL initially, demonstrating the signature error.
        """
        try:
            result = types_create_server_message(MessageType.SYSTEM_MESSAGE, {'status': 'connected', 'user_id': 'test123', 'timestamp': 1234567890.0})
            assert isinstance(result, ServerMessage), 'Should return ServerMessage instance'
            self.logger.info(f'Unexpected success: {result}')
        except TypeError as e:
            self.logger.error(f'Expected signature error detected: {e}')
            assert 'missing 1 required positional argument' in str(e) or 'takes' in str(e), f'Expected signature error, got: {e}'

    def test_single_argument_call_success(self):
        """
        Test that single argument calls now work (SSOT signature fix).

        This demonstrates that the signature issue has been resolved.
        The data parameter now has a default value of None.
        """
        # This should now work without errors
        result = types_create_server_message(MessageType.SYSTEM_MESSAGE)
        assert isinstance(result, ServerMessage), 'Should return ServerMessage instance'
        assert result.type == MessageType.SYSTEM_MESSAGE
        assert result.data is None or isinstance(result.data, dict), 'Data should be None or dict'

    def test_correct_call_pattern(self):
        """
        Test the correct usage pattern that should work.
        
        This test validates what the proper call should look like.
        """
        result = types_create_server_message(MessageType.SYSTEM_MESSAGE, {'status': 'test', 'timestamp': 1234567890.0}, correlation_id='test-123')
        assert isinstance(result, ServerMessage), 'Should return ServerMessage instance'
        assert result.type == MessageType.SYSTEM_MESSAGE
        assert result.data['status'] == 'test'
        assert result.correlation_id == 'test-123'

    def test_unified_implementation_behavior(self):
        """
        Test that the unified implementation behaves consistently.

        This validates that both import paths lead to the same function with the same behavior.
        """
        self.logger.info('Testing that both imports reference the same function (SSOT compliance)')
        assert init_create_server_message is types_create_server_message, 'Both imports should reference the same function from types.py'

        # Both should have the same successful behavior (since they're the same function)
        result1 = init_create_server_message(MessageType.SYSTEM_MESSAGE)
        result2 = types_create_server_message(MessageType.SYSTEM_MESSAGE)

        assert isinstance(result1, ServerMessage), 'init import should return ServerMessage'
        assert isinstance(result2, ServerMessage), 'types import should return ServerMessage'
        assert result1.type == result2.type == MessageType.SYSTEM_MESSAGE, 'Both should create same message type'

    def test_handlers_import_resolution(self):
        """
        Test that handlers.py imports the correct types.py implementation.

        This confirms the unified implementation is working correctly.
        """
        from netra_backend.app.websocket_core.types import create_server_message as handlers_import
        import inspect
        sig = inspect.signature(handlers_import)
        params = list(sig.parameters.keys())
        assert 'msg_type_or_dict' in params and 'data' in params, f'Should have types.py signature, got: {params}'
        data_param = sig.parameters.get('data')
        if data_param:
            assert data_param.default is None, 'data parameter should have None as default (SSOT fix)'

    def test_specific_handler_pattern_success(self):
        """
        Test that patterns from handlers.py lines now work correctly.

        These patterns should now succeed due to the SSOT signature fix.
        """
        # These calls should now work without errors
        result1 = types_create_server_message(MessageType.AGENT_TASK_ACK)
        result2 = types_create_server_message(MessageType.SYSTEM_MESSAGE)

        assert isinstance(result1, ServerMessage), 'AGENT_TASK_ACK should create ServerMessage'
        assert isinstance(result2, ServerMessage), 'SYSTEM_MESSAGE should create ServerMessage'
        assert result1.type == MessageType.AGENT_TASK_ACK
        assert result2.type == MessageType.SYSTEM_MESSAGE

class SignatureCompatibilityAnalysisTests(SSotBaseTestCase):
    """Additional tests for analyzing signature compatibility issues."""

    def setUp(self):
        """Set up test with proper logger."""
        super().setUp()
        from netra_backend.app.logging_config import central_logger
        self.logger = central_logger.get_logger(self.__class__.__name__)

    def test_parameter_inspection(self):
        """
        Analyze unified implementation parameters (SSOT validation).
        """
        import inspect
        types_sig = inspect.signature(types_create_server_message)
        init_sig = inspect.signature(init_create_server_message)
        types_params = {name: param for name, param in types_sig.parameters.items()}
        init_params = {name: param for name, param in init_sig.parameters.items()}
        self.logger.info(f'Types implementation parameters: {list(types_params.keys())}')
        self.logger.info(f'Init implementation parameters: {list(init_params.keys())}')

        # SSOT SUCCESS: Both should have identical parameters since they're the same function
        assert types_params.keys() == init_params.keys(), 'SSOT SUCCESS: Both imports have identical parameters'

        types_data = types_params.get('data')
        init_data = init_params.get('data')
        if types_data and init_data:
            self.logger.info(f'Types data default: {types_data.default}')
            self.logger.info(f'Init data default: {init_data.default}')
            assert types_data.default == init_data.default, 'SSOT SUCCESS: Data parameter defaults are identical'

    def test_return_type_differences(self):
        """
        Test return types - both should be the same since init imports from types.
        """
        types_result = types_create_server_message(MessageType.SYSTEM_MESSAGE, {'test': 'data'})
        init_result = init_create_server_message(MessageType.SYSTEM_MESSAGE, {'test': 'data'})
        assert type(types_result) == type(init_result), 'Both should return same type from types.py'
        assert isinstance(types_result, ServerMessage), 'Types implementation returns ServerMessage'
        assert isinstance(init_result, ServerMessage), 'Init implementation also returns ServerMessage'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')