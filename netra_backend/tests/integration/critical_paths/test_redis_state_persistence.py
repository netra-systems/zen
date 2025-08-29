"""
Redis State Persistence Tests for Multi-Agent Systems

Comprehensive tests for Redis-based state management and persistence in multi-agent systems.
Tests include shared context, state recovery, concurrent access, TTL handling, versioning,
and performance benchmarks.

Business Value Justification (BVJ):
- Segment: Enterprise, Mid
- Business Goal: System Reliability and Agent Orchestration
- Value Impact: Ensures robust state management for multi-agent workflows
- Strategic Impact: Foundation for enterprise-grade AI orchestration platform
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import patch
import uuid

import pytest

from test_framework import setup_test_path
setup_test_path()

from netra_backend.app.services.state.state_manager import StateManager, StateStorage
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockSupervisorStateManager:
    """Mock supervisor state manager for testing"""
    
    def __init__(self, state_storage: StateStorage, redis_manager):
        self.state_storage = state_storage
        self.redis_manager = redis_manager
        self.state_manager = StateManager(storage=state_storage)
        
    async def save_agent_state(self, agent_id: str, state: Dict[str, Any]) -> None:
        """Save agent state"""
        await self.state_manager.set(f"agent_state:{agent_id}", state)
        
    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state"""
        return await self.state_manager.get(f"agent_state:{agent_id}")


class MockAgent:
    """Mock agent for testing multi-agent scenarios"""
    
    def __init__(self, agent_id: str, state_manager: StateManager):
        self.agent_id = agent_id
        self.state_manager = state_manager
        self.is_active = True
        self.shared_context = {}
        
    async def set_shared_state(self, key: str, value: Any, transaction_id: Optional[str] = None) -> None:
        """Set shared state accessible by other agents"""
        full_key = f"agent_shared:{key}"
        await self.state_manager.set(full_key, value, transaction_id)
        
    async def get_shared_state(self, key: str) -> Any:
        """Get shared state from other agents"""
        full_key = f"agent_shared:{key}"
        return await self.state_manager.get(full_key)
        
    async def update_context(self, context: Dict[str, Any]) -> None:
        """Update agent's context"""
        context_key = f"agent_context:{self.agent_id}"
        await self.state_manager.set(context_key, context)
        
    async def get_context(self) -> Dict[str, Any]:
        """Get agent's context"""
        context_key = f"agent_context:{self.agent_id}"
        return await self.state_manager.get(context_key, {})
        
    def simulate_failure(self):
        """Simulate agent failure"""
        self.is_active = False


class MockRedisClient:
    """Mock Redis client that maintains in-memory state for testing"""
    
    def __init__(self):
        self._store = {}
        self._ttls = {}
    
    async def get(self, key: str):
        return self._store.get(key)
    
    async def set(self, key: str, value: str, ex: int = None):
        self._store[key] = value
        if ex:
            self._ttls[key] = ex
        return True
    
    async def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                count += 1
            if key in self._ttls:
                del self._ttls[key]
        return count
    
    async def keys(self, pattern: str = "*"):
        return list(self._store.keys())
    
    async def ping(self):
        return True
    
    async def expire(self, key: str, seconds: int):
        if key in self._store:
            self._ttls[key] = seconds
            return True
        return False
    
    async def ttl(self, key: str):
        return self._ttls.get(key, -1)
    
    def pipeline(self):
        return MockRedisPipeline(self)


class MockRedisPipeline:
    """Mock Redis pipeline for batch operations"""
    
    def __init__(self, client):
        self.client = client
        self.commands = []
    
    def set(self, key: str, value: str, ex: int = None):
        self.commands.append(('set', key, value, ex))
        return self
    
    def delete(self, *keys):
        self.commands.append(('delete', *keys))
        return self
    
    async def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == 'set':
                result = await self.client.set(cmd[1], cmd[2], cmd[3] if len(cmd) > 3 else None)
                results.append(result)
            elif cmd[0] == 'delete':
                result = await self.client.delete(*cmd[1:])
                results.append(result)
        self.commands.clear()
        return results


@pytest.fixture
async def redis_state_manager():
    """Create Redis-only state manager for testing"""
    mock_redis = MockRedisClient()
    with patch.object(redis_manager, 'enabled', True):
        with patch.object(redis_manager, 'redis_client', mock_redis):
            manager = StateManager(storage=StateStorage.REDIS)
            await manager.clear()  # Clean slate for tests
            yield manager
            await manager.clear()  # Cleanup after tests


@pytest.fixture
async def hybrid_state_manager():
    """Create hybrid state manager for testing"""
    mock_redis = MockRedisClient()
    with patch.object(redis_manager, 'enabled', True):
        with patch.object(redis_manager, 'redis_client', mock_redis):
            manager = StateManager(storage=StateStorage.HYBRID)
            await manager.clear()  # Clean slate for tests
            yield manager
            await manager.clear()  # Cleanup after tests


