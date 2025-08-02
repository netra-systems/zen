# /v2/app/services/security_service.py
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from cryptography.fernet import Fernet
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlmodel import Session, select

from ..db import models_postgres
from ..db import models_clickhouse
from .key_manager import KeyManager

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.key_manager.jwt_secret_key, algorithm="HS256")
        return encoded_jwt

    def encrypt(self, value: str) -> bytes:
        return self.fernet.encrypt(value.encode('utf-8'))

    def decrypt(self, encrypted_value: bytes) -> str:
        return self.fernet.decrypt(encrypted_value).decode('utf-8')

    def save_user_credentials(self, user_id: int, credentials: models_clickhouse.ClickHouseCredentials, db_session: Session):
        existing_secrets_query = select(models_postgres.Secret).where(models_postgres.Secret.user_id == user_id)
        existing_secrets_list = db_session.exec(existing_secrets_query).all()
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
        
        db_session.commit()

    def get_user_credentials(self, user_id: int, db_session: Session) -> Optional[models_clickhouse.ClickHouseCredentials]:
        secrets = db_session.exec(select(models_postgres.Secret).where(models_postgres.Secret.user_id == user_id)).all()
        if not secrets:
            return None
            
        decrypted_creds = {}
        try:
            for secret in secrets:
                decrypted_creds[secret.key] = self.decrypt(secret.encrypted_value)
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for user_id {user_id}: {e}")
            return None
        
        required_keys = models_postgres.ClickHouseCredentials.model_fields.keys()
        if not all(key in decrypted_creds for key in required_keys):
            logger.warning(f"Incomplete credentials found for user_id {user_id}. Missing keys: {required_keys - decrypted_creds.keys()}")
            # Still return the model, it will raise a validation error on use, which is informative.
        
        return models_postgres.ClickHouseCredentials(**decrypted_creds)

security_service = SecurityService(key_manager=KeyManager())
