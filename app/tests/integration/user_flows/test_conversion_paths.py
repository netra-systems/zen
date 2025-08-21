"""
User conversion path testing across all tiers.
Critical for protecting the entire revenue funnel.

BVJ (Business Value Justification):
1. Segment: All tiers (Complete conversion funnel)
2. Business Goal: Protect $570K MRR by ensuring smooth tier transitions
3. Value Impact: Validates upgrade triggers and conversion mechanisms
4. Strategic Impact: Optimizes revenue funnel and reduces churn
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import patch

import pytest
import httpx
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.user import User
from app.models.conversion_event import ConversionEvent
from app.services.user_service import UserService as UsageService

from ..test_helpers.user_flow_base import UserFlowTestBase
from ..fixtures.user_journey_data import UserTestData


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_complete_free_to_enterprise_conversion_journey(
    async_client: httpx.AsyncClient,
    async_session: AsyncSession,
    redis_client: Redis,
    usage_service: UsageService
):
    """Test complete user journey from free tier to enterprise."""
    # Start with free tier user
    user_data = UserTestData.generate_user_data("free")
    auth_data = await UserFlowTestBase.create_verified_user(async_client, user_data)
    access_token = auth_data["access_token"]
    user_id = auth_data["user_id"]
    
    # Phase 1: Free tier experience and limit discovery
    await UserFlowTestBase.simulate_chat_activity(async_client, access_token, 45)
    
    # Hit free tier limit
    for i in range(50):
        await usage_service.track_message(user_id)
    
    # Attempt message that triggers upgrade prompt
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.post(
        "/api/v1/chat/message",
        json={"content": "Need advanced analysis", "thread_id": str(uuid.uuid4())},
        headers=headers
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "upgrade" in response.json()["detail"].lower()
    
    # Phase 2: Upgrade to Early tier
    early_upgrade = await UserFlowTestBase.simulate_upgrade_flow(
        async_client, access_token, "early"
    )
    assert early_upgrade["success"] is True
    
    # Verify early tier features work
    response = await async_client.post(
        "/api/v1/tools/advanced-cost-analyzer/execute",
        json={"analysis_type": "basic"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Phase 3: Team growth triggers Mid tier
    # Simulate team collaboration needs
    response = await async_client.post(
        "/api/v1/teams/create",
        json={"name": "Test Team", "description": "Growing team"},
        headers=headers
    )
    # Should prompt for Pro upgrade for team features
    if response.status_code == status.HTTP_403_FORBIDDEN:
        assert "upgrade" in response.json()["detail"].lower()
    
    # Upgrade to Pro/Mid tier
    pro_upgrade = await UserFlowTestBase.simulate_upgrade_flow(
        async_client, access_token, "pro"
    )
    assert pro_upgrade["new_plan"] == "pro"
    
    # Phase 4: Enterprise needs trigger final upgrade
    # Simulate enterprise requirements
    response = await async_client.post(
        "/api/v1/organizations/create",
        json={"name": "Enterprise Corp", "compliance_requirements": ["SOC2"]},
        headers=headers
    )
    # Should prompt for Enterprise upgrade
    if response.status_code == status.HTTP_403_FORBIDDEN:
        assert "enterprise" in response.json()["detail"].lower()
    
    # Final upgrade to Enterprise
    enterprise_upgrade = await UserFlowTestBase.simulate_upgrade_flow(
        async_client, access_token, "enterprise"
    )
    assert enterprise_upgrade["new_plan"] == "enterprise"
    
    # Verify full enterprise feature access
    response = await async_client.post(
        "/api/v1/audit/logs",
        headers=headers
    )
    assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_usage_based_conversion_triggers(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    usage_service: UsageService
):
    """Test that usage patterns trigger appropriate conversion prompts."""
    access_token = authenticated_user["access_token"]
    user_id = authenticated_user["user_id"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test approaching daily limit trigger
    for i in range(40):  # 80% of free tier limit
        await usage_service.track_message(user_id)
    
    response = await async_client.post(
        "/api/v1/chat/message",
        json={"content": "Test message", "thread_id": str(uuid.uuid4())},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "warning" in data or "upgrade" in str(data).lower()
    
    # Test feature-based conversion trigger
    response = await async_client.post(
        "/api/v1/tools/enterprise-analytics",
        json={"query": "advanced analysis"},
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error_data = response.json()
    assert "upgrade" in error_data["detail"].lower()
    assert "early" in error_data["detail"].lower() or "pro" in error_data["detail"].lower()




@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_conversion_analytics_tracking(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession
):
    """Test conversion event tracking and analytics."""
    access_token = authenticated_user["access_token"]
    user_id = authenticated_user["user_id"]
    
    # Simulate conversion trigger events
    trigger_events = [
        "daily_limit_reached",
        "advanced_feature_attempted", 
        "export_requested",
        "api_key_requested"
    ]
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    for event in trigger_events:
        # Simulate the trigger event
        if event == "daily_limit_reached":
            response = await async_client.post(
                "/api/v1/usage/track-limit-event",
                json={"event_type": "limit_reached", "limit_type": "daily_messages"},
                headers=headers
            )
        elif event == "advanced_feature_attempted":
            await async_client.post(
                "/api/v1/tools/advanced-analytics",
                headers=headers
            )
        # Events should be automatically tracked
    
    # Check conversion analytics
    response = await async_client.get(
        "/api/v1/analytics/conversion-funnel",
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    funnel_data = response.json()
    assert "trigger_events" in funnel_data
    assert "conversion_score" in funnel_data
    
    # Verify events are tracked in database
    conversion_events = await async_session.query(ConversionEvent).filter(
        ConversionEvent.user_id == user_id
    ).all()
    assert len(conversion_events) > 0




@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_trial_and_retention_mechanisms(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test trial extension, churn prevention, and retention offers."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test trial extension
    response = await async_client.post(
        "/api/v1/billing/trial-extension",
        json={"reason": "evaluating_features", "team_size": 5},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Upgrade to test retention
    await UserFlowTestBase.simulate_upgrade_flow(async_client, access_token, "early")
    
    # Test downgrade intent and retention
    response = await async_client.post(
        "/api/v1/billing/downgrade-intent",
        json={"reason": "cost_concerns", "feedback": "Too expensive"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    retention_data = response.json()
    assert "retention_offers" in retention_data


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_referral_and_campaign_conversion(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test referral programs and promotional conversion campaigns."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Generate referral code
    response = await async_client.post(
        "/api/v1/referrals/generate",
        json={"campaign": "free_to_early_conversion"},
        headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    referral_data = response.json()
    assert "referral_code" in referral_data
    
    # Check for active campaigns
    response = await async_client.get("/api/v1/campaigns/active", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    campaigns = response.json()
    
    # Track conversion funnel metrics
    response = await async_client.post(
        "/api/v1/analytics/conversion-event",
        json={"event": "upgrade_flow_started", "step": "pricing_viewed"},
        headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED