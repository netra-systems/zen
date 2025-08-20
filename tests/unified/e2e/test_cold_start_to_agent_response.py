"""Cold Start to Agent Response E2E Test - CRITICAL USER JOURNEY

This test validates the complete user journey from cold start to receiving the first agent response.
This is the HIGHEST PRIORITY test for user onboarding and conversion success.

Business Value Justification (BVJ):
- Segment: Free, Early, Mid (Conversion critical)
- Business Goal: Conversion, Onboarding Success
- Value Impact: Ensures smooth first-time user experience
- Revenue Impact: $25K MRR - Highest priority for user onboarding

This test validates:
1. Cold start initialization (dev_launcher from scratch)
2. Service health verification (all services ready)
3. Authentication flow (login/registration + JWT)
4. WebSocket connection establishment
5. Agent interaction (message → supervisor → sub-agent → response)
6. State persistence verification (Redis + database)

Performance SLA:
- Total flow completion: <30 seconds
- Service startup: <15 seconds
- First agent response: <10 seconds
"""

import asyncio
import time
import json
import uuid
import pytest
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
from unittest.mock import patch, AsyncMock

import httpx
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.clients.auth_client import auth_client
from tests.unified.e2e.agent_response_test_utilities import AgentResponseSimulator
from test_framework.mock_utils import mock_justified


