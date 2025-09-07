"""
Auth Routes for Auth Service
Comprehensive implementation with refresh token endpoint
"""
import json
import logging
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, UTC
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse

# Import auth service models and services
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import RefreshRequest
from auth_service.auth_core.oauth_manager import OAuthManager
from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env

# Import MockAuthService for testing (conditional import for deployment safety)
try:
    from auth_service.test_framework.mock_auth_service import MockAuthService
    MOCK_AUTH_AVAILABLE = True
except ImportError:
    MockAuthService = None
    MOCK_AUTH_AVAILABLE = False

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

@router.get("/auth/health")
async def auth_health() -> Dict[str, Any]:
    """Comprehensive health check endpoint with database connectivity"""
    try:
        # Get database connection health status
        database_status = "disconnected"
        database_details = {}
        
        if auth_service._db_connection:
            try:
                # Check database connectivity using the connection health method
                health_info = await auth_service._db_connection.get_connection_health()
                if health_info.get("status") == "healthy":
                    database_status = "connected"
                elif health_info.get("status") == "not_initialized":
                    database_status = "not_initialized"
                else:
                    database_status = "error"
                
                database_details = {
                    "connectivity_test": health_info.get("connectivity_test", "unknown"),
                    "initialized": health_info.get("initialized", False)
                }
            except Exception as db_error:
                logger.warning(f"Database health check failed: {db_error}")
                database_status = "error"
                database_details = {"error": str(db_error)}
        else:
            database_status = "not_configured"
            
        # Determine overall service health
        overall_status = "healthy" if database_status in ["connected", "not_configured"] else "unhealthy"
        
        health_response = {
            "status": overall_status,
            "service": "auth-service",
            "version": "1.0.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "database_status": database_status
        }
        
        # Add database details for debugging if available
        if database_details:
            health_response["database_details"] = database_details
            
        return health_response
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "auth-service",
            "version": "1.0.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "database_status": "error",
            "error": str(e)
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
    
    # CRITICAL: Get OAuth redirect URI from SSOT
    # See: /auth_service/auth_core/oauth/google_oauth.py:78 for implementation
    # See: /OAUTH_SSOT_COMPLIANCE_ANALYSIS.md for why this is critical
    from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider
    oauth_provider = GoogleOAuthProvider()
    oauth_redirect_uri = oauth_provider.get_redirect_uri()
    
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
        # CRITICAL: This is for frontend callback after auth service processes OAuth
        # The OAuth provider redirects to auth service, then auth redirects to frontend
        "authorized_redirect_uris": [f"{frontend_base_url}/auth/callback"],
        # SSOT: The actual OAuth redirect URI used with Google
        "oauth_redirect_uri": oauth_redirect_uri
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

