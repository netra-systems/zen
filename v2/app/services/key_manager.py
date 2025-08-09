from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, ValidationError

from app.schemas import AppConfig

class KeyManager(BaseModel):
    jwt_secret_key: str = Field(..., min_length=32)
    fernet_key: bytes = Field(...)

    @staticmethod
    def generate_key():
        return Fernet.generate_key()

    @classmethod
    def load_from_settings(cls, settings: AppConfig):
        jwt_secret_key = settings.jwt_secret_key
        fernet_key = settings.fernet_key

        fernet_key_bytes = fernet_key.encode() if isinstance(fernet_key, str) else fernet_key

        try:
            return cls(jwt_secret_key=jwt_secret_key, fernet_key=fernet_key_bytes)
        except ValidationError as e:
            if "jwt_secret_key" in str(e):
                raise ValueError(
                    "JWT secret key is too short. It must be at least 32 characters long. "
                    "Update it in your .env file or configuration."
                ) from e
            raise ValueError(f"Key validation failed: {e}") from e