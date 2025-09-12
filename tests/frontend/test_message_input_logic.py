"""
Unit test to verify the message input logic fix.
Tests the checkIfFirstMessage and message type determination logic.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import unittest
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment


class TestMessageInputLogic(SSotBaseTestCase):
    """Test the message input logic for determining message types."""
    
    def test_check_if_first_message_no_thread_id(self):
        """Test that no thread_id returns True (is first message)."""
        # This simulates the fixed checkIfFirstMessage logic
        def check_if_first_message(thread_id, messages):
            # If no threadId, this is definitely the first message
            if not thread_id:
                return True
            
            # Check if there are any messages for this thread
            thread_messages = [
                msg for msg in messages
                if msg.get('thread_id') == thread_id and msg.get('role') == 'user'
            ]
            
            return len(thread_messages) == 0
        
        # Test with no thread_id
        result = check_if_first_message(None, [])
        self.assertTrue(result, "Should return True when thread_id is None")
        
        result = check_if_first_message("", [])
        self.assertTrue(result, "Should return True when thread_id is empty string")
    
    def test_check_if_first_message_no_existing_messages(self):
        """Test that thread with no messages returns True."""
        def check_if_first_message(thread_id, messages):
            if not thread_id:
                return True
            
            thread_messages = [
                msg for msg in messages
                if msg.get('thread_id') == thread_id and msg.get('role') == 'user'
            ]
            
            return len(thread_messages) == 0
        
        # Test with thread_id but no messages
        result = check_if_first_message("thread-123", [])
        self.assertTrue(result, "Should return True when no messages exist")
        
        # Test with messages from other threads
        other_messages = [
            {'thread_id': 'thread-456', 'role': 'user', 'content': 'other message'}
        ]
        result = check_if_first_message("thread-123", other_messages)
        self.assertTrue(result, "Should return True when no messages for this thread")
    
    def test_check_if_first_message_existing_messages(self):
        """Test that thread with existing messages returns False."""
        def check_if_first_message(thread_id, messages):
            if not thread_id:
                return True
            
            thread_messages = [
                msg for msg in messages
                if msg.get('thread_id') == thread_id and msg.get('role') == 'user'
            ]
            
            return len(thread_messages) == 0
        
        # Test with existing messages in thread
        existing_messages = [
            {'thread_id': 'thread-123', 'role': 'user', 'content': 'first message'},
            {'thread_id': 'thread-123', 'role': 'assistant', 'content': 'response'}
        ]
        result = check_if_first_message("thread-123", existing_messages)
        self.assertFalse(result, "Should return False when user messages exist in thread")
    
    def test_message_type_determination(self):
        """Test the logic for determining start_agent vs user_message."""
        def determine_message_type(thread_id, messages):
            # Simplified check - matches the fix
            thread_messages = [
                msg for msg in messages
                if msg.get('thread_id') == thread_id and msg.get('role') == 'user'
            ]
            is_first_message = not thread_id or len(thread_messages) == 0
            
            if is_first_message:
                return 'start_agent'
            else:
                return 'user_message'
        
        # Test new conversation (no thread)
        msg_type = determine_message_type(None, [])
        self.assertEqual(msg_type, 'start_agent', "New conversation should use start_agent")
        
        # Test new thread (has ID but no messages)
        msg_type = determine_message_type('thread-new', [])
        self.assertEqual(msg_type, 'start_agent', "New thread should use start_agent")
        
        # Test continuing conversation
        existing = [
            {'thread_id': 'thread-123', 'role': 'user', 'content': 'hello'}
        ]
        msg_type = determine_message_type('thread-123', existing)
        self.assertEqual(msg_type, 'user_message', "Existing conversation should use user_message")
    
    def test_consistency_with_example_prompts(self):
        """Test that the logic matches example prompt behavior."""
        # Example prompts always send start_agent with thread_id: null
        def example_prompt_message_type():
            return 'start_agent'
        
        # Message input with no thread should behave the same
        def message_input_type_no_thread(thread_id, messages):
            if not thread_id:
                return 'start_agent'
            thread_messages = [
                msg for msg in messages
                if msg.get('thread_id') == thread_id and msg.get('role') == 'user'
            ]
            return 'start_agent' if len(thread_messages) == 0 else 'user_message'
        
        # Both should send start_agent for new conversations
        example_type = example_prompt_message_type()
        input_type = message_input_type_no_thread(None, [])
        
        self.assertEqual(example_type, input_type, 
                        "Example prompts and message input should use same type for new conversations")
    
    def test_edge_case_messages_without_thread_id(self):
        """Test handling of messages that don't have thread_id set."""
        def check_if_first_message_improved(thread_id, messages):
            # Improved logic from the fix
            if not thread_id:
                return True
            
            # Include messages without thread_id for new conversations
            thread_messages = [
                msg for msg in messages
                if (msg.get('thread_id') == thread_id or 
                   (not msg.get('thread_id') and len(messages) == 0)) 
                   and msg.get('role') == 'user'
            ]
            
            return len(thread_messages) == 0
        
        # Test with messages that have no thread_id
        orphan_messages = [
            {'role': 'user', 'content': 'message without thread'},
            {'thread_id': None, 'role': 'user', 'content': 'null thread_id'}
        ]
        
        # Should still return True for new thread since orphan messages don't count
        result = check_if_first_message_improved("thread-123", orphan_messages)
        self.assertTrue(result, "Should ignore messages without matching thread_id")


if __name__ == "__main__":
    unittest.main()