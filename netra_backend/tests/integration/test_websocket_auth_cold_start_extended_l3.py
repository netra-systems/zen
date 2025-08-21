"""Extended WebSocket Authentication Cold Start Agent Integration Tests (L3)

Comprehensive L3 tests with increased depth and breadth for WebSocket authentication during cold start.
These tests focus on challenging edge cases, security vulnerabilities, and real-world failure scenarios.

Business Value Justification (BVJ):
1. Segment: ALL (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure bulletproof authentication under extreme conditions
3. Value Impact: Prevents security breaches and authentication bypasses that could cost millions
4. Revenue Impact: Security incidents can cause 50%+ customer churn - $500K+ ARR protection

Mock-Real Spectrum: L3 (Real SUT with Real Local Services)
- Real WebSocket connections with complex scenarios
- Real authentication service with edge cases
- Real database connections with failure simulation
- Real agent initialization under stress
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import base64
import hashlib
import hmac
import json
import os
import random
import socket
import string
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
import websockets

# Add project root to path


# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

# Test infrastructure imports
from clients.auth_client import auth_client

from netra_backend.app.core.exceptions_websocket import WebSocketAuthenticationError


class TestWebSocketAuthColdStartExtendedL3:
    """Extended L3 Integration tests for WebSocket authentication during cold start."""
    
    # ==================== TEST 1: COLD START WITH VALID AUTH (DEPTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cold_start_valid_auth_memory_pressure(self, auth_service_config, mock_postgres, mock_redis):
        """Test 1.1 (Depth): Cold start under extreme memory pressure conditions."""
        # Simulate memory pressure by creating large objects
        memory_hog = [bytearray(10 * 1024 * 1024) for _ in range(50)]  # 500MB
        
        token = jwt.encode(
            {
                "user_id": "memory_test_user",
                "email": "memory@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        start_time = time.perf_counter()
        
        try:
            async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                # Send multiple large messages during cold start
                for i in range(10):
                    large_payload = {
                        "type": "thread_create",
                        "content": "x" * (1024 * 100),  # 100KB message
                        "metadata": {"index": i}
                    }
                    await websocket.send(json.dumps(large_payload))
                
                # Verify cold start completes despite memory pressure
                response = await websocket.recv()
                data = json.loads(response)
                
                cold_start_time = time.perf_counter() - start_time
                
                assert data["type"] == "auth_success"
                # Should handle memory pressure gracefully, maybe slower but not failing
                assert cold_start_time < 10.0, f"Cold start too slow under memory pressure: {cold_start_time}s"
                
        finally:
            del memory_hog  # Clean up memory
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cold_start_valid_auth_clock_skew(self, auth_service_config, mock_postgres, mock_redis):
        """Test 1.2 (Depth): Cold start with significant clock skew between client and server."""
        # Create token with future timestamp (simulating clock skew)
        future_time = datetime.utcnow() + timedelta(minutes=5)
        
        token = jwt.encode(
            {
                "user_id": "clock_skew_user",
                "email": "skew@example.com",
                "tier": "mid",
                "iat": future_time,  # Issued in the future
                "exp": future_time + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Should handle reasonable clock skew (up to 5 minutes)
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            data = json.loads(response)
            
            # System should accept tokens with reasonable clock skew
            assert data["type"] in ["auth_success", "pong"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cold_start_valid_auth_jwt_algorithm_confusion(self, auth_service_config):
        """Test 1.3 (Depth): Prevent JWT algorithm confusion attacks during cold start."""
        # Try to exploit algorithm confusion vulnerability
        malicious_token = jwt.encode(
            {
                "user_id": "attacker",
                "email": "attacker@evil.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            "none",  # Try to use 'none' algorithm
            algorithm="none"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {malicious_token}"}
        
        # Should reject tokens with 'none' algorithm
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cold_start_valid_auth_connection_pooling(self, auth_service_config, mock_postgres, mock_redis):
        """Test 1.4 (Breadth): Cold start with connection pool exhaustion."""
        tokens = []
        for i in range(100):  # Create many tokens
            token = jwt.encode(
                {
                    "user_id": f"pool_user_{i}",
                    "email": f"pool{i}@example.com",
                    "tier": "early",
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            tokens.append(token)
        
        ws_url = f"ws://localhost:8000/websocket"
        connections = []
        
        try:
            # Open many connections simultaneously to exhaust pool
            for token in tokens[:50]:
                headers = {"Authorization": f"Bearer {token}"}
                ws = await websockets.connect(ws_url, extra_headers=headers)
                connections.append(ws)
            
            # Now try cold start with exhausted pool
            headers = {"Authorization": f"Bearer {tokens[51]}"}
            async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                await websocket.send(json.dumps({"type": "ping"}))
                response = await websocket.recv()
                data = json.loads(response)
                
                # Should handle pool exhaustion gracefully
                assert data["type"] in ["auth_success", "pong"]
                
        finally:
            # Clean up connections
            for ws in connections:
                await ws.close()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cold_start_valid_auth_dns_resolution_delay(self, auth_service_config, mock_postgres, mock_redis):
        """Test 1.5 (Breadth): Cold start with DNS resolution delays."""
        token = jwt.encode(
            {
                "user_id": "dns_delay_user",
                "email": "dns@example.com",
                "tier": "free",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        # Mock DNS resolution delay
        with patch('socket.getaddrinfo') as mock_dns:
            original_getaddrinfo = socket.getaddrinfo
            
            async def delayed_dns(*args, **kwargs):
                await asyncio.sleep(2)  # Simulate DNS delay
                return original_getaddrinfo(*args, **kwargs)
            
            mock_dns.side_effect = delayed_dns
            
            ws_url = f"ws://localhost:8000/websocket"
            headers = {"Authorization": f"Bearer {token}"}
            
            start_time = time.perf_counter()
            
            async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                await websocket.send(json.dumps({"type": "ping"}))
                response = await websocket.recv()
                data = json.loads(response)
                
                elapsed = time.perf_counter() - start_time
                
                assert data["type"] in ["auth_success", "pong"]
                # Should handle DNS delays but complete within reasonable time
                assert elapsed < 15.0
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cold_start_valid_auth_binary_protocol(self, auth_service_config, mock_postgres, mock_redis):
        """Test 1.6 (Breadth): Cold start with binary WebSocket frames."""
        token = jwt.encode(
            {
                "user_id": "binary_user",
                "email": "binary@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            # Send binary frame instead of text
            binary_message = json.dumps({"type": "ping"}).encode('utf-8')
            await websocket.send(binary_message)
            
            response = await websocket.recv()
            
            # Handle both text and binary responses
            if isinstance(response, bytes):
                data = json.loads(response.decode('utf-8'))
            else:
                data = json.loads(response)
            
            assert data["type"] in ["auth_success", "pong", "error"]
    
    # ==================== TEST 2: EXPIRED TOKEN REJECTION (DEPTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_expired_token_replay_attack(self, auth_service_config):
        """Test 2.1 (Depth): Prevent replay attacks with expired tokens."""
        # Create an expired token
        expired_token = jwt.encode(
            {
                "user_id": "replay_user",
                "email": "replay@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() - timedelta(hours=1),
                "nonce": "abc123"  # Add nonce for replay detection
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        # First attempt - should fail
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        assert exc_info.value.status_code == 401
        
        # Second attempt (replay) - should also fail
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        assert exc_info.value.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_expired_token_timing_attack(self, auth_service_config):
        """Test 2.2 (Depth): Verify constant-time validation to prevent timing attacks."""
        valid_but_expired = jwt.encode(
            {
                "user_id": "timing_user",
                "email": "timing@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() - timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        invalid_signature = valid_but_expired[:-10] + "tampered123"
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Measure rejection time for valid-but-expired token
        times_valid = []
        for _ in range(10):
            start = time.perf_counter()
            try:
                headers = {"Authorization": f"Bearer {valid_but_expired}"}
                async with websockets.connect(ws_url, extra_headers=headers):
                    pass
            except websockets.exceptions.InvalidStatusCode:
                pass
            times_valid.append(time.perf_counter() - start)
        
        # Measure rejection time for invalid signature
        times_invalid = []
        for _ in range(10):
            start = time.perf_counter()
            try:
                headers = {"Authorization": f"Bearer {invalid_signature}"}
                async with websockets.connect(ws_url, extra_headers=headers):
                    pass
            except websockets.exceptions.InvalidStatusCode:
                pass
            times_invalid.append(time.perf_counter() - start)
        
        # Times should be similar (constant-time validation)
        avg_valid = sum(times_valid) / len(times_valid)
        avg_invalid = sum(times_invalid) / len(times_invalid)
        
        # Allow 20% variance for network jitter
        assert abs(avg_valid - avg_invalid) / max(avg_valid, avg_invalid) < 0.2
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_expired_token_boundary_conditions(self, auth_service_config):
        """Test 2.3 (Depth): Test token expiration at exact boundary moments."""
        # Token that expires in exactly 1 second
        boundary_token = jwt.encode(
            {
                "user_id": "boundary_user",
                "email": "boundary@example.com",
                "tier": "early",
                "exp": datetime.utcnow() + timedelta(seconds=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {boundary_token}"}
        
        # Should succeed immediately
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] in ["auth_success", "pong"]
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Should now fail
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        assert exc_info.value.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_expired_token_malformed_exp_claim(self, auth_service_config):
        """Test 2.4 (Breadth): Handle malformed expiration claims gracefully."""
        # Various malformed exp claims
        test_cases = [
            {"exp": "not_a_number"},  # String instead of number
            {"exp": -1},  # Negative timestamp
            {"exp": 999999999999999},  # Far future timestamp
            {"exp": None},  # Null value
            # Missing exp claim entirely
            {"user_id": "no_exp_user", "email": "noexp@example.com"}
        ]
        
        ws_url = f"ws://localhost:8000/websocket"
        
        for payload in test_cases:
            if "user_id" not in payload:
                payload.update({
                    "user_id": "malformed_user",
                    "email": "malformed@example.com",
                    "tier": "free"
                })
            
            token = jwt.encode(
                payload,
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # All malformed tokens should be rejected
            with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
                async with websockets.connect(ws_url, extra_headers=headers):
                    pass
            
            assert exc_info.value.status_code in [400, 401]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_expired_token_cache_poisoning(self, auth_service_config, mock_redis):
        """Test 2.5 (Breadth): Prevent cache poisoning with expired tokens."""
        user_id = "cache_poison_user"
        
        # First, use a valid token to populate cache
        valid_token = jwt.encode(
            {
                "user_id": user_id,
                "email": "cache@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            await ws.recv()
        
        # Now try expired token for same user
        expired_token = jwt.encode(
            {
                "user_id": user_id,  # Same user ID
                "email": "cache@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() - timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        # Should not use cached validation for expired token
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_expired_token_error_message_leakage(self, auth_service_config):
        """Test 2.6 (Breadth): Verify no sensitive information in error messages."""
        expired_token = jwt.encode(
            {
                "user_id": "sensitive_user_12345",
                "email": "sensitive@secretcorp.com",
                "tier": "enterprise",
                "internal_id": "SECRET-123-ABC",
                "exp": datetime.utcnow() - timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        # Capture the actual error response
        try:
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                pass
        except websockets.exceptions.InvalidStatusCode as e:
            # Error message should not contain sensitive information
            error_str = str(e)
            assert "sensitive_user_12345" not in error_str
            assert "sensitive@secretcorp.com" not in error_str
            assert "SECRET-123-ABC" not in error_str
            assert e.status_code == 401
    
    # ==================== TEST 3: TOKEN REFRESH (DEPTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_refresh_race_condition(self, auth_service_config, mock_postgres, mock_redis):
        """Test 3.1 (Depth): Handle concurrent token refresh requests (race condition)."""
        initial_token = jwt.encode(
            {
                "user_id": "race_user",
                "email": "race@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(seconds=5)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {initial_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            await asyncio.sleep(4)  # Wait until near expiration
            
            # Send multiple refresh requests simultaneously
            refresh_tasks = []
            for _ in range(10):
                task = websocket.send(json.dumps({
                    "type": "token_refresh",
                    "refresh_token": "test_refresh_token"
                }))
                refresh_tasks.append(task)
            
            await asyncio.gather(*refresh_tasks)
            
            # Should handle race condition - only one refresh should succeed
            refresh_count = 0
            for _ in range(10):
                response = await websocket.recv()
                data = json.loads(response)
                if data["type"] == "token_refreshed":
                    refresh_count += 1
            
            # Only one refresh should succeed, others should be deduplicated
            assert refresh_count == 1
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_refresh_rotation_tracking(self, auth_service_config, mock_postgres, mock_redis):
        """Test 3.2 (Depth): Track token rotation to prevent reuse of old tokens."""
        tokens = []
        
        # Generate initial token
        current_token = jwt.encode(
            {
                "user_id": "rotation_user",
                "email": "rotation@example.com",
                "tier": "early",
                "exp": datetime.utcnow() + timedelta(minutes=1),
                "generation": 0
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        tokens.append(current_token)
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Perform multiple rotations
        for generation in range(1, 5):
            headers = {"Authorization": f"Bearer {current_token}"}
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                await ws.send(json.dumps({
                    "type": "token_refresh",
                    "refresh_token": "test_refresh_token"
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                
                assert data["type"] == "token_refreshed"
                current_token = data["new_token"]
                tokens.append(current_token)
        
        # Try to use old tokens - should all be rejected
        for old_token in tokens[:-1]:
            headers = {"Authorization": f"Bearer {old_token}"}
            
            with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
                async with websockets.connect(ws_url, extra_headers=headers):
                    pass
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_refresh_invalid_refresh_token(self, auth_service_config, mock_postgres, mock_redis):
        """Test 3.3 (Depth): Reject refresh with invalid/expired refresh tokens."""
        access_token = jwt.encode(
            {
                "user_id": "invalid_refresh_user",
                "email": "invalid@example.com",
                "tier": "free",
                "exp": datetime.utcnow() + timedelta(seconds=5)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        test_cases = [
            "expired_refresh_token",
            "invalid_signature_token",
            "",  # Empty refresh token
            "a" * 1000,  # Very long token
            "../../etc/passwd",  # Path traversal attempt
            None  # Null token
        ]
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            for invalid_refresh in test_cases:
                await websocket.send(json.dumps({
                    "type": "token_refresh",
                    "refresh_token": invalid_refresh
                }))
                
                response = await websocket.recv()
                data = json.loads(response)
                
                assert data["type"] == "error"
                assert "refresh" in data["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_refresh_cross_tier_upgrade(self, auth_service_config, mock_postgres, mock_redis):
        """Test 3.4 (Breadth): Handle tier upgrades during token refresh."""
        # Start with free tier
        initial_token = jwt.encode(
            {
                "user_id": "tier_upgrade_user",
                "email": "upgrade@example.com",
                "tier": "free",
                "exp": datetime.utcnow() + timedelta(seconds=5)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {initial_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            # Simulate tier upgrade in backend
            with patch('app.clients.auth_client.auth_client.get_user_tier') as mock_tier:
                mock_tier.return_value = "enterprise"
                
                await websocket.send(json.dumps({
                    "type": "token_refresh",
                    "refresh_token": "upgrade_refresh_token"
                }))
                
                response = await websocket.recv()
                data = json.loads(response)
                
                assert data["type"] == "token_refreshed"
                # New token should reflect upgraded tier
                new_token_payload = jwt.decode(
                    data["new_token"],
                    auth_service_config["jwt_secret"],
                    algorithms=["HS256"]
                )
                assert new_token_payload["tier"] == "enterprise"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_refresh_during_maintenance_mode(self, auth_service_config, mock_postgres, mock_redis):
        """Test 3.5 (Breadth): Token refresh behavior during maintenance mode."""
        token = jwt.encode(
            {
                "user_id": "maintenance_user",
                "email": "maintenance@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(seconds=5)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            # Simulate maintenance mode
            with patch('app.core.config.MAINTENANCE_MODE', True):
                await websocket.send(json.dumps({
                    "type": "token_refresh",
                    "refresh_token": "maintenance_refresh"
                }))
                
                response = await websocket.recv()
                data = json.loads(response)
                
                # Should either queue refresh or return maintenance error
                assert data["type"] in ["maintenance_mode", "token_refresh_queued"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_refresh_with_ip_change(self, auth_service_config, mock_postgres, mock_redis):
        """Test 3.6 (Breadth): Detect IP address changes during token refresh."""
        token = jwt.encode(
            {
                "user_id": "ip_change_user",
                "email": "ipchange@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(seconds=5),
                "client_ip": "192.168.1.100"
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Initial connection from one IP
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Real-IP": "192.168.1.100"
        }
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            # Attempt refresh from different IP
            headers["X-Real-IP"] = "10.0.0.1"
            
            await websocket.send(json.dumps({
                "type": "token_refresh",
                "refresh_token": "ip_change_refresh"
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            # Should require additional verification for IP change
            assert data["type"] in ["additional_verification_required", "security_alert"]
    
    # ==================== TEST 4: CONCURRENT AUTH (DEPTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_auth_thundering_herd(self, auth_service_config, mock_postgres, mock_redis):
        """Test 4.1 (Depth): Handle thundering herd problem with 1000+ concurrent connections."""
        tokens = []
        for i in range(1000):
            token = jwt.encode(
                {
                    "user_id": f"herd_user_{i}",
                    "email": f"herd{i}@example.com",
                    "tier": random.choice(["free", "early", "mid", "enterprise"]),
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            tokens.append(token)
        
        ws_url = f"ws://localhost:8000/websocket"
        
        async def connect_client(token):
            headers = {"Authorization": f"Bearer {token}"}
            try:
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    response = await ws.recv()
                    return json.loads(response)["type"] in ["auth_success", "pong"]
            except Exception:
                return False
        
        # Launch all connections simultaneously
        start_time = time.perf_counter()
        tasks = [connect_client(token) for token in tokens]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start_time
        
        success_rate = sum(results) / len(results)
        
        # Should handle most connections successfully
        assert success_rate > 0.95, f"Only {success_rate*100}% succeeded"
        # Should complete in reasonable time despite load
        assert elapsed < 30.0, f"Took {elapsed}s for 1000 connections"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_auth_deadlock_prevention(self, auth_service_config, mock_postgres, mock_redis):
        """Test 4.2 (Depth): Prevent deadlocks with complex concurrent auth patterns."""
        # Create circular dependency scenario
        users = ["deadlock_a", "deadlock_b", "deadlock_c"]
        tokens = {}
        
        for user in users:
            tokens[user] = jwt.encode(
                {
                    "user_id": user,
                    "email": f"{user}@example.com",
                    "tier": "mid",
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        async def auth_sequence(user_sequence):
            connections = []
            for user in user_sequence:
                headers = {"Authorization": f"Bearer {tokens[user]}"}
                ws = await websockets.connect(ws_url, extra_headers=headers)
                connections.append(ws)
                
                # Simulate interdependent operations
                await ws.send(json.dumps({
                    "type": "lock_resource",
                    "resource": f"resource_{user}"
                }))
            
            # Clean up
            for ws in connections:
                await ws.close()
            
            return True
        
        # Execute multiple sequences that could deadlock
        sequences = [
            ["deadlock_a", "deadlock_b", "deadlock_c"],
            ["deadlock_b", "deadlock_c", "deadlock_a"],
            ["deadlock_c", "deadlock_a", "deadlock_b"]
        ]
        
        tasks = [auth_sequence(seq) for seq in sequences]
        
        # Should complete without deadlock
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=10.0
            )
            assert all(results)
        except asyncio.TimeoutError:
            pytest.fail("Deadlock detected - operations timed out")
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_auth_resource_starvation(self, auth_service_config, mock_postgres, mock_redis):
        """Test 4.3 (Depth): Prevent resource starvation with mixed priority clients."""
        # Create tokens with different priority levels
        high_priority_tokens = []
        low_priority_tokens = []
        
        for i in range(50):
            high_token = jwt.encode(
                {
                    "user_id": f"high_priority_{i}",
                    "email": f"high{i}@example.com",
                    "tier": "enterprise",
                    "priority": "high",
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            high_priority_tokens.append(high_token)
            
            low_token = jwt.encode(
                {
                    "user_id": f"low_priority_{i}",
                    "email": f"low{i}@example.com",
                    "tier": "free",
                    "priority": "low",
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            low_priority_tokens.append(low_token)
        
        ws_url = f"ws://localhost:8000/websocket"
        
        async def measure_auth_time(token):
            start = time.perf_counter()
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    await ws.recv()
                return time.perf_counter() - start
            except Exception:
                return None
        
        # Mix high and low priority connections
        all_tokens = []
        for i in range(50):
            all_tokens.append(high_priority_tokens[i])
            all_tokens.append(low_priority_tokens[i])
        
        random.shuffle(all_tokens)
        
        tasks = [measure_auth_time(token) for token in all_tokens]
        times = await asyncio.gather(*tasks)
        
        # Check that low priority clients aren't starved
        low_priority_times = [t for t in times[::2] if t is not None]
        assert len(low_priority_times) > 40  # Most should succeed
        assert max(low_priority_times) < 10.0  # None should wait too long
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_auth_connection_hijacking(self, auth_service_config, mock_postgres, mock_redis):
        """Test 4.4 (Breadth): Prevent connection hijacking during concurrent auth."""
        victim_token = jwt.encode(
            {
                "user_id": "victim_user",
                "email": "victim@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        attacker_token = jwt.encode(
            {
                "user_id": "attacker_user",
                "email": "attacker@example.com",
                "tier": "free",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Victim establishes connection
        victim_headers = {"Authorization": f"Bearer {victim_token}"}
        victim_ws = await websockets.connect(ws_url, extra_headers=victim_headers)
        
        # Get victim's session ID
        await victim_ws.send(json.dumps({"type": "get_session"}))
        response = await victim_ws.recv()
        victim_session = json.loads(response)["session_id"]
        
        # Attacker tries to hijack victim's session
        attacker_headers = {
            "Authorization": f"Bearer {attacker_token}",
            "X-Session-Id": victim_session  # Try to use victim's session
        }
        
        try:
            attacker_ws = await websockets.connect(ws_url, extra_headers=attacker_headers)
            
            # Try to access victim's resources
            await attacker_ws.send(json.dumps({
                "type": "get_user_data",
                "session_id": victim_session
            }))
            
            response = await attacker_ws.recv()
            data = json.loads(response)
            
            # Should not allow access to victim's data
            assert data["type"] == "error"
            assert "unauthorized" in data["message"].lower()
            
            await attacker_ws.close()
        finally:
            await victim_ws.close()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_auth_load_balancing(self, auth_service_config, mock_postgres, mock_redis):
        """Test 4.5 (Breadth): Verify load balancing across auth service instances."""
        # Simulate multiple auth service instances
        auth_instances = ["auth1", "auth2", "auth3"]
        instance_counts = {instance: 0 for instance in auth_instances}
        
        tokens = []
        for i in range(300):
            token = jwt.encode(
                {
                    "user_id": f"lb_user_{i}",
                    "email": f"lb{i}@example.com",
                    "tier": "mid",
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            tokens.append(token)
        
        ws_url = f"ws://localhost:8000/websocket"
        
        async def connect_and_track(token):
            headers = {"Authorization": f"Bearer {token}"}
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                await ws.send(json.dumps({"type": "get_auth_instance"}))
                response = await ws.recv()
                data = json.loads(response)
                
                # Track which instance handled the auth
                instance = data.get("auth_instance", "auth1")
                return instance
        
        # Connect all clients
        tasks = [connect_and_track(token) for token in tokens]
        instances = await asyncio.gather(*tasks)
        
        # Count distribution
        for instance in instances:
            if instance in instance_counts:
                instance_counts[instance] += 1
        
        # Verify relatively even distribution
        total = sum(instance_counts.values())
        for count in instance_counts.values():
            distribution_ratio = count / total
            # Each instance should handle roughly 1/3 of requests (±10%)
            assert 0.23 < distribution_ratio < 0.43
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_auth_circuit_breaker(self, auth_service_config, mock_postgres, mock_redis):
        """Test 4.6 (Breadth): Circuit breaker activation under auth service failures."""
        tokens = []
        for i in range(100):
            token = jwt.encode(
                {
                    "user_id": f"circuit_user_{i}",
                    "email": f"circuit{i}@example.com",
                    "tier": "early",
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            tokens.append(token)
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Simulate auth service failures
        with patch('app.clients.auth_client.auth_client.validate_token') as mock_validate:
            failure_count = 0
            
            async def failing_validation(*args, **kwargs):
                nonlocal failure_count
                failure_count += 1
                
                # Fail first 30 requests
                if failure_count <= 30:
                    raise Exception("Auth service error")
                
                # Then recover
                return {"valid": True, "user_id": f"user_{failure_count}"}
            
            mock_validate.side_effect = failing_validation
            
            results = []
            for token in tokens[:50]:
                headers = {"Authorization": f"Bearer {token}"}
                
                try:
                    async with websockets.connect(ws_url, extra_headers=headers) as ws:
                        await ws.send(json.dumps({"type": "ping"}))
                        response = await ws.recv()
                        data = json.loads(response)
                        results.append(data["type"])
                except Exception:
                    results.append("failed")
            
            # Circuit breaker should open after initial failures
            # Later requests should fail fast or use fallback
            initial_failures = results[:30].count("failed")
            later_results = results[30:]
            
            assert initial_failures > 25  # Most initial requests fail
            # Circuit breaker should prevent cascading failures
            assert later_results.count("circuit_open") > 0 or later_results.count("fallback") > 0
    
    # ==================== TEST 5: DATABASE UNAVAILABILITY (DEPTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_database_unavailable_cache_consistency(self, auth_service_config, mock_postgres, mock_redis):
        """Test 5.1 (Depth): Maintain cache consistency when database is unavailable."""
        token = jwt.encode(
            {
                "user_id": "cache_consistency_user",
                "email": "consistency@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        # First connection - populate cache
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "get_user_data"}))
            response = await ws.recv()
            initial_data = json.loads(response)
        
        # Simulate database unavailability
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            # Second connection - should use cache
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                await ws.send(json.dumps({"type": "get_user_data"}))
                response = await ws.recv()
                cached_data = json.loads(response)
                
                # Data should be consistent
                assert cached_data["user_id"] == initial_data["user_id"]
                assert cached_data.get("from_cache") is True
                
                # Try to modify data - should be rejected or queued
                await ws.send(json.dumps({
                    "type": "update_user_data",
                    "data": {"tier": "free"}
                }))
                
                response = await ws.recv()
                update_response = json.loads(response)
                
                # Should not allow writes when DB is down
                assert update_response["type"] in ["error", "queued"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_database_unavailable_split_brain(self, auth_service_config, mock_postgres, mock_redis):
        """Test 5.2 (Depth): Prevent split-brain scenarios during partial DB failures."""
        tokens = []
        for i in range(2):
            token = jwt.encode(
                {
                    "user_id": f"split_brain_user_{i}",
                    "email": f"split{i}@example.com",
                    "tier": "mid",
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            tokens.append(token)
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Simulate partial database failure (read works, write fails)
        with patch('app.db.postgres.execute') as mock_execute:
            async def partial_failure(query, *args, **kwargs):
                if "SELECT" in query:
                    return [{"user_id": "split_brain_user_0", "tier": "mid"}]
                else:  # INSERT, UPDATE, DELETE
                    raise Exception("Write operation failed")
            
            mock_execute.side_effect = partial_failure
            
            # Both nodes try to auth simultaneously
            async def auth_node(token, node_id):
                headers = {
                    "Authorization": f"Bearer {token}",
                    "X-Node-Id": f"node_{node_id}"
                }
                
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    # Try to claim leadership
                    await ws.send(json.dumps({
                        "type": "claim_leadership",
                        "node_id": f"node_{node_id}"
                    }))
                    
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    return data.get("leader") == f"node_{node_id}"
            
            # Both nodes compete
            results = await asyncio.gather(
                auth_node(tokens[0], 0),
                auth_node(tokens[1], 1)
            )
            
            # Only one should become leader (prevent split-brain)
            assert sum(results) <= 1
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_database_unavailable_graceful_degradation(self, auth_service_config, mock_postgres, mock_redis):
        """Test 5.3 (Depth): Graceful feature degradation when database is down."""
        token = jwt.encode(
            {
                "user_id": "degradation_user",
                "email": "degrade@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Simulate database unavailability
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_db.side_effect = Exception("Database unavailable")
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                # Test various operations
                operations = [
                    {"type": "get_cached_data"},  # Should work
                    {"type": "get_historical_data"},  # Should fail gracefully
                    {"type": "create_new_thread"},  # Should queue or fail
                    {"type": "get_system_status"}  # Should work (no DB needed)
                ]
                
                results = {}
                for op in operations:
                    await ws.send(json.dumps(op))
                    response = await ws.recv()
                    data = json.loads(response)
                    results[op["type"]] = data["type"]
                
                # Verify graceful degradation
                assert results["get_cached_data"] in ["success", "data"]
                assert results["get_historical_data"] in ["error", "unavailable"]
                assert results["create_new_thread"] in ["error", "queued"]
                assert results["get_system_status"] in ["success", "status"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_database_unavailable_recovery_sync(self, auth_service_config, mock_postgres, mock_redis):
        """Test 5.4 (Breadth): Synchronize state after database recovery."""
        token = jwt.encode(
            {
                "user_id": "recovery_sync_user",
                "email": "recovery@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        queued_operations = []
        
        # Phase 1: Database is down
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_db.side_effect = Exception("Database down")
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                # Queue several operations
                for i in range(5):
                    await ws.send(json.dumps({
                        "type": "create_thread",
                        "content": f"Thread {i} while DB down"
                    }))
                    
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data["type"] == "queued":
                        queued_operations.append(data.get("queue_id"))
        
        # Phase 2: Database recovers
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Trigger sync
            await ws.send(json.dumps({
                "type": "sync_queued_operations",
                "queue_ids": queued_operations
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            
            # Should process queued operations
            assert data["type"] == "sync_complete"
            assert data["processed_count"] == len(queued_operations)
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_database_unavailable_cache_expiry(self, auth_service_config, mock_postgres, mock_redis):
        """Test 5.5 (Breadth): Handle cache expiration during extended database outage."""
        token = jwt.encode(
            {
                "user_id": "cache_expiry_user",
                "email": "expiry@example.com",
                "tier": "early",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Populate cache initially
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(json.dumps({"type": "get_user_data"}))
            await ws.recv()
        
        # Simulate extended database outage
        with patch('app.db.postgres.get_async_db') as mock_db:
            mock_db.side_effect = Exception("Database down")
            
            # Simulate cache expiry
            with patch('app.cache.redis_cache.get') as mock_cache_get:
                mock_cache_get.return_value = None  # Cache miss
                
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    await ws.send(json.dumps({"type": "get_user_data"}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    # Should handle cache miss + DB down gracefully
                    assert data["type"] in ["error", "limited_data"]
                    assert "unavailable" in data.get("message", "").lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_database_unavailable_failover_ordering(self, auth_service_config, mock_postgres, mock_redis):
        """Test 5.6 (Breadth): Correct failover ordering (primary -> replica -> cache)."""
        token = jwt.encode(
            {
                "user_id": "failover_user",
                "email": "failover@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        failover_sequence = []
        
        # Mock all data sources
        with patch('app.db.postgres.get_primary_db') as mock_primary:
            with patch('app.db.postgres.get_replica_db') as mock_replica:
                with patch('app.cache.redis_cache.get') as mock_cache:
                    
                    async def track_primary(*args, **kwargs):
                        failover_sequence.append("primary")
                        raise Exception("Primary DB down")
                    
                    async def track_replica(*args, **kwargs):
                        failover_sequence.append("replica")
                        raise Exception("Replica DB down")
                    
                    async def track_cache(*args, **kwargs):
                        failover_sequence.append("cache")
                        return {"user_id": "failover_user", "from_cache": True}
                    
                    mock_primary.side_effect = track_primary
                    mock_replica.side_effect = track_replica
                    mock_cache.side_effect = track_cache
                    
                    async with websockets.connect(ws_url, extra_headers=headers) as ws:
                        await ws.send(json.dumps({"type": "get_user_data"}))
                        response = await ws.recv()
                        data = json.loads(response)
                        
                        # Verify correct failover order
                        assert failover_sequence == ["primary", "replica", "cache"]
                        assert data.get("from_cache") is True
    
    # ==================== TEST 6: ROLE-BASED ACCESS CONTROL (DEPTH & BREADTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rbac_privilege_escalation_attempts(self, auth_service_config, mock_postgres, mock_redis):
        """Test 6.1 (Depth): Detect and prevent privilege escalation attempts."""
        # Create token with basic user role
        user_token = jwt.encode(
            {
                "user_id": "escalation_user",
                "email": "escalation@example.com",
                "tier": "free",
                "roles": ["user"],
                "permissions": ["read:own_data"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {user_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Attempt various privilege escalation techniques
            escalation_attempts = [
                {
                    "type": "update_user",
                    "user_id": "escalation_user",
                    "data": {"roles": ["admin"]}  # Try to add admin role
                },
                {
                    "type": "execute_admin_command",
                    "command": "delete_all_users",
                    "sudo": True  # Try to use sudo
                },
                {
                    "type": "impersonate_user",
                    "target_user_id": "admin_user"  # Try to impersonate admin
                },
                {
                    "type": "modify_permissions",
                    "permissions": ["write:all_data"]  # Try to add permissions
                }
            ]
            
            for attempt in escalation_attempts:
                await ws.send(json.dumps(attempt))
                response = await ws.recv()
                data = json.loads(response)
                
                # All escalation attempts should be blocked
                assert data["type"] == "error"
                assert "unauthorized" in data["message"].lower() or "forbidden" in data["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rbac_role_inheritance_delegation(self, auth_service_config, mock_postgres, mock_redis):
        """Test 6.2 (Depth): Complex role inheritance and delegation chains."""
        # Create token with inherited roles
        manager_token = jwt.encode(
            {
                "user_id": "manager_user",
                "email": "manager@example.com",
                "tier": "enterprise",
                "roles": ["manager", "team_lead"],
                "inherited_roles": ["user", "viewer"],
                "delegated_from": "director_user",
                "delegation_expires": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {manager_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Test inherited permissions
            await ws.send(json.dumps({
                "type": "access_resource",
                "resource": "team_reports",
                "required_role": "team_lead"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "access_granted"
            
            # Test delegated permissions
            await ws.send(json.dumps({
                "type": "access_resource",
                "resource": "director_dashboard",
                "use_delegation": True
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "access_granted"
            assert data.get("delegation_used") is True
            
            # Wait for delegation to expire
            await asyncio.sleep(31 * 60)  # 31 minutes
            
            # Delegated access should now fail
            await ws.send(json.dumps({
                "type": "access_resource",
                "resource": "director_dashboard",
                "use_delegation": True
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "error"
            assert "delegation expired" in data["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rbac_dynamic_role_changes(self, auth_service_config, mock_postgres, mock_redis):
        """Test 6.3 (Depth): Handle dynamic role changes during active session."""
        user_id = "dynamic_role_user"
        
        # Start with basic role
        initial_token = jwt.encode(
            {
                "user_id": user_id,
                "email": "dynamic@example.com",
                "tier": "early",
                "roles": ["user"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {initial_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Initial access check
            await ws.send(json.dumps({
                "type": "access_resource",
                "resource": "admin_panel"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "error"  # Should be denied
            
            # Simulate role upgrade in backend
            with patch('app.clients.auth_client.auth_client.get_user_roles') as mock_roles:
                mock_roles.return_value = ["user", "admin"]
                
                # Notify session of role change
                await ws.send(json.dumps({
                    "type": "refresh_roles"
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                assert data["type"] == "roles_updated"
                assert "admin" in data["new_roles"]
                
                # Now admin access should work
                await ws.send(json.dumps({
                    "type": "access_resource",
                    "resource": "admin_panel"
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                assert data["type"] == "access_granted"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rbac_cross_tenant_access_prevention(self, auth_service_config, mock_postgres, mock_redis):
        """Test 6.4 (Breadth): Prevent cross-tenant data access."""
        # Create tokens for different tenants
        tenant_a_token = jwt.encode(
            {
                "user_id": "tenant_a_user",
                "email": "user@tenanta.com",
                "tier": "enterprise",
                "tenant_id": "tenant_a",
                "roles": ["admin"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        tenant_b_token = jwt.encode(
            {
                "user_id": "tenant_b_user",
                "email": "user@tenantb.com",
                "tier": "enterprise",
                "tenant_id": "tenant_b",
                "roles": ["admin"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Tenant A creates data
        headers_a = {"Authorization": f"Bearer {tenant_a_token}"}
        async with websockets.connect(ws_url, extra_headers=headers_a) as ws_a:
            await ws_a.send(json.dumps({
                "type": "create_resource",
                "resource_type": "secret_data",
                "data": {"content": "Tenant A secret"}
            }))
            
            response = await ws_a.recv()
            data = json.loads(response)
            resource_id = data["resource_id"]
        
        # Tenant B tries to access Tenant A's data
        headers_b = {"Authorization": f"Bearer {tenant_b_token}"}
        async with websockets.connect(ws_url, extra_headers=headers_b) as ws_b:
            await ws_b.send(json.dumps({
                "type": "access_resource",
                "resource_id": resource_id,
                "tenant_override": "tenant_a"  # Try to override tenant
            }))
            
            response = await ws_b.recv()
            data = json.loads(response)
            
            # Should be blocked despite admin role
            assert data["type"] == "error"
            assert "tenant" in data["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rbac_role_specific_rate_limits(self, auth_service_config, mock_postgres, mock_redis):
        """Test 6.5 (Breadth): Different rate limits based on user roles."""
        # Create tokens with different roles
        free_token = jwt.encode(
            {
                "user_id": "free_user",
                "email": "free@example.com",
                "tier": "free",
                "roles": ["user"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        premium_token = jwt.encode(
            {
                "user_id": "premium_user",
                "email": "premium@example.com",
                "tier": "enterprise",
                "roles": ["premium_user"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test free user rate limit (should be lower)
        free_headers = {"Authorization": f"Bearer {free_token}"}
        free_request_count = 0
        
        async with websockets.connect(ws_url, extra_headers=free_headers) as ws:
            for i in range(20):
                await ws.send(json.dumps({"type": "api_request", "index": i}))
                response = await ws.recv()
                data = json.loads(response)
                
                if data["type"] == "rate_limited":
                    free_request_count = i
                    break
        
        # Test premium user rate limit (should be higher)
        premium_headers = {"Authorization": f"Bearer {premium_token}"}
        premium_request_count = 0
        
        async with websockets.connect(ws_url, extra_headers=premium_headers) as ws:
            for i in range(100):
                await ws.send(json.dumps({"type": "api_request", "index": i}))
                response = await ws.recv()
                data = json.loads(response)
                
                if data["type"] == "rate_limited":
                    premium_request_count = i
                    break
        
        # Premium should have higher limit
        assert premium_request_count > free_request_count * 2
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rbac_audit_logging_privileged_ops(self, auth_service_config, mock_postgres, mock_redis):
        """Test 6.6 (Breadth): Comprehensive audit logging for privileged operations."""
        admin_token = jwt.encode(
            {
                "user_id": "audit_admin",
                "email": "audit@example.com",
                "tier": "enterprise",
                "roles": ["admin", "auditor"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        audit_logs = []
        
        # Mock audit logging
        with patch('app.core.audit.log_privileged_operation') as mock_audit:
            async def capture_audit(*args, **kwargs):
                audit_logs.append(kwargs)
                return True
            
            mock_audit.side_effect = capture_audit
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                # Perform various privileged operations
                privileged_ops = [
                    {"type": "delete_user", "user_id": "some_user"},
                    {"type": "modify_system_config", "setting": "rate_limit", "value": 1000},
                    {"type": "access_audit_logs", "date_range": "last_week"},
                    {"type": "export_user_data", "format": "csv"}
                ]
                
                for op in privileged_ops:
                    await ws.send(json.dumps(op))
                    await ws.recv()
            
            # Verify audit logs were created
            assert len(audit_logs) == len(privileged_ops)
            
            for log in audit_logs:
                assert "user_id" in log
                assert "operation" in log
                assert "timestamp" in log
                assert "ip_address" in log
    
    # ==================== TEST 7: SESSION PERSISTENCE (DEPTH & BREADTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_fixation_attacks(self, auth_service_config, mock_postgres, mock_redis):
        """Test 7.1 (Depth): Prevent session fixation attacks."""
        # Attacker creates a session
        attacker_token = jwt.encode(
            {
                "user_id": "attacker",
                "email": "attacker@evil.com",
                "tier": "free",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        attacker_headers = {"Authorization": f"Bearer {attacker_token}"}
        
        # Attacker gets a session ID
        fixed_session_id = None
        async with websockets.connect(ws_url, extra_headers=attacker_headers) as ws:
            await ws.send(json.dumps({"type": "get_session"}))
            response = await ws.recv()
            data = json.loads(response)
            fixed_session_id = data["session_id"]
        
        # Victim tries to use the fixed session ID
        victim_token = jwt.encode(
            {
                "user_id": "victim",
                "email": "victim@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        victim_headers = {
            "Authorization": f"Bearer {victim_token}",
            "X-Session-Id": fixed_session_id  # Using attacker's session
        }
        
        async with websockets.connect(ws_url, extra_headers=victim_headers) as ws:
            await ws.send(json.dumps({"type": "get_user_data"}))
            response = await ws.recv()
            data = json.loads(response)
            
            # Should create new session, not use fixed one
            assert data.get("session_id") != fixed_session_id
            assert data["user_id"] == "victim"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_distributed_consistency(self, auth_service_config, mock_postgres, mock_redis):
        """Test 7.2 (Depth): Maintain session consistency across distributed nodes."""
        token = jwt.encode(
            {
                "user_id": "distributed_user",
                "email": "distributed@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Simulate multiple server nodes
        nodes = ["node1", "node2", "node3"]
        session_data = {}
        
        for node in nodes:
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Server-Node": node
            }
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                # Write data on this node
                await ws.send(json.dumps({
                    "type": "update_session",
                    "data": {f"from_{node}": f"data_{node}"}
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                session_data[node] = data.get("session_data", {})
        
        # Verify all nodes see consistent data
        for node in nodes:
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Server-Node": node
            }
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                await ws.send(json.dumps({"type": "get_session_data"}))
                response = await ws.recv()
                data = json.loads(response)
                
                # Should see data from all nodes
                for other_node in nodes:
                    assert f"from_{other_node}" in data["session_data"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_timeout_renewal(self, auth_service_config, mock_postgres, mock_redis):
        """Test 7.3 (Depth): Session timeout and automatic renewal mechanisms."""
        token = jwt.encode(
            {
                "user_id": "timeout_user",
                "email": "timeout@example.com",
                "tier": "early",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Set short session timeout
            await ws.send(json.dumps({
                "type": "configure_session",
                "idle_timeout": 5,  # 5 seconds
                "absolute_timeout": 60  # 60 seconds
            }))
            
            await ws.recv()
            
            # Keep session alive with activity
            for _ in range(3):
                await asyncio.sleep(3)  # Activity before idle timeout
                await ws.send(json.dumps({"type": "ping"}))
                response = await ws.recv()
                data = json.loads(response)
                assert data["type"] == "pong"
            
            # Let session idle timeout
            await asyncio.sleep(6)
            
            # Should require re-authentication
            await ws.send(json.dumps({"type": "ping"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] in ["session_expired", "reauth_required"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_cross_device_management(self, auth_service_config, mock_postgres, mock_redis):
        """Test 7.4 (Breadth): Manage sessions across multiple devices."""
        user_id = "multi_device_user"
        base_token_data = {
            "user_id": user_id,
            "email": "devices@example.com",
            "tier": "enterprise",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Create tokens for different devices
        devices = {
            "mobile": {"device_id": "iphone_123", "user_agent": "iOS/14.0"},
            "desktop": {"device_id": "mac_456", "user_agent": "Chrome/90.0"},
            "tablet": {"device_id": "ipad_789", "user_agent": "Safari/14.0"}
        }
        
        ws_url = f"ws://localhost:8000/websocket"
        active_sessions = {}
        
        # Create sessions on all devices
        for device_type, device_info in devices.items():
            token_data = {**base_token_data, **device_info}
            token = jwt.encode(token_data, auth_service_config["jwt_secret"], algorithm="HS256")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": device_info["user_agent"]
            }
            
            ws = await websockets.connect(ws_url, extra_headers=headers)
            active_sessions[device_type] = ws
            
            await ws.send(json.dumps({"type": "register_device"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "device_registered"
        
        # List all active sessions from one device
        await active_sessions["desktop"].send(json.dumps({"type": "list_sessions"}))
        response = await active_sessions["desktop"].recv()
        data = json.loads(response)
        
        assert len(data["sessions"]) == 3
        assert all(d in [s["device_type"] for s in data["sessions"]] for d in devices.keys())
        
        # Revoke mobile session from desktop
        await active_sessions["desktop"].send(json.dumps({
            "type": "revoke_session",
            "device_id": "iphone_123"
        }))
        
        # Mobile session should be terminated
        try:
            await active_sessions["mobile"].send(json.dumps({"type": "ping"}))
            response = await active_sessions["mobile"].recv()
            data = json.loads(response)
            assert data["type"] == "session_revoked"
        except websockets.exceptions.ConnectionClosed:
            pass  # Connection closed is also valid
        
        # Clean up
        for ws in active_sessions.values():
            if ws.open:
                await ws.close()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_migration_during_failover(self, auth_service_config, mock_postgres, mock_redis):
        """Test 7.5 (Breadth): Session migration during server failover."""
        token = jwt.encode(
            {
                "user_id": "failover_user",
                "email": "failover@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Connect to primary server
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Server": "primary"
        }
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Store session data
            await ws.send(json.dumps({
                "type": "store_data",
                "data": {"important": "session_data", "counter": 42}
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            session_id = data["session_id"]
            
            # Simulate primary server failure
            await ws.send(json.dumps({"type": "simulate_failure"}))
        
        # Connect to backup server
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Server": "backup",
            "X-Session-Id": session_id
        }
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Retrieve migrated session
            await ws.send(json.dumps({"type": "get_session_data"}))
            response = await ws.recv()
            data = json.loads(response)
            
            # Session data should be preserved
            assert data["session_data"]["important"] == "session_data"
            assert data["session_data"]["counter"] == 42
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_session_storage_limits(self, auth_service_config, mock_postgres, mock_redis):
        """Test 7.6 (Breadth): Handle session storage limits and cleanup."""
        token = jwt.encode(
            {
                "user_id": "storage_limit_user",
                "email": "storage@example.com",
                "tier": "free",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Try to store large amount of session data
            large_data = "x" * (1024 * 1024)  # 1MB string
            
            for i in range(10):
                await ws.send(json.dumps({
                    "type": "store_session_data",
                    "key": f"large_data_{i}",
                    "value": large_data
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                
                if data["type"] == "error":
                    # Should hit storage limit
                    assert "storage" in data["message"].lower()
                    assert "limit" in data["message"].lower()
                    assert i < 10  # Should fail before storing all
                    break
            else:
                pytest.fail("Should have hit storage limit")
    
    # ==================== TEST 8: RATE LIMITING (DEPTH & BREADTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rate_limit_distributed_accuracy(self, auth_service_config, mock_postgres, mock_redis):
        """Test 8.1 (Depth): Accurate rate limiting across distributed systems."""
        token = jwt.encode(
            {
                "user_id": "distributed_rate_user",
                "email": "distrate@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Simulate requests from multiple nodes
        nodes = ["node1", "node2", "node3"]
        total_requests = 0
        rate_limit = 100  # Expected rate limit
        
        async def send_requests_from_node(node, count):
            nonlocal total_requests
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Node": node
            }
            
            successful = 0
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                for _ in range(count):
                    await ws.send(json.dumps({"type": "api_request"}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data["type"] == "rate_limited":
                        break
                    successful += 1
            
            return successful
        
        # Send requests concurrently from all nodes
        tasks = [send_requests_from_node(node, 50) for node in nodes]
        results = await asyncio.gather(*tasks)
        total_requests = sum(results)
        
        # Total across all nodes should respect global rate limit
        assert total_requests <= rate_limit + 5  # Allow small margin for timing
        assert total_requests >= rate_limit - 5
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rate_limit_bypass_attempts(self, auth_service_config, mock_postgres, mock_redis):
        """Test 8.2 (Depth): Prevent rate limit bypass attempts."""
        base_token_data = {
            "email": "bypass@example.com",
            "tier": "free",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Various bypass techniques
        bypass_attempts = [
            # Technique 1: Different user IDs
            {"user_id": "bypass_user_1"},
            {"user_id": "bypass_user_2"},
            
            # Technique 2: Case variations
            {"user_id": "ByPass_User"},
            {"user_id": "BYPASS_USER"},
            
            # Technique 3: Adding whitespace
            {"user_id": " bypass_user "},
            {"user_id": "bypass_user\n"},
            
            # Technique 4: Unicode variations
            {"user_id": "bypäss_üser"},
            {"user_id": "bypass\u200buser"},  # Zero-width space
        ]
        
        total_successful = 0
        
        for attempt in bypass_attempts:
            token_data = {**base_token_data, **attempt}
            token = jwt.encode(token_data, auth_service_config["jwt_secret"], algorithm="HS256")
            
            headers = {"Authorization": f"Bearer {token}"}
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                for _ in range(10):
                    await ws.send(json.dumps({"type": "api_request"}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data["type"] != "rate_limited":
                        total_successful += 1
        
        # Should detect bypass attempts and apply consistent rate limiting
        assert total_successful < 50  # Much less than 80 (8 attempts × 10 requests)
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rate_limit_sliding_vs_fixed_window(self, auth_service_config, mock_postgres, mock_redis):
        """Test 8.3 (Depth): Compare sliding window vs fixed window rate limiting."""
        token = jwt.encode(
            {
                "user_id": "window_test_user",
                "email": "window@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Configure sliding window rate limit
            await ws.send(json.dumps({
                "type": "configure_rate_limit",
                "algorithm": "sliding_window",
                "limit": 10,
                "window": 60  # 60 seconds
            }))
            
            await ws.recv()
            
            # Send burst at start of window
            for i in range(10):
                await ws.send(json.dumps({"type": "api_request", "index": i}))
                response = await ws.recv()
                data = json.loads(response)
                assert data["type"] != "rate_limited"
            
            # Wait 30 seconds (half window)
            await asyncio.sleep(30)
            
            # Try more requests - sliding window should still block
            await ws.send(json.dumps({"type": "api_request"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "rate_limited"
            
            # Wait another 30 seconds (full window from first request)
            await asyncio.sleep(31)
            
            # Now should allow new requests
            await ws.send(json.dumps({"type": "api_request"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] != "rate_limited"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rate_limit_tier_based(self, auth_service_config, mock_postgres, mock_redis):
        """Test 8.4 (Breadth): Different rate limits for different tiers."""
        tiers = {
            "free": 10,
            "early": 50,
            "mid": 200,
            "enterprise": 1000
        }
        
        ws_url = f"ws://localhost:8000/websocket"
        results = {}
        
        for tier, expected_limit in tiers.items():
            token = jwt.encode(
                {
                    "user_id": f"{tier}_user",
                    "email": f"{tier}@example.com",
                    "tier": tier,
                    "exp": datetime.utcnow() + timedelta(hours=1)
                },
                auth_service_config["jwt_secret"],
                algorithm="HS256"
            )
            
            headers = {"Authorization": f"Bearer {token}"}
            successful_requests = 0
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                # Send requests until rate limited
                for i in range(expected_limit + 50):
                    await ws.send(json.dumps({"type": "api_request", "index": i}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data["type"] == "rate_limited":
                        break
                    successful_requests += 1
            
            results[tier] = successful_requests
        
        # Verify tier-based limits
        assert results["free"] < results["early"]
        assert results["early"] < results["mid"]
        assert results["mid"] < results["enterprise"]
        
        # Check approximate values
        for tier, expected in tiers.items():
            assert abs(results[tier] - expected) < expected * 0.1  # Within 10%
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rate_limit_geographic(self, auth_service_config, mock_postgres, mock_redis):
        """Test 8.5 (Breadth): Geographic-based rate limiting."""
        token = jwt.encode(
            {
                "user_id": "geo_rate_user",
                "email": "georate@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Different geographic regions with different limits
        regions = {
            "US": {"limit": 100, "ip": "1.1.1.1"},
            "EU": {"limit": 100, "ip": "2.2.2.2"},
            "CN": {"limit": 10, "ip": "3.3.3.3"},  # Restricted region
            "RU": {"limit": 5, "ip": "4.4.4.4"}  # More restricted
        }
        
        results = {}
        
        for region, config in regions.items():
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Real-IP": config["ip"],
                "X-Region": region
            }
            
            successful = 0
            
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                for i in range(150):
                    await ws.send(json.dumps({"type": "api_request"}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data["type"] == "rate_limited":
                        break
                    successful += 1
            
            results[region] = successful
        
        # Verify geographic limits
        assert results["US"] > results["CN"]
        assert results["EU"] > results["CN"]
        assert results["CN"] > results["RU"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_rate_limit_recovery_backoff(self, auth_service_config, mock_postgres, mock_redis):
        """Test 8.6 (Breadth): Rate limit recovery with exponential backoff."""
        token = jwt.encode(
            {
                "user_id": "backoff_user",
                "email": "backoff@example.com",
                "tier": "free",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Hit rate limit
            for _ in range(15):
                await ws.send(json.dumps({"type": "api_request"}))
                response = await ws.recv()
                data = json.loads(response)
                
                if data["type"] == "rate_limited":
                    first_retry_after = data.get("retry_after", 1)
                    break
            
            # Continue hitting rate limit to trigger backoff
            backoff_times = [first_retry_after]
            
            for attempt in range(3):
                await asyncio.sleep(0.5)  # Short wait
                
                await ws.send(json.dumps({"type": "api_request"}))
                response = await ws.recv()
                data = json.loads(response)
                
                if data["type"] == "rate_limited":
                    backoff_times.append(data.get("retry_after", 0))
            
            # Verify exponential backoff
            for i in range(1, len(backoff_times)):
                # Each retry_after should be larger than previous
                assert backoff_times[i] > backoff_times[i-1]
            
            # Wait for full recovery
            await asyncio.sleep(max(backoff_times))
            
            # Should be able to make requests again
            await ws.send(json.dumps({"type": "api_request"}))
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] != "rate_limited"
    
    # ==================== TEST 9: MULTI-FACTOR AUTH (DEPTH & BREADTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_totp_time_sync(self, auth_service_config, mock_postgres, mock_redis):
        """Test 9.1 (Depth): TOTP time synchronization tolerance."""
        import pyotp
        
        # Create user with MFA enabled
        secret = pyotp.random_base32()
        token = jwt.encode(
            {
                "user_id": "totp_user",
                "email": "totp@example.com",
                "tier": "enterprise",
                "mfa_enabled": True,
                "mfa_secret": secret,
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Initial auth triggers MFA
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "mfa_required"
            
            totp = pyotp.TOTP(secret)
            
            # Test with current time
            current_code = totp.now()
            await ws.send(json.dumps({
                "type": "mfa_verify",
                "code": current_code
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "mfa_verified"
            
            # Test with time drift (30 seconds in past)
            past_code = totp.at(datetime.utcnow() - timedelta(seconds=30))
            await ws.send(json.dumps({
                "type": "mfa_verify",
                "code": past_code
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            # Should accept with reasonable time drift
            assert data["type"] in ["mfa_verified", "mfa_accepted_with_drift"]
            
            # Test with excessive drift (5 minutes)
            old_code = totp.at(datetime.utcnow() - timedelta(minutes=5))
            await ws.send(json.dumps({
                "type": "mfa_verify",
                "code": old_code
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "error"
            assert "expired" in data["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_backup_code_exhaustion(self, auth_service_config, mock_postgres, mock_redis):
        """Test 9.2 (Depth): Handle backup code exhaustion scenarios."""
        backup_codes = ["BACKUP1", "BACKUP2", "BACKUP3"]
        
        token = jwt.encode(
            {
                "user_id": "backup_code_user",
                "email": "backup@example.com",
                "tier": "mid",
                "mfa_enabled": True,
                "backup_codes": backup_codes,
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "mfa_required"
            
            # Use all backup codes
            for code in backup_codes:
                await ws.send(json.dumps({
                    "type": "mfa_verify",
                    "backup_code": code
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                assert data["type"] == "mfa_verified"
                
                # Try to reuse the same code
                await ws.send(json.dumps({
                    "type": "mfa_verify",
                    "backup_code": code
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                assert data["type"] == "error"
                assert "already used" in data["message"].lower()
            
            # All codes exhausted - should prompt for recovery
            await ws.send(json.dumps({
                "type": "mfa_verify",
                "backup_code": "INVALID"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "backup_codes_exhausted"
            assert "recovery" in data["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_bypass_detection(self, auth_service_config, mock_postgres, mock_redis):
        """Test 9.3 (Depth): Detect and prevent MFA bypass attempts."""
        token = jwt.encode(
            {
                "user_id": "mfa_bypass_user",
                "email": "bypass@example.com",
                "tier": "enterprise",
                "mfa_enabled": True,
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "mfa_required"
            
            # Bypass attempt 1: Skip MFA and try direct access
            await ws.send(json.dumps({
                "type": "access_resource",
                "resource": "sensitive_data",
                "skip_mfa": True
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "error"
            assert "mfa required" in data["message"].lower()
            
            # Bypass attempt 2: Manipulate session state
            await ws.send(json.dumps({
                "type": "update_session",
                "mfa_verified": True
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "error"
            assert "unauthorized" in data["message"].lower()
            
            # Bypass attempt 3: Use expired MFA token
            await ws.send(json.dumps({
                "type": "mfa_verify",
                "cached_token": "expired_mfa_token"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "error"
            
            # Multiple failed attempts should trigger security alert
            assert data.get("security_alert") is True
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_multiple_methods(self, auth_service_config, mock_postgres, mock_redis):
        """Test 9.4 (Breadth): Support multiple MFA methods simultaneously."""
        token = jwt.encode(
            {
                "user_id": "multi_mfa_user",
                "email": "multimfa@example.com",
                "tier": "enterprise",
                "mfa_methods": ["totp", "sms", "email", "biometric"],
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "mfa_required"
            assert "available_methods" in data
            assert len(data["available_methods"]) == 4
            
            # Test each MFA method
            mfa_tests = [
                {"method": "totp", "code": "123456"},
                {"method": "sms", "code": "SMS123"},
                {"method": "email", "code": "EMAIL456"},
                {"method": "biometric", "data": "fingerprint_hash"}
            ]
            
            for test in mfa_tests:
                await ws.send(json.dumps({
                    "type": "mfa_verify",
                    "method": test["method"],
                    **{k: v for k, v in test.items() if k != "method"}
                }))
                
                response = await ws.recv()
                data = json.loads(response)
                
                # Each method should be validated
                assert data["type"] in ["mfa_verified", "mfa_pending"]
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_device_registration(self, auth_service_config, mock_postgres, mock_redis):
        """Test 9.5 (Breadth): MFA device registration and management."""
        token = jwt.encode(
            {
                "user_id": "device_reg_user",
                "email": "devreg@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Register new MFA device
            await ws.send(json.dumps({
                "type": "register_mfa_device",
                "device_type": "authenticator",
                "device_name": "iPhone 12"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "device_registration_started"
            assert "qr_code" in data
            assert "secret" in data
            
            # Verify device with code
            await ws.send(json.dumps({
                "type": "verify_device",
                "code": "123456",
                "device_id": data["device_id"]
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "device_registered"
            
            # List registered devices
            await ws.send(json.dumps({"type": "list_mfa_devices"}))
            response = await ws.recv()
            data = json.loads(response)
            assert len(data["devices"]) == 1
            assert data["devices"][0]["name"] == "iPhone 12"
            
            # Remove device
            device_id = data["devices"][0]["id"]
            await ws.send(json.dumps({
                "type": "remove_mfa_device",
                "device_id": device_id,
                "confirmation_code": "123456"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "device_removed"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_recovery_procedures(self, auth_service_config, mock_postgres, mock_redis):
        """Test 9.6 (Breadth): MFA recovery procedures for locked out users."""
        token = jwt.encode(
            {
                "user_id": "recovery_user",
                "email": "recovery@example.com",
                "tier": "enterprise",
                "mfa_enabled": True,
                "recovery_email": "backup@example.com",
                "recovery_phone": "+1234567890",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "mfa_required"
            
            # Initiate recovery
            await ws.send(json.dumps({
                "type": "initiate_mfa_recovery",
                "reason": "lost_device"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "recovery_initiated"
            assert "recovery_methods" in data
            
            # Choose email recovery
            await ws.send(json.dumps({
                "type": "select_recovery_method",
                "method": "email",
                "send_to": "backup@example.com"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "recovery_code_sent"
            recovery_id = data["recovery_id"]
            
            # Verify recovery code
            await ws.send(json.dumps({
                "type": "verify_recovery",
                "recovery_id": recovery_id,
                "code": "RECOVERY123"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "recovery_verified"
            
            # Reset MFA settings
            await ws.send(json.dumps({
                "type": "reset_mfa",
                "new_method": "totp"
            }))
            
            response = await ws.recv()
            data = json.loads(response)
            assert data["type"] == "mfa_reset_complete"
            assert "new_secret" in data
    
    # ==================== TEST 10: CORS VALIDATION (DEPTH & BREADTH) ====================
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cors_wildcard_exploitation(self, auth_service_config, mock_postgres, mock_redis):
        """Test 10.1 (Depth): Prevent wildcard origin exploitation."""
        token = jwt.encode(
            {
                "user_id": "cors_wildcard_user",
                "email": "wildcard@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test various wildcard exploitation attempts
        test_origins = [
            "*",  # Literal wildcard
            "*.evil.com",  # Wildcard subdomain
            "https://*",  # Wildcard domain
            "https://evil.com.example.com",  # Subdomain injection
            "https://example.com.evil.com",  # Domain suffix attack
            "https://example.com@evil.com",  # @ character exploit
            "https://example.com%2eevil.com"  # URL encoding
        ]
        
        for origin in test_origins:
            headers = {
                "Authorization": f"Bearer {token}",
                "Origin": origin
            }
            
            # Should reject all wildcard/malicious origins
            with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
                async with websockets.connect(ws_url, extra_headers=headers):
                    pass
            
            assert exc_info.value.status_code == 403
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cors_null_origin_handling(self, auth_service_config, mock_postgres, mock_redis):
        """Test 10.2 (Depth): Proper handling of null origin."""
        token = jwt.encode(
            {
                "user_id": "null_origin_user",
                "email": "null@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test null origin (can occur with file:// or sandboxed iframes)
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "null"
        }
        
        # Should reject null origin for security
        with pytest.raises(websockets.exceptions.InvalidStatusCode) as exc_info:
            async with websockets.connect(ws_url, extra_headers=headers):
                pass
        
        assert exc_info.value.status_code == 403
        
        # Test missing origin header
        headers = {"Authorization": f"Bearer {token}"}
        # No Origin header
        
        # Behavior depends on implementation - either accept or reject
        try:
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                await ws.send(json.dumps({"type": "ping"}))
                response = await ws.recv()
                data = json.loads(response)
                # If accepted, should work normally
                assert data["type"] in ["auth_success", "pong"]
        except websockets.exceptions.InvalidStatusCode as e:
            # If rejected, should be 403
            assert e.status_code == 403
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cors_preflight_validation(self, auth_service_config, mock_postgres, mock_redis):
        """Test 10.3 (Depth): Validate preflight request handling."""
        # Note: WebSocket doesn't use traditional CORS preflight,
        # but we test similar validation for upgrade requests
        
        token = jwt.encode(
            {
                "user_id": "preflight_user",
                "email": "preflight@example.com",
                "tier": "early",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test with various upgrade headers
        test_cases = [
            {
                "Authorization": f"Bearer {token}",
                "Origin": "https://app.netra.ai",
                "Sec-WebSocket-Version": "13",
                "Sec-WebSocket-Key": base64.b64encode(os.urandom(16)).decode()
            },
            {
                "Authorization": f"Bearer {token}",
                "Origin": "https://app.netra.ai",
                "Sec-WebSocket-Version": "8",  # Old version
                "Sec-WebSocket-Key": base64.b64encode(os.urandom(16)).decode()
            }
        ]
        
        for headers in test_cases:
            try:
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    # Modern version should work
                    if headers["Sec-WebSocket-Version"] == "13":
                        assert data["type"] in ["auth_success", "pong"]
                    
            except websockets.exceptions.InvalidStatusCode as e:
                # Old version might be rejected
                if headers["Sec-WebSocket-Version"] != "13":
                    assert e.status_code in [400, 426]  # Bad Request or Upgrade Required
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cors_dynamic_origin_whitelisting(self, auth_service_config, mock_postgres, mock_redis):
        """Test 10.4 (Breadth): Dynamic origin whitelisting based on configuration."""
        token = jwt.encode(
            {
                "user_id": "dynamic_cors_user",
                "email": "dynamic@example.com",
                "tier": "enterprise",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test origins that might be dynamically configured
        test_origins = [
            ("https://app.netra.ai", True),  # Production
            ("https://staging.netra.ai", True),  # Staging
            ("http://localhost:3000", True),  # Local development
            ("https://partner.example.com", False),  # Partner domain (might be allowed)
            ("https://malicious.com", False),  # Should never be allowed
        ]
        
        for origin, should_allow in test_origins:
            headers = {
                "Authorization": f"Bearer {token}",
                "Origin": origin
            }
            
            try:
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if should_allow:
                        assert data["type"] in ["auth_success", "pong"]
                    
            except websockets.exceptions.InvalidStatusCode as e:
                if not should_allow:
                    assert e.status_code == 403
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cors_subdomain_validation(self, auth_service_config, mock_postgres, mock_redis):
        """Test 10.5 (Breadth): Validate subdomain handling in CORS."""
        token = jwt.encode(
            {
                "user_id": "subdomain_user",
                "email": "subdomain@example.com",
                "tier": "mid",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        ws_url = f"ws://localhost:8000/websocket"
        
        # Test various subdomain patterns
        subdomain_tests = [
            ("https://app.netra.ai", True),
            ("https://api.netra.ai", True),
            ("https://staging.netra.ai", True),
            ("https://evil.netra.ai.attacker.com", False),  # Subdomain attack
            ("https://netra.ai", True),  # Root domain
            ("https://sub.sub.netra.ai", False),  # Deep subdomain
            ("https://xn--netra.ai", False),  # IDN homograph
        ]
        
        for origin, expected_allow in subdomain_tests:
            headers = {
                "Authorization": f"Bearer {token}",
                "Origin": origin
            }
            
            try:
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if expected_allow:
                        assert data["type"] in ["auth_success", "pong"]
                    else:
                        # Shouldn't get here for disallowed origins
                        pytest.fail(f"Origin {origin} was allowed but shouldn't be")
                        
            except websockets.exceptions.InvalidStatusCode as e:
                if not expected_allow:
                    assert e.status_code == 403
                else:
                    pytest.fail(f"Origin {origin} was blocked but should be allowed")
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_cors_protocol_mismatch(self, auth_service_config, mock_postgres, mock_redis):
        """Test 10.6 (Breadth): Handle protocol mismatches in CORS."""
        token = jwt.encode(
            {
                "user_id": "protocol_user",
                "email": "protocol@example.com",
                "tier": "early",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            auth_service_config["jwt_secret"],
            algorithm="HS256"
        )
        
        # Test connecting to ws:// with https:// origin and vice versa
        test_cases = [
            ("ws://localhost:8000/websocket", "https://app.netra.ai"),  # WS with HTTPS origin
            ("wss://localhost:8443/websocket", "http://app.netra.ai"),  # WSS with HTTP origin
            ("ws://localhost:8000/websocket", "http://app.netra.ai"),  # WS with HTTP origin (match)
            ("wss://localhost:8443/websocket", "https://app.netra.ai"),  # WSS with HTTPS origin (match)
        ]
        
        for ws_url, origin in test_cases:
            headers = {
                "Authorization": f"Bearer {token}",
                "Origin": origin
            }
            
            # Protocol mismatch handling
            is_secure_ws = ws_url.startswith("wss://")
            is_secure_origin = origin.startswith("https://")
            
            try:
                async with websockets.connect(ws_url, extra_headers=headers) as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    # Should only allow if protocols match in security level
                    if is_secure_ws == is_secure_origin:
                        assert data["type"] in ["auth_success", "pong"]
                    
            except (websockets.exceptions.InvalidStatusCode, OSError) as e:
                # Mismatch or connection error
                if isinstance(e, websockets.exceptions.InvalidStatusCode):
                    if is_secure_ws != is_secure_origin:
                        assert e.status_code == 403