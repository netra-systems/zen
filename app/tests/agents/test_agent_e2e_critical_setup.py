"""
Setup fixtures and base test class for critical end-to-end agent tests.
Provides shared infrastructure and mocks for agent testing.
"""

import pytest
import json
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.schemas import (
    SubAgentLifecycle, WebSocketMessage, AgentStarted, 
    SubAgentUpdate, AgentCompleted, SubAgentState
)
from app.llm.llm_manager import LLMManager
from app.services.agent_service import AgentService
from app.services.websocket.message_handler import BaseMessageHandler
from app.services.state_persistence_service import state_persistence_service
from app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from sqlalchemy.ext.asyncio import AsyncSession


class AgentE2ETestBase:
    """Base class for critical end-to-end agent tests"""

    @pytest.fixture
    def setup_agent_infrastructure(self):
        """Setup complete agent infrastructure for testing"""
        # Mock database session
        db_session = AsyncMock(spec=AsyncSession)
        db_session.commit = AsyncMock()
        db_session.rollback = AsyncMock()
        db_session.close = AsyncMock()
        
        # Mock LLM Manager with proper JSON response for ask_llm
        llm_manager = Mock(spec=LLMManager)
        llm_manager.call_llm = AsyncMock(return_value={
            "content": "Test response",
            "tool_calls": []
        })
        # ask_llm should return a JSON string for triage and other agents
        llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
            "category": "optimization",
            "analysis": "Test analysis",
            "recommendations": ["Optimize GPU", "Reduce memory usage"]
        }))
        
        # Mock ask_structured_llm for TriageSubAgent
        from app.agents.triage_sub_agent import (
            TriageResult, Priority, Complexity, UserIntent, 
            ExtractedEntities, TriageMetadata
        )
        mock_triage_result = TriageResult(
            category="Cost Optimization",
            confidence_score=0.95,
            priority=Priority.MEDIUM,
            complexity=Complexity.MODERATE,
            is_admin_mode=False,
            extracted_entities=ExtractedEntities(
                models_mentioned=[],
                metrics_mentioned=[],
                time_ranges=[]
            ),
            user_intent=UserIntent(
                primary_intent="optimize",
                secondary_intents=["analyze"]
            ),
            tool_recommendations=[],
            metadata=TriageMetadata(
                triage_duration_ms=100,
                cache_hit=False,
                fallback_used=False,
                retry_count=0
            )
        )
        llm_manager.ask_structured_llm = AsyncMock(return_value=mock_triage_result)
        
        # Mock WebSocket Manager
        websocket_manager = Mock()
        websocket_manager.send_message = AsyncMock()
        websocket_manager.send_to_thread = AsyncMock()
        websocket_manager.broadcast = AsyncMock()
        websocket_manager.send_agent_log = AsyncMock()
        websocket_manager.send_error = AsyncMock()
        websocket_manager.send_sub_agent_update = AsyncMock()
        websocket_manager.active_connections = {}
        
        # Mock Tool Dispatcher
        tool_dispatcher = Mock(spec=ApexToolSelector)
        tool_dispatcher.dispatch_tool = AsyncMock(return_value={
            "status": "success",
            "result": "Tool executed successfully"
        })
        
        # Mock state persistence service
        with patch.object(state_persistence_service, 'save_agent_state', AsyncMock()):
            with patch.object(state_persistence_service, 'load_agent_state', AsyncMock(return_value=None)):
                with patch.object(state_persistence_service, 'get_thread_context', AsyncMock(return_value=None)):
                    # Create Supervisor
                    supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
                    supervisor.thread_id = str(uuid.uuid4())
                    supervisor.user_id = str(uuid.uuid4())
        
        # Create Agent Service with Supervisor
        agent_service = AgentService(supervisor)
        agent_service.websocket_manager = websocket_manager
        
        return {
            "supervisor": supervisor,
            "agent_service": agent_service,
            "db_session": db_session,
            "llm_manager": llm_manager,
            "websocket_manager": websocket_manager,
            "tool_dispatcher": tool_dispatcher
        }

    def create_test_request(self, query="Test optimization request"):
        """Create a standard test request"""
        return {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "query": query,
            "workloads": [],
            "constraints": {}
        }

    def create_websocket_message(self, message_type="start_agent", payload=None):
        """Create a test WebSocket message"""
        if payload is None:
            payload = {
                "settings": {"debug_mode": False},
                "request": self.create_test_request()
            }
        
        return WebSocketMessage(
            type=message_type,
            payload=payload,
            sender="test_client"
        )

    def assert_agent_lifecycle_complete(self, supervisor, expected_states=None):
        """Assert that agent lifecycle completed properly"""
        if expected_states is None:
            expected_states = [
                SubAgentLifecycle.PENDING,
                SubAgentLifecycle.RUNNING,
                SubAgentLifecycle.COMPLETED
            ]
        
        assert supervisor.current_state.lifecycle in expected_states
        assert supervisor.thread_id is not None
        assert supervisor.user_id is not None

    def assert_websocket_messages_sent(self, websocket_manager, min_messages=1):
        """Assert that WebSocket messages were sent"""
        total_calls = (
            websocket_manager.send_message.call_count +
            websocket_manager.send_to_thread.call_count +
            websocket_manager.send_agent_log.call_count +
            websocket_manager.send_sub_agent_update.call_count
        )
        assert total_calls >= min_messages

    def assert_tool_dispatcher_called(self, tool_dispatcher, min_calls=1):
        """Assert that tool dispatcher was called"""
        assert tool_dispatcher.dispatch_tool.call_count >= min_calls

    def assert_llm_manager_called(self, llm_manager, min_calls=1):
        """Assert that LLM manager was called"""
        total_calls = (
            llm_manager.call_llm.call_count +
            llm_manager.ask_llm.call_count +
            llm_manager.ask_structured_llm.call_count
        )
        assert total_calls >= min_calls