"""
L3 Integration Test: Session Cleanup
Tests session cleanup and garbage collection
"""""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import time

import pytest

from netra_backend.app.config import get_config

from netra_backend.app.services.session_service import SessionService

class TestSessionCleanupL3:
    """Test session cleanup scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_manual_session_cleanup(self):
        """Test manual session cleanup/logout"""
        session_service = SessionService()

        # Create session
        session = await session_service.create_session({"user_id": "123"})
        session_id = session["session_id"]

        # Verify exists
        exists = await session_service.validate_session(session_id)
        assert exists is True

        # Clean up session
        await session_service.destroy_session(session_id)

        # Should no longer exist
        exists = await session_service.validate_session(session_id)
        assert exists is False

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.l3
        @pytest.mark.asyncio
        async def test_automatic_expired_session_cleanup(self):
            """Test automatic cleanup of expired sessions"""
            session_service = SessionService()

        # Create sessions with short expiry
            with patch.object(session_service, 'SESSION_TIMEOUT', 1):
                sessions = []
                for i in range(5):
                    session = await session_service.create_session({"user_id": f"{i}"})
                    sessions.append(session["session_id"])

            # Wait for expiry
                    await asyncio.sleep(1.5)

            # Run cleanup
                    cleaned = await session_service.cleanup_expired_sessions()

                    assert cleaned >= 5

            # Sessions should be gone
                    for sid in sessions:
                        exists = await session_service.validate_session(sid)
                        assert exists is False

                        @pytest.mark.asyncio
                        @pytest.mark.integration
                        @pytest.mark.l3
                        @pytest.mark.asyncio
                        async def test_session_cleanup_preserves_active(self):
                            """Test cleanup preserves active sessions"""
                            session_service = SessionService()

        # Create mix of sessions
                            active_session = await session_service.create_session({"user_id": "active"})

        # Create expired session
                            with patch.object(session_service, 'SESSION_TIMEOUT', 0.1):
                                expired_session = await session_service.create_session({"user_id": "expired"})

        # Wait for one to expire
                                await asyncio.sleep(0.2)

        # Run cleanup
                                await session_service.cleanup_expired_sessions()

        # Active should remain
                                assert await session_service.validate_session(active_session["session_id"]) is True

        # Expired should be gone
                                assert await session_service.validate_session(expired_session["session_id"]) is False

                                @pytest.mark.asyncio
                                @pytest.mark.integration
                                @pytest.mark.l3
                                @pytest.mark.asyncio
                                async def test_bulk_session_cleanup(self):
                                    """Test bulk session cleanup for user"""
                                    session_service = SessionService()
                                    user_id = "123"

        # Create multiple sessions for user
                                    sessions = []
                                    for _ in range(10):
                                        session = await session_service.create_session({"user_id": user_id})
                                        sessions.append(session["session_id"])

        # Destroy all user sessions
                                        await session_service.destroy_user_sessions(user_id)

        # All should be gone
                                        for sid in sessions:
                                            exists = await session_service.validate_session(sid)
                                            assert exists is False

                                            @pytest.mark.asyncio
                                            @pytest.mark.integration
                                            @pytest.mark.l3
                                            @pytest.mark.asyncio
                                            async def test_session_cleanup_race_condition(self):
                                                """Test race conditions during session cleanup"""
                                                session_service = SessionService()

                                                session = await session_service.create_session({"user_id": "123"})
                                                session_id = session["session_id"]

        # Concurrent cleanup and access
                                                async def cleanup():
                                                    await asyncio.sleep(0.01)
                                                    await session_service.destroy_session(session_id)

                                                    async def access():
                                                        await asyncio.sleep(0.01)
                                                        return await session_service.get_session(session_id)

                                                    cleanup_task = asyncio.create_task(cleanup())
                                                    access_task = asyncio.create_task(access())

                                                    result = await access_task
                                                    await cleanup_task

        # Should handle gracefully (either return None or last valid state)
                                                    assert result is None or isinstance(result, dict)