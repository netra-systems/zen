"""Backpressure Service Implementation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide basic backpressure management functionality for tests
- Value Impact: Ensures backpressure management tests can execute without import errors
- Strategic Impact: Enables backpressure management functionality validation
"""

import asyncio
from typing import Dict, Optional, Any, Callable, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class BackpressureStrategy(Enum):
    """Backpressure strategies."""
    DROP = "drop"
    QUEUE = "queue"
    DELAY = "delay"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class BackpressureConfig:
    """Backpressure configuration."""
    strategy: BackpressureStrategy = BackpressureStrategy.QUEUE
    max_queue_size: int = 1000
    max_delay_seconds: float = 5.0
    circuit_breaker_threshold: int = 10
    circuit_breaker_timeout: int = 60


@dataclass
class BackpressureMetrics:
    """Backpressure metrics."""
    queued_requests: int = 0
    dropped_requests: int = 0
    delayed_requests: int = 0
    circuit_breaker_trips: int = 0
    average_queue_time: float = 0.0
    current_queue_size: int = 0


class BackpressureService:
    """Service for managing backpressure in the application."""
    
    def __init__(self, config: Optional[BackpressureConfig] = None):
        """Initialize backpressure service."""
        self.config = config or BackpressureConfig()
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self._metrics = BackpressureMetrics()
        self._circuit_breaker_state = "closed"  # closed, open, half-open
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
        self._lock = asyncio.Lock()
    
    async def apply_backpressure(
        self, 
        request_handler: Callable,
        request_data: Any,
        priority: int = 0
    ) -> Any:
        """Apply backpressure to a request."""
        async with self._lock:
            if self._should_drop_request():
                self._metrics.dropped_requests += 1
                raise BackpressureException("Request dropped due to backpressure")
            
            if self.config.strategy == BackpressureStrategy.QUEUE:
                return await self._handle_with_queue(request_handler, request_data, priority)
            elif self.config.strategy == BackpressureStrategy.DELAY:
                return await self._handle_with_delay(request_handler, request_data)
            elif self.config.strategy == BackpressureStrategy.CIRCUIT_BREAKER:
                return await self._handle_with_circuit_breaker(request_handler, request_data)
            else:
                # Default: just execute
                return await request_handler(request_data)
    
    async def _handle_with_queue(self, handler: Callable, data: Any, priority: int) -> Any:
        """Handle request with queueing."""
        if self._queue.full():
            if self.config.strategy == BackpressureStrategy.DROP:
                self._metrics.dropped_requests += 1
                raise BackpressureException("Queue is full, request dropped")
        
        queue_start = datetime.now()
        await self._queue.put((handler, data, priority, queue_start))
        self._metrics.queued_requests += 1
        self._metrics.current_queue_size = self._queue.qsize()
        
        # Process from queue
        return await self._process_queue_item()
    
    async def _handle_with_delay(self, handler: Callable, data: Any) -> Any:
        """Handle request with delay."""
        delay = min(self._metrics.current_queue_size * 0.1, self.config.max_delay_seconds)
        if delay > 0:
            await asyncio.sleep(delay)
            self._metrics.delayed_requests += 1
        
        return await handler(data)
    
    async def _handle_with_circuit_breaker(self, handler: Callable, data: Any) -> Any:
        """Handle request with circuit breaker."""
        if self._circuit_breaker_state == "open":
            if self._should_attempt_reset():
                self._circuit_breaker_state = "half-open"
            else:
                raise BackpressureException("Circuit breaker is open")
        
        try:
            result = await handler(data)
            if self._circuit_breaker_state == "half-open":
                self._reset_circuit_breaker()
            return result
        except Exception as e:
            self._record_circuit_breaker_failure()
            raise e
    
    async def _process_queue_item(self) -> Any:
        """Process an item from the queue."""
        handler, data, priority, queue_start = await self._queue.get()
        
        queue_time = (datetime.now() - queue_start).total_seconds()
        self._update_average_queue_time(queue_time)
        self._metrics.current_queue_size = self._queue.qsize()
        
        try:
            return await handler(data)
        finally:
            self._queue.task_done()
    
    def _should_drop_request(self) -> bool:
        """Determine if request should be dropped."""
        if self.config.strategy == BackpressureStrategy.DROP:
            return self._queue.full()
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self._circuit_breaker_last_failure is None:
            return False
        
        time_since_failure = datetime.now() - self._circuit_breaker_last_failure
        return time_since_failure.total_seconds() > self.config.circuit_breaker_timeout
    
    def _record_circuit_breaker_failure(self) -> None:
        """Record a circuit breaker failure."""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = datetime.now()
        
        if self._circuit_breaker_failures >= self.config.circuit_breaker_threshold:
            self._circuit_breaker_state = "open"
            self._metrics.circuit_breaker_trips += 1
    
    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker to closed state."""
        self._circuit_breaker_state = "closed"
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = None
    
    def _update_average_queue_time(self, queue_time: float) -> None:
        """Update average queue time with new measurement."""
        if self._metrics.average_queue_time == 0:
            self._metrics.average_queue_time = queue_time
        else:
            # Simple moving average
            self._metrics.average_queue_time = (
                self._metrics.average_queue_time * 0.9 + queue_time * 0.1
            )
    
    def get_metrics(self) -> BackpressureMetrics:
        """Get current backpressure metrics."""
        return self._metrics
    
    async def reset_metrics(self) -> None:
        """Reset backpressure metrics."""
        async with self._lock:
            self._metrics = BackpressureMetrics()
    
    def get_status(self) -> Dict[str, Any]:
        """Get backpressure service status."""
        return {
            "strategy": self.config.strategy.value,
            "circuit_breaker_state": self._circuit_breaker_state,
            "queue_size": self._queue.qsize(),
            "max_queue_size": self.config.max_queue_size,
            "metrics": {
                "queued_requests": self._metrics.queued_requests,
                "dropped_requests": self._metrics.dropped_requests,
                "delayed_requests": self._metrics.delayed_requests,
                "circuit_breaker_trips": self._metrics.circuit_breaker_trips,
                "average_queue_time": self._metrics.average_queue_time,
                "current_queue_size": self._metrics.current_queue_size
            }
        }


class BackpressureException(Exception):
    """Exception raised when backpressure is applied."""
    pass


# Global backpressure service instance
default_backpressure_service = BackpressureService()