"""Canonical PerformanceMetrics type definition.

This is the single source of truth for performance metrics across the system.
All other PerformanceMetrics definitions should be removed and replaced with imports from here.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class PerformanceMetrics:
    """Canonical performance metrics container - SSOT for all performance tracking.
    
    This combines the most commonly used performance metrics fields from across
    the codebase. Use this instead of creating new PerformanceMetrics classes.
    """
    # Time-based metrics
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Latency metrics (percentiles)
    latency_p50: float = 0.0
    latency_p95: float = 0.0  
    latency_p99: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    
    # Throughput metrics
    throughput_ops_per_second: float = 0.0
    throughput_rps: float = 0.0  # requests per second alias
    request_count: int = 0
    total_requests: int = 0
    
    # Success/Error metrics
    success_count: int = 0
    failure_count: int = 0
    error_rate: float = 0.0  # percentage
    success_rate: float = 100.0  # percentage
    
    # Resource usage metrics
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    active_connections: int = 0
    
    # Availability metrics
    availability: float = 99.9  # percentage
    
    # User/load metrics
    concurrent_users: int = 1
    
    def __post_init__(self):
        """Calculate derived metrics after initialization."""
        # Calculate error rate if we have request counts
        if self.total_requests > 0:
            self.error_rate = (self.failure_count / self.total_requests) * 100
            self.success_rate = 100.0 - self.error_rate
        
        # Sync request count fields
        if self.request_count > 0 and self.total_requests == 0:
            self.total_requests = self.request_count
        elif self.total_requests > 0 and self.request_count == 0:
            self.request_count = self.total_requests
            
        # Sync throughput fields
        if self.throughput_ops_per_second > 0 and self.throughput_rps == 0:
            self.throughput_rps = self.throughput_ops_per_second
        elif self.throughput_rps > 0 and self.throughput_ops_per_second == 0:
            self.throughput_ops_per_second = self.throughput_rps