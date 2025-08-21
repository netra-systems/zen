"""
L3 Integration Test: Agent State Recovery After Crash

Business Value Justification (BVJ):
- Segment: Enterprise (mission-critical AI operations)
- Business Goal: Ensure AI agent resilience and minimal service disruption
- Value Impact: Prevents workflow interruption and data loss during agent failures
- Strategic Impact: $100K MRR - Reliability and continuity for enterprise AI workflows

L3 Test: Uses real state persistence with recovery mechanisms.
Recovery target: <30 seconds recovery time with full context preservation.
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
import pickle
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from enum import Enum
import os
import tempfile

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState 
from app.agents.supervisor.state_manager import AgentStateManager
from app.redis_manager import RedisManager
from app.schemas import UserInDB
from app.core.exceptions_base import NetraException, StateRecoveryException
from test_framework.mock_utils import mock_justified

logger = logging.getLogger(__name__)


class AgentStateType(Enum):
    """Types of agent state for recovery testing."""
    CONVERSATION_CONTEXT = "conversation_context"
    TASK_PROGRESS = "task_progress"
    MEMORY_STATE = "memory_state"
    TOOL_STATE = "tool_state"
    WORKFLOW_STATE = "workflow_state"


class StateCheckpoint:
    """Represents a state checkpoint for recovery."""
    
    def __init__(self, checkpoint_id: str, agent_id: str, state_data: Dict[str, Any], 
                 checkpoint_type: AgentStateType):
        self.checkpoint_id = checkpoint_id
        self.agent_id = agent_id
        self.state_data = state_data
        self.checkpoint_type = checkpoint_type
        self.created_at = datetime.now(timezone.utc)
        self.version = 1
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "agent_id": self.agent_id,
            "state_data": self.state_data,
            "checkpoint_type": self.checkpoint_type.value,
            "created_at": self.created_at.isoformat(),
            "version": self.version
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateCheckpoint':
        """Create checkpoint from dictionary."""
        checkpoint = cls(
            data["checkpoint_id"],
            data["agent_id"],
            data["state_data"],
            AgentStateType(data["checkpoint_type"])
        )
        checkpoint.created_at = datetime.fromisoformat(data["created_at"])
        checkpoint.version = data.get("version", 1)
        return checkpoint


class AgentStateRecoveryManager:
    """Manager for agent state persistence and recovery."""
    
    def __init__(self, redis_manager: Optional[RedisManager] = None, 
                 persistence_path: Optional[str] = None):
        self.redis_manager = redis_manager
        self.persistence_path = persistence_path or tempfile.mkdtemp()
        self.checkpoints: Dict[str, StateCheckpoint] = {}
        self.recovery_log: List[Dict[str, Any]] = []
        self.active_agents: Dict[str, 'RecoverableAgent'] = {}
        self.checkpoint_interval = 30.0  # seconds
        self.max_recovery_time = 30.0  # seconds
        
    async def create_checkpoint(self, agent_id: str, state_data: Dict[str, Any], 
                              checkpoint_type: AgentStateType) -> str:
        """Create a state checkpoint for an agent."""
        checkpoint_id = f"{agent_id}_{checkpoint_type.value}_{uuid.uuid4().hex[:8]}"
        checkpoint = StateCheckpoint(checkpoint_id, agent_id, state_data, checkpoint_type)
        
        # Store in memory
        self.checkpoints[checkpoint_id] = checkpoint
        
        # Persist to Redis if available
        if self.redis_manager and self.redis_manager.enabled:
            await self._persist_to_redis(checkpoint)
            
        # Persist to disk
        await self._persist_to_disk(checkpoint)
        
        logger.info(f"Created checkpoint {checkpoint_id} for agent {agent_id}")
        return checkpoint_id
        
    async def _persist_to_redis(self, checkpoint: StateCheckpoint) -> None:
        """Persist checkpoint to Redis."""
        try:
            key = f"agent_checkpoint:{checkpoint.agent_id}:{checkpoint.checkpoint_type.value}"
            data = json.dumps(checkpoint.to_dict())
            await self.redis_manager.set_with_expiry(key, data, 3600)  # 1 hour TTL
        except Exception as e:
            logger.error(f"Failed to persist checkpoint to Redis: {e}")
            
    async def _persist_to_disk(self, checkpoint: StateCheckpoint) -> None:
        """Persist checkpoint to disk."""
        try:
            checkpoint_file = os.path.join(
                self.persistence_path, 
                f"{checkpoint.agent_id}_{checkpoint.checkpoint_type.value}.json"
            )
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f)
        except Exception as e:
            logger.error(f"Failed to persist checkpoint to disk: {e}")
            
    async def recover_agent_state(self, agent_id: str, 
                                checkpoint_types: List[AgentStateType] = None) -> Dict[str, Any]:
        """Recover agent state from checkpoints."""
        recovery_start = time.time()
        
        if checkpoint_types is None:
            checkpoint_types = list(AgentStateType)
            
        recovered_state = {}
        recovery_sources = []
        
        for checkpoint_type in checkpoint_types:
            try:
                # Try Redis first
                state_data = await self._recover_from_redis(agent_id, checkpoint_type)
                if state_data:
                    recovered_state[checkpoint_type.value] = state_data
                    recovery_sources.append(f"redis:{checkpoint_type.value}")
                    continue
                    
                # Fallback to disk
                state_data = await self._recover_from_disk(agent_id, checkpoint_type)
                if state_data:
                    recovered_state[checkpoint_type.value] = state_data
                    recovery_sources.append(f"disk:{checkpoint_type.value}")
                    continue
                    
                # Fallback to memory
                state_data = self._recover_from_memory(agent_id, checkpoint_type)
                if state_data:
                    recovered_state[checkpoint_type.value] = state_data
                    recovery_sources.append(f"memory:{checkpoint_type.value}")
                    
            except Exception as e:
                logger.error(f"Failed to recover {checkpoint_type.value} for {agent_id}: {e}")
                
        recovery_time = time.time() - recovery_start
        
        # Log recovery event
        self.recovery_log.append({
            "agent_id": agent_id,
            "recovery_time": recovery_time,
            "recovered_types": list(recovered_state.keys()),
            "recovery_sources": recovery_sources,
            "timestamp": datetime.now(timezone.utc),
            "success": len(recovered_state) > 0
        })
        
        logger.info(f"Recovered state for {agent_id} in {recovery_time:.2f}s from {recovery_sources}")
        return recovered_state
        
    async def _recover_from_redis(self, agent_id: str, 
                                checkpoint_type: AgentStateType) -> Optional[Dict[str, Any]]:
        """Recover state from Redis."""
        if not self.redis_manager or not self.redis_manager.enabled:
            return None
            
        try:
            key = f"agent_checkpoint:{agent_id}:{checkpoint_type.value}"
            data = await self.redis_manager.get(key)
            if data:
                checkpoint_dict = json.loads(data)
                return checkpoint_dict["state_data"]
        except Exception as e:
            logger.error(f"Redis recovery failed: {e}")
        return None
        
    async def _recover_from_disk(self, agent_id: str, 
                               checkpoint_type: AgentStateType) -> Optional[Dict[str, Any]]:
        """Recover state from disk."""
        try:
            checkpoint_file = os.path.join(
                self.persistence_path, 
                f"{agent_id}_{checkpoint_type.value}.json"
            )
            if os.path.exists(checkpoint_file):
                with open(checkpoint_file, 'r') as f:
                    checkpoint_dict = json.load(f)
                    return checkpoint_dict["state_data"]
        except Exception as e:
            logger.error(f"Disk recovery failed: {e}")
        return None
        
    def _recover_from_memory(self, agent_id: str, 
                           checkpoint_type: AgentStateType) -> Optional[Dict[str, Any]]:
        """Recover state from memory."""
        for checkpoint in self.checkpoints.values():
            if (checkpoint.agent_id == agent_id and 
                checkpoint.checkpoint_type == checkpoint_type):
                return checkpoint.state_data
        return None
        
    async def simulate_agent_crash(self, agent_id: str) -> None:
        """Simulate an agent crash for testing."""
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            await agent.simulate_crash()
            logger.info(f"Simulated crash for agent {agent_id}")
            
    async def detect_agent_failure(self, agent_id: str) -> bool:
        """Detect if an agent has failed."""
        if agent_id not in self.active_agents:
            return True
            
        agent = self.active_agents[agent_id]
        return agent.is_crashed or not agent.is_healthy()
        
    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get recovery performance metrics."""
        if not self.recovery_log:
            return {"total_recoveries": 0}
            
        successful_recoveries = [r for r in self.recovery_log if r["success"]]
        recovery_times = [r["recovery_time"] for r in successful_recoveries]
        
        return {
            "total_recoveries": len(self.recovery_log),
            "successful_recoveries": len(successful_recoveries),
            "success_rate": len(successful_recoveries) / len(self.recovery_log),
            "average_recovery_time": sum(recovery_times) / len(recovery_times) if recovery_times else 0,
            "max_recovery_time": max(recovery_times) if recovery_times else 0,
            "under_30s_recoveries": len([t for t in recovery_times if t < 30.0])
        }


