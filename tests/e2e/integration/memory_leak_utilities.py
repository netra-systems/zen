"""
Memory Leak Detection Utilities

Utilities for detecting and analyzing memory leaks in tests.
"""

import psutil
import gc
import asyncio
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class MemoryLeakMetrics:
    """Memory leak metrics for testing."""
    baseline_mb: float
    current_mb: float
    peak_mb: float
    leak_detected: bool
    threshold_mb: float
    
    def leak_amount_mb(self) -> float:
        """Calculate leak amount in MB."""
        return self.current_mb - self.baseline_mb

class UserActivitySimulator:
    """Simulates user activity for memory leak testing."""
    
    def __init__(self, test_harness=None):
        self.test_harness = test_harness
        self.activity_count = 0
    
    async def simulate_user_session(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Simulate a user session."""
        start_time = asyncio.get_event_loop().time()
        actions_performed = 0
        
        while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
            await self._simulate_user_action()
            actions_performed += 1
            await asyncio.sleep(0.1)  # Small delay between actions
            
        return {
            "duration": duration_seconds,
            "actions_performed": actions_performed,
            "session_id": f"session_{self.activity_count}"
        }
    
    async def _simulate_user_action(self):
        """Simulate a single user action."""
        self.activity_count += 1
        # Mock user action - in real tests this would interact with the system

class MemoryLeakDetector:
    """Detect memory leaks during testing."""
    
    def __init__(self):
        self.baseline_memory = None
        self.peak_memory = 0
        self.process = psutil.Process()
        self.metrics = None
    
    def start_monitoring(self):
        """Start memory monitoring."""
        gc.collect()
        self.baseline_memory = self.process.memory_info().rss
        self.peak_memory = self.baseline_memory
    
    def check_for_leaks(self, threshold_mb: int = 50) -> MemoryLeakMetrics:
        """Check for memory leaks and return metrics."""
        gc.collect()
        current_memory = self.process.memory_info().rss
        
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
        
        if self.baseline_memory is None:
            # Return minimal metrics if no baseline
            self.metrics = MemoryLeakMetrics(
                baseline_mb=0.0,
                current_mb=current_memory / 1024 / 1024,
                peak_mb=current_memory / 1024 / 1024,
                leak_detected=False,
                threshold_mb=threshold_mb
            )
        else:
            leak_mb = (current_memory - self.baseline_memory) / 1024 / 1024
            self.metrics = MemoryLeakMetrics(
                baseline_mb=self.baseline_memory / 1024 / 1024,
                current_mb=current_memory / 1024 / 1024,
                peak_mb=self.peak_memory / 1024 / 1024,
                leak_detected=leak_mb > threshold_mb,
                threshold_mb=threshold_mb
            )
        
        return self.metrics
