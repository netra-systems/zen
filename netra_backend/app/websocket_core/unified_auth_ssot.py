"""
SSOT: Unified WebSocket Authentication
CRITICAL: Golden Path restoration - Single source of truth for all WebSocket authentication

Business Impact: $500K+ ARR - Enables complete user login → AI response flow
Technical Impact: Consolidates 6 conflicting auth pathways into 1 canonical implementation

ISSUE #1176 REMEDIATION: jwt-auth subprotocol as primary, Authorization header as fallback
ISSUE #886 REMEDIATION: GCP Authorization header stripping workaround
"""

import asyncio
from typing import Optional, Dict, Any
from fastapi import WebSocket, HTTPException
from dataclasses import dataclass

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)

@dataclass
class WebSocketAuthResult:
    """Standardized authentication result for WebSocket connections."""
    success: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    permissions: Optional[list] = None
    error_message: Optional[str] = None
    auth_method: Optional[str] = None  # "jwt-auth-subprotocol", "authorization-header", "query-param-fallback"
    
    # Aliases for backward compatibility
    @property
    def is_authenticated(self) -> bool:
        """Alias for success for backward compatibility"""
        return self.success
    
    @property
    def error_code(self) -> Optional[str]:
        """Alias for error_message for backward compatibility"""
        return self.error_message
    
    @property
    def bypass_reason(self) -> Optional[str]:
        """Bypass reason (used in permissive mode)"""
        return getattr(self, '_bypass_reason', None)
        
    def set_bypass_reason(self, reason: str):
        """Set bypass reason for permissive mode"""
        self._bypass_reason = reason

