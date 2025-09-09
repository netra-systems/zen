"""
Thread ID Consistency Tests Package

This package contains comprehensive tests for validating thread_ID consistency
throughout the WebSocket manager lifecycle to prevent resource leaks.

Key Components:
- ThreadIDConsistencyTracker: Core monitoring utility
- TestThreadIdConsistencyComprehensive: Full test suite
- ThreadIdSnapshot: Point-in-time thread_ID value capture

Usage:
    from tests.thread_id_consistency import ThreadIDConsistencyTracker
"""

from .test_thread_id_consistency_comprehensive import (
    ThreadIDConsistencyTracker,
    ThreadIdSnapshot,
    TestThreadIdConsistencyComprehensive
)

__all__ = [
    "ThreadIDConsistencyTracker",
    "ThreadIdSnapshot", 
    "TestThreadIdConsistencyComprehensive"
]