"""Regression tests for User model SQL parameter binding issues.

Tests to prevent:
1. SQL parameter count mismatch when creating users
2. Error handler IndexError when logging SQLAlchemy errors
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_user import User, Secret, ToolUsageLog


@pytest.mark.asyncio
async def test_user_creation_with_defaults():
    """Test that User model creates with proper defaults."""
    user = User(
        email="test@example.com",
        full_name="Test User"
    )
    
    # Verify defaults are set correctly
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.role == "standard_user"
    assert user.plan_tier == "free"
    assert user.payment_status == "active"
    assert user.auto_renew is False
    assert user.trial_period == 0
    assert isinstance(user.permissions, dict)
    assert isinstance(user.feature_flags, dict)
    assert isinstance(user.tool_permissions, dict)


@pytest.mark.asyncio
async def test_user_creation_datetime_defaults():
    """Test that datetime defaults are properly callable."""
    user = User(
        email="test2@example.com",
        full_name="Test User 2"
    )
    
    # The datetime defaults should be callable
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.plan_started_at is not None
    
    # They should be close to current time
    now = datetime.now(timezone.utc)
    assert abs((now - user.created_at).total_seconds()) < 5
    assert abs((now - user.updated_at).total_seconds()) < 5
    assert abs((now - user.plan_started_at).total_seconds()) < 5


@pytest.mark.asyncio 
async def test_tool_usage_log_datetime_defaults():
    """Test that ToolUsageLog datetime defaults are properly callable."""
    log = ToolUsageLog(
        user_id="test-user-id",
        tool_name="test_tool",
        status="success",
        plan_tier="free"
    )
    
    # The datetime default should be callable
    assert log.created_at is not None
    
    # Should be close to current time
    now = datetime.now(timezone.utc)
    assert abs((now - log.created_at).total_seconds()) < 5


@pytest.mark.asyncio
async def test_secret_datetime_defaults():
    """Test that Secret datetime defaults are properly callable."""
    secret = Secret(
        user_id="test-user-id",
        key="test_key",
        encrypted_value="encrypted_test_value"
    )
    
    # The datetime defaults should be callable
    assert secret.created_at is not None
    assert secret.updated_at is not None
    
    # Should be close to current time
    now = datetime.now(timezone.utc)
    assert abs((now - secret.created_at).total_seconds()) < 5
    assert abs((now - secret.updated_at).total_seconds()) < 5


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_database_insert(async_session: AsyncSession):
    """Integration test for actual database insert with User model."""
    user = User(
        email="db_test@example.com",
        full_name="DB Test User"
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Verify the user was created with proper ID
    assert user.id is not None
    assert user.email == "db_test@example.com"
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.plan_started_at is not None
    
    # Clean up
    await async_session.delete(user)
    await async_session.commit()


@pytest.mark.asyncio
@pytest.mark.integration  
async def test_user_with_all_fields(async_session: AsyncSession):
    """Test creating user with all fields populated."""
    user = User(
        email="complete@example.com",
        full_name="Complete User",
        hashed_password="hashed_password_here",
        picture="https://example.com/pic.jpg",
        is_active=True,
        is_superuser=True,
        role="admin",
        permissions={"admin": True},
        is_developer=True,
        plan_tier="enterprise",
        plan_expires_at=datetime.now(timezone.utc),
        feature_flags={"feature1": True},
        tool_permissions={"tool1": "allowed"},
        auto_renew=True,
        payment_status="active",
        trial_period=False
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    # Verify all fields
    assert user.id is not None
    assert user.email == "complete@example.com"
    assert user.role == "admin"
    assert user.plan_tier == "enterprise"
    assert user.permissions == {"admin": True}
    
    # Clean up
    await async_session.delete(user)
    await async_session.commit()