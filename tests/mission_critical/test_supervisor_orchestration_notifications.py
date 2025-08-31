#!/usr/bin/env python
"""
Test Supervisor Orchestration-Level WebSocket Notifications

This test validates that the supervisor sends high-level orchestration notifications
in addition to the low-level agent and tool events.

CRITICAL: This ensures users see meaningful progress updates during complex workflows.
"""

import asyncio
import os
import sys
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.base.interface import ExecutionContext


class MockWebSocketManager:
    """Mock WebSocket manager that captures orchestration events."""
    
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.orchestration_events: List[Dict[str, Any]] = []
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Capture sent messages and identify orchestration events."""
        self.sent_messages.append({
            'thread_id': thread_id,
            'message': message,
            'timestamp': asyncio.get_event_loop().time()
        })
        
        # Check if this is an orchestration-level event
        payload = message.get('payload', {})
        if payload.get('orchestration_level') == True:
            self.orchestration_events.append({
                'event_type': payload.get('event_type'),
                'message': payload.get('message'),
                'agent_name': payload.get('agent_name'),
                'thread_id': thread_id
            })
            logger.info(f"🎯 ORCHESTRATION EVENT: {payload.get('event_type')} - {payload.get('message')}")
        
        return True
    
    def get_orchestration_events(self) -> List[Dict[str, Any]]:
        """Get all orchestration-level events."""
        return self.orchestration_events
    
    def get_orchestration_event_types(self) -> List[str]:
        """Get orchestration event types in order."""
        return [event['event_type'] for event in self.orchestration_events]


class TestSupervisorOrchestrationNotifications:
    """Test supervisor orchestration-level WebSocket notifications."""
    
    @pytest.fixture
    async def mock_setup(self):
        """Set up mock components for testing."""
        # Create mock components
        mock_db_session = AsyncMock()
        mock_llm_manager = MagicMock(spec=LLMManager)
        mock_websocket_manager = MockWebSocketManager()
        
        # Create proper mock tool dispatcher with executor attribute
        mock_tool_dispatcher = MagicMock(spec=ToolDispatcher)
        mock_tool_dispatcher.executor = MagicMock()
        mock_tool_dispatcher._websocket_enhanced = False
        
        # Create supervisor with mocks
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            websocket_manager=mock_websocket_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        return {
            'supervisor': supervisor,
            'websocket_manager': mock_websocket_manager,
            'db_session': mock_db_session
        }
    
    @pytest.mark.asyncio
    async def test_supervisor_sends_orchestration_notifications(self, mock_setup):
        """Test that supervisor sends orchestration-level notifications during execution."""
        supervisor = mock_setup['supervisor']
        websocket_manager = mock_setup['websocket_manager']
        
        # Mock the workflow executor to avoid complex pipeline execution
        supervisor.workflow_executor.execute_workflow_steps = AsyncMock(return_value=DeepAgentState())
        
        # Test data
        user_prompt = "Analyze my infrastructure costs and suggest optimizations"
        thread_id = "test-thread-123"
        user_id = "test-user-456"
        run_id = "test-run-789"
        
        # Execute supervisor workflow
        logger.info("🚀 Starting supervisor orchestration test")
        await supervisor.run(user_prompt, thread_id, user_id, run_id)
        
        # Verify orchestration events were sent
        orchestration_events = websocket_manager.get_orchestration_events()
        event_types = websocket_manager.get_orchestration_event_types()
        
        logger.info(f"📊 Captured {len(orchestration_events)} orchestration events")
        for event in orchestration_events:
            logger.info(f"   • {event['event_type']}: {event['message'][:50]}...")
        
        # Validate orchestration events were sent
        assert len(orchestration_events) > 0, "No orchestration events were sent!"
        
        # Check for expected orchestration event types
        expected_events = {
            'orchestration_started',
            'orchestration_thinking', 
            'orchestration_delegating',
            'orchestration_completed'
        }
        
        sent_event_types = set(event_types)
        found_events = expected_events.intersection(sent_event_types)
        
        logger.info(f"✅ Found orchestration events: {found_events}")
        
        # We should have at least some orchestration events
        assert len(found_events) > 0, f"No expected orchestration events found. Got: {event_types}"
        
        # Verify all events are marked as orchestration level
        for event in orchestration_events:
            assert event['agent_name'] == 'supervisor', f"Expected supervisor, got {event['agent_name']}"
        
        logger.info("✅ Supervisor orchestration notifications test PASSED!")
    
    @pytest.mark.asyncio
    async def test_orchestration_notifications_have_meaningful_messages(self, mock_setup):
        """Test that orchestration notifications contain meaningful user-facing messages."""
        supervisor = mock_setup['supervisor']
        websocket_manager = mock_setup['websocket_manager']
        
        # Mock workflow execution
        supervisor.workflow_executor.execute_workflow_steps = AsyncMock(return_value=DeepAgentState())
        
        # Execute workflow
        await supervisor.run("Test request", "thread-123", "user-456", "run-789")
        
        # Get orchestration events
        orchestration_events = websocket_manager.get_orchestration_events()
        
        # Verify messages are meaningful
        for event in orchestration_events:
            message = event['message']
            
            # Messages should be non-empty and user-friendly
            assert len(message) > 10, f"Message too short: '{message}'"
            assert not message.startswith('ERROR'), f"Error in message: '{message}'"
            
            # Messages should contain relevant context
            common_words = ['process', 'request', 'agent', 'analyz', 'delegat', 'complet', 'task']
            has_relevant_word = any(word in message.lower() for word in common_words)
            assert has_relevant_word, f"Message lacks relevant context: '{message}'"
        
        logger.info("✅ Orchestration message quality test PASSED!")
    
    @pytest.mark.asyncio
    async def test_orchestration_events_include_proper_metadata(self, mock_setup):
        """Test that orchestration events include proper metadata."""
        supervisor = mock_setup['supervisor']
        websocket_manager = mock_setup['websocket_manager']
        
        # Mock workflow execution
        supervisor.workflow_executor.execute_workflow_steps = AsyncMock(return_value=DeepAgentState())
        
        test_thread_id = "thread-test-metadata"
        test_run_id = "run-test-metadata"
        
        # Execute workflow
        await supervisor.run("Test request", test_thread_id, "user-123", test_run_id)
        
        # Check all sent messages for orchestration events
        for sent_message in websocket_manager.sent_messages:
            payload = sent_message['message'].get('payload', {})
            
            if payload.get('orchestration_level') == True:
                # Verify required metadata fields
                assert 'run_id' in payload, "Missing run_id in orchestration event"
                assert 'event_type' in payload, "Missing event_type in orchestration event"
                assert 'timestamp' in payload, "Missing timestamp in orchestration event"
                assert 'agent_name' in payload, "Missing agent_name in orchestration event"
                
                # Verify values
                assert payload['run_id'] == test_run_id, f"Wrong run_id: {payload['run_id']}"
                assert payload['agent_name'] == 'supervisor', f"Wrong agent_name: {payload['agent_name']}"
                assert sent_message['thread_id'] == test_thread_id, f"Wrong thread_id: {sent_message['thread_id']}"
        
        logger.info("✅ Orchestration metadata test PASSED!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])