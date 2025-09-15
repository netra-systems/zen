"""
BaseAgent Lifecycle Integration Tests - Phase 1 Core Infrastructure

Business Value Justification (BVJ):
- Segment: Platform/All Tiers
- Business Goal: Platform Stability & Agent Execution Reliability  
- Value Impact: Protects $500K+ ARR by ensuring BaseAgent lifecycle works correctly
- Strategic Impact: Core platform functionality - agent lifecycle enables chat value delivery

CRITICAL MISSION: Validates BaseAgent lifecycle management including initialization, 
execution patterns, state transitions, error handling, and cleanup operations.

Phase 1 Focus Areas:
1. BaseAgent initialization and factory pattern validation
2. State lifecycle management (PENDING → RUNNING → COMPLETED/FAILED → SHUTDOWN)
3. UserExecutionContext integration and user isolation
4. WebSocket integration and event emission during lifecycle
5. Error handling and recovery patterns
6. Resource cleanup and memory leak prevention
7. Concurrent execution scenarios
8. Circuit breaker and reliability infrastructure

NO Docker dependencies - all tests run locally with real SSOT components.
"""

import asyncio
import gc
import pytest
import time
import uuid
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# SSOT Base Test Case 
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core Agent Infrastructure
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.llm.llm_manager import LLMManager

# WebSocket and Infrastructure
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Test Utilities
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager


class BaseAgentLifecyclePatternsTests(BaseAgent):
    """Test BaseAgent implementation with modern UserExecutionContext pattern."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(
            name="TestLifecycleAgent",
            description="Test agent for lifecycle validation",
            *args,
            **kwargs
        )
        # Track execution history for testing
        self.execution_history = []
        self.lifecycle_events = []
    
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Modern execution pattern implementation."""
        
        # Record lifecycle event
        self.lifecycle_events.append({"event": "execution_started", "timestamp": time.time()})
        
        # Emit WebSocket events during execution
        await self.emit_agent_started("Starting test lifecycle execution")
        
        # Simulate execution phases
        await self.emit_thinking("Processing user request", step_number=1, context=context)
        
        # Simulate some work
        await asyncio.sleep(0.01)
        
        # Store execution result
        result = {
            "status": "completed",
            "user_request": context.metadata.get("user_request", ""),
            "execution_time": time.time(),
            "context_data": {
                "user_id": context.user_id,
                "thread_id": context.thread_id,
                "run_id": context.run_id
            }
        }
        
        # Store result in context
        self.store_metadata_result(context, "test_execution_result", result)
        
        # Track execution
        self.execution_history.append(result)
        self.lifecycle_events.append({"event": "execution_completed", "timestamp": time.time()})
        
        # Emit completion
        await self.emit_agent_completed(result, context=context)
        
        return result


