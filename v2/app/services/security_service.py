# /v2/app/services/security_service.py
import logging
from typing import Optional
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from datetime import datetime, timedelta

from ..db import models_postgres
from .. import schemas
from .key_manager import KeyManager

class SecurityService:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.fernet = Fernet(self.key_manager.fernet_key)

    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def get_password_hash(self, password: str) -> str:
        return self.encrypt(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            decrypted_password = self.decrypt(hashed_password)
            return plain_password == decrypted_password
        except Exception:
            return False

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
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

    async def get_user(self, db_session: AsyncSession, email: str) -> Optional[schemas.UserInDB]:
        result = await db_session.execute(select(models_postgres.User).where(models_postgres.User.email == email))
        user_in_db = result.scalars().first()
        if user_in_db:
            return schemas.UserInDB.model_validate(user_in_db)
        return None

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
