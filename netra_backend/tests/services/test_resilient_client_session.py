"""Tests for ResilientHTTPClient session management."""

import sys
from pathlib import Path

from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest

from netra_backend.app.services.external_api_client import ResilientHTTPClient
from netra_backend.tests.services.external_api_client_utils import (
    create_mock_session,
    verify_new_session_creation,
)

class TestResilientHTTPClientSession:
    """Test ResilientHTTPClient session management."""
    
    @pytest.fixture
    def client(self):
        """Create a ResilientHTTPClient for testing."""
        return ResilientHTTPClient(
            base_url="https://api.example.com",
            default_headers={"User-Agent": "test-client"}
        )
    @pytest.mark.asyncio
    async def test_get_session_new(self, client):
        """Test getting new session."""
        mock_session = create_mock_session()
        
        with patch('app.services.external_api_client.ClientSession', return_value=mock_session) as mock_session_class:
            session = await client._get_session()
            verify_new_session_creation(session, mock_session, mock_session_class, client)
    @pytest.mark.asyncio
    async def test_get_session_reuse(self, client):
        """Test reusing existing session."""
        mock_session = Mock()
        mock_session.closed = False
        client._session = mock_session
        
        session = await client._get_session()
        assert session == mock_session
    @pytest.mark.asyncio
    async def test_get_session_closed_recreate(self, client):
        """Test recreating closed session."""
        old_session = create_mock_session(closed=True)
        client._session = old_session
        
        with patch('app.services.external_api_client.ClientSession') as mock_session_class:
            new_session = create_mock_session()
            mock_session_class.return_value = new_session
            
            session = await client._get_session()
            assert session == new_session
    @pytest.mark.asyncio
    async def test_close_session(self, client):
        """Test closing HTTP session."""
        mock_session = self._setup_mock_session_for_close()
        client._session = mock_session
        
        await client.close()
        mock_session.close.assert_called_once()
    
    def _setup_mock_session_for_close(self):
        """Setup mock session for close test."""
        from unittest.mock import AsyncMock, MagicMock
        mock_session = Mock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        return mock_session
    @pytest.mark.asyncio
    async def test_close_no_session(self, client):
        """Test closing when no session exists."""
        await client.close()  # Should not raise exception
    @pytest.mark.asyncio
    async def test_close_already_closed_session(self, client):
        """Test closing already closed session."""
        mock_session = self._setup_closed_session_mock()
        client._session = mock_session
        
        await client.close()
        mock_session.close.assert_not_called()
    
    def _setup_closed_session_mock(self):
        """Setup mock closed session."""
        from unittest.mock import AsyncMock, MagicMock
        mock_session = Mock()
        mock_session.closed = True
        mock_session.close = AsyncMock()
        return mock_session