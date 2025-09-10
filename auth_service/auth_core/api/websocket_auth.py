"""
WebSocket Authentication API - Phase 1 JWT SSOT Remediation
Specialized authentication APIs for WebSocket connections
Handles both Authorization header and Sec-WebSocket-Protocol token extraction
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/auth/websocket", tags=["WebSocket Authentication"])

# Global JWT handler instance
jwt_handler = JWTHandler()

# Request/Response Models
class WebSocketAuthRequest(BaseModel):
    """Request model for WebSocket authentication"""
    authorization_header: Optional[str] = Field(None, description="Authorization header from WebSocket")
    subprotocol_token: Optional[str] = Field(None, description="Token from Sec-WebSocket-Protocol header")
    demo_mode: bool = Field(default=False, description="Enable demo mode for isolated environments")
    user_context_required: bool = Field(default=True, description="Whether user execution context is required")
    connection_id: Optional[str] = Field(None, description="WebSocket connection identifier")

class WebSocketAuthResponse(BaseModel):
    """Response model for WebSocket authentication"""
    authenticated: bool = Field(..., description="Whether authentication succeeded")
    user_id: Optional[str] = Field(None, description="Authenticated user ID")
    email: Optional[str] = Field(None, description="User email")
    permissions: Optional[list] = Field(None, description="User permissions")
    execution_context: Optional[Dict[str, Any]] = Field(None, description="User execution context")
    demo_user: bool = Field(default=False, description="Whether this is a demo user")
    error: Optional[str] = Field(None, description="Error message if authentication failed")
    auth_method: Optional[str] = Field(None, description="Authentication method used")
    connection_id: Optional[str] = Field(None, description="WebSocket connection identifier")
    auth_timestamp: str = Field(..., description="When authentication occurred")

class WebSocketTokenExtractionRequest(BaseModel):
    """Request model for WebSocket token extraction"""
    headers: Dict[str, str] = Field(..., description="WebSocket headers")
    subprotocols: Optional[list] = Field(None, description="WebSocket subprotocols")

class WebSocketTokenExtractionResponse(BaseModel):
    """Response model for WebSocket token extraction"""
    token_found: bool = Field(..., description="Whether a token was found")
    token: Optional[str] = Field(None, description="Extracted token")
    source: Optional[str] = Field(None, description="Source of token (header/subprotocol)")
    method: Optional[str] = Field(None, description="Extraction method used")
    error: Optional[str] = Field(None, description="Error message if extraction failed")

@router.post("/authenticate", response_model=WebSocketAuthResponse)
async def authenticate_websocket_connection(request: WebSocketAuthRequest) -> Dict[str, Any]:
    """
    Authenticate WebSocket connection for real-time chat
    
    Supports multiple authentication methods:
    1. Authorization header JWT extraction
    2. Sec-WebSocket-Protocol JWT extraction (staging compatibility)
    3. Demo mode for isolated environments
    
    Returns:
        WebSocketAuthResponse: Authentication result with user context
    """
    auth_start = time.time()
    
    try:
        # Log authentication attempt
        logger.info(f"WebSocket authentication request: demo_mode={request.demo_mode}, "
                   f"connection_id={request.connection_id}")
        
        token = None
        auth_method = None
        
        # Try to extract token from Authorization header first
        if request.authorization_header:
            if request.authorization_header.startswith("Bearer "):
                token = request.authorization_header.replace("Bearer ", "").strip()
                auth_method = "authorization_header"
                logger.debug("Token extracted from Authorization header")
            else:
                logger.warning("Authorization header provided but doesn't start with 'Bearer '")
        
        # Fall back to subprotocol token if no Authorization header
        if not token and request.subprotocol_token:
            token = request.subprotocol_token.strip()
            auth_method = "subprotocol"
            logger.debug("Token extracted from Sec-WebSocket-Protocol")
        
        # Handle demo mode for isolated environments
        if not token and request.demo_mode:
            environment = AuthConfig.get_environment()
            if environment in ["development", "test"]:
                # Create demo user context
                demo_user_id = "demo-websocket-user"
                demo_email = "demo@websocket.local"
                
                auth_time = (time.time() - auth_start) * 1000
                logger.info(f"Demo mode authentication for WebSocket in {auth_time:.2f}ms")
                
                return {
                    "authenticated": True,
                    "user_id": demo_user_id,
                    "email": demo_email,
                    "permissions": ["read", "write"],
                    "execution_context": {
                        "user_id": demo_user_id,
                        "session_id": f"demo-session-{int(time.time())}",
                        "environment": environment,
                        "demo_mode": True
                    },
                    "demo_user": True,
                    "auth_method": "demo_mode",
                    "connection_id": request.connection_id,
                    "auth_timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                logger.warning(f"Demo mode requested in {environment} environment - denied")
                return {
                    "authenticated": False,
                    "error": "demo_mode_not_allowed_in_production",
                    "auth_timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        # Validate token if provided
        if token:
            try:
                payload = jwt_handler.validate_token(token, "access")
                
                if payload:
                    user_id = payload.get("sub")
                    email = payload.get("email")
                    permissions = payload.get("permissions", [])
                    
                    # Create user execution context
                    execution_context = {
                        "user_id": user_id,
                        "session_id": f"ws-session-{int(time.time())}",
                        "environment": AuthConfig.get_environment(),
                        "connection_id": request.connection_id,
                        "auth_method": auth_method,
                        "authenticated_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    auth_time = (time.time() - auth_start) * 1000
                    logger.info(f"WebSocket authentication successful for user {user_id} in {auth_time:.2f}ms")
                    
                    return {
                        "authenticated": True,
                        "user_id": user_id,
                        "email": email,
                        "permissions": permissions,
                        "execution_context": execution_context,
                        "demo_user": False,
                        "auth_method": auth_method,
                        "connection_id": request.connection_id,
                        "auth_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    auth_time = (time.time() - auth_start) * 1000
                    logger.warning(f"WebSocket token validation failed in {auth_time:.2f}ms")
                    return {
                        "authenticated": False,
                        "error": "invalid_or_expired_token",
                        "auth_method": auth_method,
                        "connection_id": request.connection_id,
                        "auth_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
            except Exception as e:
                auth_time = (time.time() - auth_start) * 1000
                logger.error(f"WebSocket token validation error in {auth_time:.2f}ms: {e}")
                return {
                    "authenticated": False,
                    "error": "token_validation_error",
                    "auth_method": auth_method,
                    "connection_id": request.connection_id,
                    "auth_timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        # No token provided and not demo mode
        auth_time = (time.time() - auth_start) * 1000
        logger.warning(f"WebSocket authentication failed - no token provided in {auth_time:.2f}ms")
        return {
            "authenticated": False,
            "error": "no_authentication_provided",
            "connection_id": request.connection_id,
            "auth_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        auth_time = (time.time() - auth_start) * 1000
        logger.error(f"WebSocket authentication error in {auth_time:.2f}ms: {e}")
        return {
            "authenticated": False,
            "error": "authentication_error",
            "connection_id": request.connection_id,
            "auth_timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.post("/extract-token", response_model=WebSocketTokenExtractionResponse)
async def extract_websocket_token(request: WebSocketTokenExtractionRequest) -> Dict[str, Any]:
    """
    Extract JWT token from WebSocket headers and subprotocols
    
    Supports multiple extraction methods for different staging environments.
    """
    try:
        # Try Authorization header first
        authorization = request.headers.get("Authorization") or request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "").strip()
            if token:
                return {
                    "token_found": True,
                    "token": token,
                    "source": "header",
                    "method": "authorization_bearer"
                }
        
        # Try Sec-WebSocket-Protocol for staging compatibility
        subprotocol_header = (request.headers.get("Sec-WebSocket-Protocol") or 
                             request.headers.get("sec-websocket-protocol"))
        
        if subprotocol_header:
            # Handle multiple subprotocols (comma-separated)
            subprotocols = [p.strip() for p in subprotocol_header.split(",")]
            
            for subprotocol in subprotocols:
                # Check if subprotocol looks like a JWT token
                if self._is_jwt_like_token(subprotocol):
                    return {
                        "token_found": True,
                        "token": subprotocol,
                        "source": "subprotocol",
                        "method": "sec_websocket_protocol"
                    }
        
        # Try request.subprotocols if provided
        if request.subprotocols:
            for subprotocol in request.subprotocols:
                if self._is_jwt_like_token(subprotocol):
                    return {
                        "token_found": True,
                        "token": subprotocol,
                        "source": "subprotocol",
                        "method": "subprotocols_array"
                    }
        
        # No token found
        logger.debug("No JWT token found in WebSocket headers or subprotocols")
        return {
            "token_found": False,
            "error": "no_token_found_in_headers_or_subprotocols"
        }
        
    except Exception as e:
        logger.error(f"WebSocket token extraction error: {e}")
        return {
            "token_found": False,
            "error": "token_extraction_error"
        }

def _is_jwt_like_token(token_candidate: str) -> bool:
    """
    Check if a string looks like a JWT token
    
    JWT tokens have 3 parts separated by dots and use base64url encoding.
    """
    if not token_candidate or not isinstance(token_candidate, str):
        return False
    
    # Basic JWT structure check
    parts = token_candidate.split(".")
    if len(parts) != 3:
        return False
    
    # Check that parts are not empty and contain base64url-like characters
    for part in parts:
        if not part:
            return False
        # Base64url characters: A-Z, a-z, 0-9, -, _
        if not all(c.isalnum() or c in "-_" for c in part):
            return False
    
    # Additional length check (JWT tokens are typically 100+ characters)
    if len(token_candidate) < 50:
        return False
    
    return True

@router.post("/validate-connection")
async def validate_websocket_connection(request: Request) -> Dict[str, Any]:
    """
    Validate an existing WebSocket connection's authentication
    
    Used for periodic validation and connection health checks.
    """
    try:
        body = await request.json()
        connection_id = body.get("connection_id")
        token = body.get("token")
        
        if not connection_id:
            return {
                "valid": False,
                "error": "connection_id_required"
            }
        
        if not token:
            return {
                "valid": False,
                "error": "token_required"
            }
        
        # Validate token
        payload = jwt_handler.validate_token(token, "access")
        
        if payload:
            user_id = payload.get("sub")
            logger.debug(f"WebSocket connection {connection_id} validation successful for user {user_id}")
            
            return {
                "valid": True,
                "connection_id": connection_id,
                "user_id": user_id,
                "email": payload.get("email"),
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            logger.warning(f"WebSocket connection {connection_id} validation failed")
            return {
                "valid": False,
                "connection_id": connection_id,
                "error": "invalid_or_expired_token",
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    except Exception as e:
        logger.error(f"WebSocket connection validation error: {e}")
        return {
            "valid": False,
            "error": "validation_error"
        }

@router.post("/refresh-context")
async def refresh_websocket_context(request: Request) -> Dict[str, Any]:
    """
    Refresh user execution context for a WebSocket connection
    
    Used when tokens are refreshed or user permissions change.
    """
    try:
        body = await request.json()
        connection_id = body.get("connection_id")
        new_token = body.get("new_token")
        
        if not connection_id or not new_token:
            return {
                "success": False,
                "error": "connection_id_and_new_token_required"
            }
        
        # Validate new token
        payload = jwt_handler.validate_token(new_token, "access")
        
        if payload:
            user_id = payload.get("sub")
            email = payload.get("email")
            permissions = payload.get("permissions", [])
            
            # Create updated execution context
            updated_context = {
                "user_id": user_id,
                "session_id": f"ws-session-refreshed-{int(time.time())}",
                "environment": AuthConfig.get_environment(),
                "connection_id": connection_id,
                "refreshed_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"WebSocket context refreshed for connection {connection_id}, user {user_id}")
            
            return {
                "success": True,
                "connection_id": connection_id,
                "user_id": user_id,
                "email": email,
                "permissions": permissions,
                "execution_context": updated_context,
                "refresh_timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "success": False,
                "connection_id": connection_id,
                "error": "invalid_new_token"
            }
        
    except Exception as e:
        logger.error(f"WebSocket context refresh error: {e}")
        return {
            "success": False,
            "error": "context_refresh_error"
        }

@router.get("/health")
async def websocket_auth_health() -> Dict[str, Any]:
    """
    Health check for WebSocket authentication service
    """
    try:
        # Test WebSocket authentication flow
        test_user_id = "websocket-health-check"
        test_email = "websocket-health@example.com"
        
        # Create test token
        test_token = jwt_handler.create_access_token(test_user_id, test_email)
        
        # Test authentication
        auth_request = WebSocketAuthRequest(
            authorization_header=f"Bearer {test_token}",
            connection_id="health-check-connection"
        )
        
        auth_result = await authenticate_websocket_connection(auth_request)
        
        if auth_result.get("authenticated"):
            health_status = "healthy"
        else:
            health_status = "unhealthy"
        
        return {
            "status": health_status,
            "service": "websocket-authentication",
            "test_result": auth_result.get("authenticated", False),
            "environment": AuthConfig.get_environment(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"WebSocket auth health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "websocket-authentication",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }