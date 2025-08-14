"""Tests for StartupChecker network connectivity checks."""

import pytest
from unittest.mock import patch, Mock

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import (
    create_mock_app, setup_socket_mock
)


class TestStartupCheckerNetwork:
    """Test StartupChecker network connectivity checks."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_success(self, checker):
        """Test network connectivity check success."""
        with patch('socket.socket') as mock_socket_class:
            setup_socket_mock(mock_socket_class, 0)
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user:pass@localhost:5432/db"
                mock_settings.redis = Mock(host="localhost", port=6379)
                
                await checker.check_network_connectivity()
                
                assert len(checker.results) == 1
                assert checker.results[0].success == True
                assert "All network endpoints reachable" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_failure(self, checker):
        """Test network connectivity check with unreachable endpoints."""
        with patch('socket.socket') as mock_socket_class:
            setup_socket_mock(mock_socket_class, 1)
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user:pass@localhost:5432/db"
                mock_settings.redis = Mock(host="localhost", port=6379)
                
                await checker.check_network_connectivity()
                
                assert len(checker.results) == 1
                assert checker.results[0].success == False
                assert "Cannot reach" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_socket_exception(self, checker):
        """Test network connectivity check with socket exception."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.side_effect = Exception("Socket error")
            mock_socket_class.return_value = mock_socket
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://localhost/db"
                mock_settings.redis = None
                
                await checker.check_network_connectivity()
                
                assert len(checker.results) == 1
                assert checker.results[0].success == False
                assert "Socket error" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_no_port(self, checker):
        """Test network connectivity check with endpoint without port."""
        with patch('socket.socket') as mock_socket_class:
            setup_socket_mock(mock_socket_class, 0)
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://hostname/db"
                mock_settings.redis = None
                
                await checker.check_network_connectivity()
                
                assert len(checker.results) == 1
                assert checker.results[0].success == True