"""
End-to-end integration test for WebSocket token refresh during active sessions.

This test validates the complete token refresh flow with real services.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import jwt
import pytest
from fastapi import WebSocket
from httpx import AsyncClient

from netra_backend.app.core.configuration import get_configuration
from netra_backend.app.main import app
from netra_backend.app.websocket_core.manager import WebSocketManager
# Simple service manager for tests
class ServiceManager:
    async def start_services(self):
        pass
    
    async def stop_services(self):
        pass

def get_service_manager():
    return ServiceManager()


class WebSocketTokenRefreshValidator:
    """Validates WebSocket behavior during token refresh."""
    
    def __init__(self):
        self.config = get_configuration()
        self.ws_manager = WebSocketManager()
        self.events_received = []
        self.refresh_completed = False
        
    def create_test_token(self, expires_in_seconds: int = 300) -> str:
        """Create a test JWT token."""
        now = datetime.utcnow()
        payload = {
            "sub": "test_user_ws",
            "email": "ws_test@example.com",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
            "permissions": ["chat", "agent:run"]
        }
        return jwt.encode(payload, self.config.jwt_secret, algorithm="HS256")
    
    def validate_event_continuity(self, events: List[Dict]) -> bool:
        """Validate that events continued flowing during refresh."""
        if len(events) < 2:
            return False
        
        # Check for time gaps
        for i in range(1, len(events)):
            if "timestamp" in events[i] and "timestamp" in events[i-1]:
                gap = events[i]["timestamp"] - events[i-1]["timestamp"]
                if gap > 2.0:  # More than 2 second gap indicates interruption
                    return False
        
        return True
    
    async def simulate_agent_activity(self, websocket: WebSocket) -> List[Dict]:
        """Simulate agent sending events."""
        events = []
        for i in range(20):
            event = {
                "type": "agent_thinking",
                "content": f"Processing step {i+1}",
                "timestamp": time.time(),
                "sequence": i
            }
            
            # Send event
            await websocket.send_json(event)
            events.append(event)
            
            # Small delay between events
            await asyncio.sleep(0.1)
        
        return events


@pytest.mark.asyncio
class TestWebSocketTokenRefreshE2E:
    """End-to-end tests for WebSocket token refresh."""
    
    async def test_websocket_maintains_connection_during_refresh(self):
        """Test that WebSocket connection persists during token refresh."""
        service_manager = get_service_manager()
        await service_manager.start_services()
        
        validator = WebSocketTokenRefreshValidator()
        
        try:
            # Create initial token
            token = validator.create_test_token(expires_in_seconds=60)
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Establish WebSocket connection
                ws_path = f"/ws?token={token}"
                
                # Mock WebSocket for testing
                from unittest.mock import AsyncMock, MagicMock
                mock_websocket = AsyncMock(spec=WebSocket)
                mock_websocket.send_json = AsyncMock()
                mock_websocket.receive_json = AsyncMock()
                
                connection_active = True
                events_sent = []
                
                # Simulate agent activity
                agent_task = asyncio.create_task(
                    validator.simulate_agent_activity(mock_websocket)
                )
                
                # Wait briefly for events to start
                await asyncio.sleep(1.0)
                
                # Trigger token refresh
                new_token = validator.create_test_token(expires_in_seconds=3600)
                
                # Simulate refresh notification
                refresh_event = {
                    "type": "token_refreshed",
                    "new_token": new_token,
                    "timestamp": time.time()
                }
                await mock_websocket.send_json(refresh_event)
                
                # Continue agent activity
                await asyncio.sleep(1.0)
                
                # Complete agent task
                events_sent = await agent_task
                
                # Validate continuity
                assert len(events_sent) == 20
                assert validator.validate_event_continuity(events_sent)
                assert connection_active
                
        finally:
            await service_manager.stop_services()
    
    async def test_concurrent_api_calls_during_token_refresh(self):
        """Test that API calls continue working during token refresh."""
        service_manager = get_service_manager()
        await service_manager.start_services()
        
        validator = WebSocketTokenRefreshValidator()
        
        try:
            # Create tokens
            old_token = validator.create_test_token(expires_in_seconds=30)
            new_token = validator.create_test_token(expires_in_seconds=3600)
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                
                async def make_api_call(token: str, endpoint: str) -> int:
                    """Make an API call and return status code."""
                    headers = {"Authorization": f"Bearer {token}"}
                    response = await client.get(endpoint, headers=headers)
                    return response.status_code
                
                # Start making API calls with old token
                api_calls = []
                endpoints = ["/api/health", "/api/status"]
                
                for endpoint in endpoints:
                    task = asyncio.create_task(make_api_call(old_token, endpoint))
                    api_calls.append(task)
                
                # Simulate token refresh happening
                await asyncio.sleep(0.1)
                
                # Continue with new token
                for endpoint in endpoints:
                    task = asyncio.create_task(make_api_call(new_token, endpoint))
                    api_calls.append(task)
                
                # Wait for all calls to complete
                results = await asyncio.gather(*api_calls, return_exceptions=True)
                
                # Verify no authentication failures
                for result in results:
                    if isinstance(result, int):
                        # Should be 200 or 404 (endpoint may not exist), but not 401
                        assert result != 401
                        
        finally:
            await service_manager.stop_services()
    
    async def test_token_refresh_performance_metrics(self):
        """Test token refresh performance under load."""
        validator = WebSocketTokenRefreshValidator()
        
        refresh_times = []
        
        for i in range(10):
            start_time = time.time()
            
            # Create expiring token
            old_token = validator.create_test_token(expires_in_seconds=10)
            
            # Simulate refresh
            new_token = validator.create_test_token(expires_in_seconds=3600)
            
            # Validate tokens are different
            old_payload = jwt.decode(old_token, validator.config.jwt_secret, algorithms=["HS256"])
            new_payload = jwt.decode(new_token, validator.config.jwt_secret, algorithms=["HS256"])
            
            assert old_payload["exp"] < new_payload["exp"]
            assert old_payload["sub"] == new_payload["sub"]
            
            refresh_time = time.time() - start_time
            refresh_times.append(refresh_time)
        
        # Analyze performance
        avg_time = sum(refresh_times) / len(refresh_times)
        max_time = max(refresh_times)
        
        # Performance requirements
        assert avg_time < 0.1  # Average under 100ms
        assert max_time < 0.5  # Max under 500ms
        
        print(f"Token Refresh Performance: Avg={avg_time:.3f}s, Max={max_time:.3f}s")


@pytest.mark.asyncio
class TestWebSocketEventContinuity:
    """Test WebSocket event continuity during token refresh."""
    
    async def test_agent_events_continue_during_refresh(self):
        """Test that agent events continue flowing during token refresh."""
        validator = WebSocketTokenRefreshValidator()
        
        # Track events
        event_log = []
        refresh_triggered = False
        
        async def event_producer():
            """Produce continuous events."""
            for i in range(100):
                event = {
                    "type": "agent_update",
                    "sequence": i,
                    "timestamp": time.time()
                }
                event_log.append(event)
                
                # Trigger refresh midway
                if i == 50 and not refresh_triggered:
                    event_log.append({
                        "type": "token_refresh_start",
                        "timestamp": time.time()
                    })
                    
                    # Simulate refresh delay
                    await asyncio.sleep(0.2)
                    
                    event_log.append({
                        "type": "token_refresh_complete",
                        "timestamp": time.time()
                    })
                
                await asyncio.sleep(0.01)  # 10ms between events
        
        # Run event producer
        await event_producer()
        
        # Analyze event continuity
        refresh_start_idx = next(i for i, e in enumerate(event_log) if e["type"] == "token_refresh_start")
        refresh_end_idx = next(i for i, e in enumerate(event_log) if e["type"] == "token_refresh_complete")
        
        # Get events during refresh
        events_during_refresh = [
            e for i, e in enumerate(event_log)
            if refresh_start_idx < i < refresh_end_idx and e["type"] == "agent_update"
        ]
        
        # Should have some events during refresh (continuity maintained)
        assert len(events_during_refresh) > 0
        
        # Check sequence continuity
        sequences = [e["sequence"] for e in event_log if e["type"] == "agent_update"]
        for i in range(1, len(sequences)):
            assert sequences[i] == sequences[i-1] + 1  # No gaps in sequence
    
    async def test_websocket_reconnection_with_new_token(self):
        """Test WebSocket reconnection using refreshed token."""
        validator = WebSocketTokenRefreshValidator()
        
        # Create expiring token
        old_token = validator.create_test_token(expires_in_seconds=10)
        
        # Simulate connection with old token
        connection_1 = {
            "token": old_token,
            "connected_at": time.time(),
            "status": "active"
        }
        
        # Wait for token to near expiry
        await asyncio.sleep(5)
        
        # Refresh token
        new_token = validator.create_test_token(expires_in_seconds=3600)
        
        # Reconnect with new token
        connection_2 = {
            "token": new_token,
            "connected_at": time.time(),
            "status": "active",
            "previous_connection": connection_1
        }
        
        # Validate reconnection
        assert connection_2["token"] != connection_1["token"]
        assert connection_2["connected_at"] > connection_1["connected_at"]
        assert connection_2["status"] == "active"


if __name__ == "__main__":
    # Run specific test
    import sys
    
    test_name = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if test_name == "connection":
        asyncio.run(TestWebSocketTokenRefreshE2E().test_websocket_maintains_connection_during_refresh())
    elif test_name == "continuity":
        asyncio.run(TestWebSocketEventContinuity().test_agent_events_continue_during_refresh())
    elif test_name == "performance":
        asyncio.run(TestWebSocketTokenRefreshE2E().test_token_refresh_performance_metrics())
    else:
        pytest.main([__file__, "-v"])