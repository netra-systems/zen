"""
Auth proxy routes - Forward auth requests to auth service.
This provides backward compatibility for tests while maintaining auth service separation.
"""

import logging
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Request

from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.core.isolated_environment import get_env

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth-proxy"])


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
    """Delegate request to auth service using auth client."""
    try:
        if endpoint == "/register":
            # Use auth client's registration method if available, otherwise use HTTP client
            return await _http_proxy_to_auth_service(endpoint, method, request_data, headers)
        elif endpoint == "/login":
            if isinstance(request_data, dict):
                email = request_data.get("email", "")
                password = request_data.get("password", "")
                result = await auth_client.login(email, password)
                if result:
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
                    raise HTTPException(status_code=401, detail="Login failed")
        elif endpoint == "/dev/login":
            # Dev login still needs to go through auth service
            return await _http_proxy_to_auth_service(endpoint, method, request_data, headers)
        elif endpoint == "/logout":
            # Extract token from headers
            token = None
            if headers and headers.get("authorization"):
                auth_header = headers["authorization"]
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix
            
            if token:
                success = await auth_client.logout(token)
                return {"success": success, "message": "Logged out successfully" if success else "Logout failed"}
            else:
                raise HTTPException(status_code=401, detail="No token provided")
        else:
            # For other endpoints, use HTTP proxy
            return await _http_proxy_to_auth_service(endpoint, method, request_data, headers)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth delegation failed for {endpoint}: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")


async def _http_proxy_to_auth_service(
    endpoint: str, 
    method: str, 
    request_data: Any = None,
    headers: Dict[str, str] = None
) -> Dict[str, Any]:
    """HTTP proxy to auth service - fallback for endpoints not handled by auth client."""
    auth_url = _get_auth_service_url()
    url = f"{auth_url}/auth{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            request_headers = headers or {}
            
            if method == "POST":
                response = await client.post(url, json=request_data, headers=request_headers)
            elif method == "GET":
                response = await client.get(url, headers=request_headers)
            else:
                raise HTTPException(status_code=405, detail=f"Method {method} not supported")
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Auth service error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text or "Auth service error"
                )
                
    except httpx.RequestError as e:
        logger.error(f"Auth service connection failed: {e}")
        # SECURITY: Never fall back to mock responses in non-test environments
        if _is_test_mode():
            logger.warning("Auth service unavailable in test mode - this should not happen in production")
            raise HTTPException(
                status_code=503,
                detail="Auth service unavailable"
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="Auth service unavailable"
            )


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