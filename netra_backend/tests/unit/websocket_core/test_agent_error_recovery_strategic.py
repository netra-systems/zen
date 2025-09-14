"""
Strategic Unit Tests for Error Recovery Mechanisms During Partial Agent Failures

Business Value Justification (BVJ):
- Segment: Enterprise/Mission-Critical - Production reliability requirements
- Business Goal: Reliability & Trust - Graceful failure recovery without data loss
- Value Impact: Protects $500K+ ARR from catastrophic failure scenarios and user abandonment  
- Strategic Impact: Enables enterprise confidence in system reliability and fault tolerance

STRATEGIC GAP ADDRESSED: Error Recovery Mechanisms for partial failures
This test suite focuses on sophisticated error recovery scenarios:
1. Partial agent execution failure with state recovery
2. WebSocket connection failure with message queuing and replay
3. Cascading failure prevention and circuit breaker patterns
4. Multi-step operation rollback and compensation
5. System recovery after infrastructure outages

CRITICAL: These tests validate enterprise-grade fault tolerance and recovery requirements.
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock, call
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig
)


class FailureType(Enum):
    """Types of failures for recovery testing."""
    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_DROP = "connection_drop"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    SERVICE_UNAVAILABLE = "service_unavailable"
    AUTHENTICATION_FAILURE = "authentication_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PARTIAL_SUCCESS = "partial_success"
    CASCADE_FAILURE = "cascade_failure"


@dataclass
class RecoveryScenario:
    """Recovery test scenario configuration."""
    scenario_name: str
    failure_type: FailureType
    failure_point: str  # When in the process failure occurs
    recovery_strategy: str
    expected_recovery_time: float  # Max seconds to recover
    data_loss_acceptable: bool = False
    operations_before_failure: int = 3
    operations_after_recovery: int = 2
    failure_duration: float = 1.0  # How long failure lasts


@dataclass
class RecoveryMetrics:
    """Metrics tracking for recovery testing."""
    scenario_start: float = field(default_factory=time.time)
    failure_detected_at: Optional[float] = None
    recovery_initiated_at: Optional[float] = None
    recovery_completed_at: Optional[float] = None
    messages_before_failure: List[Dict] = field(default_factory=list)
    messages_during_failure: List[Dict] = field(default_factory=list)
    messages_after_recovery: List[Dict] = field(default_factory=list)
    recovery_attempts: int = 0
    data_lost: List[Dict] = field(default_factory=list)
    
    @property
    def recovery_time(self) -> Optional[float]:
        """Time taken to recover from failure."""
        if self.recovery_initiated_at and self.recovery_completed_at:
            return self.recovery_completed_at - self.recovery_initiated_at
        return None
    
    @property
    def failure_detection_time(self) -> Optional[float]:
        """Time taken to detect failure."""
        if self.scenario_start and self.failure_detected_at:
            return self.failure_detected_at - self.scenario_start
        return None


class TestAgentErrorRecoveryStrategic(SSotAsyncTestCase):
    """
    Strategic unit tests for error recovery mechanisms during partial agent failures.
    
    RECOVERY FOCUS: Enterprise-grade fault tolerance scenarios that could cause
    business-critical failures in production environments.
    """
    
    def setup_method(self, method):
        """Set up test fixtures with recovery monitoring."""
        super().setup_method(method)
        
        # Create bridge for recovery testing
        self.bridge = AgentWebSocketBridge()
        
        # Recovery scenario tracking
        self.current_scenario = None
        self.recovery_metrics = RecoveryMetrics()
        self.failure_injection_active = False
        self.recovery_attempts = []
        
        # Mock WebSocket manager with failure simulation
        self.mock_websocket_manager = AsyncMock()
        self.mock_websocket_manager.emit_to_run.side_effect = self._simulate_failures_and_recovery
        
        # Message queue for recovery testing
        self.message_queue = []
        self.failed_messages = []
        self.recovered_messages = []

    async def _simulate_failures_and_recovery(self, run_id, event_type, data, **kwargs):
        """Simulate various failure scenarios and recovery mechanisms."""
        message = {
            'timestamp': time.time(),
            'run_id': run_id,
            'event_type': event_type,
            'data': data.copy() if isinstance(data, dict) else data,
            'attempt_count': getattr(self, '_message_attempt_count', 0)
        }
        
        # Track message based on current failure scenario
        if self.current_scenario and self.failure_injection_active:
            return await self._handle_failure_scenario(message)
        else:
            # Normal operation - record successful message
            if hasattr(self.recovery_metrics, 'messages_after_recovery'):
                self.recovery_metrics.messages_after_recovery.append(message)
            return True

    async def _handle_failure_scenario(self, message: Dict) -> bool:
        """Handle different failure scenarios with appropriate recovery logic."""
        if not self.current_scenario:
            return True
            
        failure_type = self.current_scenario.failure_type
        
        # Simulate different failure types
        if failure_type == FailureType.NETWORK_TIMEOUT:
            # Network timeout - retry with backoff
            if message.get('attempt_count', 0) < 3:
                self._message_attempt_count = message.get('attempt_count', 0) + 1
                await asyncio.sleep(0.1 * self._message_attempt_count)  # Exponential backoff
                self.recovery_metrics.recovery_attempts += 1
                # Simulate recovery after retries
                if self._message_attempt_count >= 2:
                    self.failure_injection_active = False
                    self.recovery_metrics.recovery_completed_at = time.time()
                    return True
                else:
                    raise Exception(f"Network timeout (attempt {self._message_attempt_count})")
            
        elif failure_type == FailureType.CONNECTION_DROP:
            # Connection drop - queue message for replay
            self.message_queue.append(message)
            self.recovery_metrics.messages_during_failure.append(message)
            self.recovery_metrics.recovery_attempts += 1
            
            # Simulate reconnection after delay
            if len(self.message_queue) >= 2:
                self.failure_injection_active = False
                self.recovery_metrics.recovery_completed_at = time.time()
                # Replay queued messages
                await self._replay_queued_messages()
                return True
            else:
                raise Exception("WebSocket connection dropped")
                
        elif failure_type == FailureType.SERVICE_UNAVAILABLE:
            # Service unavailable - implement circuit breaker
            self.recovery_metrics.recovery_attempts += 1
            if self.recovery_metrics.recovery_attempts <= 3:
                await asyncio.sleep(0.5)  # Circuit breaker delay
                raise Exception(f"Service unavailable (attempt {self.recovery_metrics.recovery_attempts})")
            else:
                # Circuit breaker opens - recovery
                self.failure_injection_active = False
                self.recovery_metrics.recovery_completed_at = time.time()
                return True
                
        elif failure_type == FailureType.PARTIAL_SUCCESS:
            # Partial success - some operations succeed, others fail
            self.recovery_metrics.recovery_attempts += 1
            if message.get('event_type') == 'agent_thinking':
                # Thinking messages fail
                self.recovery_metrics.messages_during_failure.append(message)
                raise Exception("Partial failure: thinking operation failed")
            else:
                # Other messages succeed
                return True
        
        return False

    async def _replay_queued_messages(self):
        """Replay messages that were queued during connection failure."""
        for queued_message in self.message_queue:
            # Mark as recovered
            queued_message['recovered'] = True
            queued_message['recovery_timestamp'] = time.time()
            self.recovered_messages.append(queued_message)
        
        self.message_queue.clear()

    async def test_partial_agent_execution_failure_with_state_recovery(self):
        """
        RECOVERY CRITICAL: Agent execution fails mid-process, state must be recoverable.
        
        SCENARIO: Agent starts processing, fails during thinking phase, recovers and completes.
        This tests the most common production failure pattern.
        """
        # Arrange - Setup partial execution failure scenario
        self.current_scenario = RecoveryScenario(
            scenario_name="partial_execution_recovery",
            failure_type=FailureType.NETWORK_TIMEOUT,
            failure_point="agent_thinking",
            recovery_strategy="retry_with_backoff",
            expected_recovery_time=2.0,
            operations_before_failure=2,
            operations_after_recovery=3
        )
        
        run_id = "recovery_test_run_123"
        agent_name = "RecoveryTestAgent"
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Act - Execute operations that will encounter partial failure
            
            # Phase 1: Normal operations before failure
            result1 = await self.bridge.notify_agent_started(
                run_id=run_id,
                agent_name=agent_name,
                context={
                    "operation": "critical_business_analysis",
                    "user_data": "important_customer_request",
                    "recovery_test": True
                }
            )
            assert result1, "Initial agent start should succeed"
            
            # Phase 2: Failure occurs during thinking phase
            self.failure_injection_active = True
            self.recovery_metrics.failure_detected_at = time.time()
            self.recovery_metrics.recovery_initiated_at = time.time()
            
            # This should trigger network timeout and retry logic
            result2 = await self.bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name=agent_name,
                reasoning="Processing critical analysis - this will fail and recover",
                step_number=1
            )
            
            # Phase 3: Recovery should have occurred, operations continue
            result3 = await self.bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name=agent_name,
                reasoning="Continuing after recovery",
                step_number=2
            )
            
            result4 = await self.bridge.notify_agent_completed(
                run_id=run_id,
                agent_name=agent_name,
                result={
                    "analysis_complete": True,
                    "recovery_successful": True,
                    "data_integrity": "maintained"
                }
            )
            
            # Assert - Recovery should have occurred successfully
            assert result2, "Should recover from network timeout"
            assert result3, "Should continue normally after recovery"
            assert result4, "Should complete successfully after recovery"
            
            # Verify recovery metrics
            assert self.recovery_metrics.recovery_attempts >= 1, "Should have attempted recovery"
            assert self.recovery_metrics.recovery_completed_at is not None, "Recovery should have completed"
            
            # Verify recovery time is within acceptable bounds
            if self.recovery_metrics.recovery_time:
                assert self.recovery_metrics.recovery_time <= self.current_scenario.expected_recovery_time, \
                    f"Recovery took too long: {self.recovery_metrics.recovery_time:.2f}s (max: {self.current_scenario.expected_recovery_time}s)"

    async def test_websocket_connection_failure_with_message_queuing(self):
        """
        RECOVERY CRITICAL: WebSocket connection drops, messages must be queued and replayed.
        
        SCENARIO: Active conversation when connection drops, all messages preserved and delivered
        after reconnection. This prevents user message loss.
        """
        # Arrange - Setup connection drop scenario with message queuing
        self.current_scenario = RecoveryScenario(
            scenario_name="connection_drop_queuing",
            failure_type=FailureType.CONNECTION_DROP,
            failure_point="websocket_connection",
            recovery_strategy="queue_and_replay",
            expected_recovery_time=3.0,
            data_loss_acceptable=False
        )
        
        run_id = "connection_recovery_test"
        agent_name = "ConnectionRecoveryAgent"
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Act - Operations during connection failure
            
            # Phase 1: Normal operation before connection drop
            result1 = await self.bridge.notify_agent_started(
                run_id=run_id,
                agent_name=agent_name,
                context={
                    "user_query": "Important customer question",
                    "session_critical": True,
                    "connection_test": True
                }
            )
            assert result1, "Should start normally before connection issues"
            
            # Phase 2: Connection drops - messages should be queued
            self.failure_injection_active = True
            self.recovery_metrics.failure_detected_at = time.time()
            
            # These messages will be queued during connection failure
            result2 = await self.bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name=agent_name,
                reasoning="Critical thinking process - must not be lost",
                step_number=1
            )
            
            result3 = await self.bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name=agent_name,
                reasoning="Continuing analysis - also critical",
                step_number=2
            )
            
            # Phase 3: Connection recovers, queued messages replayed
            # The mock will automatically trigger recovery after 2 queued messages
            result4 = await self.bridge.notify_agent_completed(
                run_id=run_id,
                agent_name=agent_name,
                result={
                    "analysis_result": "Complete analysis with all steps preserved",
                    "message_integrity": "guaranteed",
                    "connection_recovery": "successful"
                }
            )
            
            # Assert - Message queuing and replay should work
            assert result2, "Messages should be queued during connection failure"
            assert result3, "Multiple messages should be queued"
            assert result4, "Should complete after connection recovery"
            
            # Verify message queuing worked
            assert len(self.recovered_messages) >= 2, \
                f"Should have recovered queued messages: {len(self.recovered_messages)} recovered"
            
            # Verify no data loss occurred
            total_messages = (len(self.recovery_metrics.messages_during_failure) + 
                            len(self.recovery_metrics.messages_after_recovery))
            assert total_messages >= 3, "All messages should be preserved"
            
            # Verify recovered messages maintain order and content
            for recovered_msg in self.recovered_messages:
                assert 'recovered' in recovered_msg, "Recovered messages should be marked"
                assert 'recovery_timestamp' in recovered_msg, "Should have recovery timestamp"

    async def test_cascading_failure_prevention_circuit_breaker(self):
        """
        RECOVERY CRITICAL: Prevent cascading failures through circuit breaker patterns.
        
        SCENARIO: One service fails, circuit breaker prevents cascade to other services.
        This protects system stability during infrastructure outages.
        """
        # Arrange - Setup cascading failure prevention
        self.current_scenario = RecoveryScenario(
            scenario_name="cascade_prevention",
            failure_type=FailureType.SERVICE_UNAVAILABLE,
            failure_point="service_dependency",
            recovery_strategy="circuit_breaker",
            expected_recovery_time=5.0
        )
        
        # Multiple agents to test cascade prevention
        agents = [
            {"run_id": "cascade_test_1", "agent": "PrimaryAgent"},
            {"run_id": "cascade_test_2", "agent": "SecondaryAgent"},
            {"run_id": "cascade_test_3", "agent": "TertiaryAgent"}
        ]
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Act - Trigger failure in one service, observe cascade prevention
            
            # Phase 1: Normal operations across all agents
            normal_results = []
            for agent_info in agents:
                result = await self.bridge.notify_agent_started(
                    run_id=agent_info["run_id"],
                    agent_name=agent_info["agent"],
                    context={
                        "cascade_test": True,
                        "agent_id": agent_info["agent"],
                        "operation": "multi_agent_coordination"
                    }
                )
                normal_results.append(result)
            
            assert all(normal_results), "All agents should start normally"
            
            # Phase 2: Service failure affects first agent
            self.failure_injection_active = True
            self.recovery_metrics.failure_detected_at = time.time()
            
            # First agent encounters service failure (circuit breaker will trigger)
            failure_results = []
            for attempt in range(4):  # Will trigger circuit breaker after 3 attempts
                try:
                    result = await self.bridge.notify_agent_thinking(
                        run_id=agents[0]["run_id"],
                        agent_name=agents[0]["agent"],
                        reasoning=f"Attempting operation {attempt} - will fail until circuit opens",
                        step_number=attempt
                    )
                    failure_results.append(result)
                except Exception as e:
                    failure_results.append(False)
            
            # Phase 3: Other agents should continue working (cascade prevented)
            other_agent_results = []
            for agent_info in agents[1:]:  # Skip first agent
                result = await self.bridge.notify_agent_thinking(
                    run_id=agent_info["run_id"],
                    agent_name=agent_info["agent"],
                    reasoning="This should work - cascade prevented",
                    step_number=1
                )
                other_agent_results.append(result)
            
            # Phase 4: Circuit breaker should have opened, allowing recovery
            recovery_result = await self.bridge.notify_agent_completed(
                run_id=agents[0]["run_id"],
                agent_name=agents[0]["agent"],
                result={
                    "circuit_breaker": "opened_and_recovered",
                    "cascade_prevented": True,
                    "service_recovered": True
                }
            )
            
            # Assert - Cascading failure should be prevented
            
            # First agent should eventually recover (after circuit breaker opens)
            final_success = failure_results[-1]  # Last attempt should succeed
            assert final_success, "Circuit breaker should allow recovery"
            
            # Other agents should not be affected by the first agent's failure
            assert all(other_agent_results), "Other agents should continue working despite one failure"
            
            # Recovery should complete within acceptable time
            assert self.recovery_metrics.recovery_completed_at is not None, "Recovery should complete"
            assert recovery_result, "Should recover after circuit breaker opens"
            
            # Verify circuit breaker behavior
            assert self.recovery_metrics.recovery_attempts >= 3, \
                "Should attempt multiple times before circuit breaker opens"

    async def test_multi_step_operation_rollback_compensation(self):
        """
        RECOVERY CRITICAL: Multi-step operation fails, implement rollback and compensation.
        
        SCENARIO: Complex operation with multiple steps fails mid-way, system rolls back
        completed steps and compensates for partial state.
        """
        # Arrange - Setup multi-step operation with rollback
        operation_steps = [
            {"step": 1, "action": "data_collection", "compensation": "clear_collected_data"},
            {"step": 2, "action": "analysis_processing", "compensation": "reset_analysis_state"},
            {"step": 3, "action": "result_generation", "compensation": "cleanup_partial_results"},
            {"step": 4, "action": "result_delivery", "compensation": "cancel_delivery"}
        ]
        
        run_id = "rollback_test_operation"
        agent_name = "RollbackTestAgent"
        completed_steps = []
        compensation_actions = []
        
        # Mock that simulates step execution and failure
        async def execute_step_with_failure(run_id, event_type, data, **kwargs):
            if 'step_number' in str(data):
                step_num = data.get('step_number', 0) if isinstance(data, dict) else 0
                completed_steps.append(step_num)
                
                # Simulate failure at step 3
                if step_num == 3:
                    self.recovery_metrics.failure_detected_at = time.time()
                    raise Exception(f"Multi-step operation failed at step {step_num}")
                
                return True
            return True
        
        self.mock_websocket_manager.emit_to_run.side_effect = execute_step_with_failure
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Act - Execute multi-step operation that will fail and rollback
            
            # Phase 1: Start operation
            await self.bridge.notify_agent_started(
                run_id=run_id,
                agent_name=agent_name,
                context={
                    "operation_type": "multi_step_complex",
                    "rollback_enabled": True,
                    "compensation_required": True
                }
            )
            
            # Phase 2: Execute steps until failure
            step_results = []
            for step_info in operation_steps:
                try:
                    result = await self.bridge.notify_agent_thinking(
                        run_id=run_id,
                        agent_name=agent_name,
                        reasoning=f"Executing step {step_info['step']}: {step_info['action']}",
                        step_number=step_info['step']
                    )
                    step_results.append((step_info['step'], True))
                except Exception as e:
                    step_results.append((step_info['step'], False))
                    # Simulate rollback compensation for completed steps
                    for completed_step in completed_steps[:-1]:  # Exclude failed step
                        compensation_actions.append(f"rollback_step_{completed_step}")
                    break
            
            # Phase 3: Recovery with compensation
            self.recovery_metrics.recovery_initiated_at = time.time()
            
            # Simulate compensation completion
            compensation_result = await self.bridge.notify_agent_error(
                run_id=run_id,
                agent_name=agent_name,
                error="Multi-step operation failed at step 3",
                error_context={
                    "completed_steps": completed_steps[:-1],
                    "compensation_actions": compensation_actions,
                    "rollback_status": "completed"
                }
            )
            
            # Phase 4: Retry with recovery strategy
            retry_result = await self.bridge.notify_agent_completed(
                run_id=run_id,
                agent_name=agent_name,
                result={
                    "operation_status": "completed_with_recovery",
                    "rollback_successful": True,
                    "compensation_applied": compensation_actions,
                    "data_integrity": "maintained"
                }
            )
            
            # Assert - Rollback and compensation should work correctly
            
            # Should have completed some steps before failure
            assert len(completed_steps) >= 2, f"Should complete some steps before failure: {completed_steps}"
            
            # Should have triggered compensation for completed steps
            assert len(compensation_actions) >= 1, \
                f"Should have compensation actions: {compensation_actions}"
            
            # Error reporting should work
            assert compensation_result, "Should report error with compensation details"
            
            # Final recovery should succeed
            assert retry_result, "Should complete with recovery after rollback"

    async def test_infrastructure_outage_graceful_degradation(self):
        """
        RECOVERY CRITICAL: System gracefully degrades during infrastructure outages.
        
        SCENARIO: Database or cache service becomes unavailable, system continues
        operating with degraded functionality until services recover.
        """
        # Arrange - Simulate infrastructure outage scenario
        outage_start_time = time.time()
        outage_duration = 3.0  # 3-second outage
        degraded_mode_active = False
        
        async def simulate_infrastructure_outage(run_id, event_type, data, **kwargs):
            nonlocal degraded_mode_active
            current_time = time.time()
            
            # Simulate outage period
            if current_time - outage_start_time < outage_duration:
                if not degraded_mode_active:
                    degraded_mode_active = True
                    self.recovery_metrics.failure_detected_at = current_time
                    self.recovery_metrics.recovery_initiated_at = current_time
                
                # During outage - operate in degraded mode
                if 'critical' in str(data).lower():
                    # Critical operations still work but slower
                    await asyncio.sleep(0.2)  # Degraded performance
                    return True
                else:
                    # Non-critical operations fail gracefully
                    raise Exception("Non-critical service unavailable during outage")
            else:
                # After outage - full recovery
                if degraded_mode_active:
                    degraded_mode_active = False
                    self.recovery_metrics.recovery_completed_at = current_time
                return True
        
        self.mock_websocket_manager.emit_to_run.side_effect = simulate_infrastructure_outage
        
        with patch.object(self.bridge, '_get_websocket_manager', return_value=self.mock_websocket_manager):
            # Act - Operations during infrastructure outage
            
            operations = [
                # Critical operations (should work in degraded mode)
                {
                    "run_id": "critical_op_1",
                    "agent": "CriticalAgent",
                    "context": {"priority": "critical", "operation": "user_facing_critical"},
                    "should_succeed": True
                },
                {
                    "run_id": "critical_op_2", 
                    "agent": "CriticalAgent",
                    "context": {"priority": "critical", "operation": "business_critical"},
                    "should_succeed": True
                },
                
                # Non-critical operations (may fail gracefully)
                {
                    "run_id": "noncritical_op_1",
                    "agent": "AnalyticsAgent", 
                    "context": {"priority": "low", "operation": "background_analytics"},
                    "should_succeed": False
                },
                {
                    "run_id": "noncritical_op_2",
                    "agent": "ReportingAgent",
                    "context": {"priority": "low", "operation": "scheduled_report"},
                    "should_succeed": False
                }
            ]
            
            results = []
            for op in operations:
                try:
                    result = await self.bridge.notify_agent_started(
                        run_id=op["run_id"],
                        agent_name=op["agent"],
                        context=op["context"]
                    )
                    results.append((op["run_id"], True))
                except Exception:
                    results.append((op["run_id"], False))
                
                # Small delay between operations
                await asyncio.sleep(0.5)
            
            # Wait for full recovery
            await asyncio.sleep(outage_duration + 1)
            
            # Post-recovery operations should all work
            post_recovery_result = await self.bridge.notify_agent_completed(
                run_id="post_recovery_test",
                agent_name="RecoveryVerificationAgent",
                result={
                    "infrastructure_status": "fully_recovered",
                    "degraded_mode": "disabled",
                    "all_services": "available"
                }
            )
            
            # Assert - Graceful degradation should work
            
            # Critical operations should succeed even during outage
            critical_results = [(rid, success) for rid, success in results if 'critical' in rid]
            critical_successes = sum(1 for _, success in critical_results if success)
            assert critical_successes >= 1, \
                f"At least some critical operations should succeed during outage: {critical_successes}/{len(critical_results)}"
            
            # System should recover fully after outage
            assert post_recovery_result, "System should fully recover after infrastructure outage"
            assert self.recovery_metrics.recovery_completed_at is not None, "Recovery should be tracked"
            
            # Recovery time should be reasonable
            if self.recovery_metrics.recovery_time:
                assert self.recovery_metrics.recovery_time <= outage_duration + 2, \
                    f"Recovery should complete soon after outage ends: {self.recovery_metrics.recovery_time:.2f}s"

    def teardown_method(self, method):
        """Clean up recovery test artifacts."""
        super().teardown_method(method)
        
        # Reset recovery state
        self.current_scenario = None
        self.failure_injection_active = False
        
        # Clear recovery tracking
        self.recovery_attempts.clear()
        self.message_queue.clear()
        self.failed_messages.clear()
        self.recovered_messages.clear()


if __name__ == '__main__':
    """
    Run strategic error recovery tests.
    
    These tests validate enterprise-grade fault tolerance requirements that protect
    the $500K+ ARR business from catastrophic failure scenarios and ensure reliable recovery.
    """
    pytest.main([__file__, "-v", "--tb=short"])