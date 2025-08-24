"""Agent Startup Performance Measurer - Supporting Module

Performance measurement utilities for agent startup E2E tests.
Tracks timing, memory usage, and response performance metrics.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Ensure agent performance meets SLA requirements
- Value Impact: Identifies performance bottlenecks before production
- Revenue Impact: Protects customer satisfaction through performance validation

Architecture:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Focused on performance measurement and analysis
- Integration with system resource monitoring
"""

from dataclasses import dataclass
from netra_backend.app.monitoring.metrics_collector import PerformanceMetric
from tests.e2e.load_test_utilities import SystemResourceMonitor
from typing import Any, Dict, List
import asyncio
import statistics

@dataclass

class PerformanceMetrics:

    """Performance metrics container."""

    agent_init_time: float = 0.0

    service_ready_time: float = 0.0

    first_response_time: float = 0.0

    memory_usage_mb: float = 0.0

    error_count: int = 0


class PerformanceMeasurer:

    """Measures performance metrics for agent startup tests."""
    

    def __init__(self):

        self.metrics = PerformanceMetrics()

        self.response_times: List[float] = []

        self.resource_monitor = SystemResourceMonitor()

        self.measurement_started = False
        

    def start_measurement(self) -> None:

        """Start performance measurement tracking."""

        if not self.measurement_started:

            asyncio.create_task(self.resource_monitor.start_monitoring())

            self.measurement_started = True
            

    def stop_measurement(self) -> None:

        """Stop performance measurement tracking."""

        if self.measurement_started:

            self.resource_monitor.stop_monitoring()

            self.measurement_started = False
            

    def record_agent_init_time(self, duration: float) -> None:

        """Record agent initialization time."""

        self.metrics.agent_init_time = duration
        

    def record_service_ready_time(self, duration: float) -> None:

        """Record service readiness time."""

        self.metrics.service_ready_time = duration
        

    def record_response_time(self, response_time: float) -> None:

        """Record individual response time."""

        self.response_times.append(response_time)

        if not self.metrics.first_response_time:

            self.metrics.first_response_time = response_time
            

    def record_error(self) -> None:

        """Record performance-related error."""

        self.metrics.error_count += 1
        

    def record_memory_usage(self, memory_mb: float) -> None:

        """Record current memory usage."""

        self.metrics.memory_usage_mb = memory_mb
        

    def get_performance_summary(self) -> Dict[str, Any]:

        """Get comprehensive performance summary."""

        return {

            "agent_init_time": self.metrics.agent_init_time,

            "service_ready_time": self.metrics.service_ready_time,

            "first_response_time": self.metrics.first_response_time,

            "avg_response_time": self._calculate_avg_response_time(),

            "p95_response_time": self._calculate_p95_response_time(),

            "p99_response_time": self._calculate_p99_response_time(),

            "memory_usage_mb": self.metrics.memory_usage_mb,

            "error_count": self.metrics.error_count,

            "total_responses": len(self.response_times)

        }
        

    def get_sla_compliance(self, sla_thresholds: Dict[str, float]) -> Dict[str, bool]:

        """Check performance against SLA thresholds."""

        summary = self.get_performance_summary()

        compliance = {}
        

        for metric, threshold in sla_thresholds.items():

            if metric in summary:

                compliance[f"{metric}_compliant"] = summary[metric] <= threshold
                

        return compliance
        

    def reset_metrics(self) -> None:

        """Reset all performance metrics."""

        self.metrics = PerformanceMetrics()

        self.response_times.clear()
        

    def get_response_time_distribution(self) -> Dict[str, float]:

        """Get response time distribution statistics."""

        if not self.response_times:

            return {"min": 0, "max": 0, "median": 0, "std_dev": 0}
            

        sorted_times = sorted(self.response_times)

        return {

            "min": sorted_times[0],

            "max": sorted_times[-1],

            "median": statistics.median(sorted_times),

            "std_dev": statistics.stdev(sorted_times) if len(sorted_times) > 1 else 0

        }
        

    def _calculate_avg_response_time(self) -> float:

        """Calculate average response time."""

        return statistics.mean(self.response_times) if self.response_times else 0.0
        

    def _calculate_p95_response_time(self) -> float:

        """Calculate 95th percentile response time."""

        return self._calculate_percentile(0.95)
        

    def _calculate_p99_response_time(self) -> float:

        """Calculate 99th percentile response time."""

        return self._calculate_percentile(0.99)
        

    def _calculate_percentile(self, percentile: float) -> float:

        """Calculate specified percentile from response times."""

        if not self.response_times:

            return 0.0

        sorted_times = sorted(self.response_times)

        index = int(percentile * len(sorted_times))

        return sorted_times[min(index, len(sorted_times) - 1)]