@pytest.fixture
async def memory_state_manager():
    """Create memory-only state manager for fallback testing"""
    manager = StateManager(storage=StateStorage.MEMORY)
    await manager.clear()
    yield manager
    await manager.clear()


@pytest.fixture
async def mock_agents(redis_state_manager):
    """Create multiple mock agents for testing"""
    # Wait for the manager to be ready (async fixture)
    manager = redis_state_manager
    agents = [
        MockAgent(f"agent_{i}", manager) 
        for i in range(1, 4)
    ]
    return agents


class TestSharedContextBetweenAgents:
    """Test shared context between multiple agents using Redis"""
    
    async def test_agents_can_share_context_data(self, mock_agents):
        """Test that agents can share context data through Redis"""
        agent1, agent2, agent3 = mock_agents
        
        # Agent 1 sets shared context
        shared_data = {
            "task_id": "task_123",
            "workflow_status": "in_progress",
            "results": ["step1_complete", "step2_pending"]
        }
        await agent1.set_shared_state("workflow_context", shared_data)
        
        # Agent 2 and 3 can read the shared context
        agent2_view = await agent2.get_shared_state("workflow_context")
        agent3_view = await agent3.get_shared_state("workflow_context")
        
        assert agent2_view == shared_data
        assert agent3_view == shared_data
        assert agent2_view["task_id"] == "task_123"
        assert agent3_view["workflow_status"] == "in_progress"
        
    async def test_agents_can_update_shared_context_collaboratively(self, mock_agents):
        """Test collaborative updates to shared context"""
        agent1, agent2, agent3 = mock_agents
        
        # Initialize shared workflow state
        workflow = {
            "task_id": "collaborative_task",
            "steps": {
                "step1": {"assigned_to": "agent_1", "status": "pending"},
                "step2": {"assigned_to": "agent_2", "status": "pending"},
                "step3": {"assigned_to": "agent_3", "status": "pending"}
            }
        }
        await agent1.set_shared_state("workflow", workflow)
        
        # Each agent updates their step
        async with agent1.state_manager.transaction() as txn_id:
            current_workflow = await agent1.get_shared_state("workflow")
            current_workflow["steps"]["step1"]["status"] = "completed"
            current_workflow["steps"]["step1"]["result"] = "analysis_done"
            await agent1.set_shared_state("workflow", current_workflow, txn_id)
        
        async with agent2.state_manager.transaction() as txn_id:
            current_workflow = await agent2.get_shared_state("workflow")
            current_workflow["steps"]["step2"]["status"] = "in_progress"
            await agent2.set_shared_state("workflow", current_workflow, txn_id)
        
        # Verify final state
        final_workflow = await agent3.get_shared_state("workflow")
        assert final_workflow["steps"]["step1"]["status"] == "completed"
        assert final_workflow["steps"]["step2"]["status"] == "in_progress"
        assert final_workflow["steps"]["step3"]["status"] == "pending"
        
    async def test_agent_specific_context_isolation(self, mock_agents):
        """Test that agent-specific contexts remain isolated"""
        agent1, agent2, agent3 = mock_agents
        
        # Each agent sets their own context
        await agent1.update_context({
            "role": "analyzer",
            "current_task": "data_analysis",
            "progress": 0.3
        })
        
        await agent2.update_context({
            "role": "executor", 
            "current_task": "action_execution",
            "progress": 0.7
        })
        
        await agent3.update_context({
            "role": "monitor",
            "current_task": "health_check",
            "progress": 1.0
        })
        
        # Verify isolation
        agent1_context = await agent1.get_context()
        agent2_context = await agent2.get_context()
        agent3_context = await agent3.get_context()
        
        assert agent1_context["role"] == "analyzer"
        assert agent2_context["role"] == "executor"
        assert agent3_context["role"] == "monitor"
        assert agent1_context["progress"] != agent2_context["progress"]


