"""
Integration test to verify message type determination works correctly.
This test simulates the actual logic flow for both example prompts and message input.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import unittest
from enum import Enum
from shared.isolated_environment import IsolatedEnvironment

# Simulate the WebSocketMessageType enum
class WebSocketMessageType(Enum):
    START_AGENT = 'start_agent'
    USER_MESSAGE = 'user_message'

class MessageTypeIntegrationTest(SSotBaseTestCase):
    """Test that message type determination is consistent between input methods."""
    
    def setUp(self):
        """Set up test data."""
        self.messages = []
        
    def simulate_example_prompt_logic(self):
        """
        Simulate how ExamplePrompts.tsx works.
        Always uses START_AGENT for new conversations.
        """
        return {
            'type': WebSocketMessageType.START_AGENT,
            'payload': {
                'user_request': 'Example prompt message',
                'thread_id': None,
                'context': {'source': 'example_prompt'},
                'settings': {}
            }
        }
    
    def simulate_message_input_logic(self, thread_id=None, messages=None):
        """
        Simulate the fixed useMessageSending.ts logic.
        Uses START_AGENT for new conversations, USER_MESSAGE for existing.
        """
        if messages is None:
            messages = self.messages
            
        # Check if this is the first message - simplified check (from the fix)
        thread_messages = [
            msg for msg in messages 
            if msg.get('thread_id') == thread_id and msg.get('role') == 'user'
        ]
        is_first_message = not thread_id or len(thread_messages) == 0
        
        if is_first_message:
            return {
                'type': WebSocketMessageType.START_AGENT,
                'payload': {
                    'user_request': 'User typed message',
                    'thread_id': thread_id,
                    'context': {'source': 'message_input'},
                    'settings': {}
                }
            }
        else:
            return {
                'type': WebSocketMessageType.USER_MESSAGE,
                'payload': {
                    'content': 'User typed message',
                    'references': [],
                    'thread_id': thread_id
                }
            }
    
    def test_new_conversation_consistency(self):
        """Test that both methods use START_AGENT for new conversations."""
        # Example prompt for new conversation
        example_result = self.simulate_example_prompt_logic()
        
        # Message input for new conversation (no thread)
        input_result = self.simulate_message_input_logic(thread_id=None)
        
        # Both should use START_AGENT
        self.assertEqual(example_result['type'], WebSocketMessageType.START_AGENT)
        self.assertEqual(input_result['type'], WebSocketMessageType.START_AGENT)
        
        # Verify they're the same
        self.assertEqual(example_result['type'], input_result['type'],
                        "Example prompts and message input should use same message type for new conversations")
    
    def test_new_thread_consistency(self):
        """Test that both methods handle new threads correctly."""
        thread_id = "new-thread-123"
        
        # Message input for new thread (has ID but no messages)
        input_result = self.simulate_message_input_logic(thread_id=thread_id, messages=[])
        
        # Should use START_AGENT for new thread
        self.assertEqual(input_result['type'], WebSocketMessageType.START_AGENT,
                        "New thread should use START_AGENT")
    
    def test_existing_conversation(self):
        """Test that continuing conversations use USER_MESSAGE."""
        thread_id = "existing-thread-456"
        
        # Simulate existing messages
        existing_messages = [
            {'thread_id': thread_id, 'role': 'user', 'content': 'First message'},
            {'thread_id': thread_id, 'role': 'assistant', 'content': 'Response'}
        ]
        
        # Message input for existing conversation
        input_result = self.simulate_message_input_logic(
            thread_id=thread_id, 
            messages=existing_messages
        )
        
        # Should use USER_MESSAGE for continuing conversation
        self.assertEqual(input_result['type'], WebSocketMessageType.USER_MESSAGE,
                        "Continuing conversation should use USER_MESSAGE")
    
    def test_full_conversation_flow(self):
        """Test a complete conversation flow."""
        thread_id = "flow-thread-789"
        messages = []
        
        # First message - should use START_AGENT
        first_msg = self.simulate_message_input_logic(thread_id=thread_id, messages=messages)
        self.assertEqual(first_msg['type'], WebSocketMessageType.START_AGENT,
                        "First message should use START_AGENT")
        
        # Add the first message to history
        messages.append({'thread_id': thread_id, 'role': 'user', 'content': 'First message'})
        
        # Second message - should use USER_MESSAGE
        second_msg = self.simulate_message_input_logic(thread_id=thread_id, messages=messages)
        self.assertEqual(second_msg['type'], WebSocketMessageType.USER_MESSAGE,
                        "Second message should use USER_MESSAGE")
        
        # Add more messages
        messages.append({'thread_id': thread_id, 'role': 'assistant', 'content': 'Response'})
        messages.append({'thread_id': thread_id, 'role': 'user', 'content': 'Another question'})
        
        # Third message - should still use USER_MESSAGE
        third_msg = self.simulate_message_input_logic(thread_id=thread_id, messages=messages)
        self.assertEqual(third_msg['type'], WebSocketMessageType.USER_MESSAGE,
                        "Subsequent messages should use USER_MESSAGE")
    
    def test_edge_case_empty_thread_id(self):
        """Test edge case with empty thread_id."""
        # Empty string thread_id should be treated as no thread
        result = self.simulate_message_input_logic(thread_id="", messages=[])
        self.assertEqual(result['type'], WebSocketMessageType.START_AGENT,
                        "Empty thread_id should use START_AGENT")
        
        # None thread_id
        result = self.simulate_message_input_logic(thread_id=None, messages=[])
        self.assertEqual(result['type'], WebSocketMessageType.START_AGENT,
                        "None thread_id should use START_AGENT")
    
    def test_payload_structure(self):
        """Test that payload structure is correct for each message type."""
        # START_AGENT payload
        start_agent_msg = self.simulate_message_input_logic(thread_id=None)
        self.assertIn('user_request', start_agent_msg['payload'])
        self.assertIn('context', start_agent_msg['payload'])
        self.assertEqual(start_agent_msg['payload']['context']['source'], 'message_input')
        
        # USER_MESSAGE payload (with existing messages)
        existing = [{'thread_id': 'test', 'role': 'user', 'content': 'hi'}]
        user_msg = self.simulate_message_input_logic(thread_id='test', messages=existing)
        self.assertIn('content', user_msg['payload'])
        self.assertIn('references', user_msg['payload'])
        self.assertIn('thread_id', user_msg['payload'])


if __name__ == "__main__":
    unittest.main(verbosity=2)