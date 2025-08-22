"""Gateway Metrics Service for API Gateway monitoring."""

import time
from collections import defaultdict
from typing import Dict, Optional


class GatewayMetrics:
    """Collects and manages API gateway metrics."""
    
    def __init__(self):
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, list] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.status_codes: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        
    def record_request(self, endpoint: str, method: str = "GET"):
        """Record a request to an endpoint."""
        key = f"{method}:{endpoint}"
        self.request_counts[key] += 1
    
    def record_response(self, endpoint: str, status_code: int, response_time: float, method: str = "GET"):
        """Record a response from an endpoint."""
        key = f"{method}:{endpoint}"
        self.response_times[key].append(response_time)
        self.status_codes[key][status_code] += 1
        
        if status_code >= 400:
            self.error_counts[key] += 1
    
    def get_endpoint_metrics(self, endpoint: str, method: str = "GET") -> Dict:
        """Get metrics for a specific endpoint."""
        key = f"{method}:{endpoint}"
        
        avg_response_time = 0
        if self.response_times[key]:
            avg_response_time = sum(self.response_times[key]) / len(self.response_times[key])
        
        total_requests = self.request_counts[key]
        error_rate = self.error_counts[key] / total_requests if total_requests > 0 else 0
        
        return {
            "endpoint": endpoint,
            "method": method,
            "total_requests": total_requests,
            "errors": self.error_counts[key],
            "error_rate": error_rate,
            "avg_response_time": avg_response_time,
            "status_codes": dict(self.status_codes[key])
        }
    
    def reset(self, endpoint: Optional[str] = None, method: Optional[str] = None):
        """Reset metrics for a specific endpoint or all endpoints."""
        if endpoint and method:
            key = f"{method}:{endpoint}"
            self.request_counts[key] = 0
            self.response_times[key] = []
            self.error_counts[key] = 0
            self.status_codes[key] = defaultdict(int)
        else:
            self.request_counts.clear()
            self.response_times.clear()
            self.error_counts.clear()
            self.status_codes.clear()


class GatewayMetricsService:
    """Service interface for gateway metrics collection."""
    
    def __init__(self):
        self.metrics = GatewayMetrics()
    
    async def record_request(self, endpoint: str, method: str = "GET"):
        """Record an incoming request."""
        self.metrics.record_request(endpoint, method)
    
    async def record_response(self, endpoint: str, status_code: int, response_time: float, method: str = "GET"):
        """Record a response."""
        self.metrics.record_response(endpoint, status_code, response_time, method)
    
    async def get_endpoint_metrics(self, endpoint: str, method: str = "GET") -> Dict:
        """Get metrics for an endpoint."""
        return self.metrics.get_endpoint_metrics(endpoint, method)
    
    async def get_all_metrics(self) -> Dict:
        """Get all gateway metrics."""
        all_metrics = {}
        
        # Get unique endpoints
        endpoints = set()
        for key in self.metrics.request_counts.keys():
            endpoints.add(key)
        
        for key in endpoints:
            if ":" in key:
                method, endpoint = key.split(":", 1)
                all_metrics[key] = self.metrics.get_endpoint_metrics(endpoint, method)
        
        return all_metrics
    
    async def reset_metrics(self, endpoint: Optional[str] = None, method: Optional[str] = None):
        """Reset metrics."""
        self.metrics.reset(endpoint, method)