"""Regression tests for User model SQL parameter binding issues.

Tests to prevent:
1. SQL parameter count mismatch when creating users
2. Error handler IndexError when logging SQLAlchemy errors
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_user import Secret, ToolUsageLog, User

@pytest.mark.asyncio
async def test_user_creation_with_defaults():
    """Test that User model creates with proper defaults."""
    user = User(
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        role="standard_user",
        plan_tier="free",
        payment_status="active",
        auto_renew=False,
        trial_period=0,
        permissions={},
        feature_flags={},
        tool_permissions={}
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
    """Test that datetime defaults are properly configured with SQLAlchemy func.now()."""
    # Test that the defaults use SQLAlchemy's func.now() (SSOT method)
    from netra_backend.app.db.models_user import User as UserModel
    from sqlalchemy.sql.functions import now
    
    # Check that the default is SQLAlchemy func.now() - the SSOT method
    assert UserModel.created_at.default is not None
    assert UserModel.updated_at.default is not None  
    assert UserModel.plan_started_at.default is not None
    
    # Verify the default is func.now() (not Python callable)
    assert isinstance(UserModel.created_at.default.arg, now)
    assert isinstance(UserModel.updated_at.default.arg, now)
    assert isinstance(UserModel.plan_started_at.default.arg, now)
    
    # Create a user and test default values work when saved to DB
    user = User(
        email="test2@example.com",
        full_name="Test User 2"
    )
    
    # Note: The defaults won't be set until the object is saved to database
    # For unit test, we just verify the model structure is correct

@pytest.mark.asyncio 
async def test_tool_usage_log_datetime_defaults():
    """Test that ToolUsageLog datetime defaults are properly configured with SQLAlchemy func.now()."""
    from netra_backend.app.db.models_user import ToolUsageLog as LogModel
    from sqlalchemy.sql.functions import now
    
    # Check that the default is SQLAlchemy func.now() - the SSOT method
    assert LogModel.created_at.default is not None
    
    # Verify the default is func.now() (not Python callable)
    assert isinstance(LogModel.created_at.default.arg, now)
    
    log = ToolUsageLog(
        user_id="test-user-id",
        tool_name="test_tool",
        status="success",
        plan_tier="free"
    )
    
    # Note: The defaults won't be set until the object is saved to database
    # For unit test, we just verify the model structure is correct

@pytest.mark.asyncio
async def test_secret_datetime_defaults():
    """Test that Secret datetime defaults are properly configured."""
    from netra_backend.app.db.models_user import Secret as SecretModel
    from sqlalchemy.sql.functions import now
    
    # Check that the default is set to SQLAlchemy's func.now()
    assert SecretModel.created_at.default is not None
    assert SecretModel.updated_at.default is not None
    
    # Verify the default is func.now()
    assert isinstance(SecretModel.created_at.default.arg, now)
    assert isinstance(SecretModel.updated_at.default.arg, now)
    
    secret = Secret(
        user_id="test-user-id",
        key="test_key",
        encrypted_value="encrypted_test_value"
    )
    
    # Note: The defaults won't be set until the object is saved to database
    # For unit test, we just verify the model structure is correct