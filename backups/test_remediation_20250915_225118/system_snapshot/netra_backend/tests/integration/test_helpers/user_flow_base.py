"""
Base utilities for user flow testing across tiers.
Provides common helpers for authentication, session management, and validation.

BVJ (Business Value Justification):
1. Segment: All tiers (Free  ->  Early  ->  Mid  ->  Enterprise)
2. Business Goal: Prevent regression in revenue funnel
3. Value Impact: Enables efficient test maintenance and development
4. Strategic Impact: Protects $570K MRR through test modularity
"""

from datetime import datetime, timedelta
from fastapi import status
from netra_backend.app.auth_integration.auth import get_current_user as AuthService
from netra_backend.app.config import get_config
from netra_backend.app.schemas.user_plan import UserPlan
from netra_backend.app.schemas.registry import Message, Thread, User
from netra_backend.app.services.agent_service import AgentService as AgentDispatcher
from netra_backend.app.services.cost_calculator import (
    CostCalculatorService as BillingService,
)
from netra_backend.app.services.user_service import user_service as UsageService
from netra_backend.app.services.user_service import user_service as UserService
from netra_backend.app.websocket_core import WebSocketManager
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import httpx
import json
import pytest
import time
import uuid

class UserFlowTestBase:

    """Base class for user flow testing with common utilities."""
    
    @staticmethod

    async def create_verified_user(

        async_client: httpx.AsyncClient,

        user_data: Dict[str, Any]

    ) -> Dict[str, Any]:

        """Create and verify a user account."""
        # Register

        response = await async_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED

        reg_data = response.json()
        
        # Verify email

        response = await async_client.post(

            f"/auth/verify-email/{reg_data['verification_token']}"

        )

        assert response.status_code == status.HTTP_200_OK
        
        # Login

        response = await async_client.post(

            "/auth/login",

            json={"email": user_data["email"], "password": user_data["password"]}

        )

        assert response.status_code == status.HTTP_200_OK

        return response.json()

    @staticmethod

    async def simulate_chat_activity(

        async_client: httpx.AsyncClient,

        access_token: str,

        num_messages: int = 5

    ) -> List[str]:

        """Simulate user chat activity and return thread IDs."""

        headers = {"Authorization": f"Bearer {access_token}"}

        thread_ids = []
        
        for i in range(num_messages):

            response = await async_client.post(

                "/api/chat/message",

                json={

                    "content": f"Test message {i}",

                    "thread_id": str(uuid.uuid4())

                },

                headers=headers

            )

            if response.status_code == status.HTTP_200_OK:

                thread_ids.append(response.json().get("thread_id"))
        
        return thread_ids

    @staticmethod

    async def verify_plan_limits(

        async_client: httpx.AsyncClient,

        access_token: str,

        expected_plan: str

    ) -> Dict[str, Any]:

        """Verify user plan and limits."""

        headers = {"Authorization": f"Bearer {access_token}"}

        response = await async_client.get("/api/usage/current", headers=headers)

        assert response.status_code == status.HTTP_200_OK

        usage_data = response.json()

        assert usage_data["plan"] == expected_plan

        return usage_data

    @staticmethod

    async def test_websocket_connection(

        async_client: httpx.AsyncClient,

        access_token: str,

        test_message: str = "Test WebSocket message"

    ) -> Dict[str, Any]:

        """Test WebSocket connection and message handling."""

        async with async_client.websocket_connect(f"/ws?token={access_token}") as ws:
            # Send test message

            await ws.send_json({

                "type": "user_message",

                "content": test_message,

                "thread_id": str(uuid.uuid4())

            })
            
            # Receive acknowledgment

            ack = await ws.receive_json()

            assert ack["type"] == "message_acknowledged"

            return ack

    @staticmethod

    async def verify_feature_access(

        async_client: httpx.AsyncClient,

        access_token: str,

        feature_endpoint: str,

        should_have_access: bool

    ) -> bool:

        """Verify access to specific features based on plan."""

        headers = {"Authorization": f"Bearer {access_token}"}

        response = await async_client.post(feature_endpoint, json={}, headers=headers)
        
        if should_have_access:

            assert response.status_code != status.HTTP_403_FORBIDDEN

            return True

        else:

            assert response.status_code == status.HTTP_403_FORBIDDEN

            return False

    @staticmethod

    async def simulate_upgrade_flow(

        async_client: httpx.AsyncClient,

        access_token: str,

        target_plan: str

    ) -> Dict[str, Any]:

        """Simulate plan upgrade flow."""

        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get available plans

        response = await async_client.get("/api/billing/plans")

        assert response.status_code == status.HTTP_200_OK

        plans = response.json()

        target_plan_data = next(p for p in plans if p["name"] == target_plan)
        
        # Mock payment processing

        with patch("app.services.payment_service.process_payment") as mock_payment:

            mock_payment.return_value = {

                "success": True,

                "transaction_id": f"txn_test_{int(time.time())}",

                "amount": target_plan_data["price"]

            }
            
            # Initiate upgrade

            response = await async_client.post(

                "/api/billing/upgrade",

                json={

                    "plan_id": target_plan_data["id"],

                    "payment_method": "card",

                    "payment_token": "tok_test_visa_4242"

                },

                headers=headers

            )

            assert response.status_code == status.HTTP_200_OK

            return response.json()

    @staticmethod

    async def test_usage_tracking(

        async_client: httpx.AsyncClient,

        access_token: str,

        usage_service: UsageService,

        user_id: str

    ) -> Dict[str, Any]:

        """Test usage tracking functionality."""

        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get baseline usage

        response = await async_client.get("/api/usage/detailed", headers=headers)

        assert response.status_code == status.HTTP_200_OK

        baseline = response.json()
        
        # Perform tracked action

        await async_client.post(

            "/api/chat/message",

            json={"content": "Usage test", "thread_id": str(uuid.uuid4())},

            headers=headers

        )
        
        # Verify usage incremented

        response = await async_client.get("/api/usage/detailed", headers=headers)

        assert response.status_code == status.HTTP_200_OK

        current = response.json()

        assert current["messages_sent"] > baseline["messages_sent"]
        
        return current

    @staticmethod

    async def verify_data_export_capability(

        async_client: httpx.AsyncClient,

        access_token: str,

        export_type: str = "basic"

    ) -> Dict[str, Any]:

        """Verify data export capabilities based on plan."""

        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await async_client.post(

            "/api/export/usage",

            json={

                "format": "csv",

                "date_range": "last_30_days",

                "include_fields": ["timestamp", "message", "tokens"]

            },

            headers=headers

        )
        
        if export_type == "basic":

            assert response.status_code == status.HTTP_200_OK
        
        return response.json() if response.status_code == 200 else {}

    @staticmethod

    async def test_error_recovery(

        async_client: httpx.AsyncClient,

        access_token: str

    ) -> bool:

        """Test error recovery mechanisms."""

        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test validation error handling

        response = await async_client.post(

            "/api/chat/message",

            json={"content": "", "thread_id": "invalid-uuid"},

            headers=headers

        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test rate limiting

        with patch("app.services.rate_limiter.check_rate_limit") as mock_limit:

            mock_limit.return_value = False

            response = await async_client.post(

                "/api/chat/message",

                json={"content": "Test", "thread_id": str(uuid.uuid4())},

                headers=headers

            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        
        return True

    @staticmethod

    async def test_session_persistence(

        async_client: httpx.AsyncClient,

        authenticated_user: Dict[str, Any],

        redis_client: Redis

    ) -> Dict[str, Any]:

        """Test session persistence across refresh."""

        access_token = authenticated_user["access_token"]

        refresh_token = authenticated_user["refresh_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Create session state

        ui_state = {"theme": "dark", "active_thread": str(uuid.uuid4())}

        response = await async_client.put(

            "/api/session/ui-state", json=ui_state, headers=headers

        )

        assert response.status_code == status.HTTP_200_OK
        
        # Refresh token and restore session

        response = await async_client.post(

            "/auth/refresh", json={"refresh_token": refresh_token}

        )

        new_token = response.json()["access_token"]

        new_headers = {"Authorization": f"Bearer {new_token}"}
        
        response = await async_client.get("/api/session/restore", headers=new_headers)

        assert response.status_code == status.HTTP_200_OK

        return response.json()

# Common assertion helpers for user flow testing

def assert_successful_registration(response_data: Dict[str, Any]) -> None:

    """Assert successful user registration."""

    assert "user_id" in response_data

    assert "verification_token" in response_data

def assert_plan_compliance(usage_data: Dict[str, Any], plan: str) -> None:

    """Assert usage data matches plan expectations."""

    if plan == "free":

        assert usage_data["daily_message_limit"] == 50

    elif plan == "pro":

        assert usage_data["daily_message_limit"] > 50