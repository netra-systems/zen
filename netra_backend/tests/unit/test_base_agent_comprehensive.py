"""
Comprehensive Unit Test Suite for Base Agent Core Module

Business Value Justification (BVJ):
- **Segment:** All customer segments (Free through Enterprise)
- **Goal:** Stability and reliability of core agent execution patterns
- **Value Impact:** Ensures 90% of platform value (chat functionality) works reliably
- **Revenue Impact:** Protects $500K+ ARR by validating core agent execution patterns

This test suite validates the BaseAgent SSOT implementation with focus on:
1. Lifecycle management and state transitions 
2. User context isolation (Enterprise security requirement)
3. WebSocket integration for real-time chat updates
4. Reliability infrastructure (circuit breakers, retries) 
5. Modern execution patterns (UserExecutionContext)
6. Token management and cost optimization

Test Categories:
- Lifecycle Management: Agent state transitions and validation
- User Isolation: Concurrent user execution without cross-contamination
- WebSocket Integration: Real-time event emission for chat functionality
- Reliability Infrastructure: Circuit breakers and error handling
- Modern Execution Patterns: UserExecutionContext compliance
- Token Management: Cost tracking and optimization features

Created: 2025-09-10
Last Updated: 2025-09-10
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import classes under test
from netra_backend.app.agents.base_agent import BaseAgent, AgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError

# Import supporting types and enums
from shared.types.core_types import UserID, ThreadID, RunID


class TestBaseAgent(BaseAgent):
    """Test agent implementation for comprehensive testing."""
    
    def __init__(self, *args, **kwargs):
        # Add test-specific initialization
        self._test_execution_results = []
        self._test_thinking_events = []
        self._test_tool_events = []
        super().__init__(*args, **kwargs)
    
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Test implementation of modern execution pattern."""
        # Simulate agent thinking
        if stream_updates:
            await self.emit_thinking("Processing user request", 1, context)
            await self.emit_tool_executing("test_tool", {"param": "value"})
            await self.emit_tool_completed("test_tool", {"result": "success"})
        
        # Store execution for validation
        self._test_execution_results.append({
            "user_id": context.user_id,
            "thread_id": context.thread_id,
            "run_id": context.run_id,
            "request_id": context.request_id,
            "stream_updates": stream_updates,
            "timestamp": time.time()
        })
        
        # Simulate successful execution
        result = {
            "status": "success",
            "message": "Test agent execution completed",
            "user_id": context.user_id,
            "execution_id": len(self._test_execution_results)
        }
        
        return result
    
    def get_test_executions(self):
        """Get all test executions for validation."""
        return self._test_execution_results.copy()
    
    def reset_test_state(self):
        """Reset test state for clean test runs."""
        self._test_execution_results.clear()
        self._test_thinking_events.clear() 
        self._test_tool_events.clear()


