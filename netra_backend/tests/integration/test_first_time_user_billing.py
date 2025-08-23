"""
First-time user billing and usage limit integration tests.

BVJ (Business Value Justification):
1. Segment: Free → Early → Mid (Revenue conversion funnel)
2. Business Goal: Protect $140K MRR by ensuring billing flow reliability
3. Value Impact: Validates usage limits and smooth upgrade experience
4. Strategic Impact: Core revenue protection and expansion mechanism
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import patch

import httpx
import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.tests.integration.first_time_user_fixtures import (
    assert_billing_metrics,
    track_usage_and_verify,
    usage_service,
)

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_free_tier_usage_limits_enforcement(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    usage_service,
    redis_client
):
    """Test free tier daily message limits are enforced."""
    user_id = authenticated_user["user_id"]
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Check initial usage and limits
    response = await async_client.get("/api/v1/usage/current", headers=headers)
    usage_data = assert_billing_metrics(response, "free")
    assert usage_data["daily_message_limit"] == 50
    assert usage_data["messages_used_today"] == 0
    
    # Simulate approaching limit (80%)
    await track_usage_and_verify(usage_service, user_id, 40)
    
    # Send message near limit - should get warning
    response = await async_client.post(
        "/api/v1/chat/message",
        json={"content": "Test near limit", "thread_id": str(uuid.uuid4())},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "warning" in data
    assert "80%" in data["warning"] or "limit" in data["warning"].lower()

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_daily_limit_exceeded_blocking(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    usage_service
):
    """Test users are blocked when exceeding daily limits."""
    user_id = authenticated_user["user_id"]
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Reach daily limit
    await track_usage_and_verify(usage_service, user_id, 50)
    
    # Attempt to exceed limit
    response = await async_client.post(
        "/api/v1/chat/message",
        json={"content": "Beyond limit", "thread_id": str(uuid.uuid4())},
        headers=headers
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    data = response.json()
    assert "daily limit" in data["detail"].lower()
    assert "upgrade" in data["detail"].lower()

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_premium_features_access_control(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test premium features are blocked for free tier."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Advanced tools should be blocked
    response = await async_client.post(
        "/api/v1/tools/enterprise-analytics",
        json={"data": "test"},
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "upgrade required" in response.json()["detail"].lower()
    
    # Advanced features should prompt upgrade
    response = await async_client.post(
        "/api/v1/tools/advanced-analytics/execute",
        json={"query": "test"},
        headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_usage_tracking_accuracy(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    usage_service,
    redis_client
):
    """Test usage tracking for billing accuracy."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Get baseline usage
    response = await async_client.get("/api/v1/usage/detailed", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    baseline_usage = response.json()
    
    # Perform tracked actions
    actions = [
        async_client.post(
            "/api/v1/chat/message",
            json={"content": "Usage test 1", "thread_id": str(uuid.uuid4())},
            headers=headers
        ),
        async_client.get("/api/v1/user/profile", headers=headers),
        async_client.post(
            "/api/v1/tools/cost-analyzer/execute",
            json={"data": {"cost": 1000}},
            headers=headers
        ),
    ]
    await asyncio.gather(*actions)
    
    # Verify usage incremented
    response = await async_client.get("/api/v1/usage/detailed", headers=headers)
    current_usage = response.json()
    assert current_usage["messages_sent"] > baseline_usage["messages_sent"]
    assert current_usage["api_calls"] > baseline_usage["api_calls"]

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_usage_reset_daily_cycle(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    redis_client
):
    """Test usage resets on new billing cycle."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id = authenticated_user["user_id"]
    
    # Simulate next day - clear daily usage
    await redis_client.delete(f"usage:{user_id}:daily")
    
    # Check usage reset
    response = await async_client.get("/api/v1/usage/current", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["messages_used_today"] == 0

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_upgrade_to_pro_plan_flow(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession
):
    """Test smooth upgrade from free to paid plan."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Check current plan
    response = await async_client.get("/api/v1/billing/subscription", headers=headers)
    current_plan = assert_billing_metrics(response, "free")
    assert current_plan["trial_days_remaining"] >= 0
    
    # Get available plans
    response = await async_client.get("/api/v1/billing/plans")
    assert response.status_code == status.HTTP_200_OK
    plans = response.json()
    pro_plan = next(p for p in plans if p["name"] == "pro")
    assert pro_plan["price"] > 0
    
    # Initiate upgrade with mocked payment
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

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_pro_plan_benefits_activation(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test pro plan benefits are immediately available."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Mock successful upgrade first
    with patch("app.services.billing_service.get_user_plan") as mock_plan:
        mock_plan.return_value = {"plan": "pro", "status": "active"}
        
        # Verify increased limits
        response = await async_client.get("/api/v1/usage/limits", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        limits = response.json()
        assert limits["daily_messages"] > 50  # More than free tier
        assert limits["concurrent_sessions"] > 2
        
        # Test access to pro features
        response = await async_client.post(
            "/api/v1/tools/advanced-analytics/execute",
            json={"query": "test"},
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_billing_invoice_generation(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test billing invoice generation for paid plans."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Mock pro plan user
    with patch("app.services.billing_service.get_user_plan") as mock_plan:
        mock_plan.return_value = {"plan": "pro", "status": "active", "price": 99}
        
        # Get next invoice
        response = await async_client.get("/api/v1/billing/next-invoice", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        next_invoice = response.json()
        assert next_invoice["amount"] == 99
        assert "due_date" in next_invoice
        
        # Get current billing period
        response = await async_client.get("/api/v1/billing/current-period", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        billing = response.json()
        assert "total_cost" in billing
        assert billing["total_cost"] >= 0

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_downgrade_prevention_during_billing(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test downgrade is prevented during active billing period."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Mock pro plan user
    with patch("app.services.billing_service.get_user_plan") as mock_plan:
        mock_plan.return_value = {"plan": "pro", "status": "active"}
        
        # Attempt immediate downgrade
        response = await async_client.post(
            "/api/v1/billing/change-plan",
            json={"plan_id": "free"},
            headers=headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "end of billing period" in response.json()["detail"].lower()