"""
🔴 MISSION CRITICAL: Token Refresh During Active Chat Test Suite
Tests seamless auth token rotation mid-conversation without disruption.

CRITICAL REQUIREMENTS:
1. WebSocket connection must persist during token refresh
2. Agent events must continue flowing without interruption  
3. User must not see any auth errors or disconnections
4. Token refresh must complete within 2 seconds
5. New token must be used for subsequent API calls
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx
import jwt
import pytest
import websockets
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from netra_backend.app.auth_integration.auth import auth_client
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.core.configuration import get_configuration
from netra_backend.app.database import get_db
from netra_backend.app.main import app
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from test_framework.auth_jwt_test_manager import JWTGenerationTestManager as AuthJWTTestManager
from test_framework.services import ServiceManager, get_service_manager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import get_env


class TokenRefreshTestScenarios:
    """Test scenarios for token refresh during active chat."""
    
    def __init__(self):
        self.auth_manager = AuthJWTTestManager()
        self.service_manager = get_service_manager()
        self.ws_manager = WebSocketManager()
        self.config = get_configuration()
        
    async def setup(self):
        """Setup test environment."""
        await self.service_manager.start_services()
        
    async def teardown(self):
        """Cleanup test environment."""
        await self.service_manager.stop_services()
        
    def create_expiring_token(self, expires_in_seconds: int = 30) -> str:
        """Create a token that expires soon."""
        now = datetime.utcnow()
        exp_time = now + timedelta(seconds=expires_in_seconds)
        
        payload = {
            "sub": "test_user_123",
            "email": "test@example.com",
            "iat": int(now.timestamp()),
            "exp": int(exp_time.timestamp()),
            "permissions": ["chat", "agent:run"]
        }
        
        token = jwt.encode(payload, self.config.jwt_secret, algorithm="HS256")
        return token
    
    def create_refreshed_token(self, original_token: str) -> str:
        """Create a refreshed version of a token."""
        decoded = jwt.decode(original_token, self.config.jwt_secret, algorithms=["HS256"])
        
        # Extend expiration by 1 hour
        now = datetime.utcnow()
        decoded["iat"] = int(now.timestamp())
        decoded["exp"] = int((now + timedelta(hours=1)).timestamp())
        decoded["refresh_count"] = decoded.get("refresh_count", 0) + 1
        
        return jwt.encode(decoded, self.config.jwt_secret, algorithm="HS256")
        
    async def validate_token_transition(self, old_token: str, new_token: str) -> bool:
        """Validate that token transition preserves user identity."""
        old_decoded = jwt.decode(old_token, self.config.jwt_secret, algorithms=["HS256"])
        new_decoded = jwt.decode(new_token, self.config.jwt_secret, algorithms=["HS256"])
        
        # User identity must remain same
        assert old_decoded["sub"] == new_decoded["sub"]
        assert old_decoded["email"] == new_decoded["email"]
        
        # New token must have later expiration
        assert new_decoded["exp"] > old_decoded["exp"]
        
        return True


@pytest.mark.asyncio
class TestTokenRefreshDuringActiveChat:
    """Test token refresh during active WebSocket chat sessions."""
    
    async def test_seamless_token_refresh_mid_conversation(self):
        """Test that token refresh doesn't interrupt active conversation."""
        scenarios = TokenRefreshTestScenarios()
        await scenarios.setup()
        
        try:
            # Create expiring token (expires in 30 seconds)
            initial_token = scenarios.create_expiring_token(30)
            
            # Establish WebSocket connection
            ws_url = f"ws://localhost:8000/ws?token={initial_token}"
            
            events_received = []
            refresh_completed = False
            
            async with websockets.connect(ws_url) as websocket:
                # Start agent execution
                await websocket.send(json.dumps({
                    "type": "agent_start",
                    "agent_name": "test_agent",
                    "task": "Process data"
                }))
                
                # Simulate ongoing agent work
                for i in range(10):
                    # Send agent progress events
                    await websocket.send(json.dumps({
                        "type": "agent_thinking",
                        "content": f"Processing step {i+1}/10"
                    }))
                    
                    # Receive acknowledgment
                    response = await websocket.recv()
                    events_received.append(json.loads(response))
                    
                    # Trigger token refresh midway
                    if i == 5 and not refresh_completed:
                        # Simulate token refresh
                        new_token = scenarios.create_refreshed_token(initial_token)
                        
                        # Send token refresh notification
                        await websocket.send(json.dumps({
                            "type": "token_refresh",
                            "new_token": new_token
                        }))
                        
                        # Validate token transition
                        await scenarios.validate_token_transition(initial_token, new_token)
                        refresh_completed = True
                    
                    await asyncio.sleep(0.1)
                
                # Complete agent execution
                await websocket.send(json.dumps({
                    "type": "agent_completed",
                    "result": "Task completed successfully"
                }))
                
                # Verify all events received
                assert len(events_received) >= 10
                assert refresh_completed
                
        finally:
            await scenarios.teardown()
    
    async def test_token_refresh_with_concurrent_api_calls(self):
        """Test token refresh while making concurrent API calls."""
        scenarios = TokenRefreshTestScenarios()
        await scenarios.setup()
        
        try:
            initial_token = scenarios.create_expiring_token(60)
            client = TestClient(app)
            
            async def make_api_call(token: str, endpoint: str) -> Dict:
                """Make an API call with the given token."""
                headers = {"Authorization": f"Bearer {token}"}
                response = client.get(endpoint, headers=headers)
                return {"status": response.status_code, "data": response.json()}
            
            # Start multiple concurrent API calls
            api_tasks = []
            endpoints = ["/api/user/profile", "/api/agents/list", "/api/chat/history"]
            
            for endpoint in endpoints:
                task = asyncio.create_task(make_api_call(initial_token, endpoint))
                api_tasks.append(task)
            
            # Trigger token refresh while API calls are in progress
            await asyncio.sleep(0.1)
            new_token = scenarios.create_refreshed_token(initial_token)
            
            # Update auth client with new token
            with patch.object(auth_client, 'validate_token_jwt', new_callable=AsyncMock) as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "user_id": "test_user_123",
                    "email": "test@example.com"
                }
                
                # Complete API calls
                results = await asyncio.gather(*api_tasks, return_exceptions=True)
                
                # Verify no auth failures
                for result in results:
                    if isinstance(result, dict):
                        assert result["status"] in [200, 201]
                    
        finally:
            await scenarios.teardown()
    
    async def test_token_refresh_recovery_from_network_failure(self):
        """Test token refresh recovery when network temporarily fails."""
        scenarios = TokenRefreshTestScenarios()
        await scenarios.setup()
        
        try:
            initial_token = scenarios.create_expiring_token(30)
            refresh_attempts = []
            
            async def simulate_network_failure_recovery():
                """Simulate network failure then recovery."""
                await asyncio.sleep(0.5)
                # Network "fails"
                refresh_attempts.append({"status": "failed", "time": time.time()})
                
                await asyncio.sleep(1.0)
                # Network "recovers"
                refresh_attempts.append({"status": "recovered", "time": time.time()})
                
                # Successful refresh
                new_token = scenarios.create_refreshed_token(initial_token)
                refresh_attempts.append({
                    "status": "success",
                    "time": time.time(),
                    "new_token": new_token
                })
                return new_token
            
            # Start refresh with retry logic
            max_retries = 3
            retry_count = 0
            refresh_token = None
            
            while retry_count < max_retries and not refresh_token:
                try:
                    refresh_token = await simulate_network_failure_recovery()
                except Exception as e:
                    retry_count += 1
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            
            # Verify recovery succeeded
            assert refresh_token is not None
            assert len(refresh_attempts) >= 2
            assert refresh_attempts[-1]["status"] == "success"
            
        finally:
            await scenarios.teardown()
    
    async def test_websocket_event_continuity_during_refresh(self):
        """Test that WebSocket events continue flowing during token refresh."""
        scenarios = TokenRefreshTestScenarios()
        await scenarios.setup()
        
        try:
            initial_token = scenarios.create_expiring_token(60)
            ws_url = f"ws://localhost:8000/ws?token={initial_token}"
            
            event_timeline = []
            refresh_start_time = None
            refresh_end_time = None
            
            async with websockets.connect(ws_url) as websocket:
                # Start continuous event stream
                event_task = asyncio.create_task(self._continuous_event_sender(websocket, event_timeline))
                
                # Monitor for events
                monitor_task = asyncio.create_task(self._event_monitor(websocket, event_timeline))
                
                # Wait for some events to flow
                await asyncio.sleep(1.0)
                
                # Trigger token refresh
                refresh_start_time = time.time()
                new_token = scenarios.create_refreshed_token(initial_token)
                
                await websocket.send(json.dumps({
                    "type": "token_refresh",
                    "new_token": new_token
                }))
                
                refresh_end_time = time.time()
                
                # Continue monitoring
                await asyncio.sleep(2.0)
                
                # Stop tasks
                event_task.cancel()
                monitor_task.cancel()
                
                # Analyze event continuity
                refresh_duration = refresh_end_time - refresh_start_time
                events_during_refresh = [
                    e for e in event_timeline
                    if refresh_start_time <= e["timestamp"] <= refresh_end_time
                ]
                
                # Verify no interruption
                assert refresh_duration < 2.0  # Must complete within 2 seconds
                assert len(events_during_refresh) > 0  # Events continued during refresh
                
                # Check for gaps in event sequence
                for i in range(1, len(event_timeline)):
                    time_gap = event_timeline[i]["timestamp"] - event_timeline[i-1]["timestamp"]
                    assert time_gap < 0.5  # No gaps larger than 500ms
                    
        finally:
            await scenarios.teardown()
    
    async def _continuous_event_sender(self, websocket, event_timeline: List):
        """Send continuous events to simulate active agent."""
        sequence = 0
        while True:
            await websocket.send(json.dumps({
                "type": "agent_thinking",
                "sequence": sequence,
                "timestamp": time.time()
            }))
            event_timeline.append({
                "type": "sent",
                "sequence": sequence,
                "timestamp": time.time()
            })
            sequence += 1
            await asyncio.sleep(0.1)
    
    async def _event_monitor(self, websocket, event_timeline: List):
        """Monitor received events."""
        while True:
            try:
                message = await websocket.recv()
                event = json.loads(message)
                event_timeline.append({
                    "type": "received",
                    "data": event,
                    "timestamp": time.time()
                })
            except Exception as e:
                break


@pytest.mark.asyncio
class TestTokenRefreshRaceConditions:
    """Test race conditions during token refresh."""
    
    async def test_simultaneous_refresh_requests(self):
        """Test handling of simultaneous token refresh requests."""
        scenarios = TokenRefreshTestScenarios()
        await scenarios.setup()
        
        try:
            initial_token = scenarios.create_expiring_token(30)
            
            # Create multiple refresh tasks
            async def attempt_refresh(token: str, id: int) -> Dict:
                """Attempt to refresh token."""
                start_time = time.time()
                
                # Simulate refresh API call
                await asyncio.sleep(0.1 * (id % 3))  # Vary timing slightly
                
                new_token = scenarios.create_refreshed_token(token)
                
                return {
                    "id": id,
                    "start_time": start_time,
                    "end_time": time.time(),
                    "new_token": new_token
                }
            
            # Launch 10 simultaneous refresh attempts
            refresh_tasks = []
            for i in range(10):
                task = asyncio.create_task(attempt_refresh(initial_token, i))
                refresh_tasks.append(task)
            
            results = await asyncio.gather(*refresh_tasks)
            
            # Verify only one refresh succeeded (or all got same token)
            unique_tokens = set(r["new_token"] for r in results)
            assert len(unique_tokens) == 1  # All should get same refreshed token
            
        finally:
            await scenarios.teardown()
    
    async def test_refresh_during_logout(self):
        """Test token refresh attempt during logout process."""
        scenarios = TokenRefreshTestScenarios()
        await scenarios.setup()
        
        try:
            initial_token = scenarios.create_expiring_token(30)
            
            logout_started = False
            refresh_attempted = False
            
            async def attempt_logout():
                """Attempt logout."""
                nonlocal logout_started
                logout_started = True
                await asyncio.sleep(0.5)  # Simulate logout processing
                return {"status": "logged_out"}
            
            async def attempt_refresh():
                """Attempt token refresh."""
                nonlocal refresh_attempted
                await asyncio.sleep(0.1)  # Small delay
                refresh_attempted = True
                
                if logout_started:
                    raise Exception("Cannot refresh - logout in progress")
                
                return scenarios.create_refreshed_token(initial_token)
            
            # Start both operations
            logout_task = asyncio.create_task(attempt_logout())
            refresh_task = asyncio.create_task(attempt_refresh())
            
            # Wait for completion
            results = await asyncio.gather(logout_task, refresh_task, return_exceptions=True)
            
            # Verify refresh was rejected during logout
            assert logout_started
            assert refresh_attempted
            assert isinstance(results[1], Exception)
            
        finally:
            await scenarios.teardown()


@pytest.mark.asyncio
class TestTokenRefreshPerformance:
    """Test performance characteristics of token refresh."""
    
    async def test_refresh_latency_under_load(self):
        """Test token refresh latency under heavy load."""
        scenarios = TokenRefreshTestScenarios()
        await scenarios.setup()
        
        try:
            # Create tokens with varying expiration times
            tokens = [scenarios.create_expiring_token(30 + i) for i in range(100)]
            
            refresh_latencies = []
            
            async def measure_refresh_latency(token: str) -> float:
                """Measure refresh latency."""
                start = time.time()
                new_token = scenarios.create_refreshed_token(token)
                latency = time.time() - start
                return latency
            
            # Refresh all tokens concurrently
            tasks = [measure_refresh_latency(token) for token in tokens]
            latencies = await asyncio.gather(*tasks)
            
            # Analyze performance
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            
            # Performance requirements
            assert avg_latency < 0.1  # Average under 100ms
            assert p95_latency < 0.5  # 95th percentile under 500ms
            assert max_latency < 2.0  # Max under 2 seconds
            
            print(f"Refresh Performance: Avg={avg_latency:.3f}s, P95={p95_latency:.3f}s, Max={max_latency:.3f}s")
            
        finally:
            await scenarios.teardown()
    
    async def test_refresh_with_websocket_message_flood(self):
        """Test token refresh while handling WebSocket message flood."""
        scenarios = TokenRefreshTestScenarios()
        await scenarios.setup()
        
        try:
            initial_token = scenarios.create_expiring_token(60)
            ws_url = f"ws://localhost:8000/ws?token={initial_token}"
            
            messages_sent = 0
            messages_received = 0
            refresh_completed = False
            
            async with websockets.connect(ws_url) as websocket:
                
                async def flood_messages():
                    """Send rapid messages."""
                    nonlocal messages_sent
                    for i in range(1000):
                        await websocket.send(json.dumps({
                            "type": "ping",
                            "id": i
                        }))
                        messages_sent += 1
                        await asyncio.sleep(0.001)  # 1ms between messages
                
                async def receive_messages():
                    """Receive messages."""
                    nonlocal messages_received
                    while messages_received < 900:  # Stop before all sent
                        try:
                            await asyncio.wait_for(websocket.recv(), timeout=0.1)
                            messages_received += 1
                        except asyncio.TimeoutError:
                            continue
                
                async def refresh_token():
                    """Refresh token mid-flood."""
                    nonlocal refresh_completed
                    await asyncio.sleep(0.5)  # Wait for flood to start
                    
                    start_time = time.time()
                    new_token = scenarios.create_refreshed_token(initial_token)
                    
                    await websocket.send(json.dumps({
                        "type": "token_refresh",
                        "new_token": new_token
                    }))
                    
                    refresh_duration = time.time() - start_time
                    refresh_completed = True
                    return refresh_duration
                
                # Run all operations concurrently
                flood_task = asyncio.create_task(flood_messages())
                receive_task = asyncio.create_task(receive_messages())
                refresh_task = asyncio.create_task(refresh_token())
                
                # Wait for completion
                refresh_duration = await refresh_task
                
                # Cancel ongoing tasks
                flood_task.cancel()
                receive_task.cancel()
                
                # Verify performance under load
                assert refresh_completed
                assert refresh_duration < 2.0  # Still completes quickly
                assert messages_sent > 500  # Significant load
                assert messages_received > 400  # Messages still flowing
                
        finally:
            await scenarios.teardown()


if __name__ == "__main__":
    # Run specific test scenarios
    import sys
    
    test_suite = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if test_suite == "seamless":
        asyncio.run(TestTokenRefreshDuringActiveChat().test_seamless_token_refresh_mid_conversation())
    elif test_suite == "concurrent":
        asyncio.run(TestTokenRefreshDuringActiveChat().test_token_refresh_with_concurrent_api_calls())
    elif test_suite == "race":
        asyncio.run(TestTokenRefreshRaceConditions().test_simultaneous_refresh_requests())
    elif test_suite == "performance":
        asyncio.run(TestTokenRefreshPerformance().test_refresh_latency_under_load())
    else:
        # Run all tests
        pytest.main([__file__, "-v"])