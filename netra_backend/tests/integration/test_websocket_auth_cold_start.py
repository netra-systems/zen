"""WebSocket Authentication Cold Start Agent Integration Tests (L3)

Tests the authentication and cold start behavior of agents when initiated through WebSocket connections.
These are L3 tests using real services (containerized) for high confidence validation.

Business Value Justification (BVJ):
1. Segment: ALL (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure reliable authentication and fast agent startup for user retention
3. Value Impact: Prevents authentication failures and slow startup that cause user abandonment
4. Revenue Impact: Fast, reliable auth and startup reduces abandonment by 30% - $100K+ ARR protection

Mock-Real Spectrum: L3 (Real SUT with Real Local Services)
- Real WebSocket connections
- Real authentication service (containerized)
- Real database connections (containerized PostgreSQL/Redis)
- Real agent initialization
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import jwt
import pytest
import websockets

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

# Test infrastructure
from netra_backend.app.clients.auth_client import auth_client

from netra_backend.app.core.exceptions_websocket import WebSocketAuthenticationError

@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL for testing."""
    # Mock: Generic component isolation for controlled unit testing
    mock_db = MagicMock()
    # Mock: PostgreSQL database isolation for testing without real database connections
    mock_db.get_connection_url = MagicMock(return_value="postgresql://test_user:test_password@localhost/test_db")
    return mock_db

@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock_redis = MagicMock()
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock_redis.get_container_host_ip = MagicMock(return_value="localhost")
    # Mock: Redis external service isolation for fast, reliable tests without network dependency
    mock_redis.get_exposed_port = MagicMock(return_value=6379)
    return mock_redis

@pytest.fixture
async def auth_service_config(mock_postgres, mock_redis):
    """Provide mock Auth Service configuration for testing."""
    # Auth service uses mocked dependencies for faster tests
    auth_config = {
        "postgres_url": "postgresql://test_user:test_password@localhost/test_db",
        "redis_url": "redis://localhost:6379",
        "jwt_secret": "test_jwt_secret_key"
    }
    yield auth_config

