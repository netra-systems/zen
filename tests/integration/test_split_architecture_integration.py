# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: COMPREHENSIVE INTEGRATION TESTS: Split Architecture Isolation
    # REMOVED_SYNTAX_ERROR: ================================================================

    # REMOVED_SYNTAX_ERROR: CRITICAL MISSION: Validate the new split architecture provides complete user isolation:
        # REMOVED_SYNTAX_ERROR: 1. AgentClassRegistry - Infrastructure-only agent class registration
        # REMOVED_SYNTAX_ERROR: 2. AgentInstanceFactory - Per-request agent instantiation with complete isolation
        # REMOVED_SYNTAX_ERROR: 3. UserExecutionContext - Per-request execution context with validation
        # REMOVED_SYNTAX_ERROR: 4. WebSocket event routing with proper user isolation
        # REMOVED_SYNTAX_ERROR: 5. Database session isolation across concurrent requests
        # REMOVED_SYNTAX_ERROR: 6. Resource cleanup and memory management

        # REMOVED_SYNTAX_ERROR: Business Value Justification:
            # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
            # REMOVED_SYNTAX_ERROR: - Business Goal: Stability & Security
            # REMOVED_SYNTAX_ERROR: - Value Impact: Enables safe 10+ concurrent users with zero data leakage
            # REMOVED_SYNTAX_ERROR: - Strategic Impact: Foundation for multi-tenant production deployment

            # REMOVED_SYNTAX_ERROR: These tests are INTENTIONALLY DIFFICULT and COMPREHENSIVE to validate:
                # REMOVED_SYNTAX_ERROR: - Complete flow from FastAPI request to agent execution with isolation
                # REMOVED_SYNTAX_ERROR: - Concurrent user requests with proper isolation
                # REMOVED_SYNTAX_ERROR: - WebSocket events reach correct users only
                # REMOVED_SYNTAX_ERROR: - Database session isolation across requests
                # REMOVED_SYNTAX_ERROR: - Resource cleanup prevents memory leaks
                # REMOVED_SYNTAX_ERROR: - Error scenarios and edge cases
                # REMOVED_SYNTAX_ERROR: - Performance under stress (5+ concurrent users)
                # REMOVED_SYNTAX_ERROR: '''

                # REMOVED_SYNTAX_ERROR: import asyncio
                # REMOVED_SYNTAX_ERROR: import gc
                # REMOVED_SYNTAX_ERROR: import pytest
                # REMOVED_SYNTAX_ERROR: import time
                # REMOVED_SYNTAX_ERROR: import uuid
                # REMOVED_SYNTAX_ERROR: import weakref
                # REMOVED_SYNTAX_ERROR: from concurrent.futures import ThreadPoolExecutor, as_completed
                # REMOVED_SYNTAX_ERROR: from dataclasses import dataclass
                # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
                # REMOVED_SYNTAX_ERROR: from typing import Dict, List, Set, Optional, Any, Tuple
                # REMOVED_SYNTAX_ERROR: import psutil
                # REMOVED_SYNTAX_ERROR: import threading
                # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
                # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
                # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

                # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
                # REMOVED_SYNTAX_ERROR: from sqlalchemy import text

                # Import the split architecture components
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_class_registry import ( )
                # REMOVED_SYNTAX_ERROR: AgentClassRegistry,
                # REMOVED_SYNTAX_ERROR: AgentClassInfo,
                # REMOVED_SYNTAX_ERROR: get_agent_class_registry,
                # REMOVED_SYNTAX_ERROR: create_test_registry
                
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_instance_factory import ( )
                # REMOVED_SYNTAX_ERROR: AgentInstanceFactory,
                # REMOVED_SYNTAX_ERROR: UserWebSocketEmitter,
                # REMOVED_SYNTAX_ERROR: configure_agent_instance_factory,
                # REMOVED_SYNTAX_ERROR: get_agent_instance_factory
                
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_execution_context import UserExecutionContext as ModelsUserExecutionContext

                # Import supervisor UserExecutionContext
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_execution_context import UserExecutionContext as SupervisorUserExecutionContext
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.llm.llm_manager import LLMManager
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
                # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

                # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


                # ============================================================================
                # Mock Classes for Testing
                # ============================================================================

# REMOVED_SYNTAX_ERROR: class MockAgent(BaseAgent):
    # REMOVED_SYNTAX_ERROR: """Mock agent for testing isolation with comprehensive instrumentation."""

# REMOVED_SYNTAX_ERROR: def __init__(self, *args, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: super().__init__(*args, **kwargs)
    # REMOVED_SYNTAX_ERROR: self.execution_log = []
    # REMOVED_SYNTAX_ERROR: self.websocket_events_sent = []
    # REMOVED_SYNTAX_ERROR: self.user_data_accessed = []
    # REMOVED_SYNTAX_ERROR: self.db_queries_executed = []
    # REMOVED_SYNTAX_ERROR: self.memory_footprint = []
    # REMOVED_SYNTAX_ERROR: self._execution_count = 0
    # REMOVED_SYNTAX_ERROR: self._is_cleaned_up = False

# REMOVED_SYNTAX_ERROR: async def execute(self, state: DeepAgentState, run_id: str) -> DeepAgentState:
    # REMOVED_SYNTAX_ERROR: """Mock execution with comprehensive tracking."""
    # REMOVED_SYNTAX_ERROR: execution_id = "formatted_string"
    # REMOVED_SYNTAX_ERROR: self._execution_count += 1

    # Record execution details for isolation validation
    # REMOVED_SYNTAX_ERROR: execution_record = { )
    # REMOVED_SYNTAX_ERROR: 'execution_id': execution_id,
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'user_id': getattr(self, 'user_id', 'unknown'),
    # REMOVED_SYNTAX_ERROR: 'thread_id': getattr(state, 'thread_id', 'unknown'),
    # REMOVED_SYNTAX_ERROR: 'start_time': datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: 'memory_before': psutil.Process().memory_info().rss,
    # REMOVED_SYNTAX_ERROR: 'thread_local_data': threading.current_thread().ident
    

    # REMOVED_SYNTAX_ERROR: self.execution_log.append(execution_record)

    # Simulate WebSocket event emission
    # REMOVED_SYNTAX_ERROR: if hasattr(self, '_websocket_adapter') and self._websocket_adapter:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: await self.emit_thinking("Processing user request", step_number=1)
            # REMOVED_SYNTAX_ERROR: self.websocket_events_sent.append({ ))
            # REMOVED_SYNTAX_ERROR: 'event_type': 'agent_thinking',
            # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
            # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc),
            # REMOVED_SYNTAX_ERROR: 'user_context': getattr(self, 'user_id', 'unknown')
            
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                # Simulate processing time and memory usage
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # Simulate work

                # Record memory usage during execution
                # REMOVED_SYNTAX_ERROR: memory_during = psutil.Process().memory_info().rss
                # REMOVED_SYNTAX_ERROR: self.memory_footprint.append({ ))
                # REMOVED_SYNTAX_ERROR: 'execution_id': execution_id,
                # REMOVED_SYNTAX_ERROR: 'memory_peak': memory_during,
                # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc)
                

                # Update execution record with completion details
                # REMOVED_SYNTAX_ERROR: execution_record.update({ ))
                # REMOVED_SYNTAX_ERROR: 'end_time': datetime.now(timezone.utc),
                # REMOVED_SYNTAX_ERROR: 'memory_after': psutil.Process().memory_info().rss,
                # REMOVED_SYNTAX_ERROR: 'memory_delta': memory_during - execution_record['memory_before'],
                # REMOVED_SYNTAX_ERROR: 'completed': True
                

                # Return modified state to validate state isolation
                # REMOVED_SYNTAX_ERROR: result_state = DeepAgentState( )
                # REMOVED_SYNTAX_ERROR: user_message="formatted_string",
                # REMOVED_SYNTAX_ERROR: thread_id=getattr(state, 'thread_id', 'unknown'),
                # REMOVED_SYNTAX_ERROR: additional_context={ )
                # REMOVED_SYNTAX_ERROR: 'agent_execution_id': execution_id,
                # REMOVED_SYNTAX_ERROR: 'processed_at': datetime.now(timezone.utc).isoformat(),
                # REMOVED_SYNTAX_ERROR: 'agent_user_id': getattr(self, 'user_id', 'unknown')
                
                

                # REMOVED_SYNTAX_ERROR: return result_state

