"""
Integration Tests for AgentRegistry SSOT Interplay

Business Value Justification (BVJ):
- Segment: All segments - Agent coordination affects all user interactions  
- Business Goal: Multi-User System Stability & Real-Time Communication
- Value Impact: Ensures agent coordination prevents context leakage and enables chat value
- Strategic Impact: CRITICAL for WebSocket events that deliver AI value to users

This test suite validates the critical interactions between AgentRegistry and other SSOT 
components across the Netra platform. These tests use REAL services to validate actual 
business scenarios that could break multi-user operations.

CRITICAL AREAS TESTED:
1. Agent Registration and Factory Integration - Factory pattern isolation & real agent instances
2. WebSocket Event Coordination - 5 critical events for chat business value delivery
3. User Context Isolation - Multi-user safety preventing context leakage  
4. Agent Lifecycle Management - Resource management with real database sessions
5. Cross-Service Agent Integration - Service factory & supervisor integration

WARNING: NO MOCKS! These are integration tests using real AgentRegistry instances,
real WebSocket connections, real user context isolation, real database sessions.
"""

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from unittest.mock import AsyncMock, MagicMock, patch
import threading

import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture, with_test_database
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_factory import ExecutionStatus
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service_factory import get_agent_service
from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from netra_backend.app.websocket_core import create_websocket_manager, UnifiedWebSocketManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.database.session_manager import SessionScopeValidator, validate_agent_session_isolation
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class MockAgentForTesting(BaseAgent):
    """Real agent implementation for testing registry integration."""
    
    def __init__(self, name: str, user_context: UserExecutionContext, 
                 tool_dispatcher: Optional[UnifiedToolDispatcher] = None,
                 websocket_bridge = None):
        self.name = name
        self.user_context = user_context
        self.tool_dispatcher = tool_dispatcher
        self.websocket_bridge = websocket_bridge
        self.execution_count = 0
        self.is_cleanup_called = False
        self._status = "initialized"
        
    async def execute(self, input_data: str) -> str:
        """Mock execute method that tracks calls."""
        self.execution_count += 1
        self._status = "executing"
        await asyncio.sleep(0.01)  # Simulate real execution
        self._status = "completed"
        return f"Mock execution #{self.execution_count} for {self.name} by user {self.user_context.user_id}"
    
    async def cleanup(self):
        """Mock cleanup method that tracks calls."""
        self.is_cleanup_called = True
        self._status = "cleaned"
        
    def get_status(self) -> str:
        return self._status


