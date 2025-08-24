
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from netra_backend.app.schemas import AppConfig

from netra_backend.app.services.key_manager import KeyManager

# Mock AppConfig for testing
class MockAppConfig(AppConfig):
    jwt_secret_key: str = "a_super_secret_jwt_key_for_development_that_is_long_enough"
    fernet_key: str = "a_valid_fernet_key_that_is_long_enough_for_testing_purposes"

    class Config:
        # Pydantic v2 requires this for from_attributes to work with mock objects
        from_attributes = True

def test_load_from_settings_success():
    # Arrange
    settings = MockAppConfig()

    # Act
    key_manager = KeyManager.load_from_settings(settings)

    # Assert
    assert key_manager.jwt_secret_key == settings.jwt_secret_key
    assert key_manager.fernet_key == settings.fernet_key.encode()

def test_load_from_settings_jwt_key_too_short():
    # Arrange
    class InvalidMockConfig(MockAppConfig):
        jwt_secret_key: str = "short_key"

    settings = InvalidMockConfig()

    # Act & Assert
    with pytest.raises(ValueError, match="JWT secret key is too short"):
        KeyManager.load_from_settings(settings)