class UnifiedWebSocketAuthenticator:
    """
    SSOT: Unified WebSocket Authentication
    
    Consolidates all authentication pathways into a single, reliable implementation.
    Implements infrastructure workarounds for production environment constraints.
    """
    
    def __init__(self):
        # Lazy load auth service to prevent circular imports
        self._auth_service = None
        
    @property
    def auth_service(self):
        """Lazy load auth service to prevent import issues"""
        if self._auth_service is None:
            try:
                from netra_backend.app.services.unified_authentication_service import get_unified_auth_service
                self._auth_service = get_unified_auth_service()
            except ImportError as e:
                logger.warning(f"Auth service not available: {e}")
                self._auth_service = None
        return self._auth_service
        
    async def authenticate_websocket_connection(self, websocket: WebSocket) -> WebSocketAuthResult:
        """
        CRITICAL: Single authentication pathway for all WebSocket connections.
        
        Authentication Priority (reliability-first approach):
        1. jwt-auth subprotocol (most reliable in GCP)
        2. Authorization header (may be stripped by load balancer)
        3. Query parameter fallback (infrastructure workaround)
        4. E2E bypass for testing (controlled environments only)
        
        Returns:
            WebSocketAuthResult: Standardized auth result with method used
        """
        # METHOD 1: jwt-auth subprotocol (PRIMARY - most reliable)
        jwt_token = self._extract_jwt_from_subprotocol(websocket)
        if jwt_token:
            result = await self._validate_jwt_token(jwt_token, "jwt-auth-subprotocol")
            if result.success:
                logger.info(f"✅ WebSocket auth SUCCESS via jwt-auth subprotocol for user {result.user_id}")
                return result
                
        # METHOD 2: Authorization header (SECONDARY - may be stripped)
        jwt_token = self._extract_jwt_from_auth_header(websocket)
        if jwt_token:
            result = await self._validate_jwt_token(jwt_token, "authorization-header")
            if result.success:
                logger.info(f"✅ WebSocket auth SUCCESS via Authorization header for user {result.user_id}")
                return result
                
        # METHOD 3: Query parameter fallback (INFRASTRUCTURE WORKAROUND)
        jwt_token = self._extract_jwt_from_query_params(websocket)
        if jwt_token:
            result = await self._validate_jwt_token(jwt_token, "query-param-fallback")
            if result.success:
                logger.info(f"✅ WebSocket auth SUCCESS via query parameter fallback for user {result.user_id}")
                return result
                
        # METHOD 4: E2E bypass (TESTING ONLY)
        if self._is_e2e_test_environment():
            bypass_result = await self._handle_e2e_bypass(websocket)
            if bypass_result.success:
                logger.warning(f"⚠️ WebSocket auth BYPASS for E2E testing: {bypass_result.user_id}")
                return bypass_result
        
        # ALL METHODS FAILED - LOG COMPREHENSIVE FAILURE INFO
        logger.error("❌ WebSocket authentication FAILED - all methods exhausted")
        logger.error(f"   - Headers available: {list(websocket.headers.keys())}")
        logger.error(f"   - Subprotocol: {websocket.headers.get('sec-websocket-protocol', 'NONE')}")
        logger.error(f"   - Auth header: {'PRESENT' if websocket.headers.get('authorization') else 'MISSING'}")
        logger.error(f"   - Query string: {websocket.query_string.decode()}")
        
        return WebSocketAuthResult(
            success=False,
            error_message="Authentication failed: No valid JWT token found via any method",
            auth_method="none"
        )
    
    def _extract_jwt_from_subprotocol(self, websocket: WebSocket) -> Optional[str]:
        """Extract JWT from Sec-WebSocket-Protocol header (jwt-auth.TOKEN format)"""
        subprotocol = websocket.headers.get("sec-websocket-protocol", "")
        logger.debug(f"🔑 Checking subprotocol: {subprotocol}")
        
        # Support multiple subprotocol formats for compatibility
        for prefix in ["jwt-auth.", "jwt.", "bearer."]:
            if subprotocol.startswith(prefix):
                token = subprotocol[len(prefix):]
                logger.debug(f"🔑 JWT extracted from subprotocol: {prefix}*** (token length: {len(token)})")
                return token
                
        return None
    
    def _extract_jwt_from_auth_header(self, websocket: WebSocket) -> Optional[str]:
        """Extract JWT from Authorization header (Bearer TOKEN format)"""
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            logger.debug("🔑 JWT extracted from Authorization header")
            return token
        return None
    
    def _extract_jwt_from_query_params(self, websocket: WebSocket) -> Optional[str]:
        """INFRASTRUCTURE WORKAROUND: Extract JWT from query parameters"""
        from urllib.parse import parse_qs
        
        query_string = websocket.query_string.decode()
        if not query_string:
            return None
            
        query_params = parse_qs(query_string)
        
        # Check multiple query parameter names for flexibility
        for param_name in ["token", "jwt", "auth_token", "access_token"]:
            if param_name in query_params and query_params[param_name]:
                token = query_params[param_name][0]  # Get first value
                logger.debug(f"🔑 JWT extracted from query parameter: {param_name}")
                return token
                
        return None
    
    async def _validate_jwt_token(self, token: str, auth_method: str) -> WebSocketAuthResult:
        """
        JWT Migration Phase 2: Validate JWT token using auth service APIs.
        """
        from shared.isolated_environment import get_env

        try:
            env = get_env()
            # Check Phase 2 migration feature flag
            phase_2_enabled = env.get("ENABLE_JWT_MIGRATION_PHASE_2", "true").lower() == "true"

            if phase_2_enabled:
                logger.info(f"JWT PHASE 2: Using auth service APIs for {auth_method}")
                return await self._validate_jwt_via_auth_service_apis(token, auth_method)
            else:
                logger.info(f"JWT PHASE 2: Using legacy unified auth service for {auth_method}")
                return await self._validate_jwt_via_legacy_service(token, auth_method)

        except Exception as e:
            logger.error(f"❌ JWT validation error via {auth_method}: {str(e)}")
            return WebSocketAuthResult(
                success=False,
                error_message=f"JWT validation error: {str(e)}",
                auth_method=auth_method
            )

    async def _validate_jwt_via_auth_service_apis(self, token: str, auth_method: str) -> WebSocketAuthResult:
        """Use auth service APIs for validation (Phase 2)."""
        try:
            # Use auth client validate_token_jwt API directly
            from netra_backend.app.clients.auth_client_core import auth_client

            validation_result = await auth_client.validate_token_jwt(token)

            if validation_result and validation_result.get('valid'):
                return WebSocketAuthResult(
                    success=True,
                    user_id=validation_result.get('user_id'),
                    email=validation_result.get('email'),
                    permissions=validation_result.get('permissions', []),
                    auth_method=f"{auth_method}-phase2"
                )
            else:
                # Fall back to legacy service on API failure
                logger.warning(f"⚠️ Auth service API validation failed via {auth_method}, trying legacy service")
                return await self._validate_jwt_via_legacy_service(token, auth_method)

        except Exception as e:
            logger.error(f"Auth service API validation error: {e}")
            # Fall back to legacy service
            return await self._validate_jwt_via_legacy_service(token, auth_method)

    async def _validate_jwt_via_legacy_service(self, token: str, auth_method: str) -> WebSocketAuthResult:
        """Use legacy unified auth service for validation."""
        try:
            # Fallback JWT validation if auth service not available
            if self.auth_service is None:
                return await self._fallback_jwt_validation(token, auth_method)

            # Use SSOT auth service for validation (correct method name)
            from netra_backend.app.services.unified_authentication_service import AuthenticationContext, AuthenticationMethod

            auth_result = await self.auth_service.authenticate_token(
                token=token,
                context=AuthenticationContext.WEBSOCKET,
                method=AuthenticationMethod.JWT_TOKEN
            )

            if auth_result.success:
                return WebSocketAuthResult(
                    success=True,
                    user_id=auth_result.user_id,
                    email=auth_result.email,
                    permissions=auth_result.permissions,
                    auth_method=f"{auth_method}-legacy"
                )
            else:
                # If auth service is unreachable, fall back to JWT validation
                if "auth_service_unreachable" in str(auth_result.error):
                    logger.info(f"🔄 Auth service unreachable, falling back to JWT validation")
                    return await self._fallback_jwt_validation(token, f"{auth_method}-fallback")

                logger.warning(f"⚠️ JWT validation failed via {auth_method}: {auth_result.error}")
                return WebSocketAuthResult(
                    success=False,
                    error_message=f"JWT validation failed: {auth_result.error}",
                    auth_method=auth_method
                )

        except Exception as e:
            logger.error(f"❌ Legacy service JWT validation error via {auth_method}: {str(e)}")
            return WebSocketAuthResult(
                success=False,
                error_message=f"Legacy JWT validation error: {str(e)}",
                auth_method=auth_method
            )
    
    async def _fallback_jwt_validation(self, token: str, auth_method: str) -> WebSocketAuthResult:
        """
        JWT Migration Phase 2: Fallback validation using auth service APIs.

        This method now uses auth service APIs instead of local JWT decoding.
        """
        from shared.isolated_environment import get_env

        try:
            env = get_env()
            # Check Phase 2 migration feature flag
            phase_2_enabled = env.get("ENABLE_JWT_MIGRATION_PHASE_2", "true").lower() == "true"

            if phase_2_enabled:
                logger.info(f"JWT PHASE 2 FALLBACK: Using auth service APIs for {auth_method}")
                return await self._fallback_via_auth_service_apis(token, auth_method)
            else:
                logger.info(f"JWT PHASE 2 FALLBACK: Using legacy JWT decoding for {auth_method}")
                return await self._fallback_via_legacy_jwt_decoding(token, auth_method)

        except Exception as e:
            logger.error(f"❌ Phase 2 fallback JWT validation failed: {str(e)}")
            return WebSocketAuthResult(
                success=False,
                error_message=f"Phase 2 fallback JWT validation failed: {str(e)}",
                auth_method=auth_method
            )

    async def _fallback_via_auth_service_apis(self, token: str, auth_method: str) -> WebSocketAuthResult:
        """Use auth service APIs for fallback validation (Phase 2)."""
        try:
            # Try to get auth client and use validate_token_jwt API
            from netra_backend.app.clients.auth_client_core import auth_client

            validation_result = await auth_client.validate_token_jwt(token)

            if validation_result and validation_result.get('valid'):
                return WebSocketAuthResult(
                    success=True,
                    user_id=validation_result.get('user_id'),
                    email=validation_result.get('email'),
                    permissions=validation_result.get('permissions', []),
                    auth_method=f"{auth_method}-phase2-fallback"
                )
            else:
                # If auth service API fails, try legacy path as last resort
                logger.warning(f"Auth service API fallback failed, trying legacy JWT decode")
                return await self._fallback_via_legacy_jwt_decoding(token, auth_method)

        except Exception as e:
            logger.error(f"Auth service API fallback error: {e}")
            # Fall back to legacy as last resort
            return await self._fallback_via_legacy_jwt_decoding(token, auth_method)

    async def _fallback_via_legacy_jwt_decoding(self, token: str, auth_method: str) -> WebSocketAuthResult:
        """Legacy JWT decoding fallback (Phase 2 compatibility)."""
        try:
            import jwt
            from shared.jwt_secret_manager import get_unified_jwt_secret

            secret = get_unified_jwt_secret()
            decoded = jwt.decode(token, secret, algorithms=['HS256'])

            return WebSocketAuthResult(
                success=True,
                user_id=decoded.get('sub'),
                email=decoded.get('email'),
                permissions=decoded.get('permissions', []),
                auth_method=f"{auth_method}-legacy-fallback"
            )

        except Exception as e:
            logger.error(f"❌ Legacy JWT validation failed: {str(e)}")
            return WebSocketAuthResult(
                success=False,
                error_message=f"Legacy JWT validation failed: {str(e)}",
                auth_method=auth_method
            )
    
    def _is_e2e_test_environment(self) -> bool:
        """Check if running in E2E test environment where bypass is allowed"""
        try:
            from shared.isolated_environment import get_env
            
            env = get_env()
            environment = env.get('ENVIRONMENT', '').lower()
            
            # Only allow bypass in specific test environments
            return environment in ['test', 'development', 'local']
        except Exception as e:
            logger.debug(f"Environment check failed: {e}")
            return False
    
    async def _handle_e2e_bypass(self, websocket: WebSocket) -> WebSocketAuthResult:
        """TESTING ONLY: Handle E2E authentication bypass"""
        # Check for E2E bypass headers
        e2e_user_id = websocket.headers.get("x-e2e-user-id")
        e2e_bypass = websocket.headers.get("x-e2e-bypass") == "true"
        
        if e2e_bypass and e2e_user_id:
            logger.warning(f"🚨 E2E BYPASS: Creating test user context for {e2e_user_id}")
            
            return WebSocketAuthResult(
                success=True,
                user_id=e2e_user_id,
                email=f"{e2e_user_id}@e2e.test",
                permissions=["read", "write", "chat", "websocket", "agent:execute"],
                auth_method="e2e-bypass"
            )
        
        return WebSocketAuthResult(success=False, error_message="E2E bypass not configured", auth_method="e2e-bypass")
    
    async def authenticate_manual(
        self, 
        token: Optional[str],
        headers: Dict[str, Any],
        environment: Optional[str],
        permissive: bool = False
    ) -> WebSocketAuthResult:
        """
        Manual authentication for testing and validation purposes.
        
        This method supports authentication without a WebSocket connection,
        useful for unit tests and validation scenarios.
        """
        try:
            if not token:
                if permissive and self._should_allow_bypass():
                    logger.warning("🚨 PERMISSIVE MODE: Allowing authentication without token")
                    result = WebSocketAuthResult(
                        success=True,
                        user_id="test-user-permissive",
                        email="test@permissive.local",
                        permissions=["read", "write", "chat", "websocket", "agent:execute"],
                        auth_method="permissive-bypass"
                    )
                    result.set_bypass_reason("no-token-permissive-mode")
                    return result
                
                return WebSocketAuthResult(
                    success=False,
                    error_message="No token provided",
                    auth_method="manual"
                )
            
            # Validate token with auth service
            auth_result = await self.auth_service.validate_token(token)
            
            if auth_result["valid"]:
                return WebSocketAuthResult(
                    success=True,
                    user_id=auth_result["user_id"],
                    email=auth_result.get("email"),
                    permissions=auth_result.get("permissions", ["read", "write", "chat", "websocket", "agent:execute"]),
                    auth_method="manual-jwt"
                )
            else:
                return WebSocketAuthResult(
                    success=False,
                    error_message=auth_result.get("error", "Token validation failed"),
                    auth_method="manual-jwt"
                )
                
        except Exception as e:
            logger.error(f"Manual authentication error: {e}")
            
            if permissive and self._should_allow_bypass():
                logger.warning(f"🚨 PERMISSIVE MODE: Allowing failed authentication - {str(e)}")
                result = WebSocketAuthResult(
                    success=True,
                    user_id="test-user-error-bypass",
                    email="error@permissive.local",
                    permissions=["read", "write", "chat", "websocket", "agent:execute"],
                    auth_method="permissive-error-bypass"
                )
                result.set_bypass_reason(f"error-bypass: {str(e)}")
                return result
            
            return WebSocketAuthResult(
                success=False,
                error_message=f"Authentication error: {str(e)}",
                auth_method="manual-error"
            )

# SSOT EXPORT: Single authenticator instance
websocket_authenticator = UnifiedWebSocketAuthenticator()

async def authenticate_websocket(
    websocket: WebSocket = None,
    token: Optional[str] = None,
    headers: Optional[Dict[str, Any]] = None,
    environment: Optional[str] = None,
    permissive: bool = False
) -> WebSocketAuthResult:
    """
    SSOT FUNCTION: Primary entry point for all WebSocket authentication
    
    This function should be used by all WebSocket routes and handlers.
    Replaces all other authentication methods.
    
    Args:
        websocket: WebSocket connection (if available)
        token: JWT token for authentication
        headers: HTTP headers dict
        environment: Environment name for permissive mode logic
        permissive: Enable permissive mode for testing
    """
    if websocket is not None:
        # Use WebSocket-based authentication (primary path)
        return await websocket_authenticator.authenticate_websocket_connection(websocket)
    else:
        # Use manual authentication (for testing/validation)
        return await websocket_authenticator.authenticate_manual(
            token=token,
            headers=headers or {},
            environment=environment,
            permissive=permissive
        )