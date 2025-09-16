"""
Resource monitoring utilities for E2E testing.
Extracted from test_agent_resource_isolation.py and other files.
"""

import asyncio
import gc
import logging
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, NamedTuple, Optional

import psutil

logger = logging.getLogger(__name__)

@dataclass
class ResourceSnapshot:
    """Single point-in-time resource measurement"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    thread_count: int
    fd_count: int
    
    @classmethod
    def capture(cls) -> 'ResourceSnapshot':
        """Capture current system resources"""
        process = psutil.Process()
        return cls(
            timestamp=time.time(),
            cpu_percent=process.cpu_percent(),
            memory_mb=process.memory_info().rss / 1024 / 1024,
            thread_count=process.num_threads(),
            fd_count=process.num_fds() if hasattr(process, 'num_fds') else 0
        )

@dataclass 
class ResourceMonitor:
    """Continuous resource monitoring for tests"""
    interval_seconds: float = 1.0
    max_samples: int = 1000
    snapshots: deque = field(default_factory=lambda: deque(maxlen=1000))
    monitoring: bool = False
    _monitor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start continuous monitoring"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.debug("Resource monitoring started")
        
    async def stop(self):
        """Stop monitoring and return final stats"""
        if not self.monitoring:
            return {}
            
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
        logger.debug("Resource monitoring stopped")
        return self.get_statistics()
        
    async def _monitor_loop(self):
        """Internal monitoring loop"""
        try:
            while self.monitoring:
                snapshot = ResourceSnapshot.capture()
                self.snapshots.append(snapshot)
                await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            pass
            
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate resource usage statistics"""
        if not self.snapshots:
            return {}
            
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_mb for s in self.snapshots]
        thread_values = [s.thread_count for s in self.snapshots]
        
        return {
            "duration_seconds": self.snapshots[-1].timestamp - self.snapshots[0].timestamp,
            "sample_count": len(self.snapshots),
            "cpu": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values),
                "peak_sustained": max(cpu_values[-10:]) if len(cpu_values) >= 10 else max(cpu_values)
            },
            "memory": {
                "min_mb": min(memory_values),
                "max_mb": max(memory_values),
                "avg_mb": sum(memory_values) / len(memory_values),
                "growth_mb": memory_values[-1] - memory_values[0] if len(memory_values) > 1 else 0
            },
            "threads": {
                "min": min(thread_values),
                "max": max(thread_values),
                "avg": sum(thread_values) / len(thread_values)
            }
        }

@asynccontextmanager
async def resource_monitoring_context(interval: float = 1.0):
    """Context manager for resource monitoring"""
    monitor = ResourceMonitor(interval_seconds=interval)
    await monitor.start()
    try:
        yield monitor
    finally:
        stats = await monitor.stop()
        logger.info(f"Resource monitoring completed: {stats}")

class MemoryLeakDetector:
    """Detect memory leaks during test execution"""
    
    def __init__(self, threshold_mb: float = 50.0):
        self.threshold_mb = threshold_mb
        self.baseline_mb: Optional[float] = None
        self.measurements: List[float] = []
        
    def establish_baseline(self):
        """Establish memory baseline before test"""
        gc.collect()  # Force garbage collection
        self.baseline_mb = ResourceSnapshot.capture().memory_mb
        logger.debug(f"Memory baseline established: {self.baseline_mb:.2f} MB")
        
    def check_for_leak(self) -> Dict[str, Any]:
        """Check if memory usage indicates a leak"""
        if self.baseline_mb is None:
            raise ValueError("Baseline not established")
            
        gc.collect()  # Force garbage collection
        current_mb = ResourceSnapshot.capture().memory_mb
        growth_mb = current_mb - self.baseline_mb
        self.measurements.append(current_mb)
        
        result = {
            "baseline_mb": self.baseline_mb,
            "current_mb": current_mb,
            "growth_mb": growth_mb,
            "leak_detected": growth_mb > self.threshold_mb,
            "measurements": self.measurements.copy()
        }
        
        if result["leak_detected"]:
            logger.warning(f"Potential memory leak detected: {growth_mb:.2f} MB growth")
            
        return result

def check_resource_limits(cpu_limit: float = 80.0, memory_limit_mb: float = 1024.0) -> Dict[str, bool]:
    """Check if current resource usage exceeds limits"""
    snapshot = ResourceSnapshot.capture()
    
    return {
        "cpu_ok": snapshot.cpu_percent <= cpu_limit,
        "memory_ok": snapshot.memory_mb <= memory_limit_mb,
        "cpu_percent": snapshot.cpu_percent,
        "memory_mb": snapshot.memory_mb,
        "cpu_limit": cpu_limit,
        "memory_limit_mb": memory_limit_mb
    }

async def stress_system_resources(duration_seconds: float = 30.0, 
                                cpu_intensive: bool = True,
                                memory_intensive: bool = True) -> Dict[str, Any]:
    """Generate controlled system stress for testing"""
    start_time = time.time()
    tasks = []
    
    if cpu_intensive:
        tasks.append(asyncio.create_task(_cpu_stress_task(duration_seconds)))
        
    if memory_intensive:
        tasks.append(asyncio.create_task(_memory_stress_task(duration_seconds)))
        
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
        
    return {
        "duration_actual": time.time() - start_time,
        "duration_requested": duration_seconds,
        "cpu_stress_enabled": cpu_intensive,
        "memory_stress_enabled": memory_intensive
    }

async def _cpu_stress_task(duration: float):
    """CPU-intensive task for stress testing"""
    end_time = time.time() + duration
    count = 0
    
    while time.time() < end_time:
        count += 1
        if count % 100000 == 0:  # Yield periodically
            await asyncio.sleep(0.001)

async def _memory_stress_task(duration: float):
    """Memory-intensive task for stress testing"""
    end_time = time.time() + duration
    memory_blocks = []
    
    try:
        while time.time() < end_time:
            # Allocate 1MB blocks
            block = bytearray(1024 * 1024)
            memory_blocks.append(block)
            
            # Keep only last 100 blocks to prevent excessive memory use
            if len(memory_blocks) > 100:
                memory_blocks.pop(0)
                
            await asyncio.sleep(0.1)
    finally:
        # Clean up allocated memory
        del memory_blocks
        gc.collect()
