"""Thread Performance Utilities for E2E Testing.

This module provides performance measurement utilities for thread-related testing.
"""

from typing import Dict, Any, List
import asyncio
import threading


class ThreadPerformanceUtils:
    """Thread Performance Utilities for E2E Testing.
    
    Provides performance measurement and analysis utilities for thread-related testing.
    Measures execution time, resource usage, and concurrency performance metrics.
    
    CRITICAL: This class enables performance validation for thread isolation and concurrent execution.
    Essential for Enterprise customers requiring multi-user concurrent system validation.
    """
    
    def __init__(self):
        """Initialize thread performance utilities."""
        self.performance_metrics = {}
        self.execution_times = {}
        self.resource_usage = {}
        self.concurrency_metrics = {}
    
    async def measure_thread_execution_time(self, thread_id: str, operation: callable) -> float:
        """Measure execution time for a thread operation.
        
        Args:
            thread_id: Thread identifier for tracking
            operation: Async operation to measure
            
        Returns:
            Execution time in seconds
        """
        import time
        start_time = time.perf_counter()
        
        try:
            result = await operation()
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Store metrics for analysis
            if thread_id not in self.execution_times:
                self.execution_times[thread_id] = []
            self.execution_times[thread_id].append(execution_time)
            
            return execution_time
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            print(f"Thread {thread_id} operation failed after {execution_time}s: {e}")
            return execution_time
    
    def measure_resource_usage(self, thread_id: str) -> Dict[str, Any]:
        """Measure resource usage for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Resource usage metrics
        """
        try:
            import psutil
            current_process = psutil.Process()
        except ImportError:
            # Fallback if psutil not available
            current_process = None
        
        current_thread = threading.current_thread()
        
        if current_process:
            metrics = {
                "memory_usage": current_process.memory_info().rss / 1024 / 1024,  # MB
                "cpu_percent": current_process.cpu_percent(),
                "thread_count": current_process.num_threads(),
                "thread_name": current_thread.name,
                "thread_id": thread_id
            }
        else:
            # Basic metrics without psutil
            metrics = {
                "memory_usage": 0,  # Placeholder
                "cpu_percent": 0,   # Placeholder
                "thread_count": threading.active_count(),
                "thread_name": current_thread.name,
                "thread_id": thread_id
            }
        
        # Store for analysis
        self.resource_usage[thread_id] = metrics
        return metrics
    
    def analyze_concurrency_performance(self, thread_results: Dict[str, List[float]]) -> Dict[str, Any]:
        """Analyze concurrency performance across multiple threads.
        
        Args:
            thread_results: Dictionary of thread_id -> execution times
            
        Returns:
            Concurrency performance analysis
        """
        import statistics
        
        if not thread_results:
            return {"error": "No thread results to analyze"}
        
        # Calculate statistics across all threads
        all_times = []
        thread_stats = {}
        
        for thread_id, times in thread_results.items():
            if times:
                thread_stats[thread_id] = {
                    "avg_time": statistics.mean(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
                    "total_operations": len(times)
                }
                all_times.extend(times)
        
        # Overall performance metrics
        if all_times:
            overall_stats = {
                "total_operations": len(all_times),
                "avg_execution_time": statistics.mean(all_times),
                "min_execution_time": min(all_times),
                "max_execution_time": max(all_times),
                "std_dev": statistics.stdev(all_times) if len(all_times) > 1 else 0,
                "total_threads": len(thread_results)
            }
        else:
            overall_stats = {"error": "No valid execution times"}
        
        analysis = {
            "overall": overall_stats,
            "per_thread": thread_stats,
            "concurrency_efficiency": self._calculate_concurrency_efficiency(thread_stats)
        }
        
        # Store for future reference
        self.concurrency_metrics = analysis
        return analysis
    
    def _calculate_concurrency_efficiency(self, thread_stats: Dict[str, Dict]) -> float:
        """Calculate concurrency efficiency metric.
        
        Args:
            thread_stats: Per-thread performance statistics
            
        Returns:
            Efficiency score (0.0 to 1.0)
        """
        if not thread_stats:
            return 0.0
        
        # Simple efficiency calculation: lower variance = higher efficiency
        avg_times = [stats["avg_time"] for stats in thread_stats.values()]
        if len(avg_times) <= 1:
            return 1.0
        
        import statistics
        mean_avg = statistics.mean(avg_times)
        if len(avg_times) < 2:
            return 1.0
            
        variance = statistics.variance(avg_times)
        
        # Normalize to 0-1 scale (lower variance = higher efficiency)
        if mean_avg == 0:
            return 1.0
        
        coefficient_of_variation = (variance ** 0.5) / mean_avg
        efficiency = max(0.0, 1.0 - min(1.0, coefficient_of_variation))
        
        return efficiency
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report.
        
        Returns:
            Complete performance analysis report
        """
        return {
            "execution_times": self.execution_times,
            "resource_usage": self.resource_usage,
            "concurrency_metrics": self.concurrency_metrics,
            "summary": {
                "total_threads_measured": len(self.execution_times),
                "total_resource_snapshots": len(self.resource_usage),
                "has_concurrency_analysis": bool(self.concurrency_metrics)
            }
        }
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics for fresh testing."""
        self.performance_metrics.clear()
        self.execution_times.clear()
        self.resource_usage.clear()
        self.concurrency_metrics.clear()