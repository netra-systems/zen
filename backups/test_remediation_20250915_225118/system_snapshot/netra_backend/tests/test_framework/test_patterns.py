from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Test patterns and base classes for integration tests."""

import os
import asyncio
import pytest
from typing import Any, Dict, Optional
import aiohttp
from pathlib import Path
import sys

# Add parent directories to path

class L3IntegrationTest:
    """Base class for L3 integration tests."""
    
    backend_url = get_env().get("BACKEND_URL", "http://localhost:8080")
    auth_url = get_env().get("AUTH_URL", "http://localhost:8081")
    
    @classmethod
    def setup_class(cls):
        """Setup test class."""
        pass
    
    @classmethod
    def teardown_class(cls):
        """Teardown test class."""
        pass
    
    async def create_test_user(self, email: str, **kwargs) -> Dict[str, Any]:
        """Create a test user."""
        user_data = {
            "email": email,
            "password": "test_password123",
            "username": email.split("@")[0],
            **kwargs
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.auth_url}/auth/register",
                json=user_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    # User might already exist, try login
                    return user_data
    
    async def get_auth_token(self, user_data: Dict[str, Any]) -> str:
        """Get authentication token for user."""
        login_data = {
            "email": user_data.get("email"),
            "password": user_data.get("password", "test_password123")
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.auth_url}/auth/login",
                json=login_data
            ) as response:
                data = await response.json()
                return data.get("access_token", "")
    
    async def cleanup_test_data(self, user_id: Optional[str] = None):
        """Cleanup test data."""
        # Implementation depends on your cleanup needs
        pass

class IntegrationTestBase:
    """Base class for integration tests."""
    
    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Setup
        yield
        # Teardown
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Cleanup test data after test."""
        pass
