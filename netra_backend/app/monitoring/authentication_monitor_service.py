"""
AuthenticationMonitorService - SSOT for WebSocket Authentication Monitoring

Business Value Justification:
- Segment: Platform/Internal - WebSocket Infrastructure  
- Business Goal: Restore WebSocket functionality and ensure reliable authentication monitoring
- Value Impact: Enables monitoring of authentication failures to prevent user session disruption
- Revenue Impact: Protects chat functionality that drives user engagement and retention

CRITICAL SSOT COMPLIANCE:
This module provides unified authentication monitoring for WebSocket connections,
integrating with existing authentication infrastructure while maintaining SSOT patterns.

Features:
- Real-time authentication status monitoring
- Integration with existing AuthenticationConnectionMonitor
- Health status aggregation for multiple auth validation points
- Authentication success/failure rate tracking
- Authentication latency monitoring
- Circuit breaker integration
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.websocket_core.unified_emitter import AuthenticationConnectionMonitor

logger = get_logger(__name__)


class AuthenticationStatus(Enum):
    """Authentication monitoring status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class AuthenticationMetrics:
    """Authentication monitoring metrics."""
    total_attempts: int = 0
    successful_authentications: int = 0
    failed_authentications: int = 0
    authentication_timeouts: int = 0
    circuit_breaker_trips: int = 0
    average_response_time_ms: float = 0.0
    last_success_timestamp: Optional[datetime] = None
    last_failure_timestamp: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success_rate(self) -> float:
        """Calculate authentication success rate percentage."""
        if self.total_attempts == 0:
            return 100.0  # Default to healthy if no attempts
        return (self.successful_authentications / self.total_attempts) * 100.0

    @property
    def failure_rate(self) -> float:
        """Calculate authentication failure rate percentage."""
        return 100.0 - self.success_rate

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            "total_attempts": self.total_attempts,
            "successful_authentications": self.successful_authentications,
            "failed_authentications": self.failed_authentications,
            "authentication_timeouts": self.authentication_timeouts,
            "circuit_breaker_trips": self.circuit_breaker_trips,
            "average_response_time_ms": round(self.average_response_time_ms, 2),
            "success_rate_percent": round(self.success_rate, 2),
            "failure_rate_percent": round(self.failure_rate, 2),
            "last_success_timestamp": self.last_success_timestamp.isoformat() if self.last_success_timestamp else None,
            "last_failure_timestamp": self.last_failure_timestamp.isoformat() if self.last_failure_timestamp else None,
            "uptime_seconds": (datetime.now(timezone.utc) - self.created_at).total_seconds()
        }


