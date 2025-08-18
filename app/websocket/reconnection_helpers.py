"""Reconnection helper functions and utilities."""

import random
import time
from datetime import datetime, timezone
from typing import Optional

from app.logging_config import central_logger
from .reconnection_types import ReconnectionConfig, ReconnectionAttempt

logger = central_logger.get_logger(__name__)


class ReconnectionDelayCalculator:
    """Handles reconnection delay calculations."""
    
    def __init__(self, config: ReconnectionConfig):
        self.config = config
    
    def calculate_backoff_delay(self, current_attempt: int, current_delay_ms: int) -> int:
        """Calculate exponential backoff delay with jitter."""
        base_delay = self._calculate_exponential_delay(current_attempt, current_delay_ms)
        jitter_delay = self._apply_jitter(base_delay)
        return int(jitter_delay)

    def _calculate_exponential_delay(self, current_attempt: int, current_delay_ms: int) -> float:
        """Calculate exponential delay without jitter."""
        delay = current_delay_ms * (self.config.backoff_multiplier ** (current_attempt - 1))
        return min(delay, self.config.max_delay_ms)

    def _apply_jitter(self, delay: float) -> float:
        """Apply jitter to delay."""
        jitter_range = delay * self.config.jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)
        return max(0, delay + jitter)


class ReconnectionAttemptHelper:
    """Helps with reconnection attempt creation and logging."""
    
    def __init__(self, connection_id: str, config: ReconnectionConfig):
        self.connection_id = connection_id
        self.config = config
    
    def create_attempt_record(self, attempt_number: int, delay_ms: int) -> ReconnectionAttempt:
        """Create reconnection attempt record."""
        return ReconnectionAttempt(
            attempt_number=attempt_number,
            timestamp=datetime.now(timezone.utc),
            delay_ms=delay_ms,
            reason=f"Attempt {attempt_number}/{self.config.max_attempts}"
        )

    def log_reconnection_attempt(self, attempt_number: int, delay_ms: int) -> None:
        """Log reconnection attempt information."""
        logger.info(f"Reconnection attempt {attempt_number}/{self.config.max_attempts} "
                   f"for {self.connection_id} in {delay_ms}ms")

    def log_connection_failure(self, attempt_number: int, error: Exception) -> None:
        """Log connection failure."""
        logger.warning(f"Reconnection attempt {attempt_number} failed for "
                     f"{self.connection_id}: {error}")


class ReconnectionMetricsHelper:
    """Helps with reconnection metrics calculations."""
    
    @staticmethod
    def update_average_reconnection_time(current_avg: float, successful_count: int, duration_ms: float) -> float:
        """Update average reconnection time."""
        return (current_avg * (successful_count - 1) + duration_ms) / successful_count

    @staticmethod
    def calculate_downtime_ms(disconnect_time: Optional[datetime]) -> float:
        """Calculate downtime in milliseconds."""
        if not disconnect_time:
            return 0.0
        return (datetime.now(timezone.utc) - disconnect_time).total_seconds() * 1000

    @staticmethod
    def calculate_attempt_duration_ms(start_time: float) -> float:
        """Calculate attempt duration in milliseconds."""
        return (time.time() - start_time) * 1000