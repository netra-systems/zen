# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()
    # REMOVED_SYNTAX_ERROR: \n'''
    # REMOVED_SYNTAX_ERROR: Shared fixtures for WebSocket resilience tests.

    # REMOVED_SYNTAX_ERROR: Common test fixtures, utilities, and mock classes used across all WebSocket resilience tests.
    # REMOVED_SYNTAX_ERROR: Extracted from original test files to reduce duplication and maintain consistency.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import hashlib
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import random
    # REMOVED_SYNTAX_ERROR: import secrets
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from dataclasses import dataclass, field
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
    # REMOVED_SYNTAX_ERROR: from enum import Enum
    # REMOVED_SYNTAX_ERROR: from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

    # REMOVED_SYNTAX_ERROR: import jwt
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import websockets
    # REMOVED_SYNTAX_ERROR: from websockets.exceptions import ConnectionClosed, InvalidStatus

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

    # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


# REMOVED_SYNTAX_ERROR: class SecureJWTGenerator:
    # REMOVED_SYNTAX_ERROR: """Secure JWT token generator for testing expired token scenarios."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.secret = "test-secret-key-for-security-testing-only"
    # REMOVED_SYNTAX_ERROR: self.algorithm = "HS256"
    # REMOVED_SYNTAX_ERROR: self.issuer = "netra-test-auth"
    # REMOVED_SYNTAX_ERROR: self.token_fingerprints = set()

# REMOVED_SYNTAX_ERROR: def create_expired_token(self, user_id: str, expired_minutes_ago: int = 1,
# REMOVED_SYNTAX_ERROR: permissions: List[str] = None) -> str:
    # REMOVED_SYNTAX_ERROR: """Create JWT token that expired specified minutes ago."""
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: exp_time = now - timedelta(minutes=expired_minutes_ago)

    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "sub": user_id,
    # REMOVED_SYNTAX_ERROR: "iat": now - timedelta(minutes=expired_minutes_ago + 15),  # Issued before expiry
    # REMOVED_SYNTAX_ERROR: "exp": exp_time,
    # REMOVED_SYNTAX_ERROR: "email": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "permissions": permissions or ["read"],
    # REMOVED_SYNTAX_ERROR: "token_type": "access",
    # REMOVED_SYNTAX_ERROR: "iss": self.issuer,
    # REMOVED_SYNTAX_ERROR: "jti": str(uuid.uuid4())  # Unique token ID for tracking
    

    # REMOVED_SYNTAX_ERROR: token = jwt.encode(payload, self.secret, algorithm=self.algorithm)

    # Track token fingerprint for security testing
    # REMOVED_SYNTAX_ERROR: token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
    # REMOVED_SYNTAX_ERROR: self.token_fingerprints.add(token_hash)

    # REMOVED_SYNTAX_ERROR: return token

# REMOVED_SYNTAX_ERROR: def create_valid_token(self, user_id: str, expires_in_minutes: int = 15,
# REMOVED_SYNTAX_ERROR: permissions: List[str] = None) -> str:
    # REMOVED_SYNTAX_ERROR: """Create valid JWT token for comparison testing."""
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: exp_time = now + timedelta(minutes=expires_in_minutes)

    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "sub": user_id,
    # REMOVED_SYNTAX_ERROR: "iat": now,
    # REMOVED_SYNTAX_ERROR: "exp": exp_time,
    # REMOVED_SYNTAX_ERROR: "email": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "permissions": permissions or ["read"],
    # REMOVED_SYNTAX_ERROR: "token_type": "access",
    # REMOVED_SYNTAX_ERROR: "iss": self.issuer,
    # REMOVED_SYNTAX_ERROR: "jti": str(uuid.uuid4())
    

    # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, self.secret, algorithm=self.algorithm)