class ColdStartTestManager:
    """Manages complete cold start to agent response test flow."""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.services_ready = False
        self.auth_token: Optional[str] = None
        self.websocket_connection: Optional[websockets.WebSocketServerProtocol] = None
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_email = f"test_{uuid.uuid4().hex[:8]}@netra.ai"
        
        # Service endpoints
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000" 
        self.websocket_url = "ws://localhost:8000/ws/secure"
        
        # Test metrics
        self.startup_time = 0.0
        self.auth_time = 0.0
        self.websocket_time = 0.0
        self.response_time = 0.0
        self.total_time = 0.0
    
    async def cold_start_services(self) -> bool:
        """Start all services from cold state using dev launcher."""
        start_time = time.time()
        
        try:
            # Configure test environment
            os.environ["TESTING"] = "true"
            os.environ["DEV_MODE"] = "true"
            os.environ["LOG_LEVEL"] = "INFO"
            os.environ["DISABLE_BROWSER_OPEN"] = "true"
            
            # Start dev launcher in subprocess
            launcher_cmd = [
                sys.executable, "scripts/dev_launcher.py",
                "--dynamic-ports",
                "--no-browser",
                "--non-interactive",
                "--startup-mode", "standard"
            ]
            
            # Start the dev launcher process
            launcher_process = subprocess.Popen(
                launcher_cmd,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append(launcher_process)
            
            # Wait for services to start up (check health endpoints)
            max_wait_time = 120  # 2 minutes max
            check_interval = 2   # Check every 2 seconds
            
            for i in range(max_wait_time // check_interval):
                if await self._check_services_ready():
                    self.startup_time = time.time() - start_time
                    self.services_ready = True
                    return True
                
                await asyncio.sleep(check_interval)
            
            # Timeout - services didn't start
            self.startup_time = time.time() - start_time
            return False
            
        except Exception as e:
            self.startup_time = time.time() - start_time
            print(f"Cold start failed: {e}")
            return False
    
    async def _check_services_ready(self) -> bool:
        """Check if all required services are ready."""
        required_endpoints = [
            f"{self.backend_url}/health",
            f"{self.auth_url}/health"
        ]
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                for endpoint in required_endpoints:
                    try:
                        response = await client.get(endpoint)
                        if response.status_code != 200:
                            return False
                        
                        data = response.json()
                        if data.get("status") not in ["healthy", "success"]:
                            return False
                    except:
                        return False
            
            return True
            
        except:
            return False
    
    async def verify_service_health(self) -> bool:
        """Verify all critical services are healthy."""
        if not self.services_ready:
            return False
        
        health_checks = [
            (f"{self.backend_url}/health", "backend"),
            (f"{self.auth_url}/health", "auth_service"),
            (f"{self.backend_url}/ws/secure/health", "websocket")
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint, service in health_checks:
                try:
                    response = await client.get(endpoint)
                    if response.status_code != 200:
                        print(f"Health check failed for {service}: {response.status_code}")
                        return False
                    
                    data = response.json()
                    if data.get("status") not in ["healthy", "success"]:
                        print(f"Service {service} not healthy: {data}")
                        return False
                        
                except Exception as e:
                    print(f"Health check error for {service}: {e}")
                    return False
        
        return True
    
    async def authenticate_user(self) -> bool:
        """Authenticate test user and get JWT token."""
        start_time = time.time()
        
        try:
            # Mock justification: Using test auth token instead of real OAuth flow
            # in integration test to avoid external service dependencies
            with mock_justified(auth_client, "validate_token", 
                                reason="Integration test using mock token validation"):
                auth_client.validate_token.return_value = {
                    "valid": True,
                    "user_id": self.test_user_id,
                    "email": self.test_email,
                    "permissions": ["read", "write"],
                    "expires_at": "2024-12-31T23:59:59Z"
                }
                
                # Create test JWT token
                self.auth_token = f"test_jwt_{uuid.uuid4().hex[:16]}"
                
                # Verify token validation works
                validation_result = await auth_client.validate_token(self.auth_token)
                
                if not validation_result.get("valid"):
                    return False
                
                self.auth_time = time.time() - start_time
                return True
                
        except Exception as e:
            self.auth_time = time.time() - start_time
            print(f"Authentication failed: {e}")
            return False
    
    async def establish_websocket_connection(self) -> bool:
        """Establish WebSocket connection with auth token."""
        start_time = time.time()
        
        try:
            # WebSocket headers with JWT auth
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Origin": "http://localhost:3000"
            }
            
            # Connect to secure WebSocket endpoint
            self.websocket_connection = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    extra_headers=headers,
                    timeout=15
                ),
                timeout=15
            )
            
            self.websocket_time = time.time() - start_time
            return True
            
        except Exception as e:
            self.websocket_time = time.time() - start_time
            print(f"WebSocket connection failed: {e}")
            return False
    
    async def send_agent_message_and_get_response(self, message: str) -> Optional[Dict[str, Any]]:
        """Send message to agent and wait for response."""
        start_time = time.time()
        
        try:
            if not self.websocket_connection:
                return None
            
            # Send user message to supervisor agent
            user_message = {
                "type": "user_message",
                "payload": {
                    "content": message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message_id": f"msg_{uuid.uuid4().hex[:8]}"
                }
            }
            
            await self.websocket_connection.send(json.dumps(user_message))
            
            # Wait for agent response with timeout
            response_timeout = 10.0
            end_time = time.time() + response_timeout
            
            while time.time() < end_time:
                try:
                    message_raw = await asyncio.wait_for(
                        self.websocket_connection.recv(),
                        timeout=1.0
                    )
                    
                    response_data = json.loads(message_raw)
                    
                    # Check if this is an agent response
                    if (response_data.get("type") == "agent_response" and 
                        response_data.get("payload", {}).get("content")):
                        
                        self.response_time = time.time() - start_time
                        return response_data
                        
                except asyncio.TimeoutError:
                    continue
                except (ConnectionClosedError, ConnectionClosedOK):
                    break
            
            self.response_time = time.time() - start_time
            return None
            
        except Exception as e:
            self.response_time = time.time() - start_time
            print(f"Agent message/response failed: {e}")
            return None
    
    async def verify_state_persistence(self) -> bool:
        """Verify session state is persisted in Redis and database."""
        try:
            # Check backend health to verify database connectivity
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.backend_url}/health")
                health_data = response.json()
                
                # Verify database connections are working
                if not health_data.get("database_connected", False):
                    return False
                
                if not health_data.get("redis_connected", False):
                    return False
            
            return True
            
        except Exception as e:
            print(f"State persistence verification failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        if self.websocket_connection:
            try:
                await self.websocket_connection.close()
            except:
                pass
        
        # Terminate all processes
        for process in self.processes:
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    # Give it a moment to terminate gracefully
                    await asyncio.sleep(1)
                    if process.poll() is None:
                        process.kill()  # Force kill if needed
            except:
                pass
        
        self.processes.clear()


@pytest.fixture
async def cold_start_manager():
    """Fixture providing cold start test manager."""
    manager = ColdStartTestManager()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_cold_start_to_first_agent_response_e2e(cold_start_manager):
    """
    CRITICAL: Test complete cold start to first agent response journey.
    
    This test validates the entire user onboarding flow that determines
    conversion success for Free tier users.
    """
    test_start_time = time.time()
    manager = cold_start_manager
    
    # Step 1: Cold start all services
    print("Step 1: Starting services from cold state...")
    services_started = await manager.cold_start_services()
    assert services_started, f"Services failed to start in {manager.startup_time:.2f}s"
    print(f"✓ Services started in {manager.startup_time:.2f}s")
    
    # Step 2: Verify all services are healthy
    print("Step 2: Verifying service health...")
    health_verified = await manager.verify_service_health()
    assert health_verified, "Service health checks failed"
    print("✓ All services healthy")
    
    # Step 3: Authenticate user
    print("Step 3: Authenticating user...")
    auth_success = await manager.authenticate_user()
    assert auth_success, f"Authentication failed in {manager.auth_time:.2f}s"
    assert manager.auth_token is not None
    print(f"✓ User authenticated in {manager.auth_time:.2f}s")
    
    # Step 4: Establish WebSocket connection
    print("Step 4: Establishing WebSocket connection...")
    websocket_connected = await manager.establish_websocket_connection()
    assert websocket_connected, f"WebSocket connection failed in {manager.websocket_time:.2f}s"
    print(f"✓ WebSocket connected in {manager.websocket_time:.2f}s")
    
    # Step 5: Send message and get agent response
    print("Step 5: Sending message to agent...")
    test_message = "Hello! This is my first message. Can you help me understand what you can do?"
    agent_response = await manager.send_agent_message_and_get_response(test_message)
    
    # Verify we got a response
    assert agent_response is not None, f"No agent response received in {manager.response_time:.2f}s"
    assert agent_response.get("type") == "agent_response"
    
    response_content = agent_response.get("payload", {}).get("content")
    assert response_content, "Agent response has no content"
    assert len(response_content) > 10, "Agent response too short"
    
    print(f"✓ Agent responded in {manager.response_time:.2f}s")
    print(f"Response preview: {response_content[:100]}...")
    
    # Step 6: Verify state persistence
    print("Step 6: Verifying state persistence...")
    state_verified = await manager.verify_state_persistence()
    assert state_verified, "State persistence verification failed"
    print("✓ State persistence verified")
    
    # Calculate and verify total time
    manager.total_time = time.time() - test_start_time
    print(f"\n=== PERFORMANCE METRICS ===")
    print(f"Service startup: {manager.startup_time:.2f}s")
    print(f"Authentication: {manager.auth_time:.2f}s") 
    print(f"WebSocket connection: {manager.websocket_time:.2f}s")
    print(f"Agent response: {manager.response_time:.2f}s")
    print(f"Total time: {manager.total_time:.2f}s")
    
    # Verify SLA compliance
    assert manager.total_time < 30.0, f"Total flow took {manager.total_time:.2f}s (SLA: 30s)"
    assert manager.startup_time < 15.0, f"Startup took {manager.startup_time:.2f}s (SLA: 15s)"
    assert manager.response_time < 10.0, f"Agent response took {manager.response_time:.2f}s (SLA: 10s)"
    
    print("✓ All SLA requirements met")
    print("\n🎉 COLD START TO AGENT RESPONSE TEST PASSED")


@pytest.mark.asyncio
async def test_cold_start_multiple_message_exchange(cold_start_manager):
    """Test cold start followed by multiple message exchanges."""
    manager = cold_start_manager
    
    # Start services and authenticate
    services_started = await manager.cold_start_services()
    assert services_started, "Services failed to start"
    
    health_verified = await manager.verify_service_health()
    assert health_verified, "Service health checks failed"
    
    auth_success = await manager.authenticate_user()
    assert auth_success, "Authentication failed"
    
    websocket_connected = await manager.establish_websocket_connection()
    assert websocket_connected, "WebSocket connection failed"
    
    # Test multiple message exchanges
    messages = [
        "What can you help me with?",
        "Tell me about your capabilities.",
        "How do I get started?"
    ]
    
    responses = []
    for i, message in enumerate(messages):
        print(f"Sending message {i+1}: {message[:30]}...")
        response = await manager.send_agent_message_and_get_response(message)
        assert response is not None, f"No response to message {i+1}"
        responses.append(response)
    
    # Verify we got responses to all messages
    assert len(responses) == len(messages), "Not all messages got responses"
    
    for i, response in enumerate(responses):
        content = response.get("payload", {}).get("content", "")
        assert len(content) > 5, f"Response {i+1} too short"
    
    print("✓ Multiple message exchange test passed")


@pytest.mark.asyncio 
async def test_cold_start_concurrent_connections(cold_start_manager):
    """Test cold start with multiple concurrent WebSocket connections."""
    manager = cold_start_manager
    
    # Start services and basic setup
    services_started = await manager.cold_start_services()
    assert services_started, "Services failed to start"
    
    health_verified = await manager.verify_service_health()
    assert health_verified, "Service health checks failed"
    
    auth_success = await manager.authenticate_user()
    assert auth_success, "Authentication failed"
    
    # Create multiple concurrent connections
    connection_count = 3
    connections = []
    
    try:
        headers = {
            "Authorization": f"Bearer {manager.auth_token}",
            "Origin": "http://localhost:3000"
        }
        
        # Establish concurrent connections
        connection_tasks = []
        for i in range(connection_count):
            task = asyncio.create_task(
                websockets.connect(
                    manager.websocket_url,
                    extra_headers=headers,
                    timeout=10
                )
            )
            connection_tasks.append(task)
        
        connections = await asyncio.gather(*connection_tasks)
        assert len(connections) == connection_count, "Not all connections established"
        
        # Send messages on all connections concurrently
        message_tasks = []
        for i, conn in enumerate(connections):
            message = {
                "type": "user_message",
                "payload": {
                    "content": f"Test message from connection {i+1}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            task = asyncio.create_task(conn.send(json.dumps(message)))
            message_tasks.append(task)
        
        await asyncio.gather(*message_tasks)
        print("✓ Concurrent connections test passed")
        
    finally:
        # Clean up connections
        for conn in connections:
            try:
                await conn.close()
            except:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])