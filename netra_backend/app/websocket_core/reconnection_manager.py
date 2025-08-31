"""
WebSocket Reconnection Manager

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & User Experience
- Value Impact: Handles connection failures gracefully, maintains session continuity
- Strategic Impact: Reduces user frustration, improves platform stability

Manages WebSocket reconnection logic with exponential backoff and jitter.
"""

import asyncio
import random
import time
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.types import (
    ReconnectionConfig,
    WebSocketConnectionState,
    ConnectionInfo
)

logger = central_logger.get_logger(__name__)


class ReconnectionState(str, Enum):
    """States for reconnection process."""
    IDLE = "idle"
    ATTEMPTING = "attempting"
    CONNECTED = "connected"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class ReconnectionAttempt:
    """Information about a reconnection attempt."""
    attempt_number: int
    timestamp: float
    delay_seconds: float
    success: bool = False
    error_message: Optional[str] = None


class ReconnectionManager:
    """Manages WebSocket reconnection with exponential backoff."""
    
    def __init__(self, config: Optional[ReconnectionConfig] = None):
        self.config = config or ReconnectionConfig()
        self.connection_states: Dict[str, ReconnectionState] = {}
        self.attempt_history: Dict[str, List[ReconnectionAttempt]] = {}
        self.reconnection_tasks: Dict[str, asyncio.Task] = {}
        self.connection_callbacks: Dict[str, Callable] = {}
        self.stats = {
            "total_attempts": 0,
            "successful_reconnections": 0,
            "failed_reconnections": 0,
            "active_reconnections": 0
        }
    
    def register_connection(self, connection_id: str, 
                          connection_callback: Callable[[], Any]) -> None:
        """Register a connection for reconnection management."""
        self.connection_states[connection_id] = ReconnectionState.CONNECTED
        self.connection_callbacks[connection_id] = connection_callback
        self.attempt_history[connection_id] = []
        
        logger.info(f"Registered connection {connection_id} for reconnection management")
    
    def unregister_connection(self, connection_id: str) -> None:
        """Unregister a connection from reconnection management."""
        # Cancel any active reconnection tasks
        if connection_id in self.reconnection_tasks:
            self.reconnection_tasks[connection_id].cancel()
            del self.reconnection_tasks[connection_id]
        
        # Clean up state
        self.connection_states.pop(connection_id, None)
        self.connection_callbacks.pop(connection_id, None)
        self.attempt_history.pop(connection_id, None)
        
        logger.info(f"Unregistered connection {connection_id} from reconnection management")
    
    async def handle_connection_lost(self, connection_id: str) -> None:
        """Handle a lost connection and start reconnection process."""
        if connection_id not in self.connection_states:
            logger.warning(f"Unknown connection {connection_id} reported as lost")
            return
        
        if not self.config.enabled:
            logger.info(f"Reconnection disabled for connection {connection_id}")
            self.connection_states[connection_id] = ReconnectionState.DISABLED
            return
        
        logger.warning(f"Connection {connection_id} lost, starting reconnection process")
        self.connection_states[connection_id] = ReconnectionState.ATTEMPTING
        
        # Start reconnection task
        if connection_id not in self.reconnection_tasks:
            self.reconnection_tasks[connection_id] = asyncio.create_task(
                self._reconnection_loop(connection_id)
            )
    
    async def _reconnection_loop(self, connection_id: str) -> None:
        """Main reconnection loop with exponential backoff and staging optimizations."""
        attempt_number = 0
        consecutive_failures = 0
        
        try:
            while (attempt_number < self.config.max_attempts and 
                   self.connection_states.get(connection_id) == ReconnectionState.ATTEMPTING):
                
                attempt_number += 1
                delay = self.config.calculate_delay(attempt_number)
                
                # CRITICAL FIX: Add circuit breaker pattern for staging environments
                from shared.isolated_environment import get_env
                env = get_env()
                environment = env.get("ENVIRONMENT", "development").lower()
                
                if environment in ["staging", "production"] and consecutive_failures >= 3:
                    # Implement circuit breaker - longer delay after multiple failures
                    circuit_breaker_delay = min(delay * 2, 120.0)  # Max 2 minutes
                    logger.warning(f"Circuit breaker active for {connection_id}, waiting {circuit_breaker_delay:.1f}s")
                    await asyncio.sleep(circuit_breaker_delay - delay)  # Additional delay
                
                # Create attempt record
                attempt = ReconnectionAttempt(
                    attempt_number=attempt_number,
                    timestamp=time.time(),
                    delay_seconds=delay
                )
                
                logger.info(f"Reconnection attempt {attempt_number}/{self.config.max_attempts} "
                          f"for {connection_id} in {delay:.2f}s (consecutive_failures: {consecutive_failures})")
                
                # Wait before attempting
                await asyncio.sleep(delay)
                
                # Attempt reconnection
                if await self._attempt_reconnection(connection_id, attempt):
                    # Success - reset consecutive failures
                    consecutive_failures = 0
                    self.connection_states[connection_id] = ReconnectionState.CONNECTED
                    self.stats["successful_reconnections"] += 1
                    logger.info(f"Successfully reconnected {connection_id} on attempt {attempt_number}")
                    break
                else:
                    # Failed attempt
                    consecutive_failures += 1
                    self.stats["failed_reconnections"] += 1
                    logger.warning(f"Reconnection attempt {attempt_number} failed for {connection_id} (consecutive: {consecutive_failures})")
                    
                    # CRITICAL FIX: For staging, add health check after failed attempts
                    if environment in ["staging", "production"] and attempt_number < self.config.max_attempts:
                        await self._perform_connection_health_check(connection_id)
            
            # Check if all attempts exhausted
            if (attempt_number >= self.config.max_attempts and 
                self.connection_states.get(connection_id) == ReconnectionState.ATTEMPTING):
                
                self.connection_states[connection_id] = ReconnectionState.FAILED
                logger.error(f"All reconnection attempts exhausted for {connection_id} after {consecutive_failures} consecutive failures")
                
        except asyncio.CancelledError:
            logger.info(f"Reconnection task cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error in reconnection loop for {connection_id}: {e}")
            self.connection_states[connection_id] = ReconnectionState.FAILED
        finally:
            # Clean up task reference
            if connection_id in self.reconnection_tasks:
                del self.reconnection_tasks[connection_id]
    
    async def _attempt_reconnection(self, connection_id: str, 
                                  attempt: ReconnectionAttempt) -> bool:
        """Attempt to reconnect a specific connection."""
        try:
            self.stats["total_attempts"] += 1
            
            # Get connection callback
            callback = self.connection_callbacks.get(connection_id)
            if not callback:
                attempt.error_message = "No connection callback found"
                attempt.success = False
                self.attempt_history[connection_id].append(attempt)
                return False
            
            # Use connection timeout
            success = await asyncio.wait_for(
                callback(),
                timeout=self.config.connection_timeout_seconds
            )
            
            attempt.success = bool(success)
            self.attempt_history[connection_id].append(attempt)
            
            return attempt.success
            
        except asyncio.TimeoutError:
            attempt.error_message = f"Connection timeout after {self.config.connection_timeout_seconds}s"
            attempt.success = False
            self.attempt_history[connection_id].append(attempt)
            return False
        except Exception as e:
            attempt.error_message = str(e)
            attempt.success = False
            self.attempt_history[connection_id].append(attempt)
            logger.error(f"Reconnection attempt failed for {connection_id}: {e}")
            return False
    
    def get_connection_state(self, connection_id: str) -> Optional[ReconnectionState]:
        """Get current state of a connection."""
        return self.connection_states.get(connection_id)
    
    def is_reconnecting(self, connection_id: str) -> bool:
        """Check if connection is currently reconnecting."""
        return self.connection_states.get(connection_id) == ReconnectionState.ATTEMPTING
    
    def get_attempt_history(self, connection_id: str) -> List[ReconnectionAttempt]:
        """Get reconnection attempt history for a connection."""
        return self.attempt_history.get(connection_id, [])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reconnection manager statistics."""
        stats = self.stats.copy()
        stats["active_reconnections"] = len(self.reconnection_tasks)
        stats["managed_connections"] = len(self.connection_states)
        stats["config"] = self.config.model_dump()
        
        # Add state distribution
        state_counts = {}
        for state in self.connection_states.values():
            state_counts[state] = state_counts.get(state, 0) + 1
        stats["connection_states"] = state_counts
        
        return stats
    
    async def force_reconnect(self, connection_id: str) -> bool:
        """Force an immediate reconnection attempt."""
        if connection_id not in self.connection_states:
            logger.warning(f"Cannot force reconnect unknown connection {connection_id}")
            return False
        
        # Cancel any existing reconnection task
        if connection_id in self.reconnection_tasks:
            self.reconnection_tasks[connection_id].cancel()
            del self.reconnection_tasks[connection_id]
        
        # Set state and start reconnection
        self.connection_states[connection_id] = ReconnectionState.ATTEMPTING
        self.reconnection_tasks[connection_id] = asyncio.create_task(
            self._reconnection_loop(connection_id)
        )
        
        logger.info(f"Forced reconnection started for {connection_id}")
        return True
    
    def disable_reconnection(self, connection_id: str) -> None:
        """Disable reconnection for a specific connection."""
        if connection_id in self.reconnection_tasks:
            self.reconnection_tasks[connection_id].cancel()
            del self.reconnection_tasks[connection_id]
        
        self.connection_states[connection_id] = ReconnectionState.DISABLED
        logger.info(f"Reconnection disabled for {connection_id}")
    
    def enable_reconnection(self, connection_id: str) -> None:
        """Re-enable reconnection for a specific connection."""
        if connection_id in self.connection_states:
            self.connection_states[connection_id] = ReconnectionState.IDLE
            logger.info(f"Reconnection re-enabled for {connection_id}")
    
    async def cleanup(self) -> None:
        """Clean up all reconnection tasks and state."""
        # Cancel all active tasks
        for task in self.reconnection_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.reconnection_tasks:
            await asyncio.gather(*self.reconnection_tasks.values(), return_exceptions=True)
        
        # Clear state
        self.reconnection_tasks.clear()
        self.connection_states.clear()
        self.connection_callbacks.clear()
        self.attempt_history.clear()
        
        logger.info("Reconnection manager cleaned up")
    
    async def _perform_connection_health_check(self, connection_id: str) -> None:
        """Perform connection health check for staging environments."""
        try:
            # Simple health check - just log for now, can be extended with actual health checks
            logger.info(f"Performing connection health check for {connection_id}")
            # Add small delay to avoid overwhelming the system
            await asyncio.sleep(1.0)
        except Exception as e:
            logger.warning(f"Connection health check failed for {connection_id}: {e}")


# Global reconnection manager instance
_reconnection_manager: Optional[ReconnectionManager] = None

def get_reconnection_manager(config: Optional[ReconnectionConfig] = None) -> ReconnectionManager:
    """Get global reconnection manager instance with environment-aware configuration."""
    global _reconnection_manager
    if _reconnection_manager is None:
        # CRITICAL FIX: Use environment-specific reconnection configuration
        if config is None:
            from shared.isolated_environment import get_env
            env = get_env()
            environment = env.get("ENVIRONMENT", "development").lower()
            
            # Create staging-optimized reconnection config
            if environment == "staging":
                config = ReconnectionConfig(
                    enabled=True,
                    max_attempts=5,                    # More attempts for staging
                    base_delay_seconds=2.0,           # Longer initial delay
                    max_delay_seconds=60.0,           # Longer max delay
                    jitter_factor=0.3,                # More jitter for staging
                    connection_timeout_seconds=30.0    # Longer connection timeout
                )
            elif environment == "production":
                config = ReconnectionConfig(
                    enabled=True,
                    max_attempts=3,                    # Conservative attempts
                    base_delay_seconds=1.5,           # Balanced delay
                    max_delay_seconds=45.0,           # Reasonable max delay
                    jitter_factor=0.2,                # Less jitter for production
                    connection_timeout_seconds=25.0    # Production timeout
                )
            # Development uses default config
        
        _reconnection_manager = ReconnectionManager(config)
    return _reconnection_manager


async def setup_connection_with_reconnection(
    connection_id: str,
    connection_factory: Callable[[], Any],
    config: Optional[ReconnectionConfig] = None
) -> ReconnectionManager:
    """Set up a connection with automatic reconnection management."""
    manager = get_reconnection_manager(config)
    manager.register_connection(connection_id, connection_factory)
    return manager


def calculate_next_reconnect_delay(attempt: int, config: ReconnectionConfig) -> float:
    """Calculate the delay for the next reconnection attempt."""
    return config.calculate_delay(attempt)