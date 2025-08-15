"""WebSocket Batch Load Monitor.

System load monitoring for adaptive batching with micro-functions.
"""

import asyncio
import time
from typing import List, Tuple


class LoadMonitor:
    """Monitor system load for adaptive batching with micro-functions."""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self._load_history: List[Tuple[float, float]] = []  # (timestamp, load)
        self._lock = asyncio.Lock()
    
    async def record_load(self, load: float) -> None:
        """Record current load measurement."""
        async with self._lock:
            self._add_load_measurement(load)
            self._trim_old_entries()
    
    def _add_load_measurement(self, load: float) -> None:
        """Add load measurement to history."""
        now = time.time()
        self._load_history.append((now, load))
    
    def _trim_old_entries(self) -> None:
        """Remove old load entries outside window."""
        cutoff_time = time.time() - self.window_size
        self._load_history = [entry for entry in self._load_history if entry[0] > cutoff_time]
    
    def get_current_load(self) -> float:
        """Get current system load estimate."""
        if not self._load_history:
            return 0.0
        return self._calculate_weighted_average_load()
    
    def _calculate_weighted_average_load(self) -> float:
        """Calculate weighted average of recent load measurements."""
        total_weight, weighted_sum = self._compute_load_weights()
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _compute_load_weights(self) -> Tuple[float, float]:
        """Compute weights and weighted sum for load calculation."""
        now = time.time()
        total_weight = 0.0
        weighted_sum = 0.0
        
        for timestamp, load in self._load_history:
            weight = self._calculate_entry_weight(now, timestamp)
            weighted_sum += load * weight
            total_weight += weight
        
        return total_weight, weighted_sum
    
    def _calculate_entry_weight(self, now: float, timestamp: float) -> float:
        """Calculate weight for a load history entry."""
        age = now - timestamp
        return max(0, 1.0 - (age / self.window_size))  # Linear decay