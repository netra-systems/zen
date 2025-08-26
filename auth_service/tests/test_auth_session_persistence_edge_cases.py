"""
Authentication session persistence edge case tests.

Tests critical session persistence scenarios that cause revenue loss through user abandonment.
Focus: Service restart scenarios, database failover, and cross-service session consistency.
"""
import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock

from auth_service.auth_core.core.session_manager import SessionManager
from auth_service.auth_core.models.auth_models import User
from auth_service.auth_core.database.database_manager import AuthDatabaseManager as DatabaseManager


@pytest.mark.critical
@pytest.mark.auth_service
async def test_session_persistence_during_service_restart():
    """Test session survives auth service restart without user re-login."""
    session_manager = SessionManager()
    
    # Create active session
    user = User(id="user123", email="test@example.com")
    session_token = await session_manager.create_session(user)
    
    # Simulate service restart by creating new manager instance
    restarted_manager = SessionManager()
    
    # Verify session still valid
    is_valid = await restarted_manager.validate_session(session_token)
    assert is_valid, "Session must persist through service restart"


@pytest.mark.critical 
@pytest.mark.auth_service
async def test_session_consistency_during_database_failover():
    """Test session remains valid during database failover scenarios."""
    session_manager = SessionManager()
    user = User(id="user456", email="failover@example.com")
    session_token = await session_manager.create_session(user)
    
    # Simulate database connection failure
    with patch.object(DatabaseManager, 'get_connection') as mock_conn:
        mock_conn.side_effect = Exception("Database connection lost")
        
        # Session should still validate from cache
        is_valid = await session_manager.validate_session(session_token)
        assert is_valid, "Session must work during database failover"


@pytest.mark.critical
@pytest.mark.auth_service  
async def test_cross_service_session_sync_consistency():
    """Test session updates sync correctly between auth and backend services."""
    session_manager = SessionManager()
    user = User(id="user789", email="sync@example.com")
    session_token = await session_manager.create_session(user)
    
    # Update session permissions
    await session_manager.update_permissions(session_token, ["admin"])
    
    # Verify sync happens within acceptable timeframe
    start_time = time.time()
    synced = False
    
    while time.time() - start_time < 2.0:  # 2 second timeout
        permissions = await session_manager.get_permissions(session_token)
        if "admin" in permissions:
            synced = True
            break
        await asyncio.sleep(0.1)
    
    assert synced, "Session updates must sync within 2 seconds"


@pytest.mark.critical
@pytest.mark.auth_service
async def test_session_cleanup_on_user_logout():
    """Test session properly cleaned up when user logs out."""
    session_manager = SessionManager()
    user = User(id="user101", email="logout@example.com")
    session_token = await session_manager.create_session(user)
    
    # Logout user
    await session_manager.logout(session_token)
    
    # Verify session invalidated
    is_valid = await session_manager.validate_session(session_token)
    assert not is_valid, "Session must be invalid after logout"