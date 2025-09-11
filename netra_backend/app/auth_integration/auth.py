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
import time
from datetime import timedelta
from typing import Annotated, Dict, Optional, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Initialize auth client instance
auth_client = AuthServiceClient()
from netra_backend.app.db.models_postgres import User
from netra_backend.app.dependencies import get_request_scoped_db_session as get_db

# Note: Password hashing is handled by the auth service, not directly here


logger = logging.getLogger('auth_integration.auth')

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from auth service with JWT claims validation."""
    token = credentials.credentials
    validation_result = await _validate_token_with_auth_service(token)
    user = await _get_user_from_database(db, validation_result)
    
    # SECURITY: Store JWT validation result on user object for admin functions
    if hasattr(user, '__dict__'):
        user._jwt_validation_result = validation_result
    
    return user

async def _validate_token_with_auth_service(token: str) -> Dict[str, str]:
    """Validate token with auth service and extract all claims with comprehensive service dependency logging."""
    start_time = time.time()
    logger.critical(f"🔑 AUTH SERVICE DEPENDENCY: Starting token validation "
                   f"(token_length: {len(token) if token else 0}, "
                   f"auth_service_endpoint: {auth_client.settings.base_url}, "
                   f"service_timeout: 30s)")
    
    try:
        validation_result = await auth_client.validate_token_jwt(token)
        response_time = (time.time() - start_time) * 1000
        
        if not validation_result or not validation_result.get("valid"):
            logger.critical(f"🚨 AUTH SERVICE FAILURE: Token validation failed at auth service "
                           f"(response_time: {response_time:.2f}ms, "
                           f"result: {validation_result}, "
                           f"service_status: auth_service_responded_but_invalid, "
                           f"golden_path_impact: CRITICAL - User authentication blocked)")
            logger.warning("Token validation failed - invalid or expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not validation_result.get("user_id"):
            logger.critical(f"🚨 AUTH SERVICE FAILURE: Token validation failed - no user_id in payload "
                           f"(response_time: {response_time:.2f}ms, "
                           f"payload_keys: {list(validation_result.keys()) if validation_result else 'none'}, "
                           f"service_status: auth_service_invalid_response, "
                           f"golden_path_impact: CRITICAL - User identification failed)")
            logger.warning("Token validation failed - no user_id in payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # Log successful token validation with key claims info
        user_id = validation_result.get('user_id', 'unknown')
        logger.info(f"✅ AUTH SERVICE SUCCESS: Token validated successfully "
                   f"(user_id: {user_id[:8]}..., "
                   f"role: {validation_result.get('role', 'none')}, "
                   f"response_time: {response_time:.2f}ms, "
                   f"service_status: auth_service_healthy, "
                   f"golden_path_status: user_authenticated)")
        logger.debug(
            f"Token validated successfully for user {validation_result.get('user_id', 'unknown')[:8]}... "
            f"with role: {validation_result.get('role', 'none')} "
            f"and permissions: {validation_result.get('permissions', [])}"
        )
        
        return validation_result
        
    except HTTPException:
        # Re-raise HTTP exceptions (these are expected auth failures)
        raise
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.critical(f"🚨 AUTH SERVICE EXCEPTION: Auth service communication failed "
                       f"(exception_type: {type(e).__name__}, "
                       f"exception_message: {str(e)}, "
                       f"response_time: {response_time:.2f}ms, "
                       f"service_status: auth_service_unreachable, "
                       f"golden_path_impact: CRITICAL - All authentication blocked, "
                       f"dependent_services: ['websocket_service', 'supervisor_service', 'thread_service'], "
                       f"recovery_action: Check auth service health and connectivity)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )


async def _get_user_from_database(db: AsyncSession, validation_result: Dict[str, str]) -> User:
    """Get or create user from database with JWT claims synchronization and comprehensive service dependency logging."""
    from sqlalchemy import select
    from shared.database.session_validation import validate_db_session
    
    start_time = time.time()
    user_id = validation_result.get("user_id")
    
    logger.info(f"🔍 DATABASE SERVICE DEPENDENCY: Starting user lookup "
               f"(user_id: {user_id[:8]}..., "
               f"db_session_type: {type(db).__name__}, "
               f"dependent_service: database)")
    
    try:
        # Validate database session (handles both production and test scenarios)
        validate_db_session(db, "get_user_from_database")
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        db_response_time = (time.time() - start_time) * 1000
        
        if not user:
            logger.warning(f"🔑 DATABASE USER AUTO-CREATE: User {user_id[:8]}... not found in database "
                          f"(response_time: {db_response_time:.2f}ms, "
                          f"service_status: database_healthy_but_user_missing, "
                          f"action: auto-creating from JWT claims)")
            user = await _auto_create_user_if_needed(db, validation_result)
        else:
            logger.info(f"✅ DATABASE USER FOUND: User {user_id[:8]}... exists in database "
                       f"(response_time: {db_response_time:.2f}ms, "
                       f"service_status: database_healthy, "
                       f"action: syncing JWT claims)")
            # SECURITY: Sync JWT role/permissions with database if needed
            await _sync_jwt_claims_to_user_record(user, validation_result, db)
        
        return user
        
    except Exception as e:
        db_response_time = (time.time() - start_time) * 1000
        logger.critical(f"🚨 DATABASE SERVICE FAILURE: User database lookup failed "
                       f"(user_id: {user_id[:8]}..., "
                       f"exception_type: {type(e).__name__}, "
                       f"exception_message: {str(e)}, "
                       f"response_time: {db_response_time:.2f}ms, "
                       f"service_status: database_unreachable, "
                       f"golden_path_impact: CRITICAL - User authentication cannot complete, "
                       f"dependent_services: ['auth_integration', 'websocket_service'], "
                       f"recovery_action: Check database connectivity and session pool)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable",
        )

async def _sync_jwt_claims_to_user_record(user: User, validation_result: Dict[str, str], db: AsyncSession) -> None:
    """Synchronize JWT claims with user database record for consistency.
    
    This ensures that the database record reflects the authoritative JWT claims,
    preventing privilege escalation through database manipulation.
    """
    try:
        jwt_role = validation_result.get("role", "standard_user")
        jwt_permissions = validation_result.get("permissions", [])
        
        # Check if user record needs updating
        needs_update = False
        
        # Sync role from JWT if different
        if hasattr(user, 'role') and user.role != jwt_role:
            logger.info(f"Syncing role from JWT: {user.role} -> {jwt_role} for user {user.id[:8]}...")
            user.role = jwt_role
            needs_update = True
        
        # Sync admin status from JWT role/permissions
        jwt_is_admin = (
            jwt_role in ["admin", "super_admin"] or
            "admin" in jwt_permissions or
            "system:*" in jwt_permissions
        )
        
        if hasattr(user, 'is_superuser') and bool(user.is_superuser) != jwt_is_admin:
            logger.info(f"Syncing admin status from JWT: {user.is_superuser} -> {jwt_is_admin} for user {user.id[:8]}...")
            user.is_superuser = jwt_is_admin
            needs_update = True
        
        if needs_update:
            await db.commit()
            logger.warning(f"🔄 USER SYNC: User record synchronized with JWT claims for user {user.id[:8]}... (role: {jwt_role}, admin: {jwt_is_admin})")
            logger.info(f"User record synchronized with JWT claims for user {user.id[:8]}...")
    
    except Exception as e:
        logger.critical(f"🚨 USER SYNC FAILURE: Failed to sync JWT claims to user record: {e} (type: {type(e).__name__})")
        logger.error(f"Failed to sync JWT claims to user record: {e}")
        # Don't fail the entire authentication flow for sync issues
        await db.rollback()

async def _auto_create_user_if_needed(db: AsyncSession, validation_result: Dict[str, str]) -> User:
    """Auto-create user from JWT claims."""
    from netra_backend.app.services.user_service import user_service
    from netra_backend.app.config import get_config
    from shared.database.session_validation import validate_db_session
    
    # Validate database session (handles both production and test scenarios)
    validate_db_session(db, "auto_create_user_if_needed")
    
    user_id = validation_result.get("user_id")
    email = validation_result.get("email", f"user_{user_id}@example.com")
    user = await user_service.get_or_create_dev_user(db, email=email, user_id=user_id)
    
    config = get_config()
    logger.warning(f"🔑 USER AUTO-CREATED: Created user {user.email} from JWT claims (env: {config.environment}, user_id: {user_id[:8]}...)")
    logger.info(f"Auto-created user from JWT: {user.email} (env: {config.environment})")
    return user

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    """
    if not credentials:
        return None
    
    # Validate database session (handles both production and test scenarios)
    from shared.database.session_validation import validate_db_session
    logger.debug(f"get_current_user_optional - db type: {type(db)}")
    try:
        validate_db_session(db, "get_current_user_optional")
    except TypeError as e:
        logger.error(f"ERROR in get_current_user_optional: {e}")
    
    try:
        # Extract the token and validate it
        token = credentials.credentials
        logger.info(f"🔑 OPTIONAL AUTH: Attempting optional authentication (token_length: {len(token) if token else 0})")
        validation_result = await _validate_token_with_auth_service(token)
        user = await _get_user_from_database(db, validation_result)
        logger.info(f"✅ OPTIONAL AUTH SUCCESS: Optional authentication succeeded for user {user.id[:8] if user and hasattr(user, 'id') else 'unknown'}...")
        return user
    except Exception as e:
        logger.warning(f"🔑 OPTIONAL AUTH FAILURE: Optional authentication failed: {e} (type: {type(e).__name__})")
        logger.debug(f"Optional auth failed: {e}")
        return None

# Aliases for backward compatibility
get_current_active_user = get_current_user
validate_jwt_token = _validate_token_with_auth_service  # Compatibility alias for tests

async def get_current_user_with_db(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = None  # Will be injected separately
) -> User:
    """
    Get current authenticated user from auth service.
    This version is for use when db is already injected by another dependency.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session not provided"
        )
    token = credentials.credentials
    validation_result = await _validate_token_with_auth_service(token)
    user = await _get_user_from_database(db, validation_result)
    return user


async def validate_token_jwt(token: str) -> Optional[Dict[str, str]]:
    """Validate a JWT token through the auth service."""
    validation = await auth_client.validate_token(token)
    return validation if validation else None

# Type annotations for dependency injection
ActiveUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[Optional[User], Depends(get_current_user_optional)]

# Enhanced security function for extracting and validating JWT admin status
async def extract_admin_status_from_jwt(token: str) -> Dict[str, Any]:
    """Extract and validate admin status directly from JWT token.
    
    This function provides the authoritative source for admin status validation,
    bypassing any potential database record manipulation.
    
    Returns:
        Dict containing admin validation results and details
    """
    try:
        validation_result = await auth_client.validate_token_jwt(token)
        
        if not validation_result or not validation_result.get("valid"):
            return {
                "is_admin": False,
                "error": "Invalid token",
                "source": "jwt_validation_failed"
            }
        
        jwt_role = validation_result.get("role", "")
        jwt_permissions = validation_result.get("permissions", [])
        user_id = validation_result.get("user_id", "unknown")
        
        # Determine admin status from JWT claims
        is_admin = (
            jwt_role in ["admin", "super_admin"] or
            "admin" in jwt_permissions or
            "system:*" in jwt_permissions or
            "admin:*" in jwt_permissions
        )
        
        return {
            "is_admin": is_admin,
            "user_id": user_id,
            "role": jwt_role,
            "permissions": jwt_permissions,
            "source": "jwt_claims",
            "validation_result": validation_result
        }
        
    except Exception as e:
        logger.error(f"JWT admin status extraction failed: {e}")
        return {
            "is_admin": False,
            "error": str(e),
            "source": "jwt_extraction_error"
        }

# Permission-based dependencies with enhanced JWT validation
async def require_admin_with_enhanced_validation(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: User = Depends(get_current_user)
) -> User:
    """Enhanced admin requirement with direct JWT validation.
    
    This function provides dual validation:
    1. Standard database-based admin check
    2. Direct JWT claims validation for additional security
    """
    # Standard database check
    if not _check_admin_permissions(user):
        # If database check fails, try JWT validation as authoritative source
        token = credentials.credentials
        jwt_admin_status = await extract_admin_status_from_jwt(token)
        
        if not jwt_admin_status.get("is_admin", False):
            logger.critical(
                f"🚨 ADMIN ACCESS DENIED: User {user.id if hasattr(user, 'id') else 'unknown'} failed both database and JWT admin validation. JWT result: {jwt_admin_status}"
            )
            logger.error(
                f"Admin access denied for user {user.id if hasattr(user, 'id') else 'unknown'} - "
                f"Failed both database and JWT validation. JWT result: {jwt_admin_status}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required: Insufficient privileges"
            )
        else:
            logger.warning(
                f"🔄 ADMIN JWT OVERRIDE: Admin access granted via JWT override for user {user.id if hasattr(user, 'id') else 'unknown'} - Database record may be out of sync"
            )
            logger.warning(
                f"Admin access granted via JWT override for user {user.id if hasattr(user, 'id') else 'unknown'} - "
                f"Database record may be out of sync"
            )
    
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin permissions."""
    if not _check_admin_permissions(user):
        # Enhanced logging for security audit
        logger.critical(
            f"🚨 ADMIN ACCESS DENIED: User {user.id if hasattr(user, 'id') else 'unknown'} lacks admin permissions in database record"
        )
        logger.warning(
            f"Admin access denied for user {user.id if hasattr(user, 'id') else 'unknown'} - "
            f"insufficient permissions in database record"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

def _check_admin_permissions(user: User) -> bool:
    """Check if user has admin permissions from database record.
    
    WARNING: This function checks database records, not JWT claims.
    For security-critical operations, also validate JWT claims directly.
    """
    is_admin = (
        (hasattr(user, 'is_superuser') and user.is_superuser) or
        (hasattr(user, 'role') and user.role in ['admin', 'super_admin']) or
        (hasattr(user, 'is_admin') and user.is_admin)
    )
    
    if is_admin:
        logger.debug(f"Admin permissions confirmed for user {user.id if hasattr(user, 'id') else 'unknown'}")
    
    return is_admin

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
EnhancedAdminDep = Annotated[User, Depends(require_admin_with_enhanced_validation)]

def require_permission(permission: str):
    """Create a dependency that requires a specific permission"""
    async def check_permission(user: User = Depends(get_current_user)) -> User:
        _validate_user_permission(user, permission)
        return user
    return check_permission

async def get_jwt_claims_for_user(user: User) -> Dict[str, Any]:
    """Extract JWT claims from user object if available.
    
    Returns the JWT validation result that was stored during authentication.
    This allows admin functions to access the original JWT claims.
    """
    if hasattr(user, '_jwt_validation_result'):
        return user._jwt_validation_result
    
    logger.warning("JWT claims not available on user object - this may indicate a security issue")
    return {}

def _validate_user_permission(user: User, permission: str) -> None:
    """Validate that user has the required permission from both database and JWT claims."""
    # Check database permissions first
    has_db_permission = False
    if hasattr(user, 'permissions') and user.permissions is not None:
        has_db_permission = permission in user.permissions
    
    # Check JWT permissions if available (more authoritative)
    has_jwt_permission = False
    if hasattr(user, '_jwt_validation_result'):
        jwt_permissions = user._jwt_validation_result.get('permissions', [])
        has_jwt_permission = (
            permission in jwt_permissions or
            "system:*" in jwt_permissions or
            any(perm.endswith(":*") and permission.startswith(perm[:-1]) for perm in jwt_permissions)
        )
    
    # Grant access if either source has the permission
    if not (has_db_permission or has_jwt_permission):
        logger.warning(
            f"Permission '{permission}' denied for user {user.id if hasattr(user, 'id') else 'unknown'} - "
            f"DB: {has_db_permission}, JWT: {has_jwt_permission}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required"
        )

# NOTE: All JWT and password hashing logic has been moved to the auth service
# This module ONLY handles FastAPI dependency injection
# See auth_service for actual authentication implementation

# Compatibility aliases for deprecated dependencies
ActiveUserWsDep = Annotated[User, Depends(get_current_user)]

def get_auth_client() -> AuthServiceClient:
    """Get the auth service client instance
    
    Returns:
        AuthServiceClient instance for making auth service calls
    """
    return auth_client


# Compatibility function for generate_access_token (DEPRECATED)
async def generate_access_token(user_id: str, email: str = None, **kwargs) -> str:
    """
    Generate access token - Compatibility wrapper.
    
    DEPRECATED: This function provides backward compatibility for tests.
    New code should use the auth service client directly.
    
    Args:
        user_id: User ID for token generation
        email: User email (optional)
        **kwargs: Additional token parameters
        
    Returns:
        Access token string
        
    Raises:
        Exception: If token generation fails
    """
    logger.warning("DEPRECATED: generate_access_token used - please update to use auth service directly")
    
    try:
        # Use the auth service client to generate the token
        result = await auth_client.create_access_token(user_id=user_id, email=email or f"{user_id}@example.com")
        if result and "access_token" in result:
            return result["access_token"]
        else:
            raise Exception("Failed to generate access token via auth service")
    except Exception as e:
        logger.error(f"Error generating access token: {e}")
        raise


# NOTE: All JWT and password hashing logic has been moved to the auth service
# This module ONLY handles FastAPI dependency injection
# See auth_service for actual authentication implementation