@dataclass
class AuthenticationHealthStatus:
    """Authentication health status summary."""
    status: AuthenticationStatus
    metrics: AuthenticationMetrics
    active_connections: int = 0
    unhealthy_connections: int = 0
    monitoring_enabled: bool = True
    last_health_check: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert health status to dictionary for serialization."""
        return {
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "active_connections": self.active_connections,
            "unhealthy_connections": self.unhealthy_connections,
            "monitoring_enabled": self.monitoring_enabled,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class AuthenticationMonitorService:
    """
    SSOT Authentication Monitoring Service.
    
    This service provides centralized authentication monitoring for WebSocket connections,
    integrating with existing authentication infrastructure while maintaining SSOT patterns.
    
    Key Features:
    - Aggregates health status from multiple auth validation points
    - Tracks authentication success/failure rates
    - Monitors authentication latency
    - Integrates with circuit breaker patterns
    - Provides health status for integration with health endpoints
    """

    def __init__(self, websocket_manager=None):
        """
        Initialize the authentication monitoring service.
        
        Args:
            websocket_manager: Optional WebSocket manager for connection monitoring
        """
        self.websocket_manager = websocket_manager
        self.metrics = AuthenticationMetrics()
        self.response_times: List[float] = []  # Track last 100 response times
        self.max_response_times = 100
        
        # Integration with existing AuthenticationConnectionMonitor
        self.connection_monitor: Optional[AuthenticationConnectionMonitor] = None
        if websocket_manager:
            try:
                self.connection_monitor = AuthenticationConnectionMonitor(websocket_manager)
                logger.info("AuthenticationMonitorService integrated with existing AuthenticationConnectionMonitor")
            except Exception as e:
                logger.warning(f"Failed to initialize AuthenticationConnectionMonitor integration: {e}")
        
        # Health status tracking
        self.last_health_check = datetime.now(timezone.utc)
        self.health_check_interval = 30.0  # seconds
        self.health_errors: List[str] = []
        self.health_warnings: List[str] = []
        
        # Circuit breaker integration
        self.circuit_breaker_enabled = True
        self.circuit_breaker_threshold = 50.0  # Failure rate threshold (%)
        self.circuit_breaker_timeout = 60.0  # seconds
        self.circuit_breaker_open = False
        self.circuit_breaker_last_trip = None
        
        logger.info("AuthenticationMonitorService initialized")

    async def record_authentication_attempt(
        self, 
        success: bool, 
        response_time_ms: float, 
        user_id: Optional[str] = None,
        error_details: Optional[str] = None
    ) -> None:
        """
        Record an authentication attempt and update metrics.
        
        Args:
            success: Whether the authentication was successful
            response_time_ms: Response time in milliseconds
            user_id: Optional user ID for tracking
            error_details: Optional error details for failed attempts
        """
        try:
            # Update basic metrics
            self.metrics.total_attempts += 1
            
            if success:
                self.metrics.successful_authentications += 1
                self.metrics.last_success_timestamp = datetime.now(timezone.utc)
                logger.debug(f"Authentication success recorded for user {user_id[:8] if user_id else 'unknown'}...")
            else:
                self.metrics.failed_authentications += 1
                self.metrics.last_failure_timestamp = datetime.now(timezone.utc)
                logger.warning(f"Authentication failure recorded for user {user_id[:8] if user_id else 'unknown'}...: {error_details}")
                
                # Check for timeout-specific failures
                if error_details and "timeout" in error_details.lower():
                    self.metrics.authentication_timeouts += 1
            
            # Update response time tracking
            self.response_times.append(response_time_ms)
            if len(self.response_times) > self.max_response_times:
                self.response_times.pop(0)  # Remove oldest
            
            # Recalculate average response time
            if self.response_times:
                self.metrics.average_response_time_ms = sum(self.response_times) / len(self.response_times)
            
            # Check circuit breaker conditions
            await self._check_circuit_breaker()
            
            logger.debug(f"Authentication attempt recorded: success={success}, response_time={response_time_ms}ms")
            
        except Exception as e:
            logger.error(f"Error recording authentication attempt: {e}")

    async def record_circuit_breaker_trip(self, reason: str) -> None:
        """
        Record a circuit breaker trip event.
        
        Args:
            reason: Reason for the circuit breaker trip
        """
        try:
            self.metrics.circuit_breaker_trips += 1
            self.circuit_breaker_open = True
            self.circuit_breaker_last_trip = datetime.now(timezone.utc)
            
            logger.critical(f"CIRCUIT BREAKER TRIP: {reason}")
            
        except Exception as e:
            logger.error(f"Error recording circuit breaker trip: {e}")

    async def get_health_status(self) -> AuthenticationHealthStatus:
        """
        Get current authentication health status.
        
        Returns:
            AuthenticationHealthStatus with current health metrics
        """
        try:
            await self._update_health_status()
            
            # Determine overall status
            status = self._calculate_overall_status()
            
            # Get connection counts if available
            active_connections = 0
            unhealthy_connections = 0
            
            if self.connection_monitor:
                try:
                    monitor_stats = self.connection_monitor.get_monitoring_stats()
                    unhealthy_connections = monitor_stats.get("unhealthy_connections_detected", 0)
                    # Active connections would come from websocket manager
                    if self.websocket_manager and hasattr(self.websocket_manager, 'get_active_connection_count'):
                        active_connections = self.websocket_manager.get_active_connection_count()
                except Exception as e:
                    logger.warning(f"Error getting connection monitor stats: {e}")
            
            health_status = AuthenticationHealthStatus(
                status=status,
                metrics=self.metrics,
                active_connections=active_connections,
                unhealthy_connections=unhealthy_connections,
                monitoring_enabled=True,
                last_health_check=self.last_health_check,
                errors=self.health_errors.copy(),
                warnings=self.health_warnings.copy()
            )
            
            logger.debug(f"Authentication health status: {status.value} (success_rate: {self.metrics.success_rate:.1f}%)")
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error getting authentication health status: {e}")
            
            # Return degraded status on error
            return AuthenticationHealthStatus(
                status=AuthenticationStatus.DEGRADED,
                metrics=self.metrics,
                monitoring_enabled=False,
                last_health_check=self.last_health_check,
                errors=[f"Health status check failed: {str(e)}"]
            )

    async def ensure_auth_connection_health(self, user_id: str) -> bool:
        """
        Ensure authentication connection health for a specific user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self.connection_monitor:
                logger.warning("Connection monitor not available for health check")
                return True  # Assume healthy if monitor not available
            
            # Use existing AuthenticationConnectionMonitor
            await self.connection_monitor.ensure_auth_connection_health(user_id)
            return True
            
        except Exception as e:
            logger.error(f"Authentication connection health check failed for user {user_id}: {e}")
            await self.record_authentication_attempt(
                success=False,
                response_time_ms=0.0,
                user_id=user_id,
                error_details=f"Connection health check failed: {str(e)}"
            )
            return False

    async def monitor_auth_session(
        self, 
        user_id: str, 
        session_duration_ms: int = 30000
    ) -> Dict[str, Any]:
        """
        Monitor authentication session for a user.
        
        Args:
            user_id: User ID to monitor
            session_duration_ms: How long to monitor (default 30s)
            
        Returns:
            Dictionary with monitoring results
        """
        try:
            if not self.connection_monitor:
                logger.warning("Connection monitor not available for session monitoring")
                return {
                    "user_id": user_id,
                    "monitoring_available": False,
                    "error": "Connection monitor not initialized"
                }
            
            # Use existing AuthenticationConnectionMonitor
            return await self.connection_monitor.monitor_auth_session(user_id, session_duration_ms)
            
        except Exception as e:
            logger.error(f"Error monitoring auth session for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "monitoring_available": False,
                "error": str(e)
            }

    def get_authentication_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive authentication statistics.
        
        Returns:
            Dictionary with authentication statistics
        """
        try:
            stats = {
                "service_info": {
                    "name": "AuthenticationMonitorService",
                    "ssot_compliant": True,
                    "monitoring_enabled": True,
                    "integration_with_connection_monitor": self.connection_monitor is not None
                },
                "metrics": self.metrics.to_dict(),
                "circuit_breaker": {
                    "enabled": self.circuit_breaker_enabled,
                    "is_open": self.circuit_breaker_open,
                    "threshold_percent": self.circuit_breaker_threshold,
                    "timeout_seconds": self.circuit_breaker_timeout,
                    "last_trip": self.circuit_breaker_last_trip.isoformat() if self.circuit_breaker_last_trip else None
                },
                "health_status": {
                    "last_check": self.last_health_check.isoformat(),
                    "check_interval_seconds": self.health_check_interval,
                    "errors_count": len(self.health_errors),
                    "warnings_count": len(self.health_warnings)
                },
                "response_time_analysis": {
                    "samples_count": len(self.response_times),
                    "average_ms": round(self.metrics.average_response_time_ms, 2),
                    "min_ms": round(min(self.response_times), 2) if self.response_times else 0,
                    "max_ms": round(max(self.response_times), 2) if self.response_times else 0
                }
            }
            
            # Add connection monitor stats if available
            if self.connection_monitor:
                try:
                    monitor_stats = self.connection_monitor.get_monitoring_stats()
                    stats["connection_monitor"] = monitor_stats
                except Exception as e:
                    stats["connection_monitor"] = {"error": str(e)}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting authentication stats: {e}")
            return {
                "service_info": {
                    "name": "AuthenticationMonitorService",
                    "error": str(e)
                }
            }

    async def _check_circuit_breaker(self) -> None:
        """Check and update circuit breaker status based on failure rate."""
        try:
            if not self.circuit_breaker_enabled:
                return
            
            # Check if circuit breaker should close (reset)
            if self.circuit_breaker_open and self.circuit_breaker_last_trip:
                time_since_trip = (datetime.now(timezone.utc) - self.circuit_breaker_last_trip).total_seconds()
                if time_since_trip > self.circuit_breaker_timeout:
                    self.circuit_breaker_open = False
                    logger.info("Circuit breaker reset after timeout")
                    return
            
            # Check if circuit breaker should trip
            if not self.circuit_breaker_open and self.metrics.failure_rate > self.circuit_breaker_threshold:
                # Only trip if we have enough samples
                if self.metrics.total_attempts >= 5:
                    await self.record_circuit_breaker_trip(
                        f"Failure rate {self.metrics.failure_rate:.1f}% exceeds threshold {self.circuit_breaker_threshold}%"
                    )
            
        except Exception as e:
            logger.error(f"Error checking circuit breaker: {e}")

    def _calculate_overall_status(self) -> AuthenticationStatus:
        """Calculate overall authentication status based on metrics."""
        try:
            # If circuit breaker is open, status is critical
            if self.circuit_breaker_open:
                return AuthenticationStatus.CRITICAL
            
            # If no attempts yet, status is unknown
            if self.metrics.total_attempts == 0:
                return AuthenticationStatus.UNKNOWN
            
            # Check failure rate thresholds
            failure_rate = self.metrics.failure_rate
            
            if failure_rate >= 50.0:  # 50% or more failures
                return AuthenticationStatus.CRITICAL
            elif failure_rate >= 20.0:  # 20-49% failures
                return AuthenticationStatus.DEGRADED
            elif failure_rate >= 5.0:  # 5-19% failures
                return AuthenticationStatus.DEGRADED
            else:  # Less than 5% failures
                return AuthenticationStatus.HEALTHY
            
        except Exception as e:
            logger.error(f"Error calculating overall status: {e}")
            return AuthenticationStatus.UNKNOWN

    async def _update_health_status(self) -> None:
        """Update internal health status tracking."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Clear old errors and warnings
            self.health_errors.clear()
            self.health_warnings.clear()
            
            # Check if health check is overdue
            time_since_last_check = (current_time - self.last_health_check).total_seconds()
            if time_since_last_check > self.health_check_interval * 2:
                self.health_warnings.append(f"Health check overdue by {time_since_last_check:.1f}s")
            
            # Check for concerning patterns
            if self.metrics.total_attempts > 0:
                if self.metrics.failure_rate > 30.0:
                    self.health_errors.append(f"High failure rate: {self.metrics.failure_rate:.1f}%")
                elif self.metrics.failure_rate > 10.0:
                    self.health_warnings.append(f"Elevated failure rate: {self.metrics.failure_rate:.1f}%")
            
            # Check response times
            if self.metrics.average_response_time_ms > 5000:  # 5 seconds
                self.health_errors.append(f"High response time: {self.metrics.average_response_time_ms:.1f}ms")
            elif self.metrics.average_response_time_ms > 2000:  # 2 seconds
                self.health_warnings.append(f"Elevated response time: {self.metrics.average_response_time_ms:.1f}ms")
            
            # Check for authentication timeouts
            if self.metrics.authentication_timeouts > 5:
                self.health_warnings.append(f"Multiple authentication timeouts: {self.metrics.authentication_timeouts}")
            
            self.last_health_check = current_time
            
        except Exception as e:
            logger.error(f"Error updating health status: {e}")
            self.health_errors.append(f"Health status update failed: {str(e)}")


# Global SSOT instance for authentication monitoring
_authentication_monitor_service: Optional[AuthenticationMonitorService] = None


def get_authentication_monitor_service(websocket_manager=None) -> AuthenticationMonitorService:
    """
    Get the global SSOT authentication monitoring service.
    
    Args:
        websocket_manager: Optional WebSocket manager for connection monitoring
        
    Returns:
        AuthenticationMonitorService instance (SSOT for auth monitoring)
    """
    global _authentication_monitor_service
    if _authentication_monitor_service is None:
        _authentication_monitor_service = AuthenticationMonitorService(websocket_manager)
        logger.info("SSOT ENFORCEMENT: AuthenticationMonitorService instance created")
    return _authentication_monitor_service


async def record_auth_attempt(
    success: bool,
    response_time_ms: float,
    user_id: Optional[str] = None,
    error_details: Optional[str] = None,
    websocket_manager=None
) -> None:
    """
    Convenience function to record authentication attempts.
    
    Args:
        success: Whether the authentication was successful
        response_time_ms: Response time in milliseconds
        user_id: Optional user ID for tracking
        error_details: Optional error details for failed attempts
        websocket_manager: Optional WebSocket manager for service initialization
    """
    monitor_service = get_authentication_monitor_service(websocket_manager)
    await monitor_service.record_authentication_attempt(
        success=success,
        response_time_ms=response_time_ms,
        user_id=user_id,
        error_details=error_details
    )


async def get_auth_health_status(websocket_manager=None) -> AuthenticationHealthStatus:
    """
    Convenience function to get authentication health status.
    
    Args:
        websocket_manager: Optional WebSocket manager for service initialization
        
    Returns:
        AuthenticationHealthStatus with current health metrics
    """
    monitor_service = get_authentication_monitor_service(websocket_manager)
    return await monitor_service.get_health_status()


# SSOT ENFORCEMENT: Export only SSOT-compliant interfaces
__all__ = [
    "AuthenticationMonitorService",
    "AuthenticationStatus",
    "AuthenticationMetrics",
    "AuthenticationHealthStatus",
    "get_authentication_monitor_service",
    "record_auth_attempt",
    "get_auth_health_status"
]