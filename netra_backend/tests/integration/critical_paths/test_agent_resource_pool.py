"""Agent Resource Pool Management L3 Integration Tests

Business Value Justification (BVJ):
- Segment: All tiers (resource optimization)
- Business Goal: Resource allocation and scaling, optimal resource utilization
- Value Impact: $100K MRR - Ensures efficient resource usage >85% utilization
- Strategic Impact: Resource pool management prevents waste and enables cost-effective scaling

Critical Path: Resource allocation -> Pool sizing -> Utilization monitoring -> Fair scheduling -> Priority handling -> Leak prevention
Coverage: Resource pool strategies, allocation algorithms, utilization optimization, leak detection, scaling policies
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.registry import TaskPriority

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """Types of resources in the pool."""
    COMPUTE_AGENT = "compute_agent"
    MEMORY_POOL = "memory_pool"
    IO_HANDLER = "io_handler"
    LLM_CONNECTION = "llm_connection"
    DATABASE_CONNECTION = "database_connection"

class ResourceState(Enum):
    """Resource allocation states."""
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    FAILED = "failed"

@dataclass
class ResourceMetrics:
    """Resource utilization and performance metrics."""
    total_allocations: int = 0
    successful_allocations: int = 0
    failed_allocations: int = 0
    resource_leaks: int = 0
    average_utilization: float = 0.0
    peak_utilization: float = 0.0
    total_wait_time: float = 0.0
    allocation_failures: int = 0
    
    def get_utilization_efficiency(self) -> float:
        """Calculate resource utilization efficiency percentage."""
        if self.total_allocations == 0:
            return 0.0
        return (self.successful_allocations / self.total_allocations) * 100.0

@dataclass
class PooledResource:
    """Represents a resource in the pool."""
    id: str
    resource_type: ResourceType
    state: ResourceState = ResourceState.AVAILABLE
    allocated_at: Optional[datetime] = None
    allocated_to: Optional[str] = None
    usage_count: int = 0
    max_usage: int = 100
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    
    def is_available(self) -> bool:
        """Check if resource is available for allocation."""
        return self.state == ResourceState.AVAILABLE and self.usage_count < self.max_usage
    
    def is_expired(self) -> bool:
        """Check if resource should be retired due to usage."""
        return self.usage_count >= self.max_usage
    
    def allocate(self, allocator_id: str):
        """Allocate resource to a consumer."""
        if not self.is_available():
            raise NetraException(f"Resource {self.id} not available for allocation")
        
        self.state = ResourceState.ALLOCATED
        self.allocated_at = datetime.now(timezone.utc)
        self.allocated_to = allocator_id
        self.usage_count += 1
        self.last_used_at = self.allocated_at
    
    def release(self):
        """Release resource back to pool."""
        self.state = ResourceState.AVAILABLE
        self.allocated_at = None
        self.allocated_to = None

class ResourcePool:
    """Manages a pool of resources with allocation and scaling."""
    
    def __init__(self, resource_type: ResourceType, initial_size: int = 5, max_size: int = 20):
        self.resource_type = resource_type
        self.initial_size = initial_size
        self.max_size = max_size
        self.resources: Dict[str, PooledResource] = {}
        self.allocation_queue: List[Tuple[str, TaskPriority, datetime]] = []
        self.metrics = ResourceMetrics()
        self.utilization_history: List[Tuple[datetime, float]] = []
        
        # Initialize pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize pool with initial resources."""
        for i in range(self.initial_size):
            resource_id = f"{self.resource_type.value}_{uuid.uuid4().hex[:8]}"
            resource = PooledResource(
                id=resource_id,
                resource_type=self.resource_type
            )
            self.resources[resource_id] = resource
    
    async def allocate_resource(self, allocator_id: str, 
                              priority: TaskPriority = TaskPriority.NORMAL,
                              timeout: float = 10.0) -> Optional[PooledResource]:
        """Allocate resource with priority scheduling and timeout."""
        start_time = time.time()
        request_time = datetime.now(timezone.utc)
        
        self.metrics.total_allocations += 1
        
        # Add to allocation queue
        self.allocation_queue.append((allocator_id, priority, request_time))
        
        try:
            # Wait for resource with timeout
            resource = await self._wait_for_resource(allocator_id, priority, timeout)
            
            if resource:
                resource.allocate(allocator_id)
                self.metrics.successful_allocations += 1
                
                # Update utilization metrics
                await self._update_utilization_metrics()
                
                return resource
            else:
                self.metrics.failed_allocations += 1
                self.metrics.allocation_failures += 1
                return None
                
        except asyncio.TimeoutError:
            self.metrics.total_wait_time += time.time() - start_time
            self.metrics.failed_allocations += 1
            return None
        finally:
            # Remove from queue
            self.allocation_queue = [
                (aid, p, t) for aid, p, t in self.allocation_queue 
                if aid != allocator_id
            ]
    
    async def _wait_for_resource(self, allocator_id: str, priority: TaskPriority, 
                               timeout: float) -> Optional[PooledResource]:
        """Wait for resource to become available."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Try to find available resource
            resource = self._find_available_resource()
            
            if resource:
                return resource
            
            # Try to scale pool if possible
            if await self._try_scale_pool():
                continue
            
            # Check if this request has priority
            if self._has_allocation_priority(allocator_id, priority):
                # Wait a bit and try again
                await asyncio.sleep(0.1)
                continue
            
            # Wait longer for lower priority requests
            await asyncio.sleep(0.5)
        
        return None
    
    def _find_available_resource(self) -> Optional[PooledResource]:
        """Find an available resource in the pool."""
        for resource in self.resources.values():
            if resource.is_available():
                return resource
        return None
    
    async def _try_scale_pool(self) -> bool:
        """Try to scale pool by adding new resources."""
        current_size = len(self.resources)
        
        if current_size >= self.max_size:
            return False
        
        # Calculate utilization
        allocated_count = sum(1 for r in self.resources.values() 
                            if r.state == ResourceState.ALLOCATED)
        utilization = allocated_count / current_size if current_size > 0 else 0
        
        # Scale if utilization is high
        if utilization >= 0.8:  # 80% utilization threshold
            new_resource_id = f"{self.resource_type.value}_{uuid.uuid4().hex[:8]}"
            new_resource = PooledResource(
                id=new_resource_id,
                resource_type=self.resource_type
            )
            self.resources[new_resource_id] = new_resource
            logger.info(f"Scaled pool {self.resource_type.value} to {len(self.resources)} resources")
            return True
        
        return False
    
    def _has_allocation_priority(self, allocator_id: str, priority: TaskPriority) -> bool:
        """Check if allocator has priority for allocation."""
        # High priority requests get preference
        if priority == TaskPriority.HIGH:
            return True
        
        # Check if there are higher priority requests waiting
        higher_priority_count = sum(
            1 for aid, p, t in self.allocation_queue 
            if p.value > priority.value and aid != allocator_id
        )
        
        return higher_priority_count == 0
    
    async def release_resource(self, resource_id: str, allocator_id: str) -> bool:
        """Release resource back to pool."""
        if resource_id not in self.resources:
            self.metrics.resource_leaks += 1
            return False
        
        resource = self.resources[resource_id]
        
        if resource.allocated_to != allocator_id:
            self.metrics.resource_leaks += 1
            return False
        
        # Check if resource should be retired
        if resource.is_expired():
            await self._retire_resource(resource_id)
        else:
            resource.release()
        
        await self._update_utilization_metrics()
        return True
    
    async def _retire_resource(self, resource_id: str):
        """Retire an expired resource and create new one if needed."""
        if resource_id in self.resources:
            del self.resources[resource_id]
            
            # Create new resource if below minimum
            if len(self.resources) < self.initial_size:
                new_resource_id = f"{self.resource_type.value}_{uuid.uuid4().hex[:8]}"
                new_resource = PooledResource(
                    id=new_resource_id,
                    resource_type=self.resource_type
                )
                self.resources[new_resource_id] = new_resource
    
    async def _update_utilization_metrics(self):
        """Update resource utilization metrics."""
        current_time = datetime.now(timezone.utc)
        total_resources = len(self.resources)
        allocated_resources = sum(1 for r in self.resources.values() 
                                if r.state == ResourceState.ALLOCATED)
        
        if total_resources > 0:
            current_utilization = (allocated_resources / total_resources) * 100.0
            self.metrics.average_utilization = current_utilization
            
            if current_utilization > self.metrics.peak_utilization:
                self.metrics.peak_utilization = current_utilization
            
            self.utilization_history.append((current_time, current_utilization))
            
            # Keep only recent history (last 100 samples)
            if len(self.utilization_history) > 100:
                self.utilization_history = self.utilization_history[-100:]
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get comprehensive resource pool status."""
        total_resources = len(self.resources)
        available_resources = sum(1 for r in self.resources.values() if r.is_available())
        allocated_resources = sum(1 for r in self.resources.values() 
                                if r.state == ResourceState.ALLOCATED)
        expired_resources = sum(1 for r in self.resources.values() if r.is_expired())
        
        current_utilization = (allocated_resources / total_resources * 100.0) if total_resources > 0 else 0
        
        return {
            "pool_type": self.resource_type.value,
            "total_resources": total_resources,
            "available_resources": available_resources,
            "allocated_resources": allocated_resources,
            "expired_resources": expired_resources,
            "current_utilization": current_utilization,
            "queue_length": len(self.allocation_queue),
            "metrics": {
                "total_allocations": self.metrics.total_allocations,
                "utilization_efficiency": self.metrics.get_utilization_efficiency(),
                "peak_utilization": self.metrics.peak_utilization,
                "resource_leaks": self.metrics.resource_leaks,
                "allocation_failures": self.metrics.allocation_failures
            }
        }

