# /v2.1/services/security_service.py
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from .. import models
from ..config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- JWT Token Creation ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

# --- Credentials Encryption and Management ---
class SecurityService:
    def __init__(self):
        try:
            key = settings.FERNET_KEY.encode()
            self.fernet = Fernet(key)
        except Exception as e:
            logger.critical(f"FATAL: Could not initialize Fernet. FERNET_KEY may be invalid. Error: {e}")
            raise

    def encrypt(self, value: str) -> bytes:
        return self.fernet.encrypt(value.encode('utf-8'))

    def decrypt(self, encrypted_value: bytes) -> str:
        return self.fernet.decrypt(encrypted_value).decode('utf-8')

    def save_user_credentials(self, user_id: int, credentials: models.ClickHouseCredentials, db_session: Session):
        """
        Efficiently saves user credentials by fetching all existing secrets at once,
        then updating or creating them in a single transaction.
        """
        # Fetch all existing secrets for the user in one query
        existing_secrets_query = select(models.Secret).where(models.Secret.user_id == user_id)
        existing_secrets_list = db_session.exec(existing_secrets_query).all()
        existing_secrets_map = {secret.key: secret for secret in existing_secrets_list}

        creds_dict = credentials.model_dump()
        for key, value in creds_dict.items():
            encrypted_value = self.encrypt(str(value))

            if key in existing_secrets_map:
                # Update existing secret if the value has changed
                if existing_secrets_map[key].encrypted_value != encrypted_value:
                    existing_secrets_map[key].encrypted_value = encrypted_value
                    db_session.add(existing_secrets_map[key])
            else:
                # Create a new secret
                new_secret = models.Secret(user_id=user_id, key=key, encrypted_value=encrypted_value)
                db_session.add(new_secret)
        
        db_session.commit()


    def get_user_credentials(self, user_id: int, db_session: Session) -> Optional[models.ClickHouseCredentials]:
        """
        Retrieves and decrypts all secrets for a user to reconstruct the credentials model.
        """
        secrets = db_session.exec(select(models.Secret).where(models.Secret.user_id == user_id)).all()
        if not secrets:
            return None
            
        decrypted_creds = {}
        try:
            for secret in secrets:
                decrypted_creds[secret.key] = self.decrypt(secret.encrypted_value)
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for user_id {user_id}: {e}")
            return None

        # Validate that all necessary keys are present before creating the model
        required_keys = models.ClickHouseCredentials.model_fields.keys()
        if not all(key in decrypted_creds for key in required_keys):
            logger.warning(f"Incomplete credentials found for user_id {user_id}")
            return None
            
        return models.ClickHouseCredentials(**decrypted_creds)

security_service = SecurityService()