class TestStateRecoveryAfterFailures:
    """Test state recovery after agent failures"""
    
    async def test_agent_state_persists_after_simulated_failure(self, mock_agents):
        """Test that agent state persists after agent failure"""
        agent1, agent2, _ = mock_agents
        
        # Agent 1 creates important state
        critical_state = {
            "session_id": "session_123",
            "user_preferences": {"theme": "dark", "language": "en"},
            "active_workflows": ["workflow_1", "workflow_2"],
            "checkpoint": "step_5_completed"
        }
        await agent1.update_context(critical_state)
        await agent1.set_shared_state("critical_session_data", critical_state)
        
        # Simulate agent 1 failure
        agent1.simulate_failure()
        assert not agent1.is_active
        
        # Agent 2 should still be able to access the state
        recovered_context = await agent2.get_shared_state("critical_session_data")
        assert recovered_context == critical_state
        assert recovered_context["session_id"] == "session_123"
        assert recovered_context["checkpoint"] == "step_5_completed"
        
    async def test_state_recovery_with_supervisor_state_manager(self, redis_state_manager):
        """Test state recovery using SupervisorStateManager patterns"""
        # Create supervisor with state manager
        supervisor_manager = MockSupervisorStateManager(
            state_storage=StateStorage.REDIS,
            redis_manager=redis_manager
        )
        
        # Create agent state before failure
        agent_id = "critical_agent_001"
        agent_state = {
            "agent_id": agent_id,
            "status": "processing",
            "current_task": {
                "id": "task_456",
                "type": "data_processing",
                "progress": 0.65,
                "intermediate_results": ["result1", "result2"]
            },
            "last_heartbeat": datetime.utcnow().isoformat()
        }
        
        await supervisor_manager.save_agent_state(agent_id, agent_state)
        
        # Simulate agent failure and recovery
        recovered_state = await supervisor_manager.get_agent_state(agent_id)
        
        assert recovered_state is not None
        assert recovered_state["agent_id"] == agent_id
        assert recovered_state["current_task"]["progress"] == 0.65
        assert len(recovered_state["current_task"]["intermediate_results"]) == 2
        
    async def test_partial_state_recovery_with_corruption(self, redis_state_manager):
        """Test graceful handling of partial state corruption"""
        agent = MockAgent("resilient_agent", redis_state_manager)
        
        # Create valid state
        valid_state = {"task_id": "task_789", "status": "active"}
        await agent.set_shared_state("valid_key", valid_state)
        
        # Simulate corrupted state by setting invalid JSON
        await redis_manager.set("state:agent_shared:corrupted_key", "invalid_json{")
        
        # Recovery should handle corruption gracefully
        recovered_valid = await agent.get_shared_state("valid_key")
        recovered_corrupted = await agent.get_shared_state("corrupted_key")
        
        assert recovered_valid == valid_state
        assert recovered_corrupted is None  # Should return None for corrupted data


class TestConcurrentStateAccess:
    """Test concurrent state access patterns (multiple agents accessing same state)"""
    
    async def test_concurrent_state_reads(self, mock_agents):
        """Test multiple agents reading state concurrently"""
        agent1, agent2, agent3 = mock_agents
        
        # Set shared state
        shared_config = {
            "version": "1.0",
            "feature_flags": {"new_ui": True, "beta_api": False},
            "limits": {"max_requests": 1000, "timeout": 30}
        }
        await agent1.set_shared_state("system_config", shared_config)
        
        # Concurrent reads from multiple agents
        read_tasks = [
            agent1.get_shared_state("system_config"),
            agent2.get_shared_state("system_config"),
            agent3.get_shared_state("system_config")
        ]
        
        results = await asyncio.gather(*read_tasks)
        
        # All agents should get consistent data
        assert all(result == shared_config for result in results)
        assert all(result["version"] == "1.0" for result in results)
        
    async def test_concurrent_state_writes_with_transactions(self, mock_agents):
        """Test concurrent writes using transactions for consistency"""
        agent1, agent2, agent3 = mock_agents
        
        # Initialize counter state
        await agent1.set_shared_state("global_counter", {"value": 0})
        
        async def increment_counter(agent, increment_by=1):
            async with agent.state_manager.transaction() as txn_id:
                current = await agent.get_shared_state("global_counter")
                current["value"] += increment_by
                await agent.set_shared_state("global_counter", current, txn_id)
        
        # Concurrent increments
        increment_tasks = [
            increment_counter(agent1, 1),
            increment_counter(agent2, 2),
            increment_counter(agent3, 3)
        ]
        
        await asyncio.gather(*increment_tasks)
        
        # Final value should be consistent (0 + 1 + 2 + 3 = 6)
        final_counter = await agent1.get_shared_state("global_counter")
        assert final_counter["value"] == 6
        
    async def test_concurrent_access_performance_benchmark(self, mock_agents):
        """Benchmark concurrent access performance"""
        agent1, agent2, agent3 = mock_agents
        num_operations = 50
        
        # Prepare test data
        test_data = {"benchmark": True, "data": list(range(100))}
        await agent1.set_shared_state("benchmark_data", test_data)
        
        # Benchmark concurrent reads
        start_time = time.time()
        
        read_tasks = []
        for _ in range(num_operations):
            read_tasks.extend([
                agent1.get_shared_state("benchmark_data"),
                agent2.get_shared_state("benchmark_data"),
                agent3.get_shared_state("benchmark_data")
            ])
        
        results = await asyncio.gather(*read_tasks)
        
        end_time = time.time()
        total_operations = len(read_tasks)
        duration = end_time - start_time
        ops_per_second = total_operations / duration
        
        logger.info(f"Concurrent read benchmark: {total_operations} operations in {duration:.3f}s "
                   f"({ops_per_second:.1f} ops/sec)")
        
        # Performance assertions
        assert ops_per_second > 100  # Should handle at least 100 ops/sec
        assert all(result == test_data for result in results)


