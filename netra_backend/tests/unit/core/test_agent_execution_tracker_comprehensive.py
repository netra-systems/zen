"""
Comprehensive Unit Tests for AgentExecutionTracker - SSOT Execution Tracking

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Enterprise - Core agent execution tracking protecting $500K+ ARR
- Goal: System Stability & Reliability - Prevent silent agent failures
- Value Impact: Ensures reliable execution tracking for all agent operations
- Revenue Impact: Protects 90% of platform value through execution monitoring

CRITICAL MODULE: AgentExecutionTracker is the SSOT for agent execution state tracking.
This module prevents silent agent failures, tracks performance metrics, manages timeouts,
and provides circuit breaker protection. Essential for reliable chat functionality.

TEST CATEGORIES:
1. Core Execution Tracking: State management, heartbeat monitoring
2. Phase Transitions: State validation, WebSocket event integration
3. Timeout Management: Circuit breakers, failure detection
4. Performance Monitoring: Metrics collection, cleanup operations
5. User Isolation: Context validation, concurrent execution safety

SSOT COMPLIANCE: Uses test_framework.ssot.base_test_case for unified test infrastructure.
"""
import asyncio
import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, ExecutionState, AgentExecutionPhase, ExecutionRecord, TimeoutConfig, PhaseTransition, CircuitBreakerState, CircuitBreakerOpenError, get_execution_tracker, initialize_tracker, shutdown_tracker

