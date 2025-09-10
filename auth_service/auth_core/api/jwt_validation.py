"""
JWT Validation API - Phase 1 JWT SSOT Remediation
Centralized JWT validation APIs for backend and WebSocket services
Enables auth service to be the single source of truth for ALL JWT operations
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
router = APIRouter(prefix="/api/v1/jwt", tags=["JWT Validation"])

# Global JWT handler instance
jwt_handler = JWTHandler()

# Request/Response Models
class JWTValidationRequest(BaseModel):
    """Request model for JWT validation"""
    token: str = Field(..., description="JWT token to validate")
    token_type: str = Field(default="access", description="Type of token (access, refresh, service)")
    include_user_context: bool = Field(default=True, description="Include user context in response")
    validate_for_consumption: bool = Field(default=False, description="Validate for token consumption (with replay protection)")

class JWTValidationResponse(BaseModel):
    """Response model for JWT validation"""
    valid: bool = Field(..., description="Whether the token is valid")
    user_id: Optional[str] = Field(None, description="User ID from token")
    email: Optional[str] = Field(None, description="User email from token")
    permissions: Optional[list] = Field(None, description="User permissions")
    expires_at: Optional[str] = Field(None, description="Token expiration timestamp")
    issued_at: Optional[str] = Field(None, description="Token issued timestamp")
    token_type: Optional[str] = Field(None, description="Type of token")
    service_signature: Optional[str] = Field(None, description="Service authentication signature")
    error: Optional[str] = Field(None, description="Error message if validation failed")
    validation_timestamp: str = Field(..., description="When validation occurred")

class WebSocketAuthRequest(BaseModel):
    """Request model for WebSocket authentication"""
    authorization_header: Optional[str] = Field(None, description="Authorization header from WebSocket")
    subprotocol_token: Optional[str] = Field(None, description="Token from Sec-WebSocket-Protocol header")
    demo_mode: bool = Field(default=False, description="Enable demo mode for isolated environments")
    user_context_required: bool = Field(default=True, description="Whether user execution context is required")

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

@router.post("/validate", response_model=JWTValidationResponse)
async def validate_jwt_token(request: JWTValidationRequest) -> Dict[str, Any]:
    """
    Validate JWT token for other services (backend, WebSocket)
    
    This is the central JWT validation endpoint that replaces backend JWT logic.
    Supports both validation and consumption operations with replay protection.
    
    Returns:
        JWTValidationResponse: Validation result with user context
    """
    validation_start = time.time()
    
    try:
        # Log validation request for debugging
        logger.info(f"JWT validation request: token_type={request.token_type}, "
                   f"consumption={request.validate_for_consumption}, "
                   f"include_context={request.include_user_context}")
        
        # Validate token using appropriate method
        if request.validate_for_consumption:
            # Use consumption validation with replay protection
            payload = jwt_handler.validate_token_for_consumption(
                request.token, 
                request.token_type
            )
        else:
            # Use standard validation (most common case)
            payload = jwt_handler.validate_token(
                request.token, 
                request.token_type
            )
        
        validation_time = (time.time() - validation_start) * 1000  # Convert to ms
        
        if payload is None:
            logger.warning(f"JWT validation failed in {validation_time:.2f}ms")
            return {
                "valid": False,
                "error": "invalid_or_expired_token",
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Build response with user context
        response_data = {
            "valid": True,
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Include user context if requested
        if request.include_user_context:
            response_data.update({
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "permissions": payload.get("permissions", []),
                "token_type": payload.get("token_type"),
                "service_signature": payload.get("service_signature")
            })
            
            # Add timestamp fields
            if payload.get("exp"):
                response_data["expires_at"] = datetime.fromtimestamp(
                    payload["exp"], timezone.utc
                ).isoformat()
            
            if payload.get("iat"):
                response_data["issued_at"] = datetime.fromtimestamp(
                    payload["iat"], timezone.utc
                ).isoformat()
        
        logger.info(f"JWT validation successful for user {payload.get('sub')} in {validation_time:.2f}ms")
        return response_data
        
    except Exception as e:
        validation_time = (time.time() - validation_start) * 1000
        logger.error(f"JWT validation error in {validation_time:.2f}ms: {e}")
        return {
            "valid": False,
            "error": "validation_error",
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.post("/validate-batch")
async def validate_jwt_tokens_batch(request: Request) -> Dict[str, Any]:
    """
    Validate multiple JWT tokens in a single request for performance
    
    Useful for services that need to validate multiple tokens efficiently.
    """
    try:
        body = await request.json()
        tokens = body.get("tokens", [])
        token_type = body.get("token_type", "access")
        include_user_context = body.get("include_user_context", True)
        
        if not tokens or not isinstance(tokens, list):
            return {
                "valid_count": 0,
                "invalid_count": 0,
                "results": [],
                "error": "tokens_array_required"
            }
        
        if len(tokens) > 100:  # Rate limiting
            return {
                "valid_count": 0,
                "invalid_count": 0,
                "results": [],
                "error": "too_many_tokens_max_100"
            }
        
        results = []
        valid_count = 0
        invalid_count = 0
        
        for i, token in enumerate(tokens):
            try:
                # Create individual validation request
                validation_request = JWTValidationRequest(
                    token=token,
                    token_type=token_type,
                    include_user_context=include_user_context
                )
                
                # Validate using individual endpoint logic
                result = await validate_jwt_token(validation_request)
                result["token_index"] = i
                
                if result.get("valid"):
                    valid_count += 1
                else:
                    invalid_count += 1
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Batch validation error for token {i}: {e}")
                results.append({
                    "valid": False,
                    "error": "individual_validation_error",
                    "token_index": i,
                    "validation_timestamp": datetime.now(timezone.utc).isoformat()
                })
                invalid_count += 1
        
        logger.info(f"Batch validation completed: {valid_count} valid, {invalid_count} invalid")
        
        return {
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "total_processed": len(tokens),
            "results": results,
            "batch_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch validation error: {e}")
        return {
            "valid_count": 0,
            "invalid_count": 0,
            "results": [],
            "error": "batch_processing_error"
        }

@router.post("/extract-user-id")
async def extract_user_id_from_token(request: Request) -> Dict[str, Any]:
    """
    Extract user ID from token without full validation
    
    Useful for logging, routing, and other operations that need user ID
    but don't require full token validation.
    """
    try:
        body = await request.json()
        token = body.get("token")
        
        if not token:
            return {
                "success": False,
                "error": "token_required"
            }
        
        user_id = jwt_handler.extract_user_id(token)
        
        if user_id:
            return {
                "success": True,
                "user_id": user_id,
                "extraction_timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "success": False,
                "error": "user_id_extraction_failed"
            }
            
    except Exception as e:
        logger.error(f"User ID extraction error: {e}")
        return {
            "success": False,
            "error": "extraction_error"
        }

@router.get("/performance-stats")
async def get_jwt_performance_stats() -> Dict[str, Any]:
    """
    Get JWT validation performance statistics
    
    Useful for monitoring and optimization.
    """
    try:
        stats = jwt_handler.get_performance_stats()
        
        return {
            "performance_stats": stats,
            "service_info": {
                "environment": AuthConfig.get_environment(),
                "service_id": AuthConfig.get_service_id(),
                "jwt_algorithm": AuthConfig.get_jwt_algorithm()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Performance stats error: {e}")
        return {
            "error": "stats_unavailable",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.post("/check-blacklist")
async def check_token_blacklist(request: Request) -> Dict[str, Any]:
    """
    Check if a token is blacklisted
    
    Separate endpoint for blacklist checking to support caching strategies.
    """
    try:
        body = await request.json()
        token = body.get("token")
        
        if not token:
            return {
                "blacklisted": False,
                "error": "token_required"
            }
        
        is_blacklisted = jwt_handler.is_token_blacklisted(token)
        
        return {
            "blacklisted": is_blacklisted,
            "check_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Blacklist check error: {e}")
        return {
            "blacklisted": False,
            "error": "blacklist_check_error"
        }

@router.post("/blacklist-token")
async def blacklist_token_endpoint(request: Request) -> Dict[str, Any]:
    """
    Add token to blacklist for immediate invalidation
    
    Requires service authentication.
    """
    try:
        body = await request.json()
        token = body.get("token")
        
        if not token:
            return {
                "success": False,
                "error": "token_required"
            }
        
        # TODO: Add service authentication check
        
        success = jwt_handler.blacklist_token(token)
        
        return {
            "success": success,
            "blacklist_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Token blacklist error: {e}")
        return {
            "success": False,
            "error": "blacklist_error"
        }

@router.get("/health")
async def jwt_validation_health() -> Dict[str, Any]:
    """
    Health check for JWT validation service
    
    Returns service status and performance metrics.
    """
    try:
        # Test JWT validation functionality
        test_user_id = "health-check-user"
        test_email = "health@example.com"
        
        # Create test token
        test_token = jwt_handler.create_access_token(test_user_id, test_email)
        
        # Validate test token
        validation_start = time.time()
        payload = jwt_handler.validate_token(test_token, "access")
        validation_time = (time.time() - validation_start) * 1000
        
        if payload and payload.get("sub") == test_user_id:
            health_status = "healthy"
        else:
            health_status = "unhealthy"
            
        # Get performance stats
        stats = jwt_handler.get_performance_stats()
        
        return {
            "status": health_status,
            "service": "jwt-validation",
            "validation_time_ms": round(validation_time, 2),
            "performance_stats": stats,
            "environment": AuthConfig.get_environment(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"JWT validation health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "jwt-validation",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }