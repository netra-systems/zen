"""
Core Tool Registry Registration Tests
Tests basic tool registration functionality
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import json
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, patch, call, AsyncMock
from datetime import datetime, UTC

from langchain_core.tools import BaseTool

# Add project root to path

from netra_backend.app.services.tool_registry import ToolRegistry
from netra_backend.app.core.exceptions_base import NetraException

# Add project root to path


class MockTool(BaseTool):
    """Mock tool for testing"""
    name: str = "mock_tool"
    description: str = "Mock tool for testing"
    
    def __init__(self, name: str = "mock_tool", description: str = "Mock tool", **kwargs):
        super().__init__(name=name, description=description, **kwargs)
        self.call_count = 0
        self.last_input = None
    
    def _run(self, query: str) -> str:
        self.call_count += 1
        self.last_input = query
        return f"Mock result for: {query}"
    
    async def _arun(self, query: str) -> str:
        return self._run(query)


class TestToolRegistryRegistration:
    """Test tool registration functionality"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return MagicMock()
    
    @pytest.fixture
    def tool_registry(self, mock_db_session):
        """Create tool registry with mocked dependencies"""
        return ToolRegistry(mock_db_session)
    
    @pytest.fixture
    def sample_tools(self):
        """Create sample tools for testing"""
        return {
            "triage": [
                MockTool(name="classification_tool", description="Classifies messages"),
                MockTool(name="priority_tool", description="Assigns priorities")
            ],
            "data": [
                MockTool(name="analyzer_tool", description="Analyzes data"),
                MockTool(name="transformer_tool", description="Transforms data")
            ],
            "optimizations_core": [
                MockTool(name="performance_tool", description="Optimizes performance"),
                MockTool(name="cost_tool", description="Reduces costs")
            ]
        }
    
    def test_register_single_tool(self, tool_registry):
        """Test registering a single tool"""
        # Setup
        tool = MockTool(name="test_tool", description="Test tool")
        category = "triage"
        
        # Execute
        tool_registry.register_tool(category, tool)
        
        # Assert
        registered_tools = tool_registry.get_tools([category])
        assert len(registered_tools) == 1
        assert registered_tools[0].name == "test_tool"
    
    def test_register_multiple_tools_same_category(self, tool_registry):
        """Test registering multiple tools in same category"""
        # Setup
        tools = [
            MockTool(name="tool_1", description="First tool"),
            MockTool(name="tool_2", description="Second tool"),
            MockTool(name="tool_3", description="Third tool")
        ]
        category = "data"
        
        # Execute
        for tool in tools:
            tool_registry.register_tool(category, tool)
        
        # Assert
        registered_tools = tool_registry.get_tools([category])
        assert len(registered_tools) == 3
        assert {tool.name for tool in registered_tools} == {"tool_1", "tool_2", "tool_3"}
    
    def test_register_tools_multiple_categories(self, tool_registry, sample_tools):
        """Test registering tools across multiple categories"""
        # Setup & Execute
        for category, tools in sample_tools.items():
            for tool in tools:
                tool_registry.register_tool(category, tool)
        
        # Assert
        for category, expected_tools in sample_tools.items():
            registered_tools = tool_registry.get_tools([category])
            assert len(registered_tools) == len(expected_tools)
            
            registered_names = {tool.name for tool in registered_tools}
            expected_names = {tool.name for tool in expected_tools}
            assert registered_names == expected_names
    
    def test_register_tool_with_metadata(self, tool_registry):
        """Test registering tool with additional metadata"""
        # Setup
        tool = MockTool(name="metadata_tool", description="Tool with metadata")
        category = "optimizations_core"
        metadata = {
            "version": "1.0.0",
            "author": "test",
            "tags": ["optimization", "performance"],
            "created_at": datetime.now(UTC).isoformat()
        }
        
        # Execute
        tool_registry.register_tool_with_metadata(category, tool, metadata)
        
        # Assert
        tool_info = tool_registry.get_tool_info(category, "metadata_tool")
        assert tool_info["metadata"]["version"] == "1.0.0"
        assert tool_info["metadata"]["author"] == "test"
        assert "optimization" in tool_info["metadata"]["tags"]
    
    def test_register_duplicate_tool_handling(self, tool_registry):
        """Test handling of duplicate tool registration"""
        # Setup
        tool1 = MockTool(name="duplicate_tool", description="First instance")
        tool2 = MockTool(name="duplicate_tool", description="Second instance")
        category = "triage"
        
        # Execute
        tool_registry.register_tool(category, tool1)
        
        # Should either replace or raise exception based on policy
        with pytest.raises(NetraException) as exc_info:
            tool_registry.register_tool(category, tool2, allow_duplicates=False)
        
        assert "already registered" in str(exc_info.value).lower()
    
    def test_register_tool_validation_failure(self, tool_registry):
        """Test tool registration with validation failure"""
        # Setup
        invalid_tool = MagicMock()
        invalid_tool.name = ""  # Invalid empty name
        invalid_tool.description = "Valid description"
        
        # Execute & Assert
        with pytest.raises(NetraException) as exc_info:
            tool_registry.register_tool("data", invalid_tool)
        
        assert "validation" in str(exc_info.value).lower()
    
    def test_register_tool_invalid_category(self, tool_registry):
        """Test registering tool in invalid category"""
        # Setup
        tool = MockTool(name="valid_tool", description="Valid tool")
        invalid_category = "non_existent_category"
        
        # Execute & Assert
        with pytest.raises(NetraException) as exc_info:
            tool_registry.register_tool(invalid_category, tool)
        
        assert "invalid category" in str(exc_info.value).lower()
    
    def test_bulk_tool_registration(self, tool_registry, sample_tools):
        """Test bulk registration of multiple tools"""
        # Execute
        tool_registry.bulk_register_tools(sample_tools)
        
        # Assert
        all_categories = list(sample_tools.keys())
        all_registered_tools = tool_registry.get_tools(all_categories)
        
        expected_count = sum(len(tools) for tools in sample_tools.values())
        assert len(all_registered_tools) == expected_count
    
    def test_tool_registration_rollback_on_error(self, tool_registry):
        """Test rollback behavior when registration fails"""
        # Setup
        valid_tools = [
            MockTool(name="tool_1", description="Valid tool 1"),
            MockTool(name="tool_2", description="Valid tool 2")
        ]
        invalid_tool = MagicMock()
        invalid_tool.name = ""  # Invalid
        
        tools_to_register = valid_tools + [invalid_tool]
        
        # Execute - should fail and rollback
        with pytest.raises(NetraException):
            tool_registry.bulk_register_tools({"triage": tools_to_register}, atomic=True)
        
        # Assert - no tools should be registered due to rollback
        registered_tools = tool_registry.get_tools(["triage"])
        assert len(registered_tools) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])