from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Setup fixtures and base test class for critical end-to-end agent tests.
# REMOVED_SYNTAX_ERROR: Provides shared infrastructure and mocks for agent testing.
""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import json
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState

# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor_consolidated import ( )
# REMOVED_SYNTAX_ERROR: SupervisorAgent as Supervisor)
from netra_backend.app.llm.llm_manager import LLMManager
# REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.agent import ( )
AgentCompleted,
AgentStarted,
SubAgentLifecycle,
SubAgentState
from netra_backend.app.schemas.websocket_models import SubAgentUpdate
from netra_backend.app.schemas.websocket_server_messages import WebSocketMessage
from netra_backend.app.services.agent_service import AgentService
# REMOVED_SYNTAX_ERROR: from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import ( )
ApexToolSelector
from netra_backend.app.services.state_persistence import state_persistence_service
from netra_backend.app.services.websocket.message_handler import UserMessageHandler

# REMOVED_SYNTAX_ERROR: class AgentE2ETestBase:
    # REMOVED_SYNTAX_ERROR: """Base class for critical end-to-end agent tests"""

# REMOVED_SYNTAX_ERROR: def _create_mock_db_session(self):
    # REMOVED_SYNTAX_ERROR: """Create mock database session with async context manager support"""
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: db_session = AsyncMock(spec=AsyncSession)
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: db_session.commit = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: db_session.rollback = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: db_session.close = AsyncMock()  # TODO: Use real service instance

    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: async_context_manager = AsyncMock()  # TODO: Use real service instance
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: async_context_manager.__aenter__ = AsyncMock(return_value=db_session)
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: async_context_manager.__aexit__ = AsyncMock(return_value=None)
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: db_session.begin = AsyncMock(return_value=async_context_manager)
    # REMOVED_SYNTAX_ERROR: return db_session

# REMOVED_SYNTAX_ERROR: def _create_mock_llm_manager(self):
    # REMOVED_SYNTAX_ERROR: """Create mock LLM Manager with proper response structures"""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager = Mock(spec=LLMManager)
    # Mock: LLM provider isolation to prevent external API usage and costs
    # REMOVED_SYNTAX_ERROR: llm_manager.call_llm = AsyncMock(return_value={"content": "Test response", "tool_calls": [}])
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    # REMOVED_SYNTAX_ERROR: llm_manager.ask_llm = AsyncMock(return_value=self._get_mock_llm_json_response())
    # Mock: LLM provider isolation to prevent external API usage and costs
    # REMOVED_SYNTAX_ERROR: llm_manager.ask_structured_llm = AsyncMock(return_value=self._get_mock_triage_result())
    # REMOVED_SYNTAX_ERROR: return llm_manager

# REMOVED_SYNTAX_ERROR: def _get_mock_llm_json_response(self):
    # REMOVED_SYNTAX_ERROR: """Get mock JSON response for LLM ask_llm method"""
    # REMOVED_SYNTAX_ERROR: return json.dumps({ ))
    # REMOVED_SYNTAX_ERROR: "plan_steps": [{ ))
    # REMOVED_SYNTAX_ERROR: "step_id": "step_1", "description": "Optimize GPU utilization",
    # REMOVED_SYNTAX_ERROR: "estimated_duration": "2 hours", "dependencies": [},
    # REMOVED_SYNTAX_ERROR: "resources_needed": ["GPU monitoring tools"], "status": "pending"
    # REMOVED_SYNTAX_ERROR: }],
    # REMOVED_SYNTAX_ERROR: "priority": "medium", "estimated_duration": "4 hours",
    # REMOVED_SYNTAX_ERROR: "required_resources": ["GPU monitoring tools", "Performance analytics"],
    # REMOVED_SYNTAX_ERROR: "success_metrics": ["Improved throughput", "Reduced costs"]
    

# REMOVED_SYNTAX_ERROR: def _get_mock_triage_result(self):
    # REMOVED_SYNTAX_ERROR: """Get mock triage result for structured LLM calls"""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.unified_triage_agent import ( )
    # REMOVED_SYNTAX_ERROR: Complexity,
    # REMOVED_SYNTAX_ERROR: ExtractedEntities,
    # REMOVED_SYNTAX_ERROR: Priority,
    # REMOVED_SYNTAX_ERROR: TriageMetadata,
    # REMOVED_SYNTAX_ERROR: TriageResult,
    # REMOVED_SYNTAX_ERROR: UserIntent)
    # REMOVED_SYNTAX_ERROR: return TriageResult( )
    # REMOVED_SYNTAX_ERROR: category="Cost Optimization", confidence_score=0.95, priority=Priority.MEDIUM,
    # REMOVED_SYNTAX_ERROR: complexity=Complexity.MODERATE, is_admin_mode=False,
    # REMOVED_SYNTAX_ERROR: extracted_entities=ExtractedEntities(models_mentioned=[], metrics_mentioned=[], time_ranges=[]),
    # REMOVED_SYNTAX_ERROR: user_intent=UserIntent(primary_intent="optimize", secondary_intents=["analyze"]),
    # REMOVED_SYNTAX_ERROR: tool_recommendations=[], metadata=TriageMetadata( )
    # REMOVED_SYNTAX_ERROR: triage_duration_ms=100, cache_hit=False, fallback_used=False, retry_count=0
    
    

