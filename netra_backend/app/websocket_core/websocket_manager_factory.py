"""WebSocket Manager Factory - Enhanced Emergency Cleanup System

This module provides enterprise-grade WebSocket manager factory with:
- 20-manager hard limit enforcement
- Enhanced emergency cleanup with zombie detection
- Graduated cleanup levels (Conservative → Moderate → Aggressive → Force)
- Circuit breaker protection for failed cleanups
- Real-time resource monitoring and health checks

Business Value Justification (BVJ):
- Segment: Enterprise (protects $500K+ ARR)
- Business Goal: Maintain AI chat availability under extreme load
- Value Impact: Prevents permanent chat blocking for enterprise users
- Revenue Impact: Protects revenue-critical user interactions

CRITICAL FEATURES:
- Resource exhaustion recovery mechanisms
- Zombie manager detection and removal
- Multi-level emergency response with health validation
- Comprehensive monitoring and circuit breaker protection
"""

import asyncio
import time
import weakref
import gc
import threading
from enum import Enum
from typing import Dict, Optional, Set, Any, List, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# Import WebSocket manager types
from netra_backend.app.websocket_core.types import WebSocketManagerMode
from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation

logger = get_logger(__name__)


class CleanupLevel(Enum):
    """Graduated cleanup levels for emergency resource management"""
    CONSERVATIVE = "conservative"  # Remove only clearly inactive managers
    MODERATE = "moderate"         # Remove inactive + old idle managers
    AGGRESSIVE = "aggressive"     # Remove inactive + old + zombie managers
    FORCE = "force"              # Force remove oldest managers (nuclear option)


class ManagerHealthStatus(Enum):
    """Manager health status for cleanup decision making"""
    HEALTHY = "healthy"          # Active with recent activity and responsive connections
    IDLE = "idle"               # Active but no recent activity
    ZOMBIE = "zombie"           # Appears active but unresponsive/stuck
    INACTIVE = "inactive"       # Clearly inactive
    UNKNOWN = "unknown"         # Unable to determine status


@dataclass
class ManagerHealth:
    """Health assessment for a WebSocket manager"""
    status: ManagerHealthStatus
    last_activity: Optional[datetime] = None
    connection_count: int = 0
    responsive_connections: int = 0
    health_score: float = 0.0  # 0.0 (poor) to 1.0 (excellent)
    last_health_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    failure_count: int = 0
    creation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_healthy(self) -> bool:
        """Quick health assessment"""
        return self.status == ManagerHealthStatus.HEALTHY and self.health_score >= 0.7

    @property
    def is_zombie(self) -> bool:
        """Detect zombie managers"""
        return self.status == ManagerHealthStatus.ZOMBIE or (
            self.connection_count > 0 and self.responsive_connections == 0
        )

    @property
    def age_seconds(self) -> float:
        """Age of manager in seconds"""
        return (datetime.now(timezone.utc) - self.creation_time).total_seconds()


@dataclass
class FactoryMetrics:
    """Metrics for factory resource management"""
    total_managers: int = 0
    managers_by_user: Dict[str, int] = field(default_factory=dict)
    cleanup_events: int = 0
    emergency_cleanups: int = 0
    failed_cleanups: int = 0
    circuit_breaker_activations: int = 0
    zombie_managers_detected: int = 0
    aggressive_cleanups_triggered: int = 0
    revenue_protection_events: int = 0

    def record_business_protection(self, event_type: str):
        """Record business protection event"""
        self.revenue_protection_events += 1
        logger.info(f"Business protection event recorded: {event_type}")


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for failed cleanup protection"""
    is_open: bool = False
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    success_count: int = 0
    next_attempt_time: Optional[datetime] = None

    def should_attempt_cleanup(self) -> bool:
        """Check if cleanup should be attempted based on circuit breaker state"""
        if not self.is_open:
            return True

        if self.next_attempt_time and datetime.now(timezone.utc) >= self.next_attempt_time:
            return True

        return False

    def record_success(self):
        """Record successful cleanup"""
        self.success_count += 1
        if self.success_count >= 3:  # Reset circuit breaker after 3 successes
            self.is_open = False
            self.failure_count = 0
            self.success_count = 0
            self.next_attempt_time = None

    def record_failure(self):
        """Record failed cleanup"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= 5:  # Open circuit breaker after 5 failures
            self.is_open = True
            self.next_attempt_time = datetime.now(timezone.utc) + timedelta(minutes=5)


class ZombieDetectionEngine:
    """Engine for detecting and analyzing zombie WebSocket managers"""

    def __init__(self):
        self.detection_threshold = 300  # 5 minutes without activity
        self.response_timeout = 10  # 10 seconds for health check response

    async def detect_zombie_managers(self, managers: Dict[str, Any], health_data: Dict[str, ManagerHealth]) -> List[str]:
        """
        Detect zombie managers using multiple detection methods

        Args:
            managers: Dictionary of active managers
            health_data: Current health data for managers

        Returns:
            List of manager keys identified as zombies
        """
        zombie_keys = []
        now = datetime.now(timezone.utc)

        for manager_key, manager in managers.items():
            health = health_data.get(manager_key)
            if not health:
                continue

            # Method 1: Activity-based detection
            if self._is_activity_zombie(health, now):
                zombie_keys.append(manager_key)
                continue

            # Method 2: Connection responsiveness detection
            if await self._is_connection_zombie(manager, health):
                zombie_keys.append(manager_key)
                continue

            # Method 3: Memory leak detection
            if self._is_memory_leak_zombie(manager, health):
                zombie_keys.append(manager_key)
                continue

        if zombie_keys:
            logger.warning(f"Zombie detection engine identified {len(zombie_keys)} zombie managers: {zombie_keys}")

        return zombie_keys

    def _is_activity_zombie(self, health: ManagerHealth, now: datetime) -> bool:
        """Check if manager is zombie based on activity"""
        if health.last_activity:
            inactivity_seconds = (now - health.last_activity).total_seconds()
            return inactivity_seconds > self.detection_threshold
        return False

    async def _is_connection_zombie(self, manager: Any, health: ManagerHealth) -> bool:
        """Check if manager has zombie connections"""
        try:
            # Check if manager has connections but none are responsive
            if hasattr(manager, '_connections') and manager._connections:
                total_connections = len(manager._connections)
                if total_connections > 0 and health.responsive_connections == 0:
                    # Try a quick health check on connections
                    responsive_count = 0
                    for conn in list(manager._connections.values()):
                        if await self._is_connection_responsive(conn):
                            responsive_count += 1

                    # Update health data with real-time check
                    health.responsive_connections = responsive_count
                    health.connection_count = total_connections

                    return responsive_count == 0 and total_connections > 0

        except Exception as e:
            logger.warning(f"Error checking connection responsiveness: {e}")

        return False

    async def _is_connection_responsive(self, connection: Any) -> bool:
        """Check if individual connection is responsive"""
        try:
            if hasattr(connection, 'websocket') and connection.websocket:
                # Quick ping check with timeout
                await asyncio.wait_for(
                    connection.websocket.ping(),
                    timeout=self.response_timeout
                )
                return True
        except (asyncio.TimeoutError, Exception):
            return False
        return False

    def _is_memory_leak_zombie(self, manager: Any, health: ManagerHealth) -> bool:
        """Check if manager has memory leak characteristics"""
        try:
            # Check for excessive reference counts or memory usage patterns
            if hasattr(manager, '__dict__'):
                # Count references and check for circular references
                ref_count = len(manager.__dict__)
                if ref_count > 100:  # Arbitrary threshold for excessive references
                    logger.warning(f"Manager has excessive references: {ref_count}")
                    return True

        except Exception as e:
            logger.debug(f"Error checking memory leak characteristics: {e}")

        return False


