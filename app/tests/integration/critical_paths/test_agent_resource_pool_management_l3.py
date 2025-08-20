"""L3 Integration Test: Agent Resource Pool Management

Business Value Justification (BVJ):
- Segment: Enterprise (performance and cost optimization)
- Business Goal: Efficient resource utilization and cost control
- Value Impact: Optimizes $100K MRR through intelligent resource management
- Strategic Impact: Critical for scalable multi-agent operations

L3 Test: Uses real local services to validate agent resource pool management.
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import testcontainers.redis as redis_container
import testcontainers.postgres as postgres_container

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState, AgentStateManager
from app.services.resource_pool import AgentResourcePool
from app.services.resource_monitor import ResourceMonitor
from app.redis_manager import RedisManager
from app.services.database.postgres_service import PostgresService
from test_framework.testcontainers_utils import TestcontainerHelper

logger = logging.getLogger(__name__)


class L3ResourcePoolManager:
    """Manages L3 resource pool testing with real infrastructure."""
    
    def __init__(self):
        self.redis_client = None
        self.postgres_service = None
        self.state_manager: Optional[AgentStateManager] = None
        self.resource_pool: Optional[AgentResourcePool] = None
        self.resource_monitor: Optional[ResourceMonitor] = None
        self.active_agents: Dict[str, BaseSubAgent] = {}
        self.resource_allocations: Dict[str, Dict[str, Any]] = {}
        self.pool_metrics = {
            "agents_created": 0,
            "agents_destroyed": 0,
            "peak_memory_usage": 0,
            "peak_cpu_usage": 0.0,
            "resource_violations": 0,
            "pool_expansions": 0,
            "pool_contractions": 0
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
        
        # Initialize resource monitor
        self.resource_monitor = ResourceMonitor()
        await self.resource_monitor.start_monitoring()
        
        # Initialize resource pool with limits
        self.resource_pool = AgentResourcePool(
            max_agents=10,
            max_memory_mb=512,  # 512MB limit for testing
            max_cpu_percent=80.0,
            state_manager=self.state_manager,
            redis_client=self.redis_client
        )
        
    async def create_resource_limited_environment(self, pool_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create resource-limited environment for testing."""
        # Configure pool with specific limits
        await self.resource_pool.configure(
            max_agents=pool_config.get("max_agents", 5),
            max_memory_mb=pool_config.get("max_memory_mb", 256),
            max_cpu_percent=pool_config.get("max_cpu_percent", 60.0),
            cleanup_threshold=pool_config.get("cleanup_threshold", 0.8)
        )
        
        # Initialize resource tracking
        initial_stats = await self.resource_monitor.get_current_stats()
        
        return {
            "pool_configured": True,
            "max_agents": pool_config.get("max_agents", 5),
            "memory_limit_mb": pool_config.get("max_memory_mb", 256),
            "cpu_limit_percent": pool_config.get("max_cpu_percent", 60.0),
            "initial_memory_mb": initial_stats["memory_mb"],
            "initial_cpu_percent": initial_stats["cpu_percent"]
        }
    
    async def test_agent_allocation_within_limits(self, target_agent_count: int) -> Dict[str, Any]:
        """Test agent allocation respecting resource limits."""
        allocation_start = time.time()
        
        try:
            allocated_agents = []
            allocation_results = []
            
            for i in range(target_agent_count):
                # Request agent allocation
                allocation_request = {
                    "agent_type": "resource_test_agent",
                    "memory_requirement_mb": 32,  # 32MB per agent
                    "cpu_requirement_percent": 5.0,  # 5% CPU per agent
                    "priority": "normal"
                }
                
                allocation_result = await self.resource_pool.allocate_agent(allocation_request)
                allocation_results.append(allocation_result)
                
                if allocation_result["success"]:
                    agent_id = allocation_result["agent_id"]
                    
                    # Create actual agent
                    agent = BaseSubAgent(
                        agent_id=agent_id,
                        agent_type="resource_test_agent",
                        state_manager=self.state_manager,
                        redis_client=self.redis_client
                    )
                    
                    # Initialize agent state
                    agent_state = DeepAgentState(
                        agent_id=agent_id,
                        agent_type="resource_test_agent",
                        status="active",
                        resource_allocation=allocation_result["allocation"],
                        created_at=time.time()
                    )
                    await self.state_manager.save_state(agent_id, agent_state)
                    
                    self.active_agents[agent_id] = agent
                    self.resource_allocations[agent_id] = allocation_result["allocation"]
                    allocated_agents.append(agent_id)
                    
                    self.pool_metrics["agents_created"] += 1
                
                # Monitor resource usage
                current_stats = await self.resource_monitor.get_current_stats()
                self.pool_metrics["peak_memory_usage"] = max(
                    self.pool_metrics["peak_memory_usage"], 
                    current_stats["memory_mb"]
                )
                self.pool_metrics["peak_cpu_usage"] = max(
                    self.pool_metrics["peak_cpu_usage"], 
                    current_stats["cpu_percent"]
                )
            
            allocation_time = time.time() - allocation_start
            
            # Check for resource violations
            violations = await self._check_resource_violations()
            self.pool_metrics["resource_violations"] += len(violations)
            
            successful_allocations = len(allocated_agents)
            allocation_rate = successful_allocations / target_agent_count
            
            return {
                "success": True,
                "target_agents": target_agent_count,
                "allocated_agents": successful_allocations,
                "allocation_rate": allocation_rate,
                "allocation_time": allocation_time,
                "resource_violations": violations,
                "allocated_agent_ids": allocated_agents,
                "peak_memory_mb": self.pool_metrics["peak_memory_usage"],
                "peak_cpu_percent": self.pool_metrics["peak_cpu_usage"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "allocation_time": time.time() - allocation_start
            }
    
    async def test_resource_pool_scaling(self, load_pattern: List[int]) -> Dict[str, Any]:
        """Test resource pool scaling with varying load patterns."""
        scaling_start = time.time()
        scaling_events = []
        
        try:
            for phase, target_agents in enumerate(load_pattern):
                phase_start = time.time()
                
                current_agent_count = len(self.active_agents)
                
                if target_agents > current_agent_count:
                    # Scale up
                    agents_to_add = target_agents - current_agent_count
                    scale_result = await self.test_agent_allocation_within_limits(agents_to_add)
                    
                    if scale_result["allocation_rate"] > 0:
                        self.pool_metrics["pool_expansions"] += 1
                        
                    scaling_events.append({
                        "phase": phase,
                        "action": "scale_up",
                        "target_agents": target_agents,
                        "agents_added": scale_result.get("allocated_agents", 0),
                        "duration": time.time() - phase_start
                    })
                    
                elif target_agents < current_agent_count:
                    # Scale down
                    agents_to_remove = current_agent_count - target_agents
                    scale_result = await self._scale_down_agents(agents_to_remove)
                    
                    if scale_result["success"]:
                        self.pool_metrics["pool_contractions"] += 1
                    
                    scaling_events.append({
                        "phase": phase,
                        "action": "scale_down",
                        "target_agents": target_agents,
                        "agents_removed": scale_result.get("removed_agents", 0),
                        "duration": time.time() - phase_start
                    })
                
                # Monitor resources after scaling
                await asyncio.sleep(0.1)  # Brief pause for stabilization
                current_stats = await self.resource_monitor.get_current_stats()
                
                scaling_events[-1].update({
                    "memory_usage_mb": current_stats["memory_mb"],
                    "cpu_usage_percent": current_stats["cpu_percent"],
                    "active_agents": len(self.active_agents)
                })
            
            total_scaling_time = time.time() - scaling_start
            
            return {
                "success": True,
                "scaling_events": scaling_events,
                "total_scaling_time": total_scaling_time,
                "pool_expansions": self.pool_metrics["pool_expansions"],
                "pool_contractions": self.pool_metrics["pool_contractions"],
                "final_agent_count": len(self.active_agents)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "scaling_time": time.time() - scaling_start
            }
    
    async def _scale_down_agents(self, agents_to_remove: int) -> Dict[str, Any]:
        """Scale down by removing agents from pool."""
        try:
            removed_agents = []
            active_agent_ids = list(self.active_agents.keys())
            
            # Remove oldest agents first (FIFO)
            for i in range(min(agents_to_remove, len(active_agent_ids))):
                agent_id = active_agent_ids[i]
                
                # Cleanup agent
                if agent_id in self.active_agents:
                    agent = self.active_agents[agent_id]
                    if hasattr(agent, 'cleanup'):
                        await agent.cleanup()
                    
                    # Remove from tracking
                    del self.active_agents[agent_id]
                    if agent_id in self.resource_allocations:
                        del self.resource_allocations[agent_id]
                    
                    # Release resources in pool
                    await self.resource_pool.release_agent(agent_id)
                    
                    removed_agents.append(agent_id)
                    self.pool_metrics["agents_destroyed"] += 1
            
            return {
                "success": True,
                "removed_agents": len(removed_agents),
                "removed_agent_ids": removed_agents
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_memory_pressure_handling(self, memory_stress_mb: int) -> Dict[str, Any]:
        """Test resource pool behavior under memory pressure."""
        stress_start = time.time()
        
        try:
            # Create memory-intensive agents
            memory_per_agent = 64  # 64MB per agent
            target_agents = memory_stress_mb // memory_per_agent
            
            allocation_result = await self.test_agent_allocation_within_limits(target_agents)
            
            # Monitor memory usage
            peak_memory_stats = await self.resource_monitor.get_current_stats()
            
            # Test memory cleanup when limits exceeded
            cleanup_triggered = False
            if peak_memory_stats["memory_mb"] > (memory_stress_mb * 0.8):
                cleanup_result = await self.resource_pool.trigger_memory_cleanup()
                cleanup_triggered = cleanup_result.get("cleanup_performed", False)
            
            # Verify system stability after pressure
            stability_check = await self._verify_pool_stability()
            
            stress_time = time.time() - stress_start
            
            return {
                "success": True,
                "memory_stress_mb": memory_stress_mb,
                "target_agents": target_agents,
                "allocated_agents": allocation_result.get("allocated_agents", 0),
                "peak_memory_mb": peak_memory_stats["memory_mb"],
                "cleanup_triggered": cleanup_triggered,
                "system_stable": stability_check["stable"],
                "stress_duration": stress_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stress_duration": time.time() - stress_start
            }
    
    async def test_cpu_throttling(self, cpu_stress_percent: float) -> Dict[str, Any]:
        """Test CPU throttling and resource management."""
        throttle_start = time.time()
        
        try:
            # Create CPU-intensive agents
            cpu_per_agent = 10.0  # 10% CPU per agent
            target_agents = int(cpu_stress_percent / cpu_per_agent)
            
            # Allocate agents with high CPU requirements
            allocated_agents = []
            for i in range(target_agents):
                allocation_request = {
                    "agent_type": "cpu_intensive_agent",
                    "memory_requirement_mb": 16,
                    "cpu_requirement_percent": cpu_per_agent,
                    "priority": "high"
                }
                
                allocation_result = await self.resource_pool.allocate_agent(allocation_request)
                if allocation_result["success"]:
                    allocated_agents.append(allocation_result["agent_id"])
            
            # Monitor CPU usage
            cpu_stats = await self.resource_monitor.get_current_stats()
            
            # Test CPU throttling if limits exceeded
            throttling_applied = False
            if cpu_stats["cpu_percent"] > cpu_stress_percent:
                throttle_result = await self.resource_pool.apply_cpu_throttling()
                throttling_applied = throttle_result.get("throttling_applied", False)
            
            throttle_time = time.time() - throttle_start
            
            return {
                "success": True,
                "cpu_stress_percent": cpu_stress_percent,
                "target_agents": target_agents,
                "allocated_agents": len(allocated_agents),
                "peak_cpu_percent": cpu_stats["cpu_percent"],
                "throttling_applied": throttling_applied,
                "throttle_duration": throttle_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "throttle_duration": time.time() - throttle_start
            }
    
    async def _check_resource_violations(self) -> List[Dict[str, Any]]:
        """Check for resource limit violations."""
        violations = []
        
        try:
            current_stats = await self.resource_monitor.get_current_stats()
            pool_limits = await self.resource_pool.get_current_limits()
            
            # Check memory violations
            if current_stats["memory_mb"] > pool_limits["max_memory_mb"]:
                violations.append({
                    "type": "memory_violation",
                    "current_mb": current_stats["memory_mb"],
                    "limit_mb": pool_limits["max_memory_mb"],
                    "severity": "high" if current_stats["memory_mb"] > pool_limits["max_memory_mb"] * 1.2 else "medium"
                })
            
            # Check CPU violations
            if current_stats["cpu_percent"] > pool_limits["max_cpu_percent"]:
                violations.append({
                    "type": "cpu_violation",
                    "current_percent": current_stats["cpu_percent"],
                    "limit_percent": pool_limits["max_cpu_percent"],
                    "severity": "high" if current_stats["cpu_percent"] > pool_limits["max_cpu_percent"] * 1.2 else "medium"
                })
            
            # Check agent count violations
            if len(self.active_agents) > pool_limits["max_agents"]:
                violations.append({
                    "type": "agent_count_violation",
                    "current_count": len(self.active_agents),
                    "limit_count": pool_limits["max_agents"],
                    "severity": "medium"
                })
            
        except Exception as e:
            violations.append({"type": "check_error", "error": str(e)})
        
        return violations
    
    async def _verify_pool_stability(self) -> Dict[str, Any]:
        """Verify resource pool stability."""
        try:
            # Check resource usage is within acceptable bounds
            current_stats = await self.resource_monitor.get_current_stats()
            pool_limits = await self.resource_pool.get_current_limits()
            
            memory_utilization = current_stats["memory_mb"] / pool_limits["max_memory_mb"]
            cpu_utilization = current_stats["cpu_percent"] / pool_limits["max_cpu_percent"]
            
            # Stability criteria
            memory_stable = memory_utilization < 0.9  # Below 90% memory usage
            cpu_stable = cpu_utilization < 0.9  # Below 90% CPU usage
            agents_responsive = await self._check_agent_responsiveness()
            
            overall_stable = memory_stable and cpu_stable and agents_responsive
            
            return {
                "stable": overall_stable,
                "memory_stable": memory_stable,
                "cpu_stable": cpu_stable,
                "agents_responsive": agents_responsive,
                "memory_utilization": memory_utilization,
                "cpu_utilization": cpu_utilization
            }
            
        except Exception as e:
            return {"stable": False, "error": str(e)}
    
    async def _check_agent_responsiveness(self) -> bool:
        """Check if agents are still responsive."""
        try:
            responsive_count = 0
            total_agents = len(self.active_agents)
            
            if total_agents == 0:
                return True  # No agents to check
            
            # Check a sample of agents
            sample_size = min(3, total_agents)
            sample_agents = list(self.active_agents.values())[:sample_size]
            
            for agent in sample_agents:
                # Simple responsiveness check
                try:
                    state = await self.state_manager.load_state(agent.agent_id)
                    if state and state.status in ["active", "idle"]:
                        responsive_count += 1
                except Exception:
                    pass  # Agent not responsive
            
            return responsive_count >= (sample_size * 0.8)  # 80% responsive threshold
            
        except Exception:
            return False
    
    async def generate_resource_report(self) -> Dict[str, Any]:
        """Generate comprehensive resource management report."""
        current_stats = await self.resource_monitor.get_current_stats()
        
        return {
            "pool_metrics": self.pool_metrics,
            "current_resources": {
                "active_agents": len(self.active_agents),
                "memory_usage_mb": current_stats["memory_mb"],
                "cpu_usage_percent": current_stats["cpu_percent"]
            },
            "resource_efficiency": {
                "agent_creation_rate": self.pool_metrics["agents_created"] / max(1, time.time()),
                "resource_violation_rate": self.pool_metrics["resource_violations"] / max(1, self.pool_metrics["agents_created"]),
                "scaling_responsiveness": (self.pool_metrics["pool_expansions"] + self.pool_metrics["pool_contractions"]) / max(1, self.pool_metrics["agents_created"])
            },
            "allocations": dict(self.resource_allocations),
            "stability_score": await self._calculate_stability_score()
        }
    
    async def _calculate_stability_score(self) -> float:
        """Calculate resource pool stability score."""
        stability_check = await self._verify_pool_stability()
        
        if not stability_check["stable"]:
            return 0.0
        
        # Factor in efficiency metrics
        violation_rate = self.pool_metrics["resource_violations"] / max(1, self.pool_metrics["agents_created"])
        efficiency_score = max(0.0, 1.0 - violation_rate)
        
        # Factor in utilization efficiency
        memory_efficiency = min(1.0, stability_check["memory_utilization"])
        cpu_efficiency = min(1.0, stability_check["cpu_utilization"])
        
        return (efficiency_score + memory_efficiency + cpu_efficiency) / 3.0
    
    async def cleanup_l3_resources(self):
        """Clean up L3 test resources."""
        try:
            # Clean up all active agents
            for agent in self.active_agents.values():
                if hasattr(agent, 'cleanup'):
                    await agent.cleanup()
            
            # Stop resource monitoring
            if self.resource_monitor:
                await self.resource_monitor.stop_monitoring()
            
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
async def l3_resource_manager(testcontainer_infrastructure):
    """Create L3 resource manager with real infrastructure."""
    redis_url, postgres_url = testcontainer_infrastructure
    
    manager = L3ResourcePoolManager()
    await manager.initialize_l3_infrastructure(redis_url, postgres_url)
    
    yield manager
    
    await manager.cleanup_l3_resources()


@pytest.mark.L3
@pytest.mark.integration
class TestAgentResourcePoolManagementL3:
    """L3 integration tests for agent resource pool management."""
    
    async def test_basic_resource_allocation(self, l3_resource_manager):
        """Test basic agent resource allocation within limits."""
        # Configure resource pool
        pool_config = {
            "max_agents": 5,
            "max_memory_mb": 256,
            "max_cpu_percent": 50.0
        }
        
        environment = await l3_resource_manager.create_resource_limited_environment(pool_config)
        assert environment["pool_configured"] is True
        
        # Test allocation within limits
        allocation_result = await l3_resource_manager.test_agent_allocation_within_limits(3)
        
        # Verify allocation success
        assert allocation_result["success"] is True
        assert allocation_result["allocated_agents"] == 3
        assert allocation_result["allocation_rate"] == 1.0
        assert len(allocation_result["resource_violations"]) == 0
        assert allocation_result["allocation_time"] < 5.0
        
        # Verify resource usage within limits
        assert allocation_result["peak_memory_mb"] <= pool_config["max_memory_mb"]
        assert allocation_result["peak_cpu_percent"] <= pool_config["max_cpu_percent"]
    
    async def test_resource_limit_enforcement(self, l3_resource_manager):
        """Test enforcement of resource limits."""
        # Configure strict limits
        pool_config = {
            "max_agents": 3,
            "max_memory_mb": 128,
            "max_cpu_percent": 30.0
        }
        
        await l3_resource_manager.create_resource_limited_environment(pool_config)
        
        # Try to exceed agent limit
        allocation_result = await l3_resource_manager.test_agent_allocation_within_limits(5)
        
        # Should not allocate more than limit
        assert allocation_result["allocated_agents"] <= pool_config["max_agents"]
        
        # Should respect memory and CPU limits
        violations = allocation_result["resource_violations"]
        critical_violations = [v for v in violations if v.get("severity") == "high"]
        assert len(critical_violations) == 0  # No critical violations
    
    async def test_dynamic_pool_scaling(self, l3_resource_manager):
        """Test dynamic scaling of resource pool."""
        # Configure pool
        pool_config = {"max_agents": 8, "max_memory_mb": 384, "max_cpu_percent": 60.0}
        await l3_resource_manager.create_resource_limited_environment(pool_config)
        
        # Define scaling pattern: up, peak, down, baseline
        load_pattern = [2, 5, 3, 1]
        
        scaling_result = await l3_resource_manager.test_resource_pool_scaling(load_pattern)
        
        # Verify scaling success
        assert scaling_result["success"] is True
        assert scaling_result["pool_expansions"] >= 1
        assert scaling_result["pool_contractions"] >= 1
        assert scaling_result["total_scaling_time"] < 10.0
        
        # Verify final state
        assert scaling_result["final_agent_count"] == load_pattern[-1]
        
        # Verify scaling events
        events = scaling_result["scaling_events"]
        assert len(events) == len(load_pattern)
        
        # Check scaling performance
        max_scaling_duration = max(event["duration"] for event in events)
        assert max_scaling_duration < 3.0  # Individual scaling should be fast
    
    async def test_memory_pressure_handling(self, l3_resource_manager):
        """Test behavior under memory pressure."""
        # Configure memory-constrained environment
        pool_config = {"max_agents": 6, "max_memory_mb": 192, "max_cpu_percent": 50.0}
        await l3_resource_manager.create_resource_limited_environment(pool_config)
        
        # Apply memory stress
        stress_result = await l3_resource_manager.test_memory_pressure_handling(256)
        
        # Verify graceful handling
        assert stress_result["success"] is True
        assert stress_result["system_stable"] is True
        assert stress_result["stress_duration"] < 8.0
        
        # Should trigger cleanup if needed
        if stress_result["peak_memory_mb"] > 192 * 0.8:
            assert stress_result["cleanup_triggered"] is True
    
    async def test_cpu_throttling(self, l3_resource_manager):
        """Test CPU throttling under load."""
        # Configure CPU-constrained environment
        pool_config = {"max_agents": 5, "max_memory_mb": 256, "max_cpu_percent": 40.0}
        await l3_resource_manager.create_resource_limited_environment(pool_config)
        
        # Apply CPU stress
        throttle_result = await l3_resource_manager.test_cpu_throttling(60.0)
        
        # Verify throttling behavior
        assert throttle_result["success"] is True
        assert throttle_result["throttle_duration"] < 5.0
        
        # Should apply throttling if needed
        if throttle_result["peak_cpu_percent"] > 40.0:
            assert throttle_result["throttling_applied"] is True
    
    async def test_concurrent_resource_requests(self, l3_resource_manager):
        """Test concurrent resource allocation requests."""
        # Configure pool
        pool_config = {"max_agents": 6, "max_memory_mb": 256, "max_cpu_percent": 50.0}
        await l3_resource_manager.create_resource_limited_environment(pool_config)
        
        # Execute concurrent allocation requests
        allocation_tasks = [
            l3_resource_manager.test_agent_allocation_within_limits(2)
            for _ in range(3)
        ]
        
        allocation_results = await asyncio.gather(*allocation_tasks)
        
        # Verify concurrent handling
        successful_results = [r for r in allocation_results if r["success"]]
        assert len(successful_results) >= 2  # Most should succeed
        
        # Total allocated should respect limits
        total_allocated = sum(r["allocated_agents"] for r in successful_results)
        assert total_allocated <= pool_config["max_agents"]
        
        # Verify reasonable performance under concurrent load
        max_allocation_time = max(r["allocation_time"] for r in allocation_results)
        assert max_allocation_time < 8.0
    
    async def test_resource_efficiency_metrics(self, l3_resource_manager):
        """Test comprehensive resource efficiency metrics."""
        # Configure pool
        pool_config = {"max_agents": 5, "max_memory_mb": 256, "max_cpu_percent": 50.0}
        await l3_resource_manager.create_resource_limited_environment(pool_config)
        
        # Execute various operations
        await l3_resource_manager.test_agent_allocation_within_limits(3)
        await l3_resource_manager.test_resource_pool_scaling([3, 2, 4, 1])
        
        # Generate report
        report = await l3_resource_manager.generate_resource_report()
        
        # Verify report structure
        assert "pool_metrics" in report
        assert "current_resources" in report
        assert "resource_efficiency" in report
        assert "stability_score" in report
        
        # Verify metrics
        pool_metrics = report["pool_metrics"]
        assert pool_metrics["agents_created"] > 0
        assert pool_metrics["peak_memory_usage"] > 0
        
        # Verify efficiency
        efficiency = report["resource_efficiency"]
        assert efficiency["agent_creation_rate"] > 0
        assert efficiency["resource_violation_rate"] < 0.1  # Low violation rate
        
        # Verify stability
        assert report["stability_score"] >= 0.7  # High stability score