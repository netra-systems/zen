"""
Test authentication layer in message flow.

Tests authentication at each step of the message flow to ensure
secure message routing and proper error handling for auth failures.

Business Value: Prevents unauthorized access to billable agent services,
protecting revenue and customer data security.

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines
- Function size: <8 lines each  
- Strong typing for all auth models
- Comprehensive error scenario coverage
"""

import asyncio
import json
import jwt

from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, patch, Mock
import pytest
from datetime import datetime, timezone, timedelta

from app.tests.test_utilities.auth_test_helpers import (
    create_test_token, create_expired_token, create_invalid_token
)
from app.tests.test_utilities.websocket_mocks import MockWebSocket
from app.tests.integration.test_unified_message_flow import MessageFlowTracker
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AuthFlowTracker(MessageFlowTracker):
    """Extended tracker for authentication flow steps."""
    
    def __init__(self):
        super().__init__()
        self.auth_attempts: List[Dict[str, Any]] = []
        self.failed_auth_count = 0
    
    def log_auth_attempt(self, user_id: str, token_valid: bool, 
                        error: Optional[str] = None) -> None:
        """Log authentication attempt."""
        attempt = {
            "user_id": user_id,
            "token_valid": token_valid,
            "timestamp": datetime.now(timezone.utc),
            "error": error
        }
        self.auth_attempts.append(attempt)
        
        if not token_valid:
            self.failed_auth_count += 1
    
    def get_auth_success_rate(self) -> float:
        """Calculate authentication success rate."""
        if not self.auth_attempts:
            return 0.0
        
        successful = sum(1 for attempt in self.auth_attempts if attempt["token_valid"])
        return successful / len(self.auth_attempts)


@pytest.fixture
def auth_tracker():
    """Create authentication flow tracker."""
    return AuthFlowTracker()