# REMOVED_SYNTAX_ERROR: def _create_mock_websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket Manager with all required methods"""
    # Mock: WebSocket connection isolation for testing without network overhead
    # REMOVED_SYNTAX_ERROR: websocket_manager = UnifiedWebSocketManager()
    # Mock: WebSocket connection isolation for testing without network overhead
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_message = AsyncMock()  # TODO: Use real service instance
    # Mock: WebSocket connection isolation for testing without network overhead
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_to_thread = AsyncMock()  # TODO: Use real service instance
    # Mock: WebSocket connection isolation for testing without network overhead
    # REMOVED_SYNTAX_ERROR: websocket_manager.broadcast = AsyncMock()  # TODO: Use real service instance
    # Mock: WebSocket connection isolation for testing without network overhead
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_agent_log = AsyncMock()  # TODO: Use real service instance
    # Mock: WebSocket connection isolation for testing without network overhead
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_error = AsyncMock()  # TODO: Use real service instance
    # Mock: WebSocket connection isolation for testing without network overhead
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_sub_agent_update = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: websocket_manager.active_connections = {}
    # REMOVED_SYNTAX_ERROR: return websocket_manager

# REMOVED_SYNTAX_ERROR: def _create_mock_tool_dispatcher(self):
    # REMOVED_SYNTAX_ERROR: """Create mock Tool Dispatcher with success response"""
    # Mock: Tool execution isolation for predictable agent testing
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = Mock(spec=ApexToolSelector)
    # Mock: Tool execution isolation for predictable agent testing
    # REMOVED_SYNTAX_ERROR: tool_dispatcher.dispatch_tool = AsyncMock(return_value={ ))
    # REMOVED_SYNTAX_ERROR: "status": "success", "result": "Tool executed successfully"
    
    # REMOVED_SYNTAX_ERROR: return tool_dispatcher

# REMOVED_SYNTAX_ERROR: def _create_supervisor_with_patches(self, db_session, llm_manager, websocket_manager, tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Create supervisor with state persistence patches"""
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: mock_save_state = AsyncMock(return_value=(True, "state_saved"))
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: mock_load_state = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: mock_get_context = AsyncMock(return_value={})

    # REMOVED_SYNTAX_ERROR: with patch.object(state_persistence_service, 'save_agent_state', mock_save_state):
        # REMOVED_SYNTAX_ERROR: with patch.object(state_persistence_service, 'load_agent_state', mock_load_state):
            # REMOVED_SYNTAX_ERROR: with patch.object(state_persistence_service, 'get_thread_context', mock_get_context):
                # Create AgentWebSocketBridge (no arguments)
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
                # REMOVED_SYNTAX_ERROR: websocket_bridge = AgentWebSocketBridge()
                # Set websocket_manager on the bridge
                # REMOVED_SYNTAX_ERROR: websocket_bridge.websocket_manager = websocket_manager

                # Supervisor now takes 2 arguments: llm_manager, websocket_bridge
                # tool_dispatcher is created per-request for isolation
                # REMOVED_SYNTAX_ERROR: supervisor = Supervisor(llm_manager, websocket_bridge)
                # REMOVED_SYNTAX_ERROR: supervisor.thread_id = str(uuid.uuid4())
                # REMOVED_SYNTAX_ERROR: supervisor.user_id = str(uuid.uuid4())
                # REMOVED_SYNTAX_ERROR: return supervisor