class EnhancedWebSocketManagerFactory:
    """
    Enhanced WebSocket Manager Factory with comprehensive emergency cleanup

    CRITICAL REMEDIATION: This factory addresses the P0 issue where emergency
    cleanup fails when users hit the 20/20 manager limit, causing permanent
    chat blocking for affected users.
    """

    def __init__(self, max_managers_per_user: int = 20):
        """Initialize enhanced factory with resource management"""
        self.max_managers_per_user = max_managers_per_user
        self.id_manager = UnifiedIDManager()

        # Registry and tracking
        self._active_managers: Dict[str, _UnifiedWebSocketManagerImplementation] = {}
        self._user_manager_keys: Dict[str, Set[str]] = {}
        self._creation_times: Dict[str, datetime] = {}
        self._manager_health: Dict[str, ManagerHealth] = {}

        # Cleanup configuration
        self._proactive_threshold = 0.8  # Start cleanup at 80% of limit
        self._moderate_threshold = 0.85  # Moderate cleanup at 85%
        self._aggressive_threshold = 0.9  # Aggressive cleanup at 90%

        # Metrics and monitoring
        self._metrics = FactoryMetrics()
        self._registry_lock = threading.Lock()

        # Enhanced systems
        self.zombie_detector = ZombieDetectionEngine()
        self.circuit_breaker = CircuitBreakerState()

        # Health monitoring
        self._last_health_check = datetime.now(timezone.utc)
        self._health_check_interval = 60  # 1 minute

        logger.info(f"Enhanced WebSocket Manager Factory initialized with {max_managers_per_user}-manager limit")

    async def create_manager(self, user_context: Any, mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED) -> _UnifiedWebSocketManagerImplementation:
        """
        Create WebSocket manager with enhanced emergency cleanup

        Args:
            user_context: User execution context
            mode: WebSocket manager mode

        Returns:
            WebSocket manager instance

        Raises:
            RuntimeError: If resource limits exceeded and all cleanup attempts fail
        """
        user_id = str(getattr(user_context, 'user_id', 'unknown'))

        with self._registry_lock:
            current_count = self.get_user_manager_count(user_id)

            # Proactive cleanup before hitting limits
            if current_count >= self.max_managers_per_user * self._proactive_threshold:
                logger.warning(f"User {user_id} approaching limit ({current_count}/{self.max_managers_per_user}), starting proactive cleanup")

                cleanup_level = self._determine_cleanup_level(current_count)
                await self._enhanced_emergency_cleanup(user_id, cleanup_level)
                current_count = self.get_user_manager_count(user_id)

            # Hard limit enforcement with graduated emergency cleanup
            if current_count >= self.max_managers_per_user:
                logger.critical(f"HARD LIMIT: User {user_id} over limit ({current_count}/{self.max_managers_per_user}) - attempting enhanced emergency cleanup")

                success = await self._graduated_emergency_cleanup(user_id)
                if not success:
                    error_msg = (
                        f"CRITICAL: Emergency cleanup FAILED for user {user_id}. "
                        f"User has reached maximum WebSocket managers ({self.max_managers_per_user}) "
                        f"and all cleanup attempts have been exhausted. This indicates "
                        f"zombie managers or resource leaks requiring immediate investigation."
                    )
                    logger.critical(error_msg)

                    self._metrics.failed_cleanups += 1
                    self.circuit_breaker.record_failure()

                    raise RuntimeError(error_msg)

                current_count = self.get_user_manager_count(user_id)
                logger.info(f"SUCCESS: Enhanced emergency cleanup freed space for user {user_id}")

                self.circuit_breaker.record_success()
                self._metrics.record_business_protection("emergency_cleanup_success")

            # Create the manager
            return await self._create_manager_instance(user_context, mode, user_id)

    async def _graduated_emergency_cleanup(self, user_id: str) -> bool:
        """
        Graduated emergency cleanup with all enhancement levels

        Args:
            user_id: User ID to clean up managers for

        Returns:
            bool: True if cleanup succeeded, False if failed
        """
        if not self.circuit_breaker.should_attempt_cleanup():
            logger.error(f"Circuit breaker OPEN - skipping cleanup attempt for user {user_id}")
            self._metrics.circuit_breaker_activations += 1
            return False

        cleanup_levels = [CleanupLevel.CONSERVATIVE, CleanupLevel.MODERATE, CleanupLevel.AGGRESSIVE, CleanupLevel.FORCE]
        total_cleaned = 0

        for level in cleanup_levels:
            current_count = self.get_user_manager_count(user_id)
            if current_count < self.max_managers_per_user:
                logger.info(f"Graduated cleanup SUCCESS at {level.value} level for user {user_id}")
                return True

            logger.warning(f"Escalating to {level.value} cleanup for user {user_id}")
            cleaned = await self._enhanced_emergency_cleanup(user_id, level)
            total_cleaned += cleaned

            logger.info(f"Level {level.value} cleaned {cleaned} managers for user {user_id}")

        # Final check
        final_count = self.get_user_manager_count(user_id)
        success = final_count < self.max_managers_per_user

        if success:
            logger.info(f"Graduated cleanup FINAL SUCCESS: User {user_id} now at {final_count}/{self.max_managers_per_user} (cleaned {total_cleaned})")
        else:
            logger.critical(f"Graduated cleanup FINAL FAILURE: User {user_id} still at {final_count}/{self.max_managers_per_user} after cleaning {total_cleaned}")

        return success

    async def _enhanced_emergency_cleanup(self, user_id: str, cleanup_level: CleanupLevel) -> int:
        """
        Enhanced emergency cleanup with zombie detection and health validation

        Args:
            user_id: User ID to clean up managers for
            cleanup_level: Cleanup aggressiveness level

        Returns:
            Number of managers cleaned up
        """
        start_time = time.time()
        cleaned_count = 0

        logger.warning(f"Starting enhanced emergency cleanup for user {user_id} at level {cleanup_level.value}")

        user_manager_keys = self._user_manager_keys.get(user_id, set()).copy()
        if not user_manager_keys:
            logger.warning(f"No managers found for user {user_id}")
            return 0

        # Update health data for all managers
        await self._update_manager_health(user_manager_keys)

        # Detect zombie managers
        zombie_managers = await self.zombie_detector.detect_zombie_managers(
            {key: self._active_managers[key] for key in user_manager_keys if key in self._active_managers},
            {key: self._manager_health[key] for key in user_manager_keys if key in self._manager_health}
        )

        if zombie_managers:
            self._metrics.zombie_managers_detected += len(zombie_managers)
            logger.warning(f"Detected {len(zombie_managers)} zombie managers for user {user_id}")

        # Determine cleanup targets based on level
        cleanup_targets = []

        if cleanup_level == CleanupLevel.CONSERVATIVE:
            # Only remove clearly inactive managers
            cleanup_targets = [key for key in user_manager_keys
                             if self._manager_health.get(key, ManagerHealth(ManagerHealthStatus.UNKNOWN)).status == ManagerHealthStatus.INACTIVE]

        elif cleanup_level == CleanupLevel.MODERATE:
            # Remove inactive + old idle managers
            cleanup_targets = [key for key in user_manager_keys
                             if self._manager_health.get(key, ManagerHealth(ManagerHealthStatus.UNKNOWN)).status in
                             [ManagerHealthStatus.INACTIVE, ManagerHealthStatus.IDLE] and
                             self._manager_health.get(key, ManagerHealth(ManagerHealthStatus.UNKNOWN)).age_seconds > 300]

        elif cleanup_level == CleanupLevel.AGGRESSIVE:
            # Remove inactive + idle + zombie managers
            cleanup_targets = [key for key in user_manager_keys
                             if (self._manager_health.get(key, ManagerHealth(ManagerHealthStatus.UNKNOWN)).status in
                                 [ManagerHealthStatus.INACTIVE, ManagerHealthStatus.IDLE, ManagerHealthStatus.ZOMBIE] or
                                 key in zombie_managers)]
            self._metrics.aggressive_cleanups_triggered += 1

        elif cleanup_level == CleanupLevel.FORCE:
            # Force remove oldest managers (nuclear option)
            sorted_by_age = sorted(user_manager_keys,
                                 key=lambda k: self._creation_times.get(k, datetime.now(timezone.utc)))
            cleanup_targets = sorted_by_age[:len(user_manager_keys)//2]  # Remove oldest 50%
            logger.critical(f"FORCE cleanup targeting {len(cleanup_targets)} oldest managers for user {user_id}")

        # Perform cleanup
        for manager_key in cleanup_targets:
            try:
                if await self._cleanup_manager(manager_key, user_id):
                    cleaned_count += 1
                    logger.debug(f"Cleaned up manager {manager_key} for user {user_id}")
                else:
                    logger.warning(f"Failed to cleanup manager {manager_key} for user {user_id}")
            except Exception as e:
                logger.error(f"Error cleaning up manager {manager_key} for user {user_id}: {e}")

        cleanup_duration = time.time() - start_time

        # Update metrics
        self._metrics.cleanup_events += 1
        if cleanup_level != CleanupLevel.CONSERVATIVE:
            self._metrics.emergency_cleanups += 1

        logger.info(f"Enhanced emergency cleanup completed: level={cleanup_level.value}, "
                   f"user={user_id}, cleaned={cleaned_count}, targets={len(cleanup_targets)}, "
                   f"duration={cleanup_duration:.2f}s")

        return cleaned_count

    async def _update_manager_health(self, manager_keys: Set[str]):
        """Update health data for all managers"""
        now = datetime.now(timezone.utc)

        for key in manager_keys:
            if key not in self._active_managers:
                continue

            manager = self._active_managers[key]
            health = self._manager_health.get(key, ManagerHealth(ManagerHealthStatus.UNKNOWN))

            # Update basic health metrics
            try:
                # Check connection count
                connection_count = 0
                responsive_connections = 0

                if hasattr(manager, '_connections') and manager._connections:
                    connection_count = len(manager._connections)

                    # Quick responsiveness check for some connections
                    sample_connections = list(manager._connections.values())[:3]  # Check up to 3 connections
                    for conn in sample_connections:
                        if await self._quick_connection_check(conn):
                            responsive_connections += 1

                # Determine health status
                if connection_count == 0:
                    status = ManagerHealthStatus.IDLE
                elif responsive_connections == 0 and connection_count > 0:
                    status = ManagerHealthStatus.ZOMBIE
                elif responsive_connections > 0:
                    status = ManagerHealthStatus.HEALTHY
                else:
                    status = ManagerHealthStatus.UNKNOWN

                # Calculate health score
                if connection_count > 0:
                    health_score = responsive_connections / connection_count
                else:
                    health_score = 0.5  # Neutral score for idle managers

                # Update health data
                health.status = status
                health.connection_count = connection_count
                health.responsive_connections = responsive_connections
                health.health_score = health_score
                health.last_health_check = now

                self._manager_health[key] = health

            except Exception as e:
                logger.debug(f"Error updating health for manager {key}: {e}")
                health.status = ManagerHealthStatus.UNKNOWN
                self._manager_health[key] = health

    async def _quick_connection_check(self, connection: Any) -> bool:
        """Quick health check for a connection"""
        try:
            if hasattr(connection, 'websocket') and connection.websocket:
                # Very quick ping with short timeout
                await asyncio.wait_for(connection.websocket.ping(), timeout=2.0)
                return True
        except Exception:
            pass
        return False

    async def _cleanup_manager(self, manager_key: str, user_id: str) -> bool:
        """Cleanup individual manager with proper resource handling"""
        try:
            manager = self._active_managers.get(manager_key)
            if not manager:
                return True  # Already cleaned up

            # Graceful shutdown of manager
            if hasattr(manager, 'shutdown'):
                try:
                    await asyncio.wait_for(manager.shutdown(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Manager {manager_key} shutdown timed out")

            # Close connections
            if hasattr(manager, '_connections') and manager._connections:
                for conn in list(manager._connections.values()):
                    try:
                        if hasattr(conn, 'websocket') and conn.websocket:
                            await conn.websocket.close()
                    except Exception as e:
                        logger.debug(f"Error closing connection: {e}")

            # Remove from registries
            if manager_key in self._active_managers:
                del self._active_managers[manager_key]
            if manager_key in self._creation_times:
                del self._creation_times[manager_key]
            if manager_key in self._manager_health:
                del self._manager_health[manager_key]

            # Update user tracking
            if user_id in self._user_manager_keys:
                self._user_manager_keys[user_id].discard(manager_key)
                if not self._user_manager_keys[user_id]:
                    del self._user_manager_keys[user_id]

            # Force garbage collection for the manager
            del manager
            gc.collect()

            return True

        except Exception as e:
            logger.error(f"Error cleaning up manager {manager_key}: {e}")
            return False

    async def _create_manager_instance(self, user_context: Any, mode: WebSocketManagerMode, user_id: str) -> _UnifiedWebSocketManagerImplementation:
        """Create and register new manager instance"""
        manager_key = self._generate_manager_key(user_context)

        try:
            # Import here to avoid circular imports
            from netra_backend.app.websocket_core.types import create_isolated_mode
            import secrets

            # Create isolated manager instance
            isolated_mode = create_isolated_mode(mode.value)
            manager = _UnifiedWebSocketManagerImplementation(
                mode=isolated_mode,
                user_context=user_context,
                _ssot_authorization_token=secrets.token_urlsafe(32)
            )

            # Register manager
            self._active_managers[manager_key] = manager
            self._creation_times[manager_key] = datetime.now(timezone.utc)

            # Update user manager tracking
            if user_id not in self._user_manager_keys:
                self._user_manager_keys[user_id] = set()
            self._user_manager_keys[user_id].add(manager_key)

            # Initialize health tracking
            self._manager_health[manager_key] = ManagerHealth(
                status=ManagerHealthStatus.HEALTHY,
                last_activity=datetime.now(timezone.utc),
                creation_time=datetime.now(timezone.utc)
            )

            # Update metrics
            self._metrics.total_managers = len(self._active_managers)
            self._metrics.managers_by_user[user_id] = len(self._user_manager_keys[user_id])

            logger.info(f"Enhanced WebSocket manager created: key={manager_key}, user={user_id}, total={self._metrics.total_managers}")
            return manager

        except Exception as e:
            logger.error(f"Failed to create WebSocket manager for user {user_id}: {e}")
            raise

    def _determine_cleanup_level(self, current_count: int) -> CleanupLevel:
        """Determine appropriate cleanup level based on resource pressure"""
        usage_ratio = current_count / self.max_managers_per_user

        if usage_ratio >= self._aggressive_threshold:
            return CleanupLevel.AGGRESSIVE
        elif usage_ratio >= self._moderate_threshold:
            return CleanupLevel.MODERATE
        else:
            return CleanupLevel.CONSERVATIVE

    def _generate_manager_key(self, user_context: Any) -> str:
        """Generate unique manager key"""
        user_id = str(getattr(user_context, 'user_id', 'unknown'))
        unique_id = self.id_manager.generate_id(IDType.REQUEST, prefix="mgr")
        return f"{user_id}_{unique_id}"

    def get_user_manager_count(self, user_id: str) -> int:
        """Get current manager count for user"""
        return len(self._user_manager_keys.get(user_id, set()))

    def get_factory_status(self) -> Dict[str, Any]:
        """Get comprehensive factory status"""
        return {
            "total_managers": self._metrics.total_managers,
            "managers_by_user": dict(self._metrics.managers_by_user),
            "max_per_user": self.max_managers_per_user,
            "cleanup_events": self._metrics.cleanup_events,
            "emergency_cleanups": self._metrics.emergency_cleanups,
            "failed_cleanups": self._metrics.failed_cleanups,
            "zombie_managers_detected": self._metrics.zombie_managers_detected,
            "circuit_breaker": {
                "is_open": self.circuit_breaker.is_open,
                "failure_count": self.circuit_breaker.failure_count,
                "activations": self._metrics.circuit_breaker_activations
            },
            "health_check": {
                "last_check": self._last_health_check.isoformat(),
                "interval_seconds": self._health_check_interval
            }
        }


# Global factory instance
_enhanced_factory_instance: Optional[EnhancedWebSocketManagerFactory] = None
_factory_lock = threading.Lock()


def get_enhanced_websocket_factory() -> EnhancedWebSocketManagerFactory:
    """Get the global enhanced WebSocket manager factory instance"""
    global _enhanced_factory_instance

    with _factory_lock:
        if _enhanced_factory_instance is None:
            _enhanced_factory_instance = EnhancedWebSocketManagerFactory()
            logger.info("Enhanced WebSocket Manager Factory initialized")

        return _enhanced_factory_instance


# Integration with existing websocket_manager.py
async def create_manager_with_enhanced_cleanup(user_context: Any, mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED) -> _UnifiedWebSocketManagerImplementation:
    """
    Create WebSocket manager using enhanced factory with emergency cleanup

    This function integrates with the existing get_websocket_manager() function
    to provide enhanced emergency cleanup capabilities.
    """
    factory = get_enhanced_websocket_factory()
    return await factory.create_manager(user_context, mode)


# Export key components
__all__ = [
    'EnhancedWebSocketManagerFactory',
    'ZombieDetectionEngine',
    'CleanupLevel',
    'ManagerHealthStatus',
    'ManagerHealth',
    'CircuitBreakerState',
    'get_enhanced_websocket_factory',
    'create_manager_with_enhanced_cleanup'
]

logger.info("Enhanced WebSocket Manager Factory module loaded - Emergency cleanup system active")