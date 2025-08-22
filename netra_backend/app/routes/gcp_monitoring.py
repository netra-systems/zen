"""GCP Error Monitoring API Endpoints

Business Value Justification (BVJ):
1. Segment: Mid & Enterprise
2. Business Goal: Reduce MTTR by 40% through automated error detection
3. Value Impact: Saves 5-10 hours/week of engineering time, prevents customer-facing issues
4. Revenue Impact: +$15K MRR from enhanced reliability features

CRITICAL ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (enforced)
- Maximum function size: 8 lines (enforced)
- Strong typing with Pydantic models
- Modular design with single responsibility
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from netra_backend.app.auth_integration.auth import get_current_user, require_permission
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.monitoring_schemas import (
    ErrorDetailResponse,
    ErrorQuery,
    ErrorResolution,
    ErrorResponse,
    ErrorSeverity,
    ErrorStatus,
)

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["gcp-error-monitoring"])


async def _get_gcp_error_service():
    """Get GCP Error Service instance with dependency injection."""
    from netra_backend.app.config import settings
    from netra_backend.app.schemas.monitoring_schemas import (
        GCPCredentialsConfig,
        GCPErrorServiceConfig,
    )
    from netra_backend.app.services.monitoring.gcp_error_service import GCPErrorService
    project_id = settings.google_cloud.project_id
    credentials = GCPCredentialsConfig(project_id=project_id)
    config = GCPErrorServiceConfig(project_id=project_id, credentials=credentials)
    service = GCPErrorService(config)
    await service.initialize()
    return service


def _log_gcp_errors_request(current_user: Dict[str, Any], query: ErrorQuery) -> None:
    """Log GCP errors list request."""
    logger.info(f"GCP errors requested by user: {current_user.get('user_id', 'unknown')}, "
                f"status: {query.status}, service: {query.service}")


def _build_error_query(status: str, limit: int, service: Optional[str], 
                      severity: Optional[str], time_range: str) -> ErrorQuery:
    """Build error query from parameters."""
    return ErrorQuery(status=ErrorStatus(status), limit=limit, service=service,
                     severity=ErrorSeverity(severity) if severity else None, time_range=time_range)


def _handle_gcp_errors_error(e: Exception) -> None:
    """Handle GCP errors endpoint errors."""
    logger.error(f"Error in GCP errors endpoint: {e}")
    if isinstance(e, NetraException):
        raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=500, detail=f"Failed to fetch GCP errors: {str(e)}")


@router.get("/errors", response_model=ErrorResponse)
async def get_gcp_errors(
    status: str = Query(default="OPEN", description="Error status filter"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum errors to return"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    time_range: str = Query(default="24h", description="Time range for errors"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ErrorResponse:
    """Retrieve open errors from GCP Error Reporting."""
    try:
        query = _build_error_query(status, limit, service, severity, time_range)
        _log_gcp_errors_request(current_user, query)
        gcp_service = await _get_gcp_error_service()
        return await gcp_service.fetch_errors(query)
    except Exception as e:
        _handle_gcp_errors_error(e)


def _log_gcp_error_details_request(current_user: Dict[str, Any], error_id: str) -> None:
    """Log GCP error details request."""
    logger.info(f"GCP error details requested by user: {current_user.get('user_id', 'unknown')}, "
                f"error_id: {error_id}")


def _handle_gcp_error_details_error(e: Exception, error_id: str) -> None:
    """Handle GCP error details endpoint errors."""
    logger.error(f"Error in GCP error details endpoint for {error_id}: {e}")
    if isinstance(e, NetraException):
        raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=500, detail=f"Failed to get error details: {str(e)}")


@router.get("/errors/{error_id}", response_model=ErrorDetailResponse)
async def get_gcp_error_details(
    error_id: str = Path(..., description="Error ID to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ErrorDetailResponse:
    """Get detailed information for a specific error."""
    try:
        _log_gcp_error_details_request(current_user, error_id)
        gcp_service = await _get_gcp_error_service()
        return await gcp_service.get_error_details(error_id)
    except Exception as e:
        _handle_gcp_error_details_error(e, error_id)


def _log_gcp_error_resolve_request(current_user: Dict[str, Any], error_id: str) -> None:
    """Log GCP error resolution request."""
    logger.info(f"GCP error resolution requested by user: {current_user.get('user_id', 'unknown')}, "
                f"error_id: {error_id}")


def _build_error_resolution(resolution_note: str, user_id: str) -> ErrorResolution:
    """Build error resolution object."""
    return ErrorResolution(resolution_note=resolution_note, resolved_by=user_id)


def _handle_gcp_error_resolve_error(e: Exception, error_id: str) -> None:
    """Handle GCP error resolution endpoint errors."""
    logger.error(f"Error in GCP error resolution endpoint for {error_id}: {e}")
    if isinstance(e, NetraException):
        raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=500, detail=f"Failed to resolve error: {str(e)}")


def _build_resolution_response(success: bool, error_id: str) -> Dict[str, Any]:
    """Build error resolution response."""
    return {"success": success, "error_id": error_id, "timestamp": datetime.now().isoformat(),
            "message": "Error marked as resolved" if success else "Failed to resolve error"}


class ErrorResolutionRequest(BaseModel):
    """Request model for error resolution."""
    resolution_note: str = Field(..., description="Resolution description")


@router.post("/errors/{error_id}/resolve")
async def resolve_gcp_error(
    error_id: str = Path(..., description="Error ID to resolve"),
    resolution: ErrorResolutionRequest = ...,
    current_user: Dict[str, Any] = Depends(require_permission("error_resolution"))
) -> Dict[str, Any]:
    """Mark error as resolved with resolution note."""
    try:
        _log_gcp_error_resolve_request(current_user, error_id)
        user_id = current_user.get('user_id', 'unknown')
        error_resolution = _build_error_resolution(resolution.resolution_note, user_id)
        gcp_service = await _get_gcp_error_service()
        success = await gcp_service.update_error_status(error_id, error_resolution)
        return _build_resolution_response(success, error_id)
    except Exception as e:
        _handle_gcp_error_resolve_error(e, error_id)