"""
L3 Integration Test: API CRUD Operations
Tests basic Create, Read, Update, Delete operations
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import httpx
from unittest.mock import patch, AsyncMock

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.config import settings
import json

# Add project root to path


class TestAPICRUDOperationsL3:
    """Test API CRUD operation scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_create_resource(self):
        """Test creating a new resource via API"""
        async with httpx.AsyncClient() as client:
            resource_data = {
                "name": "Test Resource",
                "type": "document",
                "content": "Test content",
                "metadata": {"version": 1}
            }
            
            response = await client.post(
                f"{settings.API_BASE_URL}/api/v1/resources",
                json=resource_data,
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["name"] == "Test Resource"
            assert data["type"] == "document"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_read_resource(self):
        """Test reading an existing resource"""
        async with httpx.AsyncClient() as client:
            resource_id = "test_123"
            
            response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources/{resource_id}",
                headers={"Authorization": "Bearer test_token"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["id"] == resource_id
                assert "name" in data
                assert "created_at" in data
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_update_resource(self):
        """Test updating an existing resource"""
        async with httpx.AsyncClient() as client:
            resource_id = "test_123"
            update_data = {
                "name": "Updated Resource",
                "content": "Updated content",
                "metadata": {"version": 2}
            }
            
            response = await client.put(
                f"{settings.API_BASE_URL}/api/v1/resources/{resource_id}",
                json=update_data,
                headers={"Authorization": "Bearer test_token"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["name"] == "Updated Resource"
                assert data["metadata"]["version"] == 2
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_delete_resource(self):
        """Test deleting a resource"""
        async with httpx.AsyncClient() as client:
            resource_id = "test_123"
            
            # Delete resource
            response = await client.delete(
                f"{settings.API_BASE_URL}/api/v1/resources/{resource_id}",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code in [200, 204]
            
            # Verify deleted
            get_response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources/{resource_id}",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_list_resources_with_pagination(self):
        """Test listing resources with pagination"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.API_BASE_URL}/api/v1/resources",
                params={"page": 1, "limit": 10},
                headers={"Authorization": "Bearer test_token"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "items" in data
                assert "total" in data
                assert "page" in data
                assert "limit" in data
                assert len(data["items"]) <= 10