# /v2/app/services/key_manager.py
import os
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, ValidationError

class KeyManager(BaseModel):
    jwt_secret_key: str = Field(..., min_length=32)
    fernet_key: bytes = Field(...)

    @classmethod
    def load_from_env(cls, app_env: str = "development"):
        if app_env == "production":
            # In production, fetch keys from a secure vault
            # This is a placeholder for actual vault integration
            jwt_secret_key = os.environ.get("JWT_SECRET_KEY")
            fernet_key = os.environ.get("FERNET_KEY")
            if not jwt_secret_key or not fernet_key:
                raise ValueError("JWT_SECRET_KEY and FERNET_KEY must be set in production")
        else:
            # In development, use default keys for convenience
            jwt_secret_key = os.environ.get("JWT_SECRET_KEY", "default_jwt_secret_key_for_development_env_only")
            fernet_key = os.environ.get("FERNET_KEY", Fernet.generate_key().decode())

        try:
            return cls(jwt_secret_key=jwt_secret_key, fernet_key=fernet_key.encode())
        except ValidationError as e:
            raise ValueError(f"Key validation failed: {e}") from e
