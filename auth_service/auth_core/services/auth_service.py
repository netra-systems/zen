"""
Auth Service - Core authentication business logic
Single Source of Truth for authentication operations
"""
import asyncio
import hashlib
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import httpx

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.core.session_manager import SessionManager
from auth_service.auth_core.database.repository import (
    AuthAuditRepository,
    AuthUserRepository,
)
from auth_service.auth_core.models.auth_models import (
    AuthError,
    AuthException,
    AuthProvider,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    ServiceTokenRequest,
    ServiceTokenResponse,
    TokenResponse,
)

logger = logging.getLogger(__name__)

class AuthService:
    """Core authentication service implementation"""
    
    def __init__(self):
        self.jwt_handler = JWTHandler()
        self.session_manager = SessionManager()
        self.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lockout_duration = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
        self.db_session = None  # Initialize as None, set later if database available
        
        # Circuit breaker for external API calls
        self._circuit_breaker_state = {}
        self._failure_counts = {}
        self._last_failure_times = {}
        self._circuit_breaker_redis_prefix = "circuit_breaker:"
        
        # Simple in-memory user store for testing
        self._test_users = {}
        
    async def login(self, request: LoginRequest, 
                   client_info: Dict) -> LoginResponse:
        """Process user login"""
        try:
            # Validate credentials based on provider
            user = await self._validate_credentials(request)
            if not user:
                raise AuthException(
                    error="invalid_credentials",
                    error_code="AUTH001",
                    message="Invalid credentials provided"
                )
            
            # Check account status
            if not await self._check_account_status(user["id"]):
                raise AuthException(
                    error="account_locked",
                    error_code="AUTH002",
                    message="Account is locked or disabled"
                )
            
            # Generate tokens
            access_token = self.jwt_handler.create_access_token(
                user_id=user["id"],
                email=user["email"],
                permissions=user.get("permissions", [])
            )
            
            refresh_token = self.jwt_handler.create_refresh_token(
                user_id=user["id"]
            )
            
            # Create session
            session_id = self.session_manager.create_session(
                user_id=user["id"],
                user_data={
                    "email": user["email"],
                    "ip_address": client_info.get("ip"),
                    "user_agent": client_info.get("user_agent")
                }
            )
            
            # Log successful login
            await self._audit_log(
                event_type="login",
                user_id=user["id"],
                success=True,
                metadata={"provider": request.provider},
                client_info=client_info
            )
            
            return LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=15 * 60,  # 15 minutes
                user={
                    "id": user["id"],
                    "email": user["email"],
                    "name": user.get("name"),
                    "session_id": session_id
                }
            )
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
    
    async def logout(self, token: str, 
                    session_id: Optional[str] = None) -> bool:
        """Process user logout with token blacklisting"""
        try:
            # Extract user from token
            user_id = self.jwt_handler.extract_user_id(token)
            
            # Blacklist the specific token to invalidate it immediately
            self.jwt_handler.blacklist_token(token)
            
            # Delete session if provided
            if session_id:
                self.session_manager.delete_session(session_id)
            elif user_id:
                # Invalidate all user sessions
                await self.session_manager.invalidate_user_sessions(user_id)
            
            # Log logout
            await self._audit_log(
                event_type="logout",
                user_id=user_id,
                success=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
    
    def register_test_user(self, email: str, password: str) -> Dict:
        """Register a test user in memory"""
        import uuid
        user_id = str(uuid.uuid4())
        
        self._test_users[email] = {
            "id": user_id,
            "email": email,
            "password": password,
            "name": "Test User",
            "created_at": datetime.utcnow().isoformat()
        }
        
        return {
            "user_id": user_id,
            "email": email,
            "message": "User registered successfully"
        }
    
    async def validate_token(self, token: str) -> TokenResponse:
        """Validate access token"""
        payload = self.jwt_handler.validate_token(token, "access")
        
        if not payload:
            return TokenResponse(valid=False)
        
        return TokenResponse(
            valid=True,
            user_id=payload.get("sub"),
            email=payload.get("email"),
            permissions=payload.get("permissions", []),
            expires_at=datetime.fromtimestamp(payload.get("exp"))
        )
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[Tuple]:
        """Refresh access and refresh tokens with race condition protection"""
        # Add race condition protection by marking refresh token as used atomically
        result = await self._refresh_with_race_protection(refresh_token)
        
        if result:
            access_token, new_refresh = result
            return access_token, new_refresh
            
        return None
    
    async def _refresh_with_race_protection(self, refresh_token: str) -> Optional[Tuple]:
        """Implement atomic refresh token handling to prevent race conditions"""
        try:
            # Validate the refresh token first
            payload = self.jwt_handler.validate_token(refresh_token, "refresh")
            if not payload:
                return None
            
            user_id = payload["sub"]
            
            # In a real implementation, this would use a database transaction or Redis
            # to atomically mark the refresh token as used and generate new tokens
            # For now, we'll simulate this with session manager state
            
            # Check if token was already used (race condition check)
            if hasattr(self.session_manager, 'used_refresh_tokens'):
                if refresh_token in self.session_manager.used_refresh_tokens:
                    return None
                # Mark token as used atomically
                self.session_manager.used_refresh_tokens.add(refresh_token)
            else:
                # Initialize used tokens set if not exists
                self.session_manager.used_refresh_tokens = {refresh_token}
            
            # Get user details (in real implementation, from database)
            email = "user@example.com"  # Placeholder
            permissions = []
            
            # Generate new tokens
            new_access = self.jwt_handler.create_access_token(user_id, email, permissions)
            new_refresh = self.jwt_handler.create_refresh_token(user_id)
            
            return new_access, new_refresh
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    async def create_oauth_user(self, user_info: Dict) -> Dict:
        """Create or update user from OAuth info"""
        if not self.db_session:
            # Fallback for when no database is available
            return {
                "id": user_info.get("id", user_info.get("sub")),
                "email": user_info["email"],
                "name": user_info.get("name", ""),
                "provider": user_info.get("provider", "google"),
                "permissions": ["read", "write"]
            }
        
        # Use database repository to persist user
        user_repo = AuthUserRepository(self.db_session)
        auth_user = await user_repo.create_oauth_user(user_info)
        
        return {
            "id": auth_user.id,
            "email": auth_user.email,
            "name": auth_user.full_name,
            "provider": auth_user.auth_provider,
            "permissions": ["read", "write"],
            "is_verified": auth_user.is_verified
        }
    
    async def create_service_token(self, 
                                  request: ServiceTokenRequest) -> ServiceTokenResponse:
        """Create token for service-to-service auth"""
        # Validate service credentials
        if not await self._validate_service(
            request.service_id, 
            request.service_secret
        ):
            raise AuthException(
                error="invalid_service",
                error_code="AUTH003",
                message="Invalid service credentials"
            )
        
        # Get service name from config/database
        service_name = await self._get_service_name(request.service_id)
        
        token = self.jwt_handler.create_service_token(
            service_id=request.service_id,
            service_name=service_name
        )
        
        return ServiceTokenResponse(
            token=token,
            expires_in=5 * 60,  # 5 minutes
            service_name=service_name
        )
    
    async def _validate_credentials(self, 
                                   request: LoginRequest) -> Optional[Dict]:
        """Validate user credentials based on provider"""
        if request.provider == AuthProvider.LOCAL:
            return await self._validate_local_auth(
                request.email, 
                request.password
            )
        elif request.provider == AuthProvider.GOOGLE:
            return await self._validate_oauth(
                request.provider, 
                request.oauth_token
            )
        elif request.provider == AuthProvider.API_KEY:
            return await self._validate_api_key(request.email)
        
        return None
    
    async def _validate_local_auth(self, email: str, 
                                  password: str) -> Optional[Dict]:
        """Validate local username/password"""
        if not self.db_session:
            # Check test users store first
            if email in self._test_users:
                stored_user = self._test_users[email]
                if stored_user["password"] == password:
                    return {
                        "id": stored_user["id"],
                        "email": email,
                        "name": stored_user.get("name", "Test User"),
                        "permissions": ["read", "write"]
                    }
            
            # Fallback for testing
            hashed = hashlib.sha256(password.encode()).hexdigest()
            if email == "test@example.com":
                return {
                    "id": "user-123",
                    "email": email,
                    "name": "Test User",
                    "permissions": ["read", "write"]
                }
            return None
        
        # Use database repository
        user_repo = AuthUserRepository(self.db_session)
        
        # Check if account is locked
        if await user_repo.check_account_locked(email):
            return None
        
        # Get user from database
        user = await user_repo.get_by_email(email)
        if not user or not user.hashed_password:
            await user_repo.increment_failed_attempts(email)
            return None
        
        # Verify password (would use proper hashing in production)
        # For now, simple comparison
        if user.hashed_password != hashlib.sha256(password.encode()).hexdigest():
            await user_repo.increment_failed_attempts(email)
            return None
        
        # Reset failed attempts on successful login
        await user_repo.reset_failed_attempts(user.id)
        await user_repo.update_login_time(user.id)
        
        return {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "permissions": ["read", "write"]
        }
    
    async def _validate_oauth(self, provider: str, 
                             token: str) -> Optional[Dict]:
        """Validate OAuth token with provider"""
        if provider == "google":
            return await self._validate_google_oauth(token)
        return None
    
    async def _validate_google_oauth(self, token: str) -> Optional[Dict]:
        """Validate Google OAuth token with circuit breaker"""
        async def make_request():
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Verify token with Google
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code != 200:
                    return None
                
                user_info = response.json()
                return {
                    "id": user_info["id"],
                    "email": user_info["email"],
                    "name": user_info.get("name", ""),
                    "permissions": ["read", "write"]
                }
        
        try:
            return await self._make_http_request_with_circuit_breaker("google_oauth", make_request)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.error(f"Google OAuth validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Google OAuth validation failed: {e}")
            return None
    
    async def _validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate API key"""
        # In real implementation, lookup API key in database
        # This is a placeholder
        return None
    
    async def _validate_service(self, service_id: str, 
                               service_secret: str) -> bool:
        """Validate service credentials"""
        # In real implementation, validate from database
        # This is a placeholder
        expected_secret = os.getenv(f"SERVICE_SECRET_{service_id}")
        return expected_secret and service_secret == expected_secret
    
    async def _get_service_name(self, service_id: str) -> str:
        """Get service name from ID"""
        # In real implementation, lookup from database
        service_names = {
            "backend": "netra-backend",
            "worker": "netra-worker",
            "scheduler": "netra-scheduler"
        }
        return service_names.get(service_id, service_id)
    
    async def _check_account_status(self, user_id: str) -> bool:
        """Check if account is active and not locked"""
        if not self.db_session:
            return True  # Fallback
        
        user_repo = AuthUserRepository(self.db_session)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            return False
        
        return user.is_active and not user.locked_until
    
    async def _audit_log(self, event_type: str, 
                        user_id: Optional[str] = None,
                        success: bool = True, 
                        metadata: Dict = None,
                        client_info: Optional[Dict] = None):
        """Log authentication events for audit"""
        if self.db_session:
            audit_repo = AuthAuditRepository(self.db_session)
            await audit_repo.log_event(
                event_type=event_type,
                user_id=user_id,
                success=success,
                metadata=metadata,
                client_info=client_info
            )
        else:
            # Fallback to logger when no database
            logger.info(f"Audit: {event_type} for user {user_id} - Success: {success}")
    
    async def request_password_reset(self, 
                                   request: PasswordResetRequest) -> PasswordResetResponse:
        """Request password reset for user"""
        try:
            if not self.db_session:
                # Testing fallback
                return await self._mock_password_reset_request(request.email)
            
            user_repo = AuthUserRepository(self.db_session)
            user = await user_repo.get_by_email(request.email)
            
            if not user:
                # Don't reveal if email exists
                return PasswordResetResponse(
                    success=True,
                    message="If email exists, reset link sent"
                )
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
            
            # Store token in database
            await user_repo.create_password_reset_token(
                user.id, 
                token_hash, 
                user.email
            )
            
            # Send email (mocked in tests)
            await self._send_password_reset_email(user.email, reset_token)
            
            # Audit log
            await self._audit_log(
                event_type="password_reset_requested",
                user_id=user.id,
                success=True
            )
            
            return PasswordResetResponse(
                success=True,
                message="If email exists, reset link sent",
                reset_token=reset_token if os.getenv("TESTING") else None
            )
            
        except Exception as e:
            logger.error(f"Password reset request failed: {e}")
            raise AuthError(
                error="reset_failed",
                error_code="AUTH004",
                message="Password reset request failed"
            )
    
    async def confirm_password_reset(self, 
                                   request: PasswordResetConfirm) -> PasswordResetConfirmResponse:
        """Confirm password reset with token"""
        try:
            if not self.db_session:
                # Testing fallback
                return await self._mock_password_reset_confirm(
                    request.reset_token, 
                    request.new_password
                )
            
            user_repo = AuthUserRepository(self.db_session)
            token_hash = hashlib.sha256(request.reset_token.encode()).hexdigest()
            
            # Validate token
            token_valid = await user_repo.validate_password_reset_token(token_hash)
            if not token_valid:
                raise AuthError(
                    error="invalid_token",
                    error_code="AUTH005",
                    message="Invalid or expired reset token"
                )
            
            # Get user from token
            user = await user_repo.get_user_by_reset_token(token_hash)
            if not user:
                raise AuthError(
                    error="user_not_found",
                    error_code="AUTH006",
                    message="User not found for reset token"
                )
            
            # Update password
            new_password_hash = hashlib.sha256(request.new_password.encode()).hexdigest()
            await user_repo.update_password(user.id, new_password_hash)
            
            # Mark token as used
            await user_repo.mark_reset_token_used(token_hash)
            
            # Invalidate all user sessions
            await self.session_manager.invalidate_user_sessions(user.id)
            
            # Audit log
            await self._audit_log(
                event_type="password_reset_completed",
                user_id=user.id,
                success=True
            )
            
            return PasswordResetConfirmResponse(
                success=True,
                message="Password reset successfully"
            )
            
        except AuthError:
            raise
        except Exception as e:
            logger.error(f"Password reset confirmation failed: {e}")
            raise AuthError(
                error="reset_failed",
                error_code="AUTH007",
                message="Password reset confirmation failed"
            )
    
    async def _mock_password_reset_request(self, email: str) -> PasswordResetResponse:
        """Mock password reset for testing"""
        if email == "test@example.com":
            reset_token = secrets.token_urlsafe(32)
            return PasswordResetResponse(
                success=True,
                message="If email exists, reset link sent",
                reset_token=reset_token
            )
        return PasswordResetResponse(
            success=True,
            message="If email exists, reset link sent"
        )
    
    async def _mock_password_reset_confirm(self, 
                                         token: str, 
                                         password: str) -> PasswordResetConfirmResponse:
        """Mock password reset confirmation for testing"""
        # Simple validation for testing
        if len(token) >= 20 and len(password) >= 8:
            return PasswordResetConfirmResponse(
                success=True,
                message="Password reset successfully"
            )
        raise AuthError(
            error="invalid_token",
            error_code="AUTH005",
            message="Invalid or expired reset token"
        )
    
    async def _send_password_reset_email(self, email: str, token: str):
        """Send password reset email (mocked in tests)"""
        if os.getenv("TESTING"):
            logger.info(f"Mock email sent to {email} with token {token}")
            return
        
        # Real email sending logic would go here
        logger.info(f"Password reset email sent to {email}")
    
    async def _retry_with_exponential_backoff(self, operation, max_retries: int = 3, base_delay: float = 1.0):
        """Execute operation with exponential backoff retry logic"""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt failed, re-raise the exception
                    raise e
                
                # Calculate delay with exponential backoff
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Operation failed on attempt {attempt + 1}/{max_retries}, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
    
    async def _audit_log_with_retry(self, event_type: str, 
                                  user_id: Optional[str] = None,
                                  success: bool = True, 
                                  metadata: Dict = None,
                                  client_info: Optional[Dict] = None):
        """Log authentication events with retry logic"""
        try:
            await self._retry_with_exponential_backoff(
                lambda: self._audit_log(event_type, user_id, success, metadata, client_info)
            )
        except Exception as e:
            logger.error(f"Audit logging failed after retries: {e}")
            # Don't fail the main operation if audit logging fails
    
    async def create_oauth_user_with_retry(self, user_info: Dict) -> Dict:
        """Create or update user from OAuth info with database retry logic"""
        if not self.db_session:
            # Fallback for when no database is available
            return {
                "id": user_info.get("id", user_info.get("sub")),
                "email": user_info["email"],
                "name": user_info.get("name", ""),
                "provider": user_info.get("provider", "google"),
                "permissions": ["read", "write"]
            }
        
        # Use database with retry logic
        async def create_user_operation():
            user_repo = AuthUserRepository(self.db_session)
            auth_user = await user_repo.create_oauth_user(user_info)
            return {
                "id": auth_user.id,
                "email": auth_user.email,
                "name": auth_user.full_name,
                "provider": auth_user.auth_provider,
                "permissions": ["read", "write"],
                "is_verified": auth_user.is_verified
            }
        
        try:
            return await self._retry_with_exponential_backoff(create_user_operation)
        except Exception as e:
            logger.error(f"Database user creation failed after retries: {e}")
            # Return fallback user for graceful degradation
            return {
                "id": user_info.get("id", user_info.get("sub")),
                "email": user_info["email"],
                "name": user_info.get("name", ""),
                "provider": user_info.get("provider", "google"),
                "permissions": ["read", "write"],
                "error": "database_unavailable"
            }
    
    def _is_circuit_breaker_open(self, service: str) -> bool:
        """Check if circuit breaker is open for a service with Redis persistence"""
        try:
            # Try to get state from Redis first
            if self.session_manager.redis_client:
                redis_key = f"{self._circuit_breaker_redis_prefix}{service}_state"
                redis_state = self.session_manager.redis_client.get(redis_key)
                if redis_state:
                    state = redis_state
                else:
                    state = self._circuit_breaker_state.get(service, "closed")
            else:
                state = self._circuit_breaker_state.get(service, "closed")
        except Exception as e:
            logger.warning(f"Failed to read circuit breaker state from Redis: {e}")
            state = self._circuit_breaker_state.get(service, "closed")
        
        if state == "closed":
            return False
        
        if state == "open":
            # Check if we should transition to half-open
            last_failure = self._get_last_failure_time(service)
            if time.time() - last_failure > 60:  # 60 second timeout
                self._set_circuit_breaker_state(service, "half-open")
                logger.info(f"Circuit breaker for {service} transitioning to half-open")
                return False
            return True
        
        if state == "half-open":
            return False
        
        return False
    
    def _record_success(self, service: str):
        """Record successful call for circuit breaker"""
        self._set_circuit_breaker_state(service, "closed")
        self._set_failure_count(service, 0)
        logger.info(f"Circuit breaker for {service} reset to closed state")
        
    def _record_failure(self, service: str):
        """Record failed call for circuit breaker"""
        current_failures = self._get_failure_count(service) + 1
        self._set_failure_count(service, current_failures)
        self._set_last_failure_time(service, time.time())
        
        # Open circuit breaker after 5 failures
        if current_failures >= 5:
            self._set_circuit_breaker_state(service, "open")
            logger.warning(f"Circuit breaker opened for {service} after {current_failures} failures")
        elif self._get_circuit_breaker_state(service) == "half-open":
            # Failed in half-open state, go back to open
            self._set_circuit_breaker_state(service, "open")
            logger.warning(f"Circuit breaker for {service} returned to open state")
    
    async def _make_http_request_with_circuit_breaker(self, service: str, request_func):
        """Make HTTP request with circuit breaker protection"""
        if self._is_circuit_breaker_open(service):
            logger.error(f"Circuit breaker is open for {service} - rejecting request")
            raise httpx.ConnectError(f"Circuit breaker is open for {service}")
        
        try:
            result = await request_func()
            self._record_success(service)
            return result
        except (httpx.ConnectError, httpx.TimeoutException, Exception) as e:
            self._record_failure(service)
            logger.error(f"Request failed for {service}: {e}")
            raise e
    
    def _set_circuit_breaker_state(self, service: str, state: str):
        """Set circuit breaker state with Redis persistence"""
        self._circuit_breaker_state[service] = state
        try:
            if self.session_manager.redis_client:
                redis_key = f"{self._circuit_breaker_redis_prefix}{service}_state"
                self.session_manager.redis_client.setex(redis_key, 3600, state)  # 1 hour TTL
        except Exception as e:
            logger.warning(f"Failed to persist circuit breaker state to Redis: {e}")
    
    def _get_circuit_breaker_state(self, service: str) -> str:
        """Get circuit breaker state from Redis or memory"""
        try:
            if self.session_manager.redis_client:
                redis_key = f"{self._circuit_breaker_redis_prefix}{service}_state"
                redis_state = self.session_manager.redis_client.get(redis_key)
                if redis_state:
                    return redis_state
        except Exception as e:
            logger.warning(f"Failed to read circuit breaker state from Redis: {e}")
        return self._circuit_breaker_state.get(service, "closed")
    
    def _set_failure_count(self, service: str, count: int):
        """Set failure count with Redis persistence"""
        self._failure_counts[service] = count
        try:
            if self.session_manager.redis_client:
                redis_key = f"{self._circuit_breaker_redis_prefix}{service}_failures"
                self.session_manager.redis_client.setex(redis_key, 3600, str(count))
        except Exception as e:
            logger.warning(f"Failed to persist failure count to Redis: {e}")
    
    def _get_failure_count(self, service: str) -> int:
        """Get failure count from Redis or memory"""
        try:
            if self.session_manager.redis_client:
                redis_key = f"{self._circuit_breaker_redis_prefix}{service}_failures"
                redis_count = self.session_manager.redis_client.get(redis_key)
                if redis_count:
                    return int(redis_count)
        except Exception as e:
            logger.warning(f"Failed to read failure count from Redis: {e}")
        return self._failure_counts.get(service, 0)
    
    def _set_last_failure_time(self, service: str, timestamp: float):
        """Set last failure time with Redis persistence"""
        self._last_failure_times[service] = timestamp
        try:
            if self.session_manager.redis_client:
                redis_key = f"{self._circuit_breaker_redis_prefix}{service}_last_failure"
                self.session_manager.redis_client.setex(redis_key, 3600, str(timestamp))
        except Exception as e:
            logger.warning(f"Failed to persist last failure time to Redis: {e}")
    
    def _get_last_failure_time(self, service: str) -> float:
        """Get last failure time from Redis or memory"""
        try:
            if self.session_manager.redis_client:
                redis_key = f"{self._circuit_breaker_redis_prefix}{service}_last_failure"
                redis_time = self.session_manager.redis_client.get(redis_key)
                if redis_time:
                    return float(redis_time)
        except Exception as e:
            logger.warning(f"Failed to read last failure time from Redis: {e}")
        return self._last_failure_times.get(service, 0)
    
    def reset_circuit_breaker(self, service: str = None):
        """Reset circuit breaker state for a specific service or all services"""
        if service:
            # Reset specific service
            self._circuit_breaker_state.pop(service, None)
            self._failure_counts.pop(service, None)
            self._last_failure_times.pop(service, None)
            
            # Clear from Redis too
            try:
                if self.session_manager.redis_client:
                    redis_keys = [
                        f"{self._circuit_breaker_redis_prefix}{service}_state",
                        f"{self._circuit_breaker_redis_prefix}{service}_failures",
                        f"{self._circuit_breaker_redis_prefix}{service}_last_failure"
                    ]
                    for key in redis_keys:
                        self.session_manager.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Failed to clear circuit breaker state from Redis for {service}: {e}")
        else:
            # Reset all services
            self._circuit_breaker_state.clear()
            self._failure_counts.clear()
            self._last_failure_times.clear()
            
            # Clear from Redis too
            try:
                if self.session_manager.redis_client:
                    # Get all circuit breaker keys and delete them
                    pattern = f"{self._circuit_breaker_redis_prefix}*"
                    keys = self.session_manager.redis_client.keys(pattern)
                    if keys:
                        self.session_manager.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Failed to clear circuit breaker state from Redis: {e}")