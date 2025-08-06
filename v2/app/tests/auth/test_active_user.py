import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from app.auth.active_user import ActiveUser
from app.db import models_postgres

@pytest.mark.asyncio
async def test_active_user_development():
    """Tests that the active user dependency returns a mock user in development mode."""
    request = Mock()
    request.app.state.security_service = None
    request.app.state.db_session_factory = None

    active_user_dependency = ActiveUser(None, None)

    with patch("app.auth.active_user.settings.app_env", "development"):
        user = await active_user_dependency(request)
        assert user.email == "dev@example.com"

@pytest.mark.asyncio
async def test_active_user_production_unauthenticated():
    """Tests that the active user dependency raises an HTTPException for unauthenticated users in production mode."""
    request = Mock()
    request.headers.get = Mock(return_value=None)
    request.app.state.security_service = None
    request.app.state.db_session_factory = None

    active_user_dependency = ActiveUser(None, None)

    with patch("app.auth.active_user.settings.app_env", "production"):
        with pytest.raises(HTTPException) as exc_info:
            await active_user_dependency(request)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"