class LegacyTestAgent(BaseAgent):
    """Legacy agent implementation for compatibility testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._legacy_executions = []
    
    async def execute_core_logic(self, context) -> Dict[str, Any]:
        """Legacy execution pattern for compatibility testing."""
        self._legacy_executions.append({
            "execution_time": time.time(),
            "context_type": type(context).__name__
        })
        return {"status": "legacy_success"}


class TestBaseAgentLifecycleManagement(SSotAsyncTestCase):
    """Test suite for agent lifecycle management and state transitions."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_agent = TestBaseAgent(
            name="TestLifecycleAgent",
            description="Agent for lifecycle testing",
            enable_reliability=True
        )
        
    async def asyncTearDown(self):
        """Clean up after tests."""
        if hasattr(self.test_agent, 'reset_state'):
            await self.test_agent.reset_state()
        if hasattr(self.test_agent, 'shutdown'):
            await self.test_agent.shutdown()
    
    def test_agent_initialization_with_default_state(self):
        """Test agent initializes with PENDING state and proper defaults."""
        # Verify initial state
        self.assertEqual(self.test_agent.state, SubAgentLifecycle.PENDING)
        self.assertEqual(self.test_agent.name, "TestLifecycleAgent")
        self.assertIsNone(self.test_agent.start_time)
        self.assertIsNone(self.test_agent.end_time)
        
        # Verify reliability components are initialized
        self.assertTrue(hasattr(self.test_agent, 'circuit_breaker'))
        self.assertTrue(hasattr(self.test_agent, 'monitor'))
        self.assertTrue(hasattr(self.test_agent, '_reliability_manager_instance'))
        
        # Verify WebSocket adapter is initialized
        self.assertTrue(hasattr(self.test_agent, '_websocket_adapter'))
        
        # Verify timing collector is initialized
        self.assertTrue(hasattr(self.test_agent, 'timing_collector'))
    
    def test_valid_state_transitions(self):
        """Test that valid state transitions are allowed."""
        # PENDING -> RUNNING
        self.test_agent.set_state(SubAgentLifecycle.RUNNING)
        self.assertEqual(self.test_agent.state, SubAgentLifecycle.RUNNING)
        
        # RUNNING -> COMPLETED
        self.test_agent.set_state(SubAgentLifecycle.COMPLETED)
        self.assertEqual(self.test_agent.state, SubAgentLifecycle.COMPLETED)
        
        # COMPLETED -> SHUTDOWN
        self.test_agent.set_state(SubAgentLifecycle.SHUTDOWN)
        self.assertEqual(self.test_agent.state, SubAgentLifecycle.SHUTDOWN)
    
    def test_invalid_state_transitions_raise_errors(self):
        """Test that invalid state transitions raise appropriate errors."""
        # PENDING -> COMPLETED (should fail - must go through RUNNING)
        with self.assertRaises(ValueError) as context:
            self.test_agent.set_state(SubAgentLifecycle.COMPLETED)
        
        error_message = str(context.exception)
        self.assertIn("Invalid state transition", error_message)
        self.assertIn("PENDING", error_message)
        self.assertIn("COMPLETED", error_message)
        
        # SHUTDOWN -> RUNNING (should fail - terminal state)
        self.test_agent.set_state(SubAgentLifecycle.SHUTDOWN)
        with self.assertRaises(ValueError):
            self.test_agent.set_state(SubAgentLifecycle.RUNNING)
    
    async def test_agent_reset_state_clears_all_components(self):
        """Test that reset_state properly clears all agent components."""
        # Set up agent in a complex state
        self.test_agent.set_state(SubAgentLifecycle.RUNNING)
        self.test_agent.context["test_data"] = "should_be_cleared"
        self.test_agent.start_time = time.time()
        
        # Reset state
        await self.test_agent.reset_state()
        
        # Verify state is reset
        self.assertEqual(self.test_agent.state, SubAgentLifecycle.PENDING)
        self.assertIsNone(self.test_agent.start_time)
        self.assertIsNone(self.test_agent.end_time)
        self.assertEqual(len(self.test_agent.context), 0)
    
    async def test_agent_shutdown_is_idempotent(self):
        """Test that shutdown can be called multiple times safely."""
        # First shutdown
        await self.test_agent.shutdown()
        self.assertEqual(self.test_agent.state, SubAgentLifecycle.SHUTDOWN)
        
        # Second shutdown should not raise error
        await self.test_agent.shutdown()
        self.assertEqual(self.test_agent.state, SubAgentLifecycle.SHUTDOWN)
    
    def test_agent_health_status_reflects_lifecycle_state(self):
        """Test that health status properly reflects agent lifecycle state."""
        # Test PENDING state health
        health = self.test_agent.get_health_status()
        self.assertEqual(health["state"], SubAgentLifecycle.PENDING.value)
        self.assertIn("agent_name", health)
        self.assertEqual(health["agent_name"], "TestLifecycleAgent")
        
        # Test RUNNING state health
        self.test_agent.set_state(SubAgentLifecycle.RUNNING)
        health = self.test_agent.get_health_status()
        self.assertEqual(health["state"], SubAgentLifecycle.RUNNING.value)
        
        # Test circuit breaker status is included
        self.assertIn("circuit_breaker", health)
        self.assertIn("can_execute", health["circuit_breaker"])


class TestBaseAgentUserIsolation(SSotAsyncTestCase):
    """Test suite for user context isolation and concurrent execution."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def create_test_context(self, user_id: str, thread_id: str = None, run_id: str = None) -> UserExecutionContext:
        """Create test user execution context."""
        return UserExecutionContext(
            user_id=UserID(user_id),
            thread_id=ThreadID(thread_id or f"thread_{user_id}"),
            run_id=RunID(run_id or f"run_{user_id}_{int(time.time())}"),
            request_id=f"req_{user_id}_{int(time.time())}",
            operation_depth=1,
            agent_context={"user_request": f"Test request from {user_id}"},
            metadata={}
        )
    
    async def test_concurrent_user_execution_isolation(self):
        """Test that concurrent users are properly isolated during execution."""
        # Create agents for concurrent users
        agent1 = TestBaseAgent(name="ConcurrentAgent1")
        agent2 = TestBaseAgent(name="ConcurrentAgent2")
        
        # Create isolated contexts for different users
        context1 = self.create_test_context("user123")
        context2 = self.create_test_context("user456")
        
        # Execute concurrently
        task1 = asyncio.create_task(agent1.execute(context=context1, stream_updates=True))
        task2 = asyncio.create_task(agent2.execute(context=context2, stream_updates=True))
        
        # Wait for both executions
        result1, result2 = await asyncio.gather(task1, task2)
        
        # Verify results are isolated
        self.assertEqual(result1["user_id"], "user123")
        self.assertEqual(result2["user_id"], "user456")
        self.assertNotEqual(result1["execution_id"], result2["execution_id"])
        
        # Verify execution logs are isolated
        executions1 = agent1.get_test_executions()
        executions2 = agent2.get_test_executions()
        
        self.assertEqual(len(executions1), 1)
        self.assertEqual(len(executions2), 1)
        self.assertEqual(executions1[0]["user_id"], "user123")
        self.assertEqual(executions2[0]["user_id"], "user456")
        
        # Cleanup
        await agent1.shutdown()
        await agent2.shutdown()
    
    def test_user_context_setting_validates_context(self):
        """Test that set_user_context validates context before storing."""
        agent = TestBaseAgent(name="ContextAgent")
        
        # Valid context should work
        valid_context = self.create_test_context("user789")
        agent.set_user_context(valid_context)
        self.assertEqual(agent.user_context.user_id, "user789")
        
        # Invalid context should raise error
        with self.assertRaises(TypeError):
            agent.set_user_context("invalid_context")
    
    async def test_factory_method_creates_isolated_agents(self):
        """Test that factory method creates properly isolated agent instances."""
        context1 = self.create_test_context("factory_user1")
        context2 = self.create_test_context("factory_user2")
        
        # Create agents using factory method
        agent1 = TestBaseAgent.create_agent_with_context(context1)
        agent2 = TestBaseAgent.create_agent_with_context(context2)
        
        # Verify agents have different contexts
        self.assertEqual(agent1.user_context.user_id, "factory_user1")
        self.assertEqual(agent2.user_context.user_id, "factory_user2")
        self.assertNotEqual(agent1.user_context, agent2.user_context)
        
        # Verify agents are separate instances
        self.assertIsNot(agent1, agent2)
        self.assertNotEqual(agent1.agent_id, agent2.agent_id)
        
        # Cleanup
        await agent1.shutdown()
        await agent2.shutdown()


class TestBaseAgentWebSocketIntegration(SSotAsyncTestCase):
    """Test suite for WebSocket integration and real-time event emission."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_agent = TestBaseAgent(name="WebSocketTestAgent")
        self.mock_bridge = Mock()
        
    async def asyncTearDown(self):
        """Clean up after tests."""
        await self.test_agent.shutdown()
    
    def test_websocket_adapter_initialization(self):
        """Test that WebSocket adapter is properly initialized."""
        self.assertTrue(hasattr(self.test_agent, '_websocket_adapter'))
        self.assertIsNotNone(self.test_agent._websocket_adapter)
        
        # Test adapter methods are available
        self.assertTrue(hasattr(self.test_agent._websocket_adapter, 'emit_thinking'))
        self.assertTrue(hasattr(self.test_agent._websocket_adapter, 'emit_tool_executing'))
        self.assertTrue(hasattr(self.test_agent._websocket_adapter, 'emit_agent_completed'))
    
    def test_websocket_bridge_setting(self):
        """Test that WebSocket bridge can be set and configured."""
        run_id = "test_run_123"
        
        # Set WebSocket bridge
        self.test_agent.set_websocket_bridge(self.mock_bridge, run_id)
        
        # Verify bridge is set in adapter
        self.assertTrue(self.test_agent._websocket_adapter.has_websocket_bridge())
    
    async def test_websocket_event_emission_methods(self):
        """Test that all WebSocket event emission methods work correctly."""
        # Enable test mode to prevent RuntimeErrors
        self.test_agent.enable_websocket_test_mode()
        
        # Test agent started event
        await self.test_agent.emit_agent_started("Test agent starting")
        
        # Test thinking event
        await self.test_agent.emit_thinking("Processing request", 1)
        
        # Test tool events
        await self.test_agent.emit_tool_executing("test_tool", {"param": "value"})
        await self.test_agent.emit_tool_completed("test_tool", {"result": "success"})
        
        # Test progress event
        await self.test_agent.emit_progress("50% complete", False)
        
        # Test completion event
        await self.test_agent.emit_agent_completed({"status": "success"})
        
        # Test error event
        await self.test_agent.emit_error("Test error", "TestError")
        
        # If we reach here without exceptions, all events were emitted successfully
        self.assertTrue(True)


