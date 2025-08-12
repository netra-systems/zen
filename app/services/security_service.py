# app/services/security_service.py

from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from datetime import datetime, timedelta

from app.db import models_postgres
from app import schemas
from app.services.key_manager import KeyManager
from app.config import settings
from app.logging_config import central_logger as logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityService:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: schemas.TokenPayload, expires_delta: Optional[timedelta] = None):
        to_encode = data.model_dump()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.key_manager.jwt_secret_key, algorithm="HS256")
        return encoded_jwt

    def get_user_email_from_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, self.key_manager.jwt_secret_key, algorithms=["HS256"])
            email: str = payload.get("sub")
            if email is None:
                return None
            return email
        except JWTError:
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
            payload = jwt.decode(token, self.key_manager.jwt_secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.info(f"Token expired: {token}")
            return None
        except JWTError as e:
            logger.error(f"JWT decode error: {e}, token: {token}")
            return None

    async def get_user_by_id(self, db_session: AsyncSession, user_id: str) -> Optional[models_postgres.User]:
        result = await db_session.execute(select(models_postgres.User).filter(models_postgres.User.id == user_id))
        return result.scalars().first()

    async def get_or_create_user_from_oauth(self, db_session: AsyncSession, user_info: dict) -> schemas.User:
        user = await self.get_user(db_session, user_info["email"])
        if user:
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