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
from typing import Dict, Optional, Tuple
import redis

logger = logging.getLogger(__name__)


class OAuthSecurityManager:
    """Manages OAuth security validations and protections"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.hmac_secret = self._get_hmac_secret()
        
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
        redis_client = self.redis_client
        
        # If no Redis client, try to create one for testing
        if not redis_client:
            try:
                import os
                import redis
                # Try to connect to Redis with various URLs for testing
                redis_urls = [
                    os.getenv("REDIS_URL"),
                    os.getenv("TEST_REDIS_URL"),
                    "redis://localhost:6379",
                ]
                
                for url in redis_urls:
                    if url:
                        try:
                            test_client = redis.from_url(url, decode_responses=True)
                            test_client.ping()
                            redis_client = test_client
                            logger.info(f"Connected to Redis for nonce checking: {url}")
                            break
                        except Exception:
                            continue
                            
                # Also try testcontainer Redis information if available
                test_redis_host = os.getenv("TEST_REDIS_HOST", "localhost")
                test_redis_port = os.getenv("TEST_REDIS_PORT")
                
                if test_redis_port:
                    try:
                        test_client = redis.Redis(
                            host=test_redis_host, 
                            port=int(test_redis_port), 
                            decode_responses=True,
                            socket_timeout=1.0
                        )
                        test_client.ping()
                        redis_client = test_client
                        self.redis_client = redis_client  # Cache for future use
                        logger.info(f"Connected to test Redis: {test_redis_host}:{test_redis_port}")
                    except Exception as e:
                        logger.warning(f"Failed to connect to test Redis: {e}")
                
                # If still no Redis, try common test ports
                if not redis_client:
                    test_ports = [6379, 6380, 16379, 26379]
                    for port in test_ports:
                        try:
                            test_client = redis.Redis(host='localhost', port=port, decode_responses=True, socket_timeout=0.5)
                            test_client.ping()
                            redis_client = test_client
                            logger.info(f"Connected to Redis on port: {port}")
                            break
                        except Exception:
                            continue
                        
            except Exception as e:
                logger.warning(f"Could not establish Redis connection for nonce checking: {e}")
        
        if not redis_client:
            logger.warning("Redis not available for nonce tracking")
            return True  # Allow if Redis not available
            
        try:
            nonce_key = f"oauth_nonce:{nonce}"
            
            # Check if nonce exists
            if redis_client.exists(nonce_key):
                logger.warning(f"Nonce replay attack detected: {nonce}")
                return False
            
            # Store nonce with 10-minute expiry
            redis_client.setex(nonce_key, 600, "used")
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
        redis_client = self.redis_client
        
        # If no Redis client, try to connect (same logic as nonce checking)
        if not redis_client:
            try:
                import os
                import redis
                # Try to connect to Redis with various URLs for testing
                redis_urls = [
                    os.getenv("REDIS_URL"),
                    os.getenv("TEST_REDIS_URL"),
                    "redis://localhost:6379",
                ]
                
                for url in redis_urls:
                    if url:
                        try:
                            test_client = redis.from_url(url, decode_responses=True)
                            test_client.ping()
                            redis_client = test_client
                            break
                        except Exception:
                            continue
                            
                # Also try common Redis test ports
                if not redis_client:
                    test_ports = [6379, 6380, 16379, 26379]
                    for port in test_ports:
                        try:
                            test_client = redis.Redis(host='localhost', port=port, decode_responses=True)
                            test_client.ping()
                            redis_client = test_client
                            break
                        except Exception:
                            continue
                            
            except Exception:
                pass
        
        if not redis_client:
            logger.warning("Redis not available for code tracking")
            return True  # Allow if Redis not available
            
        try:
            code_key = f"oauth_code:{code}"
            
            # Check if code already used
            if redis_client.exists(code_key):
                logger.warning(f"Authorization code reuse attack detected: {code}")
                return False
            
            # Mark code as used with 10-minute expiry
            redis_client.setex(code_key, 600, "used")
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
            # If we're in development and no secret is configured, use a development default
            env = os.getenv("ENVIRONMENT", "development").lower()
            if env == "development":
                logger.warning("Using development default JWT secret - NOT FOR PRODUCTION")
                secret = "dev-secret-key-DO-NOT-USE-IN-PRODUCTION-32chars"
            else:
                raise ValueError(f"JWT secret not configured for {env} environment") from e
        
        # Ensure secret is strong enough for production environments
        env = os.getenv("ENVIRONMENT", "development").lower()
        if len(secret) < 32 and env in ["staging", "production"]:
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        
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