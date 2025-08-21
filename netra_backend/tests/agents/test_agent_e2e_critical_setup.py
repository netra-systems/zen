"""
Setup fixtures and base test class for critical end-to-end agent tests.
Provides shared infrastructure and mocks for agent testing.
"""

import pytest
import json
import uuid
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from schemas import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    SubAgentLifecycle, WebSocketMessage, AgentStarted, 
    SubAgentUpdate, AgentCompleted, SubAgentState
)
from llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.websocket.message_handler import BaseMessageHandler
from netra_backend.app.services.state_persistence import state_persistence_service
from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from sqlalchemy.ext.asyncio import AsyncSession


class AgentE2ETestBase:
    """Base class for critical end-to-end agent tests"""

    def _create_mock_db_session(self):
        """Create mock database session with async context manager support"""
        db_session = AsyncMock(spec=AsyncSession)
        db_session.commit = AsyncMock()
        db_session.rollback = AsyncMock()
        db_session.close = AsyncMock()
        
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=db_session)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        db_session.begin = AsyncMock(return_value=async_context_manager)
        return db_session

    def _create_mock_llm_manager(self):
        """Create mock LLM Manager with proper response structures"""
        llm_manager = Mock(spec=LLMManager)
        llm_manager.call_llm = AsyncMock(return_value={"content": "Test response", "tool_calls": []})
        llm_manager.ask_llm = AsyncMock(return_value=self._get_mock_llm_json_response())
        llm_manager.ask_structured_llm = AsyncMock(return_value=self._get_mock_triage_result())
        return llm_manager

    def _get_mock_llm_json_response(self):
        """Get mock JSON response for LLM ask_llm method"""
        return json.dumps({
            "plan_steps": [{
                "step_id": "step_1", "description": "Optimize GPU utilization",
                "estimated_duration": "2 hours", "dependencies": [],
                "resources_needed": ["GPU monitoring tools"], "status": "pending"
            }],
            "priority": "medium", "estimated_duration": "4 hours",
            "required_resources": ["GPU monitoring tools", "Performance analytics"],
            "success_metrics": ["Improved throughput", "Reduced costs"]
        })

    def _get_mock_triage_result(self):
        """Get mock triage result for structured LLM calls"""
        from netra_backend.app.agents.triage_sub_agent import (
            TriageResult, Priority, Complexity, UserIntent, 
            ExtractedEntities, TriageMetadata
        )
        return TriageResult(
            category="Cost Optimization", confidence_score=0.95, priority=Priority.MEDIUM,
            complexity=Complexity.MODERATE, is_admin_mode=False,
            extracted_entities=ExtractedEntities(models_mentioned=[], metrics_mentioned=[], time_ranges=[]),
            user_intent=UserIntent(primary_intent="optimize", secondary_intents=["analyze"]),
            tool_recommendations=[], metadata=TriageMetadata(
                triage_duration_ms=100, cache_hit=False, fallback_used=False, retry_count=0
            )
        )

    def _create_mock_websocket_manager(self):
        """Create mock WebSocket Manager with all required methods"""
        websocket_manager = Mock()
        websocket_manager.send_message = AsyncMock()
        websocket_manager.send_to_thread = AsyncMock()
        websocket_manager.broadcast = AsyncMock()
        websocket_manager.send_agent_log = AsyncMock()
        websocket_manager.send_error = AsyncMock()
        websocket_manager.send_sub_agent_update = AsyncMock()
        websocket_manager.active_connections = {}
        return websocket_manager

    def _create_mock_tool_dispatcher(self):
        """Create mock Tool Dispatcher with success response"""
        tool_dispatcher = Mock(spec=ApexToolSelector)
        tool_dispatcher.dispatch_tool = AsyncMock(return_value={
            "status": "success", "result": "Tool executed successfully"
        })
        return tool_dispatcher

    def _create_supervisor_with_patches(self, db_session, llm_manager, websocket_manager, tool_dispatcher):
        """Create supervisor with state persistence patches"""
        mock_save_state = AsyncMock(return_value=(True, "state_saved"))
        mock_load_state = AsyncMock(return_value=None)
        mock_get_context = AsyncMock(return_value={})
        
        with patch.object(state_persistence_service, 'save_agent_state', mock_save_state):
            with patch.object(state_persistence_service, 'load_agent_state', mock_load_state):
                with patch.object(state_persistence_service, 'get_thread_context', mock_get_context):
                    supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
                    supervisor.thread_id = str(uuid.uuid4())
                    supervisor.user_id = str(uuid.uuid4())
                    return supervisor

    def _create_agent_service(self, supervisor, websocket_manager):
        """Create Agent Service with Supervisor and WebSocket manager"""
        agent_service = AgentService(supervisor)
        agent_service.websocket_manager = websocket_manager
        return agent_service

    @pytest.fixture
    def setup_agent_infrastructure(self):
        """Setup complete agent infrastructure for testing"""
        db_session = self._create_mock_db_session()
        llm_manager = self._create_mock_llm_manager()
        websocket_manager = self._create_mock_websocket_manager()
        tool_dispatcher = self._create_mock_tool_dispatcher()
        
        supervisor = self._create_supervisor_with_patches(db_session, llm_manager, websocket_manager, tool_dispatcher)
        agent_service = self._create_agent_service(supervisor, websocket_manager)
        
        return {
            "supervisor": supervisor, "agent_service": agent_service, "db_session": db_session,
            "llm_manager": llm_manager, "websocket_manager": websocket_manager, "tool_dispatcher": tool_dispatcher
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