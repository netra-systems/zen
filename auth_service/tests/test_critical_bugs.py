"""
Failing tests for critical bugs identified in the system.
These tests are designed to fail initially to demonstrate the bugs exist.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add auth_service to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_core.routes.auth_routes import refresh_tokens
from auth_core.models.auth_models import User


class TestAuthRefreshEndpointBug:
    """Test the critical bug in refresh endpoint - await request.body() is not awaitable"""
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_body_await_bug(self):
        """
        This test demonstrates the bug where request.body() is being awaited
        but it's not an awaitable method.
        """
        # Create a mock request with body() that returns bytes (not awaitable)
        request = MagicMock(spec=Request)
        request.body = MagicMock(return_value=b'{"refresh_token": "test_token"}')
        
        # This should fail because body() is not awaitable
        with pytest.raises((TypeError, AttributeError)) as exc_info:
            await refresh_tokens(request)
        
        # The error should indicate that body() is not awaitable
        assert "await" in str(exc_info.value).lower() or "coroutine" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_should_use_json_method(self):
        """
        Test that demonstrates the correct way - using request.json()
        This test will fail with current implementation but pass when fixed.
        """
        # Create a mock request with json() that is properly awaitable
        request = AsyncMock(spec=Request)
        request.json = AsyncMock(return_value={"refresh_token": "test_token"})
        
        # Mock dependencies
        with patch('auth_core.routes.auth_routes.verify_token') as mock_verify, \
             patch('auth_core.routes.auth_routes.refresh_access_token') as mock_refresh, \
             patch('auth_core.routes.auth_routes.db_manager') as mock_db:
            
            mock_verify.return_value = {"user_id": "123", "email": "test@test.com"}
            mock_refresh.return_value = ("new_access", "new_refresh")
            mock_db.get_user_by_id = AsyncMock(return_value={"id": "123", "email": "test@test.com"})
            
            # This should work if the implementation is fixed to use request.json()
            try:
                result = await refresh_tokens(request)
                # If we get here, the fix has been applied
                assert "access_token" in result
                assert "refresh_token" in result
            except (TypeError, AttributeError) as e:
                # Current buggy implementation will fail here
                pytest.fail(f"refresh_tokens failed with current bug: {e}")


class TestUserModelRoleFieldBug:
    """Test the missing 'role' field requirement in User model"""
    
    def test_user_model_missing_required_fields(self):
        """
        Test that User model is missing required fields that tests expect.
        Many tests fail because they expect fields like 'role' that don't exist.
        """
        # Current User model only has: id, email, name, picture, verified_email, provider
        # But tests expect additional fields like 'role'
        user_data = {
            "id": "123",
            "email": "test@test.com",
            "name": "Test User",
            "provider": "google"
        }
        
        # Create user with current model
        user = User(**user_data)
        
        # This will fail - User model doesn't have 'role' field
        with pytest.raises(AttributeError) as exc_info:
            _ = user.role
        
        assert "role" in str(exc_info.value).lower() or "attribute" in str(exc_info.value).lower()
    
    def test_user_model_needs_extension(self):
        """
        Test showing that User model needs to be extended with additional fields.
        """
        # What the tests expect
        expected_fields = ['id', 'email', 'name', 'role', 'is_active', 'created_at', 'updated_at']
        
        # What User model actually has
        user = User(id="123", email="test@test.com")
        actual_fields = list(user.model_fields.keys())
        
        # Find missing fields
        missing_fields = [f for f in expected_fields if f not in actual_fields]
        
        # This assertion will fail, showing which fields are missing
        assert len(missing_fields) == 0, f"User model missing fields: {missing_fields}"


class TestAsyncClientInitializationBug:
    """Test AsyncClient initialization problems in E2E tests"""
    
    @pytest.mark.asyncio
    async def test_async_client_proper_initialization(self):
        """
        Test that demonstrates proper AsyncClient initialization.
        Many E2E tests fail due to improper AsyncClient setup.
        """
        from httpx import AsyncClient
        import asyncio
        
        # Common mistake: not using async context manager
        client = AsyncClient()
        
        # This will fail if not properly closed
        try:
            # Attempt to use client without proper context
            response = await client.get("http://localhost:8000/health")
            # Should fail or warn about unclosed client
            pytest.fail("AsyncClient should not work without proper context management")
        except Exception as e:
            # Expected to fail
            pass
        finally:
            await client.aclose()
    
    @pytest.mark.asyncio
    async def test_async_client_context_manager(self):
        """
        Test showing the correct way to use AsyncClient with context manager.
        """
        from httpx import AsyncClient
        
        # Correct way: use async context manager
        async with AsyncClient() as client:
            # Mock the endpoint for testing
            with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json = AsyncMock(return_value={"status": "healthy"})
                
                response = await client.get("http://localhost:8000/health")
                assert response.status_code == 200


class TestImportIssues:
    """Test for import issues with JWTGenerationTestManager"""
    
    def test_jwt_generation_test_manager_import(self):
        """
        Test that JWTGenerationTestManager can be imported.
        This will fail if the import path is incorrect.
        """
        try:
            # Try the import that's failing in tests
            from test_framework.test_managers import JWTGenerationTestManager
            assert JWTGenerationTestManager is not None
        except ImportError as e:
            # This is expected to fail with current import issues
            pytest.fail(f"JWTGenerationTestManager import failed: {e}")
    
    def test_alternative_jwt_manager_import_paths(self):
        """
        Test various possible import paths for JWT test utilities.
        """
        import_attempts = [
            "from test_framework.test_managers import JWTGenerationTestManager",
            "from auth_service.test_framework.test_managers import JWTGenerationTestManager",
            "from tests.test_managers import JWTGenerationTestManager",
            "from auth_core.test_utils import JWTGenerationTestManager"
        ]
        
        successful_import = None
        for import_statement in import_attempts:
            try:
                exec(import_statement)
                successful_import = import_statement
                break
            except ImportError:
                continue
        
        assert successful_import is not None, f"No valid import path found. Tried: {import_attempts}"


if __name__ == "__main__":
    # Run the tests to demonstrate the failures
    pytest.main([__file__, "-v", "--tb=short"])