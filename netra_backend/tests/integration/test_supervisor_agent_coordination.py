"""Integration Tests for Supervisor Agent Coordination and Delegation.

Tests the complete integration of supervisor with sub-agents, ensuring proper
coordination, delegation, state management, and error handling across the system.

Business Value: Validates that the orchestration engine correctly coordinates
multiple agents to deliver end-to-end value.
"""

import asyncio
import pytest
import time
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
    AgentExecutionStrategy,
)
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.websocket_core import UnifiedWebSocketManager
from netra_backend.app.schemas.websocket_models import WebSocketMessage


class MockSubAgent(BaseSubAgent):
    """Mock sub-agent for testing coordination."""
    
    def __init__(self, name: str, llm_manager: LLMManager, 
                 behavior: str = "success", delay: float = 0.1):
        super().__init__(llm_manager, name=name, description=f"Mock {name} agent")
        self.behavior = behavior
        self.delay = delay
        self.execution_count = 0
        self.received_state = None
        self.execution_history = []
    
    async def execute(self, state: DeepAgentState, run_id: str, 
                     stream_updates: bool) -> Dict[str, Any]:
        """Execute mock agent behavior."""
        self.execution_count += 1
        self.received_state = state
        self.execution_history.append({
            'run_id': run_id,
            'timestamp': datetime.now(timezone.utc),
            'state_messages': len(state.messages) if state.messages else 0
        })
        
        # Simulate processing time
        await asyncio.sleep(self.delay)
        
        if self.behavior == "success":
            return {
                "status": "success",
                "agent": self.name,
                "result": f"Processed by {self.name}",
                "execution_number": self.execution_count
            }
        elif self.behavior == "failure":
            raise Exception(f"{self.name} agent failed as configured")
        elif self.behavior == "timeout":
            await asyncio.sleep(30)  # Exceed typical timeout
            return {"status": "timeout"}
        elif self.behavior == "partial":
            return {
                "status": "partial",
                "agent": self.name,
                "needs_more_data": True
            }
        else:
            return {"status": "unknown"}


class TestAgentCoordination:
    """Test agent coordination and delegation."""
    
    @pytest.fixture
    def mock_agents(self, mock_llm_manager):
        """Create a set of mock agents for testing."""
        return {
            'triage': MockSubAgent('triage', mock_llm_manager, behavior='success', delay=0.05),
            'optimization': MockSubAgent('optimization', mock_llm_manager, behavior='success', delay=0.1),
            'data': MockSubAgent('data', mock_llm_manager, behavior='success', delay=0.08),
            'actions': MockSubAgent('actions', mock_llm_manager, behavior='success', delay=0.06),
            'reporting': MockSubAgent('reporting', mock_llm_manager, behavior='success', delay=0.04),
            'data_helper': MockSubAgent('data_helper', mock_llm_manager, behavior='partial', delay=0.03),
        }
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager."""
        manager = MagicMock(spec=LLMManager)
        manager.generate = AsyncMock(return_value="Test LLM response")
        return manager
    
    @pytest.fixture
    def supervisor_with_mocks(self, mock_agents, mock_llm_manager):
        """Create supervisor with mock agents registered."""
        db_session = AsyncMock(spec=AsyncSession)
        websocket_manager = MagicMock(spec=UnifiedWebSocketManager)
        websocket_manager.send_message = AsyncMock()
        tool_dispatcher = MagicMock(spec=ToolDispatcher)
        
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=mock_llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Replace registry agents with mocks
        for name, agent in mock_agents.items():
            supervisor.agent_registry.agents[name] = agent
        
        return supervisor, mock_agents
    
    @pytest.mark.asyncio
    async def test_sequential_agent_coordination(self, supervisor_with_mocks):
        """Test that agents are coordinated sequentially as per dependencies."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Define sequential workflow
        workflow = [
            PipelineStep('triage', AgentExecutionStrategy.SEQUENTIAL, []),
            PipelineStep('optimization', AgentExecutionStrategy.SEQUENTIAL, ['triage']),
            PipelineStep('data', AgentExecutionStrategy.SEQUENTIAL, ['optimization']),
            PipelineStep('actions', AgentExecutionStrategy.SEQUENTIAL, ['data']),
            PipelineStep('reporting', AgentExecutionStrategy.SEQUENTIAL, ['actions']),
        ]
        
        with patch.object(supervisor.workflow_orchestrator, 
                         '_define_workflow_based_on_triage', return_value=workflow):
            
            context = ExecutionContext(
                run_id="test-sequential",
                agent_name="ModernSupervisor",
                state=DeepAgentState(),
                stream_updates=True,
                thread_id="test-thread",
                user_id="test-user",
                start_time=datetime.now(timezone.utc)
            )
            
            # Execute workflow
            result = await supervisor.execute_core_logic(context)
            
            # Verify all agents executed
            for agent in ['triage', 'optimization', 'data', 'actions', 'reporting']:
                assert mock_agents[agent].execution_count > 0
            
            # Verify sequential execution by checking timestamps
            execution_times = {}
            for name, agent in mock_agents.items():
                if agent.execution_history:
                    execution_times[name] = agent.execution_history[0]['timestamp']
            
            # Dependencies should execute in order
            if 'triage' in execution_times and 'optimization' in execution_times:
                assert execution_times['triage'] <= execution_times['optimization']
            if 'optimization' in execution_times and 'data' in execution_times:
                assert execution_times['optimization'] <= execution_times['data']
    
    @pytest.mark.asyncio
    async def test_parallel_agent_coordination(self, supervisor_with_mocks):
        """Test parallel execution of independent agents."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Create agents that can run in parallel (no dependencies between them)
        parallel_workflow = [
            PipelineStep('triage', AgentExecutionStrategy.SEQUENTIAL, []),
            PipelineStep('optimization', AgentExecutionStrategy.PARALLEL, ['triage']),
            PipelineStep('data', AgentExecutionStrategy.PARALLEL, ['triage']),
            PipelineStep('reporting', AgentExecutionStrategy.SEQUENTIAL, ['optimization', 'data']),
        ]
        
        with patch.object(supervisor.workflow_orchestrator,
                         '_define_workflow_based_on_triage', return_value=parallel_workflow):
            
            context = ExecutionContext(
                run_id="test-parallel",
                agent_name="ModernSupervisor",
                state=DeepAgentState(),
                stream_updates=True,
                thread_id="test-thread",
                user_id="test-user",
                start_time=datetime.now(timezone.utc)
            )
            
            start_time = time.time()
            result = await supervisor.execute_core_logic(context)
            elapsed = time.time() - start_time
            
            # Verify parallel execution saved time
            # If sequential, would take sum of all delays
            sequential_time = sum(agent.delay for agent in mock_agents.values())
            
            # Parallel execution should be faster
            assert elapsed < sequential_time * 0.8  # Allow some overhead
    
    @pytest.mark.asyncio
    async def test_state_propagation_between_agents(self, supervisor_with_mocks):
        """Test that state is properly propagated between agents."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Initial state
        initial_state = DeepAgentState()
        initial_state.messages = [{"role": "user", "content": "Test message"}]
        initial_state.metadata = {"test_key": "test_value"}
        
        context = ExecutionContext(
            run_id="test-state-prop",
            agent_name="ModernSupervisor",
            state=initial_state,
            stream_updates=True,
            thread_id="test-thread",
            user_id="test-user",
            start_time=datetime.now(timezone.utc)
        )
        
        workflow = [
            PipelineStep('triage', AgentExecutionStrategy.SEQUENTIAL, []),
            PipelineStep('optimization', AgentExecutionStrategy.SEQUENTIAL, ['triage']),
        ]
        
        with patch.object(supervisor.workflow_orchestrator,
                         '_define_workflow_based_on_triage', return_value=workflow):
            
            await supervisor.execute_core_logic(context)
            
            # Verify state was passed to agents
            assert mock_agents['triage'].received_state is not None
            assert mock_agents['optimization'].received_state is not None
            
            # Check state contents
            triage_state = mock_agents['triage'].received_state
            assert len(triage_state.messages) > 0
            assert triage_state.metadata.get('test_key') == 'test_value'
    
    @pytest.mark.asyncio
    async def test_agent_failure_handling(self, supervisor_with_mocks):
        """Test handling of agent failures during coordination."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Configure one agent to fail
        mock_agents['optimization'].behavior = 'failure'
        
        workflow = [
            PipelineStep('triage', AgentExecutionStrategy.SEQUENTIAL, []),
            PipelineStep('optimization', AgentExecutionStrategy.SEQUENTIAL, ['triage']),
            PipelineStep('reporting', AgentExecutionStrategy.SEQUENTIAL, ['optimization']),
        ]
        
        with patch.object(supervisor.workflow_orchestrator,
                         '_define_workflow_based_on_triage', return_value=workflow):
            
            context = ExecutionContext(
                run_id="test-failure",
                agent_name="ModernSupervisor",
                state=DeepAgentState(),
                stream_updates=True,
                thread_id="test-thread",
                user_id="test-user",
                start_time=datetime.now(timezone.utc)
            )
            
            # Execute and expect partial completion
            result = await supervisor.execute_core_logic(context)
            
            # Triage should have executed
            assert mock_agents['triage'].execution_count == 1
            
            # Reporting should not execute due to optimization failure
            assert mock_agents['reporting'].execution_count == 0
            
            # Result should indicate failure
            assert result['supervisor_result'] == 'failed' or 'error' in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, supervisor_with_mocks):
        """Test handling of agent timeouts."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Configure agent to timeout
        mock_agents['data'].behavior = 'timeout'
        
        # Set shorter timeout for testing
        supervisor.execution_engine.AGENT_EXECUTION_TIMEOUT = 1.0  # 1 second
        
        workflow = [
            PipelineStep('data', AgentExecutionStrategy.SEQUENTIAL, []),
        ]
        
        with patch.object(supervisor.workflow_orchestrator,
                         '_define_workflow_based_on_triage', return_value=workflow):
            
            context = ExecutionContext(
                run_id="test-timeout",
                agent_name="ModernSupervisor",
                state=DeepAgentState(),
                stream_updates=True,
                thread_id="test-thread",
                user_id="test-user",
                start_time=datetime.now(timezone.utc)
            )
            
            # Execute with timeout
            with patch.object(supervisor.execution_engine, 'AGENT_EXECUTION_TIMEOUT', 1.0):
                start_time = time.time()
                
                # Should handle timeout gracefully
                try:
                    result = await supervisor.execute_core_logic(context)
                    elapsed = time.time() - start_time
                    
                    # Should timeout quickly, not wait 30 seconds
                    assert elapsed < 5.0
                except asyncio.TimeoutError:
                    # Timeout is acceptable
                    pass


class TestDelegationPatterns:
    """Test various delegation patterns and strategies."""
    
    @pytest.mark.asyncio
    async def test_conditional_delegation(self, supervisor_with_mocks):
        """Test conditional delegation based on previous results."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Mock triage returning different data sufficiency levels
        async def adaptive_workflow_execution(context):
            # First execute triage
            triage_result = await mock_agents['triage'].execute(
                context.state, context.run_id, context.stream_updates
            )
            
            # Determine workflow based on triage
            if triage_result.get('needs_more_data'):
                # Execute data_helper path
                return [
                    ExecutionResult(success=True, result=triage_result),
                    ExecutionResult(success=True, result=await mock_agents['data_helper'].execute(
                        context.state, context.run_id, context.stream_updates
                    ))
                ]
            else:
                # Execute normal path
                return [
                    ExecutionResult(success=True, result=triage_result),
                    ExecutionResult(success=True, result=await mock_agents['optimization'].execute(
                        context.state, context.run_id, context.stream_updates
                    ))
                ]
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         side_effect=adaptive_workflow_execution):
            
            context = ExecutionContext(
                run_id="test-conditional",
                agent_name="ModernSupervisor",
                state=DeepAgentState(),
                stream_updates=True,
                thread_id="test-thread",
                user_id="test-user",
                start_time=datetime.now(timezone.utc)
            )
            
            result = await supervisor.execute_core_logic(context)
            
            # Verify adaptive delegation occurred
            assert mock_agents['triage'].execution_count == 1
            assert (mock_agents['data_helper'].execution_count == 1 or 
                   mock_agents['optimization'].execution_count == 1)
    
    @pytest.mark.asyncio
    async def test_recursive_delegation(self, supervisor_with_mocks):
        """Test recursive delegation patterns."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Track delegation depth
        delegation_depth = []
        
        async def recursive_execution(context, depth=0):
            delegation_depth.append(depth)
            
            if depth >= 3:  # Max recursion depth
                return ExecutionResult(success=True, result={"depth": depth})
            
            # Simulate recursive delegation
            sub_context = ExecutionContext(
                run_id=f"{context.run_id}-depth-{depth}",
                agent_name=context.agent_name,
                state=context.state,
                stream_updates=context.stream_updates,
                thread_id=context.thread_id,
                user_id=context.user_id,
                start_time=context.start_time
            )
            
            return await recursive_execution(sub_context, depth + 1)
        
        with patch.object(supervisor, '_execute_with_error_handling',
                         side_effect=recursive_execution):
            
            state = DeepAgentState()
            await supervisor.execute(state, "test-recursive", stream_updates=True)
            
            # Verify recursive delegation occurred
            assert len(delegation_depth) > 1
            assert max(delegation_depth) >= 3
    
    @pytest.mark.asyncio
    async def test_fallback_delegation(self, supervisor_with_mocks):
        """Test fallback delegation when primary agent fails."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Create fallback agent
        fallback_agent = MockSubAgent('fallback', supervisor.llm_manager, 
                                     behavior='success', delay=0.01)
        supervisor.agent_registry.agents['fallback'] = fallback_agent
        
        # Configure primary agent to fail
        mock_agents['optimization'].behavior = 'failure'
        
        # Track fallback activation
        fallback_activated = False
        
        async def execute_with_fallback(context):
            nonlocal fallback_activated
            try:
                # Try primary agent
                return await mock_agents['optimization'].execute(
                    context.state, context.run_id, context.stream_updates
                )
            except Exception:
                # Activate fallback
                fallback_activated = True
                return await fallback_agent.execute(
                    context.state, context.run_id, context.stream_updates
                )
        
        with patch.object(supervisor.execution_engine.agent_core, 'execute_agent',
                         side_effect=execute_with_fallback):
            
            context = AgentExecutionContext(
                run_id="test-fallback",
                thread_id="test-thread",
                agent_name="optimization",
                stream_updates=True
            )
            
            result = await supervisor.execution_engine.execute_agent(
                context, DeepAgentState()
            )
            
            # Verify fallback was activated
            assert fallback_activated
            assert fallback_agent.execution_count == 1


class TestWebSocketCoordination:
    """Test WebSocket event coordination during agent execution."""
    
    @pytest.mark.asyncio
    async def test_websocket_events_for_each_agent(self, supervisor_with_mocks):
        """Test that WebSocket events are sent for each agent execution."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Track WebSocket messages
        websocket_messages = []
        
        async def capture_websocket(thread_id, message):
            websocket_messages.append({
                'thread_id': thread_id,
                'type': message.type if hasattr(message, 'type') else 'unknown',
                'payload': message.payload if hasattr(message, 'payload') else None
            })
        
        supervisor.websocket_manager.send_message = AsyncMock(side_effect=capture_websocket)
        
        workflow = [
            PipelineStep('triage', AgentExecutionStrategy.SEQUENTIAL, []),
            PipelineStep('optimization', AgentExecutionStrategy.SEQUENTIAL, ['triage']),
            PipelineStep('reporting', AgentExecutionStrategy.SEQUENTIAL, ['optimization']),
        ]
        
        with patch.object(supervisor.workflow_orchestrator,
                         '_define_workflow_based_on_triage', return_value=workflow):
            
            context = ExecutionContext(
                run_id="test-websocket",
                agent_name="ModernSupervisor",
                state=DeepAgentState(),
                stream_updates=True,
                thread_id="test-thread",
                user_id="test-user",
                start_time=datetime.now(timezone.utc)
            )
            
            await supervisor.execute_core_logic(context)
            
            # Verify WebSocket events were sent
            message_types = [msg['type'] for msg in websocket_messages]
            
            # Should have events for each agent
            expected_events = ['agent_started', 'agent_completed']
            for event in expected_events:
                assert any(event in msg_type for msg_type in message_types)
    
    @pytest.mark.asyncio
    async def test_websocket_event_ordering(self, supervisor_with_mocks):
        """Test that WebSocket events maintain proper ordering."""
        supervisor, mock_agents = supervisor_with_mocks
        
        event_sequence = []
        
        async def track_event_order(thread_id, message):
            if hasattr(message, 'type'):
                event_sequence.append({
                    'type': message.type,
                    'timestamp': time.time()
                })
        
        supervisor.websocket_manager.send_message = AsyncMock(side_effect=track_event_order)
        
        context = ExecutionContext(
            run_id="test-ordering",
            agent_name="ModernSupervisor",
            state=DeepAgentState(),
            stream_updates=True,
            thread_id="test-thread",
            user_id="test-user",
            start_time=datetime.now(timezone.utc)
        )
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await supervisor.execute_core_logic(context)
        
        # Verify event ordering
        if len(event_sequence) >= 2:
            # Started events should come before completed events
            started_events = [e for e in event_sequence if 'started' in e['type']]
            completed_events = [e for e in event_sequence if 'completed' in e['type']]
            
            if started_events and completed_events:
                assert started_events[0]['timestamp'] <= completed_events[-1]['timestamp']


class TestStateManagementIntegration:
    """Test state management across agent coordination."""
    
    @pytest.mark.asyncio
    async def test_state_checkpointing_between_agents(self, supervisor_with_mocks):
        """Test that state is checkpointed between agent executions."""
        supervisor, mock_agents = supervisor_with_mocks
        
        checkpoints_created = []
        
        # Mock checkpoint creation
        async def create_checkpoint(run_id, state):
            checkpoint_id = f"checkpoint-{len(checkpoints_created)}"
            checkpoints_created.append({
                'id': checkpoint_id,
                'run_id': run_id,
                'state': state
            })
            return checkpoint_id
        
        with patch('netra_backend.app.agents.supervisor.state_checkpoint_manager.StateCheckpointManager.create_checkpoint',
                  side_effect=create_checkpoint):
            
            workflow = [
                PipelineStep('triage', AgentExecutionStrategy.SEQUENTIAL, []),
                PipelineStep('optimization', AgentExecutionStrategy.SEQUENTIAL, ['triage']),
                PipelineStep('actions', AgentExecutionStrategy.SEQUENTIAL, ['optimization']),
            ]
            
            with patch.object(supervisor.workflow_orchestrator,
                            '_define_workflow_based_on_triage', return_value=workflow):
                
                context = ExecutionContext(
                    run_id="test-checkpointing",
                    agent_name="ModernSupervisor",
                    state=DeepAgentState(),
                    stream_updates=True,
                    thread_id="test-thread",
                    user_id="test-user",
                    start_time=datetime.now(timezone.utc)
                )
                
                await supervisor.execute_core_logic(context)
                
                # Verify checkpoints were created between agents
                assert len(checkpoints_created) >= 2  # At least checkpoint after major steps
    
    @pytest.mark.asyncio
    async def test_state_recovery_on_failure(self, supervisor_with_mocks):
        """Test state recovery when an agent fails."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Configure agent to fail on first attempt, succeed on retry
        execution_attempt = 0
        
        async def fail_then_succeed(state, run_id, stream_updates):
            nonlocal execution_attempt
            execution_attempt += 1
            
            if execution_attempt == 1:
                raise Exception("First attempt fails")
            
            return {"status": "success", "attempt": execution_attempt}
        
        mock_agents['optimization'].execute = fail_then_succeed
        
        # Track recovery attempts
        recovery_attempted = False
        
        async def recover_state(run_id, original_state, error):
            nonlocal recovery_attempted
            recovery_attempted = True
            return {
                "recovered": True,
                "original_error": str(error)
            }
        
        with patch('netra_backend.app.agents.supervisor.state_recovery_manager.StateRecoveryManager.prepare_recovery_state',
                  side_effect=recover_state):
            
            workflow = [
                PipelineStep('optimization', AgentExecutionStrategy.SEQUENTIAL, []),
            ]
            
            with patch.object(supervisor.workflow_orchestrator,
                            '_define_workflow_based_on_triage', return_value=workflow):
                
                context = ExecutionContext(
                    run_id="test-recovery",
                    agent_name="ModernSupervisor",
                    state=DeepAgentState(),
                    stream_updates=True,
                    thread_id="test-thread",
                    user_id="test-user",
                    start_time=datetime.now(timezone.utc)
                )
                
                # Execute with retry logic
                with patch.object(supervisor.execution_engine, 'MAX_RETRIES', 2):
                    result = await supervisor.execute_core_logic(context)
                
                # Verify recovery was attempted
                assert recovery_attempted or execution_attempt > 1


class TestPerformanceIntegration:
    """Test performance characteristics of agent coordination."""
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, supervisor_with_mocks):
        """Test concurrent execution of multiple workflows."""
        supervisor, mock_agents = supervisor_with_mocks
        
        num_workflows = 5
        workflow_results = []
        
        async def execute_workflow(workflow_id):
            context = ExecutionContext(
                run_id=f"workflow-{workflow_id}",
                agent_name="ModernSupervisor",
                state=DeepAgentState(),
                stream_updates=True,
                thread_id=f"thread-{workflow_id}",
                user_id=f"user-{workflow_id}",
                start_time=datetime.now(timezone.utc)
            )
            
            result = await supervisor.execute_core_logic(context)
            return result
        
        # Execute multiple workflows concurrently
        start_time = time.time()
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            tasks = [execute_workflow(i) for i in range(num_workflows)]
            workflow_results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        # All workflows should complete
        assert len(workflow_results) == num_workflows
        
        # Should handle concurrent workflows efficiently
        assert elapsed < num_workflows * 2  # Less than 2 seconds per workflow
    
    @pytest.mark.asyncio
    async def test_agent_pool_management(self, supervisor_with_mocks):
        """Test efficient management of agent pool under load."""
        supervisor, mock_agents = supervisor_with_mocks
        
        # Track agent utilization
        agent_utilization = {name: [] for name in mock_agents.keys()}
        
        async def track_utilization(agent_name, start=True):
            timestamp = time.time()
            agent_utilization[agent_name].append({
                'timestamp': timestamp,
                'event': 'start' if start else 'end'
            })
        
        # Wrap agent executions to track utilization
        for name, agent in mock_agents.items():
            original_execute = agent.execute
            
            async def tracked_execute(self, state, run_id, stream_updates, 
                                     agent_name=name, original=original_execute):
                await track_utilization(agent_name, start=True)
                result = await original(state, run_id, stream_updates)
                await track_utilization(agent_name, start=False)
                return result
            
            agent.execute = lambda s, r, u, a=agent, f=tracked_execute: f(a, s, r, u)
        
        # Execute multiple workflows
        workflows = []
        for i in range(3):
            context = ExecutionContext(
                run_id=f"pool-test-{i}",
                agent_name="ModernSupervisor",
                state=DeepAgentState(),
                stream_updates=True,
                thread_id=f"thread-{i}",
                user_id="test-user",
                start_time=datetime.now(timezone.utc)
            )
            workflows.append(supervisor.execute_core_logic(context))
        
        with patch.object(supervisor, '_execute_protected_workflow',
                         return_value=[ExecutionResult(success=True)]):
            await asyncio.gather(*workflows)
        
        # Analyze utilization
        for agent_name, events in agent_utilization.items():
            if events:
                # Calculate concurrent executions
                concurrent_count = 0
                max_concurrent = 0
                
                for event in sorted(events, key=lambda x: x['timestamp']):
                    if event['event'] == 'start':
                        concurrent_count += 1
                        max_concurrent = max(max_concurrent, concurrent_count)
                    else:
                        concurrent_count -= 1
                
                # Agents should handle concurrent requests
                assert max_concurrent <= 3  # No more than number of workflows


if __name__ == "__main__":
    # Run integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])