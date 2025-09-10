"""Test WorkflowOrchestrator User Isolation - P0 Failing Integration Tests.

This test module validates that WorkflowOrchestrator properly isolates user contexts
in concurrent scenarios when using SSOT UserExecutionEngine vs deprecated engines.

EXPECTED BEHAVIOR (BEFORE REMEDIATION):
- These tests should FAIL because deprecated engines don't properly isolate users
- After remediation: Tests should PASS when SSOT UserExecutionEngine enforces isolation

TEST PURPOSE: Prove user isolation violations exist and validate fix effectiveness.

Business Value: Prevents critical user data leakage in multi-user production environment.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWorkflowOrchestratorUserIsolation(SSotAsyncTestCase):
    """Integration tests for WorkflowOrchestrator user isolation with SSOT compliance.
    
    These tests should FAIL initially, proving user isolation violations exist.
    After remediation, they should PASS to validate proper isolation.
    """

    def setUp(self):
        """Set up test fixtures for user isolation testing."""
        super().setUp()
        
        # Create multiple user contexts for isolation testing
        self.user1_context = UserExecutionContext(
            user_id="user_1_alice",
            thread_id="thread_1_alice",
            run_id="run_1_alice"
        )
        
        self.user2_context = UserExecutionContext(
            user_id="user_2_bob", 
            thread_id="thread_2_bob",
            run_id="run_2_bob"
        )
        
        # Mock shared resources that should NOT be shared between users
        self.mock_agent_registry = Mock()
        self.mock_websocket_manager = Mock()
        
        # Track which user data gets processed (should be isolated)
        self.user_data_processed = {}
        
    async def _create_orchestrator_with_ssot_engine(self, user_context: UserExecutionContext) -> WorkflowOrchestrator:
        """Create WorkflowOrchestrator with SSOT UserExecutionEngine for testing."""
        # Create properly isolated UserExecutionEngine
        user_engine = Mock(spec=UserExecutionEngine)
        user_engine.__class__.__name__ = "UserExecutionEngine"
        user_engine.user_context = user_context
        
        # Mock execute_agent to track user-specific execution
        async def mock_execute_agent(context: ExecutionContext, state: DeepAgentState):
            # Record which user's data was processed
            user_id = context.user_id or "unknown"
            if user_id not in self.user_data_processed:
                self.user_data_processed[user_id] = []
            self.user_data_processed[user_id].append({
                'context_user_id': context.user_id,
                'context_thread_id': context.thread_id,
                'context_run_id': context.run_id,
                'agent_name': context.agent_name,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            return ExecutionResult(
                success=True,
                result=f"Result for {user_id}",
                agent_name=context.agent_name,
                execution_time_ms=100
            )
            
        user_engine.execute_agent.side_effect = mock_execute_agent
        
        return WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=user_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=user_context
        )
        
    async def _create_orchestrator_with_deprecated_engine(self, user_context: UserExecutionContext) -> WorkflowOrchestrator:
        """Create WorkflowOrchestrator with deprecated engine (for comparison)."""
        # Create deprecated engine that violates user isolation
        deprecated_engine = Mock()
        deprecated_engine.__class__.__name__ = "ExecutionEngine"  # Deprecated
        
        # This engine shares state between users (violation)
        shared_state = {}
        
        async def mock_execute_agent_shared(context: ExecutionContext, state: DeepAgentState):
            # BUG: Uses shared state instead of user-isolated state
            user_id = context.user_id or "unknown"
            shared_state[user_id] = f"Shared data for {user_id}"
            
            # Record execution (this will show cross-user contamination)
            if user_id not in self.user_data_processed:
                self.user_data_processed[user_id] = []
            self.user_data_processed[user_id].append({
                'context_user_id': context.user_id,
                'shared_state_keys': list(shared_state.keys()),  # Shows contamination
                'agent_name': context.agent_name,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            return ExecutionResult(
                success=True,
                result=f"Result with shared state: {shared_state}",
                agent_name=context.agent_name,
                execution_time_ms=100
            )
            
        deprecated_engine.execute_agent.side_effect = mock_execute_agent_shared
        
        return WorkflowOrchestrator(
            agent_registry=self.mock_agent_registry,
            execution_engine=deprecated_engine,
            websocket_manager=self.mock_websocket_manager,
            user_context=user_context
        )
        
    async def test_concurrent_user_execution_with_ssot_engine_isolation(self):
        """Test that SSOT UserExecutionEngine properly isolates concurrent users.
        
        EXPECTED: This test should FAIL before remediation (isolation not enforced).
        AFTER REMEDIATION: Should PASS when SSOT engines properly isolate users.
        """
        # Create orchestrators for both users with SSOT engines
        orchestrator1 = await self._create_orchestrator_with_ssot_engine(self.user1_context)
        orchestrator2 = await self._create_orchestrator_with_ssot_engine(self.user2_context)
        
        # Create execution contexts for both users
        context1 = ExecutionContext(
            run_id=self.user1_context.run_id,
            agent_name="triage",
            state=Mock(spec=DeepAgentState),
            stream_updates=True,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id
        )
        
        context2 = ExecutionContext(
            run_id=self.user2_context.run_id,
            agent_name="triage", 
            state=Mock(spec=DeepAgentState),
            stream_updates=True,
            thread_id=self.user2_context.thread_id,
            user_id=self.user2_context.user_id
        )
        
        # Execute both workflows concurrently
        results = await asyncio.gather(
            orchestrator1.execute_standard_workflow(context1),
            orchestrator2.execute_standard_workflow(context2),
            return_exceptions=True
        )
        
        # Validate user isolation
        assert len(self.user_data_processed) == 2, "Should process data for exactly 2 users"
        assert "user_1_alice" in self.user_data_processed, "User 1 data not processed"
        assert "user_2_bob" in self.user_data_processed, "User 2 data not processed"
        
        # CRITICAL: User contexts should not be contaminated
        user1_data = self.user_data_processed["user_1_alice"]
        user2_data = self.user_data_processed["user_2_bob"]
        
        for entry in user1_data:
            assert entry['context_user_id'] == "user_1_alice", "User 1 context contaminated"
            assert entry['context_thread_id'] == "thread_1_alice", "User 1 thread contaminated"
            
        for entry in user2_data:
            assert entry['context_user_id'] == "user_2_bob", "User 2 context contaminated"
            assert entry['context_thread_id'] == "thread_2_bob", "User 2 thread contaminated"
            
    async def test_concurrent_user_websocket_event_isolation(self):
        """Test that WebSocket events are properly isolated between concurrent users.
        
        EXPECTED: This test should FAIL before remediation (WebSocket cross-contamination).
        AFTER REMEDIATION: Should PASS when SSOT patterns isolate WebSocket events.
        """
        # Track WebSocket events per user
        user1_events = []
        user2_events = []
        
        # Mock WebSocket managers with event tracking
        def create_mock_emitter(user_id: str, events_list: List):
            mock_emitter = AsyncMock()
            
            async def track_emit(event_type: str, data: Dict):
                events_list.append({
                    'event_type': event_type,
                    'user_id': user_id,
                    'data': data,
                    'timestamp': asyncio.get_event_loop().time()
                })
                
            mock_emitter.emit_agent_started.side_effect = lambda agent, data: track_emit('agent_started', {'agent': agent, **data})
            mock_emitter.emit_agent_completed.side_effect = lambda agent, data: track_emit('agent_completed', {'agent': agent, **data})
            
            return mock_emitter
            
        # Create orchestrators with user-specific WebSocket tracking
        orchestrator1 = await self._create_orchestrator_with_ssot_engine(self.user1_context)
        orchestrator2 = await self._create_orchestrator_with_ssot_engine(self.user2_context)
        
        # Mock _get_user_emitter_from_context to return user-specific emitters
        orchestrator1._get_user_emitter_from_context = AsyncMock(
            return_value=create_mock_emitter("user_1_alice", user1_events)
        )
        orchestrator2._get_user_emitter_from_context = AsyncMock(
            return_value=create_mock_emitter("user_2_bob", user2_events)
        )
        
        # Execute workflows concurrently
        context1 = ExecutionContext(
            run_id=self.user1_context.run_id,
            agent_name="triage",
            state=Mock(spec=DeepAgentState),
            stream_updates=True,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id
        )
        
        context2 = ExecutionContext(
            run_id=self.user2_context.run_id,
            agent_name="triage",
            state=Mock(spec=DeepAgentState), 
            stream_updates=True,
            thread_id=self.user2_context.thread_id,
            user_id=self.user2_context.user_id
        )
        
        await asyncio.gather(
            orchestrator1.execute_standard_workflow(context1),
            orchestrator2.execute_standard_workflow(context2)
        )
        
        # Validate WebSocket event isolation
        assert len(user1_events) > 0, "User 1 should receive WebSocket events"
        assert len(user2_events) > 0, "User 2 should receive WebSocket events"
        
        # CRITICAL: Events should not cross-contaminate between users
        for event in user1_events:
            assert event['user_id'] == "user_1_alice", f"User 1 received event for wrong user: {event}"
            
        for event in user2_events:
            assert event['user_id'] == "user_2_bob", f"User 2 received event for wrong user: {event}"
            
        # Events should be temporally isolated (no race conditions)
        user1_times = [e['timestamp'] for e in user1_events]
        user2_times = [e['timestamp'] for e in user2_events]
        
        assert max(user1_times) - min(user1_times) < 5.0, "User 1 events took too long (possible race condition)"
        assert max(user2_times) - min(user2_times) < 5.0, "User 2 events took too long (possible race condition)"
        
    async def test_memory_isolation_between_concurrent_users(self):
        """Test that memory state is isolated between concurrent users.
        
        EXPECTED: This test should FAIL before remediation (memory sharing).
        AFTER REMEDIATION: Should PASS when SSOT patterns enforce memory isolation.
        """
        # Create orchestrators
        orchestrator1 = await self._create_orchestrator_with_ssot_engine(self.user1_context)
        orchestrator2 = await self._create_orchestrator_with_ssot_engine(self.user2_context)
        
        # Simulate memory-intensive operations
        user1_state = Mock(spec=DeepAgentState)
        user1_state.conversation_history = [f"User 1 message {i}" for i in range(100)]
        user1_state.agent_memory = {"user1_data": "sensitive_user1_info"}
        
        user2_state = Mock(spec=DeepAgentState) 
        user2_state.conversation_history = [f"User 2 message {i}" for i in range(100)]
        user2_state.agent_memory = {"user2_data": "sensitive_user2_info"}
        
        context1 = ExecutionContext(
            run_id=self.user1_context.run_id,
            agent_name="data",
            state=user1_state,
            stream_updates=False,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id
        )
        
        context2 = ExecutionContext(
            run_id=self.user2_context.run_id,
            agent_name="data",
            state=user2_state,
            stream_updates=False,
            thread_id=self.user2_context.thread_id,
            user_id=self.user2_context.user_id
        )
        
        # Execute with high concurrency stress test
        async def stress_execute(orchestrator, context, iterations=10):
            results = []
            for i in range(iterations):
                result = await orchestrator.execute_standard_workflow(context)
                results.append(result)
                # Small delay to allow memory pressure
                await asyncio.sleep(0.01)
            return results
            
        # Run stress test concurrently
        user1_results, user2_results = await asyncio.gather(
            stress_execute(orchestrator1, context1),
            stress_execute(orchestrator2, context2)
        )
        
        # Validate memory isolation
        assert len(user1_results) == 10, "User 1 should complete all iterations"
        assert len(user2_results) == 10, "User 2 should complete all iterations"
        
        # CRITICAL: Memory should not be shared between users
        # Check that user data was properly processed and isolated
        user1_processed = self.user_data_processed.get("user_1_alice", [])
        user2_processed = self.user_data_processed.get("user_2_bob", [])
        
        assert len(user1_processed) >= 10, "User 1 processing incomplete"
        assert len(user2_processed) >= 10, "User 2 processing incomplete"
        
        # Validate that no user data crossed over
        for entry in user1_processed:
            assert entry['context_user_id'] == "user_1_alice", "User 1 memory contaminated"
            
        for entry in user2_processed:
            assert entry['context_user_id'] == "user_2_bob", "User 2 memory contaminated"
            
    async def test_deprecated_engine_fails_user_isolation_comparison(self):
        """Test that deprecated engines fail user isolation (proving SSOT necessity).
        
        EXPECTED: This test should FAIL before remediation (deprecated engines used).
        AFTER REMEDIATION: Should PASS when deprecated engines are rejected.
        """
        # This test should demonstrate why SSOT UserExecutionEngine is necessary
        
        # FIRST: Try to create with deprecated engine (should be rejected after remediation)
        try:
            # This should fail after remediation
            deprecated_orchestrator = await self._create_orchestrator_with_deprecated_engine(self.user1_context)
            
            # If we get here, SSOT validation is not working
            context = ExecutionContext(
                run_id=self.user1_context.run_id,
                agent_name="triage",
                state=Mock(spec=DeepAgentState),
                stream_updates=False,
                thread_id=self.user1_context.thread_id,
                user_id=self.user1_context.user_id
            )
            
            await deprecated_orchestrator.execute_standard_workflow(context)
            
            # If execution succeeds, deprecated engine was allowed (SSOT violation)
            pytest.fail("Deprecated engine was allowed to execute (SSOT violation)")
            
        except ValueError as e:
            # This is the expected behavior after remediation
            assert "deprecated" in str(e).lower(), "Should reject deprecated engines"
            assert "UserExecutionEngine" in str(e), "Should recommend UserExecutionEngine"
            
    async def test_ssot_engine_runtime_validation_prevents_contamination(self):
        """Test that SSOT engines perform runtime validation to prevent contamination.
        
        EXPECTED: This test should FAIL before remediation (no runtime validation).
        AFTER REMEDIATION: Should PASS when runtime validation is added.
        """
        orchestrator = await self._create_orchestrator_with_ssot_engine(self.user1_context)
        
        # Create context for user 1
        context = ExecutionContext(
            run_id=self.user1_context.run_id,
            agent_name="triage",
            state=Mock(spec=DeepAgentState),
            stream_updates=True,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id
        )
        
        # Simulate runtime context contamination attempt
        contaminated_context = ExecutionContext(
            run_id="different_run_id",  # Wrong run_id
            agent_name="triage",
            state=Mock(spec=DeepAgentState),
            stream_updates=True,
            thread_id="different_thread_id",  # Wrong thread_id
            user_id="different_user_id"  # Wrong user_id
        )
        
        # SSOT engine should detect and reject context mismatch at runtime
        with pytest.raises(ValueError, match="Runtime validation failed.*context mismatch"):
            await orchestrator.execute_standard_workflow(contaminated_context)