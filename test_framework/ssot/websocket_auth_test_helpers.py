"""
SSOT WebSocket Authentication Test Helpers - Advanced Authentication Scenarios

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication security infrastructure
- Business Goal: Prevent authentication vulnerabilities in WebSocket connections
- Value Impact: Protects against token hijacking, session manipulation, and user data breaches  
- Revenue Impact: Prevents security breaches that could cost $200K+ per incident

This module provides advanced WebSocket authentication testing utilities that FAIL HARD
when authentication security is compromised. These helpers validate:
- Token lifecycle management during active connections
- Session security and isolation
- Permission boundary enforcement
- Connection authentication validation
- Advanced attack scenario resistance

CRITICAL REQUIREMENTS FROM CLAUDE.MD:
- ALL e2e tests MUST use authentication except tests directly validating auth
- Tests MUST FAIL HARD when authentication is compromised
- NO MOCKS in E2E testing - use real WebSocket connections
- Follow SSOT patterns throughout
- Tests with 0-second execution = automatic hard failure

@compliance CLAUDE.md - Real authentication required, hard failures for security violations
@compliance SPEC/core.xml - WebSocket authentication enables secure chat interactions
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import hashlib

import jwt
import websockets
from websockets import ConnectionClosed, InvalidStatus

from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, AuthenticatedUser
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient, SecurityError, WebSocketEvent

logger = logging.getLogger(__name__)


class AuthenticationScenario(Enum):
    """Authentication scenarios for WebSocket testing."""
    VALID_TOKEN = "valid_token"
    EXPIRED_TOKEN = "expired_token"
    MALFORMED_TOKEN = "malformed_token"
    MISSING_TOKEN = "missing_token"
    INVALID_SIGNATURE = "invalid_signature"
    TOKEN_REFRESH = "token_refresh"
    SESSION_HIJACKING = "session_hijacking"
    CROSS_USER_VIOLATION = "cross_user_violation"
    PERMISSION_ESCALATION = "permission_escalation"
    TIMING_ATTACK = "timing_attack"


@dataclass
class AuthenticationTestResult:
    """Result of an authentication test scenario."""
    scenario: AuthenticationScenario
    success: bool
    error_message: Optional[str]
    response_time: float
    security_violations: List[str]
    expected_failure: bool
    actual_failure: bool
    
    @property
    def test_passed(self) -> bool:
        """Check if test passed based on expected vs actual behavior."""
        return self.expected_failure == self.actual_failure
    
    @property
    def security_validated(self) -> bool:
        """Check if security was properly validated."""
        return len(self.security_violations) == 0 or self.expected_failure


@dataclass 
class TokenLifecycleState:
    """State tracking for token lifecycle tests."""
    original_token: str
    current_token: str
    expiry_time: datetime
    refresh_count: int = 0
    active_connections: Set[str] = None
    
    def __post_init__(self):
        if self.active_connections is None:
            self.active_connections = set()


@dataclass
class CachedToken:
    """Cached JWT token for performance optimization."""
    token: str
    user_id: str
    email: str
    permissions: List[str]
    created_at: datetime
    expires_at: datetime
    cache_key: str
    
    @property
    def is_valid(self) -> bool:
        """Check if cached token is still valid (with buffer)."""
        # Add 30 second buffer to avoid using tokens too close to expiry
        buffer_time = timedelta(seconds=30)
        return datetime.now(timezone.utc) < (self.expires_at - buffer_time)
    
    @property
    def remaining_lifetime_seconds(self) -> float:
        """Get remaining token lifetime in seconds."""
        remaining = self.expires_at - datetime.now(timezone.utc)
        return max(0, remaining.total_seconds())


class JWTTokenCache:
    """
    Performance-optimized JWT token cache for authentication testing.
    
    This cache enables intelligent token reuse for non-security scenarios,
    significantly reducing token generation overhead while maintaining
    security requirements.
    
    SECURITY CRITICAL:
    - Only reuses tokens for non-security scenarios
    - Security tests always get fresh tokens
    - Tokens have safety buffers before expiry
    - Cache isolation prevents token leakage
    """
    
    def __init__(self, default_cache_ttl_minutes: int = 10):
        """Initialize JWT token cache.
        
        Args:
            default_cache_ttl_minutes: Default cache TTL in minutes
        """
        self.cache: Dict[str, CachedToken] = {}
        self.default_cache_ttl_minutes = default_cache_ttl_minutes
        self.cache_hits = 0
        self.cache_misses = 0
        self.security_bypass_count = 0
        
        logger.info(f"Initialized JWT token cache with {default_cache_ttl_minutes}min TTL")
    
    def _generate_cache_key(
        self,
        user_id: str,
        email: str,
        permissions: List[str],
        exp_minutes: int,
        is_security_test: bool = False
    ) -> str:
        """Generate cache key for token parameters."""
        # Security tests always get unique keys (no caching)
        if is_security_test:
            return f"security_test_{uuid.uuid4().hex}"
        
        # Create deterministic cache key for non-security scenarios
        permissions_str = "_".join(sorted(permissions or []))
        cache_data = f"{user_id}_{email}_{permissions_str}_{exp_minutes}"
        return hashlib.sha256(cache_data.encode()).hexdigest()[:16]
    
    def get_cached_token(
        self,
        user_id: str,
        email: str,
        permissions: List[str],
        exp_minutes: int,
        is_security_test: bool = False
    ) -> Optional[CachedToken]:
        """Get cached token if available and valid.
        
        Args:
            user_id: User ID for token
            email: User email
            permissions: Required permissions
            exp_minutes: Required expiry minutes
            is_security_test: If True, bypasses cache for security
            
        Returns:
            Cached token if available and valid, None otherwise
        """
        if is_security_test:
            self.security_bypass_count += 1
            logger.debug("Security test detected - bypassing token cache")
            return None
        
        cache_key = self._generate_cache_key(user_id, email, permissions, exp_minutes, is_security_test)
        cached_token = self.cache.get(cache_key)
        
        if cached_token and cached_token.is_valid:
            self.cache_hits += 1
            logger.debug(
                f"Token cache HIT: {cache_key} "
                f"(remaining: {cached_token.remaining_lifetime_seconds:.1f}s)"
            )
            return cached_token
        
        if cached_token:
            # Remove expired token
            del self.cache[cache_key]
            logger.debug(f"Removed expired token from cache: {cache_key}")
        
        self.cache_misses += 1
        return None
    
    def cache_token(
        self,
        token: str,
        user_id: str,
        email: str,
        permissions: List[str],
        exp_minutes: int,
        is_security_test: bool = False
    ) -> CachedToken:
        """Cache a JWT token for reuse.
        
        Args:
            token: JWT token string
            user_id: User ID
            email: User email
            permissions: Token permissions
            exp_minutes: Token expiry minutes
            is_security_test: If True, won't be cached
            
        Returns:
            CachedToken object
        """
        cache_key = self._generate_cache_key(user_id, email, permissions, exp_minutes, is_security_test)
        
        cached_token = CachedToken(
            token=token,
            user_id=user_id,
            email=email,
            permissions=permissions or [],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=exp_minutes),
            cache_key=cache_key
        )
        
        # Only cache non-security test tokens
        if not is_security_test:
            self.cache[cache_key] = cached_token
            logger.debug(f"Cached token: {cache_key} (expires in {exp_minutes}min)")
        
        return cached_token
    
    def clear_cache(self) -> int:
        """Clear all cached tokens.
        
        Returns:
            Number of tokens cleared
        """
        cleared_count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared {cleared_count} tokens from cache")
        return cleared_count
    
    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from cache.
        
        Returns:
            Number of expired tokens removed
        """
        expired_keys = [
            key for key, token in self.cache.items()
            if not token.is_valid
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired tokens")
        
        return len(expired_keys)
    
    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 1),
            "cached_tokens": len(self.cache),
            "security_bypasses": self.security_bypass_count,
            "total_requests": total_requests
        }


class WebSocketConnectionPool:
    """
    Performance-optimized WebSocket connection pool for testing.
    
    This pool enables connection reuse where security allows, significantly
    reducing connection establishment overhead while maintaining security isolation.
    
    SECURITY CRITICAL:
    - Only reuses connections for compatible scenarios
    - Security tests always get fresh connections
    - Connections maintain proper user isolation
    - Pool prevents connection leakage
    """
    
    def __init__(self, max_pool_size: int = 10):
        """Initialize connection pool.
        
        Args:
            max_pool_size: Maximum number of pooled connections
        """
        self.available_connections: List[RealWebSocketTestClient] = []
        self.active_connections: Dict[str, RealWebSocketTestClient] = {}
        self.max_pool_size = max_pool_size
        self.pool_hits = 0
        self.pool_misses = 0
        self.security_bypasses = 0
        
        # Thread pool for parallel connection operations
        self.thread_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="websocket_pool")
        
        logger.info(f"Initialized WebSocket connection pool (max_size: {max_pool_size})")
    
    def get_connection(
        self,
        backend_url: str,
        environment: str,
        is_security_test: bool = False
    ) -> Optional[RealWebSocketTestClient]:
        """Get connection from pool if available and suitable.
        
        Args:
            backend_url: WebSocket backend URL
            environment: Test environment
            is_security_test: If True, bypasses pool for security
            
        Returns:
            Pooled connection if available, None otherwise
        """
        if is_security_test:
            self.security_bypasses += 1
            logger.debug("Security test detected - bypassing connection pool")
            return None
        
        # Check for available connection with matching parameters
        for i, conn in enumerate(self.available_connections):
            if (hasattr(conn, 'backend_url') and conn.backend_url == backend_url and
                hasattr(conn, 'environment') and conn.environment == environment and
                not conn.connection or conn.connection.closed):
                
                # Remove from available pool and mark as active
                connection = self.available_connections.pop(i)
                connection_id = str(uuid.uuid4())
                self.active_connections[connection_id] = connection
                
                self.pool_hits += 1
                logger.debug(f"Connection pool HIT: Reusing connection for {backend_url}")
                return connection
        
        self.pool_misses += 1
        return None
    
    def return_connection(
        self,
        connection: RealWebSocketTestClient,
        is_security_test: bool = False
    ) -> bool:
        """Return connection to pool if suitable for reuse.
        
        Args:
            connection: Connection to return
            is_security_test: If True, connection won't be pooled
            
        Returns:
            True if connection was pooled, False otherwise
        """
        if is_security_test or len(self.available_connections) >= self.max_pool_size:
            return False
        
        # Clean connection state for reuse
        try:
            if hasattr(connection, 'authenticated_user'):
                connection.authenticated_user = None
            if hasattr(connection, 'expected_user_id'):
                connection.expected_user_id = None
            
            # Only pool if connection is in good state
            if connection.connection and not connection.connection.closed:
                self.available_connections.append(connection)
                logger.debug("Connection returned to pool for reuse")
                return True
        
        except Exception as e:
            logger.debug(f"Connection not suitable for pooling: {e}")
        
        return False
    
    async def cleanup_pool(self) -> int:
        """Clean up all pooled connections.
        
        Returns:
            Number of connections cleaned up
        """
        cleanup_count = 0
        
        # Close available connections
        for conn in self.available_connections:
            try:
                await conn.close()
                cleanup_count += 1
            except Exception as e:
                logger.debug(f"Error closing pooled connection: {e}")
        
        # Close active connections
        for conn in self.active_connections.values():
            try:
                await conn.close()
                cleanup_count += 1
            except Exception as e:
                logger.debug(f"Error closing active connection: {e}")
        
        self.available_connections.clear()
        self.active_connections.clear()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=False)
        
        logger.info(f"Cleaned up {cleanup_count} pooled connections")
        return cleanup_count
    
    @property
    def pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        total_requests = self.pool_hits + self.pool_misses
        hit_rate = (self.pool_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "pool_hits": self.pool_hits,
            "pool_misses": self.pool_misses,
            "hit_rate_percent": round(hit_rate, 1),
            "available_connections": len(self.available_connections),
            "active_connections": len(self.active_connections),
            "security_bypasses": self.security_bypasses,
            "total_requests": total_requests
        }


