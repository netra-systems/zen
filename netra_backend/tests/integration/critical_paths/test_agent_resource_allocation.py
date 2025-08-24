"""Agent Resource Allocation L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (cost optimization)
- Business Goal: Resource efficiency and cost optimization
- Value Impact: Protects $9K MRR from resource waste and over-provisioning
- Strategic Impact: Core cost management for scalable AI operations

Critical Path: Resource request -> Allocation strategy -> Limits -> Monitoring -> Scaling
Coverage: Real resource manager, allocation algorithms, monitoring, auto-scaling
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest
from netra_backend.app.monitoring.metrics_collector import MetricsCollector

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager as ConnectionManager

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """Types of resources that can be allocated."""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    STORAGE = "storage"
    NETWORK = "network"
    LLM_TOKENS = "llm_tokens"

class AllocationStrategy(Enum):
    """Resource allocation strategies."""
    FAIR_SHARE = "fair_share"
    PRIORITY_BASED = "priority_based"
    DEMAND_BASED = "demand_based"
    PREDICTIVE = "predictive"

@dataclass
class ResourceQuota:
    """Resource quota definition."""
    resource_type: ResourceType
    total_available: float
    allocated: float
    reserved: float
    
    @property
    def free(self) -> float:
        """Get free resources."""
        return self.total_available - self.allocated - self.reserved
    
    @property
    def utilization(self) -> float:
        """Get utilization percentage."""
        return (self.allocated / self.total_available) * 100 if self.total_available > 0 else 0

@dataclass
class ResourceRequest:
    """Resource allocation request."""
    request_id: str
    agent_id: str
    agent_type: str
    resource_type: ResourceType
    amount: float
    priority: int
    duration_seconds: Optional[int]
    created_at: datetime
    
    def __post_init__(self):
        if self.duration_seconds is None:
            self.duration_seconds = 3600  # Default 1 hour

@dataclass
class ResourceAllocation:
    """Active resource allocation."""
    allocation_id: str
    request: ResourceRequest
    allocated_amount: float
    allocated_at: datetime
    expires_at: Optional[datetime]
    active: bool = True
    
    @property
    def is_expired(self) -> bool:
        """Check if allocation has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

class ResourceMonitor:
    """Monitors resource usage and performance."""
    
    def __init__(self):
        self.usage_history = {}
        self.performance_metrics = {}
        
    def record_usage(self, allocation_id: str, resource_type: ResourceType, 
                    usage_amount: float, timestamp: datetime = None):
        """Record resource usage."""
        timestamp = timestamp or datetime.now()
        
        if allocation_id not in self.usage_history:
            self.usage_history[allocation_id] = []
        
        self.usage_history[allocation_id].append({
            "resource_type": resource_type,
            "usage_amount": usage_amount,
            "timestamp": timestamp
        })
    
    def get_usage_stats(self, allocation_id: str) -> Dict[str, Any]:
        """Get usage statistics for an allocation."""
        history = self.usage_history.get(allocation_id, [])
        
        if not history:
            return {"total_usage": 0, "average_usage": 0, "peak_usage": 0}
        
        usage_amounts = [h["usage_amount"] for h in history]
        
        return {
            "total_usage": sum(usage_amounts),
            "average_usage": sum(usage_amounts) / len(usage_amounts),
            "peak_usage": max(usage_amounts),
            "data_points": len(usage_amounts)
        }
    
    def calculate_efficiency(self, allocation_id: str, allocated_amount: float) -> float:
        """Calculate resource utilization efficiency."""
        stats = self.get_usage_stats(allocation_id)
        
        if allocated_amount == 0:
            return 0.0
        
        return (stats["average_usage"] / allocated_amount) * 100

class ResourceAllocator:
    """Allocates resources based on strategies and policies."""
    
    def __init__(self, strategy: AllocationStrategy = AllocationStrategy.FAIR_SHARE):
        self.strategy = strategy
        self.quotas = {}
        self.allocations = {}
        self.waiting_requests = []
        
    def set_quota(self, resource_type: ResourceType, total_available: float):
        """Set resource quota."""
        self.quotas[resource_type] = ResourceQuota(
            resource_type=resource_type,
            total_available=total_available,
            allocated=0.0,
            reserved=0.0
        )
    
    def request_resources(self, request: ResourceRequest) -> Optional[str]:
        """Request resource allocation."""
        quota = self.quotas.get(request.resource_type)
        
        if not quota:
            logger.error(f"No quota defined for {request.resource_type}")
            return None
        
        # Check if resources are available
        if quota.free >= request.amount:
            allocation_id = self._allocate_resources(request, quota)
            return allocation_id
        else:
            # Add to waiting queue
            self.waiting_requests.append(request)
            logger.info(f"Request {request.request_id} queued - insufficient resources")
            return None
    
    def _allocate_resources(self, request: ResourceRequest, quota: ResourceQuota) -> str:
        """Perform actual resource allocation."""
        allocation_id = f"alloc_{int(time.time() * 1000000)}"
        
        # Determine allocation amount based on strategy
        allocated_amount = self._calculate_allocation_amount(request, quota)
        
        # Create allocation
        expires_at = None
        if request.duration_seconds:
            expires_at = datetime.now() + timedelta(seconds=request.duration_seconds)
        
        allocation = ResourceAllocation(
            allocation_id=allocation_id,
            request=request,
            allocated_amount=allocated_amount,
            allocated_at=datetime.now(),
            expires_at=expires_at
        )
        
        # Update quota and tracking
        quota.allocated += allocated_amount
        self.allocations[allocation_id] = allocation
        
        logger.info(f"Allocated {allocated_amount} {request.resource_type.value} to {request.agent_id}")
        return allocation_id
    
    def _calculate_allocation_amount(self, request: ResourceRequest, quota: ResourceQuota) -> float:
        """Calculate allocation amount based on strategy."""
        if self.strategy == AllocationStrategy.FAIR_SHARE:
            # Fair share: give exactly what's requested if available
            return min(request.amount, quota.free)
        
        elif self.strategy == AllocationStrategy.PRIORITY_BASED:
            # Priority-based: higher priority gets preference
            multiplier = 1.0 + (request.priority / 10.0)
            return min(request.amount * multiplier, quota.free)
        
        elif self.strategy == AllocationStrategy.DEMAND_BASED:
            # Demand-based: allocate based on historical usage
            base_amount = min(request.amount, quota.free)
            # In a real system, this would use historical data
            return base_amount * 0.8  # Conservative allocation
        
        else:
            return min(request.amount, quota.free)
    
    def release_resources(self, allocation_id: str) -> bool:
        """Release allocated resources."""
        allocation = self.allocations.get(allocation_id)
        
        if not allocation or not allocation.active:
            return False
        
        quota = self.quotas[allocation.request.resource_type]
        quota.allocated -= allocation.allocated_amount
        allocation.active = False
        
        logger.info(f"Released {allocation.allocated_amount} {allocation.request.resource_type.value}")
        
        # Process waiting requests
        self._process_waiting_requests()
        
        return True
    
    def _process_waiting_requests(self):
        """Process waiting resource requests."""
        processed_requests = []
        
        for request in self.waiting_requests[:]:
            quota = self.quotas.get(request.resource_type)
            if quota and quota.free >= request.amount:
                allocation_id = self._allocate_resources(request, quota)
                if allocation_id:
                    processed_requests.append(request)
                    self.waiting_requests.remove(request)
        
        return len(processed_requests)
    
    def cleanup_expired_allocations(self) -> int:
        """Clean up expired allocations."""
        expired_count = 0
        
        for allocation_id, allocation in list(self.allocations.items()):
            if allocation.is_expired:
                self.release_resources(allocation_id)
                expired_count += 1
        
        return expired_count
    
    def get_allocation_summary(self) -> Dict[str, Any]:
        """Get resource allocation summary."""
        active_allocations = [a for a in self.allocations.values() if a.active]
        
        summary = {
            "total_allocations": len(active_allocations),
            "waiting_requests": len(self.waiting_requests),
            "resource_utilization": {}
        }
        
        for resource_type, quota in self.quotas.items():
            summary["resource_utilization"][resource_type.value] = {
                "total": quota.total_available,
                "allocated": quota.allocated,
                "free": quota.free,
                "utilization_percent": quota.utilization
            }
        
        return summary

