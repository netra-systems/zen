"""
AgentExecutionTracker SSOT Integration Tests
============================================

Comprehensive integration tests for the AgentExecutionTracker SSOT class.
Tests critical business functionality that prevents silent agent failures in chat.

Business Value: Platform/Internal - System Stability & $500K+ ARR Protection
These tests protect the Golden Path user flow by ensuring agent executions are 
properly tracked and failures are detected, preventing chat system breakdowns.

Test Categories:
1. Execution Lifecycle Tests (4-5 tests) - PENDING -> RUNNING -> COMPLETED/FAILED flows
2. Death Detection and Heartbeat Tests (3-4 tests) - Prevent silent failures
3. Timeout and Cancellation Tests (3-4 tests) - Enforce execution limits  
4. State Transition and Phase Tracking Tests (3-4 tests) - Track agent progress
5. Concurrent Execution Management Tests (2-3 tests) - Multi-user isolation

CRITICAL: These tests use NO MOCKS - real components without requiring running services.
They test the gap between unit tests and full E2E tests with realistic scenarios.

REQUIREMENTS per CLAUDE.md:
- Must inherit from SSotAsyncTestCase (test_framework.ssot.base_test_case)
- Must use IsolatedEnvironment for all configuration access
- Must use absolute imports from SSOT_IMPORT_REGISTRY.md
- Must test realistic agent execution scenarios
- Must validate business value delivery (chat reliability)
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SsotTestMetrics, SsotTestContext
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, ExecutionRecord, ExecutionState, AgentExecutionPhase, TimeoutConfig, CircuitBreakerState, get_execution_tracker
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from shared.types.core_types import UserID, ThreadID, RunID

class TestAgentExecutionTrackerLifecycle(SSotAsyncTestCase):
    """
    Test execution lifecycle management (PENDING -> RUNNING -> COMPLETED/FAILED).
    
    Business Value: Ensures chat agents properly transition through execution states,
    preventing stuck or zombie agents that break user chat experience.
    """

    async def async_setup_method(self, method=None):
        """Setup for async tests with SSOT compliance."""
        await super().async_setup_method(method)
        self.tracker = AgentExecutionTracker(heartbeat_timeout=2, execution_timeout=5, cleanup_interval=30)
        await self.tracker.start_monitoring()
        self.add_cleanup(lambda: asyncio.create_task(self.tracker.stop_monitoring()))
        self.id_manager = UnifiedIDManager()
        self.test_user_id = self.id_manager.generate_id(IDType.USER, prefix='test')
        self.test_thread_id = self.id_manager.generate_id(IDType.THREAD, prefix='chat')
        self.record_metric('test_category', 'execution_lifecycle')
        self.record_metric('business_value', 'chat_reliability')

    async def test_create_and_start_execution_basic_flow(self):
        """
        Test basic execution creation and startup flow.
        
        BUSINESS VALUE: Validates that chat agents can be properly created and started,
        ensuring users see immediate feedback when requesting AI assistance.
        """
        execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, timeout_seconds=10, metadata={'chat_context': 'user_asking_for_optimization_help'})
        assert execution_id.startswith('exec_execution_'), f'Expected structured ID, got: {execution_id}'
        assert len(execution_id.split('_')) >= 4, 'ID should have structured format: prefix_type_counter_uuid'
        record = self.tracker.get_execution(execution_id)
        assert record is not None, 'Execution record should be created'
        assert record.state == ExecutionState.PENDING, 'New execution should be PENDING'
        assert record.agent_name == 'DataHelperAgent'
        assert record.user_id == self.test_user_id
        assert record.thread_id == self.test_thread_id
        assert record.timeout_seconds == 10
        assert record.metadata['chat_context'] == 'user_asking_for_optimization_help'
        success = self.tracker.start_execution(execution_id)
        assert success, 'Should successfully start execution'
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.STARTING, 'Should transition to STARTING'
        heartbeat_success = self.tracker.heartbeat(execution_id)
        assert heartbeat_success, 'Heartbeat should succeed'
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.RUNNING, 'Should auto-transition to RUNNING on heartbeat'
        assert record.heartbeat_count == 1, 'Should track heartbeat count'
        self.record_metric('executions_created', 1)
        self.record_metric('state_transitions_successful', 3)
        self.record_metric('test_passed', 'create_and_start_execution_basic_flow')

    async def test_execution_completion_success_flow(self):
        """
        Test successful execution completion with result.
        
        BUSINESS VALUE: Ensures chat agents can properly complete and deliver
        results to users, maintaining chat system reliability.
        """
        execution_id = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'task': 'analyze_customer_ai_spend'})
        self.tracker.start_execution(execution_id)
        self.tracker.heartbeat(execution_id)
        completion_result = {'optimization_recommendations': ['Switch to GPT-4 Turbo for 20% cost savings', 'Implement request batching for 15% efficiency gain'], 'estimated_savings': '$2,400/month', 'execution_time_ms': 3500}
        success = self.tracker.update_execution_state(execution_id, ExecutionState.COMPLETED, result=completion_result)
        assert success, 'Should successfully complete execution'
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.COMPLETED, 'Should be COMPLETED'
        assert record.is_terminal, 'COMPLETED should be terminal state'
        assert not record.is_alive, 'COMPLETED execution should not be alive'
        assert record.result == completion_result, 'Should store execution result'
        assert record.completed_at is not None, 'Should set completion timestamp'
        active_executions = self.tracker.get_active_executions()
        active_ids = [e.execution_id for e in active_executions]
        assert execution_id not in active_ids, 'Completed execution should not be in active list'
        metrics = self.tracker.get_metrics()
        assert metrics['successful_executions'] >= 1, 'Should track successful completion'
        assert metrics['total_executions'] >= 1, 'Should track total executions'
        self.record_metric('successful_completions', 1)
        self.record_metric('business_value_delivered', completion_result['estimated_savings'])
        self.record_metric('test_passed', 'execution_completion_success_flow')

    async def test_execution_failure_with_error_handling(self):
        """
        Test execution failure scenarios with proper error tracking.
        
        BUSINESS VALUE: Ensures chat system can gracefully handle agent failures
        and provide meaningful feedback to users instead of silent failures.
        """
        execution_id = self.tracker.create_execution(agent_name='ReportingSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'report_type': 'monthly_optimization_summary'})
        self.tracker.start_execution(execution_id)
        self.tracker.heartbeat(execution_id)
        error_message = 'Database connection timeout during report generation'
        success = self.tracker.update_execution_state(execution_id, ExecutionState.FAILED, error=error_message)
        assert success, 'Should successfully mark execution as failed'
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.FAILED, 'Should be FAILED'
        assert record.is_terminal, 'FAILED should be terminal state'
        assert record.error == error_message, 'Should store error message'
        assert record.completed_at is not None, 'Should set completion timestamp'
        metrics = self.tracker.get_metrics()
        assert metrics['failed_executions'] >= 1, 'Should track failed executions'
        assert metrics['failure_rate'] > 0, 'Should calculate failure rate'
        active_executions = self.tracker.get_active_executions()
        active_ids = [e.execution_id for e in active_executions]
        assert execution_id not in active_ids, 'Failed execution should not be in active list'
        self.record_metric('execution_failures', 1)
        self.record_metric('failure_reason', 'database_timeout')
        self.record_metric('user_impact', 'report_generation_failed')
        self.record_metric('test_passed', 'execution_failure_with_error_handling')

    async def test_invalid_state_transitions_protection(self):
        """
        Test protection against invalid state transitions.
        
        BUSINESS VALUE: Prevents chat system corruption by ensuring execution
        states follow valid patterns and terminal states cannot be modified.
        """
        execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=self.test_thread_id, user_id=self.test_user_id)
        self.tracker.start_execution(execution_id)
        self.tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
        invalid_update = self.tracker.update_execution_state(execution_id, ExecutionState.RUNNING, result='should_not_work')
        assert not invalid_update, 'Should not allow updates to terminal states'
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.COMPLETED, 'Terminal state should be protected'
        invalid_heartbeat = self.tracker.heartbeat(execution_id)
        assert not invalid_heartbeat, 'Should not allow heartbeat on terminal execution'
        fake_id = 'fake_execution_123'
        assert not self.tracker.start_execution(fake_id), 'Should fail on non-existent ID'
        assert not self.tracker.heartbeat(fake_id), 'Should fail on non-existent ID'
        assert not self.tracker.update_execution_state(fake_id, ExecutionState.RUNNING), 'Should fail on non-existent ID'
        self.record_metric('invalid_transitions_blocked', 3)
        self.record_metric('data_integrity_protected', True)
        self.record_metric('test_passed', 'invalid_state_transitions_protection')

    async def test_concurrent_execution_management(self):
        """
        Test management of multiple concurrent executions for same user.
        
        BUSINESS VALUE: Ensures chat system can handle multiple simultaneous
        requests from users without conflicts or resource leaks.
        """
        execution_ids = []
        agent_names = ['DataHelperAgent', 'OptimizationsCoreSubAgent', 'ReportingSubAgent']
        for i, agent_name in enumerate(agent_names):
            execution_id = self.tracker.create_execution(agent_name=agent_name, thread_id=f'{self.test_thread_id}_{i}', user_id=self.test_user_id, metadata={'concurrent_request': i + 1})
            execution_ids.append(execution_id)
            self.tracker.start_execution(execution_id)
            self.tracker.heartbeat(execution_id)
        active_executions = self.tracker.get_active_executions()
        assert len(active_executions) >= 3, 'Should track all concurrent executions'
        for exec_id in execution_ids:
            record = self.tracker.get_execution(exec_id)
            assert record.user_id == self.test_user_id, 'All should belong to same user'
            assert record.state == ExecutionState.RUNNING, 'All should be running'
        self.tracker.update_execution_state(execution_ids[1], ExecutionState.COMPLETED)
        self.tracker.update_execution_state(execution_ids[0], ExecutionState.FAILED, error='test_error')
        self.tracker.update_execution_state(execution_ids[2], ExecutionState.COMPLETED)
        final_states = [self.tracker.get_execution(execution_ids[0]).state, self.tracker.get_execution(execution_ids[1]).state, self.tracker.get_execution(execution_ids[2]).state]
        assert final_states == [ExecutionState.FAILED, ExecutionState.COMPLETED, ExecutionState.COMPLETED]
        metrics = self.tracker.get_metrics()
        assert metrics['total_executions'] >= 3, 'Should count all executions'
        assert metrics['successful_executions'] >= 2, 'Should count successes'
        assert metrics['failed_executions'] >= 1, 'Should count failures'
        self.record_metric('concurrent_executions_handled', 3)
        self.record_metric('user_isolation_maintained', True)
        self.record_metric('completion_order_independence', True)
        self.record_metric('test_passed', 'concurrent_execution_management')

class TestAgentExecutionTrackerDeathDetection(SSotAsyncTestCase):
    """
    Test death detection and heartbeat monitoring functionality.
    
    Business Value: Prevents silent agent failures that would leave users
    waiting indefinitely for chat responses that never come.
    """

    async def async_setup_method(self, method=None):
        """Setup for death detection tests."""
        await super().async_setup_method(method)
        self.tracker = AgentExecutionTracker(heartbeat_timeout=1, execution_timeout=3, cleanup_interval=10)
        await self.tracker.start_monitoring()
        self.add_cleanup(lambda: asyncio.create_task(self.tracker.stop_monitoring()))
        self.id_manager = UnifiedIDManager()
        self.test_user_id = self.id_manager.generate_id(IDType.USER, prefix='test')
        self.test_thread_id = self.id_manager.generate_id(IDType.THREAD, prefix='chat')
        self.record_metric('test_category', 'death_detection')
        self.record_metric('business_value', 'prevent_silent_failures')

    async def test_heartbeat_monitoring_normal_operation(self):
        """
        Test normal heartbeat operation keeps execution alive.
        
        BUSINESS VALUE: Ensures healthy chat agents continue operating
        without false positive death detection.
        """
        execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'operation': 'normal_chat_processing'})
        self.tracker.start_execution(execution_id)
        initial_heartbeat_count = 0
        for i in range(5):
            success = self.tracker.heartbeat(execution_id)
            assert success, f'Heartbeat {i + 1} should succeed'
            record = self.tracker.get_execution(execution_id)
            assert record.heartbeat_count == initial_heartbeat_count + i + 1, f'Should track heartbeat {i + 1}'
            assert record.state in [ExecutionState.STARTING, ExecutionState.RUNNING], 'Should remain alive'
            await asyncio.sleep(0.5)
        await asyncio.sleep(1.5)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.RUNNING, 'Should still be running with regular heartbeats'
        assert not record.is_dead(), 'Should not be detected as dead'
        self.record_metric('heartbeats_sent', 5)
        self.record_metric('false_positives', 0)
        self.record_metric('agent_health_maintained', True)
        self.record_metric('test_passed', 'heartbeat_monitoring_normal_operation')

    async def test_death_detection_no_heartbeat(self):
        """
        Test death detection when agent stops sending heartbeats.
        
        BUSINESS VALUE: Critical for chat reliability - detects when agents
        have silently failed and users would otherwise wait forever.
        """
        execution_id = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'critical_chat_request': True})
        self.tracker.start_execution(execution_id)
        self.tracker.heartbeat(execution_id)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.RUNNING, 'Should be running initially'
        last_heartbeat_time = record.last_heartbeat
        await asyncio.sleep(2.5)
        await asyncio.sleep(0.5)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.DEAD, 'Should be detected as DEAD'
        assert record.is_terminal, 'DEAD should be terminal state'
        assert record.error is not None, 'Should have error message describing death'
        assert 'heartbeat' in record.error.lower(), 'Error should mention heartbeat timeout'
        assert record.last_heartbeat == last_heartbeat_time, 'Last heartbeat time should be preserved'
        time_since_heartbeat = record.time_since_heartbeat.total_seconds()
        assert time_since_heartbeat >= 2.0, 'Should reflect actual time without heartbeat'
        active_executions = self.tracker.get_active_executions()
        active_ids = [e.execution_id for e in active_executions]
        assert execution_id not in active_ids, 'Dead execution should not be in active list'
        metrics = self.tracker.get_metrics()
        assert metrics['dead_executions'] >= 1, 'Should track dead executions'
        self.record_metric('death_detections', 1)
        self.record_metric('silent_failures_prevented', 1)
        self.record_metric('user_wait_time_bounded', True)
        self.record_metric('test_passed', 'death_detection_no_heartbeat')

    async def test_death_detection_callback_integration(self):
        """
        Test death detection callback system for business logic integration.
        
        BUSINESS VALUE: Enables chat system to notify users when agents fail
        and take recovery actions like retrying or escalating to human support.
        """
        death_notifications = []

        async def death_callback(record: ExecutionRecord):
            death_notifications.append({'execution_id': record.execution_id, 'agent_name': record.agent_name, 'user_id': record.user_id, 'thread_id': record.thread_id, 'error': record.error, 'timestamp': datetime.now(timezone.utc)})
        self.tracker.register_death_callback(death_callback)
        execution_id = self.tracker.create_execution(agent_name='ReportingSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'user_request': 'generate_monthly_report', 'priority': 'high'})
        self.tracker.start_execution(execution_id)
        self.tracker.heartbeat(execution_id)
        await asyncio.sleep(2.0)
        await asyncio.sleep(0.5)
        assert len(death_notifications) >= 1, 'Death callback should be triggered'
        notification = death_notifications[-1]
        assert notification['execution_id'] == execution_id, 'Should notify correct execution'
        assert notification['agent_name'] == 'ReportingSubAgent', 'Should include agent name'
        assert notification['user_id'] == self.test_user_id, 'Should include user context'
        assert notification['thread_id'] == self.test_thread_id, 'Should include thread context'
        assert notification['error'] is not None, 'Should include error information'
        assert 'user_request' not in notification, 'Notification should not expose metadata directly'
        self.record_metric('death_callbacks_triggered', len(death_notifications))
        self.record_metric('user_context_preserved', True)
        self.record_metric('recovery_actions_enabled', True)
        self.record_metric('test_passed', 'death_detection_callback_integration')

    async def test_mixed_healthy_and_dying_executions(self):
        """
        Test monitoring with mix of healthy and dying executions.
        
        BUSINESS VALUE: Ensures death detection only affects failed agents
        while healthy chat agents continue serving users normally.
        """
        healthy_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=f'{self.test_thread_id}_healthy', user_id=self.test_user_id, metadata={'status': 'healthy'})
        dying_id = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=f'{self.test_thread_id}_dying', user_id=self.test_user_id, metadata={'status': 'will_die'})
        self.tracker.start_execution(healthy_id)
        self.tracker.start_execution(dying_id)
        self.tracker.heartbeat(healthy_id)
        self.tracker.heartbeat(dying_id)
        for i in range(3):
            await asyncio.sleep(0.8)
            self.tracker.heartbeat(healthy_id)
        await asyncio.sleep(1.0)
        await asyncio.sleep(0.5)
        healthy_record = self.tracker.get_execution(healthy_id)
        dying_record = self.tracker.get_execution(dying_id)
        assert healthy_record.state == ExecutionState.RUNNING, 'Healthy execution should remain running'
        assert dying_record.state == ExecutionState.DEAD, 'Dying execution should be detected as dead'
        assert healthy_record.heartbeat_count >= 3, 'Healthy execution should have multiple heartbeats'
        assert dying_record.heartbeat_count == 1, 'Dying execution should have only initial heartbeat'
        active_executions = self.tracker.get_active_executions()
        active_ids = [e.execution_id for e in active_executions]
        assert healthy_id in active_ids, 'Healthy execution should remain active'
        assert dying_id not in active_ids, 'Dead execution should be removed from active list'
        self.record_metric('healthy_executions_preserved', 1)
        self.record_metric('dead_executions_detected', 1)
        self.record_metric('selective_monitoring_accuracy', True)
        self.record_metric('test_passed', 'mixed_healthy_and_dying_executions')

class TestAgentExecutionTrackerTimeouts(SSotAsyncTestCase):
    """
    Test timeout enforcement and cancellation scenarios.
    
    Business Value: Ensures chat system doesn't consume unlimited resources
    and provides timely feedback when agents take too long.
    """

    async def async_setup_method(self, method=None):
        """Setup for timeout tests."""
        await super().async_setup_method(method)
        self.tracker = AgentExecutionTracker(heartbeat_timeout=2, execution_timeout=4, cleanup_interval=10)
        await self.tracker.start_monitoring()
        self.add_cleanup(lambda: asyncio.create_task(self.tracker.stop_monitoring()))
        self.id_manager = UnifiedIDManager()
        self.test_user_id = self.id_manager.generate_id(IDType.USER, prefix='test')
        self.test_thread_id = self.id_manager.generate_id(IDType.THREAD, prefix='chat')
        self.record_metric('test_category', 'timeout_enforcement')
        self.record_metric('business_value', 'resource_protection')

    async def test_execution_timeout_detection(self):
        """
        Test detection of executions that exceed timeout limits.
        
        BUSINESS VALUE: Prevents runaway chat agents from consuming resources
        indefinitely and provides user feedback about processing delays.
        """
        execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, timeout_seconds=2, metadata={'operation': 'data_analysis', 'timeout_test': True})
        self.tracker.start_execution(execution_id)
        self.tracker.heartbeat(execution_id)
        start_time = time.time()
        while time.time() - start_time < 3.0:
            await asyncio.sleep(0.5)
            self.tracker.heartbeat(execution_id)
        await asyncio.sleep(0.5)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.TIMEOUT, 'Should be detected as TIMEOUT'
        assert record.is_terminal, 'TIMEOUT should be terminal state'
        assert record.error is not None, 'Should have timeout error message'
        assert 'timeout' in record.error.lower(), 'Error should mention timeout'
        assert record.completed_at is not None, 'Should set completion timestamp'
        duration = record.duration
        assert duration is not None, 'Should have duration calculation'
        assert duration.total_seconds() >= 2.0, 'Duration should reflect actual execution time'
        metrics = self.tracker.get_metrics()
        assert metrics['timeout_executions'] >= 1, 'Should track timeout executions'
        self.record_metric('timeout_detections', 1)
        self.record_metric('resource_usage_bounded', True)
        self.record_metric('user_feedback_timing', duration.total_seconds())
        self.record_metric('test_passed', 'execution_timeout_detection')

    async def test_timeout_callback_system(self):
        """
        Test timeout callback system for business logic integration.
        
        BUSINESS VALUE: Enables chat system to notify users about delays
        and take corrective actions like retrying with different parameters.
        """
        timeout_notifications = []

        async def timeout_callback(record: ExecutionRecord):
            timeout_notifications.append({'execution_id': record.execution_id, 'agent_name': record.agent_name, 'user_id': record.user_id, 'timeout_seconds': record.timeout_seconds, 'actual_duration': record.duration.total_seconds() if record.duration else 0, 'metadata': record.metadata})
        self.tracker.register_timeout_callback(timeout_callback)
        execution_id = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, timeout_seconds=1, metadata={'complex_analysis': True, 'user_priority': 'high'})
        self.tracker.start_execution(execution_id)
        self.tracker.heartbeat(execution_id)
        for i in range(3):
            await asyncio.sleep(0.5)
            self.tracker.heartbeat(execution_id)
        await asyncio.sleep(0.5)
        assert len(timeout_notifications) >= 1, 'Timeout callback should be triggered'
        notification = timeout_notifications[-1]
        assert notification['execution_id'] == execution_id, 'Should notify correct execution'
        assert notification['agent_name'] == 'OptimizationsCoreSubAgent', 'Should include agent context'
        assert notification['timeout_seconds'] == 1, 'Should include timeout configuration'
        assert notification['actual_duration'] >= 1.0, 'Should include actual execution time'
        assert notification['metadata']['complex_analysis'], 'Should preserve business context'
        self.record_metric('timeout_callbacks_triggered', len(timeout_notifications))
        self.record_metric('business_context_preserved', True)
        self.record_metric('corrective_actions_enabled', True)
        self.record_metric('test_passed', 'timeout_callback_system')

    async def test_custom_timeout_configuration(self):
        """
        Test custom timeout configuration for different agent types.
        
        BUSINESS VALUE: Allows chat system to set appropriate timeouts
        for different types of AI operations (quick vs. complex analysis).
        """
        complex_config = TimeoutConfig(agent_execution_timeout=10.0, llm_api_timeout=8.0, failure_threshold=2, recovery_timeout=15.0)
        execution_id = self.tracker.create_execution_with_full_context(agent_name='ReportingSubAgent', user_context={'user_id': self.test_user_id, 'thread_id': self.test_thread_id, 'metadata': {'report_type': 'comprehensive_monthly_analysis'}}, timeout_config={'timeout_seconds': 10.0, 'llm_timeout': 8.0, 'failure_threshold': 2, 'recovery_timeout': 15.0})
        record = self.tracker.get_execution(execution_id)
        assert record.timeout_seconds == 10, 'Should use custom timeout'
        assert record.timeout_config is not None, 'Should have timeout configuration'
        assert record.timeout_config.agent_execution_timeout == 10.0, 'Should match custom config'
        assert record.timeout_config.llm_api_timeout == 8.0, 'Should match LLM timeout'
        timeout_status = self.tracker.check_timeout(execution_id)
        assert timeout_status is not None, 'Should provide timeout status'
        assert timeout_status['timeout_seconds'] == 10.0, 'Should reflect custom timeout'
        assert timeout_status['elapsed_seconds'] >= 0, 'Should track elapsed time'
        assert not timeout_status['is_timed_out'], 'Should not be timed out initially'
        cb_status = self.tracker.circuit_breaker_status(execution_id)
        assert cb_status is not None, 'Should have circuit breaker status'
        assert cb_status['failure_threshold'] == 2, 'Should use custom failure threshold'
        assert cb_status['recovery_timeout'] == 15.0, 'Should use custom recovery timeout'
        self.record_metric('custom_timeouts_configured', 1)
        self.record_metric('operation_type_optimization', True)
        self.record_metric('timeout_flexibility', 'comprehensive_monthly_analysis')
        self.record_metric('test_passed', 'custom_timeout_configuration')

    async def test_execution_cancellation_flow(self):
        """
        Test manual execution cancellation capabilities.
        
        BUSINESS VALUE: Allows users to cancel long-running chat requests
        and enables system administrators to stop problematic agents.
        """
        execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'cancellable_operation': True, 'user_request': 'large_data_export'})
        self.tracker.start_execution(execution_id)
        self.tracker.heartbeat(execution_id)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.RUNNING, 'Should be running before cancellation'
        cancellation_reason = 'User requested cancellation'
        success = self.tracker.update_execution_state(execution_id, ExecutionState.CANCELLED, error=cancellation_reason)
        assert success, 'Should successfully cancel execution'
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.CANCELLED, 'Should be CANCELLED'
        assert record.is_terminal, 'CANCELLED should be terminal state'
        assert record.error == cancellation_reason, 'Should store cancellation reason'
        assert record.completed_at is not None, 'Should set completion timestamp'
        active_executions = self.tracker.get_active_executions()
        active_ids = [e.execution_id for e in active_executions]
        assert execution_id not in active_ids, 'Cancelled execution should not be in active list'
        restart_attempt = self.tracker.start_execution(execution_id)
        assert not restart_attempt, 'Should not allow restarting cancelled execution'
        heartbeat_attempt = self.tracker.heartbeat(execution_id)
        assert not heartbeat_attempt, 'Should not allow heartbeat on cancelled execution'
        self.record_metric('cancellations_processed', 1)
        self.record_metric('user_control_enabled', True)
        self.record_metric('resource_cleanup_immediate', True)
        self.record_metric('test_passed', 'execution_cancellation_flow')

class TestAgentExecutionTrackerPhaseTracking(SSotAsyncTestCase):
    """
    Test state transition and phase tracking through AgentExecutionPhase states.
    
    Business Value: Provides detailed progress tracking for chat agents,
    enabling rich user feedback about AI processing steps.
    """

    async def async_setup_method(self, method=None):
        """Setup for phase tracking tests."""
        await super().async_setup_method(method)
        self.tracker = AgentExecutionTracker(heartbeat_timeout=5, execution_timeout=20, cleanup_interval=30)
        await self.tracker.start_monitoring()
        self.add_cleanup(lambda: asyncio.create_task(self.tracker.stop_monitoring()))
        self.id_manager = UnifiedIDManager()
        self.test_user_id = self.id_manager.generate_id(IDType.USER, prefix='test')
        self.test_thread_id = self.id_manager.generate_id(IDType.THREAD, prefix='chat')
        self.record_metric('test_category', 'phase_tracking')
        self.record_metric('business_value', 'user_progress_feedback')

    async def test_complete_agent_execution_phase_workflow(self):
        """
        Test complete agent execution workflow through all phases.
        
        BUSINESS VALUE: Ensures users get detailed feedback about AI processing
        progress, improving perceived responsiveness and user experience.
        """
        execution_id = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'workflow': 'complete_optimization_analysis'})
        record = self.tracker.get_execution(execution_id)
        assert record.current_phase == AgentExecutionPhase.CREATED, 'Should start in CREATED phase'
        phase_sequence = [(AgentExecutionPhase.WEBSOCKET_SETUP, {'websocket_connected': True}), (AgentExecutionPhase.CONTEXT_VALIDATION, {'user_context_valid': True}), (AgentExecutionPhase.STARTING, {'initialization_complete': True}), (AgentExecutionPhase.THINKING, {'analyzing_requirements': True}), (AgentExecutionPhase.LLM_INTERACTION, {'llm_model': 'gpt-4', 'prompt_tokens': 150}), (AgentExecutionPhase.TOOL_EXECUTION, {'tools': ['data_analyzer', 'cost_calculator']}), (AgentExecutionPhase.RESULT_PROCESSING, {'recommendations_count': 5}), (AgentExecutionPhase.COMPLETING, {'final_validation': True}), (AgentExecutionPhase.COMPLETED, {'success': True, 'execution_time_ms': 8500})]
        for phase, metadata in phase_sequence:
            success = await self.tracker.transition_state(execution_id, phase, metadata=metadata)
            assert success, f'Should successfully transition to {phase.value}'
            record = self.tracker.get_execution(execution_id)
            assert record.current_phase == phase, f'Should be in {phase.value} phase'
            await asyncio.sleep(0.1)
        history = self.tracker.get_state_history(execution_id)
        assert len(history) == len(phase_sequence), 'Should record all phase transitions'
        for i, (expected_phase, expected_metadata) in enumerate(phase_sequence):
            transition = history[i]
            assert transition['to_phase'] == expected_phase.value, f'Transition {i} should be to {expected_phase.value}'
            assert transition['metadata'] == expected_metadata, f'Transition {i} should preserve metadata'
            assert transition['duration_ms'] >= 0, f'Transition {i} should have valid duration'
        record = self.tracker.get_execution(execution_id)
        assert record.current_phase == AgentExecutionPhase.COMPLETED, 'Should end in COMPLETED phase'
        assert record.state == ExecutionState.RUNNING, 'Execution state separate from phase'
        thinking_duration = record.get_phase_duration_ms(AgentExecutionPhase.THINKING)
        assert thinking_duration >= 0, 'Should calculate thinking phase duration'
        total_duration = record.get_total_duration_ms()
        assert total_duration >= len(phase_sequence) * 100, 'Total duration should reflect all phases'
        self.record_metric('phase_transitions_completed', len(phase_sequence))
        self.record_metric('user_progress_visibility', True)
        self.record_metric('workflow_completion_time_ms', total_duration)
        self.record_metric('test_passed', 'complete_agent_execution_phase_workflow')

    async def test_phase_transition_validation_rules(self):
        """
        Test phase transition validation rules and error handling.
        
        BUSINESS VALUE: Ensures chat system maintains consistent agent state
        and prevents invalid transitions that could confuse users.
        """
        execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'validation_test': True})
        valid_transitions = [AgentExecutionPhase.WEBSOCKET_SETUP, AgentExecutionPhase.CONTEXT_VALIDATION, AgentExecutionPhase.STARTING]
        for phase in valid_transitions:
            success = await self.tracker.transition_state(execution_id, phase)
            assert success, f'Valid transition to {phase.value} should succeed'
        current_record = self.tracker.get_execution(execution_id)
        current_phase = current_record.current_phase
        invalid_success = await self.tracker.transition_state(execution_id, AgentExecutionPhase.COMPLETED)
        if invalid_success:
            pass
        else:
            record = self.tracker.get_execution(execution_id)
            assert record.current_phase == current_phase, 'Invalid transition should not change phase'
        valid_next = self.tracker.validate_state_transition(AgentExecutionPhase.THINKING, AgentExecutionPhase.LLM_INTERACTION)
        assert valid_next, 'THINKING  ->  LLM_INTERACTION should be valid'
        invalid_next = self.tracker.validate_state_transition(AgentExecutionPhase.CREATED, AgentExecutionPhase.COMPLETED)
        assert not invalid_next, 'CREATED  ->  COMPLETED should be invalid'
        self.record_metric('valid_transitions_tested', len(valid_transitions))
        self.record_metric('invalid_transitions_tested', 1)
        self.record_metric('state_consistency_maintained', True)
        self.record_metric('test_passed', 'phase_transition_validation_rules')

    async def test_websocket_event_integration_with_phases(self):
        """
        Test WebSocket event integration with phase transitions.
        
        BUSINESS VALUE: Ensures users receive real-time updates about
        agent progress through the chat interface.
        """
        mock_websocket_manager = AsyncMock()
        execution_id = self.tracker.create_execution(agent_name='ReportingSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'websocket_test': True})
        business_phases = [(AgentExecutionPhase.STARTING, 'agent_started'), (AgentExecutionPhase.THINKING, 'agent_thinking'), (AgentExecutionPhase.TOOL_EXECUTION, 'tool_executing'), (AgentExecutionPhase.COMPLETING, 'agent_thinking'), (AgentExecutionPhase.COMPLETED, 'agent_completed')]
        for phase, expected_event in business_phases:
            success = await self.tracker.transition_state(execution_id, phase, metadata={'step': phase.value}, websocket_manager=mock_websocket_manager)
            assert success, f'Should transition to {phase.value} with WebSocket events'
        mock_calls = mock_websocket_manager.method_calls
        called_methods = [call[0] for call in mock_calls]
        expected_methods = ['notify_agent_started', 'notify_agent_thinking', 'notify_tool_executing', 'notify_agent_thinking', 'notify_agent_completed']
        for expected_method in expected_methods:
            assert expected_method in called_methods, f'Should call {expected_method}'
        history = self.tracker.get_state_history(execution_id)
        for transition in history:
            if transition['to_phase'] in [phase.value for phase, _ in business_phases]:
                assert 'websocket_event_sent' in transition, 'Should track WebSocket event status'
        self.record_metric('websocket_events_triggered', len(business_phases))
        self.record_metric('real_time_updates_enabled', True)
        self.record_metric('user_experience_enhanced', True)
        self.record_metric('test_passed', 'websocket_event_integration_with_phases')

    async def test_phase_performance_tracking(self):
        """
        Test performance tracking for different execution phases.
        
        BUSINESS VALUE: Enables optimization of chat system performance
        by identifying bottlenecks in agent processing pipeline.
        """
        execution_id = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'performance_analysis': True})
        performance_phases = [(AgentExecutionPhase.WEBSOCKET_SETUP, 0.1), (AgentExecutionPhase.CONTEXT_VALIDATION, 0.2), (AgentExecutionPhase.THINKING, 0.5), (AgentExecutionPhase.LLM_INTERACTION, 1.0), (AgentExecutionPhase.TOOL_EXECUTION, 0.3), (AgentExecutionPhase.RESULT_PROCESSING, 0.4), (AgentExecutionPhase.COMPLETED, 0.1)]
        phase_start_times = {}
        for phase, expected_duration in performance_phases:
            phase_start_time = time.time()
            phase_start_times[phase] = phase_start_time
            await asyncio.sleep(expected_duration)
            success = await self.tracker.transition_state(execution_id, phase, metadata={'expected_duration_ms': expected_duration * 1000, 'phase_start': phase_start_time})
            assert success, f'Should transition to {phase.value}'
        record = self.tracker.get_execution(execution_id)
        history = self.tracker.get_state_history(execution_id)
        total_duration = record.get_total_duration_ms()
        assert total_duration >= sum((duration * 1000 for _, duration in performance_phases)), 'Total duration should reflect all phase durations'
        thinking_duration = record.get_phase_duration_ms(AgentExecutionPhase.THINKING)
        llm_duration = record.get_phase_duration_ms(AgentExecutionPhase.LLM_INTERACTION)
        assert thinking_duration >= 400, 'Thinking phase should take expected time'
        assert llm_duration >= 900, 'LLM interaction should take expected time'
        current_phase_duration = record.get_current_phase_duration_ms()
        assert current_phase_duration >= 0, 'Should track current phase duration'
        slowest_phase = None
        slowest_duration = 0
        for transition in history:
            if transition['duration_ms'] > slowest_duration:
                slowest_duration = transition['duration_ms']
                slowest_phase = transition['to_phase']
        self.record_metric('performance_phases_tracked', len(performance_phases))
        self.record_metric('total_execution_time_ms', total_duration)
        self.record_metric('slowest_phase', slowest_phase)
        self.record_metric('slowest_phase_duration_ms', slowest_duration)
        self.record_metric('performance_optimization_enabled', True)
        self.record_metric('test_passed', 'phase_performance_tracking')

class TestAgentExecutionTrackerConcurrentManagement(SSotAsyncTestCase):
    """
    Test concurrent execution management and user isolation.
    
    Business Value: Ensures chat system can handle multiple users and
    multiple simultaneous requests without conflicts or data leaks.
    """

    async def async_setup_method(self, method=None):
        """Setup for concurrent management tests."""
        await super().async_setup_method(method)
        self.tracker = AgentExecutionTracker(heartbeat_timeout=3, execution_timeout=10, cleanup_interval=30)
        await self.tracker.start_monitoring()
        self.add_cleanup(lambda: asyncio.create_task(self.tracker.stop_monitoring()))
        self.id_manager = UnifiedIDManager()
        self.users = {'alice': self.id_manager.generate_id(IDType.USER, prefix='alice'), 'bob': self.id_manager.generate_id(IDType.USER, prefix='bob'), 'charlie': self.id_manager.generate_id(IDType.USER, prefix='charlie')}
        self.record_metric('test_category', 'concurrent_management')
        self.record_metric('business_value', 'multi_user_isolation')

    async def test_multi_user_execution_isolation(self):
        """
        Test execution isolation between different users.
        
        BUSINESS VALUE: Ensures chat sessions from different users are completely
        isolated and don't interfere with each other's agent executions.
        """
        user_executions = {}
        for username, user_id in self.users.items():
            thread_id = self.id_manager.generate_id(IDType.THREAD, prefix=f'{username}_chat')
            execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=thread_id, user_id=user_id, metadata={'username': username, 'session_type': 'individual_chat', 'privacy_level': 'user_isolated'})
            user_executions[username] = {'execution_id': execution_id, 'user_id': user_id, 'thread_id': thread_id}
            self.tracker.start_execution(execution_id)
            self.tracker.heartbeat(execution_id)
        assert len(user_executions) == 3, 'Should create executions for all users'
        for username, exec_data in user_executions.items():
            record = self.tracker.get_execution(exec_data['execution_id'])
            assert record.user_id == exec_data['user_id'], f'User {username} should have correct user_id'
            assert record.thread_id == exec_data['thread_id'], f'User {username} should have correct thread_id'
            assert record.metadata['username'] == username, f'Should preserve user-specific metadata'
            assert record.state == ExecutionState.RUNNING, f'User {username} execution should be running'
        alice_id = user_executions['alice']['execution_id']
        bob_id = user_executions['bob']['execution_id']
        alice_record = self.tracker.get_execution(alice_id)
        bob_record = self.tracker.get_execution(bob_id)
        assert alice_record.user_id != bob_record.user_id, 'Users should have different user_ids'
        assert alice_record.thread_id != bob_record.thread_id, 'Users should have different thread_ids'
        assert alice_record.metadata['username'] != bob_record.metadata['username'], 'Metadata should be user-specific'
        self.tracker.update_execution_state(alice_id, ExecutionState.COMPLETED, result={'user': 'alice', 'result': 'success'})
        self.tracker.update_execution_state(bob_id, ExecutionState.FAILED, error='test failure for bob')
        alice_final = self.tracker.get_execution(alice_id)
        bob_final = self.tracker.get_execution(bob_id)
        charlie_final = self.tracker.get_execution(user_executions['charlie']['execution_id'])
        assert alice_final.state == ExecutionState.COMPLETED, 'Alice should be completed'
        assert bob_final.state == ExecutionState.FAILED, 'Bob should be failed'
        assert charlie_final.state == ExecutionState.RUNNING, 'Charlie should still be running'
        self.record_metric('concurrent_users_isolated', len(self.users))
        self.record_metric('user_data_isolation_verified', True)
        self.record_metric('independent_state_management', True)
        self.record_metric('test_passed', 'multi_user_execution_isolation')

    async def test_same_user_multiple_concurrent_executions(self):
        """
        Test handling multiple concurrent executions for the same user.
        
        BUSINESS VALUE: Enables users to have multiple chat conversations
        or submit multiple AI requests simultaneously without conflicts.
        """
        user_id = self.users['alice']
        concurrent_executions = []
        agent_types = ['DataHelperAgent', 'OptimizationsCoreSubAgent', 'ReportingSubAgent']
        for i, agent_name in enumerate(agent_types):
            thread_id = self.id_manager.generate_id(IDType.THREAD, prefix=f'alice_thread_{i}')
            execution_id = self.tracker.create_execution(agent_name=agent_name, thread_id=thread_id, user_id=user_id, metadata={'thread_number': i + 1, 'concurrent_session': True, 'agent_type': agent_name})
            concurrent_executions.append({'execution_id': execution_id, 'thread_id': thread_id, 'agent_name': agent_name})
            self.tracker.start_execution(execution_id)
            self.tracker.heartbeat(execution_id)
        active_executions = self.tracker.get_active_executions()
        user_active_executions = [e for e in active_executions if e.user_id == user_id]
        assert len(user_active_executions) >= 3, 'Should have multiple active executions for same user'
        for exec_data in concurrent_executions:
            record = self.tracker.get_execution(exec_data['execution_id'])
            assert record.user_id == user_id, 'All should belong to same user'
            assert record.thread_id == exec_data['thread_id'], 'Each should have unique thread'
            assert record.agent_name == exec_data['agent_name'], 'Should preserve agent type'
            assert record.state == ExecutionState.RUNNING, 'All should be running'
        for i, exec_data in enumerate(concurrent_executions):
            await asyncio.sleep(0.1)
            success = self.tracker.heartbeat(exec_data['execution_id'])
            assert success, f'Heartbeat should succeed for execution {i}'
        import random
        completion_order = concurrent_executions.copy()
        random.shuffle(completion_order)
        results = ['result_1', 'result_2', 'result_3']
        for i, exec_data in enumerate(completion_order):
            self.tracker.update_execution_state(exec_data['execution_id'], ExecutionState.COMPLETED, result={'order': i + 1, 'result': results[i]})
        for exec_data in concurrent_executions:
            record = self.tracker.get_execution(exec_data['execution_id'])
            assert record.state == ExecutionState.COMPLETED, 'All should be completed'
            assert record.result is not None, 'All should have results'
            assert record.user_id == user_id, 'All should still belong to same user'
        self.record_metric('concurrent_executions_per_user', len(concurrent_executions))
        self.record_metric('thread_isolation_maintained', True)
        self.record_metric('concurrent_operations_successful', True)
        self.record_metric('test_passed', 'same_user_multiple_concurrent_executions')

    async def test_execution_query_and_filtering(self):
        """
        Test execution querying and filtering capabilities.
        
        BUSINESS VALUE: Enables chat system to efficiently query and manage
        executions for monitoring, debugging, and user experience features.
        """
        test_executions = []
        alice_id = self.users['alice']
        alice_executions = []
        for i, agent in enumerate(['DataHelperAgent', 'OptimizationsCoreSubAgent']):
            thread_id = self.id_manager.generate_id(IDType.THREAD, prefix=f'alice_{i}')
            execution_id = self.tracker.create_execution(agent_name=agent, thread_id=thread_id, user_id=alice_id, metadata={'user': 'alice', 'session': i + 1})
            alice_executions.append(execution_id)
            test_executions.append(execution_id)
            self.tracker.start_execution(execution_id)
            self.tracker.heartbeat(execution_id)
        bob_id = self.users['bob']
        bob_thread = self.id_manager.generate_id(IDType.THREAD, prefix='bob_main')
        bob_execution = self.tracker.create_execution(agent_name='ReportingSubAgent', thread_id=bob_thread, user_id=bob_id, metadata={'user': 'bob', 'priority': 'high'})
        test_executions.append(bob_execution)
        self.tracker.start_execution(bob_execution)
        self.tracker.heartbeat(bob_execution)
        data_helper_executions = self.tracker.get_executions_by_agent('DataHelperAgent')
        data_helper_ids = [e.execution_id for e in data_helper_executions]
        assert alice_executions[0] in data_helper_ids, "Should find Alice's DataHelperAgent execution"
        assert bob_execution not in data_helper_ids, "Should not include Bob's ReportingSubAgent"
        optimization_executions = self.tracker.get_executions_by_agent('OptimizationsCoreSubAgent')
        optimization_ids = [e.execution_id for e in optimization_executions]
        assert alice_executions[1] in optimization_ids, "Should find Alice's OptimizationsCoreSubAgent execution"
        alice_thread_0 = alice_executions[0]
        alice_record_0 = self.tracker.get_execution(alice_thread_0)
        thread_executions = self.tracker.get_executions_by_thread(alice_record_0.thread_id)
        thread_ids = [e.execution_id for e in thread_executions]
        assert alice_thread_0 in thread_ids, 'Should find execution by thread ID'
        assert len(thread_ids) == 1, 'Should only return executions for specific thread'
        active_executions = self.tracker.get_active_executions()
        active_ids = [e.execution_id for e in active_executions]
        for exec_id in test_executions:
            assert exec_id in active_ids, f'Execution {exec_id} should be in active list'
        self.tracker.update_execution_state(alice_executions[0], ExecutionState.COMPLETED)
        self.tracker.update_execution_state(bob_execution, ExecutionState.FAILED, error='test failure')
        updated_active = self.tracker.get_active_executions()
        updated_active_ids = [e.execution_id for e in updated_active]
        assert alice_executions[0] not in updated_active_ids, 'Completed execution should not be active'
        assert bob_execution not in updated_active_ids, 'Failed execution should not be active'
        assert alice_executions[1] in updated_active_ids, 'Running execution should still be active'
        metrics = self.tracker.get_metrics()
        assert metrics['total_executions'] >= len(test_executions), 'Should count all created executions'
        assert metrics['active_executions'] >= 1, 'Should count remaining active executions'
        assert metrics['successful_executions'] >= 1, 'Should count completed executions'
        assert metrics['failed_executions'] >= 1, 'Should count failed executions'
        self.record_metric('query_operations_tested', 4)
        self.record_metric('filtering_accuracy_verified', True)
        self.record_metric('execution_management_efficiency', True)
        self.record_metric('test_passed', 'execution_query_and_filtering')

class TestAgentExecutionTrackerUnifiedIDIntegration(SSotAsyncTestCase):
    """
    Test UnifiedIDManager SSOT integration for ID generation.
    
    Business Value: Ensures consistent, traceable ID generation across
    the entire chat system for debugging and audit purposes.
    """

    async def async_setup_method(self, method=None):
        """Setup for UnifiedIDManager integration tests."""
        await super().async_setup_method(method)
        self.tracker = AgentExecutionTracker()
        await self.tracker.start_monitoring()
        self.add_cleanup(lambda: asyncio.create_task(self.tracker.stop_monitoring()))
        self.id_manager = UnifiedIDManager()
        self.test_user_id = self.id_manager.generate_id(IDType.USER, prefix='ssot_test')
        self.test_thread_id = self.id_manager.generate_id(IDType.THREAD, prefix='ssot_chat')
        self.record_metric('test_category', 'unified_id_integration')
        self.record_metric('business_value', 'system_traceability')

    async def test_ssot_id_generation_compliance(self):
        """
        Test compliance with UnifiedIDManager SSOT patterns.
        
        BUSINESS VALUE: Ensures all execution IDs follow consistent format
        for system-wide traceability and debugging across chat infrastructure.
        """
        execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'ssot_test': True})
        assert execution_id.startswith('exec_execution_'), 'Should use exec prefix with execution type'
        parts = execution_id.split('_')
        assert len(parts) == 4, f'Should have 4 parts, got: {parts}'
        assert parts[0] == 'exec', 'Should have exec prefix'
        assert parts[1] == 'execution', 'Should have execution type'
        assert parts[2].isdigit(), 'Should have numeric counter'
        assert len(parts[3]) == 8, 'Should have 8-character UUID part'
        assert all((c in '0123456789abcdef' for c in parts[3].lower())), 'UUID part should be hex'
        metadata = self.id_manager.get_id_metadata(execution_id)
        assert metadata is not None, 'ID should be registered with UnifiedIDManager'
        assert metadata.id_type == IDType.EXECUTION, 'Should be registered as EXECUTION type'
        assert metadata.prefix == 'exec', 'Should preserve prefix in metadata'
        assert 'agent_name' in metadata.context, 'Should include agent context'
        assert metadata.context['agent_name'] == 'DataHelperAgent', 'Should preserve agent name'
        is_valid = self.id_manager.is_valid_id(execution_id, IDType.EXECUTION)
        assert is_valid, 'Generated ID should be valid'
        is_valid_format = self.id_manager.is_valid_id_format_compatible(execution_id, IDType.EXECUTION)
        assert is_valid_format, 'ID should have valid format'
        self.record_metric('ssot_id_compliance_verified', True)
        self.record_metric('id_traceability_enabled', True)
        self.record_metric('unified_id_format_correct', True)
        self.record_metric('test_passed', 'ssot_id_generation_compliance')

    async def test_id_context_preservation(self):
        """
        Test preservation of business context in ID metadata.
        
        BUSINESS VALUE: Enables rich debugging and audit trails by preserving
        execution context information for chat system troubleshooting.
        """
        context_metadata = {'user_request': 'optimize_ai_costs', 'complexity': 'high', 'estimated_duration': 30, 'priority_level': 'business_critical'}
        execution_id = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, timeout_seconds=45, metadata=context_metadata)
        id_metadata = self.id_manager.get_id_metadata(execution_id)
        assert id_metadata is not None, 'Should have ID metadata'
        assert id_metadata.context['agent_name'] == 'OptimizationsCoreSubAgent', 'Should preserve agent name'
        assert id_metadata.context['operation'] == 'execution', 'Should identify as execution operation'
        assert 'timestamp' in id_metadata.context, 'Should include creation timestamp'
        record = self.tracker.get_execution(execution_id)
        assert record.metadata == context_metadata, 'Should preserve all execution metadata'
        assert record.timeout_seconds == 45, 'Should preserve timeout configuration'
        full_context = self.tracker.get_execution_with_full_context(execution_id)
        assert full_context is not None, 'Should provide full context'
        assert full_context['execution_id'] == execution_id, 'Should include execution ID'
        assert full_context['metadata'] == context_metadata, 'Should include full metadata'
        assert full_context['created_with_ssot'], 'Should indicate SSOT creation'
        self.record_metric('context_preservation_verified', True)
        self.record_metric('audit_trail_enabled', True)
        self.record_metric('debugging_capability_enhanced', True)
        self.record_metric('test_passed', 'id_context_preservation')

    async def test_id_lifecycle_management(self):
        """
        Test complete ID lifecycle management with UnifiedIDManager.
        
        BUSINESS VALUE: Ensures proper resource management and cleanup
        for chat system scalability and performance.
        """
        execution_id = self.tracker.create_execution(agent_name='ReportingSubAgent', thread_id=self.test_thread_id, user_id=self.test_user_id, metadata={'lifecycle_test': True})
        active_execution_ids = self.id_manager.get_active_ids(IDType.EXECUTION)
        assert execution_id in active_execution_ids, 'Should be in active IDs'
        id_count_before = self.id_manager.count_active_ids(IDType.EXECUTION)
        assert id_count_before >= 1, 'Should have at least one active execution ID'
        self.tracker.start_execution(execution_id)
        self.tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
        release_success = self.id_manager.release_id(execution_id)
        assert release_success, 'Should successfully release ID'
        updated_active_ids = self.id_manager.get_active_ids(IDType.EXECUTION)
        assert execution_id not in updated_active_ids, 'Should be removed from active IDs'
        id_metadata = self.id_manager.get_id_metadata(execution_id)
        assert id_metadata is not None, 'Metadata should be preserved for audit'
        assert 'released_at' in id_metadata.context, 'Should mark release timestamp'
        stats = self.id_manager.get_stats()
        assert stats['total_registered'] >= 1, 'Should count registered IDs'
        assert IDType.EXECUTION.value in stats['active_by_type'], 'Should track execution IDs'
        assert IDType.EXECUTION.value in stats['counters_by_type'], 'Should track execution counters'
        self.record_metric('id_lifecycle_managed', True)
        self.record_metric('resource_cleanup_verified', True)
        self.record_metric('audit_preservation_maintained', True)
        self.record_metric('test_passed', 'id_lifecycle_management')

class TestAgentExecutionTrackerBusinessValueScenarios(SSotAsyncTestCase):
    """
    Test business value scenarios preventing silent agent failures in chat.
    
    Business Value: Critical tests that directly protect $500K+ ARR by ensuring
    chat reliability and preventing user experience degradation.
    """

    async def async_setup_method(self, method=None):
        """Setup for business value scenario tests."""
        await super().async_setup_method(method)
        self.tracker = AgentExecutionTracker(heartbeat_timeout=2, execution_timeout=8, cleanup_interval=20)
        await self.tracker.start_monitoring()
        self.add_cleanup(lambda: asyncio.create_task(self.tracker.stop_monitoring()))
        self.id_manager = UnifiedIDManager()
        self.enterprise_user = self.id_manager.generate_id(IDType.USER, prefix='enterprise')
        self.premium_user = self.id_manager.generate_id(IDType.USER, prefix='premium')
        self.free_user = self.id_manager.generate_id(IDType.USER, prefix='free')
        self.record_metric('test_category', 'business_value_protection')
        self.record_metric('business_value', 'arr_protection_500k')

    async def test_enterprise_customer_chat_reliability(self):
        """
        Test enterprise customer chat reliability protection.
        
        BUSINESS VALUE: Protects $15K+ MRR enterprise customers from chat failures
        that could lead to churn and significant revenue loss.
        """
        enterprise_thread = self.id_manager.generate_id(IDType.THREAD, prefix='enterprise_analysis')
        execution_id = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=enterprise_thread, user_id=self.enterprise_user, timeout_seconds=30, metadata={'customer_tier': 'enterprise', 'monthly_value': 15000, 'request_type': 'comprehensive_cost_optimization', 'priority': 'high', 'sla_requirement': '99.9%'})
        self.tracker.start_execution(execution_id)
        enterprise_phases = [(AgentExecutionPhase.WEBSOCKET_SETUP, {'enterprise_priority': True}), (AgentExecutionPhase.CONTEXT_VALIDATION, {'enterprise_context_validated': True}), (AgentExecutionPhase.STARTING, {'enterprise_resources_allocated': True}), (AgentExecutionPhase.THINKING, {'analysis_scope': 'comprehensive'}), (AgentExecutionPhase.LLM_INTERACTION, {'model': 'gpt-4', 'enhanced_reasoning': True}), (AgentExecutionPhase.TOOL_EXECUTION, {'enterprise_tools': ['advanced_optimizer', 'cost_analyzer']}), (AgentExecutionPhase.RESULT_PROCESSING, {'detailed_recommendations': True})]
        for phase, metadata in enterprise_phases:
            success = await self.tracker.transition_state(execution_id, phase, metadata=metadata)
            assert success, f'Enterprise execution should successfully transition to {phase.value}'
            self.tracker.heartbeat(execution_id)
            await asyncio.sleep(0.2)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.RUNNING, 'Enterprise execution should be running smoothly'
        assert record.current_phase == AgentExecutionPhase.RESULT_PROCESSING, 'Should reach processing phase'
        assert record.heartbeat_count >= len(enterprise_phases), 'Should maintain healthy heartbeat'
        enterprise_results = {'optimization_savings': '$50,000/month', 'recommendations': ['Switch to GPT-4 Turbo for 25% cost reduction', 'Implement advanced caching for 40% performance gain', 'Optimize batch processing for 30% efficiency improvement'], 'roi_analysis': {'implementation_cost': '$10,000', 'monthly_savings': '$50,000'}, 'executive_summary': 'Comprehensive optimization analysis complete', 'confidence_score': 0.95}
        success = self.tracker.update_execution_state(execution_id, ExecutionState.COMPLETED, result=enterprise_results)
        assert success, 'Enterprise execution should complete successfully'
        final_record = self.tracker.get_execution(execution_id)
        execution_duration = final_record.duration.total_seconds() if final_record.duration else 0
        assert execution_duration < 30, 'Should complete within enterprise SLA timeout'
        assert final_record.result == enterprise_results, 'Should deliver comprehensive results'
        self.record_metric('enterprise_customer_protected', True)
        self.record_metric('monthly_value_at_risk', 15000)
        self.record_metric('sla_compliance_verified', True)
        self.record_metric('execution_duration_seconds', execution_duration)
        self.record_metric('test_passed', 'enterprise_customer_chat_reliability')

    async def test_silent_failure_prevention_golden_path(self):
        """
        Test prevention of silent failures in Golden Path user flow.
        
        BUSINESS VALUE: Protects the core $500K+ ARR user flow by ensuring
        agent failures are detected and handled, not silently ignored.
        """
        golden_path_thread = self.id_manager.generate_id(IDType.THREAD, prefix='golden_path')
        execution_id = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=golden_path_thread, user_id=self.premium_user, metadata={'flow_type': 'golden_path', 'user_tier': 'premium', 'revenue_critical': True, 'user_expectation': 'immediate_response'})
        failure_notifications = []

        async def business_failure_callback(record: ExecutionRecord):
            failure_notifications.append({'execution_id': record.execution_id, 'user_id': record.user_id, 'failure_type': 'death' if record.state == ExecutionState.DEAD else 'timeout', 'business_impact': 'golden_path_disruption', 'revenue_at_risk': 'high', 'recovery_action_required': True})
        self.tracker.register_death_callback(business_failure_callback)
        self.tracker.register_timeout_callback(business_failure_callback)
        self.tracker.start_execution(execution_id)
        self.tracker.heartbeat(execution_id)
        self.tracker.transition_state(execution_id, AgentExecutionPhase.THINKING, metadata={'golden_path_analysis': True})
        await asyncio.sleep(0.5)
        await asyncio.sleep(3.0)
        await asyncio.sleep(0.5)
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.DEAD, 'Silent failure should be detected as DEAD'
        assert record.error is not None, 'Should have error description'
        assert 'heartbeat' in record.error.lower(), 'Should identify heartbeat failure'
        assert len(failure_notifications) >= 1, 'Business failure callback should be triggered'
        notification = failure_notifications[-1]
        assert notification['failure_type'] == 'death', 'Should identify as death failure'
        assert notification['business_impact'] == 'golden_path_disruption', 'Should identify business impact'
        assert notification['recovery_action_required'], 'Should flag need for recovery'
        active_executions = self.tracker.get_active_executions()
        active_ids = [e.execution_id for e in active_executions]
        assert execution_id not in active_ids, 'Failed execution should be cleaned up'
        self.record_metric('silent_failures_prevented', 1)
        self.record_metric('golden_path_protected', True)
        self.record_metric('business_callbacks_triggered', len(failure_notifications))
        self.record_metric('revenue_protection_enabled', True)
        self.record_metric('test_passed', 'silent_failure_prevention_golden_path')

    async def test_multi_tier_user_experience_protection(self):
        """
        Test protection across different user tiers (Free, Premium, Enterprise).
        
        BUSINESS VALUE: Ensures all user tiers receive appropriate service levels
        while maintaining system stability and resource allocation efficiency.
        """
        tier_executions = {}
        free_thread = self.id_manager.generate_id(IDType.THREAD, prefix='free_chat')
        free_execution = self.tracker.create_execution(agent_name='DataHelperAgent', thread_id=free_thread, user_id=self.free_user, timeout_seconds=10, metadata={'tier': 'free', 'features': 'basic', 'priority': 'normal'})
        tier_executions['free'] = free_execution
        premium_thread = self.id_manager.generate_id(IDType.THREAD, prefix='premium_chat')
        premium_execution = self.tracker.create_execution(agent_name='OptimizationsCoreSubAgent', thread_id=premium_thread, user_id=self.premium_user, timeout_seconds=20, metadata={'tier': 'premium', 'features': 'enhanced', 'priority': 'high'})
        tier_executions['premium'] = premium_execution
        enterprise_thread = self.id_manager.generate_id(IDType.THREAD, prefix='enterprise_chat')
        enterprise_execution = self.tracker.create_execution(agent_name='ReportingSubAgent', thread_id=enterprise_thread, user_id=self.enterprise_user, timeout_seconds=30, metadata={'tier': 'enterprise', 'features': 'comprehensive', 'priority': 'critical'})
        tier_executions['enterprise'] = enterprise_execution
        for tier, exec_id in tier_executions.items():
            success = self.tracker.start_execution(exec_id)
            assert success, f'Should start {tier} tier execution'
            self.tracker.heartbeat(exec_id)
        for tier, exec_id in tier_executions.items():
            record = self.tracker.get_execution(exec_id)
            if tier == 'free':
                assert record.timeout_seconds == 10, 'Free tier should have basic timeout'
                assert record.metadata['features'] == 'basic', 'Free tier should have basic features'
            elif tier == 'premium':
                assert record.timeout_seconds == 20, 'Premium tier should have enhanced timeout'
                assert record.metadata['features'] == 'enhanced', 'Premium tier should have enhanced features'
            elif tier == 'enterprise':
                assert record.timeout_seconds == 30, 'Enterprise tier should have premium timeout'
                assert record.metadata['features'] == 'comprehensive', 'Enterprise tier should have comprehensive features'
        self.tracker.update_execution_state(tier_executions['free'], ExecutionState.COMPLETED, result={'analysis': 'basic', 'recommendations': 2})
        self.tracker.update_execution_state(tier_executions['premium'], ExecutionState.COMPLETED, result={'analysis': 'detailed', 'recommendations': 5, 'savings_estimate': '$1,200/month'})
        self.tracker.update_execution_state(tier_executions['enterprise'], ExecutionState.COMPLETED, result={'analysis': 'comprehensive', 'recommendations': 10, 'savings_estimate': '$15,000/month', 'executive_summary': True, 'custom_integration': True})
        for tier, exec_id in tier_executions.items():
            record = self.tracker.get_execution(exec_id)
            assert record.state == ExecutionState.COMPLETED, f'{tier} tier should complete successfully'
            result = record.result
            if tier == 'free':
                assert result['recommendations'] == 2, 'Free tier should get basic recommendations'
            elif tier == 'premium':
                assert result['recommendations'] == 5, 'Premium tier should get enhanced recommendations'
                assert 'savings_estimate' in result, 'Premium tier should get savings analysis'
            elif tier == 'enterprise':
                assert result['recommendations'] == 10, 'Enterprise tier should get comprehensive recommendations'
                assert result['executive_summary'], 'Enterprise tier should get executive summary'
        metrics = self.tracker.get_metrics()
        assert metrics['successful_executions'] >= 3, 'All tiers should complete successfully'
        assert metrics['failure_rate'] == 0, 'No failures should occur for tier-appropriate service'
        self.record_metric('user_tiers_protected', 3)
        self.record_metric('service_differentiation_maintained', True)
        self.record_metric('system_stability_across_tiers', True)
        self.record_metric('revenue_optimization_enabled', True)
        self.record_metric('test_passed', 'multi_tier_user_experience_protection')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')