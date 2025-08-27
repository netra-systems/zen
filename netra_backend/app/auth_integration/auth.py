"""
🔴 CRITICAL: Auth Integration Module - DO NOT IMPLEMENT AUTH LOGIC HERE

This module ONLY provides FastAPI dependency injection for authentication.
It connects to an EXTERNAL auth service via auth_client.

ARCHITECTURE:
- Auth Service: Separate microservice at AUTH_SERVICE_URL (e.g., http://localhost:8001)
- This Module: ONLY integration point - NO auth logic
- auth_client: HTTP client that calls the external auth service

⚠️ NEVER IMPLEMENT HERE:
- Token generation/validation logic
- Password hashing/verification (except legacy compatibility)
- OAuth provider integration
- User authentication logic

✅ ONLY DO HERE:
- Call auth_client methods
- FastAPI dependency injection
- Convert auth service responses to User objects

See: CRITICAL_AUTH_ARCHITECTURE.md for full details
"""
# Create auth-specific logger
import logging
from datetime import timedelta
from typing import Annotated, Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Initialize auth client instance
auth_client = AuthServiceClient()
from netra_backend.app.db.models_postgres import User
from netra_backend.app.database import get_db_session
from netra_backend.app.dependencies import get_db_dependency as get_db

logger = logging.getLogger('auth_integration.auth')

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Get current authenticated user from auth service
    """
    token = credentials.credentials
    
    # Validate token with auth service
    validation_result = await auth_client.validate_token_jwt(token)
    
    if not validation_result or not validation_result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_id = validation_result.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    import os

    from sqlalchemy import select
    
    # db is already an AsyncSession from the dependency injection
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        # In development mode, create and persist a dev user
        from netra_backend.app.config import get_config
        config = get_config()
        if config.environment == "development":
            from netra_backend.app.services.user_service import user_service
            
            # Use centralized dev user creation
            email = validation_result.get("email", "dev@example.com")
            user = await user_service.get_or_create_dev_user(db, email=email, user_id=user_id)
            logger.warning(f"Using dev user: {user.email}")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
    
    return user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

# Alias for compatibility
get_optional_current_user = get_current_user_optional
get_current_active_user = get_current_user

# Type annotations for dependency injection
ActiveUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[Optional[User], Depends(get_current_user_optional)]

# Permission-based dependencies
async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin permissions"""
    # Check both is_superuser, role, and legacy is_admin for admin permissions
    is_admin = (hasattr(user, 'is_superuser') and user.is_superuser) or \
               (hasattr(user, 'role') and user.role in ['admin', 'super_admin']) or \
               (hasattr(user, 'is_admin') and user.is_admin)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def require_developer(user: User = Depends(get_current_user)) -> User:
    """Require developer permissions"""
    if not hasattr(user, 'is_developer') or not user.is_developer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer access required"
        )
    return user

AdminDep = Annotated[User, Depends(require_admin)]
DeveloperDep = Annotated[User, Depends(require_developer)]

def require_permission(permission: str):
    """Create a dependency that requires a specific permission"""
    async def check_permission(user: User = Depends(get_current_user)) -> User:
        _validate_user_permission(user, permission)
        return user
    return check_permission

def _validate_user_permission(user: User, permission: str) -> None:
    """Validate that user has the required permission."""
    if hasattr(user, 'permissions') and user.permissions is not None:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )

# NOTE: All JWT and password hashing logic has been moved to the auth service
# This module ONLY handles FastAPI dependency injection
# See auth_service for actual authentication implementation

# Compatibility aliases for deprecated dependencies
ActiveUserWsDep = Annotated[User, Depends(get_current_user)]

# Backward compatibility stubs - These are deprecated and should not be used
# They exist only to prevent import errors during migration
def get_password_hash(password: str) -> str:
    """DEPRECATED: Use auth service instead"""
    logger.warning("get_password_hash is deprecated - use auth service")
    return ""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """DEPRECATED: Use auth service instead"""
    logger.warning("verify_password is deprecated - use auth service")
    return False

def _check_password_rehash_needed(hashed_password: str) -> bool:
    """DEPRECATED: Use auth service instead"""
    logger.warning("_check_password_rehash_needed is deprecated - use auth service")
    return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """DEPRECATED: Use auth service instead"""
    logger.warning("create_access_token is deprecated - use auth service")
    return ""

def validate_token_jwt(token: str) -> Optional[Dict]:
    """DEPRECATED: Use auth service instead"""
    logger.warning("validate_token_jwt is deprecated - use auth service")
    return None

# Backward compatibility for token_manager imports
from dataclasses import dataclass


@dataclass
class TokenClaims:
    """DEPRECATED: Compatibility stub for token_manager.TokenClaims"""
    user_id: str
    email: str
    environment: str
    iat: int
    exp: int
    jti: str
    pr_number: Optional[str] = None

class JWTTokenManager:
    """DEPRECATED: Compatibility stub for token_manager.JWTTokenManager"""
    def __init__(self):
        logger.warning("JWTTokenManager is deprecated - use auth service")
        self.algorithm = "HS256"
        self.expiration_hours = 1
        self.config = None
        self.redis_manager = None

