"""
Unit tests for UnifiedToolRegistry

Tests the core functionality of the tool registry including:
- Tool registration and retrieval
- Category management
- Permission checking
- Tool execution
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.unified_tool_registry import (
    UnifiedToolRegistry,
    UnifiedTool,
    ToolExecutionResult
)


class TestUnifiedToolRegistry:
    """Test UnifiedToolRegistry core functionality"""
    
    @pytest.fixture
    def registry(self):
        """Create a registry instance for testing"""
        return UnifiedToolRegistry()
    
    @pytest.fixture
    def sample_tool(self):
        """Create a sample tool for testing"""
        return UnifiedTool(
            id="test_tool",
            name="Test Tool",
            description="A test tool",
            category="testing",
            version="1.0.0"
        )
    
    @pytest.fixture
    def sample_handler(self):
        """Create a sample async handler"""
        handler = AsyncMock()
        handler.return_value = {"status": "success", "data": "test"}
        return handler
    
    def test_register_tool(self, registry, sample_tool):
        """Test registering a tool in the registry"""
        registry.register_tool(sample_tool)
        
        assert "test_tool" in registry._tools
        assert registry._tools["test_tool"] == sample_tool
    
    def test_register_tool_with_handler(self, registry, sample_tool, sample_handler):
        """Test registering a tool with an execution handler"""
        registry.register_tool(sample_tool, sample_handler)
        
        assert "test_tool" in registry._tools
        assert "test_tool" in registry._tool_handlers
        assert registry._tool_handlers["test_tool"] == sample_handler
    
    def test_get_tool(self, registry, sample_tool):
        """Test retrieving a tool by ID"""
        registry.register_tool(sample_tool)
        
        retrieved = registry.get_tool("test_tool")
        assert retrieved == sample_tool
    
    def test_get_tool_not_found(self, registry):
        """Test retrieving a non-existent tool returns None"""
        retrieved = registry.get_tool("non_existent")
        assert retrieved is None
    
    def test_list_tools_empty(self, registry):
        """Test listing tools when registry is empty"""
        tools = registry.list_tools()
        assert tools == []
    
    def test_list_tools_with_category_filter(self, registry):
        """Test listing tools filtered by category"""
        tool1 = UnifiedTool(
            id="tool1", name="Tool 1", description="", category="cat1", version="1.0"
        )
        tool2 = UnifiedTool(
            id="tool2", name="Tool 2", description="", category="cat2", version="1.0"
        )
        tool3 = UnifiedTool(
            id="tool3", name="Tool 3", description="", category="cat1", version="1.0"
        )
        
        registry.register_tool(tool1)
        registry.register_tool(tool2)
        registry.register_tool(tool3)
        
        cat1_tools = registry.list_tools(category="cat1")
        assert len(cat1_tools) == 2
        assert all(t.category == "cat1" for t in cat1_tools)
    
    def test_get_tool_categories_empty(self, registry):
        """Test getting categories when registry is empty"""
        categories = registry.get_tool_categories()
        assert categories == []
    
    def test_get_tool_categories_with_tools(self, registry):
        """Test getting categories with registered tools"""
        tool1 = UnifiedTool(
            id="tool1", name="Tool 1", description="", category="analysis", version="1.0"
        )
        tool2 = UnifiedTool(
            id="tool2", name="Tool 2", description="", category="optimization", version="1.0"
        )
        tool3 = UnifiedTool(
            id="tool3", name="Tool 3", description="", category="analysis", version="1.0"
        )
        
        registry.register_tool(tool1)
        registry.register_tool(tool2)
        registry.register_tool(tool3)
        
        categories = registry.get_tool_categories()
        assert len(categories) == 2
        
        analysis_cat = next(c for c in categories if c["name"] == "analysis")
        assert analysis_cat["count"] == 2
        assert "Analysis tools" in analysis_cat["description"]
        
        optimization_cat = next(c for c in categories if c["name"] == "optimization")
        assert optimization_cat["count"] == 1
    
    def test_get_tool_categories_handles_missing_category(self, registry):
        """Test handling tools without category attribute"""
        # Create a mock tool without category attribute
        tool_without_category = MagicMock()
        tool_without_category.id = "no_cat_tool"
        del tool_without_category.category  # Ensure category doesn't exist
        
        registry._tools["no_cat_tool"] = tool_without_category
        
        categories = registry.get_tool_categories()
        assert len(categories) == 1
        assert categories[0]["name"] == "default"
        assert categories[0]["count"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, registry, sample_tool, sample_handler):
        """Test successful tool execution"""
        registry.register_tool(sample_tool, sample_handler)
        
        result = await registry.execute_tool(
            "test_tool",
            {"param1": "value1"},
            {"user": "test_user"}
        )
        
        assert result.success is True
        assert result.result == {"status": "success", "data": "test"}
        assert result.error is None
        sample_handler.assert_called_once_with(
            {"param1": "value1"},
            {"user": "test_user"}
        )
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, registry):
        """Test executing non-existent tool"""
        result = await registry.execute_tool(
            "non_existent",
            {},
            {}
        )
        
        assert result.success is False
        assert result.error == "Tool non_existent not found"
        assert result.result is None
    
    @pytest.mark.asyncio
    async def test_execute_tool_no_handler(self, registry, sample_tool):
        """Test executing tool without handler"""
        registry.register_tool(sample_tool)  # Register without handler
        
        result = await registry.execute_tool(
            "test_tool",
            {},
            {}
        )
        
        assert result.success is False
        assert result.error == "No handler registered for tool test_tool"
    
    @pytest.mark.asyncio
    async def test_execute_tool_handler_exception(self, registry, sample_tool):
        """Test tool execution when handler raises exception"""
        failing_handler = AsyncMock(side_effect=Exception("Handler failed"))
        registry.register_tool(sample_tool, failing_handler)
        
        result = await registry.execute_tool(
            "test_tool",
            {},
            {}
        )
        
        assert result.success is False
        assert "Handler failed" in result.error
    
    def test_check_permission_tool_not_found(self, registry):
        """Test permission check for non-existent tool"""
        has_permission = registry.check_permission(
            "non_existent",
            "user123",
            "execute"
        )
        assert has_permission is False
    
    def test_check_permission_always_true(self, registry, sample_tool):
        """Test permission check currently always returns True for existing tools"""
        registry.register_tool(sample_tool)
        
        has_permission = registry.check_permission(
            "test_tool",
            "user123",
            "execute"
        )
        assert has_permission is True
    
    def test_clear_registry(self, registry, sample_tool, sample_handler):
        """Test clearing the registry"""
        registry.register_tool(sample_tool, sample_handler)
        assert len(registry._tools) == 1
        assert len(registry._tool_handlers) == 1
        
        registry.clear()
        
        assert len(registry._tools) == 0
        assert len(registry._tool_handlers) == 0
    
    def test_multiple_tools_registration(self, registry):
        """Test registering multiple tools"""
        tools = []
        for i in range(5):
            tool = UnifiedTool(
                id=f"tool_{i}",
                name=f"Tool {i}",
                description=f"Description {i}",
                category=f"cat_{i % 2}",  # Alternate between 2 categories
                version="1.0.0"
            )
            tools.append(tool)
            registry.register_tool(tool)
        
        assert len(registry._tools) == 5
        all_tools = registry.list_tools()
        assert len(all_tools) == 5
        
        categories = registry.get_tool_categories()
        assert len(categories) == 2
        assert sum(c["count"] for c in categories) == 5