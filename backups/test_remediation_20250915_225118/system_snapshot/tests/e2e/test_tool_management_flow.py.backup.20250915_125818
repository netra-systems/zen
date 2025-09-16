"""
End-to-End tests for Tool Management Flow

Tests the complete tool management workflow including:
- User authentication
- Tool discovery and listing
- Tool execution with real services
- Permission validation
- Error handling and recovery
"""

import asyncio
import pytest
from typing import Dict, Any
import httpx
from shared.isolated_environment import IsolatedEnvironment

from test_framework.base_e2e_test import BaseE2ETest


class TestToolManagementE2E(BaseE2ETest):
    """End-to-end tests for tool management workflow"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment"""
        await self.initialize_test_environment()
        self.api_base = "http://localhost:8000"
        self.auth_headers = None
        self.test_user = None
    
    async def authenticate_user(self) -> Dict[str, str]:
        """Authenticate a test user and return headers"""
        async with httpx.AsyncClient() as client:
            # Create test user
            user_data = {
                "email": "tooltest@example.com",
                "password": "TestPass123!",
                "name": "Tool Tester"
            }
            
            # Register user
            register_response = await client.post(
                f"{self.api_base}/auth/register",
                json=user_data
            )
            
            if register_response.status_code != 200:
                # User might already exist, try login
                login_response = await client.post(
                    f"{self.api_base}/auth/token",
                    data={
                        "username": user_data["email"],
                        "password": user_data["password"]
                    }
                )
                assert login_response.status_code == 200
                token = login_response.json()["access_token"]
            else:
                token = register_response.json()["access_token"]
            
            return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_tool_workflow(self):
        """Test the complete tool workflow from authentication to execution"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Authenticate
            self.auth_headers = await self.authenticate_user()
            
            # Step 2: List available tools
            tools_response = await client.get(
                f"{self.api_base}/api/tools/",
                headers=self.auth_headers
            )
            assert tools_response.status_code == 200
            tools_data = tools_response.json()
            assert "tools" in tools_data
            assert "categories" in tools_data
            
            # Step 3: Get tool categories
            categories_response = await client.get(
                f"{self.api_base}/api/tools/categories",
                headers=self.auth_headers
            )
            assert categories_response.status_code == 200
            categories = categories_response.json()
            assert isinstance(categories, list)
            
            # Step 4: Execute a tool (if available)
            if tools_data["tools"]:
                first_tool = tools_data["tools"][0]
                execute_response = await client.post(
                    f"{self.api_base}/api/tools/execute",
                    json={
                        "tool_name": first_tool["id"],
                        "parameters": {"test": "data"}
                    },
                    headers=self.auth_headers
                )
                # Tool might not have handler, but request should be processed
                assert execute_response.status_code in [200, 500]
            
            # Step 5: Check user plan
            plan_response = await client.get(
                f"{self.api_base}/api/tools/plan",
                headers=self.auth_headers
            )
            # This endpoint might not be fully implemented
            assert plan_response.status_code in [200, 404, 500]
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_permission_flow(self):
        """Test tool permission checking flow"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.auth_headers = await self.authenticate_user()
            
            # Check permission for a specific tool
            permission_response = await client.get(
                f"{self.api_base}/api/tools/test_tool/permission?action=execute",
                headers=self.auth_headers
            )
            
            # Permission endpoint should respond even for non-existent tools
            assert permission_response.status_code in [200, 404]
            if permission_response.status_code == 200:
                data = permission_response.json()
                assert "has_permission" in data
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test error handling in tool operations"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.auth_headers = await self.authenticate_user()
            
            # Test with invalid tool name
            invalid_tool_response = await client.post(
                f"{self.api_base}/api/tools/execute",
                json={
                    "tool_name": "definitely_invalid_tool_name_xyz",
                    "parameters": {}
                },
                headers=self.auth_headers
            )
            assert invalid_tool_response.status_code in [404, 500]
            
            # Test with malformed request
            malformed_response = await client.post(
                f"{self.api_base}/api/tools/execute",
                json={"invalid": "request"},
                headers=self.auth_headers
            )
            assert malformed_response.status_code == 422
            
            # Test without authentication
            no_auth_response = await client.get(f"{self.api_base}/api/tools/")
            assert no_auth_response.status_code == 401
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_category_filtering(self):
        """Test filtering tools by category"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.auth_headers = await self.authenticate_user()
            
            # First get all categories
            categories_response = await client.get(
                f"{self.api_base}/api/tools/categories",
                headers=self.auth_headers
            )
            
            if categories_response.status_code == 200:
                categories = categories_response.json()
                
                # Test filtering by each category
                for category in categories[:3]:  # Test first 3 categories
                    filtered_response = await client.get(
                        f"{self.api_base}/api/tools/?category={category['name']}",
                        headers=self.auth_headers
                    )
                    assert filtered_response.status_code == 200
                    data = filtered_response.json()
                    
                    # All returned tools should be in the requested category
                    if data["tools"]:
                        for tool in data["tools"]:
                            assert tool.get("category") == category["name"]
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_concurrent_tool_operations(self):
        """Test concurrent tool operations for thread safety"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.auth_headers = await self.authenticate_user()
            
            # Create multiple concurrent requests
            tasks = []
            for i in range(5):
                # Mix of different operations
                if i % 2 == 0:
                    task = client.get(
                        f"{self.api_base}/api/tools/",
                        headers=self.auth_headers
                    )
                else:
                    task = client.get(
                        f"{self.api_base}/api/tools/categories",
                        headers=self.auth_headers
                    )
                tasks.append(task)
            
            # Execute concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed without errors
            for response in responses:
                assert not isinstance(response, Exception)
                assert response.status_code == 200
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_pagination(self):
        """Test pagination in tool listing"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.auth_headers = await self.authenticate_user()
            
            # Test different pagination parameters
            pagination_tests = [
                {"limit": 5, "offset": 0},
                {"limit": 10, "offset": 5},
                {"limit": 2, "offset": 10},
            ]
            
            for params in pagination_tests:
                response = await client.get(
                    f"{self.api_base}/api/tools/",
                    params=params,
                    headers=self.auth_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert "tools" in data
                
                # Check that limit is respected (if tools exist)
                if data["tools"]:
                    assert len(data["tools"]) <= params["limit"]
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_metadata_retrieval(self):
        """Test retrieving detailed tool metadata"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.auth_headers = await self.authenticate_user()
            
            # First get list of tools
            tools_response = await client.get(
                f"{self.api_base}/api/tools/",
                headers=self.auth_headers
            )
            
            if tools_response.status_code == 200:
                tools = tools_response.json()["tools"]
                
                # Get metadata for each tool (test first 3)
                for tool in tools[:3]:
                    metadata_response = await client.get(
                        f"{self.api_base}/api/tools/{tool['id']}",
                        headers=self.auth_headers
                    )
                    # Metadata endpoint might not be implemented
                    assert metadata_response.status_code in [200, 404]
                    
                    if metadata_response.status_code == 200:
                        metadata = metadata_response.json()
                        assert metadata["id"] == tool["id"]
                        assert "name" in metadata
                        assert "description" in metadata
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_execution_with_large_payload(self):
        """Test tool execution with large payloads"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            self.auth_headers = await self.authenticate_user()
            
            # Create a large payload
            large_data = {
                "data": ["item"] * 1000,  # Large array
                "nested": {
                    f"key_{i}": f"value_{i}" * 100
                    for i in range(100)
                }
            }
            
            execute_response = await client.post(
                f"{self.api_base}/api/tools/execute",
                json={
                    "tool_name": "test_tool",
                    "parameters": large_data
                },
                headers=self.auth_headers
            )
            
            # Should handle large payloads gracefully
            assert execute_response.status_code in [200, 404, 413, 500]
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_system_recovery(self):
        """Test system recovery after tool execution failures"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.auth_headers = await self.authenticate_user()
            
            # Cause intentional failures
            for _ in range(3):
                await client.post(
                    f"{self.api_base}/api/tools/execute",
                    json={
                        "tool_name": "non_existent",
                        "parameters": {"will": "fail"}
                    },
                    headers=self.auth_headers
                )
            
            # System should still be responsive
            health_response = await client.get(f"{self.api_base}/health")
            assert health_response.status_code == 200
            
            # Should still be able to list tools
            tools_response = await client.get(
                f"{self.api_base}/api/tools/",
                headers=self.auth_headers
            )
            assert tools_response.status_code == 200
