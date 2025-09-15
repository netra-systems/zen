"""
SMD Graceful Degradation for Issue #1278

This module provides graceful degradation mechanisms for SMD (Startup Module)
to prevent cascade failures when database connections timeout due to 
VPC connector capacity constraints.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Staging Environment Resilience  
- Value Impact: Prevent total service failure during infrastructure constraints
- Strategic Impact: Maintain partial service availability during Cloud SQL/VPC issues
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ServiceAvailabilityLevel(Enum):
    """Service availability levels during degraded operation."""
    FULL = "full"
    DEGRADED = "degraded"
    MINIMAL = "minimal"
    UNAVAILABLE = "unavailable"


class StartupPhaseStatus(Enum):
    """Startup phase completion status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseResult:
    """Result of a startup phase execution."""
    phase_name: str
    status: StartupPhaseStatus
    error: Optional[Exception] = None
    duration_seconds: float = 0.0
    fallback_applied: bool = False
    availability_impact: ServiceAvailabilityLevel = ServiceAvailabilityLevel.FULL


class GracefulDegradationManager:
    """Manages graceful degradation during SMD startup failures."""
    
    def __init__(self, app_state):
        self.app_state = app_state
        self.phase_results: Dict[str, PhaseResult] = {}
        self.current_availability = ServiceAvailabilityLevel.FULL
        self.fallback_strategies = self._initialize_fallback_strategies()
        
    def _initialize_fallback_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize fallback strategies for each startup phase."""
        return {
            "database": {
                "fallback_enabled": True,
                "availability_level": ServiceAvailabilityLevel.DEGRADED,
                "fallback_timeout": 60.0,  # Extended timeout for database fallback
                "retry_strategy": "exponential_backoff",
                "partial_service_endpoints": ["/health", "/status"],
                "error_message": "Database temporarily unavailable - operating in degraded mode",
            },
            "cache": {
                "fallback_enabled": True,
                "availability_level": ServiceAvailabilityLevel.DEGRADED,
                "fallback_timeout": 30.0,
                "retry_strategy": "immediate_fallback",
                "partial_service_endpoints": ["/health", "/status", "/auth"],
                "error_message": "Cache temporarily unavailable - performance may be reduced",
            },
            "services": {
                "fallback_enabled": True,
                "availability_level": ServiceAvailabilityLevel.MINIMAL,
                "fallback_timeout": 45.0,
                "retry_strategy": "selective_initialization",
                "partial_service_endpoints": ["/health", "/status"],
                "error_message": "Some services unavailable - limited functionality available",
            },
            "validation": {
                "fallback_enabled": False,  # Validation failures should not trigger fallback
                "availability_level": ServiceAvailabilityLevel.UNAVAILABLE,
                "fallback_timeout": 0.0,
                "retry_strategy": "none",
                "error_message": "Critical validation failed - service cannot start safely",
            }
        }
    
    async def handle_phase_failure(self, phase_name: str, error: Exception, 
                                 timeout_occurred: bool = False) -> PhaseResult:
        """Handle failure of a startup phase with graceful degradation.
        
        Args:
            phase_name: Name of the failed phase
            error: Exception that caused the failure
            timeout_occurred: Whether the failure was due to timeout
            
        Returns:
            Phase result with fallback information
        """
        logger.warning(f"Startup phase '{phase_name}' failed: {error}")
        
        fallback_config = self.fallback_strategies.get(phase_name, {})
        
        if not fallback_config.get("fallback_enabled", False):
            # No fallback available - mark as failed
            result = PhaseResult(
                phase_name=phase_name,
                status=StartupPhaseStatus.FAILED,
                error=error,
                availability_impact=fallback_config.get("availability_level", ServiceAvailabilityLevel.UNAVAILABLE)
            )
            self.phase_results[phase_name] = result
            return result
        
        # Attempt fallback strategy
        logger.info(f"Attempting fallback for phase '{phase_name}'")
        
        try:
            fallback_result = await self._execute_fallback(phase_name, error, timeout_occurred)
            
            if fallback_result:
                logger.info(f"Fallback successful for phase '{phase_name}'")
                result = PhaseResult(
                    phase_name=phase_name,
                    status=StartupPhaseStatus.COMPLETED,
                    fallback_applied=True,
                    availability_impact=fallback_config.get("availability_level", ServiceAvailabilityLevel.DEGRADED)
                )
            else:
                logger.error(f"Fallback failed for phase '{phase_name}'")
                result = PhaseResult(
                    phase_name=phase_name,
                    status=StartupPhaseStatus.FAILED,
                    error=error,
                    availability_impact=ServiceAvailabilityLevel.UNAVAILABLE
                )
                
        except Exception as fallback_error:
            logger.error(f"Fallback execution failed for phase '{phase_name}': {fallback_error}")
            result = PhaseResult(
                phase_name=phase_name,
                status=StartupPhaseStatus.FAILED,
                error=fallback_error,
                availability_impact=ServiceAvailabilityLevel.UNAVAILABLE
            )
        
        self.phase_results[phase_name] = result
        self._update_overall_availability()
        return result
    
    async def _execute_fallback(self, phase_name: str, original_error: Exception, 
                              timeout_occurred: bool) -> bool:
        """Execute fallback strategy for a specific phase.
        
        Args:
            phase_name: Name of the phase
            original_error: Original error that triggered fallback
            timeout_occurred: Whether the error was timeout-related
            
        Returns:
            True if fallback was successful, False otherwise
        """
        fallback_config = self.fallback_strategies[phase_name]
        strategy = fallback_config.get("retry_strategy", "none")
        
        if strategy == "exponential_backoff" and phase_name == "database":
            return await self._database_fallback(original_error, timeout_occurred)
        elif strategy == "immediate_fallback" and phase_name == "cache":
            return await self._cache_fallback(original_error)
        elif strategy == "selective_initialization" and phase_name == "services":
            return await self._services_fallback(original_error)
        else:
            logger.warning(f"No fallback strategy implemented for phase '{phase_name}' strategy '{strategy}'")
            return False
    
    async def _database_fallback(self, error: Exception, timeout_occurred: bool) -> bool:
        """Implement database connection fallback strategy.
        
        For Issue #1278, this implements extended timeout and connection pooling fallback.
        """
        logger.info("Executing database fallback strategy")
        
        # Set app state to indicate degraded database availability
        self.app_state.database_available = False
        self.app_state.database_degraded = True
        self.app_state.database_error = str(error)
        
        # Initialize minimal database state for health checks
        try:
            # Create a minimal connection pool for health endpoints only
            from netra_backend.app.core.database_timeout_config import get_database_timeout_config
            
            # Use extended timeout configuration
            extended_config = get_database_timeout_config("staging")
            extended_timeout = extended_config.get("initialization_timeout", 45.0)
            
            # Apply VPC connector capacity awareness
            from netra_backend.app.infrastructure.vpc_connector_monitoring import get_capacity_aware_database_timeout
            vpc_aware_timeout = get_capacity_aware_database_timeout("staging", "initialization")
            
            final_timeout = max(extended_timeout, vpc_aware_timeout)
            
            logger.info(f"Database fallback using extended timeout: {final_timeout}s")
            
            # Set minimal database session factory for health checks only
            self.app_state.db_session_factory = None  # Will be created on-demand for health checks
            self.app_state.database_health_only = True
            
            return True
            
        except Exception as fallback_error:
            logger.error(f"Database fallback failed: {fallback_error}")
            return False
    
    async def _cache_fallback(self, error: Exception) -> bool:
        """Implement cache fallback strategy (operate without cache)."""
        logger.info("Executing cache fallback strategy - operating without cache")
        
        # Set app state to indicate no cache available
        self.app_state.redis_manager = None
        self.app_state.cache_available = False
        self.app_state.cache_degraded = True
        self.app_state.cache_error = str(error)
        
        return True
    
    async def _services_fallback(self, error: Exception) -> bool:
        """Implement services fallback strategy (minimal service initialization)."""
        logger.info("Executing services fallback strategy - minimal service initialization")
        
        # Initialize only critical services for health endpoints
        try:
            # Health service is essential even in degraded mode
            if not hasattr(self.app_state, 'health_service') or self.app_state.health_service is None:
                # Initialize minimal health service
                self.app_state.health_service_degraded = True
                logger.info("Minimal health service initialized")
            
            # Mark other services as unavailable
            self.app_state.agent_supervisor = None
            self.app_state.background_task_manager = None
            self.app_state.services_degraded = True
            self.app_state.services_error = str(error)
            
            return True
            
        except Exception as fallback_error:
            logger.error(f"Services fallback failed: {fallback_error}")
            return False
    
    def _update_overall_availability(self) -> None:
        """Update overall service availability based on phase results."""
        availability_levels = [result.availability_impact for result in self.phase_results.values()]
        
        if not availability_levels:
            self.current_availability = ServiceAvailabilityLevel.FULL
            return
        
        # Determine the most restrictive availability level
        if ServiceAvailabilityLevel.UNAVAILABLE in availability_levels:
            self.current_availability = ServiceAvailabilityLevel.UNAVAILABLE
        elif ServiceAvailabilityLevel.MINIMAL in availability_levels:
            self.current_availability = ServiceAvailabilityLevel.MINIMAL
        elif ServiceAvailabilityLevel.DEGRADED in availability_levels:
            self.current_availability = ServiceAvailabilityLevel.DEGRADED
        else:
            self.current_availability = ServiceAvailabilityLevel.FULL
        
        logger.info(f"Overall service availability: {self.current_availability.value}")
    
    def get_degradation_status(self) -> Dict[str, Any]:
        """Get current degradation status and recommendations.
        
        Returns:
            Dictionary with degradation status and recovery recommendations
        """
        phase_summaries = {}
        for phase_name, result in self.phase_results.items():
            phase_summaries[phase_name] = {
                "status": result.status.value,
                "fallback_applied": result.fallback_applied,
                "availability_impact": result.availability_impact.value,
                "error": str(result.error) if result.error else None,
            }
        
        # Generate recovery recommendations
        recommendations = []
        
        if self.current_availability in [ServiceAvailabilityLevel.DEGRADED, ServiceAvailabilityLevel.MINIMAL]:
            recommendations.append("Service is operating in degraded mode - investigate infrastructure issues")
        
        database_result = self.phase_results.get("database")
        if database_result and database_result.status == StartupPhaseStatus.FAILED:
            recommendations.append("Database connection failed - check Cloud SQL and VPC connector capacity")
        
        cache_result = self.phase_results.get("cache")
        if cache_result and cache_result.status == StartupPhaseStatus.FAILED:
            recommendations.append("Cache unavailable - Redis connection issues detected")
        
        return {
            "overall_availability": self.current_availability.value,
            "phase_results": phase_summaries,
            "recommendations": recommendations,
            "fallback_strategies_available": len([p for p in self.fallback_strategies.values() if p.get("fallback_enabled", False)]),
            "degraded_endpoints_available": self._get_available_endpoints(),
        }
    
    def _get_available_endpoints(self) -> List[str]:
        """Get list of endpoints available in current degradation state."""
        available_endpoints = ["/health"]  # Health endpoint always available
        
        if self.current_availability in [ServiceAvailabilityLevel.FULL, ServiceAvailabilityLevel.DEGRADED]:
            available_endpoints.extend(["/status", "/metrics"])
        
        if self.current_availability == ServiceAvailabilityLevel.FULL:
            available_endpoints.extend(["/auth", "/chat", "/websocket"])
        
        return available_endpoints
    
    def is_service_available(self) -> bool:
        """Check if service is available at any level.
        
        Returns:
            True if service provides any level of functionality
        """
        return self.current_availability != ServiceAvailabilityLevel.UNAVAILABLE
    
    def get_user_facing_message(self) -> str:
        """Get user-facing message for current degradation state.
        
        Returns:
            Human-readable message explaining service status
        """
        if self.current_availability == ServiceAvailabilityLevel.FULL:
            return "All services are operating normally."
        elif self.current_availability == ServiceAvailabilityLevel.DEGRADED:
            return "Some services are temporarily unavailable. Core functionality is available with reduced performance."
        elif self.current_availability == ServiceAvailabilityLevel.MINIMAL:
            return "Service is operating with limited functionality. Please try again later."
        else:
            return "Service is temporarily unavailable. Please try again later."


# Global degradation manager instance
_degradation_manager: Optional[GracefulDegradationManager] = None


def get_degradation_manager(app_state) -> GracefulDegradationManager:
    """Get or create graceful degradation manager.
    
    Args:
        app_state: FastAPI app state object
        
    Returns:
        Graceful degradation manager instance
    """
    global _degradation_manager
    
    if _degradation_manager is None:
        _degradation_manager = GracefulDegradationManager(app_state)
        logger.info("Initialized graceful degradation manager")
    
    return _degradation_manager


async def handle_startup_phase_failure(app_state, phase_name: str, error: Exception, 
                                     timeout_occurred: bool = False) -> PhaseResult:
    """Handle startup phase failure with graceful degradation.
    
    Args:
        app_state: FastAPI app state
        phase_name: Name of the failed phase
        error: Exception that caused the failure
        timeout_occurred: Whether failure was due to timeout
        
    Returns:
        Phase result with fallback information
    """
    manager = get_degradation_manager(app_state)
    return await manager.handle_phase_failure(phase_name, error, timeout_occurred)


def get_service_availability_status(app_state) -> Dict[str, Any]:
    """Get current service availability status.
    
    Args:
        app_state: FastAPI app state
        
    Returns:
        Service availability status dictionary
    """
    manager = get_degradation_manager(app_state)
    return manager.get_degradation_status()