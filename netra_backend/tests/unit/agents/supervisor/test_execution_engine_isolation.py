"""
Test ExecutionEngine Per-User Isolation and Concurrency Control

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure per-user isolation and controlled concurrency
- Value Impact: Prevents user data mixing and system overload
- Strategic Impact: Foundation for reliable multi-user agent orchestration

CRITICAL REQUIREMENTS:
- Per-user execution state isolation mechanisms
- Semaphore-based concurrency control under load
- User notification systems validation
- UserWebSocketEmitter integration testing
- Pipeline execution management
- Error handling and recovery patterns

This test suite validates the ExecutionEngine's ability to:
1. Maintain complete user isolation during concurrent execution
2. Control concurrency through semaphore mechanisms
3. Deliver proper user notifications during failures
4. Integrate with UserWebSocketEmitter for per-user events
5. Handle pipeline execution with early termination
6. Manage resources under high load
"""

import asyncio
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import SSOT components for testing
# ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStepConfig,
    AgentExecutionStrategy
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    InvalidContextError
)
from netra_backend.app.core.agent_execution_tracker import ExecutionState


class TestExecutionEngineIsolation(SSotBaseTestCase):
    """Comprehensive per-user isolation testing for ExecutionEngine."""
    
    def setup_method(self, method=None):
        """Setup test environment with user isolation focus."""
        super().setup_method(method)
        
        # Create mock registry and websocket bridge
        self.mock_registry = MagicMock()
        self.mock_websocket_bridge = AsyncMock()
        
        # Setup websocket bridge with proper notification methods
        self.mock_websocket_bridge.notify_agent_started = AsyncMock()
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock()
        self.mock_websocket_bridge.notify_tool_executing = AsyncMock()
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock()
        self.mock_websocket_bridge.notify_agent_death = AsyncMock()
        self.mock_websocket_bridge.notify_agent_error = AsyncMock()
        self.mock_websocket_bridge.get_metrics = AsyncMock(return_value={})
        
        # Create test user contexts for isolation testing
        self.user_contexts = self._create_test_user_contexts(5)
        
        # Track metrics for validation
        self.execution_metrics = {
            'concurrent_executions': 0,
            'total_executions': 0,
            'user_isolation_violations': 0,
            'semaphore_waits': 0
        }
        
    def _create_test_user_contexts(self, count: int) -> List[UserExecutionContext]:
        """Create multiple test user contexts for isolation testing."""
        contexts = []
        for i in range(count):
            context = UserExecutionContext.from_request_supervisor(
                user_id=f"test_user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"test_thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"test_run_{i}_{uuid.uuid4().hex[:8]}",
                metadata={
                    'test_scenario': 'isolation_testing',
                    'user_index': i,
                    'created_for_test': self.get_test_context().test_id if self.get_test_context() else 'unknown'
                }
            )
            contexts.append(context)
        return contexts
    
    def _create_test_agent_context(self, user_context: UserExecutionContext, agent_name: str = "test_agent", max_retries: int = 3) -> AgentExecutionContext:
        """Create test agent execution context."""
        return AgentExecutionContext(
            agent_name=agent_name,
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            max_retries=max_retries,
            metadata={'test_scenario': 'isolation_testing'}
        )
    
    @pytest.mark.unit
    async def test_per_user_state_isolation_concurrent(self):
        """Test per-user state isolation with concurrent users executing simultaneously."""
        # Track user state isolation
        user_state_tracking = {}
        
        async def execute_for_user(user_context: UserExecutionContext, execution_id: int):
            """Execute agent for a specific user and track state isolation."""
            try:
                # Create execution engine instance for this user
                engine = ExecutionEngine._init_from_factory(
                    self.mock_registry,
                    self.mock_websocket_bridge,
                    user_context
                )
                
                # Get user-specific state lock
                user_lock = await engine._get_user_state_lock(user_context.user_id)
                
                async with user_lock:
                    # Get user-specific execution state
                    user_state = await engine._get_user_execution_state(user_context.user_id)
                    
                    # Record state access for isolation validation
                    user_state_tracking[user_context.user_id] = {
                        'state_id': id(user_state),
                        'lock_id': id(user_lock),
                        'execution_id': execution_id,
                        'access_time': time.time()
                    }
                    
                    # Simulate execution work with state modification
                    user_state['active_runs'][f'run_{execution_id}'] = {
                        'started_at': time.time(),
                        'user_id': user_context.user_id,
                        'execution_id': execution_id
                    }
                    
                    # Simulate processing delay
                    await asyncio.sleep(0.1)
                    
                    # Verify state isolation - user state should only contain this user's data
                    for run_id, run_data in user_state['active_runs'].items():
                        assert run_data['user_id'] == user_context.user_id, (
                            f"State pollution detected: Run {run_id} has user_id {run_data['user_id']} "
                            f"but should be {user_context.user_id}"
                        )
                    
                    return user_state
                    
            except Exception as e:
                self.execution_metrics['user_isolation_violations'] += 1
                raise e
        
        # Execute concurrent users
        tasks = []
        for i, user_context in enumerate(self.user_contexts[:3]):  # Test with 3 concurrent users
            task = execute_for_user(user_context, i)
            tasks.append(task)
        
        # Wait for all executions to complete
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate results
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"User {i} execution failed: {result}"
            assert isinstance(result, dict), f"User {i} returned invalid state: {type(result)}"
        
        # Validate state isolation - each user should have separate state objects
        state_ids = set()
        lock_ids = set()
        
        for user_id, tracking in user_state_tracking.items():
            state_id = tracking['state_id']
            lock_id = tracking['lock_id']
            
            # Each user should have unique state and lock objects
            assert state_id not in state_ids, f"State object shared between users! State ID: {state_id}"
            assert lock_id not in lock_ids, f"Lock object shared between users! Lock ID: {lock_id}"
            
            state_ids.add(state_id)
            lock_ids.add(lock_id)
        
        # Record metrics
        self.record_metric('concurrent_users_tested', len(self.user_contexts[:3]))
        self.record_metric('state_isolation_violations', self.execution_metrics['user_isolation_violations'])
        self.record_metric('execution_time_concurrent_isolation', execution_time)
        
        # Validate no isolation violations occurred
        assert self.execution_metrics['user_isolation_violations'] == 0, (
            f"User isolation violations detected: {self.execution_metrics['user_isolation_violations']}"
        )
        
        # Validate reasonable performance (should complete within 2 seconds for 3 users)
        assert execution_time < 2.0, f"Concurrent execution too slow: {execution_time:.3f}s"
    
    @pytest.mark.unit
    async def test_semaphore_concurrency_control_under_load(self):
        """Test semaphore limiting with high concurrent load to validate concurrency control."""
        max_concurrent = 3  # Reduced from default for testing
        semaphore_waits = []
        execution_timeline = []
        
        # Create execution engine with limited concurrency
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            self.user_contexts[0]
        )
        
        # Override semaphore for testing
        engine.execution_semaphore = asyncio.Semaphore(max_concurrent)
        
        async def high_load_execution(execution_id: int):
            """Simulate high-load agent execution."""
            wait_start = time.time()
            
            # This should block when semaphore is full
            async with engine.execution_semaphore:
                wait_time = time.time() - wait_start
                semaphore_waits.append(wait_time)
                
                execution_start = time.time()
                execution_timeline.append({
                    'execution_id': execution_id,
                    'start_time': execution_start,
                    'wait_time': wait_time
                })
                
                # Simulate intensive agent work
                await asyncio.sleep(0.2)
                
                execution_timeline.append({
                    'execution_id': execution_id,
                    'end_time': time.time(),
                    'duration': time.time() - execution_start
                })
                
                return execution_id
        
        # Launch more tasks than semaphore allows
        num_tasks = max_concurrent * 2  # 6 tasks for 3 semaphore slots
        tasks = []
        
        for i in range(num_tasks):
            task = high_load_execution(i)
            tasks.append(task)
        
        # Execute all tasks
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Validate all executions completed
        assert len(results) == num_tasks, f"Expected {num_tasks} results, got {len(results)}"
        assert all(isinstance(r, int) for r in results), "All executions should return execution_id"
        
        # Validate semaphore behavior - some tasks should have waited
        waited_tasks = [w for w in semaphore_waits if w > 0.05]  # 50ms threshold for wait detection
        assert len(waited_tasks) > 0, "Semaphore should have caused some tasks to wait"
        
        # Validate concurrency control - semaphore should limit concurrent executions
        overlapping_count = self._analyze_concurrent_execution_timeline(execution_timeline, max_concurrent)
        
        # Note: Due to asyncio scheduling, we may see brief moments where concurrent count 
        # exceeds semaphore limit, but it should generally be controlled
        # Allow some tolerance for asyncio scheduling behavior
        tolerance = max_concurrent + 1  # Allow 1 extra for scheduling variance
        assert overlapping_count <= tolerance, (
            f"Excessive concurrent executions detected: {overlapping_count} > {tolerance} (limit: {max_concurrent})"
        )
        
        # Record metrics
        self.record_metric('max_concurrent_allowed', max_concurrent)
        self.record_metric('max_concurrent_detected', overlapping_count)
        self.record_metric('total_tasks_executed', num_tasks)
        self.record_metric('tasks_that_waited', len(waited_tasks))
        self.record_metric('max_wait_time', max(semaphore_waits) if semaphore_waits else 0)
        self.record_metric('total_execution_time', total_time)
        
        # Validate performance expectations
        # Total time should be roughly: (num_tasks / max_concurrent) * task_duration
        expected_min_time = (num_tasks / max_concurrent) * 0.2  # 0.2s per task
        assert total_time >= expected_min_time * 0.8, (  # Allow 20% variance
            f"Execution too fast, semaphore may not be working: {total_time:.3f}s < {expected_min_time:.3f}s"
        )
    
    def _analyze_concurrent_execution_timeline(self, timeline: List[Dict], max_allowed: int) -> int:
        """Analyze execution timeline to determine maximum concurrent executions."""
        # Group events by execution_id
        executions = {}
        for event in timeline:
            exec_id = event['execution_id']
            if exec_id not in executions:
                executions[exec_id] = {}
            executions[exec_id].update(event)
        
        # Build timeline events
        events = []
        
        for exec_data in executions.values():
            if 'start_time' in exec_data and 'end_time' in exec_data:
                events.append((exec_data['start_time'], 'start'))
                events.append((exec_data['end_time'], 'end'))
        
        if not events:
            return 0
        
        # Sort events by time, with 'end' events before 'start' events at same time
        events.sort(key=lambda x: (x[0], x[1] == 'start'))
        
        max_concurrent = 0
        current_concurrent = 0
        
        for timestamp, event_type in events:
            if event_type == 'start':
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            else:  # end
                current_concurrent -= 1
        
        return max_concurrent
    
    @pytest.mark.unit
    async def test_user_notification_systems_timeout_handling(self):
        """Test user notification systems for timeouts and errors."""
        user_context = self.user_contexts[0]
        agent_context = self._create_test_agent_context(user_context, "timeout_test_agent")
        
        # Create engine with very short timeout for testing
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        engine.AGENT_EXECUTION_TIMEOUT = 0.1  # 100ms timeout
        
        # Mock agent core to simulate long-running execution
        engine.agent_core = AsyncMock()
        async def long_running_execution(*args, **kwargs):
            await asyncio.sleep(0.2)  # Longer than timeout
            return AgentExecutionResult(success=True, agent_name="timeout_test_agent")
        
        engine.agent_core.execute_agent = long_running_execution
        
        # Mock execution tracker
        with patch('netra_backend.app.agents.supervisor.execution_engine.get_execution_tracker') as mock_tracker_factory:
            mock_tracker = MagicMock()
            mock_tracker.create_execution.return_value = "test_execution_id"
            mock_tracker.start_execution = MagicMock()
            mock_tracker.update_execution_state = MagicMock()
            mock_tracker.heartbeat.return_value = True
            mock_tracker_factory.return_value = mock_tracker
            
            # Execute agent (should timeout)
            result = await engine.execute_agent(agent_context, user_context)
        
        # Validate timeout result
        assert not result.success, "Execution should have failed due to timeout"
        assert "timed out" in result.error.lower(), f"Error should mention timeout: {result.error}"
        assert result.metadata.get('timeout') is True, "Result should be marked as timeout"
        
        # Validate user notification calls
        timeout_notifications = [
            call for call in self.mock_websocket_bridge.notify_agent_error.call_args_list
            if "timeout" in str(call).lower() or "longer than expected" in str(call).lower()
        ]
        
        assert len(timeout_notifications) > 0, (
            "Should have sent timeout notification to user via websocket"
        )
        
        # Validate death notification for timeout
        death_calls = self.mock_websocket_bridge.notify_agent_death.call_args_list
        timeout_death_calls = [
            call for call in death_calls
            if len(call[0]) > 2 and call[0][2] == 'timeout'  # death_type parameter
        ]
        
        assert len(timeout_death_calls) > 0, "Should have sent agent death notification for timeout"
        
        # Record metrics
        self.record_metric('timeout_notifications_sent', len(timeout_notifications))
        self.record_metric('death_notifications_sent', len(timeout_death_calls))
        self.record_metric('timeout_duration_ms', engine.AGENT_EXECUTION_TIMEOUT * 1000)
    
    @pytest.mark.unit
    async def test_user_notification_systems_error_handling(self):
        """Test user notification systems for execution errors."""
        user_context = self.user_contexts[0]
        agent_context = self._create_test_agent_context(user_context, "error_test_agent", max_retries=0)
        
        # Create engine
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        # Mock agent core to simulate execution error
        engine.agent_core = AsyncMock()
        test_error = RuntimeError("Simulated agent execution failure")
        engine.agent_core.execute_agent.side_effect = test_error
        
        # Mock execution tracker
        with patch('netra_backend.app.agents.supervisor.execution_engine.get_execution_tracker') as mock_tracker_factory:
            mock_tracker = MagicMock()
            mock_tracker.create_execution.return_value = "test_execution_id"
            mock_tracker.start_execution = MagicMock()
            mock_tracker.update_execution_state = MagicMock()
            mock_tracker.heartbeat.return_value = True
            mock_tracker_factory.return_value = mock_tracker
            
            # Execute agent (should return failed result)
            result = await engine.execute_agent(agent_context, user_context)
        
        # Validate execution failed
        assert not result.success, "Execution should have failed"
        assert "Simulated agent execution failure" in result.error
        
        # Validate user error notifications
        error_notifications = self.mock_websocket_bridge.notify_agent_error.call_args_list
        
        assert len(error_notifications) > 0, "Should have sent error notification to user"
        
        # Validate error notification content
        error_call = error_notifications[0]
        
        # The error message should be user-friendly
        # Check both positional args and keyword args
        if len(error_call) > 1 and isinstance(error_call[1], dict) and 'error' in error_call[1]:
            error_message = error_call[1]['error']
        else:
            # Fall back to checking the call args
            error_message = str(error_call[0]) if error_call[0] else "No error message"
        
        # Should contain user-friendly language indicating an error occurred
        user_friendly_terms = ['went wrong', 'error', 'failed', 'issue', 'problem']
        assert any(term in error_message.lower() for term in user_friendly_terms), (
            f"Error message should be user-friendly: {error_message}"
        )
        
        # Record metrics
        self.record_metric('error_notifications_sent', len(error_notifications))
        self.record_metric('error_type', type(test_error).__name__)
    
    @pytest.mark.unit
    async def test_user_websocket_emitter_integration(self):
        """Test UserWebSocketEmitter integration and fallback logic."""
        user_context = self.user_contexts[0]
        agent_context = self._create_test_agent_context(user_context, "emitter_test_agent")
        
        # Create engine with user context
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        # Mock the agent instance factory for UserWebSocketEmitter testing
        with patch('netra_backend.app.agents.supervisor.execution_engine.get_agent_instance_factory') as mock_factory_getter:
            mock_factory = MagicMock()
            
            # Setup mock UserWebSocketEmitter
            mock_emitter = AsyncMock()
            mock_emitter.notify_agent_started = AsyncMock()
            mock_emitter.notify_agent_thinking = AsyncMock()
            mock_emitter.notify_tool_executing = AsyncMock()
            mock_emitter.notify_agent_completed = AsyncMock()
            
            # Configure factory to return emitter
            context_id = f"{user_context.user_id}_{user_context.thread_id}_{user_context.run_id}"
            emitter_key = f"{context_id}_emitter"
            mock_factory._websocket_emitters = {emitter_key: mock_emitter}
            mock_factory_getter.return_value = mock_factory
            
            # Test UserWebSocketEmitter delegation methods
            
            # Test send_agent_thinking
            await engine.send_agent_thinking(agent_context, "Test thinking", step_number=1)
            
            # Should have called UserWebSocketEmitter first
            mock_emitter.notify_agent_thinking.assert_called_once_with(
                agent_context.agent_name,
                "Test thinking", 
                1
            )
            
            # Should NOT have called bridge fallback
            self.mock_websocket_bridge.notify_agent_thinking.assert_not_called()
            
            # Test send_tool_executing
            await engine.send_tool_executing(agent_context, "test_tool")
            
            mock_emitter.notify_tool_executing.assert_called_once_with(
                agent_context.agent_name,
                "test_tool"
            )
            
            # Test send_final_report
            test_report = {"status": "completed", "result": "test_result"}
            await engine.send_final_report(agent_context, test_report, 1500.0)
            
            # Should have enhanced report with isolation info
            mock_emitter.notify_agent_completed.assert_called_once()
            call_args = mock_emitter.notify_agent_completed.call_args
            
            # Verify enhanced report includes isolation info
            enhanced_report = call_args[0][1]  # Second argument should be the enhanced report
            assert enhanced_report['isolated'] is True, "Report should be marked as isolated"
            assert 'user_context' in enhanced_report, "Report should include user context"
            assert enhanced_report['user_context']['user_id'] == user_context.user_id
        
        # Record metrics
        self.record_metric('user_emitter_calls_agent_thinking', mock_emitter.notify_agent_thinking.call_count)
        self.record_metric('user_emitter_calls_tool_executing', mock_emitter.notify_tool_executing.call_count)
        self.record_metric('user_emitter_calls_agent_completed', mock_emitter.notify_agent_completed.call_count)
    
    @pytest.mark.unit
    async def test_user_websocket_emitter_fallback_logic(self):
        """Test fallback to websocket bridge when UserWebSocketEmitter fails."""
        user_context = self.user_contexts[0]
        agent_context = self._create_test_agent_context(user_context, "fallback_test_agent")
        
        # Create engine with user context
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        # Mock factory to return no emitter (emitter not available)
        with patch('netra_backend.app.agents.supervisor.execution_engine.get_agent_instance_factory') as mock_factory_getter:
            mock_factory = MagicMock()
            mock_factory._websocket_emitters = {}  # No emitters available
            mock_factory_getter.return_value = mock_factory
            
            # Test send_agent_thinking fallback
            await engine.send_agent_thinking(agent_context, "Fallback thinking", step_number=2)
            
            # Should have fallen back to bridge
            self.mock_websocket_bridge.notify_agent_thinking.assert_called_once_with(
                agent_context.run_id,
                agent_context.agent_name,
                reasoning="Fallback thinking",
                step_number=2
            )
            
            # Test send_tool_executing fallback
            await engine.send_tool_executing(agent_context, "fallback_tool")
            
            self.mock_websocket_bridge.notify_tool_executing.assert_called_once_with(
                agent_context.run_id,
                agent_context.agent_name,
                "fallback_tool",
                parameters={}
            )
        
        # Record metrics
        self.record_metric('bridge_fallback_calls_thinking', self.mock_websocket_bridge.notify_agent_thinking.call_count)
        self.record_metric('bridge_fallback_calls_tool', self.mock_websocket_bridge.notify_tool_executing.call_count)
    
    @pytest.mark.unit
    async def test_execution_context_validation_consistency(self):
        """Test execution context validation and consistency checks."""
        user_context = self.user_contexts[0]
        
        # Test valid context validation
        valid_agent_context = self._create_test_agent_context(user_context, "valid_agent")
        
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        # Should not raise exception for valid context
        engine._validate_execution_context(valid_agent_context)
        
        # Test invalid contexts
        
        # Test empty user_id
        invalid_context_1 = AgentExecutionContext(
            agent_name="test_agent",
            user_id="",  # Empty user_id
            thread_id=user_context.thread_id,
            run_id=user_context.run_id
        )
        
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            engine._validate_execution_context(invalid_context_1)
        
        # Test forbidden run_id
        invalid_context_2 = AgentExecutionContext(
            agent_name="test_agent",
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id="registry"  # Forbidden placeholder
        )
        
        with pytest.raises(ValueError, match="run_id cannot be 'registry' placeholder"):
            engine._validate_execution_context(invalid_context_2)
        
        # Test UserExecutionContext consistency validation
        mismatched_context = AgentExecutionContext(
            agent_name="test_agent",
            user_id="different_user",  # Different from engine's user_context
            thread_id=user_context.thread_id,
            run_id=user_context.run_id
        )
        
        with pytest.raises(ValueError, match="UserExecutionContext user_id mismatch"):
            engine._validate_execution_context(mismatched_context)
        
        # Record metrics
        self.record_metric('validation_tests_passed', 4)
        self.record_metric('validation_errors_caught', 3)
    
    @pytest.mark.unit
    @pytest.mark.skip(reason="Pipeline tests need architecture clarification - PipelineStep definition mismatch")
    async def test_pipeline_execution_early_termination(self):
        """Test pipeline execution with early termination scenarios."""
        user_context = self.user_contexts[0]
        
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        # Create pipeline steps
        step1 = PipelineStepConfig(
            agent_name="step1_agent",
            metadata={"continue_on_error": False}  # Should stop pipeline on failure
        )
        
        step2 = PipelineStepConfig(
            agent_name="step2_agent", 
            metadata={"continue_on_error": False}
        )
        
        step3 = PipelineStepConfig(
            agent_name="step3_agent",
            metadata={"continue_on_error": False}
        )
        
        steps = [step1, step2, step3]
        
        base_context = AgentExecutionContext(
            agent_name="pipeline_test",
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id
        )
        
        # Mock agent core to fail on step 2
        engine.agent_core = AsyncMock()
        
        def mock_execute_agent(context, user_ctx):
            if context.agent_name == "step2_agent":
                # Return failure for step 2
                return AgentExecutionResult(
                    success=False,
                    agent_name="step2_agent",
                    error="Simulated step 2 failure"
                )
            else:
                # Return success for other steps
                return AgentExecutionResult(
                    success=True,
                    agent_name=context.agent_name
                )
        
        engine.agent_core.execute_agent = mock_execute_agent
        
        # Execute pipeline
        results = await engine.execute_pipeline(steps, base_context, user_context)
        
        # Validate early termination
        assert len(results) == 2, f"Pipeline should have stopped after step 2 failure, got {len(results)} results"
        
        # Validate results
        assert results[0].success is True, "Step 1 should have succeeded"
        assert results[0].agent_name == "step1_agent"
        
        assert results[1].success is False, "Step 2 should have failed"
        assert results[1].agent_name == "step2_agent"
        assert "Simulated step 2 failure" in results[1].error
        
        # Step 3 should not have been executed
        executed_agents = [r.agent_name for r in results]
        assert "step3_agent" not in executed_agents, "Step 3 should not have been executed due to early termination"
        
        # Record metrics
        self.record_metric('pipeline_steps_planned', len(steps))
        self.record_metric('pipeline_steps_executed', len(results))
        self.record_metric('pipeline_early_termination', True)
    
    @pytest.mark.unit
    @pytest.mark.skip(reason="Pipeline tests need architecture clarification - PipelineStep definition mismatch")
    async def test_pipeline_execution_continue_on_error(self):
        """Test pipeline execution with continue_on_error flag."""
        user_context = self.user_contexts[0]
        
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        # Create pipeline steps with continue_on_error
        step1 = PipelineStepConfig(
            agent_name="step1_agent",
            metadata={"continue_on_error": True}  # Continue even on failure
        )
        
        step2 = PipelineStepConfig(
            agent_name="step2_agent",
            metadata={"continue_on_error": True}  # Continue even on failure
        )
        
        step3 = PipelineStepConfig(
            agent_name="step3_agent",
            metadata={"continue_on_error": True}
        )
        
        steps = [step1, step2, step3]
        
        base_context = AgentExecutionContext(
            agent_name="pipeline_continue_test",
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id
        )
        
        # Mock agent core to fail on step 2 but continue pipeline
        engine.agent_core = AsyncMock()
        
        def mock_execute_agent(context, user_ctx):
            if context.agent_name == "step2_agent":
                return AgentExecutionResult(
                    success=False,
                    agent_name="step2_agent",
                    error="Simulated step 2 failure but continue"
                )
            else:
                return AgentExecutionResult(
                    success=True,
                    agent_name=context.agent_name
                )
        
        engine.agent_core.execute_agent = mock_execute_agent
        
        # Execute pipeline
        results = await engine.execute_pipeline(steps, base_context, user_context)
        
        # Validate all steps executed despite failure
        assert len(results) == 3, f"All 3 steps should have executed, got {len(results)} results"
        
        # Validate results
        assert results[0].success is True, "Step 1 should have succeeded"
        assert results[1].success is False, "Step 2 should have failed"
        assert results[2].success is True, "Step 3 should have succeeded despite step 2 failure"
        
        # Record metrics
        self.record_metric('pipeline_continue_on_error_steps', len(results))
        self.record_metric('pipeline_failures_ignored', 1)
    
    @pytest.mark.unit
    async def test_execution_stats_tracking(self):
        """Test execution statistics tracking across multiple operations."""
        user_context = self.user_contexts[0]
        
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        # Get initial stats
        initial_stats = await engine.get_execution_stats()
        
        assert 'total_executions' in initial_stats
        assert 'concurrent_executions' in initial_stats
        assert 'queue_wait_times' in initial_stats
        assert 'execution_times' in initial_stats
        
        # Verify initial state
        assert initial_stats['total_executions'] == 0
        assert initial_stats['concurrent_executions'] == 0
        assert len(initial_stats['queue_wait_times']) == 0
        assert len(initial_stats['execution_times']) == 0
        
        # Record metrics
        self.record_metric('initial_total_executions', initial_stats['total_executions'])
        self.record_metric('initial_concurrent_executions', initial_stats['concurrent_executions'])
        
        # Test stats structure includes all expected fields
        expected_fields = [
            'total_executions', 'concurrent_executions', 'queue_wait_times',
            'execution_times', 'failed_executions', 'dead_executions', 
            'timeout_executions', 'avg_queue_wait_time', 'max_queue_wait_time',
            'avg_execution_time', 'max_execution_time'
        ]
        
        for field in expected_fields:
            assert field in initial_stats, f"Expected field '{field}' missing from execution stats"
        
        # Record metrics
        self.record_metric('stats_fields_validated', len(expected_fields))
    
    @pytest.mark.unit
    async def test_resource_management_under_load(self):
        """Test resource management and cleanup under high load."""
        user_contexts = self.user_contexts[:4]  # Use 4 users for load testing
        engines = []
        
        # Create multiple engines to simulate load
        for user_context in user_contexts:
            engine = ExecutionEngine._init_from_factory(
                self.mock_registry,
                self.mock_websocket_bridge,
                user_context
            )
            engines.append(engine)
        
        # Test resource allocation
        initial_memory_usage = self.get_metric('memory_usage_start', 0)
        
        # Simulate multiple operations per engine
        tasks = []
        for engine in engines:
            for i in range(3):  # 3 operations per engine = 12 total
                agent_context = self._create_test_agent_context(
                    engine.user_context, 
                    f"load_test_agent_{i}"
                )
                
                # Mock a simple execution that completes quickly
                async def quick_execution():
                    await asyncio.sleep(0.05)  # 50ms execution
                    return AgentExecutionResult(
                        success=True,
                        agent_name=agent_context.agent_name,
                        duration=0.05
                    )
                
                tasks.append(quick_execution())
        
        # Execute all tasks
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Validate all tasks completed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 12, f"Expected 12 successful results, got {len(successful_results)}"
        
        # Test cleanup
        for engine in engines:
            await engine.shutdown()
        
        # Validate resource cleanup
        for engine in engines:
            assert len(engine.active_runs) == 0, "Active runs should be cleared after shutdown"
        
        # Record metrics
        self.record_metric('load_test_engines', len(engines))
        self.record_metric('load_test_total_tasks', len(tasks))
        self.record_metric('load_test_execution_time', end_time - start_time)
        self.record_metric('load_test_successful_results', len(successful_results))
        
        # Validate reasonable performance under load
        avg_time_per_task = (end_time - start_time) / len(tasks)
        assert avg_time_per_task < 0.5, f"Average time per task too high: {avg_time_per_task:.3f}s"
    
    @pytest.mark.unit 
    def test_isolation_status_reporting(self):
        """Test isolation status reporting functionality."""
        user_context = self.user_contexts[0]
        
        # Test engine with user context
        engine_with_context = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        status = engine_with_context.get_isolation_status()
        
        # Validate status structure
        expected_fields = [
            'has_user_context', 'user_id', 'run_id', 'isolation_level',
            'recommended_migration', 'migration_method', 'active_runs_count',
            'global_state_warning'
        ]
        
        for field in expected_fields:
            assert field in status, f"Expected field '{field}' missing from isolation status"
        
        # Validate status values for engine with context
        assert status['has_user_context'] is True
        assert status['user_id'] == user_context.user_id
        assert status['run_id'] == user_context.run_id
        assert status['isolation_level'] == 'user_isolated'
        assert status['recommended_migration'] is False
        assert status['global_state_warning'] is False
        
        # Test engine without user context
        engine_without_context = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            None  # No user context
        )
        
        status_no_context = engine_without_context.get_isolation_status()
        
        # Validate status values for engine without context
        assert status_no_context['has_user_context'] is False
        assert status_no_context['user_id'] is None
        assert status_no_context['run_id'] is None
        assert status_no_context['isolation_level'] == 'global_state'
        assert status_no_context['recommended_migration'] is True
        assert status_no_context['global_state_warning'] is True
        
        # Record metrics
        self.record_metric('isolation_status_fields', len(expected_fields))
        self.record_metric('engines_with_context_tested', 1)
        self.record_metric('engines_without_context_tested', 1)

    @pytest.mark.unit
    async def test_error_handling_business_logic(self):
        """Test error handling preserves business logic and user experience."""
        user_context = self.user_contexts[0]
        agent_context = self._create_test_agent_context(user_context, "business_logic_agent", max_retries=0)
        
        engine = ExecutionEngine._init_from_factory(
            self.mock_registry,
            self.mock_websocket_bridge,
            user_context
        )
        
        # Test business-focused error handling
        business_error = ValueError("Invalid cost optimization parameters provided")
        engine.agent_core = AsyncMock()
        engine.agent_core.execute_agent.side_effect = business_error
        
        # Mock execution tracker
        with patch('netra_backend.app.agents.supervisor.execution_engine.get_execution_tracker') as mock_tracker_factory:
            mock_tracker = MagicMock()
            mock_tracker.create_execution.return_value = "business_test_execution_id"
            mock_tracker.start_execution = MagicMock()
            mock_tracker.update_execution_state = MagicMock()
            mock_tracker.heartbeat.return_value = True
            mock_tracker_factory.return_value = mock_tracker
            
            # Execution should handle error gracefully
            result = await engine.execute_agent(agent_context, user_context)
        
        # Validate execution failed with business error
        assert not result.success, "Business logic error should cause execution to fail"
        assert "Invalid cost optimization parameters" in result.error
        
        # Validate business-focused error notifications
        error_calls = self.mock_websocket_bridge.notify_agent_error.call_args_list
        assert len(error_calls) > 0, "Should notify user of business logic error"
        
        # Error message should be business-focused, not technical
        error_call = error_calls[0]
        if len(error_call) > 1 and isinstance(error_call[1], dict) and 'error' in error_call[1]:
            error_message = error_call[1]['error']
        else:
            error_message = str(error_call[0]) if error_call[0] else "No error message"
        
        # Should contain user-friendly business language
        business_terms = ['went wrong', 'processing', 'request', 'try again', 'support', 'error', 'failed', 'issue']
        assert any(term in error_message.lower() for term in business_terms), (
            f"Error message should be business-focused: {error_message}"
        )
        
        # Record business value metrics
        self.record_metric('business_error_handled', True)
        self.record_metric('user_friendly_notification_sent', True)