
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from app.services.security_service import SecurityService, verify_password, get_password_hash
from app.services.key_manager import KeyManager

@pytest.fixture
def key_manager():
    return KeyManager(
        jwt_secret_key="a_super_secret_jwt_key_for_development_that_is_long_enough",
        fernet_key=b'ZUbYw04IIPQ-WXwlW4i0DIxocMd-w1xgLJ4FtvIyhrI='
    )

@pytest.fixture
def security_service(key_manager):
    return SecurityService(key_manager)

def test_create_and_validate_access_token(security_service: SecurityService):
    # Arrange
    email = "test@example.com"
    token = security_service.create_access_token(data={"sub": email})

    # Act
    decoded_email = security_service.get_user_email_from_token(token)

    # Assert
    assert decoded_email == email

def test_token_expiry(security_service: SecurityService):
    # Arrange
    email = "test@example.com"
    token = security_service.create_access_token(data={"sub": email}, expires_delta=timedelta(seconds=-1))

    # Act
    decoded_email = security_service.get_user_email_from_token(token)

    # Assert
    assert decoded_email is None

def test_encrypt_decrypt(security_service: SecurityService):
    # Arrange
    original_string = "test_string"

    # Act
    encrypted_string = security_service.encrypt(original_string)
    decrypted_string = security_service.decrypt(encrypted_string)

    # Assert
    assert decrypted_string == original_string

def test_password_hashing():
    # Arrange
    password = "test_password"

    # Act
    hashed_password = get_password_hash(password)
    is_valid = verify_password(password, hashed_password)

    # Assert
    assert is_valid
    assert not verify_password("wrong_password", hashed_password)