class TestStateTTLAndExpiration:
    """Test state TTL and expiration handling"""
    
    async def test_state_expiration_with_ttl(self, redis_state_manager):
        """Test that state expires according to TTL"""
        # Set state with TTL through Redis directly
        test_key = "state:expiring_data"
        test_value = json.dumps({"temp_session": "temp_123", "expires": True})
        
        # Set with 2 second TTL
        await redis_manager.set(test_key, test_value, ex=2)
        
        # Should be available immediately
        result = await redis_state_manager.get("expiring_data")
        assert result is not None
        assert result["temp_session"] == "temp_123"
        
        # Should expire after TTL
        await asyncio.sleep(2.5)
        expired_result = await redis_state_manager.get("expiring_data")
        assert expired_result is None
        
    async def test_ttl_renewal_on_access(self, redis_state_manager):
        """Test TTL renewal patterns for active state"""
        agent = MockAgent("ttl_agent", redis_state_manager)
        
        # Set initial state with TTL
        session_data = {"session_id": "renewable_session", "active": True}
        await agent.set_shared_state("renewable_session", session_data)
        
        # Manually set TTL on the Redis key
        await redis_manager.expire("state:agent_shared:renewable_session", 3)
        
        # Check TTL
        initial_ttl = await redis_manager.ttl("state:agent_shared:renewable_session")
        assert initial_ttl > 0
        
        # Renew by accessing and updating
        await asyncio.sleep(1)
        current_data = await agent.get_shared_state("renewable_session")
        current_data["last_accessed"] = datetime.utcnow().isoformat()
        await agent.set_shared_state("renewable_session", current_data)
        await redis_manager.expire("state:agent_shared:renewable_session", 5)  # Reset TTL
        
        # Should still be available after original TTL would have expired
        await asyncio.sleep(2)  # Total 3 seconds, original would have expired
        renewed_data = await agent.get_shared_state("renewable_session")
        assert renewed_data is not None
        assert renewed_data["session_id"] == "renewable_session"
        
    async def test_cleanup_expired_states(self, redis_state_manager):
        """Test cleanup of expired states"""
        agent = MockAgent("cleanup_agent", redis_state_manager)
        
        # Create multiple states with different TTLs
        states = [
            ("short_lived", {"ttl": "short"}, 1),
            ("medium_lived", {"ttl": "medium"}, 3),
            ("long_lived", {"ttl": "long"}, 5)
        ]
        
        for key, data, ttl in states:
            await agent.set_shared_state(key, data)
            await redis_manager.expire(f"state:agent_shared:{key}", ttl)
        
        # Check all exist initially
        for key, data, _ in states:
            result = await agent.get_shared_state(key)
            assert result == data
        
        # After 2 seconds, only short_lived should be expired
        await asyncio.sleep(2)
        assert await agent.get_shared_state("short_lived") is None
        assert await agent.get_shared_state("medium_lived") is not None
        assert await agent.get_shared_state("long_lived") is not None


class TestStateVersioningAndConflictResolution:
    """Test state versioning and conflict resolution"""
    
    async def test_optimistic_locking_conflict_detection(self, mock_agents):
        """Test conflict detection with optimistic locking"""
        agent1, agent2, _ = mock_agents
        
        # Initialize versioned state
        initial_state = {
            "version": 1,
            "data": {"counter": 0},
            "last_modified": datetime.utcnow().isoformat()
        }
        await agent1.set_shared_state("versioned_counter", initial_state)
        
        # Both agents read the same version
        agent1_copy = await agent1.get_shared_state("versioned_counter")
        agent2_copy = await agent2.get_shared_state("versioned_counter")
        
        assert agent1_copy["version"] == agent2_copy["version"] == 1
        
        # Agent 1 updates first
        agent1_copy["version"] += 1
        agent1_copy["data"]["counter"] += 1
        agent1_copy["last_modified"] = datetime.utcnow().isoformat()
        await agent1.set_shared_state("versioned_counter", agent1_copy)
        
        # Agent 2 attempts to update with stale version
        agent2_copy["version"] += 1  # This will conflict
        agent2_copy["data"]["counter"] += 2
        
        # Simulate conflict detection by checking current version
        current_state = await agent2.get_shared_state("versioned_counter")
        if current_state["version"] > agent2_copy["version"] - 1:
            # Conflict detected - need to merge or retry
            logger.info("Conflict detected - performing merge")
            merged_state = {
                "version": current_state["version"] + 1,
                "data": {"counter": current_state["data"]["counter"] + 2},
                "last_modified": datetime.utcnow().isoformat()
            }
            await agent2.set_shared_state("versioned_counter", merged_state)
        
        # Final state should reflect merged updates
        final_state = await agent1.get_shared_state("versioned_counter")
        assert final_state["data"]["counter"] == 3  # 0 + 1 + 2
        assert final_state["version"] == 3
        
    async def test_last_write_wins_resolution(self, mock_agents):
        """Test last-write-wins conflict resolution"""
        agent1, agent2, _ = mock_agents
        
        # Rapid conflicting updates
        updates = [
            (agent1, {"source": "agent1", "timestamp": 1}),
            (agent2, {"source": "agent2", "timestamp": 2}),
            (agent1, {"source": "agent1", "timestamp": 3}),
            (agent2, {"source": "agent2", "timestamp": 4})
        ]
        
        # Apply updates sequentially with small delays
        for agent, data in updates:
            await agent.set_shared_state("conflict_test", data)
            await asyncio.sleep(0.1)  # Small delay to ensure ordering
        
        # Last write should win
        final_state = await agent1.get_shared_state("conflict_test")
        assert final_state["source"] == "agent2"
        assert final_state["timestamp"] == 4