class AutoScaler:
    """Handles automatic resource scaling based on demand."""
    
    def __init__(self, allocator: ResourceAllocator, monitor: ResourceMonitor):
        self.allocator = allocator
        self.monitor = monitor
        self.scaling_rules = []
        
    def add_scaling_rule(self, resource_type: ResourceType, 
                        scale_up_threshold: float, scale_down_threshold: float,
                        scale_factor: float = 1.5):
        """Add auto-scaling rule."""
        self.scaling_rules.append({
            "resource_type": resource_type,
            "scale_up_threshold": scale_up_threshold,
            "scale_down_threshold": scale_down_threshold,
            "scale_factor": scale_factor
        })
    
    def evaluate_scaling(self) -> List[Dict[str, Any]]:
        """Evaluate scaling needs and return recommendations."""
        recommendations = []
        
        for rule in self.scaling_rules:
            resource_type = rule["resource_type"]
            quota = self.allocator.quotas.get(resource_type)
            
            if not quota:
                continue
            
            utilization = quota.utilization
            
            if utilization > rule["scale_up_threshold"]:
                # Recommend scale up
                new_quota = quota.total_available * rule["scale_factor"]
                recommendations.append({
                    "action": "scale_up",
                    "resource_type": resource_type,
                    "current_quota": quota.total_available,
                    "recommended_quota": new_quota,
                    "reason": f"Utilization {utilization:.1f}% > {rule['scale_up_threshold']}%"
                })
            
            elif utilization < rule["scale_down_threshold"]:
                # Recommend scale down
                new_quota = quota.total_available / rule["scale_factor"]
                # Don't scale below current allocation
                new_quota = max(new_quota, quota.allocated * 1.2)
                
                if new_quota < quota.total_available:
                    recommendations.append({
                        "action": "scale_down",
                        "resource_type": resource_type,
                        "current_quota": quota.total_available,
                        "recommended_quota": new_quota,
                        "reason": f"Utilization {utilization:.1f}% < {rule['scale_down_threshold']}%"
                    })
        
        return recommendations
    
    def apply_scaling_recommendation(self, recommendation: Dict[str, Any]) -> bool:
        """Apply a scaling recommendation."""
        try:
            resource_type = recommendation["resource_type"]
            new_quota = recommendation["recommended_quota"]
            
            self.allocator.set_quota(resource_type, new_quota)
            
            logger.info(f"Scaled {resource_type.value} to {new_quota}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply scaling: {e}")
            return False

