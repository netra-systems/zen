"""
Tool Registry Discovery Tests
Tests tool discovery and search functionality
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from langchain_core.tools import BaseTool

from netra_backend.app.services.tool_registry import ToolRegistry
from netra_backend.tests.test_tool_registry_registration_core import MockTool

class TestToolRegistryDiscovery:
    """Test tool discovery functionality"""
    
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
    
    @pytest.fixture
    def populated_registry(self, tool_registry, sample_tools):
        """Registry populated with sample tools"""
        for category, tools in sample_tools.items():
            for tool in tools:
                tool_registry.register_tool(category, tool)
        return tool_registry
    
    def test_discover_tools_by_category(self, populated_registry):
        """Test discovering tools by category"""
        # Test single category
        triage_tools = populated_registry.get_tools(["triage"])
        assert len(triage_tools) == 2
        assert all(tool.name in ["classification_tool", "priority_tool"] for tool in triage_tools)
        
        # Test multiple categories
        multi_tools = populated_registry.get_tools(["triage", "data"])
        assert len(multi_tools) == 4
    
    def test_discover_tools_by_name_pattern(self, populated_registry):
        """Test discovering tools by name pattern"""
        # Search for tools with "tool" in name
        matching_tools = populated_registry.find_tools_by_pattern("*_tool")
        assert len(matching_tools) >= 6  # All sample tools end with "_tool"
        
        # Search for specific pattern
        analyzer_tools = populated_registry.find_tools_by_pattern("analyzer*")
        assert len(analyzer_tools) == 1
        assert analyzer_tools[0].name == "analyzer_tool"
    
    def test_discover_tools_by_tags(self, populated_registry):
        """Test discovering tools by tags/metadata"""
        # Add tags to some tools
        populated_registry.add_tool_tags("triage", "classification_tool", ["ai", "classification"])
        populated_registry.add_tool_tags("data", "analyzer_tool", ["analysis", "data"])
        populated_registry.add_tool_tags("optimizations_core", "performance_tool", ["optimization", "performance"])
        
        # Search by single tag
        ai_tools = populated_registry.find_tools_by_tag("ai")
        assert len(ai_tools) == 1
        assert ai_tools[0].name == "classification_tool"
        
        # Search by multiple tags
        analysis_tools = populated_registry.find_tools_by_tags(["analysis", "optimization"])
        assert len(analysis_tools) == 2
    
    def test_discover_tools_by_capability(self, populated_registry):
        """Test discovering tools by capability"""
        # Setup capabilities
        capabilities = {
            "classification_tool": ["text_analysis", "categorization"],
            "analyzer_tool": ["data_processing", "statistical_analysis"],
            "performance_tool": ["optimization", "monitoring"]
        }
        
        for category, tools in populated_registry._tool_configs.items():
            for tool in tools:
                if tool.name in capabilities:
                    populated_registry.add_tool_capabilities(
                        category, tool.name, capabilities[tool.name]
                    )
        
        # Search by capability
        analysis_capable = populated_registry.find_tools_by_capability("data_processing")
        assert len(analysis_capable) == 1
        assert analysis_capable[0].name == "analyzer_tool"
    
    def test_discover_compatible_tools(self, populated_registry):
        """Test discovering tools compatible with input/output types"""
        # Setup input/output specifications
        populated_registry.set_tool_io_spec("triage", "classification_tool", {
            "input_type": "str",
            "output_type": "dict",
            "input_schema": {"message": "str"}
        })
        
        populated_registry.set_tool_io_spec("data", "transformer_tool", {
            "input_type": "dict",
            "output_type": "list",
            "input_schema": {"data": "dict"}
        })
        
        # Find tools that can chain together
        compatible_chain = populated_registry.find_compatible_chain(
            start_type="str", end_type="list"
        )
        
        assert len(compatible_chain) >= 1
        assert compatible_chain[0]["from_tool"] == "classification_tool"
        assert compatible_chain[0]["to_tool"] == "transformer_tool"
    
    def test_discover_tools_fuzzy_search(self, populated_registry):
        """Test fuzzy search for tool discovery"""
        # Test fuzzy name matching
        fuzzy_results = populated_registry.fuzzy_search("classifi")  # Partial match
        assert len(fuzzy_results) >= 1
        assert any("classification" in result["tool"].name.lower() for result in fuzzy_results)
        
        # Test description fuzzy matching
        desc_results = populated_registry.fuzzy_search_description("analyze")
        assert len(desc_results) >= 1
        assert any("analyz" in result["tool"].description.lower() for result in desc_results)
    
    def test_discover_recently_used_tools(self, populated_registry):
        """Test discovering recently used tools"""
        # Simulate tool usage
        classification_tool = populated_registry.get_tool_by_name("classification_tool")
        analyzer_tool = populated_registry.get_tool_by_name("analyzer_tool")
        
        populated_registry.record_tool_usage("classification_tool", "user_123")
        populated_registry.record_tool_usage("analyzer_tool", "user_123")
        populated_registry.record_tool_usage("classification_tool", "user_456")
        
        # Get recently used tools
        recent_tools = populated_registry.get_recently_used_tools("user_123", limit=5)
        assert len(recent_tools) == 2
        assert recent_tools[0]["tool_name"] == "analyzer_tool"  # Most recent first
        
        # Get popular tools across all users
        popular_tools = populated_registry.get_popular_tools(limit=3)
        assert len(popular_tools) >= 1
        assert popular_tools[0]["tool_name"] == "classification_tool"  # Most used
    
    def test_tool_recommendation_engine(self, populated_registry):
        """Test tool recommendation based on context"""
        # Setup user preferences and history
        user_context = {
            "user_id": "user_123",
            "current_task": "data_analysis",
            "recent_tools": ["classification_tool"],
            "preferences": {"category": "data", "complexity": "medium"}
        }
        
        # Get recommendations
        recommendations = populated_registry.recommend_tools(user_context, limit=3)
        
        assert len(recommendations) <= 3
        assert all("score" in rec for rec in recommendations)
        assert all(rec["score"] > 0 for rec in recommendations)
        
        # Data category tools should be recommended higher for data_analysis task
        data_tools = [rec for rec in recommendations if rec["category"] == "data"]
        assert len(data_tools) >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])