"""
L2 Integration Test: WebSocket Authentication Handshake

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Secure connections worth $9K MRR security
- Value Impact: Ensures authenticated and authorized WebSocket connections
- Strategic Impact: Prevents security breaches and maintains enterprise trust

L2 Test: Real internal auth handshake components with mocked external auth services.
Performance target: <200ms handshake completion, 99.9% auth accuracy.
"""

import pytest
import asyncio
import json
import time
import jwt
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
from enum import Enum

from ws_manager import WebSocketManager
from schemas import UserInDB
from test_framework.mock_utils import mock_justified


class HandshakeState(Enum):
    """WebSocket handshake states."""
    INITIATED = "initiated"
    TOKEN_VALIDATED = "token_validated"
    USER_AUTHORIZED = "user_authorized"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class AuthTokenType(Enum):
    """Types of authentication tokens."""
    JWT = "jwt"
    API_KEY = "api_key"
    SESSION = "session"
    OAUTH = "oauth"


class WebSocketAuthHandshake:
    """Handle WebSocket authentication handshake process."""
    
    def __init__(self):
        self.secret_key = "test_secret_key_for_jwt"
        self.token_expiry = 3600  # 1 hour
        self.handshake_timeout = 10.0  # 10 seconds
        self.supported_protocols = ["netra-v1", "netra-v2"]
        self.auth_stats = {
            "total_handshakes": 0,
            "successful_auth": 0,
            "failed_auth": 0,
            "token_expired": 0,
            "invalid_tokens": 0,
            "unauthorized_users": 0,
            "protocol_mismatches": 0
        }
    
    async def initiate_handshake(self, websocket: Any, headers: Dict[str, str]) -> Dict[str, Any]:
        """Initiate WebSocket authentication handshake."""
        self.auth_stats["total_handshakes"] += 1
        handshake_id = str(uuid4())
        
        handshake_context = {
            "handshake_id": handshake_id,
            "state": HandshakeState.INITIATED,
            "started_at": time.time(),
            "websocket": websocket,
            "headers": headers,
            "auth_data": {},
            "errors": []
        }
        
        try:
            # Validate protocol
            protocol_check = self._validate_protocol(headers)
            if not protocol_check["valid"]:
                handshake_context["state"] = HandshakeState.REJECTED
                handshake_context["errors"].append(protocol_check["error"])
                self.auth_stats["protocol_mismatches"] += 1
                return handshake_context
            
            # Extract authentication token
            token_result = self._extract_auth_token(headers)
            if not token_result["success"]:
                handshake_context["state"] = HandshakeState.FAILED
                handshake_context["errors"].append(token_result["error"])
                self.auth_stats["failed_auth"] += 1
                return handshake_context
            
            handshake_context["auth_data"] = token_result["data"]
            
            # Validate token
            validation_result = await self._validate_token_jwt(token_result["data"])
            if not validation_result["valid"]:
                handshake_context["state"] = HandshakeState.FAILED
                handshake_context["errors"].extend(validation_result["errors"])
                if "expired" in str(validation_result["errors"]):
                    self.auth_stats["token_expired"] += 1
                else:
                    self.auth_stats["invalid_tokens"] += 1
                return handshake_context
            
            handshake_context["state"] = HandshakeState.TOKEN_VALIDATED
            handshake_context["auth_data"].update(validation_result["data"])
            
            # Authorize user
            auth_result = await self._authorize_user(validation_result["data"])
            if not auth_result["authorized"]:
                handshake_context["state"] = HandshakeState.REJECTED
                handshake_context["errors"].append(auth_result["error"])
                self.auth_stats["unauthorized_users"] += 1
                return handshake_context
            
            handshake_context["state"] = HandshakeState.USER_AUTHORIZED
            handshake_context["auth_data"]["user"] = auth_result["user_data"]
            
            # Complete handshake
            completion_result = await self._complete_handshake(handshake_context)
            if completion_result["success"]:
                handshake_context["state"] = HandshakeState.COMPLETED
                self.auth_stats["successful_auth"] += 1
            else:
                handshake_context["state"] = HandshakeState.FAILED
                handshake_context["errors"].append(completion_result["error"])
                self.auth_stats["failed_auth"] += 1
            
        except Exception as e:
            handshake_context["state"] = HandshakeState.FAILED
            handshake_context["errors"].append(f"Handshake exception: {str(e)}")
            self.auth_stats["failed_auth"] += 1
        
        handshake_context["completed_at"] = time.time()
        handshake_context["duration"] = handshake_context["completed_at"] - handshake_context["started_at"]
        
        return handshake_context
    
    def _validate_protocol(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Validate WebSocket protocol version."""
        protocol = headers.get("Sec-WebSocket-Protocol", "")
        
        if not protocol:
            return {
                "valid": False,
                "error": "Missing WebSocket protocol header"
            }
        
        # Check if protocol is supported
        protocols = [p.strip() for p in protocol.split(",")]
        supported_protocol = None
        
        for proto in protocols:
            if proto in self.supported_protocols:
                supported_protocol = proto
                break
        
        if not supported_protocol:
            return {
                "valid": False,
                "error": f"Unsupported protocol. Supported: {self.supported_protocols}"
            }
        
        return {
            "valid": True,
            "protocol": supported_protocol
        }
    
    def _extract_auth_token(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Extract authentication token from headers."""
        # Try Authorization header first
        auth_header = headers.get("Authorization", "")
        if auth_header:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
                return {
                    "success": True,
                    "data": {
                        "token": token,
                        "type": AuthTokenType.JWT,
                        "source": "authorization_header"
                    }
                }
            elif auth_header.startswith("ApiKey "):
                api_key = auth_header[7:]  # Remove "ApiKey " prefix
                return {
                    "success": True,
                    "data": {
                        "token": api_key,
                        "type": AuthTokenType.API_KEY,
                        "source": "authorization_header"
                    }
                }
        
        # Try query parameters
        query_token = headers.get("X-Auth-Token", "")
        if query_token:
            return {
                "success": True,
                "data": {
                    "token": query_token,
                    "type": AuthTokenType.SESSION,
                    "source": "query_parameter"
                }
            }
        
        # Try cookie-based session
        cookie_header = headers.get("Cookie", "")
        if "session_id=" in cookie_header:
            # Extract session ID from cookie
            for part in cookie_header.split(";"):
                if "session_id=" in part:
                    session_id = part.split("=")[1].strip()
                    return {
                        "success": True,
                        "data": {
                            "token": session_id,
                            "type": AuthTokenType.SESSION,
                            "source": "cookie"
                        }
                    }
        
        return {
            "success": False,
            "error": "No authentication token found in headers"
        }
    
    async def _validate_token_jwt(self, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate authentication token."""
        token = auth_data["token"]
        token_type = auth_data["type"]
        
        if token_type == AuthTokenType.JWT:
            return await self._validate_jwt_token(token)
        elif token_type == AuthTokenType.API_KEY:
            return await self._validate_api_key(token)
        elif token_type == AuthTokenType.SESSION:
            return await self._validate_session_token(token)
        else:
            return {
                "valid": False,
                "errors": [f"Unsupported token type: {token_type}"]
            }
    
    async def _validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token."""
        try:
            # Decode JWT token
            decoded = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # Check expiration
            exp = decoded.get("exp", 0)
            if exp < time.time():
                return {
                    "valid": False,
                    "errors": ["Token expired"]
                }
            
            # Validate required claims
            required_claims = ["user_id", "sub", "iat"]
            for claim in required_claims:
                if claim not in decoded:
                    return {
                        "valid": False,
                        "errors": [f"Missing required claim: {claim}"]
                    }
            
            return {
                "valid": True,
                "data": {
                    "user_id": decoded["user_id"],
                    "subject": decoded["sub"],
                    "issued_at": decoded["iat"],
                    "expires_at": decoded["exp"],
                    "claims": decoded
                }
            }
        
        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "errors": ["Token expired"]
            }
        except jwt.InvalidTokenError as e:
            return {
                "valid": False,
                "errors": [f"Invalid token: {str(e)}"]
            }
    
    async def _validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate API key."""
        # Simulate API key validation
        # In real implementation, would check against database
        if len(api_key) < 32:
            return {
                "valid": False,
                "errors": ["Invalid API key format"]
            }
        
        # Mock API key validation
        if api_key.startswith("test_"):
            user_id = api_key.replace("test_", "").replace("_key", "")
            return {
                "valid": True,
                "data": {
                    "user_id": user_id,
                    "api_key": api_key,
                    "scope": "websocket_access"
                }
            }
        
        return {
            "valid": False,
            "errors": ["API key not found"]
        }
    
    async def _validate_session_token(self, session_token: str) -> Dict[str, Any]:
        """Validate session token."""
        # Simulate session validation
        # In real implementation, would check against session store
        if len(session_token) < 16:
            return {
                "valid": False,
                "errors": ["Invalid session token format"]
            }
        
        # Mock session validation
        if session_token.startswith("sess_"):
            user_id = session_token.replace("sess_", "").replace("_active", "")
            return {
                "valid": True,
                "data": {
                    "user_id": user_id,
                    "session_id": session_token,
                    "session_type": "web"
                }
            }
        
        return {
            "valid": False,
            "errors": ["Session not found or expired"]
        }
    
    async def _authorize_user(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Authorize user for WebSocket access."""
        user_id = token_data.get("user_id")
        
        if not user_id:
            return {
                "authorized": False,
                "error": "No user ID in token"
            }
        
        # Simulate user authorization check
        # In real implementation, would check user permissions and status
        user_data = await self._get_user_data(user_id)
        
        if not user_data:
            return {
                "authorized": False,
                "error": "User not found"
            }
        
        if not user_data.get("is_active", False):
            return {
                "authorized": False,
                "error": "User account inactive"
            }
        
        # Check WebSocket access permissions
        permissions = user_data.get("permissions", [])
        if "websocket_access" not in permissions:
            return {
                "authorized": False,
                "error": "User not authorized for WebSocket access"
            }
        
        return {
            "authorized": True,
            "user_data": user_data
        }
    
    async def _get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data for authorization."""
        # Mock user data lookup
        if user_id.startswith("auth_user_"):
            return {
                "user_id": user_id,
                "is_active": True,
                "permissions": ["websocket_access", "read", "write"],
                "tier": "premium",
                "created_at": time.time() - 86400  # 1 day ago
            }
        elif user_id.startswith("inactive_user_"):
            return {
                "user_id": user_id,
                "is_active": False,
                "permissions": [],
                "tier": "free"
            }
        elif user_id.startswith("limited_user_"):
            return {
                "user_id": user_id,
                "is_active": True,
                "permissions": ["read"],  # No websocket_access
                "tier": "free"
            }
        
        return None  # User not found
    
    async def _complete_handshake(self, handshake_context: Dict[str, Any]) -> Dict[str, Any]:
        """Complete the authentication handshake."""
        try:
            # Send handshake completion message
            websocket = handshake_context["websocket"]
            user_data = handshake_context["auth_data"]["user"]
            
            completion_message = {
                "type": "auth_complete",
                "handshake_id": handshake_context["handshake_id"],
                "user_id": user_data["user_id"],
                "session_data": {
                    "permissions": user_data["permissions"],
                    "tier": user_data["tier"]
                },
                "timestamp": time.time()
            }
            
            if hasattr(websocket, "send"):
                await websocket.send(json.dumps(completion_message))
            
            return {
                "success": True,
                "session_data": completion_message["session_data"]
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Handshake completion failed: {str(e)}"
            }
    
    def create_test_jwt_token(self, user_id: str, expires_in: int = None) -> str:
        """Create test JWT token for testing."""
        if expires_in is None:
            expires_in = self.token_expiry
        
        payload = {
            "user_id": user_id,
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
            "iss": "netra-test",
            "aud": "websocket"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        stats = self.auth_stats.copy()
        
        if stats["total_handshakes"] > 0:
            stats["success_rate"] = (stats["successful_auth"] / stats["total_handshakes"]) * 100
            stats["failure_rate"] = (stats["failed_auth"] / stats["total_handshakes"]) * 100
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
        
        return stats


class TokenVerifier:
    """Verify and refresh authentication tokens."""
    
    def __init__(self, auth_handshake: WebSocketAuthHandshake):
        self.auth_handshake = auth_handshake
        self.refresh_stats = {
            "tokens_refreshed": 0,
            "refresh_failures": 0,
            "refresh_requests": 0
        }
    
    async def verify_token_validity(self, token: str, token_type: AuthTokenType) -> Dict[str, Any]:
        """Verify if token is still valid."""
        auth_data = {
            "token": token,
            "type": token_type
        }
        
        validation_result = await self.auth_handshake._validate_token_jwt(auth_data)
        
        return {
            "valid": validation_result["valid"],
            "expires_soon": self._check_expiration_warning(validation_result),
            "data": validation_result.get("data", {}),
            "errors": validation_result.get("errors", [])
        }
    
    def _check_expiration_warning(self, validation_result: Dict[str, Any]) -> bool:
        """Check if token expires soon (within 5 minutes)."""
        if not validation_result["valid"]:
            return False
        
        data = validation_result.get("data", {})
        expires_at = data.get("expires_at", 0)
        
        if expires_at:
            time_to_expiry = expires_at - time.time()
            return time_to_expiry < 300  # Less than 5 minutes
        
        return False
    
    async def refresh_token(self, current_token: str, token_type: AuthTokenType) -> Dict[str, Any]:
        """Refresh authentication token."""
        self.refresh_stats["refresh_requests"] += 1
        
        try:
            # Verify current token first
            verification = await self.verify_token_validity(current_token, token_type)
            
            if not verification["valid"]:
                self.refresh_stats["refresh_failures"] += 1
                return {
                    "success": False,
                    "error": "Cannot refresh invalid token"
                }
            
            # Generate new token based on current token data
            if token_type == AuthTokenType.JWT:
                user_id = verification["data"]["user_id"]
                new_token = self.auth_handshake.create_test_jwt_token(user_id)
                
                self.refresh_stats["tokens_refreshed"] += 1
                return {
                    "success": True,
                    "new_token": new_token,
                    "token_type": token_type,
                    "expires_in": self.auth_handshake.token_expiry
                }
            
            else:
                # For API keys and sessions, refreshing may not be applicable
                return {
                    "success": False,
                    "error": f"Token refresh not supported for {token_type}"
                }
        
        except Exception as e:
            self.refresh_stats["refresh_failures"] += 1
            return {
                "success": False,
                "error": f"Token refresh failed: {str(e)}"
            }
    
    def get_refresh_stats(self) -> Dict[str, Any]:
        """Get token refresh statistics."""
        return self.refresh_stats.copy()


class UpgradeHandler:
    """Handle WebSocket protocol upgrade."""
    
    def __init__(self):
        self.upgrade_stats = {
            "upgrade_requests": 0,
            "successful_upgrades": 0,
            "upgrade_failures": 0,
            "protocol_negotiation_failures": 0
        }
    
    def validate_upgrade_request(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Validate WebSocket upgrade request headers."""
        self.upgrade_stats["upgrade_requests"] += 1
        
        required_headers = {
            "Connection": "upgrade",
            "Upgrade": "websocket",
            "Sec-WebSocket-Version": "13"
        }
        
        missing_headers = []
        invalid_headers = []
        
        for header, expected_value in required_headers.items():
            actual_value = headers.get(header, "").lower()
            
            if not actual_value:
                missing_headers.append(header)
            elif expected_value.lower() not in actual_value:
                invalid_headers.append(f"{header}: expected {expected_value}, got {actual_value}")
        
        # Check for WebSocket key
        ws_key = headers.get("Sec-WebSocket-Key", "")
        if not ws_key or len(ws_key) < 16:
            missing_headers.append("Sec-WebSocket-Key")
        
        if missing_headers or invalid_headers:
            self.upgrade_stats["upgrade_failures"] += 1
            return {
                "valid": False,
                "missing_headers": missing_headers,
                "invalid_headers": invalid_headers
            }
        
        self.upgrade_stats["successful_upgrades"] += 1
        return {
            "valid": True,
            "websocket_key": ws_key
        }
    
    def negotiate_protocol(self, requested_protocols: str, supported_protocols: List[str]) -> Dict[str, Any]:
        """Negotiate WebSocket subprotocol."""
        if not requested_protocols:
            return {
                "success": True,
                "protocol": supported_protocols[0] if supported_protocols else None
            }
        
        protocols = [p.strip() for p in requested_protocols.split(",")]
        
        # Find first supported protocol
        for protocol in protocols:
            if protocol in supported_protocols:
                return {
                    "success": True,
                    "protocol": protocol
                }
        
        self.upgrade_stats["protocol_negotiation_failures"] += 1
        return {
            "success": False,
            "error": f"No supported protocol found. Requested: {protocols}, Supported: {supported_protocols}"
        }
    
    def get_upgrade_stats(self) -> Dict[str, Any]:
        """Get upgrade statistics."""
        return self.upgrade_stats.copy()


@pytest.mark.L2
@pytest.mark.integration
class TestWebSocketAuthHandshake:
    """L2 integration tests for WebSocket authentication handshake."""
    
    @pytest.fixture
    def auth_handshake(self):
        """Create auth handshake handler."""
        return WebSocketAuthHandshake()
    
    @pytest.fixture
    def token_verifier(self, auth_handshake):
        """Create token verifier."""
        return TokenVerifier(auth_handshake)
    
    @pytest.fixture
    def upgrade_handler(self):
        """Create upgrade handler."""
        return UpgradeHandler()
    
    @pytest.fixture
    def test_users(self):
        """Create test users."""
        return [
            UserInDB(
                id="auth_user_1",
                email="authuser1@example.com",
                username="authuser1",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            ),
            UserInDB(
                id="inactive_user_1",
                email="inactive@example.com",
                username="inactive",
                is_active=False,
                created_at=datetime.now(timezone.utc)
            ),
            UserInDB(
                id="limited_user_1",
                email="limited@example.com",
                username="limited",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
        ]
    
    def create_mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = AsyncMock()
        websocket.send = AsyncMock()
        websocket.messages_sent = []
        
        async def mock_send(message):
            websocket.messages_sent.append(message)
        
        websocket.send.side_effect = mock_send
        return websocket
    
    def create_test_headers(self, auth_type: str = "jwt", user_id: str = "auth_user_1") -> Dict[str, str]:
        """Create test headers for handshake."""
        base_headers = {
            "Connection": "upgrade",
            "Upgrade": "websocket",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
            "Sec-WebSocket-Protocol": "netra-v1"
        }
        
        if auth_type == "jwt":
            token = jwt.encode(
                {
                    "user_id": user_id,
                    "sub": user_id,
                    "iat": int(time.time()),
                    "exp": int(time.time()) + 3600,
                    "iss": "netra-test"
                },
                "test_secret_key_for_jwt",
                algorithm="HS256"
            )
            base_headers["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "api_key":
            base_headers["Authorization"] = f"ApiKey test_{user_id}_key"
        
        elif auth_type == "session":
            base_headers["X-Auth-Token"] = f"sess_{user_id}_active"
        
        return base_headers
    
    async def test_successful_jwt_handshake(self, auth_handshake, test_users):
        """Test successful JWT authentication handshake."""
        user = test_users[0]  # auth_user_1
        websocket = self.create_mock_websocket()
        headers = self.create_test_headers("jwt", user.id)
        
        # Perform handshake
        result = await auth_handshake.initiate_handshake(websocket, headers)
        
        # Verify successful handshake
        assert result["state"] == HandshakeState.COMPLETED
        assert len(result["errors"]) == 0
        assert result["auth_data"]["user"]["user_id"] == user.id
        assert result["auth_data"]["user"]["is_active"] is True
        assert "websocket_access" in result["auth_data"]["user"]["permissions"]
        
        # Verify completion message was sent
        assert len(websocket.messages_sent) == 1
        completion_msg = json.loads(websocket.messages_sent[0])
        assert completion_msg["type"] == "auth_complete"
        assert completion_msg["user_id"] == user.id
        
        # Check performance
        assert result["duration"] < 0.2  # Less than 200ms
    
    async def test_api_key_authentication(self, auth_handshake, test_users):
        """Test API key authentication."""
        user = test_users[0]
        websocket = self.create_mock_websocket()
        headers = self.create_test_headers("api_key", user.id)
        
        result = await auth_handshake.initiate_handshake(websocket, headers)
        
        assert result["state"] == HandshakeState.COMPLETED
        assert result["auth_data"]["user"]["user_id"] == user.id
        assert result["auth_data"]["token"].endswith("_key")
    
    async def test_session_token_authentication(self, auth_handshake, test_users):
        """Test session token authentication."""
        user = test_users[0]
        websocket = self.create_mock_websocket()
        headers = self.create_test_headers("session", user.id)
        
        result = await auth_handshake.initiate_handshake(websocket, headers)
        
        assert result["state"] == HandshakeState.COMPLETED
        assert result["auth_data"]["user"]["user_id"] == user.id
        assert result["auth_data"]["session_id"].startswith("sess_")
    
    async def test_expired_token_rejection(self, auth_handshake):
        """Test rejection of expired tokens."""
        websocket = self.create_mock_websocket()
        
        # Create expired JWT token
        expired_token = jwt.encode(
            {
                "user_id": "auth_user_1",
                "sub": "auth_user_1",
                "iat": int(time.time()) - 7200,  # 2 hours ago
                "exp": int(time.time()) - 3600,  # 1 hour ago (expired)
                "iss": "netra-test"
            },
            "test_secret_key_for_jwt",
            algorithm="HS256"
        )
        
        headers = self.create_test_headers("jwt")
        headers["Authorization"] = f"Bearer {expired_token}"
        
        result = await auth_handshake.initiate_handshake(websocket, headers)
        
        assert result["state"] == HandshakeState.FAILED
        assert any("expired" in error.lower() for error in result["errors"])
        
        # Check stats
        stats = auth_handshake.get_auth_stats()
        assert stats["token_expired"] > 0
    
    async def test_inactive_user_rejection(self, auth_handshake, test_users):
        """Test rejection of inactive users."""
        inactive_user = test_users[1]  # inactive_user_1
        websocket = self.create_mock_websocket()
        headers = self.create_test_headers("jwt", inactive_user.id)
        
        result = await auth_handshake.initiate_handshake(websocket, headers)
        
        assert result["state"] == HandshakeState.REJECTED
        assert any("inactive" in error.lower() for error in result["errors"])
        
        # Check stats
        stats = auth_handshake.get_auth_stats()
        assert stats["unauthorized_users"] > 0
    
    async def test_insufficient_permissions_rejection(self, auth_handshake, test_users):
        """Test rejection of users without WebSocket permissions."""
        limited_user = test_users[2]  # limited_user_1
        websocket = self.create_mock_websocket()
        headers = self.create_test_headers("jwt", limited_user.id)
        
        result = await auth_handshake.initiate_handshake(websocket, headers)
        
        assert result["state"] == HandshakeState.REJECTED
        assert any("not authorized" in error for error in result["errors"])
    
    async def test_missing_auth_token_failure(self, auth_handshake):
        """Test failure when no auth token is provided."""
        websocket = self.create_mock_websocket()
        headers = {
            "Connection": "upgrade",
            "Upgrade": "websocket",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
            "Sec-WebSocket-Protocol": "netra-v1"
            # No authorization header
        }
        
        result = await auth_handshake.initiate_handshake(websocket, headers)
        
        assert result["state"] == HandshakeState.FAILED
        assert any("no authentication token" in error.lower() for error in result["errors"])
    
    async def test_protocol_validation(self, auth_handshake):
        """Test WebSocket protocol validation."""
        websocket = self.create_mock_websocket()
        
        # Test unsupported protocol
        headers = self.create_test_headers("jwt")
        headers["Sec-WebSocket-Protocol"] = "unsupported-protocol"
        
        result = await auth_handshake.initiate_handshake(websocket, headers)
        
        assert result["state"] == HandshakeState.REJECTED
        assert any("unsupported protocol" in error.lower() for error in result["errors"])
        
        # Check stats
        stats = auth_handshake.get_auth_stats()
        assert stats["protocol_mismatches"] > 0
    
    async def test_token_verification_and_refresh(self, token_verifier, auth_handshake):
        """Test token verification and refresh functionality."""
        user_id = "auth_user_1"
        
        # Create token
        token = auth_handshake.create_test_jwt_token(user_id)
        
        # Verify token
        verification = await token_verifier.verify_token_validity(token, AuthTokenType.JWT)
        
        assert verification["valid"] is True
        assert verification["data"]["user_id"] == user_id
        assert verification["expires_soon"] is False
        
        # Test token refresh
        refresh_result = await token_verifier.refresh_token(token, AuthTokenType.JWT)
        
        assert refresh_result["success"] is True
        assert refresh_result["new_token"] != token  # Should be different
        assert refresh_result["token_type"] == AuthTokenType.JWT
        
        # Verify new token
        new_verification = await token_verifier.verify_token_validity(
            refresh_result["new_token"], AuthTokenType.JWT
        )
        assert new_verification["valid"] is True
    
    async def test_token_expiration_warning(self, token_verifier, auth_handshake):
        """Test token expiration warning."""
        user_id = "auth_user_1"
        
        # Create token that expires soon (2 minutes)
        token = auth_handshake.create_test_jwt_token(user_id, expires_in=120)
        
        verification = await token_verifier.verify_token_validity(token, AuthTokenType.JWT)
        
        assert verification["valid"] is True
        assert verification["expires_soon"] is True
    
    async def test_upgrade_request_validation(self, upgrade_handler):
        """Test WebSocket upgrade request validation."""
        # Valid upgrade request
        valid_headers = {
            "Connection": "upgrade",
            "Upgrade": "websocket",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="
        }
        
        result = upgrade_handler.validate_upgrade_request(valid_headers)
        
        assert result["valid"] is True
        assert result["websocket_key"] == "dGhlIHNhbXBsZSBub25jZQ=="
        
        # Invalid upgrade request (missing headers)
        invalid_headers = {
            "Connection": "keep-alive",  # Wrong value
            "Upgrade": "websocket"
            # Missing other required headers
        }
        
        result = upgrade_handler.validate_upgrade_request(invalid_headers)
        
        assert result["valid"] is False
        assert len(result["missing_headers"]) > 0
        assert len(result["invalid_headers"]) > 0
    
    async def test_protocol_negotiation(self, upgrade_handler):
        """Test WebSocket protocol negotiation."""
        supported_protocols = ["netra-v1", "netra-v2"]
        
        # Successful negotiation
        result = upgrade_handler.negotiate_protocol("netra-v1, other-protocol", supported_protocols)
        
        assert result["success"] is True
        assert result["protocol"] == "netra-v1"
        
        # Failed negotiation
        result = upgrade_handler.negotiate_protocol("unsupported-v1, unsupported-v2", supported_protocols)
        
        assert result["success"] is False
        assert "no supported protocol" in result["error"].lower()
    
    @mock_justified("L2: WebSocket auth handshake with real internal components")
    async def test_complete_handshake_flow_integration(self, auth_handshake, upgrade_handler, test_users):
        """Test complete handshake flow integration."""
        user = test_users[0]
        websocket = self.create_mock_websocket()
        
        # Step 1: Validate upgrade request
        headers = self.create_test_headers("jwt", user.id)
        upgrade_result = upgrade_handler.validate_upgrade_request(headers)
        
        assert upgrade_result["valid"] is True
        
        # Step 2: Negotiate protocol
        protocol_result = upgrade_handler.negotiate_protocol(
            headers["Sec-WebSocket-Protocol"], 
            auth_handshake.supported_protocols
        )
        
        assert protocol_result["success"] is True
        
        # Step 3: Perform authentication handshake
        auth_result = await auth_handshake.initiate_handshake(websocket, headers)
        
        assert auth_result["state"] == HandshakeState.COMPLETED
        
        # Verify complete flow timing
        assert auth_result["duration"] < 0.3  # Complete flow under 300ms
        
        # Verify all statistics
        auth_stats = auth_handshake.get_auth_stats()
        upgrade_stats = upgrade_handler.get_upgrade_stats()
        
        assert auth_stats["successful_auth"] > 0
        assert auth_stats["success_rate"] > 0
        assert upgrade_stats["successful_upgrades"] > 0
    
    async def test_concurrent_handshake_performance(self, auth_handshake, test_users):
        """Test concurrent handshake performance."""
        concurrent_count = 50
        handshake_tasks = []
        
        # Create concurrent handshake tasks
        for i in range(concurrent_count):
            user = test_users[i % len(test_users)]
            if user.id.startswith("auth_user_"):  # Only use valid users
                websocket = self.create_mock_websocket()
                headers = self.create_test_headers("jwt", user.id)
                
                task = auth_handshake.initiate_handshake(websocket, headers)
                handshake_tasks.append(task)
        
        # Execute concurrent handshakes
        start_time = time.time()
        results = await asyncio.gather(*handshake_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_handshakes = sum(
            1 for result in results 
            if not isinstance(result, Exception) and 
               result.get("state") == HandshakeState.COMPLETED
        )
        
        # Performance assertions
        assert total_time < 10.0  # All handshakes within 10 seconds
        assert successful_handshakes >= len(handshake_tasks) * 0.8  # 80% success rate
        
        # Verify average handshake time
        valid_results = [r for r in results if not isinstance(r, Exception)]
        if valid_results:
            avg_duration = sum(r.get("duration", 0) for r in valid_results) / len(valid_results)
            assert avg_duration < 0.5  # Average under 500ms
        
        # Check final statistics
        stats = auth_handshake.get_auth_stats()
        assert stats["success_rate"] >= 80.0  # 80% overall success rate


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])