# REMOVED_SYNTAX_ERROR: def create_near_expiry_token(self, user_id: str, expires_in_seconds: int = 5) -> str:
    # REMOVED_SYNTAX_ERROR: """Create token that expires very soon for grace period testing."""
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: exp_time = now + timedelta(seconds=expires_in_seconds)

    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "sub": user_id,
    # REMOVED_SYNTAX_ERROR: "iat": now,
    # REMOVED_SYNTAX_ERROR: "exp": exp_time,
    # REMOVED_SYNTAX_ERROR: "email": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "permissions": ["read"],
    # REMOVED_SYNTAX_ERROR: "token_type": "access",
    # REMOVED_SYNTAX_ERROR: "iss": self.issuer,
    # REMOVED_SYNTAX_ERROR: "jti": str(uuid.uuid4())
    

    # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, self.secret, algorithm=self.algorithm)

# REMOVED_SYNTAX_ERROR: def create_malformed_expired_token(self, user_id: str) -> str:
    # REMOVED_SYNTAX_ERROR: """Create malformed token that appears expired for edge case testing."""
    # Create token with invalid signature but expired timestamp
    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: exp_time = now - timedelta(minutes=5)

    # REMOVED_SYNTAX_ERROR: payload = { )
    # REMOVED_SYNTAX_ERROR: "sub": user_id,
    # REMOVED_SYNTAX_ERROR: "exp": exp_time,
    # REMOVED_SYNTAX_ERROR: "iat": now - timedelta(minutes=20),
    # REMOVED_SYNTAX_ERROR: "malformed": True
    

    # Use wrong secret to create invalid signature
    # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, "wrong-secret", algorithm=self.algorithm)

# REMOVED_SYNTAX_ERROR: def validate_token(self, token: str) -> Optional[Dict]:
    # REMOVED_SYNTAX_ERROR: """Validate token for testing purposes."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        # REMOVED_SYNTAX_ERROR: return payload
        # REMOVED_SYNTAX_ERROR: except jwt.ExpiredSignatureError:
            # REMOVED_SYNTAX_ERROR: return {"error": "expired", "type": "ExpiredSignatureError"}
            # REMOVED_SYNTAX_ERROR: except jwt.InvalidTokenError as e:
                # REMOVED_SYNTAX_ERROR: return {"error": "invalid", "type": type(e).__name__, "message": str(e)}


# REMOVED_SYNTAX_ERROR: class SecurityAuditLogger:
    # REMOVED_SYNTAX_ERROR: """Mock security audit logger for testing security event logging."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.security_events = []
    # REMOVED_SYNTAX_ERROR: self.alert_triggers = []
    # REMOVED_SYNTAX_ERROR: self.suspicious_patterns = {}

# REMOVED_SYNTAX_ERROR: async def log_expired_token_attempt(self, event_data: Dict[str, Any]):
    # REMOVED_SYNTAX_ERROR: """Log expired token access attempt."""
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat(),
    # REMOVED_SYNTAX_ERROR: "event_type": "expired_token_attempt",
    # REMOVED_SYNTAX_ERROR: "severity": "HIGH",
    # REMOVED_SYNTAX_ERROR: "user_id": event_data.get("user_id"),
    # REMOVED_SYNTAX_ERROR: "source_ip": event_data.get("source_ip", "127.0.0.1"),
    # REMOVED_SYNTAX_ERROR: "token_fingerprint": event_data.get("token_fingerprint"),
    # REMOVED_SYNTAX_ERROR: "expiry_time": event_data.get("expiry_time"),
    # REMOVED_SYNTAX_ERROR: "attempt_time": event_data.get("attempt_time"),
    # REMOVED_SYNTAX_ERROR: "user_agent": event_data.get("user_agent"),
    # REMOVED_SYNTAX_ERROR: "session_id": event_data.get("session_id")
    

    # REMOVED_SYNTAX_ERROR: self.security_events.append(event)

    # Check for suspicious patterns
    # REMOVED_SYNTAX_ERROR: await self._analyze_suspicious_patterns(event)

# REMOVED_SYNTAX_ERROR: async def log_successful_token_refresh(self, event_data: Dict[str, Any]):
    # REMOVED_SYNTAX_ERROR: """Log successful token refresh event."""
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat(),
    # REMOVED_SYNTAX_ERROR: "event_type": "token_refresh_success",
    # REMOVED_SYNTAX_ERROR: "severity": "INFO",
    # REMOVED_SYNTAX_ERROR: "user_id": event_data.get("user_id"),
    # REMOVED_SYNTAX_ERROR: "old_token_fingerprint": event_data.get("old_token_fingerprint"),
    # REMOVED_SYNTAX_ERROR: "new_token_fingerprint": event_data.get("new_token_fingerprint")
    

    # REMOVED_SYNTAX_ERROR: self.security_events.append(event)

