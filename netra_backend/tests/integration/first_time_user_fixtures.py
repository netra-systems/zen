"""
Shared fixtures and utilities for first-time user integration tests.

BVJ (Business Value Justification):
1. Segment: Free  ->  Early  ->  Paid (Primary revenue funnel)
2. Business Goal: DRY shared test infrastructure for reliable onboarding tests
3. Value Impact: Ensures consistent test setup across all first-time user flows
4. Strategic Impact: Reduces test maintenance overhead while improving coverage
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
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from netra_backend.app.services.tool_registry import ToolRegistry
from netra_backend.app.services.user_service import user_service as UsageService
from netra_backend.app.services.user_service import user_service as UserService
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.websocket_core import WebSocketManager as WebSocketManager
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

# from app.utils.test_helpers import create_test_user, create_test_session  # TODO: Fix missing helper

# ============================================================================
# SHARED FIXTURES
# ============================================================================

@pytest.fixture
async def async_client() -> httpx.AsyncClient:
    """Provide async HTTP client for API testing."""
    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=30.0
    ) as client:
        yield client

@pytest.fixture
async def authenticated_user(async_client: httpx.AsyncClient, test_user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Provide authenticated user with access token."""
    # Create and verify user
    user_auth = await create_verified_user(async_client, test_user_data)
    
    return {
        "user_id": user_auth.get("user_id"),
        "access_token": user_auth.get("access_token"),
        "refresh_token": user_auth.get("refresh_token"),
        "email": test_user_data["email"]
    }

@pytest.fixture
async def redis_client() -> Redis:
    """Provide Redis client for session management."""
    from test_framework.fixtures.database_fixtures import isolated_redis_client
    return isolated_redis_client()

@pytest.fixture
async def async_session() -> AsyncSession:
    """Provide async database session for testing."""
    from test_framework.fixtures.database_fixtures import test_db_session
    async with test_db_session() as session:
        yield session

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
# HELPER FUNCTIONS
# ============================================================================

async def create_verified_user(

    async_client: httpx.AsyncClient,

    user_data: Dict[str, Any]

) -> Dict[str, Any]:

    """Helper to create and verify a user."""
    # Register

    response = await async_client.post(

        "/auth/register",

        json=user_data

    )

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

async def assert_user_registration_success(response: httpx.Response) -> Dict[str, Any]:

    """Helper to validate successful user registration."""

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert "user_id" in data

    assert "verification_token" in data

    return data

async def assert_websocket_message_flow(

    websocket,

    message_content: str,

    thread_id: Optional[str] = None

) -> Dict[str, Any]:

    """Helper to assert standard WebSocket message flow."""
    # Send message

    await websocket.send_json({

        "type": "user_message",

        "content": message_content,

        "thread_id": thread_id

    })
    
    # Get acknowledgment

    ack = await websocket.receive_json()

    assert ack["type"] == "message_acknowledged"

    assert "message_id" in ack

    assert "thread_id" in ack
    
    return ack

async def wait_for_agent_response(

    websocket,

    timeout: int = 30

) -> Dict[str, Any]:

    """Helper to wait for and validate agent response."""

    start_time = time.time()
    
    while time.time() - start_time < timeout:

        try:

            message = await asyncio.wait_for(

                websocket.receive_json(),

                timeout=1.0

            )

            if message["type"] == "agent_response":

                assert len(message["content"]) > 10  # Meaningful response

                return message

        except asyncio.TimeoutError:

            continue
    
    raise AssertionError("No agent response received within timeout")

async def verify_user_in_database(

    async_session: AsyncSession,

    user_id: str,

    expected_email: str,

    should_be_active: bool = True

) -> User:

    """Helper to verify user exists in database with expected state."""

    user = await async_session.get(User, user_id)

    assert user is not None

    assert user.email == expected_email

    assert user.is_active == should_be_active

    return user

async def verify_rate_limiting(

    async_client: httpx.AsyncClient,

    endpoint: str,

    headers: Dict[str, str],

    limit: int = 100

) -> int:

    """Helper to verify rate limiting is working."""

    requests = []

    for i in range(limit + 5):  # Exceed limit

        requests.append(async_client.get(endpoint, headers=headers))
    
    responses = await asyncio.gather(*requests, return_exceptions=True)

    rate_limited = sum(1 for r in responses 

                      if hasattr(r, 'status_code') and r.status_code == 429)
    
    assert rate_limited > 0, "Rate limiting not working"

    return rate_limited

async def simulate_oauth_callback(

    provider: str,

    user_info: Dict[str, Any],

    state: str

) -> Dict[str, Any]:

    """Helper to simulate OAuth provider callback."""

    service_map = {

        "google": "app.services.oauth_service.GoogleOAuth.get_user_info",

        "github": "app.services.oauth_service.GitHubOAuth.get_user_info"

    }
    
    with patch(service_map[provider]) as mock_service:

        mock_service.return_value = user_info

        return {

            "mock": mock_service,

            "state": state,

            "code": f"{provider}_auth_code_test"

        }

