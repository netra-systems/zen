"""
Comprehensive integration tests for first-time user flows.
Critical for protecting the Free → Early → Paid conversion funnel.

BVJ (Business Value Justification):
1. Segment: Free → Early → Paid (Primary revenue funnel)
2. Business Goal: Protect $570K MRR from first-time user journey failures
3. Value Impact: Each test prevents deployment of broken onboarding flows
4. Strategic Impact: Ensures enterprise-ready user experience

Test Coverage Areas:
- User registration and email verification
- First chat session initialization
- Free tier limits and notifications
- WebSocket connection lifecycle
- API key generation and management
- User profile setup and preferences
- Provider connection flow (OAuth/API)
- First optimization request
- Usage tracking and metering
- Trial to paid conversion flow
- Error recovery and support
- Multi-agent coordination
- Data export and analytics
- Session persistence
- OAuth integration flow
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.user import User, UserPlan
from app.models.thread import Thread
from app.models.message import Message
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.websocket_manager import WebSocketManager
from app.services.usage_service import UsageService
from app.services.billing_service import BillingService
from app.services.agent_dispatcher import AgentDispatcher
from app.services.tool_registry import ToolRegistry
from app.core.config import settings
from app.utils.test_helpers import create_test_user, create_test_session


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
async def test_user_data() -> Dict[str, Any]:
    """Generate unique test user data for each test."""
    timestamp = int(time.time() * 1000)
    return {
        "email": f"test-user-{timestamp}@netratest.com",
        "password": "TestPass123!Secure",
        "full_name": "Test User Integration",
        "company": "Netra Test Corp",
        "accept_terms": True
    }


@pytest.fixture
async def auth_service() -> AuthService:
    """Provide authenticated auth service instance."""
    service = AuthService()
    await service.initialize()
    return service


@pytest.fixture
async def user_service(async_session: AsyncSession) -> UserService:
    """Provide user service with database access."""
    return UserService(db=async_session)


@pytest.fixture
async def websocket_manager(redis_client: Redis) -> WebSocketManager:
    """Provide WebSocket manager with Redis backing."""
    manager = WebSocketManager(redis=redis_client)
    await manager.initialize()
    return manager


@pytest.fixture
async def usage_service(async_session: AsyncSession, redis_client: Redis) -> UsageService:
    """Provide usage tracking service."""
    service = UsageService(db=async_session, redis=redis_client)
    await service.initialize()
    return service


@pytest.fixture
async def agent_dispatcher() -> AgentDispatcher:
    """Provide agent dispatcher for multi-agent coordination."""
    dispatcher = AgentDispatcher()
    await dispatcher.initialize()
    return dispatcher


# ============================================================================
# TEST 1: USER REGISTRATION WITH EMAIL VERIFICATION
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_user_registration_with_email_verification(
    async_client: httpx.AsyncClient,
    test_user_data: Dict[str, Any],
    async_session: AsyncSession,
    redis_client: Redis
):
    """
    Test complete user registration flow with email verification.
    
    BVJ: Protects $30K MRR by ensuring new users can successfully join platform.
    """
    # Step 1: Register new user
    response = await async_client.post(
        "/api/v1/auth/register",
        json=test_user_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "user_id" in data
    assert "verification_token" in data
    user_id = data["user_id"]
    verification_token = data["verification_token"]
    
    # Step 2: Verify user exists in database with is_active=False
    user = await async_session.get(User, user_id)
    assert user is not None
    assert user.email == test_user_data["email"]
    assert user.is_active is False
    assert user.email_verified is False
    
    # Step 3: Verify email verification token in Redis
    token_key = f"email_verify:{verification_token}"
    stored_user_id = await redis_client.get(token_key)
    assert stored_user_id == str(user_id)
    
    # Step 4: Complete email verification
    response = await async_client.post(
        f"/api/v1/auth/verify-email/{verification_token}"
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Step 5: Verify user is now active
    await async_session.refresh(user)
    assert user.is_active is True
    assert user.email_verified is True
    
    # Step 6: Verify user can now authenticate
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    
    # Step 7: Test duplicate registration prevention
    response = await async_client.post(
        "/api/v1/auth/register",
        json=test_user_data
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"].lower()


# ============================================================================
# TEST 2: FIRST CHAT SESSION INITIALIZATION
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_first_chat_session_initialization(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    websocket_manager: WebSocketManager,
    agent_dispatcher: AgentDispatcher,
    async_session: AsyncSession
):
    """
    Test first chat session initialization for new users.
    
    BVJ: Protects $25K MRR by ensuring users get immediate value demonstration.
    """
    user_id = authenticated_user["user_id"]
    access_token = authenticated_user["access_token"]
    
    # Step 1: Establish WebSocket connection
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with async_client.websocket_connect(
        f"/ws?token={access_token}",
        headers=headers
    ) as websocket:
        # Step 2: Send first user message
        first_message = {
            "type": "user_message",
            "content": "I want to optimize my AI costs by 20% without losing quality",
            "thread_id": None  # New thread
        }
        await websocket.send_json(first_message)
        
        # Step 3: Receive acknowledgment
        ack = await websocket.receive_json()
        assert ack["type"] == "message_acknowledged"
        assert "message_id" in ack
        assert "thread_id" in ack
        thread_id = ack["thread_id"]
        
        # Step 4: Receive agent selection notification
        agent_selection = await websocket.receive_json()
        assert agent_selection["type"] == "agent_selection"
        assert "supervisor" in agent_selection["agents"]
        
        # Step 5: Receive agent response
        response_received = False
        start_time = time.time()
        
        while time.time() - start_time < 30:  # 30 second timeout
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=1.0
                )
                if message["type"] == "agent_response":
                    response_received = True
                    assert len(message["content"]) > 50  # Meaningful response
                    assert "cost" in message["content"].lower()
                    assert "optimization" in message["content"].lower()
                    break
            except asyncio.TimeoutError:
                continue
        
        assert response_received, "No agent response received within timeout"
        
        # Step 6: Verify thread created in database
        thread = await async_session.get(Thread, thread_id)
        assert thread is not None
        assert thread.user_id == user_id
        assert thread.status == "active"
        
        # Step 7: Verify messages stored
        messages = await async_session.query(Message).filter(
            Message.thread_id == thread_id
        ).all()
        assert len(messages) >= 2  # User message + agent response
        
        # Step 8: Verify usage tracked
        usage_key = f"usage:{user_id}:daily"
        usage_count = await redis_client.get(usage_key)
        assert int(usage_count) >= 1


# ============================================================================
# TEST 3: FREE TIER LIMITS AND NOTIFICATIONS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_free_tier_limits_and_notifications(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    usage_service: UsageService,
    async_session: AsyncSession,
    redis_client: Redis
):
    """
    Test free tier usage limits and upgrade notifications.
    
    BVJ: Protects $40K MRR by preventing abuse while encouraging upgrades.
    """
    user_id = authenticated_user["user_id"]
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 1: Get current usage and limits
    response = await async_client.get(
        "/api/v1/usage/current",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    usage_data = response.json()
    assert usage_data["plan"] == "free"
    assert usage_data["daily_message_limit"] == 50
    assert usage_data["messages_used_today"] == 0
    
    # Step 2: Simulate approaching daily limit (80%)
    for i in range(40):  # 80% of 50
        await usage_service.track_message(user_id)
    
    # Step 3: Send message near limit - should get warning
    response = await async_client.post(
        "/api/v1/chat/message",
        json={
            "content": "Test message near limit",
            "thread_id": str(uuid.uuid4())
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "warning" in data
    assert "80%" in data["warning"] or "limit" in data["warning"].lower()
    
    # Step 4: Reach daily limit
    for i in range(10):  # Reach 50 messages
        await usage_service.track_message(user_id)
    
    # Step 5: Attempt to exceed limit - should be blocked
    response = await async_client.post(
        "/api/v1/chat/message",
        json={
            "content": "Message beyond limit",
            "thread_id": str(uuid.uuid4())
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    data = response.json()
    assert "daily limit" in data["detail"].lower()
    assert "upgrade" in data["detail"].lower()
    
    # Step 6: Verify advanced tools are blocked for free tier
    response = await async_client.post(
        "/api/v1/tools/enterprise-analytics",
        json={"data": "test"},
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "upgrade required" in response.json()["detail"].lower()
    
    # Step 7: Test usage reset on new billing cycle
    # Simulate next day
    await redis_client.delete(f"usage:{user_id}:daily")
    
    response = await async_client.get(
        "/api/v1/usage/current",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["messages_used_today"] == 0


# ============================================================================
# TEST 4: WEBSOCKET CONNECTION LIFECYCLE
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_websocket_connection_lifecycle(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    websocket_manager: WebSocketManager,
    redis_client: Redis
):
    """
    Test WebSocket connection lifecycle through network issues.
    
    BVJ: Protects $20K MRR by ensuring real-time chat reliability.
    """
    access_token = authenticated_user["access_token"]
    user_id = authenticated_user["user_id"]
    
    # Step 1: Establish initial connection
    async with async_client.websocket_connect(
        f"/ws?token={access_token}"
    ) as websocket:
        # Step 2: Verify heartbeat mechanism
        await websocket.send_json({"type": "ping"})
        pong = await websocket.receive_json()
        assert pong["type"] == "pong"
        assert "timestamp" in pong
        
        # Step 3: Send message and track connection ID
        await websocket.send_json({
            "type": "user_message",
            "content": "Test message",
            "thread_id": str(uuid.uuid4())
        })
        
        ack = await websocket.receive_json()
        assert ack["type"] == "message_acknowledged"
        connection_id = ack.get("connection_id")
        
        # Step 4: Verify connection tracked in Redis
        connection_key = f"ws:connection:{user_id}"
        stored_connection = await redis_client.get(connection_key)
        assert stored_connection is not None
    
    # Connection closed - simulate network drop
    
    # Step 5: Attempt reconnection with same token
    async with async_client.websocket_connect(
        f"/ws?token={access_token}"
    ) as websocket:
        # Step 6: Send reconnection signal
        await websocket.send_json({
            "type": "reconnect",
            "previous_connection_id": connection_id
        })
        
        # Step 7: Receive state recovery
        recovery = await websocket.receive_json()
        assert recovery["type"] == "state_recovered"
        assert "missed_messages" in recovery
        
        # Step 8: Test message queuing during disconnection
        # This would be tested with actual network simulation
        
        # Step 9: Verify graceful degradation under load
        tasks = []
        for i in range(10):  # Simulate 10 concurrent messages
            task = websocket.send_json({
                "type": "user_message",
                "content": f"Concurrent message {i}",
                "thread_id": str(uuid.uuid4())
            })
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Receive acknowledgments
        acks_received = 0
        start_time = time.time()
        while acks_received < 10 and time.time() - start_time < 10:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                if msg["type"] == "message_acknowledged":
                    acks_received += 1
            except asyncio.TimeoutError:
                continue
        
        assert acks_received == 10, f"Only received {acks_received}/10 acknowledgments"


# ============================================================================
# TEST 5: API KEY GENERATION AND MANAGEMENT
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_api_key_generation_and_management(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession,
    redis_client: Redis
):
    """
    Test API key generation and management for programmatic access.
    
    BVJ: Protects $35K MRR by enabling programmatic access for paying customers.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Step 1: Generate development API key
    response = await async_client.post(
        "/api/v1/api-keys/generate",
        json={
            "name": "Development Key",
            "type": "development",
            "permissions": ["read", "write"],
            "expiry_days": 90
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    key_data = response.json()
    assert "key" in key_data
    assert key_data["key"].startswith("nk_dev_")  # Netra key prefix
    assert "key_id" in key_data
    api_key = key_data["key"]
    key_id = key_data["key_id"]
    
    # Step 2: Test API key authentication
    response = await async_client.get(
        "/api/v1/user/profile",
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_id"] == user_id
    
    # Step 3: Test rate limiting for API key
    requests = []
    for i in range(105):  # Free tier limit is 100/hour
        requests.append(async_client.get(
            "/api/v1/usage/current",
            headers={"X-API-Key": api_key}
        ))
    
    responses = await asyncio.gather(*requests[:105], return_exceptions=True)
    
    # Should have some rate limited responses
    rate_limited = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 429)
    assert rate_limited > 0, "Rate limiting not working for API keys"
    
    # Step 4: List API keys
    response = await async_client.get(
        "/api/v1/api-keys",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    keys = response.json()
    assert len(keys) >= 1
    assert any(k["key_id"] == key_id for k in keys)
    
    # Step 5: Rotate API key
    response = await async_client.post(
        f"/api/v1/api-keys/{key_id}/rotate",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    new_key_data = response.json()
    assert new_key_data["key"] != api_key
    new_api_key = new_key_data["key"]
    
    # Step 6: Verify old key is invalidated
    response = await async_client.get(
        "/api/v1/user/profile",
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Step 7: Verify new key works
    response = await async_client.get(
        "/api/v1/user/profile",
        headers={"X-API-Key": new_api_key}
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Step 8: Delete API key
    response = await async_client.delete(
        f"/api/v1/api-keys/{key_id}",
        headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Step 9: Verify deleted key doesn't work
    response = await async_client.get(
        "/api/v1/user/profile",
        headers={"X-API-Key": new_api_key}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# TEST 6: USER PROFILE SETUP AND PREFERENCES
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_user_profile_setup_and_preferences(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession,
    redis_client: Redis
):
    """
    Test user profile setup and preference management.
    
    BVJ: Protects $15K MRR by enabling personalized user experience.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Step 1: Get initial profile
    response = await async_client.get(
        "/api/v1/user/profile",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    initial_profile = response.json()
    
    # Step 2: Update profile information
    profile_update = {
        "full_name": "John Doe",
        "company": "Acme Corp",
        "role": "AI Engineer",
        "timezone": "America/Los_Angeles",
        "phone": "+1-555-0123"
    }
    
    response = await async_client.patch(
        "/api/v1/user/profile",
        json=profile_update,
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    updated_profile = response.json()
    assert updated_profile["full_name"] == profile_update["full_name"]
    assert updated_profile["company"] == profile_update["company"]
    
    # Step 3: Set user preferences
    preferences = {
        "theme": "dark",
        "notifications": {
            "email": True,
            "in_app": True,
            "push": False
        },
        "language": "en",
        "ai_preferences": {
            "response_style": "concise",
            "technical_level": "expert",
            "preferred_models": ["gpt-4", "claude-3-sonnet"]
        }
    }
    
    response = await async_client.put(
        "/api/v1/user/preferences",
        json=preferences,
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Step 4: Verify preferences persisted
    response = await async_client.get(
        "/api/v1/user/preferences",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    saved_prefs = response.json()
    assert saved_prefs["theme"] == "dark"
    assert saved_prefs["ai_preferences"]["response_style"] == "concise"
    
    # Step 5: Test preference application in chat
    async with async_client.websocket_connect(
        f"/ws?token={access_token}"
    ) as websocket:
        await websocket.send_json({
            "type": "user_message",
            "content": "Explain quantum computing",
            "thread_id": str(uuid.uuid4())
        })
        
        # Wait for response
        response_found = False
        start_time = time.time()
        while time.time() - start_time < 10:
            msg = await websocket.receive_json()
            if msg["type"] == "agent_response":
                response_found = True
                # Should be concise per preference
                assert len(msg["content"]) < 500  # Concise response
                break
        
        assert response_found
    
    # Step 6: Test notification preferences
    response = await async_client.post(
        "/api/v1/test/trigger-notification",
        json={"type": "usage_warning"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    notifications = response.json()
    assert notifications["email_sent"] is True  # Per preference
    assert notifications["push_sent"] is False  # Per preference
    
    # Step 7: Test privacy settings
    response = await async_client.put(
        "/api/v1/user/privacy",
        json={
            "data_retention_days": 90,
            "allow_analytics": False,
            "share_usage_data": False
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Step 8: Verify privacy settings enforced
    response = await async_client.get(
        "/api/v1/analytics/user-data",
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "analytics disabled" in response.json()["detail"].lower()


# ============================================================================
# TEST 7: PROVIDER CONNECTION FLOW (OAuth/API)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_provider_connection_flow(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession
):
    """
    Test OAuth and API key provider connection flows.
    
    BVJ: Protects $50K MRR by enabling AI provider integrations.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Step 1: Add OpenAI API key
    response = await async_client.post(
        "/api/v1/providers/openai/connect",
        json={
            "api_key": "sk-test-1234567890abcdef",
            "organization_id": "org-test123"
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["provider"] == "openai"
    assert response.json()["status"] == "connected"
    
    # Step 2: Test provider connection
    response = await async_client.post(
        "/api/v1/providers/openai/test",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    test_result = response.json()
    assert test_result["connection_valid"] is True
    assert "models_available" in test_result
    
    # Step 3: Add Anthropic API key
    response = await async_client.post(
        "/api/v1/providers/anthropic/connect",
        json={
            "api_key": "sk-ant-test-key-123"
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Step 4: List connected providers
    response = await async_client.get(
        "/api/v1/providers",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    providers = response.json()
    assert len(providers) >= 2
    assert any(p["name"] == "openai" for p in providers)
    assert any(p["name"] == "anthropic" for p in providers)
    
    # Step 5: Initiate Google OAuth flow
    response = await async_client.get(
        "/api/v1/providers/google/oauth/authorize",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    oauth_data = response.json()
    assert "authorization_url" in oauth_data
    assert "state" in oauth_data
    assert "google.com/o/oauth2" in oauth_data["authorization_url"]
    
    # Step 6: Simulate OAuth callback (would be real in production)
    with patch("app.services.oauth_service.exchange_code_for_token") as mock_exchange:
        mock_exchange.return_value = {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_in": 3600
        }
        
        response = await async_client.get(
            "/api/v1/providers/google/oauth/callback",
            params={
                "code": "test-auth-code",
                "state": oauth_data["state"]
            },
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["provider"] == "google"
        assert response.json()["status"] == "connected"
    
    # Step 7: Update provider settings
    response = await async_client.patch(
        "/api/v1/providers/openai/settings",
        json={
            "default_model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Step 8: Rotate API key
    response = await async_client.post(
        "/api/v1/providers/openai/rotate-key",
        json={
            "new_api_key": "sk-test-new-key-9876543210"
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "API key rotated successfully"
    
    # Step 9: Disconnect provider
    response = await async_client.delete(
        "/api/v1/providers/anthropic/disconnect",
        headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Step 10: Verify provider disconnected
    response = await async_client.get(
        "/api/v1/providers",
        headers=headers
    )
    providers = response.json()
    anthropic_providers = [p for p in providers if p["name"] == "anthropic"]
    assert len(anthropic_providers) == 0 or anthropic_providers[0]["status"] == "disconnected"


# ============================================================================
# TEST 8: FIRST OPTIMIZATION REQUEST
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_first_optimization_request(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    agent_dispatcher: AgentDispatcher,
    async_session: AsyncSession
):
    """
    Test end-to-end optimization workflow for new users.
    
    BVJ: Protects $60K MRR by demonstrating core platform value.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 1: Submit optimization request
    optimization_request = {
        "type": "cost_optimization",
        "context": {
            "current_monthly_cost": 5000,
            "target_reduction_percentage": 20,
            "quality_threshold": 0.95,
            "models_in_use": ["gpt-4", "claude-3-sonnet"],
            "daily_requests": 10000,
            "average_tokens_per_request": 500
        },
        "urgency": "normal",
        "detailed_analysis": True
    }
    
    response = await async_client.post(
        "/api/v1/optimizations/analyze",
        json=optimization_request,
        headers=headers
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    job_data = response.json()
    assert "job_id" in job_data
    assert "estimated_completion_time" in job_data
    job_id = job_data["job_id"]
    
    # Step 2: Poll for completion
    max_polls = 30
    poll_count = 0
    analysis_complete = False
    
    while poll_count < max_polls:
        response = await async_client.get(
            f"/api/v1/optimizations/status/{job_id}",
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        status = response.json()
        
        if status["status"] == "completed":
            analysis_complete = True
            break
        elif status["status"] == "failed":
            pytest.fail(f"Optimization analysis failed: {status.get('error')}")
        
        await asyncio.sleep(2)
        poll_count += 1
    
    assert analysis_complete, "Optimization analysis did not complete in time"
    
    # Step 3: Get optimization results
    response = await async_client.get(
        f"/api/v1/optimizations/results/{job_id}",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    results = response.json()
    
    # Step 4: Validate optimization recommendations
    assert "recommendations" in results
    assert len(results["recommendations"]) > 0
    
    for rec in results["recommendations"]:
        assert "action" in rec
        assert "expected_savings" in rec
        assert "quality_impact" in rec
        assert "confidence_score" in rec
        assert rec["confidence_score"] >= 0.6
    
    # Step 5: Verify cost analysis
    assert "cost_analysis" in results
    cost_analysis = results["cost_analysis"]
    assert "current_cost" in cost_analysis
    assert "projected_cost" in cost_analysis
    assert "savings_amount" in cost_analysis
    assert cost_analysis["savings_amount"] > 0
    
    # Step 6: Verify quality impact assessment
    assert "quality_assessment" in results
    quality = results["quality_assessment"]
    assert "current_quality_score" in quality
    assert "projected_quality_score" in quality
    assert quality["projected_quality_score"] >= 0.95  # Meets threshold
    
    # Step 7: Test follow-up questions
    assert "follow_up_questions" in results
    assert len(results["follow_up_questions"]) > 0
    
    # Step 8: Submit follow-up
    follow_up_response = await async_client.post(
        f"/api/v1/optimizations/{job_id}/follow-up",
        json={
            "question": results["follow_up_questions"][0],
            "additional_context": {"peak_hours": "9am-5pm PST"}
        },
        headers=headers
    )
    assert follow_up_response.status_code == status.HTTP_200_OK
    
    # Step 9: Verify optimization saved to user history
    response = await async_client.get(
        "/api/v1/optimizations/history",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    history = response.json()
    assert len(history) >= 1
    assert any(h["job_id"] == job_id for h in history)


# ============================================================================
# TEST 9: USAGE TRACKING AND METERING
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_usage_tracking_and_metering(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    usage_service: UsageService,
    redis_client: Redis
):
    """
    Test accurate usage tracking for billing and analytics.
    
    BVJ: Protects $45K MRR by enabling accurate billing and usage analytics.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Step 1: Get baseline usage
    response = await async_client.get(
        "/api/v1/usage/detailed",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    baseline_usage = response.json()
    
    # Step 2: Perform tracked actions
    actions = [
        # Send chat messages
        async_client.post(
            "/api/v1/chat/message",
            json={"content": "Test message 1", "thread_id": str(uuid.uuid4())},
            headers=headers
        ),
        # Call API
        async_client.get("/api/v1/user/profile", headers=headers),
        # Execute tool
        async_client.post(
            "/api/v1/tools/cost-analyzer/execute",
            json={"data": {"cost": 1000}},
            headers=headers
        ),
    ]
    
    await asyncio.gather(*actions)
    
    # Step 3: Verify usage incremented
    response = await async_client.get(
        "/api/v1/usage/detailed",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    current_usage = response.json()
    
    assert current_usage["messages_sent"] > baseline_usage["messages_sent"]
    assert current_usage["api_calls"] > baseline_usage["api_calls"]
    assert current_usage["tools_executed"] > baseline_usage["tools_executed"]
    
    # Step 4: Test token consumption tracking
    response = await async_client.post(
        "/api/v1/chat/message",
        json={
            "content": "Calculate the ROI of switching from GPT-4 to Claude-3",
            "thread_id": str(uuid.uuid4())
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    message_data = response.json()
    assert "tokens_used" in message_data
    assert message_data["tokens_used"] > 0
    
    # Step 5: Get usage by time period
    response = await async_client.get(
        "/api/v1/usage/history",
        params={
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "granularity": "hourly"
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    usage_history = response.json()
    assert "data_points" in usage_history
    assert len(usage_history["data_points"]) > 0
    
    # Step 6: Test usage aggregations
    response = await async_client.get(
        "/api/v1/usage/analytics",
        params={"metric": "cost_by_model"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    analytics = response.json()
    assert "breakdown" in analytics
    
    # Step 7: Verify billing metrics
    response = await async_client.get(
        "/api/v1/billing/current-period",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    billing = response.json()
    assert "total_cost" in billing
    assert "breakdown" in billing
    assert billing["total_cost"] >= 0
    
    # Step 8: Test usage export
    response = await async_client.post(
        "/api/v1/usage/export",
        json={
            "format": "csv",
            "period": "current_month"
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    export_data = response.json()
    assert "download_url" in export_data or "data" in export_data


# ============================================================================
# TEST 10: TRIAL TO PAID CONVERSION FLOW
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_trial_to_paid_conversion_flow(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession
):
    """
    Test smooth upgrade from trial/free to paid plan.
    
    BVJ: Protects $100K MRR by ensuring smooth upgrade process.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Step 1: Check current plan status
    response = await async_client.get(
        "/api/v1/billing/subscription",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    current_plan = response.json()
    assert current_plan["plan"] == "free"
    assert current_plan["trial_days_remaining"] >= 0
    
    # Step 2: Get available plans
    response = await async_client.get(
        "/api/v1/billing/plans"
    )
    assert response.status_code == status.HTTP_200_OK
    plans = response.json()
    pro_plan = next(p for p in plans if p["name"] == "pro")
    assert pro_plan["price"] > 0
    
    # Step 3: Initiate upgrade to Pro
    with patch("app.services.payment_service.process_payment") as mock_payment:
        mock_payment.return_value = {
            "success": True,
            "transaction_id": "txn_test_123",
            "amount": pro_plan["price"]
        }
        
        response = await async_client.post(
            "/api/v1/billing/upgrade",
            json={
                "plan_id": pro_plan["id"],
                "payment_method": "card",
                "payment_token": "tok_test_visa_4242"
            },
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        upgrade_result = response.json()
        assert upgrade_result["success"] is True
        assert upgrade_result["new_plan"] == "pro"
    
    # Step 4: Verify plan activated immediately
    response = await async_client.get(
        "/api/v1/billing/subscription",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    new_plan = response.json()
    assert new_plan["plan"] == "pro"
    assert new_plan["status"] == "active"
    
    # Step 5: Verify increased limits
    response = await async_client.get(
        "/api/v1/usage/limits",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    limits = response.json()
    assert limits["daily_messages"] > 50  # More than free tier
    assert limits["concurrent_sessions"] > 2
    
    # Step 6: Test access to pro features
    response = await async_client.post(
        "/api/v1/tools/advanced-analytics/execute",
        json={"query": "test"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK  # Now accessible
    
    # Step 7: Verify billing cycle started
    response = await async_client.get(
        "/api/v1/billing/next-invoice",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    next_invoice = response.json()
    assert next_invoice["amount"] == pro_plan["price"]
    assert "due_date" in next_invoice
    
    # Step 8: Test downgrade prevention during billing period
    response = await async_client.post(
        "/api/v1/billing/change-plan",
        json={"plan_id": "free"},
        headers=headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "end of billing period" in response.json()["detail"].lower()


# ============================================================================
# TEST 11: ERROR RECOVERY AND SUPPORT
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_error_recovery_and_support(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """
    Test error handling and support access during issues.
    
    BVJ: Protects $30K MRR by preventing user churn during issues.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 1: Trigger validation error
    response = await async_client.post(
        "/api/v1/chat/message",
        json={
            "content": "",  # Empty message
            "thread_id": "invalid-uuid"  # Invalid UUID
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "detail" in error
    assert any("content" in str(e).lower() for e in error["detail"])
    
    # Step 2: Trigger rate limit error
    with patch("app.services.rate_limiter.check_rate_limit") as mock_limit:
        mock_limit.return_value = False
        
        response = await async_client.post(
            "/api/v1/chat/message",
            json={"content": "Test", "thread_id": str(uuid.uuid4())},
            headers=headers
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        error = response.json()
        assert "retry_after" in error
        assert "upgrade" in error["detail"].lower()
    
    # Step 3: Simulate LLM service error
    with patch("app.services.llm_manager.generate_response") as mock_llm:
        mock_llm.side_effect = Exception("LLM service unavailable")
        
        response = await async_client.post(
            "/api/v1/chat/message",
            json={"content": "Test message", "thread_id": str(uuid.uuid4())},
            headers=headers
        )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        error = response.json()
        assert "temporarily unavailable" in error["detail"].lower()
        assert "support_options" in error
    
    # Step 4: Access support options
    response = await async_client.get(
        "/api/v1/support/options",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    support = response.json()
    assert "contact_methods" in support
    assert "knowledge_base_url" in support
    assert "status_page_url" in support
    
    # Step 5: Create support ticket
    response = await async_client.post(
        "/api/v1/support/ticket",
        json={
            "subject": "Error during optimization",
            "description": "Getting 503 errors when running optimization",
            "priority": "high",
            "category": "technical"
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    ticket = response.json()
    assert "ticket_id" in ticket
    assert "estimated_response_time" in ticket
    
    # Step 6: Test error recovery with retry
    retry_count = 0
    max_retries = 3
    success = False
    
    while retry_count < max_retries:
        with patch("app.services.llm_manager.generate_response") as mock_llm:
            if retry_count < 2:
                mock_llm.side_effect = Exception("Temporary failure")
            else:
                mock_llm.return_value = {"content": "Success after retry"}
            
            response = await async_client.post(
                "/api/v1/chat/message",
                json={"content": "Test retry", "thread_id": str(uuid.uuid4())},
                headers={**headers, "X-Retry-Count": str(retry_count)}
            )
            
            if response.status_code == status.HTTP_200_OK:
                success = True
                break
            
            retry_count += 1
            await asyncio.sleep(1)
    
    assert success, "Retry mechanism did not recover from error"
    
    # Step 7: Access error logs for debugging
    response = await async_client.get(
        "/api/v1/debug/recent-errors",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    errors = response.json()
    assert "errors" in errors
    assert len(errors["errors"]) > 0


# ============================================================================
# TEST 12: MULTI-AGENT COORDINATION
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_multi_agent_coordination(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    agent_dispatcher: AgentDispatcher
):
    """
    Test multi-agent orchestration for complex requests.
    
    BVJ: Protects $40K MRR by ensuring AI system works effectively.
    """
    access_token = authenticated_user["access_token"]
    
    # Step 1: Submit complex request requiring multiple agents
    complex_request = {
        "content": """
        I need a comprehensive analysis:
        1. Analyze my current AI costs and identify savings opportunities
        2. Evaluate performance metrics and suggest optimizations
        3. Recommend model switching strategies
        4. Create an implementation roadmap
        """,
        "thread_id": str(uuid.uuid4()),
        "context": {
            "monthly_spend": 10000,
            "models": ["gpt-4", "claude-3"],
            "daily_requests": 50000
        }
    }
    
    async with async_client.websocket_connect(
        f"/ws?token={access_token}"
    ) as websocket:
        # Step 2: Send complex request
        await websocket.send_json({
            "type": "user_message",
            **complex_request
        })
        
        # Step 3: Track agent coordination
        agents_involved = set()
        agent_messages = []
        coordination_complete = False
        start_time = time.time()
        
        while time.time() - start_time < 45:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                
                if msg["type"] == "agent_selection":
                    agents_involved.update(msg["agents"])
                elif msg["type"] == "agent_status":
                    agent_messages.append(msg)
                elif msg["type"] == "agent_response":
                    coordination_complete = True
                    final_response = msg
                    break
            except asyncio.TimeoutError:
                continue
        
        assert coordination_complete, "Agent coordination did not complete"
        
        # Step 4: Verify multiple agents were involved
        assert len(agents_involved) >= 3  # Supervisor + at least 2 sub-agents
        assert "supervisor" in agents_involved
        
        # Step 5: Verify comprehensive response
        response_content = final_response["content"].lower()
        assert "cost" in response_content
        assert "performance" in response_content
        assert "model" in response_content
        assert "roadmap" in response_content or "implementation" in response_content
        
        # Step 6: Test agent state consistency
        await websocket.send_json({
            "type": "follow_up",
            "content": "Can you elaborate on the cost savings?",
            "thread_id": complex_request["thread_id"]
        })
        
        follow_up_received = False
        start_time = time.time()
        
        while time.time() - start_time < 20:
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                if msg["type"] == "agent_response":
                    follow_up_received = True
                    # Should maintain context from previous analysis
                    assert "savings" in msg["content"].lower()
                    break
            except asyncio.TimeoutError:
                continue
        
        assert follow_up_received, "Follow-up response not received"


# ============================================================================
# TEST 13: DATA EXPORT AND ANALYTICS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_data_export_and_analytics(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """
    Test data export and analytics for free tier users.
    
    BVJ: Protects $25K MRR by demonstrating analytics value.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 1: Generate some usage data
    for i in range(5):
        await async_client.post(
            "/api/v1/chat/message",
            json={
                "content": f"Test message {i}",
                "thread_id": str(uuid.uuid4())
            },
            headers=headers
        )
    
    # Step 2: Get basic analytics
    response = await async_client.get(
        "/api/v1/analytics/summary",
        params={"period": "last_7_days"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    analytics = response.json()
    assert "total_messages" in analytics
    assert "total_tokens" in analytics
    assert "average_response_time" in analytics
    assert analytics["total_messages"] >= 5
    
    # Step 3: Get cost trends
    response = await async_client.get(
        "/api/v1/analytics/cost-trends",
        params={"granularity": "daily"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    trends = response.json()
    assert "data_points" in trends
    assert len(trends["data_points"]) > 0
    
    # Step 4: Export data as CSV (free tier limit)
    response = await async_client.post(
        "/api/v1/export/usage",
        json={
            "format": "csv",
            "date_range": "last_30_days",
            "include_fields": ["timestamp", "message", "tokens", "cost"]
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    export = response.json()
    
    if "data" in export:  # Inline data for small exports
        assert len(export["data"]) > 0
        assert "timestamp" in export["data"][0]
    else:  # Download URL for larger exports
        assert "download_url" in export
        assert "expires_at" in export
    
    # Step 5: Try to access advanced analytics (should be restricted)
    response = await async_client.get(
        "/api/v1/analytics/advanced/ml-insights",
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "upgrade" in response.json()["detail"].lower()
    
    # Step 6: Export conversation history
    response = await async_client.post(
        "/api/v1/export/conversations",
        json={
            "format": "json",
            "include_agent_analysis": False  # Free tier restriction
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    conversations = response.json()
    assert "threads" in conversations
    assert len(conversations["threads"]) > 0
    
    # Step 7: Get performance summary
    response = await async_client.get(
        "/api/v1/analytics/performance",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    performance = response.json()
    assert "average_latency" in performance
    assert "success_rate" in performance
    assert performance["success_rate"] > 0


# ============================================================================
# TEST 14: SESSION PERSISTENCE
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_session_persistence(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    redis_client: Redis
):
    """
    Test session persistence across browser refresh.
    
    BVJ: Protects $20K MRR by maintaining user context.
    """
    access_token = authenticated_user["access_token"]
    refresh_token = authenticated_user["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Step 1: Create active session with state
    thread_id = str(uuid.uuid4())
    
    # Send messages to create history
    messages = [
        "What's the best way to reduce AI costs?",
        "Can you analyze my current usage?",
        "Show me optimization opportunities"
    ]
    
    for msg in messages:
        response = await async_client.post(
            "/api/v1/chat/message",
            json={"content": msg, "thread_id": thread_id},
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
    
    # Set UI preferences
    ui_state = {
        "theme": "dark",
        "sidebar_collapsed": False,
        "active_thread": thread_id,
        "draft_message": "What about switching to GPT-3.5?"
    }
    
    response = await async_client.put(
        "/api/v1/session/ui-state",
        json=ui_state,
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Step 2: Store session data
    session_key = f"session:{user_id}"
    session_data = await redis_client.get(session_key)
    assert session_data is not None
    
    # Step 3: Simulate browser refresh - get new access token
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == status.HTTP_200_OK
    new_access_token = response.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_access_token}"}
    
    # Step 4: Restore session state
    response = await async_client.get(
        "/api/v1/session/restore",
        headers=new_headers
    )
    assert response.status_code == status.HTTP_200_OK
    restored_session = response.json()
    
    # Step 5: Verify chat history restored
    assert "threads" in restored_session
    assert thread_id in [t["id"] for t in restored_session["threads"]]
    
    response = await async_client.get(
        f"/api/v1/threads/{thread_id}/messages",
        headers=new_headers
    )
    assert response.status_code == status.HTTP_200_OK
    restored_messages = response.json()
    assert len(restored_messages) >= len(messages)
    
    # Step 6: Verify UI state restored
    response = await async_client.get(
        "/api/v1/session/ui-state",
        headers=new_headers
    )
    assert response.status_code == status.HTTP_200_OK
    restored_ui = response.json()
    assert restored_ui["theme"] == "dark"
    assert restored_ui["active_thread"] == thread_id
    assert restored_ui["draft_message"] == ui_state["draft_message"]
    
    # Step 7: Test WebSocket reconnection with session
    async with async_client.websocket_connect(
        f"/ws?token={new_access_token}"
    ) as websocket:
        await websocket.send_json({
            "type": "restore_session",
            "thread_id": thread_id
        })
        
        restoration = await websocket.receive_json()
        assert restoration["type"] == "session_restored"
        assert restoration["thread_id"] == thread_id
        assert "message_history" in restoration
    
    # Step 8: Verify draft message preserved
    response = await async_client.get(
        f"/api/v1/threads/{thread_id}/draft",
        headers=new_headers
    )
    assert response.status_code == status.HTTP_200_OK
    draft = response.json()
    assert draft["content"] == ui_state["draft_message"]


# ============================================================================
# TEST 15: OAUTH INTEGRATION FLOW
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_oauth_integration_flow(
    async_client: httpx.AsyncClient,
    async_session: AsyncSession
):
    """
    Test OAuth integration with Google/GitHub for social sign-in.
    
    BVJ: Protects $35K MRR by enabling frictionless social sign-in.
    """
    # Step 1: Initiate Google OAuth flow
    response = await async_client.get(
        "/api/v1/auth/oauth/google/authorize"
    )
    assert response.status_code == status.HTTP_200_OK
    google_auth = response.json()
    assert "authorization_url" in google_auth
    assert "state" in google_auth
    assert "accounts.google.com" in google_auth["authorization_url"]
    google_state = google_auth["state"]
    
    # Step 2: Simulate Google OAuth callback
    with patch("app.services.oauth_service.GoogleOAuth.get_user_info") as mock_google:
        mock_google.return_value = {
            "id": "google_123456",
            "email": "testuser@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "verified_email": True
        }
        
        response = await async_client.get(
            "/api/v1/auth/oauth/google/callback",
            params={
                "code": "google_auth_code_test",
                "state": google_state
            }
        )
        assert response.status_code == status.HTTP_200_OK
        auth_result = response.json()
        assert "access_token" in auth_result
        assert "refresh_token" in auth_result
        assert "user" in auth_result
        assert auth_result["user"]["email"] == "testuser@gmail.com"
        google_user_id = auth_result["user"]["id"]
    
    # Step 3: Verify user created/linked
    user = await async_session.query(User).filter(
        User.email == "testuser@gmail.com"
    ).first()
    assert user is not None
    assert user.oauth_provider == "google"
    assert user.oauth_provider_id == "google_123456"
    
    # Step 4: Test GitHub OAuth flow
    response = await async_client.get(
        "/api/v1/auth/oauth/github/authorize"
    )
    assert response.status_code == status.HTTP_200_OK
    github_auth = response.json()
    assert "authorization_url" in github_auth
    assert "github.com/login/oauth" in github_auth["authorization_url"]
    github_state = github_auth["state"]
    
    # Step 5: Simulate GitHub OAuth callback
    with patch("app.services.oauth_service.GitHubOAuth.get_user_info") as mock_github:
        mock_github.return_value = {
            "id": 789012,
            "login": "testuser",
            "email": "testuser@github.com",
            "name": "Test GitHub User",
            "avatar_url": "https://avatars.githubusercontent.com/u/789012"
        }
        
        response = await async_client.get(
            "/api/v1/auth/oauth/github/callback",
            params={
                "code": "github_auth_code_test",
                "state": github_state
            }
        )
        assert response.status_code == status.HTTP_200_OK
        github_result = response.json()
        assert "access_token" in github_result
    
    # Step 6: Test account linking (existing email)
    with patch("app.services.oauth_service.GoogleOAuth.get_user_info") as mock_google:
        mock_google.return_value = {
            "id": "google_different_id",
            "email": "testuser@github.com",  # Same email as GitHub user
            "name": "Test User",
            "verified_email": True
        }
        
        response = await async_client.get(
            "/api/v1/auth/oauth/google/callback",
            params={
                "code": "google_auth_code_test2",
                "state": google_state
            }
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Should link to existing account
        linked_user = await async_session.query(User).filter(
            User.email == "testuser@github.com"
        ).first()
        assert linked_user is not None
        # Should update OAuth provider info
        assert linked_user.oauth_provider == "google"  # Latest provider
    
    # Step 7: Test OAuth token refresh
    response = await async_client.post(
        "/api/v1/auth/oauth/refresh",
        json={
            "provider": "google",
            "refresh_token": "google_refresh_token_test"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    refreshed = response.json()
    assert "access_token" in refreshed
    
    # Step 8: Test OAuth disconnect
    headers = {"Authorization": f"Bearer {auth_result['access_token']}"}
    response = await async_client.post(
        "/api/v1/auth/oauth/disconnect",
        json={"provider": "google"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Verify OAuth info cleared
    user = await async_session.get(User, google_user_id)
    assert user.oauth_provider is None
    assert user.oauth_provider_id is None


# ============================================================================
# TEST UTILITIES
# ============================================================================

async def create_verified_user(
    async_client: httpx.AsyncClient,
    user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Helper to create and verify a user."""
    # Register
    response = await async_client.post(
        "/api/v1/auth/register",
        json=user_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    reg_data = response.json()
    
    # Verify email
    response = await async_client.post(
        f"/api/v1/auth/verify-email/{reg_data['verification_token']}"
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Login
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": user_data["email"],
            "password": user_data["password"]
        }
    )
    assert response.status_code == status.HTTP_200_OK
    
    return response.json()


async def simulate_user_activity(
    async_client: httpx.AsyncClient,
    access_token: str,
    num_messages: int = 5
) -> List[str]:
    """Helper to simulate user chat activity."""
    headers = {"Authorization": f"Bearer {access_token}"}
    thread_ids = []
    
    for i in range(num_messages):
        response = await async_client.post(
            "/api/v1/chat/message",
            json={
                "content": f"Test message {i}",
                "thread_id": str(uuid.uuid4())
            },
            headers=headers
        )
        if response.status_code == status.HTTP_200_OK:
            thread_ids.append(response.json().get("thread_id"))
    
    return thread_ids


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])