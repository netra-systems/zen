"""Overload detection and handling for LLM operations.

Provides mechanisms to detect and handle API overload conditions
with adaptive backoff and resource management.
"""

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class OverloadState(Enum):
    """API overload states."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    RECOVERING = "recovering"


class OverloadDetector:
    """Detects API overload conditions."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}
        self.state = OverloadState.NORMAL
        self.recovery_start: Optional[datetime] = None
    
    def analyze_error(self, error: Exception) -> bool:
        """Analyze error to detect overload."""
        error_msg = str(error).lower()
        return self._is_overload_error(error_msg)
    
    def _is_overload_error(self, error_msg: str) -> bool:
        """Check if error indicates overload."""
        overload_indicators = [
            'overloaded', '429', 'rate limit',
            'too many requests', 'quota exceeded',
            '503 service unavailable'
        ]
        return any(indicator in error_msg for indicator in overload_indicators)
    
    def record_error(self, config_name: str, error: Exception) -> None:
        """Record error occurrence."""
        if self.analyze_error(error):
            self._increment_error_count(config_name)
            self._update_state(config_name)
    
    def _increment_error_count(self, config_name: str) -> None:
        """Increment error count for config."""
        self.error_counts[config_name] = self.error_counts.get(config_name, 0) + 1
        self.last_errors[config_name] = datetime.now()
    
    def _update_state(self, config_name: str) -> None:
        """Update overload state based on error counts."""
        count = self.error_counts.get(config_name, 0)
        if count >= 10:
            self._set_critical_state()
        elif count >= 5:
            self._set_warning_state()
    
    def _set_critical_state(self) -> None:
        """Set critical overload state."""
        if self.state != OverloadState.CRITICAL:
            self.state = OverloadState.CRITICAL
            logger.error("API overload state: CRITICAL")
    
    def _set_warning_state(self) -> None:
        """Set warning overload state."""
        if self.state == OverloadState.NORMAL:
            self.state = OverloadState.WARNING
            logger.warning("API overload state: WARNING")
    
    def record_success(self, config_name: str) -> None:
        """Record successful request."""
        if config_name in self.error_counts:
            self.error_counts[config_name] = max(0, self.error_counts[config_name] - 1)
            if self._should_recover():
                self._initiate_recovery()
    
    def _should_recover(self) -> bool:
        """Check if should start recovery."""
        total_errors = sum(self.error_counts.values())
        return total_errors < 3 and self.state != OverloadState.NORMAL
    
    def _initiate_recovery(self) -> None:
        """Start recovery process."""
        self.state = OverloadState.RECOVERING
        self.recovery_start = datetime.now()
        logger.info("Starting overload recovery")
    
    def get_backoff_time(self) -> float:
        """Get recommended backoff time based on state."""
        backoff_times = {
            OverloadState.NORMAL: 0,
            OverloadState.WARNING: 5,
            OverloadState.CRITICAL: 30,
            OverloadState.RECOVERING: 10
        }
        return backoff_times.get(self.state, 0)


class AdaptiveThrottler:
    """Adaptive request throttling based on overload conditions."""
    
    def __init__(self, detector: OverloadDetector):
        self.detector = detector
        self.request_delays: Dict[str, float] = {}
        self.last_requests: Dict[str, datetime] = {}
    
    async def throttle_request(self, config_name: str) -> None:
        """Apply throttling before request."""
        delay = self._calculate_delay(config_name)
        if delay > 0:
            logger.debug(f"Throttling {config_name} for {delay:.2f}s")
            await asyncio.sleep(delay)
        self.last_requests[config_name] = datetime.now()
    
    def _calculate_delay(self, config_name: str) -> float:
        """Calculate throttle delay."""
        base_delay = self.detector.get_backoff_time()
        adaptive_delay = self._get_adaptive_delay(config_name)
        return max(base_delay, adaptive_delay)
    
    def _get_adaptive_delay(self, config_name: str) -> float:
        """Get adaptive delay based on recent requests."""
        if config_name not in self.last_requests:
            return 0
        elapsed = (datetime.now() - self.last_requests[config_name]).total_seconds()
        if elapsed < 1:  # Too fast
            return 2 - elapsed
        return 0
    
    def adjust_rate(self, config_name: str, success: bool) -> None:
        """Adjust throttling rate based on results."""
        current_delay = self.request_delays.get(config_name, 0)
        if success:
            self.request_delays[config_name] = max(0, current_delay - 0.5)
        else:
            self.request_delays[config_name] = min(60, current_delay + 2)


class OverloadManager:
    """Manages overload detection and response."""
    
    def __init__(self):
        self.detector = OverloadDetector()
        self.throttler = AdaptiveThrottler(self.detector)
        self.circuit_states: Dict[str, bool] = {}
    
    async def pre_request(self, config_name: str) -> bool:
        """Pre-request check and throttling."""
        if self._is_circuit_open(config_name):
            return False
        await self.throttler.throttle_request(config_name)
        return True
    
    def _is_circuit_open(self, config_name: str) -> bool:
        """Check if circuit is open for config."""
        if self.detector.state == OverloadState.CRITICAL:
            return True
        return self.circuit_states.get(config_name, False)
    
    def handle_error(self, config_name: str, error: Exception) -> None:
        """Handle request error."""
        self.detector.record_error(config_name, error)
        self.throttler.adjust_rate(config_name, False)
        if self.detector.analyze_error(error):
            self._open_circuit_temporarily(config_name)
    
    def _open_circuit_temporarily(self, config_name: str) -> None:
        """Temporarily open circuit for config."""
        self.circuit_states[config_name] = True
        asyncio.create_task(self._close_circuit_after_delay(config_name))
    
    async def _close_circuit_after_delay(self, config_name: str) -> None:
        """Close circuit after delay."""
        delay = self.detector.get_backoff_time()
        await asyncio.sleep(delay)
        self.circuit_states[config_name] = False
        logger.info(f"Circuit reopened for {config_name}")
    
    def handle_success(self, config_name: str) -> None:
        """Handle successful request."""
        self.detector.record_success(config_name)
        self.throttler.adjust_rate(config_name, True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get overload manager status."""
        return {
            'state': self.detector.state.value,
            'error_counts': self.detector.error_counts,
            'circuit_states': self.circuit_states,
            'request_delays': self.throttler.request_delays
        }


# Global overload manager instance
overload_manager = OverloadManager()