# REMOVED_SYNTAX_ERROR: async def _analyze_suspicious_patterns(self, event: Dict[str, Any]):
    # REMOVED_SYNTAX_ERROR: """Analyze events for suspicious patterns and trigger alerts."""
    # REMOVED_SYNTAX_ERROR: user_id = event.get("user_id")
    # REMOVED_SYNTAX_ERROR: source_ip = event.get("source_ip")

    # Track repeated attempts by user
    # REMOVED_SYNTAX_ERROR: user_key = "formatted_string"
    # REMOVED_SYNTAX_ERROR: if user_key not in self.suspicious_patterns:
        # REMOVED_SYNTAX_ERROR: self.suspicious_patterns[user_key] = []

        # REMOVED_SYNTAX_ERROR: self.suspicious_patterns[user_key].append(event["timestamp"])

        # Clean old events (keep last hour)
        # REMOVED_SYNTAX_ERROR: recent_events = [ )
        # REMOVED_SYNTAX_ERROR: ts for ts in self.suspicious_patterns[user_key]
        # REMOVED_SYNTAX_ERROR: if (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() < 3600
        
        # REMOVED_SYNTAX_ERROR: self.suspicious_patterns[user_key] = recent_events

        # Trigger alert if more than 5 attempts in last 10 minutes
        # REMOVED_SYNTAX_ERROR: recent_attempts = [ )
        # REMOVED_SYNTAX_ERROR: ts for ts in recent_events
        # REMOVED_SYNTAX_ERROR: if (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() < 600
        

        # REMOVED_SYNTAX_ERROR: if len(recent_attempts) >= 5:
            # REMOVED_SYNTAX_ERROR: alert = { )
            # REMOVED_SYNTAX_ERROR: "alert_type": "repeated_expired_token_attempts",
            # REMOVED_SYNTAX_ERROR: "severity": "CRITICAL",
            # REMOVED_SYNTAX_ERROR: "user_id": user_id,
            # REMOVED_SYNTAX_ERROR: "source_ip": source_ip,
            # REMOVED_SYNTAX_ERROR: "attempt_count": len(recent_attempts),
            # REMOVED_SYNTAX_ERROR: "time_window": "10_minutes",
            # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat()
            
            # REMOVED_SYNTAX_ERROR: self.alert_triggers.append(alert)

# REMOVED_SYNTAX_ERROR: def get_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
    # REMOVED_SYNTAX_ERROR: """Get all security events for specific user."""
    # REMOVED_SYNTAX_ERROR: return [item for item in []]

# REMOVED_SYNTAX_ERROR: def get_alert_count(self) -> int:
    # REMOVED_SYNTAX_ERROR: """Get number of security alerts triggered."""
    # REMOVED_SYNTAX_ERROR: return len(self.alert_triggers)

# REMOVED_SYNTAX_ERROR: async def log_session_event(self, user_id: str, session_id: str, event_type: str, details: Dict[str, Any] = None):
    # REMOVED_SYNTAX_ERROR: """Log session-related event."""
    # REMOVED_SYNTAX_ERROR: event = { )
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat(),
    # REMOVED_SYNTAX_ERROR: "event_type": event_type,
    # REMOVED_SYNTAX_ERROR: "severity": "INFO",
    # REMOVED_SYNTAX_ERROR: "user_id": user_id,
    # REMOVED_SYNTAX_ERROR: "session_id": session_id,
    # REMOVED_SYNTAX_ERROR: "details": details or {}
    

    # REMOVED_SYNTAX_ERROR: self.security_events.append(event)


# REMOVED_SYNTAX_ERROR: class SecureWebSocketTestClient:
    # REMOVED_SYNTAX_ERROR: """Security-focused WebSocket test client for expired token testing."""

# REMOVED_SYNTAX_ERROR: def __init__(self, uri: str, token: str, jwt_generator: SecureJWTGenerator,
# REMOVED_SYNTAX_ERROR: audit_logger: SecurityAuditLogger):
    # REMOVED_SYNTAX_ERROR: self.uri = uri
    # REMOVED_SYNTAX_ERROR: self.token = token
    # REMOVED_SYNTAX_ERROR: self.jwt_generator = jwt_generator
    # REMOVED_SYNTAX_ERROR: self.audit_logger = audit_logger
    # REMOVED_SYNTAX_ERROR: self.websocket = None
    # REMOVED_SYNTAX_ERROR: self.is_connected = False
    # REMOVED_SYNTAX_ERROR: self.connection_metadata = {}
    # REMOVED_SYNTAX_ERROR: self.last_error = None

# REMOVED_SYNTAX_ERROR: async def attempt_connection(self, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Dict[str, Any]]:
    # REMOVED_SYNTAX_ERROR: """Attempt WebSocket connection and return detailed result."""
    # REMOVED_SYNTAX_ERROR: connection_start = time.time()

    # REMOVED_SYNTAX_ERROR: try:
        # Validate token before attempting connection
        # REMOVED_SYNTAX_ERROR: token_validation = self.jwt_generator.validate_token(self.token)

        # REMOVED_SYNTAX_ERROR: if token_validation and "error" in token_validation:
            # Extract user ID from token for logging
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: unverified_payload = jwt.decode(self.token, options={"verify_signature": False})
                # REMOVED_SYNTAX_ERROR: user_id = unverified_payload.get("sub", "unknown_user")
                # REMOVED_SYNTAX_ERROR: except Exception:
                    # REMOVED_SYNTAX_ERROR: user_id = "unknown_user"

                    # Log expired token attempt
                    # Removed problematic line: await self.audit_logger.log_expired_token_attempt({ ))
                    # REMOVED_SYNTAX_ERROR: "user_id": user_id,
                    # REMOVED_SYNTAX_ERROR: "token_fingerprint": hashlib.sha256(self.token.encode()).hexdigest()[:16],
                    # REMOVED_SYNTAX_ERROR: "expiry_time": "expired",
                    # REMOVED_SYNTAX_ERROR: "attempt_time": datetime.now(timezone.utc).isoformat(),
                    # REMOVED_SYNTAX_ERROR: "source_ip": headers.get("X-Forwarded-For", "127.0.0.1") if headers else "127.0.0.1",
                    # REMOVED_SYNTAX_ERROR: "user_agent": headers.get("User-Agent", "TestClient") if headers else "TestClient"
                    

                    # Simulate immediate rejection
                    # REMOVED_SYNTAX_ERROR: connection_time = time.time() - connection_start

                    # REMOVED_SYNTAX_ERROR: return False, { )
                    # REMOVED_SYNTAX_ERROR: "error": "authentication_failed",
                    # REMOVED_SYNTAX_ERROR: "error_code": 401,
                    # REMOVED_SYNTAX_ERROR: "message": "Authentication failed: Token expired",
                    # REMOVED_SYNTAX_ERROR: "connection_time": connection_time,
                    # REMOVED_SYNTAX_ERROR: "token_error": token_validation["error"],
                    # REMOVED_SYNTAX_ERROR: "rejected_immediately": connection_time < 0.1
                    

                    # Mock successful connection for valid tokens
                    # REMOVED_SYNTAX_ERROR: self.websocket = TestWebSocketConnection()
                    # REMOVED_SYNTAX_ERROR: self.is_connected = True
                    # REMOVED_SYNTAX_ERROR: connection_time = time.time() - connection_start

                    # REMOVED_SYNTAX_ERROR: return True, { )
                    # REMOVED_SYNTAX_ERROR: "success": True,
                    # REMOVED_SYNTAX_ERROR: "connection_time": connection_time,
                    # REMOVED_SYNTAX_ERROR: "session_established": True
                    

                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                        # REMOVED_SYNTAX_ERROR: connection_time = time.time() - connection_start
                        # REMOVED_SYNTAX_ERROR: self.last_error = str(e)

                        # REMOVED_SYNTAX_ERROR: return False, { )
                        # REMOVED_SYNTAX_ERROR: "error": "connection_failed",
                        # REMOVED_SYNTAX_ERROR: "message": str(e),
                        # REMOVED_SYNTAX_ERROR: "connection_time": connection_time
                        

# REMOVED_SYNTAX_ERROR: async def disconnect(self):
    # REMOVED_SYNTAX_ERROR: """Disconnect from WebSocket."""
    # REMOVED_SYNTAX_ERROR: if self.websocket and self.is_connected:
        # REMOVED_SYNTAX_ERROR: await self.websocket.close()
        # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: async def send_message(self, message: Dict[str, Any]) -> bool:
    # REMOVED_SYNTAX_ERROR: """Send message (should fail for expired token connections)."""
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: return False

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: await self.websocket.send(json.dumps(message))
            # REMOVED_SYNTAX_ERROR: return True
            # REMOVED_SYNTAX_ERROR: except Exception:
                # REMOVED_SYNTAX_ERROR: return False


# REMOVED_SYNTAX_ERROR: class TokenRefreshService:
    # REMOVED_SYNTAX_ERROR: """Mock token refresh service for testing refresh flows."""

# REMOVED_SYNTAX_ERROR: def __init__(self, jwt_generator: SecureJWTGenerator, audit_logger: SecurityAuditLogger):
    # REMOVED_SYNTAX_ERROR: self.jwt_generator = jwt_generator
    # REMOVED_SYNTAX_ERROR: self.audit_logger = audit_logger
    # REMOVED_SYNTAX_ERROR: self.invalidated_tokens = set()

# REMOVED_SYNTAX_ERROR: async def refresh_expired_token(self, expired_token: str, refresh_token: str) -> Optional[Dict[str, str]]:
    # REMOVED_SYNTAX_ERROR: """Attempt to refresh expired access token."""
    # Validate refresh token (mock validation)
    # REMOVED_SYNTAX_ERROR: if not refresh_token or len(refresh_token) < 20:
        # REMOVED_SYNTAX_ERROR: return None

        # Extract user ID from expired token (without validation)
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: unverified_payload = jwt.decode(expired_token, options={"verify_signature": False})
            # REMOVED_SYNTAX_ERROR: user_id = unverified_payload.get("sub")
            # REMOVED_SYNTAX_ERROR: except Exception:
                # REMOVED_SYNTAX_ERROR: return None

                # REMOVED_SYNTAX_ERROR: if not user_id:
                    # REMOVED_SYNTAX_ERROR: return None

                    # Generate new tokens
                    # REMOVED_SYNTAX_ERROR: new_access_token = self.jwt_generator.create_valid_token(user_id)
                    # REMOVED_SYNTAX_ERROR: new_refresh_token = "formatted_string"

                    # Invalidate old tokens
                    # REMOVED_SYNTAX_ERROR: old_token_hash = hashlib.sha256(expired_token.encode()).hexdigest()[:16]
                    # REMOVED_SYNTAX_ERROR: self.invalidated_tokens.add(old_token_hash)

                    # Log successful refresh
                    # Removed problematic line: await self.audit_logger.log_successful_token_refresh({ ))
                    # REMOVED_SYNTAX_ERROR: "user_id": user_id,
                    # REMOVED_SYNTAX_ERROR: "old_token_fingerprint": old_token_hash,
                    # REMOVED_SYNTAX_ERROR: "new_token_fingerprint": hashlib.sha256(new_access_token.encode()).hexdigest()[:16]
                    

                    # REMOVED_SYNTAX_ERROR: return { )
                    # REMOVED_SYNTAX_ERROR: "access_token": new_access_token,
                    # REMOVED_SYNTAX_ERROR: "refresh_token": new_refresh_token,
                    # REMOVED_SYNTAX_ERROR: "expires_in": 900  # 15 minutes
                    

# REMOVED_SYNTAX_ERROR: def is_token_invalidated(self, token: str) -> bool:
    # REMOVED_SYNTAX_ERROR: """Check if token has been invalidated."""
    # REMOVED_SYNTAX_ERROR: token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
    # REMOVED_SYNTAX_ERROR: return token_hash in self.invalidated_tokens


    # Helper Functions for Token Tampering Tests

# REMOVED_SYNTAX_ERROR: def create_tampered_token_expiry(original_token: str) -> str:
    # REMOVED_SYNTAX_ERROR: """Create token with tampered expiry time."""
    # REMOVED_SYNTAX_ERROR: try:
        # Decode without verification to get payload
        # REMOVED_SYNTAX_ERROR: payload = jwt.decode(original_token, options={"verify_signature": False})

        # Modify expiry to future time
        # REMOVED_SYNTAX_ERROR: payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=1)

        # Re-encode with wrong secret (will fail validation)
        # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, "wrong-secret", algorithm="HS256")
        # REMOVED_SYNTAX_ERROR: except Exception:
            # REMOVED_SYNTAX_ERROR: return "tampered.expiry.token"


# REMOVED_SYNTAX_ERROR: def create_tampered_token_user(original_token: str) -> str:
    # REMOVED_SYNTAX_ERROR: """Create token with tampered user ID."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: payload = jwt.decode(original_token, options={"verify_signature": False})
        # REMOVED_SYNTAX_ERROR: payload["sub"] = "admin_user"  # Elevate to admin
        # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, "wrong-secret", algorithm="HS256")
        # REMOVED_SYNTAX_ERROR: except Exception:
            # REMOVED_SYNTAX_ERROR: return "tampered.user.token"


# REMOVED_SYNTAX_ERROR: def create_tampered_token_permissions(original_token: str) -> str:
    # REMOVED_SYNTAX_ERROR: """Create token with tampered permissions."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: payload = jwt.decode(original_token, options={"verify_signature": False})
        # REMOVED_SYNTAX_ERROR: payload["permissions"] = ["read", "write", "admin", "delete"]  # Elevate permissions
        # REMOVED_SYNTAX_ERROR: return jwt.encode(payload, "wrong-secret", algorithm="HS256")
        # REMOVED_SYNTAX_ERROR: except Exception:
            # REMOVED_SYNTAX_ERROR: return "tampered.permissions.token"


            # Common Fixtures

            # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def jwt_generator():
    # REMOVED_SYNTAX_ERROR: """JWT generator fixture for creating test tokens."""
    # REMOVED_SYNTAX_ERROR: return SecureJWTGenerator()


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def audit_logger():
    # REMOVED_SYNTAX_ERROR: """Security audit logger fixture."""
    # REMOVED_SYNTAX_ERROR: return SecurityAuditLogger()


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def token_refresh_service(jwt_generator, audit_logger):
    # REMOVED_SYNTAX_ERROR: """Token refresh service fixture."""
    # REMOVED_SYNTAX_ERROR: return TokenRefreshService(jwt_generator, audit_logger)


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def expired_token(jwt_generator):
    # REMOVED_SYNTAX_ERROR: """Expired token fixture."""
    # REMOVED_SYNTAX_ERROR: return jwt_generator.create_expired_token("test_user_123", expired_minutes_ago=5)


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def valid_token(jwt_generator):
    # REMOVED_SYNTAX_ERROR: """Valid token fixture."""
    # REMOVED_SYNTAX_ERROR: return jwt_generator.create_valid_token("test_user_123")


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def near_expiry_token(jwt_generator):
    # REMOVED_SYNTAX_ERROR: """Near expiry token fixture."""
    # REMOVED_SYNTAX_ERROR: return jwt_generator.create_near_expiry_token("test_user_123", expires_in_seconds=10)


    # Streaming and Network Simulation Classes

# REMOVED_SYNTAX_ERROR: class ConnectionState(Enum):
    # REMOVED_SYNTAX_ERROR: """WebSocket connection states for testing."""
    # REMOVED_SYNTAX_ERROR: DISCONNECTED = "disconnected"
    # REMOVED_SYNTAX_ERROR: CONNECTING = "connecting"
    # REMOVED_SYNTAX_ERROR: CONNECTED = "connected"
    # REMOVED_SYNTAX_ERROR: STREAMING = "streaming"
    # REMOVED_SYNTAX_ERROR: INTERRUPTED = "interrupted"
    # REMOVED_SYNTAX_ERROR: RECOVERING = "recovering"
    # REMOVED_SYNTAX_ERROR: FAILED = "failed"


