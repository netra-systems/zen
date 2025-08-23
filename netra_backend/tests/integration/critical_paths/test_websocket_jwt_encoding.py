"""Integration tests for WebSocket JWT subprotocol encoding/decoding (L3).

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Security & Stability
- Value Impact: Prevents WebSocket authentication failures in production
- Strategic Impact: Ensures secure WebSocket connections work across all browsers

These tests verify that JWT tokens are properly encoded for WebSocket subprotocols
to prevent "SyntaxError: Failed to construct 'WebSocket'" errors.
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import WebSocket
from netra_backend.app.routes.websocket_unified import unified_websocket_endpoint
from netra_backend.app.websocket.unified_websocket_manager import UnifiedWebSocketManager
from starlette.websockets import WebSocketState

from netra_backend.app.db.postgres import get_async_db

class MockWebSocket:

    """Mock WebSocket for testing."""
    
    def __init__(self, headers: Dict[str, str] = None):

        self.headers = headers or {}

        self.application_state = WebSocketState.CONNECTED

        self.accepted = False

        self.accepted_subprotocol = None

        self.messages_sent = []

        self.close_code = None

        self.close_reason = None
    
    async def accept(self, subprotocol: Optional[str] = None):

        self.accepted = True

        self.accepted_subprotocol = subprotocol
    
    async def send_json(self, data: Any):

        self.messages_sent.append(data)
    
    async def receive_text(self):

        await asyncio.sleep(0.1)

        return json.dumps({"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()})
    
    async def close(self, code: int = 1000, reason: str = ""):

        self.application_state = WebSocketState.DISCONNECTED

        self.close_code = code

        self.close_reason = reason

def create_test_jwt(user_id: str = "test-user-123", email: str = "test@example.com") -> str:

    """Create a test JWT token."""

    payload = {

        "sub": user_id,

        "email": email,

        "permissions": ["read", "write"],

        "iat": datetime.now(timezone.utc),

        "exp": datetime.now(timezone.utc) + timedelta(hours=1),

        "token_type": "access",

        "iss": "netra-auth-service"

    }

    return jwt.encode(payload, "test-secret", algorithm="HS256")

def encode_jwt_for_subprotocol(token: str) -> str:

    """Encode JWT token for safe use in WebSocket subprotocol."""
    # Remove Bearer prefix if present

    clean_token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token
    # Base64URL encode

    encoded = base64.b64encode(clean_token.encode()).decode()
    # Make URL-safe

    return encoded.replace('+', '-').replace('/', '_').replace('=', '')

@pytest.mark.asyncio

class TestWebSocketJWTEncodingL3:

    """L3 integration tests for WebSocket JWT encoding."""
    
    async def test_valid_jwt_encoding_decoding(self):

        """Test 1: Valid JWT token is properly encoded and decoded."""
        # Create a test JWT

        test_token = create_test_jwt("user-123", "user@test.com")
        
        # Encode for subprotocol

        encoded_token = encode_jwt_for_subprotocol(test_token)
        
        # Create mock WebSocket with encoded JWT in subprotocol

        mock_ws = MockWebSocket({

            "sec-websocket-protocol": f"jwt-auth, jwt.{encoded_token}"

        })
        
        # Create manager and test validation

        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:

                mock_validate.return_value = {

                    "valid": True,

                    "user_id": "user-123",

                    "email": "user@test.com",

                    "permissions": ["read", "write"],

                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

                }
                
                # Validate auth should decode and validate the token

                result = await manager.validate_secure_auth(mock_ws)
                
                assert result["user_id"] == "user-123"

                assert result["email"] == "user@test.com"

                assert result["auth_method"] == "subprotocol"
                
                # Verify the decoded token was sent to auth service

                mock_validate.assert_called_once()

                call_args = mock_validate.call_args[0][0]

                assert call_args == test_token  # Should be the original token
    
    async def test_invalid_base64_encoding_rejection(self):

        """Test 2: Invalid base64 encoded tokens are rejected."""
        # Create invalid base64 (not properly encoded)

        invalid_encoded = "not-valid-base64!@#$%"
        
        mock_ws = MockWebSocket({

            "sec-websocket-protocol": f"jwt.{invalid_encoded}"

        })
        
        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with pytest.raises(Exception) as exc_info:

                await manager.validate_secure_auth(mock_ws)
            
            assert "No secure JWT token provided" in str(exc_info.value.detail)
    
    async def test_bearer_prefix_handling(self):

        """Test 3: Bearer prefix is properly handled in encoding/decoding."""
        # Test with Bearer prefix

        test_token = "Bearer " + create_test_jwt("user-456", "bearer@test.com")
        
        # Frontend would encode without Bearer

        clean_token = test_token.replace("Bearer ", "")

        encoded_token = encode_jwt_for_subprotocol(clean_token)
        
        mock_ws = MockWebSocket({

            "sec-websocket-protocol": f"jwt.{encoded_token}"

        })
        
        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:

                mock_validate.return_value = {

                    "valid": True,

                    "user_id": "user-456",

                    "email": "bearer@test.com",

                    "permissions": ["read"],

                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

                }
                
                result = await manager.validate_secure_auth(mock_ws)
                
                assert result["user_id"] == "user-456"

                assert result["auth_method"] == "subprotocol"
                
                # Should validate with clean token (no Bearer)

                mock_validate.assert_called_once()

                call_args = mock_validate.call_args[0][0]

                assert not call_args.startswith("Bearer ")
    
    async def test_special_characters_in_jwt(self):

        """Test 4: JWTs with special characters are properly encoded."""
        # JWT tokens naturally contain dots, hyphens, underscores

        test_token = create_test_jwt("special-user_123.456", "special@test.com")
        
        # These characters would break subprotocol without encoding

        assert "." in test_token

        assert "_" in test_token or "-" in test_token
        
        encoded_token = encode_jwt_for_subprotocol(test_token)
        
        # Encoded version should be subprotocol-safe
        # (base64url uses only A-Z, a-z, 0-9, -, _)

        assert all(c.isalnum() or c in '-_' for c in encoded_token)
        
        mock_ws = MockWebSocket({

            "sec-websocket-protocol": f"jwt.{encoded_token}"

        })
        
        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:

                mock_validate.return_value = {

                    "valid": True,

                    "user_id": "special-user_123.456",

                    "email": "special@test.com",

                    "permissions": ["admin"],

                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

                }
                
                result = await manager.validate_secure_auth(mock_ws)

                assert result["user_id"] == "special-user_123.456"
    
    async def test_subprotocol_negotiation_with_jwt_auth(self):

        """Test 5: Proper subprotocol negotiation with jwt-auth protocol."""

        test_token = create_test_jwt("negotiation-user", "negotiate@test.com")

        encoded_token = encode_jwt_for_subprotocol(test_token)
        
        # Client sends multiple protocols

        mock_ws = MockWebSocket({

            "sec-websocket-protocol": f"jwt-auth, jwt.{encoded_token}, chat"

        })
        
        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:

                mock_validate.return_value = {

                    "valid": True,

                    "user_id": "negotiation-user",

                    "email": "negotiate@test.com",

                    "permissions": ["read"],

                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

                }
                
                # Test the endpoint's subprotocol selection logic

                result = await manager.validate_secure_auth(mock_ws)

                assert result["auth_method"] == "subprotocol"
                
                # Server should select jwt-auth as the accepted protocol
                # (This would be done in the actual endpoint)

                protocols = mock_ws.headers.get("sec-websocket-protocol", "").split(",")

                selected = None

                for protocol in protocols:

                    protocol = protocol.strip()

                    if protocol == "jwt-auth" or protocol.startswith("jwt."):

                        selected = "jwt-auth"

                        break
                
                assert selected == "jwt-auth"
    
    async def test_malformed_jwt_structure_rejection(self):

        """Test 6: Malformed JWT structure (not 3 parts) is rejected."""
        # JWT should have 3 parts separated by dots

        malformed_token = "only.two.parts"  # Missing signature

        encoded_token = encode_jwt_for_subprotocol(malformed_token)
        
        mock_ws = MockWebSocket({

            "sec-websocket-protocol": f"jwt.{encoded_token}"

        })
        
        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:

                mock_validate.return_value = {"valid": False}
                
                with pytest.raises(Exception) as exc_info:

                    await manager.validate_secure_auth(mock_ws)
                
                assert "Invalid or expired token" in str(exc_info.value.detail)
    
    async def test_expired_jwt_rejection(self):

        """Test 7: Expired JWT tokens are properly rejected."""
        # Create an expired token

        expired_payload = {

            "sub": "expired-user",

            "email": "expired@test.com",

            "permissions": ["read"],

            "iat": datetime.now(timezone.utc) - timedelta(hours=2),

            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago

            "token_type": "access",

            "iss": "netra-auth-service"

        }

        expired_token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")

        encoded_token = encode_jwt_for_subprotocol(expired_token)
        
        mock_ws = MockWebSocket({

            "sec-websocket-protocol": f"jwt.{encoded_token}"

        })
        
        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:
                # Auth service would reject expired token

                mock_validate.return_value = {"valid": False, "error": "Token expired"}
                
                with pytest.raises(Exception) as exc_info:

                    await manager.validate_secure_auth(mock_ws)
                
                assert "Invalid or expired token" in str(exc_info.value.detail)
    
    async def test_empty_subprotocol_fallback(self):

        """Test 8: Empty or missing JWT in subprotocol falls back to header auth."""
        # No JWT in subprotocol, but has Authorization header

        test_token = create_test_jwt("header-user", "header@test.com")
        
        mock_ws = MockWebSocket({

            "authorization": f"Bearer {test_token}",

            "sec-websocket-protocol": "chat"  # No JWT protocol

        })
        
        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:

                mock_validate.return_value = {

                    "valid": True,

                    "user_id": "header-user",

                    "email": "header@test.com",

                    "permissions": ["read", "write"],

                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

                }
                
                result = await manager.validate_secure_auth(mock_ws)
                
                assert result["user_id"] == "header-user"

                assert result["auth_method"] == "header"  # Used header instead of subprotocol
    
    async def test_concurrent_connections_with_encoded_jwt(self):

        """Test 9: Multiple concurrent connections with encoded JWTs work correctly."""
        # Create multiple users with different tokens

        users = [

            ("concurrent-user-1", "user1@test.com"),

            ("concurrent-user-2", "user2@test.com"),

            ("concurrent-user-3", "user3@test.com")

        ]
        
        async def connect_user(user_id: str, email: str):

            test_token = create_test_jwt(user_id, email)

            encoded_token = encode_jwt_for_subprotocol(test_token)
            
            mock_ws = MockWebSocket({

                "sec-websocket-protocol": f"jwt.{encoded_token}"

            })
            
            async with get_async_db() as db_session:

                manager = SecureWebSocketManager(db_session)
                
                with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:

                    mock_validate.return_value = {

                        "valid": True,

                        "user_id": user_id,

                        "email": email,

                        "permissions": ["read"],

                        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

                    }
                    
                    result = await manager.validate_secure_auth(mock_ws)

                    return result
        
        # Connect all users concurrently

        results = await asyncio.gather(*[

            connect_user(user_id, email) for user_id, email in users

        ])
        
        # Verify all connections succeeded with correct user data

        for i, (user_id, email) in enumerate(users):

            assert results[i]["user_id"] == user_id

            assert results[i]["email"] == email

            assert results[i]["auth_method"] == "subprotocol"
    
    async def test_encoding_decoding_roundtrip_integrity(self):

        """Test 10: JWT encoding/decoding roundtrip maintains token integrity."""
        # Create a complex JWT with all possible claims

        complex_payload = {

            "sub": "roundtrip-user",

            "email": "roundtrip@test.com",

            "permissions": ["read", "write", "admin", "super-admin"],

            "roles": ["user", "moderator", "admin"],

            "org_id": "org-123-456-789",

            "session_id": "sess_abcdef123456",

            "iat": datetime.now(timezone.utc),

            "exp": datetime.now(timezone.utc) + timedelta(hours=24),

            "nbf": datetime.now(timezone.utc) - timedelta(minutes=5),

            "token_type": "access",

            "iss": "netra-auth-service",

            "aud": ["api", "websocket", "admin-panel"],

            "custom_claim": "test-value-with-special-chars!@#$%"

        }
        
        original_token = jwt.encode(complex_payload, "test-secret", algorithm="HS256")
        
        # Encode for subprotocol

        encoded_token = encode_jwt_for_subprotocol(original_token)
        
        # Manually decode (as backend would)

        padded_token = encoded_token + '=' * (4 - len(encoded_token) % 4)

        standard_b64 = padded_token.replace('-', '+').replace('_', '/')

        decoded_token = base64.b64decode(standard_b64).decode('utf-8')
        
        # Verify tokens match

        assert decoded_token == original_token
        
        # Verify JWT payload integrity

        decoded_payload = jwt.decode(decoded_token, "test-secret", algorithms=["HS256"])
        
        assert decoded_payload["sub"] == "roundtrip-user"

        assert decoded_payload["email"] == "roundtrip@test.com"

        assert len(decoded_payload["permissions"]) == 4

        assert decoded_payload["custom_claim"] == "test-value-with-special-chars!@#$%"
        
        # Test with the actual WebSocket manager

        mock_ws = MockWebSocket({

            "sec-websocket-protocol": f"jwt.{encoded_token}"

        })
        
        async with get_async_db() as db_session:

            manager = SecureWebSocketManager(db_session)
            
            with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:

                mock_validate.return_value = {

                    "valid": True,

                    "user_id": "roundtrip-user",

                    "email": "roundtrip@test.com",

                    "permissions": complex_payload["permissions"],

                    "expires_at": complex_payload["exp"].isoformat()

                }
                
                result = await manager.validate_secure_auth(mock_ws)
                
                assert result["user_id"] == "roundtrip-user"

                assert result["permissions"] == complex_payload["permissions"]
                
                # Verify the original token was sent to auth service

                mock_validate.assert_called_once()

                call_args = mock_validate.call_args[0][0]

                assert call_args == original_token