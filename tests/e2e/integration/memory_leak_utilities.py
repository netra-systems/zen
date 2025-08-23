"""
Memory Leak Detection Utilities

Utilities for detecting and analyzing memory leaks in tests.
"""

import psutil
import gc
from typing import Dict, Any

class MemoryLeakDetector:
    """Detect memory leaks during testing."""
    
    def __init__(self):
        self.baseline_memory = None
        self.process = psutil.Process()
    
    def start_monitoring(self):
        """Start memory monitoring."""
        gc.collect()
        self.baseline_memory = self.process.memory_info().rss
    
    def check_for_leaks(self, threshold_mb: int = 50) -> Dict[str, Any]:
        """Check for memory leaks."""
        gc.collect()
        current_memory = self.process.memory_info().rss
        
        if self.baseline_memory is None:
            return {"status": "no_baseline"}
        
        leak_mb = (current_memory - self.baseline_memory) / 1024 / 1024
        
        return {
            "status": "leak" if leak_mb > threshold_mb else "ok",
            "leak_mb": leak_mb,
            "current_mb": current_memory / 1024 / 1024,
            "baseline_mb": self.baseline_memory / 1024 / 1024
        }
