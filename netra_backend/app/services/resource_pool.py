"""Agent Resource Pool Service

Manages resource allocation and limits for agents.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentResourcePool:
    """Manages resource allocation and limits for agents."""
    
    def __init__(self, max_agents: int = 10, max_memory_mb: int = 512, max_cpu_percent: float = 80.0):
        """Initialize the resource pool."""
        self.max_agents = max_agents
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.allocated_agents: Dict[str, Dict[str, Any]] = {}
        self.pool_stats = {
            "total_allocations": 0,
            "current_agents": 0,
            "memory_usage_mb": 0,
            "cpu_usage_percent": 0.0
        }
        logger.info(f"AgentResourcePool initialized with limits: agents={max_agents}, memory={max_memory_mb}MB, cpu={max_cpu_percent}%")
    
    async def configure(self, max_agents: Optional[int] = None, max_memory_mb: Optional[int] = None, 
                       max_cpu_percent: Optional[float] = None) -> Dict[str, Any]:
        """Configure pool limits."""
        if max_agents is not None:
            self.max_agents = max_agents
        if max_memory_mb is not None:
            self.max_memory_mb = max_memory_mb
        if max_cpu_percent is not None:
            self.max_cpu_percent = max_cpu_percent
        
        logger.info(f"Pool reconfigured: agents={self.max_agents}, memory={self.max_memory_mb}MB")
        return {"success": True, "limits": await self.get_current_limits()}
    
    async def allocate_agent(self, allocation_request: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate resources for an agent."""
        agent_id = str(uuid4())
        
        # Check if we can allocate
        if len(self.allocated_agents) >= self.max_agents:
            return {
                "success": False,
                "agent_id": None,
                "reason": "Max agents limit reached"
            }
        
        # Simulate resource allocation
        estimated_memory = allocation_request.get("memory_mb", 64)
        if self.pool_stats["memory_usage_mb"] + estimated_memory > self.max_memory_mb:
            return {
                "success": False,
                "agent_id": None,
                "reason": "Memory limit would be exceeded"
            }
        
        # Allocate the agent
        self.allocated_agents[agent_id] = {
            "allocation_time": datetime.now(timezone.utc),
            "memory_mb": estimated_memory,
            "priority": allocation_request.get("priority", "normal")
        }
        
        self.pool_stats["total_allocations"] += 1
        self.pool_stats["current_agents"] = len(self.allocated_agents)
        self.pool_stats["memory_usage_mb"] += estimated_memory
        
        logger.debug(f"Allocated agent {agent_id}, current usage: {self.pool_stats}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "allocated_memory_mb": estimated_memory
        }
    
    async def release_agent(self, agent_id: str) -> Dict[str, Any]:
        """Release resources for an agent."""
        if agent_id not in self.allocated_agents:
            return {"success": False, "reason": "Agent not found"}
        
        agent_info = self.allocated_agents.pop(agent_id)
        self.pool_stats["current_agents"] = len(self.allocated_agents)
        self.pool_stats["memory_usage_mb"] -= agent_info["memory_mb"]
        
        logger.debug(f"Released agent {agent_id}")
        
        return {"success": True, "released_memory_mb": agent_info["memory_mb"]}
    
    async def get_current_limits(self) -> Dict[str, Any]:
        """Get current pool limits."""
        return {
            "max_agents": self.max_agents,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent
        }
    
    async def get_current_stats(self) -> Dict[str, Any]:
        """Get current pool statistics."""
        return self.pool_stats.copy()
    
    async def trigger_memory_cleanup(self) -> Dict[str, Any]:
        """Trigger memory cleanup process."""
        # Simulate cleanup by reducing memory usage slightly
        cleanup_amount = min(50, self.pool_stats["memory_usage_mb"] * 0.1)
        self.pool_stats["memory_usage_mb"] = max(0, self.pool_stats["memory_usage_mb"] - cleanup_amount)
        
        logger.info(f"Memory cleanup performed, freed {cleanup_amount}MB")
        
        return {
            "cleanup_performed": True,
            "memory_freed_mb": cleanup_amount
        }
    
    async def apply_cpu_throttling(self) -> Dict[str, Any]:
        """Apply CPU throttling to manage resource usage."""
        # Simulate CPU throttling
        self.pool_stats["cpu_usage_percent"] = min(self.max_cpu_percent * 0.8, self.pool_stats["cpu_usage_percent"])
        
        logger.info("CPU throttling applied")
        
        return {
            "throttling_applied": True,
            "new_cpu_limit": self.pool_stats["cpu_usage_percent"]
        }