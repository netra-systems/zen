"""Agent Lifecycle Management Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (core platform functionality)
- Business Goal: Reliable agent execution and state management  
- Value Impact: Prevents AI processing failures, ensures consistent responses
- Strategic Impact: $20K-40K MRR protection through reliable agent operations

Critical Path: Agent creation -> State initialization -> Task execution -> State persistence -> Cleanup
Coverage: Full agent lifecycle, state preservation, error recovery, resource management
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.state_manager import AgentStateManager

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.config import get_settings
from netra_backend.app.schemas.registry import (
    AgentCompleted,
    AgentStarted,
    SubAgentUpdate,
)
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.llm.llm_manager import LLMManager
from netra_backend.app.services.state_persistence import StatePersistenceService

logger = logging.getLogger(__name__)

class AgentLifecycleManager:
    """Manages agent lifecycle testing with real state persistence."""
    
    def __init__(self):
        self.active_agents = {}
        self.agent_states = {}
        self.execution_history = []
        self.state_manager = AgentStateManager()
        
    async def create_agent(self, agent_type: str, agent_id: str = None, **kwargs) -> BaseSubAgent:
        """Create and initialize an agent with state tracking."""
        if agent_id is None:
            agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
        
        try:
            if agent_type == "supervisor":
                agent = SupervisorAgent(agent_id=agent_id, **kwargs)
            else:
                # Create generic subagent for testing
                agent = BaseSubAgent(agent_id=agent_id, agent_type=agent_type, **kwargs)
            
            # Initialize agent state
            initial_state = DeepAgentState(
                agent_id=agent_id,
                agent_type=agent_type,
                status="initializing",
                created_at=time.time(),
                metadata=kwargs
            )
            
            await self.state_manager.save_state(agent_id, initial_state)
            
            self.active_agents[agent_id] = agent
            self.agent_states[agent_id] = initial_state
            
            self.execution_history.append({
                "action": "agent_created",
                "agent_id": agent_id,
                "agent_type": agent_type,
                "timestamp": time.time()
            })
            
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent {agent_id}: {e}")
            raise
    
    async def execute_agent_task(self, agent_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task with an agent and track state changes."""
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.active_agents[agent_id]
        start_time = time.time()
        
        try:
            # Update state to running
            await self.update_agent_state(agent_id, "running", {"task": task_data})
            
            # Execute task (mock execution for testing)
            if hasattr(agent, 'process_message'):
                result = await agent.process_message(task_data.get("message", "test task"))
            else:
                # Mock task execution
                await asyncio.sleep(0.1)
                result = {"status": "completed", "output": "task completed successfully"}
            
            execution_time = time.time() - start_time
            
            # Update state to completed
            await self.update_agent_state(agent_id, "completed", {
                "result": result,
                "execution_time": execution_time
            })
            
            self.execution_history.append({
                "action": "task_executed", 
                "agent_id": agent_id,
                "execution_time": execution_time,
                "timestamp": time.time()
            })
            
            return result
            
        except Exception as e:
            await self.update_agent_state(agent_id, "error", {"error": str(e)})
            self.execution_history.append({
                "action": "task_failed",
                "agent_id": agent_id, 
                "error": str(e),
                "timestamp": time.time()
            })
            raise
    
    async def update_agent_state(self, agent_id: str, status: str, metadata: Dict = None):
        """Update agent state and persist changes."""
        if agent_id not in self.agent_states:
            raise ValueError(f"Agent state {agent_id} not found")
        
        current_state = self.agent_states[agent_id]
        current_state.status = status
        current_state.updated_at = time.time()
        
        if metadata:
            current_state.metadata.update(metadata)
        
        await self.state_manager.save_state(agent_id, current_state)
        
        self.execution_history.append({
            "action": "state_updated",
            "agent_id": agent_id,
            "status": status,
            "timestamp": time.time()
        })
    
    async def cleanup_agent(self, agent_id: str) -> bool:
        """Clean up agent resources and state."""
        try:
            if agent_id in self.active_agents:
                agent = self.active_agents[agent_id]
                
                # Cleanup agent resources
                if hasattr(agent, 'cleanup'):
                    await agent.cleanup()
                
                # Archive final state
                await self.update_agent_state(agent_id, "archived", {"cleanup_time": time.time()})
                
                # Remove from active tracking
                del self.active_agents[agent_id]
                
                self.execution_history.append({
                    "action": "agent_cleaned_up",
                    "agent_id": agent_id,
                    "timestamp": time.time()
                })
                
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup agent {agent_id}: {e}")
            return False
    
    async def get_agent_metrics(self) -> Dict[str, Any]:
        """Get comprehensive agent lifecycle metrics."""
        total_agents = len(self.execution_history)
        active_count = len(self.active_agents)
        
        # Calculate execution times
        execution_times = [
            entry["execution_time"] for entry in self.execution_history 
            if entry["action"] == "task_executed" and "execution_time" in entry
        ]
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Count status distribution
        status_counts = {}
        for agent_state in self.agent_states.values():
            status = agent_state.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_agents_created": total_agents,
            "active_agents": active_count,
            "average_execution_time": avg_execution_time,
            "status_distribution": status_counts,
            "execution_history_length": len(self.execution_history)
        }

