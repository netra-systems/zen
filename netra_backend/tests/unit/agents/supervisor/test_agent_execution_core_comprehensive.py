"""
Comprehensive Unit Tests for AgentExecutionCore - MEGA CLASS Coverage

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Enterprise - Core chat functionality protecting $500K+ ARR
- Goal: System Stability & User Experience - Ensure reliable agent execution
- Value Impact: Prevents silent agent failures that break customer AI interactions
- Revenue Impact: Protects 90% of platform value (chat functionality)

CRITICAL MODULE: AgentExecutionCore handles the core execution lifecycle for agents,
including timeout management, user context isolation, WebSocket events, and error recovery.
This is the backbone of the chat experience that delivers primary business value.

TEST CATEGORIES:
1. Core Business Logic: Agent execution flow, state transitions
2. User Isolation: Context validation, factory pattern compliance
3. Error Handling: Timeout management, graceful degradation, circuit breakers
4. Performance: Resource limits, execution monitoring
5. Integration Points: WebSocket events, execution tracking, persistence

SSOT COMPLIANCE: Uses test_framework.ssot.base_test_case for unified test infrastructure.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import UUID, uuid4

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# System Under Test
from netra_backend.app.agents.supervisor.agent_execution_core import (
    AgentExecutionCore,
    get_agent_state_tracker
)

# Dependencies
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.execution_tracker import ExecutionState
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker,
    AgentExecutionPhase,
    CircuitBreakerOpenError
)
from netra_backend.app.core.unified_trace_context import UnifiedTraceContext


@pytest.mark.unit
@pytest.mark.agent_execution
class TestAgentExecutionCoreBusinessLogic(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Core agent execution flow validation
    
    Tests the primary execution path that enables customer chat interactions.
    Validates state transitions, timeout handling, and business critical events.
    """
    
    async def asyncSetUp(self):
        """Set up test fixtures with proper user context isolation."""
        await super().asyncSetUp()
        
        # Mock dependencies
        self.mock_registry = MagicMock()
        self.mock_websocket_bridge = AsyncMock()
        self.mock_agent = AsyncMock()
        
        # Create system under test
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Test data
        self.test_user_id = "test-user-123"
        self.test_thread_id = "thread-456"
        self.test_run_id = uuid4()
        self.test_agent_name = "test-agent"
        
        self.execution_context = AgentExecutionContext(
            agent_name=self.test_agent_name,
            run_id=str(self.test_run_id),
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            correlation_id="corr-789"
        )
        
        self.user_context = UserExecutionContext.create_for_user(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=str(self.test_run_id)
        )
    
    async def test_successful_agent_execution_delivers_business_value(self):
        """
        BUSINESS CRITICAL: Validates complete successful agent execution flow
        
        This test ensures that when an agent executes successfully:
        1. WebSocket events are sent for user visibility
        2. Execution tracking captures all phases
        3. Business metrics are collected
        4. User receives meaningful agent response
        """
        # Arrange: Set up successful agent execution
        expected_result = AgentExecutionResult(
            success=True,
            agent_name=self.test_agent_name,
            duration=2.5,
            data={"message": "Agent provided valuable insights on customer's AI optimization needs"},
            metadata={
                "business_value": "high", 
                "customer_satisfaction": 95
            }
        )
        
        self.mock_agent.run.return_value = expected_result
        self.mock_registry.get_agent.return_value = self.mock_agent
        
        # Mock execution tracking
        mock_exec_id = uuid4()
        with patch.object(self.execution_core.execution_tracker, 'register_execution', return_value=mock_exec_id):
            with patch.object(self.execution_core.execution_tracker, 'start_execution'):
                with patch.object(self.execution_core.execution_tracker, 'complete_execution'):
                    with patch.object(self.execution_core.agent_tracker, 'create_execution', return_value="state-exec-123"):
                        with patch.object(self.execution_core.agent_tracker, 'start_execution', return_value=True):
                            with patch.object(self.execution_core.agent_tracker, 'transition_state'):
                                
                                # Act: Execute agent
                                result = await self.execution_core.execute_agent(
                                    context=self.execution_context,
                                    state=self.user_context,
                                    timeout=30.0
                                )
        
        # Assert: Verify business value delivery
        self.assertTrue(result.success, "Agent execution must succeed for business value")
        self.assertIn("valuable insights", result.data.get("message", ""), "Agent must provide substantive value")
        
        # Verify WebSocket events sent for user experience
        self.mock_websocket_bridge.notify_agent_started.assert_called_once()
        
        # Verify agent was executed with proper context
        self.mock_agent.run.assert_called_once()
        
        # Verify execution tracking captured business metrics
        self.execution_core.execution_tracker.register_execution.assert_called_once()
        
    async def test_agent_not_found_error_provides_graceful_degradation(self):
        """
        BUSINESS CRITICAL: When agent is not found, system must gracefully degrade
        
        This prevents silent failures that would break customer chat experience.
        """
        # Arrange: Agent not in registry
        self.mock_registry.get_agent.return_value = None
        
        mock_exec_id = uuid4()
        with patch.object(self.execution_core.execution_tracker, 'register_execution', return_value=mock_exec_id):
            with patch.object(self.execution_core.execution_tracker, 'start_execution'):
                with patch.object(self.execution_core.execution_tracker, 'complete_execution'):
                    with patch.object(self.execution_core.agent_tracker, 'create_execution', return_value="state-exec-123"):
                        with patch.object(self.execution_core.agent_tracker, 'start_execution', return_value=True):
                            with patch.object(self.execution_core.agent_tracker, 'transition_state'):
                                with patch.object(self.execution_core.agent_tracker, 'update_execution_state'):
                                    
                                    # Act: Attempt to execute non-existent agent
                                    result = await self.execution_core.execute_agent(
                                        context=self.execution_context,
                                        state=self.user_context
                                    )
        
        # Assert: Graceful error handling
        self.assertFalse(result.success, "Should indicate failure for missing agent")
        self.assertIn("not found", result.error, "Error message should be informative")
        
        # Verify execution marked as failed
        self.execution_core.agent_tracker.update_execution_state.assert_called_with(
            "state-exec-123", ExecutionState.FAILED
        )
    
    async def test_timeout_handling_prevents_hanging_user_sessions(self):
        """
        BUSINESS CRITICAL: Timeout prevents agents from hanging and blocking chat
        
        Long-running agents without timeouts block users from receiving responses,
        directly impacting the 90% chat value delivery.
        """
        # Arrange: Agent that hangs
        async def hanging_agent(*args, **kwargs):
            await asyncio.sleep(100)  # Simulates hanging
            
        self.mock_agent.run.side_effect = hanging_agent
        self.mock_registry.get_agent.return_value = self.mock_agent
        
        mock_exec_id = uuid4()
        with patch.object(self.execution_core.execution_tracker, 'register_execution', return_value=mock_exec_id):
            with patch.object(self.execution_core.execution_tracker, 'start_execution'):
                with patch.object(self.execution_core.execution_tracker, 'complete_execution'):
                    with patch.object(self.execution_core.agent_tracker, 'create_execution', return_value="state-exec-123"):
                        with patch.object(self.execution_core.agent_tracker, 'start_execution', return_value=True):
                            with patch.object(self.execution_core.agent_tracker, 'transition_state'):
                                
                                # Act: Execute with short timeout
                                start_time = time.time()
                                result = await self.execution_core.execute_agent(
                                    context=self.execution_context,
                                    state=self.user_context,
                                    timeout=0.1  # 100ms timeout
                                )
                                execution_time = time.time() - start_time
        
        # Assert: Execution completed quickly due to timeout
        self.assertLess(execution_time, 1.0, "Should timeout quickly to unblock user")
        self.assertFalse(result.success, "Timeout should result in failure")
        self.assertIn("timeout", result.error.lower(), "Should indicate timeout occurred")


