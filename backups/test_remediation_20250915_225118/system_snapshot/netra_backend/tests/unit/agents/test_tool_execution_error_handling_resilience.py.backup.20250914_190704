"""Unit tests for tool execution error handling and resilience patterns.

These tests validate that the tool execution system handles errors gracefully,
maintains system stability under failure conditions, and provides proper
error reporting and recovery mechanisms.

Business Value: Platform/Internal - System Reliability
Ensures tool execution failures don't cascade and system remains stable.

Test Coverage:
- Tool execution timeout handling
- Memory limit enforcement and recovery
- Tool failure isolation and error propagation
- WebSocket notification error handling
- Circuit breaker patterns for failing tools
- Resource cleanup on errors
- Security violation detection and handling
"""

import asyncio
import pytest
import time
import psutil
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    AuthenticationError,
    PermissionError,
    SecurityViolationError,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from langchain_core.tools import BaseTool


class FailingTool(BaseTool):
    """Tool that simulates various failure scenarios."""
    
    name: str = "failing_tool"
    description: str = "Tool that fails in configurable ways"
    failure_mode: str = "exception"
    failure_delay_ms: int = 0
    failure_message: str = "Simulated failure"
    execution_count: int = 0
    
    def __init__(
        self, 
        failure_mode: str = "exception",
        failure_delay_ms: int = 0,
        failure_message: str = "Simulated failure",
        **kwargs
    ):
        kwargs.update({
            'failure_mode': failure_mode,
            'failure_delay_ms': failure_delay_ms,
            'failure_message': failure_message,
            'execution_count': 0
        })
        super().__init__(**kwargs)
        
    def _run(self, operation: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(operation, **kwargs))
        
    async def _arun(self, operation: str, **kwargs) -> str:
        """Asynchronous execution with configurable failures."""
        self.execution_count += 1
        
        # Add delay before failure if configured
        if self.failure_delay_ms > 0:
            await asyncio.sleep(self.failure_delay_ms / 1000)
            
        if self.failure_mode == "exception":
            raise RuntimeError(self.failure_message)
            
        elif self.failure_mode == "timeout":
            # Simulate infinite operation
            await asyncio.sleep(300)  # 5 minutes - should timeout
            
        elif self.failure_mode == "memory":
            # Simulate memory exhaustion (don't actually consume memory in tests)
            raise MemoryError("Simulated memory exhaustion")
            
        elif self.failure_mode == "security":
            raise PermissionError("Simulated security violation")
            
        elif self.failure_mode == "intermittent":
            # Fail every other execution
            if self.execution_count % 2 == 0:
                raise RuntimeError(f"Intermittent failure #{self.execution_count}")
            else:
                return f"Success #{self.execution_count}"
                
        elif self.failure_mode == "none":
            return f"Success: {operation}"
            
        else:
            raise ValueError(f"Unknown failure mode: {self.failure_mode}")


class SlowTool(BaseTool):
    """Tool that simulates slow execution."""
    
    name: str = "slow_tool"
    description: str = "Tool that takes a long time to execute"
    execution_time_ms: int = 1000
    execution_count: int = 0
    was_interrupted: bool = False
    
    def __init__(self, execution_time_ms: int = 1000, **kwargs):
        kwargs.update({
            'execution_time_ms': execution_time_ms,
            'execution_count': 0,
            'was_interrupted': False
        })
        super().__init__(**kwargs)
        
    def _run(self, task: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(task, **kwargs))
        
    async def _arun(self, task: str, **kwargs) -> str:
        """Asynchronous execution with configurable delay."""
        self.execution_count += 1
        
        try:
            await asyncio.sleep(self.execution_time_ms / 1000)
            return f"Slow task completed: {task}"
        except asyncio.CancelledError:
            self.was_interrupted = True
            raise


class ResourceExhaustionTool(BaseTool):
    """Tool that simulates resource exhaustion scenarios."""
    
    name: str = "resource_tool"
    description: str = "Tool that consumes system resources"
    resource_type: str = "memory"
    execution_count: int = 0
    
    def __init__(self, resource_type: str = "memory", **kwargs):
        kwargs.update({
            'resource_type': resource_type,
            'execution_count': 0
        })
        super().__init__(**kwargs)
        
    def _run(self, size: str, **kwargs) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(size, **kwargs))
        
    async def _arun(self, size: str, **kwargs) -> str:
        """Asynchronous execution that simulates resource consumption."""
        self.execution_count += 1
        
        if self.resource_type == "memory":
            # Simulate memory usage without actually consuming memory
            raise MemoryError(f"Simulated memory exhaustion for {size}")
            
        elif self.resource_type == "cpu":
            # Simulate CPU-intensive operation
            start_time = time.time()
            iterations = 0
            while time.time() - start_time < 0.01:  # 10ms of CPU work
                iterations += 1
            return f"CPU task completed: {iterations} iterations"
            
        else:
            return f"Resource operation completed: {size}"


class MockResilientWebSocketBridge:
    """Mock WebSocket bridge that tracks error scenarios."""
    
    def __init__(self):
        self.executing_calls = []
        self.completed_calls = []
        self.error_calls = []
        self.connection_failures = 0
        self.notification_failures = 0
        self.should_fail_executing = False
        self.should_fail_completed = False
        
    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Dict[str, Any] = None) -> bool:
        """Mock executing notification with failure simulation."""
        call_record = {
            "run_id": run_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "parameters": parameters,
            "timestamp": time.time()
        }
        
        if self.should_fail_executing:
            self.error_calls.append(call_record)
            self.notification_failures += 1
            return False
            
        self.executing_calls.append(call_record)
        return True
        
    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Dict[str, Any] = None, execution_time_ms: float = None) -> bool:
        """Mock completed notification with failure simulation."""
        call_record = {
            "run_id": run_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "timestamp": time.time()
        }
        
        if self.should_fail_completed:
            self.error_calls.append(call_record)
            self.notification_failures += 1
            return False
            
        self.completed_calls.append(call_record)
        return True
        
    def simulate_connection_failure(self):
        """Simulate WebSocket connection failure."""
        self.should_fail_executing = True
        self.should_fail_completed = True
        self.connection_failures += 1
        
    def restore_connection(self):
        """Restore WebSocket connection."""
        self.should_fail_executing = False
        self.should_fail_completed = False


class TestToolExecutionErrorHandlingResilience(SSotAsyncTestCase):
    """Unit tests for tool execution error handling and resilience."""
    
    def setup_method(self, method):
        """Set up test environment following SSOT patterns."""
        super().setup_method(method)
        
        # Create test contexts
        self.user_context = UserExecutionContext(
            user_id="resilience_user_001",
            run_id=f"resilience_run_{int(time.time() * 1000)}",
            thread_id="resilience_thread_001",
            request_id=f"resilience_req_{int(time.time() * 1000)}"
        )
        
        self.agent_context = AgentExecutionContext(
            agent_name="ResilienceTestAgent",
            run_id=self.user_context.run_id,
            thread_id=self.user_context.thread_id,
            user_id=self.user_context.user_id
        )
        
        # Create resilient WebSocket bridge
        self.websocket_bridge = MockResilientWebSocketBridge()
        
        # Create test tools
        self.failing_tool = FailingTool(failure_mode="exception", failure_delay_ms=0, failure_message="Standard test failure")
        self.timeout_tool = FailingTool(failure_mode="timeout", failure_delay_ms=0, failure_message="Tool timeout")
        self.slow_tool = SlowTool(execution_time_ms=500)  # 500ms execution
        self.memory_tool = ResourceExhaustionTool(resource_type="memory")
        
        # Create execution engine
        self.execution_engine = UnifiedToolExecutionEngine(
            websocket_bridge=self.websocket_bridge
        )
        
    async def teardown_method(self, method):
        """Clean up after tests following SSOT patterns."""
        await UnifiedToolDispatcher.cleanup_user_dispatchers(self.user_context.user_id)
        await super().teardown_method(method)
        
    # ===================== BASIC ERROR HANDLING =====================
        
    async def test_tool_exception_handling(self):
        """Test handling of tool exceptions."""
        tool_input = ToolInput(
            tool_name="failing_tool",
            parameters={"operation": "test_exception"},
            request_id=self.user_context.run_id
        )
        
        # Execute failing tool
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.failing_tool,
            kwargs={"context": self.agent_context, "operation": "test_exception"}
        )
        
        # Verify error is handled gracefully
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertIn("Standard test failure", result.message)
        
        # Verify WebSocket notifications were still sent
        self.assertEqual(len(self.websocket_bridge.executing_calls), 1)
        self.assertEqual(len(self.websocket_bridge.completed_calls), 1)
        
        # Verify error information in completed notification
        completed_call = self.websocket_bridge.completed_calls[0]
        self.assertEqual(completed_call["result"]["status"], "error")
        self.assertIn("error", completed_call["result"])
        
    async def test_tool_timeout_handling(self):
        """Test handling of tool timeouts."""
        # Create tool that will timeout
        timeout_tool = SlowTool(execution_time_ms=5000)  # 5 second execution
        
        tool_input = ToolInput(
            tool_name="slow_tool",
            parameters={"task": "timeout_test"},
            request_id=self.user_context.run_id
        )
        
        start_time = time.time()
        
        # Execute with short timeout (should timeout before completion)
        with patch.object(self.execution_engine, 'default_timeout', 0.1):  # 100ms timeout
            result = await self.execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=timeout_tool,
                kwargs={"context": self.agent_context, "task": "timeout_test"}
            )
        
        execution_time = time.time() - start_time
        
        # Verify timeout was handled
        self.assertLess(execution_time, 1.0)  # Should complete quickly due to timeout
        self.assertEqual(result.status, ToolStatus.ERROR)
        
        # Verify tool was interrupted
        self.assertTrue(timeout_tool.was_interrupted)
        
    async def test_memory_error_handling(self):
        """Test handling of memory-related errors."""
        tool_input = ToolInput(
            tool_name="resource_tool",
            parameters={"size": "1GB"},
            request_id=self.user_context.run_id
        )
        
        # Execute memory-exhausting tool
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.memory_tool,
            kwargs={"context": self.agent_context, "size": "1GB"}
        )
        
        # Verify memory error is handled
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertIn("memory exhaustion", result.message.lower())
        
        # Verify system metrics tracked the error
        metrics = self.execution_engine.get_execution_metrics()
        self.assertGreater(metrics['failed_executions'], 0)
        
    async def test_security_violation_handling(self):
        """Test handling of security violations."""
        security_tool = FailingTool(failure_mode="security", failure_delay_ms=0, failure_message="Access denied")
        
        tool_input = ToolInput(
            tool_name="failing_tool",
            parameters={"operation": "security_test"},
            request_id=self.user_context.run_id
        )
        
        # Execute tool that raises security violation
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=security_tool,
            kwargs={"context": self.agent_context, "operation": "security_test"}
        )
        
        # Verify security error is handled
        self.assertEqual(result.status, ToolStatus.ERROR)
        self.assertIn("Access denied", result.message)
        
    # ===================== RESILIENCE PATTERNS =====================
        
    async def test_websocket_notification_failure_resilience(self):
        """Test tool execution continues when WebSocket notifications fail."""
        # Configure WebSocket to fail
        self.websocket_bridge.simulate_connection_failure()
        
        # Create working tool
        working_tool = FailingTool(failure_mode="none", failure_delay_ms=0, failure_message="Success")
        
        tool_input = ToolInput(
            tool_name="failing_tool",
            parameters={"operation": "websocket_test"},
            request_id=self.user_context.run_id
        )
        
        # Execute tool (should succeed despite WebSocket failures)
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=working_tool,
            kwargs={"context": self.agent_context, "operation": "websocket_test"}
        )
        
        # Verify tool execution succeeded
        self.assertEqual(result.status, ToolStatus.SUCCESS)
        
        # Verify WebSocket failures were tracked
        self.assertGreater(self.websocket_bridge.notification_failures, 0)
        
    async def test_concurrent_tool_failure_isolation(self):
        """Test that tool failures don't affect concurrent executions."""
        # Create multiple tools with different failure modes
        tools = [
            FailingTool(failure_mode="exception", failure_delay_ms=0, failure_message="Tool 1 failure"),
            FailingTool(failure_mode="none", failure_delay_ms=0, failure_message="Tool 2 success"),
            FailingTool(failure_mode="memory", failure_delay_ms=0, failure_message="Tool 3 memory error"),
            FailingTool(failure_mode="none", failure_delay_ms=0, failure_message="Tool 4 success")
        ]
        
        # Execute tools concurrently
        tasks = []
        for i, tool in enumerate(tools):
            tool_input = ToolInput(
                tool_name="failing_tool",
                parameters={"operation": f"concurrent_test_{i}"},
                request_id=f"{self.user_context.run_id}_{i}"
            )
            
            task = self.execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=tool,
                kwargs={"context": self.agent_context, "operation": f"concurrent_test_{i}"}
            )
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results match expected patterns
        self.assertEqual(len(results), 4)
        
        # Tool 1: Should fail with exception
        self.assertEqual(results[0].status, ToolStatus.ERROR)
        self.assertIn("Tool 1 failure", results[0].message)
        
        # Tool 2: Should succeed
        self.assertEqual(results[1].status, ToolStatus.SUCCESS)
        
        # Tool 3: Should fail with memory error
        self.assertEqual(results[2].status, ToolStatus.ERROR)
        
        # Tool 4: Should succeed
        self.assertEqual(results[3].status, ToolStatus.SUCCESS)
        
        # Verify failures didn't cascade
        success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)
        self.assertEqual(success_count, 2)
        
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for repeatedly failing tools."""
        # Create intermittently failing tool
        intermittent_tool = FailingTool(failure_mode="intermittent", failure_delay_ms=0, failure_message="Intermittent failure")
        
        results = []
        
        # Execute tool multiple times to trigger circuit breaker
        for i in range(10):
            tool_input = ToolInput(
                tool_name="failing_tool",
                parameters={"operation": f"circuit_test_{i}"},
                request_id=f"{self.user_context.run_id}_{i}"
            )
            
            result = await self.execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=intermittent_tool,
                kwargs={"context": self.agent_context, "operation": f"circuit_test_{i}"}
            )
            
            results.append(result)
            
        # Verify mix of successes and failures
        successes = [r for r in results if r.status == ToolStatus.SUCCESS]
        failures = [r for r in results if r.status == ToolStatus.ERROR]
        
        self.assertGreater(len(successes), 0)
        self.assertGreater(len(failures), 0)
        
        # Verify intermittent pattern (every other execution)
        self.assertEqual(len(successes), 5)
        self.assertEqual(len(failures), 5)
        
    # ===================== RESOURCE MANAGEMENT =====================
        
    async def test_resource_cleanup_on_failure(self):
        """Test that resources are properly cleaned up on tool failure."""
        initial_metrics = self.execution_engine.get_execution_metrics()
        initial_active = initial_metrics.get('active_executions', 0)
        
        # Execute failing tool
        tool_input = ToolInput(
            tool_name="failing_tool",
            parameters={"operation": "cleanup_test"},
            request_id=self.user_context.run_id
        )
        
        result = await self.execution_engine.execute_tool_with_input(
            tool_input=tool_input,
            tool=self.failing_tool,
            kwargs={"context": self.agent_context, "operation": "cleanup_test"}
        )
        
        # Verify failure
        self.assertEqual(result.status, ToolStatus.ERROR)
        
        # Verify resources were cleaned up
        final_metrics = self.execution_engine.get_execution_metrics()
        final_active = final_metrics.get('active_executions', 0)
        
        self.assertEqual(final_active, initial_active)  # Should be back to initial state
        
    async def test_memory_limit_enforcement(self):
        """Test memory limit enforcement during tool execution."""
        # This test simulates memory limit checking rather than actual memory exhaustion
        original_max_memory = self.execution_engine.max_memory_mb
        
        # Set very low memory limit for testing
        self.execution_engine.max_memory_mb = 1  # 1MB limit
        
        try:
            tool_input = ToolInput(
                tool_name="resource_tool",
                parameters={"size": "large_dataset"},
                request_id=self.user_context.run_id
            )
            
            # Execute memory-exhausting tool
            result = await self.execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=self.memory_tool,
                kwargs={"context": self.agent_context, "size": "large_dataset"}
            )
            
            # Verify memory error was caught
            self.assertEqual(result.status, ToolStatus.ERROR)
            self.assertIn("memory", result.message.lower())
            
        finally:
            # Restore original memory limit
            self.execution_engine.max_memory_mb = original_max_memory
            
    # ===================== ERROR RECOVERY =====================
            
    async def test_tool_execution_recovery_after_failure(self):
        """Test system recovery after tool execution failures."""
        # Execute failing tool
        failing_result = await self.execution_engine.execute_tool_with_input(
            tool_input=ToolInput(
                tool_name="failing_tool",
                parameters={"operation": "recovery_test_fail"},
                request_id=f"{self.user_context.run_id}_fail"
            ),
            tool=self.failing_tool,
            kwargs={"context": self.agent_context, "operation": "recovery_test_fail"}
        )
        
        self.assertEqual(failing_result.status, ToolStatus.ERROR)
        
        # Verify system can still execute successful tools
        success_tool = FailingTool(failure_mode="none", failure_delay_ms=0, failure_message="Recovery success")
        
        success_result = await self.execution_engine.execute_tool_with_input(
            tool_input=ToolInput(
                tool_name="failing_tool",
                parameters={"operation": "recovery_test_success"},
                request_id=f"{self.user_context.run_id}_success"
            ),
            tool=success_tool,
            kwargs={"context": self.agent_context, "operation": "recovery_test_success"}
        )
        
        self.assertEqual(success_result.status, ToolStatus.SUCCESS)
        
    async def test_health_check_after_failures(self):
        """Test system health check after experiencing failures."""
        # Cause multiple failures
        for i in range(3):
            tool_input = ToolInput(
                tool_name="failing_tool",
                parameters={"operation": f"health_test_{i}"},
                request_id=f"{self.user_context.run_id}_{i}"
            )
            
            await self.execution_engine.execute_tool_with_input(
                tool_input=tool_input,
                tool=self.failing_tool,
                kwargs={"context": self.agent_context, "operation": f"health_test_{i}"}
            )
            
        # Check health status
        health = await self.execution_engine.health_check()
        
        self.assertIn("status", health)
        self.assertIn("issues", health)
        self.assertIn("can_process_agents", health)
        
        # Despite failures, system should still be capable of processing
        self.assertTrue(health["can_process_agents"])
        
    async def test_emergency_shutdown_recovery(self):
        """Test emergency shutdown and recovery capabilities."""
        # Start multiple tool executions
        slow_tools = [SlowTool(execution_time_ms=1000) for _ in range(3)]  # 1 second each
        
        tasks = []
        for i, tool in enumerate(slow_tools):
            tool_input = ToolInput(
                tool_name="slow_tool",
                parameters={"task": f"emergency_test_{i}"},
                request_id=f"{self.user_context.run_id}_emergency_{i}"
            )
            
            task = asyncio.create_task(
                self.execution_engine.execute_tool_with_input(
                    tool_input=tool_input,
                    tool=tool,
                    kwargs={"context": self.agent_context, "task": f"emergency_test_{i}"}
                )
            )
            tasks.append(task)
            
        # Let executions start
        await asyncio.sleep(0.1)
        
        # Trigger emergency shutdown
        shutdown_result = await self.execution_engine.emergency_shutdown_all_executions()
        
        self.assertIn("shutdown_executions", shutdown_result)
        self.assertGreater(shutdown_result["shutdown_executions"], 0)
        
        # Wait for tasks to complete (should be cancelled)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify system can still process new requests
        health = await self.execution_engine.health_check()
        self.assertIn("status", health)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])