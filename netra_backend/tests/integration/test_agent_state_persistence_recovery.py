"""
CRITICAL INTEGRATION TEST #8: Agent State Persistence During Initialization

BVJ:
- Segment: Platform/Internal (foundation for ALL customer segments)
- Business Goal: Platform Stability - Prevent $35K MRR loss from state corruption failures
- Value Impact: Ensures initialize → save state → crash recovery → state restoration pipeline
- Revenue Impact: Prevents customer session loss during agent crashes/restarts

REQUIREMENTS:
- Initialize agent state correctly
- Persist state to storage (Redis/Database)
- Simulate crash/restart scenarios
- Restore state from persistence
- State consistency validation
- Recovery within 10 seconds
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json

# Add project root to path
# Set testing environment
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from logging_config import central_logger

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from test_framework.mock_utils import mock_justified

logger = central_logger.get_logger(__name__)


class MockPersistentAgent(BaseSubAgent):
    """Mock agent with state persistence capabilities."""
    
    def __init__(self, name: str, llm_manager=None):
        super().__init__(llm_manager, name=name)
        self.execution_history = []
        self.state_versions = []
        self.crash_count = 0
    
    async def execute(self, request: Dict[str, Any], state: DeepAgentState) -> Dict[str, Any]:
        """Execute with state tracking."""
        execution_id = f"exec_{len(self.execution_history)}"
        
        # Record execution
        self.execution_history.append({
            "id": execution_id,
            "request": request,
            "timestamp": datetime.now(timezone.utc),
            "state_snapshot": state.to_dict() if state else None
        })
        
        # Update state
        if state:
            state = state.copy_with_updates(
                last_execution=execution_id,
                execution_count=len(self.execution_history)
            )
            self.state_versions.append(state.to_dict())
        
        return {
            "status": "success",
            "execution_id": execution_id,
            "agent": self.name,
            "state_version": len(self.state_versions)
        }
    
    def simulate_crash(self):
        """Simulate agent crash with state loss."""
        self.crash_count += 1
        # Lose in-memory state but keep persistence-backed data
        return f"crash_{self.crash_count}"


class TestAgentStatePersistenceRecovery:
    """BVJ: Protects $35K MRR through reliable agent state persistence and recovery."""

    @pytest.fixture
    @mock_justified("Redis service external dependency for state persistence")
    def redis_manager_mock(self):
        """Mock Redis manager for state persistence testing."""
        redis_mock = Mock(spec=RedisManager)
        redis_mock.enabled = True
        
        # In-memory state store simulation
        state_store = {}
        
        async def mock_set(key: str, value: str, ex: Optional[int] = None):
            state_store[key] = {
                "value": value,
                "expiry": ex,
                "timestamp": datetime.now(timezone.utc)
            }
            return True
        
        async def mock_get(key: str):
            if key in state_store:
                return state_store[key]["value"]
            return None
        
        async def mock_delete(key: str):
            if key in state_store:
                del state_store[key]
                return 1
            return 0
        
        async def mock_exists(key: str):
            return key in state_store
        
        redis_mock.set = AsyncMock(side_effect=mock_set)
        redis_mock.get = AsyncMock(side_effect=mock_get)
        redis_mock.delete = AsyncMock(side_effect=mock_delete)
        redis_mock.exists = AsyncMock(side_effect=mock_exists)
        redis_mock._state_store = state_store  # For test inspection
        
        return redis_mock

    @pytest.fixture
    @mock_justified("LLM service external dependency for agent testing")
    def llm_manager_mock(self):
        """Mock LLM manager for state testing."""
        llm_mock = Mock(spec=LLMManager)
        llm_mock.generate_response = AsyncMock(return_value={
            "content": "State persistence response",
            "usage": {"prompt_tokens": 30, "completion_tokens": 10}
        })
        return llm_mock

    @pytest.fixture
    @mock_justified("Tool dispatcher external dependency for state operations")
    def tool_dispatcher_mock(self):
        """Mock tool dispatcher for state testing."""
        dispatcher_mock = Mock(spec=ToolDispatcher)
        dispatcher_mock.dispatch = AsyncMock(return_value={"status": "success"})
        return dispatcher_mock

    @pytest.mark.asyncio
    async def test_01_agent_state_initialization_persistence(self, redis_manager_mock, llm_manager_mock):
        """BVJ: Validates agent state is correctly initialized and persisted."""
        # Step 1: Create initial agent state
        user_id = "test_user_123"
        thread_id = "thread_456"
        
        initial_state = DeepAgentState(
            user_id=user_id,
            thread_id=thread_id,
            current_agent="triage",
            redis_manager=redis_manager_mock
        )
        
        # Step 2: Add state data
        test_context = {
            "user_request": "Optimize GPU memory usage",
            "session_data": {"preferences": {"theme": "dark"}},
            "request_history": []
        }
        
        state_with_context = initial_state.copy_with_updates(
            user_request=test_context["user_request"],
            context=test_context
        )
        
        # Step 3: Persist state to Redis
        state_key = f"agent_state:{user_id}:{thread_id}"
        state_json = json.dumps(state_with_context.to_dict())
        
        await redis_manager_mock.set(state_key, state_json, ex=3600)
        
        # Step 4: Verify persistence
        persisted_state_json = await redis_manager_mock.get(state_key)
        assert persisted_state_json is not None, "State not persisted to Redis"
        
        persisted_state_dict = json.loads(persisted_state_json)
        assert persisted_state_dict["user_id"] == user_id, "User ID not preserved"
        assert persisted_state_dict["thread_id"] == thread_id, "Thread ID not preserved"
        assert persisted_state_dict["current_agent"] == "triage", "Current agent not preserved"
        assert persisted_state_dict["user_request"] == test_context["user_request"], "User request not preserved"
        
        # Step 5: Validate state can be reconstructed
        reconstructed_state = DeepAgentState.from_dict(persisted_state_dict, redis_manager_mock)
        assert reconstructed_state.user_id == user_id, "Reconstructed user ID incorrect"
        assert reconstructed_state.thread_id == thread_id, "Reconstructed thread ID incorrect"
        assert reconstructed_state.user_request == test_context["user_request"], "Reconstructed request incorrect"
        
        logger.info(f"State initialization and persistence validated for user {user_id}")

    @pytest.mark.asyncio
    async def test_02_agent_execution_state_tracking(self, redis_manager_mock, llm_manager_mock):
        """BVJ: Validates agent execution states are tracked and persisted correctly."""
        # Step 1: Create persistent agent
        agent = MockPersistentAgent("state_tracker", llm_manager_mock)
        
        # Step 2: Create initial state
        state = DeepAgentState(
            user_id="tracking_user",
            thread_id="tracking_thread",
            current_agent="state_tracker",
            redis_manager=redis_manager_mock
        )
        
        # Step 3: Execute multiple operations with state tracking
        execution_requests = [
            {"operation": "initialize", "data": {"mode": "performance"}},
            {"operation": "analyze", "data": {"target": "gpu_memory"}},
            {"operation": "optimize", "data": {"strategy": "checkpoint"}},
            {"operation": "validate", "data": {"threshold": 0.95}}
        ]
        
        execution_results = []
        
        for i, request in enumerate(execution_requests):
            # Execute with state
            result = await agent.execute(request, state)
            execution_results.append(result)
            
            # Persist state after each execution
            state_key = f"agent_state:tracking_user:tracking_thread:v{i+1}"
            state_json = json.dumps(state.to_dict())
            await redis_manager_mock.set(state_key, state_json)
            
            # Update state for next iteration
            state = state.copy_with_updates(
                last_operation=request["operation"],
                execution_count=i+1
            )
        
        # Step 4: Validate execution tracking
        assert len(execution_results) == 4, f"Expected 4 executions, got {len(execution_results)}"
        assert len(agent.execution_history) == 4, f"Agent missing execution history"
        assert len(agent.state_versions) == 4, f"Agent missing state versions"
        
        # Step 5: Verify state versions in Redis
        for i in range(4):
            version_key = f"agent_state:tracking_user:tracking_thread:v{i+1}"
            version_exists = await redis_manager_mock.exists(version_key)
            assert version_exists, f"State version {i+1} not persisted"
        
        # Step 6: Validate execution sequence integrity
        for i, result in enumerate(execution_results):
            assert result["status"] == "success", f"Execution {i} failed"
            assert result["state_version"] == i+1, f"State version mismatch at execution {i}"
        
        logger.info(f"Execution state tracking validated: {len(execution_results)} operations tracked")

    @pytest.mark.asyncio
    async def test_03_crash_recovery_state_restoration(self, redis_manager_mock, llm_manager_mock):
        """BVJ: Validates agent state can be restored after crash/restart scenarios."""
        # Step 1: Create agent and establish state
        original_agent = MockPersistentAgent("crash_test", llm_manager_mock)
        
        pre_crash_state = DeepAgentState(
            user_id="crash_user",
            thread_id="crash_thread", 
            current_agent="crash_test",
            redis_manager=redis_manager_mock
        )
        
        # Step 2: Execute operations to build state
        pre_crash_operations = [
            {"task": "data_load", "progress": 25},
            {"task": "analysis", "progress": 60},
            {"task": "optimization", "progress": 80}
        ]
        
        for i, operation in enumerate(pre_crash_operations):
            await original_agent.execute(operation, pre_crash_state)
            
            # Persist state
            state_key = f"agent_state:crash_user:crash_thread"
            pre_crash_state = pre_crash_state.copy_with_updates(
                current_task=operation["task"],
                progress=operation["progress"],
                last_update=datetime.now(timezone.utc).isoformat()
            )
            state_json = json.dumps(pre_crash_state.to_dict())
            await redis_manager_mock.set(state_key, state_json)
        
        # Step 3: Record pre-crash state metrics
        pre_crash_metrics = {
            "execution_count": len(original_agent.execution_history),
            "state_versions": len(original_agent.state_versions),
            "last_task": pre_crash_state.current_task,
            "progress": pre_crash_state.progress
        }
        
        # Step 4: Simulate agent crash
        crash_id = original_agent.simulate_crash()
        logger.info(f"Simulated agent crash: {crash_id}")
        
        # Step 5: Create new agent instance (restart)
        start_recovery_time = time.time()
        
        recovered_agent = MockPersistentAgent("crash_test_recovered", llm_manager_mock)
        
        # Step 6: Restore state from persistence
        state_key = f"agent_state:crash_user:crash_thread"
        persisted_state_json = await redis_manager_mock.get(state_key)
        assert persisted_state_json is not None, "No persisted state found for recovery"
        
        persisted_state_dict = json.loads(persisted_state_json)
        recovered_state = DeepAgentState.from_dict(persisted_state_dict, redis_manager_mock)
        
        recovery_time = time.time() - start_recovery_time
        
        # Step 7: Validate state recovery
        assert recovered_state.user_id == "crash_user", "User ID not recovered"
        assert recovered_state.thread_id == "crash_thread", "Thread ID not recovered"
        assert recovered_state.current_task == "optimization", "Last task not recovered"
        assert recovered_state.progress == 80, "Progress not recovered"
        
        # Step 8: Test continued operation post-recovery
        post_recovery_operation = {"task": "completion", "progress": 100}
        recovery_result = await recovered_agent.execute(post_recovery_operation, recovered_state)
        
        assert recovery_result["status"] == "success", "Post-recovery execution failed"
        
        # Step 9: Validate recovery timing
        assert recovery_time < 10.0, f"Recovery took {recovery_time:.2f}s, exceeds 10s limit"
        
        logger.info(f"Crash recovery validated: {recovery_time:.2f}s recovery time")

    @pytest.mark.asyncio
    async def test_04_state_consistency_validation(self, redis_manager_mock, llm_manager_mock):
        """BVJ: Validates state consistency across multiple operations and persistence layers."""
        # Step 1: Create multiple agents sharing state context
        agents = [
            MockPersistentAgent("consistency_agent_1", llm_manager_mock),
            MockPersistentAgent("consistency_agent_2", llm_manager_mock),
            MockPersistentAgent("consistency_agent_3", llm_manager_mock)
        ]
        
        # Step 2: Create shared state
        shared_state = DeepAgentState(
            user_id="consistency_user",
            thread_id="consistency_thread",
            current_agent="consistency_agent_1",
            redis_manager=redis_manager_mock
        )
        
        # Step 3: Execute concurrent operations with state updates
        consistency_operations = [
            {"agent_id": 0, "operation": "phase_1", "data": {"step": 1, "value": 100}},
            {"agent_id": 1, "operation": "phase_2", "data": {"step": 2, "value": 200}},
            {"agent_id": 2, "operation": "phase_3", "data": {"step": 3, "value": 300}},
            {"agent_id": 0, "operation": "phase_1_update", "data": {"step": 4, "value": 150}},
            {"agent_id": 1, "operation": "phase_2_update", "data": {"step": 5, "value": 250}}
        ]
        
        state_snapshots = []
        
        for i, operation in enumerate(consistency_operations):
            agent = agents[operation["agent_id"]]
            
            # Execute operation
            result = await agent.execute(operation, shared_state)
            
            # Update shared state
            shared_state = shared_state.copy_with_updates(
                current_agent=agent.name,
                last_operation=operation["operation"],
                operation_sequence=i+1,
                step_data=operation["data"]
            )
            
            # Persist state snapshot
            snapshot_key = f"state_snapshot:consistency_user:consistency_thread:op_{i+1}"
            state_json = json.dumps(shared_state.to_dict())
            await redis_manager_mock.set(snapshot_key, state_json)
            
            state_snapshots.append({
                "operation_id": i+1,
                "agent": agent.name,
                "operation": operation["operation"],
                "state_hash": hash(state_json),
                "timestamp": datetime.now(timezone.utc)
            })
        
        # Step 4: Validate state consistency across snapshots
        for i, snapshot in enumerate(state_snapshots):
            snapshot_key = f"state_snapshot:consistency_user:consistency_thread:op_{i+1}"
            
            # Retrieve and validate snapshot
            snapshot_json = await redis_manager_mock.get(snapshot_key)
            assert snapshot_json is not None, f"Snapshot {i+1} not found"
            
            snapshot_dict = json.loads(snapshot_json)
            assert snapshot_dict["operation_sequence"] == i+1, f"Operation sequence mismatch at snapshot {i+1}"
            assert snapshot_dict["current_agent"] == snapshot["agent"], f"Agent mismatch at snapshot {i+1}"
        
        # Step 5: Verify state evolution correctness
        final_snapshot_key = f"state_snapshot:consistency_user:consistency_thread:op_{len(consistency_operations)}"
        final_state_json = await redis_manager_mock.get(final_snapshot_key)
        final_state_dict = json.loads(final_state_json)
        
        assert final_state_dict["operation_sequence"] == len(consistency_operations), "Final operation sequence incorrect"
        assert final_state_dict["last_operation"] == "phase_2_update", "Final operation incorrect"
        
        # Step 6: Test state reconstruction consistency
        reconstructed_state = DeepAgentState.from_dict(final_state_dict, redis_manager_mock)
        
        assert reconstructed_state.user_id == "consistency_user", "Reconstructed user ID inconsistent"
        assert reconstructed_state.operation_sequence == len(consistency_operations), "Reconstructed sequence inconsistent"
        
        logger.info(f"State consistency validated across {len(consistency_operations)} operations")

    @pytest.mark.asyncio
    async def test_05_concurrent_state_persistence_integrity(self, redis_manager_mock, llm_manager_mock):
        """BVJ: Validates state persistence maintains integrity under concurrent access."""
        # Step 1: Create multiple concurrent agents
        concurrent_agents = [
            MockPersistentAgent(f"concurrent_agent_{i}", llm_manager_mock)
            for i in range(10)
        ]
        
        # Step 2: Create individual states for each agent
        agent_states = []
        for i, agent in enumerate(concurrent_agents):
            state = DeepAgentState(
                user_id=f"concurrent_user_{i}",
                thread_id=f"concurrent_thread_{i}",
                current_agent=agent.name,
                redis_manager=redis_manager_mock
            )
            agent_states.append(state)
        
        # Step 3: Execute concurrent operations with state persistence
        async def concurrent_agent_operations(agent_index):
            """Execute multiple operations for a single agent."""
            agent = concurrent_agents[agent_index]
            state = agent_states[agent_index]
            
            operations = [
                {"step": "init", "value": agent_index * 10},
                {"step": "process", "value": agent_index * 20},
                {"step": "optimize", "value": agent_index * 30},
                {"step": "finalize", "value": agent_index * 40}
            ]
            
            for j, operation in enumerate(operations):
                # Execute operation
                result = await agent.execute(operation, state)
                
                # Update and persist state
                state = state.copy_with_updates(
                    current_step=operation["step"],
                    step_value=operation["value"],
                    iteration=j+1
                )
                
                state_key = f"concurrent_state:user_{agent_index}:thread_{agent_index}"
                state_json = json.dumps(state.to_dict())
                await redis_manager_mock.set(state_key, state_json)
                
                # Small delay to simulate processing
                await asyncio.sleep(0.01)
            
            return {
                "agent_index": agent_index,
                "operations_completed": len(operations),
                "final_state": state.to_dict()
            }
        
        # Step 4: Execute all agents concurrently
        start_time = time.time()
        
        concurrent_results = await asyncio.gather(*[
            concurrent_agent_operations(i) for i in range(len(concurrent_agents))
        ])
        
        concurrent_time = time.time() - start_time
        
        # Step 5: Validate all operations completed successfully
        assert len(concurrent_results) == len(concurrent_agents), f"Missing results: expected {len(concurrent_agents)}, got {len(concurrent_results)}"
        
        for result in concurrent_results:
            assert result["operations_completed"] == 4, f"Agent {result['agent_index']} incomplete operations"
        
        # Step 6: Verify state persistence integrity
        for i in range(len(concurrent_agents)):
            state_key = f"concurrent_state:user_{i}:thread_{i}"
            persisted_state_json = await redis_manager_mock.get(state_key)
            
            assert persisted_state_json is not None, f"State not persisted for agent {i}"
            
            persisted_state = json.loads(persisted_state_json)
            assert persisted_state["iteration"] == 4, f"Agent {i} state iteration incorrect"
            assert persisted_state["step_value"] == i * 40, f"Agent {i} final value incorrect"
        
        # Step 7: Validate concurrency performance
        operations_per_second = (len(concurrent_agents) * 4) / concurrent_time
        assert operations_per_second >= 100, f"Concurrent operations too slow: {operations_per_second:.1f} ops/sec"
        
        # Step 8: Test state isolation (no cross-contamination)
        for i in range(len(concurrent_agents)):
            state_key = f"concurrent_state:user_{i}:thread_{i}"
            state_json = await redis_manager_mock.get(state_key)
            state_dict = json.loads(state_json)
            
            assert state_dict["user_id"] == f"concurrent_user_{i}", f"State cross-contamination at agent {i}"
            assert state_dict["step_value"] == i * 40, f"Value cross-contamination at agent {i}"
        
        logger.info(f"Concurrent state persistence validated: {len(concurrent_agents)} agents, {operations_per_second:.1f} ops/sec")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])