# app/services/security_service.py

from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from datetime import datetime, timedelta, UTC
from cryptography.fernet import Fernet
import secrets

from app.db import models_postgres
from app import schemas
from app.services.key_manager import KeyManager
from app.config import settings
from app.logging_config import central_logger as logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityService:
    def __init__(self, key_manager: Optional[KeyManager] = None):
        if key_manager is None:
            # Create default key manager from settings
            from app.services.key_manager import KeyManager
            self.key_manager = KeyManager.load_from_settings(settings)
        else:
            self.key_manager = key_manager
        
        if hasattr(self.key_manager, 'fernet_key') and self.key_manager.fernet_key:
            self.fernet = Fernet(self.key_manager.fernet_key)
        else:
            self.fernet = None

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

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: schemas.TokenPayload, expires_delta: Optional[timedelta] = None):
        to_encode = data.model_dump()
        current_time = datetime.now(UTC)
        
        if expires_delta:
            expire = current_time + expires_delta
        else:
            expire = current_time + timedelta(minutes=settings.access_token_expire_minutes)
        
        # SECURITY FIX: Add proper JWT claims for enhanced security
        to_encode.update({
            "exp": expire,
            "iat": current_time,  # Issued at timestamp
            "nbf": current_time,  # Not before timestamp
            "jti": secrets.token_hex(16),  # JWT ID for token blacklisting support
            "iss": "netra-auth-service",  # Issuer claim
            "aud": "netra-api"  # Audience claim
        })
        
        encoded_jwt = jwt.encode(to_encode, self.key_manager.jwt_secret_key, algorithm="HS256")
        return encoded_jwt

    def get_user_email_from_token(self, token: str) -> Optional[str]:
        try:
            # SECURITY FIX: Use the same enhanced JWT validation logic
            payload = self.decode_access_token(token)
            if payload is None:
                return None
            
            email: str = payload.get("sub")
            if email is None or not isinstance(email, str):
                logger.error("Invalid or missing email in token subject claim")
                return None
                
            # Additional email validation
            if "@" not in email or len(email) < 3:
                logger.error(f"Invalid email format in token: {email}")
                return None
                
            return email
        except Exception as e:
            logger.error(f"Error extracting email from token: {e}")
            return None

    async def get_user(self, db_session: AsyncSession, email: str) -> Optional[models_postgres.User]:
        result = await db_session.execute(select(models_postgres.User).where(models_postgres.User.email == email))
        return result.scalars().first()

    async def create_user(self, db_session: AsyncSession, user_create: schemas.UserCreate) -> schemas.User:
        hashed_password = self.get_password_hash(user_create.password)
        db_user = models_postgres.User(
            **user_create.model_dump(exclude={"password"}),
            hashed_password=hashed_password
        )
        db_session.add(db_user)
        await db_session.commit()
        await db_session.refresh(db_user)
        return schemas.User.model_validate(db_user)

    async def authenticate_user(self, db_session: AsyncSession, email: str, password: str) -> Optional[models_postgres.User]:
        user = await self.get_user(db_session, email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def decode_access_token(self, token: str) -> Optional[dict]:
        try:
            # SECURITY FIX: Enhanced JWT validation with strict checks
            payload = jwt.decode(
                token, 
                self.key_manager.jwt_secret_key, 
                algorithms=["HS256"],
                audience="netra-api",  # Verify audience claim
                issuer="netra-auth-service",  # Verify issuer claim
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_signature": True,
                    "require_exp": True,
                    "require_iat": True,
                    "require_nbf": True,
                    "require_aud": True,
                    "require_iss": True
                }
            )
            
            # Additional security checks
            exp_timestamp = payload.get("exp")
            iat_timestamp = payload.get("iat")
            current_timestamp = datetime.now(UTC).timestamp()
            
            # Verify token not too old (max 24 hours)
            if iat_timestamp and (current_timestamp - iat_timestamp) > 86400:
                logger.warning(f"Token too old, issued: {iat_timestamp}, current: {current_timestamp}")
                return None
                
            # Strict expiration check with tolerance
            if exp_timestamp and current_timestamp > (exp_timestamp + 5):  # 5 second tolerance
                logger.info(f"Token expired with strict check: exp={exp_timestamp}, current={current_timestamp}")
                return None
            
            # Validate required claims
            required_claims = ["sub", "exp", "iat"]
            for claim in required_claims:
                if claim not in payload:
                    logger.error(f"Missing required claim: {claim}")
                    return None
            
            return payload
        except jwt.ExpiredSignatureError:
            logger.info("Token expired during JWT validation")
            return None
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None

    async def get_user_by_id(self, db_session: AsyncSession, user_id: str) -> Optional[models_postgres.User]:
        result = await db_session.execute(select(models_postgres.User).filter(models_postgres.User.id == user_id))
        return result.scalars().first()

    async def get_or_create_user_from_oauth(self, db_session: AsyncSession, user_info: dict) -> schemas.User:
        user = await self.get_user(db_session, user_info["email"])
        if user:
            # Update existing user's profile information from OAuth data
            user.full_name = user_info.get("name", user.full_name)
            user.picture = user_info.get("picture", user.picture)
            await db_session.commit()
            await db_session.refresh(user)
            return user

        # Create a new user if one doesn't exist
        db_user = models_postgres.User(
            email=user_info["email"],
            full_name=user_info.get("name"),
            picture=user_info.get("picture"),
        )
        db_session.add(db_user)
        await db_session.commit()
        await db_session.refresh(db_user)
        return schemas.User.model_validate(db_user)