"""
Service-to-Service Authentication API - Phase 1 JWT SSOT Remediation
Secure authentication mechanisms for backend → auth service calls
Handles service tokens, API keys, and request signing/verification
"""
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env
# SSOT: Import SERVICE_ID constant for service registry
from shared.constants.service_identifiers import SERVICE_ID

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/service", tags=["Service Authentication"])

# Global JWT handler instance
jwt_handler = JWTHandler()

# Security scheme
security = HTTPBearer()

# Request/Response Models
class ServiceAuthRequest(BaseModel):
    """Request model for service authentication"""
    service_id: str = Field(..., description="Service identifier")
    service_secret: str = Field(..., description="Service secret key")
    requested_permissions: Optional[list] = Field(None, description="Requested permissions")
    token_duration_minutes: Optional[int] = Field(60, description="Token duration in minutes")

class ServiceAuthResponse(BaseModel):
    """Response model for service authentication"""
    authenticated: bool = Field(..., description="Whether authentication succeeded")
    service_token: Optional[str] = Field(None, description="Generated service token")
    service_id: Optional[str] = Field(None, description="Authenticated service ID")
    permissions: Optional[list] = Field(None, description="Granted permissions")
    expires_at: Optional[str] = Field(None, description="Token expiration timestamp")
    error: Optional[str] = Field(None, description="Error message if authentication failed")

class RequestSignatureRequest(BaseModel):
    """Request model for request signing"""
    service_id: str = Field(..., description="Service identifier")
    request_method: str = Field(..., description="HTTP method")
    request_path: str = Field(..., description="Request path")
    request_body: Optional[str] = Field(None, description="Request body (if any)")
    timestamp: Optional[str] = Field(None, description="Request timestamp")

class RequestSignatureResponse(BaseModel):
    """Response model for request signing"""
    signature: str = Field(..., description="Generated request signature")
    timestamp: str = Field(..., description="Request timestamp")
    algorithm: str = Field(..., description="Signature algorithm")
    headers: Dict[str, str] = Field(..., description="Headers to include in request")

class ServiceValidationRequest(BaseModel):
    """Request model for service validation"""
    service_id: str = Field(..., description="Service identifier")
    signature: str = Field(..., description="Request signature")
    timestamp: str = Field(..., description="Request timestamp")
    request_method: str = Field(..., description="HTTP method")
    request_path: str = Field(..., description="Request path")
    request_body: Optional[str] = Field(None, description="Request body")

class ServiceValidationResponse(BaseModel):
    """Response model for service validation"""
    valid: bool = Field(..., description="Whether service request is valid")
    service_id: Optional[str] = Field(None, description="Validated service ID")
    permissions: Optional[list] = Field(None, description="Service permissions")
    error: Optional[str] = Field(None, description="Error message if validation failed")

# Service registry (in production, this would be in database)
SERVICE_REGISTRY = {
    SERVICE_ID: {
        "name": "Netra Backend Service", 
        "permissions": ["jwt_validation", "websocket_auth", "user_management"],
        "rate_limit": 1000  # requests per minute
    },
    "netra-websocket": {
        "name": "Netra WebSocket Service",
        "permissions": ["jwt_validation", "websocket_auth"],
        "rate_limit": 500
    },
    "netra-admin": {
        "name": "Netra Admin Service",
        "permissions": ["jwt_validation", "user_management", "admin"],
        "rate_limit": 100
    }
}

