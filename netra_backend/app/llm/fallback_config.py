"""
LLM Fallback Configuration Classes

This module contains configuration classes for LLM fallback handling.
Each class focuses on a single configuration aspect with ≤8 line methods.
"""

import time
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

from netra_backend.app.error_classification import FailureType


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    timeout: float = 60.0
    use_circuit_breaker: bool = True
    log_circuit_breaker_warnings: bool = False


@dataclass 
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    failure_type: FailureType
    error_message: str
    timestamp: float


class RetryHistoryManager:
    """Manages retry attempt history with memory leak prevention"""
    
    def __init__(self, max_history: int = 100, trim_to: int = 50):
        """Initialize retry history manager with strong typing."""
        self.retry_history: List[RetryAttempt] = []
        self.max_history = max_history
        self.trim_to = trim_to
    
    def add_attempt(self, attempt: int, failure_type: FailureType, error_msg: str) -> None:
        """Add retry attempt with automatic trimming."""
        retry_attempt = self._create_retry_attempt(attempt, failure_type, error_msg)
        self.retry_history.append(retry_attempt)
        self._trim_history_if_needed()
    
    def _create_retry_attempt(self, attempt: int, failure_type: FailureType, error_msg: str) -> RetryAttempt:
        """Create retry attempt with current timestamp."""
        return RetryAttempt(
            attempt_number=attempt,
            failure_type=failure_type,
            error_message=error_msg,
            timestamp=time.time()
        )
    
    def _trim_history_if_needed(self) -> None:
        """Trim history to prevent memory leaks."""
        if len(self.retry_history) > self.max_history:
            self.retry_history = self.retry_history[-self.trim_to:]
    
    def get_recent_failures(self, time_window_seconds: float = 300) -> List[RetryAttempt]:
        """Get recent failures within time window."""
        cutoff_time = time.time() - time_window_seconds
        return [
            attempt for attempt in self.retry_history
            if attempt.timestamp >= cutoff_time
        ]
    
    def clear_history(self) -> None:
        """Clear all retry history."""
        self.retry_history.clear()