# REMOVED_SYNTAX_ERROR: def _create_agent_service(self, supervisor, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Create Agent Service with Supervisor and WebSocket manager"""
    # REMOVED_SYNTAX_ERROR: agent_service = AgentService(supervisor)
    # REMOVED_SYNTAX_ERROR: agent_service.websocket_manager = websocket_manager
    # REMOVED_SYNTAX_ERROR: return agent_service

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def setup_agent_infrastructure(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Setup complete agent infrastructure for testing"""
    # REMOVED_SYNTAX_ERROR: db_session = self._create_mock_db_session()
    # REMOVED_SYNTAX_ERROR: llm_manager = self._create_mock_llm_manager()
    # REMOVED_SYNTAX_ERROR: websocket_manager = self._create_mock_websocket_manager()
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = self._create_mock_tool_dispatcher()

    # REMOVED_SYNTAX_ERROR: supervisor = self._create_supervisor_with_patches(db_session, llm_manager, websocket_manager, tool_dispatcher)
    # REMOVED_SYNTAX_ERROR: agent_service = self._create_agent_service(supervisor, websocket_manager)

    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "supervisor": supervisor, "agent_service": agent_service, "db_session": db_session,
    # REMOVED_SYNTAX_ERROR: "llm_manager": llm_manager, "websocket_manager": websocket_manager, "tool_dispatcher": tool_dispatcher
    

# REMOVED_SYNTAX_ERROR: def create_test_request(self, query="Test optimization request"):
    # REMOVED_SYNTAX_ERROR: """Create a standard test request"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "id": str(uuid.uuid4()),
    # REMOVED_SYNTAX_ERROR: "user_id": str(uuid.uuid4()),
    # REMOVED_SYNTAX_ERROR: "query": query,
    # REMOVED_SYNTAX_ERROR: "workloads": [},
    # REMOVED_SYNTAX_ERROR: "constraints": {}
    

# REMOVED_SYNTAX_ERROR: def create_websocket_message(self, message_type="start_agent", payload=None):
    # REMOVED_SYNTAX_ERROR: """Create a test WebSocket message"""
    # REMOVED_SYNTAX_ERROR: if payload is None:
        # REMOVED_SYNTAX_ERROR: payload = { )
        # REMOVED_SYNTAX_ERROR: "settings": {"debug_mode": False},
        # REMOVED_SYNTAX_ERROR: "request": self.create_test_request()
        

        # REMOVED_SYNTAX_ERROR: return WebSocketMessage( )
        # REMOVED_SYNTAX_ERROR: type=message_type,
        # REMOVED_SYNTAX_ERROR: payload=payload,
        # REMOVED_SYNTAX_ERROR: sender="test_client"
        

# REMOVED_SYNTAX_ERROR: def assert_agent_lifecycle_complete(self, supervisor, expected_states=None):
    # REMOVED_SYNTAX_ERROR: """Assert that agent lifecycle completed properly"""
    # REMOVED_SYNTAX_ERROR: if expected_states is None:
        # REMOVED_SYNTAX_ERROR: expected_states = [ )
        # REMOVED_SYNTAX_ERROR: SubAgentLifecycle.PENDING,
        # REMOVED_SYNTAX_ERROR: SubAgentLifecycle.RUNNING,
        # REMOVED_SYNTAX_ERROR: SubAgentLifecycle.COMPLETED
        

        # REMOVED_SYNTAX_ERROR: assert supervisor.current_state.lifecycle in expected_states
        # REMOVED_SYNTAX_ERROR: assert supervisor.thread_id is not None
        # REMOVED_SYNTAX_ERROR: assert supervisor.user_id is not None

# REMOVED_SYNTAX_ERROR: def assert_websocket_messages_sent(self, websocket_manager, min_messages=1):
    # REMOVED_SYNTAX_ERROR: """Assert that WebSocket messages were sent"""
    # REMOVED_SYNTAX_ERROR: total_calls = ( )
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_message.call_count +
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_to_thread.call_count +
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_agent_log.call_count +
    # REMOVED_SYNTAX_ERROR: websocket_manager.send_sub_agent_update.call_count
    
    # REMOVED_SYNTAX_ERROR: assert total_calls >= min_messages

# REMOVED_SYNTAX_ERROR: def assert_tool_dispatcher_called(self, tool_dispatcher, min_calls=1):
    # REMOVED_SYNTAX_ERROR: """Assert that tool dispatcher was called"""
    # REMOVED_SYNTAX_ERROR: assert tool_dispatcher.dispatch_tool.call_count >= min_calls

# REMOVED_SYNTAX_ERROR: def assert_llm_manager_called(self, llm_manager, min_calls=1):
    # REMOVED_SYNTAX_ERROR: """Assert that LLM manager was called"""
    # REMOVED_SYNTAX_ERROR: total_calls = ( )
    # REMOVED_SYNTAX_ERROR: llm_manager.call_llm.call_count +
    # REMOVED_SYNTAX_ERROR: llm_manager.ask_llm.call_count +
    # REMOVED_SYNTAX_ERROR: llm_manager.ask_structured_llm.call_count
    
    # REMOVED_SYNTAX_ERROR: assert total_calls >= min_calls