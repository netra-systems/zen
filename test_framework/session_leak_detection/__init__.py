"""
Session Leak Detection Infrastructure

This module provides comprehensive session leak detection and monitoring
for the Netra backend database connections.

Business Value:
- Prevents database connection pool exhaustion
- Ensures proper session lifecycle management
- Identifies session leaks in thread handlers before production
- Validates database session safety across all operations

CRITICAL: This infrastructure is designed to FAIL when session leaks exist,
following CLAUDE.md testing principles: "Tests MUST raise errors"
"""

from .session_leak_tracker import SessionLeakTracker
from .database_session_monitor import DatabaseSessionMonitor
from .session_leak_test_base import SessionLeakTestBase

__all__ = [
    "SessionLeakTracker",
    "DatabaseSessionMonitor", 
    "SessionLeakTestBase"
]