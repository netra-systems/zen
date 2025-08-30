"""Test auto-creation of users from JWT claims in staging environment."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.db.models_postgres import User


@pytest.mark.asyncio
async def test_auto_create_user_in_staging_from_jwt():
    """Test that users are auto-created in staging when JWT is valid but user doesn't exist."""
    
    # Setup mock JWT validation result
    user_id = str(uuid.uuid4())
    email = "anthony.chaudhary@netrasystems.ai"
    validation_result = {
        "valid": True,
        "user_id": user_id,
        "email": email
    }
    
    # Mock credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid_jwt_token"
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # First query returns no user (user doesn't exist)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Mock the created user
    created_user = User(
        id=user_id,
        email=email,
        full_name="Development User",
        is_active=True,
        is_superuser=True,
        is_developer=True,
        role="admin"
    )
    
    with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token_jwt', 
               return_value=validation_result):
        with patch('netra_backend.app.config.get_config') as mock_config:
            # Set environment to staging
            mock_config.return_value.environment = "staging"
            
            with patch('netra_backend.app.services.user_service.user_service.get_or_create_dev_user',
                      return_value=created_user) as mock_create_user:
                
                # Call the function
                result = await get_current_user(mock_credentials, mock_db)
                
                # Verify user was created
                assert result == created_user
                mock_create_user.assert_called_once_with(
                    mock_db, 
                    email=email, 
                    user_id=user_id
                )


@pytest.mark.asyncio
async def test_auto_create_in_production():
    """Test that users ARE auto-created in production from JWT claims."""
    
    # Setup mock JWT validation result
    user_id = str(uuid.uuid4())
    email = "prod-user@example.com"
    validation_result = {
        "valid": True,
        "user_id": user_id,
        "email": email
    }
    
    # Mock credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid_jwt_token"
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # First query returns no user (user doesn't exist)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Mock the created user
    created_user = User(
        id=user_id,
        email=email,
        full_name="Development User",
        is_active=True,
        is_superuser=True,
        is_developer=True,
        role="admin"
    )
    
    with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token_jwt', 
               return_value=validation_result):
        with patch('netra_backend.app.config.get_config') as mock_config:
            # Set environment to production
            mock_config.return_value.environment = "production"
            
            with patch('netra_backend.app.services.user_service.user_service.get_or_create_dev_user',
                      return_value=created_user) as mock_create_user:
                
                # Call the function
                result = await get_current_user(mock_credentials, mock_db)
                
                # Verify user was created even in production
                assert result == created_user
                mock_create_user.assert_called_once_with(
                    mock_db, 
                    email=email, 
                    user_id=user_id
                )


@pytest.mark.asyncio
async def test_existing_user_not_recreated():
    """Test that existing users are returned without recreation."""
    
    # Setup mock JWT validation result
    user_id = str(uuid.uuid4())
    validation_result = {
        "valid": True,
        "user_id": user_id
    }
    
    # Mock credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid_jwt_token"
    
    # Mock existing user
    existing_user = User(
        id=user_id,
        email="existing@example.com",
        full_name="Existing User",
        is_active=True
    )
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_result
    
    with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token_jwt', 
               return_value=validation_result):
        # Call the function
        result = await get_current_user(mock_credentials, mock_db)
        
        # Verify existing user was returned
        assert result == existing_user
        
        # Verify no user creation was attempted
        with patch('netra_backend.app.services.user_service.user_service.get_or_create_dev_user') as mock_create:
            mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_auto_create_user_in_development():
    """Test that users are auto-created in development environment as well."""
    
    # Setup mock JWT validation result
    user_id = str(uuid.uuid4())
    email = "dev@example.com"
    validation_result = {
        "valid": True,
        "user_id": user_id,
        "email": email
    }
    
    # Mock credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid_jwt_token"
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # First query returns no user (user doesn't exist)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Mock the created user
    created_user = User(
        id=user_id,
        email=email,
        full_name="Development User",
        is_active=True,
        is_superuser=True,
        is_developer=True,
        role="admin"
    )
    
    with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token_jwt', 
               return_value=validation_result):
        with patch('netra_backend.app.config.get_config') as mock_config:
            # Set environment to development
            mock_config.return_value.environment = "development"
            
            with patch('netra_backend.app.services.user_service.user_service.get_or_create_dev_user',
                      return_value=created_user) as mock_create_user:
                
                # Call the function
                result = await get_current_user(mock_credentials, mock_db)
                
                # Verify user was created
                assert result == created_user
                mock_create_user.assert_called_once_with(
                    mock_db, 
                    email=email, 
                    user_id=user_id
                )


@pytest.mark.asyncio
async def test_invalid_jwt_raises_401():
    """Test that invalid JWT raises 401 Unauthorized."""
    
    # Setup mock JWT validation result - invalid
    validation_result = {
        "valid": False
    }
    
    # Mock credentials
    mock_credentials = MagicMock()
    mock_credentials.credentials = "invalid_jwt_token"
    
    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)
    
    with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token_jwt', 
               return_value=validation_result):
        # Should raise HTTPException with 401
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail