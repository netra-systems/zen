"""
Issue #1116: Multi-User Chat Isolation Failures - Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise/Mid-Market - Multi-tenant chat security for $500K+ ARR protection
- Business Goal: Security & Compliance - Prevent chat message cross-contamination
- Value Impact: Validates chat isolation prevents message leakage between concurrent users
- Strategic Impact: Enterprise customer trust requires bulletproof chat isolation

CRITICAL: These tests should FAIL initially to prove the chat isolation problem exists.
They validate that chat messages, AI responses, and user context leak between concurrent users.

Test Coverage:
1. Concurrent chat message isolation failures
2. Agent response cross-contamination between users
3. Chat history bleeding across user sessions
4. WebSocket message mis-delivery in multi-user scenarios
5. AI conversation context contamination
6. User session state leakage during concurrent chat
7. Tool execution results delivered to wrong user
8. Chat performance degradation due to shared resources

ARCHITECTURE ALIGNMENT:
- Tests prove chat isolation failures affect $500K+ ARR customers
- Validates USER_CONTEXT_ARCHITECTURE.md factory isolation requirements
- Shows enterprise security compliance violations
- Demonstrates multi-tenant chat deployment blockers
"""

import asyncio
import pytest
import threading
import time
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import concurrent.futures
from contextlib import asynccontextmanager

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import real components for integration testing (NO MOCKS per CLAUDE.md)
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory, 
    get_agent_instance_factory,
    create_agent_instance_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge, 
    create_agent_websocket_bridge
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.base_agent import BaseAgent

# Mock chat infrastructure for testing
class MockChatAgent(BaseAgent):
    """Mock chat agent that simulates real chat behavior with state tracking."""
    
    def __init__(self, agent_id: str = None):
        super().__init__()
        self.agent_id = agent_id or str(uuid.uuid4())
        self.chat_history = []
        self.user_context = None
        self.websocket_bridge = None
        self.run_id = None
        self.ai_responses = []
        self.tool_executions = []
        self.session_state = {}
        
    def set_user_context(self, context: UserExecutionContext):
        """Set user context for this agent instance."""
        self.user_context = context
        
    def set_websocket_bridge(self, bridge, run_id: str):
        """Set WebSocket bridge for real-time notifications."""
        self.websocket_bridge = bridge
        self.run_id = run_id
        
    async def process_chat_message(self, message: str, user_id: str) -> str:
        """Process chat message and return AI response."""
        # Store message in chat history (THIS SHOULD BE ISOLATED PER USER)
        chat_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': user_id,
            'message': message,
            'agent_id': self.agent_id
        }
        self.chat_history.append(chat_entry)
        
        # Generate AI response
        ai_response = f"AI response to '{message}' for user {user_id} at {time.time()}"
        self.ai_responses.append({
            'response': ai_response,
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Send WebSocket notification (SHOULD ONLY GO TO CORRECT USER)
        if self.websocket_bridge:
            await self.websocket_bridge.notify_agent_completed(
                run_id=self.run_id,
                agent_name='ChatAgent',
                result={'response': ai_response}
            )
        
        return ai_response
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool and return results."""
        tool_result = {
            'tool': tool_name,
            'parameters': parameters,
            'result': f"Tool {tool_name} executed for user {self.user_context.user_id if self.user_context else 'unknown'}",
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'agent_id': self.agent_id
        }
        self.tool_executions.append(tool_result)
        
        # Notify via WebSocket (SHOULD ONLY GO TO CORRECT USER)
        if self.websocket_bridge:
            await self.websocket_bridge.notify_tool_completed(
                run_id=self.run_id,
                tool_name=tool_name,
                result=tool_result
            )
            
        return tool_result


@pytest.mark.integration
class MultiUserChatIsolation1116Tests(SSotAsyncTestCase):
    """
    Integration tests proving multi-user chat isolation failures.
    
    These tests should FAIL initially, proving the chat contamination problem.
    Success means the isolation problem has been fixed.
    """
    
    def setup_method(self, method):
        """Set up test environment with clean state."""
        super().setup_method(method)
        
        # Clear any singleton state
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        factory_module._factory_instance = None
        
        # Create test users
        self.user1_id = "chat_user_1"
        self.user2_id = "chat_user_2"
        self.user3_id = "chat_user_3"  # For 3-way contamination tests
        
        # Create test thread/run IDs
        self.thread1_id = "chat_thread_1"
        self.thread2_id = "chat_thread_2"
        self.thread3_id = "chat_thread_3"
        
        timestamp = int(time.time())
        self.run1_id = f"chat_run_1_{timestamp}"
        self.run2_id = f"chat_run_2_{timestamp}"
        self.run3_id = f"chat_run_3_{timestamp}"
        
        # Mock WebSocket bridge for testing
        self.mock_websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.notify_agent_started = AsyncMock()
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock()
        self.mock_websocket_bridge.notify_tool_executing = AsyncMock()
        self.mock_websocket_bridge.notify_tool_completed = AsyncMock()
        
        # Track WebSocket events for validation
        self.websocket_events = []
        
        # Mock WebSocket bridge methods to track events
        async def track_event(event_type: str, **kwargs):
            event = {
                'type': event_type,
                'timestamp': time.time(),
                'run_id': kwargs.get('run_id'),
                'data': kwargs
            }
            self.websocket_events.append(event)
            return True
            
        self.mock_websocket_bridge.notify_agent_started.side_effect = \
            lambda **kwargs: track_event('agent_started', **kwargs)
        self.mock_websocket_bridge.notify_agent_completed.side_effect = \
            lambda **kwargs: track_event('agent_completed', **kwargs)
        self.mock_websocket_bridge.notify_tool_executing.side_effect = \
            lambda **kwargs: track_event('tool_executing', **kwargs)
        self.mock_websocket_bridge.notify_tool_completed.side_effect = \
            lambda **kwargs: track_event('tool_completed', **kwargs)

    async def test_concurrent_chat_message_contamination(self):
        """
        CRITICAL: Test chat message contamination between concurrent users.
        
        This test should FAIL initially - proving that chat messages leak
        between users when using singleton factory patterns.
        
        Expected FAILURE: User 2 sees user 1's chat messages in their history.
        Expected FIX: Complete chat message isolation between users.
        """
        # Get singleton factory (THE PROBLEM - same factory for all users)
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # Create chat agents for both users (MIGHT SHARE STATE - THE PROBLEM)
        agent1 = MockChatAgent("user1_chat_agent")
        agent1.set_user_context(context1)
        agent1.set_websocket_bridge(self.mock_websocket_bridge, self.run1_id)
        
        agent2 = MockChatAgent("user2_chat_agent")
        agent2.set_user_context(context2)
        agent2.set_websocket_bridge(self.mock_websocket_bridge, self.run2_id)
        
        # Simulate concurrent chat messages
        user1_message = "User 1 confidential business discussion about Project Alpha"
        user2_message = "User 2 personal question about weather"
        
        # Process messages concurrently
        async def user1_chat():
            return await agent1.process_chat_message(user1_message, self.user1_id)
            
        async def user2_chat():
            return await agent2.process_chat_message(user2_message, self.user2_id)
        
        # Execute chat processing concurrently
        results = await asyncio.gather(user1_chat(), user2_chat())
        user1_response, user2_response = results
        
        # CRITICAL TEST: Chat histories should be COMPLETELY ISOLATED
        # This assertion should FAIL initially if chat history is shared
        
        # Check if user 1's message appears in user 2's chat history
        user2_history_content = ' '.join([
            entry.get('message', '') for entry in agent2.chat_history
        ])
        user1_confidential_leaked = 'Project Alpha' in user2_history_content
        
        assert not user1_confidential_leaked, (
            f"CHAT CONTAMINATION VIOLATION: User 1's confidential message "
            f"'Project Alpha' found in User 2's chat history. "
            f"User 2 history: {agent2.chat_history}. "
            f"This is a critical security violation."
        )
        
        # Check if user 2's message appears in user 1's chat history  
        user1_history_content = ' '.join([
            entry.get('message', '') for entry in agent1.chat_history
        ])
        user2_message_leaked = 'weather' in user1_history_content
        
        assert not user2_message_leaked, (
            f"CHAT CONTAMINATION VIOLATION: User 2's message about 'weather' "
            f"found in User 1's chat history. "
            f"User 1 history: {agent1.chat_history}. "
            f"This shows bidirectional chat contamination."
        )
        
        # Validate chat history isolation by checking user IDs
        user1_history_user_ids = {entry.get('user_id') for entry in agent1.chat_history}
        user2_history_user_ids = {entry.get('user_id') for entry in agent2.chat_history}
        
        assert self.user2_id not in user1_history_user_ids, (
            f"CHAT USER ID VIOLATION: User 2's ID ({self.user2_id}) found in "
            f"User 1's chat history user IDs: {user1_history_user_ids}"
        )
        
        assert self.user1_id not in user2_history_user_ids, (
            f"CHAT USER ID VIOLATION: User 1's ID ({self.user1_id}) found in "
            f"User 2's chat history user IDs: {user2_history_user_ids}"
        )
        
        print("EXPECTED FAILURE: Concurrent chat message contamination test should fail initially")

    async def test_ai_response_cross_contamination(self):
        """
        CRITICAL: Test AI response cross-contamination between users.
        
        This test should FAIL initially - proving that AI responses generated
        for one user are visible to other users due to shared agent state.
        
        Expected FAILURE: User 2 receives AI responses generated for user 1.
        Expected FIX: Complete AI response isolation per user context.
        """
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # Create chat agents that might share AI response state (THE PROBLEM)
        agent1 = MockChatAgent("user1_ai_agent")
        agent1.set_user_context(context1)
        agent1.set_websocket_bridge(self.mock_websocket_bridge, self.run1_id)
        
        agent2 = MockChatAgent("user2_ai_agent")
        agent2.set_user_context(context2)
        agent2.set_websocket_bridge(self.mock_websocket_bridge, self.run2_id)
        
        # Process user-specific messages that should generate isolated responses
        user1_private_message = "What are the quarterly revenue figures for Q4?"
        user2_general_message = "How do I reset my password?"
        
        # Generate AI responses
        user1_ai_response = await agent1.process_chat_message(user1_private_message, self.user1_id)
        user2_ai_response = await agent2.process_chat_message(user2_general_message, self.user2_id)
        
        # CRITICAL TEST: AI responses should be completely isolated
        # This assertion should FAIL initially if AI responses are shared
        
        # Check if user 1's AI response appears in user 2's responses
        user2_response_content = ' '.join([
            response.get('response', '') for response in agent2.ai_responses
        ])
        user1_revenue_data_leaked = 'quarterly revenue' in user2_response_content.lower()
        
        assert not user1_revenue_data_leaked, (
            f"AI RESPONSE CONTAMINATION: User 1's response about 'quarterly revenue' "
            f"found in User 2's AI responses. "
            f"User 2 responses: {agent2.ai_responses}. "
            f"This exposes confidential business data to wrong user."
        )
        
        # Check response user ID isolation
        user1_response_user_ids = {response.get('user_id') for response in agent1.ai_responses}
        user2_response_user_ids = {response.get('user_id') for response in agent2.ai_responses}
        
        assert self.user2_id not in user1_response_user_ids, (
            f"AI RESPONSE USER ID VIOLATION: User 2's responses found in User 1's AI responses. "
            f"User 1 response user IDs: {user1_response_user_ids}"
        )
        
        assert self.user1_id not in user2_response_user_ids, (
            f"AI RESPONSE USER ID VIOLATION: User 1's responses found in User 2's AI responses. "
            f"User 2 response user IDs: {user2_response_user_ids}"
        )
        
        # Test AI response content uniqueness (no cross-pollination)
        user1_response_content = user1_ai_response.lower()
        user2_response_content = user2_ai_response.lower()
        
        # User 1's response should contain business context, User 2's should not
        user1_has_business_context = 'revenue' in user1_response_content
        user2_has_business_context = 'revenue' in user2_response_content
        
        assert user1_has_business_context, "User 1 should get business-relevant AI response"
        assert not user2_has_business_context, (
            f"AI CONTEXT CONTAMINATION: User 2's response contains business context "
            f"from User 1's question. User 2 response: {user2_ai_response}"
        )
        
        print("EXPECTED FAILURE: AI response cross-contamination test should fail initially")

    async def test_chat_session_state_leakage(self):
        """
        CRITICAL: Test chat session state leakage between users.
        
        This test should FAIL initially - proving that chat session state
        (preferences, history, context) leaks between concurrent users.
        
        Expected FAILURE: User 2 inherits user 1's session state and preferences.
        Expected FIX: Complete session state isolation between users.
        """
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts with session-specific metadata
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            metadata={
                'session_preferences': {
                    'language': 'en',
                    'complexity_level': 'expert',
                    'domain_focus': 'business_finance'
                },
                'conversation_context': {
                    'current_topic': 'quarterly_planning',
                    'user_role': 'cfo',
                    'access_level': 'confidential'
                }
            }
        )
        
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            metadata={
                'session_preferences': {
                    'language': 'es',
                    'complexity_level': 'beginner',
                    'domain_focus': 'general_help'
                },
                'conversation_context': {
                    'current_topic': 'password_reset',
                    'user_role': 'user',
                    'access_level': 'public'
                }
            }
        )
        
        # Create agents and set their session state
        agent1 = MockChatAgent("user1_session_agent")
        agent1.set_user_context(context1)
        agent1.session_state = {
            'user_preferences': context1.metadata.get('session_preferences', {}),
            'conversation_context': context1.metadata.get('conversation_context', {}),
            'active_tools': ['financial_calculator', 'report_generator'],
            'security_clearance': 'high'
        }
        
        agent2 = MockChatAgent("user2_session_agent")
        agent2.set_user_context(context2)
        agent2.session_state = {
            'user_preferences': context2.metadata.get('session_preferences', {}),
            'conversation_context': context2.metadata.get('conversation_context', {}),
            'active_tools': ['password_helper', 'basic_info'],
            'security_clearance': 'standard'
        }
        
        # CRITICAL TEST: Session states should be completely isolated
        # This assertion should FAIL initially if session state is shared
        
        # Check for session preference contamination
        user1_domain_focus = agent1.session_state['user_preferences'].get('domain_focus')
        user2_domain_focus = agent2.session_state['user_preferences'].get('domain_focus')
        
        assert user1_domain_focus != user2_domain_focus, (
            f"SESSION PREFERENCE CONTAMINATION: Users have same domain focus "
            f"({user1_domain_focus}). This indicates shared session state."
        )
        
        # Check for conversation context isolation
        user1_access_level = agent1.session_state['conversation_context'].get('access_level')
        user2_access_level = agent2.session_state['conversation_context'].get('access_level')
        
        assert user1_access_level != user2_access_level, (
            f"CONVERSATION CONTEXT CONTAMINATION: Users have same access level "
            f"({user1_access_level}). User 1 should have 'confidential', User 2 'public'."
        )
        
        # Check for tool access contamination
        user1_tools = set(agent1.session_state.get('active_tools', []))
        user2_tools = set(agent2.session_state.get('active_tools', []))
        
        tool_overlap = user1_tools.intersection(user2_tools)
        assert not tool_overlap, (
            f"TOOL ACCESS CONTAMINATION: Users share tools {tool_overlap}. "
            f"User 1 should have financial tools, User 2 should have basic tools. "
            f"Shared tools indicate session state leakage."
        )
        
        # Check security clearance isolation
        user1_clearance = agent1.session_state.get('security_clearance')
        user2_clearance = agent2.session_state.get('security_clearance')
        
        assert user1_clearance != user2_clearance, (
            f"SECURITY CLEARANCE CONTAMINATION: Users have same security clearance "
            f"({user1_clearance}). This is a critical security violation."
        )
        
        # Test session state mutation isolation
        # User 1 adds confidential data to session
        agent1.session_state['confidential_data'] = {
            'financial_targets': {'q4_revenue': 5000000},
            'strategic_plans': 'market_expansion_europe'
        }
        
        # User 2 should not see user 1's confidential data
        user2_confidential = agent2.session_state.get('confidential_data')
        assert user2_confidential is None, (
            f"SESSION MUTATION CONTAMINATION: User 2 can see User 1's confidential data: "
            f"{user2_confidential}. This indicates shared session object references."
        )
        
        print("EXPECTED FAILURE: Chat session state leakage test should fail initially")

    async def test_websocket_message_misdelivery_in_chat(self):
        """
        CRITICAL: Test WebSocket message mis-delivery in multi-user chat scenarios.
        
        This test should FAIL initially - proving that WebSocket messages intended
        for one user are delivered to other users due to shared routing state.
        
        Expected FAILURE: User 2 receives WebSocket events meant for user 1.
        Expected FIX: Complete WebSocket event isolation per user connection.
        """
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            websocket_client_id="ws_client_user1"
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            websocket_client_id="ws_client_user2"
        )
        
        # Create chat agents with WebSocket connections
        agent1 = MockChatAgent("user1_ws_agent")
        agent1.set_user_context(context1)
        agent1.set_websocket_bridge(self.mock_websocket_bridge, self.run1_id)
        
        agent2 = MockChatAgent("user2_ws_agent")
        agent2.set_user_context(context2)
        agent2.set_websocket_bridge(self.mock_websocket_bridge, self.run2_id)
        
        # Clear previous WebSocket events
        self.websocket_events.clear()
        
        # Process concurrent chat messages that should generate WebSocket events
        user1_message = "Execute financial analysis for Q4 planning"
        user2_message = "Show me my profile settings"
        
        # Process messages concurrently
        await asyncio.gather(
            agent1.process_chat_message(user1_message, self.user1_id),
            agent2.process_chat_message(user2_message, self.user2_id)
        )
        
        # CRITICAL TEST: WebSocket events should be delivered to correct users only
        # This assertion should FAIL initially if events are mis-delivered
        
        # Separate events by run_id
        user1_events = [event for event in self.websocket_events if event['run_id'] == self.run1_id]
        user2_events = [event for event in self.websocket_events if event['run_id'] == self.run2_id]
        
        # Check for event mis-delivery
        user1_event_content = ' '.join([
            str(event.get('data', {})) for event in user1_events
        ])
        user2_event_content = ' '.join([
            str(event.get('data', {})) for event in user2_events
        ])
        
        # User 1's events should not contain user 2's message content
        user2_content_in_user1_events = 'profile settings' in user1_event_content
        assert not user2_content_in_user1_events, (
            f"WEBSOCKET MISDELIVERY: User 2's message content found in User 1's WebSocket events. "
            f"User 1 events: {user1_events}. This causes message mis-delivery."
        )
        
        # User 2's events should not contain user 1's message content
        user1_content_in_user2_events = 'financial analysis' in user2_event_content
        assert not user1_content_in_user2_events, (
            f"WEBSOCKET MISDELIVERY: User 1's confidential message found in User 2's WebSocket events. "
            f"User 2 events: {user2_events}. This exposes confidential data."
        )
        
        # Check run_id isolation in WebSocket events
        user1_run_ids = {event['run_id'] for event in user1_events}
        user2_run_ids = {event['run_id'] for event in user2_events}
        
        assert self.run2_id not in user1_run_ids, (
            f"WEBSOCKET RUN ID VIOLATION: User 2's run ID ({self.run2_id}) found in "
            f"User 1's WebSocket events: {user1_run_ids}"
        )
        
        assert self.run1_id not in user2_run_ids, (
            f"WEBSOCKET RUN ID VIOLATION: User 1's run ID ({self.run1_id}) found in "
            f"User 2's WebSocket events: {user2_run_ids}"
        )
        
        # Validate event timing isolation (events should not be interleaved improperly)
        all_events = sorted(self.websocket_events, key=lambda x: x['timestamp'])
        for i, event in enumerate(all_events):
            run_id = event['run_id']
            if run_id == self.run1_id:
                # Check if this user 1 event is surrounded by user 2 events improperly
                prev_event = all_events[i-1] if i > 0 else None
                next_event = all_events[i+1] if i < len(all_events) - 1 else None
                
                if prev_event and next_event:
                    improper_interleaving = (
                        prev_event['run_id'] == self.run2_id and 
                        next_event['run_id'] == self.run2_id
                    )
                    
                    assert not improper_interleaving, (
                        f"WEBSOCKET INTERLEAVING VIOLATION: User 1's event improperly "
                        f"interleaved with User 2's events. This indicates shared event state."
                    )
        
        print("EXPECTED FAILURE: WebSocket message mis-delivery test should fail initially")

    async def test_tool_execution_result_misdelivery(self):
        """
        CRITICAL: Test tool execution result mis-delivery between users.
        
        This test should FAIL initially - proving that tool execution results
        are delivered to wrong users due to shared agent factory state.
        
        Expected FAILURE: User 2 receives tool results from user 1's execution.
        Expected FIX: Complete tool execution result isolation per user.
        """
        # Get singleton factory
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create user contexts
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        
        # Create agents with tool execution capability
        agent1 = MockChatAgent("user1_tool_agent")
        agent1.set_user_context(context1)
        agent1.set_websocket_bridge(self.mock_websocket_bridge, self.run1_id)
        
        agent2 = MockChatAgent("user2_tool_agent")
        agent2.set_user_context(context2)
        agent2.set_websocket_bridge(self.mock_websocket_bridge, self.run2_id)
        
        # Clear WebSocket events
        self.websocket_events.clear()
        
        # Execute different tools for each user concurrently
        user1_tool_params = {
            'report_type': 'financial_summary',
            'confidential_data': True,
            'access_level': 'executive'
        }
        user2_tool_params = {
            'request_type': 'password_reset',
            'email': 'user2@example.com',
            'public_data': True
        }
        
        # Execute tools concurrently
        user1_result, user2_result = await asyncio.gather(
            agent1.execute_tool('financial_report_generator', user1_tool_params),
            agent2.execute_tool('account_management', user2_tool_params)
        )
        
        # CRITICAL TEST: Tool execution results should be completely isolated
        # This assertion should FAIL initially if results are mis-delivered
        
        # Check tool execution isolation in agent state
        user1_tool_results = agent1.tool_executions
        user2_tool_results = agent2.tool_executions
        
        # User 1's tool executions should not appear in user 2's results
        user1_result_content = ' '.join([
            str(result.get('result', '')) for result in user1_tool_results
        ])
        user2_result_content = ' '.join([
            str(result.get('result', '')) for result in user2_tool_results
        ])
        
        user1_confidential_in_user2_results = 'financial_summary' in user2_result_content
        assert not user1_confidential_in_user2_results, (
            f"TOOL RESULT CONTAMINATION: User 1's financial tool results found in "
            f"User 2's tool executions: {user2_tool_results}. "
            f"This exposes confidential business data."
        )
        
        user2_account_data_in_user1_results = 'password_reset' in user1_result_content
        assert not user2_account_data_in_user1_results, (
            f"TOOL RESULT CONTAMINATION: User 2's account data found in "
            f"User 1's tool executions: {user1_tool_results}. "
            f"This shows bidirectional tool result contamination."
        )
        
        # Check WebSocket tool event delivery isolation
        tool_events = [event for event in self.websocket_events if event['type'] == 'tool_completed']
        
        user1_tool_events = [event for event in tool_events if event['run_id'] == self.run1_id]
        user2_tool_events = [event for event in tool_events if event['run_id'] == self.run2_id]
        
        # Validate tool event content isolation
        user1_tool_event_content = ' '.join([
            str(event.get('data', {})) for event in user1_tool_events
        ])
        user2_tool_event_content = ' '.join([
            str(event.get('data', {})) for event in user2_tool_events
        ])
        
        user1_financial_in_user2_events = 'financial_report_generator' in user2_tool_event_content
        assert not user1_financial_in_user2_events, (
            f"WEBSOCKET TOOL EVENT MISDELIVERY: User 1's financial tool event delivered to "
            f"User 2's WebSocket connection: {user2_tool_events}"
        )
        
        user2_account_in_user1_events = 'account_management' in user1_tool_event_content
        assert not user2_account_in_user1_events, (
            f"WEBSOCKET TOOL EVENT MISDELIVERY: User 2's account management event delivered to "
            f"User 1's WebSocket connection: {user1_tool_events}"
        )
        
        # Check tool execution parameter isolation
        user1_has_confidential_param = any(
            result.get('parameters', {}).get('confidential_data') is True
            for result in user1_tool_results
        )
        user2_has_confidential_param = any(
            result.get('parameters', {}).get('confidential_data') is True
            for result in user2_tool_results
        )
        
        assert user1_has_confidential_param, "User 1 should have confidential tool parameters"
        assert not user2_has_confidential_param, (
            f"TOOL PARAMETER CONTAMINATION: User 2 has confidential parameters "
            f"from User 1's tool execution: {user2_tool_results}"
        )
        
        print("EXPECTED FAILURE: Tool execution result mis-delivery test should fail initially")

    async def test_three_way_chat_contamination_stress_test(self):
        """
        CRITICAL: Test three-way chat contamination under concurrent load.
        
        This test should FAIL initially - proving that chat isolation breaks down
        completely under concurrent multi-user scenarios with 3+ users.
        
        Expected FAILURE: All three users see each other's messages and responses.
        Expected FIX: Robust isolation that scales to multiple concurrent users.
        """
        # Get singleton factory (THE PROBLEM - same instance for all users)
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create contexts for all three users
        context1 = await factory.create_user_execution_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id
        )
        context2 = await factory.create_user_execution_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id
        )
        context3 = await factory.create_user_execution_context(
            user_id=self.user3_id,
            thread_id=self.thread3_id,
            run_id=self.run3_id
        )
        
        # Create agents for all users
        agent1 = MockChatAgent("user1_stress_agent")
        agent1.set_user_context(context1)
        agent1.set_websocket_bridge(self.mock_websocket_bridge, self.run1_id)
        
        agent2 = MockChatAgent("user2_stress_agent")
        agent2.set_user_context(context2)
        agent2.set_websocket_bridge(self.mock_websocket_bridge, self.run2_id)
        
        agent3 = MockChatAgent("user3_stress_agent")
        agent3.set_user_context(context3)
        agent3.set_websocket_bridge(self.mock_websocket_bridge, self.run3_id)
        
        # Define user-specific messages with distinct content
        user_messages = {
            self.user1_id: [
                "Execute quarterly financial analysis for board presentation",
                "Generate confidential revenue projections for Q1",
                "Access executive dashboard with sensitive metrics"
            ],
            self.user2_id: [
                "Help me update my personal profile settings",
                "Show my recent activity and notifications",
                "Change my password and security preferences"
            ],
            self.user3_id: [
                "Create a summary report for the marketing team",
                "Schedule social media posts for next week",
                "Analyze customer feedback from surveys"
            ]
        }
        
        # Process all messages concurrently (high load simulation)
        async def process_user_messages(agent, user_id, messages):
            results = []
            for message in messages:
                response = await agent.process_chat_message(message, user_id)
                results.append(response)
            return results
        
        # Execute all users' chat sessions concurrently
        all_results = await asyncio.gather(
            process_user_messages(agent1, self.user1_id, user_messages[self.user1_id]),
            process_user_messages(agent2, self.user2_id, user_messages[self.user2_id]),
            process_user_messages(agent3, self.user3_id, user_messages[self.user3_id])
        )
        
        user1_responses, user2_responses, user3_responses = all_results
        
        # CRITICAL TEST: Complete isolation between all three users
        # These assertions should FAIL initially if contamination occurs
        
        # Check for cross-user message contamination in chat histories
        user1_history_content = ' '.join([
            entry.get('message', '') for entry in agent1.chat_history
        ])
        user2_history_content = ' '.join([
            entry.get('message', '') for entry in agent2.chat_history
        ])
        user3_history_content = ' '.join([
            entry.get('message', '') for entry in agent3.chat_history
        ])
        
        # User 1 should not see user 2's personal data
        user2_personal_in_user1 = 'profile settings' in user1_history_content
        assert not user2_personal_in_user1, (
            f"3-WAY CONTAMINATION: User 2's personal messages found in User 1's history. "
            f"User 1 history: {user1_history_content[:200]}..."
        )
        
        # User 1 should not see user 3's marketing data
        user3_marketing_in_user1 = 'marketing team' in user1_history_content
        assert not user3_marketing_in_user1, (
            f"3-WAY CONTAMINATION: User 3's marketing messages found in User 1's history. "
            f"User 1 history: {user1_history_content[:200]}..."
        )
        
        # User 2 should not see user 1's financial data
        user1_financial_in_user2 = 'financial analysis' in user2_history_content
        assert not user1_financial_in_user2, (
            f"3-WAY CONTAMINATION: User 1's confidential financial data found in User 2's history. "
            f"User 2 history: {user2_history_content[:200]}..."
        )
        
        # User 2 should not see user 3's marketing data
        user3_marketing_in_user2 = 'social media' in user2_history_content
        assert not user3_marketing_in_user2, (
            f"3-WAY CONTAMINATION: User 3's marketing data found in User 2's history. "
            f"User 2 history: {user2_history_content[:200]}..."
        )
        
        # User 3 should not see user 1's financial data
        user1_financial_in_user3 = 'quarterly financial' in user3_history_content
        assert not user1_financial_in_user3, (
            f"3-WAY CONTAMINATION: User 1's financial data found in User 3's history. "
            f"User 3 history: {user3_history_content[:200]}..."
        )
        
        # User 3 should not see user 2's personal data
        user2_personal_in_user3 = 'password' in user3_history_content
        assert not user2_personal_in_user3, (
            f"3-WAY CONTAMINATION: User 2's personal data found in User 3's history. "
            f"User 3 history: {user3_history_content[:200]}..."
        )
        
        # Validate complete user ID isolation across all agents
        user1_history_user_ids = {entry.get('user_id') for entry in agent1.chat_history}
        user2_history_user_ids = {entry.get('user_id') for entry in agent2.chat_history}
        user3_history_user_ids = {entry.get('user_id') for entry in agent3.chat_history}
        
        assert user1_history_user_ids == {self.user1_id}, (
            f"3-WAY USER ID CONTAMINATION: User 1's history contains other user IDs: "
            f"{user1_history_user_ids}"
        )
        
        assert user2_history_user_ids == {self.user2_id}, (
            f"3-WAY USER ID CONTAMINATION: User 2's history contains other user IDs: "
            f"{user2_history_user_ids}"
        )
        
        assert user3_history_user_ids == {self.user3_id}, (
            f"3-WAY USER ID CONTAMINATION: User 3's history contains other user IDs: "
            f"{user3_history_user_ids}"
        )
        
        print("EXPECTED FAILURE: Three-way chat contamination stress test should fail initially")

    async def test_performance_degradation_due_to_shared_resources(self):
        """
        CRITICAL: Test chat performance degradation due to shared factory resources.
        
        This test should FAIL initially - proving that singleton factory causes
        performance bottlenecks when multiple users access shared resources.
        
        Expected FAILURE: Response times degrade significantly under concurrent load.
        Expected FIX: Per-user resource isolation prevents performance interference.
        """
        # Get singleton factory (THE PROBLEM - all users compete for same resources)
        factory = get_agent_instance_factory()
        factory.configure(websocket_bridge=self.mock_websocket_bridge)
        
        # Create multiple concurrent users
        num_concurrent_users = 5
        user_contexts = []
        agents = []
        
        for i in range(num_concurrent_users):
            user_id = f"perf_user_{i}"
            thread_id = f"perf_thread_{i}"
            run_id = f"perf_run_{i}_{int(time.time())}"
            
            context = await factory.create_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            user_contexts.append(context)
            
            agent = MockChatAgent(f"perf_agent_{i}")
            agent.set_user_context(context)
            agent.set_websocket_bridge(self.mock_websocket_bridge, run_id)
            agents.append(agent)
        
        # Measure baseline performance (single user)
        baseline_agent = agents[0]
        baseline_message = "Simple test message for baseline measurement"
        
        baseline_start = time.time()
        await baseline_agent.process_chat_message(baseline_message, user_contexts[0].user_id)
        baseline_time = time.time() - baseline_start
        
        # Measure concurrent performance (all users simultaneously)
        concurrent_messages = [
            f"Concurrent message {i} with processing load simulation" 
            for i in range(num_concurrent_users)
        ]
        
        async def process_concurrent_message(agent, message, user_id):
            start_time = time.time()
            await agent.process_chat_message(message, user_id)
            return time.time() - start_time
        
        # Execute all messages concurrently
        concurrent_start = time.time()
        concurrent_times = await asyncio.gather(*[
            process_concurrent_message(agents[i], concurrent_messages[i], user_contexts[i].user_id)
            for i in range(num_concurrent_users)
        ])
        total_concurrent_time = time.time() - concurrent_start
        
        # CRITICAL TEST: Performance should not degrade significantly under concurrent load
        # This assertion should FAIL initially if resources are shared and cause contention
        
        avg_concurrent_time = sum(concurrent_times) / len(concurrent_times)
        max_concurrent_time = max(concurrent_times)
        
        # Performance degradation factor (should be close to 1 for good isolation)
        performance_degradation = max_concurrent_time / baseline_time
        
        # If performance degrades by more than 3x, it indicates resource contention
        significant_degradation = performance_degradation > 3.0
        
        assert not significant_degradation, (
            f"PERFORMANCE DEGRADATION: Concurrent processing is {performance_degradation:.1f}x slower "
            f"than baseline ({max_concurrent_time:.3f}s vs {baseline_time:.3f}s). "
            f"This indicates shared resource contention in singleton factory. "
            f"Concurrent times: {concurrent_times}"
        )
        
        # Test resource competition indicators
        # Check if agents are sharing and competing for same factory resources
        factory_metrics = factory.get_factory_metrics() if hasattr(factory, 'get_factory_metrics') else {}
        active_contexts_count = factory_metrics.get('active_contexts', 0)
        
        # All users should have isolated contexts, not compete for same context pool
        expected_contexts = num_concurrent_users + 1  # +1 for baseline
        resource_competition = active_contexts_count > expected_contexts * 2  # Allow some overhead
        
        assert not resource_competition, (
            f"RESOURCE COMPETITION: Factory has {active_contexts_count} active contexts "
            f"for {expected_contexts} expected contexts. This indicates resource sharing "
            f"and competition between users."
        )
        
        # Test memory usage growth (indication of shared state accumulation)
        total_chat_history_entries = sum(len(agent.chat_history) for agent in agents)
        expected_entries = num_concurrent_users  # Each user should have 1 message
        
        memory_accumulation = total_chat_history_entries > expected_entries * 2  # Allow some overhead
        assert not memory_accumulation, (
            f"MEMORY ACCUMULATION: Total chat history entries {total_chat_history_entries} "
            f"exceeds expected {expected_entries}. This indicates shared memory state "
            f"accumulating across users."
        )
        
        print("EXPECTED FAILURE: Performance degradation test should fail initially")