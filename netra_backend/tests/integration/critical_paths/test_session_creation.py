"""
L3 Integration Test: Session Creation
Tests session creation and initialization scenarios
"""""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid

import pytest

from netra_backend.app.config import get_config

from netra_backend.app.services.session_service import SessionService

class TestSessionCreationL3:
    """Test session creation scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_session_creation_with_user_data(self):
        """Test session creation with user data"""
        session_service = SessionService()

        user_data = {
        "user_id": "123",
        "username": "testuser",
        "email": "test@example.com",
        "role": "user"
        }

        session = await session_service.create_session(user_data)

        assert session is not None
        assert "session_id" in session
        assert session["user_id"] == "123"
        assert session["username"] == "testuser"
        assert "created_at" in session
        assert "expires_at" in session

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.l3
        @pytest.mark.asyncio
        async def test_session_unique_id_generation(self):
            """Test unique session ID generation"""
            session_service = SessionService()

            sessions = []
            for _ in range(10):
                session = await session_service.create_session({"user_id": "123"})
                sessions.append(session["session_id"])

        # All session IDs should be unique
                assert len(set(sessions)) == 10

        # Should be valid UUIDs or similar format
                for sid in sessions:
                    assert len(sid) > 0
                    assert isinstance(sid, str)

                    @pytest.mark.asyncio
                    @pytest.mark.integration
                    @pytest.mark.l3
                    @pytest.mark.asyncio
                    async def test_session_expiration_time_setting(self):
                        """Test session expiration time configuration"""
                        session_service = SessionService()

                        session = await session_service.create_session({"user_id": "123"})

                        created_at = session["created_at"]
                        expires_at = session["expires_at"]

        # Calculate duration
                        duration = expires_at - created_at

        # Should match configured session timeout
                        assert duration > 0
                        assert duration <= settings.SESSION_TIMEOUT

                        @pytest.mark.asyncio
                        @pytest.mark.integration
                        @pytest.mark.l3
                        @pytest.mark.asyncio
                        async def test_session_metadata_storage(self):
                            """Test session metadata storage"""
                            session_service = SessionService()

                            metadata = {
                            "ip_address": "192.168.1.100",
                            "user_agent": "Mozilla/5.0",
                            "device_id": "device_123",
                            "location": "US"
                            }

                            session = await session_service.create_session(
                            user_data={"user_id": "123"},
                            metadata=metadata
                            )

                            assert session["ip_address"] == "192.168.1.100"
                            assert session["user_agent"] == "Mozilla/5.0"
                            assert session["device_id"] == "device_123"

                            @pytest.mark.asyncio
                            @pytest.mark.integration
                            @pytest.mark.l3
                            @pytest.mark.asyncio
                            async def test_concurrent_session_creation(self):
                                """Test concurrent session creation for same user"""
                                session_service = SessionService()

        # Create multiple sessions concurrently
                                tasks = [
                                session_service.create_session({"user_id": "123"})
                                for _ in range(10)
                                ]

                                sessions = await asyncio.gather(*tasks)

        # All should succeed
                                assert len(sessions) == 10

        # All should have unique IDs
                                session_ids = [s["session_id"] for s in sessions]
                                assert len(set(session_ids)) == 10