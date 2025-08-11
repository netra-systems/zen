"""
Comprehensive tests for Tool Registry registration, discovery, and validation
Tests tool registration, dynamic discovery, validation, and metadata management
"""

import pytest
import json
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, patch, call, AsyncMock
from datetime import datetime

from langchain_core.tools import BaseTool
from app.services.tool_registry import ToolRegistry
from app.core.exceptions import NetraException


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
            "created_at": datetime.utcnow().isoformat()
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


class TestToolRegistryDiscovery:
    """Test tool discovery functionality"""
    
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


class TestToolRegistryValidation:
    """Test tool validation functionality"""
    
    @pytest.fixture
    def validator_registry(self, tool_registry):
        """Registry with validation enabled"""
        tool_registry.enable_validation = True
        return tool_registry
    
    def test_tool_interface_validation(self, validator_registry):
        """Test tool interface validation"""
        # Valid tool
        valid_tool = MockTool(name="valid_tool", description="Valid tool description")
        assert validator_registry.validate_tool_interface(valid_tool) is True
        
        # Invalid tool - missing required methods
        invalid_tool = MagicMock()
        invalid_tool.name = "invalid_tool"
        invalid_tool.description = "Invalid tool"
        del invalid_tool._run  # Remove required method
        
        assert validator_registry.validate_tool_interface(invalid_tool) is False
    
    def test_tool_metadata_validation(self, validator_registry):
        """Test tool metadata validation"""
        # Valid metadata
        valid_metadata = {
            "version": "1.0.0",
            "author": "test_author",
            "tags": ["test", "validation"],
            "created_at": datetime.utcnow().isoformat(),
            "dependencies": ["langchain"]
        }
        
        assert validator_registry.validate_metadata(valid_metadata) is True
        
        # Invalid metadata - missing required fields
        invalid_metadata = {
            "tags": ["test"]
            # Missing required fields
        }
        
        assert validator_registry.validate_metadata(invalid_metadata) is False
    
    def test_tool_security_validation(self, validator_registry):
        """Test tool security validation"""
        # Safe tool
        safe_tool = MockTool(name="safe_tool", description="Safe tool")
        assert validator_registry.validate_tool_security(safe_tool) is True
        
        # Potentially unsafe tool
        class UnsafeTool(BaseTool):
            name = "unsafe_tool"
            description = "Tool with file system access"
            
            def _run(self, query: str) -> str:
                import os
                return os.listdir("/")  # File system access
        
        unsafe_tool = UnsafeTool()
        
        # Should fail security validation if strict mode enabled
        validator_registry.strict_security = True
        assert validator_registry.validate_tool_security(unsafe_tool) is False
    
    def test_tool_performance_validation(self, validator_registry):
        """Test tool performance validation"""
        # Setup performance thresholds
        validator_registry.performance_thresholds = {
            "max_execution_time": 5.0,  # seconds
            "max_memory_usage": 100 * 1024 * 1024,  # 100MB
            "max_cpu_usage": 80  # 80%
        }
        
        # Fast tool
        fast_tool = MockTool(name="fast_tool", description="Fast executing tool")
        
        # Mock performance measurement
        with patch.object(validator_registry, 'measure_tool_performance') as mock_measure:
            mock_measure.return_value = {
                "execution_time": 0.5,
                "memory_usage": 10 * 1024 * 1024,  # 10MB
                "cpu_usage": 30
            }
            
            assert validator_registry.validate_tool_performance(fast_tool) is True
        
        # Slow tool
        with patch.object(validator_registry, 'measure_tool_performance') as mock_measure:
            mock_measure.return_value = {
                "execution_time": 10.0,  # Exceeds threshold
                "memory_usage": 50 * 1024 * 1024,
                "cpu_usage": 40
            }
            
            assert validator_registry.validate_tool_performance(fast_tool) is False
    
    def test_tool_compatibility_validation(self, validator_registry):
        """Test tool compatibility validation"""
        # Setup compatibility matrix
        compatibility_matrix = {
            "triage": {
                "compatible_with": ["data", "reporting"],
                "incompatible_with": ["optimizations_core"]
            }
        }
        
        validator_registry.set_compatibility_matrix(compatibility_matrix)
        
        # Compatible tools
        assert validator_registry.validate_compatibility("triage", "data") is True
        assert validator_registry.validate_compatibility("triage", "reporting") is True
        
        # Incompatible tools
        assert validator_registry.validate_compatibility("triage", "optimizations_core") is False
    
    def test_tool_dependency_validation(self, validator_registry):
        """Test tool dependency validation"""
        # Tool with valid dependencies
        tool_with_deps = MockTool(name="dependent_tool", description="Tool with dependencies")
        dependencies = ["numpy", "pandas", "sklearn"]
        
        # Mock dependency check
        with patch.object(validator_registry, 'check_dependencies') as mock_check:
            mock_check.return_value = {"numpy": True, "pandas": True, "sklearn": False}
            
            validation_result = validator_registry.validate_dependencies(tool_with_deps, dependencies)
            
            assert validation_result["valid"] is False
            assert "sklearn" in validation_result["missing_dependencies"]
    
    def test_tool_version_compatibility_validation(self, validator_registry):
        """Test tool version compatibility validation"""
        # Setup version requirements
        version_requirements = {
            "min_python": "3.8",
            "max_python": "3.11",
            "langchain": ">=0.1.0,<1.0.0"
        }
        
        # Mock system version
        with patch('sys.version_info', (3, 9, 0)):
            with patch.object(validator_registry, 'get_package_version') as mock_version:
                mock_version.return_value = "0.5.0"  # langchain version
                
                assert validator_registry.validate_version_compatibility(version_requirements) is True
        
        # Incompatible Python version
        with patch('sys.version_info', (3, 12, 0)):  # Too new
            assert validator_registry.validate_version_compatibility(version_requirements) is False


class TestToolRegistryPerformance:
    """Test performance aspects of tool registry"""
    
    @pytest.mark.asyncio
    async def test_large_scale_tool_registration(self, tool_registry):
        """Test registration performance with large number of tools"""
        import time
        
        # Create many tools
        tools = []
        for i in range(1000):
            tool = MockTool(
                name=f"performance_tool_{i}",
                description=f"Performance test tool number {i}"
            )
            tools.append(("triage", tool))
        
        # Measure registration time
        start_time = time.time()
        
        for category, tool in tools:
            tool_registry.register_tool(category, tool)
        
        registration_time = time.time() - start_time
        
        # Should register 1000 tools in reasonable time (< 5 seconds)
        assert registration_time < 5.0
        
        # Verify all tools registered
        registered_tools = tool_registry.get_tools(["triage"])
        assert len(registered_tools) == 1000
    
    def test_tool_discovery_performance(self, tool_registry):
        """Test discovery performance with many tools"""
        import time
        
        # Register many tools across categories
        for category in ["triage", "data", "optimizations_core"]:
            for i in range(100):
                tool = MockTool(
                    name=f"{category}_tool_{i}",
                    description=f"Tool {i} for {category}"
                )
                tool_registry.register_tool(category, tool)
        
        # Measure discovery time
        start_time = time.time()
        
        # Multiple discovery operations
        for _ in range(10):
            _ = tool_registry.get_tools(["triage", "data"])
            _ = tool_registry.find_tools_by_pattern("*_tool_5*")
            _ = tool_registry.fuzzy_search("tool")
        
        discovery_time = time.time() - start_time
        
        # Should complete discovery operations in reasonable time
        assert discovery_time < 2.0
    
    def test_concurrent_tool_access(self, tool_registry):
        """Test concurrent access to tool registry"""
        import threading
        import time
        
        # Register some tools
        for i in range(50):
            tool = MockTool(name=f"concurrent_tool_{i}", description=f"Tool {i}")
            tool_registry.register_tool("triage", tool)
        
        results = []
        errors = []
        
        def concurrent_access():
            try:
                for _ in range(10):
                    tools = tool_registry.get_tools(["triage"])
                    results.append(len(tools))
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=concurrent_access)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Assert no errors and consistent results
        assert len(errors) == 0
        assert len(results) == 100  # 10 threads * 10 operations
        assert all(result == 50 for result in results)  # Consistent tool count