@router.get("/auth/login")
async def oauth_login_get(provider: str = Query(default=None), request: Request = None) -> Any:
    """OAuth login endpoint - initiates OAuth flow for GET requests
    
    This endpoint handles GET requests to /auth/login?provider=google
    and redirects to the Google OAuth authorization page.
    """
    if not provider:
        # If no provider specified, return error for GET request
        raise HTTPException(
            status_code=400,
            detail="Provider parameter is required for OAuth login"
        )
    
    if provider != "google":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider: {provider}"
        )
    
    try:
        # Initialize OAuth manager
        oauth_manager = OAuthManager()
        
        # Check if Google provider is configured
        if not oauth_manager.is_provider_configured("google"):
            logger.error("Google OAuth provider not configured")
            raise HTTPException(
                status_code=503,
                detail="OAuth provider not configured"
            )
        
        # Get Google provider
        google_provider = oauth_manager.get_provider("google")
        if not google_provider:
            raise HTTPException(
                status_code=503,
                detail="Failed to get OAuth provider"
            )
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state in session or cache (for now, we'll pass it through)
        # In production, this should be stored server-side
        
        # Get authorization URL
        auth_url = google_provider.get_authorization_url(state)
        
        logger.info(f"Redirecting to Google OAuth: {auth_url[:50]}...")
        
        # Redirect to Google OAuth
        return RedirectResponse(url=auth_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth login failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to initiate OAuth login"
        )

@router.post("/auth/login")
async def login_endpoint(request: Request) -> Dict[str, Any]:
    """Login endpoint - authenticate user and return tokens for POST requests"""
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

@router.post("/auth/e2e/test-auth")
async def e2e_test_auth(request: Request) -> Dict[str, Any]:
    """E2E test authentication endpoint - simulates OAuth flow for staging/test environments
    
    This endpoint is protected by E2E_OAUTH_SIMULATION_KEY and only works in non-production
    environments. It simulates a successful OAuth authentication flow for E2E testing.
    """
    from auth_service.auth_core.config import AuthConfig
    from auth_service.auth_core.secret_loader import AuthSecretLoader
    
    env = AuthConfig.get_environment()
    
    # Prevent usage in production
    if env == "production":
        logger.warning("E2E test auth attempted in production environment")
        raise HTTPException(
            status_code=403,
            detail="E2E test authentication is not available in production"
        )
    
    # Verify E2E bypass key
    bypass_key = request.headers.get("X-E2E-Bypass-Key")
    if not bypass_key:
        logger.warning("E2E test auth attempted without bypass key")
        raise HTTPException(
            status_code=401,
            detail="E2E bypass key required"
        )
    
    # Load expected E2E key from secrets
    expected_key = AuthSecretLoader.get_E2E_OAUTH_SIMULATION_KEY()
    
    if not expected_key:
        logger.error("E2E_OAUTH_SIMULATION_KEY not configured")
        raise HTTPException(
            status_code=503,
            detail="E2E authentication not configured"
        )
    
    if bypass_key != expected_key:
        logger.warning(f"Invalid E2E bypass key provided")
        raise HTTPException(
            status_code=401,
            detail="Invalid E2E bypass key"
        )
    
    try:
        # Parse request body
        body = await request.json()
        email = body.get("email", "e2e-test@staging.netrasystems.ai")
        name = body.get("name", "E2E Test User")
        permissions = body.get("permissions", ["read", "write"])
        simulate_oauth = body.get("simulate_oauth", True)
        
        # Generate user ID based on email
        user_id = f"e2e-{email.split('@')[0]}"
        
        # Generate tokens simulating OAuth authentication
        access_token = await auth_service.create_access_token(
            user_id=user_id,
            email=email
        )
        
        refresh_token = await auth_service.create_refresh_token(
            user_id=user_id,
            email=email
        )
        
        logger.info(f"E2E test auth successful for {email} in {env} environment")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,  # 15 minutes
            "user": {
                "id": user_id,
                "email": email,
                "name": name,
                "permissions": permissions,
                "oauth_simulated": simulate_oauth
            }
        }
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail="Invalid JSON body"
        )
    except Exception as e:
        logger.error(f"E2E test auth failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate E2E test tokens"
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
        
        # Validate service credentials using auth service validation logic
        # This will handle development mode fallbacks and proper service validation
        if not await auth_service._validate_service(service_id, service_secret):
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

@router.get("/auth/oauth/callback")
@router.get("/auth/callback")
async def oauth_callback(
    code: str = Query(default=None),
    state: str = Query(default=None),
    error: str = Query(default=None),
    error_description: str = Query(default=None)
) -> Any:
    """OAuth callback endpoint - handles OAuth provider response"""
    
    # Check for OAuth errors
    if error:
        logger.error(f"OAuth callback error: {error} - {error_description}")
        # Redirect to frontend with error
        env = AuthConfig.get_environment()
        if env == "staging":
            frontend_url = "https://app.staging.netrasystems.ai"
        elif env == "production":
            frontend_url = "https://app.netrasystems.ai"
        else:
            frontend_url = "http://localhost:3000"
        
        error_params = urlencode({"error": error, "error_description": error_description or ""})
        return RedirectResponse(
            url=f"{frontend_url}/auth/error?{error_params}",
            status_code=302
        )
    
    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail="Missing authorization code or state"
        )
    
    try:
        # Initialize OAuth manager
        oauth_manager = OAuthManager()
        google_provider = oauth_manager.get_provider("google")
        
        if not google_provider:
            raise HTTPException(
                status_code=503,
                detail="OAuth provider not available"
            )
        
        # Exchange code for user info
        user_info = google_provider.exchange_code_for_user_info(code, state)
        
        if not user_info:
            raise HTTPException(
                status_code=401,
                detail="Failed to get user information from OAuth provider"
            )
        
        # Create or update user in database
        email = user_info.get("email")
        name = user_info.get("name", "")
        google_id = user_info.get("sub")
        
        if not email:
            raise HTTPException(
                status_code=400,
                detail="Email not provided by OAuth provider"
            )
        
        # Generate tokens for the user
        # In a real implementation, you would create/update the user in the database first
        access_token = await auth_service.create_access_token(
            user_id=google_id or email,
            email=email
        )
        
        refresh_token = await auth_service.create_refresh_token(
            user_id=google_id or email,
            email=email
        )
        
        # Redirect to frontend with tokens
        env = AuthConfig.get_environment()
        if env == "staging":
            frontend_url = "https://app.staging.netrasystems.ai"
        elif env == "production":
            frontend_url = "https://app.netrasystems.ai"
        else:
            frontend_url = "http://localhost:3000"
        
        # Pass tokens to frontend via URL parameters (in production, use more secure method)
        auth_params = urlencode({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "email": email,
            "name": name
        })
        
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?{auth_params}",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="OAuth authentication failed"
        )