@pytest.mark.unit
@pytest.mark.user_isolation
class TestAgentExecutionCoreUserIsolation(SSotAsyncTestCase):
    """
    BUSINESS VALUE: User context isolation validation
    
    Ensures proper user isolation prevents data leakage between concurrent users.
    Critical for Enterprise customers and compliance requirements.
    """
    
    async def asyncSetUp(self):
        """Set up test fixtures for user isolation testing."""
        await super().asyncSetUp()
        
        self.mock_registry = MagicMock()
        self.mock_websocket_bridge = AsyncMock()
        
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
    
    async def test_user_execution_context_isolation_validation(self):
        """
        ENTERPRISE CRITICAL: Validates proper user context isolation
        
        Each user's agent execution must be completely isolated to prevent
        data leakage that would violate Enterprise security requirements.
        """
        # Arrange: Two different user contexts
        user1_context = UserExecutionContext.create_for_user(
            user_id="enterprise-user-1",
            thread_id="thread-1",
            run_id=str(uuid4())
        )
        
        user2_context = UserExecutionContext.create_for_user(
            user_id="enterprise-user-2", 
            thread_id="thread-2",
            run_id=str(uuid4())
        )
        
        # Act: Process both contexts
        result1_context = self.execution_core._ensure_user_execution_context(
            state=user1_context,
            context=AgentExecutionContext(
                agent_name="test-agent",
                run_id=uuid4(),
                thread_id="thread-1"
            )
        )
        
        result2_context = self.execution_core._ensure_user_execution_context(
            state=user2_context,
            context=AgentExecutionContext(
                agent_name="test-agent",
                run_id=uuid4(),
                thread_id="thread-2"
            )
        )
        
        # Assert: Complete isolation maintained
        self.assertNotEqual(result1_context.user_id, result2_context.user_id)
        self.assertNotEqual(result1_context.thread_id, result2_context.thread_id)
        self.assertNotEqual(result1_context.run_id, result2_context.run_id)
        
        # Verify context data doesn't cross-contaminate
        self.assertEqual(result1_context.user_id, "enterprise-user-1")
        self.assertEqual(result2_context.user_id, "enterprise-user-2")
    
    async def test_deprecated_deep_agent_state_migration_with_security_warning(self):
        """
        SECURITY CRITICAL: Validates migration from insecure DeepAgentState
        
        DeepAgentState creates user isolation risks. This test ensures proper
        migration to secure UserExecutionContext with appropriate warnings.
        """
        # Arrange: Legacy DeepAgentState (insecure)
        legacy_state = DeepAgentState()
        legacy_state.user_id = "legacy-user"
        legacy_state.thread_id = "legacy-thread"
        legacy_state.run_id = "legacy-run"
        legacy_state.user_request = "Legacy user request"
        
        context = AgentExecutionContext(
            agent_name="migration-test-agent",
            run_id=uuid4(),
            thread_id="legacy-thread"
        )
        
        # Act: Migrate to secure context (should trigger warning)
        with self.assertWarns(DeprecationWarning) as warning_context:
            secure_context = self.execution_core._ensure_user_execution_context(
                state=legacy_state,
                context=context
            )
        
        # Assert: Proper security migration
        self.assertIsInstance(secure_context, UserExecutionContext)
        self.assertEqual(secure_context.user_id, "legacy-user")
        self.assertIn("USER ISOLATION RISKS", str(warning_context.warning))
        self.assertIn("data leakage", str(warning_context.warning))
        
        # Verify audit trail for security compliance
        self.assertIn("migration_source", secure_context.audit_metadata)
        self.assertEqual(secure_context.audit_metadata["migration_source"], "DeepAgentState")
    
    async def test_concurrent_user_execution_isolation(self):
        """
        ENTERPRISE CRITICAL: Multiple users executing simultaneously must be isolated
        
        Validates that concurrent agent executions for different users don't
        share state or interfere with each other.
        """
        # Arrange: Multiple concurrent user executions
        self.mock_registry.get_agent.return_value = AsyncMock()
        
        user_contexts = [
            UserExecutionContext.create_for_user(f"user-{i}", f"thread-{i}", str(uuid4()))
            for i in range(5)
        ]
        
        execution_contexts = [
            AgentExecutionContext(
                agent_name="concurrent-agent",
                run_id=uuid4(),
                thread_id=f"thread-{i}"
            )
            for i in range(5)
        ]
        
        # Mock execution infrastructure
        with patch.object(self.execution_core.execution_tracker, 'register_execution', return_value=uuid4()):
            with patch.object(self.execution_core.execution_tracker, 'start_execution'):
                with patch.object(self.execution_core.execution_tracker, 'complete_execution'):
                    with patch.object(self.execution_core.agent_tracker, 'create_execution', side_effect=[f"exec-{i}" for i in range(5)]):
                        with patch.object(self.execution_core.agent_tracker, 'start_execution', return_value=True):
                            with patch.object(self.execution_core.agent_tracker, 'transition_state'):
                                
                                # Act: Execute all users concurrently
                                tasks = [
                                    self.execution_core.execute_agent(
                                        context=execution_contexts[i],
                                        state=user_contexts[i],
                                        timeout=1.0
                                    )
                                    for i in range(5)
                                ]
                                
                                results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert: All executions completed independently
        self.assertEqual(len(results), 5)
        
        # Verify each user got isolated execution tracking
        self.assertEqual(self.execution_core.agent_tracker.create_execution.call_count, 5)
        
        # Verify no cross-user contamination in calls
        create_calls = self.execution_core.agent_tracker.create_execution.call_args_list
        user_ids = [call.kwargs['user_id'] for call in create_calls]
        self.assertEqual(len(set(user_ids)), 5, "Each user should have unique execution")


@pytest.mark.unit
@pytest.mark.error_handling
class TestAgentExecutionCoreErrorHandling(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Error recovery and resilience
    
    Validates error boundaries, circuit breakers, and graceful degradation
    to maintain system stability under failure conditions.
    """
    
    async def asyncSetUp(self):
        """Set up error handling test fixtures."""
        await super().asyncSetUp()
        
        self.mock_registry = MagicMock()
        self.mock_websocket_bridge = AsyncMock()
        
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        self.user_context = UserExecutionContext.create_for_user(
            user_id="error-test-user",
            thread_id="error-thread",
            run_id=str(uuid4())
        )
        
        self.execution_context = AgentExecutionContext(
            agent_name="error-agent",
            run_id=uuid4(),
            thread_id="error-thread"
        )
    
    async def test_agent_execution_exception_graceful_recovery(self):
        """
        BUSINESS CRITICAL: Agent exceptions must not crash the system
        
        Individual agent failures should be contained and not affect
        other users or system stability.
        """
        # Arrange: Agent that throws exception
        self.mock_registry.get_agent.return_value = self.mock_agent = AsyncMock()
        self.mock_agent.run.side_effect = ValueError("Agent processing error")
        
        mock_exec_id = uuid4()
        with patch.object(self.execution_core.execution_tracker, 'register_execution', return_value=mock_exec_id):
            with patch.object(self.execution_core.execution_tracker, 'start_execution'):
                with patch.object(self.execution_core.execution_tracker, 'complete_execution'):
                    with patch.object(self.execution_core.agent_tracker, 'create_execution', return_value="error-exec-123"):
                        with patch.object(self.execution_core.agent_tracker, 'start_execution', return_value=True):
                            with patch.object(self.execution_core.agent_tracker, 'transition_state'):
                                
                                # Act: Execute failing agent
                                result = await self.execution_core.execute_agent(
                                    context=self.execution_context,
                                    state=self.user_context
                                )
        
        # Assert: Graceful error handling
        self.assertFalse(result.success, "Should indicate failure")
        self.assertIn("Agent processing error", result.error)
        
        # Verify execution was properly cleaned up
        self.execution_core.execution_tracker.complete_execution.assert_called()
    
    async def test_circuit_breaker_prevents_cascade_failures(self):
        """
        BUSINESS CRITICAL: Circuit breaker prevents system overload
        
        When agents consistently fail, circuit breaker should open to
        prevent resource exhaustion and maintain system stability.
        """
        # Arrange: Circuit breaker in open state
        with patch.object(self.execution_core.agent_tracker, 'create_execution') as mock_create:
            mock_create.side_effect = CircuitBreakerOpenError("Circuit breaker open due to high failure rate")
            
            # Act: Attempt execution with open circuit breaker
            result = await self.execution_core.execute_agent(
                context=self.execution_context,
                state=self.user_context
            )
        
        # Assert: Circuit breaker protection
        self.assertFalse(result.success)
        self.assertIn("Circuit breaker", result.error)
        
        # Verify no agent execution attempted
        self.mock_registry.get_agent.assert_not_called()
    
    async def test_websocket_notification_failure_isolation(self):
        """
        BUSINESS CRITICAL: WebSocket failures must not break agent execution
        
        If WebSocket notifications fail, the agent should still execute and
        return results, maintaining core business value delivery.
        """
        # Arrange: WebSocket bridge that fails
        self.mock_websocket_bridge.notify_agent_started.side_effect = Exception("WebSocket connection lost")
        self.mock_registry.get_agent.return_value = self.mock_agent = AsyncMock()
        self.mock_agent.run.return_value = AgentExecutionResult(
            success=True,
            result="Agent completed successfully despite WebSocket issues"
        )
        
        mock_exec_id = uuid4()
        with patch.object(self.execution_core.execution_tracker, 'register_execution', return_value=mock_exec_id):
            with patch.object(self.execution_core.execution_tracker, 'start_execution'):
                with patch.object(self.execution_core.execution_tracker, 'complete_execution'):
                    with patch.object(self.execution_core.agent_tracker, 'create_execution', return_value="ws-test-123"):
                        with patch.object(self.execution_core.agent_tracker, 'start_execution', return_value=True):
                            with patch.object(self.execution_core.agent_tracker, 'transition_state'):
                                
                                # Act: Execute with failing WebSocket
                                result = await self.execution_core.execute_agent(
                                    context=self.execution_context,
                                    state=self.user_context
                                )
        
        # Assert: Agent execution succeeded despite WebSocket failure
        self.assertTrue(result.success, "Agent execution should succeed despite WebSocket issues")
        self.assertIn("completed successfully", result.result)
        
        # Verify agent was still executed
        self.mock_agent.run.assert_called_once()


@pytest.mark.unit
@pytest.mark.performance
class TestAgentExecutionCorePerformance(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Performance and resource management
    
    Validates execution timing, resource limits, and performance monitoring
    to ensure system can handle production load efficiently.
    """
    
    async def asyncSetUp(self):
        """Set up performance test fixtures."""
        await super().asyncSetUp()
        
        self.mock_registry = MagicMock()
        self.mock_websocket_bridge = AsyncMock()
        
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
    
    async def test_execution_timeout_configuration_business_impact(self):
        """
        BUSINESS CRITICAL: Timeout configuration affects user experience
        
        Default timeout must balance allowing complex AI processing while
        preventing users from waiting too long for responses.
        """
        # Assert: Business-appropriate default timeout
        self.assertEqual(self.execution_core.DEFAULT_TIMEOUT, 25.0, 
                        "Default timeout should be 25s for balance of AI processing vs user experience")
        
        # Assert: Heartbeat interval for user progress visibility
        self.assertEqual(self.execution_core.HEARTBEAT_INTERVAL, 5.0,
                        "Heartbeat every 5s provides regular user progress updates")
    
    async def test_metrics_collection_enables_business_insights(self):
        """
        BUSINESS CRITICAL: Performance metrics enable optimization decisions
        
        Execution metrics must be collected to understand agent performance
        and guide optimization efforts for better customer experience.
        """
        # Arrange: Mock metrics collection
        with patch.object(self.execution_core, '_collect_metrics') as mock_collect:
            with patch.object(self.execution_core, '_persist_metrics') as mock_persist:
                
                # Mock successful execution
                mock_metrics = {
                    'execution_time': 2.5,
                    'memory_usage': 150.5,
                    'cpu_usage': 45.2,
                    'websocket_events_sent': 5,
                    'business_value_score': 95
                }
                mock_collect.return_value = mock_metrics
                
                # Act: Trigger metrics calculation
                result_metrics = self.execution_core._calculate_performance_metrics(
                    start_time=time.time() - 2.5,
                    end_time=time.time(),
                    success=True,
                    context=AgentExecutionContext(
                        agent_name="metrics-agent",
                        run_id=uuid4(),
                        thread_id="metrics-thread"
                    )
                )
        
        # Assert: Business-relevant metrics captured
        self.assertIn('execution_time', result_metrics)
        self.assertIn('resource_efficiency', result_metrics)
        self.assertIn('business_impact', result_metrics)
        
        # Verify metrics support business decisions
        self.assertIsInstance(result_metrics['execution_time'], (int, float))
        self.assertIn('agent_name', result_metrics)


@pytest.mark.unit
@pytest.mark.integration_points
class TestAgentExecutionCoreIntegrationPoints(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Integration reliability
    
    Validates proper integration with WebSocket events, execution tracking,
    and persistence systems that support the complete chat experience.
    """
    
    async def asyncSetUp(self):
        """Set up integration test fixtures."""
        await super().asyncSetUp()
        
        self.mock_registry = MagicMock()
        self.mock_websocket_bridge = AsyncMock()
        
        self.execution_core = AgentExecutionCore(
            registry=self.mock_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
    
    async def test_websocket_event_delivery_sequence_business_critical(self):
        """
        BUSINESS CRITICAL: WebSocket events provide real-time user experience
        
        The sequence of WebSocket events (agent_started, agent_thinking, etc.)
        is critical for user engagement and perceived system responsiveness.
        """
        # Arrange: Mock successful agent execution
        self.mock_registry.get_agent.return_value = self.mock_agent = AsyncMock()
        self.mock_agent.run.return_value = AgentExecutionResult(success=True, result="Success")
        
        user_context = UserExecutionContext.create_for_user("ws-user", "ws-thread", str(uuid4()))
        execution_context = AgentExecutionContext(
            agent_name="websocket-agent",
            run_id=uuid4(),
            thread_id="ws-thread"
        )
        
        mock_exec_id = uuid4()
        with patch.object(self.execution_core.execution_tracker, 'register_execution', return_value=mock_exec_id):
            with patch.object(self.execution_core.execution_tracker, 'start_execution'):
                with patch.object(self.execution_core.execution_tracker, 'complete_execution'):
                    with patch.object(self.execution_core.agent_tracker, 'create_execution', return_value="ws-exec-123"):
                        with patch.object(self.execution_core.agent_tracker, 'start_execution', return_value=True):
                            with patch.object(self.execution_core.agent_tracker, 'transition_state'):
                                
                                # Act: Execute agent
                                await self.execution_core.execute_agent(
                                    context=execution_context,
                                    state=user_context
                                )
        
        # Assert: WebSocket events sent for user experience
        self.mock_websocket_bridge.notify_agent_started.assert_called_once_with(
            run_id=execution_context.run_id,
            agent_name="websocket-agent",
            context={"status": "starting", "phase": "initialization"}
        )
        
        # Verify state transitions include WebSocket manager
        transition_calls = self.execution_core.agent_tracker.transition_state.call_args_list
        websocket_transitions = [call for call in transition_calls if 'websocket_manager' in call.kwargs]
        self.assertGreater(len(websocket_transitions), 0, "WebSocket manager should be passed to state transitions")
    
    async def test_execution_tracking_integration_business_monitoring(self):
        """
        BUSINESS CRITICAL: Execution tracking enables system monitoring
        
        Proper integration with execution tracking provides visibility into
        system health and agent performance for business operations.
        """
        # Arrange: Mock tracking integration
        user_context = UserExecutionContext.create_for_user("tracking-user", "tracking-thread", str(uuid4()))
        execution_context = AgentExecutionContext(
            agent_name="tracking-agent",
            run_id=uuid4(),
            thread_id="tracking-thread"
        )
        
        mock_exec_id = uuid4()
        mock_state_exec_id = "state-tracking-123"
        
        with patch.object(self.execution_core.execution_tracker, 'register_execution', return_value=mock_exec_id) as mock_register:
            with patch.object(self.execution_core.execution_tracker, 'start_execution') as mock_start:
                with patch.object(self.execution_core.agent_tracker, 'create_execution', return_value=mock_state_exec_id) as mock_create:
                    with patch.object(self.execution_core.agent_tracker, 'start_execution', return_value=True) as mock_state_start:
                        
                        # Mock agent execution
                        self.mock_registry.get_agent.return_value = self.mock_agent = AsyncMock()
                        self.mock_agent.run.return_value = AgentExecutionResult(success=True)
                        
                        with patch.object(self.execution_core.agent_tracker, 'transition_state'):
                            
                            # Act: Execute with tracking
                            await self.execution_core.execute_agent(
                                context=execution_context,
                                state=user_context,
                                timeout=30.0
                            )
        
        # Assert: Proper tracking integration
        mock_register.assert_called_once_with(
            agent_name="tracking-agent",
            correlation_id=pytest.unordered.Any(),
            thread_id="tracking-thread", 
            user_id="tracking-user",
            timeout_seconds=30.0
        )
        
        mock_create.assert_called_once_with(
            agent_name="tracking-agent",
            thread_id="tracking-thread",
            user_id="tracking-user", 
            timeout_seconds=30.0,
            metadata=pytest.unordered.Any()
        )
        
        mock_start.assert_called_once_with(mock_exec_id)
        mock_state_start.assert_called_once_with(mock_state_exec_id)


@pytest.mark.unit
@pytest.mark.compatibility
class TestAgentExecutionCoreCompatibility(SSotAsyncTestCase):
    """
    BUSINESS VALUE: Legacy support during migration
    
    Validates backward compatibility functions and migration paths
    to ensure system stability during SSOT transitions.
    """
    
    async def test_get_agent_state_tracker_deprecation_warning(self):
        """
        MIGRATION CRITICAL: Legacy function provides compatibility with deprecation warning
        
        Ensures legacy code continues working while guiding migration to new patterns.
        """
        # Act: Call legacy function
        with self.assertWarns(DeprecationWarning) as warning_context:
            tracker = get_agent_state_tracker()
        
        # Assert: Proper deprecation guidance
        self.assertIsNotNone(tracker, "Should return valid tracker for compatibility")
        self.assertIn("deprecated", str(warning_context.warning))
        self.assertIn("get_execution_tracker", str(warning_context.warning))
    
    async def test_unsupported_state_type_validation(self):
        """
        VALIDATION CRITICAL: Invalid state types should be rejected clearly
        
        Clear error messages help developers understand required patterns.
        """
        # Arrange: Invalid state type
        invalid_state = {"invalid": "state"}
        
        execution_context = AgentExecutionContext(
            agent_name="validation-agent",
            run_id=uuid4(),
            thread_id="validation-thread"
        )
        
        execution_core = AgentExecutionCore(
            registry=MagicMock(),
            websocket_bridge=AsyncMock()
        )
        
        # Act & Assert: Clear validation error
        with self.assertRaises(ValueError) as error_context:
            execution_core._ensure_user_execution_context(invalid_state, execution_context)
        
        self.assertIn("Unsupported state type", str(error_context.exception))
        self.assertIn("UserExecutionContext", str(error_context.exception))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])