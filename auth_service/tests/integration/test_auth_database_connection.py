"""Test auth service database connection and session management."""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from auth_service.auth_core.database_manager import DatabaseManager
from auth_service.auth_core.models import User
from test_framework.fixtures import isolated_environment
from test_framework.unified.auth_database_session import AuthDatabaseSessionTestManager

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth_service,
    pytest.mark.database
]

class TestAuthDatabaseConnection:
    """Test auth service database connectivity and session management."""
    
    @pytest.mark.asyncio
    async def test_auth_database_connection_fails_without_ssl(self, isolated_environment):
        """Test that auth database connection fails without SSL configuration."""
        # This test should fail initially - we expect SSL to be required
        manager = DatabaseManager()
        
        # Attempt connection without SSL parameters
        with pytest.raises(Exception, match="SSL"):
            await manager.get_session()
            
    @pytest.mark.asyncio 
    async def test_auth_user_creation_database_integrity(self, isolated_environment):
        """Test that user creation maintains database integrity."""
        session_manager = AuthDatabaseSessionTestManager()
        
        # This should fail initially - no database session setup
        async with session_manager.get_test_session() as session:
            user = User(
                email="test@example.com",
                password_hash="hashed_password",
                is_active=True
            )
            session.add(user)
            await session.commit()
            
            # Verify user exists
            result = await session.execute("SELECT * FROM users WHERE email = 'test@example.com'")
            assert result.rowcount > 0