"""Load Testing Utilities - Supporting Module for Load Performance Tests

Utility classes and functions for load testing operations.
Separated from main test file to maintain 450-line architectural limit.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise (infrastructure scalability)
- Business Goal: Enable systematic load testing for growth validation
- Value Impact: Modular utilities enable comprehensive scalability testing
- Revenue Impact: Scalability validation prevents 100K+ ARR loss from outages

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (enforced through focused utility design)
- Function size: <8 lines each (enforced through composition)
- Modular design for reuse across load tests
"""

import asyncio
import gc
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psutil


@dataclass
class LoadMetrics:
    """Comprehensive load testing metrics tracker"""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    response_times: List[float] = field(default_factory=list)
    memory_samples: List[float] = field(default_factory=list)
    error_count: int = 0
    success_count: int = 0
    connections_peak: int = 0
    degraded_features: List[str] = field(default_factory=list)


class LoadPatternGenerator:
    """Generates realistic load patterns for testing"""
    
    def __init__(self, base_load: int = 10):
        self.base_load = base_load
        self.burst_multiplier = 5
        self.ramp_duration = 30  # seconds
    
    def generate_concurrent_pattern(self, duration: int) -> List[int]:
        """Generate concurrent user pattern over time"""
        pattern = []
        steps = duration // 5  # 5-second intervals
        for i in range(steps):
            load = self._calculate_load_at_time(i * 5)
            pattern.append(load)
        return pattern
    
    def generate_burst_pattern(self) -> List[int]:
        """Generate burst traffic pattern"""
        return [
            self.base_load,
            self.base_load * 2,
            self.base_load * self.burst_multiplier,
            self.base_load * 3,
            self.base_load
        ]
    
    def _calculate_load_at_time(self, elapsed: int) -> int:
        """Calculate load level at specific time"""
        if elapsed < self.ramp_duration:
            ramp_factor = elapsed / self.ramp_duration
            return int(self.base_load * ramp_factor)
        return self.base_load


class SystemResourceMonitor:
    """Monitors system resources during load testing"""
    
    def __init__(self):
        self.memory_samples: List[float] = []
        self.cpu_samples: List[float] = []
        self.monitoring = False
    
    async def start_monitoring(self, interval: float = 1.0):
        """Start continuous resource monitoring"""
        self.monitoring = True
        while self.monitoring:
            await self._collect_resource_sample()
            await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
    
    async def _collect_resource_sample(self):
        """Collect single resource measurement"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        self.memory_samples.append(memory_mb)
        self.cpu_samples.append(cpu_percent)


class LoadTestSimulator:
    """Core load test simulation engine"""
    
    def __init__(self, config):
        self.config = config
        self.metrics = LoadMetrics()
        self.resource_monitor = SystemResourceMonitor()
        self.active_users: List[str] = []
    
    async def simulate_concurrent_users(self, user_count: int) -> Dict[str, Any]:
        """Simulate specified number of concurrent users"""
        user_tasks = await self._create_user_tasks(user_count)
        results = await self._execute_user_tasks(user_tasks)
        return self._compile_user_results(results)
    
    async def simulate_sustained_load(self, duration_hours: int) -> Dict[str, Any]:
        """Simulate sustained load over extended period"""
        duration_seconds = duration_hours * 3600
        monitor_task = asyncio.create_task(
            self.resource_monitor.start_monitoring()
        )
        
        load_result = await self._run_sustained_simulation(duration_seconds)
        
        self.resource_monitor.stop_monitoring()
        await monitor_task
        return load_result
    
    async def _create_user_tasks(self, count: int) -> List[asyncio.Task]:
        """Create concurrent user simulation tasks"""
        tasks = []
        for i in range(count):
            user_id = f"load_user_{i}"
            task = asyncio.create_task(self._simulate_user_session(user_id))
            tasks.append(task)
        return tasks
    
    async def _execute_user_tasks(self, tasks: List[asyncio.Task]) -> List[Any]:
        """Execute all user tasks concurrently"""
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _simulate_user_session(self, user_id: str) -> Dict[str, Any]:
        """Simulate individual user session"""
        start_time = time.time()
        self.active_users.append(user_id)
        
        try:
            session_result = await self._execute_user_workflow(user_id)
            response_time = time.time() - start_time
            self.metrics.response_times.append(response_time)
            self.metrics.success_count += 1
            return session_result
        except Exception as e:
            self.metrics.error_count += 1
            return {"error": str(e), "user_id": user_id}
        finally:
            self.active_users.remove(user_id)
    
    async def _execute_user_workflow(self, user_id: str) -> Dict[str, Any]:
        """Execute standard user workflow"""
        workflow_steps = [
            self._perform_auth_flow,
            self._perform_message_exchange,
            self._perform_data_fetch
        ]
        
        results = {}
        for step in workflow_steps:
            step_result = await step(user_id)
            results.update(step_result)
        return results
    
    async def _perform_auth_flow(self, user_id: str) -> Dict[str, Any]:
        """Perform authentication workflow step"""
        await asyncio.sleep(0.1)  # Simulate auth time
        return {"auth_completed": True, "user_id": user_id}
    
    async def _perform_message_exchange(self, user_id: str) -> Dict[str, Any]:
        """Perform message exchange workflow step"""
        await asyncio.sleep(0.2)  # Simulate message processing
        return {"messages_sent": 5, "messages_received": 5}
    
    async def _perform_data_fetch(self, user_id: str) -> Dict[str, Any]:
        """Perform data fetch workflow step"""
        await asyncio.sleep(0.15)  # Simulate data fetch
        return {"data_fetched": True, "records_count": 10}
    
    async def _run_sustained_simulation(self, duration: int) -> Dict[str, Any]:
        """Run sustained load simulation for specified duration"""
        end_time = time.time() + duration
        simulation_results = []
        
        while time.time() < end_time:
            batch_result = await self.simulate_concurrent_users(10)
            simulation_results.append(batch_result)
            await asyncio.sleep(5)  # 5-second intervals
        
        return {"simulations_completed": len(simulation_results)}
    
    def _compile_user_results(self, results: List[Any]) -> Dict[str, Any]:
        """Compile results from user simulation tasks"""
        successful = sum(1 for r in results if isinstance(r, dict) and not r.get("error"))
        failed = len(results) - successful
        
        return {
            "total_users": len(results),
            "successful_sessions": successful,
            "failed_sessions": failed,
            "success_rate": (successful / len(results)) * 100 if results else 0,
            "avg_response_time": statistics.mean(self.metrics.response_times) if self.metrics.response_times else 0
        }


def calculate_p95_response_time(response_times: List[float]) -> float:
    """Calculate 95th percentile response time"""
    if not response_times:
        return 0.0
    return statistics.quantiles(sorted(response_times), n=20)[18]


def calculate_success_rate(success_count: int, error_count: int) -> float:
    """Calculate overall success rate percentage"""
    total = success_count + error_count
    if total == 0:
        return 0.0
    return (success_count / total) * 100


def analyze_memory_usage(initial: float, final: float, threshold: float) -> Dict[str, Any]:
    """Analyze memory usage patterns for leak detection"""
    memory_growth = final - initial
    
    return {
        "initial_memory_mb": initial,
        "final_memory_mb": final,
        "memory_growth_mb": memory_growth,
        "memory_leak_detected": memory_growth > threshold
    }


def detect_degraded_features() -> List[str]:
    """Detect which features were degraded under load"""
    # Mock feature degradation detection for testing
    return ["search_optimization", "real_time_analytics"]
