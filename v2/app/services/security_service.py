# /v2/services/security_service.py
import os
import json
from datetime import datetime, timedelta
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from .. import models
from ..config import settings

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- JWT Token Creation ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- Credentials Encryption and Management ---
class SecurityService:
    def __init__(self):
        key = settings.FERNET_KEY.encode()
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> bytes:
        return self.fernet.encrypt(value.encode())

    def decrypt(self, encrypted_value: bytes) -> str:
        return self.fernet.decrypt(encrypted_value).decode()

    def save_user_credentials(self, user_id: int, credentials: models.ClickHouseCredentials, db_session: Session):
        creds_dict = credentials.model_dump()
        for key, value in creds_dict.items():
            encrypted_value = self.encrypt(str(value)) # Ensure value is string
            
            # Check if a secret with this key already exists for the user
            statement = select(models.Secret).where(models.Secret.user_id == user_id, models.Secret.key == key)
            db_secret = db_session.exec(statement).first()

            if db_secret:
                # Update existing secret
                db_secret.encrypted_value = encrypted_value
            else:
                # Create new secret
                db_secret = models.Secret(user_id=user_id, key=key, encrypted_value=encrypted_value)
            
            db_session.add(db_secret)
        
        db_session.commit()

    def get_user_credentials(self, user_id: int, db_session: Session) -> Optional[models.ClickHouseCredentials]:
        statement = select(models.Secret).where(models.Secret.user_id == user_id)
        secrets = db_session.exec(statement).all()
        if not secrets:
            return None
            
        decrypted_creds = {}
        for secret in secrets:
            decrypted_creds[secret.key] = self.decrypt(secret.encrypted_value)
        
        # Validate that all necessary keys are present before creating the model
        required_keys = models.ClickHouseCredentials.model_fields.keys()
        if not all(key in decrypted_creds for key in required_keys):
            return None
            
        return models.ClickHouseCredentials(**decrypted_creds)

    def get_netra_credentials(self) -> Optional[models.ClickHouseCredentials]:
        """Retrieves Netra's internal credentials from environment variables."""
        try:
            return models.ClickHouseCredentials(
                host=os.environ["NETRA_CLICKHOUSE_HOST"],
                port=int(os.environ["NETRA_CLICKHOUSE_PORT"]),
                user=os.environ["NETRA_CLICKHOUSE_USER"],
                password=os.environ["NETRA_CLICKHOUSE_PASSWORD"],
                database=os.environ["NETRA_CLICKHOUSE_DATABASE"],
            )
        except (KeyError, ValueError) as e:
            print(f"Error loading Netra credentials from environment: {e}")
            return None

security_service = SecurityService()
