"""
Auth Routes for Auth Service
Comprehensive implementation with refresh token endpoint
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

# Import auth service models and services
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import RefreshRequest
from shared.isolated_environment import get_env

# Import MockAuthService for testing
from auth_service.test_framework.mock_auth_service import MockAuthService

# Get environment manager
env = get_env()

logger = logging.getLogger(__name__)

# Create router instances
router = APIRouter()
oauth_router = APIRouter()

# Global auth service instance - use real implementation
auth_service = AuthService()

@router.get("/auth/status")
async def auth_status() -> Dict[str, Any]:
    """Basic auth service status endpoint"""
    return {
        "service": "auth-service",
        "status": "running",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0"
    }

@router.get("/auth/config")
async def auth_config() -> Dict[str, Any]:
    """Get auth service configuration for frontend initialization"""
    from auth_service.auth_core.config import AuthConfig
    
    # Get environment for conditional logic
    environment = AuthConfig.get_environment()
    is_development = environment in ["development", "test"]
    
    # Get Google OAuth client ID
    google_client_id = AuthConfig.get_google_client_id() or ""
    
    # Determine base URLs based on environment
    if environment == "production":
        auth_base_url = "https://auth.netrasystems.ai"
        frontend_base_url = "https://app.netrasystems.ai"
    elif environment == "staging":
        auth_base_url = "https://auth.staging.netrasystems.ai"
        frontend_base_url = "https://app.staging.netrasystems.ai"
    else:
        # Development/test environment
        auth_base_url = "http://localhost:8081"
        frontend_base_url = "http://localhost:3000"
    
    # Build auth configuration response matching frontend expectations
    config_response = {
        "google_client_id": google_client_id,
        "oauth_enabled": bool(google_client_id),
        "development_mode": is_development,
        "endpoints": {
            "login": f"{auth_base_url}/auth/login",
            "logout": f"{auth_base_url}/auth/logout", 
            "callback": f"{auth_base_url}/auth/callback",
            "token": f"{auth_base_url}/auth/token",
            "user": f"{auth_base_url}/auth/me",
            "dev_login": f"{auth_base_url}/auth/dev/login" if is_development else None
        },
        "authorized_javascript_origins": [frontend_base_url],
        "authorized_redirect_uris": [f"{frontend_base_url}/auth/callback"]
    }
    
    # Remove None values from endpoints
    config_response["endpoints"] = {k: v for k, v in config_response["endpoints"].items() if v is not None}
    
    logger.info(f"Auth config requested for {environment} environment")
    return config_response

@router.post("/auth/refresh")
async def refresh_tokens_endpoint(request: Request) -> Dict[str, Any]:
    """Refresh token endpoint with flexible field name support"""
    try:
        # Parse request body manually to handle different field names
        try:
            body = await request.body()
            if not body:
                raise HTTPException(
                    status_code=422,
                    detail="Empty request body - refresh_token field is required"
                )
            
            body_data = json.loads(body.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in refresh request: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Invalid JSON body: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error parsing refresh request body: {e}")
            raise HTTPException(
                status_code=422,
                detail="Failed to parse request body"
            )
        
        # Extract refresh token from various possible field names
        refresh_token = None
        received_keys = list(body_data.keys()) if isinstance(body_data, dict) else []
        
        # Try different field name variations
        for field_name in ["refresh_token", "refreshToken", "token"]:
            if field_name in body_data:
                refresh_token = body_data[field_name]
                break
        
        if not refresh_token:
            error_detail = f"refresh_token field is required. received_keys: {received_keys}"
            logger.warning(f"Refresh token missing: {error_detail}")
            raise HTTPException(
                status_code=422,
                detail=error_detail
            )
        
        # Validate token format
        if not isinstance(refresh_token, str) or len(refresh_token.strip()) == 0:
            raise HTTPException(
                status_code=422,
                detail="refresh_token must be a non-empty string"
            )
        
        # Call auth service to refresh tokens
        try:
            result = await auth_service.refresh_tokens(refresh_token.strip())
        except Exception as e:
            logger.error(f"Auth service refresh_tokens failed: {e}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during token refresh"
            )
        
        if result is None:
            logger.warning(f"Invalid refresh token provided")
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
        
        access_token, new_refresh_token = result
        
        # Return new tokens
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": 900  # 15 minutes
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in refresh endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/auth/login")
async def login_endpoint(request: Request) -> Dict[str, Any]:
    """Login endpoint - authenticate user and return tokens"""
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        
        if not email or not password:
            raise HTTPException(
                status_code=422,
                detail="Email and password are required"
            )
        
        # Use auth service to authenticate
        result = await auth_service.authenticate_user(email, password)
        
        if not result:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        user_id, user_data = result
        
        # Generate tokens
        access_token = await auth_service.create_access_token(
            user_id=user_id,
            email=email
        )
        
        refresh_token = await auth_service.create_refresh_token(
            user_id=user_id,
            email=email
        )
        
        logger.info(f"Login successful for user: {email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,  # 15 minutes
            "user": {
                "id": user_id,
                "email": email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Authentication failed"
        )

@router.post("/auth/logout")
async def logout_endpoint(request: Request) -> Dict[str, Any]:
    """Logout endpoint - invalidate tokens"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Blacklist the token
            await auth_service.blacklist_token(token)
        
        return {
            "message": "Successfully logged out",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        # Logout should always succeed from client perspective
        return {
            "message": "Logged out",
            "status": "success"
        }

@router.post("/auth/register")
async def register_endpoint(request: Request) -> Dict[str, Any]:
    """Register a new user"""
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        name = body.get("name", "")
        
        if not email or not password:
            raise HTTPException(
                status_code=422,
                detail="Email and password are required"
            )
        
        # Create user using auth service
        user_id = await auth_service.create_user(email, password, name)
        
        if not user_id:
            raise HTTPException(
                status_code=409,
                detail="User already exists"
            )
        
        # Generate tokens for new user
        access_token = await auth_service.create_access_token(
            user_id=user_id,
            email=email
        )
        
        refresh_token = await auth_service.create_refresh_token(
            user_id=user_id,
            email=email
        )
        
        logger.info(f"User registered successfully: {email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,
            "user": {
                "id": user_id,
                "email": email,
                "name": name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Registration failed"
        )

@router.post("/auth/dev/login")
async def dev_login() -> Dict[str, Any]:
    """Development login endpoint - generates tokens for dev environment only"""
    # Check if we're in development environment
    from auth_service.auth_core.config import AuthConfig
    env = AuthConfig.get_environment()
    
    if env not in ["development", "test"]:
        logger.warning(f"Dev login attempted in {env} environment")
        raise HTTPException(
            status_code=403,
            detail="Dev login is only available in development environment"
        )
    
    # Generate development tokens
    try:
        # Create a dev user token with standard claims
        dev_user_id = "dev-user-001"
        dev_email = "dev@example.com"
        
        # Generate tokens using auth service
        access_token = await auth_service.create_access_token(
            user_id=dev_user_id,
            email=dev_email
        )
        
        refresh_token = await auth_service.create_refresh_token(
            user_id=dev_user_id,
            email=dev_email
        )
        
        logger.info(f"Dev login successful for environment: {env}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900  # 15 minutes
        }
        
    except Exception as e:
        logger.error(f"Dev login failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate development tokens"
        )

@router.post("/auth/service-token")
async def service_token_endpoint(request: Request) -> Dict[str, Any]:
    """Generate service-to-service authentication token"""
    try:
        body = await request.json()
        service_id = body.get("service_id")
        service_secret = body.get("service_secret")
        
        if not service_id or not service_secret:
            raise HTTPException(
                status_code=422,
                detail="Service ID and secret are required"
            )
        
        # Validate service credentials
        # In a real implementation, validate against configured services
        expected_secret = env.get("SERVICE_SECRET")
        if service_secret != expected_secret:
            raise HTTPException(
                status_code=401,
                detail="Invalid service credentials"
            )
        
        # Generate service token
        access_token = await auth_service.create_service_token(service_id)
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600  # 1 hour for service tokens
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service token generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate service token"
        )

@router.post("/auth/verify-password")
async def verify_password_endpoint(request: Request) -> Dict[str, Any]:
    """Verify a password hash"""
    try:
        body = await request.json()
        password = body.get("password")
        hash_value = body.get("hash")
        
        if not password or not hash_value:
            raise HTTPException(
                status_code=422,
                detail="Password and hash are required"
            )
        
        # Verify password
        is_valid = await auth_service.verify_password(password, hash_value)
        
        return {
            "valid": is_valid
        }
        
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Password verification failed"
        )

@router.post("/auth/hash-password")
async def hash_password_endpoint(request: Request) -> Dict[str, Any]:
    """Hash a password"""
    try:
        body = await request.json()
        password = body.get("password")
        
        if not password:
            raise HTTPException(
                status_code=422,
                detail="Password is required"
            )
        
        # Hash password
        hash_value = await auth_service.hash_password(password)
        
        return {
            "hash": hash_value
        }
        
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Password hashing failed"
        )

@router.post("/auth/create-token")
async def create_token_endpoint(request: Request) -> Dict[str, Any]:
    """Create a custom token"""
    try:
        body = await request.json()
        user_id = body.get("user_id")
        email = body.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=422,
                detail="User ID and email are required"
            )
        
        # Generate tokens
        access_token = await auth_service.create_access_token(
            user_id=user_id,
            email=email
        )
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 900
        }
        
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Token creation failed"
        )

@oauth_router.get("/oauth/providers")
async def oauth_providers() -> Dict[str, Any]:
    """Basic OAuth providers endpoint"""
    return {
        "providers": ["google"],
        "status": "configured",
        "timestamp": datetime.now(UTC).isoformat()
    }