# /v2/app/services/key_manager.py
import os
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, ValidationError

from ..config import AppConfig

class KeyManager(BaseModel):
    jwt_secret_key: str = Field(..., min_length=32)
    fernet_key: bytes = Field(...)

    @classmethod
    def load_from_settings(cls, settings: AppConfig):
        jwt_secret_key = settings.jwt_secret_key
        fernet_key = settings.fernet_key

        if settings.app_env == "development" and jwt_secret_key == "jwt_secret_key":
            jwt_secret_key = "a_super_secret_jwt_key_for_development_that_is_long_enough"

        try:
            return cls(jwt_secret_key=jwt_secret_key, fernet_key=fernet_key.encode())
        except ValidationError as e:
            if "jwt_secret_key" in str(e):
                raise ValueError(
                    "JWT secret key is too short. It must be at least 32 characters long. "
                    "Update it in your .env file or configuration."
                ) from e
            raise ValueError(f"Key validation failed: {e}") from e
