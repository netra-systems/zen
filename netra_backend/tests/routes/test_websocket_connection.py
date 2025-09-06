import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json

import pytest
from fastapi import WebSocket
from netra_backend.app.routes.utils.websocket_helpers import (
    accept_websocket_connection,
    authenticate_websocket_user,
    extract_app_services,
)

class TestWebSocketConnection:
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_success(self):
        """Test successful WebSocket authentication flow"""
        
        # Mock WebSocket
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-token"}
        
        # Mock security service
        # Mock: Security service isolation for auth testing without real token validation
        mock_security_service = MagicNone  # TODO: Use real service instance
        # Mock: Security service isolation for auth testing without real token validation
        mock_security_service.get_user_by_id = AsyncMock(return_value=MagicMock(
            id="test-user-123",
            email="test@example.com", 
            is_active=True
        ))
        
        # Mock auth client (now used for token validation)
        # Mock: Authentication service isolation for testing without real auth flows
        with patch('netra_backend.app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            # Mock: JWT token handling isolation to avoid real crypto dependencies
            mock_auth_client.validate_token_jwt = AsyncMock(return_value={
                "valid": True,
                "user_id": "test-user-123",
                "email": "test@example.com",
                "permissions": []
            })
            
            # Mock database session
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_db_session = MagicNone  # TODO: Use real service instance
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_db.__aenter__ = AsyncMock(return_value=mock_db_session)
                # Mock: Async component isolation for testing without real async operations
                mock_db.__aexit__ = AsyncMock(return_value=None)
                
                # Test authentication
                result = await authenticate_websocket_user(
                    mock_websocket, "valid-token", mock_security_service
                )
                
                assert result == "test-user-123"
                mock_auth_client.validate_token_jwt.assert_called_once_with("valid-token")
                mock_security_service.get_user_by_id.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_websocket_authentication_invalid_token(self):
        """Test WebSocket authentication with invalid token"""
        
        # Mock WebSocket
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "invalid-token"}
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.close = AsyncNone  # TODO: Use real service instance
        
        # Mock security service
        # Mock: Security service isolation for auth testing without real token validation
        mock_security_service = MagicNone  # TODO: Use real service instance
        
        # Mock auth client to return invalid token response
        # Mock: Authentication service isolation for testing without real auth flows
        with patch('netra_backend.app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            # Mock: JWT token handling isolation to avoid real crypto dependencies
            mock_auth_client.validate_token_jwt = AsyncMock(return_value={
                "valid": False,
                "error": "Invalid token"
            })
            
            # Test authentication failure - ValueError should be raised for invalid tokens
            with pytest.raises(ValueError, match="Invalid or expired token"):
                await authenticate_websocket_user(
                    mock_websocket, "invalid-token", mock_security_service
                )
            
            # Verify WebSocket was closed
            mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_accept_websocket_connection_success(self):
        """Test successful WebSocket connection acceptance"""
        
        # Mock WebSocket
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-token"}
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.accept = AsyncNone  # TODO: Use real service instance
        
        # Mock auth client (now used for token validation)
        # Mock: Authentication service isolation for testing without real auth flows
        with patch('netra_backend.app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            # Mock: JWT token handling isolation to avoid real crypto dependencies
            mock_auth_client.validate_token_jwt = AsyncMock(return_value={
                "valid": True,
                "user_id": "test-user"
            })
            
            # Test accept connection
            result = await accept_websocket_connection(mock_websocket)
            
            assert result == "valid-token"
            mock_websocket.accept.assert_called_once()
            mock_auth_client.validate_token_jwt.assert_called_once_with("valid-token")
    
    @pytest.mark.asyncio
    async def test_accept_websocket_connection_no_token(self):
        """Test WebSocket connection with no token"""
        
        # Mock WebSocket without token
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {}
        
        # Test rejection
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await accept_websocket_connection(mock_websocket)
        
        assert exc_info.value.status_code == 403
        assert "No token provided" in str(exc_info.value.detail)
    
    def test_extract_app_services(self):
        """Test extraction of app services from WebSocket"""
        
        # Mock WebSocket with app services
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        # Mock: Generic component isolation for controlled unit testing
        mock_app = MagicNone  # TODO: Use real service instance
        # Mock: Security service isolation for auth testing without real token validation
        mock_security_service = MagicNone  # TODO: Use real service instance
        # Mock: Agent service isolation for testing without LLM agent execution
        mock_agent_service = MagicNone  # TODO: Use real service instance
        
        mock_app.state.security_service = mock_security_service
        mock_app.state.agent_service = mock_agent_service
        mock_websocket.app = mock_app
        
        # Test service extraction
        security, agent = extract_app_services(mock_websocket)
        
        assert security == mock_security_service
        assert agent == mock_agent_service
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_user_not_found(self):
        """Test WebSocket authentication when user not found"""
        
        # Mock WebSocket
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-token"}
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.close = AsyncNone  # TODO: Use real service instance
        
        # Mock security service
        # Mock: Security service isolation for auth testing without real token validation
        mock_security_service = MagicNone  # TODO: Use real service instance
        # Mock: Security service isolation for auth testing without real token validation
        mock_security_service.get_user_by_id = AsyncMock(return_value=None)
        
        # Mock auth client to return valid token for nonexistent user
        # Mock: Authentication service isolation for testing without real auth flows
        with patch('netra_backend.app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            # Mock: JWT token handling isolation to avoid real crypto dependencies
            mock_auth_client.validate_token_jwt = AsyncMock(return_value={
                "valid": True,
                "user_id": "nonexistent-user",
                "email": "nonexistent@example.com",
                "permissions": []
            })
            
            # Mock database session
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_db_session = MagicNone  # TODO: Use real service instance
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_db.__aenter__ = AsyncMock(return_value=mock_db_session)
                # Mock: Async component isolation for testing without real async operations
                mock_db.__aexit__ = AsyncMock(return_value=None)
                
                # Mock user count query
                # Mock: Component isolation for testing without external dependencies
                with patch('netra_backend.app.routes.utils.websocket_helpers.select') as mock_select, \
                     patch('netra_backend.app.routes.utils.websocket_helpers.func') as mock_func:
                    
                    # Mock: Generic component isolation for controlled unit testing
                    mock_result = MagicNone  # TODO: Use real service instance
                    mock_result.scalar.return_value = 1  # Database has users
                    # Mock: Database session isolation for transaction testing without real database dependency
                    mock_db_session.execute = AsyncMock(return_value=mock_result)
                    
                    # Test authentication failure - "User not found" is caught as ValueError and re-raised
                    with pytest.raises(ValueError, match="User not found"):
                        await authenticate_websocket_user(
                            mock_websocket, "valid-token", mock_security_service
                        )
                    
                    # Verify WebSocket was closed
                    mock_websocket.close.assert_called()
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_inactive_user(self):
        """Test WebSocket authentication with inactive user"""
        
        # Mock WebSocket
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-token"}
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.close = AsyncNone  # TODO: Use real service instance
        
        # Mock security service
        # Mock: Security service isolation for auth testing without real token validation
        mock_security_service = MagicNone  # TODO: Use real service instance
        
        # Mock inactive user
        # Mock: Generic component isolation for controlled unit testing
        mock_user = MagicNone  # TODO: Use real service instance
        mock_user.id = "test-user-123"
        mock_user.is_active = False
        # Mock: Security service isolation for auth testing without real token validation
        mock_security_service.get_user_by_id = AsyncMock(return_value=mock_user)
        
        # Mock auth client to return valid token for inactive user
        # Mock: Authentication service isolation for testing without real auth flows
        with patch('netra_backend.app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            # Mock: JWT token handling isolation to avoid real crypto dependencies
            mock_auth_client.validate_token_jwt = AsyncMock(return_value={
                "valid": True,
                "user_id": "test-user-123",
                "email": "test@example.com",
                "permissions": []
            })
            
            # Mock database session
            # Mock: Component isolation for testing without external dependencies
            with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_db_session = MagicNone  # TODO: Use real service instance
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_db.__aenter__ = AsyncMock(return_value=mock_db_session)
                # Mock: Async component isolation for testing without real async operations
                mock_db.__aexit__ = AsyncMock(return_value=None)
                
                # Test authentication failure - "User not active" is caught as ValueError and re-raised
                with pytest.raises(ValueError, match="User not active"):
                    await authenticate_websocket_user(
                        mock_websocket, "valid-token", mock_security_service
                    )
                
                # Verify WebSocket was closed
                mock_websocket.close.assert_called()