@pytest.fixture
async def lifecycle_manager():
    """Create agent lifecycle manager for testing."""
    manager = AgentLifecycleManager()
    yield manager
    
    # Cleanup all agents
    for agent_id in list(manager.active_agents.keys()):
        await manager.cleanup_agent(agent_id)

@pytest.mark.asyncio
async def test_agent_creation_and_initialization(lifecycle_manager):
    """Test agent creation with proper state initialization."""
    agent_id = "test_supervisor_001"
    
    # Create supervisor agent
    agent = await lifecycle_manager.create_agent("supervisor", agent_id)
    
    # Verify agent created
    assert agent_id in lifecycle_manager.active_agents
    assert agent_id in lifecycle_manager.agent_states
    
    # Verify initial state
    state = lifecycle_manager.agent_states[agent_id]
    assert state.agent_id == agent_id
    assert state.agent_type == "supervisor"
    assert state.status == "initializing"
    assert state.created_at > 0
    
    # Verify execution history
    creation_events = [
        event for event in lifecycle_manager.execution_history 
        if event["action"] == "agent_created" and event["agent_id"] == agent_id
    ]
    assert len(creation_events) == 1

@pytest.mark.asyncio
async def test_agent_task_execution_lifecycle(lifecycle_manager):
    """Test complete task execution with state transitions."""
    agent_id = "test_executor_001"
    
    # Create agent
    agent = await lifecycle_manager.create_agent("executor", agent_id)
    
    # Execute task
    task_data = {
        "message": "Process this test message",
        "priority": "high",
        "context": {"user_id": "test_user"}
    }
    
    result = await lifecycle_manager.execute_agent_task(agent_id, task_data)
    
    # Verify result
    assert result is not None
    assert "status" in result
    
    # Verify state transitions
    final_state = lifecycle_manager.agent_states[agent_id]
    assert final_state.status == "completed"
    assert "result" in final_state.metadata
    assert "execution_time" in final_state.metadata
    
    # Verify execution history includes all transitions
    agent_events = [
        event for event in lifecycle_manager.execution_history 
        if event["agent_id"] == agent_id
    ]
    
    event_actions = [event["action"] for event in agent_events]
    assert "agent_created" in event_actions
    assert "task_executed" in event_actions
    
    # Verify state updates
    state_updates = [
        event for event in agent_events 
        if event["action"] == "state_updated"
    ]
    assert len(state_updates) >= 2  # running -> completed

@pytest.mark.asyncio
async def test_agent_state_persistence_and_recovery(lifecycle_manager):
    """Test that agent state persists and can be recovered."""
    agent_id = "test_persistent_001"
    
    # Create agent and execute task
    agent = await lifecycle_manager.create_agent("persistent", agent_id)
    
    task_data = {"message": "persistence test"}
    await lifecycle_manager.execute_agent_task(agent_id, task_data)
    
    # Get current state
    original_state = lifecycle_manager.agent_states[agent_id]
    
    # Simulate state recovery (reload from persistence)
    recovered_state = await lifecycle_manager.state_manager.load_state(agent_id)
    
    # Verify state persistence
    assert recovered_state is not None
    assert recovered_state.agent_id == original_state.agent_id
    assert recovered_state.agent_type == original_state.agent_type
    assert recovered_state.status == original_state.status
    
    # Verify metadata preservation
    assert "result" in recovered_state.metadata
    assert "execution_time" in recovered_state.metadata