@router.get("/auth/me")
async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current user's profile information
    
    Requires a valid JWT token in the Authorization header.
    Returns the authenticated user's profile information.
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Profile request without valid Authorization header")
            raise HTTPException(
                status_code=401,
                detail="Authorization header with Bearer token required"
            )
        
        token = auth_header.split(" ")[1]
        
        # Validate token using auth service
        try:
            token_response = await auth_service.validate_token(token, "access")
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )
        
        # Check if token is valid
        if not token_response or not token_response.valid:
            logger.debug("Invalid token provided for profile request")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )
        
        # Build user profile response
        user_profile = {
            "user_id": token_response.user_id,
            "email": token_response.email,
            "permissions": token_response.permissions or []
        }
        
        # Try to enrich with database information if available
        try:
            if auth_service._db_connection:
                from auth_service.auth_core.database.repository import AuthUserRepository
                session = await auth_service._get_db_session()
                if session:
                    user_repo = AuthUserRepository(session)
                    user = await user_repo.get_by_id(token_response.user_id)
                    if user:
                        user_profile.update({
                            "name": user.full_name,
                            "created_at": user.created_at.isoformat() if user.created_at else None,
                            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                            "is_verified": user.is_verified,
                            "auth_provider": user.auth_provider
                        })
        except Exception as e:
            logger.warning(f"Failed to enrich user profile from database: {e}")
            # Continue with token-based information only
        
        # Add token expiration if available
        if token_response.expires_at:
            user_profile["token_expires_at"] = token_response.expires_at.isoformat()
        
        logger.debug(f"Profile retrieved successfully for user: {token_response.email}")
        return user_profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in profile endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/auth/verify")
@router.get("/auth/verify")
async def verify_token_endpoint(request: Request) -> Dict[str, Any]:
    """Verify JWT token endpoint for E2E tests and authentication validation
    
    Accepts token from Authorization header (Bearer token) or request body.
    Returns user information if valid, error message if invalid.
    """
    try:
        token = None
        
        # Try to get token from Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        # If no Authorization header, try to get token from request body (POST only)
        if not token and request.method == "POST":
            try:
                body = await request.json()
                token = body.get("token") or body.get("access_token")
            except Exception:
                # Ignore JSON parsing errors and continue with no token
                pass
        
        if not token:
            logger.warning("Token verification requested with no token provided")
            return {
                "valid": False,
                "error": "No token provided in Authorization header or request body"
            }
        
        # Validate token using auth service
        try:
            token_response = await auth_service.validate_token(token, "access")
        except Exception as e:
            logger.error(f"Token validation failed with error: {e}")
            return {
                "valid": False,
                "error": "Token validation failed"
            }
        
        # Check if token is valid
        if not token_response or not token_response.valid:
            logger.debug("Token validation returned invalid token")
            return {
                "valid": False,
                "error": "Invalid or expired token"
            }
        
        # Return user information for valid token
        response_data = {
            "valid": True,
            "user_id": token_response.user_id,
            "email": token_response.email
        }
        
        # Add expiration timestamp if available
        if token_response.expires_at:
            response_data["exp"] = token_response.expires_at.isoformat()
        
        # Add permissions if available
        if hasattr(token_response, 'permissions') and token_response.permissions:
            response_data["permissions"] = token_response.permissions
        
        logger.debug(f"Token verified successfully for user: {token_response.email}")
        return response_data
        
    except Exception as e:
        logger.error(f"Unexpected error in token verification endpoint: {e}")
        return {
            "valid": False,
            "error": "Internal server error during token verification"
        }

@oauth_router.get("/oauth/providers")
async def oauth_providers() -> Dict[str, Any]:
    """Get available OAuth providers"""
    try:
        oauth_manager = OAuthManager()
        available_providers = oauth_manager.get_available_providers()
        
        provider_status = {}
        for provider_name in available_providers:
            provider_status[provider_name] = oauth_manager.get_provider_status(provider_name)
        
        return {
            "providers": available_providers,
            "status": "configured" if available_providers else "not_configured",
            "provider_details": provider_status,
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get OAuth providers: {e}")
        return {
            "providers": [],
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat()
        }