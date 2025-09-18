"""
AuthHealthProvider - Authentication Health Status for Health Endpoints

Business Value Justification:
- Segment: Platform/Internal - WebSocket Infrastructure  
- Business Goal: Ensure authentication monitoring is accessible via health endpoints
- Value Impact: Enables monitoring and alerting on authentication health status
- Revenue Impact: Prevents chat functionality disruption through proactive monitoring

CRITICAL SSOT COMPLIANCE:
This module provides authentication health status integration with existing health endpoints,
using the AuthenticationMonitorService as the SSOT for authentication metrics.

Features:
- Integration with AuthenticationMonitorService for health data
- Standardized health response format for monitoring systems
- Authentication success/failure rate tracking for health endpoints
- Circuit breaker status integration
- Authentication latency monitoring for health checks
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.monitoring.authentication_monitor_service import (
    get_authentication_monitor_service,
    AuthenticationStatus,
    AuthenticationHealthStatus
)

logger = get_logger(__name__)


class AuthHealthProvider:
    """
    Authentication Health Provider for Health Endpoint Integration.
    
    This class provides authentication health status data for integration with
    system health endpoints, using the AuthenticationMonitorService as the SSOT
    for authentication metrics and status.
    
    Key Features:
    - Interface with AuthenticationMonitorService for health data
    - Standardized health response format for monitoring
    - Authentication metrics aggregation for health checks
    - Circuit breaker status integration
    - Health status caching for performance
    """

    def __init__(self, websocket_manager=None):
        """
        Initialize the authentication health provider.
        
        Args:
            websocket_manager: Optional WebSocket manager for monitor service initialization
        """
        self.websocket_manager = websocket_manager
        self.monitor_service = get_authentication_monitor_service(websocket_manager)
        
        # Health status caching
        self.last_health_check = None
        self.cached_health_status = None
        self.cache_duration_seconds = 10  # Cache for 10 seconds
        
        logger.info("AuthHealthProvider initialized")

    async def get_authentication_health_status(self) -> Dict[str, Any]:
        """
        Get authentication health status for health endpoints.
        
        Returns:
            Dictionary with authentication health status and metrics
        """
        try:
            # Check cache first
            if self._is_cached_status_valid():
                logger.debug("Using cached authentication health status")
                return self.cached_health_status
            
            # Get fresh status from monitor service
            health_status = await self.monitor_service.get_health_status()
            
            # Convert to health endpoint format
            health_response = await self._format_health_response(health_status)
            
            # Cache the result
            self.cached_health_status = health_response
            self.last_health_check = datetime.now(timezone.utc)
            
            logger.debug(f"Authentication health status: {health_status.status.value}")
            
            return health_response
            
        except Exception as e:
            logger.error(f"Error getting authentication health status: {e}")
            return self._create_error_health_response(str(e))

    async def get_authentication_metrics(self) -> Dict[str, Any]:
        """
        Get authentication metrics for health endpoints.
        
        Returns:
            Dictionary with authentication metrics
        """
        try:
            stats = self.monitor_service.get_authentication_stats()
            
            # Extract key metrics for health endpoints
            metrics = stats.get("metrics", {})
            
            return {
                "authentication_metrics": {
                    "total_attempts": metrics.get("total_attempts", 0),
                    "successful_authentications": metrics.get("successful_authentications", 0),
                    "failed_authentications": metrics.get("failed_authentications", 0),
                    "success_rate_percent": metrics.get("success_rate_percent", 100.0),
                    "average_response_time_ms": metrics.get("average_response_time_ms", 0.0),
                    "authentication_timeouts": metrics.get("authentication_timeouts", 0),
                    "last_success_timestamp": metrics.get("last_success_timestamp"),
                    "last_failure_timestamp": metrics.get("last_failure_timestamp")
                },
                "circuit_breaker": stats.get("circuit_breaker", {}),
                "monitoring_enabled": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting authentication metrics: {e}")
            return {
                "authentication_metrics": {
                    "error": str(e),
                    "monitoring_enabled": False
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def check_authentication_circuit_breaker(self) -> Dict[str, Any]:
        """
        Check authentication circuit breaker status for health endpoints.
        
        Returns:
            Dictionary with circuit breaker status
        """
        try:
            stats = self.monitor_service.get_authentication_stats()
            circuit_breaker = stats.get("circuit_breaker", {})
            
            return {
                "circuit_breaker_status": {
                    "enabled": circuit_breaker.get("enabled", True),
                    "is_open": circuit_breaker.get("is_open", False),
                    "threshold_percent": circuit_breaker.get("threshold_percent", 50.0),
                    "timeout_seconds": circuit_breaker.get("timeout_seconds", 60.0),
                    "last_trip": circuit_breaker.get("last_trip"),
                    "health_impact": "critical" if circuit_breaker.get("is_open") else "none"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking authentication circuit breaker: {e}")
            return {
                "circuit_breaker_status": {
                    "error": str(e),
                    "health_impact": "unknown"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def get_websocket_authentication_health(self) -> Dict[str, Any]:
        """
        Get WebSocket-specific authentication health status.
        
        Returns:
            Dictionary with WebSocket authentication health
        """
        try:
            health_status = await self.monitor_service.get_health_status()
            
            return {
                "websocket_authentication": {
                    "status": health_status.status.value,
                    "active_connections": health_status.active_connections,
                    "unhealthy_connections": health_status.unhealthy_connections,
                    "monitoring_enabled": health_status.monitoring_enabled,
                    "last_health_check": health_status.last_health_check.isoformat() if health_status.last_health_check else None,
                    "errors": health_status.errors,
                    "warnings": health_status.warnings,
                    "connection_health_ratio": self._calculate_connection_health_ratio(health_status)
                },
                "golden_path_impact": self._assess_golden_path_impact(health_status),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting WebSocket authentication health: {e}")
            return {
                "websocket_authentication": {
                    "status": "error",
                    "error": str(e),
                    "monitoring_enabled": False
                },
                "golden_path_impact": "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def is_authentication_healthy(self) -> bool:
        """
        Quick check if authentication is healthy.
        
        Returns:
            True if authentication is healthy, False otherwise
        """
        try:
            # Use cached status if available
            if self._is_cached_status_valid():
                return self.cached_health_status.get("overall_status") in ["healthy", "degraded"]
            
            # For synchronous check, we'll need to estimate health
            # This is a simplified check for cases where async call isn't possible
            stats = self.monitor_service.get_authentication_stats()
            metrics = stats.get("metrics", {})
            
            # Quick health assessment based on failure rate
            failure_rate = metrics.get("failure_rate_percent", 0.0)
            circuit_breaker_open = stats.get("circuit_breaker", {}).get("is_open", False)
            
            # Consider unhealthy if failure rate > 50% or circuit breaker is open
            is_healthy = failure_rate < 50.0 and not circuit_breaker_open
            
            logger.debug(f"Quick authentication health check: {is_healthy} (failure_rate: {failure_rate}%, cb_open: {circuit_breaker_open})")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Error checking authentication health: {e}")
            return False  # Fail safe - assume unhealthy if we can't check

    async def _format_health_response(self, health_status: AuthenticationHealthStatus) -> Dict[str, Any]:
        """
        Format authentication health status for health endpoint response.
        
        Args:
            health_status: AuthenticationHealthStatus from monitor service
            
        Returns:
            Formatted health response dictionary
        """
        try:
            # Map AuthenticationStatus to health endpoint status
            status_mapping = {
                AuthenticationStatus.HEALTHY: "healthy",
                AuthenticationStatus.DEGRADED: "degraded", 
                AuthenticationStatus.CRITICAL: "critical",
                AuthenticationStatus.UNKNOWN: "unknown"
            }
            
            overall_status = status_mapping.get(health_status.status, "unknown")
            
            # Create comprehensive health response
            health_response = {
                "overall_status": overall_status,
                "authentication_status": health_status.status.value,
                "metrics": health_status.metrics.to_dict(),
                "connections": {
                    "active_connections": health_status.active_connections,
                    "unhealthy_connections": health_status.unhealthy_connections,
                    "health_ratio": self._calculate_connection_health_ratio(health_status)
                },
                "monitoring": {
                    "enabled": health_status.monitoring_enabled,
                    "last_check": health_status.last_health_check.isoformat() if health_status.last_health_check else None
                },
                "issues": {
                    "errors": health_status.errors,
                    "warnings": health_status.warnings,
                    "error_count": len(health_status.errors),
                    "warning_count": len(health_status.warnings)
                },
                "golden_path_assessment": self._assess_golden_path_impact(health_status),
                "health_check_timestamp": datetime.now(timezone.utc).isoformat(),
                "ssot_compliant": True,
                "service_info": {
                    "name": "AuthHealthProvider",
                    "monitor_service": "AuthenticationMonitorService",
                    "integration_version": "1.0.0"
                }
            }
            
            return health_response
            
        except Exception as e:
            logger.error(f"Error formatting health response: {e}")
            return self._create_error_health_response(str(e))

    def _calculate_connection_health_ratio(self, health_status: AuthenticationHealthStatus) -> float:
        """
        Calculate connection health ratio.
        
        Args:
            health_status: AuthenticationHealthStatus with connection counts
            
        Returns:
            Health ratio as percentage (0.0 to 100.0)
        """
        try:
            total_connections = health_status.active_connections + health_status.unhealthy_connections
            if total_connections == 0:
                return 100.0  # No connections = healthy
            
            healthy_connections = health_status.active_connections
            ratio = (healthy_connections / total_connections) * 100.0
            
            return round(ratio, 2)
            
        except Exception as e:
            logger.error(f"Error calculating connection health ratio: {e}")
            return 0.0

    def _assess_golden_path_impact(self, health_status: AuthenticationHealthStatus) -> Dict[str, Any]:
        """
        Assess impact on golden path (login → AI responses).
        
        Args:
            health_status: AuthenticationHealthStatus to assess
            
        Returns:
            Dictionary with golden path impact assessment
        """
        try:
            # Assess impact based on authentication status and metrics
            status = health_status.status
            metrics = health_status.metrics
            
            # Determine impact level
            if status == AuthenticationStatus.CRITICAL:
                impact_level = "critical"
                impact_description = "Authentication failures blocking user access"
            elif status == AuthenticationStatus.DEGRADED:
                if metrics.failure_rate > 20.0:
                    impact_level = "major"
                    impact_description = "Elevated authentication failures affecting user experience"
                else:
                    impact_level = "minor"
                    impact_description = "Some authentication issues detected"
            elif status == AuthenticationStatus.HEALTHY:
                impact_level = "none"
                impact_description = "Authentication functioning normally"
            else:
                impact_level = "unknown"
                impact_description = "Unable to assess authentication status"
            
            # Check specific golden path blockers
            golden_path_blockers = []
            if metrics.failure_rate > 50.0:
                golden_path_blockers.append("High authentication failure rate")
            if metrics.authentication_timeouts > 10:
                golden_path_blockers.append("Authentication timeouts detected")
            if health_status.unhealthy_connections > 5:
                golden_path_blockers.append("Multiple unhealthy WebSocket connections")
            if len(health_status.errors) > 0:
                golden_path_blockers.append("Authentication errors present")
            
            return {
                "impact_level": impact_level,
                "impact_description": impact_description,
                "golden_path_blocked": len(golden_path_blockers) > 0,
                "blockers": golden_path_blockers,
                "user_authentication_available": status != AuthenticationStatus.CRITICAL,
                "chat_functionality_impacted": status == AuthenticationStatus.CRITICAL,
                "assessment_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error assessing golden path impact: {e}")
            return {
                "impact_level": "unknown",
                "impact_description": f"Assessment error: {str(e)}",
                "golden_path_blocked": True,
                "assessment_timestamp": datetime.now(timezone.utc).isoformat()
            }

    def _is_cached_status_valid(self) -> bool:
        """
        Check if cached health status is still valid.
        
        Returns:
            True if cached status is valid, False otherwise
        """
        if not self.last_health_check or not self.cached_health_status:
            return False
        
        # Check if cache has expired
        cache_age = (datetime.now(timezone.utc) - self.last_health_check).total_seconds()
        return cache_age < self.cache_duration_seconds

    def _create_error_health_response(self, error_message: str) -> Dict[str, Any]:
        """
        Create error health response when health check fails.
        
        Args:
            error_message: Error message to include in response
            
        Returns:
            Error health response dictionary
        """
        return {
            "overall_status": "error",
            "authentication_status": "unknown",
            "error": error_message,
            "metrics": {
                "error": "Unable to retrieve authentication metrics",
                "monitoring_available": False
            },
            "monitoring": {
                "enabled": False,
                "error": error_message
            },
            "golden_path_assessment": {
                "impact_level": "unknown",
                "impact_description": "Unable to assess due to monitoring error",
                "golden_path_blocked": True,
                "chat_functionality_impacted": True
            },
            "health_check_timestamp": datetime.now(timezone.utc).isoformat(),
            "ssot_compliant": True,
            "service_info": {
                "name": "AuthHealthProvider",
                "error": "Health check failed"
            }
        }


# Global SSOT instance for authentication health provider
_auth_health_provider: Optional[AuthHealthProvider] = None


def get_auth_health_provider(websocket_manager=None) -> AuthHealthProvider:
    """
    Get the global SSOT authentication health provider.
    
    Args:
        websocket_manager: Optional WebSocket manager for service initialization
        
    Returns:
        AuthHealthProvider instance (SSOT for auth health status)
    """
    global _auth_health_provider
    if _auth_health_provider is None:
        _auth_health_provider = AuthHealthProvider(websocket_manager)
        logger.info("SSOT ENFORCEMENT: AuthHealthProvider instance created")
    return _auth_health_provider


async def get_auth_health_for_endpoint(websocket_manager=None) -> Dict[str, Any]:
    """
    Convenience function to get authentication health status for health endpoints.
    
    Args:
        websocket_manager: Optional WebSocket manager for service initialization
        
    Returns:
        Dictionary with authentication health status
    """
    health_provider = get_auth_health_provider(websocket_manager)
    return await health_provider.get_authentication_health_status()


async def get_auth_metrics_for_endpoint(websocket_manager=None) -> Dict[str, Any]:
    """
    Convenience function to get authentication metrics for health endpoints.
    
    Args:
        websocket_manager: Optional WebSocket manager for service initialization
        
    Returns:
        Dictionary with authentication metrics
    """
    health_provider = get_auth_health_provider(websocket_manager)
    return await health_provider.get_authentication_metrics()


def is_auth_healthy_sync(websocket_manager=None) -> bool:
    """
    Synchronous check if authentication is healthy (for health endpoint quick checks).
    
    Args:
        websocket_manager: Optional WebSocket manager for service initialization
        
    Returns:
        True if authentication is healthy, False otherwise
    """
    health_provider = get_auth_health_provider(websocket_manager)
    return health_provider.is_authentication_healthy()


# SSOT ENFORCEMENT: Export only SSOT-compliant interfaces
__all__ = [
    "AuthHealthProvider",
    "get_auth_health_provider",
    "get_auth_health_for_endpoint",
    "get_auth_metrics_for_endpoint", 
    "is_auth_healthy_sync"
]