import pytest
from unittest.mock import MagicMock
from app.services.security_service import SecurityService
from app.services.key_manager import KeyManager

@pytest.fixture
def key_manager():
    """
    Provides a mock KeyManager for testing.
    """
    km = MagicMock(spec=KeyManager)
    km.jwt_secret_key = "test_secret_key"
    km.fernet_key = KeyManager.generate_key()
    return km

@pytest.fixture
def security_service(key_manager: KeyManager):
    """
    Provides a SecurityService instance with a mock KeyManager.
    """
    return SecurityService(key_manager)

def test_create_and_validate_access_token(security_service: SecurityService):
    """
    Tests that an access token can be created and then successfully validated.
    """
    email = "test@example.com"
    token = security_service.create_access_token(data={"sub": email})
    assert token is not None
    
    decoded_email = security_service.get_user_email_from_token(token)
    assert decoded_email == email

def test_invalid_token(security_service: SecurityService):
    """
    Tests that an invalid token returns None.
    """
    decoded_email = security_service.get_user_email_from_token("invalid_token")
    assert decoded_email is None

def test_encrypt_and_decrypt(security_service: SecurityService):
    """
    Tests that a value can be encrypted and then successfully decrypted.
    """
    original_value = "my_secret_password"
    encrypted_value = security_service.encrypt(original_value)
    assert encrypted_value is not None
    
    decrypted_value = security_service.decrypt(encrypted_value)
    assert decrypted_value == original_value