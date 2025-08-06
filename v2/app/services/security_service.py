# /v2/app/services/security_service.py
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer

from ..db import models_postgres
from ..db import models_clickhouse
from .key_manager import KeyManager

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

class SecurityService:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.fernet = Fernet(self.key_manager.fernet_key)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.key_manager.jwt_secret_key, algorithm="HS256")
        return encoded_jwt

    def get_user_email_from_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, self.key_manager.jwt_secret_key, algorithms=["HS256"])
            email: str = payload.get("sub")
            return email
        except JWTError:
            return None

    def encrypt(self, value: str) -> bytes:
        return self.fernet.encrypt(value.encode('utf-8'))

    def decrypt(self, encrypted_value: bytes) -> str:
        return self.fernet.decrypt(encrypted_value).decode('utf-8')

    async def get_user(self, db_session: AsyncSession, email: str) -> Optional[models_postgres.User]:
        result = await db_session.execute(select(models_postgres.User).where(models_postgres.User.email == email))
        return result.scalars().first()

    async def save_user_credentials(self, user_id: int, credentials: models_clickhouse.ClickHouseCredentials, db_session: AsyncSession):
        existing_secrets_query = select(models_postgres.Secret).where(models_postgres.Secret.user_id == user_id)
        existing_secrets_list = await db_session.exec(existing_secrets_query)
        existing_secrets_list = existing_secrets_list.all()
        existing_secrets_map = {secret.key: secret for secret in existing_secrets_list}

        creds_dict = credentials.model_dump()
        for key, value in creds_dict.items():
            if value is None:
                continue
            encrypted_value = self.encrypt(str(value))

            if key in existing_secrets_map:
                if existing_secrets_map[key].encrypted_value != encrypted_value:
                    existing_secrets_map[key].encrypted_value = encrypted_value
                    db_session.add(existing_secrets_map[key])
            else:
                new_secret = models_postgres.Secret(user_id=user_id, key=key, encrypted_value=encrypted_value)
                db_session.add(new_secret)
        
        await db_session.commit()

    async def get_user_credentials(self, user_id: int, db_session: AsyncSession) -> Optional[models_clickhouse.ClickHouseCredentials]:
        result = await db_session.execute(select(models_postgres.Secret).where(models_postgres.Secret.user_id == user_id))
        secrets = result.scalars().all()
        if not secrets:
            return None
            
        decrypted_creds = {}
        try:
            for secret in secrets:
                decrypted_creds[secret.key] = self.decrypt(secret.encrypted_value)
        except Exception as e:
            logging.error(f"Failed to decrypt credentials for user_id {user_id}: {e}")
            return None
        
        required_keys = models_clickhouse.ClickHouseCredentials.model_fields.keys()
        if not all(key in decrypted_creds for key in required_keys):
            logging.warning(f"Incomplete credentials found for user_id {user_id}. Missing keys: {required_keys - decrypted_creds.keys()}")
            # Still return the model, it will raise a validation error on use, which is informative.
        
        return models_clickhouse.ClickHouseCredentials(**decrypted_creds)

# Create a global instance of the security service
try:
    from ..config import settings
    key_manager = KeyManager.load_from_settings(settings)
    security_service = SecurityService(key_manager)
except (ImportError, ValueError) as e:
    logging.error(f"Failed to initialize SecurityService: {e}")
    security_service = None
