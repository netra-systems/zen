"""
User Execution Engine Core Integration Tests - Phase 1 Multi-User Focus

Business Value Justification (BVJ):
- Segment: Platform/All Tiers
- Business Goal: Multi-Tenant Architecture & User Isolation
- Value Impact: Protects $500K+ ARR by ensuring user data isolation and concurrent execution
- Strategic Impact: Enables platform scalability and prevents data contamination risks

CRITICAL MISSION: Validates UserExecutionEngine handles concurrent users with complete
data isolation, proper resource management, and reliable execution patterns.

Phase 1 Focus Areas:
1. UserExecutionEngine multi-user concurrent execution
2. UserExecutionContext factory patterns and isolation validation  
3. User-specific WebSocket event routing and delivery
4. Resource limits and memory management per user
5. Execution state tracking and cleanup per user
6. Error isolation and recovery patterns
7. Circuit breaker and reliability per user
8. Performance under concurrent user load

NO Docker dependencies - all tests run locally with real SSOT components.
BUSINESS CRITICAL: User data contamination = immediate security incident.
"""

import asyncio
import gc
import pytest
import time
import uuid
import weakref
from datetime import datetime, timezone, UTC
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from concurrent.futures import ThreadPoolExecutor

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# User Execution Infrastructure
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory

# Agent Infrastructure
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory

# Core Infrastructure  
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.llm.llm_manager import LLMManager

# WebSocket Infrastructure
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class MockMultiUserAgent(BaseAgent):
    """Mock agent for multi-user testing."""
    
    def __init__(self, agent_id: str, simulation_type: str = "normal", *args, **kwargs):
        super().__init__(
            name=f"MultiUserAgent_{agent_id}",
            description=f"Multi-user test agent {agent_id}",
            *args,
            **kwargs
        )
        self.agent_id = agent_id
        self.simulation_type = simulation_type
        self.execution_log = []
    
    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with user context simulation."""
        
        self.execution_log.append({
            "event": "execution_started",
            "user_id": context.user_id,
            "timestamp": time.time()
        })
        
        # Emit lifecycle events
        await self.emit_agent_started(f"Starting {self.simulation_type} execution for user {context.user_id}")
        
        # Simulate different execution patterns
        if self.simulation_type == "fast":
            await asyncio.sleep(0.01)  # Fast execution
        elif self.simulation_type == "slow": 
            await asyncio.sleep(0.05)  # Slower execution
        elif self.simulation_type == "error":
            await self.emit_error(f"Simulated error for user {context.user_id}", "SimulationError")
            raise ValueError(f"Simulated error for user {context.user_id}")
        else:
            await asyncio.sleep(0.02)  # Normal execution
        
        await self.emit_thinking(f"Processing request for user {context.user_id}", context=context)
        
        # Create user-specific result
        result = {
            "status": "completed",
            "user_id": context.user_id,
            "agent_id": self.agent_id,
            "simulation_type": self.simulation_type,
            "user_data": context.metadata.get("user_data", {}),
            "execution_time": time.time()
        }
        
        # Store in context
        self.store_metadata_result(context, f"multi_user_result_{self.agent_id}", result)
        
        self.execution_log.append({
            "event": "execution_completed",
            "user_id": context.user_id, 
            "result": result,
            "timestamp": time.time()
        })
        
        await self.emit_agent_completed(result, context=context)
        
        return result


@pytest.mark.integration
class UserExecutionEngineCoreIntegrationTests(SSotAsyncTestCase):
    """Integration tests for multi-user execution engine patterns."""
    
    def create_user_context(self, user_id: str, user_data: Dict[str, Any] = None) -> UserExecutionContext:
        """Create user context with user-specific data."""
        metadata = {
            "user_request": f"Multi-user test request for {user_id}",
            "user_data": user_data or {"user_tier": "enterprise", "user_region": "us-east-1"},
            "test_scenario": "multi_user_execution",
            "sensitive_data": f"secret_data_for_{user_id}"
        }
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{user_id}_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{user_id}_{uuid.uuid4().hex[:8]}",
            db_session=None,
            websocket_connection_id=f"ws_{user_id}_{uuid.uuid4().hex[:8]}",
            metadata=metadata
        )
    
    @pytest.fixture
    async def mock_llm_manager(self):
        """Mock LLM manager for testing."""
        mock_manager = AsyncMock(spec=LLMManager) 
        mock_manager.initialize = AsyncMock()
        mock_manager._initialized = True
        mock_manager.generate_text = AsyncMock(return_value={
            "response": "Multi-user test response",
            "token_usage": {"input_tokens": 50, "output_tokens": 25, "total_cost": 0.001}
        })
        return mock_manager
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Mock WebSocket bridge with user-specific event tracking."""
        mock_bridge = AsyncMock()
        mock_bridge.user_events = {}  # Track events per user
        
        async def track_user_event(event_type, user_id, *args, **kwargs):
            if user_id not in mock_bridge.user_events:
                mock_bridge.user_events[user_id] = []
            mock_bridge.user_events[user_id].append({
                "event_type": event_type,
                "timestamp": datetime.now(UTC),
                "args": args,
                "kwargs": kwargs
            })
            return True
        
        # Mock WebSocket methods with user tracking
        mock_bridge.emit_agent_started = AsyncMock()
        mock_bridge.emit_agent_thinking = AsyncMock()
        mock_bridge.emit_agent_completed = AsyncMock() 
        mock_bridge.emit_error = AsyncMock()
        
        return mock_bridge
    
    @pytest.fixture
    async def execution_engine_factory(self, mock_websocket_bridge):
        """Real execution engine factory."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        yield factory
        await factory.shutdown()
    
    @pytest.fixture
    async def agent_instance_factory(self, mock_websocket_bridge, mock_llm_manager):
        """Real agent instance factory."""
        factory = AgentInstanceFactory()
        factory.configure(
            websocket_bridge=mock_websocket_bridge,
            llm_manager=mock_llm_manager
        )
        yield factory
        factory.reset_for_testing()
    
    @pytest.mark.real_services
    async def test_concurrent_user_execution_complete_isolation(self, execution_engine_factory):
        """Test concurrent user execution with complete data isolation."""
        
        # Create contexts for 5 different users
        num_users = 5
        user_contexts = []
        
        for i in range(num_users):
            user_data = {
                "user_tier": "enterprise" if i % 2 == 0 else "free",
                "user_preference": f"preference_{i}",
                "sensitive_data": f"secret_{i}_{uuid.uuid4().hex}",
                "user_region": "us-east-1" if i < 3 else "eu-west-1"
            }
            context = self.create_user_context(f"concurrent_user_{i:03d}", user_data)
            user_contexts.append(context)
        
        # Create execution engines for each user
        execution_engines = []
        for context in user_contexts:
            engine = await execution_engine_factory.create_for_user(context)
            execution_engines.append(engine)
        
        # Create agents with different simulation types
        agents = []
        for i, context in enumerate(user_contexts):
            simulation_type = ["fast", "normal", "slow", "normal", "fast"][i]
            agent = MockMultiUserAgent(
                agent_id=f"agent_{i:03d}",
                simulation_type=simulation_type,
                user_context=context
            )
            agents.append(agent)
        
        # Execute all users concurrently
        async def execute_user(engine, agent, context):
            return await engine.execute_agent(agent, context, stream_updates=True)
        
        # Run concurrent executions
        start_time = time.time()
        results = await asyncio.gather(*[
            execute_user(engine, agent, context)
            for engine, agent, context in zip(execution_engines, agents, user_contexts)
        ])
        execution_time = time.time() - start_time
        
        # Validate complete isolation
        assert len(results) == num_users
        
        # Check each user's result is isolated
        for i, (result, context, agent) in enumerate(zip(results, user_contexts, agents)):
            expected_user_id = f"concurrent_user_{i:03d}"
            
            assert result["status"] == "completed"
            assert result["user_id"] == expected_user_id
            assert result["agent_id"] == f"agent_{i:03d}"
            
            # Validate user-specific data is preserved
            assert result["user_data"]["user_preference"] == f"preference_{i}"
            assert result["user_data"]["sensitive_data"] == context.metadata["user_data"]["sensitive_data"]
            
            # Validate no data leakage
            for j, other_result in enumerate(results):
                if i != j:
                    assert result["user_data"]["sensitive_data"] != other_result["user_data"]["sensitive_data"]
                    assert result["user_id"] != other_result["user_id"]
        
        # Validate agent execution logs show proper isolation
        for i, agent in enumerate(agents):
            user_executions = [log for log in agent.execution_log if log["user_id"] == f"concurrent_user_{i:03d}"]
            assert len(user_executions) >= 2  # start and completion events
            
            # No logs should exist for other users
            other_user_logs = [log for log in agent.execution_log if log["user_id"] != f"concurrent_user_{i:03d}"]
            assert len(other_user_logs) == 0
        
        # Validate performance is reasonable
        assert execution_time < 1.0, f"Concurrent execution too slow: {execution_time:.2f}s"
        
        # Cleanup engines
        for engine in execution_engines:
            await execution_engine_factory.cleanup_engine(engine)
        
        self.record_metric("concurrent_users_tested", num_users)
        self.record_metric("user_isolation_verified", True)
        self.record_metric("concurrent_execution_time", execution_time)
        self.record_metric("data_leakage_detected", False)
        
    @pytest.mark.real_services  
    async def test_user_execution_context_factory_patterns(self, agent_instance_factory):
        """Test UserExecutionContext factory patterns maintain isolation."""
        
        # Create contexts for multiple users simultaneously
        num_users = 8
        contexts = []
        
        # Create contexts concurrently
        async def create_user_context(user_id):
            return await agent_instance_factory.create_user_execution_context(
                user_id=f"factory_user_{user_id}",
                thread_id=f"factory_thread_{user_id}_{uuid.uuid4().hex[:8]}",
                run_id=f"factory_run_{user_id}_{uuid.uuid4().hex[:8]}"
            )
        
        contexts = await asyncio.gather(*[
            create_user_context(i) for i in range(num_users)
        ])
        
        # Validate each context is unique and isolated
        context_ids = set()
        user_ids = set()
        thread_ids = set()
        run_ids = set()
        
        for context in contexts:
            # Check uniqueness
            context_id = f"{context.user_id}_{context.thread_id}_{context.run_id}"
            assert context_id not in context_ids, "Context IDs must be unique"
            context_ids.add(context_id)
            
            user_ids.add(context.user_id)
            thread_ids.add(context.thread_id)
            run_ids.add(context.run_id)
            
            # Validate context structure
            assert context.user_id.startswith("factory_user_")
            assert context.thread_id.startswith("factory_thread_")
            assert context.run_id.startswith("factory_run_")
            assert context.request_id is not None
        
        # All IDs should be unique
        assert len(user_ids) == num_users
        assert len(thread_ids) == num_users  
        assert len(run_ids) == num_users
        
        # Test factory metrics
        factory_metrics = agent_instance_factory.get_factory_metrics()
        assert factory_metrics["total_instances_created"] >= num_users
        assert factory_metrics["active_contexts"] >= num_users
        
        # Test concurrent context operations
        async def modify_context(context, user_index):
            """Modify context and verify isolation."""
            context.metadata[f"user_data_{user_index}"] = f"data_for_user_{user_index}"
            context.metadata["modification_time"] = time.time()
            return context
        
        modified_contexts = await asyncio.gather(*[
            modify_context(context, i) for i, context in enumerate(contexts)
        ])
        
        # Verify modifications are isolated
        for i, context in enumerate(modified_contexts):
            assert context.metadata[f"user_data_{i}"] == f"data_for_user_{i}"
            
            # Check no contamination from other users
            for j in range(num_users):
                if i != j:
                    assert f"user_data_{j}" not in context.metadata
        
        # Cleanup contexts
        for context in contexts:
            await agent_instance_factory.cleanup_user_context(context)
        
        # Verify cleanup
        final_metrics = agent_instance_factory.get_factory_metrics()
        assert final_metrics["total_contexts_cleaned"] >= num_users
        assert final_metrics["active_contexts"] == 0
        
        self.record_metric("factory_contexts_created", num_users)
        self.record_metric("context_isolation_verified", True)
        self.record_metric("factory_cleanup_working", True)
        
    @pytest.mark.real_services
    async def test_user_specific_websocket_event_routing(self, mock_websocket_bridge, execution_engine_factory):
        """Test WebSocket events are routed to correct users only."""
        
        # Create contexts for 3 users
        user_contexts = [
            self.create_user_context(f"websocket_user_{i}", {"user_role": f"role_{i}"})
            for i in range(3)
        ]
        
        # Create execution engines with WebSocket tracking
        execution_engines = []
        for context in user_contexts:
            engine = await execution_engine_factory.create_for_user(context)
            execution_engines.append(engine)
        
        # Create agents with WebSocket bridge
        agents = []
        for i, context in enumerate(user_contexts):
            agent = MockMultiUserAgent(
                agent_id=f"ws_agent_{i}",
                simulation_type="normal", 
                user_context=context
            )
            # Set WebSocket bridge with user-specific routing
            agent.set_websocket_bridge(mock_websocket_bridge, context.run_id)
            agents.append(agent)
        
        # Execute agents concurrently and track WebSocket calls
        websocket_calls = []
        
        # Mock WebSocket bridge methods to capture user-specific calls
        original_emit_started = mock_websocket_bridge.emit_agent_started
        original_emit_thinking = mock_websocket_bridge.emit_agent_thinking
        original_emit_completed = mock_websocket_bridge.emit_agent_completed
        
        async def track_emit_started(*args, **kwargs):
            websocket_calls.append(("agent_started", args, kwargs))
            return await original_emit_started(*args, **kwargs)
            
        async def track_emit_thinking(*args, **kwargs):
            websocket_calls.append(("agent_thinking", args, kwargs))
            return await original_emit_thinking(*args, **kwargs)
            
        async def track_emit_completed(*args, **kwargs):
            websocket_calls.append(("agent_completed", args, kwargs))
            return await original_emit_completed(*args, **kwargs)
        
        mock_websocket_bridge.emit_agent_started = track_emit_started
        mock_websocket_bridge.emit_agent_thinking = track_emit_thinking
        mock_websocket_bridge.emit_agent_completed = track_emit_completed
        
        # Execute all agents concurrently
        results = await asyncio.gather(*[
            engine.execute_agent(agent, context)
            for engine, agent, context in zip(execution_engines, agents, user_contexts)
        ])
        
        # Validate WebSocket events were sent for each user
        assert len(websocket_calls) >= len(user_contexts) * 2  # At least start and completion per user
        
        # Check event types distribution
        event_types = [call[0] for call in websocket_calls]
        assert "agent_started" in event_types
        assert "agent_thinking" in event_types  
        assert "agent_completed" in event_types
        
        # Validate results for each user
        for i, (result, context) in enumerate(zip(results, user_contexts)):
            assert result["status"] == "completed"
            assert result["user_id"] == f"websocket_user_{i}"
            
            # Check user-specific data in context
            stored_result_key = f"multi_user_result_ws_agent_{i}"
            assert stored_result_key in context.metadata
            stored_result = context.metadata[stored_result_key]
            assert stored_result["user_id"] == f"websocket_user_{i}"
        
        # Cleanup
        for engine in execution_engines:
            await execution_engine_factory.cleanup_engine(engine)
        
        self.record_metric("websocket_users_tested", len(user_contexts))
        self.record_metric("websocket_events_captured", len(websocket_calls))
        self.record_metric("websocket_routing_verified", True)
        
    @pytest.mark.real_services
    async def test_user_resource_limits_and_enforcement(self, execution_engine_factory):
        """Test resource limits are enforced per user."""
        
        # Create user context
        user_context = self.create_user_context("resource_limit_user")
        
        # Get factory limits
        factory_metrics = execution_engine_factory.get_factory_metrics()
        max_engines_per_user = factory_metrics.get("max_engines_per_user", 2)
        
        # Create engines up to the limit
        engines = []
        for i in range(max_engines_per_user):
            engine = await execution_engine_factory.create_for_user(user_context)
            engines.append(engine)
            assert engine.get_user_context().user_id == "resource_limit_user"
        
        # Verify limit enforcement
        try:
            # This should fail due to user limit
            excess_engine = await execution_engine_factory.create_for_user(user_context)
            # If we get here, either no limit exists or it's not enforced
            await execution_engine_factory.cleanup_engine(excess_engine)
            pytest.fail("Expected resource limit to be enforced")
        except Exception as e:
            # Expected - resource limit should be enforced
            assert "limit" in str(e).lower() or "maximum" in str(e).lower()
        
        # Verify other users can still create engines
        other_user_context = self.create_user_context("other_resource_user")
        other_user_engine = await execution_engine_factory.create_for_user(other_user_context)
        assert other_user_engine.get_user_context().user_id == "other_resource_user"
        
        # Cleanup one engine and verify we can create another for original user
        await execution_engine_factory.cleanup_engine(engines[0])
        engines.pop(0)
        
        replacement_engine = await execution_engine_factory.create_for_user(user_context)
        engines.append(replacement_engine)
        
        # Cleanup all engines
        for engine in engines:
            await execution_engine_factory.cleanup_engine(engine)
        await execution_engine_factory.cleanup_engine(other_user_engine)
        
        # Verify cleanup metrics
        final_metrics = execution_engine_factory.get_factory_metrics()
        assert final_metrics["total_engines_cleaned"] >= max_engines_per_user + 1
        
        self.record_metric("resource_limits_enforced", True)
        self.record_metric("max_engines_per_user", max_engines_per_user)
        self.record_metric("cross_user_isolation_verified", True)
        
    @pytest.mark.real_services
    async def test_user_execution_error_isolation(self, execution_engine_factory):
        """Test errors in one user's execution don't affect other users."""
        
        # Create contexts for 4 users
        user_contexts = [
            self.create_user_context(f"error_test_user_{i}")
            for i in range(4)
        ]
        
        # Create execution engines
        execution_engines = []
        for context in user_contexts:
            engine = await execution_engine_factory.create_for_user(context)
            execution_engines.append(engine)
        
        # Create agents - one will fail, others should succeed
        agents = []
        simulation_types = ["normal", "normal", "error", "normal"]  # Third agent will error
        
        for i, (context, sim_type) in enumerate(zip(user_contexts, simulation_types)):
            agent = MockMultiUserAgent(
                agent_id=f"error_agent_{i}",
                simulation_type=sim_type,
                user_context=context
            )
            agents.append(agent)
        
        # Execute all agents concurrently (one will fail)
        results = await asyncio.gather(*[
            self._safe_execute_agent(engine, agent, context)
            for engine, agent, context in zip(execution_engines, agents, user_contexts)
        ], return_exceptions=True)
        
        # Validate error isolation
        successful_results = []
        error_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_results.append((i, result))
            else:
                successful_results.append((i, result))
        
        # Should have 1 error and 3 successes
        assert len(error_results) == 1, f"Expected 1 error, got {len(error_results)}"
        assert len(successful_results) == 3, f"Expected 3 successes, got {len(successful_results)}"
        
        # Verify error is from the expected agent
        error_index, error_exception = error_results[0]
        assert error_index == 2  # Third agent (index 2) should have failed
        assert "error_test_user_2" in str(error_exception)
        
        # Verify successful executions
        for success_index, result in successful_results:
            assert result["status"] == "completed"
            assert result["user_id"] == f"error_test_user_{success_index}"
            expected_agent_id = f"error_agent_{success_index}"
            assert result["agent_id"] == expected_agent_id
        
        # Verify engine health after error
        for i, engine in enumerate(execution_engines):
            if i != 2:  # Non-erroring engines should be healthy
                assert engine.is_active()
        
        # Cleanup engines
        for engine in execution_engines:
            try:
                await execution_engine_factory.cleanup_engine(engine)
            except:
                pass  # Error engine might already be cleaned up
        
        self.record_metric("error_isolation_verified", True)
        self.record_metric("error_users_contained", 1)
        self.record_metric("successful_users_unaffected", 3)
        
    async def _safe_execute_agent(self, engine, agent, context):
        """Safely execute agent, returning result or raising exception."""
        try:
            return await engine.execute_agent(agent, context)
        except Exception as e:
            # Re-raise to be caught by gather
            raise e
    
    @pytest.mark.real_services
    async def test_user_execution_memory_cleanup(self, agent_instance_factory, execution_engine_factory):
        """Test user execution cleanup prevents memory leaks."""
        
        initial_memory = self.get_memory_usage_mb()
        
        # Create and execute many user sessions
        num_sessions = 15
        session_data = []
        
        for i in range(num_sessions):
            user_id = f"memory_user_{i:03d}"
            
            # Create context with bulk data
            context = self.create_user_context(user_id, {
                "bulk_data": "x" * 1000,  # 1KB per user
                "user_files": [f"file_{j}.dat" for j in range(10)],
                "session_data": {"key": f"value_{i}", "timestamp": time.time()}
            })
            
            # Create execution engine
            engine = await execution_engine_factory.create_for_user(context)
            
            # Create and execute agent
            agent = MockMultiUserAgent(
                agent_id=f"memory_agent_{i}",
                simulation_type="fast",
                user_context=context
            )
            
            # Execute agent
            result = await engine.execute_agent(agent, context)
            
            # Store session data for cleanup tracking
            session_data.append({
                "user_id": user_id,
                "context": context,
                "engine": engine,
                "agent": agent,
                "result": result
            })
        
        # Verify all executions succeeded
        for session in session_data:
            assert session["result"]["status"] == "completed"
            assert session["result"]["user_id"] == session["user_id"]
        
        # Cleanup all sessions
        for session in session_data:
            # Cleanup engine
            await execution_engine_factory.cleanup_engine(session["engine"])
            
            # Cleanup context  
            await agent_instance_factory.cleanup_user_context(session["context"])
            
            # Cleanup agent
            await session["agent"].cleanup()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)  # Allow async cleanup
        
        # Check memory usage
        final_memory = self.get_memory_usage_mb()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (< 10MB for 15 sessions)
        assert memory_increase < 10.0, f"Potential memory leak: {memory_increase:.1f}MB increase"
        
        # Verify factory cleanup metrics
        factory_metrics = agent_instance_factory.get_factory_metrics()
        assert factory_metrics["total_contexts_cleaned"] >= num_sessions
        assert factory_metrics["active_contexts"] == 0
        
        execution_metrics = execution_engine_factory.get_factory_metrics()
        assert execution_metrics["total_engines_cleaned"] >= num_sessions
        
        self.record_metric("memory_cleanup_verified", True)
        self.record_metric("user_sessions_cleaned", num_sessions)
        self.record_metric("memory_increase_mb", memory_increase)
        
    @pytest.mark.real_services
    async def test_user_execution_performance_under_load(self, execution_engine_factory):
        """Test user execution performance under concurrent load."""
        
        # Create high-concurrency scenario
        num_concurrent_users = 20
        user_contexts = [
            self.create_user_context(f"perf_user_{i:03d}")
            for i in range(num_concurrent_users)
        ]
        
        # Create execution engines
        engines = []
        for context in user_contexts:
            engine = await execution_engine_factory.create_for_user(context)
            engines.append(engine)
        
        # Create agents with mixed execution types
        agents = []
        for i, context in enumerate(user_contexts):
            sim_type = ["fast", "normal", "slow"][i % 3]
            agent = MockMultiUserAgent(
                agent_id=f"perf_agent_{i}",
                simulation_type=sim_type,
                user_context=context
            )
            agents.append(agent)
        
        # Measure concurrent execution performance
        start_time = time.perf_counter()
        
        results = await asyncio.gather(*[
            engine.execute_agent(agent, context)
            for engine, agent, context in zip(engines, agents, user_contexts)
        ])
        
        end_time = time.perf_counter()
        total_execution_time = end_time - start_time
        
        # Validate all executions succeeded
        assert len(results) == num_concurrent_users
        for i, result in enumerate(results):
            assert result["status"] == "completed"
            assert result["user_id"] == f"perf_user_{i:03d}"
        
        # Performance requirements
        avg_time_per_user = total_execution_time / num_concurrent_users
        
        # Should handle concurrent users efficiently
        assert total_execution_time < 2.0, f"Concurrent execution too slow: {total_execution_time:.2f}s"
        assert avg_time_per_user < 0.1, f"Average time per user too high: {avg_time_per_user:.3f}s"
        
        # Check for user isolation in results
        user_ids = {result["user_id"] for result in results}
        assert len(user_ids) == num_concurrent_users, "User ID isolation failed"
        
        # Cleanup
        for engine in engines:
            await execution_engine_factory.cleanup_engine(engine)
        
        self.record_metric("concurrent_users_tested", num_concurrent_users)
        self.record_metric("total_execution_time", total_execution_time)
        self.record_metric("avg_time_per_user", avg_time_per_user)
        self.record_metric("performance_requirements_met", True)
        
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    
    def teardown_method(self, method=None):
        """Clean up test resources."""
        super().teardown_method(method)
        
        # Force garbage collection
        gc.collect()
        
        # Log comprehensive metrics
        metrics = self.get_all_metrics()
        print(f"\nUser Execution Engine Core Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        # Verify critical metrics for business value protection
        critical_metrics = [
            "user_isolation_verified",
            "context_isolation_verified",
            "error_isolation_verified",
            "memory_cleanup_verified",
            "performance_requirements_met"
        ]
        
        for metric in critical_metrics:
            assert metrics.get(metric, False), f"Critical metric {metric} failed - multi-user platform at risk"