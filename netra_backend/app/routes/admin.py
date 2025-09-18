from typing import Any, Dict, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from netra_backend.app import schemas
from netra_backend.app.auth_integration.auth import (
    ActiveUserDep,
    AdminDep,
    DeveloperDep,
    require_permission,
    auth_client
)
from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.schemas.config import AppConfig
from netra_backend.app.services.permission_service import PermissionService
from netra_backend.app.services.audit_service import AuditService
from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.authentication_monitor_service import (
    get_authentication_monitor_service,
    get_auth_health_status,
    AuthenticationHealthStatus
)

logger = central_logger.get_logger(__name__)
audit_service = AuditService()

router = APIRouter()

async def verify_admin_role_from_jwt(token: str) -> bool:
    """
    SECURITY: Verify admin role directly from JWT claims - server-side validation only.
    Never trust client-provided admin flags.
    """
    try:
        # Validate token and extract claims from JWT directly
        validation_result = await auth_client.validate_token_jwt(token)
        
        if not validation_result or not validation_result.get("valid"):
            logger.warning("Admin role verification failed: Invalid token")
            return False
        
        # Extract role/permissions from JWT claims
        jwt_permissions = validation_result.get("permissions", [])
        jwt_role = validation_result.get("role", "")
        
        # Check for admin permissions in JWT
        is_admin = (
            jwt_role in ["admin", "super_admin"] or
            "admin" in jwt_permissions or
            "system:*" in jwt_permissions or
            "admin:*" in jwt_permissions
        )
        
        if is_admin:
            logger.info(f"Admin access granted for user {validation_result.get('user_id', 'unknown')[:8]}...")
        else:
            logger.warning(f"Admin access denied for user {validation_result.get('user_id', 'unknown')[:8]}... - insufficient permissions")
        
        return is_admin
        
    except Exception as e:
        logger.error(f"Admin role verification error: {e}")
        return False


def verify_admin_role(user: Dict[str, Any]) -> bool:
    """
    DEPRECATED: Legacy function - DO NOT USE for security decisions.
    This function is maintained for backward compatibility only.
    Use verify_admin_role_from_jwt() for actual security validation.
    """
    logger.warning("verify_admin_role() called - this is deprecated for security purposes")
    return user.get("role") == "admin"

async def get_all_users() -> List[Dict[str, Any]]:
    """Get all users from the system."""
    from netra_backend.app.core.configuration.services import user_service
    return await user_service.get_all_users()

async def update_user_role(user_id: str, role: str) -> Dict[str, Any]:
    """Update user role in the system."""
    from netra_backend.app.core.configuration.services import user_service
    return await user_service.update_user_role(user_id, role)

async def get_audit_logs(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get recent audit logs with pagination."""
    return await audit_service.get_logs(limit, offset)

async def log_admin_operation(action: str, user_id: str, details: Dict[str, Any], ip_address: str = None) -> None:
    """
    SECURITY: Log all admin operations for audit trail.
    Critical for security compliance and breach investigation.
    """
    try:
        audit_details = {
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip_address": ip_address,
            "user_agent": details.get("user_agent"),
            **details
        }
        
        await audit_service.log_action(f"ADMIN_{action.upper()}", user_id, audit_details)
        logger.info(f"Admin operation logged: {action} by user {user_id[:8]}...")
        
    except Exception as e:
        logger.error(f"Failed to log admin operation: {e}")
        # Continue execution - don't fail operations due to audit logging issues
        # But ensure this is highly visible in logs
        logger.critical(f"AUDIT LOGGING FAILURE: Admin operation {action} by {user_id} was NOT logged!")

async def require_admin_with_jwt_validation(request: Request, current_user: schemas.UserBase = Depends(ActiveUserDep)) -> schemas.UserBase:
    """
    SECURITY: Enhanced admin requirement with JWT validation.
    Extracts token and validates admin role from JWT claims directly.
    """
    # Extract JWT token from request
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.error("Admin access denied: No Bearer token found")
        raise HTTPException(
            status_code=401,
            detail="Authentication required: Bearer token missing"
        )
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Validate admin role from JWT
    is_admin = await verify_admin_role_from_jwt(token)
    if not is_admin:
        # Log the security violation
        await log_admin_operation(
            "UNAUTHORIZED_ADMIN_ACCESS_ATTEMPT",
            current_user.id,
            {
                "reason": "Insufficient admin privileges in JWT",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "attempted_endpoint": str(request.url)
            },
            request.client.host if request.client else "unknown"
        )
        
        logger.error(f"Admin access denied for user {current_user.id[:8]}... - JWT validation failed")
        raise HTTPException(
            status_code=403,
            detail="Admin access required: Insufficient privileges"
        )
    
    # Log successful admin access
    await log_admin_operation(
        "ADMIN_ACCESS_GRANTED",
        current_user.id,
        {
            "endpoint": str(request.url),
            "user_agent": request.headers.get("user-agent", "unknown")
        },
        request.client.host if request.client else "unknown"
    )
    
    return current_user

@router.get("/settings", response_model=AppConfig)
async def get_app_settings(
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> AppConfig:
    """
    Retrieve the current application settings.
    SECURITY: Only accessible to JWT-validated admins with full audit trail.
    """
    await log_admin_operation(
        "GET_SETTINGS",
        current_user.id,
        {"settings_accessed": "app_config"},
        request.client.host if request.client else "unknown"
    )
    return settings

def _validate_table_exists(log_table: str) -> None:
    """Validate table exists in available tables."""
    if log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' is not available.")

def _update_default_table(log_table: str) -> None:
    """Update default table setting."""
    settings.clickhouse_logging.default_table = log_table

def _build_table_response(log_table: str, action: str) -> Dict[str, str]:
    """Build table operation response."""
    return {"message": f"Log table '{log_table}' {action}."}

@router.post("/settings/log_table")
async def set_log_table(
    data: schemas.LogTableSettings,
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, str]:
    """Set the default ClickHouse log table."""
    _validate_table_exists(data.log_table)
    _update_default_table(data.log_table)
    
    await log_admin_operation(
        "SET_LOG_TABLE",
        current_user.id,
        {"old_table": settings.clickhouse_logging.default_table, "new_table": data.log_table},
        request.client.host if request.client else "unknown"
    )
    
    return {"message": f"Default log table updated to: {data.log_table}"}

def _validate_table_not_exists(log_table: str) -> None:
    """Validate table does not already exist."""
    if log_table in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' already exists.")

def _add_table_to_available(log_table: str) -> None:
    """Add table to available tables list."""
    settings.clickhouse_logging.available_tables.append(log_table)

@router.post("/settings/log_tables")
async def add_log_table(
    data: schemas.LogTableSettings,
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, str]:
    """Add a new ClickHouse log table to the list of available tables."""
    _validate_table_not_exists(data.log_table)
    _add_table_to_available(data.log_table)
    
    await log_admin_operation(
        "ADD_LOG_TABLE",
        current_user.id,
        {"table_added": data.log_table},
        request.client.host if request.client else "unknown"
    )
    
    return _build_table_response(data.log_table, "added to available tables")

def _validate_table_removal(log_table: str) -> None:
    """Validate table can be removed."""
    if log_table not in settings.clickhouse_logging.available_tables:
        raise HTTPException(status_code=400, detail=f"Log table '{log_table}' not found.")
    if settings.clickhouse_logging.default_table == log_table:
        raise HTTPException(status_code=400, detail="Cannot remove the default log table.")

def _remove_table_from_available(log_table: str) -> None:
    """Remove table from available tables list."""
    settings.clickhouse_logging.available_tables.remove(log_table)

@router.delete("/settings/log_tables")
async def remove_log_table(
    data: schemas.LogTableSettings,
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, str]:
    """Remove a ClickHouse log table from the list of available tables."""
    _validate_table_removal(data.log_table)
    _remove_table_from_available(data.log_table)
    
    await log_admin_operation(
        "REMOVE_LOG_TABLE",
        current_user.id,
        {"table_removed": data.log_table},
        request.client.host if request.client else "unknown"
    )
    
    return _build_table_response(data.log_table, "removed from available tables")

def _validate_time_period(days: int) -> None:
    """Validate time period is available."""
    if days not in settings.clickhouse_logging.available_time_periods:
        raise HTTPException(status_code=400, detail=f"Time period '{days}' is not available.")

def _update_default_time_period(days: int) -> None:
    """Update default time period setting."""
    settings.clickhouse_logging.default_time_period_days = days

@router.post("/settings/time_period")
async def set_time_period(
    data: schemas.TimePeriodSettings,
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, str]:
    """Set the default time period for log analysis."""
    _validate_time_period(data.days)
    old_period = settings.clickhouse_logging.default_time_period_days
    _update_default_time_period(data.days)
    
    await log_admin_operation(
        "SET_TIME_PERIOD",
        current_user.id,
        {"old_period_days": old_period, "new_period_days": data.days},
        request.client.host if request.client else "unknown"
    )
    
    return {"message": f"Default time period updated to: {data.days} days"}

def _set_context_default_table(context: str, log_table: str) -> None:
    """Set default table for specific context."""
    settings.clickhouse_logging.default_tables[context] = log_table

@router.post("/settings/default_log_table")
async def set_default_log_table_for_context(
    data: schemas.DefaultLogTableSettings,
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, str]:
    """Set the default ClickHouse log table for a specific context."""
    _validate_table_exists(data.log_table)
    old_table = settings.clickhouse_logging.default_tables.get(data.context)
    _set_context_default_table(data.context, data.log_table)
    
    await log_admin_operation(
        "SET_CONTEXT_LOG_TABLE",
        current_user.id,
        {
            "context": data.context,
            "old_table": old_table,
            "new_table": data.log_table
        },
        request.client.host if request.client else "unknown"
    )
    
    return {"message": f"Default log table for context '{data.context}' updated to: {data.log_table}"}

def _validate_context_exists(context: str) -> None:
    """Validate context exists in default tables."""
    if context not in settings.clickhouse_logging.default_tables:
        raise HTTPException(status_code=400, detail=f"Context '{context}' not found.")

def _remove_context_default_table(context: str) -> None:
    """Remove default table for context."""
    del settings.clickhouse_logging.default_tables[context]

@router.delete("/settings/default_log_table")
async def remove_default_log_table_for_context(
    data: schemas.DefaultLogTableSettings,
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, str]:
    """Remove the default ClickHouse log table for a specific context."""
    _validate_context_exists(data.context)
    old_table = settings.clickhouse_logging.default_tables.get(data.context)
    _remove_context_default_table(data.context)
    
    await log_admin_operation(
        "REMOVE_CONTEXT_LOG_TABLE",
        current_user.id,
        {
            "context": data.context,
            "removed_table": old_table
        },
        request.client.host if request.client else "unknown"
    )
    
    return {"message": f"Default log table for context '{data.context}' removed."}


# Enhanced admin dependency that validates JWT claims directly
EnhancedAdminDep = Depends(require_admin_with_jwt_validation)


# Issue #1300 Task 7: WebSocket Authentication Monitoring Dashboard Endpoints

@router.get("/websocket-auth/health")
async def get_websocket_auth_health(
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, Any]:
    """
    Get current WebSocket authentication health status.

    Business Value:
    - Real-time monitoring of WebSocket authentication reliability
    - Proactive detection of authentication failures
    - Operational visibility into chat functionality health
    """
    await log_admin_operation(
        "GET_WEBSOCKET_AUTH_HEALTH",
        current_user.id,
        {"monitoring_endpoint": "websocket-auth-health"},
        request.client.host if request.client else "unknown"
    )

    try:
        health_status = await get_auth_health_status()
        return health_status.to_dict()
    except Exception as e:
        logger.error(f"Failed to get WebSocket auth health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication monitoring service error: {str(e)}"
        )


@router.get("/websocket-auth/metrics")
async def get_websocket_auth_metrics(
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, Any]:
    """
    Get comprehensive WebSocket authentication metrics.

    Business Value:
    - Detailed authentication performance analysis
    - Success/failure rate tracking
    - Connection lifecycle monitoring
    - Circuit breaker status
    """
    await log_admin_operation(
        "GET_WEBSOCKET_AUTH_METRICS",
        current_user.id,
        {"monitoring_endpoint": "websocket-auth-metrics"},
        request.client.host if request.client else "unknown"
    )

    try:
        monitor_service = get_authentication_monitor_service()
        return monitor_service.get_authentication_stats()
    except Exception as e:
        logger.error(f"Failed to get WebSocket auth metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication monitoring service error: {str(e)}"
        )


@router.post("/websocket-auth/test-connection")
async def test_websocket_auth_connection(
    user_id: str,
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, Any]:
    """
    Test WebSocket authentication connection for a specific user.

    Business Value:
    - Admin troubleshooting capability
    - Proactive connection health validation
    - User-specific authentication issue diagnosis
    """
    await log_admin_operation(
        "TEST_WEBSOCKET_AUTH_CONNECTION",
        current_user.id,
        {"test_user_id": user_id[:8] + "..." if len(user_id) > 8 else user_id},
        request.client.host if request.client else "unknown"
    )

    try:
        monitor_service = get_authentication_monitor_service()
        result = await monitor_service.ensure_auth_connection_health(user_id)

        return {
            "user_id": user_id,
            "connection_healthy": result,
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "tested_by": current_user.id
        }
    except Exception as e:
        logger.error(f"Failed to test WebSocket auth connection for user {user_id}: {e}")
        return {
            "user_id": user_id,
            "connection_healthy": False,
            "error": str(e),
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "tested_by": current_user.id
        }


@router.get("/websocket-auth/session/{user_id}")
async def monitor_websocket_auth_session(
    user_id: str,
    duration_ms: int = 30000,
    request: Request,
    current_user: schemas.UserBase = Depends(require_admin_with_jwt_validation)
) -> Dict[str, Any]:
    """
    Monitor WebSocket authentication session for a specific user.

    Business Value:
    - Real-time session monitoring
    - Authentication state tracking
    - User-specific troubleshooting support
    """
    await log_admin_operation(
        "MONITOR_WEBSOCKET_AUTH_SESSION",
        current_user.id,
        {
            "monitored_user_id": user_id[:8] + "..." if len(user_id) > 8 else user_id,
            "duration_ms": duration_ms
        },
        request.client.host if request.client else "unknown"
    )

    try:
        monitor_service = get_authentication_monitor_service()
        result = await monitor_service.monitor_auth_session(user_id, duration_ms)

        return {
            **result,
            "monitored_by": current_user.id,
            "monitor_start_time": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to monitor WebSocket auth session for user {user_id}: {e}")
        return {
            "user_id": user_id,
            "monitoring_available": False,
            "error": str(e),
            "monitored_by": current_user.id,
            "monitor_start_time": datetime.now(timezone.utc).isoformat()
        }