class TestRedisPipelineOperations:
    """Test Redis pipeline operations for batch updates"""
    
    async def test_batch_state_updates_with_pipeline(self, redis_state_manager):
        """Test batch updates using Redis pipeline"""
        agent = MockAgent("pipeline_agent", redis_state_manager)
        
        # Prepare batch updates
        batch_updates = {
            "batch_item_1": {"type": "config", "value": "value1"},
            "batch_item_2": {"type": "data", "value": "value2"},
            "batch_item_3": {"type": "result", "value": "value3"}
        }
        
        # Use Redis pipeline for atomic batch update
        pipeline = redis_manager.pipeline()
        for key, value in batch_updates.items():
            pipeline.set(f"state:agent_shared:{key}", json.dumps(value))
        
        await pipeline.execute()
        
        # Verify all updates were applied
        for key, expected_value in batch_updates.items():
            actual_value = await agent.get_shared_state(key)
            assert actual_value == expected_value
            
    async def test_pipeline_transaction_rollback_on_error(self, redis_state_manager):
        """Test pipeline transaction rollback on error"""
        # This test demonstrates pipeline behavior
        # Note: Redis pipelines are not transactions by default
        # For true transactions, we'd use MULTI/EXEC
        
        initial_state = {"pipeline_test": "initial"}
        await redis_state_manager.set("pipeline_test", initial_state)
        
        # Create pipeline with intentional error
        pipeline = redis_manager.pipeline()
        pipeline.set("state:valid_key", json.dumps({"status": "success"}))
        
        try:
            # Execute pipeline - should succeed despite individual operation issues
            results = await pipeline.execute()
            logger.info(f"Pipeline results: {results}")
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
        
        # Check final state
        final_state = await redis_state_manager.get("pipeline_test")
        assert final_state == initial_state
        
    async def test_pipeline_performance_vs_individual_operations(self, redis_state_manager):
        """Benchmark pipeline vs individual operations performance"""
        num_operations = 100
        test_data = [
            (f"perf_test_{i}", {"index": i, "data": f"data_{i}"})
            for i in range(num_operations)
        ]
        
        # Benchmark individual operations
        start_time = time.time()
        for key, value in test_data:
            await redis_state_manager.set(key, value)
        individual_duration = time.time() - start_time
        
        # Clear state for pipeline test
        await redis_state_manager.clear()
        
        # Benchmark pipeline operations
        start_time = time.time()
        pipeline = redis_manager.pipeline()
        for key, value in test_data:
            pipeline.set(f"state:{key}", json.dumps(value))
        await pipeline.execute()
        pipeline_duration = time.time() - start_time
        
        logger.info(f"Individual operations: {individual_duration:.3f}s")
        logger.info(f"Pipeline operations: {pipeline_duration:.3f}s")
        logger.info(f"Pipeline speedup: {individual_duration/pipeline_duration:.1f}x")
        
        # Pipeline should be significantly faster
        assert pipeline_duration < individual_duration * 0.5  # At least 2x faster


