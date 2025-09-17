"""
SSOT: Unified WebSocket Authentication
CRITICAL: Golden Path restoration - Single source of truth for all WebSocket authentication

Business Impact: $500K+ ARR - Enables complete user login → AI response flow
Technical Impact: Consolidates 6 conflicting auth pathways into 1 canonical implementation

ISSUE #1176 REMEDIATION: jwt-auth subprotocol as primary, Authorization header as fallback
ISSUE #886 REMEDIATION: GCP Authorization header stripping workaround
"""

import asyncio
import json
import secrets
import time
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


@dataclass
class AuthTicket:
    """Standardized auth ticket structure for temporary authentication."""
    ticket_id: str
    user_id: str
    email: str
    permissions: list
    expires_at: float
    created_at: float
    single_use: bool = True
    metadata: Optional[Dict[str, Any]] = None


class AuthTicketManager:
    """
    SSOT: Authentication Ticket Manager for Issue #1293

    Provides secure, time-limited tickets for authentication workflows that require
    temporary access tokens. Integrates with Redis for scalable ticket storage.

    Business Impact: Enables secure temporary authentication for CI/CD, webhooks,
    and automated testing without exposing long-lived credentials.
    """

    def __init__(self):
        """Initialize the auth ticket manager."""
        self._redis_manager = None
        self._ticket_prefix = "auth:ticket:"
        self._default_ttl = 300  # 5 minutes default
        self._max_ttl = 3600     # 1 hour maximum

    @property
    def redis_manager(self):
        """Lazy load Redis manager to prevent circular imports."""
        if self._redis_manager is None:
            try:
                from netra_backend.app.redis_manager import redis_manager
                self._redis_manager = redis_manager
            except ImportError as e:
                logger.warning(f"Redis manager not available for ticket storage: {e}")
                self._redis_manager = None
        return self._redis_manager

    async def generate_ticket(
        self,
        user_id: str,
        email: str,
        permissions: list = None,
        ttl_seconds: int = None,
        single_use: bool = True,
        metadata: Dict[str, Any] = None
    ) -> AuthTicket:
        """
        Generate a new authentication ticket.

        Args:
            user_id: User ID to authenticate as
            email: User email for the ticket
            permissions: List of permissions for the ticket
            ttl_seconds: Time to live in seconds (default: 300, max: 3600)
            single_use: Whether ticket is single-use (default: True)
            metadata: Additional metadata to store with ticket

        Returns:
            AuthTicket: Generated ticket with unique ID
        """
        # Validate and sanitize inputs
        if not user_id or not email:
            raise ValueError("user_id and email are required for ticket generation")

        ttl_seconds = ttl_seconds or self._default_ttl
        ttl_seconds = min(ttl_seconds, self._max_ttl)  # Enforce maximum TTL
        permissions = permissions or ["read", "chat", "websocket"]

        # Generate secure ticket ID
        ticket_id = self._generate_secure_ticket_id()

        # Create ticket
        current_time = time.time()
        ticket = AuthTicket(
            ticket_id=ticket_id,
            user_id=user_id,
            email=email,
            permissions=permissions,
            expires_at=current_time + ttl_seconds,
            created_at=current_time,
            single_use=single_use,
            metadata=metadata or {}
        )

        # Store in Redis
        success = await self._store_ticket(ticket, ttl_seconds)
        if not success:
            logger.error(f"Failed to store ticket {ticket_id} in Redis")
            raise RuntimeError("Failed to store authentication ticket")

        logger.info(f"Generated auth ticket {ticket_id} for user {user_id} (TTL: {ttl_seconds}s)")
        return ticket

    async def validate_ticket(self, ticket_id: str) -> Optional[AuthTicket]:
        """
        Validate and retrieve a ticket by ID.

        Args:
            ticket_id: The ticket ID to validate

        Returns:
            AuthTicket if valid and not expired, None otherwise
        """
        if not ticket_id:
            logger.debug("Empty ticket ID provided for validation")
            return None

        # Retrieve ticket from Redis
        ticket = await self._retrieve_ticket(ticket_id)
        if not ticket:
            logger.debug(f"Ticket {ticket_id} not found in storage")
            return None

        # Check expiration
        current_time = time.time()
        if current_time > ticket.expires_at:
            logger.info(f"Ticket {ticket_id} has expired")
            await self._delete_ticket(ticket_id)  # Clean up expired ticket
            return None

        # If single-use, delete after validation
        if ticket.single_use:
            await self._delete_ticket(ticket_id)
            logger.debug(f"Single-use ticket {ticket_id} consumed and deleted")

        logger.info(f"Ticket {ticket_id} validated for user {ticket.user_id}")
        return ticket

    async def revoke_ticket(self, ticket_id: str) -> bool:
        """
        Revoke a ticket before its expiration.

        Args:
            ticket_id: The ticket ID to revoke

        Returns:
            bool: True if ticket was revoked, False if not found
        """
        success = await self._delete_ticket(ticket_id)
        if success:
            logger.info(f"Ticket {ticket_id} revoked successfully")
        else:
            logger.debug(f"Ticket {ticket_id} not found for revocation")
        return success

    async def cleanup_expired_tickets(self) -> int:
        """
        Clean up expired tickets from storage.

        Returns:
            int: Number of tickets cleaned up
        """
        if not self.redis_manager:
            logger.debug("Redis not available - cannot cleanup expired tickets")
            return 0

        try:
            # Get all ticket keys
            pattern = f"{self._ticket_prefix}*"
            keys = await self.redis_manager.keys(pattern)

            cleaned_count = 0
            current_time = time.time()

            for key in keys:
                ticket_data = await self.redis_manager.get(key)
                if ticket_data:
                    try:
                        ticket_dict = json.loads(ticket_data)
                        if ticket_dict.get('expires_at', 0) < current_time:
                            await self.redis_manager.delete(key)
                            cleaned_count += 1
                    except json.JSONDecodeError:
                        # Invalid ticket data, clean it up
                        await self.redis_manager.delete(key)
                        cleaned_count += 1

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired tickets")

            return cleaned_count

        except Exception as e:
            logger.error(f"Error during ticket cleanup: {e}")
            return 0

    def _generate_secure_ticket_id(self) -> str:
        """Generate a cryptographically secure ticket ID."""
        return secrets.token_urlsafe(32)  # 256-bit entropy

    async def _store_ticket(self, ticket: AuthTicket, ttl_seconds: int) -> bool:
        """Store ticket in Redis with TTL."""
        if not self.redis_manager:
            logger.warning("Redis not available - cannot store ticket")
            return False

        try:
            # Convert ticket to JSON
            ticket_data = {
                'ticket_id': ticket.ticket_id,
                'user_id': ticket.user_id,
                'email': ticket.email,
                'permissions': ticket.permissions,
                'expires_at': ticket.expires_at,
                'created_at': ticket.created_at,
                'single_use': ticket.single_use,
                'metadata': ticket.metadata
            }
            ticket_json = json.dumps(ticket_data)

            # Store with Redis TTL
            key = f"{self._ticket_prefix}{ticket.ticket_id}"
            return await self.redis_manager.set(key, ticket_json, ex=ttl_seconds)

        except Exception as e:
            logger.error(f"Error storing ticket {ticket.ticket_id}: {e}")
            return False

    async def _retrieve_ticket(self, ticket_id: str) -> Optional[AuthTicket]:
        """Retrieve ticket from Redis."""
        if not self.redis_manager:
            logger.debug("Redis not available - cannot retrieve ticket")
            return None

        try:
            key = f"{self._ticket_prefix}{ticket_id}"
            ticket_data = await self.redis_manager.get(key)

            if not ticket_data:
                return None

            # Parse JSON data
            ticket_dict = json.loads(ticket_data)

            # Reconstruct AuthTicket
            return AuthTicket(
                ticket_id=ticket_dict['ticket_id'],
                user_id=ticket_dict['user_id'],
                email=ticket_dict['email'],
                permissions=ticket_dict['permissions'],
                expires_at=ticket_dict['expires_at'],
                created_at=ticket_dict['created_at'],
                single_use=ticket_dict['single_use'],
                metadata=ticket_dict.get('metadata', {})
            )

        except Exception as e:
            logger.error(f"Error retrieving ticket {ticket_id}: {e}")
            return None

    async def _delete_ticket(self, ticket_id: str) -> bool:
        """Delete ticket from Redis."""
        if not self.redis_manager:
            logger.debug("Redis not available - cannot delete ticket")
            return False

        try:
            key = f"{self._ticket_prefix}{ticket_id}"
            return await self.redis_manager.delete(key)
        except Exception as e:
            logger.error(f"Error deleting ticket {ticket_id}: {e}")
            return False

class UnifiedWebSocketAuthenticator:
    """
    SSOT: Unified WebSocket Authentication
    
    Consolidates all authentication pathways into a single, reliable implementation.
    Implements infrastructure workarounds for production environment constraints.
    """
    
    def __init__(self):
        # Lazy load auth service to prevent circular imports
        self._auth_service = None
        # Initialize ticket manager
        self._ticket_manager = AuthTicketManager()
        
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

        # METHOD 4: Ticket-based authentication (ISSUE #1293)
        ticket_id = self._extract_ticket_from_query_params(websocket)
        if ticket_id:
            result = await self._validate_ticket_auth(ticket_id, "ticket-auth")
            if result.success:
                logger.info(f"✅ WebSocket auth SUCCESS via ticket authentication for user {result.user_id}")
                return result
                
        # METHOD 5: E2E bypass (TESTING ONLY)
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

    def _extract_ticket_from_query_params(self, websocket: WebSocket) -> Optional[str]:
        """Extract authentication ticket from query parameters (Issue #1293)"""
        from urllib.parse import parse_qs

        query_string = websocket.query_string.decode()
        if not query_string:
            return None

        query_params = parse_qs(query_string)

        # Check for ticket parameter
        for param_name in ["ticket", "auth_ticket", "ticket_id"]:
            if param_name in query_params and query_params[param_name]:
                ticket_id = query_params[param_name][0]  # Get first value
                logger.debug(f"🎫 Ticket extracted from query parameter: {param_name}")
                return ticket_id

        return None

    async def _validate_ticket_auth(self, ticket_id: str, auth_method: str) -> WebSocketAuthResult:
        """
        Validate authentication ticket and return WebSocket auth result.

        Args:
            ticket_id: The ticket ID to validate
            auth_method: Authentication method identifier

        Returns:
            WebSocketAuthResult: Authentication result
        """
        try:
            # Validate ticket using ticket manager
            ticket = await self._ticket_manager.validate_ticket(ticket_id)

            if ticket is None:
                logger.debug(f"❌ Ticket validation failed - ticket not found or expired: {ticket_id}")
                return WebSocketAuthResult(
                    success=False,
                    error_message="Invalid or expired authentication ticket",
                    auth_method=auth_method
                )

            # Create successful auth result from ticket
            logger.info(f"✅ Ticket authentication successful for user {ticket.user_id}")
            return WebSocketAuthResult(
                success=True,
                user_id=ticket.user_id,
                email=ticket.email,
                permissions=ticket.permissions,
                auth_method=auth_method
            )

        except Exception as e:
            logger.error(f"❌ Ticket validation error: {str(e)}")
            return WebSocketAuthResult(
                success=False,
                error_message=f"Ticket validation error: {str(e)}",
                auth_method=auth_method
            )

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
                # Legacy path removed - return failure
                logger.error(f"JWT PHASE 2: Legacy unified auth service removed for {auth_method}")
                return WebSocketAuthResult(
                    success=False,
                    error_message="Legacy authentication path has been removed",
                    auth_method=auth_method
                )

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
                # Legacy service removed - return failure
                logger.error(f"❌ Auth service API validation failed via {auth_method}, legacy service removed")
                return WebSocketAuthResult(
                    success=False,
                    error_message="Authentication failed and legacy service has been removed",
                    auth_method=auth_method
                )

        except Exception as e:
            logger.error(f"Auth service API validation error: {e}")
            # Fall back to legacy service
            return await self._validate_jwt_via_legacy_service(token, auth_method)

    

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

    def _should_allow_bypass(self) -> bool:
        """
        SSOT COMPLIANCE: Control when authentication bypass is allowed.

        Returns True only in controlled test environments.
        """
        try:
            from shared.isolated_environment import get_env

            env = get_env()
            environment = env.get('ENVIRONMENT', '').lower()

            # Only allow bypass in specific test environments
            allowed_envs = ['test', 'development', 'local']
            return environment in allowed_envs

        except Exception as e:
            logger.debug(f"Environment check failed: {e}")
            return False

# SSOT EXPORT: Single authenticator instance
websocket_authenticator = UnifiedWebSocketAuthenticator()

# SSOT EXPORT: Single ticket manager instance (Issue #1293)
ticket_manager = AuthTicketManager()

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


# ============================================================================
# TICKET AUTHENTICATION API (Issue #1293)
# ============================================================================

async def generate_auth_ticket(
    user_id: str,
    email: str,
    permissions: list = None,
    ttl_seconds: int = None,
    single_use: bool = True,
    metadata: Dict[str, Any] = None
) -> AuthTicket:
    """
    Generate a new authentication ticket for temporary access.

    ISSUE #1293: Provides secure, time-limited tickets for authentication
    workflows without exposing long-lived credentials.

    Args:
        user_id: User ID to authenticate as
        email: User email for the ticket
        permissions: List of permissions (default: ["read", "chat", "websocket"])
        ttl_seconds: Time to live in seconds (default: 300, max: 3600)
        single_use: Whether ticket is single-use (default: True)
        metadata: Additional metadata to store with ticket

    Returns:
        AuthTicket: Generated ticket with unique ID

    Raises:
        ValueError: If user_id or email is empty
        RuntimeError: If ticket storage fails
    """
    return await ticket_manager.generate_ticket(
        user_id=user_id,
        email=email,
        permissions=permissions,
        ttl_seconds=ttl_seconds,
        single_use=single_use,
        metadata=metadata
    )


async def validate_auth_ticket(ticket_id: str) -> Optional[AuthTicket]:
    """
    Validate an authentication ticket by ID.

    ISSUE #1293: Validates ticket authenticity, expiration, and handles
    single-use ticket consumption.

    Args:
        ticket_id: The ticket ID to validate

    Returns:
        AuthTicket if valid and not expired, None otherwise
    """
    return await ticket_manager.validate_ticket(ticket_id)


async def revoke_auth_ticket(ticket_id: str) -> bool:
    """
    Revoke an authentication ticket before its expiration.

    ISSUE #1293: Allows immediate ticket invalidation for security purposes.

    Args:
        ticket_id: The ticket ID to revoke

    Returns:
        bool: True if ticket was revoked, False if not found
    """
    return await ticket_manager.revoke_ticket(ticket_id)


async def cleanup_expired_tickets() -> int:
    """
    Clean up expired tickets from storage.

    ISSUE #1293: Maintenance function to remove expired tickets and
    free up Redis storage space.

    Returns:
        int: Number of tickets cleaned up
    """
    return await ticket_manager.cleanup_expired_tickets()


def get_ticket_manager() -> AuthTicketManager:
    """
    Get the global ticket manager instance.

    ISSUE #1293: Provides access to the SSOT ticket manager for
    advanced use cases.

    Returns:
        AuthTicketManager: The global ticket manager instance
    """
    return ticket_manager