"""
L3 Integration Test: Session Sharing
Tests session sharing across services and devices
"""""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json

import pytest

from netra_backend.app.config import get_config

from netra_backend.app.services.session_service import SessionService

class TestSessionSharingL3:
    """Test session sharing scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_session_sharing_across_services(self):
        """Test session sharing between microservices"""
        session_service = SessionService()

        # Create session in main service
        session = await session_service.create_session({
        "user_id": "123",
        "service": "main"
        })
        session_id = session["session_id"]

        # Validate from auth service
        with patch.object(session_service, 'service_name', 'auth'):
            is_valid = await session_service.validate_session(session_id)
            assert is_valid is True

            # Can read session data
            data = await session_service.get_session(session_id)
            assert data["user_id"] == "123"

            @pytest.mark.asyncio
            @pytest.mark.integration
            @pytest.mark.l3
            @pytest.mark.asyncio
            async def test_session_device_binding(self):
                """Test session binding to specific devices"""
                session_service = SessionService()

        # Create device-bound session
                session = await session_service.create_session(
                user_data={"user_id": "123"},
                metadata={"device_id": "device_abc", "bind_to_device": True}
                )
                session_id = session["session_id"]

        # Access from same device
                is_valid = await session_service.validate_session(
                session_id,
                device_id="device_abc"
                )
                assert is_valid is True

        # Access from different device
                is_valid = await session_service.validate_session(
                session_id,
                device_id="device_xyz"
                )
                assert is_valid is False

                @pytest.mark.asyncio
                @pytest.mark.integration
                @pytest.mark.l3
                @pytest.mark.asyncio
                async def test_session_delegation(self):
                    """Test session delegation/impersonation"""
                    session_service = SessionService()

        # Admin session
                    admin_session = await session_service.create_session({
                    "user_id": "admin",
                    "role": "admin",
                    "can_delegate": True
                    })

        # Create delegated session
                    delegated = await session_service.create_delegated_session(
                    admin_session["session_id"],
                    target_user_id="user_123",
                    duration=3600
                    )

                    assert delegated is not None
                    assert delegated["delegated_from"] == "admin"
                    assert delegated["user_id"] == "user_123"
                    assert delegated["is_delegated"] is True

                    @pytest.mark.asyncio
                    @pytest.mark.integration
                    @pytest.mark.l3
                    @pytest.mark.asyncio
                    async def test_session_federation(self):
                        """Test session federation across domains"""
                        session_service = SessionService()

        # Create session in primary domain
                        session = await session_service.create_session({
                        "user_id": "123",
                        "domain": "primary.com"
                        })

        # Generate federation token
                        fed_token = await session_service.generate_federation_token(
                        session["session_id"],
                        target_domain="secondary.com"
                        )

                        assert fed_token is not None

        # Validate federation token in secondary domain
                        with patch.object(session_service, 'domain', 'secondary.com'):
                            federated_session = await session_service.validate_federation_token(fed_token)
                            assert federated_session is not None
                            assert federated_session["user_id"] == "123"
                            assert federated_session["federated_from"] == "primary.com"

                            @pytest.mark.asyncio
                            @pytest.mark.integration
                            @pytest.mark.l3
                            @pytest.mark.asyncio
                            async def test_session_scope_restrictions(self):
                                """Test session scope and permission restrictions"""
                                session_service = SessionService()

        # Create limited scope session
                                session = await session_service.create_session({
                                "user_id": "123",
                                "scope": ["read:profile", "read:settings"]
                                })
                                session_id = session["session_id"]

        # Check allowed scope
                                can_read = await session_service.check_session_scope(
                                session_id,
                                "read:profile"
                                )
                                assert can_read is True

        # Check disallowed scope
                                can_write = await session_service.check_session_scope(
                                session_id,
                                "write:settings"
                                )
                                assert can_write is False