@pytest.mark.asyncio
async def test_agent_error_handling_and_recovery(lifecycle_manager):
    """Test agent error handling and state management during failures."""
    agent_id = "test_error_001"
    
    # Create agent
    agent = await lifecycle_manager.create_agent("error_test", agent_id)
    
    # Simulate task that causes error
    with patch.object(lifecycle_manager, 'execute_agent_task', 
                     side_effect=Exception("Simulated task failure")):
        
        try:
            task_data = {"message": "failing task"}
            await lifecycle_manager.execute_agent_task(agent_id, task_data)
        except Exception:
            pass  # Expected to fail
    
    # Verify error state recorded
    error_events = [
        event for event in lifecycle_manager.execution_history
        if event["action"] == "task_failed" and event["agent_id"] == agent_id
    ]
    assert len(error_events) > 0
    
    # Verify agent can recover after error
    recovery_task = {"message": "recovery task"}
    
    # Reset task execution to normal behavior
    with patch.object(BaseSubAgent, 'process_message', return_value={"status": "recovered"}):
        result = await lifecycle_manager.execute_agent_task(agent_id, recovery_task)
        assert result["status"] == "recovered"

@pytest.mark.asyncio
async def test_concurrent_agent_management(lifecycle_manager):
    """Test managing multiple agents concurrently."""
    num_agents = 5
    agent_ids = [f"concurrent_agent_{i}" for i in range(num_agents)]
    
    # Create multiple agents concurrently
    create_tasks = [
        lifecycle_manager.create_agent("concurrent", agent_id)
        for agent_id in agent_ids
    ]
    
    agents = await asyncio.gather(*create_tasks)
    assert len(agents) == num_agents
    
    # Execute tasks concurrently
    task_data = {"message": "concurrent execution test"}
    execution_tasks = [
        lifecycle_manager.execute_agent_task(agent_id, task_data)
        for agent_id in agent_ids
    ]
    
    results = await asyncio.gather(*execution_tasks)
    assert len(results) == num_agents
    
    # Verify all agents completed successfully
    for agent_id in agent_ids:
        state = lifecycle_manager.agent_states[agent_id]
        assert state.status == "completed"
    
    # Clean up all agents
    cleanup_tasks = [
        lifecycle_manager.cleanup_agent(agent_id)
        for agent_id in agent_ids
    ]
    
    cleanup_results = await asyncio.gather(*cleanup_tasks)
    assert all(cleanup_results)
    
    # Verify agents cleaned up
    assert len(lifecycle_manager.active_agents) == 0

@pytest.mark.asyncio
async def test_agent_performance_metrics(lifecycle_manager):
    """Test agent performance tracking and metrics collection."""
    # Create and run multiple agents with varying loads
    performance_agents = []
    
    for i in range(3):
        agent_id = f"perf_agent_{i}"
        agent = await lifecycle_manager.create_agent("performance", agent_id)
        performance_agents.append(agent_id)
        
        # Execute task with different complexities
        task_data = {"message": f"performance test {i}", "complexity": i + 1}
        await lifecycle_manager.execute_agent_task(agent_id, task_data)
    
    # Get performance metrics
    metrics = await lifecycle_manager.get_agent_metrics()
    
    # Verify metrics structure
    assert "total_agents_created" in metrics
    assert "active_agents" in metrics  
    assert "average_execution_time" in metrics
    assert "status_distribution" in metrics
    
    # Verify metrics values
    assert metrics["total_agents_created"] >= 3
    assert metrics["active_agents"] == 3
    assert metrics["average_execution_time"] > 0
    assert "completed" in metrics["status_distribution"]
    assert metrics["status_distribution"]["completed"] >= 3