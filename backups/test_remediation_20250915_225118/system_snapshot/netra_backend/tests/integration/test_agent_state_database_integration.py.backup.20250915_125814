"""
Comprehensive integration tests for BaseAgent, UnifiedStateManager, and DatabaseSessionManager interactions.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure conversation continuity and multi-user isolation
- Value Impact: Agent state persistence enables context preservation across user sessions
- Strategic Impact: Core platform reliability for multi-user AI interactions with data consistency

Test Coverage:
- BaseAgent execution with state persistence through UnifiedStateManager
- Multi-user agent execution with isolated state management
- Agent conversation history persistence and retrieval  
- State synchronization between agents and database sessions
- Agent failure recovery with state restoration
- Session isolation across concurrent agent executions
- State versioning and conflict resolution
- Cross-agent state sharing and coordination
- Performance optimization with state caching
"""

import asyncio
import pytest
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.managers.unified_state_manager import (
    UnifiedStateManager, StateScope, StateType, StateStatus,
    StateEntry, StateQuery, StateChangeEvent, StateManagerFactory
)
from netra_backend.app.database.session_manager import DatabaseSessionManager, SessionIsolationError
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.agent import SubAgentLifecycle


class MockAgent(BaseAgent):
    """Test agent implementation for integration testing."""
    
    def __init__(self, name: str = "MockAgent", **kwargs):
        super().__init__(name=name, **kwargs)
        self.execution_results: List[Dict[str, Any]] = []
        self.state_operations: List[Dict[str, Any]] = []
    
    async def _execute_with_user_context(
        self, 
        context: UserExecutionContext, 
        stream_updates: bool = False
    ) -> Any:
        """Modern execution pattern implementation."""
        await self.emit_agent_started(f"{self.name} starting execution")
        
        # Store execution context in state manager
        if hasattr(self, '_state_manager') and self._state_manager:
            await self._store_execution_state(context)
        
        await self.emit_thinking("Processing user request with state persistence")
        
        # Simulate some work with state operations
        result = await self._simulate_work_with_state(context)
        
        await self.emit_agent_completed(result, context)
        return result
    
    async def _store_execution_state(self, context: UserExecutionContext) -> None:
        """Store execution state using UnifiedStateManager."""
        state_key = f"agent_execution_{self.name}_{context.run_id}"
        execution_state = {
            "agent_name": self.name,
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "run_id": context.run_id,
            "status": "executing",
            "timestamp": time.time()
        }
        
        self._state_manager.set_agent_state(
            agent_id=self.name,
            key=state_key,
            value=execution_state,
            ttl_seconds=3600
        )
        
        self.state_operations.append({
            "operation": "store_execution_state",
            "key": state_key,
            "value": execution_state
        })
    
    async def _simulate_work_with_state(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Simulate work that involves state operations."""
        # Store conversation history
        if hasattr(self, '_state_manager'):
            history_key = f"conversation_history_{context.thread_id}"
            current_history = self._state_manager.get_thread_state(
                context.thread_id, 
                history_key, 
                []
            )
            
            current_history.append({
                "agent": self.name,
                "message": f"Processed request from user {context.user_id}",
                "timestamp": time.time()
            })
            
            self._state_manager.set_thread_state(
                thread_id=context.thread_id,
                key=history_key,
                value=current_history
            )
            
            self.state_operations.append({
                "operation": "update_conversation_history",
                "key": history_key,
                "history_length": len(current_history)
            })
        
        result = {
            "status": "completed",
            "message": f"Agent {self.name} completed successfully",
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "run_id": context.run_id,
            "state_operations": len(self.state_operations)
        }
        
        self.execution_results.append(result)
        return result


class TestAgentStateIntegration(BaseIntegrationTest):
    """Test BaseAgent execution with UnifiedStateManager integration."""
    
    @pytest.fixture
    def state_manager(self):
        """Create UnifiedStateManager instance for testing."""
        return UnifiedStateManager(
            user_id="test_user_123",
            enable_persistence=False,  # In-memory for tests
            enable_ttl_cleanup=False,  # Disable cleanup for deterministic tests
            cleanup_interval=3600,  # Long interval for tests
            max_memory_entries=1000
        )
    
    @pytest.fixture
    def user_context(self):
        """Create UserExecutionContext for testing."""
        return UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789",
            request_id=str(uuid.uuid4()),
            metadata={"test_mode": True, "agent_input": "test input"}
        )
    
    @pytest.fixture
    def mock_agent(self, state_manager):
        """Create MockAgent with state manager."""
        agent = MockAgent(name="TestAgent")
        agent._state_manager = state_manager
        return agent
    
    @pytest.mark.integration
    async def test_agent_execution_with_state_persistence(self, mock_agent, user_context):
        """Test BaseAgent execution with state persistence through UnifiedStateManager."""
        # Execute agent with user context
        result = await mock_agent.execute(user_context)
        
        # Verify execution result
        assert result is not None
        assert result["status"] == "completed"
        assert result["user_id"] == user_context.user_id
        assert result["thread_id"] == user_context.thread_id
        assert result["run_id"] == user_context.run_id
        assert result["state_operations"] > 0
        
        # Verify state was persisted
        assert len(mock_agent.state_operations) > 0
        assert any(op["operation"] == "store_execution_state" for op in mock_agent.state_operations)
        assert any(op["operation"] == "update_conversation_history" for op in mock_agent.state_operations)
    
    @pytest.mark.integration
    async def test_agent_state_scopes_isolation(self, state_manager):
        """Test agent state isolation across different scopes."""
        # Create agents with different contexts
        agent1 = MockAgent(name="Agent1")
        agent1._state_manager = state_manager
        
        agent2 = MockAgent(name="Agent2") 
        agent2._state_manager = state_manager
        
        # Set state at different scopes
        state_manager.set_user_state("user1", "preference", "value1")
        state_manager.set_user_state("user2", "preference", "value2")
        
        state_manager.set_session_state("session1", "data", "session1_data")
        state_manager.set_session_state("session2", "data", "session2_data")
        
        state_manager.set_thread_state("thread1", "context", "thread1_context")
        state_manager.set_thread_state("thread2", "context", "thread2_context")
        
        state_manager.set_agent_state("Agent1", "execution_state", "agent1_state")
        state_manager.set_agent_state("Agent2", "execution_state", "agent2_state")
        
        # Verify isolation
        assert state_manager.get_user_state("user1", "preference") == "value1"
        assert state_manager.get_user_state("user2", "preference") == "value2"
        assert state_manager.get_user_state("user1", "preference") != state_manager.get_user_state("user2", "preference")
        
        assert state_manager.get_session_state("session1", "data") == "session1_data"
        assert state_manager.get_session_state("session2", "data") == "session2_data"
        
        assert state_manager.get_thread_state("thread1", "context") == "thread1_context"
        assert state_manager.get_thread_state("thread2", "context") == "thread2_context"
        
        assert state_manager.get_agent_state("Agent1", "execution_state") == "agent1_state"
        assert state_manager.get_agent_state("Agent2", "execution_state") == "agent2_state"
    
    @pytest.mark.integration
    async def test_database_session_manager_integration(self, user_context):
        """Test DatabaseSessionManager integration with agent execution contexts."""
        # Create mock database session manager
        session_manager = DatabaseSessionManager()
        
        # Verify session manager handles user context
        session = await session_manager.create_session()
        assert session is None  # Stub implementation returns None
        
        # Verify session isolation validation works
        agent = MockAgent(name="TestAgent")
        isolation_result = session_manager.validate_agent_session_isolation(agent)
        assert isolation_result is True  # Stub always returns True
        
        # Test session scope validation
        from netra_backend.app.database.session_manager import SessionScopeValidator
        mock_session = Mock()
        mock_session._global_storage_flag = False
        
        # Should not raise exception for properly scoped session
        SessionScopeValidator.validate_request_scoped(mock_session)
        
        # Should raise exception for globally stored session
        mock_session._global_storage_flag = True
        with pytest.raises(SessionIsolationError):
            SessionScopeValidator.validate_request_scoped(mock_session)
    
    @pytest.mark.integration
    async def test_multi_user_agent_execution_isolation(self, state_manager):
        """Test multi-user agent execution with isolated state management."""
        # Create contexts for different users
        user1_context = UserExecutionContext(
            user_id="user_001",
            thread_id="thread_001", 
            run_id="run_001",
            metadata={"agent_input": "user1 request"}
        )
        
        user2_context = UserExecutionContext(
            user_id="user_002",
            thread_id="thread_002",
            run_id="run_002", 
            metadata={"agent_input": "user2 request"}
        )
        
        # Create agents for different users
        agent1 = MockAgent(name="Agent1")
        agent1._state_manager = state_manager
        
        agent2 = MockAgent(name="Agent2")
        agent2._state_manager = state_manager
        
        # Execute agents concurrently
        results = await asyncio.gather(
            agent1.execute(user1_context),
            agent2.execute(user2_context),
            return_exceptions=True
        )
        
        result1, result2 = results
        
        # Verify both executions completed successfully
        assert result1["status"] == "completed"
        assert result2["status"] == "completed"
        
        # Verify user isolation
        assert result1["user_id"] == "user_001"
        assert result2["user_id"] == "user_002"
        assert result1["thread_id"] != result2["thread_id"]
        assert result1["run_id"] != result2["run_id"]
        
        # Verify state isolation - agents should have separate state operations
        assert len(agent1.state_operations) > 0
        assert len(agent2.state_operations) > 0
        
        # State operations should be isolated to their respective contexts
        for op in agent1.state_operations:
            if "key" in op:
                assert "user_001" in str(op["key"]) or "thread_001" in str(op["key"]) or "Agent1" in str(op["key"])
        
        for op in agent2.state_operations:
            if "key" in op:
                assert "user_002" in str(op["key"]) or "thread_002" in str(op["key"]) or "Agent2" in str(op["key"])
    
    @pytest.mark.integration
    async def test_conversation_history_persistence(self, state_manager, user_context):
        """Test agent conversation history persistence and retrieval."""
        agent = MockAgent(name="ConversationAgent")
        agent._state_manager = state_manager
        
        # Execute agent multiple times to build conversation history
        for i in range(3):
            modified_context = UserExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=f"{user_context.run_id}_{i}",
                metadata={"agent_input": f"message {i}"}
            )
            await agent.execute(modified_context)
        
        # Retrieve conversation history
        history_key = f"conversation_history_{user_context.thread_id}"
        history = state_manager.get_thread_state(
            user_context.thread_id,
            history_key,
            []
        )
        
        # Verify history was persisted correctly
        assert len(history) == 3
        for i, entry in enumerate(history):
            assert entry["agent"] == "ConversationAgent"
            assert f"user {user_context.user_id}" in entry["message"]
            assert "timestamp" in entry
        
        # Verify history is accessible across agent instances
        new_agent = MockAgent(name="ConversationAgent")
        new_agent._state_manager = state_manager
        
        retrieved_history = state_manager.get_thread_state(
            user_context.thread_id,
            history_key,
            []
        )
        
        assert len(retrieved_history) == 3
        assert retrieved_history == history
    
    @pytest.mark.integration
    async def test_agent_failure_recovery_with_state(self, state_manager, user_context):
        """Test agent failure recovery with state restoration."""
        agent = MockAgent(name="RecoveryAgent")
        agent._state_manager = state_manager
        
        # Store pre-failure state
        recovery_key = "recovery_checkpoint"
        checkpoint_data = {
            "phase": "processing",
            "partial_result": {"step": 1, "data": "important_data"},
            "timestamp": time.time()
        }
        
        state_manager.set_agent_state(
            agent_id=agent.name,
            key=recovery_key,
            value=checkpoint_data,
            ttl_seconds=3600
        )
        
        # Simulate agent failure and recovery
        class FailingAgent(MockAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.should_fail = True
            
            async def _simulate_work_with_state(self, context):
                if self.should_fail:
                    self.should_fail = False
                    raise Exception("Simulated agent failure")
                
                # Recovery: check for checkpoint state
                recovery_data = self._state_manager.get_agent_state(
                    self.name,
                    recovery_key,
                    None
                )
                
                if recovery_data:
                    result = await super()._simulate_work_with_state(context)
                    result["recovered_from_checkpoint"] = recovery_data
                    return result
                
                return await super()._simulate_work_with_state(context)
        
        failing_agent = FailingAgent(name="RecoveryAgent")
        failing_agent._state_manager = state_manager
        
        # First execution should fail
        with pytest.raises(Exception, match="Simulated agent failure"):
            await failing_agent.execute(user_context)
        
        # Second execution should recover using state
        result = await failing_agent.execute(user_context)
        
        assert result["status"] == "completed"
        assert "recovered_from_checkpoint" in result
        assert result["recovered_from_checkpoint"]["phase"] == "processing"
        assert result["recovered_from_checkpoint"]["partial_result"]["data"] == "important_data"
    
    @pytest.mark.integration
    async def test_session_isolation_concurrent_agents(self, state_manager):
        """Test session isolation across concurrent agent executions."""
        num_concurrent_sessions = 5
        sessions = []
        agents = []
        
        # Create multiple concurrent sessions
        for i in range(num_concurrent_sessions):
            context = UserExecutionContext(
                user_id=f"user_{i:03d}",
                thread_id=f"thread_{i:03d}",
                run_id=f"run_{i:03d}",
                metadata={"session_id": f"session_{i:03d}"}
            )
            sessions.append(context)
            
            agent = MockAgent(name=f"ConcurrentAgent_{i}")
            agent._state_manager = state_manager
            agents.append(agent)
        
        # Execute all agents concurrently
        tasks = [
            agent.execute(session)
            for agent, session in zip(agents, sessions)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions completed successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Agent {i} failed: {result}"
            assert result["status"] == "completed"
            assert result["user_id"] == f"user_{i:03d}"
            assert result["thread_id"] == f"thread_{i:03d}"
            assert result["run_id"] == f"run_{i:03d}"
        
        # Verify state isolation - each agent should have separate state
        for i, agent in enumerate(agents):
            assert len(agent.state_operations) > 0
            
            # Check that state operations are scoped to this agent's context
            for op in agent.state_operations:
                if "key" in op and "value" in op:
                    # State should contain references to this agent's context
                    key_str = str(op["key"])
                    value_str = str(op["value"])
                    
                    # Should contain this agent's identifiers
                    assert (f"user_{i:03d}" in key_str or f"user_{i:03d}" in value_str or
                           f"thread_{i:03d}" in key_str or f"thread_{i:03d}" in value_str or
                           f"ConcurrentAgent_{i}" in key_str or f"ConcurrentAgent_{i}" in value_str)
    
    @pytest.mark.integration
    async def test_state_versioning_and_conflict_resolution(self, state_manager):
        """Test state versioning and conflict resolution."""
        # Test state versioning
        key = "versioned_state"
        initial_value = {"version": 1, "data": "initial"}
        
        state_manager.set(key, initial_value, scope=StateScope.GLOBAL)
        entry = state_manager._states[key]
        initial_version = entry.version
        
        # Update state multiple times
        for i in range(3):
            updated_value = {"version": i + 2, "data": f"update_{i}"}
            state_manager.set(key, updated_value, scope=StateScope.GLOBAL)
        
        final_entry = state_manager._states[key]
        assert final_entry.version > initial_version
        assert final_entry.value["version"] == 4
        assert final_entry.value["data"] == "update_2"
        
        # Test atomic updates to prevent conflicts
        counter_key = "atomic_counter"
        state_manager.set(counter_key, 0, scope=StateScope.GLOBAL)
        
        # Simulate concurrent updates using atomic update
        def increment_counter(current_value):
            return (current_value or 0) + 1
        
        # Perform multiple atomic increments
        for _ in range(10):
            state_manager.update(counter_key, increment_counter)
        
        final_count = state_manager.get(counter_key)
        assert final_count == 10
    
    @pytest.mark.integration
    async def test_agent_state_cleanup_and_garbage_collection(self, state_manager):
        """Test agent state cleanup and garbage collection."""
        agent = MockAgent(name="CleanupAgent")
        agent._state_manager = state_manager
        
        # Create temporary state with short TTL
        temp_key = "temporary_state"
        temp_value = {"data": "temporary", "expires_soon": True}
        
        state_manager.set(
            temp_key,
            temp_value,
            scope=StateScope.TEMPORARY,
            ttl_seconds=1  # 1 second TTL
        )
        
        # Verify state exists initially
        retrieved_value = state_manager.get(temp_key)
        assert retrieved_value == temp_value
        assert state_manager.exists(temp_key)
        
        # Wait for TTL expiration
        await asyncio.sleep(1.1)
        
        # Verify state is expired and cleaned up
        expired_value = state_manager.get(temp_key)
        assert expired_value is None
        assert not state_manager.exists(temp_key)
        
        # Test cleanup of agent-specific state
        agent_state_key = "cleanup_test"
        state_manager.set_agent_state(
            agent_id=agent.name,
            key=agent_state_key,
            value={"test": "cleanup"},
            ttl_seconds=2
        )
        
        # Verify agent state exists
        agent_value = state_manager.get_agent_state(agent.name, agent_state_key)
        assert agent_value["test"] == "cleanup"
        
        # Clear agent states
        cleared_count = state_manager.clear_agent_states(agent.name)
        assert cleared_count >= 1
        
        # Verify agent state is cleared
        cleared_value = state_manager.get_agent_state(agent.name, agent_state_key)
        assert cleared_value is None
    
    @pytest.mark.integration
    async def test_cross_agent_state_coordination(self, state_manager):
        """Test cross-agent state sharing and coordination."""
        # Create multiple agents that need to coordinate
        producer_agent = MockAgent(name="ProducerAgent")
        producer_agent._state_manager = state_manager
        
        consumer_agent = MockAgent(name="ConsumerAgent") 
        consumer_agent._state_manager = state_manager
        
        coordinator_agent = MockAgent(name="CoordinatorAgent")
        coordinator_agent._state_manager = state_manager
        
        # Set up shared coordination state
        coordination_key = "agent_coordination"
        shared_state = {
            "tasks": ["task1", "task2", "task3"],
            "completed_tasks": [],
            "active_agents": []
        }
        
        state_manager.set(
            coordination_key,
            shared_state,
            scope=StateScope.GLOBAL,
            state_type=StateType.CONFIGURATION_STATE
        )
        
        # Producer agent adds tasks
        def add_task(current_state):
            if current_state is None:
                current_state = shared_state.copy()
            current_state["tasks"].append("task4")
            current_state["active_agents"].append("ProducerAgent")
            return current_state
        
        updated_state = state_manager.update(coordination_key, add_task)
        assert "task4" in updated_state["tasks"]
        assert "ProducerAgent" in updated_state["active_agents"]
        
        # Consumer agent processes tasks
        def process_task(current_state):
            if current_state and current_state["tasks"]:
                task = current_state["tasks"].pop(0)
                current_state["completed_tasks"].append(task)
                if "ConsumerAgent" not in current_state["active_agents"]:
                    current_state["active_agents"].append("ConsumerAgent")
            return current_state
        
        for _ in range(2):  # Process 2 tasks
            state_manager.update(coordination_key, process_task)
        
        # Coordinator agent checks status
        final_state = state_manager.get(coordination_key)
        assert len(final_state["completed_tasks"]) == 2
        assert len(final_state["tasks"]) == 2  # 4 total - 2 processed = 2 remaining
        assert "ProducerAgent" in final_state["active_agents"]
        assert "ConsumerAgent" in final_state["active_agents"]
        
        # Test agent coordination with events
        change_events = []
        
        def capture_changes(event: StateChangeEvent):
            change_events.append(event)
        
        state_manager.add_change_listener(capture_changes)
        
        # Make coordinated state change
        def coordinator_update(current_state):
            if current_state:
                current_state["coordinator_status"] = "monitoring"
                current_state["active_agents"].append("CoordinatorAgent")
            return current_state
        
        state_manager.update(coordination_key, coordinator_update)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify coordination events were captured
        assert len(change_events) > 0
        latest_event = change_events[-1]
        assert latest_event.key == coordination_key
        assert latest_event.change_type == "update"
        assert "CoordinatorAgent" in str(latest_event.new_value)
    
    @pytest.mark.integration
    async def test_websocket_state_integration(self, state_manager):
        """Test state persistence with WebSocket disconnections."""
        # Simulate WebSocket connection state
        connection_id = "websocket_conn_123"
        user_id = "websocket_user_456"
        
        # Store WebSocket connection state
        connection_state = {
            "user_id": user_id,
            "connected_at": time.time(),
            "last_activity": time.time(),
            "subscriptions": ["agent_events", "state_changes"]
        }
        
        state_manager.set_websocket_state(
            connection_id=connection_id,
            key="connection_info",
            value=connection_state,
            ttl_seconds=1800  # 30 minutes
        )
        
        # Create agent that works with WebSocket state
        websocket_agent = MockAgent(name="WebSocketAgent")
        websocket_agent._state_manager = state_manager
        
        # Add WebSocket-aware execution logic
        async def websocket_execution(context):
            # Check if user has active WebSocket connection
            ws_state = state_manager.get_websocket_state(
                connection_id,
                "connection_info",
                None
            )
            
            if ws_state and ws_state["user_id"] == context.user_id:
                # User is connected via WebSocket
                result = await websocket_agent._simulate_work_with_state(context)
                result["websocket_connected"] = True
                result["connection_id"] = connection_id
                
                # Update last activity
                def update_activity(current_state):
                    if current_state:
                        current_state["last_activity"] = time.time()
                    return current_state
                
                state_manager.update(
                    f"websocket:{connection_id}:connection_info",
                    update_activity
                )
                
                return result
            else:
                # User not connected, store result for later delivery
                result = await websocket_agent._simulate_work_with_state(context)
                result["websocket_connected"] = False
                
                # Store result for later WebSocket delivery
                pending_key = f"pending_results_{context.user_id}"
                pending_results = state_manager.get_user_state(
                    context.user_id,
                    pending_key,
                    []
                )
                pending_results.append(result)
                
                state_manager.set_user_state(
                    user_id=context.user_id,
                    key=pending_key,
                    value=pending_results,
                    ttl_seconds=7200  # 2 hours
                )
                
                return result
        
        websocket_agent._simulate_work_with_state = websocket_execution
        
        # Test execution with active WebSocket
        ws_context = UserExecutionContext(
            user_id=user_id,
            thread_id="ws_thread_789",
            run_id="ws_run_012",
            websocket_connection_id=connection_id,
            metadata={"agent_input": "websocket test"}
        )
        
        result = await websocket_agent.execute(ws_context)
        
        assert result["websocket_connected"] is True
        assert result["connection_id"] == connection_id
        
        # Verify WebSocket state was updated
        updated_ws_state = state_manager.get_websocket_state(
            connection_id,
            "connection_info"
        )
        assert updated_ws_state["last_activity"] > connection_state["last_activity"]
        
        # Test execution without WebSocket connection
        state_manager.delete(f"websocket:{connection_id}:connection_info")
        
        offline_result = await websocket_agent.execute(ws_context)
        
        assert offline_result["websocket_connected"] is False
        
        # Verify result was stored for later delivery
        pending_results = state_manager.get_user_state(
            user_id,
            f"pending_results_{user_id}",
            []
        )
        assert len(pending_results) == 1
        assert pending_results[0]["websocket_connected"] is False
    
    @pytest.mark.integration
    async def test_state_caching_and_performance(self, state_manager):
        """Test agent state caching and performance optimization."""
        # Create agent with performance metrics
        perf_agent = MockAgent(name="PerformanceAgent")
        perf_agent._state_manager = state_manager
        
        # Test cache hit/miss performance
        cache_key = "performance_test_data"
        test_data = {"large_dataset": [f"item_{i}" for i in range(1000)]}
        
        # First access - cache miss
        start_time = time.time()
        state_manager.set(cache_key, test_data, scope=StateScope.GLOBAL)
        set_time = time.time() - start_time
        
        # Second access - cache hit
        start_time = time.time()
        retrieved_data = state_manager.get(cache_key)
        get_time = time.time() - start_time
        
        assert retrieved_data == test_data
        assert get_time < set_time  # Get should be faster than set
        
        # Test performance metrics
        initial_metrics = state_manager._metrics.copy()
        
        # Perform multiple operations
        for i in range(100):
            state_manager.set(f"perf_key_{i}", f"value_{i}")
            state_manager.get(f"perf_key_{i}")
        
        final_metrics = state_manager._metrics
        
        assert final_metrics["total_operations"] > initial_metrics["total_operations"]
        assert final_metrics["get_operations"] > initial_metrics["get_operations"]
        assert final_metrics["set_operations"] > initial_metrics["set_operations"]
        assert final_metrics["cache_hits"] > initial_metrics["cache_hits"]
        
        # Test memory limit enforcement
        original_limit = state_manager.max_memory_entries
        state_manager.max_memory_entries = 50  # Small limit for testing
        
        # Add entries beyond limit
        for i in range(60):
            state_manager.set(f"memory_test_{i}", f"data_{i}")
        
        # Verify memory limit was enforced
        assert len(state_manager._states) <= state_manager.max_memory_entries
        
        # Restore original limit
        state_manager.max_memory_entries = original_limit
    
    @pytest.mark.integration
    async def test_database_session_lifecycle_with_agent_execution(self):
        """Test database session lifecycle with agent execution."""
        # Create mock session manager
        session_manager = DatabaseSessionManager()
        
        # Test session creation and cleanup
        session = await session_manager.create_session()
        assert session is None  # Stub implementation
        
        await session_manager.close_session(session)  # Should not raise
        
        # Test with agent execution context
        context = UserExecutionContext(
            user_id="db_test_user",
            thread_id="db_test_thread", 
            run_id="db_test_run",
            db_session=None  # No actual session for stub
        )
        
        agent = MockAgent(name="DatabaseAgent")
        
        # Execute agent with database context
        result = await agent.execute(context)
        
        assert result["status"] == "completed"
        assert result["user_id"] == "db_test_user"
        
        # Verify session isolation validation
        from netra_backend.app.database.session_manager import validate_agent_session_isolation
        isolation_check = validate_agent_session_isolation(agent)
        assert isolation_check is True
    
    @pytest.mark.integration
    async def test_state_validation_and_integrity(self, state_manager):
        """Test state validation and integrity checks."""
        # Test state entry validation
        with pytest.raises(Exception):  # Should validate state structure
            state_manager.set("", "invalid_key")  # Empty key should be invalid
        
        # Test state type validation
        state_manager.set(
            "typed_state",
            {"type": "test"},
            state_type=StateType.AGENT_EXECUTION
        )
        
        # Verify type validation on retrieval
        retrieved = state_manager.get(
            "typed_state",
            state_type=StateType.AGENT_EXECUTION
        )
        assert retrieved["type"] == "test"
        
        # Type mismatch should return default
        wrong_type = state_manager.get(
            "typed_state",
            default="default_value",
            state_type=StateType.USER_PREFERENCES
        )
        assert wrong_type == "default_value"
        
        # Test scope validation
        state_manager.set(
            "scoped_state",
            "scoped_value",
            scope=StateScope.SESSION,
            session_id="session_123"
        )
        
        scoped_value = state_manager.get(
            "scoped_state",
            scope=StateScope.SESSION
        )
        assert scoped_value == "scoped_value"
        
        # Scope mismatch should return default
        wrong_scope = state_manager.get(
            "scoped_state",
            default="scope_default",
            scope=StateScope.USER
        )
        assert wrong_scope == "scope_default"
        
        # Test state consistency after operations
        consistency_key = "consistency_test"
        original_value = {"counter": 0, "operations": []}
        
        state_manager.set(consistency_key, original_value)
        
        # Perform multiple operations
        for i in range(5):
            def update_operation(current_state):
                current_state["counter"] += 1
                current_state["operations"].append(f"op_{i}")
                return current_state
            
            state_manager.update(consistency_key, update_operation)
        
        # Verify final state consistency
        final_state = state_manager.get(consistency_key)
        assert final_state["counter"] == 5
        assert len(final_state["operations"]) == 5
        assert final_state["operations"] == [f"op_{i}" for i in range(5)]
    
    @pytest.mark.integration
    async def test_agent_state_migration_between_sessions(self, state_manager):
        """Test agent state migration between sessions."""
        # Create initial session state
        old_session_id = "old_session_123"
        new_session_id = "new_session_456"
        user_id = "migrating_user_789"
        
        # Store state in old session
        old_session_data = {
            "conversation_context": ["message1", "message2", "message3"],
            "user_preferences": {"theme": "dark", "language": "en"},
            "agent_state": {"phase": "processing", "step": 3}
        }
        
        for key, value in old_session_data.items():
            state_manager.set_session_state(old_session_id, key, value)
        
        # Simulate session migration
        migration_map = {}
        
        # Query old session state
        old_session_query = StateQuery(
            scope=StateScope.SESSION,
            session_id=old_session_id
        )
        
        old_entries = state_manager.query_states(old_session_query)
        
        # Migrate state to new session
        for entry in old_entries:
            # Extract key from full session key
            session_key_prefix = f"session:{old_session_id}:"
            if entry.key.startswith(session_key_prefix):
                base_key = entry.key[len(session_key_prefix):]
                
                # Set in new session
                state_manager.set_session_state(
                    new_session_id,
                    base_key, 
                    entry.value,
                    ttl_seconds=entry.ttl_seconds
                )
                
                migration_map[entry.key] = f"session:{new_session_id}:{base_key}"
        
        # Verify migration
        for old_key, new_key in migration_map.items():
            old_value = state_manager.get(old_key)
            new_value = state_manager.get(new_key)
            assert old_value == new_value
        
        # Verify new session has all migrated data
        new_conversation = state_manager.get_session_state(
            new_session_id, 
            "conversation_context"
        )
        assert new_conversation == ["message1", "message2", "message3"]
        
        new_preferences = state_manager.get_session_state(
            new_session_id,
            "user_preferences"
        )
        assert new_preferences["theme"] == "dark"
        assert new_preferences["language"] == "en"
        
        new_agent_state = state_manager.get_session_state(
            new_session_id,
            "agent_state"
        )
        assert new_agent_state["phase"] == "processing"
        assert new_agent_state["step"] == 3
        
        # Clean up old session state
        cleared_count = state_manager.clear_session_states(old_session_id)
        assert cleared_count == len(old_session_data)
        
        # Verify old session state is cleared
        for key in old_session_data.keys():
            old_value = state_manager.get_session_state(old_session_id, key)
            assert old_value is None
    
    @pytest.mark.integration
    async def test_factory_pattern_user_isolation(self):
        """Test StateManagerFactory for user isolation."""
        # Get global manager
        global_manager = StateManagerFactory.get_global_manager()
        assert global_manager is not None
        assert global_manager.user_id is None
        
        # Get user-specific managers
        user1_manager = StateManagerFactory.get_user_manager("user1")
        user2_manager = StateManagerFactory.get_user_manager("user2")
        
        assert user1_manager is not None
        assert user2_manager is not None
        assert user1_manager != user2_manager
        assert user1_manager.user_id == "user1"
        assert user2_manager.user_id == "user2"
        
        # Verify same user gets same manager instance
        user1_manager_again = StateManagerFactory.get_user_manager("user1")
        assert user1_manager_again is user1_manager
        
        # Test state isolation between user managers
        user1_manager.set("test_key", "user1_value")
        user2_manager.set("test_key", "user2_value")
        
        assert user1_manager.get("test_key") == "user1_value"
        assert user2_manager.get("test_key") == "user2_value"
        assert global_manager.get("test_key") is None
        
        # Test manager count
        count = StateManagerFactory.get_manager_count()
        assert count["global"] == 1
        assert count["user_specific"] >= 2
        assert count["total"] >= 3
    
    @pytest.mark.integration
    async def test_comprehensive_state_query_filtering(self, state_manager):
        """Test comprehensive state querying and filtering."""
        # Create diverse state entries for testing
        test_entries = [
            ("user:user1:pref", "pref1", StateScope.USER, StateType.USER_PREFERENCES, "user1", None, None, None),
            ("user:user2:pref", "pref2", StateScope.USER, StateType.USER_PREFERENCES, "user2", None, None, None),
            ("session:sess1:data", "data1", StateScope.SESSION, StateType.SESSION_DATA, "user1", "sess1", None, None),
            ("session:sess2:data", "data2", StateScope.SESSION, StateType.SESSION_DATA, "user2", "sess2", None, None),
            ("thread:thread1:ctx", "ctx1", StateScope.THREAD, StateType.THREAD_CONTEXT, "user1", None, "thread1", None),
            ("thread:thread2:ctx", "ctx2", StateScope.THREAD, StateType.THREAD_CONTEXT, "user2", None, "thread2", None),
            ("agent:agent1:exec", "exec1", StateScope.AGENT, StateType.AGENT_EXECUTION, "user1", None, None, "agent1"),
            ("agent:agent2:exec", "exec2", StateScope.AGENT, StateType.AGENT_EXECUTION, "user2", None, None, "agent2"),
        ]
        
        # Insert test entries
        for key, value, scope, state_type, user_id, session_id, thread_id, agent_id in test_entries:
            state_manager.set(
                key=key,
                value=value,
                scope=scope,
                state_type=state_type,
                user_id=user_id,
                session_id=session_id,
                thread_id=thread_id,
                agent_id=agent_id
            )
        
        # Test scope filtering
        user_query = StateQuery(scope=StateScope.USER)
        user_results = state_manager.query_states(user_query)
        assert len(user_results) == 2
        assert all(entry.scope == StateScope.USER for entry in user_results)
        
        session_query = StateQuery(scope=StateScope.SESSION)
        session_results = state_manager.query_states(session_query)
        assert len(session_results) == 2
        assert all(entry.scope == StateScope.SESSION for entry in session_results)
        
        # Test user filtering
        user1_query = StateQuery(user_id="user1")
        user1_results = state_manager.query_states(user1_query)
        assert len(user1_results) == 4  # user1 has entries in all scopes
        assert all(entry.user_id == "user1" for entry in user1_results)
        
        user2_query = StateQuery(user_id="user2")
        user2_results = state_manager.query_states(user2_query)
        assert len(user2_results) == 4  # user2 has entries in all scopes
        assert all(entry.user_id == "user2" for entry in user2_results)
        
        # Test type filtering
        prefs_query = StateQuery(state_type=StateType.USER_PREFERENCES)
        prefs_results = state_manager.query_states(prefs_query)
        assert len(prefs_results) == 2
        assert all(entry.state_type == StateType.USER_PREFERENCES for entry in prefs_results)
        
        # Test combined filtering
        user1_session_query = StateQuery(user_id="user1", scope=StateScope.SESSION)
        user1_session_results = state_manager.query_states(user1_session_query)
        assert len(user1_session_results) == 1
        assert user1_session_results[0].user_id == "user1"
        assert user1_session_results[0].scope == StateScope.SESSION
        
        # Test key pattern filtering
        pattern_query = StateQuery(key_pattern="user:.*:pref")
        pattern_results = state_manager.query_states(pattern_query)
        assert len(pattern_results) == 2
        assert all("pref" in entry.key for entry in pattern_results)
        
        # Test limit filtering
        limited_query = StateQuery(limit=3)
        limited_results = state_manager.query_states(limited_query)
        assert len(limited_results) <= 3
        
        # Test time-based filtering
        current_time = time.time()
        recent_query = StateQuery(created_after=current_time - 10)  # Last 10 seconds
        recent_results = state_manager.query_states(recent_query)
        assert len(recent_results) == len(test_entries)  # All should be recent
        
        old_query = StateQuery(created_before=current_time - 10)  # Before 10 seconds ago
        old_results = state_manager.query_states(old_query)
        assert len(old_results) == 0  # None should be that old