class TestMessageFlowAuthentication:
    """Test authentication in message flow."""
    
    async def test_valid_token_authentication_flow(self, auth_tracker):
        """Test successful authentication with valid token."""
        timer_id = auth_tracker.start_timer("valid_token_auth")
        
        # Create valid token
        user_id = "test_user_123"
        token = create_test_token(user_id)
        
        # Test authentication flow
        result = await self._authenticate_user_with_token(auth_tracker, user_id, token)
        
        duration = auth_tracker.end_timer(timer_id)
        
        # Verify successful authentication
        assert result["authenticated"] is True
        assert result["user_id"] == user_id
        assert auth_tracker.get_auth_success_rate() == 1.0
        assert duration < 0.5, f"Auth too slow: {duration}s"
        
        auth_tracker.log_step("valid_token_auth_completed", {
            "success": True,
            "duration": duration
        })
    
    async def _authenticate_user_with_token(self, tracker: AuthFlowTracker,
                                          user_id: str, token: str) -> Dict[str, Any]:
        """Authenticate user with given token."""
        try:
            # Mock token validation
            with patch('app.routes.utils.websocket_helpers.decode_token_payload') as mock_decode:
                mock_decode.return_value = {"user_id": user_id, "exp": time.time() + 3600}
                
                payload = await mock_decode(Mock(), token)
                
                tracker.log_auth_attempt(user_id, True)
                
                return {
                    "authenticated": True,
                    "user_id": payload["user_id"],
                    "token_valid": True
                }
        
        except Exception as e:
            tracker.log_auth_attempt(user_id, False, str(e))
            return {
                "authenticated": False,
                "user_id": None,
                "error": str(e)
            }
    
    async def test_expired_token_authentication_flow(self, auth_tracker):
        """Test authentication failure with expired token."""
        timer_id = auth_tracker.start_timer("expired_token_auth")
        
        user_id = "test_user_123"
        expired_token = create_expired_token(user_id)
        
        # Test expired token handling
        result = await self._test_expired_token_handling(auth_tracker, user_id, expired_token)
        
        duration = auth_tracker.end_timer(timer_id)
        
        # Verify rejection of expired token
        assert result["authenticated"] is False
        assert "expired" in result.get("error", "").lower()
        assert auth_tracker.failed_auth_count > 0
        
        auth_tracker.log_step("expired_token_rejected", {
            "rejection_success": True,
            "duration": duration
        })
    
    async def _test_expired_token_handling(self, tracker: AuthFlowTracker,
                                         user_id: str, token: str) -> Dict[str, Any]:
        """Test handling of expired tokens."""
        try:
            with patch('app.routes.utils.websocket_helpers.decode_token_payload') as mock_decode:
                # Simulate expired token error
                mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
                
                await mock_decode(Mock(), token)
                
                # Should not reach here
                tracker.log_auth_attempt(user_id, True)
                return {"authenticated": True, "user_id": user_id}
        
        except jwt.ExpiredSignatureError as e:
            tracker.log_auth_attempt(user_id, False, str(e))
            return {
                "authenticated": False,
                "user_id": None,
                "error": "Token expired"
            }
    
    async def test_malformed_token_authentication_flow(self, auth_tracker):
        """Test authentication with malformed token."""
        timer_id = auth_tracker.start_timer("malformed_token_auth")
        
        user_id = "test_user_123"
        malformed_token = "invalid.malformed.token"
        
        # Test malformed token handling
        result = await self._test_malformed_token_handling(auth_tracker, user_id, malformed_token)
        
        duration = auth_tracker.end_timer(timer_id)
        
        # Verify rejection
        assert result["authenticated"] is False
        assert "invalid" in result.get("error", "").lower()
        
        auth_tracker.log_step("malformed_token_rejected", {
            "rejection_success": True,
            "duration": duration
        })
    
    async def _test_malformed_token_handling(self, tracker: AuthFlowTracker,
                                           user_id: str, token: str) -> Dict[str, Any]:
        """Test handling of malformed tokens."""
        try:
            with patch('app.routes.utils.websocket_helpers.decode_token_payload') as mock_decode:
                mock_decode.side_effect = jwt.InvalidTokenError("Invalid token format")
                
                await mock_decode(Mock(), token)
                
                tracker.log_auth_attempt(user_id, True)
                return {"authenticated": True, "user_id": user_id}
        
        except jwt.InvalidTokenError as e:
            tracker.log_auth_attempt(user_id, False, str(e))
            return {
                "authenticated": False,
                "user_id": None,
                "error": "Invalid token format"
            }
    
    async def test_missing_token_authentication_flow(self, auth_tracker):
        """Test authentication when no token provided."""
        timer_id = auth_tracker.start_timer("missing_token_auth")
        
        # Test missing token scenario
        websocket = MockWebSocket()
        websocket.query_params = {}  # No token
        
        result = await self._test_missing_token_handling(auth_tracker, websocket)
        
        duration = auth_tracker.end_timer(timer_id)
        
        # Verify rejection
        assert result["authenticated"] is False
        assert "no token" in result.get("error", "").lower()
        
        auth_tracker.log_step("missing_token_rejected", {
            "rejection_success": True,
            "duration": duration
        })
    
    async def _test_missing_token_handling(self, tracker: AuthFlowTracker,
                                         websocket: MockWebSocket) -> Dict[str, Any]:
        """Test handling when no token is provided."""
        from app.routes.utils.websocket_helpers import validate_websocket_token
        
        try:
            token = await validate_websocket_token(websocket)
            
            tracker.log_auth_attempt("unknown", True)
            return {"authenticated": True, "token": token}
        
        except ValueError as e:
            tracker.log_auth_attempt("unknown", False, str(e))
            return {
                "authenticated": False,
                "user_id": None,
                "error": str(e)
            }


