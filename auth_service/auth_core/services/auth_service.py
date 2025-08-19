"""
Auth Service - Core authentication business logic
Single Source of Truth for authentication operations
"""
import os
import hashlib
import secrets
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import logging

from ..core.jwt_handler import JWTHandler
from ..core.session_manager import SessionManager
from ..models.auth_models import (
    LoginRequest, LoginResponse, TokenResponse,
    ServiceTokenRequest, ServiceTokenResponse,
    AuthProvider, AuthError
)

logger = logging.getLogger(__name__)

class AuthService:
    """Core authentication service implementation"""
    
    def __init__(self):
        self.jwt_handler = JWTHandler()
        self.session_manager = SessionManager()
        self.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lockout_duration = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
        
    async def login(self, request: LoginRequest, 
                   client_info: Dict) -> LoginResponse:
        """Process user login"""
        try:
            # Validate credentials based on provider
            user = await self._validate_credentials(request)
            if not user:
                raise AuthError(
                    error="invalid_credentials",
                    error_code="AUTH001",
                    message="Invalid credentials provided"
                )
            
            # Check account status
            if not await self._check_account_status(user["id"]):
                raise AuthError(
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
        """Process user logout"""
        try:
            # Extract user from token
            user_id = self.jwt_handler.extract_user_id(token)
            
            # Delete session if provided
            if session_id:
                self.session_manager.delete_session(session_id)
            elif user_id:
                # Invalidate all user sessions
                self.session_manager.invalidate_user_sessions(user_id)
            
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
        """Refresh access and refresh tokens"""
        result = self.jwt_handler.refresh_access_token(refresh_token)
        
        if result:
            access_token, new_refresh = result
            return access_token, new_refresh
            
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
            raise AuthError(
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
        """Validate Google OAuth token"""
        try:
            async with httpx.AsyncClient() as client:
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