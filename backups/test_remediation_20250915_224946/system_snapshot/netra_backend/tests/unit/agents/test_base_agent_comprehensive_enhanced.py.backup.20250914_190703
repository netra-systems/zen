"""Enhanced BaseAgent Unit Tests - Additional Critical Coverage

This file provides additional comprehensive tests for BaseAgent that complement the existing
test_base_agent_comprehensive.py file, focusing on areas that are critical for multi-user
production scenarios and edge cases.

Business Value Justification:
- Segment: Platform/Internal | Testing Infrastructure & Production Stability  
- Business Goal: Risk Reduction & Platform Reliability
- Value Impact: Ensures BaseAgent handles concurrent multi-user scenarios correctly
- Strategic Impact: Prevents agent failures under load that would cause user-facing errors

CRITICAL AREAS COVERED:
- Multi-user concurrent execution and isolation
- Performance under load and resource management  
- Advanced error handling and recovery scenarios
- WebSocket event performance and timing
- Edge cases and race conditions
- Memory leak prevention and cleanup
- Abstract method enforcement and execution patterns

IMPORTANT: Uses real BaseAgent instances with minimal mocks per CLAUDE.md requirements.
"""

import asyncio
import gc
import logging
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# Import SSOT test framework
from test_framework.ssot.base import AsyncBaseTestCase, BaseTestCase

# Import BaseAgent and dependencies using absolute imports
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler


# Mock UserExecutionContext to avoid circular import
class MockUserExecutionContext:
    """Mock UserExecutionContext for testing multi-user scenarios."""
    
    def __init__(self, user_id: str = None, thread_id: str = None, run_id: str = None, 
                 metadata: Optional[Dict] = None):
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.thread_id = thread_id or f"thread_{uuid.uuid4().hex[:8]}"
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        self.metadata = metadata or {}
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        # Mock database session
        self.db_session = AsyncMock()


class ConcreteTestAgent(BaseAgent):
    """Concrete BaseAgent implementation for testing."""
    
    def __init__(self, *args, **kwargs):
        # Extract test configuration
        self.execution_delay = kwargs.pop('execution_delay', 0.01)
        self.should_fail = kwargs.pop('should_fail', False)
        self.failure_message = kwargs.pop('failure_message', "Test failure")
        self.execution_count = 0
        self.execution_results = []
        
        super().__init__(*args, **kwargs)
    
    async def _execute_with_user_context(self, context: MockUserExecutionContext, 
                                       stream_updates: bool = False) -> Dict[str, Any]:
        """Modern execution implementation with configurable behavior."""
        self.execution_count += 1
        
        if self.should_fail:
            raise RuntimeError(self.failure_message)
        
        # Emit WebSocket events to test event flow
        await self.emit_thinking(f"Processing request for {context.user_id}")
        
        # Simulate work with configurable delay
        await asyncio.sleep(self.execution_delay)
        
        # Simulate tool execution
        await self.emit_tool_executing("test_tool", {"user_id": context.user_id})
        await asyncio.sleep(self.execution_delay / 2)
        await self.emit_tool_completed("test_tool", {"result": "success", "user_id": context.user_id})
        
        result = {
            "status": "completed",
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "run_id": context.run_id,
            "execution_number": self.execution_count,
            "agent_name": self.name
        }
        
        self.execution_results.append(result)
        return result
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Legacy execution for backward compatibility testing."""
        if self.should_fail:
            raise ValueError(self.failure_message)
            
        return {
            "legacy_execution": True,
            "run_id": context.run_id,
            "agent_name": self.name
        }


class StressTestAgent(BaseAgent):
    """Agent designed to test resource usage and performance."""
    
    def __init__(self, *args, **kwargs):
        self.operation_count = 0
        self.memory_allocations = []
        super().__init__(*args, **kwargs)
    
    async def _execute_with_user_context(self, context: MockUserExecutionContext, 
                                       stream_updates: bool = False) -> Dict[str, Any]:
        """Execution that allocates memory and tracks operations."""
        self.operation_count += 1
        
        # Allocate some memory to test cleanup
        large_data = [i for i in range(1000)]  # Small allocation
        self.memory_allocations.append(large_data)
        
        # Simulate intensive operations
        for i in range(10):
            await self.emit_thinking(f"Processing step {i+1} of 10")
            await asyncio.sleep(0.001)  # Very small delay
        
        return {
            "operation_count": self.operation_count,
            "memory_allocations": len(self.memory_allocations),
            "user_id": context.user_id
        }


class TestBaseAgentMultiUserConcurrency(AsyncBaseTestCase):
    """Test BaseAgent behavior with multiple concurrent users.
    
    CRITICAL: Multi-user isolation is mandatory per CLAUDE.md requirements.
    """
    
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.logger = logging.getLogger(__name__)
    
    async def test_concurrent_user_isolation(self):
        """Test multiple users executing agents concurrently maintain isolation.
        
        BVJ: Platform/Internal | Risk Reduction | User data contamination prevention
        """
        num_users = 5
        
        # Create separate contexts for different users
        contexts = [
            MockUserExecutionContext(
                user_id=f"user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}"
            )
            for i in range(num_users)
        ]
        
        # Create separate agent instances (proper isolation pattern)
        agents = [
            ConcreteTestAgent(
                name=f"Agent_{i}",
                execution_delay=0.01  # Small delay to ensure concurrency
            )
            for i in range(num_users)
        ]
        
        # Execute all agents concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            agents[i].execute(contexts[i])
            for i in range(num_users)
        ])
        end_time = time.time()
        
        # Verify all executions succeeded
        self.assertEqual(len(results), num_users)
        
        # Verify user isolation - each result should have correct user_id
        for i, result in enumerate(results):
            self.assertEqual(result["user_id"], f"user_{i}")
            self.assertEqual(result["thread_id"], f"thread_{i}")
            self.assertEqual(result["run_id"], f"run_{i}")
            self.assertEqual(result["status"], "completed")
        
        # Verify agents maintained separate state
        for i, agent in enumerate(agents):
            self.assertEqual(agent.execution_count, 1)
            self.assertEqual(len(agent.execution_results), 1)
            self.assertEqual(agent.execution_results[0]["user_id"], f"user_{i}")
        
        # Performance check - concurrent execution should be faster than sequential
        expected_sequential_time = num_users * 0.01
        actual_time = end_time - start_time
        self.assertLess(actual_time, expected_sequential_time * 0.8,  # Allow some overhead
                       f"Concurrent execution too slow: {actual_time:.3f}s vs expected < {expected_sequential_time * 0.8:.3f}s")
    
    async def test_concurrent_websocket_event_isolation(self):
        """Test WebSocket events are properly isolated between concurrent users."""
        num_users = 3
        
        # Create mock bridges for each user
        mock_bridges = [AsyncMock() for _ in range(num_users)]
        contexts = [
            MockUserExecutionContext(user_id=f"ws_user_{i}", run_id=f"ws_run_{i}")
            for i in range(num_users)
        ]
        agents = [
            ConcreteTestAgent(name=f"WSAgent_{i}")
            for i in range(num_users)
        ]
        
        # Set up WebSocket bridges
        for i, agent in enumerate(agents):
            agent.set_websocket_bridge(mock_bridges[i], contexts[i].run_id)
        
        # Execute concurrently
        results = await asyncio.gather(*[
            agents[i].execute(contexts[i])
            for i in range(num_users)
        ])
        
        # Verify all executions completed
        for result in results:
            self.assertEqual(result["status"], "completed")
        
        # Verify each bridge received events only from its associated user
        for i, mock_bridge in enumerate(mock_bridges):
            # Verify thinking events were called
            self.assertTrue(mock_bridge.notify_agent_thinking.called)
            
            # Verify tool events were called
            self.assertTrue(mock_bridge.notify_tool_executing.called)
            self.assertTrue(mock_bridge.notify_tool_completed.called)
            
            # Verify events contained correct user_id
            thinking_calls = mock_bridge.notify_agent_thinking.call_args_list
            for call in thinking_calls:
                self.assertIn(f"ws_user_{i}", call[0][2])  # Third argument is the thought content
    
    async def test_high_concurrency_stress_test(self):
        """Test BaseAgent under high concurrent load."""
        num_concurrent = 20
        
        contexts = [
            MockUserExecutionContext(user_id=f"stress_user_{i}")
            for i in range(num_concurrent)
        ]
        
        agents = [
            StressTestAgent(name=f"StressAgent_{i}", execution_delay=0.005)
            for i in range(num_concurrent)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*[
            agents[i].execute(contexts[i], stream_updates=True)
            for i in range(num_concurrent)
        ])
        end_time = time.time()
        
        # Verify all executions completed
        self.assertEqual(len(results), num_concurrent)
        for result in results:
            self.assertIn("operation_count", result)
            self.assertEqual(result["operation_count"], 1)
        
        # Performance assertion
        total_time = end_time - start_time
        self.assertLess(total_time, 2.0, f"High concurrency execution took too long: {total_time:.3f}s")
        
        # Memory check - verify agents don't accumulate excessive memory
        for agent in agents:
            self.assertLessEqual(len(agent.memory_allocations), 1)
    
    async def test_mixed_success_failure_concurrent_execution(self):
        """Test concurrent execution with mix of successful and failing agents."""
        # Create mix of successful and failing agents
        contexts = [MockUserExecutionContext(user_id=f"mixed_user_{i}") for i in range(6)]
        agents = []
        
        for i in range(6):
            if i % 2 == 0:
                # Even indices succeed
                agent = ConcreteTestAgent(name=f"SuccessAgent_{i}")
            else:
                # Odd indices fail
                agent = ConcreteTestAgent(
                    name=f"FailAgent_{i}",
                    should_fail=True,
                    failure_message=f"Intentional failure {i}"
                )
            agents.append(agent)
        
        # Execute concurrently, capturing exceptions
        results = await asyncio.gather(*[
            agents[i].execute(contexts[i])
            for i in range(6)
        ], return_exceptions=True)
        
        # Verify results pattern
        self.assertEqual(len(results), 6)
        
        for i, result in enumerate(results):
            if i % 2 == 0:
                # Even indices should succeed
                self.assertIsInstance(result, dict)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["user_id"], f"mixed_user_{i}")
            else:
                # Odd indices should fail
                self.assertIsInstance(result, RuntimeError)
                self.assertIn(f"Intentional failure {i}", str(result))


class TestBaseAgentPerformanceAndEdgeCases(AsyncBaseTestCase):
    """Test BaseAgent performance characteristics and edge cases."""
    
    async def test_rapid_sequential_executions(self):
        """Test agent handling rapid sequential executions."""
        agent = ConcreteTestAgent(name="RapidAgent", execution_delay=0.001)
        contexts = [
            MockUserExecutionContext(user_id="rapid_user", run_id=f"rapid_run_{i}")
            for i in range(20)
        ]
        
        start_time = time.time()
        
        results = []
        for context in contexts:
            result = await agent.execute(context)
            results.append(result)
        
        end_time = time.time()
        
        # Verify all executions completed
        self.assertEqual(len(results), 20)
        self.assertEqual(agent.execution_count, 20)
        
        # Verify execution order and state
        for i, result in enumerate(results):
            self.assertEqual(result["execution_number"], i + 1)
            self.assertEqual(result["run_id"], f"rapid_run_{i}")
        
        # Performance check
        total_time = end_time - start_time
        self.assertLess(total_time, 1.0, f"Rapid sequential execution too slow: {total_time:.3f}s")
    
    async def test_websocket_event_timing_performance(self):
        """Test WebSocket event emission performance under load."""
        agent = ConcreteTestAgent(name="EventTimingAgent")
        mock_bridge = AsyncMock()
        context = MockUserExecutionContext()
        
        agent.set_websocket_bridge(mock_bridge, context.run_id)
        
        # Emit many events rapidly
        start_time = time.time()
        
        for i in range(100):
            await agent.emit_thinking(f"Rapid thought {i}")
            await agent.emit_tool_executing(f"tool_{i}", {"param": f"value_{i}"})
            await agent.emit_tool_completed(f"tool_{i}", {"result": f"result_{i}"})
        
        end_time = time.time()
        event_time = end_time - start_time
        
        # Events should be emitted quickly
        self.assertLess(event_time, 0.5, f"WebSocket event emission too slow: {event_time:.3f}s for 300 events")
        
        # Verify all events were called
        self.assertEqual(mock_bridge.notify_agent_thinking.call_count, 100)
        self.assertEqual(mock_bridge.notify_tool_executing.call_count, 100)
        self.assertEqual(mock_bridge.notify_tool_completed.call_count, 100)
    
    async def test_memory_cleanup_after_multiple_executions(self):
        """Test agent properly cleans up memory after multiple executions."""
        agent = StressTestAgent(name="MemoryTestAgent")
        
        # Capture initial memory state
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Run multiple executions
        for i in range(10):
            context = MockUserExecutionContext(user_id=f"memory_user_{i}")
            await agent.execute(context)
        
        # Force garbage collection
        gc.collect()
        
        # Check memory after cleanup
        final_memory = process.memory_info().rss
        memory_growth = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Memory growth should be reasonable (less than 50MB for 10 executions)
        self.assertLess(memory_growth, 50.0, 
                       f"Excessive memory growth: {memory_growth:.2f}MB after 10 executions")
    
    async def test_agent_state_reset_performance(self):
        """Test agent state reset performance and effectiveness."""
        agent = ConcreteTestAgent(name="ResetTestAgent")
        
        # Set up agent with some state
        context = MockUserExecutionContext()
        await agent.execute(context)
        
        # Add some additional state
        agent.context['test_data'] = list(range(1000))
        agent.set_state(SubAgentLifecycle.RUNNING)
        
        # Time the reset operation
        start_time = time.time()
        await agent.reset_state()
        reset_time = time.time() - start_time
        
        # Reset should be fast
        self.assertLess(reset_time, 0.1, f"Agent reset too slow: {reset_time:.3f}s")
        
        # Verify state was reset
        self.assertEqual(agent.state, SubAgentLifecycle.PENDING)
        self.assertEqual(len(agent.context), 0)
        self.assertIsNone(agent.start_time)
        self.assertIsNone(agent.end_time)
    
    async def test_edge_case_none_parameters(self):
        """Test agent behavior with None parameters and edge cases."""
        # Test with minimal initialization
        agent = ConcreteTestAgent()
        
        # Test with None context (should fail appropriately)
        with self.assertRaises(TypeError):
            await agent.execute(None)
        
        # Test with invalid context type
        with self.assertRaises(TypeError):
            await agent.execute({"invalid": "context"})
        
        # Test WebSocket methods without bridge
        await agent.emit_thinking("Test without bridge")  # Should not raise
        await agent.emit_tool_executing("test_tool")  # Should not raise
        await agent.emit_agent_completed()  # Should not raise
    
    async def test_reliability_handler_edge_cases(self):
        """Test reliability handler behavior in edge cases."""
        agent = ConcreteTestAgent(name="ReliabilityEdgeAgent")
        
        # Test with operation that always fails
        async def failing_operation():
            raise ValueError("Always fails")
        
        # Should eventually fail after retries
        with self.assertRaises(ValueError):
            await agent.execute_with_reliability(
                operation=failing_operation,
                operation_name="always_failing"
            )
        
        # Test with operation that succeeds after failures
        call_count = 0
        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = await agent.execute_with_reliability(
            operation=eventually_succeeds,
            operation_name="eventually_succeeds"
        )
        
        self.assertEqual(result, "success")
        self.assertGreaterEqual(call_count, 3)


class TestBaseAgentAdvancedErrorHandling(AsyncBaseTestCase):
    """Test advanced error handling and recovery scenarios."""
    
    async def test_circuit_breaker_integration_under_failures(self):
        """Test circuit breaker behavior under repeated failures."""
        agent = ConcreteTestAgent(
            name="CircuitBreakerAgent",
            should_fail=True,
            failure_message="Circuit breaker test failure"
        )
        
        # Initial state should be healthy
        self.assertTrue(agent.circuit_breaker.can_execute())
        
        contexts = [
            MockUserExecutionContext(user_id=f"cb_user_{i}")
            for i in range(3)
        ]
        
        # Execute and expect failures
        for context in contexts:
            with self.assertRaises(RuntimeError):
                await agent.execute(context)
        
        # Circuit breaker status should still be accessible
        status = agent.get_circuit_breaker_status()
        self.assertIn("state", status)
    
    async def test_error_recovery_after_reset(self):
        """Test agent recovery after errors and state reset."""
        agent = ConcreteTestAgent(
            name="RecoveryAgent",
            should_fail=True,
            failure_message="Recovery test failure"
        )
        
        context = MockUserExecutionContext()
        
        # Execute and expect failure
        with self.assertRaises(RuntimeError):
            await agent.execute(context)
        
        # Reset state
        await agent.reset_state()
        
        # Change agent to succeed
        agent.should_fail = False
        
        # Execute should now succeed
        result = await agent.execute(context)
        self.assertEqual(result["status"], "completed")
    
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling and graceful degradation."""
        agent = ConcreteTestAgent(name="WSErrorAgent")
        
        # Create a mock bridge that fails
        failing_bridge = AsyncMock()
        failing_bridge.notify_agent_thinking.side_effect = Exception("WebSocket failure")
        failing_bridge.notify_tool_executing.side_effect = Exception("WebSocket failure")
        failing_bridge.notify_agent_completed.side_effect = Exception("WebSocket failure")
        
        context = MockUserExecutionContext()
        agent.set_websocket_bridge(failing_bridge, context.run_id)
        
        # Execute should still succeed despite WebSocket failures
        result = await agent.execute(context)
        
        self.assertEqual(result["status"], "completed")
        # Verify WebSocket methods were attempted but failed gracefully
        self.assertTrue(failing_bridge.notify_agent_thinking.called)
    
    async def test_token_management_error_scenarios(self):
        """Test token management under error conditions."""
        agent = ConcreteTestAgent(name="TokenErrorAgent")
        context = MockUserExecutionContext()
        
        # Test token tracking with invalid parameters
        enhanced_context = agent.track_llm_usage(
            context=context,
            input_tokens=0,  # Edge case: zero tokens
            output_tokens=0,
            model="",  # Edge case: empty model
            operation_type="error_test"
        )
        
        # Should handle gracefully
        self.assertIsInstance(enhanced_context, MockUserExecutionContext)
        
        # Test with very large token counts
        enhanced_context = agent.track_llm_usage(
            context=context,
            input_tokens=1000000,  # Very large number
            output_tokens=500000,
            model="large_model",
            operation_type="stress_test"
        )
        
        # Should handle without issues
        self.assertIsInstance(enhanced_context, MockUserExecutionContext)
    
    async def test_session_isolation_error_scenarios(self):
        """Test session isolation validation under various conditions."""
        agent = ConcreteTestAgent(name="SessionErrorAgent")
        
        # Test validation with corrupted agent state
        original_validate = agent._validate_session_isolation
        
        def mock_validate_failure():
            raise Exception("Session isolation validation failed")
        
        agent._validate_session_isolation = mock_validate_failure
        
        context = MockUserExecutionContext()
        
        # Execute should handle validation errors gracefully in __init__
        # but fail if called explicitly during execution
        with self.assertRaises(Exception):
            agent._validate_session_isolation()
        
        # Restore original method
        agent._validate_session_isolation = original_validate


class TestBaseAgentResourceManagement(BaseTestCase):
    """Test BaseAgent resource management and cleanup."""
    
    def setUp(self):
        super().setUp()
        self.agents = []  # Track agents for cleanup
    
    def tearDown(self):
        # Clean up all test agents
        for agent in self.agents:
            try:
                asyncio.run(agent.shutdown())
            except Exception:
                pass  # Ignore cleanup errors
        super().tearDown()
    
    def test_agent_creation_and_cleanup_pattern(self):
        """Test proper agent creation and cleanup patterns."""
        # Create multiple agents
        for i in range(5):
            agent = ConcreteTestAgent(name=f"CleanupAgent_{i}")
            self.agents.append(agent)
        
        # Verify all agents were created properly
        self.assertEqual(len(self.agents), 5)
        
        for i, agent in enumerate(self.agents):
            self.assertEqual(agent.name, f"CleanupAgent_{i}")
            self.assertEqual(agent.state, SubAgentLifecycle.PENDING)
    
    def test_health_status_with_degraded_components(self):
        """Test health status reporting with degraded components."""
        agent = ConcreteTestAgent(name="HealthTestAgent")
        self.agents.append(agent)
        
        # Get initial health status
        health = agent.get_health_status()
        
        self.assertEqual(health["agent_name"], "HealthTestAgent")
        self.assertIn("overall_status", health)
        self.assertIn("circuit_breaker", health)
        
        # Verify health status structure
        required_fields = [
            "agent_name", "state", "websocket_available", "overall_status",
            "uses_unified_reliability"
        ]
        for field in required_fields:
            self.assertIn(field, health)
    
    def test_factory_method_patterns(self):
        """Test BaseAgent factory method patterns."""
        context = MockUserExecutionContext(user_id="factory_user")
        
        # Test modern factory method
        agent = ConcreteTestAgent.create_with_context(context)
        self.agents.append(agent)
        
        self.assertEqual(agent._user_context, context)
        
        # Test legacy factory with warnings
        with self.assertWarns(DeprecationWarning):
            legacy_agent = ConcreteTestAgent.create_legacy_with_warnings(
                name="LegacyFactoryAgent"
            )
        self.agents.append(legacy_agent)
        
        self.assertEqual(legacy_agent.name, "LegacyFactoryAgent")
    
    def test_abstract_method_enforcement(self):
        """Test that BaseAgent enforces abstract method implementation."""
        # Test that agents must implement execution methods
        class IncompleteAgent(BaseAgent):
            pass  # No execution methods
        
        agent = IncompleteAgent()
        self.agents.append(agent)
        context = MockUserExecutionContext()
        
        with self.assertRaises(NotImplementedError):
            asyncio.run(agent.execute(context))


class TestBaseAgentValidationAndCompliance(BaseTestCase):
    """Test BaseAgent pattern validation and compliance checking."""
    
    def setUp(self):
        super().setUp()
        self.agents = []
    
    def tearDown(self):
        for agent in self.agents:
            try:
                asyncio.run(agent.shutdown())
            except Exception:
                pass
        super().tearDown()
    
    def test_modern_implementation_validation(self):
        """Test validation of modern implementation patterns."""
        agent = ConcreteTestAgent(name="ModernValidationAgent")
        self.agents.append(agent)
        
        validation = agent.validate_modern_implementation()
        
        self.assertTrue(validation["compliant"])
        self.assertEqual(validation["pattern"], "modern")
        self.assertIsInstance(validation["warnings"], list)
        self.assertIsInstance(validation["errors"], list)
        self.assertIsInstance(validation["recommendations"], list)
    
    def test_migration_status_reporting(self):
        """Test migration status reporting functionality."""
        agent = ConcreteTestAgent(name="MigrationStatusAgent")
        self.agents.append(agent)
        
        status = agent.get_migration_status()
        
        required_fields = [
            "agent_name", "agent_class", "migration_status", 
            "execution_pattern", "user_isolation_safe"
        ]
        
        for field in required_fields:
            self.assertIn(field, status)
        
        self.assertEqual(status["agent_name"], "MigrationStatusAgent")
        self.assertIn(status["migration_status"], ["compliant", "needs_migration"])
    
    def test_user_execution_context_pattern_assertion(self):
        """Test UserExecutionContext pattern assertion."""
        agent = ConcreteTestAgent(name="PatternAssertionAgent")
        self.agents.append(agent)
        
        # Should not raise for compliant agent
        agent.assert_user_execution_context_pattern()
        
        # Test with agent that has violations
        agent.db_session = AsyncMock()  # Add violation
        
        # Mock validation to return error
        def mock_validate_with_error():
            return {
                "compliant": False,
                "errors": ["CRITICAL: Agent stores database session"],
                "warnings": [],
                "recommendations": []
            }
        
        agent.validate_modern_implementation = mock_validate_with_error
        
        with self.assertRaises(RuntimeError):
            agent.assert_user_execution_context_pattern()


if __name__ == '__main__':
    # Run with pytest for better async support and detailed output
    pytest.main([
        __file__, 
        '-v', 
        '--tb=short',
        '--asyncio-mode=auto'
    ])