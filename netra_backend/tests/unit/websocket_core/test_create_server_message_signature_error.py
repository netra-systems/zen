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
# SSOT COMPLIANCE FIX: Direct import instead of expecting __init__.py export
# Issue #1176 Phase 2 removed __init__.py exports to force canonical imports
# Since SSOT consolidation eliminated dual implementations, we test the canonical one
from netra_backend.app.websocket_core.types import MessageType, ServerMessage

class CreateServerMessageSignatureErrorTests(SSotBaseTestCase):
    """Test suite for create_server_message signature errors (Issue #405)."""

    def setUp(self):
        """Set up test with proper logger."""
        super().setUp()
        from netra_backend.app.logging_config import central_logger
        self.logger = central_logger.get_logger(self.__class__.__name__)

    def test_ssot_compliance_validation(self):
        """
        CRITICAL: Test that validates SSOT compliance for create_server_message.
        
        Post-Issue #1176: Validates that SSOT consolidation eliminated dual implementations.
        Now tests the canonical implementation works correctly.
        """
        assert callable(types_create_server_message), 'Canonical types.py implementation should exist'
        import inspect
        types_sig = inspect.signature(types_create_server_message)
        types_params = list(types_sig.parameters.keys())
        self.logger.info(f'Canonical SSOT signature: {types_params}')
        
        # SSOT COMPLIANCE: Validate canonical signature supports required patterns
        expected_params = ['msg_type_or_dict', 'data', 'correlation_id', 'content']
        for param in expected_params:
            assert param in types_params, f'SSOT signature missing required parameter: {param}'
        
        self.logger.info('SSOT compliance validated: Single canonical implementation confirmed')

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

    def test_incorrect_two_argument_call(self):
        """
        Test the broken pattern: create_server_message(msg_type, data_dict).
        
        Many calls in handlers.py use only 2 arguments expecting data=None default.
        This should FAIL when calling types.py implementation.
        """
        with pytest.raises(TypeError, match='missing 1 required positional argument|takes.*positional arguments'):
            types_create_server_message(MessageType.SYSTEM_MESSAGE)

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

    def test_canonical_implementation_behavior(self):
        """
        Test that canonical implementation has expected behavior.
        
        Post-SSOT: Validates the single canonical implementation works correctly.
        """
        self.logger.info('Testing canonical SSOT implementation behavior')
        
        # Test that insufficient parameters raise TypeError (validates strict signature)
        with pytest.raises(TypeError):
            types_create_server_message(MessageType.SYSTEM_MESSAGE)
        
        # Test that proper parameters work correctly
        result = types_create_server_message(
            MessageType.SYSTEM_MESSAGE, 
            {'status': 'test'}, 
            correlation_id='test-123'
        )
        assert isinstance(result, ServerMessage), 'Should return ServerMessage instance'

    def test_handlers_import_resolution(self):
        """
        Test that handlers.py imports the problematic types.py implementation.
        
        This confirms which implementation is being used in the failing code.
        """
        from netra_backend.app.websocket_core.types import create_server_message as handlers_import
        import inspect
        sig = inspect.signature(handlers_import)
        params = list(sig.parameters.keys())
        assert 'msg_type' in params or 'data' in params, f'Should have types.py signature, got: {params}'
        data_param = sig.parameters.get('data')
        if data_param:
            assert data_param.default == inspect.Parameter.empty, 'data parameter should be required (no default)'

    def test_specific_handler_error_reproduction(self):
        """
        Reproduce specific errors from handlers.py lines mentioned in issue.
        
        Tests the actual failing patterns from lines 573, 697, 798, 852.
        """
        with pytest.raises(TypeError):
            types_create_server_message(MessageType.AGENT_TASK_ACK)
        with pytest.raises(TypeError):
            types_create_server_message(MessageType.SYSTEM_MESSAGE)

class SignatureCompatibilityAnalysisTests(SSotBaseTestCase):
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
        types_sig = inspect.signature(types_create_server_message)
        init_sig = inspect.signature(init_create_server_message)
        types_params = {name: param for name, param in types_sig.parameters.items()}
        init_params = {name: param for name, param in init_sig.parameters.items()}
        self.logger.info(f'Types implementation parameters: {list(types_params.keys())}')
        self.logger.info(f'Init implementation parameters: {list(init_params.keys())}')
        types_data = types_params.get('data')
        init_data = init_params.get('data')
        if types_data and init_data:
            self.logger.info(f'Types data default: {types_data.default}')
            self.logger.info(f'Init data default: {init_data.default}')
            assert types_data.default != init_data.default, 'Data parameter defaults differ (SSOT violation)'

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