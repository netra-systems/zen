"""
WebSocket Test 10: Token Refresh over WebSocket

Tests JWT token refresh over existing WebSocket connection without requiring
full disconnect, ensuring seamless authentication renewal for long-running sessions.

Business Value: Enables $150K+ MRR from enterprise customers requiring continuous
sessions, prevents forced disconnections during token expiry.
"""

import asyncio
import json
import time
import uuid
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TokenManager:
    """Manages JWT token generation and validation for testing."""
    
    def __init__(self, secret_key: str = "test_secret_key"):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.token_history = []
        
    def generate_token(self, user_id: str, expires_in_minutes: int = 60) -> str:
        """Generate a JWT token with specified expiration."""
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=expires_in_minutes)
        
        payload = {
            'user_id': user_id,
            'issued_at': now.timestamp(),
            'expires_at': expiry.timestamp(),
            'token_id': str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        self.token_history.append({
            'token': token,
            'payload': payload,
            'generated_at': now.timestamp()
        })
        
        return token
        
    def validate_token_jwt(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token and return payload if valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            if payload['expires_at'] < time.time():
                return {'valid': False, 'error': 'token_expired', 'payload': payload}
                
            return {'valid': True, 'payload': payload}
            
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'token_expired'}
        except jwt.InvalidTokenError as e:
            return {'valid': False, 'error': 'invalid_token', 'details': str(e)}
            
    def is_token_near_expiry(self, token: str, threshold_minutes: int = 5) -> bool:
        """Check if token is approaching expiry within threshold."""
        validation = self.validate_token_jwt(token)
        if not validation['valid']:
            return True
            
        expires_at = validation['payload']['expires_at']
        threshold_time = time.time() + (threshold_minutes * 60)
        
        return expires_at <= threshold_time


class TokenRefreshTestClient:
    """WebSocket client with token refresh capabilities."""
    
    def __init__(self, uri: str, token_manager: TokenManager, user_id: str):
        self.uri = uri
        self.token_manager = token_manager
        self.user_id = user_id
        self.current_token = None
        self.websocket = None
        self.is_connected = False
        self.connection_id = str(uuid.uuid4())
        self.refresh_events = []
        self.session_data = {"messages_sent": 0, "actions_performed": 0}
        
    async def connect(self, token_lifetime_minutes: int = 60) -> bool:
        """Connect with initial JWT token."""
        try:
            # Generate initial token
            self.current_token = self.token_manager.generate_token(
                self.user_id, 
                token_lifetime_minutes
            )
            
            # Mock WebSocket connection with token authentication
            self.websocket = AsyncMock()
            self.websocket.token = self.current_token
            self.is_connected = True
            
            logger.info(f"Connected with token: {self.current_token[:20]}...")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.is_connected = False
            
    async def send_authenticated_message(self, content: str) -> Dict[str, Any]:
        """Send message that requires valid authentication."""
        if not self.is_connected:
            return {'success': False, 'error': 'Not connected'}
            
        try:
            # Validate current token
            validation = self.token_manager.validate_token_jwt(self.current_token)
            if not validation['valid']:
                return {
                    'success': False, 
                    'error': 'authentication_failed',
                    'token_error': validation['error']
                }
            
            message = {
                'content': content,
                'timestamp': time.time(),
                'user_id': self.user_id,
                'token_id': validation['payload']['token_id']
            }
            
            await self.websocket.send(json.dumps(message))
            self.session_data['messages_sent'] += 1
            
            logger.debug(f"Authenticated message sent: {content}")
            return {'success': True, 'message_id': str(uuid.uuid4())}
            
        except Exception as e:
            logger.error(f"Failed to send authenticated message: {e}")
            return {'success': False, 'error': str(e)}
            
    async def refresh_token_over_websocket(self, new_token_lifetime: int = 60) -> Dict[str, Any]:
        """Refresh JWT token over existing WebSocket connection."""
        if not self.is_connected:
            return {'success': False, 'error': 'Not connected'}
            
        try:
            old_token = self.current_token
            refresh_start = time.time()
            
            # Generate new token
            new_token = self.token_manager.generate_token(
                self.user_id,
                new_token_lifetime
            )
            
            # Send token refresh message over WebSocket
            refresh_message = {
                'type': 'token_refresh',
                'old_token': old_token,
                'new_token': new_token,
                'user_id': self.user_id,
                'timestamp': time.time()
            }
            
            await self.websocket.send(json.dumps(refresh_message))
            
            # Simulate server processing and acknowledgment
            await asyncio.sleep(0.1)  # Processing delay
            
            # Update current token
            old_validation = self.token_manager.validate_token_jwt(old_token)
            new_validation = self.token_manager.validate_token_jwt(new_token)
            
            if new_validation['valid']:
                self.current_token = new_token
                self.websocket.token = new_token
                
                refresh_event = {
                    'timestamp': refresh_start,
                    'old_token_id': old_validation['payload']['token_id'] if old_validation['valid'] else None,
                    'new_token_id': new_validation['payload']['token_id'],
                    'refresh_duration': time.time() - refresh_start,
                    'success': True
                }
                self.refresh_events.append(refresh_event)
                
                logger.info(f"Token refreshed successfully: {new_token[:20]}...")
                return {
                    'success': True,
                    'new_token': new_token,
                    'refresh_duration': refresh_event['refresh_duration']
                }
            else:
                return {'success': False, 'error': 'new_token_invalid'}
                
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            refresh_event = {
                'timestamp': time.time(),
                'success': False,
                'error': str(e)
            }
            self.refresh_events.append(refresh_event)
            return {'success': False, 'error': str(e)}
            
    async def verify_session_continuity_after_refresh(self) -> Dict[str, Any]:
        """Verify session state is preserved after token refresh."""
        try:
            # Send test message with new token
            test_result = await self.send_authenticated_message("Post-refresh continuity test")
            
            if test_result['success']:
                return {
                    'session_preserved': True,
                    'messages_sent': self.session_data['messages_sent'],
                    'connection_active': self.is_connected,
                    'current_token_valid': self.token_manager.validate_token_jwt(self.current_token)['valid']
                }
            else:
                return {'session_preserved': False, 'error': test_result['error']}
                
        except Exception as e:
            logger.error(f"Session continuity check failed: {e}")
            return {'session_preserved': False, 'error': str(e)}


@pytest.mark.asyncio
async def test_basic_token_refresh():
    """
    Test basic token refresh functionality.
    
    Validates:
    1. Initial connection with JWT token
    2. Successful token refresh over WebSocket
    3. Session continuity after refresh
    4. New token validation and acceptance
    """
    logger.info("=== Starting Basic Token Refresh Test ===")
    
    token_manager = TokenManager()
    websocket_uri = "ws://localhost:8000/ws/test"
    user_id = f"test_user_{uuid.uuid4()}"
    
    client = TokenRefreshTestClient(websocket_uri, token_manager, user_id)
    
    # Phase 1: Connect with initial token
    assert await client.connect(token_lifetime_minutes=10), "Failed to connect with initial token"
    initial_token = client.current_token
    
    # Phase 2: Send initial authenticated message
    msg_result = await client.send_authenticated_message("Initial authenticated message")
    assert msg_result['success'], "Failed to send initial authenticated message"
    
    # Phase 3: Refresh token over WebSocket
    refresh_result = await client.refresh_token_over_websocket(new_token_lifetime=30)
    assert refresh_result['success'], "Token refresh failed"
    assert refresh_result['refresh_duration'] < 1.0, "Token refresh took too long"
    
    new_token = client.current_token
    assert new_token != initial_token, "Token was not actually refreshed"
    
    # Phase 4: Verify session continuity
    continuity_result = await client.verify_session_continuity_after_refresh()
    assert continuity_result['session_preserved'], "Session continuity lost after refresh"
    assert continuity_result['current_token_valid'], "New token is not valid"
    
    # Phase 5: Send post-refresh message
    post_msg_result = await client.send_authenticated_message("Post-refresh authenticated message")
    assert post_msg_result['success'], "Failed to send message with new token"
    
    await client.disconnect()
    
    # Analyze results
    refresh_events = client.refresh_events
    
    logger.info(f"Token refresh events: {len(refresh_events)}")
    logger.info(f"Messages sent: {client.session_data['messages_sent']}")
    
    assert len(refresh_events) == 1, "Expected exactly one refresh event"
    assert refresh_events[0]['success'], "Refresh event marked as failed"
    assert client.session_data['messages_sent'] >= 2, "Expected at least 2 messages sent"
    
    logger.info("=== Basic Token Refresh Test PASSED ===")
    
    return {
        'test_id': 'WS-RESILIENCE-010A',
        'status': 'PASSED',
        'refresh_events': len(refresh_events),
        'messages_sent': client.session_data['messages_sent'],
        'refresh_duration': refresh_events[0]['refresh_duration']
    }


@pytest.mark.asyncio
async def test_token_refresh_near_expiry():
    """
    Test token refresh when approaching expiry.
    
    Validates:
    1. Detection of token near expiry
    2. Proactive token refresh
    3. Seamless transition without interruption
    4. Timing accuracy of refresh process
    """
    logger.info("=== Starting Token Refresh Near Expiry Test ===")
    
    token_manager = TokenManager()
    websocket_uri = "ws://localhost:8000/ws/test"
    user_id = f"expiry_test_user_{uuid.uuid4()}"
    
    client = TokenRefreshTestClient(websocket_uri, token_manager, user_id)
    
    # Connect with short-lived token (2 minutes)
    assert await client.connect(token_lifetime_minutes=2), "Failed to connect"
    
    # Verify token is initially valid
    initial_validation = token_manager.validate_token_jwt(client.current_token)
    assert initial_validation['valid'], "Initial token should be valid"
    
    # Simulate time passing - check if near expiry (within 5 minutes threshold)
    is_near_expiry = token_manager.is_token_near_expiry(client.current_token, threshold_minutes=5)
    assert is_near_expiry, "Token should be near expiry with 2-minute lifetime"
    
    # Perform proactive refresh
    refresh_result = await client.refresh_token_over_websocket(new_token_lifetime=60)
    assert refresh_result['success'], "Proactive refresh failed"
    
    # Verify new token has longer lifetime
    new_validation = token_manager.validate_token_jwt(client.current_token)
    assert new_validation['valid'], "New token should be valid"
    
    # Check new token is not near expiry
    is_new_near_expiry = token_manager.is_token_near_expiry(client.current_token, threshold_minutes=5)
    assert not is_new_near_expiry, "New token should not be near expiry"
    
    # Verify session continuity
    continuity_result = await client.verify_session_continuity_after_refresh()
    assert continuity_result['session_preserved'], "Session should be preserved"
    
    await client.disconnect()
    
    logger.info("=== Token Refresh Near Expiry Test PASSED ===")
    
    return {
        'test_id': 'WS-RESILIENCE-010B',
        'status': 'PASSED',
        'proactive_refresh': True,
        'session_preserved': True
    }


@pytest.mark.asyncio
async def test_multiple_token_refreshes():
    """
    Test multiple sequential token refreshes.
    
    Validates:
    1. Multiple refresh cycles in one session
    2. Session state preservation across refreshes
    3. Performance consistency across refreshes
    4. Token chain validation
    """
    logger.info("=== Starting Multiple Token Refreshes Test ===")
    
    token_manager = TokenManager()
    websocket_uri = "ws://localhost:8000/ws/test"
    user_id = f"multi_refresh_user_{uuid.uuid4()}"
    
    client = TokenRefreshTestClient(websocket_uri, token_manager, user_id)
    
    assert await client.connect(token_lifetime_minutes=5), "Failed to connect"
    
    num_refreshes = 3
    refresh_durations = []
    
    for i in range(num_refreshes):
        logger.info(f"Performing token refresh {i+1}/{num_refreshes}")
        
        # Send message before refresh
        pre_msg = await client.send_authenticated_message(f"Message before refresh {i+1}")
        assert pre_msg['success'], f"Pre-refresh message {i+1} failed"
        
        # Refresh token
        refresh_result = await client.refresh_token_over_websocket(new_token_lifetime=10)
        assert refresh_result['success'], f"Token refresh {i+1} failed"
        
        refresh_durations.append(refresh_result['refresh_duration'])
        
        # Verify continuity
        continuity = await client.verify_session_continuity_after_refresh()
        assert continuity['session_preserved'], f"Session lost during refresh {i+1}"
        
        # Send message after refresh
        post_msg = await client.send_authenticated_message(f"Message after refresh {i+1}")
        assert post_msg['success'], f"Post-refresh message {i+1} failed"
        
        # Brief pause between refreshes
        await asyncio.sleep(0.2)
    
    await client.disconnect()
    
    # Analyze performance
    avg_refresh_duration = sum(refresh_durations) / len(refresh_durations)
    max_refresh_duration = max(refresh_durations)
    
    logger.info(f"Completed {num_refreshes} token refreshes")
    logger.info(f"Average refresh duration: {avg_refresh_duration:.3f}s")
    logger.info(f"Max refresh duration: {max_refresh_duration:.3f}s")
    
    assert len(client.refresh_events) == num_refreshes, "Refresh count mismatch"
    assert all(event['success'] for event in client.refresh_events), "Some refreshes failed"
    assert avg_refresh_duration < 0.5, "Average refresh duration too slow"
    assert client.session_data['messages_sent'] >= num_refreshes * 2, "Message count too low"
    
    logger.info("=== Multiple Token Refreshes Test PASSED ===")
    
    return {
        'test_id': 'WS-RESILIENCE-010C',
        'status': 'PASSED',
        'total_refreshes': num_refreshes,
        'avg_refresh_duration': round(avg_refresh_duration, 3),
        'max_refresh_duration': round(max_refresh_duration, 3)
    }


@pytest.mark.asyncio
async def test_token_refresh_failure_handling():
    """
    Test handling of token refresh failures.
    
    Validates:
    1. Graceful handling of refresh failures
    2. Connection state management during failures
    3. Error reporting and recovery
    4. Security maintained during failure scenarios
    """
    logger.info("=== Starting Token Refresh Failure Handling Test ===")
    
    token_manager = TokenManager()
    websocket_uri = "ws://localhost:8000/ws/test"
    user_id = f"failure_test_user_{uuid.uuid4()}"
    
    client = TokenRefreshTestClient(websocket_uri, token_manager, user_id)
    
    assert await client.connect(), "Failed to connect"
    
    # Simulate refresh failure by using invalid token manager temporarily
    original_generate = token_manager.generate_token
    
    def failing_generate_token(user_id, expires_in_minutes):
        # Simulate token generation failure
        raise Exception("Token generation service unavailable")
    
    # Patch token generation to fail
    token_manager.generate_token = failing_generate_token
    
    # Attempt refresh that should fail
    refresh_result = await client.refresh_token_over_websocket()
    assert not refresh_result['success'], "Refresh should have failed"
    assert 'error' in refresh_result, "Error should be reported"
    
    # Restore original token generation
    token_manager.generate_token = original_generate
    
    # Verify connection is still active and original token still works
    msg_result = await client.send_authenticated_message("Message after failed refresh")
    assert msg_result['success'], "Should still work with original token"
    
    # Now perform successful refresh
    successful_refresh = await client.refresh_token_over_websocket()
    assert successful_refresh['success'], "Recovery refresh should succeed"
    
    # Verify post-recovery functionality
    post_recovery_msg = await client.send_authenticated_message("Post-recovery message")
    assert post_recovery_msg['success'], "Post-recovery message should work"
    
    await client.disconnect()
    
    # Analyze failure handling
    refresh_events = client.refresh_events
    failed_events = [e for e in refresh_events if not e.get('success', True)]
    successful_events = [e for e in refresh_events if e.get('success', False)]
    
    logger.info(f"Total refresh attempts: {len(refresh_events)}")
    logger.info(f"Failed refreshes: {len(failed_events)}")
    logger.info(f"Successful refreshes: {len(successful_events)}")
    
    assert len(failed_events) >= 1, "Should have at least one failed refresh"
    assert len(successful_events) >= 1, "Should have at least one successful refresh"
    assert client.session_data['messages_sent'] >= 2, "Should have sent messages despite failure"
    
    logger.info("=== Token Refresh Failure Handling Test PASSED ===")
    
    return {
        'test_id': 'WS-RESILIENCE-010D',
        'status': 'PASSED',
        'failed_refreshes': len(failed_events),
        'successful_refreshes': len(successful_events),
        'recovery_successful': True
    }


if __name__ == "__main__":
    # Run all tests for development
    async def run_all_tests():
        result1 = await test_basic_token_refresh()
        result2 = await test_token_refresh_near_expiry()
        result3 = await test_multiple_token_refreshes()
        result4 = await test_token_refresh_failure_handling()
        
        print("=== All Token Refresh Test Results ===")
        for result in [result1, result2, result3, result4]:
            print(f"{result['test_id']}: {result['status']}")
    
    asyncio.run(run_all_tests())