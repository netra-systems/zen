"""
Regression test for WebSocket manager signature issues.

This test ensures that create_websocket_manager() function
accepts both positional and keyword arguments correctly,
preventing the "unexpected keyword argument 'context'" error.

Related to: WEBSOCKET_CONTEXT_ERROR_FIVE_WHYS_20250908.md
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.integration
class TestWebSocketManagerSignature:
    """Test suite to prevent regression of WebSocket manager signature issues."""

    def test_create_websocket_manager_accepts_positional_argument(self):
        """
        Regression test: Ensure create_websocket_manager accepts positional argument.
        
        This prevents the error:
        'create_websocket_manager() got an unexpected keyword argument 'context''
        """
        context = UserExecutionContext(user_id='105945141827451681156', thread_id='thread_abc123def456', run_id='run_2025_09_08_14_30_00')
        try:
            manager = create_websocket_manager(context)
            assert manager is not None
            assert hasattr(manager, 'user_context')
            assert manager.user_context.user_id == '105945141827451681156'
        except TypeError as e:
            pytest.fail(f'Failed with positional argument: {e}')

    def test_create_websocket_manager_accepts_keyword_argument(self):
        """
        Ensure create_websocket_manager also accepts keyword argument.
        
        The function should accept both patterns for flexibility.
        """
        context = UserExecutionContext(user_id='github_user_98765432101', thread_id='thread_xyz789ghi012', run_id='run_2025_09_08_14_31_00')
        try:
            manager = create_websocket_manager(user_context=context)
            assert manager is not None
            assert hasattr(manager, 'user_context')
            assert manager.user_context.user_id == 'github_user_98765432101'
        except TypeError as e:
            pytest.fail(f'Failed with keyword argument: {e}')

    def test_create_websocket_manager_validates_argument_type(self):
        """
        Ensure proper type validation for user_context argument.
        
        This helps catch incorrect usage early with clear error messages.
        """
        invalid_contexts = [None, 'invalid_string', 123, {'user_id': 'test'}, Mock(spec=object)]
        for invalid_context in invalid_contexts:
            with pytest.raises((TypeError, ValueError, AttributeError)):
                create_websocket_manager(invalid_context)

    def test_create_websocket_manager_preserves_context_isolation(self):
        """
        Ensure each call creates an isolated manager instance.
        
        This is critical for multi-user security isolation.
        """
        context1 = UserExecutionContext(user_id='user_1', thread_id='thread_1', run_id='run_1')
        context2 = UserExecutionContext(user_id='user_2', thread_id='thread_2', run_id='run_2')
        manager1 = create_websocket_manager(context1)
        manager2 = create_websocket_manager(context2)
        assert manager1 is not manager2
        assert id(manager1) != id(manager2)
        assert manager1.user_context.user_id == 'user_1'
        assert manager2.user_context.user_id == 'user_2'
        assert manager1.user_context.user_id != manager2.user_context.user_id

    def test_all_call_patterns_in_codebase_are_valid(self):
        """
        Meta-test: Verify common call patterns found in codebase work.
        
        This catches any patterns we might have missed.
        """
        context = UserExecutionContext(user_id='email_user_john.doe@example.com', thread_id='thread_main_2025_09', run_id='run_2025_09_08_14_32_00')
        manager1 = create_websocket_manager(context)
        assert manager1 is not None
        user_context = context
        manager2 = create_websocket_manager(user_context)
        assert manager2 is not None
        manager3 = create_websocket_manager(user_context=context)
        assert manager3 is not None
        assert all([manager1, manager2, manager3])
        assert len({id(manager1), id(manager2), id(manager3)}) == 3
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')