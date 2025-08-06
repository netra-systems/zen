import pytest
from fastapi import HTTPException, status
from jose import jwt

from app.auth.active_user import ActiveUser
from app.db.models_postgres import User


@pytest.mark.asyncio
async def test_active_user_success(mocker):
    # Arrange
    email = "test@example.com"
    db_session_factory = mocker.AsyncMock()
    db_session_factory.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = User(email=email)
    security_service = mocker.Mock()
    security_service.get_user_email_from_token.return_value = email
    request = mocker.Mock()
    request.headers = {"Authorization": "Bearer test_token"}

    active_user = ActiveUser(db_session_factory, security_service)

    # Act
    user = await active_user(request)

    # Assert
    assert user.email == email


@pytest.mark.asyncio
async def test_active_user_invalid_token(mocker):
    # Arrange
    db_session_factory = mocker.AsyncMock()
    security_service = mocker.Mock()
    security_service.get_user_email_from_token.return_value = None
    request = mocker.Mock()
    request.headers = {"Authorization": "Bearer invalid_token"}

    active_user = ActiveUser(db_session_factory, security_service)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await active_user(request)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_active_user_no_user(mocker):
    # Arrange
    email = "test@example.com"
    db_session_factory = mocker.AsyncMock()
    db_session_factory.return_value.__aenter__.return_value.execute.return_value.scalar_one_or_none.return_value = None
    security_service = mocker.Mock()
    security_service.get_user_email_from_token.return_value = email
    request = mocker.Mock()
    request.headers = {"Authorization": "Bearer test_token"}

    active_user = ActiveUser(db_session_factory, security_service)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await active_user(request)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED