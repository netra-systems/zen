"""
Core auth service client functionality.
Handles token validation, authentication, and service-to-service communication.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from netra_backend.app.clients.auth_client_cache import (
    AuthCircuitBreakerManager,
    AuthServiceSettings,
    AuthTokenCache,
)
from netra_backend.app.clients.circuit_breaker import (
    get_circuit_breaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
)
from netra_backend.app.clients.auth_client_config import (
    EnvironmentDetector,
    OAuthConfig,
    OAuthConfigGenerator,
)
from netra_backend.app.core.environment_constants import get_current_environment, Environment, is_production
from netra_backend.app.core.tracing import TracingManager
from enum import Enum
from shared.isolated_environment import get_env
# SSOT: Import SERVICE_ID constant
from shared.constants.service_identifiers import SERVICE_ID

logger = logging.getLogger(__name__)


# Exception Classes for Auth Service Operations
class AuthServiceError(Exception):
    """Base exception for auth service operations."""
    pass


class AuthServiceConnectionError(AuthServiceError):
    """Exception raised when auth service connection fails."""
    pass


class AuthServiceNotAvailableError(AuthServiceError):
    """Exception raised when auth service is not available."""
    pass


class AuthServiceValidationError(AuthServiceError):
    """Exception raised when auth service validation fails."""
    pass


class AuthTokenExchangeError(AuthServiceError):
    """Exception raised when token exchange fails."""
    pass


class CircuitBreakerError(AuthServiceError):
    """Exception raised when circuit breaker is open."""
    pass


class EnvironmentDetectionError(Exception):
    """Exception raised when environment detection fails."""
    pass


class OAuthError(Exception):
    """Base exception for OAuth operations."""
    pass


class OAuthConfigError(OAuthError):
    """Exception raised when OAuth configuration fails."""
    pass


class OAuthInvalidCredentialsError(OAuthError):
    """Exception raised when OAuth credentials are invalid."""
    pass


class OAuthInvalidGrantError(OAuthError):
    """Exception raised when OAuth grant is invalid."""
    pass


class OAuthInvalidRequestError(OAuthError):
    """Exception raised when OAuth request is invalid."""
    pass


class OAuthInvalidScopeError(OAuthError):
    """Exception raised when OAuth scope is invalid."""
    pass


class OAuthRedirectMismatchError(OAuthError):
    """Exception raised when OAuth redirect URI mismatches."""
    pass


class OAuthServerError(OAuthError):
    """Exception raised when OAuth server encounters an error."""
    pass


class OAuthUnavailableError(OAuthError):
    """Exception raised when OAuth service is unavailable."""
    pass


# Data Classes and Type Definitions
class AuthServiceHealthStatus:
    """Health status of auth service."""
    def __init__(self, healthy: bool = True, message: str = "OK"):
        self.healthy = healthy
        self.message = message


class TokenStatus:
    """Token status information."""
    def __init__(self, valid: bool, expired: bool = False):
        self.valid = valid
        self.expired = expired


class ClientCredentials:
    """Client credentials for OAuth."""
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret


class ServiceCredentials:
    """Service credentials for inter-service auth."""
    def __init__(self, service_id: str, service_secret: str):
        self.service_id = service_id
        self.service_secret = service_secret


class AuthTokenRequest:
    """Request for auth token."""
    def __init__(self, token: str, token_type: str = "access"):
        self.token = token
        self.token_type = token_type


class AuthTokenResponse:
    """Response for auth token operations."""
    def __init__(self, valid: bool, user_id: str = None, email: str = None, permissions: list = None):
        self.valid = valid
        self.user_id = user_id
        self.email = email
        self.permissions = permissions or []


class TokenValidationRequest:
    """Request for token validation."""
    def __init__(self, token: str, service_name: str = None):
        self.token = token
        self.service_name = service_name


class TokenValidationResponse:
    """Response for token validation."""
    def __init__(self, valid: bool, user_id: str = None, permissions: list = None):
        self.valid = valid
        self.user_id = user_id
        self.permissions = permissions or []


class UserAuthRequest:
    """Request for user authentication."""
    def __init__(self, email: str, password: str, provider: str = "local"):
        self.email = email
        self.password = password
        self.provider = provider


class UserAuthResponse:
    """Response for user authentication."""
    def __init__(self, access_token: str, refresh_token: str = None, user_id: str = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id


class OAuth2Request:
    """Request for OAuth2 operations."""
    def __init__(self, client_id: str, redirect_uri: str, scope: str = None):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scope = scope


class OAuth2Response:
    """Response for OAuth2 operations."""
    def __init__(self, access_token: str, token_type: str = "Bearer", expires_in: int = 3600):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in


# Global auth client instance
_auth_resilience_service = None

def get_auth_resilience_service():
    """Get the global auth resilience service instance."""
    global _auth_resilience_service
    if _auth_resilience_service is None:
        _auth_resilience_service = AuthServiceClient()
    return _auth_resilience_service

def get_auth_service_client():
    """Get the global auth service client instance."""
    return get_auth_resilience_service()


def handle_auth_service_error(response, operation: str):
    """Handle auth service errors based on HTTP response."""
    status_code = getattr(response, 'status_code', 500)
    
    try:
        error_data = response.json() if hasattr(response, 'json') else {}
        error_msg = error_data.get('error', f'HTTP {status_code} error')
    except:
        error_msg = f'HTTP {status_code} error'
    
    if status_code == 401 or status_code == 403:
        raise AuthServiceValidationError(f"Authentication failed for {operation}: {error_msg}")
    elif status_code == 404:
        raise AuthServiceNotAvailableError(f"Auth service not found for {operation}: {error_msg}")
    elif status_code >= 500:
        raise AuthServiceError(f"Auth service error for {operation}: {error_msg}")
    else:
        raise AuthServiceError(f"Unexpected auth error for {operation}: {error_msg}")


def validate_jwt_format(token: str) -> bool:
    """Validate JWT token format without decoding."""
    if not token or not isinstance(token, str):
        return False
    
    # Strip Bearer prefix if present
    jwt_token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token
    
    # Basic JWT format check (header.payload.signature)
    parts = jwt_token.split('.')
    if len(parts) != 3:
        return False
    
    # Check if all parts are non-empty
    return all(part for part in parts)


class AuthOperationType(Enum):
    """Types of authentication operations for resilience handling."""
    TOKEN_VALIDATION = "token_validation"
    LOGIN = "login"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PERMISSION_CHECK = "permission_check"
    HEALTH_CHECK = "health_check"
    MONITORING = "monitoring"


class AuthResilienceMode(Enum):
    """Authentication resilience operating modes - simplified for SSOT."""
    NORMAL = "normal"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    RECOVERY = "recovery"


class AuthServiceClient:
    """Client for communicating with auth service."""
    
    def __init__(self):
        self.settings = AuthServiceSettings()
        self.token_cache = AuthTokenCache(self.settings.cache_ttl)
        self.circuit_manager = AuthCircuitBreakerManager()
        self.environment_detector = EnvironmentDetector()
        self.oauth_generator = OAuthConfigGenerator()
        self.tracing_manager = TracingManager()
        self._client = None
        
        # Initialize circuit breaker for auth service calls with improved recovery
        # REMEDIATION ISSUE #395: Configurable circuit breaker timeouts aligned with health check timeouts
        env_vars = get_env()
        circuit_call_timeout = float(env_vars.get("AUTH_CIRCUIT_CALL_TIMEOUT", "3.0"))
        circuit_recovery_timeout = float(env_vars.get("AUTH_CIRCUIT_RECOVERY_TIMEOUT", "10.0"))
        
        self.circuit_breaker = get_circuit_breaker(
            name="auth_service",
            config=CircuitBreakerConfig(
                failure_threshold=3,  # Open after 3 consecutive failures
                success_threshold=1,  # Close after 1 success in half-open (faster recovery)
                timeout=circuit_recovery_timeout,  # Try half-open after configured seconds
                call_timeout=circuit_call_timeout,  # Individual call timeout - must be > health_check_timeout
                failure_rate_threshold=0.8,  # Open if 80% of calls fail (more tolerant)
                min_calls_for_rate=3  # Need only 3 calls to calculate failure rate (faster detection)
            )
        )
        
        # Log circuit breaker configuration for debugging
        logger.debug(f"Auth circuit breaker configuration - "
                    f"Call timeout: {circuit_call_timeout}s, Recovery timeout: {circuit_recovery_timeout}s")
        
        # REMEDIATION ISSUE #395: Validate circuit breaker alignment with health check timeout
        environment = env_vars.get("ENVIRONMENT", "development").lower()
        default_health_timeout = 0.3 if environment == "staging" else 1.0  # Issue #469 optimization
        configured_health_timeout = float(env_vars.get("AUTH_HEALTH_CHECK_TIMEOUT", default_health_timeout))
        
        if circuit_call_timeout <= configured_health_timeout:
            logger.warning(f"CIRCUIT BREAKER ALIGNMENT WARNING: Circuit breaker call timeout ({circuit_call_timeout}s) "
                          f"should be greater than health check timeout ({configured_health_timeout}s) "
                          f"to prevent premature circuit breaker activation. "
                          f"Recommended: Set AUTH_CIRCUIT_CALL_TIMEOUT > {configured_health_timeout + 0.5}")
        else:
            logger.debug(f"Circuit breaker alignment validated - "
                        f"Call timeout ({circuit_call_timeout}s) > Health timeout ({configured_health_timeout}s)")
        # Load service authentication credentials
        from netra_backend.app.core.configuration import get_configuration
        config = get_configuration()
        self.service_id = config.service_id or "netra-backend"
        self.service_secret = config.service_secret
        
        # CRITICAL FIX: Fallback to environment if config doesn't have service_secret
        # This ensures we always get the secret even if config loading fails
        if not self.service_secret:
            env = get_env()
            env_service_secret = env.get('SERVICE_SECRET')
            if env_service_secret:
                self.service_secret = env_service_secret
                logger.info("Loaded SERVICE_SECRET from environment as auth client fallback")
            else:
                logger.error("SERVICE_SECRET not found in config or environment - auth will fail")
        
        # Log initialization status for debugging
        logger.info(f"AuthServiceClient initialized - Service ID: {self.service_id}, Service Secret configured: {bool(self.service_secret)}")
        
        # PRODUCTION SECURITY: Validate auth service requirements in production
        # Check both unified config and environment variable for robust production detection
        env = get_env()
        env_var = env.get('ENVIRONMENT', '').lower()
        current_env = get_current_environment()
        is_prod_env = (env_var == 'production' or current_env == Environment.PRODUCTION.value or self._is_production_environment())
        
        if is_prod_env:
            if not self.settings.enabled:
                logger.error("PRODUCTION SECURITY: Auth service is required in production")
                logger.error(f"Environment variable: {env_var}")
                logger.error(f"Current environment: {current_env}")
                logger.error(f"Auth service enabled: {self.settings.enabled}")
                raise RuntimeError("Auth service must be enabled in production environment")
            if not self.service_secret:
                logger.error("PRODUCTION SECURITY: Service secret is required in production")
                logger.error(f"Environment variable: {env_var}")
                logger.error(f"Current environment: {current_env}")
                raise RuntimeError("SERVICE_SECRET must be configured in production environment")
    
    def _get_environment_specific_timeouts(self) -> httpx.Timeout:
        """
        Get environment-specific timeout configuration for WebSocket performance optimization.
        
        CRITICAL FIX: Staging environment was experiencing 179-second WebSocket latencies
        due to excessive HTTP timeout values blocking authentication. This implements
        fast-fail timeouts to restore <5 second WebSocket connection performance.
        
        REMEDIATION ISSUE #395: Added environment variable support for configurable timeouts.
        Environment variables override defaults for runtime flexibility:
        - AUTH_CONNECT_TIMEOUT: Connection timeout in seconds
        - AUTH_READ_TIMEOUT: Read timeout in seconds  
        - AUTH_WRITE_TIMEOUT: Write timeout in seconds
        - AUTH_POOL_TIMEOUT: Pool timeout in seconds
        """
        from shared.isolated_environment import get_env
        env_vars = get_env()
        environment = env_vars.get("ENVIRONMENT", "development").lower()
        
        # Default timeout configurations per environment
        if environment == "staging":
            # ISSUE #469: Optimized timeouts for 80% performance improvement
            # Auth service typically responds in 0.195s; optimized for fast-fail approach
            # Previous total: 12s, New total: 3.2s for 73% improvement
            defaults = {"connect": 0.8, "read": 1.6, "write": 0.4, "pool": 0.4}
        elif environment == "production":
            # Production: Balanced timeouts for reliability without excessive delays
            defaults = {"connect": 2.0, "read": 5.0, "write": 3.0, "pool": 5.0}  # Max 15s total
        else:
            # Development/testing: Fast timeouts for quick feedback
            defaults = {"connect": 1.0, "read": 3.0, "write": 1.0, "pool": 3.0}  # Max 8s total
        
        # Override defaults with environment variables if provided
        connect_timeout = float(env_vars.get("AUTH_CONNECT_TIMEOUT", defaults["connect"]))
        read_timeout = float(env_vars.get("AUTH_READ_TIMEOUT", defaults["read"]))
        write_timeout = float(env_vars.get("AUTH_WRITE_TIMEOUT", defaults["write"]))
        pool_timeout = float(env_vars.get("AUTH_POOL_TIMEOUT", defaults["pool"]))
        
        # Log timeout configuration for debugging
        total_timeout = connect_timeout + read_timeout + write_timeout + pool_timeout
        logger.debug(f"Auth timeout configuration - Environment: {environment}, "
                    f"Connect: {connect_timeout}s, Read: {read_timeout}s, "
                    f"Write: {write_timeout}s, Pool: {pool_timeout}s, Total: {total_timeout}s")
        
        return httpx.Timeout(
            connect=connect_timeout, 
            read=read_timeout, 
            write=write_timeout, 
            pool=pool_timeout
        )

    def _create_http_client(self) -> httpx.AsyncClient:
        """Create new HTTP client instance with connection pooling and retry logic."""
        # CRITICAL FIX: Use environment-specific timeouts for WebSocket performance
        timeouts = self._get_environment_specific_timeouts()
        
        return httpx.AsyncClient(
            base_url=self.settings.base_url,
            timeout=timeouts,  # Environment-optimized timeouts
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            follow_redirects=True,
            transport=httpx.AsyncHTTPTransport(
                retries=1,  # Reduced retries for faster failure in staging
                verify=False,  # For local development
            )
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            self._client = self._create_http_client()
        return self._client
    
    def _get_service_auth_headers(self) -> Dict[str, str]:
        """Get service-to-service authentication headers."""
        headers = {}
        if self.service_id and self.service_secret:
            # CRITICAL FIX: Sanitize header values to remove illegal characters
            # Windows line endings and whitespace can cause "Illegal header value" errors
            sanitized_service_id = str(self.service_id).strip()
            sanitized_service_secret = str(self.service_secret).strip()
            
            # Log warning if sanitization was needed (helps detect config issues)
            if sanitized_service_id != str(self.service_id):
                logger.warning(f"SERVICE_ID contained illegal characters - sanitized from {repr(str(self.service_id))} to {repr(sanitized_service_id)}")
            if sanitized_service_secret != str(self.service_secret):
                logger.warning(f"SERVICE_SECRET contained illegal characters - sanitized (length: {len(str(self.service_secret))} -> {len(sanitized_service_secret)})")
            
            headers["X-Service-ID"] = sanitized_service_id
            headers["X-Service-Secret"] = sanitized_service_secret
            logger.debug(f"Service auth headers configured for service ID: '{sanitized_service_id}'")
        else:
            # Log detailed diagnostic info when service auth is missing
            missing_parts = []
            if not self.service_id:
                missing_parts.append("SERVICE_ID")
                logger.error(
                    f"SERVICE_ID is not configured. Set SERVICE_ID={SERVICE_ID} in environment. "
                    "Auth service will reject requests without proper service ID."
                )
            if not self.service_secret:
                missing_parts.append("SERVICE_SECRET")
                logger.error(
                    "SERVICE_SECRET is not configured. This is required for service-to-service authentication. "
                    "Set SERVICE_SECRET to a secure value (min 32 chars) that matches the auth service configuration."
                )
            
            if missing_parts:
                logger.error(
                    f"Missing service authentication configuration: {', '.join(missing_parts)}. "
                    f"Auth service calls will fail. Current service_id='{self.service_id or 'NOT SET'}'"
                )
        return headers
    
    def _get_request_headers(self, include_auth: bool = True, bearer_token: str = None) -> Dict[str, str]:
        """Get headers for auth service requests.
        
        Args:
            include_auth: Whether to include service auth headers
            bearer_token: Optional bearer token for user auth
            
        Returns:
            Dict of headers
        """
        headers = {}
        
        # Add service authentication if enabled
        if include_auth:
            headers.update(self._get_service_auth_headers())
        
        # Add tracing headers
        trace_headers = self.tracing_manager.inject_trace_headers()
        headers.update(trace_headers)
        
        # Add bearer token if provided
        if bearer_token:
            from netra_backend.app.core.auth_constants import HeaderConstants
            headers[HeaderConstants.AUTHORIZATION] = f"{HeaderConstants.BEARER_PREFIX}{bearer_token}"
        
        return headers
    
    async def _check_auth_service_enabled(self, token: str) -> Optional[Dict]:
        """Check if auth service is enabled with user-visible error reporting."""
        if not self.settings.enabled:
            logger.critical(
                "AUTH SERVICE DISABLED: Auth service is required for token validation but is disabled. "
                "Users cannot authenticate. This is a critical system configuration issue."
            )
            return {
                "valid": False, 
                "error": "auth_service_disabled",
                "user_notification": {
                    "message": "Authentication service is disabled",
                    "severity": "critical",
                    "user_friendly_message": (
                        "The authentication system is currently disabled. "
                        "This is a system configuration issue. "
                        "Please contact support immediately."
                    ),
                    "action_required": "Contact support - this requires immediate technical intervention",
                    "support_code": f"AUTH_DISABLED_{datetime.now().strftime('%H%M%S')}"
                }
            }
        return None
    
    async def _check_auth_service_connectivity(self) -> bool:
        """
        Check if auth service is reachable before attempting operations.
        
        CRITICAL FIX: Ultra-fast connectivity check to prevent WebSocket blocking.
        Previous 2-second timeout was contributing to 179-second auth delays.
        
        Returns:
            True if auth service is reachable, False otherwise
        """
        # REMEDIATION ISSUE #395: Enhanced monitoring with precise timing
        health_check_start = time.time()
        
        try:
            from shared.isolated_environment import get_env
            env_vars = get_env()
            environment = env_vars.get("ENVIRONMENT", "development").lower()
            
            # Default health check timeouts per environment
            if environment == "staging":
                # REMEDIATION ISSUE #395: Increased staging timeout from 0.5s to 1.5s for 87% buffer utilization
                # Auth service responds in 0.195s; 1.5s timeout provides 87% buffer vs 61% with 0.5s
                default_health_timeout = 0.3  # Optimized for 80% improvement (Issue #469)
            else:
                default_health_timeout = 1.0  # Still fast for other environments
            
            # REMEDIATION ISSUE #395: Environment variable override for health check timeout
            # AUTH_HEALTH_CHECK_TIMEOUT allows runtime configuration
            health_timeout = float(env_vars.get("AUTH_HEALTH_CHECK_TIMEOUT", default_health_timeout))
            
            logger.debug(f"Auth health check timeout - Environment: {environment}, "
                        f"Timeout: {health_timeout}s (default: {default_health_timeout}s)")
            
            # Quick connectivity check with minimal timeout
            client = await self._get_client()
            response = await asyncio.wait_for(
                client.get("/health"),
                timeout=health_timeout
            )
            
            # REMEDIATION ISSUE #395: Comprehensive monitoring and buffer utilization tracking
            connectivity_duration = time.time() - health_check_start
            is_reachable = response.status_code in [200, 404]  # 404 is OK, means service is up
            buffer_utilization = (1 - (connectivity_duration / health_timeout)) * 100 if health_timeout > 0 else 0
            
            # Enhanced logging with buffer utilization metrics
            if is_reachable:
                logger.info(f" PASS:  Auth service connectivity successful - "
                           f"Duration: {connectivity_duration:.3f}s, "
                           f"Timeout: {health_timeout}s, "
                           f"Buffer utilization: {buffer_utilization:.1f}%, "
                           f"Status: {response.status_code}")
                
                # Alert if buffer utilization is too low (< 50% suggests timeout could be reduced)
                if buffer_utilization < 50:
                    logger.warning(f" ALERT:  LOW BUFFER UTILIZATION: {buffer_utilization:.1f}% - "
                                  f"Consider reducing AUTH_HEALTH_CHECK_TIMEOUT from {health_timeout}s "
                                  f"to ~{connectivity_duration * 2:.1f}s for better performance")
                
                # Alert if buffer utilization is dangerously high (> 90% suggests timeout too aggressive)  
                elif buffer_utilization > 90:
                    logger.warning(f" WARNING: [U+FE0F] HIGH BUFFER UTILIZATION: {buffer_utilization:.1f}% - "
                                  f"Timeout {health_timeout}s may be too aggressive for {connectivity_duration:.3f}s response time")
            else:
                logger.error(f" FAIL:  Auth service connectivity failed - "
                           f"Duration: {connectivity_duration:.3f}s, "
                           f"Timeout: {health_timeout}s, "
                           f"Status: {response.status_code}")
            
            return is_reachable
        except asyncio.TimeoutError:
            # REMEDIATION ISSUE #395: Enhanced timeout monitoring with buffer utilization analysis
            timeout_duration = time.time() - health_check_start
            logger.warning(f"[U+1F550] Auth service connectivity TIMEOUT - "
                          f"Duration: {timeout_duration:.3f}s, "
                          f"Configured timeout: {health_timeout}s, "
                          f"Environment: {environment}")
            
            # Provide actionable remediation guidance
            suggested_timeout = health_timeout * 1.5  # 50% buffer increase
            logger.warning(f" IDEA:  TIMEOUT REMEDIATION: Consider increasing AUTH_HEALTH_CHECK_TIMEOUT "
                          f"from {health_timeout}s to {suggested_timeout:.1f}s for better reliability")
            
            return False
        except Exception as e:
            connectivity_duration = time.time() - health_check_start
            logger.warning(f" WARNING: [U+FE0F] Auth service connectivity check failed - "
                          f"Duration: {connectivity_duration:.3f}s, "
                          f"Error: {e}, "
                          f"Environment: {environment}")
            return False
    
    async def _try_cached_token(self, token: str) -> Optional[Dict]:
        """Try to get token from cache with atomic blacklist checking."""
        cached_result = await self.token_cache.get_cached_token(token)
        if cached_result:
            # ATOMIC FIX: Check blacklist BEFORE accepting cached result
            # This prevents race conditions where token is cached but then blacklisted
            if await self._is_token_blacklisted_atomic(token):
                logger.warning("Token is blacklisted, removing from cache and rejecting")
                await self.token_cache.invalidate_cached_token(token)
                return None
        return cached_result
    
    async def _validate_with_circuit_breaker(self, token: str) -> Optional[Dict]:
        """Validate token using circuit breaker."""
        return await self.circuit_manager.call_with_breaker(
            self._validate_token_remote, token
        )
    
    async def _cache_validation_result(self, token: str, result: Optional[Dict]) -> Optional[Dict]:
        """Cache validation result if successful."""
        if result:
            await self.token_cache.cache_token(token, result)
        return result
    
    async def _handle_validation_error(self, token: str, error: Exception) -> Optional[Dict]:
        """Handle validation error with enhanced user notification and graceful degradation for integration tests."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Check if this is likely an inter-service authentication issue
        is_service_auth_issue = (
            not self.service_secret or 
            not self.service_id or
            "403" in error_msg or
            "forbidden" in error_msg.lower()
        )
        
        # Check if this is a connection/circuit breaker issue (common in integration tests)
        is_connection_issue = any(conn_err in error_msg.lower() for conn_err in [
            'connection', 'timeout', 'network', 'unreachable', 'circuit breaker', 
            'service_unavailable', 'all connection attempts failed'
        ])
        
        # ENHANCED: More appropriate logging levels for different scenarios
        if is_connection_issue:
            # For connection issues, use warning level (expected during integration tests without Docker)
            logger.warning(f"AUTH SERVICE CONNECTION ISSUE: {error_msg}")
            logger.warning(f"Auth service URL: {self.settings.base_url}")
            logger.warning("This is expected when running integration tests without Docker services")
        elif is_service_auth_issue:
            logger.critical("INTER-SERVICE AUTHENTICATION CRITICAL ERROR")
            logger.critical(f"Error: {error}")
            logger.critical(f"Auth service URL: {self.settings.base_url}")
            logger.critical(f"Service ID configured: {bool(self.service_id)} (value: {self.service_id or 'NOT SET'})")
            logger.critical(f"Service Secret configured: {bool(self.service_secret)}")
            logger.critical("CRITICAL ACTION REQUIRED: Configure SERVICE_ID and SERVICE_SECRET environment variables")
            logger.critical("BUSINESS IMPACT: Users may experience authentication failures or be unable to access the system")
        else:
            logger.error(f"USER AUTHENTICATION FAILURE: Token validation failed: {error}")
            logger.error(f"Auth service URL: {self.settings.base_url}")
            logger.error(f"Auth service enabled: {self.settings.enabled}")
        
        # SSOT COMPLIANCE: NO fallback validation - auth service is SSOT
        # Fallback mechanisms violate SSOT architecture and cause JWT secret mismatches
        logger.debug("SSOT COMPLIANCE: Rejecting fallback validation - auth service is single source of truth")
        
        # Handle connection/service errors with appropriate user-friendly messages
        if is_connection_issue:
            # Provide different severity for integration tests vs production
            is_test_env = self._is_test_environment()
            severity = "warning" if is_test_env else "error"
            
            return {
                "valid": False, 
                "error": "auth_service_unreachable", 
                "details": error_msg,
                "test_environment": is_test_env,
                "user_notification": {
                    "message": "Authentication service temporarily unavailable" if not is_test_env else "Auth service not available (test environment)",
                    "severity": severity,
                    "user_friendly_message": (
                        "We're having trouble with our authentication system. "
                        "Please try logging in again in a few moments. "
                        "If this persists, contact support."
                    ) if not is_test_env else "Authentication service is not running (expected in test environment without Docker)",
                    "action_required": "Try logging in again or contact support if the issue persists" if not is_test_env else "Start auth service or use real services for testing",
                    "support_code": f"AUTH_UNAVAIL_{datetime.now().strftime('%H%M%S')}"
                }
            }
        
        # For inter-service auth issues, provide clearer error with user notification
        if is_service_auth_issue:
            return {
                "valid": False, 
                "error": "inter_service_auth_failed",
                "details": "Service credentials not configured or invalid",
                "fix": "Set SERVICE_ID and SERVICE_SECRET environment variables",
                "user_notification": {
                    "message": "Service authentication configuration error",
                    "severity": "critical",
                    "user_friendly_message": (
                        "There's a configuration issue with our authentication system. "
                        "Our technical team has been notified. "
                        "Please try again later or contact support."
                    ),
                    "action_required": "Contact support if you continue to have login issues",
                    "support_code": f"SERVICE_AUTH_{datetime.now().strftime('%H%M%S')}"
                }
            }
        
        # For other errors, return validation failure - no fallback allowed per SSOT
        enhanced_result = {"valid": False}
        enhanced_result.update({
            "error": f"validation_failed_{error_type.lower()}",
            "details": error_msg,
            "user_notification": {
                "message": "Authentication validation failed",
                "severity": "error", 
                "user_friendly_message": (
                    "We couldn't validate your login credentials. "
                    "This might be a temporary issue. "
                    "Please try logging in again."
                ),
                "action_required": "Try logging in again. Contact support if the problem continues.",
                "support_code": f"AUTH_FAIL_{error_type}_{datetime.now().strftime('%H%M%S')}"
            }
        })
        
        return enhanced_result
    
    async def _try_validation_steps(self, token: str) -> Optional[Dict]:
        """Try validation with cache and circuit breaker."""
        cached = await self._try_cached_token(token)
        if cached:
            return cached
        result = await self._validate_with_circuit_breaker(token)
        return await self._cache_validation_result(token, result)
    
    async def _execute_token_validation(self, token: str) -> Optional[Dict]:
        """
        Execute token validation with error handling, connectivity checks, and circuit breaker.
        
        CRITICAL FIX: Enhanced with ultra-fast connectivity check to prevent 179-second
        WebSocket authentication delays in staging environment.
        """
        # CRITICAL FIX: Fast connectivity check before attempting validation
        # This prevents 179-second timeout waits that were blocking WebSocket connections
        connectivity_start = time.time()
        
        if not await self._check_auth_service_connectivity():
            connectivity_duration = time.time() - connectivity_start
            logger.warning(f"Auth service unreachable after {connectivity_duration:.2f}s - preventing WebSocket timeout")
            
            # CRITICAL: Fast-fail for WebSocket performance instead of waiting for timeouts
            return {
                "valid": False,
                "error": "auth_service_unreachable",
                "details": "Auth service is not available - check if service is running",
                "performance_metrics": {
                    "connectivity_check_duration_seconds": connectivity_duration,
                    "prevented_timeout_duration_seconds": 179.0,  # What we prevented
                    "websocket_performance_optimization": True
                },
                "user_notification": {
                    "message": "Authentication service temporarily unavailable",
                    "severity": "warning",
                    "user_friendly_message": "We're having trouble connecting to our authentication system. Please try again in a moment.",
                    "action_required": "Try again or check service status",
                    "support_code": f"AUTH_CONN_{datetime.now().strftime('%H%M%S')}"
                }
            }
        
        # SSOT COMPLIANCE: Only use auth service for validation - no local fallback
        # Local validation violates SSOT and causes JWT secret mismatches
        # Use circuit breaker to protect against auth service failures
        try:
            # Define the validation function for circuit breaker
            async def validate_with_service():
                result = await self._try_validation_steps(token)
                if result is None:
                    # Auth service rejected token - this is not a circuit breaker failure
                    logger.warning("Token validation returned None - auth service rejected the token")
                    raise ValueError("Token rejected by auth service")
                return result
            
            # Execute through circuit breaker
            try:
                result = await self.circuit_breaker.call(validate_with_service)
                return result
            except CircuitBreakerOpen:
                logger.warning("Circuit breaker is OPEN - auth service is temporarily unavailable")
                # Circuit is open, provide graceful degradation response
                return await self._handle_validation_error(token, Exception("Auth service circuit breaker open"))
            except ValueError as e:
                # Token was rejected (not a service failure) - no fallback allowed
                logger.debug(f"Token rejected by auth service: {e}")
                return {"valid": False, "error": "token_rejected", "details": str(e)}
                
        except Exception as e:
            return await self._handle_validation_error(token, e)
    
    async def validate_token_jwt(self, token: str) -> Optional[Dict]:
        """Validate access token with caching."""
        disabled_result = await self._check_auth_service_enabled(token)
        if disabled_result is not None:
            return disabled_result
        return await self._execute_token_validation(token)
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validate access token - canonical method for all token validation."""
        return await self.validate_token_jwt(token)
    
    async def validate_system_user_context(self, user_id: str, operation: str = "database_session") -> Optional[Dict]:
        """Validate system user operations using service-to-service authentication.
        
        DEPRECATED: Use validate_service_user_context() for new code.
        This method maintained for backward compatibility.
        
        Args:
            user_id: User ID to validate (should be "system" for system operations)
            operation: The operation being performed for logging/audit purposes
            
        Returns:
            Dict with validation result for system user
        """
        if user_id != "system":
            return {"valid": False, "error": "not_system_user", "details": f"User {user_id} is not a system user"}
        
        # Check if we have service credentials for system operations
        if not self.service_secret or not self.service_id:
            logger.error(
                f"SYSTEM USER AUTHENTICATION: Service credentials not configured. "
                f"System operations require SERVICE_ID and SERVICE_SECRET. "
                f"Operation: {operation}"
            )
            return {
                "valid": False, 
                "error": "missing_service_credentials",
                "details": "SERVICE_ID and SERVICE_SECRET required for system user operations",
                "fix": "Configure SERVICE_ID and SERVICE_SECRET environment variables"
            }
        
        # For system users, validate using service credentials instead of JWT tokens
        logger.info(
            f"SYSTEM USER AUTHENTICATION: Validating system user for operation '{operation}' "
            f"using service-to-service authentication"
        )
        
        return {
            "valid": True,
            "user_id": "system",
            "email": f"system@{self.service_id}",
            "permissions": ["system:*"],  # System users have all permissions
            "authentication_method": "service_to_service",
            "service_id": self.service_id,
            "operation": operation
        }
    
    async def validate_service_user_context(self, service_id: str, operation: str = "database_session") -> Optional[Dict]:
        """Validate service user operations using service-to-service authentication.
        
        CRITICAL FIX: New method that handles service authentication properly.
        This replaces hardcoded "system" user with proper service context.
        
        Args:
            service_id: Service ID to validate (e.g., "netra-backend")
            operation: The operation being performed for logging/audit purposes
            
        Returns:
            Dict with validation result for service user
        """
        # Validate service ID format
        if not service_id or not isinstance(service_id, str):
            return {"valid": False, "error": "invalid_service_id", "details": f"Invalid service ID: {service_id}"}
        
        # Check if we have service credentials for service operations
        if not self.service_secret or not self.service_id:
            logger.error(
                f"SERVICE USER AUTHENTICATION: Service credentials not configured. "
                f"Service operations require SERVICE_ID and SERVICE_SECRET. "
                f"Operation: {operation}, Service ID: {service_id}"
            )
            return {
                "valid": False, 
                "error": "missing_service_credentials",
                "details": "SERVICE_ID and SERVICE_SECRET required for service user operations",
                "fix": "Configure SERVICE_ID and SERVICE_SECRET environment variables"
            }
        
        # Validate that the requested service ID matches our configured service ID
        if service_id != self.service_id:
            logger.warning(
                f"SERVICE USER AUTHENTICATION: Service ID mismatch. "
                f"Requested: {service_id}, Configured: {self.service_id}, Operation: {operation}"
            )
            # Allow the validation but log the mismatch for security auditing
        
        # For service users, validate using service credentials instead of JWT tokens
        logger.info(
            f"SERVICE USER AUTHENTICATION: Validating service user for operation '{operation}' "
            f"using service-to-service authentication. Service ID: {service_id}"
        )
        
        return {
            "valid": True,
            "user_id": f"service:{service_id}",
            "email": f"service@{service_id}",
            "permissions": ["service:*"],  # Service users have service-level permissions
            "authentication_method": "service_to_service",
            "service_id": service_id,
            "operation": operation,
            "context": "internal_service_operation"
        }
    
    async def _build_validation_request(self, token: str) -> Dict:
        """Build validation request payload.
        
        CRITICAL FIX: Auth service expects token_type field per TokenRequest model.
        Default to 'access' token type for standard API authentication.
        """
        return {
            "token": token,
            "token_type": "access"  # Required by auth service TokenRequest model
        }
    
    async def _parse_validation_response(self, data: Dict) -> Dict:
        """Parse validation response data."""
        return {
            "valid": data.get("valid", False),
            "user_id": data.get("user_id"),
            "email": data.get("email"),
            "permissions": data.get("permissions", [])
        }
    
    async def _send_validation_request(self, client: httpx.AsyncClient, request_data: Dict) -> Optional[Dict]:
        """Send validation request with distributed tracing headers."""
        # Get headers with service auth
        headers = self._get_request_headers()
        
        # Log if service credentials are missing (common staging issue)
        if not self.service_secret:
            logger.warning("SERVICE_SECRET not configured - auth service communication may fail in staging/production")
        
        # Add detailed logging for staging debugging
        logger.info(f"Validating token with auth service at: {self.settings.base_url}")
        logger.debug(f"Request headers keys: {list(headers.keys())}")
        
        response = await client.post(
            "/auth/validate", 
            json=request_data,
            headers=headers
        )
        
        # Log the trace propagation for debugging
        logger.debug(f"Auth validation request sent with service auth")
        
        if response.status_code == 200:
            logger.info("Token validation successful")
            return await self._parse_validation_response(response.json())
        elif response.status_code == 401:
            # Check if this is an inter-service authentication failure
            is_service_auth_issue = not self.service_secret or not self.service_id
            
            if is_service_auth_issue:
                logger.error("INTER-SERVICE AUTH FAILURE: Missing service credentials")
                logger.error(f"Service ID configured: {bool(self.service_id)} (value: {self.service_id or 'NOT SET'})")
                logger.error(f"Service Secret configured: {bool(self.service_secret)}")
                logger.error("Fix: Set SERVICE_ID and SERVICE_SECRET environment variables")
            else:
                logger.warning("Auth service returned 401 - user token may be invalid or expired")
            
            logger.info(f"Auth service URL: {self.settings.base_url}")
            
            # Log response body for debugging
            try:
                error_detail = response.json()
                logger.warning(f"Auth service error details: {error_detail}")
            except:
                logger.warning(f"Auth service error response: {response.text}")
        elif response.status_code == 403:
            logger.error("INTER-SERVICE AUTH FAILURE: Service not authorized (403)")
            logger.error(f"Service ID: {self.service_id or 'NOT SET'}")
            logger.error(f"Service Secret configured: {bool(self.service_secret)}")
            logger.error("This typically means the service credentials are invalid or the service is not registered")
        return None
    
    async def _prepare_remote_validation(self, token: str):
        """Prepare remote validation components."""
        client = await self._get_client()
        request_data = await self._build_validation_request(token)
        return client, request_data
    
    async def _validate_token_remote(self, token: str) -> Optional[Dict]:
        """Remote token validation with atomic blacklist checking."""
        client, request_data = await self._prepare_remote_validation(token)
        try:
            # ATOMIC FIX: Use atomic blacklist check to prevent race conditions
            if await self._is_token_blacklisted_atomic(token):
                logger.warning("Token is blacklisted, rejecting remote validation")
                return None
            
            # If not blacklisted, proceed with normal validation
            return await self._send_validation_request(client, request_data)
        except Exception as e:
            logger.error(f"Remote validation error: {e}")
            raise
    
    async def _build_login_request(self, email: str, password: str, provider: str) -> Dict:
        """Build login request payload."""
        return {
            "email": email,
            "password": password,
            "provider": provider
        }
    
    async def _execute_login_request(self, request_data: Dict) -> Optional[Dict]:
        """Execute login request with enhanced error handling."""
        client = await self._get_client()
        headers = self._get_request_headers()
        
        logger.info(f"Executing login request to: {self.settings.base_url}/auth/login")
        logger.debug(f"Request headers keys: {list(headers.keys())}")
        
        try:
            response = await client.post("/auth/login", json=request_data, headers=headers)
            
            logger.info(f"Auth service login response: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info("Login request successful")
                    return response_data
                except Exception as e:
                    logger.error(f"Failed to parse login response as JSON: {e}")
                    logger.error(f"Response text: {response.text}")
                    return None
            else:
                logger.error(f"Auth service login failed: {response.status_code}")
                
                # Log response body for debugging
                try:
                    error_detail = response.json()
                    logger.error(f"Login error details: {error_detail}")
                except:
                    logger.error(f"Login error response: {response.text}")
                
                # Provide specific error context based on status code
                if response.status_code == 401:
                    logger.error("Login failed: Invalid credentials")
                elif response.status_code == 403:
                    logger.error("Login failed: Access forbidden - check service authentication")
                    logger.error(f"Service ID configured: {bool(self.service_id)} (value: {self.service_id or 'NOT SET'})")
                    logger.error(f"Service Secret configured: {bool(self.service_secret)}")
                elif response.status_code == 404:
                    logger.error("Login failed: Auth service login endpoint not found")
                    logger.error(f"Auth service URL: {self.settings.base_url}")
                elif response.status_code >= 500:
                    logger.error("Login failed: Auth service internal error")
                else:
                    logger.error(f"Login failed: Unexpected status code {response.status_code}")
                
                return None
                
        except Exception as e:
            logger.error(f"Login request failed with exception: {e}")
            logger.error(f"Auth service URL: {self.settings.base_url}")
            raise
    
    async def _attempt_login(self, email: str, password: str, provider: str) -> Optional[Dict]:
        """Attempt login with error handling."""
        request_data = await self._build_login_request(email, password, provider)
        try:
            return await self._execute_login_request(request_data)
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None

    async def _attempt_login_with_resilience(self, email: str, password: str, provider: str) -> Optional[Dict]:
        """Attempt login with enhanced resilience for staging environments."""
        import asyncio
        from netra_backend.app.core.config import get_config
        
        config = get_config()
        max_retries = 3 if config.environment == "staging" else 1
        base_delay = 1.0  # seconds
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Login attempt {attempt + 1}/{max_retries} for user: {email}")
                
                # Log auth service configuration for debugging
                logger.debug(f"Auth service URL: {self.settings.base_url}")
                logger.debug(f"Service credentials configured: ID={bool(self.service_id)}, Secret={bool(self.service_secret)}")
                
                result = await self._attempt_login(email, password, provider)
                
                if result:
                    logger.info(f"Login successful on attempt {attempt + 1} for user: {email}")
                    return result
                else:
                    logger.warning(f"Login attempt {attempt + 1} returned None for user: {email}")
                    
                    # If this is not the last attempt, continue to retry
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying login in {base_delay * (attempt + 1)} seconds...")
                        await asyncio.sleep(base_delay * (attempt + 1))
                        continue
                    else:
                        logger.error(f"All {max_retries} login attempts failed for user: {email}")
                        return None
                        
            except Exception as e:
                last_exception = e
                logger.error(f"Login attempt {attempt + 1} failed with exception: {e}")
                
                # Log additional context for debugging
                if hasattr(e, '__dict__'):
                    logger.debug(f"Exception details: {e.__dict__}")
                
                # If this is not the last attempt, continue to retry
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter for staging
                    delay = base_delay * (2 ** attempt) + (attempt * 0.5)
                    logger.info(f"Retrying login in {delay:.1f} seconds after error...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"All {max_retries} login attempts failed for user: {email}, last error: {e}")
                    return None
        
        return None
    
    async def login(self, email: str, password: str, 
                   provider: str = "local") -> Optional[Dict]:
        """User login through auth service."""
        if not self.settings.enabled:
            logger.error("Auth service is disabled - login unavailable")
            return None
        
        # Enhanced login with retry logic for staging environment
        return await self._attempt_login_with_resilience(email, password, provider)
    
    async def _build_logout_headers(self, token: str) -> Dict[str, str]:
        """Build logout request headers."""
        from netra_backend.app.core.auth_constants import HeaderConstants
        return {HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{token}"}
    
    async def _build_logout_payload(self, session_id: Optional[str]) -> Dict:
        """Build logout request payload."""
        return {"session_id": session_id} if session_id else {}
    
    async def _execute_logout_request(self, token: str, session_id: Optional[str]) -> bool:
        """Execute logout request."""
        client = await self._get_client()
        # Get headers with service auth and bearer token
        headers = self._get_request_headers(bearer_token=token)
        payload = await self._build_logout_payload(session_id)
        response = await client.post("/auth/logout", headers=headers, json=payload)
        return response.status_code == 200
    
    async def _process_logout_result(self, token: str, result: bool) -> bool:
        """Process logout result and invalidate cache."""
        await self.token_cache.invalidate_cached_token(token)
        return result
    
    async def _is_token_blacklisted_atomic(self, token: str) -> bool:
        """Atomic blacklist check to prevent race conditions."""
        if not self.settings.enabled:
            return False
        
        try:
            client = await self._get_client()
            request_data = {"token": token}
            
            # Get headers with service auth
            headers = self._get_request_headers()
            
            response = await client.post(
                "/auth/check-blacklist",
                json=request_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("blacklisted", False)
            return False
        except Exception as e:
            logger.error(f"Atomic blacklist check failed: {e}")
            # In case of error, assume token is not blacklisted to avoid false positives
            # The main validation will still happen at the auth service
            return False
    
    async def _check_token_blacklist(self, token: str) -> Optional[Dict]:
        """Legacy blacklist check method for backward compatibility."""
        is_blacklisted = await self._is_token_blacklisted_atomic(token)
        return {"blacklisted": is_blacklisted}
    
    async def _attempt_logout(self, token: str, session_id: Optional[str]) -> bool:
        """Attempt logout with error handling."""
        try:
            result = await self._execute_logout_request(token, session_id)
            return await self._process_logout_result(token, result)
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    async def logout(self, token: str, session_id: Optional[str] = None) -> bool:
        """User logout through auth service."""
        if not self.settings.enabled:
            return True
        return await self._attempt_logout(token, session_id)
    
    async def _build_refresh_request(self, refresh_token: str) -> Dict:
        """Build refresh token request payload."""
        return {"refresh_token": refresh_token}
    
    async def _execute_refresh_request(self, request_data: Dict) -> Optional[Dict]:
        """Execute refresh token request."""
        client = await self._get_client()
        headers = self._get_request_headers()
        response = await client.post("/auth/refresh", json=request_data, headers=headers)
        return response.json() if response.status_code == 200 else None
    
    async def _attempt_token_refresh(self, refresh_token: str) -> Optional[Dict]:
        """Attempt token refresh with error handling."""
        request_data = await self._build_refresh_request(refresh_token)
        try:
            return await self._execute_refresh_request(request_data)
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token."""
        if not self.settings.enabled:
            return None
        return await self._attempt_token_refresh(refresh_token)
    
    async def _check_service_token_prereqs(self) -> bool:
        """Check service token prerequisites."""
        if not self.settings.enabled:
            return False
        if not self.settings.is_service_secret_configured():
            logger.warning("Service secret not configured")
            return False
        return True
    
    async def _build_service_token_request(self) -> Dict:
        """Build service token request payload."""
        service_id, service_secret = self.settings.get_service_credentials()
        return {
            "service_id": service_id,
            "service_secret": service_secret
        }
    
    async def _execute_service_token_request(self, request_data: Dict) -> Optional[str]:
        """Execute service token request."""
        client = await self._get_client()
        headers = self._get_request_headers()
        response = await client.post("/auth/service-token", json=request_data, headers=headers)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    async def _attempt_service_token_creation(self) -> Optional[str]:
        """Attempt service token creation with error handling."""
        request_data = await self._build_service_token_request()
        try:
            return await self._execute_service_token_request(request_data)
        except Exception as e:
            logger.error(f"Service token creation failed: {e}")
            return None
    
    async def create_service_token(self) -> Optional[str]:
        """Get service-to-service auth token."""
        if not await self._check_service_token_prereqs():
            return None
        return await self._attempt_service_token_creation()
    
    async def hash_password(self, password: str) -> Optional[Dict]:
        """Hash password through auth service."""
        if not self.settings.enabled:
            logger.error("Auth service is required for password hashing")
            return None
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/hash-password", json={"password": password})
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            return None
    
    async def verify_password(self, plain_password: str, hashed_password: str) -> Optional[Dict]:
        """Verify password through auth service."""
        if not self.settings.enabled:
            logger.error("Auth service is required for password verification")
            return None
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/verify-password", json={
                "plain_password": plain_password,
                "hashed_password": hashed_password
            })
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return None
    
    async def create_token(self, token_data: Dict) -> Optional[Dict]:
        """Create access token through auth service."""
        if not self.settings.enabled:
            logger.error("Auth service is required for token creation")
            return None
        
        try:
            client = await self._get_client()
            response = await client.post("/auth/create-token", json=token_data)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            return None

    async def create_access_token(self, user_id: str, email: str = None) -> Optional[Dict]:
        """Create access token for user through auth service."""
        token_data = {
            "user_id": user_id,
            "email": email or f"{user_id}@example.com",
            "token_type": "access"
        }
        return await self.create_token(token_data)
    
    # SSOT COMPLIANCE: _local_validate method REMOVED
    # All validation must go through auth service to maintain SSOT architecture
    # Fallback validation causes JWT secret mismatches and violates SSOT principles
    
    def _is_test_environment(self) -> bool:
        """Check if we're in a test environment.
        
        SSOT compliance: Uses common utility for consistent detection.
        """
        from netra_backend.app.core.project_utils import is_test_environment
        return is_test_environment()
    
    def _is_production_environment(self) -> bool:
        """Check if we're in a production environment.
        
        Returns:
            bool: True if in production environment
        """
        try:
            return is_production()
        except Exception:
            # If we can't determine environment, assume production for security
            return True
    
    def _is_valid_test_token(self, jwt_token: str) -> bool:
        """Basic validation for test JWT tokens."""
        try:
            # Basic JWT structure check (header.payload.signature)
            parts = jwt_token.split('.')
            if len(parts) != 3:
                return False
            
            # Check if it's a test token pattern
            test_patterns = [
                "test_signature",
                "test_user", 
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"  # Standard test JWT header
            ]
            
            return any(pattern in jwt_token for pattern in test_patterns)
        except Exception:
            return False
    

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
    
    def detect_environment(self):
        """Detect current environment from environment variables."""
        env_str = get_current_environment()
        # Convert string to Environment enum for backward compatibility
        for env in Environment:
            if env.value == env_str:
                return env
        # Default to development if unknown
        return Environment.DEVELOPMENT
    
    def get_oauth_config(self) -> OAuthConfig:
        """Get OAuth configuration for current environment."""
        environment = self.detect_environment()
        return self.oauth_generator.get_oauth_config(environment)
    
    # RBAC Methods for Role-Based Access Control
    
    async def login_with_request(self, request) -> Optional[Dict]:
        """User login through auth service with LoginRequest object."""
        # PRODUCTION SECURITY: Ensure auth service is always required in production
        if self._is_production_environment() and not self.settings.enabled:
            logger.error("PRODUCTION SECURITY: Auth service is required in production")
            raise Exception("Authentication service is required in production environment")
        
        if not self.settings.enabled:
            # Auth service is disabled - this should only occur in testing environments
            # Return proper error instead of mock authentication
            logger.error("Auth service is disabled - authentication unavailable")
            return None
            
        # Handle both dict and LoginRequest object
        if hasattr(request, 'email'):
            email = request.email
            password = request.password or ""
            provider = getattr(request, 'provider', 'local')
        else:
            email = request.get('email')
            password = request.get('password', '')
            provider = request.get('provider', 'local')
        
        result = await self._attempt_login(email, password, provider)
        
        if result:
            # Ensure the response has the expected structure
            return type('LoginResponse', (), {
                'access_token': result.get('access_token', ''),
                'refresh_token': result.get('refresh_token'),
                'role': result.get('role', 'guest'),
                'user_id': result.get('user_id', ''),
                'token_type': result.get('token_type', 'Bearer'),
                'expires_in': result.get('expires_in', 3600)
            })()
        return None
    
    
    def _check_permission_match(self, required_permission: str, user_permissions: List[str]) -> bool:
        """Check if user has the required permission."""
        for perm in user_permissions:
            # Exact match
            if perm == required_permission:
                return True
            # Wildcard match (e.g., "agents:*" matches "agents:read")
            if perm.endswith(":*") and required_permission.startswith(perm[:-1]):
                return True
            # System wildcard
            if perm == "system:*":
                return True
        return False
    
    def _resource_to_permission(self, resource: str, action: str) -> str:
        """Convert resource and action to permission format."""
        # Extract permission from resource path
        # e.g., "/api/users" + "delete" -> "users:delete"
        # e.g., "/api/system/config" + "write" -> "system:write"
        resource_parts = resource.strip('/').split('/')
        
        if 'api' in resource_parts:
            # Remove 'api' prefix
            resource_parts = [p for p in resource_parts if p != 'api']
        
        if resource_parts:
            resource_type = resource_parts[0]  # e.g., "users", "system", "agents"
            return f"{resource_type}:{action}"
        
        return f"unknown:{action}"
        
    async def check_authorization(self, token: str, resource: str, action: str) -> Dict:
        """Check authorization for resource and action."""
        if not self.settings.enabled:
            # Auth service is disabled - return unauthorized instead of mock authorization
            logger.error("Auth service disabled - authorization unavailable")
            return type('AuthorizationResult', (), {
                'authorized': False,
                'reason': 'Auth service disabled',
                'permissions': []
            })()
        
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=token)
            response = await client.post("/auth/check-authorization", json={
                "token": token,
                "resource": resource,
                "action": action
            }, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return type('AuthorizationResult', (), {
                    'authorized': result.get('authorized', False),
                    'reason': result.get('reason', 'Unknown'),
                    'permissions': result.get('permissions', [])
                })()
            else:
                logger.warning(f"Authorization check returned {response.status_code}")
                return type('AuthorizationResult', (), {
                    'authorized': False,
                    'reason': 'Service error',
                    'permissions': []
                })()
        except Exception as e:
            logger.error(f"Authorization check failed: {e}")
            return type('AuthorizationResult', (), {
                'authorized': False,
                'reason': f'Error: {str(e)}',
                'permissions': []
            })()
    
    async def check_permission(self, token: str, permission: str) -> Dict:
        """Check if token has specific permission."""
        if not self.settings.enabled:
            # Auth service is disabled - return no permission instead of mock authorization
            logger.error("Auth service disabled - permission checking unavailable")
            return type('PermissionResult', (), {
                'has_permission': False,
                'reason': 'Auth service disabled'
            })()
        
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=token)
            response = await client.post("/auth/check-permission", json={
                "token": token,
                "permission": permission
            }, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return type('PermissionResult', (), {
                    'has_permission': result.get('has_permission', False),
                    'reason': result.get('reason', 'Unknown')
                })()
            else:
                logger.warning(f"Permission check returned {response.status_code}")
                return type('PermissionResult', (), {
                    'has_permission': False,
                    'reason': 'Service error'
                })()
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return type('PermissionResult', (), {
                'has_permission': False,
                'reason': f'Error: {str(e)}'
            })()
    
    async def make_api_call(self, token: str, endpoint: str) -> Dict:
        """Make rate-limited API call."""
        if not self.settings.enabled:
            # Auth service disabled - deny API calls
            logger.error("Auth service disabled - API calls unavailable")
            return type('ApiCallResult', (), {'success': False, 'reason': 'Auth service disabled'})()
            
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=token)
            response = await client.post("/auth/api-call", json={
                "token": token,
                "endpoint": endpoint
            }, headers=headers)
            
            if response.status_code == 200:
                return type('ApiCallResult', (), {'success': True})()
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded")
            else:
                logger.warning(f"API call failed with status {response.status_code}")
                return type('ApiCallResult', (), {'success': False})()
        except Exception as e:
            if "rate limit" in str(e).lower():
                raise
            logger.error(f"API call failed: {e}")
            return type('ApiCallResult', (), {'success': False})()
    
    async def create_agent(self, token: str, agent_name: str) -> Optional[Dict]:
        """Create agent with resource limits check."""
        if not self.settings.enabled:
            # Auth service disabled - deny agent creation
            logger.error("Auth service disabled - agent creation unavailable")
            return None
            
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=token)
            response = await client.post("/auth/create-agent", json={
                "token": token,
                "agent_name": agent_name
            }, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return type('Agent', (), {
                    'id': result.get('id', ''),
                    'name': agent_name
                })()
            else:
                logger.warning(f"Agent creation failed with status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Agent creation failed: {e}")
            return None
    
    async def delete_agent(self, token: str, agent_id: str) -> bool:
        """Delete agent."""
        if not self.settings.enabled:
            logger.error("Auth service disabled - agent deletion unavailable")
            return False
            
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=token)
            response = await client.delete(f"/auth/agents/{agent_id}", headers=headers)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Agent deletion failed: {e}")
            return False
    
    async def validate_token_for_service(self, token: str, service_name: str) -> Dict:
        """Validate token for specific service."""
        if not self.settings.enabled:
            # Auth service disabled - deny service validation
            logger.error("Auth service disabled - service token validation unavailable")
            return type('ServiceValidationResult', (), {
                'valid': False,
                'role': 'guest',
                'permissions': [],
                'reason': 'Auth service disabled'
            })()
        
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=token)
            response = await client.post("/auth/validate-service-token", json={
                "token": token,
                "service_name": service_name
            }, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return type('ServiceValidationResult', (), {
                    'valid': result.get('valid', False),
                    'role': result.get('role', 'guest'),
                    'permissions': result.get('permissions', [])
                })()
            else:
                logger.warning(f"Service token validation failed with status {response.status_code}")
                return type('ServiceValidationResult', (), {
                    'valid': False,
                    'role': 'guest',
                    'permissions': []
                })()
        except Exception as e:
            logger.error(f"Service token validation failed: {e}")
            return type('ServiceValidationResult', (), {
                'valid': False,
                'role': 'guest',
                'permissions': []
            })()
    
    async def update_user_role(self, token: str, user_id: str, new_role: str) -> Dict:
        """Update user role (admin only)."""
        if not self.settings.enabled:
            # Auth service disabled - deny role updates
            logger.error("Auth service disabled - user role updates unavailable")
            raise Exception("Auth service disabled: Cannot update user role")
        
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=token)
            response = await client.put(f"/auth/users/{user_id}/role", 
                json={"role": new_role},
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                raise Exception("Unauthorized: Cannot update user role")
            else:
                raise Exception("Failed to update user role")
        except Exception as e:
            logger.error(f"Role update failed: {e}")
            raise
    
    async def get_user_info(self, token: str, user_id: str) -> Dict:
        """Get user information."""
        if not self.settings.enabled:
            # Auth service disabled - return minimal user info
            logger.error("Auth service disabled - user info unavailable")
            return type('UserInfo', (), {
                'user_id': user_id,
                'email': '',
                'role': 'guest',
                'permissions': [],
                'reason': 'Auth service disabled'
            })()
        
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=token)
            response = await client.get(f"/auth/users/{user_id}", headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return type('UserInfo', (), {
                    'user_id': result.get('user_id', ''),
                    'email': result.get('email', ''),
                    'role': result.get('role', 'guest'),
                    'permissions': result.get('permissions', [])
                })()
            else:
                logger.warning(f"Get user info failed with status {response.status_code}")
                return type('UserInfo', (), {
                    'user_id': user_id,
                    'email': '',
                    'role': 'guest',
                    'permissions': []
                })()
        except Exception as e:
            logger.error(f"Get user info failed: {e}")
            return type('UserInfo', (), {
                'user_id': user_id,
                'email': '',
                'role': 'guest',
                'permissions': []
            })()
    
    async def create_impersonation_token(self, admin_token: str, target_user_id: str, 
                                       duration_minutes: int) -> Optional[str]:
        """Create impersonation token (admin only)."""
        if not self.settings.enabled:
            # Auth service disabled - deny impersonation
            logger.error("Auth service disabled - impersonation unavailable")
            raise Exception("Auth service disabled: Cannot create impersonation token")
        
        try:
            client = await self._get_client()
            headers = self._get_request_headers(bearer_token=admin_token)
            response = await client.post("/auth/impersonate", json={
                "target_user_id": target_user_id,
                "duration_minutes": duration_minutes
            }, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('impersonation_token')
            elif response.status_code == 403:
                raise Exception("Unauthorized: Cannot create impersonation token")
            else:
                logger.warning(f"Impersonation token creation failed with status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Impersonation token creation failed: {e}")
            if "unauthorized" in str(e).lower():
                raise
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token with structured response."""
        result = await self._attempt_token_refresh(refresh_token)
        
        if result:
            return type('RefreshResponse', (), {
                'access_token': result.get('access_token', ''),
                'refresh_token': result.get('refresh_token', refresh_token),
                'token_type': result.get('token_type', 'Bearer'),
                'expires_in': result.get('expires_in', 3600)
            })()
        return None
    
    def blacklist_token(self, token: str) -> bool:
        """Blacklist token (synchronous method for backward compatibility)."""
        # For now, return True as a placeholder - in a real implementation
        # this would need to communicate with the auth service synchronously
        logger.warning("blacklist_token called - synchronous token blacklisting not fully implemented")
        return True
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions by user ID."""
        if not self.settings.enabled:
            return []
        
        try:
            client = await self._get_client()
            response = await client.get(f"/auth/users/{user_id}/permissions")
            if response.status_code == 200:
                result = response.json()
                return result.get("permissions", [])
            return []
        except Exception as e:
            logger.error(f"Get user permissions failed: {e}")
            return []
    
    async def revoke_user_sessions(self, user_id: str) -> Dict[str, bool]:
        """Revoke all sessions for a user."""
        if not self.settings.enabled:
            return {"success": False, "message": "Auth service disabled"}
        
        try:
            client = await self._get_client()
            response = await client.post(f"/auth/users/{user_id}/revoke-sessions")
            if response.status_code == 200:
                return {"success": True, "message": "Sessions revoked"}
            return {"success": False, "message": "Failed to revoke sessions"}
        except Exception as e:
            logger.error(f"Revoke user sessions failed: {e}")
            return {"success": False, "message": str(e)}
    
    def health_check(self) -> bool:
        """Health check (synchronous method for backward compatibility)."""
        return self.settings.enabled
    
    async def validate_token_with_resilience(self, token: str, operation_type: AuthOperationType = AuthOperationType.TOKEN_VALIDATION) -> Dict[str, Any]:
        """
        Validate token with resilience mechanisms using built-in circuit breaker.
        
        This method provides the same interface as the deprecated auth_resilience_service
        but uses the existing circuit breaker and caching functionality built into AuthServiceClient.
        
        Returns:
            Dict with validation result and resilience metadata
        """
        import time
        start_time = time.time()
        
        try:
            # Use the existing validate_token method which already has circuit breaker protection
            result = await self.validate_token(token)
            
            if result and result.get("valid"):
                return {
                    "success": True,
                    "valid": True,
                    "user_id": result.get("user_id"),
                    "email": result.get("email"), 
                    "permissions": result.get("permissions", []),
                    "resilience_mode": "normal",
                    "source": "auth_service",
                    # fallback_used removed - SSOT compliance
                    "response_time": time.time() - start_time
                }
            else:
                return {
                    "success": False,
                    "valid": False,
                    "error": "Token validation failed",
                    "resilience_mode": "normal",
                    "source": "auth_service",
                    # fallback_used removed - SSOT compliance
                    "response_time": time.time() - start_time
                }
                
        except Exception as e:
            logger.error(f"Token validation with resilience failed: {e}")
            
            # Try cached validation as fallback
            cached_result = await self.token_cache.get_cached_token(token)
            if cached_result and cached_result.get("valid"):
                logger.warning("Using cached token validation due to auth service unavailability")
                return {
                    "success": True,
                    "valid": True,
                    "user_id": cached_result.get("user_id"),
                    "email": cached_result.get("email"),
                    "permissions": cached_result.get("permissions", []),
                    "resilience_mode": "direct_auth_service",
                    "source": "auth_service",
                    # fallback_used removed - SSOT compliance
                    "response_time": time.time() - start_time,
                    "warning": "Using cached validation due to auth service error"
                }
            
            return {
                "success": False,
                "valid": False,
                "error": f"Auth service unavailable: {str(e)}",
                "resilience_mode": "failed",
                "source": "error",
                # fallback_used removed - SSOT compliance
                "response_time": time.time() - start_time
            }


# Global client instance
auth_client = AuthServiceClient()

# Compatibility alias for integration tests (Issue #308)
AuthClientCore = AuthServiceClient  # Main class alias for integration test compatibility


# Convenience function for backward compatibility with auth_resilience_service
async def validate_token_with_resilience(token: str, operation_type: AuthOperationType = AuthOperationType.TOKEN_VALIDATION) -> Dict[str, Any]:
    """Validate token using authentication resilience mechanisms."""
    return await auth_client.validate_token_with_resilience(token, operation_type)


# Backward compatibility function that returns the consolidated auth client
def get_auth_resilience_service():
    """Get the authentication resilience service (now consolidated into AuthServiceClient)."""
    return auth_client


# Global function for getting auth resilience health - simplified version
async def get_auth_resilience_health() -> Dict[str, Any]:
    """Get authentication resilience health status."""
    circuit_manager = auth_client.circuit_manager
    circuit_status = circuit_manager.breaker.get_status() if hasattr(circuit_manager, 'breaker') else {"state": "unknown"}
    
    return {
        "service": "authentication_resilience", 
        "status": "healthy" if auth_client.settings.enabled else "degraded",
        "current_mode": "normal" if auth_client.settings.enabled else "disabled",
        "auth_service_available": auth_client.settings.enabled,
        "emergency_bypass_active": False,
        "metrics": {
            "total_attempts": 0,  # Would need to track this
            "success_rate": 1.0,
            "cache_hit_rate": 0.0,
            "consecutive_failures": 0,
        },
        "circuit_breaker": circuit_status,
        "cache_status": {
            "cached_tokens": len(auth_client.token_cache._token_cache) if hasattr(auth_client.token_cache, '_token_cache') else 0,
            "max_tokens": 10000,
        }
    }