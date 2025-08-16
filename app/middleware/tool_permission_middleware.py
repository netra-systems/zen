"""
Tool Permission Middleware - Integrates tool permissions into FastAPI request flow
"""
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.models_postgres import User
from app.db.postgres import get_db
from app.services.tool_permission_service import ToolPermissionService
from app.services.unified_tool_registry import UnifiedToolRegistry
from app.schemas.ToolPermission import ToolExecutionContext, PermissionCheckResult
from app.auth.auth_dependencies import get_current_user
from app.logging_config import central_logger
import json
import time
from datetime import datetime, UTC

logger = central_logger


class ToolPermissionMiddleware:
    """Middleware to enforce tool permissions"""
    
    def __init__(
        self, 
        permission_service: ToolPermissionService,
        tool_registry: UnifiedToolRegistry
    ):
        self.permission_service = permission_service
        self.tool_registry = tool_registry
    
    async def __call__(self, request: Request, call_next: Callable):
        """Process request with tool permission checking"""
        start_time = time.time()
        try:
            return await self._process_tool_request(request, call_next, start_time)
        except Exception as e:
            logger.error(f"Tool permission middleware error: {e}", exc_info=True)
            return await call_next(request)
    
    async def _process_tool_request(self, request: Request, call_next: Callable, start_time: float):
        """Process tool request with permission checking and logging."""
        await self._handle_tool_permission_check(request)
        response = await call_next(request)
        await self._handle_tool_execution_logging(request, response, start_time)
        return response
    
    async def _handle_tool_permission_check(self, request: Request) -> None:
        """Handle tool permission checking for tool endpoints."""
        if await self._is_tool_endpoint(request):
            tool_info = await self._extract_tool_info(request)
            if tool_info:
                user = await self._get_user_from_request(request)
                if user:
                    await self._verify_tool_permissions(request, tool_info, user)
    
    async def _verify_tool_permissions(self, request: Request, tool_info: dict, user) -> None:
        """Verify tool permissions and set request state."""
        permission_result = await self._check_tool_permissions(tool_info, user, request)
        if not permission_result.allowed:
            raise HTTPException(status_code=403, detail=self._permission_denied_response(permission_result))
        self._set_request_permission_state(request, permission_result, tool_info)
    
    async def _handle_tool_execution_logging(self, request: Request, response, start_time: float) -> None:
        """Handle tool execution logging if needed."""
        if hasattr(request.state, 'tool_info'):
            await self._log_tool_execution(
                request, response, time.time() - start_time
            )
    
    async def _is_tool_endpoint(self, request: Request) -> bool:
        """Check if request is for a tool execution endpoint"""
        # Check for tool-related paths
        tool_paths = [
            "/api/tools/",
            "/api/agents/",
            "/api/mcp/",
            "/api/admin/"  # Admin endpoints are now tool endpoints
        ]
        
        return any(request.url.path.startswith(path) for path in tool_paths)
    
    async def _extract_tool_info(self, request: Request) -> Optional[dict]:
        """Extract tool information from request"""
        try:
            tool_info = await self._extract_from_post_body(request)
            if tool_info:
                return tool_info
            return self._extract_from_alternative_sources(request)
        except Exception as e:
            logger.error(f"Error extracting tool info: {e}")
            return None
    
    async def _extract_from_alternative_sources(self, request: Request) -> Optional[dict]:
        """Extract tool info from URL path or MCP endpoint."""
        return self._extract_from_url_path(request) or await self._extract_from_mcp_endpoint(request)
    
    async def _extract_from_post_body(self, request: Request) -> Optional[dict]:
        """Extract tool info from POST request body."""
        if not self._is_post_request_with_body(request):
            return None
        body = await request.body()
        if not body:
            return None
        data = json.loads(body)
        return self._create_tool_info_from_data(data)
    
    def _create_tool_info_from_data(self, data: dict) -> Optional[dict]:
        """Create tool info from parsed data."""
        if "tool_name" not in data:
            return None
        return {
            "name": data["tool_name"],
            "arguments": data.get("arguments", {}),
            "action": data.get("action", "execute")
        }
    
    def _extract_from_url_path(self, request: Request) -> Optional[dict]:
        """Extract tool info from URL path."""
        path_parts = request.url.path.split("/")
        if len(path_parts) >= 4 and path_parts[2] == "tools":
            return self._build_tool_info_from_path(path_parts, request.query_params)
        return None
    
    async def _extract_from_mcp_endpoint(self, request: Request) -> Optional[dict]:
        """Extract tool info from MCP endpoint."""
        if "/mcp/call" in request.url.path:
            body = await request.body()
            if body:
                data = json.loads(body)
                return self._build_mcp_tool_info(data)
        return None
    
    async def _get_user_from_request(self, request: Request) -> Optional[User]:
        """Get user from request context"""
        try:
            if hasattr(request.state, 'user'):
                return request.state.user
            return self._extract_user_from_auth_header(request)
        except Exception as e:
            logger.error(f"Error getting user from request: {e}")
            return None
    
    def _extract_user_from_auth_header(self, request: Request) -> Optional[User]:
        """Extract user from authorization header."""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # This would typically validate the JWT token and get user
            # For now, return None to skip permission checking
            pass
        return None
    
    async def _check_tool_permissions(
        self, 
        tool_info: dict, 
        user: User,
        request: Request
    ) -> PermissionCheckResult:
        """Check if user has permission to use the tool"""
        try:
            context = self._create_execution_context(tool_info, user)
            return await self.permission_service.check_tool_permission(context)
        except Exception as e:
            logger.error(f"Error checking tool permissions: {e}")
            return self._create_failed_permission_result(e)
    
    def _create_execution_context(self, tool_info: dict, user: User) -> ToolExecutionContext:
        """Create tool execution context from tool info and user."""
        return ToolExecutionContext(
            user_id=str(user.id),
            tool_name=tool_info["name"],
            requested_action=tool_info.get("action", "execute"),
            user_plan=getattr(user, 'plan_tier', 'free'),
            user_roles=getattr(user, 'roles', []),
            feature_flags=getattr(user, 'feature_flags', {}),
            is_developer=getattr(user, 'is_developer', False),
            environment=self._get_environment()
        )
    
    def _create_failed_permission_result(self, error: Exception) -> PermissionCheckResult:
        """Create failed permission result for errors."""
        return PermissionCheckResult(
            allowed=False,
            reason=f"Permission check failed: {str(error)}"
        )
    
    def _get_environment(self) -> str:
        """Get current environment"""
        import os
        return os.getenv("ENVIRONMENT", "production")
    
    def _permission_denied_response(
        self, 
        permission_result: PermissionCheckResult
    ) -> Response:
        """Create permission denied response"""
        error_detail = {
            "error": "permission_denied",
            "message": permission_result.reason,
            "required_permissions": permission_result.required_permissions,
            "missing_permissions": permission_result.missing_permissions,
            "upgrade_path": permission_result.upgrade_path
        }
        
        if permission_result.rate_limit_status:
            error_detail["rate_limit"] = permission_result.rate_limit_status
        
        return Response(
            content=json.dumps(error_detail),
            status_code=403,
            headers={"Content-Type": "application/json"}
        )
    
    async def _log_tool_execution(
        self,
        request: Request,
        response: Response,
        execution_time: float
    ):
        """Log tool execution for analytics"""
        try:
            tool_info = request.state.tool_info
            permission_check = getattr(request.state, 'permission_check', None)
            
            log_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "tool_name": tool_info["name"],
                "user_id": getattr(request.state, 'user_id', 'unknown'),
                "action": tool_info.get("action", "execute"),
                "status_code": response.status_code,
                "execution_time_ms": int(execution_time * 1000),
                "user_agent": request.headers.get("User-Agent"),
                "ip_address": request.client.host if request.client else None,
            }
            
            if permission_check:
                log_entry.update({
                    "permission_allowed": permission_check.allowed,
                    "required_permissions": permission_check.required_permissions,
                })
            
            # Log to central logger (could also send to analytics service)
            logger.info("Tool execution", extra={"tool_execution": log_entry})
            
        except Exception as e:
            logger.error(f"Error logging tool execution: {e}")

    async def _handle_middleware_error(self, error: Exception, request: Request, call_next: Callable):
        """Handle middleware errors."""
        logger.error(f"Tool permission middleware error: {error}", exc_info=True)
        return await call_next(request)

    def _set_request_permission_state(self, request: Request, permission_result, tool_info: dict) -> None:
        """Set permission state on request."""
        request.state.permission_check = permission_result
        request.state.tool_info = tool_info

    def _is_post_request_with_body(self, request: Request) -> bool:
        """Check if request is POST with body."""
        return request.method == "POST" and hasattr(request, "_body")

    def _build_tool_info_dict(self, data: dict) -> dict:
        """Build tool info dictionary from data."""
        return {
            "name": data["tool_name"],
            "arguments": data.get("arguments", {}),
            "action": data.get("action", "execute")
        }

    def _build_tool_info_from_path(self, path_parts: list, query_params) -> dict:
        """Build tool info from URL path parts."""
        return {
            "name": path_parts[3],
            "action": path_parts[4] if len(path_parts) > 4 else "execute",
            "arguments": dict(query_params)
        }

    def _build_mcp_tool_info(self, data: dict) -> dict:
        """Build tool info from MCP data."""
        return {
            "name": data.get("method", "unknown"),
            "arguments": data.get("params", {}),
            "action": "execute"
        }


def create_tool_permission_dependency(
    permission_service: ToolPermissionService,
    tool_registry: UnifiedToolRegistry
):
    """Create a dependency for checking tool permissions in FastAPI endpoints"""
    
    async def check_tool_permission(
        tool_name: str,
        action: str = "execute",
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Dependency to check tool permissions"""
        try:
            # Create execution context
            context = ToolExecutionContext(
                user_id=str(current_user.id),
                tool_name=tool_name,
                requested_action=action,
                user_plan=getattr(current_user, 'plan_tier', 'free'),
                user_roles=getattr(current_user, 'roles', []),
                feature_flags=getattr(current_user, 'feature_flags', {}),
                is_developer=getattr(current_user, 'is_developer', False),
            )
            
            # Check permissions
            permission_result = await permission_service.check_tool_permission(context)
            
            if not permission_result.allowed:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "permission_denied",
                        "message": permission_result.reason,
                        "required_permissions": permission_result.required_permissions,
                        "upgrade_path": permission_result.upgrade_path
                    }
                )
            
            return permission_result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tool permission dependency error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Permission check failed"
            )
    
    return check_tool_permission


# Convenience function to create the middleware
def create_tool_permission_middleware(
    permission_service: ToolPermissionService,
    tool_registry: UnifiedToolRegistry
) -> ToolPermissionMiddleware:
    """Create tool permission middleware instance"""
    return ToolPermissionMiddleware(permission_service, tool_registry)