@router.post("/authenticate", response_model=ServiceAuthResponse)
async def authenticate_service(request: ServiceAuthRequest) -> Dict[str, Any]:
    """
    Authenticate service and generate service token
    
    Validates service credentials and issues a service token for API access.
    """
    try:
        # Log authentication attempt
        logger.info(f"Service authentication request from: {request.service_id}")
        
        # Validate service exists in registry
        if request.service_id not in SERVICE_REGISTRY:
            logger.warning(f"Unknown service ID: {request.service_id}")
            return {
                "authenticated": False,
                "error": "unknown_service_id"
            }
        
        # Get expected service secret from environment
        expected_secret = get_env().get("SERVICE_SECRET", "")
        
        # In development, allow fallback secret
        if not expected_secret:
            environment = AuthConfig.get_environment()
            if environment in ["development", "test"]:
                expected_secret = "dev-service-secret-not-for-production"
                logger.warning(f"Using development service secret for {environment}")
            else:
                logger.error("SERVICE_SECRET not configured for production environment")
                return {
                    "authenticated": False,
                    "error": "service_secret_not_configured"
                }
        
        # Validate service secret
        if request.service_secret != expected_secret:
            logger.warning(f"Invalid service secret for service: {request.service_id}")
            return {
                "authenticated": False,
                "error": "invalid_service_secret"
            }
        
        # Get service configuration
        service_config = SERVICE_REGISTRY[request.service_id]
        
        # Determine granted permissions
        available_permissions = service_config["permissions"]
        if request.requested_permissions:
            # Grant only requested permissions that service is allowed to have
            granted_permissions = [p for p in request.requested_permissions if p in available_permissions]
        else:
            # Grant all available permissions
            granted_permissions = available_permissions
        
        # Generate service token
        token_duration = min(request.token_duration_minutes or 60, 480)  # Max 8 hours
        service_token = jwt_handler.create_service_token(
            service_id=request.service_id,
            service_name=service_config["name"]
        )
        
        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=token_duration)
        
        logger.info(f"Service authentication successful for: {request.service_id}")
        
        return {
            "authenticated": True,
            "service_token": service_token,
            "service_id": request.service_id,
            "permissions": granted_permissions,
            "expires_at": expires_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Service authentication error: {e}")
        return {
            "authenticated": False,
            "error": "authentication_error"
        }

@router.post("/sign-request", response_model=RequestSignatureResponse)
async def sign_service_request(request: RequestSignatureRequest) -> Dict[str, Any]:
    """
    Generate request signature for service-to-service calls
    
    Creates HMAC signature for request authentication and integrity.
    """
    try:
        # Validate service exists
        if request.service_id not in SERVICE_REGISTRY:
            raise HTTPException(status_code=400, detail="Unknown service ID")
        
        # Get service secret
        service_secret = get_env().get("SERVICE_SECRET", "")
        if not service_secret:
            environment = AuthConfig.get_environment()
            if environment in ["development", "test"]:
                service_secret = "dev-service-secret-not-for-production"
            else:
                raise HTTPException(status_code=500, detail="Service secret not configured")
        
        # Generate timestamp if not provided
        timestamp = request.timestamp or datetime.now(timezone.utc).isoformat()
        
        # Create signature data
        signature_data = _create_signature_data(
            request.service_id,
            request.request_method,
            request.request_path,
            request.request_body or "",
            timestamp
        )
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            service_secret.encode('utf-8'),
            signature_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Prepare headers for the request
        headers = {
            "X-Service-ID": request.service_id,
            "X-Service-Signature": signature,
            "X-Service-Timestamp": timestamp,
            "X-Service-Algorithm": "HMAC-SHA256"
        }
        
        logger.debug(f"Request signature generated for service: {request.service_id}")
        
        return {
            "signature": signature,
            "timestamp": timestamp,
            "algorithm": "HMAC-SHA256",
            "headers": headers
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request signing error: {e}")
        raise HTTPException(status_code=500, detail="Request signing failed")

@router.post("/validate-request", response_model=ServiceValidationResponse)
async def validate_service_request(request: ServiceValidationRequest) -> Dict[str, Any]:
    """
    Validate signed service request
    
    Verifies request signature and service authentication.
    """
    try:
        # Validate service exists
        if request.service_id not in SERVICE_REGISTRY:
            return {
                "valid": False,
                "error": "unknown_service_id"
            }
        
        # Get service secret
        service_secret = get_env().get("SERVICE_SECRET", "")
        if not service_secret:
            environment = AuthConfig.get_environment()
            if environment in ["development", "test"]:
                service_secret = "dev-service-secret-not-for-production"
            else:
                return {
                    "valid": False,
                    "error": "service_secret_not_configured"
                }
        
        # Check timestamp freshness (prevent replay attacks)
        try:
            request_time = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            time_diff = abs((current_time - request_time).total_seconds())
            
            if time_diff > 300:  # 5 minutes tolerance
                return {
                    "valid": False,
                    "error": "request_timestamp_too_old"
                }
        except Exception as e:
            logger.warning(f"Timestamp validation error: {e}")
            return {
                "valid": False,
                "error": "invalid_timestamp_format"
            }
        
        # Recreate signature data
        signature_data = _create_signature_data(
            request.service_id,
            request.request_method,
            request.request_path,
            request.request_body or "",
            request.timestamp
        )
        
        # Generate expected signature
        expected_signature = hmac.new(
            service_secret.encode('utf-8'),
            signature_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Verify signature using secure comparison
        if not hmac.compare_digest(request.signature, expected_signature):
            logger.warning(f"Invalid signature for service: {request.service_id}")
            return {
                "valid": False,
                "error": "invalid_signature"
            }
        
        # Get service permissions
        service_config = SERVICE_REGISTRY[request.service_id]
        
        logger.debug(f"Service request validation successful for: {request.service_id}")
        
        return {
            "valid": True,
            "service_id": request.service_id,
            "permissions": service_config["permissions"]
        }
        
    except Exception as e:
        logger.error(f"Service request validation error: {e}")
        return {
            "valid": False,
            "error": "validation_error"
        }

def _create_signature_data(service_id: str, method: str, path: str, body: str, timestamp: str) -> str:
    """
    Create canonical signature data for HMAC signing
    """
    # Canonical format for signature data
    return f"{service_id}:{method.upper()}:{path}:{body}:{timestamp}"

@router.post("/validate-service-token")
async def validate_service_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Validate service token from Authorization header
    
    Used by protected endpoints to verify service authentication.
    """
    try:
        token = credentials.credentials
        
        # Validate token using JWT handler
        payload = jwt_handler.validate_token(token, "service")
        
        if payload:
            service_id = payload.get("sub")
            service_name = payload.get("service")
            
            # Check if service exists in registry
            if service_id in SERVICE_REGISTRY:
                service_config = SERVICE_REGISTRY[service_id]
                
                return {
                    "valid": True,
                    "service_id": service_id,
                    "service_name": service_name,
                    "permissions": service_config["permissions"]
                }
            else:
                return {
                    "valid": False,
                    "error": "service_not_in_registry"
                }
        else:
            return {
                "valid": False,
                "error": "invalid_or_expired_token"
            }
            
    except Exception as e:
        logger.error(f"Service token validation error: {e}")
        return {
            "valid": False,
            "error": "token_validation_error"
        }

@router.get("/registry")
async def get_service_registry(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Get service registry information
    
    Requires valid service token. Returns available services and permissions.
    """
    try:
        # Validate service token
        validation_result = await validate_service_token(credentials)
        
        if not validation_result.get("valid"):
            raise HTTPException(status_code=401, detail="Invalid service token")
        
        # Return public registry information (without secrets)
        public_registry = {}
        for service_id, config in SERVICE_REGISTRY.items():
            public_registry[service_id] = {
                "name": config["name"],
                "permissions": config["permissions"],
                "rate_limit": config["rate_limit"]
            }
        
        return {
            "services": public_registry,
            "total_services": len(SERVICE_REGISTRY),
            "requesting_service": validation_result.get("service_id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service registry error: {e}")
        raise HTTPException(status_code=500, detail="Registry access failed")

@router.post("/revoke-token")
async def revoke_service_token(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Revoke service token
    
    Adds token to blacklist for immediate invalidation.
    """
    try:
        # Validate service token first
        validation_result = await validate_service_token(credentials)
        
        if not validation_result.get("valid"):
            raise HTTPException(status_code=401, detail="Invalid service token")
        
        # Blacklist the token
        token = credentials.credentials
        success = jwt_handler.blacklist_token(token)
        
        if success:
            logger.info(f"Service token revoked for service: {validation_result.get('service_id')}")
            return {
                "revoked": True,
                "service_id": validation_result.get("service_id"),
                "revocation_timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "revoked": False,
                "error": "revocation_failed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token revocation error: {e}")
        raise HTTPException(status_code=500, detail="Token revocation failed")

@router.get("/health")
async def service_auth_health() -> Dict[str, Any]:
    """
    Health check for service authentication
    """
    try:
        # Test service authentication flow
        test_service_id = SERVICE_ID
        test_secret = get_env().get("SERVICE_SECRET", "")
        
        if not test_secret:
            environment = AuthConfig.get_environment()
            if environment in ["development", "test"]:
                test_secret = "dev-service-secret-not-for-production"
            else:
                return {
                    "status": "unhealthy",
                    "service": "service-authentication",
                    "error": "service_secret_not_configured"
                }
        
        # Test authentication
        auth_request = ServiceAuthRequest(
            service_id=test_service_id,
            service_secret=test_secret,
            token_duration_minutes=1
        )
        
        auth_result = await authenticate_service(auth_request)
        
        if auth_result.get("authenticated"):
            health_status = "healthy"
        else:
            health_status = "unhealthy"
        
        return {
            "status": health_status,
            "service": "service-authentication",
            "test_result": auth_result.get("authenticated", False),
            "environment": AuthConfig.get_environment(),
            "services_registered": len(SERVICE_REGISTRY),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Service auth health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "service-authentication",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }