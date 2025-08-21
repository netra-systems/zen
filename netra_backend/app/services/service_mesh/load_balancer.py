"""Load Balancer Service for service mesh"""

import asyncio
import random
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"


class LoadBalancerService:
    """Load balancer for distributing requests across service instances"""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.service_instances: Dict[str, List[Dict[str, Any]]] = {}
        self.round_robin_counters: Dict[str, int] = {}
        self.connection_counts: Dict[str, int] = {}
        self.request_stats: Dict[str, int] = {}
    
    async def register_instance(self, service_name: str, instance: Dict[str, Any]) -> bool:
        """Register a service instance for load balancing"""
        if service_name not in self.service_instances:
            self.service_instances[service_name] = []
            self.round_robin_counters[service_name] = 0
        
        # Add instance if not already registered
        instance_id = instance.get("id", f"{instance.get('host', 'unknown')}:{instance.get('port', 0)}")
        instance_with_id = {**instance, "id": instance_id, "registered_at": datetime.now(UTC).isoformat()}
        
        # Check if instance already exists
        existing_ids = [inst.get("id") for inst in self.service_instances[service_name]]
        if instance_id not in existing_ids:
            self.service_instances[service_name].append(instance_with_id)
            self.connection_counts[instance_id] = 0
            return True
        return False
    
    async def unregister_instance(self, service_name: str, instance_id: str) -> bool:
        """Unregister a service instance"""
        if service_name not in self.service_instances:
            return False
        
        original_count = len(self.service_instances[service_name])
        self.service_instances[service_name] = [
            inst for inst in self.service_instances[service_name]
            if inst.get("id") != instance_id
        ]
        
        if instance_id in self.connection_counts:
            del self.connection_counts[instance_id]
        
        return len(self.service_instances[service_name]) < original_count
    
    async def get_instance(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get next instance based on load balancing strategy"""
        if service_name not in self.service_instances or not self.service_instances[service_name]:
            return None
        
        instances = self.service_instances[service_name]
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(service_name, instances)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random_select(instances)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(instances)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted_select(instances)
        
        return instances[0]  # Default fallback
    
    def _round_robin_select(self, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Round robin selection"""
        current_index = self.round_robin_counters[service_name] % len(instances)
        self.round_robin_counters[service_name] += 1
        return instances[current_index]
    
    def _random_select(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Random selection"""
        return random.choice(instances)
    
    def _least_connections_select(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Least connections selection"""
        min_connections = float('inf')
        selected_instance = instances[0]
        
        for instance in instances:
            instance_id = instance.get("id", "")
            connections = self.connection_counts.get(instance_id, 0)
            if connections < min_connections:
                min_connections = connections
                selected_instance = instance
        
        return selected_instance
    
    def _weighted_select(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Weighted selection based on instance weight"""
        total_weight = sum(instance.get("weight", 1) for instance in instances)
        if total_weight == 0:
            return random.choice(instances)
        
        random_weight = random.uniform(0, total_weight)
        current_weight = 0
        
        for instance in instances:
            current_weight += instance.get("weight", 1)
            if random_weight <= current_weight:
                return instance
        
        return instances[-1]  # Fallback
    
    async def track_request(self, service_name: str, instance_id: str) -> None:
        """Track request to an instance"""
        if instance_id in self.connection_counts:
            self.connection_counts[instance_id] += 1
        
        self.request_stats[service_name] = self.request_stats.get(service_name, 0) + 1
    
    async def finish_request(self, instance_id: str) -> None:
        """Mark request as finished for an instance"""
        if instance_id in self.connection_counts:
            self.connection_counts[instance_id] = max(0, self.connection_counts[instance_id] - 1)
    
    async def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """Get statistics for a service"""
        if service_name not in self.service_instances:
            return {"error": "Service not found"}
        
        instances = self.service_instances[service_name]
        total_requests = self.request_stats.get(service_name, 0)
        
        instance_stats = []
        for instance in instances:
            instance_id = instance.get("id", "")
            instance_stats.append({
                "id": instance_id,
                "host": instance.get("host", ""),
                "port": instance.get("port", 0),
                "active_connections": self.connection_counts.get(instance_id, 0),
                "weight": instance.get("weight", 1)
            })
        
        return {
            "service_name": service_name,
            "strategy": self.strategy.value,
            "total_instances": len(instances),
            "total_requests": total_requests,
            "instances": instance_stats
        }
    
    async def update_instance_health(self, service_name: str, instance_id: str, is_healthy: bool) -> bool:
        """Update health status of an instance"""
        if service_name not in self.service_instances:
            return False
        
        for instance in self.service_instances[service_name]:
            if instance.get("id") == instance_id:
                instance["healthy"] = is_healthy
                instance["last_health_check"] = datetime.now(UTC).isoformat()
                return True
        
        return False
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get overall load balancer statistics"""
        total_instances = sum(len(instances) for instances in self.service_instances.values())
        total_requests = sum(self.request_stats.values())
        
        return {
            "strategy": self.strategy.value,
            "total_services": len(self.service_instances),
            "total_instances": total_instances,
            "total_requests": total_requests,
            "services": list(self.service_instances.keys())
        }