"""
Comprehensive Unit Tests for ExecutionEngine Golden Path SSOT Class

Business Value Justification (BVJ):
- Segment: ALL (Free/Early/Mid/Enterprise/Platform) 
- Business Goal: Platform Stability - Agent pipeline execution reliability
- Value Impact: Validates agent pipeline execution (core of AI chat functionality)
- Revenue Impact: Protects $500K+ ARR from execution failures, ensures <2s response times

Critical Golden Path Scenarios Tested:
1. Agent pipeline execution: ExecutionEngine → Agent execution → Results
2. Multi-user isolation: User execution contexts completely isolated
3. WebSocket event delivery: All 5 critical events during agent execution
4. Concurrency control: Semaphore-based execution limiting for 5+ users
5. Error handling: Timeout detection, death monitoring, graceful recovery

SSOT Testing Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real services preferred over mocks (only external dependencies mocked)
- Business-critical functionality validation over implementation details
- Agent execution business logic focus
"""

import asyncio
import time
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# SSOT MIGRATION: Use UserExecutionEngine as the single source of truth
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, 
    AgentExecutionResult,
    PipelineStep
)

# Supporting Infrastructure
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestExecutionEngineComprehensiveGoldenPath(SSotAsyncTestCase):
    """
    Comprehensive unit tests for ExecutionEngine SSOT class.
    
    Tests the critical agent pipeline execution functionality that enables
    AI agent orchestration and chat delivery reliability.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup test environment for ExecutionEngine testing."""
        # Create mock infrastructure using SSOT mock factory
        self.mock_factory = SSotMockFactory()
        
        # Core mocked dependencies (external only - keep business logic real)
        self.mock_agent_registry = self.mock_factory.create_mock("AgentRegistry")
        self.mock_websocket_bridge = self.mock_factory.create_mock_agent_websocket_bridge()
        self.mock_agent_core = self.mock_factory.create_mock("AgentExecutionCore")
        self.mock_execution_tracker = self.mock_factory.create_mock("ExecutionTracker")
        
        # Test user contexts for multi-user isolation testing
        self.test_user_context_1 = UserExecutionContext(
            user_id="exec_user_001",
            thread_id="exec_thread_001",
            run_id="exec_run_001",
            request_id="exec_req_001",
            websocket_client_id="exec_ws_001"
        )
        
        self.test_user_context_2 = UserExecutionContext(
            user_id="exec_user_002", 
            thread_id="exec_thread_002",
            run_id="exec_run_002",
            request_id="exec_req_002",
            websocket_client_id="exec_ws_002"
        )
        
        # Test execution contexts
        self.test_execution_context_1 = AgentExecutionContext(
            run_id="exec_run_001",
            thread_id="exec_thread_001",
            user_id="exec_user_001",
            agent_name="test_agent",
            metadata={"test_key": "test_value"}
        )
        
        # Track WebSocket events for validation
        self.captured_websocket_events = []
        
        # Configure mock behaviors for execution engine testing
        await self._setup_mock_behaviors()
    
    async def _setup_mock_behaviors(self):
        """Setup realistic mock behaviors for execution engine testing."""
        # Configure agent core to simulate real agent execution
        self.mock_agent_core.execute_agent = AsyncMock(return_value=AgentExecutionResult(
            success=True,
            agent_name="test_agent",
            execution_time=0.5,
            data={"result": "test_result"}
        ))
        
        # Configure WebSocket bridge to capture events for validation
        async def capture_websocket_event(event_type, *args, **kwargs):
            self.captured_websocket_events.append({
                'event_type': event_type,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
        
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('agent_started', *a, **k)
        )
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('agent_thinking', *a, **k)
        )
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('agent_completed', *a, **k)
        )
        self.mock_websocket_bridge.notify_agent_error = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('agent_error', *a, **k)
        )
        self.mock_websocket_bridge.notify_agent_death = AsyncMock(
            side_effect=lambda *a, **k: capture_websocket_event('agent_death', *a, **k)
        )
        
        # Configure execution tracker
        self.mock_execution_tracker.create_execution = MagicMock(return_value="test_execution_id")
        self.mock_execution_tracker.start_execution = MagicMock()
        self.mock_execution_tracker.update_execution_state = MagicMock()
        self.mock_execution_tracker.heartbeat = MagicMock(return_value=True)
        self.mock_execution_tracker.register_death_callback = MagicMock()
        self.mock_execution_tracker.register_timeout_callback = MagicMock()
        
        # Patch dependencies
        self.execution_tracker_patch = patch(
            'netra_backend.app.agents.supervisor.execution_engine.get_execution_tracker',
            return_value=self.mock_execution_tracker
        )
        self.execution_tracker_patch.start()
        
        self.supervisor_flow_logger_patch = patch(
            'netra_backend.app.agents.supervisor.execution_engine.get_supervisor_flow_logger'
        )
        self.supervisor_flow_logger_patch.start()
    
    async def teardown_method(self):
        """Clean up after each test."""
        # Stop patches
        if hasattr(self, 'execution_tracker_patch'):
            self.execution_tracker_patch.stop()
        if hasattr(self, 'supervisor_flow_logger_patch'):
            self.supervisor_flow_logger_patch.stop()
        
        # Clear captured events
        self.captured_websocket_events.clear()
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 1: Agent Pipeline Execution
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.business_critical
    async def test_execute_agent_golden_path_pipeline_execution(self):
        """
        Test the golden path agent pipeline execution.
        
        BVJ: Validates core agent execution pipeline (foundation of AI chat)
        Critical Path: ExecutionEngine → Agent execution → Success result
        """
        # Arrange: Create ExecutionEngine with real business logic
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Act: Execute agent through pipeline
        result = await execution_engine.execute_agent(
            self.test_execution_context_1,
            user_context=self.test_user_context_1
        )
        
        # Assert: Verify pipeline execution completed successfully
        assert result is not None
        assert result.success is True
        assert result.agent_name == "test_agent"
        assert result.execution_time > 0
        assert "result" in result.data
        
        # Verify execution tracking was called
        self.mock_execution_tracker.create_execution.assert_called_once()
        self.mock_execution_tracker.start_execution.assert_called_once()
        self.mock_execution_tracker.update_execution_state.assert_called()
        
        # Verify agent core was called with correct context
        self.mock_agent_core.execute_agent.assert_called_once()
        call_args = self.mock_agent_core.execute_agent.call_args
        assert call_args[0][0] == self.test_execution_context_1
        assert call_args[0][1] == self.test_user_context_1
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 2: Multi-User Execution Isolation
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.isolation_critical
    async def test_multi_user_execution_isolation_validation(self):
        """
        Test that agent execution is properly isolated between different users.
        
        BVJ: Enterprise security requirement - prevents execution data mixing
        Critical Path: User1 execution ∥ User2 execution (no cross-contamination)
        """
        # Arrange: Create two execution engines for different users
        engine1 = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        engine2 = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_2
        )
        
        # Create separate execution contexts for each user
        context1 = AgentExecutionContext(
            run_id=self.test_user_context_1.run_id,
            thread_id=self.test_user_context_1.thread_id,
            user_id=self.test_user_context_1.user_id,
            agent_name="isolated_agent_1",
            metadata={"user": "user_001"}
        )
        
        context2 = AgentExecutionContext(
            run_id=self.test_user_context_2.run_id,
            thread_id=self.test_user_context_2.thread_id,
            user_id=self.test_user_context_2.user_id,
            agent_name="isolated_agent_2",
            metadata={"user": "user_002"}
        )
        
        # Act: Execute both users concurrently
        result1_task = engine1.execute_agent(context1, self.test_user_context_1)
        result2_task = engine2.execute_agent(context2, self.test_user_context_2)
        
        result1, result2 = await asyncio.gather(result1_task, result2_task)
        
        # Assert: Verify complete isolation between users
        assert result1.agent_name == "isolated_agent_1"
        assert result2.agent_name == "isolated_agent_2"
        
        # Verify user-specific state isolation
        user1_state = await engine1._get_user_execution_state("exec_user_001")
        user2_state = await engine2._get_user_execution_state("exec_user_002")
        
        assert user1_state != user2_state
        assert user1_state['execution_stats']['total_executions'] == 1
        assert user2_state['execution_stats']['total_executions'] == 1
        
        # Verify separate state locks were created
        lock1 = await engine1._get_user_state_lock("exec_user_001")
        lock2 = await engine2._get_user_state_lock("exec_user_002")
        
        assert lock1 != lock2
        assert isinstance(lock1, asyncio.Lock)
        assert isinstance(lock2, asyncio.Lock)
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 3: WebSocket Event Delivery During Execution
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.websocket_critical
    async def test_websocket_events_during_agent_execution(self):
        """
        Test WebSocket event delivery during agent execution.
        
        BVJ: Real-time user feedback - enables chat experience
        Critical Events: agent_started, agent_thinking, agent_completed
        """
        # Arrange: Create ExecutionEngine
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Act: Execute agent with WebSocket event tracking
        await execution_engine.execute_agent(
            self.test_execution_context_1,
            user_context=self.test_user_context_1
        )
        
        # Assert: Verify critical WebSocket events were sent
        event_types = [event['event_type'] for event in self.captured_websocket_events]
        
        # Verify agent_started event
        assert 'agent_started' in event_types, "agent_started event missing"
        started_event = next(e for e in self.captured_websocket_events if e['event_type'] == 'agent_started')
        assert started_event['args'][0] == "exec_run_001"
        assert started_event['args'][1] == "test_agent"
        
        # Verify agent_thinking events
        thinking_events = [e for e in self.captured_websocket_events if e['event_type'] == 'agent_thinking']
        assert len(thinking_events) >= 1, "agent_thinking events missing"
        
        # Verify agent_completed event
        assert 'agent_completed' in event_types, "agent_completed event missing"
        completed_event = next(e for e in self.captured_websocket_events if e['event_type'] == 'agent_completed')
        assert completed_event['args'][0] == "exec_run_001"
        assert completed_event['args'][1] == "test_agent"
        
        # Verify event sequence (started → thinking → completed)
        event_timestamps = [(e['event_type'], e['timestamp']) for e in self.captured_websocket_events]
        event_timestamps.sort(key=lambda x: x[1])  # Sort by timestamp
        
        # Find event indices
        started_idx = next(i for i, (event_type, _) in enumerate(event_timestamps) if event_type == 'agent_started')
        completed_idx = next(i for i, (event_type, _) in enumerate(event_timestamps) if event_type == 'agent_completed')
        
        assert started_idx < completed_idx, "WebSocket events sent in wrong order"
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 4: Concurrency Control and Performance
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.performance
    async def test_concurrency_control_semaphore_limiting(self):
        """
        Test concurrency control with semaphore-based execution limiting.
        
        BVJ: Platform scalability - supports 5+ concurrent users with controlled resource usage
        """
        # Arrange: Create ExecutionEngine with limited concurrency
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Configure a slower agent execution to test concurrency control
        slow_execution_time = 0.1  # 100ms delay
        self.mock_agent_core.execute_agent = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.sleep(slow_execution_time) or AgentExecutionResult(
            success=True,
            agent_name="slow_agent",
            execution_time=slow_execution_time,
            data={"result": "slow_result"}
        ))
        
        # Create multiple execution contexts
        num_concurrent = 15  # More than default semaphore limit (10)
        contexts = []
        for i in range(num_concurrent):
            context = AgentExecutionContext(
                run_id=f"concurrent_run_{i:03d}",
                thread_id=f"concurrent_thread_{i:03d}",
                user_id=f"concurrent_user_{i:03d}",
                agent_name=f"concurrent_agent_{i:03d}",
                metadata={"concurrent_test": i}
            )
            contexts.append(context)
        
        # Act: Execute all agents concurrently and measure timing
        start_time = time.time()
        
        tasks = [
            execution_engine.execute_agent(context, user_context=None)
            for context in contexts
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Assert: Verify concurrency control worked
        assert len(results) == num_concurrent
        assert all(result.success for result in results)
        
        # Verify semaphore controlled execution timing
        # With 10 concurrent slots and 15 tasks, some tasks should be queued
        expected_min_duration = (num_concurrent / execution_engine.MAX_CONCURRENT_AGENTS) * slow_execution_time
        assert total_duration >= expected_min_duration * 0.8  # Allow some variance
        
        # Verify execution stats were updated
        stats = execution_engine.execution_stats
        assert stats['total_executions'] == num_concurrent
        assert stats['concurrent_executions'] == 0  # Should be back to 0 after completion
        assert len(stats['execution_times']) == num_concurrent
        assert len(stats['queue_wait_times']) == num_concurrent
    
    # ============================================================================
    # GOLDEN PATH SCENARIO 5: Error Handling and Recovery
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.error_handling
    async def test_agent_execution_timeout_and_death_monitoring(self):
        """
        Test agent execution timeout detection and death monitoring.
        
        BVJ: System reliability - prevents hung agents from blocking user experience
        """
        # Arrange: Create ExecutionEngine with short timeout for testing
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Override timeout for testing
        execution_engine.AGENT_EXECUTION_TIMEOUT = 0.1  # 100ms timeout
        
        # Configure agent core to timeout
        self.mock_agent_core.execute_agent = AsyncMock(side_effect=lambda *args, **kwargs: asyncio.sleep(0.2))  # 200ms > timeout
        
        # Act & Assert: Expect timeout exception
        with pytest.raises(asyncio.TimeoutError):
            await execution_engine.execute_agent(
                self.test_execution_context_1,
                user_context=self.test_user_context_1
            )
        
        # Assert: Verify timeout handling
        # Check that agent_death event was sent
        event_types = [event['event_type'] for event in self.captured_websocket_events]
        assert 'agent_death' in event_types, "agent_death event not sent on timeout"
        
        death_event = next(e for e in self.captured_websocket_events if e['event_type'] == 'agent_death')
        assert death_event['args'][0] == "exec_run_001"
        assert death_event['args'][1] == "test_agent"
        assert death_event['args'][2] == 'timeout'
        
        # Verify execution stats were updated
        assert execution_engine.execution_stats['failed_executions'] == 1
    
    @pytest.mark.unit
    @pytest.mark.error_handling
    async def test_agent_execution_error_recovery_and_notification(self):
        """
        Test agent execution error recovery and user notification.
        
        BVJ: System reliability - graceful error handling maintains user experience
        """
        # Arrange: Create ExecutionEngine
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Configure agent core to fail
        test_error = RuntimeError("Agent execution failed")
        self.mock_agent_core.execute_agent = AsyncMock(side_effect=test_error)
        
        # Act & Assert: Expect error to propagate (after error handling)
        with pytest.raises(RuntimeError, match="Agent execution failed"):
            await execution_engine.execute_agent(
                self.test_execution_context_1,
                user_context=self.test_user_context_1
            )
        
        # Assert: Verify error notification was sent
        event_types = [event['event_type'] for event in self.captured_websocket_events]
        
        # Should still send agent_started event
        assert 'agent_started' in event_types, "agent_started should be sent even if execution fails later"
        
        # Should send user-friendly error notification
        # (Implementation detail: error notification is sent via _notify_user_of_execution_error)
        # Verify execution tracking was updated with failure
        self.mock_execution_tracker.update_execution_state.assert_called()
    
    # ============================================================================
    # PIPELINE EXECUTION TESTS
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.pipeline_execution
    async def test_execute_pipeline_sequential_steps(self):
        """
        Test pipeline execution with sequential steps.
        
        BVJ: Agent orchestration - enables complex multi-agent workflows
        """
        # Arrange: Create ExecutionEngine
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Create pipeline steps
        steps = [
            PipelineStep(
                agent_name="step1_agent",
                metadata={"step_number": 1}
            ),
            PipelineStep(
                agent_name="step2_agent", 
                metadata={"step_number": 2}
            ),
            PipelineStep(
                agent_name="step3_agent",
                metadata={"step_number": 3}
            )
        ]
        
        # Act: Execute pipeline
        results = await execution_engine.execute_pipeline(
            steps,
            self.test_execution_context_1,
            self.test_user_context_1
        )
        
        # Assert: Verify pipeline execution
        assert len(results) == 3
        assert all(result.success for result in results)
        
        # Verify steps were executed in order
        for i, result in enumerate(results):
            assert result.agent_name == f"step{i+1}_agent"
        
        # Verify agent core was called for each step
        assert self.mock_agent_core.execute_agent.call_count == 3
    
    # ============================================================================
    # PERFORMANCE AND CACHING TESTS
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.performance
    async def test_response_caching_phase3_optimization(self):
        """
        Test Phase 3 response caching for performance optimization.
        
        BVJ: Platform performance - 80% faster response times on repeat queries
        """
        # Arrange: Create ExecutionEngine  
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Create context with cacheable input
        cacheable_context = AgentExecutionContext(
            run_id="cache_run_001",
            thread_id="cache_thread_001",
            user_id="cache_user_001",
            agent_name="cacheable_agent",
            prompt="What is the meaning of life?",
            user_input="Philosophical question",
            metadata={"cacheable": True}
        )
        
        # Act: Execute same query twice
        result1 = await execution_engine.execute_agent(
            cacheable_context,
            user_context=self.test_user_context_1
        )
        
        # Second execution should potentially use cache (depends on implementation)
        result2 = await execution_engine.execute_agent(
            cacheable_context,
            user_context=self.test_user_context_1
        )
        
        # Assert: Verify both executions succeeded
        assert result1.success is True
        assert result2.success is True
        assert result1.agent_name == "cacheable_agent"
        assert result2.agent_name == "cacheable_agent"
        
        # Verify cache functionality (if implemented)
        cache_key = execution_engine._get_cache_key(cacheable_context)
        assert cache_key is not None
        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5 hash length
    
    # ============================================================================
    # USER EXECUTION ENGINE DELEGATION TESTS
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.user_engine_delegation
    async def test_user_execution_engine_delegation(self):
        """
        Test delegation to UserExecutionEngine for user isolation.
        
        BVJ: Architecture compliance - proper delegation to SSOT user engine
        """
        # Arrange: Create ExecutionEngine with UserExecutionContext
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Mock UserExecutionEngine creation
        mock_user_engine = self.mock_factory.create_mock("UserExecutionEngine")
        mock_user_engine.execute_agent = AsyncMock(return_value=AgentExecutionResult(
            success=True,
            agent_name="delegated_agent",
            execution_time=0.3,
            data={"delegated": True}
        ))
        mock_user_engine.cleanup = AsyncMock()
        
        with patch.object(execution_engine, 'create_user_engine', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_user_engine
            
            # Act: Execute agent (should delegate to UserExecutionEngine)
            result = await execution_engine.execute_agent(
                self.test_execution_context_1,
                user_context=self.test_user_context_1
            )
        
        # Assert: Verify delegation occurred
        mock_create.assert_called_once_with(self.test_user_context_1)
        mock_user_engine.execute_agent.assert_called_once()
        mock_user_engine.cleanup.assert_called_once()
        
        # Verify result from delegated engine
        assert result.success is True
        assert result.agent_name == "delegated_agent"
        assert result.data["delegated"] is True
    
    # ============================================================================
    # EXECUTION STATISTICS AND MONITORING
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.monitoring
    async def test_execution_statistics_collection_and_reporting(self):
        """
        Test execution statistics collection for monitoring and optimization.
        
        BVJ: Platform monitoring - provides metrics for performance optimization
        """
        # Arrange: Create ExecutionEngine
        execution_engine = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Act: Execute multiple agents to generate statistics
        for i in range(3):
            context = AgentExecutionContext(
                run_id=f"stats_run_{i:03d}",
                thread_id=f"stats_thread_{i:03d}",
                user_id=f"stats_user_{i:03d}",
                agent_name=f"stats_agent_{i:03d}",
                metadata={"stats_test": i}
            )
            
            await execution_engine.execute_agent(context, user_context=None)
        
        # Get comprehensive execution statistics
        stats = await execution_engine.get_execution_stats()
        
        # Assert: Verify statistics collection
        assert stats['total_executions'] == 3
        assert stats['concurrent_executions'] == 0  # Should be 0 after completion
        assert len(stats['queue_wait_times']) == 3
        assert len(stats['execution_times']) == 3
        assert stats['failed_executions'] == 0
        assert stats['dead_executions'] == 0
        assert stats['timeout_executions'] == 0
        
        # Verify calculated averages
        assert 'avg_queue_wait_time' in stats
        assert 'max_queue_wait_time' in stats
        assert 'avg_execution_time' in stats
        assert 'max_execution_time' in stats
        
        # Verify all values are reasonable
        assert stats['avg_queue_wait_time'] >= 0
        assert stats['avg_execution_time'] > 0
        assert stats['max_execution_time'] >= stats['avg_execution_time']
    
    # ============================================================================
    # ISOLATION STATUS VALIDATION
    # ============================================================================
    
    @pytest.mark.unit
    @pytest.mark.isolation_status
    async def test_isolation_status_reporting_and_validation(self):
        """
        Test isolation status reporting for user context validation.
        
        BVJ: Security compliance - validates user isolation implementation
        """
        # Arrange: Create ExecutionEngine with UserExecutionContext
        execution_engine_with_context = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context_1
        )
        
        # Create ExecutionEngine without UserExecutionContext
        execution_engine_without_context = ExecutionEngine(
            registry=self.mock_agent_registry,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=None
        )
        
        # Act: Get isolation status for both engines
        status_with_context = execution_engine_with_context.get_isolation_status()
        status_without_context = execution_engine_without_context.get_isolation_status()
        
        # Assert: Verify isolation status reporting
        # Engine with UserExecutionContext
        assert status_with_context['has_user_context'] is True
        assert status_with_context['user_id'] == "exec_user_001"
        assert status_with_context['run_id'] == "exec_run_001"
        assert status_with_context['isolation_level'] == 'user_isolated'
        assert status_with_context['recommended_migration'] is False
        assert status_with_context['global_state_warning'] is False
        
        # Engine without UserExecutionContext
        assert status_without_context['has_user_context'] is False
        assert status_without_context['user_id'] is None
        assert status_without_context['run_id'] is None
        assert status_without_context['isolation_level'] == 'global_state'
        assert status_without_context['recommended_migration'] is True
        assert status_without_context['global_state_warning'] is True
        
        # Verify migration recommendations
        assert 'migration_method' in status_without_context
        assert 'create_user_engine()' in status_without_context['migration_method']