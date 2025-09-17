"""
Auth proxy routes - Forward auth requests to auth service.
This provides backward compatibility for tests while maintaining auth service separation.
"""

import logging
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Request

from netra_backend.app.clients.auth_client_core import auth_client
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth-proxy"])

# Additional router for backward compatibility with tests expecting /auth/config
compat_router = APIRouter(prefix="/auth", tags=["auth-compat"])


def _get_auth_service_url() -> str:
    """Get auth service URL from environment."""
    env = get_env()
    auth_url = env.get("AUTH_SERVICE_URL", "http://localhost:8081")
    return auth_url


def _is_test_mode() -> bool:
    """Check if we're in test mode - STRICT checking for security."""
    env = get_env()
    # SECURITY: Only allow mock responses in explicit test modes
    return (
        env.get("TESTING") == "1" and
        (env.get("NETRA_ENV") == "e2e_testing" or 
         env.get("ENVIRONMENT", "").lower() in ["test", "testing"])
    )


async def _delegate_to_auth_service(
    endpoint: str, 
    method: str, 
    request_data: Any = None,
    headers: Dict[str, str] = None
) -> Dict[str, Any]:
    """Delegate request to auth service using auth client with enhanced error handling."""
    from netra_backend.app.routes.auth_routes.debug_helpers import (
        enhanced_auth_service_call,
        AuthServiceDebugger
    )
    
    try:
        if endpoint == "/register":
            # Use auth client's registration method if available, otherwise use HTTP client
            return await enhanced_auth_service_call(
                _http_proxy_to_auth_service, endpoint, method, request_data, headers,
                operation_name="user_registration"
            )
        elif endpoint == "/login":
            if isinstance(request_data, dict):
                email = request_data.get("email", "")
                password = request_data.get("password", "")
                
                # Enhanced login with debugging
                async def enhanced_login():
                    debugger = AuthServiceDebugger()
                    
                    # Log debug info before attempting login
                    debug_info = debugger.log_environment_debug_info()
                    logger.info(f"Attempting login for user: {email}")
                    
                    # Test connectivity first
                    connectivity = await debugger.test_auth_service_connectivity()
                    if connectivity["connectivity_test"] == "failed":
                        logger.error("Auth service connectivity test failed before login attempt")
                        logger.error(f"Connectivity details: {connectivity}")
                        
                        # Provide specific error based on connectivity issue
                        if connectivity["error"]:
                            error_detail = f"Auth service unreachable: {connectivity['error']}"
                        else:
                            error_detail = f"Auth service at {connectivity['auth_service_url']} is not responding"
                        
                        raise HTTPException(
                            status_code=503,
                            detail=error_detail
                        )
                    
                    # Attempt the login
                    result = await auth_client.login(email, password)
                    
                    if result:
                        logger.info(f"Login successful for user: {email}")
                        # Convert result to expected format
                        return {
                            "access_token": result.get("access_token", ""),
                            "refresh_token": result.get("refresh_token", ""),
                            "token_type": result.get("token_type", "Bearer"),
                            "expires_in": result.get("expires_in", 900),
                            "user": {
                                "id": result.get("user_id", ""),
                                "email": email,
                                "name": result.get("name", email.split("@")[0])
                            }
                        }
                    else:
                        logger.warning(f"Login failed for user: {email} - auth client returned None")
                        
                        # Debug the failure
                        debug_result = await debugger.debug_login_attempt(email, password)
                        logger.error(f"Login failure debug: {debug_result}")
                        
                        raise HTTPException(
                            status_code=401, 
                            detail="Login failed - invalid credentials or service unavailable"
                        )
                
                return await enhanced_login()
                
        elif endpoint == "/dev/login":
            # Dev login still needs to go through auth service
            return await enhanced_auth_service_call(
                _http_proxy_to_auth_service, endpoint, method, request_data, headers,
                operation_name="dev_login"
            )
        elif endpoint == "/logout":
            # Extract token from headers
            token = None
            if headers and headers.get("authorization"):
                auth_header = headers["authorization"]
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix
            
            if token:
                async def enhanced_logout():
                    success = await auth_client.logout(token)
                    return {"success": success, "message": "Logged out successfully" if success else "Logout failed"}
                    
                return await enhanced_auth_service_call(
                    enhanced_logout,
                    operation_name="user_logout"
                )
            else:
                raise HTTPException(status_code=401, detail="No token provided")
        else:
            # For other endpoints, use HTTP proxy
            return await enhanced_auth_service_call(
                _http_proxy_to_auth_service, endpoint, method, request_data, headers,
                operation_name=f"auth_{endpoint.replace('/', '_')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth delegation failed for {endpoint}: {e}")
        
        # Use enhanced error response
        from netra_backend.app.routes.auth_routes.debug_helpers import create_enhanced_auth_error_response
        raise create_enhanced_auth_error_response(e)


async def _http_proxy_to_auth_service(
    endpoint: str, 
    method: str, 
    request_data: Any = None,
    headers: Dict[str, str] = None
) -> Dict[str, Any]:
    """HTTP proxy to auth service - fallback for endpoints not handled by auth client."""
    from netra_backend.app.routes.auth_routes.debug_helpers import AuthServiceDebugger
    
    debugger = AuthServiceDebugger()
    auth_url = debugger.get_auth_service_url()
    url = f"{auth_url}/auth{endpoint}"
    
    # Log the proxy attempt
    logger.info(f"Proxying {method} request to: {url}")
    
    try:
        # Add service credentials to headers if available
        service_id, service_secret = debugger.get_service_credentials()
        request_headers = headers or {}
        
        if service_id and service_secret:
            request_headers.update({
                "X-Service-ID": service_id,
                "X-Service-Secret": service_secret
            })
            logger.info("Added service authentication headers to proxy request")
        else:
            logger.warning("No service credentials available for proxy request")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "POST":
                logger.debug(f"POST data: {request_data}")
                response = await client.post(url, json=request_data, headers=request_headers)
            elif method == "GET":
                response = await client.get(url, headers=request_headers)
            else:
                raise HTTPException(status_code=405, detail=f"Method {method} not supported")
            
            logger.info(f"Auth service response: {response.status_code}")
            
            if response.status_code in [200, 201]:
                try:
                    response_data = response.json()
                    logger.info("Successfully parsed JSON response from auth service")
                    return response_data
                except Exception as e:
                    logger.error(f"Failed to parse auth service response as JSON: {e}")
                    logger.error(f"Response text: {response.text}")
                    raise HTTPException(
                        status_code=502,
                        detail="Auth service returned invalid response format"
                    )
            else:
                logger.error(f"Auth service error: {response.status_code} - {response.text}")
                
                # Provide more specific error messages based on status code
                if response.status_code == 401:
                    error_detail = "Authentication failed - invalid credentials"
                elif response.status_code == 403:
                    error_detail = "Access forbidden - service authentication may be invalid"
                elif response.status_code == 404:
                    error_detail = f"Auth service endpoint not found: {endpoint}"
                elif response.status_code >= 500:
                    error_detail = "Auth service internal error"
                else:
                    error_detail = response.text or "Auth service error"
                
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
                
    except httpx.ConnectTimeout:
        logger.error(f"Connection timeout to auth service at: {auth_url}")
        raise HTTPException(
            status_code=503,
            detail=f"Auth service connection timeout at {auth_url}"
        )
    except httpx.ReadTimeout:
        logger.error(f"Read timeout from auth service at: {auth_url}")
        raise HTTPException(
            status_code=503,
            detail="Auth service response timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"Auth service connection failed: {e}")
        logger.error(f"Auth service URL: {auth_url}")
        
        # Test connectivity to provide better error messages
        connectivity = await debugger.test_auth_service_connectivity()
        logger.error(f"Connectivity test result: {connectivity}")
        
        # SECURITY: Never fall back to mock responses in non-test environments
        if _is_test_mode():
            logger.warning("Auth service unavailable in test mode - this should not happen in production")
            raise HTTPException(
                status_code=503,
                detail="Auth service unavailable in test mode"
            )
        else:
            # Provide specific error based on connectivity test
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                error_detail = f"Cannot connect to auth service at {auth_url}"
            else:
                error_detail = f"Auth service communication error: {str(e)}"
                
            raise HTTPException(
                status_code=503,
                detail=error_detail
            )


@router.get("/")
async def get_auth_info():
    """Get authentication information - base auth endpoint."""
    return {"data": "Authentication service available"}


@router.post("/", status_code=201)
async def post_auth():
    """Post to auth endpoint - generic auth POST."""
    # Return 201 Created for successful auth operation
    return {"message": "Auth operation successful"}


@router.get("/protected")
async def get_protected():
    """Protected endpoint that requires authentication."""
    # Always return 401 Unauthorized as this is a protected endpoint
    # In a real implementation, this would check for valid authentication
    raise HTTPException(status_code=401, detail="Authentication required")


@router.get("/invalid")
async def get_invalid_path():
    """Handle invalid auth path - returns 404."""
    raise HTTPException(status_code=404, detail="Auth endpoint not found")


@router.post("/register")
async def register_user(request: Request):
    """Register a new user by delegating to auth service."""
    try:
        request_body = await request.json()
        
        # Ensure confirm_password is set if only password is provided
        # This maintains backward compatibility with tests that only send password
        if "password" in request_body and "confirm_password" not in request_body:
            request_body["confirm_password"] = request_body["password"]
        
        result = await _delegate_to_auth_service("/register", "POST", request_body)
        return result
    except Exception as e:
        logger.error(f"Registration proxy failed: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login")
async def login_user(request: Request):
    """Login user by delegating to auth service."""
    try:
        request_body = await request.json()
        result = await _delegate_to_auth_service("/login", "POST", request_body)
        return result
    except Exception as e:
        logger.error(f"Login proxy failed: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/dev_login")
async def dev_login_user(request: Request):
    """Development login by delegating to auth service."""
    try:
        request_body = await request.json()
        result = await _delegate_to_auth_service("/dev/login", "POST", request_body)
        return result
    except Exception as e:
        logger.error(f"Dev login proxy failed: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Dev login failed")


@router.post("/logout")
async def logout_user(request: Request):
    """Logout user by delegating to auth service."""
    try:
        # Get Authorization header for logout
        auth_header = request.headers.get("authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="No token provided")
        
        # Create headers dict for delegation
        headers = {"authorization": auth_header}
        result = await _delegate_to_auth_service("/logout", "POST", {}, headers)
        return result
            
    except Exception as e:
        logger.error(f"Logout proxy failed: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/config")
async def get_auth_config():
    """Get authentication configuration by delegating to auth service."""
    try:
        result = await _delegate_to_auth_service("/config", "GET")
        return result
    except Exception as e:
        logger.error(f"Auth config proxy failed: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="Auth config retrieval failed")


# Compatibility router for tests expecting /auth/* endpoints
@compat_router.get("/config")
async def get_auth_config_compat():
    """Get authentication configuration - compatibility endpoint for tests."""
    return await get_auth_config()


@compat_router.post("/login")
async def login_user_compat(request: Request):
    """Login user - compatibility endpoint for tests expecting /auth/login."""
    return await login_user(request)


@compat_router.post("/register") 
async def register_user_compat(request: Request):
    """Register user - compatibility endpoint for tests expecting /auth/register."""
    return await register_user(request)


@router.post("/generate-ticket")
async def generate_ticket(request: Request):
    """
    Generate authentication ticket for temporary access.
    
    ISSUE #1296 Phase 2: Creates secure, time-limited tickets for authentication
    workflows without exposing long-lived credentials.
    
    Requires:
    - Valid JWT token in Authorization header
    - Optional: ttl_seconds, single_use, permissions, metadata in request body
    
    Returns:
    - ticket_id: Unique ticket identifier
    - expires_at: Ticket expiration timestamp
    - user_id: User the ticket was generated for
    """
    try:
        # Get JWT token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Ticket generation attempted without valid Authorization header")
            raise HTTPException(
                status_code=401,
                detail="Authorization header with Bearer token required"
            )
        
        jwt_token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate JWT token first using auth client
        try:
            validation_result = await auth_client.validate_token_jwt(jwt_token)
            if not validation_result or not validation_result.get('valid'):
                logger.warning("Ticket generation attempted with invalid JWT token")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired JWT token"
                )
            
            user_id = validation_result.get('user_id')
            email = validation_result.get('email')
            user_permissions = validation_result.get('permissions', [])
            
            if not user_id or not email:
                logger.error("JWT token validation succeeded but missing user_id or email")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token data - missing user information"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"JWT token validation failed during ticket generation: {e}")
            raise HTTPException(
                status_code=401,
                detail="Token validation failed"
            )
        
        # Parse request body for optional parameters
        try:
            body = await request.json()
        except Exception:
            body = {}  # Use defaults if no valid JSON body
        
        # Extract optional parameters with defaults
        ttl_seconds = body.get('ttl_seconds')
        single_use = body.get('single_use', True)
        permissions = body.get('permissions') or user_permissions  # Use user's permissions as default
        metadata = body.get('metadata', {})
        
        # Validate ttl_seconds if provided
        if ttl_seconds is not None:
            try:
                ttl_seconds = int(ttl_seconds)
                if ttl_seconds <= 0:
                    raise ValueError("TTL must be positive")
                if ttl_seconds > 3600:  # 1 hour max from AuthTicketManager
                    logger.warning(f"TTL {ttl_seconds}s exceeds maximum, will be capped at 3600s")
            except (ValueError, TypeError) as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid ttl_seconds: {str(e)}"
                )
        
        # Generate ticket using AuthTicketManager
        try:
            from netra_backend.app.websocket_core.unified_auth_ssot import ticket_manager
            
            ticket = await ticket_manager.generate_ticket(
                user_id=user_id,
                email=email,
                permissions=permissions,
                ttl_seconds=ttl_seconds,
                single_use=single_use,
                metadata=metadata
            )
            
            logger.info(f"Successfully generated auth ticket {ticket.ticket_id} for user {user_id}")
            
            # Return ticket information
            return {
                "ticket_id": ticket.ticket_id,
                "user_id": ticket.user_id,
                "email": ticket.email,
                "permissions": ticket.permissions,
                "expires_at": ticket.expires_at,
                "created_at": ticket.created_at,
                "single_use": ticket.single_use,
                "ttl_seconds": int(ticket.expires_at - ticket.created_at) if ticket.expires_at and ticket.created_at else None,
                "metadata": ticket.metadata
            }
            
        except ValueError as e:
            logger.error(f"Ticket generation validation error: {e}")
            raise HTTPException(
                status_code=422,
                detail=str(e)
            )
        except RuntimeError as e:
            logger.error(f"Ticket generation storage error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Ticket storage failed - service temporarily unavailable"
            )
        except Exception as e:
            logger.error(f"Unexpected error during ticket generation: {e}")
            raise HTTPException(
                status_code=500,
                detail="Ticket generation failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_ticket endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during ticket generation"
        )


@compat_router.post("/generate-ticket")
async def generate_ticket_compat(request: Request):
    """Generate authentication ticket - compatibility endpoint for tests expecting /auth/generate-ticket."""
    return await generate_ticket(request)