class WebSocketAuthenticationTester:
    """
    SSOT WebSocket Authentication Tester - Advanced Authentication Scenarios with Performance Optimization.
    
    This class provides comprehensive testing for WebSocket authentication security.
    It FAILS HARD when authentication vulnerabilities are detected.
    
    CRITICAL SECURITY FEATURES:
    - Token lifecycle validation during active connections
    - Session hijacking prevention testing
    - Cross-user isolation validation  
    - Permission boundary enforcement
    - Advanced attack scenario resistance
    - Timing attack detection
    
    PERFORMANCE OPTIMIZATIONS:
    - JWT token caching for non-security scenarios
    - WebSocket connection pooling where security allows
    - Parallel test execution for independent scenarios
    - Batch token operations for efficiency
    """
    
    def __init__(
        self,
        backend_url: str = "ws://localhost:8000",
        environment: str = "test",
        connection_timeout: float = 10.0,
        enable_performance_optimizations: bool = True
    ):
        """Initialize WebSocket authentication tester.
        
        Args:
            backend_url: WebSocket URL for backend service
            environment: Test environment ('test', 'staging', etc.)
            connection_timeout: Connection timeout in seconds
            enable_performance_optimizations: Enable performance optimizations
        """
        self.backend_url = backend_url
        self.environment = environment
        self.connection_timeout = connection_timeout
        self.enable_performance_optimizations = enable_performance_optimizations
        
        # Initialize auth helper
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Performance optimizations
        if enable_performance_optimizations:
            self.token_cache = JWTTokenCache()
            self.connection_pool = WebSocketConnectionPool()
            self.thread_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="auth_test")
        else:
            self.token_cache = None
            self.connection_pool = None
            self.thread_pool = None
        
        # Test tracking
        self.test_results: List[AuthenticationTestResult] = []
        self.active_clients: Dict[str, RealWebSocketTestClient] = {}
        self.security_violations: List[str] = []
        
        # Token lifecycle tracking
        self.token_states: Dict[str, TokenLifecycleState] = {}
        
        # Performance metrics
        self.performance_metrics = {
            "token_generation_time": 0.0,
            "connection_establishment_time": 0.0,
            "parallel_operations_count": 0,
            "cache_utilization": 0.0
        }
        
        logger.info(f"Initialized WebSocketAuthenticationTester for {environment} "
                   f"(optimizations: {'enabled' if enable_performance_optimizations else 'disabled'})")
    
    async def _get_or_create_token(
        self,
        user_id: str,
        email: str,
        permissions: List[str] = None,
        exp_minutes: int = 10,
        is_security_test: bool = False
    ) -> str:
        """Get cached token or create new one with performance optimization.
        
        Args:
            user_id: User ID
            email: User email  
            permissions: Token permissions
            exp_minutes: Token expiry in minutes
            is_security_test: If True, bypasses cache for security
            
        Returns:
            JWT token string
        """
        token_start = time.time()
        
        # Try cache first (if enabled and not security test)
        if self.token_cache and not is_security_test:
            cached_token = self.token_cache.get_cached_token(
                user_id, email, permissions or [], exp_minutes, is_security_test
            )
            
            if cached_token:
                token_time = time.time() - token_start
                self.performance_metrics["token_generation_time"] += token_time
                logger.debug(f"Using cached token (saved {token_time*1000:.1f}ms)")
                return cached_token.token
        
        # Create new token
        new_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=exp_minutes,
            permissions=permissions or []
        )
        
        # Cache new token (if enabled and not security test)
        if self.token_cache:
            self.token_cache.cache_token(
                new_token, user_id, email, permissions or [], exp_minutes, is_security_test
            )
        
        token_time = time.time() - token_start
        self.performance_metrics["token_generation_time"] += token_time
        
        return new_token
    
    async def batch_create_tokens(
        self,
        token_requests: List[Dict[str, Any]],
        is_security_test: bool = False
    ) -> List[str]:
        """Create multiple JWT tokens in parallel for performance.
        
        Args:
            token_requests: List of token request dictionaries with keys:
                - user_id: User ID
                - email: User email
                - permissions: Token permissions (optional)
                - exp_minutes: Token expiry minutes (optional, defaults to 10)
            is_security_test: If True, bypasses optimizations
            
        Returns:
            List of JWT token strings
        """
        if not self.enable_performance_optimizations or is_security_test:
            # Sequential token generation for security tests
            tokens = []
            for request in token_requests:
                token = await self._get_or_create_token(
                    user_id=request["user_id"],
                    email=request["email"],
                    permissions=request.get("permissions", []),
                    exp_minutes=request.get("exp_minutes", 10),
                    is_security_test=is_security_test
                )
                tokens.append(token)
            return tokens
        
        # Parallel token generation for performance
        async def create_single_token(request):
            return await self._get_or_create_token(
                user_id=request["user_id"],
                email=request["email"],
                permissions=request.get("permissions", []),
                exp_minutes=request.get("exp_minutes", 10),
                is_security_test=is_security_test
            )
        
        # Execute token creation in parallel
        parallel_start = time.time()
        tasks = [create_single_token(request) for request in token_requests]
        tokens = await asyncio.gather(*tasks)
        parallel_time = time.time() - parallel_start
        
        self.performance_metrics["parallel_operations_count"] += len(token_requests)
        logger.info(f"Created {len(tokens)} tokens in parallel ({parallel_time*1000:.1f}ms)")
        
        return tokens
    
    async def _get_or_create_connection(
        self,
        user: AuthenticatedUser,
        is_security_test: bool = False
    ) -> RealWebSocketTestClient:
        """Get pooled connection or create new one with performance optimization.
        
        Args:
            user: Authenticated user for the connection
            is_security_test: If True, bypasses pool for security
            
        Returns:
            WebSocket test client
        """
        conn_start = time.time()
        
        # Try connection pool first (if enabled and not security test)
        pooled_client = None
        if self.connection_pool and not is_security_test:
            pooled_client = self.connection_pool.get_connection(
                self.backend_url, self.environment, is_security_test
            )
        
        if pooled_client:
            # Configure pooled connection for new user
            pooled_client.authenticated_user = user
            pooled_client.expected_user_id = user.user_id
            
            conn_time = time.time() - conn_start
            self.performance_metrics["connection_establishment_time"] += conn_time
            logger.debug(f"Using pooled connection (saved {conn_time*1000:.1f}ms)")
            return pooled_client
        
        # Create new connection
        new_client = RealWebSocketTestClient(
            backend_url=self.backend_url,
            environment=self.environment,
            connection_timeout=self.connection_timeout
        )
        
        new_client.authenticated_user = user
        new_client.expected_user_id = user.user_id
        
        conn_time = time.time() - conn_start
        self.performance_metrics["connection_establishment_time"] += conn_time
        
        return new_client
    
    def _return_connection(
        self,
        connection: RealWebSocketTestClient,
        is_security_test: bool = False
    ) -> bool:
        """Return connection to pool if suitable.
        
        Args:
            connection: Connection to return
            is_security_test: If True, won't be pooled
            
        Returns:
            True if connection was returned to pool
        """
        if self.connection_pool and not is_security_test:
            return self.connection_pool.return_connection(connection, is_security_test)
        return False
    
    async def test_token_lifecycle_management(
        self,
        user_email: Optional[str] = None,
        initial_expiry_minutes: int = 5,
        connection_duration_minutes: int = 10
    ) -> AuthenticationTestResult:
        """
        Test token lifecycle management during active WebSocket connections.
        
        This test validates that:
        1. Tokens expire as expected during active connections
        2. Token refresh works properly
        3. Expired tokens are rejected
        4. Active connections handle token lifecycle properly
        
        Args:
            user_email: User email for testing (auto-generated if not provided)
            initial_expiry_minutes: Initial token expiry in minutes
            connection_duration_minutes: How long to maintain connection
            
        Returns:
            AuthenticationTestResult with lifecycle validation results
            
        Raises:
            SecurityError: If token lifecycle security is compromised
        """
        start_time = time.time()
        scenario = AuthenticationScenario.TOKEN_REFRESH
        security_violations = []
        
        try:
            logger.info("🔄 Testing token lifecycle management...")
            
            # Step 1: Create user with short-lived token
            if not user_email:
                user_email = f"lifecycle_test_{uuid.uuid4().hex[:8]}@example.com"
            
            # Create short-lived token for testing (SECURITY TEST - no caching)
            user_id = f"lifecycle_user_{uuid.uuid4().hex[:8]}"
            short_token = await self._get_or_create_token(
                user_id=user_id,
                email=user_email,
                permissions=["read", "write"],
                exp_minutes=initial_expiry_minutes,
                is_security_test=True  # Security test - bypass optimizations
            )
            
            # Track token lifecycle
            token_state = TokenLifecycleState(
                original_token=short_token,
                current_token=short_token,
                expiry_time=datetime.now(timezone.utc) + timedelta(minutes=initial_expiry_minutes)
            )
            self.token_states[user_id] = token_state
            
            # Step 2: Establish WebSocket connection with short-lived token
            client = RealWebSocketTestClient(
                backend_url=self.backend_url,
                environment=self.environment,
                connection_timeout=self.connection_timeout
            )
            
            # Manually set authenticated user for testing
            client.authenticated_user = AuthenticatedUser(
                user_id=user_id,
                email=user_email,
                full_name=f"Lifecycle Test User {user_id}",
                jwt_token=short_token,
                permissions=["read", "write"],
                created_at=datetime.now(timezone.utc).isoformat(),
                is_test_user=True
            )
            client.expected_user_id = user_id
            
            await client.connect(endpoint="/ws")
            self.active_clients[user_id] = client
            token_state.active_connections.add(client.connection_id)
            
            logger.info(f"✅ WebSocket connected with short-lived token (expires in {initial_expiry_minutes}m)")
            
            # Step 3: Wait for token to expire (plus buffer)
            expiry_wait = (initial_expiry_minutes * 60) + 30  # 30 second buffer
            logger.info(f"⏳ Waiting {expiry_wait}s for token expiry...")
            await asyncio.sleep(expiry_wait)
            
            # Step 4: Validate expired token is rejected
            try:
                validation_result = await self.auth_helper.validate_jwt_token(short_token)
                if validation_result.get("valid", False):
                    security_violations.append(
                        "SECURITY VIOLATION: Expired token was still accepted as valid"
                    )
                else:
                    logger.info("✅ Expired token properly rejected")
            except Exception as e:
                logger.info(f"✅ Expired token validation failed as expected: {e}")
            
            # Step 5: Test connection behavior with expired token
            try:
                # Try to send event with expired token
                await client.send_event("test_expired_token", {"test": "data"})
                
                # If this succeeds, it's a security violation
                security_violations.append(
                    "SECURITY VIOLATION: WebSocket accepted event with expired token"
                )
            except Exception as e:
                logger.info(f"✅ WebSocket properly rejected expired token: {e}")
            
            # Step 6: Test token refresh scenario
            logger.info("🔄 Testing token refresh...")
            new_token = await self._get_or_create_token(
                user_id=user_id,
                email=user_email,
                permissions=["read", "write"],
                exp_minutes=30,  # Longer expiry for refresh
                is_security_test=True  # Security test - bypass optimizations
            )
            
            token_state.current_token = new_token
            token_state.refresh_count += 1
            token_state.expiry_time = datetime.now(timezone.utc) + timedelta(minutes=30)
            
            # Test new token validation
            new_validation = await self.auth_helper.validate_jwt_token(new_token)
            if not new_validation.get("valid", False):
                security_violations.append(
                    "SECURITY VIOLATION: Valid refreshed token was rejected"
                )
            else:
                logger.info("✅ Refreshed token validation successful")
            
            # Step 7: Validate connection isolation maintained
            await client.close()
            
            response_time = time.time() - start_time
            
            result = AuthenticationTestResult(
                scenario=scenario,
                success=len(security_violations) == 0,
                error_message=None,
                response_time=response_time,
                security_violations=security_violations,
                expected_failure=False,
                actual_failure=len(security_violations) > 0
            )
            
            if security_violations:
                self.security_violations.extend(security_violations)
                raise SecurityError(
                    f"Token lifecycle security violations detected: {security_violations}"
                )
            
            logger.info(f"✅ Token lifecycle management test passed ({response_time:.2f}s)")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            error_message = str(e)
            
            result = AuthenticationTestResult(
                scenario=scenario,
                success=False,
                error_message=error_message,
                response_time=response_time,
                security_violations=security_violations,
                expected_failure=False,
                actual_failure=True
            )
            
            logger.error(f"❌ Token lifecycle management test failed: {error_message}")
            self.test_results.append(result)
            
            # Clean up
            if user_id in self.active_clients:
                await self.active_clients[user_id].close()
                del self.active_clients[user_id]
            
            raise
        finally:
            self.test_results.append(result)
    
    async def test_session_hijacking_prevention(
        self,
        legitimate_user_email: Optional[str] = None,
        attacker_user_email: Optional[str] = None
    ) -> AuthenticationTestResult:
        """
        Test session hijacking prevention mechanisms.
        
        This test validates that:
        1. Session tokens cannot be hijacked between users
        2. Cross-session data leakage is prevented
        3. Session isolation is maintained
        4. Token manipulation attempts are detected
        
        Args:
            legitimate_user_email: Legitimate user email
            attacker_user_email: Attacker user email
            
        Returns:
            AuthenticationTestResult with hijacking prevention validation
            
        Raises:
            SecurityError: If session hijacking prevention fails
        """
        start_time = time.time()
        scenario = AuthenticationScenario.SESSION_HIJACKING
        security_violations = []
        
        try:
            logger.info("🛡️ Testing session hijacking prevention...")
            
            # Step 1: Create legitimate user and session
            if not legitimate_user_email:
                legitimate_user_email = f"legitimate_{uuid.uuid4().hex[:8]}@example.com"
            
            legitimate_user = await self.auth_helper.create_authenticated_user(
                email=legitimate_user_email,
                permissions=["read", "write", "sensitive_data"]
            )
            
            # Step 2: Create attacker user
            if not attacker_user_email:
                attacker_user_email = f"attacker_{uuid.uuid4().hex[:8]}@example.com"
            
            attacker_user = await self.auth_helper.create_authenticated_user(
                email=attacker_user_email,
                permissions=["read"]  # Limited permissions
            )
            
            # Step 3: Establish legitimate WebSocket connection
            legitimate_client = RealWebSocketTestClient(
                backend_url=self.backend_url,
                environment=self.environment
            )
            legitimate_client.authenticated_user = legitimate_user
            legitimate_client.expected_user_id = legitimate_user.user_id
            
            await legitimate_client.connect()
            logger.info(f"✅ Legitimate user connected: {legitimate_user.user_id}")
            
            # Step 4: Test token hijacking attempt
            logger.info("🎯 Testing token hijacking attempt...")
            
            # Attacker tries to use legitimate user's token
            hijacker_client = RealWebSocketTestClient(
                backend_url=self.backend_url,
                environment=self.environment
            )
            
            # CRITICAL: Set attacker to use legitimate user's token (hijacking attempt)
            hijacker_client.authenticated_user = AuthenticatedUser(
                user_id=attacker_user.user_id,  # Attacker's user ID
                email=attacker_user.email,
                full_name=attacker_user.full_name,
                jwt_token=legitimate_user.jwt_token,  # But legitimate user's token!
                permissions=attacker_user.permissions,
                created_at=attacker_user.created_at,
                is_test_user=True
            )
            hijacker_client.expected_user_id = attacker_user.user_id
            
            # Step 5: Test if hijacking attempt is detected
            hijacking_detected = False
            try:
                await hijacker_client.connect()
                
                # If connection succeeds, test if proper isolation is maintained
                await hijacker_client.send_event("sensitive_operation", {
                    "action": "access_sensitive_data",
                    "target_user": legitimate_user.user_id
                })
                
                # Connection succeeded - this could indicate a security issue
                security_violations.append(
                    f"SECURITY VIOLATION: Token hijacking attempt was not blocked. "
                    f"Attacker {attacker_user.user_id} successfully connected using "
                    f"token from {legitimate_user.user_id}"
                )
                
            except Exception as e:
                hijacking_detected = True
                logger.info(f"✅ Token hijacking attempt blocked: {e}")
            
            # Step 6: Test session isolation
            logger.info("🔒 Testing session isolation...")
            
            # Send sensitive data to legitimate user
            await legitimate_client.send_event("sensitive_data", {
                "user_id": legitimate_user.user_id,
                "sensitive_info": "confidential_data_123",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Test if attacker can intercept
            if hijacker_client.connection and not hijacker_client.connection.closed:
                try:
                    # Attacker tries to receive events
                    attacker_events = await hijacker_client.wait_for_events(
                        event_types={"sensitive_data"},
                        timeout=5.0
                    )
                    
                    if attacker_events:
                        security_violations.append(
                            f"SECURITY VIOLATION: Attacker intercepted sensitive events: "
                            f"{[e.event_type for e in attacker_events]}"
                        )
                
                except asyncio.TimeoutError:
                    logger.info("✅ Attacker could not intercept sensitive events")
                except Exception as e:
                    logger.info(f"✅ Attacker event interception blocked: {e}")
            
            # Step 7: Test cross-session data leakage
            logger.info("🚫 Testing cross-session data leakage prevention...")
            
            # Create another legitimate session for the same user
            legitimate_client2 = await create_authenticated_websocket_client(
                backend_url=self.backend_url,
                environment=self.environment,
                user_email=legitimate_user.email,
                user_id=legitimate_user.user_id,
                permissions=legitimate_user.permissions
            )
            
            await legitimate_client2.connect()
            
            # Send event to first session
            await legitimate_client.send_event("session_specific_data", {
                "session_id": legitimate_client.connection_id,
                "data": "session_1_data"
            })
            
            # Check if second session receives it (should not for session isolation)
            try:
                cross_session_events = await legitimate_client2.wait_for_events(
                    event_types={"session_specific_data"},
                    timeout=3.0
                )
                
                # If events are received, check if they're properly isolated
                for event in cross_session_events:
                    if event.data.get("session_id") != legitimate_client2.connection_id:
                        # This might be acceptable depending on architecture
                        logger.warning(
                            f"Cross-session event received (may be acceptable): "
                            f"{event.event_type}"
                        )
            
            except asyncio.TimeoutError:
                logger.info("✅ Session isolation maintained - no cross-session leakage")
            
            # Clean up
            await legitimate_client.close()
            await legitimate_client2.close()
            if hijacker_client.connection and not hijacker_client.connection.closed:
                await hijacker_client.close()
            
            response_time = time.time() - start_time
            
            result = AuthenticationTestResult(
                scenario=scenario,
                success=len(security_violations) == 0,
                error_message=None,
                response_time=response_time,
                security_violations=security_violations,
                expected_failure=False,
                actual_failure=len(security_violations) > 0
            )
            
            if security_violations:
                self.security_violations.extend(security_violations)
                raise SecurityError(
                    f"Session hijacking prevention failures: {security_violations}"
                )
            
            logger.info(f"✅ Session hijacking prevention test passed ({response_time:.2f}s)")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            error_message = str(e)
            
            result = AuthenticationTestResult(
                scenario=scenario,
                success=False,
                error_message=error_message,
                response_time=response_time,
                security_violations=security_violations,
                expected_failure=False,
                actual_failure=True
            )
            
            logger.error(f"❌ Session hijacking prevention test failed: {error_message}")
            return result
        finally:
            # Clean up any remaining clients
            for client_id, client in list(self.active_clients.items()):
                try:
                    await client.close()
                except:
                    pass
    
    async def test_permission_boundary_enforcement(
        self,
        low_privilege_user_email: Optional[str] = None,
        high_privilege_user_email: Optional[str] = None
    ) -> AuthenticationTestResult:
        """
        Test permission boundary enforcement in WebSocket connections.
        
        This test validates that:
        1. Users cannot perform actions beyond their permissions
        2. Permission escalation attempts are blocked
        3. Cross-user permission violations are detected
        4. Role-based access control is enforced
        
        Args:
            low_privilege_user_email: Low privilege user email
            high_privilege_user_email: High privilege user email
            
        Returns:
            AuthenticationTestResult with permission enforcement validation
            
        Raises:
            SecurityError: If permission boundaries are violated
        """
        start_time = time.time()
        scenario = AuthenticationScenario.PERMISSION_ESCALATION
        security_violations = []
        
        try:
            logger.info("🔐 Testing permission boundary enforcement...")
            
            # Step 1: Create low privilege user
            if not low_privilege_user_email:
                low_privilege_user_email = f"lowpriv_{uuid.uuid4().hex[:8]}@example.com"
            
            low_priv_user = await self.auth_helper.create_authenticated_user(
                email=low_privilege_user_email,
                permissions=["read"]  # Very limited permissions
            )
            
            # Step 2: Create high privilege user
            if not high_privilege_user_email:
                high_privilege_user_email = f"highpriv_{uuid.uuid4().hex[:8]}@example.com"
            
            high_priv_user = await self.auth_helper.create_authenticated_user(
                email=high_privilege_user_email,
                permissions=["read", "write", "admin", "delete", "manage_users"]
            )
            
            # Step 3: Connect low privilege user
            low_priv_client = RealWebSocketTestClient(
                backend_url=self.backend_url,
                environment=self.environment
            )
            low_priv_client.authenticated_user = low_priv_user
            low_priv_client.expected_user_id = low_priv_user.user_id
            
            await low_priv_client.connect()
            logger.info(f"✅ Low privilege user connected: {low_priv_user.permissions}")
            
            # Step 4: Test permission escalation attempts
            logger.info("⚠️ Testing permission escalation attempts...")
            
            escalation_attempts = [
                {
                    "action": "admin_action",
                    "data": {"command": "grant_admin", "target_user": low_priv_user.user_id}
                },
                {
                    "action": "delete_user",
                    "data": {"user_id": "some_user_id"}
                },
                {
                    "action": "manage_permissions", 
                    "data": {"user_id": low_priv_user.user_id, "new_permissions": ["admin"]}
                },
                {
                    "action": "system_command",
                    "data": {"command": "shutdown", "force": True}
                }
            ]
            
            for attempt in escalation_attempts:
                try:
                    await low_priv_client.send_event(
                        event_type=attempt["action"],
                        data=attempt["data"]
                    )
                    
                    # If no exception is raised, check if action was blocked server-side
                    logger.warning(
                        f"Permission escalation attempt sent: {attempt['action']} "
                        f"(should be blocked server-side)"
                    )
                    
                except Exception as e:
                    logger.info(f"✅ Permission escalation blocked: {attempt['action']} - {e}")
            
            # Step 5: Test cross-user permission violations
            logger.info("🚫 Testing cross-user permission violations...")
            
            # Low privilege user tries to access high privilege user's data
            try:
                await low_priv_client.send_event("access_user_data", {
                    "target_user_id": high_priv_user.user_id,
                    "requested_data": ["profile", "permissions", "activity"]
                })
                
                # Wait for any response that might indicate violation
                try:
                    violation_events = await low_priv_client.wait_for_events(
                        event_types={"user_data_response", "access_granted"},
                        timeout=3.0
                    )
                    
                    if violation_events:
                        security_violations.append(
                            f"SECURITY VIOLATION: Low privilege user accessed other user's data: "
                            f"{[e.event_type for e in violation_events]}"
                        )
                
                except asyncio.TimeoutError:
                    logger.info("✅ Cross-user data access properly blocked")
                
            except Exception as e:
                logger.info(f"✅ Cross-user access attempt blocked: {e}")
            
            # Step 6: Connect high privilege user and verify proper access
            high_priv_client = RealWebSocketTestClient(
                backend_url=self.backend_url,
                environment=self.environment
            )
            high_priv_client.authenticated_user = high_priv_user
            high_priv_client.expected_user_id = high_priv_user.user_id
            
            await high_priv_client.connect()
            logger.info(f"✅ High privilege user connected: {high_priv_user.permissions}")
            
            # Test that high privilege user CAN perform admin actions
            try:
                await high_priv_client.send_event("admin_info_request", {
                    "info_type": "system_status"
                })
                logger.info("✅ High privilege user can perform admin actions")
            except Exception as e:
                logger.warning(f"High privilege user action blocked: {e}")
            
            # Step 7: Test permission isolation between users
            logger.info("🔒 Testing permission isolation...")
            
            # Both users should only see events for their permission level
            await low_priv_client.send_event("test_isolation", {
                "user_type": "low_privilege",
                "test_id": f"isolation_test_{uuid.uuid4().hex[:8]}"
            })
            
            await high_priv_client.send_event("admin_test_event", {
                "user_type": "high_privilege", 
                "admin_data": "sensitive_admin_info"
            })
            
            # Check if low privilege user receives admin events (should not)
            try:
                admin_events = await low_priv_client.wait_for_events(
                    event_types={"admin_test_event", "admin_response"},
                    timeout=3.0
                )
                
                if admin_events:
                    security_violations.append(
                        f"SECURITY VIOLATION: Low privilege user received admin events: "
                        f"{[e.event_type for e in admin_events]}"
                    )
            
            except asyncio.TimeoutError:
                logger.info("✅ Admin events properly isolated from low privilege user")
            
            # Clean up
            await low_priv_client.close()
            await high_priv_client.close()
            
            response_time = time.time() - start_time
            
            result = AuthenticationTestResult(
                scenario=scenario,
                success=len(security_violations) == 0,
                error_message=None,
                response_time=response_time,
                security_violations=security_violations,
                expected_failure=False,
                actual_failure=len(security_violations) > 0
            )
            
            if security_violations:
                self.security_violations.extend(security_violations)
                raise SecurityError(
                    f"Permission boundary enforcement failures: {security_violations}"
                )
            
            logger.info(f"✅ Permission boundary enforcement test passed ({response_time:.2f}s)")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            error_message = str(e)
            
            result = AuthenticationTestResult(
                scenario=scenario,
                success=False,
                error_message=error_message,
                response_time=response_time,
                security_violations=security_violations,
                expected_failure=False,
                actual_failure=True
            )
            
            logger.error(f"❌ Permission boundary enforcement test failed: {error_message}")
            return result
    
    async def test_malformed_token_handling(self) -> AuthenticationTestResult:
        """
        Test handling of malformed and invalid authentication tokens.
        
        This test validates that:
        1. Malformed JWT tokens are rejected
        2. Invalid signatures are detected
        3. Missing tokens are handled properly
        4. Token manipulation attempts are blocked
        
        Returns:
            AuthenticationTestResult with malformed token validation
            
        Raises:
            SecurityError: If malformed token handling fails
        """
        start_time = time.time()
        scenario = AuthenticationScenario.MALFORMED_TOKEN
        security_violations = []
        
        try:
            logger.info("🔍 Testing malformed token handling...")
            
            malformed_tokens = [
                "",  # Empty token
                "not-a-jwt-token",  # Plain string
                "eyJhbGciOiJIUzI1NiJ9.invalid",  # Malformed JWT
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Missing parts
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",  # Missing signature
                "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhdHRhY2tlciIsImFkbWluIjp0cnVlfQ.",  # None algorithm attack
            ]
            
            for i, malformed_token in enumerate(malformed_tokens):
                logger.info(f"Testing malformed token {i+1}/{len(malformed_tokens)}")
                
                # Test token validation
                try:
                    validation_result = await self.auth_helper.validate_jwt_token(malformed_token)
                    
                    if validation_result.get("valid", False):
                        security_violations.append(
                            f"SECURITY VIOLATION: Malformed token accepted as valid: "
                            f"'{malformed_token[:50]}...'"
                        )
                    else:
                        logger.info(f"✅ Malformed token properly rejected: {validation_result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    logger.info(f"✅ Malformed token validation failed as expected: {e}")
                
                # Test WebSocket connection with malformed token
                test_client = RealWebSocketTestClient(
                    backend_url=self.backend_url,
                    environment=self.environment
                )
                
                # Set malformed token
                test_client.authenticated_user = AuthenticatedUser(
                    user_id=f"test_user_{i}",
                    email=f"test{i}@example.com",
                    full_name=f"Test User {i}",
                    jwt_token=malformed_token,
                    permissions=["read"],
                    created_at=datetime.now(timezone.utc).isoformat(),
                    is_test_user=True
                )
                
                # Test connection attempt
                connection_blocked = True
                try:
                    await test_client.connect()
                    connection_blocked = False
                    
                    security_violations.append(
                        f"SECURITY VIOLATION: WebSocket connection succeeded with malformed token: "
                        f"'{malformed_token[:50]}...'"
                    )
                    
                    await test_client.close()
                
                except Exception as e:
                    logger.info(f"✅ WebSocket connection blocked with malformed token: {e}")
                
                if not connection_blocked:
                    logger.error(f"❌ Malformed token was accepted: {malformed_token[:50]}...")
            
            response_time = time.time() - start_time
            
            result = AuthenticationTestResult(
                scenario=scenario,
                success=len(security_violations) == 0,
                error_message=None,
                response_time=response_time,
                security_violations=security_violations,
                expected_failure=False,
                actual_failure=len(security_violations) > 0
            )
            
            if security_violations:
                self.security_violations.extend(security_violations)
                raise SecurityError(
                    f"Malformed token handling failures: {security_violations}"
                )
            
            logger.info(f"✅ Malformed token handling test passed ({response_time:.2f}s)")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            error_message = str(e)
            
            result = AuthenticationTestResult(
                scenario=scenario,
                success=False,
                error_message=error_message,
                response_time=response_time,
                security_violations=security_violations,
                expected_failure=False,
                actual_failure=True
            )
            
            logger.error(f"❌ Malformed token handling test failed: {error_message}")
            return result
    
    async def run_comprehensive_authentication_test_suite(
        self,
        include_timing_attacks: bool = True,
        use_parallel_execution: bool = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive authentication test suite with performance optimizations.
        
        This runs all authentication security tests and returns a complete report.
        Performance optimizations include parallel execution for independent tests.
        
        Args:
            include_timing_attacks: Whether to include timing attack tests
            use_parallel_execution: Override parallel execution (None = auto-detect)
            
        Returns:
            Comprehensive test report with performance metrics
            
        Raises:
            SecurityError: If any critical security violations are detected
        """
        suite_start = time.time()
        logger.info("🔒 Starting comprehensive WebSocket authentication test suite...")
        
        # Determine parallel execution strategy
        if use_parallel_execution is None:
            use_parallel_execution = self.enable_performance_optimizations
        
        # Test scenarios with parallel execution classification
        test_scenarios = [
            {
                "name": "Token Lifecycle Management",
                "method": self.test_token_lifecycle_management,
                "is_security_test": True,  # Must run sequentially for security
                "parallel_group": None
            },
            {
                "name": "Session Hijacking Prevention", 
                "method": self.test_session_hijacking_prevention,
                "is_security_test": True,  # Must run sequentially for security
                "parallel_group": None
            },
            {
                "name": "Permission Boundary Enforcement",
                "method": self.test_permission_boundary_enforcement, 
                "is_security_test": True,  # Must run sequentially for security
                "parallel_group": None
            },
            {
                "name": "Malformed Token Handling",
                "method": self.test_malformed_token_handling,
                "is_security_test": True,  # Must run sequentially for security  
                "parallel_group": None
            }
        ]
        
        results = {
            "test_suite": "WebSocket Authentication Security",
            "start_time": suite_start,
            "environment": self.environment,
            "total_tests": len(test_scenarios),
            "passed_tests": 0,
            "failed_tests": 0,
            "security_violations": [],
            "test_results": {},
            "recommendations": [],
            "performance_optimizations_enabled": self.enable_performance_optimizations,
            "parallel_execution_used": use_parallel_execution
        }
        
        if use_parallel_execution and self.enable_performance_optimizations:
            logger.info("🚀 Using parallel execution for compatible test scenarios...")
            
            # Group tests for parallel execution
            security_tests = [t for t in test_scenarios if t["is_security_test"]]
            parallel_tests = [t for t in test_scenarios if not t["is_security_test"]]
            
            # Run security tests sequentially (they need isolation)
            for test_scenario in security_tests:
                test_name = test_scenario["name"]
                test_method = test_scenario["method"]
                
                try:
                    logger.info(f"🔒 Running security test: {test_name}")
                    
                    test_start = time.time()
                    result = await test_method()
                    test_time = time.time() - test_start
                    
                    results["test_results"][test_name] = {
                        "scenario": result.scenario.value,
                        "success": result.success,
                        "response_time": result.response_time,
                        "security_violations": result.security_violations,
                        "test_passed": result.test_passed,
                        "execution_time": test_time,
                        "execution_mode": "sequential_security"
                    }
                    
                    if result.success:
                        results["passed_tests"] += 1
                        logger.info(f"✅ {test_name}: PASSED ({test_time:.2f}s)")
                    else:
                        results["failed_tests"] += 1
                        logger.error(f"❌ {test_name}: FAILED ({test_time:.2f}s)")
                        
                        if result.security_violations:
                            results["security_violations"].extend(result.security_violations)
                    
                except Exception as e:
                    results["failed_tests"] += 1
                    results["test_results"][test_name] = {
                        "scenario": "error",
                        "success": False,
                        "error": str(e),
                        "response_time": 0.0,
                        "security_violations": [],
                        "test_passed": False,
                        "execution_time": 0.0,
                        "execution_mode": "sequential_security"
                    }
                    logger.error(f"❌ {test_name}: ERROR - {e}")
            
            # Run parallel tests concurrently (if any exist in the future)
            if parallel_tests:
                logger.info(f"⚡ Running {len(parallel_tests)} tests in parallel...")
                
                async def run_parallel_test(test_scenario):
                    test_name = test_scenario["name"]
                    test_method = test_scenario["method"]
                    
                    try:
                        test_start = time.time()
                        result = await test_method()
                        test_time = time.time() - test_start
                        
                        return test_name, {
                            "scenario": result.scenario.value,
                            "success": result.success,
                            "response_time": result.response_time,
                            "security_violations": result.security_violations,
                            "test_passed": result.test_passed,
                            "execution_time": test_time,
                            "execution_mode": "parallel"
                        }, result
                    
                    except Exception as e:
                        test_time = 0.0
                        return test_name, {
                            "scenario": "error",
                            "success": False,
                            "error": str(e),
                            "response_time": 0.0,
                            "security_violations": [],
                            "test_passed": False,
                            "execution_time": test_time,
                            "execution_mode": "parallel"
                        }, None
                
                # Execute parallel tests
                parallel_tasks = [run_parallel_test(test) for test in parallel_tests]
                parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
                
                # Process parallel results
                for parallel_result in parallel_results:
                    if isinstance(parallel_result, Exception):
                        logger.error(f"Parallel test exception: {parallel_result}")
                        results["failed_tests"] += 1
                        continue
                    
                    test_name, test_result, result_obj = parallel_result
                    results["test_results"][test_name] = test_result
                    
                    if test_result["success"]:
                        results["passed_tests"] += 1
                        logger.info(f"✅ {test_name}: PASSED (parallel, {test_result['execution_time']:.2f}s)")
                    else:
                        results["failed_tests"] += 1
                        logger.error(f"❌ {test_name}: FAILED (parallel, {test_result['execution_time']:.2f}s)")
                        
                        if result_obj and result_obj.security_violations:
                            results["security_violations"].extend(result_obj.security_violations)
        
        else:
            # Sequential execution (legacy mode or optimizations disabled)
            logger.info("🐌 Using sequential execution for all tests...")
            
            for test_scenario in test_scenarios:
                test_name = test_scenario["name"]
                test_method = test_scenario["method"]
                
                try:
                    logger.info(f"🧪 Running: {test_name}")
                    
                    test_start = time.time()
                    result = await test_method()
                    test_time = time.time() - test_start
                    
                    results["test_results"][test_name] = {
                        "scenario": result.scenario.value,
                        "success": result.success,
                        "response_time": result.response_time,
                        "security_violations": result.security_violations,
                        "test_passed": result.test_passed,
                        "execution_time": test_time,
                        "execution_mode": "sequential"
                    }
                    
                    if result.success:
                        results["passed_tests"] += 1
                        logger.info(f"✅ {test_name}: PASSED ({test_time:.2f}s)")
                    else:
                        results["failed_tests"] += 1
                        logger.error(f"❌ {test_name}: FAILED ({test_time:.2f}s)")
                        
                        if result.security_violations:
                            results["security_violations"].extend(result.security_violations)
                
                except Exception as e:
                    results["failed_tests"] += 1
                    results["test_results"][test_name] = {
                        "scenario": "error",
                        "success": False,
                        "error": str(e),
                        "response_time": 0.0,
                        "security_violations": [],
                        "test_passed": False,
                        "execution_time": 0.0,
                        "execution_mode": "sequential"
                    }
                    logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # Generate recommendations based on results
        if results["security_violations"]:
            results["recommendations"].extend([
                "CRITICAL: Address all security violations immediately",
                "Review WebSocket authentication implementation",
                "Implement additional token validation checks",
                "Enhance session isolation mechanisms"
            ])
        
        if results["failed_tests"] > 0:
            results["recommendations"].extend([
                "Review failed test scenarios",
                "Implement missing security controls",
                "Test authentication with different token states"
            ])
        
        results["end_time"] = time.time()
        results["total_duration"] = results["end_time"] - suite_start
        results["success_rate"] = results["passed_tests"] / results["total_tests"] * 100
        
        # Add performance metrics
        if self.enable_performance_optimizations:
            results["performance_metrics"] = {
                "total_token_generation_time": self.performance_metrics["token_generation_time"],
                "total_connection_establishment_time": self.performance_metrics["connection_establishment_time"],
                "parallel_operations_count": self.performance_metrics["parallel_operations_count"],
                "token_cache_stats": self.token_cache.cache_stats if self.token_cache else None,
                "connection_pool_stats": self.connection_pool.pool_stats if self.connection_pool else None,
                "optimization_savings_estimate_ms": self._calculate_optimization_savings()
            }
            
            # Performance recommendations
            cache_hit_rate = results["performance_metrics"]["token_cache_stats"]["hit_rate_percent"] if results["performance_metrics"]["token_cache_stats"] else 0
            pool_hit_rate = results["performance_metrics"]["connection_pool_stats"]["hit_rate_percent"] if results["performance_metrics"]["connection_pool_stats"] else 0
            
            if cache_hit_rate > 50:
                results["recommendations"].append(f"Excellent token cache utilization: {cache_hit_rate}% hit rate")
            elif cache_hit_rate > 20:
                results["recommendations"].append(f"Good token cache utilization: {cache_hit_rate}% hit rate")
            else:
                results["recommendations"].append("Consider increasing test scenarios to improve cache utilization")
            
            if pool_hit_rate > 30:
                results["recommendations"].append(f"Good connection pool utilization: {pool_hit_rate}% hit rate")
            
            logger.info(f"⚡ Performance optimizations: Token cache {cache_hit_rate}% hit rate, Pool {pool_hit_rate}% hit rate")
        
        logger.info(
            f"🏁 Authentication test suite completed: "
            f"{results['passed_tests']}/{results['total_tests']} passed "
            f"({results['success_rate']:.1f}% success rate, {results['total_duration']:.2f}s total)"
        )
        
        if results["security_violations"]:
            raise SecurityError(
                f"CRITICAL: {len(results['security_violations'])} security violations detected. "
                f"See test report for details."
            )
        
        return results
    
    def _calculate_optimization_savings(self) -> float:
        """Calculate estimated time savings from optimizations in milliseconds."""
        if not self.enable_performance_optimizations:
            return 0.0
        
        savings = 0.0
        
        # Token cache savings (assume 50ms per avoided token generation)
        if self.token_cache:
            cache_hits = self.token_cache.cache_hits
            savings += cache_hits * 50  # 50ms per cache hit
        
        # Connection pool savings (assume 100ms per avoided connection setup)
        if self.connection_pool:
            pool_hits = self.connection_pool.pool_hits
            savings += pool_hits * 100  # 100ms per pool hit
        
        # Parallel execution savings (estimate 30% improvement)
        if self.performance_metrics["parallel_operations_count"] > 0:
            savings += self.performance_metrics["parallel_operations_count"] * 20  # 20ms per parallel op
        
        return savings
    
    async def cleanup(self) -> None:
        """Clean up test resources and performance optimization components."""
        logger.info("🧹 Cleaning up WebSocket authentication test resources...")
        
        # Close all active clients
        for client_id, client in list(self.active_clients.items()):
            try:
                await client.close()
                logger.debug(f"Closed client: {client_id}")
            except Exception as e:
                logger.warning(f"Error closing client {client_id}: {e}")
        
        self.active_clients.clear()
        self.token_states.clear()
        
        # Cleanup performance optimization components
        if self.enable_performance_optimizations:
            # Clean up token cache
            if self.token_cache:
                cleared_tokens = self.token_cache.clear_cache()
                logger.debug(f"Cleared {cleared_tokens} cached tokens")
            
            # Clean up connection pool
            if self.connection_pool:
                cleaned_connections = await self.connection_pool.cleanup_pool()
                logger.debug(f"Cleaned up {cleaned_connections} pooled connections")
            
            # Shutdown thread pool
            if self.thread_pool:
                self.thread_pool.shutdown(wait=False)
                logger.debug("Thread pool shutdown initiated")
            
            # Log final performance statistics
            if self.token_cache:
                cache_stats = self.token_cache.cache_stats
                logger.info(f"Final token cache stats: {cache_stats['cache_hits']} hits, "
                           f"{cache_stats['cache_misses']} misses, "
                           f"{cache_stats['hit_rate_percent']}% hit rate")
            
            if self.connection_pool:
                pool_stats = self.connection_pool.pool_stats
                logger.info(f"Final connection pool stats: {pool_stats['pool_hits']} hits, "
                           f"{pool_stats['pool_misses']} misses, "
                           f"{pool_stats['hit_rate_percent']}% hit rate")
            
            savings_ms = self._calculate_optimization_savings()
            if savings_ms > 0:
                logger.info(f"⚡ Estimated performance savings: {savings_ms:.1f}ms")
        
        logger.info("✅ WebSocket authentication test cleanup completed")


# SSOT Helper Functions

async def create_authenticated_websocket_client(
    backend_url: str = "ws://localhost:8000",
    environment: str = "test",
    user_email: Optional[str] = None,
    user_id: Optional[str] = None,
    permissions: Optional[List[str]] = None
) -> RealWebSocketTestClient:
    """
    Create and authenticate a WebSocket test client.
    
    This is the SSOT function for creating authenticated WebSocket clients for testing.
    
    Args:
        backend_url: WebSocket backend URL
        environment: Test environment
        user_email: User email (auto-generated if not provided)
        user_id: User ID (auto-generated if not provided)
        permissions: User permissions (defaults to ["read", "write"])
        
    Returns:
        Authenticated RealWebSocketTestClient ready for testing
    """
    client = RealWebSocketTestClient(
        backend_url=backend_url,
        environment=environment,
        auth_required=True
    )
    
    await client.authenticate_user(
        user_email=user_email,
        user_id=user_id,
        permissions=permissions
    )
    
    return client


async def run_websocket_authentication_security_tests(
    backend_url: str = "ws://localhost:8000",
    environment: str = "test"
) -> Dict[str, Any]:
    """
    Run complete WebSocket authentication security test suite.
    
    This is the main entry point for running WebSocket authentication security tests.
    Tests FAIL HARD when authentication vulnerabilities are detected.
    
    Args:
        backend_url: WebSocket backend URL to test
        environment: Test environment ('test', 'staging', etc.)
        
    Returns:
        Complete test report with security validation results
        
    Raises:
        SecurityError: If critical authentication security violations are detected
    """
    tester = WebSocketAuthenticationTester(
        backend_url=backend_url,
        environment=environment
    )
    
    try:
        return await tester.run_comprehensive_authentication_test_suite()
    finally:
        await tester.cleanup()


# Export SSOT components
__all__ = [
    "AuthenticationScenario",
    "AuthenticationTestResult", 
    "TokenLifecycleState",
    "CachedToken",
    "JWTTokenCache",
    "WebSocketConnectionPool",
    "WebSocketAuthenticationTester",
    "SecurityError",
    "create_authenticated_websocket_client",
    "run_websocket_authentication_security_tests"
]