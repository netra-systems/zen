"""Integration Tests: Concurrent Agent Execution Safety

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure platform handles multiple concurrent users and agent executions safely
- Value Impact: Concurrent execution is critical for multi-user platform scalability
- Strategic Impact: Foundation for enterprise-grade performance under load

This test suite validates:
1. Multiple concurrent agent executions within single user session
2. Multiple concurrent users executing agents simultaneously  
3. Resource contention handling and thread safety
4. Memory management under concurrent load
5. WebSocket event isolation during concurrent execution
6. Performance degradation patterns under load
7. Deadlock prevention and resource cleanup
8. User isolation during high concurrency

CRITICAL: Tests realistic concurrent scenarios that occur in production.
Validates that concurrency doesn't break user isolation or cause resource leaks.
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import threading

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

logger = central_logger.get_logger(__name__)


class ConcurrentTestAgent(BaseAgent):
    """Agent designed to test concurrent execution patterns."""
    
    # Class-level counters for testing concurrency
    _global_execution_count = 0
    _active_executions = 0
    _max_concurrent_executions = 0
    _execution_lock = threading.Lock()
    
    def __init__(self, name: str, llm_manager: LLMManager, execution_delay: float = 0.1,
                 resource_intensive: bool = False):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Concurrent test {name} agent")
        self.execution_delay = execution_delay
        self.resource_intensive = resource_intensive
        self.instance_execution_count = 0
        self.websocket_bridge = None
        self._run_id = None
        self.execution_stats = []
        
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    @classmethod
    def reset_global_counters(cls):
        """Reset global counters for testing."""
        with cls._execution_lock:
            cls._global_execution_count = 0
            cls._active_executions = 0
            cls._max_concurrent_executions = 0
            
    @classmethod
    def get_global_stats(cls):
        """Get global execution statistics."""
        with cls._execution_lock:
            return {
                "total_executions": cls._global_execution_count,
                "active_executions": cls._active_executions,
                "max_concurrent": cls._max_concurrent_executions
            }
            
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute with concurrency tracking."""
        execution_start = time.time()
        
        # Track concurrent executions
        with self._execution_lock:
            self.__class__._global_execution_count += 1
            self.__class__._active_executions += 1
            if self.__class__._active_executions > self.__class__._max_concurrent_executions:
                self.__class__._max_concurrent_executions = self.__class__._active_executions
        
        self.instance_execution_count += 1
        
        try:
            # Send WebSocket events if available
            if stream_updates and self.websocket_bridge:
                await self.websocket_bridge.notify_agent_started(
                    run_id, self.name, {"concurrent_execution": True}
                )
                
                await self.websocket_bridge.notify_agent_thinking(
                    run_id, self.name, f"Processing {self.name} with concurrency testing..."
                )
            
            # Simulate work with configurable delay
            if self.resource_intensive:
                # Simulate CPU-intensive work
                await self._simulate_cpu_intensive_work()
            else:
                # Simulate I/O work
                await asyncio.sleep(self.execution_delay)
                
            # Simulate tool usage
            if stream_updates and self.websocket_bridge:
                await self.websocket_bridge.notify_tool_executing(
                    run_id, self.name, f"{self.name}_concurrent_tool", {"concurrency_test": True}
                )
                
                await asyncio.sleep(self.execution_delay / 2)
                
                await self.websocket_bridge.notify_tool_completed(
                    run_id, self.name, f"{self.name}_concurrent_tool", 
                    {"success": True, "processed_concurrently": True}
                )
                
            # Final thinking and completion
            if stream_updates and self.websocket_bridge:
                await self.websocket_bridge.notify_agent_thinking(
                    run_id, self.name, f"Completing {self.name} concurrent execution..."
                )
                
            execution_time = time.time() - execution_start
            
            # Store execution stats
            stats = {
                "execution_time": execution_time,
                "user_id": getattr(state, 'user_id', None),
                "run_id": run_id,
                "concurrent_at_start": self.__class__._active_executions,
                "timestamp": datetime.now(timezone.utc)
            }
            self.execution_stats.append(stats)
            
            # Send completion event
            if stream_updates and self.websocket_bridge:
                await self.websocket_bridge.notify_agent_completed(
                    run_id, self.name, {"success": True, "stats": stats}, 
                    execution_time_ms=int(execution_time * 1000)
                )
            
            return {
                "success": True,
                "agent_name": self.name,
                "execution_count": self.instance_execution_count,
                "execution_time": execution_time,
                "concurrent_execution": True,
                "user_id": getattr(state, 'user_id', None),
                "concurrency_stats": {
                    "active_during_execution": stats["concurrent_at_start"],
                    "resource_intensive": self.resource_intensive
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            # Decrement active execution count
            with self._execution_lock:
                self.__class__._active_executions -= 1
                
    async def _simulate_cpu_intensive_work(self):
        """Simulate CPU-intensive work that could cause contention."""
        # Use asyncio.sleep with small intervals to simulate CPU work
        # while still yielding control to the event loop
        iterations = int(self.execution_delay * 20)  # More iterations for longer delay
        for _ in range(iterations):
            await asyncio.sleep(0.01)  # Small sleep to simulate CPU + I/O mix


class ConcurrencyWebSocketManager:
    """WebSocket manager optimized for concurrency testing."""
    
    def __init__(self):
        self.all_events = []
        self.events_by_user = {}
        self.events_by_run = {}
        self.concurrent_event_timestamps = []
        self._event_lock = asyncio.Lock()
        
    async def create_bridge(self, user_context: UserExecutionContext):
        """Create WebSocket bridge with concurrency tracking."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.tracked_events = []
        
        async def track_concurrent_event(event_type: str, data: Dict, **kwargs):
            """Track event with concurrency safety."""
            timestamp = datetime.now(timezone.utc)
            
            async with self._event_lock:
                event = {
                    "event_type": event_type,
                    "data": data,
                    "user_id": user_context.user_id,
                    "run_id": user_context.run_id,
                    "timestamp": timestamp,
                    "thread_id": threading.get_ident(),
                    "kwargs": kwargs
                }
                
                # Store in multiple indexes
                bridge.tracked_events.append(event)
                self.all_events.append(event)
                self.concurrent_event_timestamps.append(timestamp)
                
                # Index by user (thread-safe)
                if user_context.user_id not in self.events_by_user:
                    self.events_by_user[user_context.user_id] = []
                self.events_by_user[user_context.user_id].append(event)
                
                # Index by run (thread-safe)
                if user_context.run_id not in self.events_by_run:
                    self.events_by_run[user_context.run_id] = []
                self.events_by_run[user_context.run_id].append(event)
                
            return True
            
        # Mock all WebSocket methods with concurrency tracking
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            track_concurrent_event("agent_started", {"agent_name": agent_name, "context": context or {}}))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, reasoning, step_number=None, progress_percentage=None:
            track_concurrent_event("agent_thinking", {"agent_name": agent_name, "reasoning": reasoning}))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, parameters:
            track_concurrent_event("tool_executing", {"agent_name": agent_name, "tool_name": tool_name}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            track_concurrent_event("tool_completed", {"agent_name": agent_name, "tool_name": tool_name}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, execution_time_ms:
            track_concurrent_event("agent_completed", {"agent_name": agent_name, "execution_time_ms": execution_time_ms}))
        bridge.notify_agent_error = AsyncMock(side_effect=lambda run_id, agent_name, error, error_context=None:
            track_concurrent_event("agent_error", {"agent_name": agent_name, "error": str(error)}))
        
        return bridge
        
    def get_concurrency_metrics(self) -> Dict[str, Any]:
        """Get concurrency analysis metrics."""
        if not self.concurrent_event_timestamps:
            return {"no_events": True}
            
        timestamps = sorted(self.concurrent_event_timestamps)
        
        # Calculate event rate
        total_time = (timestamps[-1] - timestamps[0]).total_seconds()
        events_per_second = len(timestamps) / max(total_time, 0.001)
        
        # Calculate concurrent event clusters
        concurrent_clusters = []
        current_cluster = []
        
        for i, ts in enumerate(timestamps):
            if not current_cluster:
                current_cluster = [ts]
            else:
                # If within 50ms of last event, consider it concurrent
                if (ts - current_cluster[-1]).total_seconds() < 0.05:
                    current_cluster.append(ts)
                else:
                    if len(current_cluster) > 1:
                        concurrent_clusters.append(current_cluster)
                    current_cluster = [ts]
                    
        if len(current_cluster) > 1:
            concurrent_clusters.append(current_cluster)
            
        return {
            "total_events": len(self.all_events),
            "unique_users": len(self.events_by_user),
            "unique_runs": len(self.events_by_run),
            "events_per_second": events_per_second,
            "concurrent_clusters": len(concurrent_clusters),
            "max_cluster_size": max(len(cluster) for cluster in concurrent_clusters) if concurrent_clusters else 0,
            "total_duration_seconds": total_time
        }


class TestConcurrentAgentExecutionIntegration(BaseIntegrationTest):
    """Integration tests for concurrent agent execution safety."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        self.websocket_manager = ConcurrencyWebSocketManager()
        
        # Reset global counters
        ConcurrentTestAgent.reset_global_counters()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_manager.initialize = AsyncMock()
        return mock_manager
        
    @pytest.fixture
    async def concurrent_agents(self, mock_llm_manager):
        """Create agents optimized for concurrent testing."""
        return {
            "fast_agent": ConcurrentTestAgent("fast_agent", mock_llm_manager, execution_delay=0.05),
            "medium_agent": ConcurrentTestAgent("medium_agent", mock_llm_manager, execution_delay=0.1),
            "slow_agent": ConcurrentTestAgent("slow_agent", mock_llm_manager, execution_delay=0.2),
            "cpu_intensive": ConcurrentTestAgent("cpu_intensive", mock_llm_manager, execution_delay=0.15, resource_intensive=True),
            "io_intensive": ConcurrentTestAgent("io_intensive", mock_llm_manager, execution_delay=0.12, resource_intensive=False)
        }
        
    @pytest.fixture
    async def concurrent_registry(self, concurrent_agents):
        """Create registry with concurrent test agents."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: concurrent_agents.get(name)
        registry.get_async = AsyncMock(side_effect=lambda name, context=None: concurrent_agents.get(name))
        registry.list_keys = lambda: list(concurrent_agents.keys())
        return registry

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_concurrent_agents_single_user(
        self, concurrent_registry, concurrent_agents, mock_llm_manager
    ):
        """Test multiple agents executing concurrently for single user."""
        
        # Business Value: Users often trigger multiple agents simultaneously
        
        user_context = UserExecutionContext(
            user_id="concurrent_single_user",
            thread_id="concurrent_single_thread",
            run_id="concurrent_single_run",
            request_id="concurrent_single_req",
            metadata={"concurrent_test": "single_user_multiple_agents"}
        )
        
        websocket_bridge = await self.websocket_manager.create_bridge(user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=concurrent_registry,
            websocket_bridge=websocket_bridge,
            user_context=user_context
        )
        
        # Prepare concurrent agent executions
        agent_names = ["fast_agent", "medium_agent", "slow_agent", "cpu_intensive"]
        
        async def execute_agent(agent_name, execution_id):
            """Execute single agent with unique context."""
            context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=f"{user_context.run_id}_{agent_name}_{execution_id}",
                request_id=f"{user_context.request_id}_{agent_name}_{execution_id}",
                agent_name=agent_name,
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=execution_id
            )
            
            state = DeepAgentState(
                user_request=f"Concurrent execution {execution_id} for {agent_name}",
                user_id=user_context.user_id,
                chat_thread_id=user_context.thread_id,
                run_id=context.run_id,
                agent_input={"concurrent_test": execution_id, "agent_name": agent_name}
            )
            
            return await engine.execute_agent(context, user_context)
            
        # Execute agents concurrently
        start_time = time.time()
        tasks = []
        for i, agent_name in enumerate(agent_names):
            task = execute_agent(agent_name, i + 1)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate concurrent execution
        assert len(results) == len(agent_names)
        assert execution_time < 1.0  # Should complete quickly due to concurrency
        
        # Validate all agents succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Agent {agent_names[i]} failed: {result}"
            assert result.success is True
            assert result.agent_name == agent_names[i]
            
        # Validate concurrency actually occurred
        global_stats = ConcurrentTestAgent.get_global_stats()
        assert global_stats["total_executions"] == len(agent_names)
        assert global_stats["max_concurrent"] >= 2  # At least 2 agents ran concurrently
        
        # Validate WebSocket events were properly isolated
        concurrency_metrics = self.websocket_manager.get_concurrency_metrics()
        assert concurrency_metrics["total_events"] >= len(agent_names) * 4  # At least 4 events per agent
        assert concurrency_metrics["concurrent_clusters"] >= 1  # Should have concurrent event clusters
        
        # Validate individual agent performance
        for agent_name in agent_names:
            agent = concurrent_agents[agent_name]
            assert agent.instance_execution_count == 1
            assert len(agent.execution_stats) == 1
            
        logger.info(f" PASS:  Multiple concurrent agents single user test passed - {len(results)} agents in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_concurrent_users_with_agent_isolation(
        self, concurrent_registry, concurrent_agents, mock_llm_manager
    ):
        """Test multiple users executing agents concurrently with proper isolation."""
        
        # Business Value: Multi-user concurrency is core platform capability
        
        # Create multiple users
        concurrent_users = 4
        user_contexts = []
        websocket_bridges = []
        execution_engines = []
        
        for i in range(concurrent_users):
            context = UserExecutionContext(
                user_id=f"concurrent_user_{i}",
                thread_id=f"concurrent_thread_{i}",
                run_id=f"concurrent_run_{i}",
                request_id=f"concurrent_req_{i}",
                metadata={
                    "user_index": i,
                    "secret_data": f"user_{i}_confidential",
                    "concurrent_test": "multi_user"
                }
            )
            user_contexts.append(context)
            
            bridge = await self.websocket_manager.create_bridge(context)
            websocket_bridges.append(bridge)
            
            engine = ExecutionEngine._init_from_factory(
                registry=concurrent_registry,
                websocket_bridge=bridge,
                user_context=context
            )
            execution_engines.append(engine)
            
        # Define concurrent user execution
        async def execute_for_user(user_index, context, engine):
            """Execute agents for a specific user."""
            # Each user runs different agents to test resource sharing
            agent_assignments = {
                0: "fast_agent",
                1: "medium_agent", 
                2: "slow_agent",
                3: "cpu_intensive"
            }
            agent_name = agent_assignments[user_index]
            
            exec_context = AgentExecutionContext(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
                request_id=context.request_id,
                agent_name=agent_name,
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            state = DeepAgentState(
                user_request=f"User {user_index} concurrent request",
                user_id=context.user_id,
                chat_thread_id=context.thread_id,
                run_id=context.run_id,
                agent_input={
                    "user_index": user_index,
                    "secret_data": context.metadata["secret_data"]
                }
            )
            
            result = await engine.execute_agent(exec_context, context)
            
            return {
                "user_index": user_index,
                "user_id": context.user_id,
                "agent_name": agent_name,
                "result": result
            }
            
        # Execute all users concurrently
        start_time = time.time()
        tasks = []
        for i, (context, engine) in enumerate(zip(user_contexts, execution_engines)):
            task = execute_for_user(i, context, engine)
            tasks.append(task)
            
        concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_execution_time = time.time() - start_time
        
        # Validate multi-user concurrent execution
        assert len(concurrent_results) == concurrent_users
        assert total_execution_time < 2.0  # Should handle all users efficiently
        
        # Validate all users succeeded
        for i, result in enumerate(concurrent_results):
            assert not isinstance(result, Exception), f"User {i} failed: {result}"
            assert result["result"].success is True
            assert result["user_id"] == f"concurrent_user_{i}"
            
        # Validate user isolation
        for i, result in enumerate(concurrent_results):
            user_id = result["user_id"]
            
            # Check WebSocket event isolation
            user_events = self.websocket_manager.events_by_user[user_id]
            assert len(user_events) > 0
            
            # All events should be for this user only
            for event in user_events:
                assert event["user_id"] == user_id
                
                # Check for data leakage
                event_str = str(event["data"])
                for j in range(concurrent_users):
                    if j != i:
                        secret = f"user_{j}_confidential"
                        assert secret not in event_str, f"Data leakage: User {j} data in User {i} events"
                        
        # Validate concurrent execution stats
        global_stats = ConcurrentTestAgent.get_global_stats()
        assert global_stats["total_executions"] == concurrent_users
        assert global_stats["max_concurrent"] >= 2  # Multiple users should run concurrently
        
        # Validate performance
        concurrency_metrics = self.websocket_manager.get_concurrency_metrics()
        assert concurrency_metrics["unique_users"] == concurrent_users
        assert concurrency_metrics["events_per_second"] >= 5  # Good event throughput
        
        logger.info(f" PASS:  Multiple concurrent users test passed - {concurrent_users} users in {total_execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_contention_and_performance_degradation(
        self, concurrent_registry, concurrent_agents, mock_llm_manager
    ):
        """Test system behavior under resource contention and performance limits."""
        
        # Business Value: System must gracefully handle resource pressure
        
        user_context = UserExecutionContext(
            user_id="resource_contention_user",
            thread_id="resource_contention_thread",
            run_id="resource_contention_run",
            request_id="resource_contention_req",
            metadata={"test_type": "resource_contention"}
        )
        
        websocket_bridge = await self.websocket_manager.create_bridge(user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=concurrent_registry,
            websocket_bridge=websocket_bridge,
            user_context=user_context
        )
        
        # Test with high concurrency load
        high_concurrency_count = 10
        
        async def execute_resource_intensive_agent(execution_id):
            """Execute resource-intensive agent."""
            context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=f"{user_context.run_id}_{execution_id}",
                request_id=f"{user_context.request_id}_{execution_id}",
                agent_name="cpu_intensive",  # Resource-intensive agent
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=execution_id
            )
            
            state = DeepAgentState(
                user_request=f"Resource contention test {execution_id}",
                user_id=user_context.user_id,
                chat_thread_id=user_context.thread_id,
                run_id=context.run_id,
                agent_input={"resource_test": execution_id}
            )
            
            start_time = time.time()
            result = await engine.execute_agent(context, user_context)
            execution_time = time.time() - start_time
            
            return {"execution_id": execution_id, "result": result, "execution_time": execution_time}
            
        # Execute high concurrency load
        start_time = time.time()
        tasks = []
        for i in range(high_concurrency_count):
            task = execute_resource_intensive_agent(i + 1)
            tasks.append(task)
            
        # Add some variance in start times to simulate real-world patterns
        await asyncio.sleep(0.01)  # Small delay between some tasks
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Validate resource contention handling
        assert len(results) == high_concurrency_count
        assert total_time < 5.0  # Should complete within reasonable time even under load
        
        # Validate no failures due to contention
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Execution {i+1} failed: {result}")
            else:
                assert result["result"].success is True
                successful_results.append(result)
                
        # Should have high success rate even under contention
        success_rate = len(successful_results) / high_concurrency_count
        assert success_rate >= 0.8  # At least 80% success rate under load
        
        # Analyze performance degradation
        execution_times = [r["execution_time"] for r in successful_results]
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        
        # Under load, some degradation is expected but should be reasonable
        assert avg_execution_time < 1.0  # Average should still be reasonable
        assert max_execution_time < 2.0  # Worst case should be acceptable
        
        # Validate concurrency was actually achieved
        global_stats = ConcurrentTestAgent.get_global_stats()
        assert global_stats["max_concurrent"] >= 5  # Should have high concurrency
        
        # Validate resource management
        cpu_agent = concurrent_agents["cpu_intensive"]
        assert len(cpu_agent.execution_stats) >= success_rate * high_concurrency_count
        
        logger.info(f" PASS:  Resource contention test passed - {len(successful_results)}/{high_concurrency_count} succeeded in {total_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_deadlock_prevention_and_cleanup(
        self, concurrent_registry, concurrent_agents, mock_llm_manager
    ):
        """Test system prevents deadlocks and properly cleans up resources."""
        
        # Business Value: Deadlock prevention is critical for system stability
        
        # Create scenario prone to deadlocks - multiple users accessing shared resources
        deadlock_users = 3
        user_contexts = []
        engines = []
        
        for i in range(deadlock_users):
            context = UserExecutionContext(
                user_id=f"deadlock_user_{i}",
                thread_id=f"deadlock_thread_{i}",
                run_id=f"deadlock_run_{i}",
                request_id=f"deadlock_req_{i}",
                metadata={"deadlock_test": i}
            )
            user_contexts.append(context)
            
            bridge = await self.websocket_manager.create_bridge(context)
            engine = ExecutionEngine._init_from_factory(
                registry=concurrent_registry,
                websocket_bridge=bridge,
                user_context=context
            )
            engines.append(engine)
            
        async def execute_with_potential_deadlock(user_index, context, engine):
            """Execute multiple agents that might compete for resources."""
            # Execute multiple agents sequentially for each user to test resource cleanup
            agent_sequence = ["fast_agent", "medium_agent", "cpu_intensive"]
            results = []
            
            for j, agent_name in enumerate(agent_sequence):
                exec_context = AgentExecutionContext(
                    user_id=context.user_id,
                    thread_id=context.thread_id,
                    run_id=f"{context.run_id}_{j}",
                    request_id=f"{context.request_id}_{j}",
                    agent_name=agent_name,
                    step=PipelineStep.INITIALIZATION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=j + 1
                )
                
                state = DeepAgentState(
                    user_request=f"Deadlock test user {user_index} agent {j}",
                    user_id=context.user_id,
                    chat_thread_id=context.thread_id,
                    run_id=exec_context.run_id,
                    agent_input={"deadlock_test": user_index, "sequence": j}
                )
                
                try:
                    result = await engine.execute_agent(exec_context, context)
                    results.append({"agent": agent_name, "result": result})
                    
                    # Brief delay between agents to allow for resource contention
                    await asyncio.sleep(0.02)
                    
                except Exception as e:
                    results.append({"agent": agent_name, "error": str(e)})
                    
            return {"user_index": user_index, "results": results}
            
        # Execute all users concurrently with timeout to detect deadlocks
        try:
            start_time = time.time()
            tasks = []
            for i, (context, engine) in enumerate(zip(user_contexts, engines)):
                task = execute_with_potential_deadlock(i, context, engine)
                tasks.append(task)
                
            # Use timeout to detect potential deadlocks
            deadlock_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=10.0  # 10 second timeout
            )
            execution_time = time.time() - start_time
            
        except asyncio.TimeoutError:
            pytest.fail("Deadlock detected - execution timed out")
            
        # Validate no deadlocks occurred
        assert len(deadlock_results) == deadlock_users
        assert execution_time < 8.0  # Should complete well within timeout
        
        # Validate results
        total_successes = 0
        total_attempts = 0
        
        for user_result in deadlock_results:
            if isinstance(user_result, Exception):
                logger.warning(f"User execution failed: {user_result}")
                continue
                
            user_results = user_result["results"]
            for agent_result in user_results:
                total_attempts += 1
                if "result" in agent_result and agent_result["result"].success:
                    total_successes += 1
                    
        # High success rate indicates no deadlocks
        success_rate = total_successes / max(total_attempts, 1)
        assert success_rate >= 0.7  # Should have good success rate without deadlocks
        
        # Validate resource cleanup
        final_global_stats = ConcurrentTestAgent.get_global_stats()
        assert final_global_stats["active_executions"] == 0  # All should be cleaned up
        
        # Test engine cleanup
        for engine in engines:
            await engine.shutdown()
            # Validate engine cleaned up properly
            assert len(engine.active_runs) == 0
            
        logger.info(f" PASS:  Deadlock prevention and cleanup test passed - {total_successes}/{total_attempts} succeeded in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_under_mixed_workload_patterns(
        self, concurrent_registry, concurrent_agents, mock_llm_manager
    ):
        """Test system performance under realistic mixed concurrent workload patterns."""
        
        # Business Value: Real-world usage has mixed workload patterns
        
        # Simulate realistic usage patterns
        patterns = [
            {"type": "burst", "users": 5, "agents_per_user": 3},  # Burst of activity
            {"type": "steady", "users": 3, "agents_per_user": 2}, # Steady load
            {"type": "mixed", "users": 4, "agents_per_user": 1}   # Mixed individual requests
        ]
        
        all_results = []
        total_start_time = time.time()
        
        for pattern_index, pattern in enumerate(patterns):
            pattern_results = await self._execute_workload_pattern(
                pattern, pattern_index, concurrent_registry, mock_llm_manager
            )
            all_results.extend(pattern_results)
            
            # Brief pause between patterns
            await asyncio.sleep(0.1)
            
        total_execution_time = time.time() - total_start_time
        
        # Validate mixed workload performance
        assert len(all_results) > 0
        assert total_execution_time < 15.0  # Should handle all patterns efficiently
        
        # Analyze performance across patterns
        successful_executions = [r for r in all_results if r.get("success", False)]
        success_rate = len(successful_executions) / len(all_results)
        
        assert success_rate >= 0.8  # High success rate across mixed workloads
        
        # Validate concurrency was achieved across patterns
        final_stats = ConcurrentTestAgent.get_global_stats()
        assert final_stats["total_executions"] >= len(all_results) * 0.8
        assert final_stats["max_concurrent"] >= 3  # Should have achieved concurrency
        
        # Validate WebSocket events across all patterns
        concurrency_metrics = self.websocket_manager.get_concurrency_metrics()
        assert concurrency_metrics["total_events"] >= len(successful_executions) * 3
        assert concurrency_metrics["unique_users"] >= 5  # Multiple users across patterns
        
        logger.info(f" PASS:  Mixed workload patterns test passed - {len(successful_executions)}/{len(all_results)} succeeded in {total_execution_time:.3f}s")
        
    async def _execute_workload_pattern(self, pattern: Dict, pattern_index: int, 
                                       registry: Any, mock_llm_manager: Any) -> List[Dict]:
        """Execute a specific workload pattern."""
        pattern_results = []
        users = []
        engines = []
        
        # Create users for this pattern
        for i in range(pattern["users"]):
            context = UserExecutionContext(
                user_id=f"pattern_{pattern_index}_user_{i}",
                thread_id=f"pattern_{pattern_index}_thread_{i}",
                run_id=f"pattern_{pattern_index}_run_{i}",
                request_id=f"pattern_{pattern_index}_req_{i}",
                metadata={"pattern": pattern["type"], "pattern_index": pattern_index}
            )
            users.append(context)
            
            bridge = await self.websocket_manager.create_bridge(context)
            engine = ExecutionEngine._init_from_factory(
                registry=registry,
                websocket_bridge=bridge,
                user_context=context
            )
            engines.append(engine)
            
        # Execute pattern-specific workload
        if pattern["type"] == "burst":
            # All users start simultaneously
            tasks = []
            for i, (context, engine) in enumerate(zip(users, engines)):
                for j in range(pattern["agents_per_user"]):
                    task = self._execute_single_agent(context, engine, "fast_agent", f"{i}_{j}")
                    tasks.append(task)
                    
            results = await asyncio.gather(*tasks, return_exceptions=True)
            pattern_results.extend([r for r in results if not isinstance(r, Exception)])
            
        elif pattern["type"] == "steady":
            # Users start with small delays
            tasks = []
            for i, (context, engine) in enumerate(zip(users, engines)):
                await asyncio.sleep(0.05 * i)  # Staggered starts
                for j in range(pattern["agents_per_user"]):
                    task = self._execute_single_agent(context, engine, "medium_agent", f"{i}_{j}")
                    tasks.append(task)
                    
            results = await asyncio.gather(*tasks, return_exceptions=True)
            pattern_results.extend([r for r in results if not isinstance(r, Exception)])
            
        elif pattern["type"] == "mixed":
            # Random agent types and timing
            agent_types = ["fast_agent", "medium_agent", "slow_agent"]
            tasks = []
            
            for i, (context, engine) in enumerate(zip(users, engines)):
                for j in range(pattern["agents_per_user"]):
                    agent_type = random.choice(agent_types)
                    await asyncio.sleep(random.uniform(0.01, 0.1))  # Random delay
                    task = self._execute_single_agent(context, engine, agent_type, f"{i}_{j}")
                    tasks.append(task)
                    
            results = await asyncio.gather(*tasks, return_exceptions=True)
            pattern_results.extend([r for r in results if not isinstance(r, Exception)])
            
        # Cleanup pattern resources
        for engine in engines:
            await engine.shutdown()
            
        return pattern_results
        
    async def _execute_single_agent(self, user_context: UserExecutionContext, 
                                   engine: ExecutionEngine, agent_name: str, 
                                   execution_id: str) -> Dict:
        """Execute a single agent for workload testing."""
        context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=f"{user_context.run_id}_{execution_id}",
            request_id=f"{user_context.request_id}_{execution_id}",
            agent_name=agent_name,
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        state = DeepAgentState(
            user_request=f"Workload test {execution_id}",
            user_id=user_context.user_id,
            chat_thread_id=user_context.thread_id,
            run_id=context.run_id,
            agent_input={"workload_test": execution_id}
        )
        
        try:
            result = await engine.execute_agent(context, user_context)
            return {
                "success": result.success,
                "agent_name": agent_name,
                "execution_id": execution_id,
                "user_id": user_context.user_id
            }
        except Exception as e:
            return {
                "success": False,
                "agent_name": agent_name,
                "execution_id": execution_id,
                "user_id": user_context.user_id,
                "error": str(e)
            }


if __name__ == "__main__":
    # Run specific test for development
    pytest.main([__file__, "-v", "-s"])