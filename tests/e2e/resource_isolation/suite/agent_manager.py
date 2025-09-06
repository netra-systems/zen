"""
Tenant Agent Manager for Resource Isolation Testing

This module provides the TenantAgentManager class for managing
agent instances in resource isolation test scenarios.

Business Value Justification (BVJ):
- Segment: Internal/Platform stability
- Business Goal: Enable reliable multi-tenant testing
- Value Impact: Ensures proper resource isolation testing
- Revenue Impact: Protects multi-user system reliability
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from uuid import uuid4

from shared.isolated_environment import IsolatedEnvironment


logger = logging.getLogger(__name__)


@dataclass
class AgentInstance:
    """Represents an agent instance for testing."""
    id: str
    tenant_id: str
    status: str = "idle"
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    resources_used: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TenantContext:
    """Represents a tenant context for resource isolation."""
    tenant_id: str
    agents: Dict[str, AgentInstance] = field(default_factory=dict)
    resource_limits: Dict[str, float] = field(default_factory=dict)
    current_usage: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class TenantAgentManager:
    """
    Manages agent instances across multiple tenants for resource isolation testing.
    
    This class provides functionality to:
    - Create and manage agent instances per tenant
    - Track resource usage and isolation
    - Simulate multi-tenant agent workloads
    - Monitor resource boundaries and violations
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the tenant agent manager."""
        self.config = config or {}
        self.env = IsolatedEnvironment()
        
        # Tenant management
        self.tenants: Dict[str, TenantContext] = {}
        self.global_limits = {
            "max_agents_per_tenant": self.config.get("max_agents_per_tenant", 10),
            "max_memory_per_tenant": self.config.get("max_memory_per_tenant", 1024),  # MB
            "max_cpu_per_tenant": self.config.get("max_cpu_per_tenant", 2.0),  # CPU cores
        }
        
        # Tracking
        self.total_agents = 0
        self.active_agents: Set[str] = set()
        self.resource_violations: List[Dict[str, Any]] = []
        
        logger.info(f"TenantAgentManager initialized with limits: {self.global_limits}")
    
    def create_tenant(self, tenant_id: str, resource_limits: Optional[Dict[str, float]] = None) -> TenantContext:
        """Create a new tenant context."""
        if tenant_id in self.tenants:
            logger.warning(f"Tenant {tenant_id} already exists")
            return self.tenants[tenant_id]
        
        # Apply default limits if not specified
        limits = resource_limits or {}
        for key, default_value in self.global_limits.items():
            if key not in limits:
                limits[key] = default_value
        
        tenant = TenantContext(
            tenant_id=tenant_id,
            resource_limits=limits
        )
        
        self.tenants[tenant_id] = tenant
        logger.info(f"Created tenant {tenant_id} with limits: {limits}")
        return tenant
    
    def create_agent(self, tenant_id: str, agent_config: Optional[Dict[str, Any]] = None) -> AgentInstance:
        """Create a new agent instance for a tenant."""
        if tenant_id not in self.tenants:
            self.create_tenant(tenant_id)
        
        tenant = self.tenants[tenant_id]
        
        # Check tenant limits
        if len(tenant.agents) >= tenant.resource_limits.get("max_agents_per_tenant", 10):
            raise RuntimeError(f"Tenant {tenant_id} has reached maximum agent limit")
        
        # Create agent instance
        agent_id = str(uuid4())
        agent = AgentInstance(
            id=agent_id,
            tenant_id=tenant_id,
            status="created",
            metadata=agent_config or {}
        )
        
        # Initialize resource tracking
        agent.resources_used = {
            "memory_mb": 0.0,
            "cpu_usage": 0.0,
            "execution_time": 0.0,
            "requests_count": 0
        }
        
        # Add to tenant
        tenant.agents[agent_id] = agent
        self.active_agents.add(agent_id)
        self.total_agents += 1
        
        logger.info(f"Created agent {agent_id} for tenant {tenant_id}")
        return agent
    
    def start_agent(self, tenant_id: str, agent_id: str) -> bool:
        """Start an agent instance."""
        if tenant_id not in self.tenants:
            logger.error(f"Tenant {tenant_id} not found")
            return False
        
        tenant = self.tenants[tenant_id]
        if agent_id not in tenant.agents:
            logger.error(f"Agent {agent_id} not found in tenant {tenant_id}")
            return False
        
        agent = tenant.agents[agent_id]
        agent.status = "running"
        agent.last_activity = time.time()
        
        logger.info(f"Started agent {agent_id} for tenant {tenant_id}")
        return True
    
    def stop_agent(self, tenant_id: str, agent_id: str) -> bool:
        """Stop an agent instance."""
        if tenant_id not in self.tenants:
            logger.error(f"Tenant {tenant_id} not found")
            return False
        
        tenant = self.tenants[tenant_id]
        if agent_id not in tenant.agents:
            logger.error(f"Agent {agent_id} not found in tenant {tenant_id}")
            return False
        
        agent = tenant.agents[agent_id]
        agent.status = "stopped"
        agent.last_activity = time.time()
        
        if agent_id in self.active_agents:
            self.active_agents.remove(agent_id)
        
        logger.info(f"Stopped agent {agent_id} for tenant {tenant_id}")
        return True
    
    def update_agent_resources(self, tenant_id: str, agent_id: str, resources: Dict[str, float]) -> bool:
        """Update resource usage for an agent."""
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        if agent_id not in tenant.agents:
            return False
        
        agent = tenant.agents[agent_id]
        agent.resources_used.update(resources)
        agent.last_activity = time.time()
        
        # Update tenant totals
        for resource, value in resources.items():
            if resource in tenant.current_usage:
                tenant.current_usage[resource] += value - agent.resources_used.get(resource, 0)
            else:
                tenant.current_usage[resource] = value
        
        # Check for resource violations
        self._check_resource_violations(tenant_id)
        
        return True
    
    def get_tenant_stats(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a tenant."""
        if tenant_id not in self.tenants:
            return None
        
        tenant = self.tenants[tenant_id]
        
        return {
            "tenant_id": tenant_id,
            "total_agents": len(tenant.agents),
            "active_agents": len([a for a in tenant.agents.values() if a.status == "running"]),
            "resource_usage": tenant.current_usage.copy(),
            "resource_limits": tenant.resource_limits.copy(),
            "created_at": tenant.created_at,
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics across all tenants."""
        return {
            "total_tenants": len(self.tenants),
            "total_agents": self.total_agents,
            "active_agents": len(self.active_agents),
            "resource_violations": len(self.resource_violations),
            "tenants": {tid: self.get_tenant_stats(tid) for tid in self.tenants.keys()}
        }
    
    def cleanup_tenant(self, tenant_id: str) -> bool:
        """Clean up all resources for a tenant."""
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        
        # Stop all agents
        for agent_id in list(tenant.agents.keys()):
            self.stop_agent(tenant_id, agent_id)
        
        # Remove tenant
        del self.tenants[tenant_id]
        
        logger.info(f"Cleaned up tenant {tenant_id}")
        return True
    
    def cleanup_all(self):
        """Clean up all tenants and agents."""
        for tenant_id in list(self.tenants.keys()):
            self.cleanup_tenant(tenant_id)
        
        self.active_agents.clear()
        self.resource_violations.clear()
        self.total_agents = 0
        
        logger.info("Cleaned up all tenants and agents")
    
    def _check_resource_violations(self, tenant_id: str):
        """Check for resource limit violations."""
        tenant = self.tenants[tenant_id]
        
        for resource, usage in tenant.current_usage.items():
            limit_key = f"max_{resource}"
            if limit_key in tenant.resource_limits:
                limit = tenant.resource_limits[limit_key]
                if usage > limit:
                    violation = {
                        "tenant_id": tenant_id,
                        "resource": resource,
                        "usage": usage,
                        "limit": limit,
                        "timestamp": time.time(),
                        "severity": "warning" if usage < limit * 1.2 else "error"
                    }
                    self.resource_violations.append(violation)
                    logger.warning(f"Resource violation detected: {violation}")
    
    async def simulate_workload(self, tenant_id: str, agent_count: int, duration_seconds: float = 60.0) -> Dict[str, Any]:
        """Simulate a workload for testing purposes."""
        results = {
            "tenant_id": tenant_id,
            "agents_created": 0,
            "agents_started": 0,
            "simulation_duration": duration_seconds,
            "start_time": time.time(),
            "errors": []
        }
        
        try:
            # Create tenant if it doesn't exist
            if tenant_id not in self.tenants:
                self.create_tenant(tenant_id)
            
            # Create agents
            agents = []
            for i in range(agent_count):
                try:
                    agent = self.create_agent(tenant_id, {"workload_index": i})
                    agents.append(agent)
                    results["agents_created"] += 1
                except Exception as e:
                    results["errors"].append(f"Failed to create agent {i}: {str(e)}")
            
            # Start agents
            for agent in agents:
                try:
                    if self.start_agent(tenant_id, agent.id):
                        results["agents_started"] += 1
                except Exception as e:
                    results["errors"].append(f"Failed to start agent {agent.id}: {str(e)}")
            
            # Simulate activity
            end_time = time.time() + duration_seconds
            while time.time() < end_time:
                for agent in agents:
                    # Simulate resource usage
                    if agent.status == "running":
                        simulated_resources = {
                            "memory_mb": agent.resources_used.get("memory_mb", 0) + 0.1,
                            "cpu_usage": min(1.0, agent.resources_used.get("cpu_usage", 0) + 0.01),
                            "requests_count": agent.resources_used.get("requests_count", 0) + 1
                        }
                        self.update_agent_resources(tenant_id, agent.id, simulated_resources)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
            
            # Stop agents
            for agent in agents:
                self.stop_agent(tenant_id, agent.id)
            
        except Exception as e:
            results["errors"].append(f"Simulation error: {str(e)}")
        
        results["end_time"] = time.time()
        results["actual_duration"] = results["end_time"] - results["start_time"]
        
        return results