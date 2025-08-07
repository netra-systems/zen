import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import User
from app.services.key_manager import KeyManager
from app.config import settings
from cryptography.fernet import Fernet
import os

@pytest.fixture(scope="module")
def mock_db_session_module():
    return AsyncMock()

@pytest.fixture(scope="module")
def client(mock_db_session_module):
    mock_key_manager = MagicMock()
    mock_key_manager.fernet_key = Fernet.generate_key()
    mock_key_manager.jwt_secret_key = os.environ['SECRET_KEY']

    with patch('app.main.KeyManager.load_from_settings', return_value=mock_key_manager), \
         patch('app.main.LLMManager', autospec=True), \
         patch('app.logging_config.central_logger.clickhouse_db', autospec=True), \
         patch('app.main.OverallSupervisor', autospec=True), \
         patch('app.main.StreamingAgentSupervisor', autospec=True), \
         patch('app.main.AgentService', autospec=True):
        with TestClient(app) as c:
            yield c