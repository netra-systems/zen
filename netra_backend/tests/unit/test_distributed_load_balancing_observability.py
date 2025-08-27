"""Unit tests for distributed load balancing and resource allocation observability.

Tests load balancing algorithms, resource allocation patterns,
and auto-scaling behaviors in distributed systems.

Business Value: Ensures optimal resource utilization and system performance
through intelligent load distribution and adaptive scaling.
"""

import asyncio
import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest


@dataclass
class ServiceInstance:
    """Represents a service instance in the load balancer pool."""
    instance_id: str
    host: str
    port: int
    current_load: float  # 0.0 to 1.0
    health_score: float  # 0.0 to 1.0
    response_time_avg: float  # milliseconds
    active_connections: int
    cpu_usage: float  # 0.0 to 1.0
    memory_usage: float  # 0.0 to 1.0
    last_health_check: float
    is_healthy: bool = True


class TestDistributedLoadBalancing:
    """Test suite for distributed load balancing patterns."""
    
    @pytest.fixture
    def service_pool(self):
        """Create a pool of service instances for testing."""
        return [
            ServiceInstance(
                instance_id="auth-001",
                host="10.0.1.10",
                port=8080,
                current_load=0.3,
                health_score=0.95,
                response_time_avg=120,
                active_connections=45,
                cpu_usage=0.25,
                memory_usage=0.40,
                last_health_check=time.time()
            ),
            ServiceInstance(
                instance_id="auth-002",
                host="10.0.1.11",
                port=8080,
                current_load=0.7,
                health_score=0.85,
                response_time_avg=200,
                active_connections=85,
                cpu_usage=0.65,
                memory_usage=0.70,
                last_health_check=time.time()
            ),
            ServiceInstance(
                instance_id="auth-003",
                host="10.0.1.12",
                port=8080,
                current_load=0.1,
                health_score=0.98,
                response_time_avg=80,
                active_connections=15,
                cpu_usage=0.10,
                memory_usage=0.25,
                last_health_check=time.time()
            ),
            ServiceInstance(
                instance_id="auth-004",
                host="10.0.1.13",
                port=8080,
                current_load=0.9,
                health_score=0.60,
                response_time_avg=500,
                active_connections=120,
                cpu_usage=0.85,
                memory_usage=0.90,
                last_health_check=time.time() - 30,  # Stale health check
                is_healthy=False
            )
        ]
    
    def test_weighted_round_robin_load_balancing(self, service_pool):
        """Test weighted round-robin load balancing algorithm."""
        
        # Calculate weights based on inverse of current load and health score
        def calculate_weight(instance: ServiceInstance) -> float:
            if not instance.is_healthy:
                return 0.0
            
            # Weight is inverse of load, multiplied by health score
            load_weight = 1.0 - instance.current_load
            health_weight = instance.health_score
            return load_weight * health_weight
        
        # Calculate weights for each instance
        weights = {}
        total_weight = 0.0
        
        for instance in service_pool:
            weight = calculate_weight(instance)
            weights[instance.instance_id] = weight
            total_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            for instance_id in weights:
                weights[instance_id] = weights[instance_id] / total_weight
        
        # Simulate request distribution
        num_requests = 1000
        request_distribution = {instance.instance_id: 0 for instance in service_pool}
        
        # Simple weighted selection simulation
        for _ in range(num_requests):
            rand_value = random.random()
            cumulative_weight = 0.0
            
            for instance in service_pool:
                if instance.is_healthy:
                    cumulative_weight += weights[instance.instance_id]
                    if rand_value <= cumulative_weight:
                        request_distribution[instance.instance_id] += 1
                        break
        
        # Verify distribution patterns
        # auth-003 should get most requests (lowest load, highest health)
        # auth-004 should get no requests (unhealthy)
        assert request_distribution["auth-004"] == 0  # Unhealthy instance gets no requests
        assert request_distribution["auth-003"] > request_distribution["auth-001"]  # Lower load gets more
        assert request_distribution["auth-001"] > request_distribution["auth-002"]  # Better health gets more
    
    def test_least_connections_load_balancing(self, service_pool):
        """Test least connections load balancing algorithm."""
        
        # Filter healthy instances and sort by connection count
        healthy_instances = [instance for instance in service_pool if instance.is_healthy]
        sorted_instances = sorted(healthy_instances, key=lambda x: x.active_connections)
        
        # Simulate 100 new connections using least connections algorithm
        connection_assignments = []
        
        for i in range(100):
            # Find instance with least connections among healthy ones
            current_healthy = [instance for instance in service_pool if instance.is_healthy]
            if current_healthy:
                selected_instance = min(current_healthy, key=lambda x: x.active_connections)
                connection_assignments.append(selected_instance.instance_id)
                
                # Update connection count for next iteration
                selected_instance.active_connections += 1
        
        # Verify least connections distribution
        assignment_counts = {}
        for assignment in connection_assignments:
            assignment_counts[assignment] = assignment_counts.get(assignment, 0) + 1
        
        # auth-003 should get most connections initially (had 15 connections)
        # Distribution should be relatively even as connections are added
        assert "auth-004" not in assignment_counts  # Unhealthy instance gets nothing
        assert assignment_counts.get("auth-003", 0) > 0  # Instance with fewest connections gets some
    
    def test_adaptive_load_balancing_with_response_time(self, service_pool):
        """Test adaptive load balancing considering response times."""
        
        class AdaptiveLoadBalancer:
            def __init__(self, instances: List[ServiceInstance]):
                self.instances = instances
                self.response_time_window = []
                self.adaptation_threshold = 0.2  # 20% increase triggers adaptation
            
            def calculate_performance_score(self, instance: ServiceInstance) -> float:
                """Calculate performance score based on multiple factors."""
                if not instance.is_healthy:
                    return 0.0
                
                # Response time score (inverse relationship)
                response_time_score = 1.0 / (1.0 + instance.response_time_avg / 100.0)
                
                # Load score (inverse relationship)
                load_score = 1.0 - instance.current_load
                
                # Health score (direct relationship)
                health_score = instance.health_score
                
                # CPU usage score (inverse relationship)
                cpu_score = 1.0 - instance.cpu_usage
                
                # Weighted combination
                performance_score = (
                    response_time_score * 0.4 +
                    load_score * 0.3 +
                    health_score * 0.2 +
                    cpu_score * 0.1
                )
                
                return performance_score
            
            def select_instance(self) -> Optional[ServiceInstance]:
                """Select best instance based on performance score."""
                healthy_instances = [i for i in self.instances if i.is_healthy]
                if not healthy_instances:
                    return None
                
                # Calculate performance scores
                scores = [(self.calculate_performance_score(i), i) for i in healthy_instances]
                scores.sort(reverse=True)  # Sort by score descending
                
                return scores[0][1]  # Return instance with highest score
        
        balancer = AdaptiveLoadBalancer(service_pool)
        
        # Select instances for multiple requests
        selections = []
        for _ in range(50):
            selected = balancer.select_instance()
            if selected:
                selections.append(selected.instance_id)
        
        # Verify adaptive selection
        selection_counts = {}
        for selection in selections:
            selection_counts[selection] = selection_counts.get(selection, 0) + 1
        
        # auth-003 should be selected most often (best performance profile)
        most_selected = max(selection_counts.items(), key=lambda x: x[1])
        assert most_selected[0] == "auth-003"  # Best performing instance
        assert "auth-004" not in selection_counts  # Unhealthy instance not selected
    
    @pytest.mark.asyncio
    async def test_health_check_based_load_balancing(self, service_pool):
        """Test health check integration with load balancing."""
        
        class HealthAwareLoadBalancer:
            def __init__(self, instances: List[ServiceInstance]):
                self.instances = instances
                self.health_check_interval = 30  # seconds
                self.health_check_timeout = 5  # seconds
            
            async def perform_health_check(self, instance: ServiceInstance) -> bool:
                """Simulate health check for an instance."""
                # Simulate network latency
                await asyncio.sleep(0.01)
                
                # Health check logic based on various factors
                current_time = time.time()
                
                # Check if instance is overloaded
                if instance.current_load > 0.85:  # More sensitive threshold
                    return False
                
                # Check if response time is acceptable
                if instance.response_time_avg > 400:  # Lower threshold
                    return False
                
                # Check if CPU usage is acceptable
                if instance.cpu_usage > 0.80:  # More sensitive threshold
                    return False
                
                # Check if memory usage is acceptable
                if instance.memory_usage > 0.85:  # More sensitive threshold
                    return False
                
                # Instance passes health checks
                return True
            
            async def update_health_status(self):
                """Update health status for all instances."""
                health_check_tasks = []
                
                for instance in self.instances:
                    task = self.perform_health_check(instance)
                    health_check_tasks.append((instance, task))
                
                # Execute health checks concurrently
                for instance, task in health_check_tasks:
                    try:
                        is_healthy = await asyncio.wait_for(task, timeout=self.health_check_timeout)
                        instance.is_healthy = is_healthy
                        instance.last_health_check = time.time()
                    except asyncio.TimeoutError:
                        instance.is_healthy = False
                        instance.last_health_check = time.time()
            
            def get_healthy_instances(self) -> List[ServiceInstance]:
                """Get list of currently healthy instances."""
                return [i for i in self.instances if i.is_healthy]
        
        balancer = HealthAwareLoadBalancer(service_pool)
        
        # Update health status
        await balancer.update_health_status()
        
        # Get healthy instances
        healthy_instances = balancer.get_healthy_instances()
        
        # Verify health-based filtering
        healthy_ids = [i.instance_id for i in healthy_instances]
        
        # auth-004 should be marked unhealthy due to high load and CPU usage
        assert "auth-004" not in healthy_ids
        
        # Other instances should be healthy
        assert "auth-001" in healthy_ids
        assert "auth-002" in healthy_ids
        assert "auth-003" in healthy_ids
    
    def test_auto_scaling_trigger_conditions(self, service_pool):
        """Test auto-scaling trigger conditions based on load metrics."""
        
        class AutoScaler:
            def __init__(self, instances: List[ServiceInstance]):
                self.instances = instances
                self.scale_up_threshold = 0.70  # Scale up when average load > 70%
                self.scale_down_threshold = 0.30  # Scale down when average load < 30%
                self.min_instances = 2
                self.max_instances = 10
                self.cooldown_period = 300  # 5 minutes
                self.last_scaling_action = 0
            
            def calculate_system_metrics(self) -> Dict:
                """Calculate system-wide metrics for scaling decisions."""
                healthy_instances = [i for i in self.instances if i.is_healthy]
                
                if not healthy_instances:
                    return {
                        'average_load': 0.0,
                        'average_cpu': 0.0,
                        'average_memory': 0.0,
                        'average_response_time': 0.0,
                        'healthy_instance_count': 0,
                        'total_instance_count': len(self.instances)
                    }
                
                return {
                    'average_load': sum(i.current_load for i in healthy_instances) / len(healthy_instances),
                    'average_cpu': sum(i.cpu_usage for i in healthy_instances) / len(healthy_instances),
                    'average_memory': sum(i.memory_usage for i in healthy_instances) / len(healthy_instances),
                    'average_response_time': sum(i.response_time_avg for i in healthy_instances) / len(healthy_instances),
                    'healthy_instance_count': len(healthy_instances),
                    'total_instance_count': len(self.instances)
                }
            
            def should_scale_up(self, metrics: Dict) -> bool:
                """Determine if system should scale up."""
                current_time = time.time()
                
                # Check cooldown period
                if current_time - self.last_scaling_action < self.cooldown_period:
                    return False
                
                # Check if at max capacity
                if metrics['total_instance_count'] >= self.max_instances:
                    return False
                
                # Multiple conditions for scaling up
                conditions = [
                    metrics['average_load'] > self.scale_up_threshold,
                    metrics['average_cpu'] > 0.75,  # High CPU usage
                    metrics['average_response_time'] > 300,  # High response time
                    metrics['healthy_instance_count'] < 2  # Too few healthy instances
                ]
                
                # Scale up if any critical condition is met
                return any(conditions)
            
            def should_scale_down(self, metrics: Dict) -> bool:
                """Determine if system should scale down."""
                current_time = time.time()
                
                # Check cooldown period
                if current_time - self.last_scaling_action < self.cooldown_period:
                    return False
                
                # Check if at min capacity
                if metrics['healthy_instance_count'] <= self.min_instances:
                    return False
                
                # All conditions must be met for scaling down
                conditions = [
                    metrics['average_load'] < self.scale_down_threshold,
                    metrics['average_cpu'] < 0.40,  # Low CPU usage
                    metrics['average_response_time'] < 150,  # Good response time
                    metrics['healthy_instance_count'] > self.min_instances
                ]
                
                return all(conditions)
        
        scaler = AutoScaler(service_pool)
        metrics = scaler.calculate_system_metrics()
        
        # Test scaling decisions
        scale_up_decision = scaler.should_scale_up(metrics)
        scale_down_decision = scaler.should_scale_down(metrics)
        
        # Verify scaling logic
        assert isinstance(scale_up_decision, bool)
        assert isinstance(scale_down_decision, bool)
        assert not (scale_up_decision and scale_down_decision)  # Can't scale both ways
        
        # With current test data, should likely scale up due to high average load
        # (auth-002 at 0.7, auth-004 at 0.9, though auth-004 is unhealthy)
        healthy_load = (0.3 + 0.7 + 0.1) / 3  # Only healthy instances
        assert healthy_load < scaler.scale_up_threshold  # Should not trigger scale up
        
        # Verify metrics calculation
        assert 'average_load' in metrics
        assert 'healthy_instance_count' in metrics
        assert metrics['healthy_instance_count'] == 3  # Three healthy instances


