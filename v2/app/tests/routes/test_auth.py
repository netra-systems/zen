from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.schemas import User
from app.dependencies import get_security_service
import uuid

@pytest.fixture
def client():
    return TestClient(app)