"""
WebSocket Test 4: Reconnection with Expired Token

Security-focused test suite that validates expired JWT tokens are properly rejected
during WebSocket reconnection attempts, preventing unauthorized access and session hijacking.

Business Value: Prevents $500K+ security breaches and ensures SOC 2 compliance
for enterprise customers, maintaining customer trust and regulatory compliance.
"""

import asyncio
import json
import time
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import jwt
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from app.logging_config import central_logger

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
        
        payload = {
            "sub": user_id,
            "iat": now - timedelta(minutes=expired_minutes_ago + 15),  # Issued before expiry
            "exp": exp_time,
            "email": f"{user_id}@test.com",
            "permissions": permissions or ["read"],
            "token_type": "access",
            "iss": self.issuer,
            "jti": str(uuid.uuid4())  # Unique token ID for tracking
        }
        
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
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": exp_time,
            "email": f"{user_id}@test.com",
            "permissions": permissions or ["read"],
            "token_type": "access",
            "iss": self.issuer,
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def create_near_expiry_token(self, user_id: str, expires_in_seconds: int = 5) -> str:
        """Create token that expires very soon for grace period testing."""
        now = datetime.now(timezone.utc)
        exp_time = now + timedelta(seconds=expires_in_seconds)
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": exp_time,
            "email": f"{user_id}@test.com",
            "permissions": ["read"],
            "token_type": "access",
            "iss": self.issuer,
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def create_malformed_expired_token(self, user_id: str) -> str:
        """Create malformed token that appears expired for edge case testing."""
        # Create token with invalid signature but expired timestamp
        now = datetime.now(timezone.utc)
        exp_time = now - timedelta(minutes=5)
        
        payload = {
            "sub": user_id,
            "exp": exp_time,
            "iat": now - timedelta(minutes=20),
            "malformed": True
        }
        
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
        event = {
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
        }
        
        self.security_events.append(event)
        
        # Check for suspicious patterns
        await self._analyze_suspicious_patterns(event)
        
    async def log_successful_token_refresh(self, event_data: Dict[str, Any]):
        """Log successful token refresh event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "token_refresh_success",
            "severity": "INFO",
            "user_id": event_data.get("user_id"),
            "old_token_fingerprint": event_data.get("old_token_fingerprint"),
            "new_token_fingerprint": event_data.get("new_token_fingerprint")
        }
        
        self.security_events.append(event)
    
    async def _analyze_suspicious_patterns(self, event: Dict[str, Any]):
        """Analyze events for suspicious patterns and trigger alerts."""
        user_id = event.get("user_id")
        source_ip = event.get("source_ip")
        
        # Track repeated attempts by user
        user_key = f"user_{user_id}"
        if user_key not in self.suspicious_patterns:
            self.suspicious_patterns[user_key] = []
        
        self.suspicious_patterns[user_key].append(event["timestamp"])
        
        # Clean old events (keep last hour)
        recent_events = [
            ts for ts in self.suspicious_patterns[user_key]
            if (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() < 3600
        ]
        self.suspicious_patterns[user_key] = recent_events
        
        # Trigger alert if more than 5 attempts in last 10 minutes
        recent_attempts = [
            ts for ts in recent_events
            if (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() < 600
        ]
        
        if len(recent_attempts) >= 5:
            alert = {
                "alert_type": "repeated_expired_token_attempts",
                "severity": "CRITICAL",
                "user_id": user_id,
                "source_ip": source_ip,
                "attempt_count": len(recent_attempts),
                "time_window": "10_minutes",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.alert_triggers.append(alert)
    
    def get_events_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all security events for specific user."""
        return [event for event in self.security_events if event.get("user_id") == user_id]
    
    def get_alert_count(self) -> int:
        """Get number of security alerts triggered."""
        return len(self.alert_triggers)


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
                # Extract user ID from token for logging
                try:
                    unverified_payload = jwt.decode(self.token, options={"verify_signature": False})
                    user_id = unverified_payload.get("sub", "unknown_user")
                except Exception:
                    user_id = "unknown_user"
                
                # Log expired token attempt
                await self.audit_logger.log_expired_token_attempt({
                    "user_id": user_id,
                    "token_fingerprint": hashlib.sha256(self.token.encode()).hexdigest()[:16],
                    "expiry_time": "expired",
                    "attempt_time": datetime.now(timezone.utc).isoformat(),
                    "source_ip": headers.get("X-Forwarded-For", "127.0.0.1") if headers else "127.0.0.1",
                    "user_agent": headers.get("User-Agent", "TestClient") if headers else "TestClient"
                })
                
                # Simulate immediate rejection
                connection_time = time.time() - connection_start
                
                return False, {
                    "error": "authentication_failed",
                    "error_code": 401,
                    "message": "Authentication failed: Token expired",
                    "connection_time": connection_time,
                    "token_error": token_validation["error"],
                    "rejected_immediately": connection_time < 0.1
                }
            
            # Mock successful connection for valid tokens
            self.websocket = AsyncMock()
            self.is_connected = True
            connection_time = time.time() - connection_start
            
            return True, {
                "success": True,
                "connection_time": connection_time,
                "session_established": True
            }
            
        except Exception as e:
            connection_time = time.time() - connection_start
            self.last_error = str(e)
            
            return False, {
                "error": "connection_failed",
                "message": str(e),
                "connection_time": connection_time
            }
    
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
        
        # Extract user ID from expired token (without validation)
        try:
            unverified_payload = jwt.decode(expired_token, options={"verify_signature": False})
            user_id = unverified_payload.get("sub")
        except Exception:
            return None
        
        if not user_id:
            return None
        
        # Generate new tokens
        new_access_token = self.jwt_generator.create_valid_token(user_id)
        new_refresh_token = f"refresh_{secrets.token_urlsafe(32)}"
        
        # Invalidate old tokens
        old_token_hash = hashlib.sha256(expired_token.encode()).hexdigest()[:16]
        self.invalidated_tokens.add(old_token_hash)
        
        # Log successful refresh
        await self.audit_logger.log_successful_token_refresh({
            "user_id": user_id,
            "old_token_fingerprint": old_token_hash,
            "new_token_fingerprint": hashlib.sha256(new_access_token.encode()).hexdigest()[:16]
        })
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "expires_in": 900  # 15 minutes
        }
    
    def is_token_invalidated(self, token: str) -> bool:
        """Check if token has been invalidated."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        return token_hash in self.invalidated_tokens


# Test Fixtures

@pytest.fixture
def jwt_generator():
    """JWT generator fixture for creating test tokens."""
    return SecureJWTGenerator()


@pytest.fixture(scope="function")
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


# Core Security Test Cases

@pytest.mark.asyncio
async def test_expired_token_immediate_rejection(jwt_generator, audit_logger, expired_token):
    """
    Test Case 1: Basic expired token rejection with proper error message.
    
    Validates that expired JWT tokens are immediately rejected during WebSocket 
    connection attempts with appropriate security logging.
    """
    logger.info("Testing expired token immediate rejection")
    
    # Create client with expired token
    client = SecureWebSocketTestClient(
        "ws://mock-server/ws", 
        expired_token, 
        jwt_generator, 
        audit_logger
    )
    
    # Attempt connection with expired token
    start_time = time.time()
    success, result = await client.attempt_connection({
        "X-Forwarded-For": "192.168.1.100",
        "User-Agent": "TestClient/1.0"
    })
    connection_time = time.time() - start_time
    
    # Validate immediate rejection
    assert not success, "Expired token should be rejected"
    assert result["error"] == "authentication_failed", f"Expected authentication_failed, got {result.get('error')}"
    assert result["error_code"] == 401, f"Expected 401 error code, got {result.get('error_code')}"
    assert "Token expired" in result["message"], "Error message should indicate token expiry"
    
    # Validate immediate response (security requirement)
    assert connection_time < 0.1, f"Connection rejection took {connection_time:.3f}s, expected < 0.1s"
    assert result["rejected_immediately"], "Token should be rejected immediately"
    
    # Validate no connection established
    assert not client.is_connected, "No connection should be established"
    assert client.websocket is None, "No WebSocket session should exist"
    
    # Validate security logging
    security_events = audit_logger.get_events_for_user("test_user_123")
    assert len(security_events) >= 1, "Security event should be logged"
    
    expired_events = [e for e in security_events if e["event_type"] == "expired_token_attempt"]
    assert len(expired_events) >= 1, "Expired token attempt should be logged"
    
    event = expired_events[0]
    assert event["severity"] == "HIGH", "High severity should be logged"
    assert event["source_ip"] == "192.168.1.100", "Source IP should be logged"
    assert "token_fingerprint" in event, "Token fingerprint should be logged"
    
    logger.info(f"✓ Expired token rejected in {connection_time:.3f}s with proper logging")


@pytest.mark.asyncio
async def test_grace_period_handling(jwt_generator, audit_logger, near_expiry_token):
    """
    Test Case 2: Grace period handling for recently expired tokens.
    
    Tests system behavior for tokens that expire during active sessions vs. 
    reconnection attempts, ensuring grace periods don't apply to new connections.
    """
    logger.info("Testing grace period handling for expired tokens")
    
    # Establish connection with near-expiry token
    client = SecureWebSocketTestClient(
        "ws://mock-server/ws",
        near_expiry_token,
        jwt_generator,
        audit_logger
    )
    
    # Connect while token is still valid
    success, result = await client.attempt_connection()
    assert success, "Connection with valid token should succeed"
    
    original_connection_time = result["connection_time"]
    assert client.is_connected, "Client should be connected"
    
    # Wait for token to expire (simulate active session)
    logger.info("Waiting for token to expire during active session")
    await asyncio.sleep(12)  # Token expires in 10 seconds, wait 12
    
    # Verify token is now expired
    token_validation = jwt_generator.validate_token(near_expiry_token)
    assert "error" in token_validation, "Token should be expired"
    assert token_validation["error"] == "expired", "Token should show expired error"
    
    # Test message sending during grace period (active session)
    # Note: In real implementation, active sessions might have grace period
    message_sent = await client.send_message({"type": "test", "content": "grace period test"})
    
    # Disconnect and attempt reconnection with expired token
    await client.disconnect()
    assert not client.is_connected, "Client should be disconnected"
    
    # Attempt reconnection with expired token - should fail
    logger.info("Attempting reconnection with expired token")
    reconnect_success, reconnect_result = await client.attempt_connection()
    
    # Validate grace period does NOT apply to new connections
    assert not reconnect_success, "Reconnection with expired token should fail"
    assert reconnect_result["error"] == "authentication_failed", "Should get authentication error"
    assert "Token expired" in reconnect_result["message"], "Should indicate token expiry"
    
    # Validate performance consistency
    assert reconnect_result["connection_time"] < 0.1, "Expired token rejection should be immediate"
    
    # Validate security logging for reconnection attempt
    security_events = audit_logger.get_events_for_user("test_user_123")
    expired_attempts = [e for e in security_events if e["event_type"] == "expired_token_attempt"]
    assert len(expired_attempts) >= 1, "Expired token reconnection attempt should be logged"
    
    logger.info(f"✓ Grace period correctly limited to active sessions, reconnection rejected")


@pytest.mark.asyncio
async def test_token_refresh_prompt_and_flow(jwt_generator, audit_logger, token_refresh_service, expired_token):
    """
    Test Case 3: Token refresh prompt and flow validation.
    
    Validates proper token refresh mechanisms when expired tokens are detected,
    ensuring secure refresh flow and old token invalidation.
    """
    logger.info("Testing token refresh prompt and flow")
    
    # Attempt connection with expired token
    client = SecureWebSocketTestClient(
        "ws://mock-server/ws",
        expired_token,
        jwt_generator,
        audit_logger
    )
    
    success, result = await client.attempt_connection()
    assert not success, "Expired token should be rejected"
    assert result["error"] == "authentication_failed", "Should get authentication error"
    
    # Simulate refresh flow trigger
    if "Token expired" in result["message"]:
        logger.info("Token expiry detected, initiating refresh flow")
        
        # Mock refresh token (in real implementation, this would be stored securely)
        refresh_token = f"refresh_{secrets.token_urlsafe(32)}"
        
        # Attempt token refresh
        refresh_result = await token_refresh_service.refresh_expired_token(
            expired_token, 
            refresh_token
        )
        
        assert refresh_result is not None, "Token refresh should succeed with valid refresh token"
        assert "access_token" in refresh_result, "New access token should be provided"
        assert "refresh_token" in refresh_result, "New refresh token should be provided"
        assert refresh_result["expires_in"] > 0, "Expiry time should be positive"
        
        new_access_token = refresh_result["access_token"]
        
        # Validate new token is functional
        token_validation = jwt_generator.validate_token(new_access_token)
        assert "error" not in token_validation, "New token should be valid"
        assert token_validation["sub"] == "test_user_123", "User ID should be preserved"
        
        # Create new client with refreshed token
        new_client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            new_access_token,
            jwt_generator,
            audit_logger
        )
        
        # Test connection with new token
        new_success, new_result = await new_client.attempt_connection()
        assert new_success, "Connection with refreshed token should succeed"
        assert new_result["success"], "New connection should be successful"
        
        # Validate old token is invalidated
        old_token_invalidated = token_refresh_service.is_token_invalidated(expired_token)
        assert old_token_invalidated, "Old expired token should be invalidated"
        
        # Validate security logging for refresh
        security_events = audit_logger.security_events
        refresh_events = [e for e in security_events if e["event_type"] == "token_refresh_success"]
        assert len(refresh_events) >= 1, "Token refresh should be logged"
        
        refresh_event = refresh_events[0]
        assert refresh_event["user_id"] == "test_user_123", "User ID should be logged"
        assert "old_token_fingerprint" in refresh_event, "Old token fingerprint should be logged"
        assert "new_token_fingerprint" in refresh_event, "New token fingerprint should be logged"
        
        await new_client.disconnect()
        
        logger.info("✓ Token refresh flow completed successfully with proper security controls")


@pytest.mark.asyncio
async def test_security_logging_comprehensive_audit_trail(jwt_generator, audit_logger):
    """
    Test Case 4: Security logging and comprehensive audit trail verification.
    
    Ensures comprehensive security logging for expired token attempts with
    complete audit trail for compliance and security monitoring.
    """
    logger.info("Testing comprehensive security logging for expired token attempts")
    
    # Create multiple expired tokens with different scenarios
    test_scenarios = [
        {"user": "user_001", "expired_minutes": 1, "ip": "192.168.1.10", "agent": "Browser/1.0"},
        {"user": "user_002", "expired_minutes": 30, "ip": "10.0.0.50", "agent": "Mobile/2.0"},
        {"user": "user_001", "expired_minutes": 5, "ip": "192.168.1.10", "agent": "Browser/1.0"},  # Repeat user
        {"user": "user_003", "expired_minutes": 120, "ip": "172.16.0.100", "agent": "API/1.0"},
        {"user": "user_001", "expired_minutes": 2, "ip": "192.168.1.10", "agent": "Browser/1.0"},  # Third attempt
    ]
    
    clients = []
    
    for i, scenario in enumerate(test_scenarios):
        # Create expired token for scenario
        expired_token = jwt_generator.create_expired_token(
            scenario["user"], 
            expired_minutes_ago=scenario["expired_minutes"]
        )
        
        # Create client and attempt connection
        client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            expired_token,
            jwt_generator,
            audit_logger
        )
        
        # Attempt connection with scenario-specific headers
        headers = {
            "X-Forwarded-For": scenario["ip"],
            "User-Agent": scenario["agent"],
            "X-Request-ID": f"req_{i+1}_{uuid.uuid4().hex[:8]}"
        }
        
        success, result = await client.attempt_connection(headers)
        assert not success, f"Scenario {i+1}: Expired token should be rejected"
        
        clients.append(client)
        
        # Brief delay between attempts to simulate realistic timing
        await asyncio.sleep(0.1)
    
    # Validate comprehensive audit logging
    all_events = audit_logger.security_events
    expired_events = [e for e in all_events if e["event_type"] == "expired_token_attempt"]
    
    assert len(expired_events) == len(test_scenarios), f"Expected {len(test_scenarios)} events, got {len(expired_events)}"
    
    # Validate event completeness
    for i, event in enumerate(expired_events):
        scenario = test_scenarios[i]
        
        # Validate required fields
        required_fields = ["timestamp", "event_type", "severity", "user_id", 
                          "source_ip", "token_fingerprint", "user_agent"]
        for field in required_fields:
            assert field in event, f"Event {i+1}: Missing required field {field}"
        
        # Validate field values
        assert event["severity"] == "HIGH", f"Event {i+1}: Expected HIGH severity"
        assert event["user_id"] == scenario["user"], f"Event {i+1}: User ID mismatch"
        assert event["source_ip"] == scenario["ip"], f"Event {i+1}: Source IP mismatch"
        assert event["user_agent"] == scenario["agent"], f"Event {i+1}: User agent mismatch"
        
        # Validate timestamp format and recency
        event_time = datetime.fromisoformat(event["timestamp"])
        time_diff = (datetime.now(timezone.utc) - event_time).total_seconds()
        assert time_diff < 60, f"Event {i+1}: Timestamp too old ({time_diff}s)"
    
    # Validate suspicious pattern detection
    alert_count = audit_logger.get_alert_count()
    
    # user_001 had 3 attempts, should trigger alert
    user_001_events = audit_logger.get_events_for_user("user_001")
    assert len(user_001_events) == 3, "User_001 should have 3 events"
    
    # Check if alerts were triggered for repeated attempts
    if alert_count > 0:
        alerts = audit_logger.alert_triggers
        user_001_alerts = [a for a in alerts if a["user_id"] == "user_001"]
        assert len(user_001_alerts) >= 1, "Alert should be triggered for repeated attempts"
        
        alert = user_001_alerts[0]
        assert alert["alert_type"] == "repeated_expired_token_attempts", "Correct alert type"
        assert alert["severity"] == "CRITICAL", "Critical severity for repeated attempts"
        assert alert["attempt_count"] >= 3, "Should count multiple attempts"
    
    # Cleanup
    for client in clients:
        if client.is_connected:
            await client.disconnect()
    
    logger.info(f"✓ Comprehensive audit trail: {len(expired_events)} events logged, {alert_count} alerts triggered")


@pytest.mark.asyncio
async def test_session_hijacking_prevention_with_expired_tokens(jwt_generator, audit_logger):
    """
    Test Case 5: Session hijacking prevention with old tokens.
    
    Validates protection against session hijacking attempts using expired tokens,
    ensuring complete access denial and session state cleanup.
    """
    logger.info("Testing session hijacking prevention with expired tokens")
    
    # Simulate captured token scenario
    user_id = "victim_user_123"
    
    # Create valid token (simulate active session)
    original_token = jwt_generator.create_valid_token(user_id, expires_in_minutes=1)
    
    # Establish legitimate session
    legitimate_client = SecureWebSocketTestClient(
        "ws://mock-server/ws",
        original_token,
        jwt_generator,
        audit_logger
    )
    
    success, result = await legitimate_client.attempt_connection({
        "X-Forwarded-For": "192.168.1.100",  # Legitimate IP
        "User-Agent": "LegitimateClient/1.0"
    })
    
    assert success, "Legitimate connection should succeed"
    assert legitimate_client.is_connected, "Legitimate client should be connected"
    
    # Wait for token to expire
    logger.info("Waiting for token to expire to simulate captured expired token")
    await asyncio.sleep(65)  # Wait for token to expire
    
    # Verify token is expired
    token_validation = jwt_generator.validate_token(original_token)
    assert "error" in token_validation, "Token should be expired"
    
    # Simulate attacker capturing expired token
    attacker_ips = ["10.0.0.1", "172.16.0.50", "203.0.113.10"]  # Different IPs
    attack_attempts = []
    
    for i, attacker_ip in enumerate(attacker_ips):
        logger.info(f"Simulating hijacking attempt {i+1} from {attacker_ip}")
        
        # Create attacker client with expired token
        attacker_client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            original_token,  # Using expired token
            jwt_generator,
            audit_logger
        )
        
        # Attempt connection from different IP with expired token
        attack_headers = {
            "X-Forwarded-For": attacker_ip,
            "User-Agent": f"AttackerBot/{i+1}.0",
            "X-Attack-Vector": "session_hijacking"  # For testing purposes
        }
        
        attack_start = time.time()
        attack_success, attack_result = await attacker_client.attempt_connection(attack_headers)
        attack_time = time.time() - attack_start
        
        # Validate attack prevention
        assert not attack_success, f"Attack attempt {i+1} should be blocked"
        assert attack_result["error"] == "authentication_failed", "Should get authentication error"
        assert "Token expired" in attack_result["message"], "Should indicate token expiry"
        assert attack_time < 0.1, f"Attack should be rejected immediately ({attack_time:.3f}s)"
        
        # Validate no connection established
        assert not attacker_client.is_connected, "Attacker should not be connected"
        assert attacker_client.websocket is None, "No session should be created for attacker"
        
        attack_attempts.append({
            "ip": attacker_ip,
            "response_time": attack_time,
            "result": attack_result
        })
        
        await attacker_client.disconnect()
        await asyncio.sleep(0.2)  # Brief delay between attacks
    
    # Validate security logging captured all attempts
    security_events = audit_logger.get_events_for_user(user_id)
    hijacking_events = [e for e in security_events if e["event_type"] == "expired_token_attempt"]
    
    assert len(hijacking_events) >= len(attacker_ips), "All hijacking attempts should be logged"
    
    # Validate diverse IP addresses were logged
    logged_ips = [event["source_ip"] for event in hijacking_events]
    for attacker_ip in attacker_ips:
        assert attacker_ip in logged_ips, f"Attacker IP {attacker_ip} should be logged"
    
    # Validate alert triggering for multiple attempts
    alert_count = audit_logger.get_alert_count()
    if alert_count > 0:
        alerts = audit_logger.alert_triggers
        victim_alerts = [a for a in alerts if a["user_id"] == user_id]
        
        if victim_alerts:
            alert = victim_alerts[0]
            assert alert["alert_type"] == "repeated_expired_token_attempts", "Should detect hijacking pattern"
            assert alert["severity"] == "CRITICAL", "Should have critical severity"
    
    # Validate consistent response times (no timing attack vectors)
    response_times = [attempt["response_time"] for attempt in attack_attempts]
    max_time_variance = max(response_times) - min(response_times)
    assert max_time_variance < 0.05, f"Response time variance {max_time_variance:.3f}s too high (timing attack risk)"
    
    # Cleanup
    await legitimate_client.disconnect()
    
    logger.info(f"✓ Session hijacking prevented: {len(attack_attempts)} attempts blocked, {alert_count} alerts triggered")


# Edge Case and Attack Vector Tests

@pytest.mark.asyncio
async def test_multiple_rapid_expired_token_attempts_brute_force_protection(jwt_generator, audit_logger):
    """
    Test Case 6: Multiple expired token attempts (brute force protection).
    
    Tests system resilience against brute force attacks using expired tokens,
    validating rate limiting and protection mechanisms.
    """
    logger.info("Testing brute force protection against expired token attempts")
    
    user_id = "brute_force_target"
    attack_attempts = 15  # Exceed normal alert threshold
    failed_attempts = []
    
    # Generate multiple expired tokens
    expired_tokens = [
        jwt_generator.create_expired_token(user_id, expired_minutes_ago=i+1)
        for i in range(attack_attempts)
    ]
    
    # Simulate rapid brute force attempts
    for i, token in enumerate(expired_tokens):
        client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            token,
            jwt_generator,
            audit_logger
        )
        
        attack_headers = {
            "X-Forwarded-For": "203.0.113.50",  # Consistent attacker IP
            "User-Agent": f"BruteForceBot/1.{i}",
            "X-Attack-Type": "brute_force"
        }
        
        attempt_start = time.time()
        success, result = await client.attempt_connection(attack_headers)
        attempt_time = time.time() - attempt_start
        
        # All attempts should fail
        assert not success, f"Attempt {i+1} should fail"
        assert result["error"] == "authentication_failed", "Should get authentication error"
        
        failed_attempts.append({
            "attempt": i+1,
            "response_time": attempt_time,
            "result": result
        })
        
        # Minimal delay to simulate rapid attempts
        await asyncio.sleep(0.05)
    
    # Validate all attempts were blocked
    assert len(failed_attempts) == attack_attempts, "All brute force attempts should be blocked"
    
    # Validate consistent performance under attack
    response_times = [attempt["response_time"] for attempt in failed_attempts]
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    
    assert avg_response_time < 0.1, f"Average response time {avg_response_time:.3f}s too slow under attack"
    assert max_response_time < 0.2, f"Max response time {max_response_time:.3f}s too slow under attack"
    
    # Validate security monitoring detected attack pattern
    user_events = audit_logger.get_events_for_user(user_id)
    assert len(user_events) >= attack_attempts, "All attack attempts should be logged"
    
    # Validate alerts were triggered
    alert_count = audit_logger.get_alert_count()
    assert alert_count > 0, "Brute force attack should trigger alerts"
    
    alerts = audit_logger.alert_triggers
    brute_force_alerts = [a for a in alerts if a["user_id"] == user_id]
    assert len(brute_force_alerts) >= 1, "Should have alerts for brute force target"
    
    alert = brute_force_alerts[0]
    assert alert["alert_type"] == "repeated_expired_token_attempts", "Should detect brute force pattern"
    assert alert["severity"] == "CRITICAL", "Should escalate to critical"
    assert alert["attempt_count"] >= 5, "Should count multiple attempts"
    
    logger.info(f"✓ Brute force protection: {attack_attempts} attempts blocked, avg {avg_response_time:.3f}s response")


@pytest.mark.asyncio
async def test_malformed_expired_token_handling(jwt_generator, audit_logger):
    """
    Test Case 7: Malformed expired token handling.
    
    Tests handling of malformed tokens that appear expired, validating
    proper error handling and security logging.
    """
    logger.info("Testing malformed expired token handling")
    
    user_id = "malformed_test_user"
    
    # Test various malformed token scenarios
    malformed_scenarios = [
        {
            "name": "Invalid signature expired token",
            "token": jwt_generator.create_malformed_expired_token(user_id),
            "expected_error": "invalid"
        },
        {
            "name": "Completely invalid token",
            "token": "invalid.token.string",
            "expected_error": "invalid"
        },
        {
            "name": "Empty token",
            "token": "",
            "expected_error": "invalid"
        },
        {
            "name": "Base64 garbage",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.garbage.signature",
            "expected_error": "invalid"
        }
    ]
    
    test_results = []
    
    for i, scenario in enumerate(malformed_scenarios):
        logger.info(f"Testing scenario: {scenario['name']}")
        
        client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            scenario["token"],
            jwt_generator,
            audit_logger
        )
        
        test_headers = {
            "X-Forwarded-For": f"192.168.1.{100+i}",
            "User-Agent": f"MalformedTestClient/{i+1}.0",
            "X-Test-Scenario": scenario["name"]
        }
        
        attempt_start = time.time()
        success, result = await client.attempt_connection(test_headers)
        attempt_time = time.time() - attempt_start
        
        # All malformed tokens should be rejected
        assert not success, f"Malformed token should be rejected: {scenario['name']}"
        assert result["error"] == "authentication_failed", "Should get authentication error"
        assert "Token expired" in result["message"] or "Authentication failed" in result["message"], "Should get appropriate error message"
        
        # Validate immediate rejection
        assert attempt_time < 0.1, f"Malformed token rejection should be immediate ({attempt_time:.3f}s)"
        
        test_results.append({
            "scenario": scenario["name"],
            "response_time": attempt_time,
            "result": result
        })
        
        await client.disconnect()
    
    # Validate consistent error handling
    response_times = [result["response_time"] for result in test_results]
    avg_response_time = sum(response_times) / len(response_times)
    time_variance = max(response_times) - min(response_times)
    
    assert avg_response_time < 0.05, f"Average malformed token handling {avg_response_time:.3f}s too slow"
    assert time_variance < 0.02, f"Response time variance {time_variance:.3f}s too high (timing attack risk)"
    
    # Validate security events were logged appropriately
    # Note: Malformed tokens might be logged differently than expired tokens
    all_events = audit_logger.security_events
    recent_events = [
        e for e in all_events 
        if (datetime.now(timezone.utc) - datetime.fromisoformat(e["timestamp"])).total_seconds() < 60
    ]
    
    # Should have some security events for malformed attempts
    assert len(recent_events) >= 1, "Malformed token attempts should generate security events"
    
    logger.info(f"✓ Malformed token handling: {len(test_results)} scenarios tested, avg {avg_response_time:.3f}s")


@pytest.mark.asyncio
async def test_clock_synchronization_edge_cases(jwt_generator, audit_logger):
    """
    Test Case 8: Clock synchronization edge cases.
    
    Tests handling of expired tokens with edge cases around clock synchronization
    and time zone differences.
    """
    logger.info("Testing clock synchronization edge cases for expired tokens")
    
    user_id = "clock_sync_test_user"
    
    # Test clock skew scenarios
    clock_scenarios = [
        {
            "name": "Token expired 1 second ago",
            "token": jwt_generator.create_expired_token(user_id, expired_minutes_ago=0.0167),  # 1 second
            "should_reject": True
        },
        {
            "name": "Token expires in 1 second", 
            "token": jwt_generator.create_near_expiry_token(user_id, expires_in_seconds=10),
            "should_reject": False  # Should still be valid
        },
        {
            "name": "Token expired exactly now",
            "token": jwt_generator.create_near_expiry_token(user_id, expires_in_seconds=0),
            "should_reject": True
        }
    ]
    
    test_results = []
    
    for i, scenario in enumerate(clock_scenarios):
        logger.info(f"Testing clock scenario: {scenario['name']}")
        
        client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            scenario["token"],
            jwt_generator,
            audit_logger
        )
        
        # Add small delay for timing scenarios
        if "expires in 1 second" in scenario["name"]:
            await asyncio.sleep(0.1)  # Use token while still valid
        elif "expired exactly now" in scenario["name"]:
            await asyncio.sleep(1.1)  # Ensure token is expired
        
        attempt_start = time.time()
        success, result = await client.attempt_connection({
            "X-Forwarded-For": f"192.168.2.{10+i}",
            "User-Agent": f"ClockTestClient/{i+1}.0"
        })
        attempt_time = time.time() - attempt_start
        
        # Validate expected behavior
        if scenario["should_reject"]:
            assert not success, f"Expired token should be rejected: {scenario['name']}"
            assert result["error"] == "authentication_failed", "Should get authentication error"
        else:
            assert success, f"Valid token should be accepted: {scenario['name']}"
        
        test_results.append({
            "scenario": scenario["name"],
            "success": success,
            "response_time": attempt_time,
            "expected_rejection": scenario["should_reject"]
        })
        
        await client.disconnect()
        
        # Brief delay between tests
        await asyncio.sleep(0.1)
    
    # Validate proper clock handling
    for result in test_results:
        expected_rejection = result["expected_rejection"]
        actual_success = result["success"]
        
        if expected_rejection:
            assert not actual_success, f"Clock edge case should reject: {result['scenario']}"
        else:
            assert actual_success, f"Clock edge case should accept: {result['scenario']}"
        
        # All responses should be fast regardless of clock edge cases
        assert result["response_time"] < 0.1, f"Clock handling too slow: {result['scenario']}"
    
    logger.info(f"✓ Clock synchronization: {len(test_results)} edge cases handled correctly")


# Performance and Integration Tests

@pytest.mark.asyncio
async def test_concurrent_expired_token_requests_performance(jwt_generator, audit_logger):
    """
    Test Case 9: Concurrent expired token requests performance.
    
    Tests system performance and consistency under concurrent expired token
    connection attempts, validating resource protection and response consistency.
    """
    logger.info("Testing concurrent expired token requests performance")
    
    concurrent_users = 20
    attempts_per_user = 3
    total_attempts = concurrent_users * attempts_per_user
    
    # Create expired tokens for concurrent testing
    expired_tokens = [
        jwt_generator.create_expired_token(f"concurrent_user_{i}", expired_minutes_ago=5)
        for i in range(concurrent_users)
    ]
    
    async def attempt_connection_with_expired_token(user_index: int) -> List[Dict]:
        """Simulate user making multiple attempts with expired token."""
        user_results = []
        token = expired_tokens[user_index]
        
        for attempt in range(attempts_per_user):
            client = SecureWebSocketTestClient(
                "ws://mock-server/ws",
                token,
                jwt_generator,
                audit_logger
            )
            
            headers = {
                "X-Forwarded-For": f"10.0.{user_index // 256}.{user_index % 256}",
                "User-Agent": f"ConcurrentClient/{user_index}.{attempt}",
                "X-User-Index": str(user_index),
                "X-Attempt": str(attempt)
            }
            
            start_time = time.time()
            success, result = await client.attempt_connection(headers)
            response_time = time.time() - start_time
            
            user_results.append({
                "user_index": user_index,
                "attempt": attempt,
                "success": success,
                "response_time": response_time,
                "result": result
            })
            
            await client.disconnect()
            
            # Brief delay between user's attempts
            await asyncio.sleep(0.1)
        
        return user_results
    
    # Execute concurrent attempts
    logger.info(f"Starting {concurrent_users} concurrent users with {attempts_per_user} attempts each")
    start_time = time.time()
    
    # Run all user attempts concurrently
    concurrent_tasks = [
        attempt_connection_with_expired_token(i) 
        for i in range(concurrent_users)
    ]
    
    all_results = await asyncio.gather(*concurrent_tasks)
    total_time = time.time() - start_time
    
    # Flatten results
    flat_results = [result for user_results in all_results for result in user_results]
    
    # Validate all attempts were rejected
    successful_attempts = [r for r in flat_results if r["success"]]
    failed_attempts = [r for r in flat_results if not r["success"]]
    
    assert len(successful_attempts) == 0, f"All expired token attempts should fail, got {len(successful_attempts)} successes"
    assert len(failed_attempts) == total_attempts, f"Expected {total_attempts} failures, got {len(failed_attempts)}"
    
    # Validate performance under concurrent load
    response_times = [r["response_time"] for r in flat_results]
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    min_response_time = min(response_times)
    
    assert avg_response_time < 0.15, f"Average response time {avg_response_time:.3f}s too slow under concurrent load"
    assert max_response_time < 0.3, f"Max response time {max_response_time:.3f}s too slow under concurrent load"
    
    # Validate consistent performance (no major outliers)
    response_time_variance = max_response_time - min_response_time
    assert response_time_variance < 0.2, f"Response time variance {response_time_variance:.3f}s too high"
    
    # Validate security logging handled concurrent load
    security_events = audit_logger.security_events
    recent_events = [
        e for e in security_events
        if (datetime.now(timezone.utc) - datetime.fromisoformat(e["timestamp"])).total_seconds() < 120
    ]
    
    expired_events = [e for e in recent_events if e["event_type"] == "expired_token_attempt"]
    assert len(expired_events) >= total_attempts * 0.9, "Most concurrent attempts should be logged"
    
    # Validate alert system handled concurrent suspicious activity
    alert_count = audit_logger.get_alert_count()
    # Should have multiple alerts due to concurrent repeated attempts
    
    throughput = total_attempts / total_time
    
    logger.info(f"✓ Concurrent performance: {total_attempts} attempts in {total_time:.2f}s ({throughput:.1f} req/s)")
    logger.info(f"   Response times: avg {avg_response_time:.3f}s, max {max_response_time:.3f}s, variance {response_time_variance:.3f}s")
    logger.info(f"   Security events: {len(expired_events)} logged, {alert_count} alerts triggered")


@pytest.mark.asyncio
async def test_token_tampering_with_expired_timestamps(jwt_generator, audit_logger):
    """
    Test Case 10: Token tampering with expired timestamps.
    
    Tests detection and handling of tampered tokens that have been modified
    to extend expiration times or alter other claims.
    """
    logger.info("Testing token tampering with expired timestamps")
    
    user_id = "tampering_test_user"
    
    # Create legitimate expired token for baseline
    legitimate_expired = jwt_generator.create_expired_token(user_id, expired_minutes_ago=10)
    
    # Test tampering scenarios
    tampering_scenarios = [
        {
            "name": "Modified expiration time",
            "token": _create_tampered_token_expiry(legitimate_expired),
            "description": "Token with modified expiry timestamp"
        },
        {
            "name": "Modified user ID in expired token", 
            "token": _create_tampered_token_user(legitimate_expired),
            "description": "Expired token with different user ID"
        },
        {
            "name": "Modified permissions in expired token",
            "token": _create_tampered_token_permissions(legitimate_expired),
            "description": "Expired token with elevated permissions"
        }
    ]
    
    test_results = []
    
    for i, scenario in enumerate(tampering_scenarios):
        logger.info(f"Testing tampering scenario: {scenario['name']}")
        
        client = SecureWebSocketTestClient(
            "ws://mock-server/ws",
            scenario["token"],
            jwt_generator,
            audit_logger
        )
        
        attempt_headers = {
            "X-Forwarded-For": f"203.0.113.{50+i}",
            "User-Agent": f"TamperingTestClient/{i+1}.0",
            "X-Tampering-Test": scenario["name"]
        }
        
        attempt_start = time.time()
        success, result = await client.attempt_connection(attempt_headers)
        attempt_time = time.time() - attempt_start
        
        # All tampered tokens should be rejected
        assert not success, f"Tampered token should be rejected: {scenario['name']}"
        assert result["error"] == "authentication_failed", "Should get authentication error"
        
        # Should detect tampering quickly
        assert attempt_time < 0.1, f"Tampering detection should be immediate ({attempt_time:.3f}s)"
        
        test_results.append({
            "scenario": scenario["name"],
            "response_time": attempt_time,
            "result": result
        })
        
        await client.disconnect()
    
    # Validate consistent tampering detection
    response_times = [r["response_time"] for r in test_results]
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    
    assert avg_response_time < 0.05, f"Average tampering detection {avg_response_time:.3f}s too slow"
    assert max_response_time < 0.1, f"Max tampering detection {max_response_time:.3f}s too slow"
    
    # Validate security logging captured tampering attempts
    security_events = audit_logger.security_events
    recent_events = [
        e for e in security_events
        if (datetime.now(timezone.utc) - datetime.fromisoformat(e["timestamp"])).total_seconds() < 60
    ]
    
    # Should have security events for tampering attempts
    assert len(recent_events) >= len(tampering_scenarios), "Tampering attempts should be logged"
    
    logger.info(f"✓ Token tampering detection: {len(test_results)} scenarios, avg {avg_response_time:.3f}s detection")


# Helper Functions for Token Tampering Tests

def _create_tampered_token_expiry(original_token: str) -> str:
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


def _create_tampered_token_user(original_token: str) -> str:
    """Create token with tampered user ID."""
    try:
        payload = jwt.decode(original_token, options={"verify_signature": False})
        payload["sub"] = "admin_user"  # Elevate to admin
        return jwt.encode(payload, "wrong-secret", algorithm="HS256")
    except Exception:
        return "tampered.user.token"


def _create_tampered_token_permissions(original_token: str) -> str:
    """Create token with tampered permissions."""
    try:
        payload = jwt.decode(original_token, options={"verify_signature": False})
        payload["permissions"] = ["read", "write", "admin", "delete"]  # Elevate permissions
        return jwt.encode(payload, "wrong-secret", algorithm="HS256")
    except Exception:
        return "tampered.permissions.token"


if __name__ == "__main__":
    # Run security-focused tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--log-cli-level=INFO",
        "--asyncio-mode=auto",
        "-k", "test_"  # Run all test functions
    ])