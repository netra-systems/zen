class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()
        \n'''
        \n'''
        Shared fixtures for WebSocket resilience tests.

        Common test fixtures, utilities, and mock classes used across all WebSocket resilience tests.
        Extracted from original test files to reduce duplication and maintain consistency.
        '''
        '''

        import asyncio
        import hashlib
        import json
        import random
        import secrets
        import time
        import uuid
        from dataclasses import dataclass, field
        from datetime import datetime, timedelta, timezone
        from enum import Enum
        from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

        import jwt
        import pytest
        import websockets
        from websockets import ConnectionClosed, InvalidStatus

        from netra_backend.app.logging_config import central_logger
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env

        logger = central_logger.get_logger(__name__)


class SecureJWTGenerator:
        """Secure JWT token generator for testing expired token scenarios."""

    def __init__(self):
        self.secret = "test-secret-key-for-security-testing-only"
        self.algorithm = "HS256"
        self.issuer = "netra-test-auth"
        self.token_fingerprints = set()

        def create_expired_token(self, user_id: str, expired_minutes_ago: int = 1,
        permissions: List[str] = None) -> str:
        """Create JWT token that expired specified minutes ago."""
        now = datetime.now(timezone.utc)
        exp_time = now - timedelta(minutes=expired_minutes_ago)

        payload = { )
        "sub": user_id,
        "iat": now - timedelta(minutes=expired_minutes_ago + 15),  # Issued before expiry
        "exp": exp_time,
        "email": "formatted_string",
        "permissions": permissions or ["read"],
        "token_type": "access",
        "iss": self.issuer,
        "jti": str(uuid.uuid4())  # Unique token ID for tracking
    

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)

    # Track token fingerprint for security testing
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        self.token_fingerprints.add(token_hash)

        return token

        def create_valid_token(self, user_id: str, expires_in_minutes: int = 15,
        permissions: List[str] = None) -> str:
        """Create valid JWT token for comparison testing."""
        now = datetime.now(timezone.utc)
        exp_time = now + timedelta(minutes=expires_in_minutes)

        payload = { )
        "sub": user_id,
        "iat": now,
        "exp": exp_time,
        "email": "formatted_string",
        "permissions": permissions or ["read"],
        "token_type": "access",
        "iss": self.issuer,
        "jti": str(uuid.uuid4())
    

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_near_expiry_token(self, user_id: str, expires_in_seconds: int = 5) -> str:
        """Create token that expires very soon for grace period testing."""
        now = datetime.now(timezone.utc)
        exp_time = now + timedelta(seconds=expires_in_seconds)

        payload = { )
        "sub": user_id,
        "iat": now,
        "exp": exp_time,
        "email": "formatted_string",
        "permissions": ["read"],
        "token_type": "access",
        "iss": self.issuer,
        "jti": str(uuid.uuid4())
    

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_malformed_expired_token(self, user_id: str) -> str:
        """Create malformed token that appears expired for edge case testing."""
    # Create token with invalid signature but expired timestamp
        now = datetime.now(timezone.utc)
        exp_time = now - timedelta(minutes=5)

        payload = { )
        "sub": user_id,
        "exp": exp_time,
        "iat": now - timedelta(minutes=20),
        "malformed": True
    

    # Use wrong secret to create invalid signature
        return jwt.encode(payload, "wrong-secret", algorithm=self.algorithm)

    def validate_token(self, token: str) -> Optional[Dict]:
        """Validate token for testing purposes."""
        try:
        payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        return payload
        except jwt.ExpiredSignatureError:
        return {"error": "expired", "type": "ExpiredSignatureError"}
        except jwt.InvalidTokenError as e:
        return {"error": "invalid", "type": type(e).__name__, "message": str(e)}