# Backward compatibility for pr_router imports
def build_pr_redirect_url(pr_number: str, base_path: str = "/") -> str:
    """DEPRECATED: Compatibility stub for pr_router.build_pr_redirect_url"""
    logger.warning("build_pr_redirect_url is deprecated - use auth service")
    pr_domain = f"https://pr-{pr_number}.staging.netrasystems.ai"
    return f"{pr_domain}{base_path}"

def handle_pr_routing_error(error: Exception) -> Dict:
    """DEPRECATED: Compatibility stub for pr_router.handle_pr_routing_error"""
    logger.warning("handle_pr_routing_error is deprecated - use auth service")
    return {"error": str(error)}

def get_pr_environment_status(pr_number: str) -> Dict:
    """DEPRECATED: Compatibility stub for pr_router.get_pr_environment_status"""
    logger.warning("get_pr_environment_status is deprecated - use auth service")
    return {"pr_number": pr_number, "status": "unknown"}

def extract_pr_number_from_request(request_headers: Dict[str, str]) -> Optional[str]:
    """DEPRECATED: Compatibility stub for pr_router.extract_pr_number_from_request"""
    logger.warning("extract_pr_number_from_request is deprecated - use auth service")
    return None

def extract_pr_from_host(host: str) -> Optional[str]:
    """DEPRECATED: Compatibility stub for pr_router.extract_pr_from_host"""
    logger.warning("extract_pr_from_host is deprecated - use auth service")
    import re
    pr_pattern = r"pr-(\d+)(?:-api)?\.staging\.netrasystems\.ai"
    match = re.search(pr_pattern, host)
    return match.group(1) if match else None

async def route_pr_authentication(pr_number: str, auth_code: str) -> Dict:
    """DEPRECATED: Compatibility stub for pr_router.route_pr_authentication"""
    logger.warning("route_pr_authentication is deprecated - use auth service")
    return {"pr_number": pr_number, "authenticated": False}

# PR_STATE_TTL constant for compatibility
PR_STATE_TTL = 3600

# Additional pr_router compatibility stubs
def _build_pr_state_data(pr_number: str, csrf_token: str) -> Dict:
    """DEPRECATED: Compatibility stub for pr_router._build_pr_state_data"""
    logger.warning("_build_pr_state_data is deprecated - use auth service")
    import time
    return {"pr_number": pr_number, "csrf_token": csrf_token, "timestamp": time.time()}

def _encode_state_to_base64(state_data: Dict) -> str:
    """DEPRECATED: Compatibility stub for pr_router._encode_state_to_base64"""
    logger.warning("_encode_state_to_base64 is deprecated - use auth service")
    import base64
    import json
    return base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

def _decode_state_from_base64(state_string: str) -> Dict:
    """DEPRECATED: Compatibility stub for pr_router._decode_state_from_base64"""
    logger.warning("_decode_state_from_base64 is deprecated - use auth service")
    import base64
    import json
    return json.loads(base64.urlsafe_b64decode(state_string))

def _validate_state_timestamp(timestamp: float) -> None:
    """DEPRECATED: Compatibility stub for pr_router._validate_state_timestamp"""
    logger.warning("_validate_state_timestamp is deprecated - use auth service")
    import time
    if time.time() - timestamp > PR_STATE_TTL:
        raise ValueError("State expired")

async def _validate_and_consume_csrf_token(csrf_token: str, redis_manager: Any) -> None:
    """DEPRECATED: Compatibility stub for pr_router._validate_and_consume_csrf_token"""
    logger.warning("_validate_and_consume_csrf_token is deprecated - use auth service")
    pass

async def _store_csrf_token_in_redis(csrf_token: str, redis_manager: Any) -> None:
    """DEPRECATED: Compatibility stub for pr_router._store_csrf_token_in_redis"""
    logger.warning("_store_csrf_token_in_redis is deprecated - use auth service")
    pass

# Additional security validation stubs for pr_router
def _validate_pr_inputs(pr_number: str, return_url: Optional[str] = None) -> None:
    """DEPRECATED: Compatibility stub for pr_router._validate_pr_inputs"""
    logger.warning("_validate_pr_inputs is deprecated - use auth service")
    pass

def _validate_pr_number_format(pr_number: str) -> None:
    """DEPRECATED: Compatibility stub for pr_router._validate_pr_number_format"""
    logger.warning("_validate_pr_number_format is deprecated - use auth service")
    if not pr_number or not pr_number.isdigit():
        raise ValueError("Invalid PR number format")

async def _validate_pr_with_github(pr_number: str, github_client: Any) -> None:
    """DEPRECATED: Compatibility stub for pr_router._validate_pr_with_github"""
    logger.warning("_validate_pr_with_github is deprecated - use auth service")
    pass

def _is_valid_url(url: str) -> bool:
    """DEPRECATED: Compatibility stub for pr_router._is_valid_url"""
    logger.warning("_is_valid_url is deprecated - use auth service")
    return url.startswith(("http://", "https://"))

def _is_allowed_return_domain(domain: str) -> bool:
    """DEPRECATED: Compatibility stub for pr_router._is_allowed_return_domain"""
    logger.warning("_is_allowed_return_domain is deprecated - use auth service")
    allowed_domains = ["staging.netrasystems.ai", "localhost", "127.0.0.1"]
    return any(domain.endswith(allowed) for allowed in allowed_domains)