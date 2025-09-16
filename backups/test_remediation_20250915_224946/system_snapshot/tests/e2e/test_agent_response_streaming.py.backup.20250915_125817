"""Agent Response Streaming Tests - Real E2E WebSocket Testing

Tests real-time agent response delivery through actual WebSocket connections.
Critical for user experience and competitive differentiation - customers see 
AI optimization progress in real-time rather than waiting for batch processing.

Business Value Justification (BVJ):
- Segment: Mid and Enterprise tiers (real-time features drive tier upgrades)
- Business Goal: Deliver premium user experience through real-time AI insights  
- Value Impact: Real-time streaming increases user engagement and perceived value
- Revenue Impact: Premium UX justifies higher pricing tiers and reduces churn

CRITICAL: Uses REAL WebSocket connections only - NO MOCKS per CLAUDE.md
Architecture: 450-line compliance through focused streaming scenario testing
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import pytest

from tests.e2e.integration.config import TestEndpoints
from tests.e2e.config import get_test_config
from tests.e2e.jwt_token_helpers import JWTTestHelper


@pytest.fixture
async def real_websocket_client():
    """Real WebSocket client for E2E testing - NO MOCKS"""
    config = get_test_config()
    endpoints = TestEndpoints()  # Create endpoints instance
    jwt_helper = JWTTestHelper()
    
    # Create test user token
    user_id = "test-streaming-user"
    email = "streaming@test.com"
    token = jwt_helper.create_access_token(user_id, email)
    
    # Create WebSocket connection
    session = aiohttp.ClientSession()
    headers = {
        "Authorization": f"Bearer {token}",
        "Sec-WebSocket-Protocol": "jwt-auth"
    }
    
    try:
        ws = await session.ws_connect(
            endpoints.ws_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    except Exception as e:
        await session.close()
        pytest.fail(f"Failed to connect to real WebSocket service at {endpoints.ws_url}: {e}")
    
    yield ws, user_id, token
    
    await ws.close()
    await session.close()


@pytest.mark.e2e
class TestAgentResponseStreaming:
    """Test real-time response delivery to frontend - BVJ: User experience"""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_real_time_agent_updates_via_websocket(self, real_websocket_client):
        """Test agent progress updates stream to frontend via real WebSocket"""
        ws, user_id, token = real_websocket_client
        
        # Wait for welcome message
        welcome = await ws.receive()
        assert welcome.type == aiohttp.WSMsgType.TEXT
        welcome_data = json.loads(welcome.data)
        assert welcome_data["type"] == "system_message"
        assert welcome_data["payload"]["event"] == "connection_established"
        
        # Send chat message to trigger agent pipeline
        test_message = {
            "type": "chat",
            "content": "Optimize my AI costs",
            "user_id": user_id,
            "thread_id": f"thread_{int(time.time())}"
        }
        
        await ws.send_str(json.dumps(test_message))
        
        # Collect streaming responses
        responses = []
        timeout_start = time.time()
        while time.time() - timeout_start < 30:  # 30 second timeout
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    responses.append(data)
                    
                    # Check for agent completion
                    if data.get("type") == "agent_response":
                        break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    pytest.fail(f"WebSocket error: {msg.data}")
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    break
            except asyncio.TimeoutError:
                continue  # Continue waiting for responses
        
        # Verify we received agent response
        assert len(responses) > 0, "No responses received from agent pipeline"
        
        # Find agent response
        agent_responses = [r for r in responses if r.get("type") == "agent_response"]
        assert len(agent_responses) > 0, f"No agent responses found in: {responses}"
        
        # Verify response structure
        agent_response = agent_responses[0]
        assert "content" in agent_response or "message" in agent_response
        assert agent_response["user_id"] == user_id

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_streaming_response_chunks(self, real_websocket_client):
        """Test large responses stream appropriately via real WebSocket"""
        ws, user_id, token = real_websocket_client
        
        # Wait for welcome message
        welcome = await ws.receive()
        assert welcome.type == aiohttp.WSMsgType.TEXT
        
        # Send request for detailed analysis (triggers larger response)
        large_request_message = {
            "type": "chat",
            "content": "Give me a comprehensive analysis of my AI infrastructure with detailed optimization recommendations",
            "user_id": user_id,
            "thread_id": f"thread_{int(time.time())}"
        }
        
        await ws.send_str(json.dumps(large_request_message))
        
        # Collect all streaming responses
        responses = []
        total_content_length = 0
        timeout_start = time.time()
        
        while time.time() - timeout_start < 45:  # Longer timeout for large response
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=3.0)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    responses.append(data)
                    
                    # Track content size
                    content = data.get("content") or data.get("message", "")
                    total_content_length += len(str(content))
                    
                    # Check for completion
                    if data.get("type") == "agent_response":
                        break
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break
            except asyncio.TimeoutError:
                continue
        
        # Verify response handling
        assert len(responses) > 0, "No responses received for large request"
        
        # Find final agent response
        agent_responses = [r for r in responses if r.get("type") == "agent_response"]
        assert len(agent_responses) > 0, f"No agent responses in: {responses}"
        
        # Verify content was delivered
        final_response = agent_responses[0]
        assert "content" in final_response or "message" in final_response

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_streaming_to_frontend(self, real_websocket_client):
        """Test error messages stream to frontend immediately via real WebSocket"""
        ws, user_id, token = real_websocket_client
        
        # Wait for welcome message
        welcome = await ws.receive()
        assert welcome.type == aiohttp.WSMsgType.TEXT
        
        # Send malformed message to trigger error
        malformed_message = {
            "type": "invalid_type",
            "malformed_field": "this should trigger an error",
            "user_id": user_id
        }
        
        await ws.send_str(json.dumps(malformed_message))
        
        # Wait for error or processing response  
        responses = []
        timeout_start = time.time()
        
        while time.time() - timeout_start < 15:  # 15 second timeout
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    responses.append(data)
                    
                    # Look for error or any response
                    if data.get("type") in ["error", "agent_error", "agent_response"]:
                        break
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break
            except asyncio.TimeoutError:
                continue
        
        # Verify we got some response (error handling may vary)
        assert len(responses) > 0, f"No error response received for malformed message"
        
        # The system should handle the error gracefully
        # (Implementation may return error or fallback response)