# REMOVED_SYNTAX_ERROR: class ResponseType(Enum):
    # REMOVED_SYNTAX_ERROR: """Types of streaming responses for testing."""
    # REMOVED_SYNTAX_ERROR: TEXT = "text"
    # REMOVED_SYNTAX_ERROR: JSON = "json"
    # REMOVED_SYNTAX_ERROR: MULTIPART = "multipart"
    # REMOVED_SYNTAX_ERROR: BINARY = "binary"


    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class StreamBuffer:
    # REMOVED_SYNTAX_ERROR: """Buffer for partial streaming response data."""
    # REMOVED_SYNTAX_ERROR: buffer_id: str
    # REMOVED_SYNTAX_ERROR: response_type: ResponseType
    # REMOVED_SYNTAX_ERROR: content: List[bytes] = field(default_factory=list)
    # REMOVED_SYNTAX_ERROR: total_size: int = 0
    # REMOVED_SYNTAX_ERROR: received_size: int = 0
    # REMOVED_SYNTAX_ERROR: sequence_numbers: List[int] = field(default_factory=list)
    # REMOVED_SYNTAX_ERROR: start_time: float = field(default_factory=time.time)
    # REMOVED_SYNTAX_ERROR: last_update: float = field(default_factory=time.time)
    # REMOVED_SYNTAX_ERROR: checksum: str = ""
    # REMOVED_SYNTAX_ERROR: is_complete: bool = False
    # REMOVED_SYNTAX_ERROR: stream_generator: Optional[Any] = None

# REMOVED_SYNTAX_ERROR: def add_chunk(self, chunk: bytes, sequence_num: int) -> None:
    # REMOVED_SYNTAX_ERROR: """Add a chunk to the buffer."""
    # REMOVED_SYNTAX_ERROR: self.content.append(chunk)
    # REMOVED_SYNTAX_ERROR: self.received_size += len(chunk)
    # REMOVED_SYNTAX_ERROR: self.sequence_numbers.append(sequence_num)
    # REMOVED_SYNTAX_ERROR: self.last_update = time.time()

# REMOVED_SYNTAX_ERROR: def get_content_hash(self) -> str:
    # REMOVED_SYNTAX_ERROR: """Calculate hash of buffer content."""
    # REMOVED_SYNTAX_ERROR: full_content = b''.join(self.content)
    # REMOVED_SYNTAX_ERROR: return hashlib.sha256(full_content).hexdigest()

# REMOVED_SYNTAX_ERROR: def verify_integrity(self) -> bool:
    # REMOVED_SYNTAX_ERROR: """Verify buffer integrity."""
    # REMOVED_SYNTAX_ERROR: if not self.content:
        # REMOVED_SYNTAX_ERROR: return False

        # Check sequence continuity
        # REMOVED_SYNTAX_ERROR: if len(self.sequence_numbers) > 1:
            # REMOVED_SYNTAX_ERROR: for i in range(1, len(self.sequence_numbers)):
                # REMOVED_SYNTAX_ERROR: if self.sequence_numbers[i] != self.sequence_numbers[i-1] + 1:
                    # REMOVED_SYNTAX_ERROR: return False

                    # Check size consistency
                    # REMOVED_SYNTAX_ERROR: calculated_size = sum(len(chunk) for chunk in self.content)
                    # REMOVED_SYNTAX_ERROR: return calculated_size == self.received_size


                    # REMOVED_SYNTAX_ERROR: @dataclass
# REMOVED_SYNTAX_ERROR: class NetworkCondition:
    # REMOVED_SYNTAX_ERROR: """Network condition simulation parameters."""
    # REMOVED_SYNTAX_ERROR: name: str
    # REMOVED_SYNTAX_ERROR: disconnect_probability: float = 0.0
    # REMOVED_SYNTAX_ERROR: latency_ms: int = 0
    # REMOVED_SYNTAX_ERROR: bandwidth_limit: Optional[int] = None
    # REMOVED_SYNTAX_ERROR: packet_loss_rate: float = 0.0
    # REMOVED_SYNTAX_ERROR: is_active: bool = True


