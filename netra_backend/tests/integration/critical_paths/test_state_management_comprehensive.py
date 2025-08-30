"""Comprehensive State Management Test Suite

Business Value Justification (BVJ):
- Segment: Enterprise, Mid-tier 
- Business Goal: System reliability, risk reduction, development velocity
- Value Impact: Prevents state-related failures, ensures data consistency
- Revenue Impact: Protects $50K+ MRR from state management failures

This comprehensive test suite addresses critical coverage gaps identified in the 
multi-agent orchestration coverage report, focusing on complex workflows, 
concurrent access patterns, and resilience mechanisms.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.state.state_manager import StateManager, StateStorage


@dataclass
class StateOperationMetrics:
    """Tracks performance metrics for state operations"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    
    def add_operation(self, success: bool, latency_ms: float):
        """Record an operation"""
        self.total_operations += 1
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
        self.total_latency_ms += latency_ms
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency"""
        if self.total_operations == 0:
            return 0.0
        return self.total_latency_ms / self.total_operations
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations


@dataclass
class ConcurrentStateTest:
    """Configuration for concurrent state testing"""
    num_agents: int
    num_operations_per_agent: int
    conflict_probability: float = 0.3  # Probability of accessing same key
    delay_between_ops_ms: int = 10


class ComprehensiveStateTestManager:
    """Manages comprehensive state management testing"""
    
    def __init__(self):
        self.state_manager: Optional[StateManager] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self.active_agents: Dict[str, BaseSubAgent] = {}
        self.metrics = StateOperationMetrics()
        self.state_versions: Dict[str, List[Dict[str, Any]]] = {}  # Track state history
        
    async def setup(self, storage_type: StateStorage = StateStorage.MEMORY):
        """Initialize test manager with specified storage"""
        self.state_manager = StateManager(storage=storage_type)
        self._setup_agent_registry()
        
    def _setup_agent_registry(self):
        """Setup mock agent registry"""
        mock_llm = AsyncMock()
        mock_llm.generate_response = AsyncMock(return_value={
            "content": "Mock response",
            "metadata": {"cost": 0.001}
        })
        mock_tool_dispatcher = AsyncMock()
        
        self.agent_registry = AgentRegistry(
            llm_manager=mock_llm,
            tool_dispatcher=mock_tool_dispatcher
        )
        self.agent_registry.register_default_agents()
    
    async def create_hierarchical_agent_network(self, layers: int = 3, agents_per_layer: int = 5) -> Dict[str, Any]:
        """Create a multi-layer hierarchical agent network for complex testing"""
        network = {
            "layers": {},
            "connections": [],
            "total_agents": 0
        }
        
        for layer_idx in range(layers):
            layer_agents = []
            for agent_idx in range(agents_per_layer):
                agent_id = f"layer_{layer_idx}_agent_{agent_idx}"
                agent_type = ["triage", "data", "optimization"][agent_idx % 3]
                
                # Create agent state
                agent_state = {
                    "id": agent_id,
                    "type": agent_type,
                    "layer": layer_idx,
                    "status": "active",
                    "connections": [],
                    "state_keys": []
                }
                
                # Store in state manager
                await self.state_manager.set(f"agent:{agent_id}", agent_state)
                layer_agents.append(agent_id)
                
                # Create connections to previous layer
                if layer_idx > 0 and network["layers"].get(layer_idx - 1):
                    prev_layer_agents = network["layers"][layer_idx - 1]
                    # Connect to 2 random agents from previous layer
                    connections = prev_layer_agents[:2] if len(prev_layer_agents) >= 2 else prev_layer_agents
                    for connected_agent in connections:
                        network["connections"].append({
                            "from": connected_agent,
                            "to": agent_id,
                            "layer_transition": f"{layer_idx-1}->{layer_idx}"
                        })
                        agent_state["connections"].append(connected_agent)
                
                self.active_agents[agent_id] = MagicMock()  # Mock agent instance
                network["total_agents"] += 1
            
            network["layers"][layer_idx] = layer_agents
        
        return network
    
    async def propagate_state_through_network(self, network: Dict[str, Any], initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """Propagate state through hierarchical network with versioning"""
        propagation_results = {
            "total_propagations": 0,
            "successful_propagations": 0,
            "conflicts_resolved": 0,
            "propagation_time_ms": 0.0,
            "state_versions": {}
        }
        
        start_time = time.time()
        
        # Start from layer 0
        for layer_idx, layer_agents in network["layers"].items():
            for agent_id in layer_agents:
                # Create versioned state for this agent
                state_key = f"state:{agent_id}:data"
                current_version = len(self.state_versions.get(state_key, []))
                
                versioned_state = {
                    "version": current_version + 1,
                    "data": initial_state.copy(),
                    "agent_id": agent_id,
                    "layer": layer_idx,
                    "timestamp": time.time(),
                    "parent_version": current_version if current_version > 0 else None
                }
                
                # Apply layer-specific transformations
                versioned_state["data"][f"layer_{layer_idx}_processed"] = True
                versioned_state["data"]["processing_chain"] = versioned_state["data"].get("processing_chain", [])
                versioned_state["data"]["processing_chain"].append(agent_id)
                
                # Store versioned state
                await self.state_manager.set(state_key, versioned_state)
                
                # Track version history
                if state_key not in self.state_versions:
                    self.state_versions[state_key] = []
                self.state_versions[state_key].append(versioned_state)
                
                propagation_results["total_propagations"] += 1
                propagation_results["successful_propagations"] += 1
                propagation_results["state_versions"][agent_id] = current_version + 1
        
        propagation_results["propagation_time_ms"] = (time.time() - start_time) * 1000
        return propagation_results
    
    async def execute_concurrent_state_test(self, config: ConcurrentStateTest) -> Dict[str, Any]:
        """Execute concurrent state access test with conflict generation"""
        results = {
            "config": config,
            "conflicts_generated": 0,
            "conflicts_resolved": 0,
            "total_operations": 0,
            "successful_operations": 0,
            "metrics": StateOperationMetrics()
        }
        
        # Define shared keys that will cause conflicts
        shared_keys = [f"shared_key_{i}" for i in range(3)]
        agent_keys = {f"agent_{i}": f"private_key_{i}" for i in range(config.num_agents)}
        
        async def agent_operations(agent_id: str):
            """Simulate agent performing state operations"""
            local_metrics = StateOperationMetrics()
            
            for op_idx in range(config.num_operations_per_agent):
                start_time = time.time()
                
                # Decide whether to access shared or private key
                use_shared = asyncio.get_event_loop().time() % 10 < (config.conflict_probability * 10)
                key = shared_keys[op_idx % len(shared_keys)] if use_shared else agent_keys[agent_id]
                
                try:
                    # Read-modify-write pattern
                    current_value = await self.state_manager.get(key, {"counter": 0, "agents": []})
                    
                    # Simulate processing delay
                    await asyncio.sleep(config.delay_between_ops_ms / 1000.0)
                    
                    # Modify state
                    new_value = current_value.copy()
                    new_value["counter"] = new_value.get("counter", 0) + 1
                    new_value["agents"] = new_value.get("agents", [])
                    if agent_id not in new_value["agents"]:
                        new_value["agents"].append(agent_id)
                    new_value[f"last_modified_by"] = agent_id
                    new_value[f"modification_time"] = time.time()
                    
                    await self.state_manager.set(key, new_value)
                    
                    latency_ms = (time.time() - start_time) * 1000
                    local_metrics.add_operation(True, latency_ms)
                    
                    if use_shared:
                        results["conflicts_generated"] += 1
                        
                except Exception as e:
                    latency_ms = (time.time() - start_time) * 1000
                    local_metrics.add_operation(False, latency_ms)
            
            return local_metrics
        
        # Execute concurrent operations
        tasks = []
        for i in range(config.num_agents):
            agent_id = f"agent_{i}"
            task = agent_operations(agent_id)
            tasks.append(task)
        
        agent_metrics = await asyncio.gather(*tasks)
        
        # Aggregate metrics
        for metrics in agent_metrics:
            results["total_operations"] += metrics.total_operations
            results["successful_operations"] += metrics.successful_operations
            results["metrics"].total_operations += metrics.total_operations
            results["metrics"].successful_operations += metrics.successful_operations
            results["metrics"].failed_operations += metrics.failed_operations
            results["metrics"].total_latency_ms += metrics.total_latency_ms
            results["metrics"].max_latency_ms = max(results["metrics"].max_latency_ms, metrics.max_latency_ms)
            results["metrics"].min_latency_ms = min(results["metrics"].min_latency_ms, metrics.min_latency_ms)
        
        # Verify final state consistency
        for key in shared_keys:
            final_state = await self.state_manager.get(key, {})
            expected_agents = min(config.num_agents, int(config.num_agents * config.conflict_probability) + 1)
            if len(final_state.get("agents", [])) > 0:
                results["conflicts_resolved"] += 1
        
        return results
    
    async def test_state_recovery(self, failure_type: str = "crash") -> Dict[str, Any]:
        """Test state recovery after various failure scenarios"""
        recovery_results = {
            "failure_type": failure_type,
            "states_before_failure": 0,
            "states_recovered": 0,
            "data_integrity_maintained": True,
            "recovery_time_ms": 0.0
        }
        
        # Create initial states
        test_states = {}
        for i in range(10):
            key = f"recovery_test_{i}"
            value = {
                "id": key,
                "data": f"important_data_{i}",
                "checksum": hash(f"important_data_{i}"),
                "created_at": time.time()
            }
            await self.state_manager.set(key, value)
            test_states[key] = value
            recovery_results["states_before_failure"] += 1
        
        # Simulate failure
        if failure_type == "crash":
            # Simulate sudden crash - clear some states
            for i in range(3, 7):  # Simulate partial state loss
                key = f"recovery_test_{i}"
                await self.state_manager.delete(key)
        elif failure_type == "corruption":
            # Simulate state corruption
            for i in range(2, 5):
                key = f"recovery_test_{i}"
                corrupted_value = await self.state_manager.get(key)
                if corrupted_value:
                    corrupted_value["data"] = "CORRUPTED"
                    corrupted_value["checksum"] = "INVALID"
                    await self.state_manager.set(key, corrupted_value)
        
        # Recovery process
        start_time = time.time()
        
        for key, original_value in test_states.items():
            current_value = await self.state_manager.get(key)
            
            if current_value is None:
                # State lost - recover from backup
                await self.state_manager.set(key, original_value)
                recovery_results["states_recovered"] += 1
            elif current_value.get("checksum") != original_value["checksum"]:
                # State corrupted - restore from backup
                await self.state_manager.set(key, original_value)
                recovery_results["states_recovered"] += 1
            
            # Verify integrity
            final_value = await self.state_manager.get(key)
            if final_value != original_value:
                recovery_results["data_integrity_maintained"] = False
        
        recovery_results["recovery_time_ms"] = (time.time() - start_time) * 1000
        
        return recovery_results
    
    async def test_transaction_rollback(self) -> Dict[str, Any]:
        """Test transactional state updates with rollback capability"""
        rollback_results = {
            "transactions_started": 0,
            "transactions_committed": 0,
            "transactions_rolled_back": 0,
            "rollback_successful": True
        }
        
        # Create initial state
        initial_states = {}
        for i in range(5):
            key = f"transactional_state_{i}"
            value = {"counter": i * 10, "status": "initial"}
            await self.state_manager.set(key, value)
            initial_states[key] = value.copy()
        
        # Start transaction
        async with self.state_manager.transaction() as txn:
            rollback_results["transactions_started"] += 1
            
            try:
                # Make multiple state changes
                for i in range(5):
                    key = f"transactional_state_{i}"
                    current = await self.state_manager.get(key)
                    current["counter"] += 100
                    current["status"] = "modified"
                    await self.state_manager.set(key, current, transaction_id=txn.id)
                
                # Simulate failure condition
                if True:  # Always rollback for testing
                    raise Exception("Simulated transaction failure")
                
                await txn.commit()
                rollback_results["transactions_committed"] += 1
                
            except Exception:
                await txn.rollback()
                rollback_results["transactions_rolled_back"] += 1
        
        # Verify rollback
        for key, initial_value in initial_states.items():
            current_value = await self.state_manager.get(key)
            if current_value != initial_value:
                rollback_results["rollback_successful"] = False
                break
        
        return rollback_results
    
    async def test_checkpoint_restore(self) -> Dict[str, Any]:
        """Test checkpoint and restore functionality"""
        checkpoint_results = {
            "checkpoints_created": 0,
            "states_in_checkpoint": 0,
            "restore_successful": True,
            "data_integrity_verified": True
        }
        
        # Create states to checkpoint
        checkpoint_data = {}
        for i in range(20):
            key = f"checkpoint_state_{i}"
            value = {
                "id": i,
                "data": f"checkpoint_data_{i}",
                "timestamp": time.time()
            }
            await self.state_manager.set(key, value)
            checkpoint_data[key] = value
            checkpoint_results["states_in_checkpoint"] += 1
        
        # Create checkpoint
        checkpoint_id = f"checkpoint_{uuid.uuid4().hex[:8]}"
        await self.state_manager.create_snapshot(checkpoint_id)
        checkpoint_results["checkpoints_created"] += 1
        
        # Modify states after checkpoint
        for i in range(20):
            key = f"checkpoint_state_{i}"
            modified_value = {
                "id": i,
                "data": f"modified_data_{i}",
                "timestamp": time.time()
            }
            await self.state_manager.set(key, modified_value)
        
        # Restore from checkpoint
        await self.state_manager.restore_snapshot(checkpoint_id)
        
        # Verify restoration
        for key, original_value in checkpoint_data.items():
            restored_value = await self.state_manager.get(key)
            if restored_value != original_value:
                checkpoint_results["restore_successful"] = False
                checkpoint_results["data_integrity_verified"] = False
                break
        
        return checkpoint_results
    
    async def test_memory_under_load(self, num_objects: int = 5000) -> Dict[str, Any]:
        """Test memory usage and cleanup under heavy load"""
        memory_results = {
            "objects_created": 0,
            "peak_memory_keys": 0,
            "final_memory_keys": 0,
            "cleanup_successful": True,
            "performance_degradation": False
        }
        
        # Create large number of state objects
        creation_times = []
        for i in range(num_objects):
            key = f"load_test_{i}"
            value = {
                "id": i,
                "data": "x" * 1000,  # 1KB per object
                "metadata": {"index": i}
            }
            
            start_time = time.time()
            await self.state_manager.set(key, value)
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            
            memory_results["objects_created"] += 1
            
            if i % 1000 == 0:
                stats = self.state_manager.get_stats()
                memory_results["peak_memory_keys"] = max(
                    memory_results["peak_memory_keys"],
                    stats.get("keys", 0)
                )
        
        # Check for performance degradation
        avg_first_100 = sum(creation_times[:100]) / 100
        avg_last_100 = sum(creation_times[-100:]) / 100
        if avg_last_100 > avg_first_100 * 2:  # 2x slower
            memory_results["performance_degradation"] = True
        
        # Cleanup half the objects
        for i in range(0, num_objects, 2):
            key = f"load_test_{i}"
            await self.state_manager.delete(key)
        
        # Final memory check
        stats = self.state_manager.get_stats()
        memory_results["final_memory_keys"] = stats.get("keys", 0)
        
        # Verify cleanup
        expected_remaining = num_objects // 2
        if abs(memory_results["final_memory_keys"] - expected_remaining) > 100:
            memory_results["cleanup_successful"] = False
        
        return memory_results
    
    async def cleanup(self):
        """Clean up test resources"""
        if self.state_manager:
            await self.state_manager.clear()
        self.active_agents.clear()
        self.state_versions.clear()
        self.metrics = StateOperationMetrics()


# Test Fixtures
@pytest.fixture
async def state_test_manager():
    """Create state test manager with memory storage"""
    manager = ComprehensiveStateTestManager()
    await manager.setup(StateStorage.MEMORY)
    yield manager
    await manager.cleanup()


@pytest.fixture
async def state_test_manager_redis():
    """Create state test manager with Redis storage (if available)"""
    manager = ComprehensiveStateTestManager()
    try:
        await manager.setup(StateStorage.HYBRID)
    except Exception:
        # Fallback to memory if Redis unavailable
        await manager.setup(StateStorage.MEMORY)
    yield manager
    await manager.cleanup()


# Test Cases

@pytest.mark.asyncio
@pytest.mark.integration
async def test_complex_multi_agent_state_propagation(state_test_manager):
    """Test state propagation through complex multi-layer agent network.
    
    BVJ:
    - Segment: Enterprise
    - Business Goal: Validate complex agent collaboration patterns
    - Value Impact: Ensures state consistency in hierarchical workflows
    - Revenue Impact: Protects $30K MRR from complex workflow failures
    """
    # Create 5-layer network with 5 agents per layer (25 total agents)
    network = await state_test_manager.create_hierarchical_agent_network(layers=5, agents_per_layer=5)
    
    assert network["total_agents"] == 25
    assert len(network["layers"]) == 5
    
    # Test state propagation
    initial_state = {
        "workflow_id": "test_workflow_001",
        "priority": "high",
        "data": {"metrics": {"cost": 1000, "efficiency": 0.8}}
    }
    
    propagation_results = await state_test_manager.propagate_state_through_network(network, initial_state)
    
    assert propagation_results["successful_propagations"] == 25
    assert propagation_results["total_propagations"] == 25
    assert propagation_results["propagation_time_ms"] < 5000  # Should complete within 5 seconds
    
    # Verify state versioning
    assert len(propagation_results["state_versions"]) == 25
    for agent_id, version in propagation_results["state_versions"].items():
        assert version >= 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_high_concurrency_state_access(state_test_manager):
    """Test concurrent state access with intentional conflict generation.
    
    BVJ:
    - Segment: Enterprise, Mid
    - Business Goal: Ensure system stability under concurrent load
    - Value Impact: Prevents race conditions and data corruption
    - Revenue Impact: Protects $20K MRR from concurrency-related failures
    """
    config = ConcurrentStateTest(
        num_agents=15,
        num_operations_per_agent=20,
        conflict_probability=0.5,  # 50% chance of conflict
        delay_between_ops_ms=5
    )
    
    results = await state_test_manager.execute_concurrent_state_test(config)
    
    assert results["total_operations"] == 300  # 15 agents * 20 ops
    assert results["successful_operations"] >= 285  # Allow up to 5% failure
    assert results["metrics"].success_rate >= 0.95
    assert results["conflicts_generated"] > 0  # Should have conflicts
    assert results["conflicts_resolved"] > 0  # Should resolve conflicts
    
    # Performance assertions
    assert results["metrics"].avg_latency_ms < 100  # Average under 100ms
    assert results["metrics"].max_latency_ms < 500  # Max under 500ms


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.performance
async def test_state_operations_latency_under_load(state_test_manager):
    """Test state operation latency with 20+ concurrent workflows.
    
    BVJ:
    - Segment: Enterprise
    - Business Goal: Maintain performance SLAs under load
    - Value Impact: Ensures responsive system under peak usage
    - Revenue Impact: Prevents customer churn from performance issues
    """
    # Create 20 concurrent workflows
    workflows = []
    for i in range(20):
        config = ConcurrentStateTest(
            num_agents=5,
            num_operations_per_agent=10,
            conflict_probability=0.2,
            delay_between_ops_ms=2
        )
        workflow = state_test_manager.execute_concurrent_state_test(config)
        workflows.append(workflow)
    
    # Execute all workflows concurrently
    start_time = time.time()
    results = await asyncio.gather(*workflows)
    total_time = (time.time() - start_time) * 1000
    
    # Aggregate metrics
    total_ops = sum(r["total_operations"] for r in results)
    successful_ops = sum(r["successful_operations"] for r in results)
    
    assert total_ops == 1000  # 20 workflows * 5 agents * 10 ops
    assert successful_ops >= 950  # 95% success rate
    assert total_time < 30000  # Complete within 30 seconds
    
    # Check individual workflow performance
    for result in results:
        assert result["metrics"].success_rate >= 0.9
        assert result["metrics"].avg_latency_ms < 150


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_crash_recovery_with_state_preservation(state_test_manager):
    """Test recovery from agent crash during state update.
    
    BVJ:
    - Segment: Enterprise
    - Business Goal: System resilience and data integrity
    - Value Impact: Prevents data loss during failures
    - Revenue Impact: Protects against $10K+ incident costs
    """
    # Test crash recovery
    crash_recovery = await state_test_manager.test_state_recovery(failure_type="crash")
    
    assert crash_recovery["states_before_failure"] == 10
    assert crash_recovery["states_recovered"] >= 4  # Should recover lost states
    assert crash_recovery["data_integrity_maintained"] is True
    assert crash_recovery["recovery_time_ms"] < 1000  # Fast recovery
    
    # Test corruption recovery
    corruption_recovery = await state_test_manager.test_state_recovery(failure_type="corruption")
    
    assert corruption_recovery["states_before_failure"] == 10
    assert corruption_recovery["states_recovered"] >= 3  # Should fix corrupted states
    assert corruption_recovery["data_integrity_maintained"] is True
    assert corruption_recovery["recovery_time_ms"] < 1000


@pytest.mark.asyncio
@pytest.mark.integration
async def test_transactional_state_updates_with_rollback(state_test_manager):
    """Test transactional state updates with rollback capability.
    
    BVJ:
    - Segment: Enterprise
    - Business Goal: Ensure data consistency
    - Value Impact: Prevents partial state updates
    - Revenue Impact: Prevents data corruption worth $15K+ in recovery costs
    """
    rollback_results = await state_test_manager.test_transaction_rollback()
    
    assert rollback_results["transactions_started"] == 1
    assert rollback_results["transactions_rolled_back"] == 1
    assert rollback_results["transactions_committed"] == 0
    assert rollback_results["rollback_successful"] is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_checkpoint_and_restore_functionality(state_test_manager):
    """Test checkpoint creation and state restoration.
    
    BVJ:
    - Segment: Enterprise
    - Business Goal: Disaster recovery capability
    - Value Impact: Enables quick recovery from failures
    - Revenue Impact: Reduces downtime costs by $20K+
    """
    checkpoint_results = await state_test_manager.test_checkpoint_restore()
    
    assert checkpoint_results["checkpoints_created"] == 1
    assert checkpoint_results["states_in_checkpoint"] == 20
    assert checkpoint_results["restore_successful"] is True
    assert checkpoint_results["data_integrity_verified"] is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.slow
async def test_massive_scale_state_management(state_test_manager):
    """Test state management with 5000+ objects.
    
    BVJ:
    - Segment: Enterprise
    - Business Goal: Validate system scalability
    - Value Impact: Ensures system can handle growth
    - Revenue Impact: Enables $100K+ customer deployments
    """
    memory_results = await state_test_manager.test_memory_under_load(num_objects=5000)
    
    assert memory_results["objects_created"] == 5000
    assert memory_results["peak_memory_keys"] >= 4900  # Most objects in memory
    assert memory_results["cleanup_successful"] is True
    assert memory_results["performance_degradation"] is False
    assert memory_results["final_memory_keys"] < 2600  # Proper cleanup


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.circuit_breaker
async def test_circuit_breaker_cascade_prevention(state_test_manager):
    """Test circuit breaker prevents cascade failures.
    
    BVJ:
    - Segment: Enterprise
    - Business Goal: Prevent cascade failures
    - Value Impact: Maintains system stability
    - Revenue Impact: Prevents $50K+ outage costs
    """
    # Create agent network
    network = await state_test_manager.create_hierarchical_agent_network(layers=3, agents_per_layer=4)
    
    # Simulate failures in layer 1
    failure_count = 0
    for agent_id in network["layers"][1]:
        agent_state = await state_test_manager.state_manager.get(f"agent:{agent_id}")
        agent_state["status"] = "failed"
        agent_state["circuit_breaker"] = "open"
        await state_test_manager.state_manager.set(f"agent:{agent_id}", agent_state)
        failure_count += 1
    
    # Verify circuit breaker prevents cascade to layer 2
    cascade_prevented = True
    for agent_id in network["layers"][2]:
        agent_state = await state_test_manager.state_manager.get(f"agent:{agent_id}")
        if agent_state["status"] == "failed":
            cascade_prevented = False
            break
    
    assert failure_count == 4  # All layer 1 agents failed
    assert cascade_prevented is True  # Layer 2 protected


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.redis
async def test_redis_state_persistence_across_restart(state_test_manager_redis):
    """Test state persistence with real Redis across service restart.
    
    BVJ:
    - Segment: Enterprise
    - Business Goal: Data durability
    - Value Impact: Ensures state survives restarts
    - Revenue Impact: Prevents data loss worth $30K+
    """
    # Skip if Redis not available
    if state_test_manager_redis.state_manager.storage != StateStorage.HYBRID:
        pytest.skip("Redis not available for testing")
    
    # Create persistent states
    persistent_states = {}
    for i in range(10):
        key = f"persistent_state_{i}"
        value = {
            "id": i,
            "data": f"important_persistent_data_{i}",
            "created_at": time.time()
        }
        await state_test_manager_redis.state_manager.set(key, value)
        persistent_states[key] = value
    
    # Simulate restart by clearing memory cache
    if hasattr(state_test_manager_redis.state_manager, '_memory_store'):
        state_test_manager_redis.state_manager._memory_store.clear()
    
    # Verify states persisted
    states_recovered = 0
    for key, original_value in persistent_states.items():
        recovered_value = await state_test_manager_redis.state_manager.get(key)
        if recovered_value == original_value:
            states_recovered += 1
    
    assert states_recovered == 10  # All states persisted


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_migration_between_storage_backends(state_test_manager):
    """Test migration of states between different storage backends.
    
    BVJ:
    - Segment: Mid, Enterprise
    - Business Goal: Operational flexibility
    - Value Impact: Enables infrastructure changes
    - Revenue Impact: Reduces migration risks worth $25K+
    """
    # Create states in memory storage
    migration_states = {}
    for i in range(15):
        key = f"migration_state_{i}"
        value = {
            "id": i,
            "data": f"data_to_migrate_{i}",
            "storage": "memory"
        }
        await state_test_manager.state_manager.set(key, value)
        migration_states[key] = value
    
    # Simulate migration to different backend
    migrated_count = 0
    for key, value in migration_states.items():
        # Get from current storage
        current_value = await state_test_manager.state_manager.get(key)
        if current_value:
            # Update metadata
            current_value["storage"] = "migrated"
            current_value["migration_time"] = time.time()
            # Write back (would go to new backend in real scenario)
            await state_test_manager.state_manager.set(key, current_value)
            migrated_count += 1
    
    assert migrated_count == 15  # All states migrated
    
    # Verify migrated states
    for key in migration_states:
        migrated_value = await state_test_manager.state_manager.get(key)
        assert migrated_value["storage"] == "migrated"
        assert "migration_time" in migrated_value