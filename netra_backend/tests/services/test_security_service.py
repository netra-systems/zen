# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet
from schemas import AppConfig

# Add project root to path
from netra_backend.app.services.security_service import KeyManager, SecurityService

# Add project root to path

@pytest.fixture
def security_service():
    mock_settings = AppConfig(jwt_secret_key="a_super_secret_jwt_key_for_development_that_is_long_enough", fernet_key=Fernet.generate_key())
    key_manager = KeyManager.load_from_settings(mock_settings)
    return SecurityService(key_manager)

def test_encrypt_and_decrypt(security_service: SecurityService):
    original_string = "test_string"
    encrypted = security_service.encrypt(original_string)
    decrypted = security_service.decrypt(encrypted)
    assert decrypted == original_string


from schemas import TokenPayload


def test_create_and_validate_access_token(security_service: SecurityService):
    """
    Tests that an access token can be created and then successfully validated.
    """
    email = "test@example.com"
    token = security_service.create_access_token(data=TokenPayload(sub=email))
    assert token != None

    decoded_email = security_service.get_user_email_from_token(token)
    assert decoded_email == email


def test_invalid_token(security_service: SecurityService):
    """
    Tests that an invalid token returns None.
    """
    decoded_email = security_service.get_user_email_from_token("invalid_token")
    assert decoded_email == None
