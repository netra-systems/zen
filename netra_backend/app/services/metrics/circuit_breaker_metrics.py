"""Circuit Breaker Metrics Collection Service."""

import time
from collections import defaultdict
from typing import Dict, List, Optional


class CircuitBreakerMetrics:
    """Collects and manages circuit breaker metrics."""
    
    def __init__(self):
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.state_changes: Dict[str, List[Dict]] = defaultdict(list)
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        
    def record_failure(self, circuit_name: str, error_type: Optional[str] = None):
        """Record a failure for the given circuit."""
        self.failure_counts[circuit_name] += 1
        self.state_changes[circuit_name].append({
            "event": "failure",
            "timestamp": time.time(),
            "error_type": error_type
        })
    
    def record_success(self, circuit_name: str, response_time: Optional[float] = None):
        """Record a success for the given circuit."""
        self.success_counts[circuit_name] += 1
        if response_time is not None:
            self.response_times[circuit_name].append(response_time)
        
        self.state_changes[circuit_name].append({
            "event": "success", 
            "timestamp": time.time(),
            "response_time": response_time
        })
    
    def record_state_change(self, circuit_name: str, old_state: str, new_state: str):
        """Record a circuit breaker state change."""
        self.state_changes[circuit_name].append({
            "event": "state_change",
            "timestamp": time.time(),
            "old_state": old_state,
            "new_state": new_state
        })
    
    def get_metrics(self, circuit_name: str) -> Dict:
        """Get metrics for a specific circuit."""
        total_requests = self.failure_counts[circuit_name] + self.success_counts[circuit_name]
        failure_rate = self.failure_counts[circuit_name] / total_requests if total_requests > 0 else 0
        
        avg_response_time = 0
        if self.response_times[circuit_name]:
            avg_response_time = sum(self.response_times[circuit_name]) / len(self.response_times[circuit_name])
        
        return {
            "circuit_name": circuit_name,
            "total_requests": total_requests,
            "failures": self.failure_counts[circuit_name],
            "successes": self.success_counts[circuit_name],
            "failure_rate": failure_rate,
            "avg_response_time": avg_response_time,
            "state_changes": len(self.state_changes[circuit_name])
        }
    
    def reset(self, circuit_name: Optional[str] = None):
        """Reset metrics for a circuit or all circuits."""
        if circuit_name:
            self.failure_counts[circuit_name] = 0
            self.success_counts[circuit_name] = 0
            self.state_changes[circuit_name] = []
            self.response_times[circuit_name] = []
        else:
            self.failure_counts.clear()
            self.success_counts.clear()
            self.state_changes.clear()
            self.response_times.clear()


class CircuitBreakerMetricsCollector:
    """Central collector for circuit breaker metrics."""
    
    def __init__(self):
        self.metrics = CircuitBreakerMetrics()
    
    async def collect_endpoint_metrics(self, endpoint: str) -> Dict:
        """Collect metrics for a specific endpoint."""
        return self.metrics.get_metrics(endpoint)
    
    async def record_endpoint_failure(self, endpoint: str, error_type: str = None):
        """Record failure for an endpoint."""
        self.metrics.record_failure(endpoint, error_type)
    
    async def record_endpoint_success(self, endpoint: str, response_time: float = None):
        """Record success for an endpoint."""
        self.metrics.record_success(endpoint, response_time)