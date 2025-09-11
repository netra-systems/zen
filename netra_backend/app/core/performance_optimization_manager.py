"""
Performance optimization management system.
Provides performance monitoring and optimization recommendations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from netra_backend.app.logging_config import central_logger
# Import MemoryCache for compatibility export
from netra_backend.app.core.performance_cache import MemoryCache

logger = central_logger.get_logger(__name__)


class PerformanceOptimizationManager:
    """Manages performance optimization strategies and recommendations."""
    
    def __init__(self):
        self._metrics_history: List[Dict[str, Any]] = []
        self._optimization_recommendations: List[Dict[str, Any]] = []
        logger.debug("Initialized PerformanceOptimizationManager")
    
    async def initialize(self) -> None:
        """Initialize the performance optimization manager."""
        logger.info("PerformanceOptimizationManager initialized")
    
    async def record_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record performance metrics for analysis."""
        metrics_with_timestamp = {
            **metrics,
            "timestamp": datetime.utcnow()
        }
        self._metrics_history.append(metrics_with_timestamp)
        
        # Keep only last 1000 entries
        if len(self._metrics_history) > 1000:
            self._metrics_history = self._metrics_history[-1000:]
        
        logger.debug(f"Recorded performance metrics: {len(metrics)} entries")
    
    async def get_performance_summary(self, time_window_hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for specified time window."""
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_metrics = [
            m for m in self._metrics_history 
            if m.get("timestamp", datetime.min) > cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "summary": "No recent metrics available",
                "metrics_count": 0,
                "time_window_hours": time_window_hours
            }
        
        return {
            "metrics_count": len(recent_metrics),
            "time_window_hours": time_window_hours,
            "avg_response_time": self._calculate_avg_response_time(recent_metrics),
            "error_rate": self._calculate_error_rate(recent_metrics),
            "throughput": self._calculate_throughput(recent_metrics),
            "resource_utilization": self._calculate_resource_utilization(recent_metrics)
        }
    
    def _calculate_avg_response_time(self, metrics: List[Dict[str, Any]]) -> float:
        """Calculate average response time from metrics."""
        response_times = [
            m.get("response_time_ms", 0) for m in metrics 
            if "response_time_ms" in m
        ]
        return sum(response_times) / len(response_times) if response_times else 0.0
    
    def _calculate_error_rate(self, metrics: List[Dict[str, Any]]) -> float:
        """Calculate error rate from metrics."""
        total_requests = len(metrics)
        error_requests = len([m for m in metrics if m.get("has_error", False)])
        return error_requests / total_requests if total_requests > 0 else 0.0
    
    def _calculate_throughput(self, metrics: List[Dict[str, Any]]) -> float:
        """Calculate throughput (requests per minute)."""
        if not metrics:
            return 0.0
        
        time_span = (
            max(m.get("timestamp", datetime.min) for m in metrics) -
            min(m.get("timestamp", datetime.min) for m in metrics)
        ).total_seconds() / 60.0  # Convert to minutes
        
        return len(metrics) / max(time_span, 1.0)
    
    def _calculate_resource_utilization(self, metrics: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate resource utilization metrics."""
        cpu_values = [m.get("cpu_percent", 0) for m in metrics if "cpu_percent" in m]
        memory_values = [m.get("memory_mb", 0) for m in metrics if "memory_mb" in m]
        
        return {
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
            "avg_memory_mb": sum(memory_values) / len(memory_values) if memory_values else 0.0
        }
    
    async def generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations."""
        summary = await self.get_performance_summary(time_window_hours=24)
        recommendations = []
        
        # Check response time
        avg_response_time = summary.get("avg_response_time", 0)
        if avg_response_time > 5000:  # 5 seconds
            recommendations.append({
                "type": "response_time",
                "severity": "high",
                "message": f"High response time detected ({avg_response_time:.1f}ms). Consider optimizing queries or adding caching.",
                "metric_value": avg_response_time,
                "threshold": 5000
            })
        
        # Check error rate
        error_rate = summary.get("error_rate", 0)
        if error_rate > 0.05:  # 5%
            recommendations.append({
                "type": "error_rate",
                "severity": "critical",
                "message": f"High error rate detected ({error_rate:.1%}). Review error logs and implement fixes.",
                "metric_value": error_rate,
                "threshold": 0.05
            })
        
        # Check resource utilization
        resource_util = summary.get("resource_utilization", {})
        cpu_percent = resource_util.get("avg_cpu_percent", 0)
        if cpu_percent > 80:
            recommendations.append({
                "type": "cpu_utilization",
                "severity": "medium",
                "message": f"High CPU utilization detected ({cpu_percent:.1f}%). Consider scaling or optimizing CPU-intensive operations.",
                "metric_value": cpu_percent,
                "threshold": 80
            })
        
        self._optimization_recommendations = recommendations
        logger.info(f"Generated {len(recommendations)} optimization recommendations")
        
        return recommendations
    
    async def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report."""
        summary = await self.get_performance_summary(time_window_hours=24)
        recommendations = await self.generate_optimization_recommendations()
        
        return {
            "performance_summary": summary,
            "recommendations": recommendations,
            "report_timestamp": datetime.utcnow(),
            "metrics_analyzed": len(self._metrics_history)
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the performance optimization manager."""
        try:
            # Clear metrics history to free memory
            self._metrics_history.clear()
            self._optimization_recommendations.clear()
            logger.info("PerformanceOptimizationManager shutdown complete")
        except Exception as e:
            logger.error(f"Error during PerformanceOptimizationManager shutdown: {e}")
            # Continue shutdown even if error occurs


# Global instance
performance_manager = PerformanceOptimizationManager()


__all__ = [
    "PerformanceOptimizationManager",
    "performance_manager",
    "MemoryCache",  # COMPATIBILITY EXPORT
]