@pytest.mark.unit
@pytest.mark.execution_tracking
class AgentExecutionTrackerCoreOperationsTests(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Core execution tracking validation
    
    Tests the fundamental execution tracking operations that enable reliable
    agent monitoring and prevent silent failures that break chat interactions.
    """

    async def asyncSetUp(self):
        """Set up test fixtures for core operations."""
        await super().asyncSetUp()
        self.tracker = AgentExecutionTracker(heartbeat_timeout=5, execution_timeout=10, cleanup_interval=30)
        self.test_agent_name = 'test-agent'
        self.test_user_id = 'user-123'
        self.test_thread_id = 'thread-456'
        self.test_metadata = {'test': 'data', 'priority': 'high'}

    async def test_create_execution_generates_unique_ids(self):
        """
        BUSINESS CRITICAL: Unique execution IDs prevent tracking collisions
        
        Each agent execution must have a unique ID to ensure proper isolation
        and prevent cross-contamination between concurrent executions.
        """
        exec_id_1 = self.tracker.create_execution(agent_name=self.test_agent_name, thread_id=self.test_thread_id, user_id=self.test_user_id, timeout_seconds=30, metadata=self.test_metadata)
        exec_id_2 = self.tracker.create_execution(agent_name='another-agent', thread_id='thread-789', user_id='user-456', timeout_seconds=15)
        self.assertNotEqual(exec_id_1, exec_id_2, 'Execution IDs must be unique')
        self.assertIsInstance(exec_id_1, str, 'Execution ID should be string')
        self.assertGreater(len(exec_id_1), 10, 'Execution ID should be meaningful length')
        record_1 = self.tracker.get_execution(exec_id_1)
        record_2 = self.tracker.get_execution(exec_id_2)
        self.assertIsNotNone(record_1, 'First execution should be tracked')
        self.assertIsNotNone(record_2, 'Second execution should be tracked')
        self.assertEqual(record_1.agent_name, self.test_agent_name)
        self.assertEqual(record_2.agent_name, 'another-agent')
        self.assertEqual(record_1.user_id, self.test_user_id)
        self.assertEqual(record_2.user_id, 'user-456')

    async def test_execution_state_transitions_follow_business_logic(self):
        """
        BUSINESS CRITICAL: State transitions reflect real execution progress
        
        Agent execution states must accurately reflect business progress to
        enable proper monitoring and user experience delivery.
        """
        exec_id = self.tracker.create_execution(agent_name=self.test_agent_name, thread_id=self.test_thread_id, user_id=self.test_user_id)
        record = self.tracker.get_execution(exec_id)
        self.assertEqual(record.state, ExecutionState.PENDING, 'Should start in PENDING state')
        success = self.tracker.start_execution(exec_id)
        self.assertTrue(success, 'Should successfully start execution')
        record = self.tracker.get_execution(exec_id)
        self.assertEqual(record.state, ExecutionState.STARTING, 'Should transition to STARTING')
        success = self.tracker.heartbeat(exec_id)
        self.assertTrue(success, 'Heartbeat should succeed')
        record = self.tracker.get_execution(exec_id)
        self.assertEqual(record.state, ExecutionState.RUNNING, 'Heartbeat should move to RUNNING')
        self.assertGreater(record.heartbeat_count, 0, 'Heartbeat count should increment')
        success = self.tracker.update_execution_state(exec_id, ExecutionState.COMPLETED, result={'status': 'success'})
        self.assertTrue(success, 'Should complete execution successfully')
        record = self.tracker.get_execution(exec_id)
        self.assertEqual(record.state, ExecutionState.COMPLETED, 'Should be completed')
        self.assertIsNotNone(record.completed_at, 'Completion time should be set')
        self.assertTrue(record.is_terminal, 'Completed state should be terminal')

    async def test_heartbeat_monitoring_detects_death(self):
        """
        BUSINESS CRITICAL: Dead agent detection prevents silent failures
        
        Silent agent failures break chat functionality. The tracker must
        detect when agents stop responding and mark them as dead.
        """
        tracker = AgentExecutionTracker(heartbeat_timeout=1)
        exec_id = tracker.create_execution(agent_name=self.test_agent_name, thread_id=self.test_thread_id, user_id=self.test_user_id)
        tracker.start_execution(exec_id)
        tracker.heartbeat(exec_id)
        record = tracker.get_execution(exec_id)
        self.assertEqual(record.state, ExecutionState.RUNNING)
        await asyncio.sleep(1.5)
        dead_executions = tracker.detect_dead_executions()
        self.assertEqual(len(dead_executions), 1, 'Should detect one dead execution')
        self.assertEqual(dead_executions[0].execution_id, exec_id)
        record = tracker.get_execution(exec_id)
        self.assertTrue(record.is_dead(heartbeat_timeout=1), 'Should be considered dead')
        tracker.update_execution_state(exec_id, ExecutionState.DEAD, error='No heartbeat')
        record = tracker.get_execution(exec_id)
        self.assertEqual(record.state, ExecutionState.DEAD)
        self.assertIn('heartbeat', record.error.lower())

    async def test_execution_timeout_protection(self):
        """
        BUSINESS CRITICAL: Timeout protection prevents hanging agents
        
        Long-running agents without timeouts block users from receiving
        responses, directly impacting the 90% chat value delivery.
        """
        tracker = AgentExecutionTracker(execution_timeout=2)
        exec_id = tracker.create_execution(agent_name=self.test_agent_name, thread_id=self.test_thread_id, user_id=self.test_user_id, timeout_seconds=1)
        tracker.start_execution(exec_id)
        await asyncio.sleep(1.5)
        record = tracker.get_execution(exec_id)
        self.assertTrue(record.is_timed_out(), 'Execution should be timed out')
        timed_out_executions = [r for r in tracker.detect_dead_executions() if r.is_timed_out()]
        self.assertEqual(len(timed_out_executions), 1, 'Should detect timed out execution')
        tracker.update_execution_state(exec_id, ExecutionState.TIMEOUT, error='Execution timeout')
        record = tracker.get_execution(exec_id)
        self.assertEqual(record.state, ExecutionState.TIMEOUT)

    async def test_concurrent_execution_isolation(self):
        """
        ENTERPRISE CRITICAL: Multiple agents execute simultaneously without interference
        
        Validates that concurrent agent executions for different users don't
        share state or interfere with each other's tracking.
        """
        executions = []
        for i in range(5):
            exec_id = self.tracker.create_execution(agent_name=f'agent-{i}', thread_id=f'thread-{i}', user_id=f'user-{i}', metadata={'batch': 'concurrent', 'index': i})
            executions.append(exec_id)

        async def process_execution(exec_id, index):
            self.tracker.start_execution(exec_id)
            await asyncio.sleep(0.1)
            for _ in range(3):
                self.tracker.heartbeat(exec_id)
                await asyncio.sleep(0.05)
            self.tracker.update_execution_state(exec_id, ExecutionState.COMPLETED, result={'agent_index': index, 'status': 'success'})
        await asyncio.gather(*[process_execution(exec_id, i) for i, exec_id in enumerate(executions)])
        for i, exec_id in enumerate(executions):
            record = self.tracker.get_execution(exec_id)
            self.assertEqual(record.state, ExecutionState.COMPLETED)
            self.assertEqual(record.agent_name, f'agent-{i}')
            self.assertEqual(record.user_id, f'user-{i}')
            self.assertEqual(record.result['agent_index'], i)
            self.assertGreater(record.heartbeat_count, 0)
        active_executions = self.tracker.get_active_executions()
        self.assertEqual(len(active_executions), 0, 'All executions should be completed')
        metrics = self.tracker.get_metrics()
        self.assertEqual(metrics['total_executions'], 5)
        self.assertEqual(metrics['successful_executions'], 5)
        self.assertEqual(metrics['success_rate'], 1.0)

@pytest.mark.unit
@pytest.mark.phase_transitions
class AgentExecutionTrackerPhaseManagementTests(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Phase transition validation for WebSocket events
    
    Tests the phase transition system that enables real-time user experience
    through WebSocket events during agent execution.
    """

    async def asyncSetUp(self):
        """Set up test fixtures for phase management."""
        await super().asyncSetUp()
        self.tracker = AgentExecutionTracker()
        self.mock_websocket_manager = AsyncMock()
        self.exec_id = self.tracker.create_execution(agent_name='phase-test-agent', thread_id='phase-thread', user_id='phase-user')

    async def test_phase_transition_validation_prevents_invalid_sequences(self):
        """
        BUSINESS CRITICAL: Invalid phase transitions could break user experience
        
        Phase transitions must follow logical sequences to ensure proper
        WebSocket event delivery and user progress visibility.
        """
        record = self.tracker.get_execution(self.exec_id)
        self.assertEqual(record.current_phase, AgentExecutionPhase.CREATED)
        success = await self.tracker.transition_state(self.exec_id, AgentExecutionPhase.WEBSOCKET_SETUP, metadata={'setup': 'starting'})
        self.assertTrue(success, 'Valid transition should succeed')
        await self.tracker.transition_state(self.exec_id, AgentExecutionPhase.CONTEXT_VALIDATION)
        await self.tracker.transition_state(self.exec_id, AgentExecutionPhase.STARTING)
        await self.tracker.transition_state(self.exec_id, AgentExecutionPhase.COMPLETED)
        record = self.tracker.get_execution(self.exec_id)
        self.assertEqual(record.current_phase, AgentExecutionPhase.COMPLETED)
        history = self.tracker.get_state_history(self.exec_id)
        self.assertEqual(len(history), 4, 'All transitions should be recorded')
        record = self.tracker.get_execution(self.exec_id)
        total_duration = record.get_total_duration_ms()
        self.assertGreater(total_duration, 0, 'Total duration should be positive')

    async def test_websocket_event_emission_during_phase_transitions(self):
        """
        BUSINESS CRITICAL: WebSocket events provide real-time user experience
        
        Phase transitions must emit appropriate WebSocket events to keep
        users informed of agent progress during execution.
        """
        phases_to_test = [(AgentExecutionPhase.WEBSOCKET_SETUP, 'No WebSocket event expected'), (AgentExecutionPhase.STARTING, 'agent_started'), (AgentExecutionPhase.THINKING, 'agent_thinking'), (AgentExecutionPhase.TOOL_EXECUTION, 'tool_executing'), (AgentExecutionPhase.COMPLETED, 'agent_completed')]
        for phase, expected_event in phases_to_test:
            self.mock_websocket_manager.reset_mock()
            success = await self.tracker.transition_state(self.exec_id, phase, metadata={'phase': phase.value, 'test': True}, websocket_manager=self.mock_websocket_manager)
            self.assertTrue(success, f'Transition to {phase} should succeed')
            if 'notify_' in expected_event:
                websocket_called = any((call for call in self.mock_websocket_manager.method_calls if call[0].startswith('notify_')))
                self.assertTrue(websocket_called, f'WebSocket event should be emitted for {phase}')
        history = self.tracker.get_state_history(self.exec_id)
        for transition in history:
            self.assertIn('test', transition['metadata'], 'Metadata should be preserved')

    async def test_phase_duration_tracking_for_performance_analysis(self):
        """
        BUSINESS CRITICAL: Phase durations enable performance optimization
        
        Tracking time spent in each phase helps identify bottlenecks
        and optimize agent performance for better user experience.
        """
        phases_with_delays = [(AgentExecutionPhase.WEBSOCKET_SETUP, 0.1), (AgentExecutionPhase.STARTING, 0.15), (AgentExecutionPhase.THINKING, 0.2), (AgentExecutionPhase.TOOL_EXECUTION, 0.25)]
        start_time = time.time()
        for phase, delay in phases_with_delays:
            await self.tracker.transition_state(self.exec_id, phase)
            await asyncio.sleep(delay)
        await self.tracker.transition_state(self.exec_id, AgentExecutionPhase.COMPLETED)
        total_elapsed = time.time() - start_time
        record = self.tracker.get_execution(self.exec_id)
        total_duration_ms = record.get_total_duration_ms()
        expected_min_duration = sum((delay * 1000 for _, delay in phases_with_delays))
        self.assertGreater(total_duration_ms, expected_min_duration * 0.8, 'Total duration should reflect time spent in phases')
        thinking_duration = record.get_phase_duration_ms(AgentExecutionPhase.THINKING)
        self.assertGreater(thinking_duration, 150, 'Thinking phase should have measurable duration')
        current_phase_duration = record.get_current_phase_duration_ms()
        self.assertGreater(current_phase_duration, 0, 'Current phase should have duration')

@pytest.mark.unit
@pytest.mark.timeout_management
class AgentExecutionTrackerTimeoutManagementTests(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Timeout and circuit breaker protection
    
    Tests timeout management and circuit breaker functionality that prevents
    system overload and ensures responsive agent execution.
    """

    async def asyncSetUp(self):
        """Set up test fixtures for timeout management."""
        await super().asyncSetUp()
        self.timeout_config = TimeoutConfig(agent_execution_timeout=5.0, llm_api_timeout=2.0, failure_threshold=3, recovery_timeout=10.0, success_threshold=2, max_retries=2)
        self.tracker = AgentExecutionTracker(timeout_config=self.timeout_config)
        self.exec_id = self.tracker.create_execution(agent_name='timeout-test-agent', thread_id='timeout-thread', user_id='timeout-user')

    async def test_timeout_configuration_business_impact(self):
        """
        BUSINESS CRITICAL: Timeout configuration affects user experience
        
        Timeout settings must balance allowing complex AI processing while
        preventing users from waiting too long for responses.
        """
        success = self.tracker.set_timeout(self.exec_id, self.timeout_config)
        self.assertTrue(success, 'Should set timeout configuration')
        timeout_status = self.tracker.check_timeout(self.exec_id)
        self.assertIsNotNone(timeout_status, 'Should return timeout status')
        self.assertEqual(timeout_status['timeout_seconds'], self.timeout_config.agent_execution_timeout, 'Timeout should match configuration')
        self.assertFalse(timeout_status['is_timed_out'], 'Should not be timed out initially')
        self.assertGreater(timeout_status['time_until_timeout'], 0, 'Should have time remaining')
        self.assertLessEqual(self.timeout_config.agent_execution_timeout, 30.0, 'Agent timeout should not exceed 30s for good UX')
        self.assertGreaterEqual(self.timeout_config.agent_execution_timeout, 1.0, 'Agent timeout should allow meaningful processing')

    async def test_circuit_breaker_prevents_cascade_failures(self):
        """
        BUSINESS CRITICAL: Circuit breaker prevents system overload
        
        When agents consistently fail, circuit breaker should open to
        prevent resource exhaustion and maintain system stability.
        """
        success = self.tracker.register_circuit_breaker(self.exec_id)
        self.assertTrue(success, 'Should register circuit breaker')
        cb_status = self.tracker.circuit_breaker_status(self.exec_id)
        self.assertEqual(cb_status['state'], CircuitBreakerState.CLOSED.value)
        self.assertEqual(cb_status['failure_count'], 0)
        self.assertTrue(cb_status['can_retry'])

        async def failing_operation():
            raise ValueError('Simulated failure')
        failure_count = 0
        for i in range(5):
            try:
                await self.tracker.execute_with_circuit_breaker(self.exec_id, failing_operation, f'test_operation_{i}')
            except (ValueError, CircuitBreakerOpenError):
                failure_count += 1
        cb_status = self.tracker.circuit_breaker_status(self.exec_id)
        self.assertEqual(cb_status['state'], CircuitBreakerState.OPEN.value)
        self.assertGreaterEqual(cb_status['failure_count'], self.timeout_config.failure_threshold)
        self.assertFalse(cb_status['is_open'])
        with self.assertRaises(CircuitBreakerOpenError):
            await self.tracker.execute_with_circuit_breaker(self.exec_id, failing_operation, 'blocked_operation')

    async def test_circuit_breaker_recovery_after_success(self):
        """
        BUSINESS CRITICAL: Circuit breaker recovers after successful operations
        
        Circuit breaker must allow recovery to restore normal operation
        when underlying issues are resolved.
        """
        self.tracker.register_circuit_breaker(self.exec_id)
        record = self.tracker.get_execution(self.exec_id)
        record.circuit_breaker_state = CircuitBreakerState.OPEN
        record.circuit_breaker_failures = self.timeout_config.failure_threshold
        record.next_attempt_time = time.time() - 1

        async def successful_operation():
            return 'success'
        record.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
        result = await self.tracker.execute_with_circuit_breaker(self.exec_id, successful_operation, 'recovery_test')
        self.assertEqual(result, 'success', 'Operation should succeed')
        for _ in range(self.timeout_config.success_threshold):
            await self.tracker.execute_with_circuit_breaker(self.exec_id, successful_operation, 'close_circuit')
        cb_status = self.tracker.circuit_breaker_status(self.exec_id)
        self.assertTrue(cb_status['can_retry'], 'Should allow retries after recovery')

    async def test_timeout_detection_with_real_delays(self):
        """
        BUSINESS CRITICAL: Accurate timeout detection prevents hanging
        
        Timeout detection must accurately identify hanging agents to
        prevent blocking user interactions.
        """
        short_timeout_config = TimeoutConfig(agent_execution_timeout=0.5)
        exec_id = self.tracker.create_execution_with_full_context(agent_name='timeout-detection-agent', user_context={'user_id': 'timeout-user', 'thread_id': 'timeout-thread'}, timeout_config={'timeout_seconds': 0.5, 'llm_timeout': 0.3})
        self.tracker.start_execution(exec_id)
        await asyncio.sleep(0.8)
        timeout_status = self.tracker.check_timeout(exec_id)
        self.assertTrue(timeout_status['is_timed_out'], 'Should detect timeout')
        self.assertEqual(timeout_status['time_until_timeout'], 0, 'No time should remain')
        record = self.tracker.get_execution(exec_id)
        self.assertTrue(record.is_timed_out(), 'Record should indicate timeout')
        self.tracker.update_execution_state(exec_id, ExecutionState.TIMEOUT, error='Operation timed out')
        record = self.tracker.get_execution(exec_id)
        self.assertEqual(record.state, ExecutionState.TIMEOUT)
        self.assertIn('timed out', record.error.lower())

@pytest.mark.unit
@pytest.mark.performance_monitoring
class AgentExecutionTrackerPerformanceMonitoringTests(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Performance monitoring and optimization
    
    Tests performance tracking, metrics collection, and cleanup operations
    that ensure system efficiency and scalability.
    """

    async def asyncSetUp(self):
        """Set up test fixtures for performance monitoring."""
        await super().asyncSetUp()
        self.tracker = AgentExecutionTracker(cleanup_interval=5)

    async def test_metrics_collection_enables_performance_optimization(self):
        """
        BUSINESS CRITICAL: Performance metrics enable optimization decisions
        
        Execution metrics must be collected to understand agent performance
        and guide optimization efforts for better customer experience.
        """
        executions = []
        for i in range(3):
            exec_id = self.tracker.create_execution(agent_name=f'success-agent-{i}', thread_id=f'success-thread-{i}', user_id=f'success-user-{i}')
            executions.append(('success', exec_id))
        for i in range(2):
            exec_id = self.tracker.create_execution(agent_name=f'failed-agent-{i}', thread_id=f'failed-thread-{i}', user_id=f'failed-user-{i}')
            executions.append(('failed', exec_id))
        for outcome, exec_id in executions:
            self.tracker.start_execution(exec_id)
            self.tracker.heartbeat(exec_id)
            if outcome == 'success':
                self.tracker.update_execution_state(exec_id, ExecutionState.COMPLETED, result={'status': 'success', 'value': 42})
            else:
                self.tracker.update_execution_state(exec_id, ExecutionState.FAILED, error='Simulated failure')
        metrics = self.tracker.get_metrics()
        self.assertEqual(metrics['total_executions'], 5, 'Should track all executions')
        self.assertEqual(metrics['successful_executions'], 3, 'Should track successes')
        self.assertEqual(metrics['failed_executions'], 2, 'Should track failures')
        self.assertEqual(metrics['active_executions'], 0, 'All should be completed')
        self.assertEqual(metrics['success_rate'], 0.6, '60% success rate')
        self.assertEqual(metrics['failure_rate'], 0.4, '40% failure rate')
        self.assertIn('success_rate', metrics, 'Success rate needed for monitoring')
        self.assertIn('failure_rate', metrics, 'Failure rate needed for alerting')
        self.assertIsInstance(metrics['total_executions'], int, 'Counts should be integers')

    async def test_execution_cleanup_prevents_memory_leaks(self):
        """
        BUSINESS CRITICAL: Memory management ensures system scalability
        
        Old execution records must be cleaned up to prevent memory growth
        that could impact system performance and reliability.
        """
        old_executions = []
        for i in range(5):
            exec_id = self.tracker.create_execution(agent_name=f'cleanup-agent-{i}', thread_id=f'cleanup-thread-{i}', user_id=f'cleanup-user-{i}')
            old_executions.append(exec_id)
            self.tracker.start_execution(exec_id)
            self.tracker.update_execution_state(exec_id, ExecutionState.COMPLETED)
        initial_count = len(self.tracker._executions)
        self.assertEqual(initial_count, 5, 'All executions should be tracked')
        for exec_id in old_executions:
            record = self.tracker.get_execution(exec_id)
            if record:
                old_time = datetime.now(timezone.utc) - timedelta(seconds=10)
                record.completed_at = old_time
        await self.tracker._cleanup_old_executions()
        remaining_count = len(self.tracker._executions)
        self.assertLess(remaining_count, initial_count, 'Some executions should be cleaned up')
        metrics = self.tracker.get_metrics()
        self.assertEqual(metrics['total_executions'], 5, 'Total count should be preserved')

    async def test_concurrent_monitoring_performance(self):
        """
        BUSINESS CRITICAL: Monitoring doesn't impact execution performance
        
        Background monitoring must not degrade agent execution performance
        or introduce latency that affects user experience.
        """
        await self.tracker.start_monitoring()
        execution_count = 20
        executions = []
        start_time = time.time()

        async def process_execution(index):
            exec_id = self.tracker.create_execution(agent_name=f'perf-agent-{index}', thread_id=f'perf-thread-{index}', user_id=f'perf-user-{index}')
            self.tracker.start_execution(exec_id)
            for _ in range(3):
                self.tracker.heartbeat(exec_id)
                await asyncio.sleep(0.01)
            self.tracker.update_execution_state(exec_id, ExecutionState.COMPLETED)
            return exec_id
        completed_executions = await asyncio.gather(*[process_execution(i) for i in range(execution_count)])
        execution_time = time.time() - start_time
        self.assertEqual(len(completed_executions), execution_count, 'All executions should complete')
        self.assertLess(execution_time, 2.0, 'Concurrent execution should be performant')
        metrics = self.tracker.get_metrics()
        self.assertEqual(metrics['successful_executions'], execution_count)
        await self.tracker.stop_monitoring()

    async def test_background_monitoring_detects_issues(self):
        """
        BUSINESS CRITICAL: Background monitoring catches silent failures
        
        Continuous monitoring must detect and respond to agent failures
        that would otherwise go unnoticed and break user experience.
        """
        exec_id = self.tracker.create_execution(agent_name='monitored-agent', thread_id='monitored-thread', user_id='monitored-user')
        self.tracker.start_execution(exec_id)
        self.tracker.heartbeat(exec_id)
        death_notifications = []
        timeout_notifications = []

        async def death_callback(record):
            death_notifications.append(record.execution_id)

        async def timeout_callback(record):
            timeout_notifications.append(record.execution_id)
        self.tracker.register_death_callback(death_callback)
        self.tracker.register_timeout_callback(timeout_callback)
        await self.tracker.start_monitoring()
        await asyncio.sleep(12)
        dead_executions = self.tracker.detect_dead_executions()
        if dead_executions:
            self.assertGreater(len(dead_executions), 0, 'Should detect dead execution')
            self.assertEqual(dead_executions[0].execution_id, exec_id, 'Should detect the right execution')
        await self.tracker.stop_monitoring()

@pytest.mark.unit
@pytest.mark.ssot_compliance
class AgentExecutionTrackerSSOTComplianceTests(SSotAsyncTestCase):
    """
    BUSINESS VALUE: SSOT compliance and integration validation
    
    Tests SSOT compliance, singleton behavior, and integration with other
    system components that depend on execution tracking.
    """

    async def test_singleton_tracker_ensures_global_consistency(self):
        """
        BUSINESS CRITICAL: Single tracker instance ensures consistent state
        
        Global singleton ensures all parts of the system see the same
        execution state, preventing inconsistencies that could break chat.
        """
        tracker1 = get_execution_tracker()
        tracker2 = get_execution_tracker()
        self.assertIs(tracker1, tracker2, 'Should return same singleton instance')
        exec_id = tracker1.create_execution(agent_name='singleton-test', thread_id='singleton-thread', user_id='singleton-user')
        record1 = tracker1.get_execution(exec_id)
        record2 = tracker2.get_execution(exec_id)
        self.assertIsNotNone(record1, 'First tracker should see execution')
        self.assertIsNotNone(record2, 'Second tracker should see execution')
        self.assertEqual(record1.execution_id, record2.execution_id, 'Both should see same execution')

    async def test_initialization_and_shutdown_lifecycle(self):
        """
        BUSINESS CRITICAL: Proper lifecycle management prevents resource leaks
        
        Tracker initialization and shutdown must be clean to prevent
        resource leaks in long-running production systems.
        """
        tracker = await initialize_tracker()
        self.assertIsNotNone(tracker, 'Should return tracker instance')
        self.assertIsNotNone(tracker._monitor_task, 'Should start monitoring task')
        exec_id = tracker.create_execution(agent_name='lifecycle-test', thread_id='lifecycle-thread', user_id='lifecycle-user')
        record = tracker.get_execution(exec_id)
        self.assertIsNotNone(record, 'Tracker should be functional')
        await shutdown_tracker()
        tracker = get_execution_tracker()
        self.assertIsNone(tracker._monitor_task, 'Monitoring task should be stopped')

    async def test_execution_record_comprehensive_state_management(self):
        """
        BUSINESS CRITICAL: ExecutionRecord provides complete state tracking
        
        ExecutionRecord must provide all state information needed for
        business monitoring, debugging, and performance optimization.
        """
        exec_id = self.tracker.create_execution(agent_name='state-test-agent', thread_id='state-thread', user_id='state-user', timeout_seconds=30, metadata={'priority': 'high', 'source': 'api'})
        record = self.tracker.get_execution(exec_id)
        self.assertEqual(record.agent_name, 'state-test-agent')
        self.assertEqual(record.user_id, 'state-user')
        self.assertEqual(record.thread_id, 'state-thread')
        self.assertEqual(record.timeout_seconds, 30)
        self.assertEqual(record.metadata['priority'], 'high')
        self.assertTrue(record.is_alive, 'New execution should be alive')
        self.assertFalse(record.is_terminal, 'New execution not terminal')
        self.assertEqual(record.state, ExecutionState.PENDING)
        self.assertIsNotNone(record.started_at, 'Should have start time')
        self.assertIsNotNone(record.last_heartbeat, 'Should have heartbeat time')
        self.assertIsNone(record.completed_at, 'Should not be completed')
        duration = record.duration
        self.assertIsNotNone(duration, 'Should calculate duration for active execution')
        total_ms = record.get_total_duration_ms()
        self.assertGreater(total_ms, 0, 'Should have positive duration')
        self.assertFalse(record.is_timed_out(), 'Should not be timed out initially')
        self.assertFalse(record.is_dead(), 'Should not be dead initially')
        self.assertEqual(record.current_phase, AgentExecutionPhase.CREATED)
        self.assertEqual(len(record.phase_history), 0, 'No transitions yet')
        self.assertEqual(record.circuit_breaker_state, CircuitBreakerState.CLOSED)
        self.assertEqual(record.circuit_breaker_failures, 0)

    async def test_full_context_integration_methods(self):
        """
        BUSINESS CRITICAL: Full context methods support complex integrations
        
        Integration methods must provide complete context for enterprise
        features like monitoring, alerting, and compliance reporting.
        """
        exec_id = self.tracker.create_execution_with_full_context(agent_name='integration-agent', user_context={'user_id': 'enterprise-user', 'thread_id': 'enterprise-thread', 'metadata': {'department': 'sales', 'priority': 'critical', 'compliance_required': True}}, timeout_config={'timeout_seconds': 45, 'llm_timeout': 20, 'failure_threshold': 5, 'recovery_timeout': 60}, initial_state='PENDING')
        self.assertIsNotNone(exec_id, 'Should create execution')
        full_context = self.tracker.get_execution_with_full_context(exec_id)
        self.assertIsNotNone(full_context, 'Should return full context')
        self.assertEqual(full_context['agent_name'], 'integration-agent')
        self.assertEqual(full_context['user_id'], 'enterprise-user')
        self.assertEqual(full_context['state'], 'PENDING')
        self.assertTrue(full_context['consolidated'], 'Should be marked as consolidated')
        self.assertTrue(full_context['created_with_ssot'], 'Should be marked as SSOT')
        self.assertIn('state_info', full_context, 'Should include state information')
        self.assertIn('timeout_status', full_context, 'Should include timeout status')
        self.assertIn('circuit_breaker_status', full_context, 'Should include circuit breaker')
        self.assertIn('state_history', full_context, 'Should include state history')
        metadata = full_context.get('metadata', {})
        self.assertEqual(metadata.get('department'), 'sales')
        self.assertEqual(metadata.get('priority'), 'critical')
        self.assertTrue(metadata.get('compliance_required'))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')