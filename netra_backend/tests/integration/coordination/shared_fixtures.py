"""
Shared Fixtures for Multi-Agent Coordination Integration Tests

This module provides test fixtures and utilities for testing agent coordination
functionality across the Netra platform.

BVJ:
- Segment: Platform/Internal - Test Infrastructure  
- Business Goal: Development Velocity & Platform Stability
- Value Impact: Enables reliable coordination testing across agent workflows
- Strategic Impact: Prevents cascade failures in multi-agent operations
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class CoordinationTestAgent:
    """Mock agent for coordination testing."""
    agent_id: str
    agent_type: str
    status: str = "idle"
    capabilities: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Mock agent execution."""
        await asyncio.sleep(0.1)  # Simulate processing
        return {
            "agent_id": self.agent_id,
            "task_id": task.get("id"),
            "status": "completed",
            "result": f"Processed by {self.agent_type}"
        }
    
    async def communicate(self, message: Dict[str, Any], target_agent: str) -> bool:
        """Mock inter-agent communication."""
        await asyncio.sleep(0.05)  # Simulate network latency
        logger.debug(f"Agent {self.agent_id} sent message to {target_agent}")
        return True


class CoordinationTestRegistry:
    """Mock registry for coordination testing."""
    
    def __init__(self):
        self.agents: Dict[str, CoordinationTestAgent] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.communication_log: List[Dict[str, Any]] = []
    
    def register_agent(self, agent: CoordinationTestAgent) -> bool:
        """Register an agent in the test registry."""
        self.agents[agent.agent_id] = agent
        logger.debug(f"Registered agent {agent.agent_id} of type {agent.agent_type}")
        return True
    
    def get_agent(self, agent_id: str) -> Optional[CoordinationTestAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[CoordinationTestAgent]:
        """List all registered agents."""
        return list(self.agents.values())
    
    async def coordinate_workflow(self, workflow_id: str, agents: List[str]) -> Dict[str, Any]:
        """Coordinate a workflow across multiple agents."""
        workflow_result = {
            "workflow_id": workflow_id,
            "participating_agents": agents,
            "status": "completed",
            "results": []
        }
        
        for agent_id in agents:
            agent = self.get_agent(agent_id)
            if agent:
                task = {"id": f"task_{uuid.uuid4().hex[:8]}", "workflow_id": workflow_id}
                result = await agent.execute(task)
                workflow_result["results"].append(result)
        
        self.workflows[workflow_id] = workflow_result
        return workflow_result
    
    def log_communication(self, from_agent: str, to_agent: str, message: Dict[str, Any]):
        """Log inter-agent communication."""
        comm_entry = {
            "timestamp": asyncio.get_event_loop().time(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message
        }
        self.communication_log.append(comm_entry)


class CoordinationTestInfrastructure:
    """Test infrastructure for coordination scenarios."""
    
    def __init__(self):
        self.registry = CoordinationTestRegistry()
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.metrics: Dict[str, Any] = {
            "total_agents": 0,
            "total_workflows": 0,
            "total_communications": 0,
            "avg_workflow_time": 0.0
        }
    
    async def setup_test_agents(self, agent_configs: List[Dict[str, Any]]) -> List[CoordinationTestAgent]:
        """Set up multiple test agents for coordination testing."""
        agents = []
        
        for config in agent_configs:
            agent = CoordinationTestAgent(
                agent_id=config.get("agent_id", f"agent_{uuid.uuid4().hex[:8]}"),
                agent_type=config.get("agent_type", "generic"),
                capabilities=config.get("capabilities", []),
                metadata=config.get("metadata", {})
            )
            
            self.registry.register_agent(agent)
            agents.append(agent)
        
        self.metrics["total_agents"] = len(self.registry.agents)
        return agents
    
    async def execute_coordination_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a coordination test scenario."""
        scenario_id = scenario.get("id", f"scenario_{uuid.uuid4().hex[:8]}")
        agents = scenario.get("agents", [])
        workflow_steps = scenario.get("workflow_steps", [])
        
        scenario_result = {
            "scenario_id": scenario_id,
            "status": "running",
            "step_results": [],
            "total_time": 0.0
        }
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            for step in workflow_steps:
                step_result = await self.registry.coordinate_workflow(
                    workflow_id=f"{scenario_id}_step_{len(scenario_result['step_results'])}",
                    agents=agents
                )
                scenario_result["step_results"].append(step_result)
            
            scenario_result["status"] = "completed"
            
        except Exception as e:
            scenario_result["status"] = "failed"
            scenario_result["error"] = str(e)
        
        end_time = asyncio.get_event_loop().time()
        scenario_result["total_time"] = end_time - start_time
        
        self.metrics["total_workflows"] += 1
        self.metrics["total_communications"] = len(self.registry.communication_log)
        
        return scenario_result
    
    def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get coordination test metrics."""
        return self.metrics.copy()
    
    async def cleanup(self):
        """Clean up test infrastructure."""
        self.registry.agents.clear()
        self.registry.workflows.clear()
        self.registry.communication_log.clear()
        self.active_workflows.clear()
        self.metrics = {
            "total_agents": 0,
            "total_workflows": 0, 
            "total_communications": 0,
            "avg_workflow_time": 0.0
        }


# Pytest fixtures
@pytest.fixture
async def coordination_infrastructure():
    """Pytest fixture for coordination test infrastructure."""
    infrastructure = CoordinationTestInfrastructure()
    yield infrastructure
    await infrastructure.cleanup()


@pytest.fixture
async def coordination_agents(coordination_infrastructure):
    """Pytest fixture for basic coordination test agents."""
    agent_configs = [
        {
            "agent_id": "test_agent_1",
            "agent_type": "coordinator",
            "capabilities": ["coordinate", "delegate"],
            "metadata": {"priority": "high"}
        },
        {
            "agent_id": "test_agent_2", 
            "agent_type": "worker",
            "capabilities": ["execute", "report"],
            "metadata": {"priority": "medium"}
        },
        {
            "agent_id": "test_agent_3",
            "agent_type": "worker", 
            "capabilities": ["execute", "validate"],
            "metadata": {"priority": "medium"}
        }
    ]
    
    agents = await coordination_infrastructure.setup_test_agents(agent_configs)
    return agents


__all__ = [
    "CoordinationTestAgent",
    "CoordinationTestRegistry",
    "CoordinationTestInfrastructure", 
    "coordination_infrastructure",
    "coordination_agents"
]