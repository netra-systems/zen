"""
OAuth Security Utilities
Implements OAuth 2.0 security best practices including PKCE, CSRF protection, and replay attack prevention
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from auth_service.auth_core.redis_manager import auth_redis_manager

logger = logging.getLogger(__name__)


class OAuthSecurityManager:
    """Manages OAuth security validations and protections"""
    
    def __init__(self, redis_client: Optional[any] = None):
        # Use unified Redis manager instead of passed client
        self.redis_manager = auth_redis_manager
        self.hmac_secret = self._get_hmac_secret()
        # In-memory storage for testing when Redis not available
        self._memory_store = {}
        
    @property
    def redis_client(self):
        """Get Redis client from unified manager."""
        return self.redis_manager.get_client()
    
    def _use_memory_store(self) -> bool:
        """Check if we should use in-memory storage (for testing)"""
        try:
            return not self.redis_manager.is_available() or self.redis_client is None
        except:
            return True
        
    def _get_hmac_secret(self) -> str:
        """Get HMAC secret for state signing"""
        secret = os.getenv("OAUTH_HMAC_SECRET")
        if not secret:
            # Generate a strong secret for this session
            secret = secrets.token_hex(32)
            logger.warning("Using generated HMAC secret - set OAUTH_HMAC_SECRET for production")
        return secret
    
    def validate_pkce_challenge(self, code_verifier: str, code_challenge: str) -> bool:
        """
        Validate PKCE code challenge (RFC 7636)
        
        Args:
            code_verifier: The original code verifier
            code_challenge: The challenge received in authorization request
            
        Returns:
            True if PKCE validation passes
        """
        try:
            # Generate expected challenge from verifier
            expected_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip("=")
            
            # Compare with provided challenge
            is_valid = hmac.compare_digest(expected_challenge, code_challenge)
            
            if not is_valid:
                logger.warning("PKCE challenge validation failed")
                
            return is_valid
            
        except Exception as e:
            logger.error(f"PKCE validation error: {e}")
            return False
    
    def check_nonce_replay(self, nonce: str) -> bool:
        """
        Check if nonce has been used before (replay attack prevention)
        
        Args:
            nonce: The nonce to check
            
        Returns:
            True if nonce is valid (not replayed), False if already used
        """
        nonce_key = f"oauth_nonce:{nonce}"
        
        # Use memory store if Redis not available (for testing)
        if self._use_memory_store():
            # Check if already used
            if nonce_key in self._memory_store:
                logger.warning(f"Nonce replay attack detected: {nonce}")
                return False
            
            # Mark as used
            self._memory_store[nonce_key] = "used"
            return True
        
        # Use Redis for production
        try:
            # Ensure Redis connection via unified manager
            if not self.redis_manager.is_available():
                self.redis_manager.connect()
                
            redis_client = self.redis_client
            if not redis_client:
                logger.warning("Redis not available for nonce tracking")
                return True  # Allow if Redis not available
                
            # Use atomic SET with NX to prevent race conditions
            result = redis_client.set(nonce_key, "used", ex=600, nx=True)
            
            if not result:
                logger.warning(f"Nonce replay attack detected or concurrent use: {nonce}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Nonce validation error: {e}")
            return True  # Allow if Redis fails (graceful degradation)
    
    def track_authorization_code(self, code: str) -> bool:
        """
        Track authorization code usage to prevent reuse
        
        Args:
            code: The authorization code
            
        Returns:
            True if code is valid (first use), False if already used
        """
        code_key = f"oauth_code:{code}"
        
        # Use memory store if Redis not available (for testing)
        if self._use_memory_store():
            # Check if already used
            if code_key in self._memory_store:
                logger.warning(f"Authorization code reuse attack detected: {code}")
                return False
            
            # Mark as used
            self._memory_store[code_key] = "used"
            return True
        
        # Use Redis for production
        try:
            # Ensure Redis connection via unified manager
            if not self.redis_manager.is_available():
                self.redis_manager.connect()
                
            redis_client = self.redis_client
            if not redis_client:
                logger.warning("Redis not available for code tracking")
                return True  # Allow if Redis not available
                
            # Use atomic SET with NX to prevent race conditions
            result = redis_client.set(code_key, "used", ex=600, nx=True)
            
            if not result:
                logger.warning(f"Authorization code reuse attack detected or concurrent use: {code}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Code tracking error: {e}")
            return True  # Allow if Redis fails
    
    def validate_csrf_token_binding(self, state: str, session_id: str) -> bool:
        """
        Validate CSRF token binding to session
        
        Args:
            state: The state parameter containing session binding
            session_id: The current session ID
            
        Returns:
            True if CSRF validation passes
        """
        try:
            # Decode state parameter
            state_data = self._decode_state(state)
            if not state_data:
                return False
            
            # Check session binding
            state_session = state_data.get("session_id")
            if not state_session:
                logger.warning("No session ID in state parameter")
                return False
            
            # Validate session matches
            if not hmac.compare_digest(state_session, session_id):
                logger.warning("CSRF token binding validation failed")
                return False
            
            # Check origin if present
            origin = state_data.get("origin")
            if origin and not self._is_valid_origin(origin):
                logger.warning(f"Invalid origin in state: {origin}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"CSRF validation error: {e}")
            return False
    
    def validate_hmac_state_signature(self, state: str) -> bool:
        """
        Validate HMAC signature of state parameter
        
        Args:
            state: The signed state parameter
            
        Returns:
            True if signature is valid
        """
        try:
            # Decode state
            decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
            
            # Split state and signature
            if "|" not in decoded_state:
                logger.warning("No HMAC signature found in state")
                return False
            
            state_json, provided_hmac = decoded_state.rsplit("|", 1)
            
            # Calculate expected HMAC
            expected_hmac = hmac.new(
                self.hmac_secret.encode(),
                state_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if not hmac.compare_digest(expected_hmac, provided_hmac):
                logger.warning("HMAC signature validation failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"HMAC validation error: {e}")
            return False
    
    def validate_redirect_uri(self, redirect_uri: str) -> bool:
        """
        Validate redirect URI against whitelist
        
        Args:
            redirect_uri: The redirect URI to validate
            
        Returns:
            True if redirect URI is valid
        """
        try:
            # Get allowed redirect URIs from environment
            allowed_uris = os.getenv("OAUTH_ALLOWED_REDIRECT_URIS", "").split(",")
            
            # Default allowed URIs for development
            if not allowed_uris or not allowed_uris[0]:
                allowed_uris = [
                    "https://app.netra.ai/auth/callback",
                    "https://app.staging.netra.ai/auth/callback",
                    "http://localhost:3000/auth/callback"
                ]
            
            # Check if URI is in whitelist
            for allowed_uri in allowed_uris:
                if redirect_uri == allowed_uri.strip():
                    return True
            
            logger.warning(f"Redirect URI not in whitelist: {redirect_uri}")
            return False
            
        except Exception as e:
            logger.error(f"Redirect URI validation error: {e}")
            return False
    
    def generate_secure_session_id(self) -> str:
        """
        Generate a cryptographically secure session ID
        
        Returns:
            A secure session ID
        """
        return secrets.token_urlsafe(32)
    
    def generate_state_parameter(self) -> str:
        """
        Generate a cryptographically secure OAuth state parameter
        
        Returns:
            A secure URL-safe base64 encoded state parameter
        """
        return secrets.token_urlsafe(32)
    
    def store_state_parameter(self, state: str, session_id: str) -> bool:
        """
        Store OAuth state parameter with session binding
        
        Args:
            state: The state parameter to store
            session_id: Session ID to bind the state to
            
        Returns:
            True if state was stored successfully
        """
        state_data = {
            "session_id": session_id,
            "timestamp": time.time()
        }
        
        # Use memory store if Redis not available (for testing)
        if self._use_memory_store():
            state_key = f"oauth_state:{state}"
            # Check if already exists (nx=True behavior)
            if state_key in self._memory_store:
                return False
            self._memory_store[state_key] = state_data
            return True
        
        # Use Redis for production
        try:
            if not self.redis_manager.is_available():
                self.redis_manager.connect()
                
            redis_client = self.redis_client
            if not redis_client:
                logger.warning("Redis not available for state storage")
                return False
                
            state_key = f"oauth_state:{state}"
            # Store with 10 minute expiration
            result = redis_client.set(
                state_key, 
                json.dumps(state_data), 
                ex=600,  # 10 minutes
                nx=True  # Only set if not exists
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"State parameter storage error: {e}")
            return False
    
    def validate_state_parameter(self, state: str, session_id: str) -> bool:
        """
        Validate and consume OAuth state parameter (timing-safe)
        
        Args:
            state: The state parameter to validate
            session_id: Expected session ID
            
        Returns:
            True if state is valid and matches session
        """
        state_key = f"oauth_state:{state}"
        
        # Use memory store if Redis not available (for testing)
        if self._use_memory_store():
            if state_key not in self._memory_store:
                return False
                
            state_data = self._memory_store[state_key]
            stored_session_id = state_data.get("session_id", "")
            stored_timestamp = state_data.get("timestamp", 0)
            
            # Check expiration (10 minutes) - import time here for testability
            import time as time_module
            if time_module.time() - stored_timestamp > 600:
                del self._memory_store[state_key]
                return False
            
            # Delete state on any validation attempt (single use, prevents timing attacks)
            del self._memory_store[state_key]
            
            # Timing-safe session comparison
            return hmac.compare_digest(stored_session_id, session_id)
        
        # Use Redis for production
        try:
            if not self.redis_manager.is_available():
                self.redis_manager.connect()
                
            redis_client = self.redis_client
            if not redis_client:
                logger.warning("Redis not available for state validation")
                return False
                
            # Get and delete atomically
            state_data_json = redis_client.get(state_key)
            if not state_data_json:
                return False
                
            # Parse stored data
            state_data = json.loads(state_data_json)
            stored_session_id = state_data.get("session_id", "")
            stored_timestamp = state_data.get("timestamp", 0)
            
            # Check expiration (10 minutes) - import time here for testability
            import time as time_module
            if time_module.time() - stored_timestamp > 600:
                redis_client.delete(state_key)
                return False
            
            # Delete state on any validation attempt (single use, prevents timing attacks)
            redis_client.delete(state_key)
            
            # Timing-safe session comparison
            return hmac.compare_digest(stored_session_id, session_id)
            
        except Exception as e:
            logger.error(f"State parameter validation error: {e}")
            return False
    
    def generate_state_parameter_with_hmac(self, session_id: str) -> str:
        """
        Generate state parameter with HMAC signature
        
        Args:
            session_id: Session ID to include in HMAC
            
        Returns:
            State parameter with HMAC signature
        """
        # Generate base state
        state_data = secrets.token_urlsafe(24)
        
        # Create HMAC signature
        signature = hmac.new(
            self.hmac_secret.encode(),
            f"{state_data}:{session_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{state_data}.{signature}"
    
    def generate_provider_state(self, provider: 'AuthProvider', session_id: str) -> str:
        """
        Generate provider-specific OAuth state parameter
        
        Args:
            provider: OAuth provider enum
            session_id: Session ID to bind state to
            
        Returns:
            Provider-specific state parameter
        """
        # Generate base state with provider prefix
        base_state = secrets.token_urlsafe(24)
        provider_state = f"{provider.value}:{base_state}"
        
        # Create HMAC signature including provider
        signature = hmac.new(
            self.hmac_secret.encode(),
            f"{provider_state}:{session_id}".encode(),
            hashlib.sha256
        ).hexdigest()[:16]  # Truncate for readability
        
        return f"{base_state}_{signature}"
    
    def store_provider_state(self, provider: 'AuthProvider', state: str, session_id: str) -> bool:
        """
        Store provider-specific OAuth state
        
        Args:
            provider: OAuth provider
            state: State parameter to store
            session_id: Session ID to bind to
            
        Returns:
            True if stored successfully
        """
        provider_state_key = f"oauth_state:{provider.value}:{state}"
        state_data = {
            "session_id": session_id,
            "provider": provider.value,
            "timestamp": time.time()
        }
        
        # Use memory store if Redis not available (for testing)
        if self._use_memory_store():
            if provider_state_key in self._memory_store:
                return False
            self._memory_store[provider_state_key] = state_data
            return True
        
        # Use Redis for production
        try:
            if not self.redis_manager.is_available():
                self.redis_manager.connect()
                
            redis_client = self.redis_client
            if not redis_client:
                return False
                
            result = redis_client.set(
                provider_state_key,
                json.dumps(state_data),
                ex=600,  # 10 minutes
                nx=True
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Provider state storage error: {e}")
            return False
    
    def validate_provider_state(self, provider: 'AuthProvider', state: str, session_id: str) -> bool:
        """
        Validate provider-specific OAuth state
        
        Args:
            provider: OAuth provider
            state: State parameter to validate
            session_id: Expected session ID
            
        Returns:
            True if valid and matches provider/session
        """
        provider_state_key = f"oauth_state:{provider.value}:{state}"
        
        # Use memory store if Redis not available (for testing)
        if self._use_memory_store():
            if provider_state_key not in self._memory_store:
                return False
                
            state_data = self._memory_store[provider_state_key]
            stored_session_id = state_data.get("session_id", "")
            stored_provider = state_data.get("provider", "")
            stored_timestamp = state_data.get("timestamp", 0)
            
            # Check expiration
            import time as time_module
            if time_module.time() - stored_timestamp > 600:
                del self._memory_store[provider_state_key]
                return False
            
            # Delete on validation attempt (single use)
            del self._memory_store[provider_state_key]
            
            # Validate provider and session (timing-safe)
            provider_match = hmac.compare_digest(stored_provider, provider.value)
            session_match = hmac.compare_digest(stored_session_id, session_id)
            
            return provider_match and session_match
        
        # Use Redis for production
        try:
            if not self.redis_manager.is_available():
                self.redis_manager.connect()
                
            redis_client = self.redis_client
            if not redis_client:
                return False
                
            state_data_json = redis_client.get(provider_state_key)
            if not state_data_json:
                return False
                
            state_data = json.loads(state_data_json)
            stored_session_id = state_data.get("session_id", "")
            stored_provider = state_data.get("provider", "")
            stored_timestamp = state_data.get("timestamp", 0)
            
            # Check expiration
            import time as time_module
            if time_module.time() - stored_timestamp > 600:
                redis_client.delete(provider_state_key)
                return False
            
            # Validate provider and session (timing-safe)
            provider_match = hmac.compare_digest(stored_provider, provider.value)
            session_match = hmac.compare_digest(stored_session_id, session_id)
            
            # Delete on validation attempt (single use)
            redis_client.delete(provider_state_key)
            
            return provider_match and session_match
            
        except Exception as e:
            logger.error(f"Provider state validation error: {e}")
            return False
    
    def handle_oauth_failure(self, state: str, session_id: str, error: str) -> None:
        """
        Handle OAuth failure by cleaning up state
        
        Args:
            state: State parameter to clean up
            session_id: Session ID
            error: Error description for logging
        """
        # Use memory store if Redis not available (for testing)
        if self._use_memory_store():
            # Clean up regular state
            state_key = f"oauth_state:{state}"
            if state_key in self._memory_store:
                del self._memory_store[state_key]
            
            # Clean up provider-specific states
            for provider in ['google', 'github', 'local']:
                provider_state_key = f"oauth_state:{provider}:{state}"
                if provider_state_key in self._memory_store:
                    del self._memory_store[provider_state_key]
                    
            logger.info(f"Cleaned up OAuth state after failure: {error}")
            return
        
        # Use Redis for production
        try:
            if not self.redis_manager.is_available():
                self.redis_manager.connect()
                
            redis_client = self.redis_client
            if not redis_client:
                return
                
            # Clean up regular state
            state_key = f"oauth_state:{state}"
            redis_client.delete(state_key)
            
            # Clean up provider-specific states
            for provider in ['google', 'github', 'local']:
                provider_state_key = f"oauth_state:{provider}:{state}"
                redis_client.delete(provider_state_key)
                
            logger.info(f"Cleaned up OAuth state after failure: {error}")
            
        except Exception as e:
            logger.error(f"OAuth failure cleanup error: {e}")
    
    def _decode_state(self, state: str) -> Optional[Dict]:
        """Decode and parse state parameter"""
        try:
            # Handle HMAC-signed state
            if self.validate_hmac_state_signature(state):
                decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
                state_json = decoded_state.rsplit("|", 1)[0]
                return json.loads(state_json)
            
            # Handle unsigned state (for compatibility)
            decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
            return json.loads(decoded_state)
            
        except Exception as e:
            logger.error(f"State decoding error: {e}")
            return None
    
    def _is_valid_origin(self, origin: str) -> bool:
        """Check if origin is in allowed list"""
        allowed_origins = [
            "https://app.netra.ai",
            "https://app.staging.netra.ai",
            "http://localhost:3000"
        ]
        return origin in allowed_origins


class JWTSecurityValidator:
    """Enhanced JWT security validation"""
    
    def __init__(self):
        self.strong_secret = self._get_strong_secret()
        self.allowed_algorithms = ["HS256", "RS256"]
    
    def _get_strong_secret(self) -> str:
        """Get strong JWT secret using proper secret loading chain"""
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        try:
            secret = AuthSecretLoader.get_jwt_secret()
        except ValueError as e:
            # No fallback in any environment - require explicit JWT configuration
            env = os.getenv("ENVIRONMENT", "development").lower()
            raise ValueError(f"JWT secret not configured for {env} environment") from e
        
        # Ensure secret is strong enough for production environments
        env = os.getenv("ENVIRONMENT", "development").lower()
        if len(secret) < 32 and env in ["staging", "production"]:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
        
        return secret
    
    def validate_token_security(self, token: str) -> bool:
        """
        Validate token uses secure algorithms and parameters
        
        Args:
            token: JWT token to validate
            
        Returns:
            True if token passes security validation
        """
        try:
            import jwt
            
            # Decode header without verification to check algorithm
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            
            # Check if algorithm is allowed
            if algorithm not in self.allowed_algorithms:
                logger.warning(f"Insecure JWT algorithm: {algorithm}")
                return False
            
            # Check for algorithm confusion attacks
            if algorithm == "none":
                logger.warning("JWT algorithm 'none' is not allowed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"JWT security validation error: {e}")
            return False


class SessionFixationProtector:
    """Protects against session fixation attacks"""
    
    def __init__(self, session_manager):
        self.session_manager = session_manager
    
    def regenerate_session_after_login(self, old_session_id: Optional[str], user_id: str, user_data: Dict) -> str:
        """
        Regenerate session ID after successful authentication
        
        Args:
            old_session_id: Previous session ID (if any)
            user_id: Authenticated user ID
            user_data: User session data
            
        Returns:
            New secure session ID
        """
        try:
            # Generate new session ID
            new_session_id = secrets.token_urlsafe(32)
            
            # Invalidate old session if exists
            if old_session_id:
                self.session_manager.delete_session(old_session_id)
            
            # Create new session with new ID
            self.session_manager.create_session(
                user_id=user_id,
                user_data=user_data,
                session_id=new_session_id
            )
            
            logger.info(f"Session regenerated for user {user_id}")
            return new_session_id
            
        except Exception as e:
            logger.error(f"Session regeneration error: {e}")
            # Return a fallback session ID
            return secrets.token_urlsafe(32)


class OAuthStateCleanupManager:
    """Manages cleanup of expired OAuth states and tokens"""
    
    def __init__(self, redis_client: Optional[any] = None):
        # Use unified Redis manager instead of passed client
        self.redis_manager = auth_redis_manager
        
    @property
    def redis_client(self):
        """Get Redis client from unified manager."""
        return self.redis_manager.get_client()
    
    def cleanup_expired_states(self) -> int:
        """
        Clean up expired OAuth states, nonces, and authorization codes
        
        Returns:
            Number of items cleaned up
        """
        if not self.redis_client:
            return 0
            
        cleaned_count = 0
        
        try:
            # Get all OAuth-related keys
            oauth_patterns = [
                "oauth_nonce:*",
                "oauth_code:*", 
                "oauth_state:*"
            ]
            
            for pattern in oauth_patterns:
                keys = list(self.redis_client.scan_iter(match=pattern))
                
                for key in keys:
                    # Check TTL - if expired or no TTL set, remove
                    ttl = self.redis_client.ttl(key)
                    if ttl == -1:  # No expiry set
                        self.redis_client.delete(key)
                        cleaned_count += 1
                        logger.debug(f"Cleaned up OAuth key with no TTL: {key}")
                    elif ttl == -2:  # Key doesn't exist (already expired)
                        cleaned_count += 1
                        
            if cleaned_count > 0:
                logger.info(f"OAuth cleanup: removed {cleaned_count} expired items")
                
        except Exception as e:
            logger.error(f"OAuth state cleanup error: {e}")
            
        return cleaned_count
    
    def add_state_isolation(self, state: str, user_session_id: str) -> bool:
        """
        Add state isolation for concurrent OAuth flows
        
        Args:
            state: OAuth state parameter
            user_session_id: User's session ID for isolation
            
        Returns:
            True if state was successfully isolated
        """
        if not self.redis_client:
            return True  # Graceful degradation
            
        try:
            # Create isolated state key that includes session ID
            isolated_key = f"oauth_state:{user_session_id}:{state}"
            
            # Set with short TTL (10 minutes) and NX to prevent collisions
            result = self.redis_client.set(isolated_key, "active", ex=600, nx=True)
            
            if not result:
                logger.warning(f"OAuth state isolation failed - concurrent state detected: {state}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"OAuth state isolation error: {e}")
            return True  # Graceful degradation
    
    def validate_isolated_state(self, state: str, user_session_id: str) -> bool:
        """
        Validate and consume isolated OAuth state
        
        Args:
            state: OAuth state parameter
            user_session_id: User's session ID
            
        Returns:
            True if state is valid and was consumed
        """
        if not self.redis_client:
            return True  # Graceful degradation
            
        try:
            isolated_key = f"oauth_state:{user_session_id}:{state}"
            
            # Check if state exists and delete it atomically
            result = self.redis_client.delete(isolated_key)
            
            if result == 0:
                logger.warning(f"OAuth state not found or already consumed: {state}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"OAuth state validation error: {e}")
            return True  # Graceful degradation


def validate_cors_origin(origin: str) -> bool:
    """
    Validate CORS origin against whitelist with comprehensive security checks
    
    Args:
        origin: Origin header value
        
    Returns:
        True if origin is allowed
    """
    if not origin:
        return False
    
    # Strict whitelist of allowed origins
    allowed_origins = [
        "https://app.netra.ai",
        "https://app.staging.netra.ai",
        "https://app.staging.netrasystems.ai", 
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",  # Backend dev
        "http://127.0.0.1:8000"   # Backend dev
    ]
    
    # Check for exact match
    if origin in allowed_origins:
        logger.debug(f"CORS origin allowed: {origin}")
        return True
    
    # Additional checks for development environment
    from auth_service.auth_core.config import AuthConfig
    env = AuthConfig.get_environment()
    
    if env == "development":
        # Allow localhost and 127.0.0.1 with any port in development
        import re
        dev_pattern = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        if re.match(dev_pattern, origin):
            logger.debug(f"CORS origin allowed in development: {origin}")
            return True
    
    # Log blocked origins for security monitoring
    logger.warning(f"CORS origin blocked: {origin}")
    return False