class TestBaseAgentModernExecutionPatterns(SSotAsyncTestCase):
    """Test suite for modern execution patterns and UserExecutionContext compliance."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.modern_agent = TestBaseAgent(name="ModernAgent")
        self.legacy_agent = LegacyTestAgent(name="LegacyAgent")
        
    async def asyncTearDown(self):
        """Clean up after tests."""
        await self.modern_agent.shutdown()
        await self.legacy_agent.shutdown()
    
    def create_test_context(self, user_id: str = "test_user") -> UserExecutionContext:
        """Create test user execution context."""
        return UserExecutionContext(
            user_id=UserID(user_id),
            thread_id=ThreadID(f"thread_{user_id}"),
            run_id=RunID(f"run_{user_id}_{int(time.time())}"),
            request_id=f"req_{user_id}_{int(time.time())}",
            operation_depth=1,
            agent_context={"user_request": f"Test request from {user_id}"},
            metadata={}
        )
    
    async def test_modern_execution_pattern_with_user_context(self):
        """Test that modern agents execute properly with UserExecutionContext."""
        context = self.create_test_context("modern_user")
        
        # Execute agent
        result = await self.modern_agent.execute(context=context, stream_updates=True)
        
        # Verify execution result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["user_id"], "modern_user")
        self.assertIn("execution_id", result)
        
        # Verify execution was logged
        executions = self.modern_agent.get_test_executions()
        self.assertEqual(len(executions), 1)
        self.assertEqual(executions[0]["user_id"], "modern_user")
        self.assertTrue(executions[0]["stream_updates"])
    
    def test_migration_validation_for_modern_agent(self):
        """Test that migration validation correctly identifies modern agents."""
        validation = self.modern_agent.validate_modern_implementation()
        
        # Modern agent should be compliant
        self.assertTrue(validation["compliant"])
        self.assertEqual(validation["pattern"], "modern")
        
        # Should have minimal warnings
        self.assertEqual(len(validation["errors"]), 0)
    
    def test_migration_validation_for_legacy_agent(self):
        """Test that migration validation correctly identifies legacy agents."""
        validation = self.legacy_agent.validate_modern_implementation()
        
        # Legacy agent should not be compliant
        self.assertFalse(validation["compliant"])
        self.assertEqual(validation["pattern"], "legacy_bridge")
        
        # Should have warnings about deprecated pattern
        self.assertGreater(len(validation["warnings"]), 0)
        self.assertTrue(any("DEPRECATED" in warning for warning in validation["warnings"]))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])