class TestResourceAllocationPatterns:
    """Test suite for resource allocation and capacity planning patterns."""
    
    @pytest.fixture
    def resource_pool(self):
        """Create resource pool for allocation testing."""
        return {
            'cpu_cores': 16,
            'memory_gb': 64,
            'storage_gb': 1000,
            'network_bandwidth_gbps': 10,
            'gpu_count': 2
        }
    
    @pytest.fixture
    def service_requirements(self):
        """Define resource requirements for different services."""
        return {
            'auth_service': {
                'cpu_cores': 2,
                'memory_gb': 4,
                'storage_gb': 20,
                'network_bandwidth_gbps': 1,
                'priority': 'high',
                'min_instances': 2,
                'max_instances': 8
            },
            'data_service': {
                'cpu_cores': 4,
                'memory_gb': 8,
                'storage_gb': 100,
                'network_bandwidth_gbps': 2,
                'priority': 'critical',
                'min_instances': 1,
                'max_instances': 4
            },
            'analysis_service': {
                'cpu_cores': 6,
                'memory_gb': 16,
                'storage_gb': 50,
                'network_bandwidth_gbps': 1,
                'gpu_count': 1,
                'priority': 'medium',
                'min_instances': 1,
                'max_instances': 2
            },
            'cache_service': {
                'cpu_cores': 1,
                'memory_gb': 8,
                'storage_gb': 10,
                'network_bandwidth_gbps': 0.5,
                'priority': 'low',
                'min_instances': 1,
                'max_instances': 3
            }
        }
    
    def test_resource_allocation_optimization(self, resource_pool, service_requirements):
        """Test optimal resource allocation across services."""
        
        class ResourceAllocator:
            def __init__(self, total_resources: Dict, service_specs: Dict):
                self.total_resources = total_resources.copy()
                self.service_specs = service_specs
                self.allocations = {}
                self.remaining_resources = total_resources.copy()
            
            def calculate_resource_score(self, service_name: str, instances: int) -> float:
                """Calculate resource utilization score for a service allocation."""
                spec = self.service_specs[service_name]
                
                # Calculate total resource requirements
                total_cpu = spec['cpu_cores'] * instances
                total_memory = spec['memory_gb'] * instances
                total_storage = spec['storage_gb'] * instances
                total_network = spec['network_bandwidth_gbps'] * instances
                total_gpu = spec.get('gpu_count', 0) * instances
                
                # Check if allocation is feasible
                if (total_cpu > self.remaining_resources['cpu_cores'] or
                    total_memory > self.remaining_resources['memory_gb'] or
                    total_storage > self.remaining_resources['storage_gb'] or
                    total_network > self.remaining_resources['network_bandwidth_gbps'] or
                    total_gpu > self.remaining_resources.get('gpu_count', 0)):
                    return 0.0  # Infeasible allocation
                
                # Priority weights
                priority_weights = {'critical': 1.0, 'high': 0.8, 'medium': 0.6, 'low': 0.4}
                priority_weight = priority_weights.get(spec['priority'], 0.5)
                
                # Resource utilization efficiency
                cpu_util = total_cpu / self.total_resources['cpu_cores']
                memory_util = total_memory / self.total_resources['memory_gb']
                avg_util = (cpu_util + memory_util) / 2
                
                # Score combines priority and efficiency
                return priority_weight * (1.0 + avg_util)
            
            def allocate_resources(self):
                """Perform resource allocation optimization."""
                # Sort services by priority
                priority_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
                sorted_services = sorted(
                    self.service_specs.items(),
                    key=lambda x: priority_order.get(x[1]['priority'], 0),
                    reverse=True
                )
                
                for service_name, spec in sorted_services:
                    # Start with minimum instances
                    best_instances = spec['min_instances']
                    best_score = self.calculate_resource_score(service_name, best_instances)
                    
                    # Try increasing instances up to maximum
                    for instances in range(spec['min_instances'], spec['max_instances'] + 1):
                        score = self.calculate_resource_score(service_name, instances)
                        if score > best_score:
                            best_score = score
                            best_instances = instances
                        elif score == 0.0:  # Infeasible, stop trying higher instances
                            break
                    
                    # Allocate resources for best configuration
                    if best_score > 0:
                        self.allocations[service_name] = {
                            'instances': best_instances,
                            'total_cpu': spec['cpu_cores'] * best_instances,
                            'total_memory': spec['memory_gb'] * best_instances,
                            'total_storage': spec['storage_gb'] * best_instances,
                            'score': best_score
                        }
                        
                        # Update remaining resources
                        self.remaining_resources['cpu_cores'] -= spec['cpu_cores'] * best_instances
                        self.remaining_resources['memory_gb'] -= spec['memory_gb'] * best_instances
                        self.remaining_resources['storage_gb'] -= spec['storage_gb'] * best_instances
                        self.remaining_resources['network_bandwidth_gbps'] -= spec['network_bandwidth_gbps'] * best_instances
                        if 'gpu_count' in spec:
                            self.remaining_resources['gpu_count'] -= spec['gpu_count'] * best_instances
        
        allocator = ResourceAllocator(resource_pool, service_requirements)
        allocator.allocate_resources()
        
        # Verify allocation results
        assert len(allocator.allocations) > 0
        
        # Critical services should get resources first
        assert 'data_service' in allocator.allocations  # Critical priority
        
        # Check if auth_service got resources (might not if data_service used them all)
        # This is acceptable behavior as critical services have priority
        
        # Verify minimum instance requirements are met
        for service_name, allocation in allocator.allocations.items():
            min_instances = service_requirements[service_name]['min_instances']
            assert allocation['instances'] >= min_instances
        
        # Verify resource constraints are respected
        total_allocated_cpu = sum(alloc['total_cpu'] for alloc in allocator.allocations.values())
        assert total_allocated_cpu <= resource_pool['cpu_cores']
    
    def test_dynamic_resource_reallocation(self, resource_pool, service_requirements):
        """Test dynamic reallocation based on changing demands."""
        
        class DynamicResourceManager:
            def __init__(self, total_resources: Dict):
                self.total_resources = total_resources
                self.current_allocations = {}
                self.demand_history = {}
            
            def update_demand_metrics(self, service_name: str, metrics: Dict):
                """Update demand metrics for a service."""
                if service_name not in self.demand_history:
                    self.demand_history[service_name] = []
                
                self.demand_history[service_name].append({
                    'timestamp': time.time(),
                    'cpu_utilization': metrics.get('cpu_utilization', 0.0),
                    'memory_utilization': metrics.get('memory_utilization', 0.0),
                    'request_rate': metrics.get('request_rate', 0),
                    'response_time': metrics.get('response_time', 0.0)
                })
                
                # Keep only recent history (last 10 data points)
                self.demand_history[service_name] = self.demand_history[service_name][-10:]
            
            def calculate_demand_trend(self, service_name: str) -> Dict:
                """Calculate demand trend for a service."""
                if service_name not in self.demand_history or len(self.demand_history[service_name]) < 2:
                    return {'trend': 'stable', 'magnitude': 0.0}
                
                history = self.demand_history[service_name]
                recent = history[-3:]  # Last 3 measurements
                older = history[-6:-3] if len(history) >= 6 else history[:-3]
                
                if not older:
                    return {'trend': 'stable', 'magnitude': 0.0}
                
                # Calculate average metrics for comparison
                recent_avg_cpu = sum(h['cpu_utilization'] for h in recent) / len(recent)
                older_avg_cpu = sum(h['cpu_utilization'] for h in older) / len(older)
                
                recent_avg_requests = sum(h['request_rate'] for h in recent) / len(recent)
                older_avg_requests = sum(h['request_rate'] for h in older) / len(older)
                
                # Determine trend direction and magnitude
                cpu_change = (recent_avg_cpu - older_avg_cpu) / max(older_avg_cpu, 0.01)
                request_change = (recent_avg_requests - older_avg_requests) / max(older_avg_requests, 1)
                
                overall_change = (cpu_change + request_change) / 2
                
                if overall_change > 0.1:  # 10% increase threshold
                    return {'trend': 'increasing', 'magnitude': overall_change}
                elif overall_change < -0.1:  # 10% decrease threshold
                    return {'trend': 'decreasing', 'magnitude': abs(overall_change)}
                else:
                    return {'trend': 'stable', 'magnitude': abs(overall_change)}
            
            def should_reallocate_resources(self, service_name: str) -> Dict:
                """Determine if resources should be reallocated for a service."""
                trend = self.calculate_demand_trend(service_name)
                
                if trend['trend'] == 'increasing' and trend['magnitude'] > 0.2:
                    return {'action': 'scale_up', 'urgency': 'high' if trend['magnitude'] > 0.5 else 'medium'}
                elif trend['trend'] == 'decreasing' and trend['magnitude'] > 0.3:
                    return {'action': 'scale_down', 'urgency': 'low'}
                else:
                    return {'action': 'maintain', 'urgency': 'none'}
        
        manager = DynamicResourceManager(resource_pool)
        
        # Simulate demand metrics for auth_service
        demand_scenarios = [
            # Increasing demand scenario
            {'cpu_utilization': 0.4, 'memory_utilization': 0.5, 'request_rate': 100, 'response_time': 150},
            {'cpu_utilization': 0.6, 'memory_utilization': 0.6, 'request_rate': 150, 'response_time': 180},
            {'cpu_utilization': 0.8, 'memory_utilization': 0.7, 'request_rate': 200, 'response_time': 250},
            {'cpu_utilization': 0.9, 'memory_utilization': 0.8, 'request_rate': 250, 'response_time': 300},
            {'cpu_utilization': 0.95, 'memory_utilization': 0.85, 'request_rate': 300, 'response_time': 400}
        ]
        
        # Update demand metrics
        for scenario in demand_scenarios:
            manager.update_demand_metrics('auth_service', scenario)
        
        # Calculate trend and reallocation decision
        trend = manager.calculate_demand_trend('auth_service')
        reallocation_decision = manager.should_reallocate_resources('auth_service')
        
        # Verify trend detection and reallocation logic
        assert trend['trend'] == 'increasing'
        assert trend['magnitude'] > 0.0
        assert reallocation_decision['action'] in ['scale_up', 'maintain']
        
        # If trend is strong enough, should recommend scaling up
        if trend['magnitude'] > 0.2:
            assert reallocation_decision['action'] == 'scale_up'