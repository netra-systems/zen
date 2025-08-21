"""
First-time user signup and authentication integration tests.

BVJ (Business Value Justification):
1. Segment: Free → Early (New user acquisition)
2. Business Goal: Protect $30K MRR by ensuring seamless signup flow
3. Value Impact: Validates email verification and authentication reliability
4. Strategic Impact: Prevents signup funnel failures that block revenue
"""

import pytest
import httpx
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from netra_backend.app.models.user import User
from netra_backend.tests.first_time_user_fixtures import (
    test_user_data, auth_service, user_service,
    assert_user_registration_success, verify_user_in_database,
    simulate_oauth_callback, get_mock_provider_configs
)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_user_registration_with_email_verification(
    async_client: httpx.AsyncClient,
    test_user_data,
    async_session: AsyncSession,
    redis_client: Redis
):
    """Test complete user registration flow with email verification."""
    # Register new user
    response = await async_client.post("/auth/register", json=test_user_data)
    reg_data = await assert_user_registration_success(response)
    
    # Verify user in database (inactive)
    user = await verify_user_in_database(
        async_session, reg_data["user_id"], test_user_data["email"], should_be_active=False
    )
    assert user.email_verified is False
    
    # Verify email verification token in Redis
    token_key = f"email_verify:{reg_data['verification_token']}"
    stored_user_id = await redis_client.get(token_key)
    assert stored_user_id == str(reg_data["user_id"])


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_email_verification_activation(
    async_client: httpx.AsyncClient,
    test_user_data,
    async_session: AsyncSession
):
    """Test email verification activates user account."""
    # Register user
    response = await async_client.post("/auth/register", json=test_user_data)
    reg_data = await assert_user_registration_success(response)
    
    # Complete email verification
    response = await async_client.post(
        f"/auth/verify-email/{reg_data['verification_token']}"
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Verify user is now active
    user = await verify_user_in_database(
        async_session, reg_data["user_id"], test_user_data["email"], should_be_active=True
    )
    assert user.email_verified is True


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_user_authentication_after_verification(
    async_client: httpx.AsyncClient,
    test_user_data,
    async_session: AsyncSession
):
    """Test user can authenticate after email verification."""
    # Register and verify user
    response = await async_client.post("/auth/register", json=test_user_data)
    reg_data = await assert_user_registration_success(response)
    
    await async_client.post(f"/auth/verify-email/{reg_data['verification_token']}")
    
    # Test authentication
    response = await async_client.post(
        "/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]}
    )
    assert response.status_code == status.HTTP_200_OK
    auth_data = response.json()
    assert "access_token" in auth_data
    assert "refresh_token" in auth_data


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_duplicate_registration_prevention(
    async_client: httpx.AsyncClient,
    test_user_data
):
    """Test duplicate email registration is prevented."""
    # First registration
    response = await async_client.post("/auth/register", json=test_user_data)
    await assert_user_registration_success(response)
    
    # Attempt duplicate registration
    response = await async_client.post("/auth/register", json=test_user_data)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_google_oauth_signup_flow(
    async_client: httpx.AsyncClient,
    async_session: AsyncSession
):
    """Test Google OAuth signup integration."""
    # Initiate OAuth flow
    response = await async_client.get("/auth/oauth/google/authorize")
    assert response.status_code == status.HTTP_200_OK
    google_auth = response.json()
    assert "authorization_url" in google_auth
    assert "accounts.google.com" in google_auth["authorization_url"]
    
    # Simulate OAuth callback
    provider_configs = get_mock_provider_configs()
    oauth_mock = simulate_oauth_callback(
        "google", provider_configs["google"]["oauth_info"], google_auth["state"]
    )
    
    with oauth_mock["mock"]:
        response = await async_client.get(
            "/auth/oauth/google/callback",
            params={"code": oauth_mock["code"], "state": oauth_mock["state"]}
        )
        assert response.status_code == status.HTTP_200_OK
        auth_result = response.json()
        assert "access_token" in auth_result
        assert auth_result["user"]["email"] == "testuser@gmail.com"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_github_oauth_signup_flow(
    async_client: httpx.AsyncClient,
    async_session: AsyncSession
):
    """Test GitHub OAuth signup integration."""
    # Initiate GitHub OAuth
    response = await async_client.get("/auth/oauth/github/authorize")
    assert response.status_code == status.HTTP_200_OK
    github_auth = response.json()
    assert "github.com/login/oauth" in github_auth["authorization_url"]
    
    # Simulate GitHub callback
    github_user_info = {
        "id": 789012,
        "login": "testuser",
        "email": "testuser@github.com",
        "name": "Test GitHub User",
        "avatar_url": "https://avatars.githubusercontent.com/u/789012"
    }
    
    oauth_mock = simulate_oauth_callback("github", github_user_info, github_auth["state"])
    
    with oauth_mock["mock"]:
        response = await async_client.get(
            "/auth/oauth/github/callback",
            params={"code": oauth_mock["code"], "state": oauth_mock["state"]}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
async def test_oauth_account_linking(
    async_client: httpx.AsyncClient,
    async_session: AsyncSession
):
    """Test OAuth linking to existing email account."""
    # Create GitHub account first
    github_info = {"id": 789012, "email": "shared@test.com", "name": "Test User"}
    oauth_mock = simulate_oauth_callback("github", github_info, "test_state")
    
    with oauth_mock["mock"]:
        response = await async_client.get(
            "/auth/oauth/github/callback",
            params={"code": oauth_mock["code"], "state": oauth_mock["state"]}
        )
        assert response.status_code == status.HTTP_200_OK
    
    # Link Google to same email
    google_info = {"id": "google_123", "email": "shared@test.com", "verified_email": True}
    oauth_mock = simulate_oauth_callback("google", google_info, "test_state2")
    
    with oauth_mock["mock"]:
        response = await async_client.get(
            "/auth/oauth/google/callback",
            params={"code": oauth_mock["code"], "state": oauth_mock["state"]}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verify account was linked
        user = await async_session.query(User).filter(User.email == "shared@test.com").first()
        assert user.oauth_provider == "google"  # Latest provider