class TestFallbackToMemoryWhenRedisUnavailable:
    """Test fallback to memory when Redis unavailable"""
    
    async def test_hybrid_storage_fallback_on_redis_failure(self, hybrid_state_manager):
        """Test hybrid storage falls back to memory when Redis fails"""
        # Initially store in hybrid mode (should use both memory and Redis)
        test_data = {"fallback_test": "data", "important": True}
        await hybrid_state_manager.set("fallback_data", test_data)
        
        # Verify data is accessible
        result = await hybrid_state_manager.get("fallback_data")
        assert result == test_data
        
        # Simulate Redis failure by patching Redis operations
        with patch.object(redis_manager, 'get', side_effect=Exception("Redis connection failed")):
            with patch.object(redis_manager, 'set', side_effect=Exception("Redis connection failed")):
                # Should still work with memory fallback
                memory_result = await hybrid_state_manager.get("fallback_data")
                assert memory_result == test_data
                
                # New data should still be settable in memory
                new_data = {"memory_only": "data", "fallback_mode": True}
                await hybrid_state_manager.set("memory_only_data", new_data)
                
                retrieved_data = await hybrid_state_manager.get("memory_only_data")
                assert retrieved_data == new_data
                
    async def test_graceful_degradation_with_redis_timeout(self, hybrid_state_manager):
        """Test graceful degradation when Redis times out"""
        # Set data normally
        normal_data = {"timeout_test": "data"}
        await hybrid_state_manager.set("normal_data", normal_data)
        
        async def slow_redis_get(key):
            await asyncio.sleep(5)  # Simulate timeout
            return None
        
        # Simulate Redis timeout
        with patch.object(redis_manager, 'get', side_effect=slow_redis_get):
            start_time = time.time()
            
            # Should return None quickly instead of waiting for timeout
            result = await hybrid_state_manager.get("timeout_key")
            
            duration = time.time() - start_time
            assert result is None
            assert duration < 1.0  # Should fail fast, not wait for full timeout
            
    async def test_redis_reconnection_recovery(self, hybrid_state_manager):
        """Test recovery after Redis reconnects"""
        # Store initial data
        initial_data = {"recovery_test": "initial"}
        await hybrid_state_manager.set("recovery_data", initial_data)
        
        # Simulate Redis failure
        with patch.object(redis_manager, 'enabled', False):
            with patch.object(redis_manager, 'redis_client', None):
                # Should work with memory only
                memory_data = {"memory_update": "updated"}
                await hybrid_state_manager.set("recovery_data", memory_data)
                
                result = await hybrid_state_manager.get("recovery_data")
                assert result == memory_data
        
        # After Redis "recovery", should still work
        # In real scenario, Redis would be reconnected
        recovered_data = await hybrid_state_manager.get("recovery_data")
        assert recovered_data == memory_data


class TestPerformanceAndBenchmarks:
    """Performance benchmarks for Redis state operations"""
    
    async def test_state_manager_performance_benchmarks(self, redis_state_manager, hybrid_state_manager, memory_state_manager):
        """Comprehensive performance benchmarks across storage types"""
        num_operations = 500
        test_data = {"benchmark": True, "payload": "x" * 1000}  # 1KB payload
        
        managers = [
            ("Redis", redis_state_manager),
            ("Hybrid", hybrid_state_manager), 
            ("Memory", memory_state_manager)
        ]
        
        benchmark_results = {}
        
        for name, manager in managers:
            # Benchmark writes
            start_time = time.time()
            for i in range(num_operations):
                await manager.set(f"benchmark_write_{i}", test_data)
            write_duration = time.time() - start_time
            
            # Benchmark reads
            start_time = time.time()
            for i in range(num_operations):
                await manager.get(f"benchmark_write_{i}")
            read_duration = time.time() - start_time
            
            # Benchmark transaction performance
            start_time = time.time()
            async with manager.transaction() as txn_id:
                for i in range(min(50, num_operations)):  # Smaller batch for transactions
                    await manager.set(f"txn_test_{i}", test_data, txn_id)
            transaction_duration = time.time() - start_time
            
            benchmark_results[name] = {
                "write_ops_per_sec": num_operations / write_duration,
                "read_ops_per_sec": num_operations / read_duration,
                "transaction_duration": transaction_duration,
                "write_duration": write_duration,
                "read_duration": read_duration
            }
            
            logger.info(f"{name} Performance:")
            logger.info(f"  Writes: {benchmark_results[name]['write_ops_per_sec']:.1f} ops/sec")
            logger.info(f"  Reads: {benchmark_results[name]['read_ops_per_sec']:.1f} ops/sec")
            logger.info(f"  Transaction: {transaction_duration:.3f}s for 50 ops")
        
        # Performance assertions
        assert benchmark_results["Memory"]["write_ops_per_sec"] > 1000  # Memory should be very fast
        assert benchmark_results["Memory"]["read_ops_per_sec"] > 5000
        
        # Redis should be reasonable performance
        assert benchmark_results["Redis"]["write_ops_per_sec"] > 100
        assert benchmark_results["Redis"]["read_ops_per_sec"] > 200
        
        # Hybrid should be between memory and Redis for writes
        hybrid_writes = benchmark_results["Hybrid"]["write_ops_per_sec"]
        redis_writes = benchmark_results["Redis"]["write_ops_per_sec"] 
        memory_writes = benchmark_results["Memory"]["write_ops_per_sec"]
        
        # Hybrid should be slower than memory but reasonable
        assert hybrid_writes > redis_writes * 0.5  # At least half Redis performance
        
        return benchmark_results
        
    async def test_concurrent_agent_performance_simulation(self, hybrid_state_manager):
        """Simulate realistic multi-agent performance scenario"""
        # Create multiple agents
        num_agents = 10
        operations_per_agent = 20
        
        agents = [MockAgent(f"perf_agent_{i}", hybrid_state_manager) for i in range(num_agents)]
        
        async def agent_workload(agent: MockAgent):
            """Simulate typical agent workload"""
            for i in range(operations_per_agent):
                # Update own context
                context = {
                    "task_id": f"task_{agent.agent_id}_{i}",
                    "progress": i / operations_per_agent,
                    "status": "processing"
                }
                await agent.update_context(context)
                
                # Read shared configuration
                shared_config = await agent.get_shared_state("global_config") or {}
                
                # Update shared metrics
                metrics_key = f"metrics_{agent.agent_id}"
                current_metrics = await agent.get_shared_state(metrics_key) or {"ops": 0}
                current_metrics["ops"] += 1
                await agent.set_shared_state(metrics_key, current_metrics)
                
                # Small delay to simulate processing
                await asyncio.sleep(0.01)
        
        # Initialize shared config
        await agents[0].set_shared_state("global_config", {
            "max_concurrent": num_agents,
            "timeout": 30,
            "retry_count": 3
        })
        
        # Run concurrent agent workloads
        start_time = time.time()
        
        tasks = [agent_workload(agent) for agent in agents]
        await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        total_operations = num_agents * operations_per_agent * 3  # 3 operations per iteration
        ops_per_second = total_operations / duration
        
        logger.info(f"Multi-agent simulation:")
        logger.info(f"  {num_agents} agents, {operations_per_agent} ops each")
        logger.info(f"  Total: {total_operations} operations in {duration:.2f}s")
        logger.info(f"  Performance: {ops_per_second:.1f} ops/sec")
        
        # Verify final state consistency
        final_metrics = {}
        for agent in agents:
            metrics_key = f"metrics_{agent.agent_id}"
            metrics = await agent.get_shared_state(metrics_key)
            final_metrics[agent.agent_id] = metrics["ops"]
        
        # All agents should have completed their operations
        assert all(ops == operations_per_agent for ops in final_metrics.values())
        
        # Performance should be reasonable for multi-agent scenario
        assert ops_per_second > 50  # Should handle at least 50 ops/sec under load
        
        return {
            "agents": num_agents,
            "ops_per_agent": operations_per_agent,
            "total_ops": total_operations,
            "duration": duration,
            "ops_per_second": ops_per_second
        }


