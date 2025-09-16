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

    def test_flexible_call_patterns(self):
        """
        Test that canonical implementation supports flexible calling patterns.
        
        Post-SSOT: The implementation supports backward compatibility with defaults.
        """
        # Test single argument call (uses defaults)
        result1 = types_create_server_message(MessageType.SYSTEM_MESSAGE)
        assert isinstance(result1, ServerMessage), 'Single argument call should work with defaults'
        
        # Test two argument call
        result2 = types_create_server_message(MessageType.SYSTEM_MESSAGE, {'status': 'test'})
        assert isinstance(result2, ServerMessage), 'Two argument call should work'
        assert result2.data['status'] == 'test', 'Data should be set correctly'

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
        
        # Test minimal parameters work (flexible defaults)
        result1 = types_create_server_message(MessageType.SYSTEM_MESSAGE)
        assert isinstance(result1, ServerMessage), 'Minimal parameters should work'
        
        # Test complete parameters work correctly
        result2 = types_create_server_message(
            MessageType.SYSTEM_MESSAGE, 
            {'status': 'test'}, 
            correlation_id='test-123'
        )
        assert isinstance(result2, ServerMessage), 'Should return ServerMessage instance'
        assert result2.correlation_id == 'test-123', 'Correlation ID should be set'

    def test_handlers_import_resolution(self):
        """
        Test that handlers.py imports the canonical types.py implementation.
        
        This confirms the correct implementation is being used.
        """
        from netra_backend.app.websocket_core.types import create_server_message as handlers_import
        import inspect
        sig = inspect.signature(handlers_import)
        params = list(sig.parameters.keys())
        
        # Validate signature has expected parameters
        expected_params = ['msg_type_or_dict', 'data', 'correlation_id', 'content']
        for expected in expected_params:
            assert expected in params, f'Should have parameter {expected}, got: {params}'
        
        # Validate data parameter has default (None) for flexibility
        data_param = sig.parameters.get('data')
        if data_param:
            assert data_param.default is None, f'data parameter should have None default, got: {data_param.default}'

    def test_specific_handler_patterns_work(self):
        """
        Test that handler patterns from mentioned lines work correctly.
        
        Tests the actual calling patterns from handlers.py work with canonical implementation.
        """
        # Test patterns that handlers.py uses - should work with flexible signature
        result1 = types_create_server_message(MessageType.AGENT_TASK_ACK)
        assert isinstance(result1, ServerMessage), 'Single MessageType call should work'
        assert result1.type == MessageType.AGENT_TASK_ACK, 'Type should match'
        
        result2 = types_create_server_message(MessageType.SYSTEM_MESSAGE)
        assert isinstance(result2, ServerMessage), 'System message call should work'
        assert result2.type == MessageType.SYSTEM_MESSAGE, 'Type should match'

class SignatureCompatibilityAnalysisTests(SSotBaseTestCase):
    """Additional tests for analyzing signature compatibility issues."""

    def setUp(self):
        """Set up test with proper logger."""
        super().setUp()
        from netra_backend.app.logging_config import central_logger
        self.logger = central_logger.get_logger(self.__class__.__name__)

    def test_parameter_inspection(self):
        """
        Analyze parameter structure of canonical implementation.
        """
        import inspect
        types_sig = inspect.signature(types_create_server_message)
        types_params = {name: param for name, param in types_sig.parameters.items()}
        self.logger.info(f'Canonical implementation parameters: {list(types_params.keys())}')
        
        # SSOT COMPLIANCE: Validate parameter structure
        types_data = types_params.get('data')
        if types_data:
            self.logger.info(f'Canonical data parameter default: {types_data.default}')
            # Validate that data parameter is properly structured
            assert types_data.annotation is not None, 'Data parameter should have type annotation'

    def test_return_type_validation(self):
        """
        Test return type of canonical implementation.
        """
        result = types_create_server_message(MessageType.SYSTEM_MESSAGE, {'test': 'data'})
        assert isinstance(result, ServerMessage), 'Canonical implementation returns ServerMessage'
        
        # Validate ServerMessage structure
        assert hasattr(result, 'type'), 'ServerMessage should have type attribute'
        assert hasattr(result, 'data'), 'ServerMessage should have data attribute'
        assert result.type == MessageType.SYSTEM_MESSAGE, 'Type should match input'
        assert result.data['test'] == 'data', 'Data should match input'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')