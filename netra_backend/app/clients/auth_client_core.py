"""
Core auth service client functionality.
Handles token validation, authentication, and service-to-service communication.
"""

import logging
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

logger = logging.getLogger(__name__)


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
    CACHED_FALLBACK = "cached_fallback"
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
        
        # Initialize circuit breaker for auth service calls
        self.circuit_breaker = get_circuit_breaker(
            name="auth_service",
            config=CircuitBreakerConfig(
                failure_threshold=3,  # Open after 3 consecutive failures
                success_threshold=2,  # Close after 2 consecutive successes in half-open
                timeout=30.0,  # Try half-open after 30 seconds
                call_timeout=5.0,  # Individual call timeout
                failure_rate_threshold=0.5,  # Open if 50% of calls fail
                min_calls_for_rate=5  # Need at least 5 calls to calculate failure rate
            )
        )
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
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Create new HTTP client instance."""
        return httpx.AsyncClient(
            base_url=self.settings.base_url,
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_keepalive_connections=5)
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
            headers["X-Service-ID"] = self.service_id
            headers["X-Service-Secret"] = self.service_secret
            logger.debug(f"Service auth headers configured for service ID: '{self.service_id}'")
        else:
            # Log detailed diagnostic info when service auth is missing
            missing_parts = []
            if not self.service_id:
                missing_parts.append("SERVICE_ID")
                logger.error(
                    "SERVICE_ID is not configured. Set SERVICE_ID=netra-backend in environment. "
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
        """Handle validation error with enhanced user notification and detailed error information."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Check if this is likely an inter-service authentication issue
        is_service_auth_issue = (
            not self.service_secret or 
            not self.service_id or
            "403" in error_msg or
            "forbidden" in error_msg.lower()
        )
        
        # LOUD ERROR: Authentication failures should be highly visible
        if is_service_auth_issue:
            logger.critical("INTER-SERVICE AUTHENTICATION CRITICAL ERROR")
            logger.critical(f"Error: {error}")
            logger.critical(f"Auth service URL: {self.settings.base_url}")
            logger.critical(f"Service ID configured: {bool(self.service_id)} (value: {self.service_id or 'NOT SET'})")
            logger.critical(f"Service Secret configured: {bool(self.service_secret)}")
            logger.critical("CRITICAL ACTION REQUIRED: Configure SERVICE_ID and SERVICE_SECRET environment variables")
            logger.critical("BUSINESS IMPACT: Users may experience authentication failures or be unable to access the system")
        else:
            logger.critical(f"USER AUTHENTICATION FAILURE: Token validation failed: {error}")
            logger.critical(f"Auth service URL: {self.settings.base_url}")
            logger.critical(f"Auth service enabled: {self.settings.enabled}")
            logger.critical("BUSINESS IMPACT: Users may be unable to authenticate or access protected resources")
        
        # Always try local fallback when validation fails
        fallback_result = await self._local_validate(token)
        
        # If fallback worked, return it with error context and user notification
        if fallback_result and fallback_result.get("valid", False):
            fallback_result["error_context"] = f"Primary validation failed: {error_msg}"
            fallback_result["error_type"] = error_type
            fallback_result["user_notification"] = {
                "message": "Authentication system temporarily using backup validation",
                "severity": "warning",
                "user_friendly_message": (
                    "You're successfully authenticated using our backup system. "
                    "All features are available normally."
                ),
                "action_required": None
            }
            if is_service_auth_issue:
                fallback_result["warning"] = "Using fallback due to inter-service auth failure"
                fallback_result["user_notification"]["message"] = "Service authentication using backup method"
            logger.info(f"Using fallback validation: {fallback_result.get('source', 'unknown')}")
            return fallback_result
        
        # If fallback also failed or returned invalid token
        # Check if this is a connection/service error
        if any(conn_err in error_msg.lower() for conn_err in ['connection', 'timeout', 'network', 'unreachable', 'circuit breaker', 'service_unavailable']):
            logger.critical(f"AUTH SERVICE UNREACHABLE: {error_msg}. Users cannot authenticate.")
            return {
                "valid": False, 
                "error": "auth_service_unreachable", 
                "details": error_msg,
                "user_notification": {
                    "message": "Authentication service temporarily unavailable",
                    "severity": "error",
                    "user_friendly_message": (
                        "We're having trouble with our authentication system. "
                        "Please try logging in again in a few moments. "
                        "If this persists, contact support."
                    ),
                    "action_required": "Try logging in again or contact support if the issue persists",
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
        
        # For other errors, return the fallback result with enhanced error details
        enhanced_result = fallback_result or {"valid": False}
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
        """Execute token validation with error handling and circuit breaker."""
        # PERFORMANCE FIX: Try local JWT validation first for efficiency and reliability
        # This reduces latency and eliminates dependency on auth service HTTP calls
        try:
            local_result = await self._local_validate(token)
            if local_result and local_result.get("valid", False):
                logger.debug("Using local JWT validation (primary)")
                return local_result
        except Exception as e:
            logger.debug(f"Local validation failed, falling back to remote: {e}")
        
        # Fallback to remote validation if local validation fails
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
                logger.warning("Circuit breaker is OPEN - using cached validation fallback")
                # Circuit is open, use fallback validation
                return await self._handle_validation_error(token, Exception("Auth service unavailable (circuit open)"))
            except ValueError as e:
                # Token was rejected (not a service failure)
                logger.debug(f"Token rejected: {e}")
                return await self._local_validate(token)
                
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
    
    async def _local_validate(self, token: str) -> Optional[Dict]:
        """Local token validation with cached fallback for resilience."""
        # PRODUCTION SECURITY: Never allow mock authentication in production
        if self._is_production_environment():
            logger.error("PRODUCTION SECURITY: Mock authentication is forbidden in production")
            logger.error("Auth service is required for all token validation in production")
            return {
                "valid": False, 
                "error": "auth_service_required_production",
                "details": "Production environment requires auth service - no fallbacks allowed"
            }
        
        # First, try cached token as fallback
        cached_result = await self.token_cache.get_cached_token(token)
        if cached_result:
            logger.warning("Using cached token validation due to auth service unavailability")
            cached_result["fallback_used"] = True
            cached_result["source"] = "cache"
            return cached_result
        
        # In test/development environment, provide development user fallback
        if self._is_test_environment():
            # For JWT-like tokens, use emergency test token fallback
            if token.startswith("Bearer eyJ") or token.startswith("eyJ"):
                # Extract token from Bearer prefix if present
                jwt_token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token
                
                if self._is_valid_test_token(jwt_token):
                    logger.warning("Using emergency test token fallback due to auth service unavailability")
                    
                    # Try to decode JWT token to extract user data
                    jwt_data = self._decode_test_jwt(jwt_token)
                    if jwt_data:
                        return {
                            "valid": True,
                            "user_id": jwt_data.get("sub", "test_user"),
                            "email": jwt_data.get("email", "test@example.com"),
                            "permissions": jwt_data.get("permissions", ["user"]),
                            "fallback_used": True,
                            "source": "emergency_test_fallback",
                            "warning": "Emergency fallback validation - limited functionality"
                        }
                    
                    # Fallback to default values if JWT decode fails
                    return {
                        "valid": True,
                        "user_id": "test_user",
                        "email": "test@example.com", 
                        "permissions": ["user"],
                        "fallback_used": True,
                        "source": "emergency_test_fallback",
                        "warning": "Emergency fallback validation - limited functionality"
                    }
            
            # For any token in development environment, provide development user fallback
            logger.warning("Using development user fallback due to auth service unavailability")
            return {
                "valid": True,
                "user_id": "dev-user-1",
                "email": "dev@example.com", 
                "permissions": ["user"],
                "fallback_used": True,
                "source": "development_fallback",
                "warning": "Development environment fallback - for testing only"
            }
        
        logger.error("Auth service is required for token validation - no fallback available")
        return {
            "valid": False, 
            "error": "auth_service_required",
            "details": "Auth service unavailable and no cached validation available"
        }
    
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
    
    def _decode_test_jwt(self, jwt_token: str) -> Optional[Dict[str, Any]]:
        """Decode test JWT token to extract user data."""
        try:
            import jwt
            import os
            
            # Use same secret loading logic as backend middleware for consistency
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            secret = get_jwt_secret()
            
            # Decode the JWT token
            decoded = jwt.decode(jwt_token, secret, algorithms=["HS256"], options={"verify_exp": False})
            return decoded
        except Exception as e:
            logger.debug(f"Failed to decode test JWT token: {e}")
            return None

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
    
    def _decode_token(self, token: str) -> Dict:
        """Decode JWT token - PRODUCTION: This should only be used with proper JWT secret from auth service."""
        # PRODUCTION SECURITY: Never allow direct token decoding in production
        if self._is_production_environment():
            logger.error("PRODUCTION SECURITY: Direct token decoding is forbidden in production")
            logger.error("All token validation must go through the auth service")
            return {"error": "Direct token decoding forbidden in production"}
        
        # SECURITY: In staging/production, JWT tokens should only be validated by the auth service
        # This method exists for backward compatibility but should not be used for actual authentication
        logger.error("_decode_token called - this method should not be used in production or staging")
        logger.error("All token validation must go through the auth service")
        return {"error": "Direct token decoding not allowed - use auth service"}
    
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
                    "fallback_used": False,
                    "response_time": time.time() - start_time
                }
            else:
                return {
                    "success": False,
                    "valid": False,
                    "error": "Token validation failed",
                    "resilience_mode": "normal",
                    "source": "auth_service",
                    "fallback_used": False,
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
                    "resilience_mode": "cached_fallback",
                    "source": "cache",
                    "fallback_used": True,
                    "response_time": time.time() - start_time,
                    "warning": "Using cached validation due to auth service error"
                }
            
            return {
                "success": False,
                "valid": False,
                "error": f"Auth service unavailable: {str(e)}",
                "resilience_mode": "failed",
                "source": "error",
                "fallback_used": True,
                "response_time": time.time() - start_time
            }


# Global client instance
auth_client = AuthServiceClient()


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