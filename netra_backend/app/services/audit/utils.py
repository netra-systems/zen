"""
Corpus Audit Utilities
Utility classes and functions for audit operations.
Focused on timing and helper functions.  <= 300 lines,  <= 8 lines per function.
"""

import time
from typing import Optional


class AuditTimer:
    """Context manager for measuring operation duration."""

    def __init__(self):
        self.start_time = None
        self.duration_ms = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            end_time = time.perf_counter()
            self.duration_ms = (end_time - self.start_time) * 1000

    def get_duration(self) -> Optional[float]:
        """Get operation duration in milliseconds."""
        return self.duration_ms