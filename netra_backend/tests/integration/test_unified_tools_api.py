"""
Integration tests for Unified Tools API

Tests the API endpoints for tool management including:
- Listing available tools
- Getting tool categories
- Executing tools
- Permission checking
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from netra_backend.app.main import app
from netra_backend.app.db.models_postgres import User
from netra_backend.app.services.unified_tool_registry import UnifiedTool
from netra_backend.tests.test_utils import create_test_user, create_test_token


@pytest.mark.asyncio
class TestUnifiedToolsAPI:
    """Test unified tools API endpoints"""
    
    @pytest.fixture
    async def client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    async def auth_headers(self, test_db):
        """Create authenticated headers"""
        user = await create_test_user(test_db, email="test@example.com")
        token = create_test_token(user.id)
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def mock_registry(self):
        """Create mock tool registry with sample tools"""
        with patch("netra_backend.app.routes.unified_tools.router.tool_registry") as mock:
            # Setup sample tools
            tools = [
                UnifiedTool(
                    id="analyzer",
                    name="Data Analyzer",
                    description="Analyzes data",
                    category="analysis",
                    version="1.0.0"
                ),
                UnifiedTool(
                    id="optimizer",
                    name="Cost Optimizer", 
                    description="Optimizes costs",
                    category="optimization",
                    version="1.0.0"
                ),
                UnifiedTool(
                    id="reporter",
                    name="Report Generator",
                    description="Generates reports",
                    category="reporting",
                    version="1.0.0"
                )
            ]
            
            mock.list_tools.return_value = tools
            mock.get_tool.side_effect = lambda id: next((t for t in tools if t.id == id), None)
            mock.get_tool_categories.return_value = [
                {"name": "analysis", "count": 1, "description": "Analysis tools"},
                {"name": "optimization", "count": 1, "description": "Optimization tools"},
                {"name": "reporting", "count": 1, "description": "Reporting tools"}
            ]
            
            yield mock
    
    async def test_list_tools_unauthenticated(self, client):
        """Test listing tools without authentication fails"""
        response = await client.get("/api/tools/")
        assert response.status_code == 401
    
    async def test_list_tools_authenticated(self, client, auth_headers, mock_registry):
        """Test listing all available tools"""
        response = await client.get("/api/tools/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "tools" in data
        assert "categories" in data
        assert "tools_count" in data
        assert data["tools_count"] == 3
    
    async def test_list_tools_with_category_filter(self, client, auth_headers, mock_registry):
        """Test listing tools filtered by category"""
        mock_registry.list_tools.return_value = [
            UnifiedTool(
                id="analyzer",
                name="Data Analyzer",
                description="Analyzes data",
                category="analysis",
                version="1.0.0"
            )
        ]
        
        response = await client.get("/api/tools/?category=analysis", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["tools_count"] == 1
        assert data["tools"][0]["category"] == "analysis"
    
    async def test_get_tool_categories(self, client, auth_headers, mock_registry):
        """Test getting tool categories endpoint"""
        response = await client.get("/api/tools/categories", headers=auth_headers)
        assert response.status_code == 200
        
        categories = response.json()
        assert len(categories) == 3
        assert any(c["name"] == "analysis" for c in categories)
        assert any(c["name"] == "optimization" for c in categories)
        assert any(c["name"] == "reporting" for c in categories)
    
    async def test_execute_tool_success(self, client, auth_headers, mock_registry):
        """Test successful tool execution"""
        mock_registry.execute_tool = AsyncMock(return_value={
            "success": True,
            "result": {"data": "processed"},
            "error": None
        })
        
        request_data = {
            "tool_name": "analyzer",
            "parameters": {"input": "test data"}
        }
        
        response = await client.post(
            "/api/tools/execute",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        assert result["result"]["data"] == "processed"
    
    async def test_execute_tool_not_found(self, client, auth_headers, mock_registry):
        """Test executing non-existent tool"""
        mock_registry.get_tool.return_value = None
        
        request_data = {
            "tool_name": "non_existent",
            "parameters": {}
        }
        
        response = await client.post(
            "/api/tools/execute",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    async def test_execute_tool_permission_denied(self, client, auth_headers, mock_registry):
        """Test tool execution with insufficient permissions"""
        mock_registry.check_permission.return_value = False
        
        request_data = {
            "tool_name": "analyzer",
            "parameters": {}
        }
        
        response = await client.post(
            "/api/tools/execute",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()
    
    async def test_execute_tool_invalid_parameters(self, client, auth_headers):
        """Test tool execution with invalid parameters"""
        request_data = {
            "tool_name": "analyzer"
            # Missing required 'parameters' field
        }
        
        response = await client.post(
            "/api/tools/execute",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 422
    
    async def test_check_tool_permission(self, client, auth_headers, mock_registry):
        """Test checking permission for a tool"""
        mock_registry.check_permission.return_value = True
        
        response = await client.get(
            "/api/tools/analyzer/permission?action=execute",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["has_permission"] is True
        assert data["tool_id"] == "analyzer"
        assert data["action"] == "execute"
    
    async def test_get_user_plan_info(self, client, auth_headers):
        """Test getting user plan information"""
        with patch("netra_backend.app.routes.unified_tools.router.gather_user_plan_data") as mock_gather:
            mock_gather.return_value = {
                "plan": "professional",
                "tool_limit": 50,
                "tools_used": 10,
                "features": ["analysis", "optimization", "reporting"]
            }
            
            response = await client.get("/api/tools/plan", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["plan"] == "professional"
            assert data["tool_limit"] == 50
            assert data["tools_used"] == 10
    
    async def test_migrate_tools(self, client, auth_headers):
        """Test tool migration endpoint"""
        with patch("netra_backend.app.routes.unified_tools.router.process_migration_request") as mock_migrate:
            mock_migrate.return_value = {
                "migrated": 5,
                "failed": 0,
                "status": "completed"
            }
            
            response = await client.post(
                "/api/tools/migrate",
                json={"source": "legacy", "dry_run": False},
                headers=auth_headers
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["migrated"] == 5
            assert data["status"] == "completed"
    
    async def test_list_tools_with_pagination(self, client, auth_headers, mock_registry):
        """Test listing tools with pagination parameters"""
        response = await client.get(
            "/api/tools/?limit=2&offset=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        # Even though we request pagination, the mock returns all tools
        # In real implementation, pagination would be handled
        assert "tools" in data
    
    async def test_tool_execution_with_context(self, client, auth_headers, mock_registry):
        """Test tool execution with additional context"""
        mock_registry.execute_tool = AsyncMock(return_value={
            "success": True,
            "result": {"processed": True},
            "error": None
        })
        
        request_data = {
            "tool_name": "analyzer",
            "parameters": {"input": "data"},
            "context": {
                "request_id": "123",
                "user_preferences": {"output_format": "json"}
            }
        }
        
        response = await client.post(
            "/api/tools/execute",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify context was passed to execute_tool
        mock_registry.execute_tool.assert_called_once()
        call_args = mock_registry.execute_tool.call_args[0]
        assert call_args[0] == "analyzer"
        assert call_args[1] == {"input": "data"}
        assert "context" in call_args or len(call_args) > 2
    
    async def test_get_tool_metadata(self, client, auth_headers, mock_registry):
        """Test getting detailed tool metadata"""
        tool = UnifiedTool(
            id="analyzer",
            name="Data Analyzer",
            description="Comprehensive data analysis tool",
            category="analysis",
            version="1.0.0"
        )
        mock_registry.get_tool.return_value = tool
        
        response = await client.get("/api/tools/analyzer", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "analyzer"
        assert data["name"] == "Data Analyzer"
        assert data["version"] == "1.0.0"
    
    async def test_bulk_tool_execution(self, client, auth_headers, mock_registry):
        """Test executing multiple tools in bulk"""
        mock_registry.execute_tool = AsyncMock(side_effect=[
            {"success": True, "result": {"tool": "analyzer", "data": "result1"}},
            {"success": True, "result": {"tool": "optimizer", "data": "result2"}},
            {"success": False, "error": "Tool failed"}
        ])
        
        request_data = {
            "executions": [
                {"tool_name": "analyzer", "parameters": {"input": "data1"}},
                {"tool_name": "optimizer", "parameters": {"input": "data2"}},
                {"tool_name": "reporter", "parameters": {"input": "data3"}}
            ]
        }
        
        response = await client.post(
            "/api/tools/execute/bulk",
            json=request_data,
            headers=auth_headers
        )
        assert response.status_code == 207  # Multi-status
        
        results = response.json()["results"]
        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is True
        assert results[2]["success"] is False