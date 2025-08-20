"""Core Tests - Split from test_agent_resource_cleanup_integration.py

Business Value Justification (BVJ):
1. Segment: Platform/Infrastructure ($10K MRR protection)
2. Business Goal: Prevent memory leaks and resource exhaustion in production
3. Value Impact: Ensures system stability and prevents downtime from resource exhaustion
4. Strategic Impact: Protects $10K MRR through validated resource management

COMPLIANCE: File size <300 lines, Functions <8 lines, Real resource testing
"""

import asyncio
import time
import gc
import psutil
import os
from typing import Dict, Any, List, Optional
import pytest
from app.agents.base import BaseSubAgent
from app.agents.supervisor.supervisor_agent import SupervisorAgent
from app.llm.llm_manager import LLMManager
from app.config import get_config

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = self.process.memory_info().rss
        self.baseline_connections = len(self.process.connections())
        self.resource_snapshots = []
        self.cleanup_metrics = {}
        self.leak_thresholds = {
            "memory_leak_mb": 50,  # 50MB memory leak threshold
            "connection_leak_count": 10,  # 10 connection leak threshold
            "cleanup_time_seconds": 5.0  # 5 second cleanup time limit
        }

    def capture_resource_snapshot(self, operation: str) -> Dict[str, Any]:
        """Capture current resource usage snapshot."""
        current_memory = self.process.memory_info().rss
        current_connections = len(self.process.connections())
        current_threads = self.process.num_threads()
        
        snapshot = {
            "operation": operation,
            "timestamp": time.time(),
            "memory_bytes": current_memory,
            "memory_mb": current_memory / (1024 * 1024),
            "memory_delta_mb": (current_memory - self.baseline_memory) / (1024 * 1024),
            "connections": current_connections,
            "connection_delta": current_connections - self.baseline_connections,
            "threads": current_threads
        }
        
        self.resource_snapshots.append(snapshot)
        return snapshot

    def detect_memory_leaks(self, operation_count: int = 1) -> Dict[str, Any]:
        """Detect memory leaks across multiple operations."""
        if len(self.resource_snapshots) < 2:
            return {"leak_detected": False, "insufficient_data": True}
        
        initial_snapshot = self.resource_snapshots[0]
        final_snapshot = self.resource_snapshots[-1]
        
        memory_leak_mb = final_snapshot["memory_delta_mb"] - initial_snapshot["memory_delta_mb"]
        connection_leak = final_snapshot["connection_delta"] - initial_snapshot["connection_delta"]
        
        memory_leak_per_op = memory_leak_mb / operation_count if operation_count > 0 else memory_leak_mb
        
        leak_detection = {
            "total_memory_leak_mb": memory_leak_mb,
            "memory_leak_per_operation_mb": memory_leak_per_op,
            "total_connection_leak": connection_leak,
            "memory_leak_detected": memory_leak_mb > self.leak_thresholds["memory_leak_mb"],
            "connection_leak_detected": connection_leak > self.leak_thresholds["connection_leak_count"],
            "leak_severity": self._calculate_leak_severity(memory_leak_mb, connection_leak)
        }
        
        return leak_detection

    def _validate_cleanup_success(self, pre_snapshot: Dict[str, Any], 
                                post_snapshot: Dict[str, Any]) -> bool:
        """Validate cleanup was successful."""
        memory_growth = post_snapshot["memory_delta_mb"] - pre_snapshot["memory_delta_mb"]
        connection_growth = post_snapshot["connection_delta"] - pre_snapshot["connection_delta"]
        
        return (
            memory_growth < self.leak_thresholds["memory_leak_mb"] and
            connection_growth < self.leak_thresholds["connection_leak_count"]
        )

    def _calculate_leak_severity(self, memory_leak: float, connection_leak: int) -> str:
        """Calculate leak severity level."""
        if memory_leak > 100 or connection_leak > 20:
            return "critical"
        elif memory_leak > 50 or connection_leak > 10:
            return "high"
        elif memory_leak > 20 or connection_leak > 5:
            return "medium"
        else:
            return "low"

    def __init__(self):
        self.concurrent_metrics = []
        self.resource_monitor = ResourceCleanupMonitor()

    def resource_monitor(self):
        """Initialize resource cleanup monitor."""
        return ResourceCleanupMonitor()

    def concurrent_tester(self):
        """Initialize concurrent resource tester."""
        return ConcurrentResourceTester()
