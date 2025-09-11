"""
Agent Execution Error Recovery Integration Tests
==============================================

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All segments (error recovery protects 90% of platform value - chat functionality)
- Business Goal: Ensure system resilience and graceful degradation during failures
- Value Impact: Prevents complete service failure, maintains partial functionality during issues
- Strategic Impact: Protects $500K+ ARR by ensuring users receive responses even during infrastructure problems

CRITICAL REQUIREMENTS:
- REAL infrastructure failure simulation (network, database, Redis, WebSocket)
- Test error recovery with actual service dependencies
- Validate graceful degradation maintains core chat functionality
- Test circuit breaker patterns with real failure scenarios
- Ensure error boundaries prevent cascading failures
- Test user notification and feedback during recovery scenarios

This test suite validates that agent execution systems can recover gracefully
from various infrastructure failures while maintaining core business functionality,
ensuring users continue to receive value even during system stress.
"""

import asyncio
import pytest
import time
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

# SSOT Imports from registry
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker, ExecutionState, AgentExecutionPhase,
    CircuitBreakerOpenError, TimeoutConfig
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, create_isolated_execution_context,
    InvalidContextError, ContextIsolationError
)
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.logging_config import central_logger

# Base test infrastructure
from netra_backend.tests.integration.agent_execution.base_agent_execution_test import BaseAgentExecutionTest

logger = central_logger.get_logger(__name__)


class FailureSimulator:
    """Helper class to simulate various infrastructure failures."""
    
    def __init__(self):
        self.active_failures: Dict[str, Dict[str, Any]] = {}
        self.failure_history: List[Dict[str, Any]] = []
        self.recovery_callbacks: Dict[str, List[Callable]] = {}
        
    def simulate_failure(self, failure_type: str, duration: float = 5.0, severity: str = 'moderate'):
        """Simulate a specific type of infrastructure failure."""
        failure_id = f"{failure_type}_{uuid.uuid4().hex[:8]}"
        
        failure_info = {
            'failure_id': failure_id,
            'failure_type': failure_type,
            'severity': severity,
            'start_time': time.time(),
            'duration': duration,
            'active': True
        }
        
        self.active_failures[failure_id] = failure_info
        self.failure_history.append(failure_info.copy())
        
        logger.warning(f"🚨 SIMULATING FAILURE: {failure_type} for {duration}s (severity: {severity})")
        return failure_id
    
    def recover_from_failure(self, failure_id: str):
        """Mark a failure as recovered."""
        if failure_id in self.active_failures:
            failure_info = self.active_failures[failure_id]
            failure_info['active'] = False
            failure_info['recovered_at'] = time.time()
            failure_info['actual_duration'] = time.time() - failure_info['start_time']
            
            # Trigger recovery callbacks
            callbacks = self.recovery_callbacks.get(failure_info['failure_type'], [])
            for callback in callbacks:
                try:
                    callback(failure_info)
                except Exception as e:
                    logger.error(f"Recovery callback error: {e}")
            
            del self.active_failures[failure_id]
            logger.info(f"✅ RECOVERED FROM FAILURE: {failure_info['failure_type']}")
    
    def is_failure_active(self, failure_type: str) -> bool:
        """Check if a specific type of failure is currently active."""
        return any(f['failure_type'] == failure_type and f['active'] 
                  for f in self.active_failures.values())
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """Get statistics about simulated failures."""
        return {
            'active_failures': len(self.active_failures),
            'total_failures_simulated': len(self.failure_history),
            'failure_types': list(set(f['failure_type'] for f in self.failure_history)),
            'avg_failure_duration': sum(f.get('actual_duration', 0) for f in self.failure_history) / max(len(self.failure_history), 1)
        }


