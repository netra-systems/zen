import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import WebSocket
from app.routes.utils.websocket_helpers import (
    authenticate_websocket_user, 
    extract_app_services,
    accept_websocket_connection
)

class TestWebSocketConnection:
    
    @pytest.mark.asyncio
    async def test_websocket_authentication_success(self):
        """Test successful WebSocket authentication flow"""
        
        # Mock WebSocket
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-token"}
        
        # Mock security service
        mock_security_service = MagicMock()
        mock_security_service.get_user_by_id = AsyncMock(return_value=MagicMock(
            id="test-user-123",
            email="test@example.com", 
            is_active=True
        ))
        
        # Mock auth client (now used for token validation)
        with patch('app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            mock_auth_client.validate_token = AsyncMock(return_value={
                "valid": True,
                "user_id": "test-user-123",
                "email": "test@example.com",
                "permissions": []
            })
            
            # Mock database session
            with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
                mock_db_session = MagicMock()
                mock_db.__aenter__ = AsyncMock(return_value=mock_db_session)
                mock_db.__aexit__ = AsyncMock(return_value=None)
                
                # Test authentication
                result = await authenticate_websocket_user(
                    mock_websocket, "valid-token", mock_security_service
                )
                
                assert result == "test-user-123"
                mock_auth_client.validate_token.assert_called_once_with("valid-token")
                mock_security_service.get_user_by_id.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_websocket_authentication_invalid_token(self):
        """Test WebSocket authentication with invalid token"""
        
        # Mock WebSocket
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "invalid-token"}
        mock_websocket.close = AsyncMock()
        
        # Mock security service
        mock_security_service = MagicMock()
        
        # Mock auth client to return invalid token response
        with patch('app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            mock_auth_client.validate_token = AsyncMock(return_value={
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
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-token"}
        mock_websocket.accept = AsyncMock()
        
        # Mock auth client (now used for token validation)
        with patch('app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            mock_auth_client.validate_token = AsyncMock(return_value={
                "valid": True,
                "user_id": "test-user"
            })
            
            # Test accept connection
            result = await accept_websocket_connection(mock_websocket)
            
            assert result == "valid-token"
            mock_websocket.accept.assert_called_once()
            mock_auth_client.validate_token.assert_called_once_with("valid-token")
    
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
        mock_websocket = MagicMock(spec=WebSocket)
        mock_app = MagicMock()
        mock_security_service = MagicMock()
        mock_agent_service = MagicMock()
        
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
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-token"}
        mock_websocket.close = AsyncMock()
        
        # Mock security service
        mock_security_service = MagicMock()
        mock_security_service.get_user_by_id = AsyncMock(return_value=None)
        
        # Mock auth client to return valid token for nonexistent user
        with patch('app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            mock_auth_client.validate_token = AsyncMock(return_value={
                "valid": True,
                "user_id": "nonexistent-user",
                "email": "nonexistent@example.com",
                "permissions": []
            })
            
            # Mock database session
            with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
                mock_db_session = MagicMock()
                mock_db.__aenter__ = AsyncMock(return_value=mock_db_session)
                mock_db.__aexit__ = AsyncMock(return_value=None)
                
                # Mock user count query
                with patch('app.routes.utils.websocket_helpers.select') as mock_select, \
                     patch('app.routes.utils.websocket_helpers.func') as mock_func:
                    
                    mock_result = MagicMock()
                    mock_result.scalar.return_value = 1  # Database has users
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
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.query_params = {"token": "valid-token"}
        mock_websocket.close = AsyncMock()
        
        # Mock security service
        mock_security_service = MagicMock()
        
        # Mock inactive user
        mock_user = MagicMock()
        mock_user.id = "test-user-123"
        mock_user.is_active = False
        mock_security_service.get_user_by_id = AsyncMock(return_value=mock_user)
        
        # Mock auth client to return valid token for inactive user
        with patch('app.routes.utils.websocket_helpers.auth_client') as mock_auth_client:
            mock_auth_client.validate_token = AsyncMock(return_value={
                "valid": True,
                "user_id": "test-user-123",
                "email": "test@example.com",
                "permissions": []
            })
            
            # Mock database session
            with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
                mock_db_session = MagicMock()
                mock_db.__aenter__ = AsyncMock(return_value=mock_db_session)
                mock_db.__aexit__ = AsyncMock(return_value=None)
                
                # Test authentication failure - "User not active" is caught as ValueError and re-raised
                with pytest.raises(ValueError, match="User not active"):
                    await authenticate_websocket_user(
                        mock_websocket, "valid-token", mock_security_service
                    )
                
                # Verify WebSocket was closed
                mock_websocket.close.assert_called()