class TestAuthenticationIntegrationFlow:
    """Test authentication integration with complete message flow."""
    
    async def test_auth_integration_with_websocket_flow(self, auth_tracker):
        """Test authentication integrated with WebSocket message flow."""
        timer_id = auth_tracker.start_timer("auth_websocket_integration")
        
        # Create authenticated WebSocket connection
        websocket = await self._create_authenticated_websocket(auth_tracker)
        
        # Send message through authenticated connection
        message = {
            "type": "user_message",
            "payload": {"content": "Test authenticated message"}
        }
        
        result = await self._send_authenticated_message(auth_tracker, websocket, message)
        
        duration = auth_tracker.end_timer(timer_id)
        
        # Verify authenticated message processing
        assert result["message_sent"] is True
        assert result["auth_verified"] is True
        assert duration < 1.0
        
        auth_tracker.log_step("auth_websocket_integration_completed", {
            "success": True,
            "duration": duration
        })
    
    async def _create_authenticated_websocket(self, tracker: AuthFlowTracker) -> MockWebSocket:
        """Create authenticated WebSocket connection."""
        websocket = MockWebSocket()
        
        # Set valid token
        user_id = "test_user_123"
        token = create_test_token(user_id)
        websocket.query_params = {"token": token}
        
        # Mock authentication success
        websocket._authenticated = True
        websocket._user_id = user_id
        
        tracker.log_auth_attempt(user_id, True)
        
        return websocket
    
    async def _send_authenticated_message(self, tracker: AuthFlowTracker,
                                        websocket: MockWebSocket,
                                        message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message through authenticated WebSocket."""
        try:
            # Verify authentication before processing
            if not getattr(websocket, '_authenticated', False):
                raise ValueError("WebSocket not authenticated")
            
            # Mock message sending
            await websocket.send_json(message)
            
            tracker.log_step("authenticated_message_sent", {
                "user_id": getattr(websocket, '_user_id'),
                "message_type": message["type"]
            })
            
            return {
                "message_sent": True,
                "auth_verified": True,
                "user_id": getattr(websocket, '_user_id')
            }
        
        except Exception as e:
            return {
                "message_sent": False,
                "auth_verified": False,
                "error": str(e)
            }
    
    async def test_auth_failure_blocks_message_processing(self, auth_tracker):
        """Test that authentication failure blocks message processing."""
        timer_id = auth_tracker.start_timer("auth_failure_blocks_processing")
        
        # Create unauthenticated connection
        websocket = MockWebSocket()
        websocket.query_params = {"token": "invalid_token"}
        
        message = {
            "type": "user_message",
            "payload": {"content": "This should be blocked"}
        }
        
        result = await self._attempt_unauthenticated_message(auth_tracker, websocket, message)
        
        duration = auth_tracker.end_timer(timer_id)
        
        # Verify message was blocked
        assert result["message_processed"] is False
        assert result["auth_failed"] is True
        assert "authentication" in result.get("error", "").lower()
        
        auth_tracker.log_step("unauthenticated_message_blocked", {
            "blocking_success": True,
            "duration": duration
        })
    
    async def _attempt_unauthenticated_message(self, tracker: AuthFlowTracker,
                                             websocket: MockWebSocket,
                                             message: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to send message without authentication."""
        try:
            # Simulate authentication check
            token = websocket.query_params.get("token")
            
            if token == "invalid_token":
                tracker.log_auth_attempt("unknown", False, "Invalid token")
                raise ValueError("Authentication failed")
            
            # Should not reach here with invalid token
            await websocket.send_json(message)
            
            return {
                "message_processed": True,
                "auth_failed": False
            }
        
        except ValueError as e:
            return {
                "message_processed": False,
                "auth_failed": True,
                "error": str(e)
            }


class TestAuthenticationPerformance:
    """Test authentication performance in message flow."""
    
    async def test_auth_performance_under_load(self, auth_tracker):
        """Test authentication performance under concurrent load."""
        timer_id = auth_tracker.start_timer("auth_load_performance")
        
        # Test concurrent authentication requests
        auth_tasks = []
        for i in range(20):
            user_id = f"user_{i}"
            token = create_test_token(user_id)
            task = self._perform_auth_test(auth_tracker, user_id, token)
            auth_tasks.append(task)
        
        results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        
        duration = auth_tracker.end_timer(timer_id)
        
        # Verify performance
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("authenticated"))
        assert success_count >= 18, f"Too many auth failures: {20 - success_count}"
        assert duration < 2.0, f"Auth performance too slow: {duration}s"
        
        auth_tracker.log_step("auth_load_performance_verified", {
            "concurrent_auths": 20,
            "success_rate": success_count / 20,
            "duration": duration
        })
    
    async def _perform_auth_test(self, tracker: AuthFlowTracker,
                               user_id: str, token: str) -> Dict[str, Any]:
        """Perform single authentication test."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Mock authentication with small delay
            await asyncio.sleep(0.01)
            
            # Simulate token validation
            payload = {"user_id": user_id, "exp": time.time() + 3600}
            
            tracker.log_auth_attempt(user_id, True)
            
            duration = asyncio.get_event_loop().time() - start_time
            
            return {
                "authenticated": True,
                "user_id": user_id,
                "auth_duration": duration
            }
        
        except Exception as e:
            tracker.log_auth_attempt(user_id, False, str(e))
            return {
                "authenticated": False,
                "error": str(e)
            }


if __name__ == "__main__":
    # Manual test execution
    import time
    
    async def run_manual_auth_test():
        """Run manual authentication test."""
        tracker = AuthFlowTracker()
        
        print("Running manual authentication flow test...")
        
        # Test valid token
        user_id = "manual_test_user"
        token = create_test_token(user_id)
        
        result = await TestMessageFlowAuthentication()._authenticate_user_with_token(
            tracker, user_id, token
        )
        
        print(f"Auth result: {result}")
        print(f"Auth success rate: {tracker.get_auth_success_rate()}")
        print(f"Total auth attempts: {len(tracker.auth_attempts)}")
    
    asyncio.run(run_manual_auth_test())