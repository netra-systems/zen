"""
First-time user onboarding flow integration tests.

BVJ (Business Value Justification):
1. Segment: Free → Early (Initial value demonstration)
2. Business Goal: Protect $25K MRR by ensuring immediate value delivery
3. Value Impact: Validates chat initialization and WebSocket reliability
4. Strategic Impact: Critical for user activation and retention
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


# Test framework import - using pytest fixtures instead

import asyncio
import time
import uuid
from typing import Any, Dict

import httpx
import pytest
from fastapi import status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.models.message import Message

from netra_backend.app.models.thread import Thread
from netra_backend.tests.integration.first_time_user_fixtures import (
    agent_dispatcher,
    assert_websocket_message_flow,
    verify_user_in_database,
    wait_for_agent_response,
    websocket_manager,
)

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
@pytest.mark.asyncio
async def test_first_chat_session_initialization(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    websocket_manager,
    agent_dispatcher,
    async_session: AsyncSession
):
    """Test first chat session setup for new users."""
    user_id = authenticated_user["user_id"]
    access_token = authenticated_user["access_token"]
    
    async with async_client.websocket_connect(f"/ws?token={access_token}") as websocket:
        # Send first optimization message
        ack = await assert_websocket_message_flow(
            websocket, 
            "I want to optimize my AI costs by 20% without losing quality"
        )
        thread_id = ack["thread_id"]
        
        # Receive agent selection notification
        agent_selection = await websocket.receive_json()
        assert agent_selection["type"] == "agent_selection"
        assert "supervisor" in agent_selection["agents"]
        
        # Get meaningful agent response
        response = await wait_for_agent_response(websocket)
        assert "cost" in response["content"].lower()
        assert "optimization" in response["content"].lower()

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_chat_thread_persistence(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession,
    redis_client: Redis
):
    """Test chat threads are properly stored."""
    user_id = authenticated_user["user_id"]
    access_token = authenticated_user["access_token"]
    
    async with async_client.websocket_connect(f"/ws?token={access_token}") as websocket:
        ack = await assert_websocket_message_flow(websocket, "Test message for persistence")
        thread_id = ack["thread_id"]
        
        # Verify thread created in database
        thread = await async_session.get(Thread, thread_id)
        assert thread is not None
        assert thread.user_id == user_id
        assert thread.status == "active"
        
        # Verify messages stored
        messages = await async_session.query(Message).filter(
            Message.thread_id == thread_id
        ).all()
        assert len(messages) >= 1
        
        # Verify usage tracked in Redis
        usage_key = f"usage:{user_id}:daily"
        usage_count = await redis_client.get(usage_key)
        assert int(usage_count or 0) >= 1

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
@pytest.mark.asyncio
async def test_websocket_connection_lifecycle(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    websocket_manager,
    redis_client: Redis
):
    """Test WebSocket connection reliability through network issues."""
    access_token = authenticated_user["access_token"]
    user_id = authenticated_user["user_id"]
    
    # Establish initial connection and send message
    async with async_client.websocket_connect(f"/ws?token={access_token}") as websocket:
        # Test heartbeat mechanism
        await websocket.send_json({"type": "ping"})
        pong = await websocket.receive_json()
        assert pong["type"] == "pong"
        assert "timestamp" in pong
        
        # Track connection ID
        ack = await assert_websocket_message_flow(websocket, "Test connection tracking")
        connection_id = ack.get("connection_id")
        
        # Verify connection tracked in Redis
        connection_key = f"ws:connection:{user_id}"
        stored_connection = await redis_client.get(connection_key)
        assert stored_connection is not None
    
    # Test reconnection with state recovery
    async with async_client.websocket_connect(f"/ws?token={access_token}") as websocket:
        await websocket.send_json({
            "type": "reconnect",
            "previous_connection_id": connection_id
        })
        
        recovery = await websocket.receive_json()
        assert recovery["type"] == "state_recovered"
        assert "missed_messages" in recovery

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_websocket_concurrent_messages(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test WebSocket handles multiple concurrent messages."""
    access_token = authenticated_user["access_token"]
    
    async with async_client.websocket_connect(f"/ws?token={access_token}") as websocket:
        # Send 10 concurrent messages
        tasks = []
        for i in range(10):
            task = websocket.send_json({
                "type": "user_message",
                "content": f"Concurrent message {i}",
                "thread_id": str(uuid.uuid4())
            })
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Receive all acknowledgments
        acks_received = 0
        start_time = time.time()
        while acks_received < 10 and time.time() - start_time < 10:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                if msg["type"] == "message_acknowledged":
                    acks_received += 1
            except asyncio.TimeoutError:
                continue
        
        assert acks_received == 10

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_session_persistence_across_refresh(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    redis_client: Redis
):
    """Test session state persists across browser refresh."""
    access_token = authenticated_user["access_token"]
    refresh_token = authenticated_user["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Create session state
    thread_id = str(uuid.uuid4())
    response = await async_client.post(
        "/api/chat/message",
        json={"content": "Test persistence message", "thread_id": thread_id},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Set UI state
    ui_state = {
        "theme": "dark",
        "active_thread": thread_id,
        "draft_message": "Draft message content"
    }
    response = await async_client.put("/api/session/ui-state", json=ui_state, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    # Simulate refresh - get new token
    response = await async_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == status.HTTP_200_OK
    new_access_token = response.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_access_token}"}
    
    # Restore and verify session
    response = await async_client.get("/api/session/restore", headers=new_headers)
    assert response.status_code == status.HTTP_200_OK
    restored_session = response.json()
    assert thread_id in [t["id"] for t in restored_session["threads"]]

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
@pytest.mark.asyncio
async def test_multi_agent_coordination_flow(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    agent_dispatcher
):
    """Test multi-agent orchestration for complex requests."""
    access_token = authenticated_user["access_token"]
    
    complex_request = {
        "content": """Analyze my AI costs, evaluate performance, and create roadmap""",
        "thread_id": str(uuid.uuid4()),
        "context": {"monthly_spend": 10000, "models": [LLMModel.GEMINI_2_5_FLASH.value, "claude-3"]}
    }
    
    async with async_client.websocket_connect(f"/ws?token={access_token}") as websocket:
        # Send complex request requiring multiple agents
        await websocket.send_json({"type": "user_message", **complex_request})
        
        # Track agent coordination
        agents_involved = set()
        coordination_complete = False
        start_time = time.time()
        
        while time.time() - start_time < 45:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                
                if msg["type"] == "agent_selection":
                    agents_involved.update(msg["agents"])
                elif msg["type"] == "agent_response":
                    coordination_complete = True
                    final_response = msg
                    break
            except asyncio.TimeoutError:
                continue
        
        assert coordination_complete
        assert len(agents_involved) >= 3  # Multiple agents involved
        assert "supervisor" in agents_involved
        
        # Verify comprehensive response
        content = final_response["content"].lower()
        assert "cost" in content and "roadmap" in content