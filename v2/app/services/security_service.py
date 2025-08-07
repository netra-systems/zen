# /v2/app/services/security_service.py
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import models_postgres
from ..db import models_clickhouse
from .key_manager import KeyManager

class SecurityService:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.fernet = Fernet(self.key_manager.fernet_key)

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