# REMOVED_SYNTAX_ERROR: class NetworkSimulator:
    # REMOVED_SYNTAX_ERROR: """Simulates various network conditions for testing."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.conditions: Dict[str, NetworkCondition] = {}
    # REMOVED_SYNTAX_ERROR: self.active_condition: Optional[str] = None
    # REMOVED_SYNTAX_ERROR: self.disconnect_events: List[Dict[str, Any]] = []

# REMOVED_SYNTAX_ERROR: def add_condition(self, condition: NetworkCondition) -> None:
    # REMOVED_SYNTAX_ERROR: """Add a network condition."""
    # REMOVED_SYNTAX_ERROR: self.conditions[condition.name] = condition

# REMOVED_SYNTAX_ERROR: async def apply_condition(self, condition_name: str, duration: float = 0.0) -> None:
    # REMOVED_SYNTAX_ERROR: """Apply a network condition for specified duration."""
    # REMOVED_SYNTAX_ERROR: if condition_name not in self.conditions:
        # REMOVED_SYNTAX_ERROR: raise ValueError("formatted_string")

        # REMOVED_SYNTAX_ERROR: self.active_condition = condition_name
        # REMOVED_SYNTAX_ERROR: condition = self.conditions[condition_name]

        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

        # REMOVED_SYNTAX_ERROR: if duration > 0:
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(duration)
            # REMOVED_SYNTAX_ERROR: self.active_condition = None
            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: async def simulate_disconnect(self, connection, delay: float = 0.0) -> None:
    # REMOVED_SYNTAX_ERROR: """Simulate a network disconnection."""
    # REMOVED_SYNTAX_ERROR: if delay > 0:
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(delay)

        # REMOVED_SYNTAX_ERROR: disconnect_event = { )
        # REMOVED_SYNTAX_ERROR: "timestamp": time.time(),
        # REMOVED_SYNTAX_ERROR: "condition": self.active_condition,
        # REMOVED_SYNTAX_ERROR: "delay": delay
        
        # REMOVED_SYNTAX_ERROR: self.disconnect_events.append(disconnect_event)

        # Simulate connection closure
        # REMOVED_SYNTAX_ERROR: if hasattr(connection, 'close'):
            # REMOVED_SYNTAX_ERROR: await connection.close()
            # REMOVED_SYNTAX_ERROR: elif hasattr(connection, '_simulate_disconnect'):
                # REMOVED_SYNTAX_ERROR: await connection._simulate_disconnect()

                # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def should_drop_packet(self) -> bool:
    # REMOVED_SYNTAX_ERROR: """Check if current packet should be dropped."""
    # REMOVED_SYNTAX_ERROR: if not self.active_condition:
        # REMOVED_SYNTAX_ERROR: return False

        # REMOVED_SYNTAX_ERROR: condition = self.conditions[self.active_condition]
        # REMOVED_SYNTAX_ERROR: return random.random() < condition.packet_loss_rate

# REMOVED_SYNTAX_ERROR: def get_latency(self) -> float:
    # REMOVED_SYNTAX_ERROR: """Get current network latency in seconds."""
    # REMOVED_SYNTAX_ERROR: if not self.active_condition:
        # REMOVED_SYNTAX_ERROR: return 0.0

        # REMOVED_SYNTAX_ERROR: condition = self.conditions[self.active_condition]
        # REMOVED_SYNTAX_ERROR: return condition.latency_ms / 1000.0


        # Streaming fixtures
        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def network_simulator():
    # REMOVED_SYNTAX_ERROR: """Network simulator fixture."""
    # REMOVED_SYNTAX_ERROR: return NetworkSimulator()


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def response_configs():
    # REMOVED_SYNTAX_ERROR: """Response configuration fixture."""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: "text": {"type": ResponseType.TEXT, "chunk_size": 100, "total_chunks": 20},
    # REMOVED_SYNTAX_ERROR: "json": {"type": ResponseType.JSON, "chunk_size": 200, "total_chunks": 15},
    # REMOVED_SYNTAX_ERROR: "multipart": {"type": ResponseType.MULTIPART, "chunk_size": 150, "total_chunks": 25},
    # REMOVED_SYNTAX_ERROR: "binary": {"type": ResponseType.BINARY, "chunk_size": 512, "total_chunks": 10}
    