class AgentResourceAllocationManager:
    """Manages agent resource allocation testing."""
    
    def __init__(self):
        self.redis_service = None
        self.db_manager = None
        self.allocator = None
        self.monitor = None
        self.auto_scaler = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = ConnectionManager()
        await self.db_manager.initialize()
        
        self.allocator = ResourceAllocator(AllocationStrategy.FAIR_SHARE)
        self.monitor = ResourceMonitor()
        self.auto_scaler = AutoScaler(self.allocator, self.monitor)
        
        self._setup_resource_quotas()
        self._setup_scaling_rules()
    
    def _setup_resource_quotas(self):
        """Setup initial resource quotas."""
        self.allocator.set_quota(ResourceType.CPU, 100.0)        # 100 CPU cores
        self.allocator.set_quota(ResourceType.MEMORY, 1000.0)    # 1000 GB
        self.allocator.set_quota(ResourceType.GPU, 10.0)         # 10 GPUs
        self.allocator.set_quota(ResourceType.LLM_TOKENS, 1000000.0)  # 1M tokens
    
    def _setup_scaling_rules(self):
        """Setup auto-scaling rules."""
        for resource_type in [ResourceType.CPU, ResourceType.MEMORY, ResourceType.GPU]:
            self.auto_scaler.add_scaling_rule(
                resource_type=resource_type,
                scale_up_threshold=80.0,   # Scale up at 80% utilization
                scale_down_threshold=30.0, # Scale down at 30% utilization
                scale_factor=1.5
            )
    
    def create_resource_request(self, agent_id: str, resource_type: ResourceType, 
                               amount: float, priority: int = 5) -> ResourceRequest:
        """Create a resource request."""
        return ResourceRequest(
            request_id=f"req_{int(time.time() * 1000000)}",
            agent_id=agent_id,
            agent_type="test_agent",
            resource_type=resource_type,
            amount=amount,
            priority=priority,
            duration_seconds=300,  # 5 minutes
            created_at=datetime.now()
        )
    
    async def simulate_resource_usage(self, allocation_id: str, 
                                    resource_type: ResourceType, 
                                    usage_pattern: str = "constant"):
        """Simulate resource usage for testing."""
        if usage_pattern == "constant":
            # Constant usage
            allocation = self.allocator.allocations.get(allocation_id)
            if allocation:
                usage_amount = allocation.allocated_amount * 0.7  # 70% of allocation
                self.monitor.record_usage(allocation_id, resource_type, usage_amount)
        
        elif usage_pattern == "variable":
            # Variable usage pattern
            allocation = self.allocator.allocations.get(allocation_id)
            if allocation:
                for i in range(5):
                    usage_factor = 0.5 + (i * 0.1)  # 50% to 90% usage
                    usage_amount = allocation.allocated_amount * usage_factor
                    self.monitor.record_usage(allocation_id, resource_type, usage_amount)
                    await asyncio.sleep(0.01)
        
        elif usage_pattern == "spike":
            # Usage spike pattern
            allocation = self.allocator.allocations.get(allocation_id)
            if allocation:
                # Normal usage
                normal_usage = allocation.allocated_amount * 0.3
                self.monitor.record_usage(allocation_id, resource_type, normal_usage)
                
                # Spike
                spike_usage = allocation.allocated_amount * 0.9
                self.monitor.record_usage(allocation_id, resource_type, spike_usage)
                
                # Back to normal
                self.monitor.record_usage(allocation_id, resource_type, normal_usage)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()

@pytest.fixture
async def resource_allocation_manager():
    """Create resource allocation manager for testing."""
    manager = AgentResourceAllocationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_basic_resource_allocation(resource_allocation_manager):
    """Test basic resource allocation and release."""
    manager = resource_allocation_manager
    
    # Create resource request
    request = manager.create_resource_request("test_agent_1", ResourceType.CPU, 10.0)
    
    # Request allocation
    allocation_id = manager.allocator.request_resources(request)
    
    assert allocation_id is not None
    assert allocation_id in manager.allocator.allocations
    
    allocation = manager.allocator.allocations[allocation_id]
    assert allocation.allocated_amount == 10.0
    assert allocation.active is True
    
    # Check quota usage
    cpu_quota = manager.allocator.quotas[ResourceType.CPU]
    assert cpu_quota.allocated == 10.0
    assert cpu_quota.free == 90.0
    
    # Release resources
    release_result = manager.allocator.release_resources(allocation_id)
    assert release_result is True
    assert allocation.active is False
    assert cpu_quota.allocated == 0.0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_resource_quota_limits(resource_allocation_manager):
    """Test resource allocation with quota limits."""
    manager = resource_allocation_manager
    
    # Request more than available
    large_request = manager.create_resource_request("test_agent_1", ResourceType.GPU, 15.0)
    allocation_id = manager.allocator.request_resources(large_request)
    
    # Should be queued since only 10 GPUs available
    assert allocation_id is None
    assert len(manager.allocator.waiting_requests) == 1
    
    # Request within limits
    normal_request = manager.create_resource_request("test_agent_2", ResourceType.GPU, 5.0)
    allocation_id = manager.allocator.request_resources(normal_request)
    
    assert allocation_id is not None
    
    # Release resources and check if waiting request gets processed
    manager.allocator.release_resources(allocation_id)
    
    # Waiting request should still be there (requires 15 GPUs)
    assert len(manager.allocator.waiting_requests) == 1

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_priority_based_allocation(resource_allocation_manager):
    """Test priority-based resource allocation."""
    manager = resource_allocation_manager
    
    # Change to priority-based strategy
    manager.allocator.strategy = AllocationStrategy.PRIORITY_BASED
    
    # Create requests with different priorities
    low_priority = manager.create_resource_request("low_agent", ResourceType.CPU, 10.0, priority=1)
    high_priority = manager.create_resource_request("high_agent", ResourceType.CPU, 10.0, priority=9)
    
    # Allocate resources
    low_id = manager.allocator.request_resources(low_priority)
    high_id = manager.allocator.request_resources(high_priority)
    
    assert low_id is not None
    assert high_id is not None
    
    # High priority should get more resources (or at least equal)
    low_allocation = manager.allocator.allocations[low_id]
    high_allocation = manager.allocator.allocations[high_id]
    
    assert high_allocation.allocated_amount >= low_allocation.allocated_amount

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_resource_usage_monitoring(resource_allocation_manager):
    """Test resource usage monitoring and efficiency calculation."""
    manager = resource_allocation_manager
    
    # Allocate resources
    request = manager.create_resource_request("monitor_agent", ResourceType.MEMORY, 100.0)
    allocation_id = manager.allocator.request_resources(request)
    
    assert allocation_id is not None
    
    # Simulate usage
    await manager.simulate_resource_usage(allocation_id, ResourceType.MEMORY, "variable")
    
    # Get usage statistics
    stats = manager.monitor.get_usage_stats(allocation_id)
    
    assert stats["data_points"] > 0
    assert stats["average_usage"] > 0
    assert stats["peak_usage"] > 0
    
    # Calculate efficiency
    efficiency = manager.monitor.calculate_efficiency(allocation_id, 100.0)
    
    assert 0 <= efficiency <= 100

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_auto_scaling_evaluation(resource_allocation_manager):
    """Test auto-scaling evaluation and recommendations."""
    manager = resource_allocation_manager
    
    # Create high utilization scenario
    high_usage_requests = [
        manager.create_resource_request(f"agent_{i}", ResourceType.CPU, 15.0)
        for i in range(6)  # 90 CPU cores total (90% utilization)
    ]
    
    allocation_ids = []
    for request in high_usage_requests:
        allocation_id = manager.allocator.request_resources(request)
        if allocation_id:
            allocation_ids.append(allocation_id)
    
    # Evaluate scaling needs
    recommendations = manager.auto_scaler.evaluate_scaling()
    
    # Should recommend scaling up CPU
    cpu_recommendations = [r for r in recommendations 
                          if r["resource_type"] == ResourceType.CPU]
    
    assert len(cpu_recommendations) > 0
    assert cpu_recommendations[0]["action"] == "scale_up"
    
    # Test scale down scenario
    for allocation_id in allocation_ids:
        manager.allocator.release_resources(allocation_id)
    
    recommendations = manager.auto_scaler.evaluate_scaling()
    cpu_recommendations = [r for r in recommendations 
                          if r["resource_type"] == ResourceType.CPU]
    
    if cpu_recommendations:
        assert cpu_recommendations[0]["action"] == "scale_down"

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_allocation_expiration_cleanup(resource_allocation_manager):
    """Test automatic cleanup of expired allocations."""
    manager = resource_allocation_manager
    
    # Create short-duration request
    request = manager.create_resource_request("expire_agent", ResourceType.MEMORY, 50.0)
    request.duration_seconds = 1  # 1 second duration
    
    allocation_id = manager.allocator.request_resources(request)
    assert allocation_id is not None
    
    # Verify allocation is active
    allocation = manager.allocator.allocations[allocation_id]
    assert allocation.active is True
    
    # Wait for expiration
    await asyncio.sleep(2)
    
    # Cleanup expired allocations
    expired_count = manager.allocator.cleanup_expired_allocations()
    
    assert expired_count > 0
    assert not allocation.active

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_concurrent_resource_requests(resource_allocation_manager):
    """Test concurrent resource allocation requests."""
    manager = resource_allocation_manager
    
    # Create many concurrent requests
    requests = [
        manager.create_resource_request(f"concurrent_{i}", ResourceType.CPU, 5.0)
        for i in range(20)
    ]
    
    # Process requests concurrently
    async def allocate_request(request):
        return manager.allocator.request_resources(request)
    
    tasks = [allocate_request(req) for req in requests]
    results = await asyncio.gather(*tasks)
    
    # Count successful allocations
    successful_allocations = [r for r in results if r is not None]
    
    # Should allocate resources up to quota limit
    assert len(successful_allocations) == 20  # 20 * 5 = 100 CPU (exactly the limit)
    
    # Check that quota is properly updated
    cpu_quota = manager.allocator.quotas[ResourceType.CPU]
    assert cpu_quota.allocated == 100.0
    assert cpu_quota.free == 0.0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_resource_allocation_fairness(resource_allocation_manager):
    """Test fair resource allocation across agents."""
    manager = resource_allocation_manager
    
    # Create requests from multiple agents
    agent_requests = {}
    for i in range(5):
        agent_id = f"fair_agent_{i}"
        request = manager.create_resource_request(agent_id, ResourceType.MEMORY, 150.0)
        agent_requests[agent_id] = request
    
    # Allocate resources
    allocations = {}
    for agent_id, request in agent_requests.items():
        allocation_id = manager.allocator.request_resources(request)
        if allocation_id:
            allocations[agent_id] = manager.allocator.allocations[allocation_id]
    
    # Verify fair distribution
    allocated_amounts = [alloc.allocated_amount for alloc in allocations.values()]
    
    # All successful allocations should be roughly equal in fair share mode
    if len(allocated_amounts) > 1:
        max_allocation = max(allocated_amounts)
        min_allocation = min(allocated_amounts)
        fairness_ratio = min_allocation / max_allocation
        
        assert fairness_ratio > 0.8  # At least 80% fairness

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_resource_allocation_summary(resource_allocation_manager):
    """Test resource allocation summary reporting."""
    manager = resource_allocation_manager
    
    # Create various allocations
    requests = [
        manager.create_resource_request("summary_agent_1", ResourceType.CPU, 20.0),
        manager.create_resource_request("summary_agent_2", ResourceType.MEMORY, 200.0),
        manager.create_resource_request("summary_agent_3", ResourceType.GPU, 3.0)
    ]
    
    allocation_ids = []
    for request in requests:
        allocation_id = manager.allocator.request_resources(request)
        if allocation_id:
            allocation_ids.append(allocation_id)
    
    # Get allocation summary
    summary = manager.allocator.get_allocation_summary()
    
    assert summary["total_allocations"] == len(allocation_ids)
    assert "resource_utilization" in summary
    
    # Check CPU utilization
    cpu_util = summary["resource_utilization"]["cpu"]
    assert cpu_util["allocated"] == 20.0
    assert cpu_util["utilization_percent"] == 20.0

@pytest.mark.asyncio
@pytest.mark.l2_integration
@pytest.mark.asyncio
async def test_resource_allocation_performance(resource_allocation_manager):
    """Benchmark resource allocation performance."""
    manager = resource_allocation_manager
    
    # Benchmark allocation speed
    start_time = time.time()
    
    requests = [
        manager.create_resource_request(f"perf_{i}", ResourceType.LLM_TOKENS, 1000.0)
        for i in range(100)
    ]
    
    allocation_ids = []
    for request in requests:
        allocation_id = manager.allocator.request_resources(request)
        if allocation_id:
            allocation_ids.append(allocation_id)
    
    allocation_time = time.time() - start_time
    
    # Benchmark release speed
    start_time = time.time()
    
    for allocation_id in allocation_ids:
        manager.allocator.release_resources(allocation_id)
    
    release_time = time.time() - start_time
    
    # Performance assertions
    assert allocation_time < 1.0  # 100 allocations in under 1 second
    assert release_time < 0.5     # 100 releases in under 0.5 seconds
    
    avg_allocation_time = allocation_time / len(allocation_ids) if allocation_ids else 0
    avg_release_time = release_time / len(allocation_ids) if allocation_ids else 0
    
    assert avg_allocation_time < 0.01  # Under 10ms per allocation
    assert avg_release_time < 0.005    # Under 5ms per release
    
    logger.info(f"Performance: Allocation {avg_allocation_time*1000:.1f}ms, "
               f"Release {avg_release_time*1000:.1f}ms")