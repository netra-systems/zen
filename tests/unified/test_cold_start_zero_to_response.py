"""
Test Suite: Cold Start Zero to Response - Complete Implementation

Business Value Justification (BVJ):
- Segment: Free tier onboarding (highest conversion value)
- Business Goal: $100K+ MRR protection from failed onboarding
- Value Impact: Every failed cold start = lost $99-999/month potential revenue
- Strategic Impact: Sub-5s response time drives 40% higher conversion rates

CRITICAL REQUIREMENTS:
- Complete system cold start from zero state
- Real services with UnifiedTestHarness
- User signup → JWT → Backend init → WebSocket → AI response
- Total flow must complete in < 5 seconds
- Function limit: < 25 lines each
- File limit: < 300 lines total
"""

import pytest
import asyncio
import time
import uuid
import json
from typing import Dict, Any, Optional

from .harness_complete import UnifiedTestHarnessComplete
from .clients.auth_client import AuthTestClient
from .clients.websocket_client import WebSocketTestClient
from .clients.backend_client import BackendTestClient


class TestColdStartZeroToResponse:
    """
    Business Value: $100K+ MRR protection
    Coverage: Complete system initialization and first user interaction
    Performance: < 5 seconds total
    """
    
    async def test_complete_cold_start_flow(self):
        """Test 1: Complete cold start flow in < 5 seconds."""
        async with UnifiedTestHarnessComplete("cold_start_complete") as harness:
            start_time = time.perf_counter()
            
            # Create test user and get JWT
            auth_client = AuthTestClient(harness.get_service_url("auth_service"))
            user_data = await auth_client.create_test_user()
            
            # Establish WebSocket connection and get AI response
            ws_url = f"ws://localhost:8000/ws?token={user_data['token']}"
            ws_client = WebSocketTestClient(ws_url)
            await ws_client.connect()
            await ws_client.send_chat("Help me optimize my AI costs")
            response = await ws_client.receive_until("agent_response", timeout=3.0)
            
            total_time = time.perf_counter() - start_time
            
            # Validate performance and response
            assert total_time < 5.0, f"Cold start too slow: {total_time:.2f}s"
            assert response is not None, "Must receive AI response"
            assert len(response.get("content", "")) > 20, "Response must be meaningful"
            
            await ws_client.disconnect()
            await auth_client.close()
    
    async def test_service_health_during_cold_start(self):
        """Test 2: Service health checks during cold start."""
        async with UnifiedTestHarnessComplete("cold_start_health") as harness:
            auth_client = AuthTestClient(harness.get_service_url("auth_service"))
            backend_client = BackendTestClient(harness.get_service_url("backend"))
            
            # Check auth service health
            auth_healthy = await auth_client.health_check()
            assert auth_healthy, "Auth service must be healthy"
            
            # Check backend service health
            backend_healthy = await backend_client.health_check()
            assert backend_healthy, "Backend service must be healthy"
            
            # Verify system health check
            health_status = await harness.check_system_health()
            assert health_status.get("services_ready", False), "All services must be ready"
            
            await auth_client.close()
            await backend_client.close()
    
    async def test_jwt_token_flow_in_cold_start(self):
        """Test 3: JWT token flow validation."""
        async with UnifiedTestHarnessComplete("cold_start_jwt") as harness:
            auth_client = AuthTestClient(harness.get_service_url("auth_service"))
            backend_client = BackendTestClient(harness.get_service_url("backend"))
            
            # Create user and get JWT
            user_data = await auth_client.create_test_user()
            token = user_data["token"]
            
            # Verify token with auth service and backend
            auth_verification = await auth_client.verify_token(token)
            assert "user" in auth_verification, "Token must contain user data"
            profile = await backend_client.get_user_profile(token)
            assert profile.get("id"), "Backend must accept JWT token"
            
            # Verify WebSocket accepts token
            ws_url = f"ws://localhost:8000/ws?token={token}"
            ws_client = WebSocketTestClient(ws_url)
            connected = await ws_client.connect(timeout=3.0)
            assert connected, "WebSocket must accept JWT token"
            
            await ws_client.disconnect()
            await auth_client.close()
            await backend_client.close()
    
    async def test_error_handling_during_cold_start(self):
        """Test 4: Error handling during cold start."""
        async with UnifiedTestHarnessComplete("cold_start_errors") as harness:
            auth_client = AuthTestClient(harness.get_service_url("auth_service"))
            
            # Test invalid credentials
            with pytest.raises(Exception):
                await auth_client.login("invalid@example.com", "wrongpassword")
            
            # Test malformed requests
            with pytest.raises(Exception):
                await auth_client.register("", "")
            
            # Test invalid token for WebSocket
            ws_url = "ws://localhost:8000/ws?token=invalid_token"
            ws_client = WebSocketTestClient(ws_url)
            connected = await ws_client.connect(timeout=2.0)
            assert not connected, "Invalid token must be rejected"
            
            await auth_client.close()
    
    async def test_concurrent_cold_starts(self):
        """Test 5: Multiple concurrent cold starts."""
        async with UnifiedTestHarnessComplete("cold_start_concurrent") as harness:
            
            async def single_cold_start(user_index: int) -> Dict[str, Any]:
                auth_client = AuthTestClient(harness.get_service_url("auth_service"))
                email = f"concurrent_user_{user_index}_{uuid.uuid4().hex[:8]}@test.com"
                user_data = await auth_client.create_test_user(email=email)
                
                ws_url = f"ws://localhost:8000/ws?token={user_data['token']}"
                ws_client = WebSocketTestClient(ws_url)
                connected = await ws_client.connect(timeout=3.0)
                await ws_client.disconnect()
                await auth_client.close()
                return {"user_index": user_index, "connected": connected}
            
            # Run 3 concurrent cold starts and validate
            start_time = time.perf_counter()
            tasks = [single_cold_start(i) for i in range(3)]
            results = await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_time
            
            assert all(r["connected"] for r in results), "All concurrent starts must succeed"
            assert total_time < 8.0, f"Concurrent cold starts too slow: {total_time:.2f}s"
    
    async def test_cold_start_state_persistence(self):
        """Test 6: State persistence during cold start."""
        async with UnifiedTestHarnessComplete("cold_start_persistence") as harness:
            auth_client = AuthTestClient(harness.get_service_url("auth_service"))
            backend_client = BackendTestClient(harness.get_service_url("backend"))
            
            # Create user and verify data persisted in both services
            user_data = await auth_client.create_test_user()
            token = user_data["token"]
            profile_auth = await auth_client.get_user_profile(token)
            assert profile_auth.get("email") == user_data["email"], "User must persist in auth DB"
            profile_backend = await backend_client.get_user_profile(token)
            assert profile_backend.get("id"), "User context must exist in backend"
            
            # Verify WebSocket session state maintained
            ws_url = f"ws://localhost:8000/ws?token={token}"
            ws_client = WebSocketTestClient(ws_url)
            await ws_client.connect()
            await ws_client.send_chat("Test persistence")
            response = await ws_client.receive(timeout=3.0)
            assert response is not None, "Session must maintain state"
            
            await ws_client.disconnect()
            await auth_client.close()
            await backend_client.close()
    
    async def test_cold_start_performance_breakdown(self):
        """Test 7: Performance breakdown of cold start components."""
        async with UnifiedTestHarnessComplete("cold_start_performance") as harness:
            auth_client = AuthTestClient(harness.get_service_url("auth_service"))
            
            # Measure auth service and JWT generation performance
            auth_start = time.perf_counter()
            health = await auth_client.health_check()
            auth_time = time.perf_counter() - auth_start
            assert health and auth_time < 1.0, f"Auth service too slow: {auth_time:.2f}s"
            
            jwt_start = time.perf_counter()
            user_data = await auth_client.create_test_user()
            jwt_time = time.perf_counter() - jwt_start
            assert jwt_time < 2.0, f"JWT generation too slow: {jwt_time:.2f}s"
            
            # Measure WebSocket handshake performance
            ws_start = time.perf_counter()
            ws_url = f"ws://localhost:8000/ws?token={user_data['token']}"
            ws_client = WebSocketTestClient(ws_url)
            connected = await ws_client.connect()
            ws_time = time.perf_counter() - ws_start
            assert connected and ws_time < 1.0, f"WebSocket handshake too slow: {ws_time:.2f}s"
            
            await auth_client.close(); await ws_client.disconnect()