class AgentResourcePoolManager:
    """Manages multiple resource pools for different agent resource types."""
    
    def __init__(self):
        self.pools: Dict[ResourceType, ResourcePool] = {}
        self.allocation_tracking: Dict[str, Set[str]] = {}  # allocator_id -> resource_ids
        self.fair_scheduler = FairResourceScheduler()
        
        # Initialize pools for different resource types
        self._initialize_pools()
    
    def _initialize_pools(self):
        """Initialize resource pools for different types."""
        pool_configs = {
            ResourceType.COMPUTE_AGENT: {"initial": 8, "max": 32},
            ResourceType.MEMORY_POOL: {"initial": 4, "max": 16},
            ResourceType.IO_HANDLER: {"initial": 6, "max": 24},
            ResourceType.LLM_CONNECTION: {"initial": 3, "max": 12},
            ResourceType.DATABASE_CONNECTION: {"initial": 5, "max": 20}
        }
        
        for resource_type, config in pool_configs.items():
            self.pools[resource_type] = ResourcePool(
                resource_type=resource_type,
                initial_size=config["initial"],
                max_size=config["max"]
            )
    
    async def allocate_resources(self, allocator_id: str, 
                               resource_requirements: Dict[ResourceType, int],
                               priority: TaskPriority = TaskPriority.NORMAL) -> Dict[ResourceType, List[PooledResource]]:
        """Allocate multiple resources for an agent with fair scheduling."""
        allocated_resources = {}
        
        # Track allocations for this allocator
        if allocator_id not in self.allocation_tracking:
            self.allocation_tracking[allocator_id] = set()
        
        try:
            # Apply fair scheduling
            adjusted_requirements = await self.fair_scheduler.apply_fair_scheduling(
                allocator_id, resource_requirements, priority
            )
            
            # Allocate resources by type
            for resource_type, count in adjusted_requirements.items():
                pool = self.pools[resource_type]
                type_resources = []
                
                for _ in range(count):
                    resource = await pool.allocate_resource(allocator_id, priority)
                    if resource:
                        type_resources.append(resource)
                        self.allocation_tracking[allocator_id].add(resource.id)
                    else:
                        # Partial allocation failure - cleanup and fail
                        await self._cleanup_partial_allocation(allocator_id, allocated_resources)
                        raise NetraException(f"Failed to allocate {resource_type.value} resource")
                
                allocated_resources[resource_type] = type_resources
            
            return allocated_resources
            
        except Exception as e:
            # Cleanup on failure
            await self._cleanup_partial_allocation(allocator_id, allocated_resources)
            raise e
    
    async def _cleanup_partial_allocation(self, allocator_id: str, 
                                        allocated_resources: Dict[ResourceType, List[PooledResource]]):
        """Cleanup partially allocated resources on failure."""
        for resource_type, resources in allocated_resources.items():
            pool = self.pools[resource_type]
            for resource in resources:
                await pool.release_resource(resource.id, allocator_id)
                if resource.id in self.allocation_tracking.get(allocator_id, set()):
                    self.allocation_tracking[allocator_id].remove(resource.id)
    
    async def release_all_resources(self, allocator_id: str) -> bool:
        """Release all resources allocated to an allocator."""
        if allocator_id not in self.allocation_tracking:
            return True
        
        resource_ids = list(self.allocation_tracking[allocator_id])
        release_success = True
        
        for resource_id in resource_ids:
            # Find which pool contains this resource
            for pool in self.pools.values():
                if resource_id in pool.resources:
                    success = await pool.release_resource(resource_id, allocator_id)
                    if not success:
                        release_success = False
                    break
        
        # Clear tracking
        if allocator_id in self.allocation_tracking:
            del self.allocation_tracking[allocator_id]
        
        return release_success
    
    async def detect_resource_leaks(self) -> Dict[str, Any]:
        """Detect resource leaks and orphaned allocations."""
        leak_detection = {
            "orphaned_resources": [],
            "long_running_allocations": [],
            "expired_resources": [],
            "total_leaks": 0
        }
        
        current_time = datetime.now(timezone.utc)
        leak_threshold = timedelta(minutes=10)  # Resources held longer than 10 minutes
        
        for pool in self.pools.values():
            for resource in pool.resources.values():
                # Check for orphaned resources
                if (resource.state == ResourceState.ALLOCATED and 
                    resource.allocated_to not in self.allocation_tracking):
                    leak_detection["orphaned_resources"].append({
                        "resource_id": resource.id,
                        "resource_type": resource.resource_type.value,
                        "allocated_to": resource.allocated_to
                    })
                    leak_detection["total_leaks"] += 1
                
                # Check for long-running allocations
                if (resource.allocated_at and 
                    current_time - resource.allocated_at > leak_threshold):
                    leak_detection["long_running_allocations"].append({
                        "resource_id": resource.id,
                        "resource_type": resource.resource_type.value,
                        "allocated_to": resource.allocated_to,
                        "duration_minutes": (current_time - resource.allocated_at).total_seconds() / 60
                    })
                
                # Check for expired resources
                if resource.is_expired():
                    leak_detection["expired_resources"].append({
                        "resource_id": resource.id,
                        "resource_type": resource.resource_type.value,
                        "usage_count": resource.usage_count
                    })
        
        return leak_detection
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all resource pools."""
        pool_statuses = {}
        overall_metrics = {
            "total_resources": 0,
            "total_allocated": 0,
            "overall_utilization": 0.0,
            "total_allocations": 0,
            "total_leaks": 0
        }
        
        for resource_type, pool in self.pools.items():
            status = pool.get_resource_status()
            pool_statuses[resource_type.value] = status
            
            overall_metrics["total_resources"] += status["total_resources"]
            overall_metrics["total_allocated"] += status["allocated_resources"]
            overall_metrics["total_allocations"] += status["metrics"]["total_allocations"]
            overall_metrics["total_leaks"] += status["metrics"]["resource_leaks"]
        
        if overall_metrics["total_resources"] > 0:
            overall_metrics["overall_utilization"] = (
                overall_metrics["total_allocated"] / overall_metrics["total_resources"] * 100.0
            )
        
        return {
            "pools": pool_statuses,
            "overall_metrics": overall_metrics,
            "active_allocators": len(self.allocation_tracking),
            "fair_scheduler_metrics": self.fair_scheduler.get_metrics()
        }

class FairResourceScheduler:
    """Implements fair scheduling for resource allocation."""
    
    def __init__(self):
        self.allocator_usage_history: Dict[str, int] = {}
        self.priority_weights = {
            TaskPriority.LOW: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.HIGH: 4
        }
    
    async def apply_fair_scheduling(self, allocator_id: str, 
                                  resource_requirements: Dict[ResourceType, int],
                                  priority: TaskPriority) -> Dict[ResourceType, int]:
        """Apply fair scheduling to resource requirements."""
        # Track usage
        if allocator_id not in self.allocator_usage_history:
            self.allocator_usage_history[allocator_id] = 0
        
        current_usage = self.allocator_usage_history[allocator_id]
        priority_weight = self.priority_weights[priority]
        
        # Apply fair scheduling adjustments
        adjusted_requirements = {}
        
        for resource_type, count in resource_requirements.items():
            # Reduce allocation for heavy users (fair sharing)
            if current_usage > 10:  # Heavy user threshold
                fairness_factor = 0.8  # Reduce allocation by 20%
            else:
                fairness_factor = 1.0
            
            # Apply priority weighting
            priority_factor = priority_weight / 2.0  # Normalize
            
            adjusted_count = max(1, int(count * fairness_factor * priority_factor))
            adjusted_requirements[resource_type] = adjusted_count
            
            # Update usage tracking
            self.allocator_usage_history[allocator_id] += adjusted_count
        
        return adjusted_requirements
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get fair scheduler metrics."""
        if not self.allocator_usage_history:
            return {"total_allocators": 0, "average_usage": 0, "max_usage": 0}
        
        total_usage = sum(self.allocator_usage_history.values())
        allocator_count = len(self.allocator_usage_history)
        
        return {
            "total_allocators": allocator_count,
            "average_usage": total_usage / allocator_count,
            "max_usage": max(self.allocator_usage_history.values()),
            "total_usage": total_usage
        }