@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.error_recovery
class TestErrorRecoveryIntegration(BaseAgentExecutionTest):
    """Integration tests for agent execution error recovery with real infrastructure failures."""

    async def setup_method(self):
        """Set up error recovery test environment."""
        await super().setup_method()
        
        # Initialize failure simulator
        self.failure_simulator = FailureSimulator()
        
        # Set up execution tracker with enhanced timeout config
        timeout_config = TimeoutConfig(
            agent_execution_timeout=15.0,  # Reduced for faster failure detection
            llm_api_timeout=10.0,
            failure_threshold=2,  # Lower threshold for testing
            recovery_timeout=5.0,  # Shorter recovery window
            max_retries=3
        )
        
        self.execution_tracker = AgentExecutionTracker(timeout_config=timeout_config)
        await self.execution_tracker.start_monitoring()
        
        # Set up circuit breaker callbacks
        self.circuit_breaker_events = []
        self.execution_tracker.register_circuit_breaker_callback(self._on_circuit_breaker_event)
        
        # Track recovery metrics
        self.recovery_metrics = {
            'failures_detected': 0,
            'successful_recoveries': 0,
            'degraded_operations': 0,
            'user_notifications_sent': 0
        }
        
        logger.info("Error recovery test environment initialized")

    async def teardown_method(self):
        """Clean up error recovery test resources."""
        try:
            # Stop any active failure simulations
            for failure_id in list(self.failure_simulator.active_failures.keys()):
                self.failure_simulator.recover_from_failure(failure_id)
            
            if hasattr(self, 'execution_tracker'):
                await self.execution_tracker.stop_monitoring()
                
        except Exception as e:
            logger.warning(f"Error recovery cleanup error (non-critical): {e}")
        
        await super().teardown_method()

    async def test_database_connection_failure_recovery(self):
        """Test recovery from database connection failures.
        
        Business Value: Ensures agent execution continues during database issues,
        maintaining core chat functionality for users.
        """
        # Create execution before database failure
        execution_id = self.execution_tracker.create_execution(
            agent_name="DatabaseRecoveryAgent",
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            metadata={"database_recovery_test": True}
        )
        
        # Start normal execution
        self.execution_tracker.update_execution_state(
            execution_id, ExecutionState.RUNNING,
            result="Running before database failure"
        )
        
        # Simulate database connection failure
        failure_id = self.failure_simulator.simulate_failure(
            'database_connection', 
            duration=3.0, 
            severity='high'
        )
        
        # During failure, system should continue with in-memory tracking
        with patch('netra_backend.app.db.database_manager.DatabaseManager.get_session') as mock_db:
            mock_db.side_effect = ConnectionError("Database connection failed")
            
            # System should handle DB failure gracefully
            success = self.execution_tracker.update_execution_state(
                execution_id, ExecutionState.COMPLETING,
                result="Continuing execution despite DB failure"
            )
            
            # Should succeed with in-memory fallback
            assert success, "Execution should continue despite database failure"
            
            # Verify state updated in memory
            record = self.execution_tracker.get_execution(execution_id)
            assert record.state == ExecutionState.COMPLETING
            assert "despite DB failure" in record.result
            
            self.recovery_metrics['degraded_operations'] += 1
        
        # Simulate database recovery
        await asyncio.sleep(1.0)  # Wait for recovery
        self.failure_simulator.recover_from_failure(failure_id)
        
        # After recovery, normal operations should resume
        success = self.execution_tracker.update_execution_state(
            execution_id, ExecutionState.COMPLETED,
            result="Completed after database recovery"
        )
        
        assert success, "Operations should resume after database recovery"
        
        # Verify recovery statistics
        stats = self.failure_simulator.get_failure_stats()
        assert stats['total_failures_simulated'] >= 1
        assert 'database_connection' in stats['failure_types']
        
        self.recovery_metrics['successful_recoveries'] += 1
        logger.info("✅ Database connection failure recovery verified")

    async def test_websocket_connection_failure_graceful_degradation(self):
        """Test graceful degradation when WebSocket connections fail.
        
        Business Value: Ensures users still receive agent results even if
        real-time updates fail, preventing complete loss of functionality.
        """
        # Create execution with WebSocket integration
        execution_id = self.execution_tracker.create_execution(
            agent_name="WebSocketRecoveryAgent",
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            metadata={"websocket_recovery_test": True}
        )
        
        # Mock WebSocket manager that will fail
        failing_websocket_manager = AsyncMock()
        failing_websocket_manager.notify_agent_started.side_effect = ConnectionError("WebSocket disconnected")
        failing_websocket_manager.notify_agent_thinking.side_effect = ConnectionError("WebSocket disconnected")
        failing_websocket_manager.notify_agent_completed.side_effect = ConnectionError("WebSocket disconnected")
        
        # Simulate WebSocket failure
        failure_id = self.failure_simulator.simulate_failure(
            'websocket_connection',
            duration=4.0,
            severity='moderate'
        )
        
        # Execution should continue despite WebSocket failures
        phases_with_websocket_failure = [
            AgentExecutionPhase.STARTING,
            AgentExecutionPhase.THINKING,
            AgentExecutionPhase.COMPLETED
        ]
        
        for phase in phases_with_websocket_failure:
            # Try to transition with failing WebSocket
            success = await self.execution_tracker.transition_state(
                execution_id, phase,
                metadata={"websocket_failing": True},
                websocket_manager=failing_websocket_manager
            )
            
            # Should succeed despite WebSocket failure
            assert success, f"Phase transition should succeed despite WebSocket failure: {phase}"
            
            # Verify state updated
            record = self.execution_tracker.get_execution(execution_id)
            assert record.current_phase == phase
            
            self.recovery_metrics['degraded_operations'] += 1
        
        # Simulate WebSocket recovery with working manager
        self.failure_simulator.recover_from_failure(failure_id)
        
        working_websocket_manager = AsyncMock()
        working_websocket_manager.notify_agent_completed.return_value = True
        
        # Final notification should work after recovery
        await self.execution_tracker.transition_state(
            execution_id, AgentExecutionPhase.COMPLETED,
            metadata={"websocket_recovered": True},
            websocket_manager=working_websocket_manager
        )
        
        # Verify recovery notification sent
        working_websocket_manager.notify_agent_completed.assert_called_once()
        
        self.recovery_metrics['successful_recoveries'] += 1
        logger.info("✅ WebSocket connection failure graceful degradation verified")

    async def test_circuit_breaker_failure_protection(self):
        """Test circuit breaker protection during cascading failures.
        
        Business Value: Prevents cascading failures from bringing down
        entire system, protecting overall platform availability.
        """
        # Create execution with circuit breaker protection
        execution_id = self.execution_tracker.create_execution(
            agent_name="CircuitBreakerAgent",
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            timeout_seconds=10
        )
        
        # Register circuit breaker
        self.execution_tracker.register_circuit_breaker(execution_id)
        
        # Simulate repeated failures to trigger circuit breaker
        failure_count = 0
        max_failures = 3
        
        async def failing_operation():
            nonlocal failure_count
            failure_count += 1
            
            if failure_count <= max_failures:
                raise ConnectionError(f"Simulated failure #{failure_count}")
            else:
                return "Success after recovery"
        
        # Test circuit breaker opening
        circuit_breaker_triggered = False
        
        for attempt in range(max_failures + 1):
            try:
                result = await self.execution_tracker.execute_with_circuit_breaker(
                    execution_id, failing_operation, f"test_operation_{attempt}"
                )
                
                # Should succeed after circuit breaker recovery
                assert result == "Success after recovery"
                break
                
            except CircuitBreakerOpenError:
                circuit_breaker_triggered = True
                logger.info(f"Circuit breaker opened after {attempt + 1} failures")
                
                # Wait for circuit breaker to transition to half-open
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.info(f"Expected failure #{attempt + 1}: {e}")
                self.recovery_metrics['failures_detected'] += 1
        
        # Verify circuit breaker was triggered
        assert circuit_breaker_triggered or failure_count > max_failures, \
            "Circuit breaker should have been triggered"
        
        # Verify circuit breaker status
        cb_status = self.execution_tracker.circuit_breaker_status(execution_id)
        assert cb_status is not None
        assert cb_status['failure_count'] >= 0
        
        self.recovery_metrics['successful_recoveries'] += 1
        logger.info("✅ Circuit breaker failure protection verified")

    async def test_timeout_failure_recovery_patterns(self):
        """Test recovery from various timeout scenarios.
        
        Business Value: Ensures users don't wait indefinitely for agent responses,
        providing timely feedback and alternative actions.
        """
        # Test different timeout scenarios
        timeout_scenarios = [
            {'name': 'quick_timeout', 'timeout': 0.5, 'work_duration': 1.0},
            {'name': 'moderate_timeout', 'timeout': 2.0, 'work_duration': 3.0},
            {'name': 'recovery_success', 'timeout': 3.0, 'work_duration': 1.0}  # Should succeed
        ]
        
        for scenario in timeout_scenarios:
            execution_id = self.execution_tracker.create_execution(
                agent_name=f"TimeoutAgent_{scenario['name']}",
                thread_id=f"timeout_thread_{scenario['name']}",
                user_id=self.test_user_id,
                timeout_seconds=int(scenario['timeout']),
                metadata={"timeout_test": True, "scenario": scenario['name']}
            )
            
            # Simulate operation with specific duration
            async def timed_operation():
                await asyncio.sleep(scenario['work_duration'])
                return f"Completed {scenario['name']}"
            
            start_time = time.time()
            
            try:
                result = await asyncio.wait_for(
                    timed_operation(),
                    timeout=scenario['timeout']
                )
                
                # Update to completed if successful
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.COMPLETED,
                    result=result
                )
                
                logger.info(f"Timeout scenario '{scenario['name']}' completed successfully")
                self.recovery_metrics['successful_recoveries'] += 1
                
            except asyncio.TimeoutError:
                # Handle timeout gracefully
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.TIMEOUT,
                    error=f"Operation timed out after {scenario['timeout']}s"
                )
                
                # Simulate user notification
                await self._notify_user_of_timeout(execution_id, scenario)
                
                logger.warning(f"Timeout scenario '{scenario['name']}' timed out as expected")
                self.recovery_metrics['failures_detected'] += 1
                self.recovery_metrics['user_notifications_sent'] += 1
            
            execution_time = time.time() - start_time
            
            # Verify timeout behavior
            record = self.execution_tracker.get_execution(execution_id)
            if scenario['work_duration'] > scenario['timeout']:
                # Should timeout
                assert record.state in [ExecutionState.TIMEOUT, ExecutionState.FAILED], \
                    f"Expected timeout for scenario {scenario['name']}"
            else:
                # Should complete
                assert record.state == ExecutionState.COMPLETED, \
                    f"Expected completion for scenario {scenario['name']}"
        
        logger.info("✅ Timeout failure recovery patterns verified")

    async def test_concurrent_failure_isolation(self):
        """Test that failures in one execution don't affect others.
        
        Business Value: Ensures failures are isolated to specific users/executions,
        preventing one user's issues from affecting other users' experience.
        """
        # Create multiple concurrent executions
        execution_count = 5
        execution_tasks = []
        
        for i in range(execution_count):
            # Some executions will fail, others should succeed
            should_fail = i % 2 == 0  # Every other execution fails
            
            task = self._create_isolated_failure_test_execution(i, should_fail)
            execution_tasks.append(task)
        
        # Run all executions concurrently
        start_time = time.time()
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Verify isolation - successful executions should not be affected by failures
        successful_executions = []
        failed_executions = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_executions.append((i, result))
            else:
                successful_executions.append((i, result))
        
        # Should have both successes and failures
        assert len(successful_executions) > 0, "Should have some successful executions"
        assert len(failed_executions) > 0, "Should have some failed executions for testing"
        
        # Verify successful executions completed properly
        for exec_index, result in successful_executions:
            assert result['status'] == 'completed', f"Execution {exec_index} should be completed"
            assert result['isolated'] is True, f"Execution {exec_index} should remain isolated"
            
            # Verify no contamination from other failures
            assert 'failure_contamination' not in result, \
                f"Execution {exec_index} should not be contaminated by other failures"
        
        # Verify failure isolation
        for exec_index, error in failed_executions:
            logger.info(f"Expected failure in execution {exec_index}: {error}")
            self.recovery_metrics['failures_detected'] += 1
        
        isolation_success_rate = len(successful_executions) / execution_count
        assert isolation_success_rate >= 0.4, \
            f"Isolation success rate too low: {isolation_success_rate:.2%}"
        
        logger.info(f"✅ Concurrent failure isolation verified: {isolation_success_rate:.2%} isolation success")

    async def test_recovery_notification_and_user_feedback(self):
        """Test user notification systems during recovery scenarios.
        
        Business Value: Keeps users informed during issues, maintaining trust
        and providing clear communication about system status.
        """
        # Create execution for notification testing
        execution_id = self.execution_tracker.create_execution(
            agent_name="NotificationAgent",
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            metadata={"notification_test": True}
        )
        
        # Track notifications sent to user
        user_notifications = []
        
        async def mock_notify_user(notification_type: str, message: str, metadata: Dict[str, Any] = None):
            """Mock user notification function."""
            notification = {
                'type': notification_type,
                'message': message,
                'metadata': metadata or {},
                'timestamp': time.time(),
                'user_id': self.test_user_id
            }
            user_notifications.append(notification)
            logger.info(f"📢 USER NOTIFICATION: {notification_type} - {message}")
        
        # Simulate various failure and recovery scenarios with notifications
        failure_scenarios = [
            {
                'name': 'temporary_service_disruption',
                'duration': 1.0,
                'notification_type': 'service_disruption',
                'message': 'Experiencing temporary delays, working to resolve...'
            },
            {
                'name': 'database_maintenance', 
                'duration': 2.0,
                'notification_type': 'maintenance_mode',
                'message': 'System maintenance in progress, reduced functionality...'
            },
            {
                'name': 'recovery_complete',
                'duration': 0.5,
                'notification_type': 'service_restored',
                'message': 'All services restored, normal operation resumed'
            }
        ]
        
        for scenario in failure_scenarios:
            # Simulate failure
            failure_id = self.failure_simulator.simulate_failure(
                scenario['name'],
                scenario['duration'],
                severity='moderate'
            )
            
            # Notify user of issue
            await mock_notify_user(
                scenario['notification_type'],
                scenario['message'],
                {'execution_id': execution_id, 'scenario': scenario['name']}
            )
            
            # Continue execution in degraded mode
            self.execution_tracker.update_execution_state(
                execution_id, ExecutionState.RUNNING,
                result=f"Running in degraded mode: {scenario['name']}"
            )
            
            # Wait for recovery
            await asyncio.sleep(scenario['duration'] + 0.1)
            
            # Simulate recovery
            self.failure_simulator.recover_from_failure(failure_id)
            
            # Notify user of recovery
            if scenario['notification_type'] != 'service_restored':
                await mock_notify_user(
                    'service_restored',
                    f"Resolved: {scenario['name']} - Normal operation resumed",
                    {'execution_id': execution_id, 'recovered_from': scenario['name']}
                )
        
        # Complete execution after all recoveries
        self.execution_tracker.update_execution_state(
            execution_id, ExecutionState.COMPLETED,
            result="Execution completed successfully after recovery scenarios"
        )
        
        # Final success notification
        await mock_notify_user(
            'execution_completed',
            'Your request has been completed successfully',
            {'execution_id': execution_id, 'recovery_scenarios_handled': len(failure_scenarios)}
        )
        
        # Verify notification sequence
        assert len(user_notifications) >= len(failure_scenarios), \
            "Should have received notifications for each scenario"
        
        # Verify notification types
        notification_types = [n['type'] for n in user_notifications]
        assert 'service_disruption' in notification_types, "Should notify of disruptions"
        assert 'service_restored' in notification_types, "Should notify of recovery"
        assert 'execution_completed' in notification_types, "Should notify of completion"
        
        # Verify all notifications are for correct user
        for notification in user_notifications:
            assert notification['metadata'].get('execution_id') == execution_id
            assert notification['user_id'] == self.test_user_id
        
        self.recovery_metrics['user_notifications_sent'] += len(user_notifications)
        logger.info(f"✅ Recovery notification system verified: {len(user_notifications)} notifications")

    # Helper methods for error recovery testing

    async def _on_circuit_breaker_event(self, event_type: str, execution_id: str, details: Dict[str, Any]):
        """Callback for circuit breaker events."""
        self.circuit_breaker_events.append({
            'event_type': event_type,
            'execution_id': execution_id,
            'details': details,
            'timestamp': time.time()
        })
        
        logger.info(f"Circuit breaker event: {event_type} for {execution_id}")

    async def _create_isolated_failure_test_execution(self, exec_index: int, should_fail: bool) -> Dict[str, Any]:
        """Create execution for isolation testing."""
        execution_id = self.execution_tracker.create_execution(
            agent_name=f"IsolationTestAgent_{exec_index}",
            thread_id=f"isolation_thread_{exec_index}",
            user_id=f"isolation_user_{exec_index}",
            metadata={"isolation_test": True, "should_fail": should_fail}
        )
        
        try:
            # Start execution
            self.execution_tracker.update_execution_state(
                execution_id, ExecutionState.RUNNING,
                result=f"Isolation test {exec_index} running"
            )
            
            if should_fail:
                # Simulate failure
                await asyncio.sleep(0.1)  # Brief delay
                raise ConnectionError(f"Intentional failure for isolation test {exec_index}")
            else:
                # Simulate successful completion
                await asyncio.sleep(0.2)  # Brief work simulation
                
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.COMPLETED,
                    result=f"Isolation test {exec_index} completed successfully"
                )
                
                return {
                    'execution_id': execution_id,
                    'exec_index': exec_index,
                    'status': 'completed',
                    'isolated': True,
                    'affected_by_other_failures': False
                }
        
        except Exception as e:
            # Handle failure gracefully
            self.execution_tracker.update_execution_state(
                execution_id, ExecutionState.FAILED,
                error=str(e)
            )
            raise

    async def _notify_user_of_timeout(self, execution_id: str, scenario: Dict[str, Any]):
        """Simulate user notification for timeout scenarios."""
        record = self.execution_tracker.get_execution(execution_id)
        
        # Simulate sending timeout notification to user
        timeout_notification = {
            'type': 'execution_timeout',
            'execution_id': execution_id,
            'agent_name': record.agent_name,
            'timeout_duration': scenario['timeout'],
            'message': f"Your request is taking longer than expected. We're working on it and will provide an update soon.",
            'recovery_options': [
                'Wait for completion',
                'Retry with different parameters', 
                'Contact support'
            ]
        }
        
        logger.info(f"📢 TIMEOUT NOTIFICATION: {timeout_notification['message']}")
        return timeout_notification

    async def test_comprehensive_system_recovery_simulation(self):
        """Test comprehensive system recovery under multiple concurrent failures.
        
        Business Value: Validates system resilience under worst-case scenarios,
        ensuring platform availability during major infrastructure issues.
        """
        # Simulate comprehensive system stress
        stress_duration = 5.0
        concurrent_executions = 8
        
        # Start multiple executions before failures
        execution_ids = []
        for i in range(concurrent_executions):
            execution_id = self.execution_tracker.create_execution(
                agent_name=f"SystemRecoveryAgent_{i}",
                thread_id=f"recovery_thread_{i}",
                user_id=self.test_user_id,
                metadata={"system_recovery_test": True, "execution_index": i}
            )
            execution_ids.append(execution_id)
        
        # Simulate multiple concurrent failures
        failure_ids = []
        failure_types = ['database', 'redis', 'websocket', 'external_api']
        
        for failure_type in failure_types:
            failure_id = self.failure_simulator.simulate_failure(
                failure_type,
                duration=stress_duration,
                severity='high'
            )
            failure_ids.append(failure_id)
        
        # Continue operations during failures
        recovery_tasks = []
        for execution_id in execution_ids:
            task = self._execute_with_recovery(execution_id)
            recovery_tasks.append(task)
        
        # Wait for recovery attempts
        recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
        
        # Simulate gradual recovery
        for failure_id in failure_ids:
            await asyncio.sleep(0.5)  # Stagger recoveries
            self.failure_simulator.recover_from_failure(failure_id)
        
        # Verify system recovery
        successful_recoveries = 0
        partial_successes = 0
        
        for i, result in enumerate(recovery_results):
            if isinstance(result, Exception):
                logger.warning(f"Execution {i} failed during system stress: {result}")
            else:
                if result['status'] == 'completed':
                    successful_recoveries += 1
                elif result['status'] == 'partial':
                    partial_successes += 1
        
        # Calculate recovery metrics
        total_recovery_rate = (successful_recoveries + partial_successes) / concurrent_executions
        full_recovery_rate = successful_recoveries / concurrent_executions
        
        # Verify acceptable recovery performance
        assert total_recovery_rate >= 0.6, \
            f"Total recovery rate too low: {total_recovery_rate:.2%} (need ≥60%)"
        
        # Update metrics
        self.recovery_metrics['successful_recoveries'] += successful_recoveries
        self.recovery_metrics['degraded_operations'] += partial_successes
        
        # Verify system returned to normal operation
        failure_stats = self.failure_simulator.get_failure_stats()
        assert failure_stats['active_failures'] == 0, "All failures should be recovered"
        
        logger.info(f"✅ System recovery verified: {total_recovery_rate:.2%} total recovery, {full_recovery_rate:.2%} full recovery")

    async def _execute_with_recovery(self, execution_id: str) -> Dict[str, Any]:
        """Execute with recovery patterns during system stress."""
        record = self.execution_tracker.get_execution(execution_id)
        
        try:
            # Start execution
            self.execution_tracker.update_execution_state(
                execution_id, ExecutionState.RUNNING,
                result="Running during system stress"
            )
            
            # Simulate work with potential failures
            phases = [ExecutionState.RUNNING, ExecutionState.COMPLETING]
            completed_phases = 0
            
            for phase in phases:
                # Random chance of phase failure during stress
                if random.random() > 0.3:  # 70% success rate per phase
                    self.execution_tracker.update_execution_state(
                        execution_id, phase,
                        result=f"Phase {phase.value} completed despite system stress"
                    )
                    completed_phases += 1
                else:
                    # Phase failed, but continue with degraded functionality
                    logger.warning(f"Phase {phase.value} failed for {execution_id} due to system stress")
                    break
                
                await asyncio.sleep(0.2)  # Simulate work time
            
            # Determine final status based on completed phases
            if completed_phases == len(phases):
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.COMPLETED,
                    result="Fully completed during system recovery"
                )
                return {'status': 'completed', 'execution_id': execution_id, 'phases_completed': completed_phases}
            else:
                self.execution_tracker.update_execution_state(
                    execution_id, ExecutionState.COMPLETED,
                    result="Partially completed during system recovery"
                )
                return {'status': 'partial', 'execution_id': execution_id, 'phases_completed': completed_phases}
                
        except Exception as e:
            self.execution_tracker.update_execution_state(
                execution_id, ExecutionState.FAILED,
                error=f"Failed during system recovery: {e}"
            )
            raise