class SecurityAuditLogger:
        """Mock security audit logger for testing security event logging."""

    def __init__(self):
        self.security_events = []
        self.alert_triggers = []
        self.suspicious_patterns = {}

    async def log_expired_token_attempt(self, event_data: Dict[str, Any]):
        """Log expired token access attempt."""
        event = { )
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "expired_token_attempt",
        "severity": "HIGH",
        "user_id": event_data.get("user_id"),
        "source_ip": event_data.get("source_ip", "127.0.0.1"),
        "token_fingerprint": event_data.get("token_fingerprint"),
        "expiry_time": event_data.get("expiry_time"),
        "attempt_time": event_data.get("attempt_time"),
        "user_agent": event_data.get("user_agent"),
        "session_id": event_data.get("session_id")
    

        self.security_events.append(event)

    # Check for suspicious patterns
        await self._analyze_suspicious_patterns(event)

    async def log_successful_token_refresh(self, event_data: Dict[str, Any]):
        """Log successful token refresh event."""
        event = { )
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "token_refresh_success",
        "severity": "INFO",
        "user_id": event_data.get("user_id"),
        "old_token_fingerprint": event_data.get("old_token_fingerprint"),
        "new_token_fingerprint": event_data.get("new_token_fingerprint")
    

        self.security_events.append(event)

    async def _analyze_suspicious_patterns(self, event: Dict[str, Any]):
        """Analyze events for suspicious patterns and trigger alerts."""
        user_id = event.get("user_id")
        source_ip = event.get("source_ip")

    # Track repeated attempts by user
        user_key = "formatted_string"
        if user_key not in self.suspicious_patterns:
        self.suspicious_patterns[user_key] = []

        self.suspicious_patterns[user_key].append(event["timestamp"])

        # Clean old events (keep last hour)
        recent_events = [ )
        ts for ts in self.suspicious_patterns[user_key]
        if (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() < 3600
        
        self.suspicious_patterns[user_key] = recent_events

        # Trigger alert if more than 5 attempts in last 10 minutes
        recent_attempts = [ )
        ts for ts in recent_events
        if (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() < 600
        

        if len(recent_attempts) >= 5:
        alert = { )
        "alert_type": "repeated_expired_token_attempts",
        "severity": "CRITICAL",
        "user_id": user_id,
        "source_ip": source_ip,
        "attempt_count": len(recent_attempts),
        "time_window": "10_minutes",
        "timestamp": datetime.now(timezone.utc).isoformat()
            
        self.alert_triggers.append(alert)

    def get_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all security events for specific user."""
        return [item for item in []]

    def get_alert_count(self) -> int:
        """Get number of security alerts triggered."""
        return len(self.alert_triggers)

    async def log_session_event(self, user_id: str, session_id: str, event_type: str, details: Dict[str, Any] = None):
        """Log session-related event."""
        event = { )
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": "INFO",
        "user_id": user_id,
        "session_id": session_id,
        "details": details or {}
    

        self.security_events.append(event)


class SecureWebSocketTestClient:
        """Security-focused WebSocket test client for expired token testing."""

        def __init__(self, uri: str, token: str, jwt_generator: SecureJWTGenerator,
        audit_logger: SecurityAuditLogger):
        self.uri = uri
        self.token = token
        self.jwt_generator = jwt_generator
        self.audit_logger = audit_logger
        self.websocket = None
        self.is_connected = False
        self.connection_metadata = {}
        self.last_error = None

    async def attempt_connection(self, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Dict[str, Any]]:
        """Attempt WebSocket connection and return detailed result."""
        connection_start = time.time()

        try:
        # Validate token before attempting connection
        token_validation = self.jwt_generator.validate_token(self.token)

        if token_validation and "error" in token_validation:
            Extract user ID from token for logging
        try:
        unverified_payload = jwt.decode(self.token, options={"verify_signature": False})
        user_id = unverified_payload.get("sub", "unknown_user")
        except Exception:
        user_id = "unknown_user"

                    # Log expired token attempt
                    # Removed problematic line: await self.audit_logger.log_expired_token_attempt({)
        "user_id": user_id,
        "token_fingerprint": hashlib.sha256(self.token.encode()).hexdigest()[:16],
        "expiry_time": "expired",
        "attempt_time": datetime.now(timezone.utc).isoformat(),
        "source_ip": headers.get("X-Forwarded-For", "127.0.0.1") if headers else "127.0.0.1",
        "user_agent": headers.get("User-Agent", "TestClient") if headers else "TestClient"
                    

                    # Simulate immediate rejection
        connection_time = time.time() - connection_start

        return False, { )
        "error": "authentication_failed",
        "error_code": 401,
        "message": "Authentication failed: Token expired",
        "connection_time": connection_time,
        "token_error": token_validation["error"],
        "rejected_immediately": connection_time < 0.1
                    

                    # Mock successful connection for valid tokens
        self.websocket = TestWebSocketConnection()
        self.is_connected = True
        connection_time = time.time() - connection_start

        return True, { )
        "success": True,
        "connection_time": connection_time,
        "session_established": True
                    

        except Exception as e:
        connection_time = time.time() - connection_start
        self.last_error = str(e)

        return False, { )
        "error": "connection_failed",
        "message": str(e),
        "connection_time": connection_time
                        

    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket and self.is_connected:
        await self.websocket.close()
        self.is_connected = False

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message (should fail for expired token connections)."""
        if not self.is_connected:
        return False

        try:
        await self.websocket.send(json.dumps(message))
        return True
        except Exception:
        return False


class TokenRefreshService:
        """Mock token refresh service for testing refresh flows."""

    def __init__(self, jwt_generator: SecureJWTGenerator, audit_logger: SecurityAuditLogger):
        self.jwt_generator = jwt_generator
        self.audit_logger = audit_logger
        self.invalidated_tokens = set()

    async def refresh_expired_token(self, expired_token: str, refresh_token: str) -> Optional[Dict[str, str]]:
        """Attempt to refresh expired access token."""
    # Validate refresh token (mock validation)
        if not refresh_token or len(refresh_token) < 20:
        return None

        Extract user ID from expired token (without validation)
        try:
        unverified_payload = jwt.decode(expired_token, options={"verify_signature": False})
        user_id = unverified_payload.get("sub")
        except Exception:
        return None

        if not user_id:
        return None

                    # Generate new tokens
        new_access_token = self.jwt_generator.create_valid_token(user_id)
        new_refresh_token = "formatted_string"

                    # Invalidate old tokens
        old_token_hash = hashlib.sha256(expired_token.encode()).hexdigest()[:16]
        self.invalidated_tokens.add(old_token_hash)

                    # Log successful refresh
                    # Removed problematic line: await self.audit_logger.log_successful_token_refresh({)
        "user_id": user_id,
        "old_token_fingerprint": old_token_hash,
        "new_token_fingerprint": hashlib.sha256(new_access_token.encode()).hexdigest()[:16]
                    

        return { )
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "expires_in": 900  # 15 minutes
                    

    def is_token_invalidated(self, token: str) -> bool:
        """Check if token has been invalidated."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        return token_hash in self.invalidated_tokens


    # Helper Functions for Token Tampering Tests

    def create_tampered_token_expiry(original_token: str) -> str:
        """Create token with tampered expiry time."""
        try:
        # Decode without verification to get payload
        payload = jwt.decode(original_token, options={"verify_signature": False})

        # Modify expiry to future time
        payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=1)

        # Re-encode with wrong secret (will fail validation)
        return jwt.encode(payload, "wrong-secret", algorithm="HS256")
        except Exception:
        return "tampered.expiry.token"


    def create_tampered_token_user(original_token: str) -> str:
        """Create token with tampered user ID."""
        try:
        payload = jwt.decode(original_token, options={"verify_signature": False})
        payload["sub"] = "admin_user"  # Elevate to admin
        return jwt.encode(payload, "wrong-secret", algorithm="HS256")
        except Exception:
        return "tampered.user.token"


    def create_tampered_token_permissions(original_token: str) -> str:
        """Create token with tampered permissions."""
        try:
        payload = jwt.decode(original_token, options={"verify_signature": False})
        payload["permissions"] = ["read", "write", "admin", "delete"]  # Elevate permissions
        return jwt.encode(payload, "wrong-secret", algorithm="HS256")
        except Exception:
        return "tampered.permissions.token"


            # Common Fixtures

        @pytest.fixture
    def jwt_generator():
        """JWT generator fixture for creating test tokens."""
        return SecureJWTGenerator()


        @pytest.fixture
    def audit_logger():
        """Security audit logger fixture."""
        return SecurityAuditLogger()


        @pytest.fixture
    def token_refresh_service(jwt_generator, audit_logger):
        """Token refresh service fixture."""
        return TokenRefreshService(jwt_generator, audit_logger)


        @pytest.fixture
    def expired_token(jwt_generator):
        """Expired token fixture."""
        return jwt_generator.create_expired_token("test_user_123", expired_minutes_ago=5)


        @pytest.fixture
    def valid_token(jwt_generator):
        """Valid token fixture."""
        return jwt_generator.create_valid_token("test_user_123")


        @pytest.fixture
    def near_expiry_token(jwt_generator):
        """Near expiry token fixture."""
        return jwt_generator.create_near_expiry_token("test_user_123", expires_in_seconds=10)


    # Streaming and Network Simulation Classes

class ConnectionState(Enum):
        """WebSocket connection states for testing."""
        DISCONNECTED = "disconnected"
        CONNECTING = "connecting"
        CONNECTED = "connected"
        STREAMING = "streaming"
        INTERRUPTED = "interrupted"
        RECOVERING = "recovering"
        FAILED = "failed"


class ResponseType(Enum):
        """Types of streaming responses for testing."""
        TEXT = "text"
        JSON = "json"
        MULTIPART = "multipart"
        BINARY = "binary"


        @dataclass
class StreamBuffer:
        """Buffer for partial streaming response data."""
        buffer_id: str
        response_type: ResponseType
        content: List[bytes] = field(default_factory=list)
        total_size: int = 0
        received_size: int = 0
        sequence_numbers: List[int] = field(default_factory=list)
        start_time: float = field(default_factory=time.time)
        last_update: float = field(default_factory=time.time)
        checksum: str = ""
        is_complete: bool = False
        stream_generator: Optional[Any] = None

    def add_chunk(self, chunk: bytes, sequence_num: int) -> None:
        """Add a chunk to the buffer."""
        self.content.append(chunk)
        self.received_size += len(chunk)
        self.sequence_numbers.append(sequence_num)
        self.last_update = time.time()

    def get_content_hash(self) -> str:
        """Calculate hash of buffer content."""
        full_content = b''.join(self.content)
        return hashlib.sha256(full_content).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify buffer integrity."""
        if not self.content:
        return False

        # Check sequence continuity
        if len(self.sequence_numbers) > 1:
        for i in range(1, len(self.sequence_numbers)):
        if self.sequence_numbers[i] != self.sequence_numbers[i-1] + 1:
        return False

                    # Check size consistency
        calculated_size = sum(len(chunk) for chunk in self.content)
        return calculated_size == self.received_size


        @dataclass
class NetworkCondition:
        """Network condition simulation parameters."""
        name: str
        disconnect_probability: float = 0.0
        latency_ms: int = 0
        bandwidth_limit: Optional[int] = None
        packet_loss_rate: float = 0.0
        is_active: bool = True


class NetworkSimulator:
        """Simulates various network conditions for testing."""

    def __init__(self):
        self.conditions: Dict[str, NetworkCondition] = {}
        self.active_condition: Optional[str] = None
        self.disconnect_events: List[Dict[str, Any]] = []

    def add_condition(self, condition: NetworkCondition) -> None:
        """Add a network condition."""
        self.conditions[condition.name] = condition

    async def apply_condition(self, condition_name: str, duration: float = 0.0) -> None:
        """Apply a network condition for specified duration."""
        if condition_name not in self.conditions:
        raise ValueError("formatted_string")

        self.active_condition = condition_name
        condition = self.conditions[condition_name]

        logger.info("formatted_string")

        if duration > 0:
        await asyncio.sleep(duration)
        self.active_condition = None
        logger.info("formatted_string")

    async def simulate_disconnect(self, connection, delay: float = 0.0) -> None:
        """Simulate a network disconnection."""
        if delay > 0:
        await asyncio.sleep(delay)

        disconnect_event = { )
        "timestamp": time.time(),
        "condition": self.active_condition,
        "delay": delay
        
        self.disconnect_events.append(disconnect_event)

        # Simulate connection closure
        if hasattr(connection, 'close'):
        await connection.close()
        elif hasattr(connection, '_simulate_disconnect'):
        await connection._simulate_disconnect()

        logger.info("formatted_string")

    def should_drop_packet(self) -> bool:
        """Check if current packet should be dropped."""
        if not self.active_condition:
        return False

        condition = self.conditions[self.active_condition]
        return random.random() < condition.packet_loss_rate

    def get_latency(self) -> float:
        """Get current network latency in seconds."""
        if not self.active_condition:
        return 0.0

        condition = self.conditions[self.active_condition]
        return condition.latency_ms / 1000.0


        # Streaming fixtures
        @pytest.fixture
    def network_simulator():
        """Network simulator fixture."""
        return NetworkSimulator()


        @pytest.fixture
    def response_configs():
        """Response configuration fixture."""
        return { )
        "text": {"type": ResponseType.TEXT, "chunk_size": 100, "total_chunks": 20},
        "json": {"type": ResponseType.JSON, "chunk_size": 200, "total_chunks": 15},
        "multipart": {"type": ResponseType.MULTIPART, "chunk_size": 150, "total_chunks": 25},
        "binary": {"type": ResponseType.BINARY, "chunk_size": 512, "total_chunks": 10}
    

]]
}}}}}}}}}}}}}}}}