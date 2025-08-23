"""L3 Integration Test: Agent Failure Recovery Cascade

Business Value Justification (BVJ):
- Segment: Enterprise (reliability and resilience)
- Business Goal: Ensure system stability during agent failures
- Value Impact: Prevents cascading failures protecting $100K MRR
- Strategic Impact: Critical for enterprise reliability and customer trust

L3 Test: Uses real local services to validate cascading failure recovery.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.agents.supervisor.state_manager import AgentStateManager

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent

# Temporary stub for missing FailureRecoveryManager
class FailureRecoveryManager:
    def __init__(self, **kwargs):
        pass
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.database.postgres_service import PostgresService
from test_framework.testcontainers_utils import ContainerHelper

logger = logging.getLogger(__name__)

class L3FailureRecoveryManager:
    """Manages L3 failure recovery testing with real infrastructure."""
    
    def __init__(self):
        self.redis_client = None
        self.postgres_service = None
        self.state_manager: Optional[AgentStateManager] = None
        self.recovery_manager: Optional[FailureRecoveryManager] = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.agent_network: Dict[str, List[str]] = {}  # Dependencies
        self.failure_scenarios: List[Dict[str, Any]] = []
        self.recovery_metrics = {
            "failures_injected": 0,
            "recoveries_attempted": 0,
            "successful_recoveries": 0,
            "cascade_prevented": 0,
            "total_recovery_time": 0.0
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
        
        # Initialize state manager
        self.state_manager = AgentStateManager(
            redis_client=self.redis_client,
            postgres_service=self.postgres_service
        )
        
        # Initialize failure recovery manager
        self.recovery_manager = FailureRecoveryManager(
            state_manager=self.state_manager,
            redis_client=self.redis_client
        )
        
    async def create_agent_network(self, network_size: int = 5) -> Dict[str, Any]:
        """Create network of interconnected agents for failure testing."""
        agents = []
        
        # Create supervisor agent
        supervisor_id = f"supervisor_{uuid.uuid4().hex[:8]}"
        supervisor = SupervisorAgent(
            agent_id=supervisor_id,
            state_manager=self.state_manager,
            redis_client=self.redis_client
        )
        agents.append(supervisor)
        
        # Create sub-agents with dependencies
        sub_agents = []
        for i in range(network_size - 1):
            agent_id = f"subagent_{i}_{uuid.uuid4().hex[:6]}"
            agent = BaseSubAgent(
                agent_id=agent_id,
                agent_type=f"worker_agent",
                state_manager=self.state_manager,
                redis_client=self.redis_client
            )
            sub_agents.append(agent)
            agents.append(agent)
        
        # Set up dependency network
        self.agent_network[supervisor_id] = [agent.agent_id for agent in sub_agents]
        
        # Create cross-dependencies between sub-agents
        for i, agent in enumerate(sub_agents):
            dependencies = []
            # Each agent depends on 1-2 other agents
            dep_count = min(2, len(sub_agents) - 1)
            for j in range(dep_count):
                dep_idx = (i + j + 1) % len(sub_agents)
                if dep_idx != i:
                    dependencies.append(sub_agents[dep_idx].agent_id)
            self.agent_network[agent.agent_id] = dependencies
        
        # Initialize circuit breakers for each agent
        for agent in agents:
            self.circuit_breakers[agent.agent_id] = CircuitBreaker(
                failure_threshold=3,
                timeout=30.0,
                recovery_timeout=10.0
            )
        
        # Initialize agent states
        for agent in agents:
            initial_state = DeepAgentState(
                agent_id=agent.agent_id,
                agent_type=getattr(agent, 'agent_type', 'supervisor'),
                status="active",
                dependencies=self.agent_network.get(agent.agent_id, []),
                created_at=time.time()
            )
            await self.state_manager.save_state(agent.agent_id, initial_state)
        
        return {
            "network_size": len(agents),
            "supervisor_id": supervisor_id,
            "sub_agent_ids": [agent.agent_id for agent in sub_agents],
            "dependency_map": self.agent_network,
            "circuit_breakers_initialized": len(self.circuit_breakers)
        }
    
    async def inject_agent_failure(self, agent_id: str, failure_type: str = "crash") -> Dict[str, Any]:
        """Inject controlled failure into specific agent."""
        failure_start = time.time()
        
        try:
            # Record failure scenario
            scenario = {
                "agent_id": agent_id,
                "failure_type": failure_type,
                "timestamp": failure_start,
                "dependencies_affected": self.agent_network.get(agent_id, [])
            }
            self.failure_scenarios.append(scenario)
            
            # Update agent state to failed
            current_state = await self.state_manager.load_state(agent_id)
            if current_state:
                current_state.status = "failed"
                current_state.failure_reason = failure_type
                current_state.failed_at = failure_start
                await self.state_manager.save_state(agent_id, current_state)
            
            # Trigger circuit breaker
            circuit_breaker = self.circuit_breakers.get(agent_id)
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            self.recovery_metrics["failures_injected"] += 1
            
            return {
                "success": True,
                "agent_id": agent_id,
                "failure_type": failure_type,
                "affected_dependencies": len(scenario["dependencies_affected"]),
                "circuit_breaker_tripped": circuit_breaker.is_open() if circuit_breaker else False
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent_id": agent_id
            }
    
    async def execute_recovery_cascade(self, failed_agent_id: str) -> Dict[str, Any]:
        """Execute recovery cascade from failed agent."""
        recovery_start = time.time()
        
        try:
            self.recovery_metrics["recoveries_attempted"] += 1
            
            # Identify affected agents
            affected_agents = await self._identify_cascade_impact(failed_agent_id)
            
            # Execute recovery strategy
            recovery_plan = await self.recovery_manager.create_recovery_plan(
                failed_agent_id, affected_agents
            )
            
            # Execute recovery steps
            recovery_results = []
            
            # Step 1: Isolate failed agent
            isolation_result = await self._isolate_failed_agent(failed_agent_id)
            recovery_results.append(("isolation", isolation_result))
            
            # Step 2: Reroute dependencies
            reroute_result = await self._reroute_dependencies(failed_agent_id, affected_agents)
            recovery_results.append(("reroute", reroute_result))
            
            # Step 3: Spawn replacement agent if needed
            replacement_result = await self._spawn_replacement_agent(failed_agent_id)
            recovery_results.append(("replacement", replacement_result))
            
            # Step 4: Verify system stability
            stability_result = await self._verify_system_stability(affected_agents)
            recovery_results.append(("stability", stability_result))
            
            recovery_time = time.time() - recovery_start
            self.recovery_metrics["total_recovery_time"] += recovery_time
            
            # Check if cascade was prevented
            cascade_prevented = await self._check_cascade_prevention(affected_agents)
            if cascade_prevented:
                self.recovery_metrics["cascade_prevented"] += 1
            
            # Determine overall success
            all_steps_successful = all(result[1].get("success", False) for result in recovery_results)
            
            if all_steps_successful:
                self.recovery_metrics["successful_recoveries"] += 1
            
            return {
                "success": all_steps_successful,
                "failed_agent_id": failed_agent_id,
                "recovery_time": recovery_time,
                "affected_agents": len(affected_agents),
                "cascade_prevented": cascade_prevented,
                "recovery_steps": recovery_results,
                "recovery_plan": recovery_plan
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "recovery_time": time.time() - recovery_start
            }
    
    async def _identify_cascade_impact(self, failed_agent_id: str) -> List[str]:
        """Identify agents that could be affected by cascade failure."""
        affected = set()
        
        # Find agents that depend on the failed agent
        for agent_id, dependencies in self.agent_network.items():
            if failed_agent_id in dependencies:
                affected.add(agent_id)
        
        # Recursively find second-order effects
        to_check = list(affected)
        while to_check:
            checking_agent = to_check.pop()
            for agent_id, dependencies in self.agent_network.items():
                if checking_agent in dependencies and agent_id not in affected:
                    affected.add(agent_id)
                    to_check.append(agent_id)
        
        return list(affected)
    
    async def _isolate_failed_agent(self, agent_id: str) -> Dict[str, Any]:
        """Isolate failed agent to prevent cascade."""
        try:
            # Update state to isolated
            current_state = await self.state_manager.load_state(agent_id)
            if current_state:
                current_state.status = "isolated"
                current_state.isolated_at = time.time()
                await self.state_manager.save_state(agent_id, current_state)
            
            # Remove from active routing
            await self.recovery_manager.remove_from_routing(agent_id)
            
            return {"success": True, "agent_id": agent_id, "action": "isolated"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _reroute_dependencies(self, failed_agent_id: str, affected_agents: List[str]) -> Dict[str, Any]:
        """Reroute dependencies away from failed agent."""
        try:
            reroute_count = 0
            
            for agent_id in affected_agents:
                current_state = await self.state_manager.load_state(agent_id)
                if current_state and failed_agent_id in current_state.dependencies:
                    # Find alternative dependency
                    alternative = await self._find_alternative_dependency(failed_agent_id, agent_id)
                    if alternative:
                        current_state.dependencies.remove(failed_agent_id)
                        current_state.dependencies.append(alternative)
                        await self.state_manager.save_state(agent_id, current_state)
                        reroute_count += 1
            
            return {
                "success": True,
                "rerouted_dependencies": reroute_count,
                "affected_agents": len(affected_agents)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _find_alternative_dependency(self, failed_agent_id: str, requesting_agent_id: str) -> Optional[str]:
        """Find alternative healthy agent for dependency."""
        for agent_id, circuit_breaker in self.circuit_breakers.items():
            if (agent_id != failed_agent_id and 
                agent_id != requesting_agent_id and 
                not circuit_breaker.is_open()):
                return agent_id
        return None
    
    async def _spawn_replacement_agent(self, failed_agent_id: str) -> Dict[str, Any]:
        """Spawn replacement agent for failed agent."""
        try:
            # Get failed agent's configuration
            failed_state = await self.state_manager.load_state(failed_agent_id)
            if not failed_state:
                return {"success": False, "error": "Failed agent state not found"}
            
            # Create replacement agent
            replacement_id = f"replacement_{failed_agent_id}_{uuid.uuid4().hex[:6]}"
            replacement_agent = BaseSubAgent(
                agent_id=replacement_id,
                agent_type=failed_state.agent_type,
                state_manager=self.state_manager,
                redis_client=self.redis_client
            )
            
            # Initialize replacement state
            replacement_state = DeepAgentState(
                agent_id=replacement_id,
                agent_type=failed_state.agent_type,
                status="active",
                dependencies=failed_state.dependencies.copy(),
                replaces_agent=failed_agent_id,
                created_at=time.time()
            )
            await self.state_manager.save_state(replacement_id, replacement_state)
            
            # Update network mappings
            self.agent_network[replacement_id] = self.agent_network.get(failed_agent_id, [])
            self.circuit_breakers[replacement_id] = CircuitBreaker(
                failure_threshold=3, timeout=30.0, recovery_timeout=10.0
            )
            
            return {
                "success": True,
                "replacement_id": replacement_id,
                "replaces": failed_agent_id,
                "dependencies_inherited": len(replacement_state.dependencies)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _verify_system_stability(self, affected_agents: List[str]) -> Dict[str, Any]:
        """Verify system stability after recovery."""
        try:
            stable_agents = 0
            unstable_agents = []
            
            for agent_id in affected_agents:
                circuit_breaker = self.circuit_breakers.get(agent_id)
                agent_state = await self.state_manager.load_state(agent_id)
                
                is_stable = (
                    circuit_breaker and not circuit_breaker.is_open() and
                    agent_state and agent_state.status in ["active", "idle"]
                )
                
                if is_stable:
                    stable_agents += 1
                else:
                    unstable_agents.append(agent_id)
            
            stability_rate = stable_agents / len(affected_agents) if affected_agents else 1.0
            
            return {
                "success": stability_rate >= 0.8,  # 80% stability threshold
                "stability_rate": stability_rate,
                "stable_agents": stable_agents,
                "unstable_agents": unstable_agents,
                "total_checked": len(affected_agents)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_cascade_prevention(self, affected_agents: List[str]) -> bool:
        """Check if cascade failure was successfully prevented."""
        try:
            # Count agents that remained stable
            stable_count = 0
            for agent_id in affected_agents:
                agent_state = await self.state_manager.load_state(agent_id)
                if agent_state and agent_state.status not in ["failed", "crashed"]:
                    stable_count += 1
            
            # Cascade prevented if most agents remained stable
            return stable_count >= len(affected_agents) * 0.7  # 70% threshold
            
        except Exception:
            return False
    
    async def generate_recovery_report(self) -> Dict[str, Any]:
        """Generate comprehensive failure recovery report."""
        return {
            "recovery_summary": {
                "failures_injected": self.recovery_metrics["failures_injected"],
                "recoveries_attempted": self.recovery_metrics["recoveries_attempted"],
                "successful_recoveries": self.recovery_metrics["successful_recoveries"],
                "cascade_prevented": self.recovery_metrics["cascade_prevented"],
                "total_recovery_time": self.recovery_metrics["total_recovery_time"]
            },
            "recovery_rate": (
                self.recovery_metrics["successful_recoveries"] / 
                max(self.recovery_metrics["recoveries_attempted"], 1)
            ),
            "cascade_prevention_rate": (
                self.recovery_metrics["cascade_prevented"] / 
                max(self.recovery_metrics["failures_injected"], 1)
            ),
            "average_recovery_time": (
                self.recovery_metrics["total_recovery_time"] / 
                max(self.recovery_metrics["recoveries_attempted"], 1)
            ),
            "failure_scenarios": self.failure_scenarios,
            "network_topology": self.agent_network,
            "resilience_score": self._calculate_resilience_score()
        }
    
    def _calculate_resilience_score(self) -> float:
        """Calculate system resilience score."""
        if self.recovery_metrics["failures_injected"] == 0:
            return 1.0
        
        recovery_rate = (
            self.recovery_metrics["successful_recoveries"] / 
            self.recovery_metrics["recoveries_attempted"]
        ) if self.recovery_metrics["recoveries_attempted"] > 0 else 0
        
        cascade_prevention_rate = (
            self.recovery_metrics["cascade_prevented"] / 
            self.recovery_metrics["failures_injected"]
        )
        
        # Weight both factors equally
        return (recovery_rate + cascade_prevention_rate) / 2.0
    
    async def cleanup_l3_resources(self):
        """Clean up L3 test resources."""
        try:
            # Clean up circuit breakers
            for cb in self.circuit_breakers.values():
                if hasattr(cb, 'cleanup'):
                    await cb.cleanup()
            
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
    helper = ContainerHelper()
    
    # Start Redis container
    redis_container_instance = RedisContainer("redis:7-alpine")
    redis_container_instance.start()
    redis_url = f"redis://localhost:{redis_container_instance.get_exposed_port(6379)}"
    
    # Start Postgres container
    postgres_container_instance = PostgresContainer("postgres:15-alpine")
    postgres_container_instance.start()
    postgres_url = postgres_container_instance.get_connection_url()
    
    yield redis_url, postgres_url
    
    # Cleanup containers
    redis_container_instance.stop()
    postgres_container_instance.stop()

@pytest.fixture
async def l3_recovery_manager(testcontainer_infrastructure):
    """Create L3 recovery manager with real infrastructure."""
    redis_url, postgres_url = testcontainer_infrastructure
    
    manager = L3FailureRecoveryManager()
    await manager.initialize_l3_infrastructure(redis_url, postgres_url)
    
    yield manager
    
    await manager.cleanup_l3_resources()

@pytest.mark.L3
@pytest.mark.integration
class TestAgentFailureRecoveryCascadeL3:
    """L3 integration tests for agent failure recovery cascade."""
    
    async def test_single_agent_failure_recovery(self, l3_recovery_manager):
        """Test recovery from single agent failure."""
        # Create agent network
        network = await l3_recovery_manager.create_agent_network(4)
        
        # Select target agent for failure
        target_agent = network["sub_agent_ids"][0]
        
        # Inject failure
        failure_result = await l3_recovery_manager.inject_agent_failure(target_agent, "crash")
        assert failure_result["success"] is True
        assert failure_result["circuit_breaker_tripped"] is True
        
        # Execute recovery
        recovery_result = await l3_recovery_manager.execute_recovery_cascade(target_agent)
        
        # Verify recovery success
        assert recovery_result["success"] is True
        assert recovery_result["cascade_prevented"] is True
        assert recovery_result["recovery_time"] < 10.0
        assert recovery_result["affected_agents"] >= 1
        
        # Verify recovery steps
        recovery_steps = {step[0]: step[1] for step in recovery_result["recovery_steps"]}
        assert recovery_steps["isolation"]["success"] is True
        assert recovery_steps["replacement"]["success"] is True
        assert recovery_steps["stability"]["success"] is True
    
    async def test_cascade_failure_prevention(self, l3_recovery_manager):
        """Test prevention of cascading failures."""
        # Create larger network prone to cascades
        network = await l3_recovery_manager.create_agent_network(6)
        
        # Inject multiple failures to test cascade prevention
        failure_targets = network["sub_agent_ids"][:2]
        
        recovery_results = []
        for target_agent in failure_targets:
            # Inject failure
            await l3_recovery_manager.inject_agent_failure(target_agent, "network_partition")
            
            # Execute recovery
            recovery_result = await l3_recovery_manager.execute_recovery_cascade(target_agent)
            recovery_results.append(recovery_result)
        
        # Verify cascade prevention
        successful_recoveries = [r for r in recovery_results if r["success"]]
        assert len(successful_recoveries) == 2
        
        cascade_prevented = [r for r in recovery_results if r["cascade_prevented"]]
        assert len(cascade_prevented) >= 1  # At least one cascade prevented
        
        # Verify metrics
        assert l3_recovery_manager.recovery_metrics["cascade_prevented"] >= 1
        assert l3_recovery_manager.recovery_metrics["successful_recoveries"] >= 1
    
    async def test_concurrent_failure_recovery(self, l3_recovery_manager):
        """Test recovery from concurrent multiple failures."""
        # Create network
        network = await l3_recovery_manager.create_agent_network(5)
        
        # Inject concurrent failures
        failure_targets = network["sub_agent_ids"][:3]
        
        # Inject failures concurrently
        failure_tasks = [
            l3_recovery_manager.inject_agent_failure(agent_id, "memory_exhaustion")
            for agent_id in failure_targets
        ]
        failure_results = await asyncio.gather(*failure_tasks)
        
        # Verify all failures injected
        successful_failures = [r for r in failure_results if r["success"]]
        assert len(successful_failures) == 3
        
        # Execute concurrent recoveries
        recovery_tasks = [
            l3_recovery_manager.execute_recovery_cascade(agent_id)
            for agent_id in failure_targets
        ]
        recovery_results = await asyncio.gather(*recovery_tasks)
        
        # Verify concurrent recovery performance
        successful_recoveries = [r for r in recovery_results if r["success"]]
        assert len(successful_recoveries) >= 2  # Most should succeed
        
        # Verify reasonable performance under concurrent load
        max_recovery_time = max(r["recovery_time"] for r in recovery_results)
        assert max_recovery_time < 15.0
    
    async def test_system_stability_after_recovery(self, l3_recovery_manager):
        """Test system stability after multiple recovery cycles."""
        # Create network
        network = await l3_recovery_manager.create_agent_network(4)
        
        # Execute multiple failure-recovery cycles
        for cycle in range(3):
            target_agent = network["sub_agent_ids"][cycle % len(network["sub_agent_ids"])]
            
            # Inject failure
            await l3_recovery_manager.inject_agent_failure(target_agent, f"cycle_{cycle}_failure")
            
            # Execute recovery
            recovery_result = await l3_recovery_manager.execute_recovery_cascade(target_agent)
            
            # Verify recovery
            assert recovery_result["success"] is True
            
            # Small delay between cycles
            await asyncio.sleep(0.1)
        
        # Generate final report
        report = await l3_recovery_manager.generate_recovery_report()
        
        # Verify system resilience
        assert report["recovery_rate"] >= 0.8  # 80% recovery success rate
        assert report["cascade_prevention_rate"] >= 0.6  # 60% cascade prevention
        assert report["resilience_score"] >= 0.7  # High resilience score
        assert report["average_recovery_time"] < 5.0  # Fast recovery
    
    async def test_recovery_with_resource_constraints(self, l3_recovery_manager):
        """Test recovery under resource constraints."""
        # Create network
        network = await l3_recovery_manager.create_agent_network(3)
        
        # Simulate resource constraints by limiting replacement agents
        original_spawn_method = l3_recovery_manager._spawn_replacement_agent
        replacement_count = 0
        
        async def limited_spawn_replacement(agent_id: str):
            nonlocal replacement_count
            if replacement_count >= 1:  # Limit to 1 replacement
                return {"success": False, "error": "Resource limit exceeded"}
            replacement_count += 1
            return await original_spawn_method(agent_id)
        
        l3_recovery_manager._spawn_replacement_agent = limited_spawn_replacement
        
        try:
            # Inject failures
            failure_targets = network["sub_agent_ids"][:2]
            
            recovery_results = []
            for target_agent in failure_targets:
                await l3_recovery_manager.inject_agent_failure(target_agent, "resource_exhaustion")
                recovery_result = await l3_recovery_manager.execute_recovery_cascade(target_agent)
                recovery_results.append(recovery_result)
            
            # Verify graceful degradation
            # First recovery should succeed, second may fail replacement but should handle gracefully
            recovery_attempts = len([r for r in recovery_results if "recovery_steps" in r])
            assert recovery_attempts == 2
            
            # At least isolation and rerouting should work even with constraints
            for result in recovery_results:
                if "recovery_steps" in result:
                    steps = {step[0]: step[1] for step in result["recovery_steps"]}
                    assert steps["isolation"]["success"] is True
                    # Replacement may fail due to constraints, but other steps should work
        
        finally:
            l3_recovery_manager._spawn_replacement_agent = original_spawn_method