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
        self.key_manager = self._initialize_key_manager(key_manager)
        self.fernet = self._initialize_fernet_encryption()

    def _initialize_key_manager(self, key_manager: Optional[KeyManager]) -> KeyManager:
        """Initialize key manager from provided instance or settings."""
        if key_manager is None:
            from app.services.key_manager import KeyManager
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

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: schemas.TokenPayload, expires_delta: Optional[timedelta] = None):
        to_encode = data.model_dump()
        current_time = datetime.now(UTC)
        expire = self._calculate_token_expiration(expires_delta, current_time)
        self._add_security_claims(to_encode, expire, current_time)
        return jwt.encode(to_encode, self.key_manager.jwt_secret_key, algorithm="HS256")

    def _calculate_token_expiration(self, expires_delta: Optional[timedelta], current_time: datetime) -> datetime:
        """Calculate token expiration time."""
        if expires_delta:
            return current_time + expires_delta
        return current_time + timedelta(minutes=settings.access_token_expire_minutes)

    def _add_security_claims(self, to_encode: dict, expire: datetime, current_time: datetime) -> None:
        """Add enhanced security claims to JWT payload."""
        to_encode.update({
            "exp": expire, "iat": current_time, "nbf": current_time,
            "jti": secrets.token_hex(16), "iss": "netra-auth-service", "aud": "netra-api"
        })

    def get_user_email_from_token(self, token: str) -> Optional[str]:
        try:
            payload = self.decode_access_token(token)
            return self._process_token_payload(payload)
        except Exception as e:
            logger.error(f"Error extracting email from token: {e}")
            return None

    def _process_token_payload(self, payload: Optional[dict]) -> Optional[str]:
        """Process token payload to extract email."""
        if payload is None:
            return None
        return self._extract_and_validate_email(payload)

    def _extract_and_validate_email(self, payload: dict) -> Optional[str]:
        """Extract and validate email from token payload."""
        email = payload.get("sub")
        if not self._is_valid_email_claim(email):
            return None
        if not self._is_valid_email_format(email):
            return None
        return email

    def _is_valid_email_claim(self, email: any) -> bool:
        """Validate email claim type and presence."""
        if email is None or not isinstance(email, str):
            logger.error("Invalid or missing email in token subject claim")
            return False
        return True

    def _is_valid_email_format(self, email: str) -> bool:
        """Validate email format requirements."""
        if "@" not in email or len(email) < 3:
            logger.error(f"Invalid email format in token: {email}")
            return False
        return True

    async def get_user(self, db_session: AsyncSession, email: str) -> Optional[models_postgres.User]:
        result = await db_session.execute(select(models_postgres.User).where(models_postgres.User.email == email))
        return result.scalars().first()

    async def create_user(self, db_session: AsyncSession, user_create: schemas.UserCreate) -> schemas.User:
        hashed_password = self.get_password_hash(user_create.password)
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
        return schemas.User.model_validate(db_user)

    async def authenticate_user(self, db_session: AsyncSession, email: str, password: str) -> Optional[models_postgres.User]:
        user = await self.get_user(db_session, email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def _decode_jwt_with_validation(self, token: str) -> Optional[dict]:
        """Decode JWT with enhanced security validation options."""
        return jwt.decode(
            token, self.key_manager.jwt_secret_key, algorithms=["HS256"],
            audience="netra-api", issuer="netra-auth-service",
            options=self._get_jwt_validation_options()
        )

    def _get_jwt_validation_options(self) -> dict:
        """Get strict JWT validation options for security."""
        return {
            "verify_exp": True, "verify_iat": True, "verify_nbf": True,
            "verify_aud": True, "verify_iss": True, "verify_signature": True,
            "require_exp": True, "require_iat": True, "require_nbf": True,
            "require_aud": True, "require_iss": True
        }

    def _validate_token_timestamps(self, payload: dict) -> bool:
        """Validate token timestamps for security compliance."""
        exp_timestamp = payload.get("exp")
        iat_timestamp = payload.get("iat")
        current_timestamp = datetime.now(UTC).timestamp()
        return self._verify_timestamps(iat_timestamp, exp_timestamp, current_timestamp)

    def _verify_timestamps(self, iat_timestamp: Optional[float], exp_timestamp: Optional[float], current_timestamp: float) -> bool:
        """Verify both issued and expiration timestamps."""
        if not self._check_token_age(iat_timestamp, current_timestamp):
            return False
        return self._check_expiration_tolerance(exp_timestamp, current_timestamp)

    def _check_token_age(self, iat_timestamp: Optional[float], current_timestamp: float) -> bool:
        """Check if token is not too old (max 24 hours)."""
        if iat_timestamp and (current_timestamp - iat_timestamp) > 86400:
            logger.warning(f"Token too old, issued: {iat_timestamp}, current: {current_timestamp}")
            return False
        return True

    def _check_expiration_tolerance(self, exp_timestamp: Optional[float], current_timestamp: float) -> bool:
        """Check token expiration with tolerance for clock skew."""
        if exp_timestamp and current_timestamp > (exp_timestamp + 5):
            logger.info(f"Token expired with strict check: exp={exp_timestamp}, current={current_timestamp}")
            return False
        return True

    def _validate_required_claims(self, payload: dict) -> bool:
        """Validate presence of required JWT claims."""
        required_claims = ["sub", "exp", "iat"]
        for claim in required_claims:
            if claim not in payload:
                logger.error(f"Missing required claim: {claim}")
                return False
        return True

    def _perform_token_validations(self, payload: dict) -> bool:
        """Perform comprehensive token validations."""
        if not self._validate_token_timestamps(payload):
            return False
        if not self._validate_required_claims(payload):
            return False
        return True

    def _handle_jwt_exceptions(self, e: Exception) -> None:
        """Handle JWT-specific exceptions with appropriate logging."""
        if isinstance(e, jwt.ExpiredSignatureError):
            logger.info("Token expired during JWT validation")
        else:
            logger.error(f"JWT decode error: {e}")

    def _safe_decode_and_validate(self, token: str) -> Optional[dict]:
        """Safely decode and validate token with exception handling."""
        try:
            payload = self._decode_jwt_with_validation(token)
            return payload if self._perform_token_validations(payload) else None
        except (jwt.ExpiredSignatureError, JWTError) as e:
            self._handle_jwt_exceptions(e)
            return None

    def decode_access_token(self, token: str) -> Optional[dict]:
        """Decode and validate access token with enhanced security checks."""
        return self._safe_decode_and_validate(token)

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
        return schemas.User.model_validate(user)

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