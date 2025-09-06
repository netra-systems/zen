"""
Auth Service Database Repository
Repository pattern for auth database operations
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from auth_service.auth_core.database.models import AuthAuditLog, AuthSession, AuthUser
except ImportError:
    from auth_service.auth_core.database.models import AuthAuditLog, AuthSession, AuthUser

logger = logging.getLogger(__name__)

class AuthUserRepository:
    """Repository for auth user operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_email(self, email: str) -> Optional[AuthUser]:
        """Get user by email"""
        result = await self.session.execute(
            select(AuthUser).where(AuthUser.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id: str) -> Optional[AuthUser]:
        """Get user by ID"""
        result = await self.session.execute(
            select(AuthUser).where(AuthUser.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_oauth_user(self, user_info: Dict) -> AuthUser:
        """Create or update OAuth user with atomic transaction and race condition protection"""
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy import select
        
        email = user_info.get("email")
        provider = user_info.get("provider", "google")
        provider_user_id = user_info.get("id", user_info.get("sub"))
        
        if not email:
            raise ValueError("Email is required for OAuth user creation")
        
        max_retries = 3
        for attempt in range(max_retries):
            # CRITICAL FIX: Use a single atomic transaction
            transaction = None
            try:
                # Start atomic transaction
                transaction = await self.session.begin()
                
                # Use SELECT FOR UPDATE to lock the row and prevent race conditions
                stmt = select(AuthUser).where(AuthUser.email == email).with_for_update()
                result = await self.session.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # Update existing user atomically
                    existing_user.full_name = user_info.get("name", existing_user.full_name)
                    existing_user.auth_provider = provider
                    existing_user.provider_user_id = provider_user_id
                    existing_user.provider_data = user_info
                    existing_user.last_login_at = datetime.now(timezone.utc)
                    existing_user.updated_at = datetime.now(timezone.utc)
                    existing_user.is_active = True
                    existing_user.is_verified = True
                    
                    await self.session.flush()
                    await transaction.commit()
                    return existing_user
                
                # Create new user atomically
                new_user = AuthUser(
                    email=email,
                    full_name=user_info.get("name", ""),
                    auth_provider=provider,
                    provider_user_id=provider_user_id,
                    provider_data=user_info,
                    is_active=True,
                    is_verified=True,  # OAuth users are pre-verified
                    last_login_at=datetime.now(timezone.utc)
                )
                
                self.session.add(new_user)
                await self.session.flush()
                await transaction.commit()
                return new_user
                
            except IntegrityError as e:
                # Handle race condition: user was created by another request
                logger.info(f"Race condition detected on attempt {attempt + 1}, retrying: {e}")
                if transaction:
                    await transaction.rollback()
                
                # Wait before retry with exponential backoff
                import asyncio
                await asyncio.sleep(0.1 * (2 ** attempt))
                continue
                
            except Exception as e:
                # Handle any other errors
                logger.error(f"OAuth user creation failed on attempt {attempt + 1}: {e}")
                if transaction:
                    await transaction.rollback()
                
                if attempt == max_retries - 1:
                    raise
                
                # Wait before retry
                import asyncio
                await asyncio.sleep(0.1 * (2 ** attempt))
                continue
                
        # If we get here, all retries failed
        raise RuntimeError(f"Failed to create OAuth user for {email} after {max_retries} attempts")
    
    async def create_local_user(self, email: str, 
                               password_hash: str, 
                               full_name: Optional[str] = None) -> AuthUser:
        """Create local user with password"""
        # Check if user exists
        existing_user = await self.get_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        new_user = AuthUser(
            email=email,
            full_name=full_name or "",
            hashed_password=password_hash,
            auth_provider="local",
            is_active=True,
            is_verified=False  # Local users need email verification
        )
        
        self.session.add(new_user)
        await self.session.flush()
        return new_user
    
    async def update_login_time(self, user_id: str):
        """Update user's last login time"""
        await self.session.execute(
            update(AuthUser)
            .where(AuthUser.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.session.flush()
    
    async def increment_failed_attempts(self, email: str) -> int:
        """Increment failed login attempts"""
        user = await self.get_by_email(email)
        if user:
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                user.is_active = False
            
            await self.session.flush()
            return user.failed_login_attempts
        return 0
    
    async def reset_failed_attempts(self, user_id: str):
        """Reset failed login attempts"""
        await self.session.execute(
            update(AuthUser)
            .where(AuthUser.id == user_id)
            .values(
                failed_login_attempts=0,
                locked_until=None
            )
        )
        await self.session.flush()
    
    async def check_account_locked(self, email: str) -> bool:
        """Check if account is locked"""
        user = await self.get_by_email(email)
        if not user:
            return False
        
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            return True
        
        # Unlock if time has passed
        if user.locked_until and user.locked_until <= datetime.now(timezone.utc):
            user.locked_until = None
            user.is_active = True
            user.failed_login_attempts = 0
            await self.session.flush()
        
        return False

class AuthSessionRepository:
    """Repository for session operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_session(self, user_id: str, 
                           refresh_token: str,
                           client_info: Dict) -> AuthSession:
        """Create new auth session"""
        # Hash refresh token for storage
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        new_session = AuthSession(
            user_id=user_id,
            refresh_token_hash=token_hash,
            ip_address=client_info.get("ip"),
            user_agent=client_info.get("user_agent"),
            device_id=client_info.get("device_id"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        self.session.add(new_session)
        await self.session.flush()
        return new_session
    
    async def get_active_session(self, session_id: str) -> Optional[AuthSession]:
        """Get active session by ID"""
        result = await self.session.execute(
            select(AuthSession).where(
                and_(
                    AuthSession.id == session_id,
                    AuthSession.is_active == True,
                    AuthSession.expires_at > datetime.now(timezone.utc)
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def revoke_session(self, session_id: str):
        """Revoke a session"""
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id)
            .values(
                is_active=False,
                revoked_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()
    
    async def revoke_user_sessions(self, user_id: str):
        """Revoke all sessions for a user"""
        await self.session.execute(
            update(AuthSession)
            .where(
                and_(
                    AuthSession.user_id == user_id,
                    AuthSession.is_active == True
                )
            )
            .values(
                is_active=False,
                revoked_at=datetime.now(timezone.utc)
            )
        )
        await self.session.flush()
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        await self.session.execute(
            update(AuthSession)
            .where(
                and_(
                    AuthSession.expires_at <= datetime.now(timezone.utc),
                    AuthSession.is_active == True
                )
            )
            .values(is_active=False)
        )
        await self.session.flush()

class AuthAuditRepository:
    """Repository for audit log operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_event(self, event_type: str, 
                       user_id: Optional[str] = None,
                       success: bool = True,
                       error_message: Optional[str] = None,
                       metadata: Optional[Dict] = None,
                       client_info: Optional[Dict] = None):
        """Log authentication event"""
        audit_log = AuthAuditLog(
            event_type=event_type,
            user_id=user_id,
            success=success,
            error_message=error_message,
            event_metadata=metadata or {},
            ip_address=client_info.get("ip") if client_info else None,
            user_agent=client_info.get("user_agent") if client_info else None
        )
        
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log
    
    async def get_user_events(self, user_id: str, 
                             limit: int = 100) -> List[AuthAuditLog]:
        """Get audit events for a user"""
        result = await self.session.execute(
            select(AuthAuditLog)
            .where(AuthAuditLog.user_id == user_id)
            .order_by(AuthAuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class AuthRepository:
    """Composite repository providing access to all auth repositories"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.user_repo = None
        self.session_repo = None
        self.audit_repo = None
        
        if session:
            self.user_repo = AuthUserRepository(session)
            self.session_repo = AuthSessionRepository(session)
            self.audit_repo = AuthAuditRepository(session)
    
    def _ensure_repositories(self):
        """Ensure repositories are initialized"""
        if not self.session:
            raise RuntimeError("Database session not available")
        if not self.user_repo:
            self.user_repo = AuthUserRepository(self.session)
            self.session_repo = AuthSessionRepository(self.session)
            self.audit_repo = AuthAuditRepository(self.session)
    
    # User repository methods
    async def get_user_by_email(self, email: str) -> Optional[AuthUser]:
        """Get user by email"""
        self._ensure_repositories()
        return await self.user_repo.get_by_email(email)
    
    async def get_user_by_id(self, user_id: str) -> Optional[AuthUser]:
        """Get user by ID"""
        self._ensure_repositories()
        return await self.user_repo.get_by_id(user_id)
    
    async def create_oauth_user(self, user_info: Dict) -> AuthUser:
        """Create or update OAuth user"""
        self._ensure_repositories()
        return await self.user_repo.create_oauth_user(user_info)
    
    async def create_local_user(self, email: str, password_hash: str, full_name: Optional[str] = None) -> AuthUser:
        """Create local user with password"""
        self._ensure_repositories()
        return await self.user_repo.create_local_user(email, password_hash, full_name)
    
    async def update_login_time(self, user_id: str):
        """Update user's last login time"""
        self._ensure_repositories()
        return await self.user_repo.update_login_time(user_id)
    
    async def increment_failed_attempts(self, email: str) -> int:
        """Increment failed login attempts"""
        self._ensure_repositories()
        return await self.user_repo.increment_failed_attempts(email)
    
    async def reset_failed_attempts(self, user_id: str):
        """Reset failed login attempts"""
        self._ensure_repositories()
        return await self.user_repo.reset_failed_attempts(user_id)
    
    async def check_account_locked(self, email: str) -> bool:
        """Check if account is locked"""
        self._ensure_repositories()
        return await self.user_repo.check_account_locked(email)
    
    # Session repository methods
    async def create_session(self, user_id: str, refresh_token: str, client_info: Dict) -> AuthSession:
        """Create new auth session"""
        self._ensure_repositories()
        return await self.session_repo.create_session(user_id, refresh_token, client_info)
    
    async def get_active_session(self, session_id: str) -> Optional[AuthSession]:
        """Get active session by ID"""
        self._ensure_repositories()
        return await self.session_repo.get_active_session(session_id)
    
    async def revoke_session(self, session_id: str):
        """Revoke a session"""
        self._ensure_repositories()
        return await self.session_repo.revoke_session(session_id)
    
    async def revoke_user_sessions(self, user_id: str):
        """Revoke all sessions for a user"""
        self._ensure_repositories()
        return await self.session_repo.revoke_user_sessions(user_id)
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        self._ensure_repositories()
        return await self.session_repo.cleanup_expired_sessions()
    
    # Audit repository methods
    async def log_event(self, event_type: str, user_id: Optional[str] = None, success: bool = True, 
                       error_message: Optional[str] = None, metadata: Optional[Dict] = None,
                       client_info: Optional[Dict] = None):
        """Log authentication event"""
        self._ensure_repositories()
        return await self.audit_repo.log_event(event_type, user_id, success, error_message, metadata, client_info)
    
    async def get_user_events(self, user_id: str, limit: int = 100) -> List[AuthAuditLog]:
        """Get audit events for a user"""
        self._ensure_repositories()
        return await self.audit_repo.get_user_events(user_id, limit)