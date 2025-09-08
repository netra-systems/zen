"""Memory recovery base classes, interfaces and core types.

Base components for memory monitoring and recovery system.
Provides enums, dataclasses, and abstract interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Tuple


class MemoryPressureLevel(Enum):
    """Levels of memory pressure."""
    LOW = "low"          # < 70% usage
    MODERATE = "moderate"  # 70-80% usage
    HIGH = "high"        # 80-90% usage
    CRITICAL = "critical"  # 90-95% usage
    EMERGENCY = "emergency"  # > 95% usage


class RecoveryAction(Enum):
    """Types of memory recovery actions."""
    GARBAGE_COLLECT = "garbage_collect"
    CLEAR_CACHES = "clear_caches"
    REDUCE_CONNECTIONS = "reduce_connections"
    PAUSE_NON_CRITICAL = "pause_non_critical"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


@dataclass
class MemoryThresholds:
    """Memory usage thresholds."""
    moderate_percent: float = 70.0
    high_percent: float = 80.0
    critical_percent: float = 90.0
    emergency_percent: float = 95.0
    gc_threshold_mb: int = 100  # MB increase to trigger GC


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time."""
    timestamp: datetime
    total_mb: float
    available_mb: float
    used_mb: float
    percent_used: float
    pressure_level: MemoryPressureLevel
    
    # Python-specific metrics
    gc_counts: Tuple[int, int, int]
    object_count: int
    
    # Process-specific metrics
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size


class MemoryRecoveryStrategy(ABC):
    """Abstract base for memory recovery strategies."""
    
    @abstractmethod
    async def can_apply(self, snapshot: MemorySnapshot) -> bool:
        """Check if this strategy can be applied."""
        pass
    
    @abstractmethod
    async def execute(self, snapshot: MemorySnapshot) -> Dict[str, Any]:
        """Execute the recovery strategy."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get strategy priority (lower = higher priority)."""
        pass


# Alias for backward compatibility
MemoryRecoveryBase = MemoryRecoveryStrategy