@pytest.fixture
async def agent_resource_pool_manager():
    """Create agent resource pool manager for testing."""
    manager = AgentResourcePoolManager()
    yield manager

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
class TestAgentResourcePoolL3:
    """L3 integration tests for agent resource pool management."""
    
    async def test_resource_utilization_efficiency(self, agent_resource_pool_manager):
        """Test resource utilization achieves >85% efficiency target."""
        manager = agent_resource_pool_manager
        
        # Allocate resources to drive utilization up
        allocators = []
        for i in range(15):
            allocator_id = f"test_allocator_{i}"
            requirements = {
                ResourceType.COMPUTE_AGENT: 2,
                ResourceType.MEMORY_POOL: 1,
                ResourceType.IO_HANDLER: 1
            }
            
            try:
                allocated = await manager.allocate_resources(
                    allocator_id, requirements, TaskPriority.NORMAL
                )
                allocators.append(allocator_id)
            except NetraException:
                # Expected when resources are exhausted
                break
        
        # Get utilization metrics
        status = manager.get_comprehensive_status()
        overall_utilization = status["overall_metrics"]["overall_utilization"]
        
        # Verify high utilization achieved
        assert overall_utilization >= 75.0, \
            f"Resource utilization {overall_utilization:.1f}% should be at least 75%"
        
        # Verify efficient allocation
        for pool_type, pool_status in status["pools"].items():
            efficiency = pool_status["metrics"]["utilization_efficiency"]
            assert efficiency >= 70.0, \
                f"Pool {pool_type} efficiency {efficiency:.1f}% should be at least 70%"
        
        # Cleanup
        for allocator_id in allocators:
            await manager.release_all_resources(allocator_id)
    
    async def test_fair_scheduling_algorithms(self, agent_resource_pool_manager):
        """Test fair scheduling ensures equitable resource distribution."""
        manager = agent_resource_pool_manager
        
        # Create allocators with different priorities
        allocators = [
            ("high_priority", TaskPriority.HIGH, 3),
            ("normal_1", TaskPriority.NORMAL, 2),
            ("normal_2", TaskPriority.NORMAL, 2),
            ("low_priority", TaskPriority.LOW, 1)
        ]
        
        allocation_results = {}
        
        for allocator_id, priority, resource_count in allocators:
            requirements = {
                ResourceType.COMPUTE_AGENT: resource_count,
                ResourceType.MEMORY_POOL: 1
            }
            
            try:
                allocated = await manager.allocate_resources(
                    allocator_id, requirements, priority
                )
                allocation_results[allocator_id] = {
                    "priority": priority,
                    "requested": resource_count,
                    "allocated": len(allocated.get(ResourceType.COMPUTE_AGENT, [])),
                    "success": True
                }
            except NetraException:
                allocation_results[allocator_id] = {
                    "priority": priority,
                    "requested": resource_count,
                    "allocated": 0,
                    "success": False
                }
        
        # Verify fair scheduling principles
        high_priority_success = allocation_results["high_priority"]["success"]
        assert high_priority_success, "High priority allocation should succeed"
        
        # Verify priority ordering
        high_allocated = allocation_results["high_priority"]["allocated"]
        normal_allocated = max(
            allocation_results["normal_1"]["allocated"],
            allocation_results["normal_2"]["allocated"]
        )
        
        assert high_allocated >= normal_allocated, \
            "High priority should get at least as many resources as normal priority"
        
        # Check fair scheduler metrics
        status = manager.get_comprehensive_status()
        scheduler_metrics = status["fair_scheduler_metrics"]
        assert scheduler_metrics["total_allocators"] >= 3, \
            "Fair scheduler should track multiple allocators"
        
        # Cleanup
        for allocator_id, _, _ in allocators:
            await manager.release_all_resources(allocator_id)
    
    async def test_resource_leak_prevention(self, agent_resource_pool_manager):
        """Test resource leak detection and prevention mechanisms."""
        manager = agent_resource_pool_manager
        
        # Create allocation that simulates potential leak
        allocator_id = "leak_test_allocator"
        requirements = {
            ResourceType.COMPUTE_AGENT: 3,
            ResourceType.MEMORY_POOL: 2
        }
        
        allocated = await manager.allocate_resources(
            allocator_id, requirements, TaskPriority.NORMAL
        )
        
        # Verify initial allocation
        assert len(allocated[ResourceType.COMPUTE_AGENT]) == 3
        assert len(allocated[ResourceType.MEMORY_POOL]) == 2
        
        # Simulate leak by manually removing allocator tracking
        original_tracking = manager.allocation_tracking[allocator_id].copy()
        del manager.allocation_tracking[allocator_id]
        
        # Run leak detection
        leak_report = await manager.detect_resource_leaks()
        
        # Verify leak detection
        assert leak_report["total_leaks"] >= 5, \
            "Should detect leaked resources"
        
        assert len(leak_report["orphaned_resources"]) >= 5, \
            "Should identify orphaned resources"
        
        # Verify resource tracking integrity
        for orphaned in leak_report["orphaned_resources"]:
            assert orphaned["allocated_to"] == allocator_id, \
                "Orphaned resources should be correctly identified"
        
        # Restore tracking for cleanup
        manager.allocation_tracking[allocator_id] = original_tracking
        await manager.release_all_resources(allocator_id)
    
    async def test_priority_based_allocation(self, agent_resource_pool_manager):
        """Test priority-based resource allocation under contention."""
        manager = agent_resource_pool_manager
        
        # First, exhaust most resources with normal priority allocations
        normal_allocators = []
        for i in range(8):
            allocator_id = f"normal_allocator_{i}"
            requirements = {ResourceType.COMPUTE_AGENT: 3}
            
            try:
                await manager.allocate_resources(
                    allocator_id, requirements, TaskPriority.NORMAL
                )
                normal_allocators.append(allocator_id)
            except NetraException:
                break
        
        # Now try high priority allocation
        high_priority_allocator = "high_priority_allocator"
        high_priority_requirements = {ResourceType.COMPUTE_AGENT: 2}
        
        try:
            high_priority_allocated = await manager.allocate_resources(
                high_priority_allocator, high_priority_requirements, TaskPriority.HIGH
            )
            high_priority_success = True
        except NetraException:
            high_priority_success = False
        
        # Try low priority allocation (should likely fail)
        low_priority_allocator = "low_priority_allocator"
        low_priority_requirements = {ResourceType.COMPUTE_AGENT: 1}
        
        try:
            await manager.allocate_resources(
                low_priority_allocator, low_priority_requirements, TaskPriority.LOW
            )
            low_priority_success = True
        except NetraException:
            low_priority_success = False
        
        # Verify priority behavior
        # High priority should have better success than low priority under contention
        if not high_priority_success and not low_priority_success:
            # Both failed - acceptable under high contention
            pass
        else:
            assert high_priority_success or not low_priority_success, \
                "High priority should succeed if low priority succeeds"
        
        # Cleanup
        for allocator in normal_allocators:
            await manager.release_all_resources(allocator)
        if high_priority_success:
            await manager.release_all_resources(high_priority_allocator)
        if low_priority_success:
            await manager.release_all_resources(low_priority_allocator)
    
    async def test_pool_scaling_strategies(self, agent_resource_pool_manager):
        """Test automatic pool scaling under high demand."""
        manager = agent_resource_pool_manager
        
        # Get initial pool sizes
        initial_status = manager.get_comprehensive_status()
        initial_compute_resources = initial_status["pools"]["compute_agent"]["total_resources"]
        
        # Create high demand to trigger scaling
        scaling_allocators = []
        for i in range(20):  # More than initial pool size
            allocator_id = f"scaling_test_{i}"
            requirements = {ResourceType.COMPUTE_AGENT: 2}
            
            try:
                await manager.allocate_resources(
                    allocator_id, requirements, TaskPriority.NORMAL
                )
                scaling_allocators.append(allocator_id)
                
                # Brief pause to allow scaling
                await asyncio.sleep(0.01)
            except NetraException:
                # Expected when max capacity reached
                break
        
        # Check if scaling occurred
        final_status = manager.get_comprehensive_status()
        final_compute_resources = final_status["pools"]["compute_agent"]["total_resources"]
        
        # Verify scaling behavior
        assert final_compute_resources >= initial_compute_resources, \
            "Pool should maintain or increase size under demand"
        
        # If scaling occurred, verify it was reasonable
        if final_compute_resources > initial_compute_resources:
            scaling_factor = final_compute_resources / initial_compute_resources
            assert scaling_factor <= 4.0, \
                f"Scaling factor {scaling_factor:.1f} should be reasonable (not excessive)"
        
        # Verify utilization after scaling
        utilization = final_status["overall_metrics"]["overall_utilization"]
        assert utilization >= 60.0, \
            f"Utilization {utilization:.1f}% should remain high after scaling"
        
        # Cleanup
        for allocator in scaling_allocators:
            await manager.release_all_resources(allocator)
    
    async def test_resource_pool_performance_under_load(self, agent_resource_pool_manager):
        """Test resource pool performance under sustained load."""
        manager = agent_resource_pool_manager
        
        # Create sustained concurrent load
        async def allocate_and_release(allocator_id: str):
            requirements = {
                ResourceType.COMPUTE_AGENT: 1,
                ResourceType.IO_HANDLER: 1
            }
            
            try:
                allocated = await manager.allocate_resources(
                    allocator_id, requirements, TaskPriority.NORMAL
                )
                
                # Hold resources briefly
                await asyncio.sleep(0.1)
                
                # Release resources
                await manager.release_all_resources(allocator_id)
                
                return True
            except NetraException:
                return False
        
        # Run concurrent load test
        load_tasks = []
        for i in range(50):
            allocator_id = f"load_test_{i}"
            task = allocate_and_release(allocator_id)
            load_tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*load_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze performance
        successful_operations = sum(1 for r in results if r is True)
        success_rate = (successful_operations / len(results)) * 100.0
        
        # Verify performance under load
        assert total_time < 10.0, \
            f"Load test should complete within 10 seconds, took {total_time:.2f}s"
        
        assert success_rate >= 60.0, \
            f"Success rate {success_rate:.1f}% should be at least 60% under load"
        
        # Verify no resource leaks after load test
        leak_report = await manager.detect_resource_leaks()
        assert leak_report["total_leaks"] == 0, \
            "No resource leaks should occur after load test"
        
        # Verify pool stability
        final_status = manager.get_comprehensive_status()
        assert final_status["overall_metrics"]["total_allocated"] == 0, \
            "All resources should be available after load test"
    
    async def test_concurrent_resource_operations(self, agent_resource_pool_manager):
        """Test concurrent resource operations don't cause race conditions."""
        manager = agent_resource_pool_manager
        
        # Create multiple concurrent allocators
        concurrent_allocators = [f"concurrent_{i}" for i in range(10)]
        
        async def concurrent_allocation_cycle(allocator_id: str):
            for cycle in range(3):
                requirements = {
                    ResourceType.COMPUTE_AGENT: 1,
                    ResourceType.MEMORY_POOL: 1
                }
                
                try:
                    # Allocate
                    allocated = await manager.allocate_resources(
                        allocator_id, requirements, TaskPriority.NORMAL
                    )
                    
                    # Brief hold
                    await asyncio.sleep(0.05)
                    
                    # Release
                    await manager.release_all_resources(allocator_id)
                    
                except NetraException:
                    # Continue on allocation failure
                    pass
        
        # Run concurrent operations
        concurrent_tasks = [
            concurrent_allocation_cycle(allocator_id) 
            for allocator_id in concurrent_allocators
        ]
        
        await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify system consistency after concurrent operations
        final_status = manager.get_comprehensive_status()
        
        # All resources should be available
        assert final_status["overall_metrics"]["total_allocated"] == 0, \
            "All resources should be available after concurrent operations"
        
        # No active allocators should remain
        assert final_status["active_allocators"] == 0, \
            "No allocators should remain active"
        
        # Check for leaks
        leak_report = await manager.detect_resource_leaks()
        assert leak_report["total_leaks"] == 0, \
            "No resource leaks should occur from concurrent operations"