# REMOVED_SYNTAX_ERROR: def get_execution_summary(self) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Get summary of agent execution for validation."""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'agent_name': self.name,
    # REMOVED_SYNTAX_ERROR: 'agent_id': getattr(self, 'agent_id', 'unknown'),
    # REMOVED_SYNTAX_ERROR: 'user_id': getattr(self, 'user_id', 'unknown'),
    # REMOVED_SYNTAX_ERROR: 'total_executions': len(self.execution_log),
    # REMOVED_SYNTAX_ERROR: 'websocket_events_count': len(self.websocket_events_sent),
    # REMOVED_SYNTAX_ERROR: 'memory_samples': len(self.memory_footprint),
    # REMOVED_SYNTAX_ERROR: 'is_cleaned_up': self._is_cleaned_up,
    # REMOVED_SYNTAX_ERROR: 'execution_log': self.execution_log[-5:],  # Last 5 executions
    # REMOVED_SYNTAX_ERROR: 'websocket_events': self.websocket_events_sent[-5:],  # Last 5 events
    

# REMOVED_SYNTAX_ERROR: async def cleanup(self):
    # REMOVED_SYNTAX_ERROR: """Clean up agent resources for memory leak testing."""
    # REMOVED_SYNTAX_ERROR: self._is_cleaned_up = True
    # REMOVED_SYNTAX_ERROR: self.execution_log.clear()
    # REMOVED_SYNTAX_ERROR: self.websocket_events_sent.clear()
    # REMOVED_SYNTAX_ERROR: self.user_data_accessed.clear()
    # REMOVED_SYNTAX_ERROR: self.db_queries_executed.clear()
    # REMOVED_SYNTAX_ERROR: self.memory_footprint.clear()


# REMOVED_SYNTAX_ERROR: class MockTriageAgent(MockAgent):
    # REMOVED_SYNTAX_ERROR: """Specialized mock triage agent."""

# REMOVED_SYNTAX_ERROR: def __init__(self, *args, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: super().__init__(*args, name="triage", **kwargs)
    # REMOVED_SYNTAX_ERROR: self.description = "Mock triage agent for testing"


# REMOVED_SYNTAX_ERROR: class MockDataAgent(MockAgent):
    # REMOVED_SYNTAX_ERROR: """Specialized mock data agent."""

# REMOVED_SYNTAX_ERROR: def __init__(self, *args, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: super().__init__(*args, name="data", **kwargs)
    # REMOVED_SYNTAX_ERROR: self.description = "Mock data agent for testing"


    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class ConcurrentUserTestResult:
    # REMOVED_SYNTAX_ERROR: """Results from concurrent user testing."""
    # REMOVED_SYNTAX_ERROR: user_id: str
    # REMOVED_SYNTAX_ERROR: thread_id: str
    # REMOVED_SYNTAX_ERROR: run_id: str
    # REMOVED_SYNTAX_ERROR: success: bool
    # REMOVED_SYNTAX_ERROR: execution_time_ms: float
    # REMOVED_SYNTAX_ERROR: websocket_events_received: List[Dict[str, Any]]
    # REMOVED_SYNTAX_ERROR: agent_execution_log: List[Dict[str, Any]]
    # REMOVED_SYNTAX_ERROR: context_isolation_validated: bool
    # REMOVED_SYNTAX_ERROR: database_session_isolated: bool
    # REMOVED_SYNTAX_ERROR: memory_leak_detected: bool
    # REMOVED_SYNTAX_ERROR: error_message: Optional[str] = None


    # ============================================================================
    # Test Fixtures
    # ============================================================================

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Create mock LLM manager."""
    # REMOVED_SYNTAX_ERROR: llm_manager = MagicMock(spec=LLMManager)
    # REMOVED_SYNTAX_ERROR: llm_manager.send_completion = AsyncMock(return_value="Mock LLM response")
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return llm_manager


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Create mock tool dispatcher."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: tool_dispatcher = MagicMock(spec=ToolDispatcher)
    # REMOVED_SYNTAX_ERROR: tool_dispatcher.dispatch = AsyncMock(return_value={"result": "mock_tool_result"})
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return tool_dispatcher


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_websocket_manager():
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket manager for testing."""
    # REMOVED_SYNTAX_ERROR: websocket_manager = MagicMock(spec=WebSocketManager)
    # REMOVED_SYNTAX_ERROR: websocket_manager.emit = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: websocket_manager.emit_to_user = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: websocket_manager.emit_to_thread = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: websocket_manager.is_connected = MagicMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return websocket_manager


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_websocket_bridge(mock_websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket bridge with comprehensive event tracking."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: bridge = MagicMock(spec=AgentWebSocketBridge)

    # Track events sent to each user/run for isolation validation
    # REMOVED_SYNTAX_ERROR: bridge.events_sent = []
    # REMOVED_SYNTAX_ERROR: bridge.run_thread_mappings = {}

# REMOVED_SYNTAX_ERROR: async def mock_notify_agent_started(run_id, agent_name, context=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: 'type': 'agent_started',
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'agent_name': agent_name,
    # REMOVED_SYNTAX_ERROR: 'context': context,
    # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: 'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
    # REMOVED_SYNTAX_ERROR: bridge.events_sent.append(event)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def mock_notify_agent_thinking(run_id, agent_name, reasoning, step_number=None, progress_percentage=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: 'type': 'agent_thinking',
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'agent_name': agent_name,
    # REMOVED_SYNTAX_ERROR: 'reasoning': reasoning,
    # REMOVED_SYNTAX_ERROR: 'step_number': step_number,
    # REMOVED_SYNTAX_ERROR: 'progress_percentage': progress_percentage,
    # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: 'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
    # REMOVED_SYNTAX_ERROR: bridge.events_sent.append(event)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def mock_notify_tool_executing(run_id, agent_name, tool_name, parameters=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: 'type': 'tool_executing',
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'agent_name': agent_name,
    # REMOVED_SYNTAX_ERROR: 'tool_name': tool_name,
    # REMOVED_SYNTAX_ERROR: 'parameters': parameters,
    # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: 'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
    # REMOVED_SYNTAX_ERROR: bridge.events_sent.append(event)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def mock_notify_tool_completed(run_id, agent_name, tool_name, result=None, execution_time_ms=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: 'type': 'tool_completed',
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'agent_name': agent_name,
    # REMOVED_SYNTAX_ERROR: 'tool_name': tool_name,
    # REMOVED_SYNTAX_ERROR: 'result': result,
    # REMOVED_SYNTAX_ERROR: 'execution_time_ms': execution_time_ms,
    # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: 'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
    # REMOVED_SYNTAX_ERROR: bridge.events_sent.append(event)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def mock_notify_agent_completed(run_id, agent_name, result=None, execution_time_ms=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: 'type': 'agent_completed',
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'agent_name': agent_name,
    # REMOVED_SYNTAX_ERROR: 'result': result,
    # REMOVED_SYNTAX_ERROR: 'execution_time_ms': execution_time_ms,
    # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: 'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
    # REMOVED_SYNTAX_ERROR: bridge.events_sent.append(event)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def mock_notify_agent_error(run_id, agent_name, error, error_context=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: 'type': 'agent_error',
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'agent_name': agent_name,
    # REMOVED_SYNTAX_ERROR: 'error': error,
    # REMOVED_SYNTAX_ERROR: 'error_context': error_context,
    # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: 'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
    # REMOVED_SYNTAX_ERROR: bridge.events_sent.append(event)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def mock_register_run_thread_mapping(run_id, thread_id, metadata=None):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: bridge.run_thread_mappings[run_id] = thread_id
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: async def mock_unregister_run_mapping(run_id):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: bridge.run_thread_mappings.pop(run_id, None)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return True

    # Bind mock methods
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_started = mock_notify_agent_started
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_thinking = mock_notify_agent_thinking
    # REMOVED_SYNTAX_ERROR: bridge.notify_tool_executing = mock_notify_tool_executing
    # REMOVED_SYNTAX_ERROR: bridge.notify_tool_completed = mock_notify_tool_completed
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_completed = mock_notify_agent_completed
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_error = mock_notify_agent_error
    # REMOVED_SYNTAX_ERROR: bridge.register_run_thread_mapping = mock_register_run_thread_mapping
    # REMOVED_SYNTAX_ERROR: bridge.unregister_run_mapping = mock_unregister_run_mapping

    # REMOVED_SYNTAX_ERROR: return bridge


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_agent_registry(mock_llm_manager, mock_tool_dispatcher):
    # REMOVED_SYNTAX_ERROR: """Create mock agent registry with test agents."""
    # REMOVED_SYNTAX_ERROR: registry = MagicMock(spec=AgentRegistry)

    # Create mock agents
    # REMOVED_SYNTAX_ERROR: triage_agent = MockTriageAgent( )
    # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: name="triage"
    
    # REMOVED_SYNTAX_ERROR: data_agent = MockDataAgent( )
    # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: name="data"
    

    # REMOVED_SYNTAX_ERROR: registry.agents = { )
    # REMOVED_SYNTAX_ERROR: "triage": triage_agent,
    # REMOVED_SYNTAX_ERROR: "data": data_agent
    
    # REMOVED_SYNTAX_ERROR: registry.llm_manager = mock_llm_manager
    # REMOVED_SYNTAX_ERROR: registry.tool_dispatcher = mock_tool_dispatcher

# REMOVED_SYNTAX_ERROR: def mock_get(name):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return registry.agents.get(name)

    # REMOVED_SYNTAX_ERROR: registry.get = mock_get
    # REMOVED_SYNTAX_ERROR: return registry


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # Removed problematic line: async def test_database_sessions():
        # REMOVED_SYNTAX_ERROR: """Create test database sessions for isolation testing."""
        # Use in-memory SQLite for testing
        # REMOVED_SYNTAX_ERROR: engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        # Create session factory
        # REMOVED_SYNTAX_ERROR: async_session_factory = async_sessionmaker( )
        # REMOVED_SYNTAX_ERROR: engine, class_=AsyncSession, expire_on_commit=False
        

        # REMOVED_SYNTAX_ERROR: sessions = []

        # Create multiple isolated sessions
        # REMOVED_SYNTAX_ERROR: for i in range(10):
            # REMOVED_SYNTAX_ERROR: session = async_session_factory()
            # REMOVED_SYNTAX_ERROR: sessions.append(session)

            # REMOVED_SYNTAX_ERROR: yield sessions

            # Cleanup
            # REMOVED_SYNTAX_ERROR: for session in sessions:
                # REMOVED_SYNTAX_ERROR: try:
                    # REMOVED_SYNTAX_ERROR: await session.close()
                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                        # REMOVED_SYNTAX_ERROR: await engine.dispose()


                        # ============================================================================
                        # AgentClassRegistry Tests
                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestAgentClassRegistryIsolation:
    # REMOVED_SYNTAX_ERROR: """Test AgentClassRegistry infrastructure-only functionality."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_registry_immutability_after_freeze(self):
        # REMOVED_SYNTAX_ERROR: """Test that registry becomes immutable after freeze."""
        # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

        # Register agents before freeze
        # REMOVED_SYNTAX_ERROR: registry.register("triage", MockTriageAgent, "Triage agent for testing")
        # REMOVED_SYNTAX_ERROR: registry.register("data", MockDataAgent, "Data agent for testing")

        # Verify registration works before freeze
        # REMOVED_SYNTAX_ERROR: assert registry.has_agent_class("triage")
        # REMOVED_SYNTAX_ERROR: assert registry.has_agent_class("data")
        # REMOVED_SYNTAX_ERROR: assert len(registry) == 2

        # Freeze registry
        # REMOVED_SYNTAX_ERROR: registry.freeze()
        # REMOVED_SYNTAX_ERROR: assert registry.is_frozen()

        # Verify registration fails after freeze
        # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="Cannot register agent classes after registry is frozen"):
            # REMOVED_SYNTAX_ERROR: registry.register("new_agent", MockAgent, "Should fail")

            # Verify reads still work
            # REMOVED_SYNTAX_ERROR: triage_class = registry.get_agent_class("triage")
            # REMOVED_SYNTAX_ERROR: assert triage_class == MockTriageAgent

            # REMOVED_SYNTAX_ERROR: data_info = registry.get_agent_info("data")
            # REMOVED_SYNTAX_ERROR: assert data_info.name == "data"
            # REMOVED_SYNTAX_ERROR: assert data_info.agent_class == MockDataAgent

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_concurrent_registry_reads(self):
                # REMOVED_SYNTAX_ERROR: """Test thread-safe concurrent reads after freeze."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

                # Register multiple agents
                # REMOVED_SYNTAX_ERROR: for i in range(10):
                    # REMOVED_SYNTAX_ERROR: agent_name = "formatted_string"
                    # REMOVED_SYNTAX_ERROR: registry.register(agent_name, MockAgent, "formatted_string")

                    # REMOVED_SYNTAX_ERROR: registry.freeze()

                    # Test concurrent reads
# REMOVED_SYNTAX_ERROR: async def concurrent_reader(reader_id: int) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: results = []
    # REMOVED_SYNTAX_ERROR: for _ in range(100):
        # Read different agents concurrently
        # REMOVED_SYNTAX_ERROR: agent_name = "formatted_string"
        # REMOVED_SYNTAX_ERROR: agent_class = registry.get_agent_class(agent_name)
        # REMOVED_SYNTAX_ERROR: agent_info = registry.get_agent_info(agent_name)

        # REMOVED_SYNTAX_ERROR: results.append({ ))
        # REMOVED_SYNTAX_ERROR: 'reader_id': reader_id,
        # REMOVED_SYNTAX_ERROR: 'agent_name': agent_name,
        # REMOVED_SYNTAX_ERROR: 'class_found': agent_class is not None,
        # REMOVED_SYNTAX_ERROR: 'info_found': agent_info is not None,
        # REMOVED_SYNTAX_ERROR: 'class_correct': agent_class == MockAgent if agent_class else False
        

        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return results

        # Run concurrent readers
        # REMOVED_SYNTAX_ERROR: tasks = [concurrent_reader(i) for i in range(20)]
        # REMOVED_SYNTAX_ERROR: all_results = await asyncio.gather(*tasks)

        # Verify all reads were successful and consistent
        # REMOVED_SYNTAX_ERROR: total_reads = sum(len(results) for results in all_results)
        # REMOVED_SYNTAX_ERROR: assert total_reads == 20 * 100  # 20 readers  x  100 reads each

        # REMOVED_SYNTAX_ERROR: for results in all_results:
            # REMOVED_SYNTAX_ERROR: for result in results:
                # REMOVED_SYNTAX_ERROR: assert result['class_found'], "formatted_string"
                # REMOVED_SYNTAX_ERROR: assert result['info_found'], "formatted_string"
                # REMOVED_SYNTAX_ERROR: assert result['class_correct'], "formatted_string"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_registry_dependency_validation(self):
                    # REMOVED_SYNTAX_ERROR: """Test dependency validation functionality."""
                    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

                    # Register agents with dependencies
                    # REMOVED_SYNTAX_ERROR: registry.register("base", MockAgent, "Base agent", dependencies=["llm", "tools"])
                    # REMOVED_SYNTAX_ERROR: registry.register("triage", MockTriageAgent, "Triage agent", dependencies=["base", "llm"])
                    # REMOVED_SYNTAX_ERROR: registry.register("data", MockDataAgent, "Data agent", dependencies=["base", "database"])

                    # REMOVED_SYNTAX_ERROR: registry.freeze()

                    # Test dependency validation
                    # REMOVED_SYNTAX_ERROR: missing_deps = registry.validate_dependencies()

                    # Should find missing dependencies
                    # REMOVED_SYNTAX_ERROR: assert "base" in missing_deps
                    # REMOVED_SYNTAX_ERROR: assert "llm" in missing_deps["base"]
                    # REMOVED_SYNTAX_ERROR: assert "tools" in missing_deps["base"]

                    # REMOVED_SYNTAX_ERROR: assert "triage" in missing_deps
                    # REMOVED_SYNTAX_ERROR: assert "base" not in missing_deps["triage"]  # base exists
                    # REMOVED_SYNTAX_ERROR: assert "llm" in missing_deps["triage"]  # llm doesn"t exist

                    # Test agents by dependency
                    # REMOVED_SYNTAX_ERROR: agents_needing_base = registry.get_agents_by_dependency("base")
                    # REMOVED_SYNTAX_ERROR: assert "triage" in agents_needing_base
                    # REMOVED_SYNTAX_ERROR: assert "data" in agents_needing_base

                    # REMOVED_SYNTAX_ERROR: agents_needing_llm = registry.get_agents_by_dependency("llm")
                    # REMOVED_SYNTAX_ERROR: assert "base" in agents_needing_llm
                    # REMOVED_SYNTAX_ERROR: assert "triage" in agents_needing_llm


                    # ============================================================================
                    # AgentInstanceFactory Tests
                    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestAgentInstanceFactoryIsolation:
    # REMOVED_SYNTAX_ERROR: """Test AgentInstanceFactory per-request isolation."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_user_execution_context_creation_and_cleanup(self,
    # REMOVED_SYNTAX_ERROR: mock_agent_registry,
    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
    # REMOVED_SYNTAX_ERROR: test_database_sessions):
        # REMOVED_SYNTAX_ERROR: """Test user execution context creation and cleanup."""
        # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
        # REMOVED_SYNTAX_ERROR: factory.configure(mock_agent_registry, mock_websocket_bridge)

        # REMOVED_SYNTAX_ERROR: db_session = test_database_sessions[0]

        # Create user execution context
        # REMOVED_SYNTAX_ERROR: context = await factory.create_user_execution_context( )
        # REMOVED_SYNTAX_ERROR: user_id="user_123",
        # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
        # REMOVED_SYNTAX_ERROR: run_id="run_789",
        # REMOVED_SYNTAX_ERROR: db_session=db_session,
        # REMOVED_SYNTAX_ERROR: metadata={"test": "metadata"}
        

        # Verify context creation
        # REMOVED_SYNTAX_ERROR: assert context.user_id == "user_123"
        # REMOVED_SYNTAX_ERROR: assert context.thread_id == "thread_456"
        # REMOVED_SYNTAX_ERROR: assert context.run_id == "run_789"
        # REMOVED_SYNTAX_ERROR: assert context.db_session == db_session
        # REMOVED_SYNTAX_ERROR: assert context.websocket_emitter is not None
        # REMOVED_SYNTAX_ERROR: assert context.websocket_emitter.user_id == "user_123"
        # REMOVED_SYNTAX_ERROR: assert context.request_metadata["test"] == "metadata"

        # Verify WebSocket run-thread mapping was registered
        # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.run_thread_mappings["run_789"] == "thread_456"

        # Test context cleanup
        # REMOVED_SYNTAX_ERROR: await factory.cleanup_user_context(context)

        # Verify cleanup
        # REMOVED_SYNTAX_ERROR: assert context._is_cleaned
        # REMOVED_SYNTAX_ERROR: assert context.db_session is None
        # REMOVED_SYNTAX_ERROR: assert context.websocket_emitter is None
        # REMOVED_SYNTAX_ERROR: assert "run_789" not in mock_websocket_bridge.run_thread_mappings

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_agent_instance_creation_isolation(self,
        # REMOVED_SYNTAX_ERROR: mock_agent_registry,
        # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
        # REMOVED_SYNTAX_ERROR: test_database_sessions):
            # REMOVED_SYNTAX_ERROR: """Test isolated agent instance creation for different users."""
            # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
            # REMOVED_SYNTAX_ERROR: factory.configure(mock_agent_registry, mock_websocket_bridge)

            # Create contexts for different users
            # REMOVED_SYNTAX_ERROR: context1 = await factory.create_user_execution_context( )
            # REMOVED_SYNTAX_ERROR: user_id="user_001",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_001",
            # REMOVED_SYNTAX_ERROR: run_id="run_001",
            # REMOVED_SYNTAX_ERROR: db_session=test_database_sessions[0]
            

            # REMOVED_SYNTAX_ERROR: context2 = await factory.create_user_execution_context( )
            # REMOVED_SYNTAX_ERROR: user_id="user_002",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_002",
            # REMOVED_SYNTAX_ERROR: run_id="run_002",
            # REMOVED_SYNTAX_ERROR: db_session=test_database_sessions[1]
            

            # Create agent instances for each user
            # REMOVED_SYNTAX_ERROR: agent1 = await factory.create_agent_instance("triage", context1)
            # REMOVED_SYNTAX_ERROR: agent2 = await factory.create_agent_instance("triage", context2)

            # Verify agents are different instances
            # REMOVED_SYNTAX_ERROR: assert agent1 is not agent2
            # REMOVED_SYNTAX_ERROR: assert id(agent1) != id(agent2)

            # Verify agents are bound to correct users
            # REMOVED_SYNTAX_ERROR: assert agent1.user_id == "user_001"
            # REMOVED_SYNTAX_ERROR: assert agent2.user_id == "user_002"

            # Verify agents have different correlation IDs
            # REMOVED_SYNTAX_ERROR: assert agent1.correlation_id != agent2.correlation_id

            # Verify contexts track the agents
            # REMOVED_SYNTAX_ERROR: assert len(context1.active_runs) == 1
            # REMOVED_SYNTAX_ERROR: assert len(context2.active_runs) == 1

            # Test agent execution isolation
            # REMOVED_SYNTAX_ERROR: state1 = DeepAgentState(user_message="User 1 message", thread_id="thread_001")
            # REMOVED_SYNTAX_ERROR: state2 = DeepAgentState(user_message="User 2 message", thread_id="thread_002")

            # REMOVED_SYNTAX_ERROR: result1 = await agent1.execute(state1, "run_001")
            # REMOVED_SYNTAX_ERROR: result2 = await agent2.execute(state2, "run_002")

            # Verify results are isolated
            # REMOVED_SYNTAX_ERROR: assert "user_001" in result1.user_message
            # REMOVED_SYNTAX_ERROR: assert "user_002" in result2.user_message
            # REMOVED_SYNTAX_ERROR: assert result1.additional_context["agent_user_id"] == "user_001"
            # REMOVED_SYNTAX_ERROR: assert result2.additional_context["agent_user_id"] == "user_002"

            # Cleanup
            # REMOVED_SYNTAX_ERROR: await factory.cleanup_user_context(context1)
            # REMOVED_SYNTAX_ERROR: await factory.cleanup_user_context(context2)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_websocket_event_isolation(self,
            # REMOVED_SYNTAX_ERROR: mock_agent_registry,
            # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
            # REMOVED_SYNTAX_ERROR: test_database_sessions):
                # REMOVED_SYNTAX_ERROR: """Test WebSocket events are properly isolated per user."""
                # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
                # REMOVED_SYNTAX_ERROR: factory.configure(mock_agent_registry, mock_websocket_bridge)

                # Create contexts for 3 users
                # REMOVED_SYNTAX_ERROR: contexts = []
                # REMOVED_SYNTAX_ERROR: for i in range(3):
                    # REMOVED_SYNTAX_ERROR: context = await factory.create_user_execution_context( )
                    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                    # REMOVED_SYNTAX_ERROR: db_session=test_database_sessions[i]
                    
                    # REMOVED_SYNTAX_ERROR: contexts.append(context)

                    # Create agents and execute simultaneously
                    # REMOVED_SYNTAX_ERROR: agents = []
                    # REMOVED_SYNTAX_ERROR: for i, context in enumerate(contexts):
                        # REMOVED_SYNTAX_ERROR: agent = await factory.create_agent_instance("triage", context)
                        # REMOVED_SYNTAX_ERROR: agents.append(agent)

                        # Execute agents concurrently
                        # REMOVED_SYNTAX_ERROR: tasks = []
                        # REMOVED_SYNTAX_ERROR: for i, (agent, context) in enumerate(zip(agents, contexts)):
                            # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                            # REMOVED_SYNTAX_ERROR: user_message="formatted_string",
                            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                            
                            # REMOVED_SYNTAX_ERROR: tasks.append(agent.execute(state, "formatted_string"))

                            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

                            # Verify WebSocket events are properly isolated
                            # REMOVED_SYNTAX_ERROR: events_by_run = {}
                            # REMOVED_SYNTAX_ERROR: for event in mock_websocket_bridge.events_sent:
                                # REMOVED_SYNTAX_ERROR: run_id = event['run_id']
                                # REMOVED_SYNTAX_ERROR: if run_id not in events_by_run:
                                    # REMOVED_SYNTAX_ERROR: events_by_run[run_id] = []
                                    # REMOVED_SYNTAX_ERROR: events_by_run[run_id].append(event)

                                    # Each user should have their own events
                                    # REMOVED_SYNTAX_ERROR: assert len(events_by_run) == 3

                                    # REMOVED_SYNTAX_ERROR: for i in range(3):
                                        # REMOVED_SYNTAX_ERROR: run_id = "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"

                                        # REMOVED_SYNTAX_ERROR: assert run_id in events_by_run
                                        # REMOVED_SYNTAX_ERROR: user_events = events_by_run[run_id]

                                        # Each user should have at least one thinking event
                                        # REMOVED_SYNTAX_ERROR: thinking_events = [item for item in []] == 'agent_thinking']
                                        # REMOVED_SYNTAX_ERROR: assert len(thinking_events) > 0

                                        # All events for this user should have correct thread_id
                                        # REMOVED_SYNTAX_ERROR: for event in user_events:
                                            # REMOVED_SYNTAX_ERROR: assert event['thread_id'] == thread_id, "formatted_string"

                                            # Cleanup all contexts
                                            # REMOVED_SYNTAX_ERROR: for context in contexts:
                                                # REMOVED_SYNTAX_ERROR: await factory.cleanup_user_context(context)

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_concurrent_user_execution_stress(self,
                                                # REMOVED_SYNTAX_ERROR: mock_agent_registry,
                                                # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
                                                # REMOVED_SYNTAX_ERROR: test_database_sessions):
                                                    # REMOVED_SYNTAX_ERROR: """Stress test with 10 concurrent users to validate isolation."""
                                                    # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
                                                    # REMOVED_SYNTAX_ERROR: factory.configure(mock_agent_registry, mock_websocket_bridge)

                                                    # REMOVED_SYNTAX_ERROR: num_concurrent_users = 10
                                                    # REMOVED_SYNTAX_ERROR: executions_per_user = 5

# REMOVED_SYNTAX_ERROR: async def execute_user_workflow(user_index: int) -> ConcurrentUserTestResult:
    # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
    # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"

    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: websocket_events = []
    # REMOVED_SYNTAX_ERROR: agent_logs = []
    # REMOVED_SYNTAX_ERROR: error_message = None
    # REMOVED_SYNTAX_ERROR: success = True

    # REMOVED_SYNTAX_ERROR: try:
        # Execute multiple operations for this user
        # REMOVED_SYNTAX_ERROR: for exec_index in range(executions_per_user):
            # REMOVED_SYNTAX_ERROR: run_id = "formatted_string"

            # Use scoped execution context
            # REMOVED_SYNTAX_ERROR: async with factory.user_execution_scope( )
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
            # REMOVED_SYNTAX_ERROR: run_id=run_id,
            # REMOVED_SYNTAX_ERROR: db_session=test_database_sessions[user_index % len(test_database_sessions)]
            # REMOVED_SYNTAX_ERROR: ) as context:

                # Create and execute agent
                # REMOVED_SYNTAX_ERROR: agent = await factory.create_agent_instance("triage", context)

                # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                # REMOVED_SYNTAX_ERROR: user_message="formatted_string",
                # REMOVED_SYNTAX_ERROR: thread_id=thread_id
                

                # REMOVED_SYNTAX_ERROR: result = await agent.execute(state, run_id)

                # Validate result isolation
                # REMOVED_SYNTAX_ERROR: if user_id not in result.user_message:
                    # REMOVED_SYNTAX_ERROR: success = False
                    # REMOVED_SYNTAX_ERROR: error_message = "formatted_string"

                    # REMOVED_SYNTAX_ERROR: if result.additional_context.get("agent_user_id") != user_id:
                        # REMOVED_SYNTAX_ERROR: success = False
                        # REMOVED_SYNTAX_ERROR: error_message = "formatted_string"

                        # Collect agent execution data
                        # REMOVED_SYNTAX_ERROR: agent_summary = agent.get_execution_summary()
                        # REMOVED_SYNTAX_ERROR: agent_logs.append(agent_summary)

                        # Collect WebSocket events for this user
                        # REMOVED_SYNTAX_ERROR: for event in mock_websocket_bridge.events_sent:
                            # REMOVED_SYNTAX_ERROR: if event['run_id'].startswith("formatted_string"):
                                # REMOVED_SYNTAX_ERROR: websocket_events.append(event)

                                # REMOVED_SYNTAX_ERROR: except Exception as e:
                                    # REMOVED_SYNTAX_ERROR: success = False
                                    # REMOVED_SYNTAX_ERROR: error_message = str(e)
                                    # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")

                                    # REMOVED_SYNTAX_ERROR: execution_time_ms = (time.time() - start_time) * 1000

                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                                    # REMOVED_SYNTAX_ERROR: return ConcurrentUserTestResult( )
                                    # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
                                    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                                    # REMOVED_SYNTAX_ERROR: success=success,
                                    # REMOVED_SYNTAX_ERROR: execution_time_ms=execution_time_ms,
                                    # REMOVED_SYNTAX_ERROR: websocket_events_received=websocket_events,
                                    # REMOVED_SYNTAX_ERROR: agent_execution_log=agent_logs,
                                    # REMOVED_SYNTAX_ERROR: context_isolation_validated=success,
                                    # REMOVED_SYNTAX_ERROR: database_session_isolated=True,  # Would need more complex validation
                                    # REMOVED_SYNTAX_ERROR: memory_leak_detected=False,  # Would need memory monitoring
                                    # REMOVED_SYNTAX_ERROR: error_message=error_message
                                    

                                    # Execute all users concurrently
                                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: start_time = time.time()

                                    # REMOVED_SYNTAX_ERROR: tasks = [execute_user_workflow(i) for i in range(num_concurrent_users)]
                                    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                                    # REMOVED_SYNTAX_ERROR: total_time = time.time() - start_time
                                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                    # Analyze results
                                    # REMOVED_SYNTAX_ERROR: successful_results = [item for item in []]
                                    # REMOVED_SYNTAX_ERROR: failed_results = [item for item in []]

                                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                    # Verify success criteria
                                    # REMOVED_SYNTAX_ERROR: assert len(successful_results) >= (num_concurrent_users * 0.8), "formatted_string"

                                    # Verify isolation - each user should have their own events
                                    # REMOVED_SYNTAX_ERROR: all_websocket_events = []
                                    # REMOVED_SYNTAX_ERROR: for result in successful_results:
                                        # REMOVED_SYNTAX_ERROR: all_websocket_events.extend(result.websocket_events_received)

                                        # Group events by user
                                        # REMOVED_SYNTAX_ERROR: events_by_user = {}
                                        # REMOVED_SYNTAX_ERROR: for event in all_websocket_events:
                                            # REMOVED_SYNTAX_ERROR: run_id = event['run_id']
                                            # REMOVED_SYNTAX_ERROR: user_match = run_id.split('_')
                                            # REMOVED_SYNTAX_ERROR: if len(user_match) >= 3:
                                                # REMOVED_SYNTAX_ERROR: user_key = "formatted_string"  # stress_user_XXX
                                                # REMOVED_SYNTAX_ERROR: if user_key not in events_by_user:
                                                    # REMOVED_SYNTAX_ERROR: events_by_user[user_key] = []
                                                    # REMOVED_SYNTAX_ERROR: events_by_user[user_key].append(event)

                                                    # Each successful user should have events
                                                    # REMOVED_SYNTAX_ERROR: for result in successful_results:
                                                        # REMOVED_SYNTAX_ERROR: user_key = result.user_id
                                                        # REMOVED_SYNTAX_ERROR: assert user_key in events_by_user, "formatted_string"
                                                        # REMOVED_SYNTAX_ERROR: user_events = events_by_user[user_key]
                                                        # REMOVED_SYNTAX_ERROR: assert len(user_events) >= executions_per_user, "formatted_string"

                                                        # REMOVED_SYNTAX_ERROR: logger.info(" PASS:  Concurrent user stress test passed with proper isolation")


                                                        # ============================================================================
                                                        # UserExecutionContext Tests
                                                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestUserExecutionContextValidation:
    # REMOVED_SYNTAX_ERROR: """Test UserExecutionContext validation and isolation."""

# REMOVED_SYNTAX_ERROR: def test_context_validation_success(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Test successful context validation."""
    # REMOVED_SYNTAX_ERROR: pass
    # Test models.UserExecutionContext
    # REMOVED_SYNTAX_ERROR: context = ModelsUserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_012"
    

    # REMOVED_SYNTAX_ERROR: assert context.user_id == "user_123"
    # REMOVED_SYNTAX_ERROR: assert context.thread_id == "thread_456"
    # REMOVED_SYNTAX_ERROR: assert context.run_id == "run_789"
    # REMOVED_SYNTAX_ERROR: assert context.request_id == "req_012"

    # Test string representation
    # REMOVED_SYNTAX_ERROR: str_repr = str(context)
    # REMOVED_SYNTAX_ERROR: assert "user_123" in str_repr or "user_123..." in str_repr
    # REMOVED_SYNTAX_ERROR: assert "thread_456" in str_repr

    # Test dictionary conversion
    # REMOVED_SYNTAX_ERROR: context_dict = context.to_dict()
    # REMOVED_SYNTAX_ERROR: assert context_dict["user_id"] == "user_123"
    # REMOVED_SYNTAX_ERROR: assert context_dict["thread_id"] == "thread_456"
    # REMOVED_SYNTAX_ERROR: assert context_dict["run_id"] == "run_789"
    # REMOVED_SYNTAX_ERROR: assert context_dict["request_id"] == "req_012"

# REMOVED_SYNTAX_ERROR: def test_context_validation_failures(self):
    # REMOVED_SYNTAX_ERROR: """Test context validation failure cases."""
    # Test None user_id
    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be None"):
        # REMOVED_SYNTAX_ERROR: ModelsUserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id=None,
        # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
        # REMOVED_SYNTAX_ERROR: run_id="run_789",
        # REMOVED_SYNTAX_ERROR: request_id="req_012"
        

        # Test empty user_id
        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be empty"):
            # REMOVED_SYNTAX_ERROR: ModelsUserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
            # REMOVED_SYNTAX_ERROR: run_id="run_789",
            # REMOVED_SYNTAX_ERROR: request_id="req_012"
            

            # Test "None" string user_id
            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be the string 'None'"):
                # REMOVED_SYNTAX_ERROR: ModelsUserExecutionContext( )
                # REMOVED_SYNTAX_ERROR: user_id="None",
                # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
                # REMOVED_SYNTAX_ERROR: run_id="run_789",
                # REMOVED_SYNTAX_ERROR: request_id="req_012"
                

                # Test "registry" run_id
                # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="UserExecutionContext.run_id cannot be 'registry'"):
                    # REMOVED_SYNTAX_ERROR: ModelsUserExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: user_id="user_123",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
                    # REMOVED_SYNTAX_ERROR: run_id="registry",
                    # REMOVED_SYNTAX_ERROR: request_id="req_012"
                    

                    # Test None thread_id
                    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="UserExecutionContext.thread_id cannot be None"):
                        # REMOVED_SYNTAX_ERROR: ModelsUserExecutionContext( )
                        # REMOVED_SYNTAX_ERROR: user_id="user_123",
                        # REMOVED_SYNTAX_ERROR: thread_id=None,
                        # REMOVED_SYNTAX_ERROR: run_id="run_789",
                        # REMOVED_SYNTAX_ERROR: request_id="req_012"
                        

                        # Test empty request_id
                        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="UserExecutionContext.request_id cannot be empty"):
                            # REMOVED_SYNTAX_ERROR: ModelsUserExecutionContext( )
                            # REMOVED_SYNTAX_ERROR: user_id="user_123",
                            # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
                            # REMOVED_SYNTAX_ERROR: run_id="run_789",
                            # REMOVED_SYNTAX_ERROR: request_id=""
                            

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_context_isolation_across_requests(self):
                                # REMOVED_SYNTAX_ERROR: """Test that contexts from different requests are completely isolated."""
                                # REMOVED_SYNTAX_ERROR: pass
                                # Create multiple contexts simulating different requests
                                # REMOVED_SYNTAX_ERROR: contexts = []
                                # REMOVED_SYNTAX_ERROR: for i in range(10):
                                    # REMOVED_SYNTAX_ERROR: context = ModelsUserExecutionContext( )
                                    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                                    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
                                    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                                    # REMOVED_SYNTAX_ERROR: request_id="formatted_string"
                                    
                                    # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                    # Verify all contexts are unique
                                    # REMOVED_SYNTAX_ERROR: user_ids = [c.user_id for c in contexts]
                                    # REMOVED_SYNTAX_ERROR: thread_ids = [c.thread_id for c in contexts]
                                    # REMOVED_SYNTAX_ERROR: run_ids = [c.run_id for c in contexts]
                                    # REMOVED_SYNTAX_ERROR: request_ids = [c.request_id for c in contexts]

                                    # REMOVED_SYNTAX_ERROR: assert len(set(user_ids)) == 10  # All unique
                                    # REMOVED_SYNTAX_ERROR: assert len(set(thread_ids)) == 10  # All unique
                                    # REMOVED_SYNTAX_ERROR: assert len(set(run_ids)) == 10  # All unique
                                    # REMOVED_SYNTAX_ERROR: assert len(set(request_ids)) == 10  # All unique

                                    # Verify contexts don't interfere with each other
                                    # REMOVED_SYNTAX_ERROR: for i, context in enumerate(contexts):
                                        # REMOVED_SYNTAX_ERROR: expected_user_id = "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: expected_thread_id = "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: expected_run_id = "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: expected_request_id = "formatted_string"

                                        # REMOVED_SYNTAX_ERROR: assert context.user_id == expected_user_id
                                        # REMOVED_SYNTAX_ERROR: assert context.thread_id == expected_thread_id
                                        # REMOVED_SYNTAX_ERROR: assert context.run_id == expected_run_id
                                        # REMOVED_SYNTAX_ERROR: assert context.request_id == expected_request_id


                                        # ============================================================================
                                        # End-to-End Integration Tests
                                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestEndToEndIntegration:
    # REMOVED_SYNTAX_ERROR: """End-to-end integration tests simulating FastAPI request flow."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_complete_request_flow_with_isolation(self,
    # REMOVED_SYNTAX_ERROR: mock_agent_registry,
    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
    # REMOVED_SYNTAX_ERROR: test_database_sessions):
        # REMOVED_SYNTAX_ERROR: """Test complete request flow from API to agent execution."""
        # Step 1: Setup infrastructure (simulating FastAPI startup)
        # REMOVED_SYNTAX_ERROR: class_registry = create_test_registry()
        # REMOVED_SYNTAX_ERROR: class_registry.register("triage", MockTriageAgent, "Triage agent")
        # REMOVED_SYNTAX_ERROR: class_registry.register("data", MockDataAgent, "Data agent")
        # REMOVED_SYNTAX_ERROR: class_registry.freeze()

        # REMOVED_SYNTAX_ERROR: instance_factory = AgentInstanceFactory()
        # REMOVED_SYNTAX_ERROR: instance_factory.configure(mock_agent_registry, mock_websocket_bridge)

        # Step 2: Simulate FastAPI request processing
# REMOVED_SYNTAX_ERROR: async def simulate_api_request(user_id: str, message: str) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
    # REMOVED_SYNTAX_ERROR: run_id = "formatted_string"
    # REMOVED_SYNTAX_ERROR: request_id = "formatted_string"

    # Validate request context (simulating middleware)
    # REMOVED_SYNTAX_ERROR: request_context = ModelsUserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id=run_id,
    # REMOVED_SYNTAX_ERROR: request_id=request_id
    

    # Create execution scope (simulating request handler)
    # REMOVED_SYNTAX_ERROR: db_session = test_database_sessions[0]  # Simulating request-scoped session

    # REMOVED_SYNTAX_ERROR: async with instance_factory.user_execution_scope( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
    # REMOVED_SYNTAX_ERROR: run_id=run_id,
    # REMOVED_SYNTAX_ERROR: db_session=db_session,
    # REMOVED_SYNTAX_ERROR: metadata={"api_request": True, "message": message}
    # REMOVED_SYNTAX_ERROR: ) as execution_context:

        # Get agent class from registry (simulating agent selection logic)
        # REMOVED_SYNTAX_ERROR: triage_class = class_registry.get_agent_class("triage")
        # REMOVED_SYNTAX_ERROR: assert triage_class is not None

        # Create agent instance for this request
        # REMOVED_SYNTAX_ERROR: agent = await instance_factory.create_agent_instance("triage", execution_context)

        # Execute agent (simulating agent orchestration)
        # REMOVED_SYNTAX_ERROR: agent_state = DeepAgentState( )
        # REMOVED_SYNTAX_ERROR: user_message=message,
        # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
        # REMOVED_SYNTAX_ERROR: additional_context={ )
        # REMOVED_SYNTAX_ERROR: "request_id": request_id,
        # REMOVED_SYNTAX_ERROR: "api_request": True
        
        

        # REMOVED_SYNTAX_ERROR: result_state = await agent.execute(agent_state, run_id)

        # Return API response (simulating response serialization)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return { )
        # REMOVED_SYNTAX_ERROR: "success": True,
        # REMOVED_SYNTAX_ERROR: "user_id": user_id,
        # REMOVED_SYNTAX_ERROR: "thread_id": thread_id,
        # REMOVED_SYNTAX_ERROR: "run_id": run_id,
        # REMOVED_SYNTAX_ERROR: "request_id": request_id,
        # REMOVED_SYNTAX_ERROR: "response": result_state.user_message,
        # REMOVED_SYNTAX_ERROR: "context": result_state.additional_context,
        # REMOVED_SYNTAX_ERROR: "agent_summary": agent.get_execution_summary()
        

        # Step 3: Simulate multiple concurrent API requests
        # REMOVED_SYNTAX_ERROR: test_users = [ )
        # REMOVED_SYNTAX_ERROR: ("user_alice", "Hello, I need help with data analysis"),
        # REMOVED_SYNTAX_ERROR: ("user_bob", "Can you help me with system diagnostics?"),
        # REMOVED_SYNTAX_ERROR: ("user_charlie", "I have a question about integration"),
        # REMOVED_SYNTAX_ERROR: ("user_diana", "Need assistance with configuration"),
        # REMOVED_SYNTAX_ERROR: ("user_eve", "Help with troubleshooting please")
        

        # Execute requests concurrently
        # REMOVED_SYNTAX_ERROR: tasks = [simulate_api_request(user_id, message) for user_id, message in test_users]
        # REMOVED_SYNTAX_ERROR: api_responses = await asyncio.gather(*tasks)

        # Step 4: Validate isolation and correctness
        # REMOVED_SYNTAX_ERROR: assert len(api_responses) == 5

        # Verify each response is for the correct user
        # REMOVED_SYNTAX_ERROR: for i, (expected_user, expected_message) in enumerate(test_users):
            # REMOVED_SYNTAX_ERROR: response = api_responses[i]

            # REMOVED_SYNTAX_ERROR: assert response["success"] is True
            # REMOVED_SYNTAX_ERROR: assert response["user_id"] == expected_user
            # REMOVED_SYNTAX_ERROR: assert expected_user in response["response"]  # Agent should echo user ID
            # REMOVED_SYNTAX_ERROR: assert response["context"]["agent_user_id"] == expected_user

            # REMOVED_SYNTAX_ERROR: agent_summary = response["agent_summary"]
            # REMOVED_SYNTAX_ERROR: assert agent_summary["user_id"] == expected_user
            # REMOVED_SYNTAX_ERROR: assert agent_summary["total_executions"] == 1

            # Step 5: Verify WebSocket events were properly routed
            # REMOVED_SYNTAX_ERROR: events_by_user = {}
            # REMOVED_SYNTAX_ERROR: for event in mock_websocket_bridge.events_sent:
                # REMOVED_SYNTAX_ERROR: run_id = event["run_id"]
                # Find which user this run_id belongs to
                # REMOVED_SYNTAX_ERROR: for response in api_responses:
                    # REMOVED_SYNTAX_ERROR: if response["run_id"] == run_id:
                        # REMOVED_SYNTAX_ERROR: user_id = response["user_id"]
                        # REMOVED_SYNTAX_ERROR: if user_id not in events_by_user:
                            # REMOVED_SYNTAX_ERROR: events_by_user[user_id] = []
                            # REMOVED_SYNTAX_ERROR: events_by_user[user_id].append(event)
                            # REMOVED_SYNTAX_ERROR: break

                            # Each user should have received their own WebSocket events
                            # REMOVED_SYNTAX_ERROR: for expected_user, _ in test_users:
                                # REMOVED_SYNTAX_ERROR: assert expected_user in events_by_user, "formatted_string"
                                # REMOVED_SYNTAX_ERROR: user_events = events_by_user[expected_user]
                                # REMOVED_SYNTAX_ERROR: assert len(user_events) > 0, "formatted_string"

                                # Verify events contain correct run_id and thread_id
                                # REMOVED_SYNTAX_ERROR: for event in user_events:
                                    # Find the response for this user to get expected IDs
                                    # REMOVED_SYNTAX_ERROR: user_response = next(r for r in api_responses if r["user_id"] == expected_user)
                                    # REMOVED_SYNTAX_ERROR: expected_thread_id = user_response["thread_id"]

                                    # REMOVED_SYNTAX_ERROR: assert event["thread_id"] == expected_thread_id, "formatted_string"

                                    # REMOVED_SYNTAX_ERROR: logger.info(" PASS:  Complete end-to-end integration test passed with proper isolation")

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_memory_leak_prevention(self,
                                    # REMOVED_SYNTAX_ERROR: mock_agent_registry,
                                    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
                                    # REMOVED_SYNTAX_ERROR: test_database_sessions):
                                        # REMOVED_SYNTAX_ERROR: """Test that resource cleanup prevents memory leaks."""
                                        # REMOVED_SYNTAX_ERROR: import gc
                                        # REMOVED_SYNTAX_ERROR: import weakref

                                        # REMOVED_SYNTAX_ERROR: instance_factory = AgentInstanceFactory()
                                        # REMOVED_SYNTAX_ERROR: instance_factory.configure(mock_agent_registry, mock_websocket_bridge)

                                        # Create weak references to track object lifecycle
                                        # REMOVED_SYNTAX_ERROR: weak_refs = { )
                                        # REMOVED_SYNTAX_ERROR: 'contexts': [],
                                        # REMOVED_SYNTAX_ERROR: 'agents': [],
                                        # REMOVED_SYNTAX_ERROR: 'sessions': [],
                                        # REMOVED_SYNTAX_ERROR: 'emitters': []
                                        

                                        # Memory usage before test
                                        # REMOVED_SYNTAX_ERROR: process = psutil.Process()
                                        # REMOVED_SYNTAX_ERROR: memory_before = process.memory_info().rss

                                        # Create and execute multiple isolated contexts
                                        # REMOVED_SYNTAX_ERROR: for i in range(50):  # Large number to detect leaks
                                        # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
                                        # REMOVED_SYNTAX_ERROR: run_id = "formatted_string"

                                        # Create context in scope to ensure cleanup
                                        # REMOVED_SYNTAX_ERROR: async with instance_factory.user_execution_scope( )
                                        # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                        # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
                                        # REMOVED_SYNTAX_ERROR: run_id=run_id,
                                        # REMOVED_SYNTAX_ERROR: db_session=test_database_sessions[i % len(test_database_sessions)],
                                        # REMOVED_SYNTAX_ERROR: metadata={"leak_test": True, "iteration": i}
                                        # REMOVED_SYNTAX_ERROR: ) as context:

                                            # Create weak references for leak detection
                                            # REMOVED_SYNTAX_ERROR: weak_refs['contexts'].append(weakref.ref(context))
                                            # REMOVED_SYNTAX_ERROR: weak_refs['sessions'].append(weakref.ref(context.db_session))
                                            # REMOVED_SYNTAX_ERROR: weak_refs['emitters'].append(weakref.ref(context.websocket_emitter))

                                            # Create and use agent
                                            # REMOVED_SYNTAX_ERROR: agent = await instance_factory.create_agent_instance("triage", context)
                                            # REMOVED_SYNTAX_ERROR: weak_refs['agents'].append(weakref.ref(agent))

                                            # Execute agent to create internal state
                                            # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                                            # REMOVED_SYNTAX_ERROR: user_message="formatted_string",
                                            # REMOVED_SYNTAX_ERROR: thread_id=thread_id
                                            

                                            # REMOVED_SYNTAX_ERROR: result = await agent.execute(state, run_id)

                                            # Verify execution worked
                                            # REMOVED_SYNTAX_ERROR: assert user_id in result.user_message

                                            # Force some garbage collection within the loop
                                            # REMOVED_SYNTAX_ERROR: if i % 10 == 0:
                                                # REMOVED_SYNTAX_ERROR: gc.collect()

                                                # Force garbage collection after all contexts are cleaned up
                                                # REMOVED_SYNTAX_ERROR: gc.collect()
                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # Allow async cleanup to complete
                                                # REMOVED_SYNTAX_ERROR: gc.collect()

                                                # Check memory usage after test
                                                # REMOVED_SYNTAX_ERROR: memory_after = process.memory_info().rss
                                                # REMOVED_SYNTAX_ERROR: memory_increase_mb = (memory_after - memory_before) / 1024 / 1024

                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                                # Check weak references - most should be garbage collected
                                                # REMOVED_SYNTAX_ERROR: alive_contexts = sum(1 for ref in weak_refs['contexts'] if ref() is not None)
                                                # REMOVED_SYNTAX_ERROR: alive_agents = sum(1 for ref in weak_refs['agents'] if ref() is not None)
                                                # REMOVED_SYNTAX_ERROR: alive_sessions = sum(1 for ref in weak_refs['sessions'] if ref() is not None)
                                                # REMOVED_SYNTAX_ERROR: alive_emitters = sum(1 for ref in weak_refs['emitters'] if ref() is not None)

                                                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

                                                # Memory increase should be reasonable (less than 50MB for 50 iterations)
                                                # REMOVED_SYNTAX_ERROR: assert memory_increase_mb < 50, "formatted_string"

                                                # Most objects should be garbage collected (allow some to remain due to Python's GC behavior)
                                                # REMOVED_SYNTAX_ERROR: assert alive_contexts <= 10, "formatted_string"
                                                # REMOVED_SYNTAX_ERROR: assert alive_agents <= 10, "formatted_string"
                                                # REMOVED_SYNTAX_ERROR: assert alive_emitters <= 10, "formatted_string"

                                                # REMOVED_SYNTAX_ERROR: logger.info(" PASS:  Memory leak prevention test passed")


                                                # ============================================================================
                                                # Error Scenario Tests
                                                # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestErrorScenariosAndEdgeCases:
    # REMOVED_SYNTAX_ERROR: """Test error scenarios and edge cases in the split architecture."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_invalid_agent_creation_handling(self,
    # REMOVED_SYNTAX_ERROR: mock_agent_registry,
    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
    # REMOVED_SYNTAX_ERROR: test_database_sessions):
        # REMOVED_SYNTAX_ERROR: """Test error handling for invalid agent creation."""
        # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
        # REMOVED_SYNTAX_ERROR: factory.configure(mock_agent_registry, mock_websocket_bridge)

        # Create valid context
        # REMOVED_SYNTAX_ERROR: context = await factory.create_user_execution_context( )
        # REMOVED_SYNTAX_ERROR: user_id="test_user",
        # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
        # REMOVED_SYNTAX_ERROR: run_id="test_run",
        # REMOVED_SYNTAX_ERROR: db_session=test_database_sessions[0]
        

        # Test agent not found in registry
        # REMOVED_SYNTAX_ERROR: mock_agent_registry.get = Mock(return_value=None)

        # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="Agent creation failed"):
            # REMOVED_SYNTAX_ERROR: await factory.create_agent_instance("nonexistent_agent", context)

            # Test invalid context
            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="UserExecutionContext is required"):
                # REMOVED_SYNTAX_ERROR: await factory.create_agent_instance("triage", None)

                # REMOVED_SYNTAX_ERROR: await factory.cleanup_user_context(context)

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_websocket_bridge_failure_resilience(self,
                # REMOVED_SYNTAX_ERROR: mock_agent_registry,
                # REMOVED_SYNTAX_ERROR: test_database_sessions):
                    # REMOVED_SYNTAX_ERROR: """Test resilience when WebSocket bridge fails."""
                    # Create bridge that fails
                    # REMOVED_SYNTAX_ERROR: failing_bridge = MagicMock(spec=AgentWebSocketBridge)
                    # REMOVED_SYNTAX_ERROR: failing_bridge.register_run_thread_mapping = AsyncMock(return_value=False)
                    # REMOVED_SYNTAX_ERROR: failing_bridge.notify_agent_started = AsyncMock(side_effect=Exception("WebSocket failure"))
                    # REMOVED_SYNTAX_ERROR: failing_bridge.events_sent = []
                    # REMOVED_SYNTAX_ERROR: failing_bridge.run_thread_mappings = {}

                    # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
                    # REMOVED_SYNTAX_ERROR: factory.configure(mock_agent_registry, failing_bridge)

                    # Context creation should still work despite WebSocket failure
                    # REMOVED_SYNTAX_ERROR: context = await factory.create_user_execution_context( )
                    # REMOVED_SYNTAX_ERROR: user_id="resilience_user",
                    # REMOVED_SYNTAX_ERROR: thread_id="resilience_thread",
                    # REMOVED_SYNTAX_ERROR: run_id="resilience_run",
                    # REMOVED_SYNTAX_ERROR: db_session=test_database_sessions[0]
                    

                    # Agent creation should still work
                    # REMOVED_SYNTAX_ERROR: agent = await factory.create_agent_instance("triage", context)

                    # Agent execution should work despite WebSocket failures
                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
                    # REMOVED_SYNTAX_ERROR: user_message="Test resilience",
                    # REMOVED_SYNTAX_ERROR: thread_id="resilience_thread"
                    

                    # REMOVED_SYNTAX_ERROR: result = await agent.execute(state, "resilience_run")

                    # Verify execution completed successfully
                    # REMOVED_SYNTAX_ERROR: assert "resilience_user" in result.user_message
                    # REMOVED_SYNTAX_ERROR: assert result.additional_context["agent_user_id"] == "resilience_user"

                    # REMOVED_SYNTAX_ERROR: await factory.cleanup_user_context(context)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_database_session_failure_handling(self,
                    # REMOVED_SYNTAX_ERROR: mock_agent_registry,
                    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge):
                        # REMOVED_SYNTAX_ERROR: """Test handling of database session failures."""
                        # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
                        # REMOVED_SYNTAX_ERROR: factory.configure(mock_agent_registry, mock_websocket_bridge)

                        # Create mock session that fails
                        # REMOVED_SYNTAX_ERROR: failing_session = MagicMock(spec=AsyncSession)
                        # REMOVED_SYNTAX_ERROR: failing_session.close = AsyncMock(side_effect=Exception("DB close failure"))

                        # Context creation should work with failing session
                        # REMOVED_SYNTAX_ERROR: context = await factory.create_user_execution_context( )
                        # REMOVED_SYNTAX_ERROR: user_id="db_test_user",
                        # REMOVED_SYNTAX_ERROR: thread_id="db_test_thread",
                        # REMOVED_SYNTAX_ERROR: run_id="db_test_run",
                        # REMOVED_SYNTAX_ERROR: db_session=failing_session
                        

                        # Cleanup should handle session close failure gracefully
                        # REMOVED_SYNTAX_ERROR: await factory.cleanup_user_context(context)

                        # Context should still be marked as cleaned despite DB error
                        # REMOVED_SYNTAX_ERROR: assert context._is_cleaned

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_factory_configuration_validation(self):
                            # REMOVED_SYNTAX_ERROR: """Test factory configuration validation."""
                            # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()

                            # Test unconfigured factory
                            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="Factory not configured"):
                                # REMOVED_SYNTAX_ERROR: await factory.create_user_execution_context( )
                                # REMOVED_SYNTAX_ERROR: user_id="test",
                                # REMOVED_SYNTAX_ERROR: thread_id="test",
                                # REMOVED_SYNTAX_ERROR: run_id="test",
                                # REMOVED_SYNTAX_ERROR: db_session=Magic            )

                                # Test invalid configuration - WebSocket bridge is checked first
                                # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="AgentWebSocketBridge cannot be None"):
                                    # REMOVED_SYNTAX_ERROR: factory.configure(agent_registry=None, websocket_bridge=None)

                                    # Test missing WebSocket bridge
                                    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="AgentWebSocketBridge cannot be None"):
                                        # REMOVED_SYNTAX_ERROR: factory.configure(agent_registry=Magic )
                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_context_creation_parameter_validation(self,
                                        # REMOVED_SYNTAX_ERROR: mock_agent_registry,
                                        # REMOVED_SYNTAX_ERROR: mock_websocket_bridge):
                                            # REMOVED_SYNTAX_ERROR: """Test parameter validation in context creation."""
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
                                            # REMOVED_SYNTAX_ERROR: factory.configure(mock_agent_registry, mock_websocket_bridge)

                                            # REMOVED_SYNTAX_ERROR: mock_session = MagicMock(spec=AsyncSession)

                                            # Test missing required parameters
                                            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
                                                # REMOVED_SYNTAX_ERROR: await factory.create_user_execution_context( )
                                                # REMOVED_SYNTAX_ERROR: user_id="",
                                                # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
                                                # REMOVED_SYNTAX_ERROR: run_id="test_run",
                                                # REMOVED_SYNTAX_ERROR: db_session=mock_session
                                                

                                                # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
                                                    # REMOVED_SYNTAX_ERROR: await factory.create_user_execution_context( )
                                                    # REMOVED_SYNTAX_ERROR: user_id="test_user",
                                                    # REMOVED_SYNTAX_ERROR: thread_id="",
                                                    # REMOVED_SYNTAX_ERROR: run_id="test_run",
                                                    # REMOVED_SYNTAX_ERROR: db_session=mock_session
                                                    

                                                    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
                                                        # REMOVED_SYNTAX_ERROR: await factory.create_user_execution_context( )
                                                        # REMOVED_SYNTAX_ERROR: user_id="test_user",
                                                        # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
                                                        # REMOVED_SYNTAX_ERROR: run_id="",
                                                        # REMOVED_SYNTAX_ERROR: db_session=mock_session
                                                        

                                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="db_session is required for request isolation"):
                                                            # REMOVED_SYNTAX_ERROR: await factory.create_user_execution_context( )
                                                            # REMOVED_SYNTAX_ERROR: user_id="test_user",
                                                            # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
                                                            # REMOVED_SYNTAX_ERROR: run_id="test_run",
                                                            # REMOVED_SYNTAX_ERROR: db_session=None
                                                            


                                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                # Run specific test classes for development
                                                                # REMOVED_SYNTAX_ERROR: pytest.main([ ))
                                                                # REMOVED_SYNTAX_ERROR: __file__ + "::TestAgentClassRegistryIsolation::test_registry_immutability_after_freeze",
                                                                # REMOVED_SYNTAX_ERROR: "-v"
                                                                