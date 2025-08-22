"""
First-time user workspace and profile management integration tests.

BVJ (Business Value Justification):
1. Segment: Early → Mid (User engagement and personalization)
2. Business Goal: Protect $35K MRR by enabling API access and personalization
3. Value Impact: Validates profile setup and programmatic access capabilities
4. Strategic Impact: Foundation for premium feature adoption
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import uuid
from typing import Any, Dict

import httpx
import pytest
from fastapi import status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
from netra_backend.tests.integration.first_time_user_fixtures import (
    # Add project root to path
    assert_api_key_properties,
    assert_export_response,
    get_mock_user_preferences,
    verify_rate_limiting,
)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_user_profile_setup_and_update(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession
):
    """Test user profile information management."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Get initial profile
    response = await async_client.get("/api/v1/user/profile", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    initial_profile = response.json()
    
    # Update profile information
    profile_update = {
        "full_name": "John Doe",
        "company": "Acme Corp",
        "role": "AI Engineer",
        "timezone": "America/Los_Angeles",
        "phone": "+1-555-0123"
    }
    
    response = await async_client.patch("/api/v1/user/profile", json=profile_update, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    updated_profile = response.json()
    assert updated_profile["full_name"] == profile_update["full_name"]
    assert updated_profile["company"] == profile_update["company"]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_user_preferences_management(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test user preference storage and application."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Set comprehensive preferences
    preferences = get_mock_user_preferences()
    response = await async_client.put("/api/v1/user/preferences", json=preferences, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    # Verify preferences persisted
    response = await async_client.get("/api/v1/user/preferences", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    saved_prefs = response.json()
    assert saved_prefs["theme"] == "dark"
    assert saved_prefs["ai_preferences"]["response_style"] == "concise"
    
    # Test preference application in chat
    async with async_client.websocket_connect(f"/ws?token={access_token}") as websocket:
        await websocket.send_json({
            "type": "user_message",
            "content": "Explain quantum computing",
            "thread_id": str(uuid.uuid4())
        })
        
        # Wait for concise response per preference
        response_found = False
        start_time = time.time()
        while time.time() - start_time < 10:
            msg = await websocket.receive_json()
            if msg["type"] == "agent_response":
                response_found = True
                assert len(msg["content"]) < 500  # Concise per preference
                break
        assert response_found


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_privacy_settings_enforcement(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test privacy settings are properly enforced."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Set strict privacy settings
    privacy_settings = {
        "data_retention_days": 90,
        "allow_analytics": False,
        "share_usage_data": False
    }
    response = await async_client.put("/api/v1/user/privacy", json=privacy_settings, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    # Test analytics access blocked
    response = await async_client.get("/api/v1/analytics/user-data", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "analytics disabled" in response.json()["detail"].lower()
    
    # Test notification preferences respected
    response = await async_client.post(
        "/api/v1/test/trigger-notification",
        json={"type": "usage_warning"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_api_key_generation_and_usage(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession
):
    """Test API key creation and authentication."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Generate development API key
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
    assert_api_key_properties(key_data)
    api_key = key_data["key"]
    key_id = key_data["key_id"]
    
    # Test API key authentication
    response = await async_client.get("/api/v1/user/profile", headers={"X-API-Key": api_key})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_id"] == user_id


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_api_key_rate_limiting(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test API key rate limiting enforcement."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Generate API key
    response = await async_client.post(
        "/api/v1/api-keys/generate",
        json={"name": "Rate Test Key", "type": "development"},
        headers=headers
    )
    api_key = response.json()["key"]
    
    # Test rate limiting (free tier: 100/hour)
    rate_limited = await verify_rate_limiting(
        async_client, "/api/v1/usage/current", {"X-API-Key": api_key}, limit=100
    )
    assert rate_limited > 0


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_api_key_management_operations(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test API key rotation and deletion."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create API key
    response = await async_client.post(
        "/api/v1/api-keys/generate",
        json={"name": "Test Key", "type": "development"},
        headers=headers
    )
    key_data = response.json()
    api_key = key_data["key"]
    key_id = key_data["key_id"]
    
    # List API keys
    response = await async_client.get("/api/v1/api-keys", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    keys = response.json()
    assert any(k["key_id"] == key_id for k in keys)
    
    # Rotate API key
    response = await async_client.post(f"/api/v1/api-keys/{key_id}/rotate", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    new_api_key = response.json()["key"]
    assert new_api_key != api_key
    
    # Verify old key invalidated
    response = await async_client.get("/api/v1/user/profile", headers={"X-API-Key": api_key})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Delete API key
    response = await async_client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_data_export_capabilities(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test user data export functionality."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Generate some activity data
    for i in range(5):
        await async_client.post(
            "/api/v1/chat/message",
            json={"content": f"Export test message {i}", "thread_id": str(uuid.uuid4())},
            headers=headers
        )
    
    # Export usage data
    response = await async_client.post(
        "/api/v1/export/usage",
        json={
            "format": "csv",
            "date_range": "last_30_days",
            "include_fields": ["timestamp", "message", "tokens", "cost"]
        },
        headers=headers
    )
    export_data = assert_export_response(response, "csv")
    
    # Export conversation history
    response = await async_client.post(
        "/api/v1/export/conversations",
        json={"format": "json", "include_agent_analysis": False},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    conversations = response.json()
    assert "threads" in conversations
    assert len(conversations["threads"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_workspace_analytics_access(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test workspace analytics for free tier users."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Get basic analytics summary
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
    
    # Get cost trends
    response = await async_client.get(
        "/api/v1/analytics/cost-trends",
        params={"granularity": "daily"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    trends = response.json()
    assert "data_points" in trends
    
    # Advanced analytics should be restricted
    response = await async_client.get("/api/v1/analytics/advanced/ml-insights", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "upgrade" in response.json()["detail"].lower()