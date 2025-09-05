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

# Import MockAuthService for testing
from auth_service.test_framework.mock_auth_service import MockAuthService

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

@oauth_router.get("/oauth/providers")
async def oauth_providers() -> Dict[str, Any]:
    """Basic OAuth providers endpoint"""
    return {
        "providers": ["google"],
        "status": "configured",
        "timestamp": datetime.now(UTC).isoformat()
    }