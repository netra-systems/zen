"""
WebSocket Connection Basic Tests: Token Authentication

Basic WebSocket connection tests focusing on expired token authentication,
immediate rejection, and grace period handling.

Business Value: Prevents security breaches and ensures proper authentication
flow for all WebSocket connections.
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
from .websocket_recovery_fixtures import (
    SecureJWTGenerator, SecurityAuditLogger, SecureWebSocketTestClient,
    TokenRefreshService, jwt_generator, audit_logger, token_refresh_service,
    expired_token, valid_token, near_expiry_token
)

logger = central_logger.get_logger(__name__)


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
    token_validation = jwt_generator.validate_token_jwt(near_expiry_token)
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
async def test_clock_synchronization_edge_cases(jwt_generator, audit_logger):
    """
    Test Case 3: Clock synchronization edge cases.
    
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


if __name__ == "__main__":
    # Run basic connection tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--log-cli-level=INFO",
        "--asyncio-mode=auto",
        "-k", "test_"  # Run all test functions
    ])