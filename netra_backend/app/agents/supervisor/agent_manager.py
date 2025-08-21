"""Agent Manager for Supervisor

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (workflow automation)
- Business Goal: Efficient multi-agent coordination and lifecycle management
- Value Impact: Enables scalable AI agent operations and resource optimization
- Strategic Impact: Core component for enterprise AI automation workflows

Manages agent lifecycle, coordination, and resource allocation.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentMetrics:
    """Agent performance metrics."""
    agent_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    memory_usage_mb: float = 0.0
    last_activity: Optional[datetime] = None
    
    def update_completion(self, execution_time: float) -> None:
        """Update metrics after task completion."""
        self.tasks_completed += 1
        self.total_execution_time += execution_time
        self.average_execution_time = self.total_execution_time / self.tasks_completed
        self.last_activity = datetime.now(timezone.utc)
    
    def update_failure(self) -> None:
        """Update metrics after task failure."""
        self.tasks_failed += 1
        self.last_activity = datetime.now(timezone.utc)


@dataclass
class AgentInfo:
    """Information about a managed agent."""
    agent_id: str
    agent_type: str
    status: AgentStatus
    created_at: datetime
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: AgentMetrics = field(default_factory=lambda: AgentMetrics(""))
    
    def __post_init__(self):
        """Initialize metrics with agent ID."""
        if not self.metrics.agent_id:
            self.metrics.agent_id = self.agent_id


class AgentManager:
    """Manages lifecycle and coordination of multiple agents."""
    
    def __init__(self, max_concurrent_agents: int = 10):
        """Initialize the agent manager."""
        self.max_concurrent_agents = max_concurrent_agents
        self._agents: Dict[str, AgentInfo] = {}
        self._agent_instances: Dict[str, Any] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def register_agent(self, agent_type: str, agent_instance: Any, 
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """Register a new agent instance."""
        async with self._lock:
            agent_id = f"agent_{uuid.uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)
            
            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_type,
                status=AgentStatus.IDLE,
                created_at=now,
                last_updated=now,
                metadata=metadata or {}
            )
            
            self._agents[agent_id] = agent_info
            self._agent_instances[agent_id] = agent_instance
            
            logger.info(f"Registered agent {agent_id} of type {agent_type}")
            return agent_id
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        async with self._lock:
            if agent_id not in self._agents:
                return False
            
            # Cancel running task if exists
            if agent_id in self._running_tasks:
                task = self._running_tasks[agent_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self._running_tasks[agent_id]
            
            # Remove agent
            del self._agents[agent_id]
            del self._agent_instances[agent_id]
            
            logger.info(f"Unregistered agent {agent_id}")
            return True
    
    async def start_agent_task(self, agent_id: str, task_data: Dict[str, Any]) -> bool:
        """Start a task on the specified agent."""
        async with self._lock:
            if agent_id not in self._agents:
                raise NetraException(f"Agent {agent_id} not found")
            
            agent_info = self._agents[agent_id]
            if agent_info.status != AgentStatus.IDLE:
                raise NetraException(f"Agent {agent_id} is not idle")
            
            if len(self._running_tasks) >= self.max_concurrent_agents:
                raise NetraException("Maximum concurrent agents reached")
            
            # Update agent status
            agent_info.status = AgentStatus.RUNNING
            agent_info.last_updated = datetime.now(timezone.utc)
            
            # Start the task
            agent_instance = self._agent_instances[agent_id]
            task = asyncio.create_task(self._execute_agent_task(agent_id, agent_instance, task_data))
            self._running_tasks[agent_id] = task
            
            logger.info(f"Started task on agent {agent_id}")
            return True
    
    async def stop_agent_task(self, agent_id: str) -> bool:
        """Stop a running task on the specified agent."""
        async with self._lock:
            if agent_id not in self._running_tasks:
                return False
            
            task = self._running_tasks[agent_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Update agent status
            if agent_id in self._agents:
                self._agents[agent_id].status = AgentStatus.CANCELLED
                self._agents[agent_id].last_updated = datetime.now(timezone.utc)
            
            del self._running_tasks[agent_id]
            logger.info(f"Stopped task on agent {agent_id}")
            return True
    
    async def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent."""
        async with self._lock:
            return self._agents.get(agent_id)
    
    async def list_agents(self, status_filter: Optional[AgentStatus] = None) -> List[AgentInfo]:
        """List all agents, optionally filtered by status."""
        async with self._lock:
            agents = list(self._agents.values())
            if status_filter:
                agents = [a for a in agents if a.status == status_filter]
            return agents
    
    async def get_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        """Get metrics for a specific agent."""
        async with self._lock:
            agent_info = self._agents.get(agent_id)
            return agent_info.metrics if agent_info else None
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide agent metrics."""
        async with self._lock:
            total_agents = len(self._agents)
            running_agents = len(self._running_tasks)
            idle_agents = len([a for a in self._agents.values() if a.status == AgentStatus.IDLE])
            
            total_completed = sum(a.metrics.tasks_completed for a in self._agents.values())
            total_failed = sum(a.metrics.tasks_failed for a in self._agents.values())
            
            return {
                "total_agents": total_agents,
                "running_agents": running_agents,
                "idle_agents": idle_agents,
                "total_tasks_completed": total_completed,
                "total_tasks_failed": total_failed,
                "success_rate": total_completed / (total_completed + total_failed) if (total_completed + total_failed) > 0 else 0.0
            }
    
    async def cleanup_completed_tasks(self) -> int:
        """Clean up completed tasks and return count cleaned."""
        async with self._lock:
            completed_tasks = [
                agent_id for agent_id, task in self._running_tasks.items()
                if task.done()
            ]
            
            for agent_id in completed_tasks:
                del self._running_tasks[agent_id]
                # Reset agent to idle if still registered
                if agent_id in self._agents:
                    self._agents[agent_id].status = AgentStatus.IDLE
                    self._agents[agent_id].last_updated = datetime.now(timezone.utc)
            
            logger.info(f"Cleaned up {len(completed_tasks)} completed tasks")
            return len(completed_tasks)
    
    async def _execute_agent_task(self, agent_id: str, agent_instance: Any, task_data: Dict[str, Any]) -> Any:
        """Execute a task on an agent instance."""
        start_time = datetime.now(timezone.utc)
        try:
            # Call the agent's execute method (assuming standard interface)
            if hasattr(agent_instance, 'execute'):
                result = await agent_instance.execute(task_data)
            else:
                result = await agent_instance.process(task_data)
            
            # Update metrics on success
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            if agent_id in self._agents:
                self._agents[agent_id].metrics.update_completion(execution_time)
                self._agents[agent_id].status = AgentStatus.COMPLETED
                self._agents[agent_id].last_updated = datetime.now(timezone.utc)
            
            return result
            
        except Exception as e:
            # Update metrics on failure
            if agent_id in self._agents:
                self._agents[agent_id].metrics.update_failure()
                self._agents[agent_id].status = AgentStatus.FAILED
                self._agents[agent_id].last_updated = datetime.now(timezone.utc)
            
            logger.error(f"Agent {agent_id} task failed: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the agent manager and cancel all running tasks."""
        async with self._lock:
            # Cancel all running tasks
            for task in self._running_tasks.values():
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete
            if self._running_tasks:
                await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
            
            # Clear all data
            self._running_tasks.clear()
            self._agents.clear()
            self._agent_instances.clear()
            
            logger.info("Agent manager shutdown complete")


# Global agent manager instance
agent_manager = AgentManager()