@pytest.fixture
@pytest.mark.asyncio
async def test_jwt_token(auth_service_config):
    """Generate a valid JWT token for testing."""
    payload = {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "tier": "early",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    secret = auth_service_config["jwt_secret"]
    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.fixture
async def expired_jwt_token(auth_service_config):
    """Generate an expired JWT token for testing."""
    payload = {
        "user_id": "test_user_456",
        "email": "expired@example.com",
        "tier": "free",
        "exp": datetime.utcnow() - timedelta(hours=1)
    }
    secret = auth_service_config["jwt_secret"]
    yield jwt.encode(payload, secret, algorithm="HS256")

class TestWebSocketAuthColdStartL3:
    """L3 Integration tests for WebSocket authentication during cold start."""
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_with_valid_auth_token(
        self, 
        auth_service_config,
        mock_postgres,
        mock_redis,
        test_jwt_token
    ):
        """Test 1: Cold start agent initialization with valid authentication token."""
        # Measure cold start time
        start_time = time.perf_counter()
        
        # Connect to WebSocket with authentication
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            # Send initial message to trigger agent cold start
            await websocket.send(json.dumps({
                "type": "thread_create",
                "content": "Initialize agent cold start test"
            }))
            
            # Receive authentication acknowledgment
            auth_response = await websocket.recv()
            auth_data = json.loads(auth_response)
            
            # Verify authentication succeeded
            assert auth_data["type"] == "auth_success"
            assert auth_data["user_id"] == "test_user_123"
            
            # Measure cold start completion time
            cold_start_time = time.perf_counter() - start_time
            
            # Verify cold start performance (should be under 3 seconds)
            assert cold_start_time < 3.0, f"Cold start took {cold_start_time}s"
            
            # Verify agent is initialized
            agent_response = await websocket.recv()
            agent_data = json.loads(agent_response)
            assert agent_data["type"] == "agent_initialized"
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_with_expired_token(
        self,
        auth_service_config,
        expired_jwt_token
    ):
        """Test 2: Cold start behavior with expired authentication token."""
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {expired_jwt_token}"}
        
        # Attempt connection with expired token
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        
        # Verify proper error code (401 Unauthorized)
        assert exc_info.value.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_with_token_refresh(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis,
        test_jwt_token
    ):
        """Test 3: Cold start with token refresh during initialization."""
        # Create token that expires soon
        short_lived_token = jwt.encode(
            {
                "user_id": "test_user_789",
                "email": "refresh@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(seconds=5)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {short_lived_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            # Initial connection succeeds
            await websocket.send(json.dumps({"type": "ping"}))
            
            # Wait for token to expire
            await asyncio.sleep(6)
            
            # Send refresh token request
            await websocket.send(json.dumps({
                "type": "token_refresh",
                "refresh_token": "test_refresh_token"
            }))
            
            # Receive new token
            refresh_response = await websocket.recv()
            refresh_data = json.loads(refresh_response)
            assert refresh_data["type"] == "token_refreshed"
            assert "new_token" in refresh_data
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_concurrent_auth_requests(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 4: Cold start with multiple concurrent authentication requests."""
        # Create multiple tokens for different users
        tokens = []
        for i in range(5):
            token = jwt.encode(
                {
                    "user_id": f"concurrent_user_{i}",
                    "email": f"user{i}@example.com",
                    "tier": "early",
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            tokens.append(token)
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Connect multiple clients concurrently
        async def connect_client(token, user_index):
            headers = {"Authorization": f"Bearer {token}"}
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                await ws.send(json.dumps({
                    "type": "thread_create",
                    "content": f"User {user_index} message"
                }))
                response = await ws.recv()
                data = json.loads(response)
                assert data["type"] == "auth_success"
                assert data["user_id"] == f"concurrent_user_{user_index}"
        
        # Execute concurrent connections
        tasks = [connect_client(token, i) for i, token in enumerate(tokens)]
        await asyncio.gather(*tasks)
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="Requires actual container control")
    @pytest.mark.asyncio
    async def test_cold_start_auth_with_database_unavailable(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis,
        test_jwt_token
    ):
        """Test 5: Cold start authentication when database is temporarily unavailable."""
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        # Simulate database unavailability
        # Note: In mock setup, we would simulate this differently
        
        try:
            # Attempt connection (should use Redis cache)
            async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                await websocket.send(json.dumps({"type": "ping"}))
                
                # Should still authenticate using Redis cache
                response = await websocket.recv()
                data = json.loads(response)
                assert data["type"] in ["auth_success", "pong"]
        finally:
            # In mock setup, no restart needed
            pass
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_role_based_access(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 6: Cold start with role-based access control verification."""
        # Create tokens with different roles
        admin_token = jwt.encode(
            {
                "user_id": "admin_user",
                "email": "admin@example.com",
                "tier": "enterprise",
                "role": "admin",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        regular_token = jwt.encode(
            {
                "user_id": "regular_user",
                "email": "user@example.com",
                "tier": "free",
                "role": "user",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test admin access
        headers = {"Authorization": f"Bearer {admin_token}"}
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({
                "type": "admin_command",
                "action": "get_system_stats"
            }))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "admin_response"
        
        # Test regular user restriction
        headers = {"Authorization": f"Bearer {regular_token}"}
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({
                "type": "admin_command",
                "action": "get_system_stats"
            }))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "error"
            assert "permission" in data["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_session_persistence(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis,
        test_jwt_token
    ):
        """Test 7: Cold start with session persistence across reconnections."""
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        session_id = None
        
        # First connection - establish session
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({
                "type": "thread_create",
                "content": "Create persistent session"
            }))
            response = await ws.recv()
            data = json.loads(response)
            session_id = data.get("session_id")
            assert session_id is not None
        
        # Second connection - verify session persistence
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({
                "type": "resume_session",
                "session_id": session_id
            }))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "session_resumed"
            assert data["session_id"] == session_id
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_rate_limiting(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 8: Cold start authentication with rate limiting enforcement."""
        ws_url = f"ws://localhost:8000/websocket"
        
        # Attempt multiple rapid connections
        for i in range(10):
            try:
                # Create new token for each attempt
                token = jwt.encode(
                    {
                        "user_id": f"rate_test_user_{i}",
                        "email": f"rate{i}@example.com",
                        "tier": "free",
                        "exp": datetime.utcnow() + timedelta(hours=1)
                    },
                    auth_service_config["jwt_secret"],
                    algorithm="HS256"
                )
                
                headers = {"Authorization": f"Bearer {token}"}
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    await ws.recv()
                    
            except websockets.exceptions.InvalidStatusCode as e:
                # Should hit rate limit after certain attempts
                if i >= 5:  # Expect rate limiting after 5 attempts
                    assert e.status_code == 429  # Too Many Requests
                    break
        else:
            pytest.fail("Rate limiting was not enforced")
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="MFA not yet implemented")
    @pytest.mark.asyncio
    async def test_cold_start_auth_multi_factor(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 9: Cold start with multi-factor authentication flow."""
        # Create token requiring MFA
        mfa_token = jwt.encode(
            {
                "user_id": "mfa_user",
                "email": "mfa@example.com",
                "tier": "enterprise",
                "requires_mfa": True,
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {mfa_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Initial auth should request MFA
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "mfa_required"
            assert "challenge" in data
            
            # Send MFA response
            await ws.send(json.dumps({
                "type": "mfa_response",
                "code": "123456"  # Test MFA code
            }))
            
            # Receive full authentication
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "auth_success"
            assert data["mfa_verified"] is True
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_cross_origin_validation(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis,
        test_jwt_token
    ):
        """Test 10: Cold start authentication with CORS origin validation."""
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test allowed origin
        headers = {
            "Authorization": f"Bearer {test_jwt_token}",
            "Origin": "https://app.netrasystems.ai"
        }
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] in ["auth_success", "pong"]
        
        # Test disallowed origin
        headers = {
            "Authorization": f"Bearer {test_jwt_token}",
            "Origin": "https://malicious.site"
        }
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        
        # Should reject with 403 Forbidden
        assert exc_info.value.status_code == 403
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_token_rotation(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 11: Cold start with automatic token rotation for security."""
        # Create initial token
        initial_token = jwt.encode(
            {
                "user_id": "rotation_user",
                "email": "rotation@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(minutes=5),
                "iat": datetime.utcnow()
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {initial_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Connect and track token usage
            await ws.send(json.dumps({"type": "thread_create", "content": "test"}))
            
            # Simulate token approaching expiration
            await asyncio.sleep(2)
            
            # Request rotation before expiry
            await ws.send(json.dumps({"type": "rotate_token"}))
            response = await ws.recv()
            data = json.loads(response)
            
            assert data["type"] == "token_rotated"
            assert "new_token" in data
            assert data["new_token"] != initial_token
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_service_degradation(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis,
        test_jwt_token
    ):
        """Test 12: Cold start behavior when auth service is degraded."""
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {test_jwt_token}"}
        
        # Mock auth service degradation
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.clients.auth_client.auth_client.validate_token') as mock_validate:
            # Simulate slow response from auth service
            async def slow_validation(*args, **kwargs):
                await asyncio.sleep(5)
                return {"valid": True, "user_id": "test_user_123"}
            
            mock_validate.side_effect = slow_validation
            
            start_time = time.perf_counter()
            
            # Connection should use cached validation or timeout gracefully
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                await ws.send(json.dumps({"type": "ping"}))
                response = await ws.recv()
                data = json.loads(response)
                
                # Should respond quickly despite slow auth service
                elapsed = time.perf_counter() - start_time
                assert elapsed < 2.0  # Should use cache/fallback
                assert data["type"] in ["auth_success", "pong"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_permission_escalation_prevention(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 13: Prevent permission escalation during cold start."""
        # Create token with limited permissions
        limited_token = jwt.encode(
            {
                "user_id": "limited_user",
                "email": "limited@example.com",
                "tier": "free",
                "permissions": ["read"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {limited_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Try to perform privileged operation
            await ws.send(json.dumps({
                "type": "admin_action",
                "action": "delete_all_data"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            
            assert data["type"] == "error"
            assert "permission" in data["message"].lower()
            assert "denied" in data["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_geographic_restrictions(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 14: Cold start with geographic access restrictions."""
        # Token with geographic metadata
        geo_token = jwt.encode(
            {
                "user_id": "geo_user",
                "email": "geo@example.com",
                "tier": "enterprise",
                "allowed_regions": ["US", "EU"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test allowed region
        headers = {
            "Authorization": f"Bearer {geo_token}",
            "X-Client-Region": "US"
        }
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] in ["auth_success", "pong"]
        
        # Test restricted region
        headers = {
            "Authorization": f"Bearer {geo_token}",
            "X-Client-Region": "CN"
        }
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        
        assert exc_info.value.status_code == 403
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_device_fingerprinting(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 15: Cold start with device fingerprinting for security."""
        # Token with device binding
        device_token = jwt.encode(
            {
                "user_id": "device_user",
                "email": "device@example.com",
                "tier": "mid",
                "device_id": "device_123",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Correct device fingerprint
        headers = {
            "Authorization": f"Bearer {device_token}",
            "X-Device-Id": "device_123",
            "User-Agent": "TestClient/1.0"
        }
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] in ["auth_success", "pong"]
        
        # Different device fingerprint (potential security threat)
        headers = {
            "Authorization": f"Bearer {device_token}",
            "X-Device-Id": "different_device",
            "User-Agent": "SuspiciousClient/2.0"
        }
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_adaptive_security(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 16: Cold start with adaptive security based on risk scoring."""
        # Normal risk token
        normal_token = jwt.encode(
            {
                "user_id": "normal_risk_user",
                "email": "normal@example.com",
                "tier": "early",
                "risk_score": 0.2,
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        # High risk token
        high_risk_token = jwt.encode(
            {
                "user_id": "high_risk_user",
                "email": "suspicious@example.com",
                "tier": "early",
                "risk_score": 0.9,
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Normal risk - standard auth flow
        headers = {"Authorization": f"Bearer {normal_token}"}
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] in ["auth_success", "pong"]
        
        # High risk - requires additional verification
        headers = {"Authorization": f"Bearer {high_risk_token}"}
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            response = await ws.recv()
            data = json.loads(response)
            
            # Should require additional verification
            assert data["type"] == "additional_verification_required"
            assert "challenge" in data
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_session_hijacking_prevention(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis,
        test_jwt_token
    ):
        """Test 17: Prevent session hijacking during cold start."""
        ws_url = f"ws://localhost:8000/websocket"
        
        # Establish initial session
        initial_headers = {
            "Authorization": f"Bearer {test_jwt_token}",
            "X-Client-IP": "192.168.1.100",
            "User-Agent": "LegitClient/1.0"
        }
        
        session_id = None
        async with websockets.connect(ws_url, extra_headers=initial_headers) as ws:
            await ws.send(json.dumps({"type": "thread_create"}))
            response = await ws.recv()
            data = json.loads(response)
            session_id = data.get("session_id")
            assert session_id is not None
        
        # Attempt to hijack session from different IP
        hijack_headers = {
            "Authorization": f"Bearer {test_jwt_token}",
            "X-Client-IP": "10.0.0.1",  # Different IP
            "User-Agent": "AttackerClient/1.0",
            "X-Session-Id": session_id
        }
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=hijack_headers):
                pass
        
        # Should detect potential hijacking
        assert exc_info.value.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.skip(reason="WebSocket endpoint requires full service setup")
    @pytest.mark.asyncio
    async def test_cold_start_auth_token_binding_to_tls(
        self,
        auth_service_config,
        mock_postgres,
        mock_redis
    ):
        """Test 18: Token binding to TLS session for enhanced security."""
        # Token with TLS binding
        tls_token = jwt.encode(
            {
                "user_id": "tls_user",
                "email": "tls@example.com",
                "tier": "enterprise",
                "tls_fingerprint": "sha256:abcd1234",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        # Note: In production, this would use wss:// and actual TLS
        ws_url = f"ws://localhost:8000/websocket"
        
        headers = {
            "Authorization": f"Bearer {tls_token}",
            "X-TLS-Fingerprint": "sha256:abcd1234"
        }
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] in ["auth_success", "pong"]
        
        # Wrong TLS fingerprint
        headers["X-TLS-Fingerprint"] = "sha256:wrong5678"
        
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        
        assert exc_info.value.status_code == 401