# app/services/security_service.py

from datetime import datetime, timedelta
from typing import Dict, Optional

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from netra_backend.app import schemas
from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.db import models_postgres
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.services.key_manager import KeyManager


class SecurityService:
    def __init__(self, key_manager: Optional[KeyManager] = None):
        self.key_manager = self._initialize_key_manager(key_manager)
        self.fernet = self._initialize_fernet_encryption()

    def _initialize_key_manager(self, key_manager: Optional[KeyManager]) -> KeyManager:
        """Initialize key manager from provided instance or settings."""
        if key_manager is None:
            from netra_backend.app.services.key_manager import KeyManager
            return KeyManager.load_from_settings(settings)
        return key_manager

    def _initialize_fernet_encryption(self) -> Optional[Fernet]:
        """Initialize Fernet encryption if key is available."""
        if hasattr(self.key_manager, 'fernet_key') and self.key_manager.fernet_key:
            return Fernet(self.key_manager.fernet_key)
        return None

    def encrypt(self, data: str) -> str:
        """Encrypt string data using Fernet encryption."""
        if not self.fernet:
            raise ValueError("Fernet key not configured")
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data using Fernet encryption."""
        if not self.fernet:
            raise ValueError("Fernet key not configured")
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    async def get_password_hash(self, password: str) -> str:
        """Hash a password through auth service."""
        result = await auth_client.hash_password(password)
        if not result:
            raise ValueError("Failed to hash password")
        return result.get("hashed_password")

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password through auth service."""
        result = await auth_client.verify_password(plain_password, hashed_password)
        return result.get("valid", False) if result else False

    async def create_access_token(self, data: schemas.TokenPayload, expires_delta: Optional[timedelta] = None) -> str:
        """Create access token through auth service."""
        token_data = {
            "user_id": data.sub,
            "expires_in": int(expires_delta.total_seconds()) if expires_delta else settings.access_token_expire_minutes * 60
        }
        result = await auth_client.create_token(token_data)
        if not result or "access_token" not in result:
            raise ValueError("Failed to create access token")
        return result["access_token"]


    async def get_user_email_from_token(self, token: str) -> Optional[str]:
        """Get user email from token through auth service."""
        try:
            result = await auth_client.validate_token_jwt(token)
            if result and result.get("valid"):
                return result.get("email")
            return None
        except Exception as e:
            logger.error(f"Error extracting email from token: {e}")
            return None


    async def get_user(self, db_session: AsyncSession, email: str) -> Optional[models_postgres.User]:
        result = await db_session.execute(select(models_postgres.User).where(models_postgres.User.email == email))
        return result.scalars().first()

    async def create_user(self, db_session: AsyncSession, user_create: schemas.UserCreate) -> schemas.User:
        hashed_password = await self.get_password_hash(user_create.password)
        db_user = self._build_user_model(user_create, hashed_password)
        return await self._persist_new_user(db_session, db_user)

    def _build_user_model(self, user_create: schemas.UserCreate, hashed_password: str) -> models_postgres.User:
        """Build user model with hashed password."""
        return models_postgres.User(
            **user_create.model_dump(exclude={"password"}),
            hashed_password=hashed_password
        )

    async def _persist_new_user(self, db_session: AsyncSession, db_user: models_postgres.User) -> schemas.User:
        """Persist new user to database and return schema."""
        db_session.add(db_user)
        await db_session.commit()
        await db_session.refresh(db_user)
        # Use core_models.User explicitly to avoid ExtendedUser alias conflict
        from netra_backend.app.schemas.core_models import User as CoreUser
        return CoreUser.model_validate(db_user)

    async def authenticate_user(self, db_session: AsyncSession, email: str, password: str) -> Optional[models_postgres.User]:
        user = await self.get_user(db_session, email)
        if not user:
            return None
        if not await self.verify_password(password, user.hashed_password):
            return None
        return user

    async def decode_access_token(self, token: str) -> Optional[Dict]:
        """Validate and decode access token through auth service."""
        result = await auth_client.validate_token_jwt(token)
        if result and result.get("valid"):
            return {
                "sub": result.get("user_id"),
                "email": result.get("email"),
                "permissions": result.get("permissions", [])
            }
        return None

    async def get_user_by_id(self, db_session: AsyncSession, user_id: str) -> Optional[models_postgres.User]:
        result = await db_session.execute(select(models_postgres.User).filter(models_postgres.User.id == user_id))
        return result.scalars().first()

    async def get_or_create_user_from_oauth(self, db_session: AsyncSession, user_info: dict) -> schemas.User:
        user = await self.get_user(db_session, user_info["email"])
        if user:
            return await self._update_existing_oauth_user(db_session, user, user_info)
        return await self._create_new_oauth_user(db_session, user_info)

    async def _update_existing_oauth_user(self, db_session: AsyncSession, user: models_postgres.User, user_info: dict) -> schemas.User:
        """Update existing user with OAuth profile data."""
        user.full_name = user_info.get("name", user.full_name)
        user.picture = user_info.get("picture", user.picture)
        await db_session.commit()
        await db_session.refresh(user)
        # Use core_models.User explicitly to avoid ExtendedUser alias conflict
        from netra_backend.app.schemas.core_models import User as CoreUser
        return CoreUser.model_validate(user)

    async def _create_new_oauth_user(self, db_session: AsyncSession, user_info: dict) -> schemas.User:
        """Create new user from OAuth data."""
        db_user = self._build_oauth_user_model(user_info)
        return await self._persist_new_user(db_session, db_user)

    def _build_oauth_user_model(self, user_info: dict) -> models_postgres.User:
        """Build user model from OAuth information."""
        return models_postgres.User(
            email=user_info["email"],
            full_name=user_info.get("name"),
            picture=user_info.get("picture")
        )