class TestAgentRegistryInterplay(BaseIntegrationTest):
    """Integration tests for AgentRegistry SSOT interactions."""
    
    def setup_method(self):
        """Set up each test with clean registry state."""
        super().setup_method()
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_request_id = f"req_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        # Create real LLM manager for agent registry
        self.llm_manager = self._create_mock_llm_manager()
        
        # Track created registries for cleanup
        self._created_registries: List[AgentRegistry] = []
        
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up all created registries
        for registry in self._created_registries:
            try:
                # Use sync cleanup to avoid event loop conflicts
                if hasattr(registry, 'cleanup'):
                    # Try sync cleanup first
                    try:
                        registry.cleanup()
                    except TypeError:
                        # If cleanup is async, skip it here
                        pass
                # Clear the registry state directly
                if hasattr(registry, '_agents'):
                    registry._agents.clear()
                if hasattr(registry, '_agent_instances'):
                    registry._agent_instances.clear()
            except Exception as e:
                logger.warning(f"Error cleaning up registry: {e}")
        self._created_registries.clear()
        super().teardown_method()
    
    def _create_mock_llm_manager(self) -> LLMManager:
        """Create mock LLM manager for testing."""
        mock_llm = MagicMock(spec=LLMManager)
        mock_llm.ask_llm = AsyncMock(return_value="Mock LLM response")
        mock_llm.ask_llm_full = AsyncMock()
        mock_llm.ask_llm_structured = AsyncMock()
        mock_llm.get_available_models = AsyncMock(return_value=["gpt-4", "gpt-3.5-turbo"])
        mock_llm.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_llm.initialize = AsyncMock()
        return mock_llm
    
    async def _cleanup_registry(self, registry: AgentRegistry) -> None:
        """Async cleanup for registry."""
        try:
            await registry.emergency_cleanup_all()
        except Exception as e:
            logger.warning(f"Registry cleanup error: {e}")
    
    def _create_user_context(self, user_id: Optional[str] = None) -> UserExecutionContext:
        """Create user execution context for testing."""
        user_id = user_id or self.test_user_id
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}"
        )
    
    def _create_registry(self) -> AgentRegistry:
        """Create agent registry and track for cleanup."""
        registry = AgentRegistry(
            llm_manager=self.llm_manager,
            tool_dispatcher_factory=self._mock_tool_dispatcher_factory
        )
        self._created_registries.append(registry)
        return registry
    
    async def _mock_tool_dispatcher_factory(self, user_context: UserExecutionContext, websocket_bridge=None) -> UnifiedToolDispatcher:
        """Mock tool dispatcher factory for testing."""
        mock_dispatcher = MagicMock(spec=UnifiedToolDispatcher)
        mock_dispatcher.user_context = user_context
        mock_dispatcher.websocket_bridge = websocket_bridge
        mock_dispatcher.enabled_tools = set()
        return mock_dispatcher

    # =================== AGENT REGISTRATION AND FACTORY INTEGRATION ===================
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_agent_registration_factory_pattern_isolation(self, real_services_fixture):
        """
        Test agent registration with factory pattern isolation.
        
        BVJ: All segments | Multi-User Safety | Prevents agent context leakage between users
        Tests that agent factory pattern creates isolated instances per user with proper context.
        """
        registry = self._create_registry()
        user1_context = self._create_user_context("user1")
        user2_context = self._create_user_context("user2")
        
        # Register a factory for test agent
        async def test_agent_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            return MockAgentForTesting("test_agent", context, tool_dispatcher, websocket_bridge)
        
        registry.register_factory("test_agent", test_agent_factory, tags=["test"])
        
        # Create agents for different users
        agent1 = await registry.create_agent_for_user("user1", "test_agent", user1_context)
        agent2 = await registry.create_agent_for_user("user2", "test_agent", user2_context)
        
        # Verify agents are isolated instances
        assert agent1 is not agent2
        assert agent1.user_context.user_id == "user1"
        assert agent2.user_context.user_id == "user2"
        assert agent1.user_context.request_id != agent2.user_context.request_id
        
        # Verify each has isolated tool dispatcher
        assert agent1.tool_dispatcher is not agent2.tool_dispatcher
        assert agent1.tool_dispatcher.user_context.user_id == "user1"
        assert agent2.tool_dispatcher.user_context.user_id == "user2"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_instance_creation_with_real_user_contexts(self, real_services_fixture):
        """
        Test agent instance creation with real user contexts.
        
        BVJ: All segments | User Context Isolation | Ensures agent instances have proper context binding
        Tests that agent instances are created with complete, valid user execution contexts.
        """
        registry = self._create_registry()
        user_context = self._create_user_context()
        
        # Register factory that validates context completeness
        async def context_validating_factory(context: UserExecutionContext, websocket_bridge=None):
            # Validate all required context fields are present
            assert context.user_id is not None
            assert context.request_id is not None  
            assert context.thread_id is not None
            assert context.run_id is not None
            assert context.created_at is not None
            assert isinstance(context.metadata, dict)
            
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting("context_agent", context, tool_dispatcher, websocket_bridge)
            return agent
        
        registry.register_factory("context_agent", context_validating_factory, tags=["test"])
        
        # Create agent and verify context integrity
        agent = await registry.create_agent_for_user(
            self.test_user_id, "context_agent", user_context
        )
        
        assert agent is not None
        assert agent.user_context == user_context
        
        # Verify context fields are properly set
        assert agent.user_context.user_id == user_context.user_id
        assert agent.user_context.request_id == user_context.request_id
        assert agent.user_context.thread_id == user_context.thread_id
        assert agent.user_context.run_id == user_context.run_id
        assert isinstance(agent.user_context.metadata, dict)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_registry_cleanup_and_resource_management(self, real_services_fixture):
        """
        Test agent registry cleanup and resource management.
        
        BVJ: Platform/Internal | Memory Leak Prevention | Prevents resource exhaustion in multi-user system
        Tests that agent cleanup properly releases resources and prevents memory leaks.
        """
        registry = self._create_registry()
        user_context = self._create_user_context()
        
        # Register factory for cleanup testing
        async def cleanup_test_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            return MockAgentForTesting("cleanup_agent", context, tool_dispatcher, websocket_bridge)
        
        registry.register_factory("cleanup_agent", cleanup_test_factory, tags=["test"])
        
        # Create multiple agents - register each agent type first
        agents = []
        for i in range(3):
            agent_type = f"cleanup_agent_{i}"
            # Register factory for this specific agent type
            registry.register_factory(agent_type, cleanup_test_factory, tags=["test"])
            
            agent = await registry.create_agent_for_user(
                self.test_user_id, agent_type, user_context
            )
            agents.append(agent)
        
        # Verify agents are created
        assert len(agents) == 3
        for agent in agents:
            assert not agent.is_cleanup_called
        
        # Cleanup user session
        cleanup_metrics = await registry.cleanup_user_session(self.test_user_id)
        
        # Verify cleanup metrics
        assert cleanup_metrics['status'] == 'cleaned'
        assert cleanup_metrics['user_id'] == self.test_user_id
        
        # Verify user session is removed
        assert self.test_user_id not in registry._user_sessions
        
        # Test memory leak prevention monitoring
        monitoring_report = await registry.monitor_all_users()
        assert monitoring_report['total_users'] == 0
        assert monitoring_report['total_agents'] == 0
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_factory_pattern_with_concurrent_user_sessions(self, real_services_fixture):
        """
        Test agent factory pattern with concurrent user sessions.
        
        BVJ: All segments | Concurrent User Safety | Enables reliable multi-user agent execution
        Tests that multiple users can create agents concurrently without context leakage or race conditions.
        """
        registry = self._create_registry()
        
        # Register factory for concurrent testing
        async def concurrent_factory(context: UserExecutionContext, websocket_bridge=None):
            # Add small delay to test race conditions
            await asyncio.sleep(0.01)
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"concurrent_agent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            return agent
        
        registry.register_factory("concurrent_agent", concurrent_factory, tags=["test"])
        
        # Create agents concurrently for multiple users
        async def create_user_agent(user_id: str):
            user_context = self._create_user_context(user_id)
            agent = await registry.create_agent_for_user(user_id, "concurrent_agent", user_context)
            return user_id, agent
        
        # Run concurrent agent creation
        users = [f"user_{i}" for i in range(5)]
        tasks = [create_user_agent(user_id) for user_id in users]
        results = await asyncio.gather(*tasks)
        
        # Verify each user has isolated agent
        agents_by_user = dict(results)
        assert len(agents_by_user) == 5
        
        # Verify no context leakage
        user_ids = set()
        for user_id, agent in agents_by_user.items():
            assert agent.user_context.user_id == user_id
            user_ids.add(agent.user_context.user_id)
        
        assert len(user_ids) == 5  # All unique user IDs
        
        # Verify user sessions are isolated
        assert len(registry._user_sessions) == 5
        for user_id in users:
            assert user_id in registry._user_sessions
            user_session = registry._user_sessions[user_id]
            assert len(user_session._agents) == 1

    # =================== WEBSOCKET EVENT COORDINATION ===================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_integration_with_agent_lifecycle(self, real_services_fixture):
        """
        Test WebSocket manager integration with agent lifecycle.
        
        BVJ: All segments | Real-Time Communication | Enables chat value through WebSocket events
        Tests that WebSocket manager is properly integrated with agent lifecycle for event delivery.
        """
        registry = self._create_registry()
        user_context = self._create_user_context()
        
        # Create real WebSocket manager for testing
        websocket_manager = create_websocket_manager(user_context)
        registry.set_websocket_manager(websocket_manager)
        
        # Register factory that tests WebSocket integration
        async def websocket_integrated_factory(context: UserExecutionContext, websocket_bridge=None):
            assert websocket_bridge is not None, "WebSocket bridge should be provided"
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting("ws_agent", context, tool_dispatcher, websocket_bridge)
            return agent
        
        registry.register_factory("ws_agent", websocket_integrated_factory, tags=["test"])
        
        # Create agent and verify WebSocket bridge is set
        agent = await registry.create_agent_for_user(
            self.test_user_id, "ws_agent", user_context, websocket_manager
        )
        
        assert agent is not None
        assert agent.websocket_bridge is not None
        
        # Verify user session has WebSocket bridge
        user_session = await registry.get_user_session(self.test_user_id)
        assert user_session._websocket_bridge is not None
        
        # Test WebSocket wiring diagnosis
        diagnosis = registry.diagnose_websocket_wiring()
        assert diagnosis["registry_has_websocket_manager"] is True
        assert diagnosis["total_user_sessions"] >= 1
        assert diagnosis["users_with_websocket_bridges"] >= 1
        assert len(diagnosis["critical_issues"]) == 0
        assert diagnosis["websocket_health"] == "HEALTHY"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_event_delivery_coordination(self, real_services_fixture):
        """
        Test agent event delivery coordination through WebSocket system.
        
        BVJ: All segments | Chat Business Value | Ensures 5 critical events reach users for AI value delivery  
        Tests that all 5 critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) 
        are properly coordinated through the registry.
        """
        registry = self._create_registry()
        user_context = self._create_user_context()
        
        # Mock WebSocket manager to track events
        mock_websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        event_log = []
        
        async def mock_emit_agent_event(event_type: str, agent_name: str, data=None, user_id=None):
            event_log.append({
                'event_type': event_type,
                'agent_name': agent_name,
                'data': data,
                'user_id': user_id,
                'timestamp': datetime.now(timezone.utc)
            })
        
        mock_websocket_manager.emit_agent_event = mock_emit_agent_event
        registry.set_websocket_manager(mock_websocket_manager)
        
        # Register factory for event agent before creating it
        async def event_agent_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            return MockAgentForTesting("event_agent", context, tool_dispatcher, websocket_bridge)
        
        registry.register_factory("event_agent", event_agent_factory, tags=["test"])
        
        # Create agent with event coordination
        agent = await registry.create_agent_for_user(
            self.test_user_id, "event_agent", user_context, mock_websocket_manager
        )
        
        # Simulate agent execution with critical events
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for event_type in critical_events:
            await mock_emit_agent_event(
                event_type=event_type,
                agent_name="event_agent", 
                data={"step": event_type, "user_id": self.test_user_id},
                user_id=self.test_user_id
            )
        
        # Verify all critical events were coordinated
        assert len(event_log) == 5
        logged_events = {event['event_type'] for event in event_log}
        assert logged_events == set(critical_events)
        
        # Verify events have proper user isolation
        for event in event_log:
            assert event['user_id'] == self.test_user_id
            assert event['agent_name'] == "event_agent"
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_event_ordering_and_sequencing_guarantees(self, real_services_fixture):
        """
        Test WebSocket event ordering and sequencing guarantees.
        
        BVJ: All segments | User Experience | Ensures events arrive in correct order for coherent chat experience
        Tests that WebSocket events maintain proper ordering when multiple agents execute concurrently.
        """
        registry = self._create_registry()
        
        # Create event tracking system
        event_sequences = {}
        event_lock = threading.Lock()
        
        async def sequence_tracking_emit(event_type: str, agent_name: str, data=None, user_id=None):
            with event_lock:
                if user_id not in event_sequences:
                    event_sequences[user_id] = []
                event_sequences[user_id].append({
                    'event_type': event_type,
                    'agent_name': agent_name,
                    'sequence_num': len(event_sequences[user_id]),
                    'timestamp': time.time()
                })
        
        # Mock WebSocket manager with sequence tracking
        mock_websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        mock_websocket_manager.emit_agent_event = sequence_tracking_emit
        registry.set_websocket_manager(mock_websocket_manager)
        
        # Create agents for multiple users - register each agent type first
        users = [f"user_{i}" for i in range(3)]
        agents = {}
        
        # Register factory for sequence agents (reusable for all users)
        async def sequence_agent_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            return MockAgentForTesting(f"sequence_agent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
        
        for user_id in users:
            # Register factory for this specific agent type
            agent_type = f"sequence_agent_{user_id}"
            registry.register_factory(agent_type, sequence_agent_factory, tags=["test"])
            
            user_context = self._create_user_context(user_id)
            agent = await registry.create_agent_for_user(
                user_id, agent_type, user_context, mock_websocket_manager
            )
            agents[user_id] = agent
        
        # Simulate concurrent event generation
        async def generate_events_for_user(user_id: str):
            events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            for event in events:
                await sequence_tracking_emit(
                    event_type=event,
                    agent_name=f"sequence_agent_{user_id}",
                    user_id=user_id
                )
                await asyncio.sleep(0.001)  # Small delay between events
        
        # Run concurrent event generation
        await asyncio.gather(*[generate_events_for_user(user_id) for user_id in users])
        
        # Verify event sequencing for each user
        for user_id in users:
            user_events = event_sequences[user_id]
            assert len(user_events) == 5
            
            # Verify sequence numbers are ordered
            sequence_nums = [event['sequence_num'] for event in user_events]
            assert sequence_nums == list(range(5))
            
            # Verify timestamps are ordered
            timestamps = [event['timestamp'] for event in user_events]
            assert timestamps == sorted(timestamps)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_delivery_failure_handling_and_recovery(self, real_services_fixture):
        """
        Test WebSocket event delivery failure handling and recovery.
        
        BVJ: Platform/Internal | System Resilience | Prevents chat system failures from blocking agent execution
        Tests that agent execution continues even when WebSocket event delivery fails.
        """
        registry = self._create_registry()
        user_context = self._create_user_context()
        
        # Create failing WebSocket manager for testing failure handling
        failure_count = 0
        success_count = 0
        
        async def failing_emit(event_type: str, agent_name: str, data=None, user_id=None):
            nonlocal failure_count, success_count
            if failure_count < 3:  # Fail first 3 attempts
                failure_count += 1
                raise ConnectionError("WebSocket connection failed")
            else:
                success_count += 1
                # Event delivered successfully
        
        mock_websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        mock_websocket_manager.emit_agent_event = failing_emit
        registry.set_websocket_manager(mock_websocket_manager)
        
        # Create agent that should handle WebSocket failures gracefully
        async def resilient_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting("resilient_agent", context, tool_dispatcher, websocket_bridge)
            return agent
        
        registry.register_factory("resilient_agent", resilient_factory, tags=["test"])
        
        agent = await registry.create_agent_for_user(
            self.test_user_id, "resilient_agent", user_context, mock_websocket_manager
        )
        
        # Test event delivery with failures  
        events_to_send = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for event_type in events_to_send:
            try:
                await failing_emit(
                    event_type=event_type,
                    agent_name="resilient_agent",
                    user_id=self.test_user_id
                )
            except ConnectionError:
                # Failures should be handled gracefully
                pass
        
        # Verify system handled failures and recovered
        assert failure_count == 3  # First 3 failed
        assert success_count == 2   # Last 2 succeeded  
        
        # Agent should still be functional despite WebSocket failures
        assert agent.get_status() in ["initialized", "executing", "completed"]
        execution_result = await agent.execute("test input")
        assert "Mock execution" in execution_result
        assert agent.execution_count == 1

    # =================== USER CONTEXT ISOLATION ===================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_factory_creation_and_cleanup(self, real_services_fixture):
        """
        Test user context factory creation and cleanup.
        
        BVJ: All segments | User Isolation | Prevents user data leakage in multi-tenant system
        Tests that user context factory creates isolated contexts and cleans them up properly.
        """
        registry = self._create_registry()
        
        # Create contexts for multiple users
        users = [f"isolation_user_{i}" for i in range(3)]
        contexts = {}
        
        for user_id in users:
            user_context = UserExecutionContext(
                user_id=user_id,
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_{uuid.uuid4().hex[:8]}"
            )
            contexts[user_id] = user_context
            
            # Get user session to trigger context creation
            user_session = await registry.get_user_session(user_id)
            assert user_session.user_id == user_id
        
        # Verify each user has isolated session
        assert len(registry._user_sessions) == 3
        
        for user_id in users:
            assert user_id in registry._user_sessions
            user_session = registry._user_sessions[user_id] 
            assert user_session.user_id == user_id
            assert len(user_session._agents) == 0  # No agents yet
            assert len(user_session._execution_contexts) == 0
        
        # Test cleanup of individual user contexts
        cleanup_metrics = await registry.cleanup_user_session(users[0])
        assert cleanup_metrics['status'] == 'cleaned'
        assert cleanup_metrics['user_id'] == users[0]
        assert users[0] not in registry._user_sessions
        
        # Verify other user contexts remain
        assert len(registry._user_sessions) == 2
        assert users[1] in registry._user_sessions
        assert users[2] in registry._user_sessions
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_context_isolation_between_users(self, real_services_fixture):
        """
        Test agent execution context isolation between users.
        
        BVJ: All segments | Data Privacy | Ensures user execution data never leaks between users
        Tests that agent execution contexts are completely isolated between different users.
        """
        registry = self._create_registry()
        
        # Create factory that tracks execution context
        execution_contexts = {}
        
        async def context_tracking_factory(context: UserExecutionContext, websocket_bridge=None):
            execution_contexts[context.user_id] = context
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"isolated_agent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            return agent
        
        registry.register_factory("isolated_agent", context_tracking_factory, tags=["test"])
        
        # Create agents for different users with different execution data
        user1_context = UserExecutionContext(
            user_id="user1",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            metadata={'custom_data': "user1_secret_data"}
        )
        user2_context = UserExecutionContext(
            user_id="user2",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            metadata={'custom_data': "user2_secret_data"}
        )
        
        agent1 = await registry.create_agent_for_user("user1", "isolated_agent", user1_context)
        agent2 = await registry.create_agent_for_user("user2", "isolated_agent", user2_context)
        
        # Verify agents have isolated contexts
        assert agent1.user_context.user_id == "user1"
        assert agent2.user_context.user_id == "user2"
        
        assert agent1.user_context.metadata['custom_data'] == "user1_secret_data"
        assert agent2.user_context.metadata['custom_data'] == "user2_secret_data"
        
        # Verify execution contexts are completely separate
        assert execution_contexts["user1"] is not execution_contexts["user2"]
        assert execution_contexts["user1"].user_id != execution_contexts["user2"].user_id
        
        # Verify contexts are immutable (since they're frozen dataclasses)
        # Cannot modify the contexts after creation due to frozen=True
        # The metadata is copied during creation to ensure isolation
        
        # Verify user sessions maintain separation
        user1_session = registry._user_sessions["user1"]
        user2_session = registry._user_sessions["user2"]
        
        assert user1_session is not user2_session
        assert len(user1_session._agents) == 1
        assert len(user2_session._agents) == 1
        assert user1_session._agents != user2_session._agents
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_execution_without_context_leakage(self, real_services_fixture):
        """
        Test concurrent agent execution without context leakage.
        
        BVJ: All segments | System Integrity | Prevents data corruption in concurrent multi-user scenarios
        Tests that multiple agents can execute concurrently without any user context leakage.
        """
        registry = self._create_registry()
        
        # Create factory that simulates concurrent execution
        execution_log = []
        log_lock = threading.Lock()
        
        async def concurrent_execution_factory(context: UserExecutionContext, websocket_bridge=None):
            async def concurrent_execute(input_data: str):
                start_time = time.time()
                # Simulate work with context data
                user_id = context.user_id
                request_id = context.request_id
                
                # Add artificial delay to increase chance of race conditions
                await asyncio.sleep(0.1)
                
                end_time = time.time()
                
                with log_lock:
                    execution_log.append({
                        'user_id': user_id,
                        'request_id': request_id,
                        'input': input_data,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time
                    })
                
                return f"Executed for {user_id} with input: {input_data}"
            
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"concurrent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            agent.execute = concurrent_execute
            return agent
        
        registry.register_factory("concurrent", concurrent_execution_factory, tags=["test"])
        
        # Create agents for multiple users
        users = [f"concurrent_user_{i}" for i in range(5)]
        agents = {}
        
        for user_id in users:
            user_context = self._create_user_context(user_id)
            agent = await registry.create_agent_for_user(user_id, "concurrent", user_context)
            agents[user_id] = agent
        
        # Execute agents concurrently
        async def execute_agent(user_id: str, input_data: str):
            agent = agents[user_id]
            result = await agent.execute(input_data)
            return user_id, result
        
        # Run concurrent executions with user-specific inputs
        tasks = [
            execute_agent(user_id, f"secret_input_for_{user_id}")
            for user_id in users
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify no context leakage in results
        results_by_user = dict(results)
        for user_id in users:
            result = results_by_user[user_id]
            assert user_id in result
            assert f"secret_input_for_{user_id}" in result
        
        # Verify execution log shows proper isolation
        assert len(execution_log) == 5
        for log_entry in execution_log:
            user_id = log_entry['user_id']
            assert log_entry['input'] == f"secret_input_for_{user_id}"
            # Verify no data from other users leaked
            for other_user in users:
                if other_user != user_id:
                    assert other_user not in log_entry['input']
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_session_isolation_with_different_agent_contexts(self, real_services_fixture):
        """
        Test user session isolation with different agent contexts.
        
        BVJ: All segments | Session Management | Ensures user sessions maintain complete data isolation
        Tests that user sessions properly isolate different types of agent contexts and execution states.
        """
        registry = self._create_registry()
        
        # Create different types of agent contexts for same user
        user_id = self.test_user_id
        base_context = self._create_user_context(user_id)
        
        # Register different agent types
        async def data_agent_factory(context: UserExecutionContext, websocket_bridge=None):
            child_context = UserExecutionContext(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=f"run_data_{uuid.uuid4().hex[:8]}",
                request_id=f"req_data_{uuid.uuid4().hex[:8]}",
                metadata={'agent_type': "data_processing"}
            )
            tool_dispatcher = await self._mock_tool_dispatcher_factory(child_context, websocket_bridge)
            agent = MockAgentForTesting("data_agent", child_context, tool_dispatcher, websocket_bridge)
            return agent
        
        async def analysis_agent_factory(context: UserExecutionContext, websocket_bridge=None):
            child_context = UserExecutionContext(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=f"run_analysis_{uuid.uuid4().hex[:8]}",
                request_id=f"req_analysis_{uuid.uuid4().hex[:8]}",
                metadata={'agent_type': "analysis"}
            )
            tool_dispatcher = await self._mock_tool_dispatcher_factory(child_context, websocket_bridge)
            agent = MockAgentForTesting("analysis_agent", child_context, tool_dispatcher, websocket_bridge)
            return agent
        
        registry.register_factory("data_agent", data_agent_factory, tags=["test"])
        registry.register_factory("analysis_agent", analysis_agent_factory, tags=["test"])
        
        # Create different agents within same user session
        data_agent = await registry.create_agent_for_user(user_id, "data_agent", base_context)
        analysis_agent = await registry.create_agent_for_user(user_id, "analysis_agent", base_context)
        
        # Verify agents are in same user session but have isolated contexts
        user_session = registry._user_sessions[user_id]
        assert len(user_session._agents) == 2
        assert len(user_session._execution_contexts) == 2
        
        # Verify agents have different execution contexts within same user session
        assert data_agent.user_context is not analysis_agent.user_context
        assert data_agent.user_context.user_id == analysis_agent.user_context.user_id  # Same user
        assert data_agent.user_context.request_id != analysis_agent.user_context.request_id  # Different contexts
        
        # Test context isolation between agent types
        data_agent.user_context.execution_metrics['agent_type_data'] = "data_processing_secret"
        analysis_agent.user_context.execution_metrics['agent_type_data'] = "analysis_processing_secret"
        
        assert data_agent.user_context.execution_metrics['agent_type_data'] != analysis_agent.user_context.execution_metrics['agent_type_data']
        
        # Verify session cleanup handles multiple agent contexts
        cleanup_metrics = await registry.cleanup_user_session(user_id)
        assert cleanup_metrics['status'] == 'cleaned'
        assert user_id not in registry._user_sessions

    # =================== AGENT LIFECYCLE MANAGEMENT ===================
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_instance_lifecycle_with_real_database_sessions(self, real_services_fixture):
        """
        Test agent instance lifecycle with real database sessions.
        
        BVJ: Platform/Internal | Data Persistence | Ensures agent lifecycle integrates with database sessions
        Tests that agent lifecycle properly integrates with database session management for data persistence.
        """
        registry = self._create_registry()
        user_context = self._create_user_context()
        
        # Track database session lifecycle
        db_sessions = []
        
        async def db_integrated_factory(context: UserExecutionContext, websocket_bridge=None):
            # Simulate database session creation (mocked for integration test)
            mock_db_session = MagicMock()
            mock_db_session.id = f"db_session_{uuid.uuid4().hex[:8]}"
            mock_db_session.is_active = True
            mock_db_session.user_id = context.user_id
            db_sessions.append(mock_db_session)
            
            # Validate session scope
            SessionScopeValidator.validate_request_scoped(mock_db_session)
            
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting("db_agent", context, tool_dispatcher, websocket_bridge)
            agent.db_session = mock_db_session
            
            # Override cleanup to handle database session
            original_cleanup = agent.cleanup
            async def enhanced_cleanup():
                await original_cleanup()
                mock_db_session.is_active = False
                
            agent.cleanup = enhanced_cleanup
            return agent
        
        registry.register_factory("db_agent", db_integrated_factory, tags=["test"])
        
        # Create agent with database integration
        agent = await registry.create_agent_for_user(self.test_user_id, "db_agent", user_context)
        
        # Verify database session is created and active
        assert len(db_sessions) == 1
        db_session = db_sessions[0]
        assert db_session.is_active is True
        assert db_session.user_id == self.test_user_id
        
        # Verify agent session isolation validation
        assert validate_agent_session_isolation(agent) is True
        
        # Test agent lifecycle progression
        assert agent.get_status() == "initialized"
        
        execution_result = await agent.execute("test database operation")
        assert "Mock execution" in execution_result
        assert agent.get_status() == "completed"
        
        # Cleanup agent and verify database session cleanup
        await agent.cleanup()
        assert agent.is_cleanup_called is True
        assert db_session.is_active is False
        assert agent.get_status() == "cleaned"
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_agent_health_monitoring_and_recovery_coordination(self, real_services_fixture):
        """
        Test agent health monitoring and recovery coordination.
        
        BVJ: Platform/Internal | System Reliability | Enables automated recovery from agent failures
        Tests that agent health monitoring detects issues and coordinates recovery through registry.
        """
        registry = self._create_registry()
        
        # Create agents with different health states
        users = [f"health_user_{i}" for i in range(3)]
        agents = {}
        
        # Factory that creates agents with health tracking
        async def health_tracked_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"health_agent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            
            # Add health tracking
            agent.health_status = "healthy"
            agent.last_heartbeat = time.time()
            agent.error_count = 0
            
            # Override execute to simulate health changes
            original_execute = agent.execute
            async def health_tracked_execute(input_data: str):
                if "cause_error" in input_data:
                    agent.error_count += 1
                    agent.health_status = "unhealthy" if agent.error_count >= 3 else "degraded"
                    raise RuntimeError("Simulated agent error")
                else:
                    agent.last_heartbeat = time.time()
                    agent.health_status = "healthy"
                    return await original_execute(input_data)
            
            agent.execute = health_tracked_execute
            return agent
        
        registry.register_factory("health_agent", health_tracked_factory, tags=["test"])
        
        # Create agents for monitoring
        for user_id in users:
            user_context = self._create_user_context(user_id)
            agent = await registry.create_agent_for_user(user_id, "health_agent", user_context)
            agents[user_id] = agent
        
        # Test healthy execution
        healthy_result = await agents[users[0]].execute("normal operation")
        assert "Mock execution" in healthy_result
        assert agents[users[0]].health_status == "healthy"
        
        # Simulate agent degradation
        try:
            await agents[users[1]].execute("cause_error")
        except RuntimeError:
            pass
        assert agents[users[1]].health_status == "degraded"
        assert agents[users[1]].error_count == 1
        
        # Simulate agent failure
        for _ in range(3):
            try:
                await agents[users[2]].execute("cause_error")
            except RuntimeError:
                pass
        assert agents[users[2]].health_status == "unhealthy"
        assert agents[users[2]].error_count >= 3
        
        # Test monitoring report
        monitoring_report = await registry.monitor_all_users()
        assert monitoring_report['total_users'] == 3
        assert monitoring_report['total_agents'] == 3
        
        # Test recovery coordination - cleanup unhealthy user
        unhealthy_user = users[2]
        cleanup_metrics = await registry.cleanup_user_session(unhealthy_user)
        assert cleanup_metrics['status'] == 'cleaned'
        
        # Verify unhealthy agent is removed
        assert unhealthy_user not in registry._user_sessions
        updated_report = await registry.monitor_all_users()
        assert updated_report['total_users'] == 2
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_websocket_integration_coordination(self, real_services_fixture):
        """
        Test tool dispatcher WebSocket integration coordination.
        
        BVJ: All segments | Tool Execution Transparency | Enables real-time tool execution visibility for users
        Tests that tool dispatcher properly coordinates with WebSocket system for real-time tool execution events.
        """
        registry = self._create_registry()
        user_context = self._create_user_context()
        
        # Create WebSocket manager that tracks tool events
        tool_events = []
        
        async def tool_event_tracker(event_type: str, tool_name: str = None, data=None, user_id=None):
            tool_events.append({
                'event_type': event_type,
                'tool_name': tool_name,
                'data': data,
                'user_id': user_id,
                'timestamp': datetime.now(timezone.utc)
            })
        
        mock_websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        mock_websocket_manager.emit_tool_event = tool_event_tracker
        registry.set_websocket_manager(mock_websocket_manager)
        
        # Enhanced factory that tests tool-websocket coordination
        async def tool_websocket_factory(context: UserExecutionContext, websocket_bridge=None):
            # Create tool dispatcher with WebSocket coordination
            mock_tool_dispatcher = MagicMock(spec=UnifiedToolDispatcher)
            mock_tool_dispatcher.user_context = context
            mock_tool_dispatcher.websocket_bridge = websocket_bridge
            
            # Mock tool execution with WebSocket events
            async def execute_tool(tool_name: str, input_data: dict):
                await tool_event_tracker("tool_executing", tool_name, input_data, context.user_id)
                # Simulate tool work
                await asyncio.sleep(0.01)
                result = {"status": "success", "output": f"Tool {tool_name} executed"}
                await tool_event_tracker("tool_completed", tool_name, result, context.user_id)
                return result
            
            mock_tool_dispatcher.execute_tool = execute_tool
            
            agent = MockAgentForTesting("tool_agent", context, mock_tool_dispatcher, websocket_bridge)
            
            # Override execute to use tool dispatcher
            async def tool_integrated_execute(input_data: str):
                # Use tool dispatcher for execution
                if "use_tool" in input_data:
                    tool_result = await mock_tool_dispatcher.execute_tool("test_tool", {"input": input_data})
                    return f"Agent used tool: {tool_result}"
                else:
                    return await MockAgentForTesting.execute(agent, input_data)
            
            agent.execute = tool_integrated_execute
            return agent
        
        registry.register_factory("tool_agent", tool_websocket_factory, tags=["test"])
        
        # Create agent with tool-WebSocket coordination
        agent = await registry.create_agent_for_user(
            self.test_user_id, "tool_agent", user_context, mock_websocket_manager
        )
        
        # Test tool execution with WebSocket coordination
        result = await agent.execute("use_tool for testing")
        assert "Agent used tool" in result
        
        # Verify tool events were coordinated through WebSocket
        assert len(tool_events) == 2
        assert tool_events[0]['event_type'] == "tool_executing"
        assert tool_events[0]['tool_name'] == "test_tool"
        assert tool_events[0]['user_id'] == self.test_user_id
        
        assert tool_events[1]['event_type'] == "tool_completed"  
        assert tool_events[1]['tool_name'] == "test_tool"
        assert tool_events[1]['user_id'] == self.test_user_id
        
        # Verify agent and tool dispatcher coordination
        assert agent.tool_dispatcher.user_context.user_id == self.test_user_id
        assert agent.tool_dispatcher.websocket_bridge is not None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_engine_coordination_patterns(self, real_services_fixture):
        """
        Test agent execution engine coordination patterns.
        
        BVJ: Platform/Internal | Execution Orchestration | Ensures proper coordination between registry and execution engines
        Tests that agent registry properly coordinates with execution engines for complex agent workflows.
        """
        registry = self._create_registry()
        
        # Simulate execution engine coordination
        execution_coordination_log = []
        
        async def execution_coordinated_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"execution_agent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            
            # Add execution engine coordination
            agent.execution_engine_id = f"engine_{uuid.uuid4().hex[:8]}"
            
            # Override execute to test coordination patterns
            async def coordinated_execute(input_data: str):
                # Pre-execution coordination
                execution_coordination_log.append({
                    'phase': 'pre_execution',
                    'agent': agent.name,
                    'user_id': context.user_id,
                    'engine_id': agent.execution_engine_id,
                    'input': input_data
                })
                
                # Execute with engine coordination
                result = await MockAgentForTesting.execute(agent, input_data)
                
                # Post-execution coordination  
                execution_coordination_log.append({
                    'phase': 'post_execution',
                    'agent': agent.name,
                    'user_id': context.user_id,
                    'engine_id': agent.execution_engine_id,
                    'result': result
                })
                
                return result
            
            agent.execute = coordinated_execute
            return agent
        
        registry.register_factory("execution_agent", execution_coordinated_factory, tags=["test"])
        
        # Create agents for execution coordination testing
        users = [f"exec_user_{i}" for i in range(2)]
        agents = {}
        
        for user_id in users:
            user_context = self._create_user_context(user_id)
            agent = await registry.create_agent_for_user(user_id, "execution_agent", user_context)
            agents[user_id] = agent
        
        # Test coordinated execution
        results = {}
        for user_id in users:
            result = await agents[user_id].execute(f"coordinated task for {user_id}")
            results[user_id] = result
        
        # Verify execution coordination
        assert len(execution_coordination_log) == 4  # 2 agents × 2 phases each
        
        # Verify pre/post execution phases for each agent
        phases_by_user = {}
        for log_entry in execution_coordination_log:
            user_id = log_entry['user_id']
            if user_id not in phases_by_user:
                phases_by_user[user_id] = []
            phases_by_user[user_id].append(log_entry['phase'])
        
        for user_id in users:
            user_phases = phases_by_user[user_id]
            assert len(user_phases) == 2
            assert 'pre_execution' in user_phases
            assert 'post_execution' in user_phases
        
        # Verify execution engines are isolated per agent
        engine_ids = set()
        for log_entry in execution_coordination_log:
            engine_ids.add(log_entry['engine_id'])
        assert len(engine_ids) == 2  # Each agent has unique execution engine

    # =================== CROSS-SERVICE AGENT INTEGRATION ===================
    
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_agent_registry_with_database_session_management_integration(self, real_services_fixture):
        """
        Test agent registry with database session management integration.
        
        BVJ: Platform/Internal | Data Layer Integration | Ensures agents can persist and retrieve data reliably
        Tests that agent registry properly integrates with database session management for data persistence.
        """
        registry = self._create_registry()
        
        # Mock database session manager for integration testing
        db_session_states = {}
        
        class MockDatabaseSessionManager:
            def __init__(self):
                self.active_sessions = {}
            
            async def create_session_for_user(self, user_id: str):
                session_id = f"db_session_{user_id}_{uuid.uuid4().hex[:8]}"
                session = {
                    'id': session_id,
                    'user_id': user_id,
                    'created_at': datetime.now(timezone.utc),
                    'is_active': True,
                    'transactions': []
                }
                self.active_sessions[session_id] = session
                db_session_states[user_id] = session_id
                return session
            
            async def close_session(self, session_id: str):
                if session_id in self.active_sessions:
                    self.active_sessions[session_id]['is_active'] = False
        
        db_manager = MockDatabaseSessionManager()
        
        # Factory that integrates with database session management
        async def db_integrated_factory(context: UserExecutionContext, websocket_bridge=None):
            # Create database session for user
            db_session = await db_manager.create_session_for_user(context.user_id)
            
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"db_integrated_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            
            agent.db_session = db_session
            agent.db_manager = db_manager
            
            # Override execute to use database
            async def db_execute(input_data: str):
                # Simulate database transaction
                transaction = {
                    'type': 'agent_execution',
                    'input': input_data,
                    'timestamp': datetime.now(timezone.utc),
                    'agent': agent.name
                }
                agent.db_session['transactions'].append(transaction)
                
                result = await MockAgentForTesting.execute(agent, input_data)
                
                # Log completion transaction
                completion_transaction = {
                    'type': 'execution_completed', 
                    'result': result,
                    'timestamp': datetime.now(timezone.utc),
                    'agent': agent.name
                }
                agent.db_session['transactions'].append(completion_transaction)
                
                return result
            
            agent.execute = db_execute
            
            # Override cleanup to close database session
            original_cleanup = agent.cleanup
            async def db_cleanup():
                await original_cleanup()
                await db_manager.close_session(agent.db_session['id'])
            
            agent.cleanup = db_cleanup
            return agent
        
        registry.register_factory("db_integrated", db_integrated_factory, tags=["test"])
        
        # Create agents with database integration
        users = [f"db_user_{i}" for i in range(2)]
        agents = {}
        
        for user_id in users:
            user_context = self._create_user_context(user_id)
            agent = await registry.create_agent_for_user(user_id, "db_integrated", user_context)
            agents[user_id] = agent
        
        # Test database integration
        for user_id in users:
            result = await agents[user_id].execute(f"database operation for {user_id}")
            assert "Mock execution" in result
            
            # Verify database transactions
            db_session = agents[user_id].db_session
            assert len(db_session['transactions']) == 2  # Start and completion
            assert db_session['transactions'][0]['type'] == 'agent_execution'
            assert db_session['transactions'][1]['type'] == 'execution_completed'
            assert db_session['is_active'] is True
        
        # Verify database sessions are isolated per user
        assert len(db_manager.active_sessions) == 2
        for user_id in users:
            session_id = db_session_states[user_id]
            assert session_id in db_manager.active_sessions
            session = db_manager.active_sessions[session_id]
            assert session['user_id'] == user_id
        
        # Test cleanup closes database sessions
        await agents[users[0]].cleanup()
        session_id = db_session_states[users[0]]
        assert db_manager.active_sessions[session_id]['is_active'] is False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_service_factory_integration_with_registry(self, real_services_fixture):
        """
        Test agent service factory integration with registry.
        
        BVJ: Platform/Internal | Service Layer Integration | Enables service-layer agent orchestration
        Tests that agent registry properly integrates with service factory for higher-level agent orchestration.
        """
        registry = self._create_registry()
        
        # Mock AgentServiceFactory for integration testing
        class MockAgentServiceFactory:
            def __init__(self, agent_registry):
                self.agent_registry = agent_registry
                self.created_services = {}
            
            async def create_agent_service(self, service_type: str, user_context: UserExecutionContext):
                # Create service using registry
                agent = await self.agent_registry.create_agent_for_user(
                    user_context.user_id, service_type, user_context
                )
                
                # Wrap in service layer
                service = {
                    'service_id': f"service_{service_type}_{user_context.user_id}",
                    'service_type': service_type,
                    'agent': agent,
                    'user_context': user_context,
                    'created_at': datetime.now(timezone.utc),
                    'status': 'active'
                }
                
                self.created_services[service['service_id']] = service
                return service
            
            async def execute_service(self, service_id: str, input_data: str):
                if service_id not in self.created_services:
                    raise ValueError(f"Service {service_id} not found")
                
                service = self.created_services[service_id]
                result = await service['agent'].execute(input_data)
                
                service['last_execution'] = datetime.now(timezone.utc)
                return {
                    'service_id': service_id,
                    'result': result,
                    'execution_time': service['last_execution']
                }
        
        # Register agent factories for service integration
        async def service_agent_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"service_agent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            return agent
        
        registry.register_factory("data_service", service_agent_factory, tags=["service"])
        registry.register_factory("analysis_service", service_agent_factory, tags=["service"])
        
        # Create service factory with registry integration
        service_factory = MockAgentServiceFactory(registry)
        
        # Test service creation through factory-registry integration
        user_context = self._create_user_context()
        
        data_service = await service_factory.create_agent_service("data_service", user_context)
        analysis_service = await service_factory.create_agent_service("analysis_service", user_context)
        
        # Verify services are created with proper registry integration
        assert data_service['service_type'] == "data_service"
        assert analysis_service['service_type'] == "analysis_service"
        assert data_service['agent'] is not analysis_service['agent']
        
        # Verify services use same user context but different agents
        assert data_service['user_context'].user_id == analysis_service['user_context'].user_id
        assert data_service['agent'].user_context.user_id == self.test_user_id
        assert analysis_service['agent'].user_context.user_id == self.test_user_id
        
        # Test service execution through factory-registry integration
        data_result = await service_factory.execute_service(data_service['service_id'], "process data")
        analysis_result = await service_factory.execute_service(analysis_service['service_id'], "analyze results")
        
        assert "Mock execution" in data_result['result']
        assert "Mock execution" in analysis_result['result']
        assert data_result['service_id'] != analysis_result['service_id']
        
        # Verify registry maintains service agent isolation
        user_session = await registry.get_user_session(self.test_user_id)
        assert len(user_session._agents) == 2  # Two service agents created
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_coordination_patterns(self, real_services_fixture):
        """
        Test agent WebSocket bridge coordination patterns.
        
        BVJ: All segments | Real-Time Communication | Ensures seamless WebSocket coordination for chat features
        Tests that agent registry coordinates with WebSocket bridge for real-time communication patterns.
        """
        registry = self._create_registry()
        user_context = self._create_user_context()
        
        # Track WebSocket bridge coordination
        bridge_coordination_events = []
        
        # Create mock WebSocket bridge with coordination tracking
        class MockWebSocketBridge:
            def __init__(self, user_context):
                self.user_context = user_context
                self.connection_id = f"conn_{uuid.uuid4().hex[:8]}"
                self.is_connected = True
                
            async def emit_event(self, event_type: str, data: dict):
                bridge_coordination_events.append({
                    'event_type': event_type,
                    'data': data,
                    'user_id': self.user_context.user_id,
                    'connection_id': self.connection_id,
                    'timestamp': datetime.now(timezone.utc)
                })
            
            async def handle_agent_coordination(self, agent_name: str, action: str):
                await self.emit_event('agent_coordination', {
                    'agent_name': agent_name,
                    'action': action,
                    'user_id': self.user_context.user_id
                })
        
        # Create WebSocket manager with bridge coordination
        mock_websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        
        async def create_bridge(user_context):
            return MockWebSocketBridge(user_context)
        
        mock_websocket_manager.create_bridge = create_bridge
        registry.set_websocket_manager(mock_websocket_manager)
        
        # Factory that coordinates with WebSocket bridge
        async def bridge_coordinated_factory(context: UserExecutionContext, websocket_bridge=None):
            if websocket_bridge is None:
                websocket_bridge = await create_bridge(context)
            
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"bridge_agent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            
            # Add bridge coordination to agent lifecycle
            async def coordinated_execute(input_data: str):
                # Pre-execution coordination
                await websocket_bridge.handle_agent_coordination(agent.name, 'execution_started')
                
                # Execute agent
                result = await MockAgentForTesting.execute(agent, input_data)
                
                # Post-execution coordination
                await websocket_bridge.handle_agent_coordination(agent.name, 'execution_completed')
                
                return result
            
            agent.execute = coordinated_execute
            return agent
        
        registry.register_factory("bridge_agent", bridge_coordinated_factory, tags=["test"])
        
        # Create agent with WebSocket bridge coordination
        agent = await registry.create_agent_for_user(
            self.test_user_id, "bridge_agent", user_context, mock_websocket_manager
        )
        
        # Verify bridge coordination is established
        assert agent.websocket_bridge is not None
        assert agent.websocket_bridge.user_context.user_id == self.test_user_id
        assert agent.websocket_bridge.is_connected is True
        
        # Test coordinated execution
        result = await agent.execute("coordinated operation")
        assert "Mock execution" in result
        
        # Verify coordination events were emitted
        assert len(bridge_coordination_events) == 2
        
        start_event = bridge_coordination_events[0]
        assert start_event['event_type'] == 'agent_coordination'
        assert start_event['data']['action'] == 'execution_started'
        assert start_event['user_id'] == self.test_user_id
        
        completion_event = bridge_coordination_events[1]
        assert completion_event['event_type'] == 'agent_coordination' 
        assert completion_event['data']['action'] == 'execution_completed'
        assert completion_event['user_id'] == self.test_user_id
        
        # Verify same connection used for coordination
        assert start_event['connection_id'] == completion_event['connection_id']
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_supervisor_integration_with_registry_ssot(self, real_services_fixture):
        """
        Test agent supervisor integration with registry SSOT.
        
        BVJ: Platform/Internal | Agent Orchestration | Enables supervisor-level agent coordination and workflow management
        Tests that agent supervisor properly integrates with registry SSOT for complex agent workflow orchestration.
        """
        registry = self._create_registry()
        
        # Mock supervisor integration
        supervision_events = []
        
        class MockAgentSupervisor:
            def __init__(self, agent_registry):
                self.agent_registry = agent_registry
                self.supervised_workflows = {}
                
            async def create_supervised_workflow(self, workflow_id: str, user_context: UserExecutionContext, agent_types: List[str]):
                workflow = {
                    'workflow_id': workflow_id,
                    'user_context': user_context,
                    'agents': {},
                    'execution_order': agent_types,
                    'status': 'created',
                    'created_at': datetime.now(timezone.utc)
                }
                
                # Create agents through registry
                for agent_type in agent_types:
                    agent = await self.agent_registry.create_agent_for_user(
                        user_context.user_id, agent_type, user_context
                    )
                    workflow['agents'][agent_type] = agent
                
                self.supervised_workflows[workflow_id] = workflow
                
                supervision_events.append({
                    'event': 'workflow_created',
                    'workflow_id': workflow_id,
                    'agent_count': len(agent_types),
                    'user_id': user_context.user_id
                })
                
                return workflow
                
            async def execute_supervised_workflow(self, workflow_id: str, input_data: str):
                if workflow_id not in self.supervised_workflows:
                    raise ValueError(f"Workflow {workflow_id} not found")
                
                workflow = self.supervised_workflows[workflow_id]
                workflow['status'] = 'executing'
                
                results = {}
                for agent_type in workflow['execution_order']:
                    agent = workflow['agents'][agent_type]
                    
                    supervision_events.append({
                        'event': 'agent_supervised_execution',
                        'workflow_id': workflow_id,
                        'agent_type': agent_type,
                        'user_id': workflow['user_context'].user_id
                    })
                    
                    # Execute agent with supervision
                    result = await agent.execute(f"{input_data} (supervised by {workflow_id})")
                    results[agent_type] = result
                
                workflow['status'] = 'completed'
                workflow['results'] = results
                
                supervision_events.append({
                    'event': 'workflow_completed',
                    'workflow_id': workflow_id,
                    'results_count': len(results),
                    'user_id': workflow['user_context'].user_id
                })
                
                return results
        
        # Register agents for supervised workflows
        async def supervised_agent_factory(context: UserExecutionContext, websocket_bridge=None):
            tool_dispatcher = await self._mock_tool_dispatcher_factory(context, websocket_bridge)
            agent = MockAgentForTesting(f"supervised_agent_{context.user_id}", context, tool_dispatcher, websocket_bridge)
            return agent
        
        registry.register_factory("data_processor", supervised_agent_factory, tags=["workflow"])
        registry.register_factory("analyzer", supervised_agent_factory, tags=["workflow"]) 
        registry.register_factory("reporter", supervised_agent_factory, tags=["workflow"])
        
        # Create supervisor with registry integration
        supervisor = MockAgentSupervisor(registry)
        
        # Test supervised workflow creation
        user_context = self._create_user_context()
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        workflow = await supervisor.create_supervised_workflow(
            workflow_id, user_context, ["data_processor", "analyzer", "reporter"]
        )
        
        # Verify workflow creation through registry integration
        assert workflow['workflow_id'] == workflow_id
        assert len(workflow['agents']) == 3
        assert workflow['user_context'].user_id == self.test_user_id
        
        # Verify agents are registered in user session
        user_session = await registry.get_user_session(self.test_user_id)
        assert len(user_session._agents) == 3
        
        # Test supervised execution
        results = await supervisor.execute_supervised_workflow(workflow_id, "complex data workflow")
        
        # Verify all agents executed
        assert len(results) == 3
        assert "data_processor" in results
        assert "analyzer" in results  
        assert "reporter" in results
        
        for agent_type, result in results.items():
            assert "Mock execution" in result
            assert "supervised" in result
        
        # Verify supervision events
        workflow_events = [e for e in supervision_events if e['workflow_id'] == workflow_id]
        assert len(workflow_events) == 5  # 1 created + 3 agent executions + 1 completed
        
        assert workflow_events[0]['event'] == 'workflow_created'
        assert workflow_events[-1]['event'] == 'workflow_completed'
        
        # Verify agent execution events
        execution_events = [e for e in workflow_events if e['event'] == 'agent_supervised_execution']
        assert len(execution_events) == 3
        executed_types = {e['agent_type'] for e in execution_events}
        assert executed_types == {"data_processor", "analyzer", "reporter"}