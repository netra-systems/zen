import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, Request
from app.auth.active_user import ActiveUser
from app.db.models_postgres import User
from app.config import settings
import uuid
from datetime import datetime
from app import schemas

@pytest.mark.asyncio
async def test_active_user_success(mocker):
    # Arrange
    settings.environment = "production"
    email = "test@example.com"
    session = AsyncMock()
    security_service = AsyncMock()
    security_service.get_user = AsyncMock(return_value=User(email=email))
    db_session_factory = mocker.MagicMock()
    db_session_factory.return_value.__aenter__.return_value = session
    security_service.get_user_email_from_token.return_value = email
    request = mocker.Mock()
    request.headers = {"Authorization": "Bearer test_token"}

    active_user = ActiveUser(db_session_factory, security_service)

    # Act
    user = await active_user(request)
    assert schemas.User.model_validate(user)
