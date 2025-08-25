"""
Authentication Resilience API Routes

Provides endpoints for monitoring and managing authentication resilience:
- Health status and metrics
- Circuit breaker status
- Manual recovery controls
- Configuration management

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Operational visibility and control over auth resilience
- Value Impact: Enables proactive monitoring and manual intervention during outages
- Strategic Impact: Critical for enterprise operational requirements and SLA compliance
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from netra_backend.app.clients.auth_resilience_service import (
    get_auth_resilience_service,
    AuthResilienceMode,
    AuthOperationType,
    get_auth_resilience_health,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/auth-resilience", tags=["Authentication Resilience"])


@router.get("/health", summary="Get auth resilience health status")
async def get_resilience_health() -> Dict[str, Any]:
    """
    Get comprehensive health status of authentication resilience service.
    
    Returns:
        Detailed health information including current mode, metrics, and circuit breaker status
    """
    try:
        return await get_auth_resilience_health()
    except Exception as e:
        logger.error(f"Failed to get auth resilience health: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/status", summary="Get detailed status and metrics")
async def get_resilience_status() -> Dict[str, Any]:
    """
    Get detailed status information and metrics for authentication resilience.
    
    Returns:
        Comprehensive status including metrics, configuration, and operational data
    """
    try:
        service = get_auth_resilience_service()
        health = await service.get_health_status()
        metrics = await service.get_metrics()
        
        return {
            "service_info": {
                "name": "authentication_resilience_service",
                "version": "1.0.0",
                "uptime_seconds": health.get("uptime_seconds", 0),
            },
            "health": health,
            "metrics": {
                "total_auth_attempts": metrics.total_auth_attempts,
                "successful_auth_operations": metrics.successful_auth_operations,
                "failed_auth_operations": metrics.failed_auth_operations,
                "success_rate": (
                    metrics.successful_auth_operations / max(1, metrics.total_auth_attempts)
                ),
                "cache_hits": metrics.cache_hits,
                "cache_misses": metrics.cache_misses,
                "cache_hit_rate": (
                    metrics.cache_hits / max(1, metrics.cache_hits + metrics.cache_misses)
                ),
                "fallback_activations": metrics.fallback_activations,
                "emergency_bypasses": metrics.emergency_bypasses,
                "mode_changes": metrics.mode_changes,
                "consecutive_failures": metrics.consecutive_failures,
                "recovery_attempts": metrics.recovery_attempts,
                "successful_recoveries": metrics.successful_recoveries,
            },
            "current_state": {
                "mode": metrics.current_mode.value,
                "circuit_breaker_state": metrics.circuit_breaker_state,
                "auth_service_health": metrics.auth_service_health,
                "last_mode_change": metrics.last_mode_change.isoformat() if metrics.last_mode_change else None,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get auth resilience status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/circuit-breaker", summary="Get circuit breaker status")
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """
    Get detailed circuit breaker status for authentication service.
    
    Returns:
        Circuit breaker state, metrics, and configuration
    """
    try:
        service = get_auth_resilience_service()
        circuit_status = service.circuit_breaker.get_status()
        
        return {
            "circuit_breaker": {
                "name": circuit_status["name"],
                "state": circuit_status["state"],
                "is_healthy": circuit_status["is_healthy"],
                "last_state_change": circuit_status["last_state_change"],
                "sliding_window_size": circuit_status["sliding_window_size"],
            },
            "metrics": circuit_status["metrics"],
            "config": circuit_status["config"],
            "health": circuit_status["health"],
        }
    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail=f"Circuit breaker status failed: {str(e)}")


@router.post("/recovery/manual", summary="Manually trigger recovery attempt")
async def trigger_manual_recovery() -> Dict[str, Any]:
    """
    Manually trigger a recovery attempt to normal mode.
    
    This is useful for testing or when operators want to force recovery
    after resolving auth service issues.
    
    Returns:
        Result of the recovery attempt
    """
    try:
        service = get_auth_resilience_service()
        
        # Get current status
        current_mode = service.current_mode
        
        if current_mode == AuthResilienceMode.NORMAL:
            return {
                "success": True,
                "message": "Already in normal mode",
                "previous_mode": current_mode.value,
                "current_mode": current_mode.value,
            }
        
        # Attempt recovery
        await service._attempt_mode_recovery()
        
        return {
            "success": True,
            "message": "Recovery attempt triggered",
            "previous_mode": current_mode.value,
            "current_mode": service.current_mode.value,
            "note": "Recovery will complete automatically if auth service is healthy",
        }
    except Exception as e:
        logger.error(f"Failed to trigger manual recovery: {e}")
        raise HTTPException(status_code=500, detail=f"Manual recovery failed: {str(e)}")


@router.post("/mode/force", summary="Force specific resilience mode")
async def force_resilience_mode(
    mode: str = Query(..., description="Target mode: normal, cached_fallback, degraded, emergency, recovery"),
    confirm: bool = Query(False, description="Confirm the mode change (required for emergency mode)")
) -> Dict[str, Any]:
    """
    Force the resilience service into a specific mode.
    
    WARNING: This is for testing and emergency situations only.
    Forcing emergency mode requires confirmation.
    
    Args:
        mode: Target resilience mode
        confirm: Required confirmation for dangerous modes
        
    Returns:
        Result of the mode change
    """
    try:
        # Validate mode
        try:
            target_mode = AuthResilienceMode(mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode '{mode}'. Valid modes: {[m.value for m in AuthResilienceMode]}"
            )
        
        # Check confirmation for dangerous modes
        if target_mode == AuthResilienceMode.EMERGENCY and not confirm:
            raise HTTPException(
                status_code=400,
                detail="Emergency mode requires confirmation. Set confirm=true"
            )
        
        service = get_auth_resilience_service()
        previous_mode = service.current_mode
        
        # Force mode change
        await service.force_mode(target_mode)
        
        logger.warning(f"Manually forced auth resilience mode: {previous_mode.value} -> {target_mode.value}")
        
        return {
            "success": True,
            "message": f"Forced mode change to {target_mode.value}",
            "previous_mode": previous_mode.value,
            "current_mode": target_mode.value,
            "warning": "Manual mode changes should only be used for testing or emergencies",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force resilience mode: {e}")
        raise HTTPException(status_code=500, detail=f"Mode change failed: {str(e)}")


@router.post("/circuit-breaker/reset", summary="Reset circuit breaker")
async def reset_circuit_breaker() -> Dict[str, Any]:
    """
    Reset the authentication service circuit breaker to closed state.
    
    This can be useful for testing or when operators want to force
    the circuit breaker closed after resolving issues.
    
    Returns:
        Result of the circuit breaker reset
    """
    try:
        service = get_auth_resilience_service()
        previous_state = service.circuit_breaker.state.value
        
        # Reset circuit breaker
        await service.circuit_breaker.reset()
        
        logger.warning("Auth service circuit breaker manually reset")
        
        return {
            "success": True,
            "message": "Circuit breaker reset to closed state",
            "previous_state": previous_state,
            "current_state": service.circuit_breaker.state.value,
        }
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker: {e}")
        raise HTTPException(status_code=500, detail=f"Circuit breaker reset failed: {str(e)}")


@router.post("/circuit-breaker/force-open", summary="Force circuit breaker open")
async def force_circuit_breaker_open(
    confirm: bool = Query(False, description="Confirm forcing circuit breaker open")
) -> Dict[str, Any]:
    """
    Force the authentication service circuit breaker to open state.
    
    WARNING: This will cause all auth service calls to fail immediately.
    Only use for testing or emergency situations.
    
    Args:
        confirm: Required confirmation
        
    Returns:
        Result of forcing circuit breaker open
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Forcing circuit breaker open requires confirmation. Set confirm=true"
            )
        
        service = get_auth_resilience_service()
        previous_state = service.circuit_breaker.state.value
        
        # Force circuit breaker open
        await service.circuit_breaker.force_open()
        
        logger.warning("Auth service circuit breaker manually forced open")
        
        return {
            "success": True,
            "message": "Circuit breaker forced to open state",
            "previous_state": previous_state,
            "current_state": service.circuit_breaker.state.value,
            "warning": "Circuit breaker will prevent all auth service calls until recovery",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force circuit breaker open: {e}")
        raise HTTPException(status_code=500, detail=f"Force open failed: {str(e)}")


@router.post("/metrics/reset", summary="Reset resilience metrics")
async def reset_metrics() -> Dict[str, Any]:
    """
    Reset all resilience metrics to zero.
    
    This is useful for testing or when starting fresh monitoring periods.
    
    Returns:
        Confirmation of metrics reset
    """
    try:
        service = get_auth_resilience_service()
        service.reset_metrics()
        
        logger.info("Auth resilience metrics reset")
        
        return {
            "success": True,
            "message": "All resilience metrics reset to zero",
            "timestamp": service.metrics.last_mode_change.isoformat() if service.metrics.last_mode_change else None,
        }
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics reset failed: {str(e)}")


@router.get("/test/validate-token", summary="Test token validation with resilience")
async def test_token_validation(
    token: str = Query(..., description="Token to validate"),
    operation_type: str = Query("token_validation", description="Type of operation to simulate"),
    force_failure: bool = Query(False, description="Force validation failure for testing")
) -> Dict[str, Any]:
    """
    Test token validation through the resilience service.
    
    This endpoint is useful for testing resilience mechanisms without
    affecting production traffic.
    
    Args:
        token: Token to validate
        operation_type: Type of operation to simulate
        force_failure: Force failure for testing fallback mechanisms
        
    Returns:
        Validation result with resilience information
    """
    try:
        # Validate operation type
        try:
            op_type = AuthOperationType(operation_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operation type '{operation_type}'. Valid types: {[t.value for t in AuthOperationType]}"
            )
        
        if force_failure:
            # Return a simulated failure for testing
            return {
                "success": False,
                "valid": False,
                "error": "Simulated failure for testing",
                "resilience_mode": "normal",
                "fallback_used": False,
                "test_mode": True,
            }
        
        service = get_auth_resilience_service()
        result = await service.validate_token_with_resilience(token, op_type)
        result["test_mode"] = True
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test token validation: {e}")
        raise HTTPException(status_code=500, detail=f"Token validation test failed: {str(e)}")


@router.get("/config", summary="Get current resilience configuration")
async def get_resilience_config() -> Dict[str, Any]:
    """
    Get the current resilience service configuration.
    
    Returns:
        Current configuration settings
    """
    try:
        service = get_auth_resilience_service()
        config = service.config
        
        return {
            "circuit_breaker": {
                "failure_threshold": config.circuit_breaker_failure_threshold,
                "recovery_timeout": config.circuit_breaker_recovery_timeout,
                "half_open_max_calls": config.circuit_breaker_half_open_max_calls,
            },
            "cache": {
                "ttl_seconds": config.cache_ttl_seconds,
                "fallback_ttl_seconds": config.cache_fallback_ttl_seconds,
                "max_cached_tokens": config.max_cached_tokens,
            },
            "retry": {
                "max_attempts": config.max_retry_attempts,
                "base_delay": config.retry_base_delay,
                "max_delay": config.retry_max_delay,
                "exponential_base": config.retry_exponential_base,
            },
            "degraded_mode": {
                "timeout": config.degraded_mode_timeout,
                "allow_read_only": config.allow_read_only_operations,
                "read_only_endpoints": list(config.read_only_endpoints),
            },
            "emergency_bypass": {
                "enabled": config.emergency_bypass_enabled,
                "endpoints": list(config.emergency_bypass_endpoints),
                "timeout": config.emergency_bypass_timeout,
            },
            "recovery": {
                "validation_count": config.recovery_validation_count,
                "validation_window": config.recovery_validation_window,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get resilience config: {e}")
        raise HTTPException(status_code=500, detail=f"Config retrieval failed: {str(e)}")