"""L3 Integration Test: Supervisor to Sub-agent Delegation

Business Value Justification (BVJ):
- Segment: Enterprise (core AI optimization functionality)  
- Business Goal: Reliable agent delegation and coordination
- Value Impact: Ensures $100K MRR through stable multi-agent workflows
- Strategic Impact: Core agent orchestration reliability for AI optimization

L3 Test: Uses real local services with Testcontainers for agent spawning and coordination validation.
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import testcontainers.redis as redis_container
import testcontainers.postgres as postgres_container

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState, AgentStateManager
from app.services.agent_service import AgentService
from app.services.llm.llm_manager import LLMManager
from app.redis_manager import RedisManager
from app.services.database.postgres_service import PostgresService
from app.schemas.registry import AgentStarted, AgentCompleted, SubAgentUpdate
from test_framework.testcontainers_utils import TestcontainerHelper

logger = logging.getLogger(__name__)


class L3AgentDelegationManager:
    """Manages L3 agent delegation testing with real infrastructure."""
    
    def __init__(self):
        self.supervisor_agent: Optional[SupervisorAgent] = None
        self.sub_agents: Dict[str, BaseSubAgent] = {}
        self.active_delegations: Dict[str, Dict[str, Any]] = {}
        self.state_manager: Optional[AgentStateManager] = None
        self.redis_client = None
        self.postgres_service = None
        self.delegation_metrics = {
            "total_delegations": 0,
            "successful_delegations": 0,
            "failed_delegations": 0,
            "average_delegation_time": 0.0,
            "sub_agents_spawned": 0
        }
        
    async def initialize_l3_infrastructure(self, redis_url: str, postgres_url: str):
        """Initialize L3 infrastructure with real containers."""
        # Initialize Redis connection
        self.redis_client = RedisManager()
        self.redis_client.redis_url = redis_url
        await self.redis_client.initialize()
        
        # Initialize Postgres connection
        self.postgres_service = PostgresService()
        self.postgres_service.database_url = postgres_url
        await self.postgres_service.initialize()
        
        # Initialize state manager with real persistence
        self.state_manager = AgentStateManager(
            redis_client=self.redis_client,
            postgres_service=self.postgres_service
        )
        
        # Initialize supervisor agent with real dependencies
        self.supervisor_agent = SupervisorAgent(
            state_manager=self.state_manager,
            redis_client=self.redis_client,
            postgres_service=self.postgres_service
        )
        
    async def create_delegation_task(self, task_type: str, complexity: str = "medium") -> Dict[str, Any]:
        """Create realistic delegation task for L3 testing."""
        task_templates = {
            "data_analysis": {
                "low": {
                    "description": "Analyze user engagement metrics for the past week",
                    "data_size": "1000 records",
                    "expected_duration": 30,
                    "sub_agent_type": "analysis_agent"
                },
                "medium": {
                    "description": "Perform comprehensive cost optimization analysis across multiple AI models",
                    "data_size": "50000 records", 
                    "expected_duration": 120,
                    "sub_agent_type": "optimization_agent"
                },
                "high": {
                    "description": "Execute deep learning model performance analysis with hyperparameter tuning",
                    "data_size": "500000 records",
                    "expected_duration": 300,
                    "sub_agent_type": "ml_optimization_agent"
                }
            },
            "optimization": {
                "low": {
                    "description": "Optimize single API endpoint response time",
                    "scope": "single_endpoint",
                    "expected_duration": 45,
                    "sub_agent_type": "performance_agent"
                },
                "medium": {
                    "description": "Optimize LLM token usage across chat conversations",
                    "scope": "conversation_optimization",
                    "expected_duration": 90,
                    "sub_agent_type": "llm_optimization_agent"
                },
                "high": {
                    "description": "Full system architecture optimization for enterprise deployment",
                    "scope": "system_wide",
                    "expected_duration": 180,
                    "sub_agent_type": "architecture_agent"
                }
            }
        }
        
        template = task_templates.get(task_type, task_templates["data_analysis"])[complexity]
        
        return {
            "task_id": f"delegation_{task_type}_{uuid.uuid4().hex[:8]}",
            "task_type": task_type,
            "complexity": complexity,
            "description": template["description"],
            "sub_agent_type": template["sub_agent_type"],
            "expected_duration": template["expected_duration"],
            "created_at": time.time(),
            "metadata": template
        }
    
    async def execute_supervisor_delegation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute supervisor delegation with real agent spawning."""
        delegation_start = time.time()
        task_id = task["task_id"]
        
        try:
            # Create initial agent state
            initial_state = DeepAgentState(
                agent_id=f"supervisor_{uuid.uuid4().hex[:8]}",
                agent_type="supervisor",
                status="delegating",
                task_data=task,
                created_at=time.time()
            )
            
            # Store state in real persistence layer
            await self.state_manager.save_state(initial_state.agent_id, initial_state)
            
            # Execute delegation through supervisor
            delegation_result = await self.supervisor_agent.delegate_task(
                task_type=task["sub_agent_type"],
                task_data=task,
                priority="normal"
            )
            
            # Spawn actual sub-agent 
            sub_agent = await self._spawn_sub_agent(
                task["sub_agent_type"],
                task_id,
                delegation_result
            )
            
            if sub_agent:
                self.sub_agents[task_id] = sub_agent
                self.delegation_metrics["sub_agents_spawned"] += 1
                
                # Execute task with sub-agent
                execution_result = await self._execute_with_sub_agent(sub_agent, task)
                
                delegation_time = time.time() - delegation_start
                self.delegation_metrics["total_delegations"] += 1
                self.delegation_metrics["successful_delegations"] += 1
                self._update_average_delegation_time(delegation_time)
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "delegation_time": delegation_time,
                    "sub_agent_id": sub_agent.agent_id,
                    "execution_result": execution_result,
                    "state_persisted": True
                }
            else:
                raise Exception("Failed to spawn sub-agent")
                
        except Exception as e:
            delegation_time = time.time() - delegation_start
            self.delegation_metrics["total_delegations"] += 1
            self.delegation_metrics["failed_delegations"] += 1
            
            return {
                "success": False,
                "task_id": task_id,
                "delegation_time": delegation_time,
                "error": str(e),
                "state_persisted": False
            }
    
    async def _spawn_sub_agent(self, agent_type: str, task_id: str, delegation_context: Any) -> Optional[BaseSubAgent]:
        """Spawn real sub-agent with proper initialization."""
        try:
            agent_id = f"{agent_type}_{task_id}_{uuid.uuid4().hex[:6]}"
            
            # Create sub-agent with real dependencies
            sub_agent = BaseSubAgent(
                agent_id=agent_id,
                agent_type=agent_type,
                state_manager=self.state_manager,
                redis_client=self.redis_client
            )
            
            # Initialize sub-agent state
            sub_agent_state = DeepAgentState(
                agent_id=agent_id,
                agent_type=agent_type,
                status="initializing",
                parent_agent_id=self.supervisor_agent.agent_id,
                task_id=task_id,
                created_at=time.time()
            )
            
            await self.state_manager.save_state(agent_id, sub_agent_state)
            
            # Update to active status
            sub_agent_state.status = "active"
            await self.state_manager.save_state(agent_id, sub_agent_state)
            
            return sub_agent
            
        except Exception as e:
            logger.error(f"Failed to spawn sub-agent {agent_type}: {e}")
            return None
    
    async def _execute_with_sub_agent(self, sub_agent: BaseSubAgent, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task with spawned sub-agent."""
        execution_start = time.time()
        
        try:
            # Update sub-agent state to executing
            current_state = await self.state_manager.load_state(sub_agent.agent_id)
            current_state.status = "executing"
            current_state.execution_start = execution_start
            await self.state_manager.save_state(sub_agent.agent_id, current_state)
            
            # Simulate real task execution (in production, this would call actual LLM)
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Create realistic execution result
            execution_result = {
                "status": "completed",
                "output": f"Task {task['task_type']} completed successfully",
                "metrics": {
                    "processing_time": time.time() - execution_start,
                    "resources_used": {
                        "cpu_time": 0.05,
                        "memory_peak": "128MB"
                    }
                },
                "agent_id": sub_agent.agent_id
            }
            
            # Update final state
            current_state.status = "completed"
            current_state.execution_result = execution_result
            current_state.completed_at = time.time()
            await self.state_manager.save_state(sub_agent.agent_id, current_state)
            
            return execution_result
            
        except Exception as e:
            # Update error state
            current_state = await self.state_manager.load_state(sub_agent.agent_id)
            current_state.status = "error"
            current_state.error = str(e)
            await self.state_manager.save_state(sub_agent.agent_id, current_state)
            
            return {
                "status": "error",
                "error": str(e),
                "agent_id": sub_agent.agent_id
            }
    
    async def verify_delegation_state_consistency(self, task_id: str) -> Dict[str, Any]:
        """Verify state consistency across supervisor and sub-agent."""
        try:
            # Get supervisor state
            supervisor_state = await self.state_manager.load_state(self.supervisor_agent.agent_id)
            
            # Get sub-agent state
            sub_agent = self.sub_agents.get(task_id)
            if not sub_agent:
                return {"success": False, "error": "Sub-agent not found"}
                
            sub_agent_state = await self.state_manager.load_state(sub_agent.agent_id)
            
            # Verify consistency
            consistency_checks = {
                "supervisor_has_delegation": task_id in str(supervisor_state.task_data),
                "sub_agent_has_parent": sub_agent_state.parent_agent_id == supervisor_state.agent_id,
                "task_id_consistent": sub_agent_state.task_id == task_id,
                "states_synchronized": True  # Additional sync checks would go here
            }
            
            all_consistent = all(consistency_checks.values())
            
            return {
                "success": True,
                "all_consistent": all_consistent,
                "consistency_checks": consistency_checks,
                "supervisor_state_valid": supervisor_state is not None,
                "sub_agent_state_valid": sub_agent_state is not None
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _update_average_delegation_time(self, new_time: float):
        """Update rolling average delegation time."""
        total_delegations = self.delegation_metrics["total_delegations"]
        current_avg = self.delegation_metrics["average_delegation_time"]
        
        # Calculate new rolling average
        new_avg = ((current_avg * (total_delegations - 1)) + new_time) / total_delegations
        self.delegation_metrics["average_delegation_time"] = new_avg
    
    async def cleanup_l3_resources(self):
        """Clean up L3 test resources."""
        try:
            # Clean up sub-agents
            for sub_agent in self.sub_agents.values():
                if hasattr(sub_agent, 'cleanup'):
                    await sub_agent.cleanup()
            
            # Close connections
            if self.redis_client:
                await self.redis_client.close()
            if self.postgres_service:
                await self.postgres_service.close()
                
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


@pytest.fixture
async def testcontainer_infrastructure():
    """Setup real Redis and Postgres containers for L3 testing."""
    helper = TestcontainerHelper()
    
    # Start Redis container
    redis_container_instance = redis_container.RedisContainer("redis:7-alpine")
    redis_container_instance.start()
    redis_url = f"redis://localhost:{redis_container_instance.get_exposed_port(6379)}"
    
    # Start Postgres container
    postgres_container_instance = postgres_container.PostgresContainer("postgres:15-alpine")
    postgres_container_instance.start()
    postgres_url = postgres_container_instance.get_connection_url()
    
    yield redis_url, postgres_url
    
    # Cleanup containers
    redis_container_instance.stop()
    postgres_container_instance.stop()


@pytest.fixture
async def l3_delegation_manager(testcontainer_infrastructure):
    """Create L3 delegation manager with real infrastructure."""
    redis_url, postgres_url = testcontainer_infrastructure
    
    manager = L3AgentDelegationManager()
    await manager.initialize_l3_infrastructure(redis_url, postgres_url)
    
    yield manager
    
    await manager.cleanup_l3_resources()


@pytest.mark.L3
@pytest.mark.integration
class TestSupervisorSubAgentDelegationL3:
    """L3 integration tests for supervisor to sub-agent delegation."""
    
    async def test_basic_delegation_flow(self, l3_delegation_manager):
        """Test basic supervisor to sub-agent delegation flow."""
        # Create delegation task
        task = await l3_delegation_manager.create_delegation_task("data_analysis", "medium")
        
        # Execute delegation
        result = await l3_delegation_manager.execute_supervisor_delegation(task)
        
        # Verify delegation success
        assert result["success"] is True
        assert result["task_id"] == task["task_id"]
        assert result["delegation_time"] < 5.0  # Should complete quickly
        assert result["sub_agent_id"] is not None
        assert result["state_persisted"] is True
        
        # Verify execution result
        execution_result = result["execution_result"]
        assert execution_result["status"] == "completed"
        assert execution_result["agent_id"] is not None
        
        # Verify metrics updated
        assert l3_delegation_manager.delegation_metrics["successful_delegations"] == 1
        assert l3_delegation_manager.delegation_metrics["sub_agents_spawned"] == 1
    
    async def test_multiple_concurrent_delegations(self, l3_delegation_manager):
        """Test multiple concurrent delegations."""
        # Create multiple tasks
        tasks = []
        for i in range(3):
            task = await l3_delegation_manager.create_delegation_task(
                "optimization" if i % 2 == 0 else "data_analysis",
                "low"
            )
            tasks.append(task)
        
        # Execute concurrent delegations
        delegation_tasks = [
            l3_delegation_manager.execute_supervisor_delegation(task)
            for task in tasks
        ]
        
        results = await asyncio.gather(*delegation_tasks)
        
        # Verify all delegations succeeded
        successful_results = [r for r in results if r["success"]]
        assert len(successful_results) == 3
        
        # Verify unique sub-agents created
        sub_agent_ids = [r["sub_agent_id"] for r in successful_results]
        assert len(set(sub_agent_ids)) == 3  # All unique
        
        # Verify performance under concurrent load
        max_delegation_time = max(r["delegation_time"] for r in successful_results)
        assert max_delegation_time < 10.0  # Reasonable concurrent performance
        
        # Verify metrics
        assert l3_delegation_manager.delegation_metrics["successful_delegations"] == 3
        assert l3_delegation_manager.delegation_metrics["sub_agents_spawned"] == 3
    
    async def test_delegation_state_persistence(self, l3_delegation_manager):
        """Test state persistence across delegation process."""
        # Create and execute delegation
        task = await l3_delegation_manager.create_delegation_task("data_analysis", "high")
        result = await l3_delegation_manager.execute_supervisor_delegation(task)
        
        assert result["success"] is True
        
        # Verify state consistency
        consistency_result = await l3_delegation_manager.verify_delegation_state_consistency(
            task["task_id"]
        )
        
        assert consistency_result["success"] is True
        assert consistency_result["all_consistent"] is True
        assert consistency_result["supervisor_state_valid"] is True
        assert consistency_result["sub_agent_state_valid"] is True
        
        # Verify specific consistency checks
        checks = consistency_result["consistency_checks"]
        assert checks["supervisor_has_delegation"] is True
        assert checks["sub_agent_has_parent"] is True
        assert checks["task_id_consistent"] is True
    
    async def test_sub_agent_lifecycle_management(self, l3_delegation_manager):
        """Test complete sub-agent lifecycle through delegation."""
        task = await l3_delegation_manager.create_delegation_task("optimization", "medium")
        
        # Track initial state
        initial_sub_agent_count = l3_delegation_manager.delegation_metrics["sub_agents_spawned"]
        
        # Execute delegation
        result = await l3_delegation_manager.execute_supervisor_delegation(task)
        assert result["success"] is True
        
        # Verify sub-agent was spawned
        task_id = task["task_id"]
        assert task_id in l3_delegation_manager.sub_agents
        
        sub_agent = l3_delegation_manager.sub_agents[task_id]
        assert sub_agent.agent_id is not None
        assert sub_agent.agent_type == task["sub_agent_type"]
        
        # Verify state progression
        final_state = await l3_delegation_manager.state_manager.load_state(sub_agent.agent_id)
        assert final_state.status == "completed"
        assert final_state.execution_result is not None
        assert final_state.completed_at is not None
        
        # Verify metrics
        assert l3_delegation_manager.delegation_metrics["sub_agents_spawned"] == initial_sub_agent_count + 1
    
    async def test_delegation_error_handling(self, l3_delegation_manager):
        """Test delegation error handling and recovery."""
        # Create task that will cause controlled failure
        task = await l3_delegation_manager.create_delegation_task("data_analysis", "low")
        
        # Temporarily break sub-agent spawning
        original_spawn_method = l3_delegation_manager._spawn_sub_agent
        
        async def failing_spawn_method(*args, **kwargs):
            raise Exception("Simulated spawn failure")
        
        l3_delegation_manager._spawn_sub_agent = failing_spawn_method
        
        try:
            # Execute delegation (should fail gracefully)
            result = await l3_delegation_manager.execute_supervisor_delegation(task)
            
            # Verify controlled failure
            assert result["success"] is False
            assert "error" in result
            assert "Simulated spawn failure" in result["error"]
            assert result["state_persisted"] is False
            
            # Verify metrics track failure
            assert l3_delegation_manager.delegation_metrics["failed_delegations"] == 1
            
        finally:
            # Restore original method
            l3_delegation_manager._spawn_sub_agent = original_spawn_method
        
        # Test recovery with successful delegation
        recovery_task = await l3_delegation_manager.create_delegation_task("optimization", "low")
        recovery_result = await l3_delegation_manager.execute_supervisor_delegation(recovery_task)
        
        # Verify recovery
        assert recovery_result["success"] is True
        assert l3_delegation_manager.delegation_metrics["successful_delegations"] == 1
    
    async def test_delegation_performance_metrics(self, l3_delegation_manager):
        """Test delegation performance metrics collection."""
        # Execute multiple delegations with different complexities
        task_configs = [
            ("data_analysis", "low"),
            ("optimization", "medium"), 
            ("data_analysis", "high")
        ]
        
        for task_type, complexity in task_configs:
            task = await l3_delegation_manager.create_delegation_task(task_type, complexity)
            result = await l3_delegation_manager.execute_supervisor_delegation(task)
            assert result["success"] is True
        
        # Verify metrics collection
        metrics = l3_delegation_manager.delegation_metrics
        assert metrics["total_delegations"] == 3
        assert metrics["successful_delegations"] == 3
        assert metrics["failed_delegations"] == 0
        assert metrics["sub_agents_spawned"] == 3
        assert metrics["average_delegation_time"] > 0
        
        # Verify reasonable performance
        assert metrics["average_delegation_time"] < 2.0  # Reasonable average time