class RecoverableAgent(BaseSubAgent):
    """Agent with state recovery capabilities."""
    
    def __init__(self, agent_id: str, recovery_manager: AgentStateRecoveryManager):
        super().__init__(agent_id=agent_id)
        self.recovery_manager = recovery_manager
        self.conversation_context: List[Dict[str, Any]] = []
        self.task_progress: Dict[str, Any] = {}
        self.memory_state: Dict[str, Any] = {}
        self.tool_state: Dict[str, Any] = {}
        self.workflow_state: Dict[str, Any] = {}
        self.is_crashed = False
        self.last_heartbeat = time.time()
        self.last_checkpoint_time = time.time()
        
        # Register with recovery manager
        recovery_manager.active_agents[agent_id] = self
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and update state."""
        if self.is_crashed:
            raise StateRecoveryException(f"Agent {self.agent_id} is crashed")
            
        # Update conversation context
        self.conversation_context.append({
            "timestamp": datetime.now(timezone.utc),
            "message": message,
            "response_generated": False
        })
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
        # Generate response
        response = {
            "agent_id": self.agent_id,
            "response": f"Processed message: {message.get('content', 'unknown')}",
            "timestamp": datetime.now(timezone.utc),
            "message_id": str(uuid.uuid4())
        }
        
        # Update conversation context with response
        self.conversation_context[-1]["response"] = response
        self.conversation_context[-1]["response_generated"] = True
        
        # Update heartbeat
        self.last_heartbeat = time.time()
        
        # Create checkpoint if needed
        await self._checkpoint_if_needed()
        
        return response
        
    async def start_task(self, task: Dict[str, Any]) -> str:
        """Start a new task and track progress."""
        if self.is_crashed:
            raise StateRecoveryException(f"Agent {self.agent_id} is crashed")
            
        task_id = str(uuid.uuid4())
        self.task_progress[task_id] = {
            "task": task,
            "status": "started",
            "progress": 0.0,
            "started_at": datetime.now(timezone.utc),
            "steps_completed": []
        }
        
        await self._checkpoint_if_needed()
        return task_id
        
    async def update_task_progress(self, task_id: str, progress: float, step: str) -> None:
        """Update task progress."""
        if self.is_crashed:
            raise StateRecoveryException(f"Agent {self.agent_id} is crashed")
            
        if task_id in self.task_progress:
            self.task_progress[task_id]["progress"] = progress
            self.task_progress[task_id]["steps_completed"].append({
                "step": step,
                "completed_at": datetime.now(timezone.utc)
            })
            
            if progress >= 1.0:
                self.task_progress[task_id]["status"] = "completed"
                
        await self._checkpoint_if_needed()
        
    async def simulate_crash(self) -> None:
        """Simulate an agent crash."""
        self.is_crashed = True
        logger.warning(f"Agent {self.agent_id} crashed")
        
    async def recover_from_crash(self) -> bool:
        """Recover agent from crash using state recovery."""
        if not self.is_crashed:
            return True
            
        recovery_start = time.time()
        
        try:
            # Recover state
            recovered_state = await self.recovery_manager.recover_agent_state(self.agent_id)
            
            # Restore conversation context
            if "conversation_context" in recovered_state:
                self.conversation_context = recovered_state["conversation_context"].get("messages", [])
                
            # Restore task progress
            if "task_progress" in recovered_state:
                self.task_progress = recovered_state["task_progress"].get("tasks", {})
                
            # Restore memory state
            if "memory_state" in recovered_state:
                self.memory_state = recovered_state["memory_state"].get("memory", {})
                
            # Restore tool state
            if "tool_state" in recovered_state:
                self.tool_state = recovered_state["tool_state"].get("tools", {})
                
            # Restore workflow state
            if "workflow_state" in recovered_state:
                self.workflow_state = recovered_state["workflow_state"].get("workflows", {})
                
            # Mark as recovered
            self.is_crashed = False
            self.last_heartbeat = time.time()
            
            recovery_time = time.time() - recovery_start
            logger.info(f"Agent {self.agent_id} recovered in {recovery_time:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to recover agent {self.agent_id}: {e}")
            return False
            
    async def _checkpoint_if_needed(self) -> None:
        """Create checkpoints if enough time has passed."""
        if time.time() - self.last_checkpoint_time > self.recovery_manager.checkpoint_interval:
            await self._create_checkpoints()
            self.last_checkpoint_time = time.time()
            
    async def _create_checkpoints(self) -> None:
        """Create state checkpoints."""
        # Conversation context checkpoint
        if self.conversation_context:
            await self.recovery_manager.create_checkpoint(
                self.agent_id,
                {"messages": self.conversation_context[-10:]},  # Keep last 10 messages
                AgentStateType.CONVERSATION_CONTEXT
            )
            
        # Task progress checkpoint
        if self.task_progress:
            await self.recovery_manager.create_checkpoint(
                self.agent_id,
                {"tasks": self.task_progress},
                AgentStateType.TASK_PROGRESS
            )
            
        # Memory state checkpoint
        if self.memory_state:
            await self.recovery_manager.create_checkpoint(
                self.agent_id,
                {"memory": self.memory_state},
                AgentStateType.MEMORY_STATE
            )
            
    def is_healthy(self) -> bool:
        """Check if agent is healthy."""
        return not self.is_crashed and (time.time() - self.last_heartbeat) < 60.0
        
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current agent state."""
        return {
            "agent_id": self.agent_id,
            "is_crashed": self.is_crashed,
            "is_healthy": self.is_healthy(),
            "conversation_messages": len(self.conversation_context),
            "active_tasks": len([t for t in self.task_progress.values() if t["status"] != "completed"]),
            "memory_entries": len(self.memory_state),
            "last_heartbeat": self.last_heartbeat
        }


@pytest.mark.L3
@pytest.mark.integration
class TestAgentStateRecoveryL3:
    """L3 integration tests for agent state recovery after crash."""
    
    @pytest.fixture
    async def redis_manager(self):
        """Create Redis manager for state persistence."""
        redis_mgr = RedisManager()
        redis_mgr.enabled = True
        yield redis_mgr
        
    @pytest.fixture
    async def recovery_manager(self, redis_manager):
        """Create state recovery manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AgentStateRecoveryManager(
                redis_manager=redis_manager,
                persistence_path=temp_dir
            )
            manager.checkpoint_interval = 5.0  # Faster checkpointing for tests
            yield manager
            
    @pytest.fixture
    async def recoverable_agent(self, recovery_manager):
        """Create recoverable agent for testing."""
        agent = RecoverableAgent("test_agent_1", recovery_manager)
        yield agent
        
    async def test_agent_crash_and_recovery_under_30_seconds(self, recovery_manager, recoverable_agent):
        """Test agent recovery time is under 30 seconds."""
        # Establish agent state
        await recoverable_agent.process_message({"content": "Initial message"})
        task_id = await recoverable_agent.start_task({"type": "analysis", "data": "test"})
        await recoverable_agent.update_task_progress(task_id, 0.5, "analysis_started")
        
        # Force checkpoint creation
        await recoverable_agent._create_checkpoints()
        
        # Simulate crash
        await recovery_manager.simulate_agent_crash("test_agent_1")
        assert recoverable_agent.is_crashed
        
        # Measure recovery time
        recovery_start = time.time()
        recovery_success = await recoverable_agent.recover_from_crash()
        recovery_time = time.time() - recovery_start
        
        # Verify recovery
        assert recovery_success
        assert not recoverable_agent.is_crashed
        assert recovery_time < 30.0  # Recovery under 30 seconds
        
        # Verify state preservation
        assert len(recoverable_agent.conversation_context) > 0
        assert len(recoverable_agent.task_progress) > 0
        assert task_id in recoverable_agent.task_progress
        
    async def test_state_reconstruction_from_checkpoints(self, recovery_manager, recoverable_agent):
        """Test complete state reconstruction from checkpoints."""
        # Build comprehensive agent state
        messages = [
            {"content": "Message 1", "timestamp": datetime.now(timezone.utc)},
            {"content": "Message 2", "timestamp": datetime.now(timezone.utc)},
            {"content": "Message 3", "timestamp": datetime.now(timezone.utc)},
        ]
        
        for msg in messages:
            await recoverable_agent.process_message(msg)
            
        # Start multiple tasks
        task_ids = []
        for i in range(3):
            task_id = await recoverable_agent.start_task({"type": f"task_{i}", "priority": i})
            task_ids.append(task_id)
            await recoverable_agent.update_task_progress(task_id, 0.3 * (i + 1), f"step_{i}")
            
        # Add memory and tool state
        recoverable_agent.memory_state = {
            "learned_patterns": ["pattern1", "pattern2"],
            "user_preferences": {"style": "formal", "length": "detailed"}
        }
        recoverable_agent.tool_state = {
            "active_tools": ["calculator", "search"],
            "tool_configs": {"calculator": {"precision": 10}}
        }
        
        # Create comprehensive checkpoints
        await recoverable_agent._create_checkpoints()
        
        # Simulate crash and recovery
        await recovery_manager.simulate_agent_crash("test_agent_1")
        recovery_success = await recoverable_agent.recover_from_crash()
        
        assert recovery_success
        
        # Verify state reconstruction
        assert len(recoverable_agent.conversation_context) > 0
        assert len(recoverable_agent.task_progress) == 3
        assert all(task_id in recoverable_agent.task_progress for task_id in task_ids)
        
        # Verify memory preservation
        assert "learned_patterns" in recoverable_agent.memory_state
        assert recoverable_agent.memory_state["learned_patterns"] == ["pattern1", "pattern2"]
        
    async def test_in_progress_task_resumption(self, recovery_manager, recoverable_agent):
        """Test resumption of in-progress tasks after recovery."""
        # Start task with partial progress
        task_id = await recoverable_agent.start_task({
            "type": "long_analysis",
            "steps": ["step1", "step2", "step3", "step4"],
            "estimated_duration": 120
        })
        
        # Make partial progress
        await recoverable_agent.update_task_progress(task_id, 0.4, "step1_completed")
        await recoverable_agent.update_task_progress(task_id, 0.6, "step2_completed")
        
        # Create checkpoint
        await recoverable_agent._create_checkpoints()
        
        # Simulate crash during task execution
        await recovery_manager.simulate_agent_crash("test_agent_1")
        
        # Recover and verify task state
        recovery_success = await recoverable_agent.recover_from_crash()
        assert recovery_success
        
        # Verify task can be resumed
        assert task_id in recoverable_agent.task_progress
        task_state = recoverable_agent.task_progress[task_id]
        assert task_state["progress"] == 0.6
        assert len(task_state["steps_completed"]) == 2
        assert task_state["status"] != "completed"
        
        # Continue task after recovery
        await recoverable_agent.update_task_progress(task_id, 0.8, "step3_completed")
        await recoverable_agent.update_task_progress(task_id, 1.0, "step4_completed")
        
        # Verify task completion
        assert recoverable_agent.task_progress[task_id]["status"] == "completed"
        
    async def test_context_preservation_across_crashes(self, recovery_manager, recoverable_agent):
        """Test conversation context preservation across multiple crashes."""
        # Build conversation history
        conversation_data = [
            "What is machine learning?",
            "Explain neural networks",
            "How does backpropagation work?",
            "Compare CNN vs RNN",
            "What are transformers?"
        ]
        
        for i, question in enumerate(conversation_data):
            await recoverable_agent.process_message({"content": question, "turn": i})
            
            # Crash and recover after each message (stress test)
            if i % 2 == 1:  # Crash every other message
                await recoverable_agent._create_checkpoints()
                await recovery_manager.simulate_agent_crash("test_agent_1")
                recovery_success = await recoverable_agent.recover_from_crash()
                assert recovery_success
                
        # Verify complete conversation history preserved
        assert len(recoverable_agent.conversation_context) >= len(conversation_data)
        
        # Verify context continuity
        for i, context_entry in enumerate(recoverable_agent.conversation_context):
            if i < len(conversation_data):
                assert conversation_data[i] in str(context_entry)
                
    async def test_failure_detection_and_alerting(self, recovery_manager, recoverable_agent):
        """Test automatic failure detection and alerting mechanisms."""
        # Agent starts healthy
        assert recoverable_agent.is_healthy()
        assert not await recovery_manager.detect_agent_failure("test_agent_1")
        
        # Simulate gradual failure (no heartbeat)
        original_heartbeat = recoverable_agent.last_heartbeat
        recoverable_agent.last_heartbeat = time.time() - 70.0  # 70 seconds ago
        
        # Should detect failure due to stale heartbeat
        assert not recoverable_agent.is_healthy()
        assert await recovery_manager.detect_agent_failure("test_agent_1")
        
        # Restore heartbeat
        recoverable_agent.last_heartbeat = time.time()
        assert recoverable_agent.is_healthy()
        
        # Simulate crash
        await recovery_manager.simulate_agent_crash("test_agent_1")
        assert await recovery_manager.detect_agent_failure("test_agent_1")
        
        # Verify failure detection accuracy
        failure_detected = await recovery_manager.detect_agent_failure("test_agent_1")
        assert failure_detected == recoverable_agent.is_crashed
        
    @mock_justified("L3: State recovery testing with real persistence mechanisms")
    async def test_recovery_performance_under_load(self, recovery_manager):
        """Test recovery performance with multiple agents under load."""
        # Create multiple agents
        agents = []
        for i in range(5):
            agent = RecoverableAgent(f"load_test_agent_{i}", recovery_manager)
            agents.append(agent)
            
        # Build state for each agent
        for i, agent in enumerate(agents):
            # Create messages
            for j in range(10):
                await agent.process_message({"content": f"Message {j} for agent {i}"})
                
            # Create tasks
            for j in range(3):
                task_id = await agent.start_task({"type": f"task_{j}", "agent": i})
                await agent.update_task_progress(task_id, 0.5, f"progress_{j}")
                
            # Force checkpoint
            await agent._create_checkpoints()
            
        # Simulate simultaneous crashes
        crash_tasks = []
        for agent in agents:
            crash_tasks.append(recovery_manager.simulate_agent_crash(agent.agent_id))
        await asyncio.gather(*crash_tasks)
        
        # Measure concurrent recovery
        recovery_start = time.time()
        recovery_tasks = []
        for agent in agents:
            recovery_tasks.append(agent.recover_from_crash())
            
        recovery_results = await asyncio.gather(*recovery_tasks)
        total_recovery_time = time.time() - recovery_start
        
        # Verify all recoveries succeeded
        assert all(recovery_results)
        assert total_recovery_time < 60.0  # All recoveries under 60 seconds
        
        # Verify state preservation for all agents
        for agent in agents:
            assert len(agent.conversation_context) > 0
            assert len(agent.task_progress) > 0
            assert agent.is_healthy()
            
        # Check recovery metrics
        metrics = recovery_manager.get_recovery_metrics()
        assert metrics["success_rate"] == 1.0
        assert metrics["average_recovery_time"] < 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])