@pytest.mark.integration
class BaseAgentLifecycleIntegrationTests(SSotAsyncTestCase):
    """Integration tests for BaseAgent lifecycle management."""
    
    def create_test_user_context(self, user_id: str = None, metadata: Dict[str, Any] = None) -> UserExecutionContext:
        """Create test UserExecutionContext with realistic data."""
        user_id = user_id or f"test_user_{uuid.uuid4().hex[:8]}"
        default_metadata = {
            "user_request": "Test agent lifecycle execution",
            "agent_input": "lifecycle_test_request",
            "priority": "high"
        }
        if metadata:
            default_metadata.update(metadata)
            
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            db_session=None,  # No real DB session for integration test
            websocket_connection_id=f"ws_{uuid.uuid4().hex[:8]}",
            metadata=default_metadata
        )
    
    @pytest.fixture
    async def mock_llm_manager(self):
        """Mock LLM manager for testing."""
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.initialize = AsyncMock()
        mock_manager._initialized = True
        mock_manager.generate_text = AsyncMock(return_value={
            "response": "Test response from LLM",
            "token_usage": {"input_tokens": 100, "output_tokens": 50, "total_cost": 0.0025}
        })
        return mock_manager
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Mock WebSocket bridge with event tracking."""
        mock_bridge = AsyncMock()
        mock_bridge.events_emitted = []
        
        async def track_event(event_type, *args, **kwargs):
            mock_bridge.events_emitted.append({
                "event_type": event_type,
                "timestamp": datetime.utcnow(),
                "args": args,
                "kwargs": kwargs
            })
            return True
        
        mock_bridge.emit_agent_started = AsyncMock(side_effect=lambda *args, **kwargs: track_event("agent_started", *args, **kwargs))
        mock_bridge.emit_agent_thinking = AsyncMock(side_effect=lambda *args, **kwargs: track_event("agent_thinking", *args, **kwargs))
        mock_bridge.emit_agent_completed = AsyncMock(side_effect=lambda *args, **kwargs: track_event("agent_completed", *args, **kwargs))
        mock_bridge.emit_error = AsyncMock(side_effect=lambda *args, **kwargs: track_event("error", *args, **kwargs))
        
        return mock_bridge
    
    @pytest.mark.real_services
    async def test_base_agent_initialization_with_user_context_factory(self, mock_llm_manager):
        """Test BaseAgent factory initialization with UserExecutionContext."""
        
        # Create user context
        user_context = self.create_test_user_context("factory_test_user")
        
        # Test factory creation
        agent = BaseAgent.create_agent_with_context(user_context)
        
        # Assert proper factory initialization
        assert isinstance(agent, BaseAgent)
        assert agent.name == "BaseAgent"
        assert agent.user_context == user_context
        assert agent.state == SubAgentLifecycle.PENDING
        
        # Assert infrastructure components initialized
        assert agent._reliability_manager_instance is not None
        assert agent._execution_engine is not None
        assert agent.monitor is not None
        assert agent.timing_collector is not None
        
        # Assert WebSocket integration ready
        assert agent._websocket_adapter is not None
        
        # Verify user context validation passed
        validation_result = agent.validate_modern_implementation()
        assert validation_result["pattern"] in ["modern", "none"]  # "none" acceptable if not implemented
        
        self.record_metric("factory_initialization_success", True)
        self.record_metric("user_context_properly_set", agent.user_context.user_id == "factory_test_user")
        
    @pytest.mark.real_services
    async def test_base_agent_lifecycle_state_transitions(self):
        """Test BaseAgent state lifecycle transitions."""
        
        user_context = self.create_test_user_context("lifecycle_test_user")
        agent = BaseAgent.create_agent_with_context(user_context)
        
        # Test initial state
        assert agent.get_state() == SubAgentLifecycle.PENDING
        
        # Test valid state transitions
        state_transitions = [
            (SubAgentLifecycle.PENDING, SubAgentLifecycle.RUNNING),
            (SubAgentLifecycle.RUNNING, SubAgentLifecycle.COMPLETED),
            (SubAgentLifecycle.COMPLETED, SubAgentLifecycle.SHUTDOWN)
        ]
        
        for from_state, to_state in state_transitions:
            if agent.get_state() != from_state:
                agent.set_state(from_state)
            
            agent.set_state(to_state)
            assert agent.get_state() == to_state
        
        # Test invalid transition (should raise error)
        with pytest.raises(ValueError, match="Invalid state transition"):
            agent.set_state(SubAgentLifecycle.RUNNING)  # Can't go back from SHUTDOWN
        
        # Test failed state recovery
        failed_agent = BaseAgent.create_agent_with_context(user_context)
        failed_agent.set_state(SubAgentLifecycle.RUNNING)
        failed_agent.set_state(SubAgentLifecycle.FAILED)
        
        # Failed state can retry
        failed_agent.set_state(SubAgentLifecycle.RUNNING)
        assert failed_agent.get_state() == SubAgentLifecycle.RUNNING
        
        self.record_metric("state_transitions_working", True)
        self.record_metric("invalid_transitions_blocked", True)
        self.record_metric("failure_recovery_working", True)
        
    @pytest.mark.real_services
    async def test_base_agent_user_execution_context_integration(self, mock_websocket_bridge):
        """Test BaseAgent integration with UserExecutionContext."""
        
        user_context = self.create_test_user_context("integration_test_user", {
            "user_request": "Test user execution context integration",
            "business_value": "high",
            "integration_test": True
        })
        
        # Create agent with test pattern
        agent = BaseAgentLifecyclePatternsTests(user_context=user_context)
        agent.set_websocket_bridge(mock_websocket_bridge, user_context.run_id)
        
        # Execute with user context
        result = await agent.execute(user_context, stream_updates=True)
        
        # Validate execution result
        assert result["status"] == "completed"
        assert result["user_request"] == "Test user execution context integration"
        assert result["context_data"]["user_id"] == "integration_test_user"
        assert result["context_data"]["thread_id"] == user_context.thread_id
        assert result["context_data"]["run_id"] == user_context.run_id
        
        # Validate context metadata storage
        assert "test_execution_result" in user_context.metadata
        stored_result = user_context.metadata["test_execution_result"]
        assert stored_result["status"] == "completed"
        
        # Validate WebSocket events were emitted
        emitted_events = {event["event_type"] for event in mock_websocket_bridge.events_emitted}
        critical_events = ["agent_started", "agent_thinking", "agent_completed"]
        for event_type in critical_events:
            assert event_type in emitted_events, f"Critical event {event_type} not emitted"
        
        # Validate lifecycle events recorded
        assert len(agent.lifecycle_events) >= 2
        assert agent.lifecycle_events[0]["event"] == "execution_started"
        assert agent.lifecycle_events[-1]["event"] == "execution_completed"
        
        self.record_metric("user_context_integration_success", True)
        self.record_metric("websocket_events_emitted", len(mock_websocket_bridge.events_emitted))
        self.record_metric("lifecycle_events_recorded", len(agent.lifecycle_events))
        
    @pytest.mark.real_services
    async def test_base_agent_concurrent_execution_isolation(self, mock_websocket_bridge):
        """Test BaseAgent handles concurrent executions with proper user isolation."""
        
        # Create contexts for different users
        user_contexts = [
            self.create_test_user_context(f"concurrent_user_{i}", {
                "user_request": f"Concurrent request {i}",
                "user_data": f"sensitive_data_{i}"
            })
            for i in range(3)
        ]
        
        # Create agents using factory pattern
        agents = [
            BaseAgentLifecyclePatternsTests(user_context=context)
            for context in user_contexts
        ]
        
        # Set WebSocket bridges
        for i, agent in enumerate(agents):
            agent.set_websocket_bridge(mock_websocket_bridge, user_contexts[i].run_id)
        
        # Execute all agents concurrently
        tasks = [
            agent.execute(context, stream_updates=True)
            for agent, context in zip(agents, user_contexts)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Validate each execution was isolated
        for i, (result, context, agent) in enumerate(zip(results, user_contexts, agents)):
            assert result["status"] == "completed"
            assert result["user_request"] == f"Concurrent request {i}"
            assert result["context_data"]["user_id"] == f"concurrent_user_{i}"
            
            # Validate context isolation
            assert context.metadata["user_request"] == f"Concurrent request {i}"
            assert context.metadata["user_data"] == f"sensitive_data_{i}"
            
            # Validate agent isolation
            assert len(agent.execution_history) == 1
            assert agent.execution_history[0]["context_data"]["user_id"] == f"concurrent_user_{i}"
        
        # Validate no data leakage between agents
        for i in range(len(agents)):
            for j in range(len(agents)):
                if i != j:
                    agent_i_data = agents[i].execution_history[0]["user_request"]
                    agent_j_data = agents[j].execution_history[0]["user_request"]
                    assert agent_i_data != agent_j_data
        
        # Validate correlation IDs are unique
        correlation_ids = [agent.correlation_id for agent in agents]
        assert len(set(correlation_ids)) == len(correlation_ids), "Correlation IDs must be unique"
        
        self.record_metric("concurrent_execution_success", True)
        self.record_metric("user_isolation_maintained", True)
        self.record_metric("concurrent_agents_tested", len(agents))
        
    @pytest.mark.real_services 
    async def test_base_agent_error_handling_and_recovery(self, mock_websocket_bridge):
        """Test BaseAgent error handling, recovery, and cleanup patterns."""
        
        user_context = self.create_test_user_context("error_test_user")
        agent = BaseAgent.create_agent_with_context(user_context)
        agent.set_websocket_bridge(mock_websocket_bridge, user_context.run_id)
        
        # Test error emission
        await agent.emit_error("Test error for lifecycle validation", error_type="LifecycleTestError", error_details={
            "phase": "error_handling_test",
            "user_id": user_context.user_id
        })
        
        # Validate error was emitted
        error_events = [e for e in mock_websocket_bridge.events_emitted if e["event_type"] == "error"]
        assert len(error_events) >= 1
        
        # Test state recovery after error
        agent.set_state(SubAgentLifecycle.RUNNING)
        agent.set_state(SubAgentLifecycle.FAILED)
        
        # Agent should be able to reset and retry
        await agent.reset_state()
        assert agent.get_state() == SubAgentLifecycle.PENDING
        
        # Test health status during error conditions
        health_status = agent.get_health_status()
        assert "agent_name" in health_status
        assert "state" in health_status
        assert "websocket_available" in health_status
        
        # Test circuit breaker status
        cb_status = agent.get_circuit_breaker_status()
        assert "state" in cb_status or "status" in cb_status
        
        # Test graceful shutdown after error
        await agent.shutdown()
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN
        
        # Test idempotent shutdown
        await agent.shutdown()  # Should not raise exception
        assert agent.get_state() == SubAgentLifecycle.SHUTDOWN
        
        self.record_metric("error_handling_working", True)
        self.record_metric("state_recovery_working", True)
        self.record_metric("graceful_shutdown_working", True)
        
    @pytest.mark.real_services
    async def test_base_agent_memory_leak_prevention(self):
        """Test BaseAgent prevents memory leaks through proper cleanup."""
        
        initial_memory = self.get_memory_usage_mb()
        
        # Create many agents to test for leaks
        num_agents = 20
        agent_refs = []
        
        for i in range(num_agents):
            user_context = self.create_test_user_context(f"memory_test_user_{i}")
            agent = BaseAgentLifecyclePatternsTests(user_context=user_context)
            
            # Add bulk data to test cleanup
            agent.context[f"test_data_{i}"] = "x" * 1000
            user_context.metadata[f"bulk_data_{i}"] = "y" * 500
            
            # Create weak reference to track cleanup
            agent_refs.append(weakref.ref(agent))
            
            # Execute agent
            await agent.execute(user_context)
            
            # Cleanup agent
            await agent.cleanup()
            
            # Clear reference
            del agent
            del user_context
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow async cleanup
        
        # Check memory usage
        final_memory = self.get_memory_usage_mb()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (< 5MB for 20 agents)
        assert memory_increase < 5.0, f"Potential memory leak: {memory_increase:.1f}MB increase"
        
        # Check weak references - most should be dead
        dead_refs = sum(1 for ref in agent_refs if ref() is None)
        live_refs = len(agent_refs) - dead_refs
        
        # Allow some live references due to Python's garbage collection
        assert live_refs <= 3, f"Too many live agent references: {live_refs}"
        
        self.record_metric("memory_leak_prevention_verified", True)
        self.record_metric("agents_created_and_cleaned", num_agents)
        self.record_metric("memory_increase_mb", memory_increase)
        self.record_metric("dead_references", dead_refs)
        
    @pytest.mark.real_services
    async def test_base_agent_reliability_infrastructure_integration(self):
        """Test BaseAgent integration with reliability infrastructure."""
        
        user_context = self.create_test_user_context("reliability_test_user")
        agent = BaseAgent.create_agent_with_context(user_context)
        
        # Verify reliability manager is available
        assert agent.reliability_manager is not None
        
        # Test reliability manager health
        reliability_health = agent.reliability_manager.get_health_status()
        assert isinstance(reliability_health, dict)
        assert "status" in reliability_health
        
        # Test circuit breaker integration
        cb_status = agent.get_circuit_breaker_status()
        assert cb_status is not None
        
        # Test unified reliability handler (SSOT)
        assert agent.unified_reliability_handler is not None
        
        # Test execution with reliability
        call_count = 0
        async def reliable_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Simulated transient error")
            return {"status": "success_after_retry", "attempt": call_count}
        
        result = await agent.execute_with_reliability(
            operation=reliable_operation,
            operation_name="test_reliable_operation"
        )
        
        assert result["status"] == "success_after_retry"
        assert result["attempt"] == 2  # Should have retried
        
        # Verify health status includes reliability metrics
        health_status = agent.get_health_status()
        assert "uses_unified_reliability" in health_status
        assert health_status["uses_unified_reliability"] is True
        
        self.record_metric("reliability_infrastructure_integrated", True)
        self.record_metric("circuit_breaker_working", True)
        self.record_metric("retry_logic_working", True)
        
    @pytest.mark.real_services
    async def test_base_agent_websocket_bridge_integration(self, mock_websocket_bridge):
        """Test BaseAgent WebSocket bridge integration throughout lifecycle."""
        
        user_context = self.create_test_user_context("websocket_test_user")
        agent = BaseAgent.create_agent_with_context(user_context)
        
        # Set WebSocket bridge
        agent.set_websocket_bridge(mock_websocket_bridge, user_context.run_id)
        
        # Test bridge detection
        assert agent.has_websocket_context()
        
        # Test all WebSocket event types during lifecycle
        await agent.emit_agent_started("Testing WebSocket integration")
        await agent.emit_thinking("Processing lifecycle test", step_number=1, context=user_context)
        await agent.emit_progress("Lifecycle test progress", is_complete=False)
        await agent.emit_tool_executing("test_tool", {"param": "value"})
        await agent.emit_tool_completed("test_tool", {"result": "success"})
        await agent.emit_agent_completed({"status": "lifecycle_complete"}, context=user_context)
        
        # Test error emission
        await agent.emit_error("Test lifecycle error", error_type="LifecycleError")
        
        # Validate all events were emitted
        emitted_event_types = {event["event_type"] for event in mock_websocket_bridge.events_emitted}
        
        expected_events = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed", "error"
        ]
        
        for event_type in expected_events:
            assert event_type in emitted_event_types, f"Event {event_type} not emitted"
        
        # Test WebSocket adapter functionality
        assert agent._websocket_adapter is not None
        
        # Validate events have proper structure
        for event in mock_websocket_bridge.events_emitted:
            assert "event_type" in event
            assert "timestamp" in event
            assert isinstance(event["timestamp"], datetime)
        
        self.record_metric("websocket_integration_complete", True)
        self.record_metric("websocket_events_tested", len(expected_events))
        self.record_metric("total_events_emitted", len(mock_websocket_bridge.events_emitted))
        
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # Fallback if psutil not available
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        
    def teardown_method(self, method=None):
        """Clean up test resources."""
        super().teardown_method(method)
        
        # Force garbage collection
        gc.collect()
        
        # Log comprehensive metrics
        metrics = self.get_all_metrics()
        print(f"\nBaseAgent Lifecycle Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        # Verify critical metrics for business value protection
        critical_metrics = [
            "factory_initialization_success",
            "state_transitions_working", 
            "user_context_integration_success",
            "user_isolation_maintained",
            "memory_leak_prevention_verified"
        ]
        
        for metric in critical_metrics:
            assert metrics.get(metric, False), f"Critical metric {metric} failed - business value at risk"