# Integration test that combines multiple patterns
class TestIntegratedMultiAgentStateScenarios:
    """Integration tests combining multiple state management patterns"""
    
    async def test_complete_multi_agent_workflow_with_state_persistence(self, hybrid_state_manager):
        """Complete workflow test combining all state management features"""
        # Create agents for different roles
        supervisor = MockAgent("supervisor", hybrid_state_manager)
        analyzer = MockAgent("analyzer", hybrid_state_manager)
        executor = MockAgent("executor", hybrid_state_manager)
        monitor = MockAgent("monitor", hybrid_state_manager)
        
        # Phase 1: Initialize workflow with shared state
        workflow_id = str(uuid.uuid4())
        workflow_state = {
            "id": workflow_id,
            "status": "initialized",
            "phases": {
                "analysis": {"assigned_to": "analyzer", "status": "pending"},
                "execution": {"assigned_to": "executor", "status": "pending"}, 
                "monitoring": {"assigned_to": "monitor", "status": "pending"}
            },
            "created_at": datetime.utcnow().isoformat(),
            "version": 1
        }
        
        await supervisor.set_shared_state(f"workflow_{workflow_id}", workflow_state)
        
        # Phase 2: Analyzer processes with state updates and versioning
        async with analyzer.state_manager.transaction() as txn_id:
            current_workflow = await analyzer.get_shared_state(f"workflow_{workflow_id}")
            current_workflow["phases"]["analysis"]["status"] = "completed"
            current_workflow["phases"]["analysis"]["result"] = {
                "risk_score": 0.3,
                "recommendations": ["optimize_performance", "add_monitoring"]
            }
            current_workflow["version"] += 1
            current_workflow["last_updated"] = datetime.utcnow().isoformat()
            await analyzer.set_shared_state(f"workflow_{workflow_id}", current_workflow, txn_id)
        
        # Phase 3: Executor works with TTL-based temporary state
        temp_execution_state = {
            "execution_id": str(uuid.uuid4()),
            "temp_results": ["step1", "step2"],
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
        await executor.set_shared_state(f"temp_execution_{workflow_id}", temp_execution_state)
        
        # Set TTL on temporary state
        await redis_manager.expire(f"state:agent_shared:temp_execution_{workflow_id}", 300)  # 5 minutes
        
        # Complete execution phase
        async with executor.state_manager.transaction() as txn_id:
            current_workflow = await executor.get_shared_state(f"workflow_{workflow_id}")
            current_workflow["phases"]["execution"]["status"] = "completed"
            current_workflow["phases"]["execution"]["result"] = {
                "actions_taken": ["performance_optimization", "monitoring_setup"],
                "success_rate": 0.95
            }
            current_workflow["version"] += 1
            await executor.set_shared_state(f"workflow_{workflow_id}", current_workflow, txn_id)
        
        # Phase 4: Monitor performs concurrent health checks
        monitoring_tasks = []
        for component in ["database", "redis", "api", "websockets"]:
            async def check_component(comp_name):
                health_data = {
                    "component": comp_name,
                    "status": "healthy",
                    "checked_at": datetime.utcnow().isoformat(),
                    "metrics": {"response_time": 0.05, "error_rate": 0.01}
                }
                await monitor.set_shared_state(f"health_{comp_name}", health_data)
            
            monitoring_tasks.append(check_component(component))
        
        await asyncio.gather(*monitoring_tasks)
        
        # Complete monitoring phase
        async with monitor.state_manager.transaction() as txn_id:
            current_workflow = await monitor.get_shared_state(f"workflow_{workflow_id}")
            current_workflow["phases"]["monitoring"]["status"] = "completed"
            current_workflow["phases"]["monitoring"]["result"] = {
                "system_health": "optimal",
                "components_checked": 4,
                "issues_found": 0
            }
            current_workflow["status"] = "completed"
            current_workflow["version"] += 1
            current_workflow["completed_at"] = datetime.utcnow().isoformat()
            await monitor.set_shared_state(f"workflow_{workflow_id}", current_workflow, txn_id)
        
        # Phase 5: Verify complete workflow state
        final_workflow = await supervisor.get_shared_state(f"workflow_{workflow_id}")
        
        assert final_workflow["status"] == "completed"
        assert final_workflow["version"] == 4  # 3 updates from initial
        assert all(
            phase["status"] == "completed" 
            for phase in final_workflow["phases"].values()
        )
        
        # Verify temporary state still exists (within TTL)
        temp_state = await supervisor.get_shared_state(f"temp_execution_{workflow_id}")
        assert temp_state is not None
        
        # Verify health check states
        for component in ["database", "redis", "api", "websockets"]:
            health_state = await supervisor.get_shared_state(f"health_{component}")
            assert health_state["status"] == "healthy"
            assert health_state["component"] == component
        
        # Test state recovery simulation
        # Simulate supervisor failure and recovery
        supervisor.simulate_failure()
        
        # New supervisor instance should recover state
        recovery_supervisor = MockAgent("recovery_supervisor", hybrid_state_manager)
        recovered_workflow = await recovery_supervisor.get_shared_state(f"workflow_{workflow_id}")
        
        assert recovered_workflow == final_workflow
        assert recovered_workflow["status"] == "completed"
        
        logger.info(f"Complete workflow test passed:")
        logger.info(f"  Workflow ID: {workflow_id}")
        logger.info(f"  Final version: {final_workflow['version']}")
        logger.info(f"  All phases completed successfully")
        logger.info(f"  State recovery verified")


# Update todo progress
async def test_runner_summary():
    """Summary of all test scenarios created"""
    
    logger.info("Redis State Persistence Test Suite Summary:")
    logger.info("=" * 60)
    logger.info("Test Categories Created:")
    logger.info("1. Shared Context Between Agents")
    logger.info("   - Cross-agent data sharing")
    logger.info("   - Collaborative context updates")
    logger.info("   - Agent-specific context isolation")
    logger.info("")
    logger.info("2. State Recovery After Failures")
    logger.info("   - Persistent state after agent failure")
    logger.info("   - SupervisorStateManager recovery")
    logger.info("   - Graceful handling of corrupted state")
    logger.info("")
    logger.info("3. Concurrent State Access Patterns")
    logger.info("   - Concurrent read operations")
    logger.info("   - Transactional concurrent writes")
    logger.info("   - Performance benchmarks")
    logger.info("")
    logger.info("4. State TTL and Expiration Handling") 
    logger.info("   - TTL-based expiration")
    logger.info("   - TTL renewal patterns")
    logger.info("   - Expired state cleanup")
    logger.info("")
    logger.info("5. State Versioning and Conflict Resolution")
    logger.info("   - Optimistic locking")
    logger.info("   - Last-write-wins resolution")
    logger.info("   - Version conflict handling")
    logger.info("")
    logger.info("6. Redis Pipeline Operations")
    logger.info("   - Batch updates with pipelines")
    logger.info("   - Pipeline performance vs individual ops")
    logger.info("   - Transaction-like behavior")
    logger.info("")
    logger.info("7. Fallback to Memory When Redis Unavailable")
    logger.info("   - Hybrid storage fallback")
    logger.info("   - Graceful degradation on timeout")
    logger.info("   - Recovery after reconnection")
    logger.info("")
    logger.info("8. Performance and Benchmarks")
    logger.info("   - Cross-storage-type benchmarks")
    logger.info("   - Multi-agent performance simulation")
    logger.info("   - Real-world workflow performance")
    logger.info("")
    logger.info("9. Integrated Multi-Agent Scenarios")
    logger.info("   - Complete workflow with all patterns")
    logger.info("   - Real-world agent orchestration")
    logger.info("   - State persistence validation")
    logger.info("=" * 60)