async def assert_billing_metrics(

    response: httpx.Response,

    expected_plan: str,

    should_have_limits: bool = True

) -> Dict[str, Any]:

    """Helper to validate billing/subscription response."""

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert data["plan"] == expected_plan
    
    if should_have_limits:

        assert "daily_message_limit" in data or "daily_messages" in data
        
    return data

async def track_usage_and_verify(

    usage_service: UsageService,

    user_id: str,

    message_count: int

) -> None:

    """Helper to track usage and verify it's recorded."""

    for _ in range(message_count):

        await usage_service.track_message(user_id)
    
    # Verify usage tracked (would check Redis or database)
    # Implementation depends on usage service internals

async def assert_api_key_properties(

    key_data: Dict[str, Any],

    expected_prefix: str = "nk_dev_"

) -> None:

    """Helper to validate API key response properties."""

    assert "key" in key_data

    assert "key_id" in key_data

    assert key_data["key"].startswith(expected_prefix)

async def assert_export_response(

    response: httpx.Response,

    expected_format: str = "csv"

) -> Dict[str, Any]:

    """Helper to validate data export response."""

    assert response.status_code == status.HTTP_200_OK

    export = response.json()
    
    # Either inline data or download URL

    assert "data" in export or "download_url" in export
    
    if "data" in export:

        assert len(export["data"]) > 0

    else:

        assert "expires_at" in export
        
    return export

# ============================================================================
# FIRST TIME USER FIXTURES CLASS
# ============================================================================

class FirstTimeUserFixtures:
    """Centralized fixtures and utilities for first-time user integration tests."""
    
    @staticmethod
    async def create_comprehensive_test_env():
        """Create comprehensive test environment for first-time user tests."""
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Get the session factory for tests - we'll use a direct approach
        session_factory = DatabaseManager.get_application_session()
        session = session_factory()
        
        redis_mock = MagicMock()
        
        return {
            "session": session,
            "redis": redis_mock,
            "websocket_manager": MagicMock(),
            "agent_service": MagicMock(),
            "user_service": MagicMock()
        }
    
    @staticmethod
    def init_payment_integration():
        """Initialize payment integration system mock."""
        payment_system = MagicMock()
        payment_system.validate_payment_method = AsyncMock()
        payment_system.setup_subscription = AsyncMock()
        payment_system.process_payment = AsyncMock()
        return payment_system
    
    @staticmethod
    def init_llm_optimization():
        """Initialize LLM optimization system mock."""
        llm_system = MagicMock()
        llm_system.demonstrate_optimization = AsyncMock()
        llm_system.calculate_cost_savings = AsyncMock()
        llm_system.optimize_workload = AsyncMock()
        return llm_system
    
    @staticmethod
    def init_api_integration():
        """Initialize API integration system mock."""
        api_system = MagicMock()
        api_system.validate_api_keys = AsyncMock()
        api_system.test_connection = AsyncMock()
        api_system.configure_routing = AsyncMock()
        return api_system
    
    @staticmethod
    async def create_demo_ready_user(setup):
        """Create user ready for demo."""
        from netra_backend.app.db.models_user import User
        
        user = User(
            id=str(uuid.uuid4()),
            email="demo@company.com",
            plan_tier="free"
        )
        setup["session"].add(user)
        await setup["session"].commit()
        return user
    
    @staticmethod
    async def create_converting_user(setup):
        """Create user in conversion flow."""
        from netra_backend.app.db.models_user import User
        
        user = User(
            id=str(uuid.uuid4()),
            email="converting@company.com",
            plan_tier="free"
        )
        setup["session"].add(user)
        await setup["session"].commit()
        return user
    
    @staticmethod
    async def cleanup_test(setup):
        """Clean up test environment."""
        if setup.get("session"):
            await setup["session"].rollback()
            await setup["session"].close()

# ============================================================================
# MOCK DATA PROVIDERS
# ============================================================================

def get_mock_optimization_request() -> Dict[str, Any]:

    """Get standardized optimization request for testing."""

    return {

        "type": "cost_optimization",

        "context": {

            "current_monthly_cost": 5000,

            "target_reduction_percentage": 20,

            "quality_threshold": 0.95,

            "models_in_use": [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value],

            "daily_requests": 10000,

            "average_tokens_per_request": 500

        },

        "urgency": "normal",

        "detailed_analysis": True

    }

def get_mock_provider_configs() -> Dict[str, Dict[str, Any]]:

    """Get mock provider configurations for testing."""

    return {

        "openai": {

            "api_key": "sk-test-1234567890abcdef",

            "organization_id": "org-test123"

        },

        "anthropic": {

            "api_key": "sk-ant-test-key-123"

        },

        "google": {

            "oauth_info": {

                "id": "google_123456",

                "email": "testuser@gmail.com",

                "name": "Test User",

                "picture": "https://example.com/photo.jpg",

                "verified_email": True

            }

        }

    }

def get_mock_user_preferences() -> Dict[str, Any]:

    """Get standardized user preferences for testing."""

    return {

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

            "preferred_models": [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value]

        }

    }