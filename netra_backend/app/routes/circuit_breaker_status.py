"""
Circuit Breaker Status API for monitoring system resilience.

Provides visibility into circuit breaker states and statistics for:
- Auth service connections
- Database connections
- External service integrations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Operational Visibility - Monitor service health and resilience
- Value Impact: Enables proactive incident response and troubleshooting
- Strategic Impact: Production reliability and observability
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from netra_backend.app.clients.circuit_breaker import get_all_circuit_breaker_stats

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monitoring"])


@router.get("/api/circuit-breakers/status")
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """
    Get status of all circuit breakers in the system.
    
    Returns detailed statistics including:
    - Current state (CLOSED, OPEN, HALF_OPEN)
    - Failure rates and counts
    - Recent state transitions
    - Configuration parameters
    """
    try:
        stats = await get_all_circuit_breaker_stats()
        
        # Add summary information
        summary = {
            "total_breakers": len(stats),
            "open_breakers": sum(1 for b in stats.values() if b["state"] == "open"),
            "half_open_breakers": sum(1 for b in stats.values() if b["state"] == "half_open"),
            "closed_breakers": sum(1 for b in stats.values() if b["state"] == "closed"),
        }
        
        return {
            "status": "ok",
            "summary": summary,
            "circuit_breakers": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve circuit breaker status: {str(e)}"
        )


@router.get("/api/circuit-breakers/{breaker_name}")
async def get_specific_circuit_breaker(breaker_name: str) -> Dict[str, Any]:
    """
    Get status of a specific circuit breaker.
    
    Args:
        breaker_name: Name of the circuit breaker (e.g., "auth_service")
    
    Returns:
        Detailed statistics for the specified circuit breaker
    """
    try:
        all_stats = await get_all_circuit_breaker_stats()
        
        if breaker_name not in all_stats:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker '{breaker_name}' not found"
            )
        
        return all_stats[breaker_name]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get circuit breaker {breaker_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve circuit breaker status: {str(e)}"
        )


@router.post("/api/circuit-breakers/{breaker_name}/reset")
async def reset_circuit_breaker(breaker_name: str) -> Dict[str, str]:
    """
    Manually reset a circuit breaker to CLOSED state.
    
    Use this endpoint to force a circuit breaker to close after
    confirming the underlying issue has been resolved.
    
    Args:
        breaker_name: Name of the circuit breaker to reset
    
    Returns:
        Success message
    """
    try:
        from netra_backend.app.clients.circuit_breaker import _circuit_breakers
        
        if breaker_name not in _circuit_breakers:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker '{breaker_name}' not found"
            )
        
        breaker = _circuit_breakers[breaker_name]
        await breaker.reset()
        
        logger.info(f"Circuit breaker '{breaker_name}' manually reset by API call")
        
        return {
            "status": "success",
            "message": f"Circuit breaker '{breaker_name}' has been reset to CLOSED state"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker {breaker_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset circuit breaker: {str(e)}"
        )