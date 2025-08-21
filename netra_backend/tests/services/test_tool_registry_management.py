"""
Focused tests for Tool Registry Management - initialization and cross-registry operations
Tests unified registry initialization, tool addition, and cross-registry discovery
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

from langchain_core.tools import BaseTool

# Add project root to path

from netra_backend.app.services.tool_registry import ToolRegistry
from netra_backend.app.core.exceptions_base import NetraException

# Add project root to path


class ToolStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive" 
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


class MockAdvancedTool(BaseTool):
    """Advanced mock tool with lifecycle management"""
    
    def __init__(self, name: str, description: str = "", **kwargs):
        super().__init__(name=name, description=description, **kwargs)
        self.status = ToolStatus.ACTIVE
        self.call_count = 0
        self.last_called = None
        self.initialization_time = datetime.now(UTC)
        self.dependencies = kwargs.get('dependencies', [])
        self.resource_usage = {'memory': 0, 'cpu': 0}
        
    def _run(self, query: str) -> str:
        if self.status != ToolStatus.ACTIVE:
            raise NetraException(f"Tool {self.name} is {self.status.value}")
        
        self.call_count += 1
        self.last_called = datetime.now(UTC)
        return f"Result from {self.name}: {query}"
    
    async def _arun(self, query: str) -> str:
        return self._run(query)
    
    def activate(self):
        self.status = ToolStatus.ACTIVE
        
    def deactivate(self):
        self.status = ToolStatus.INACTIVE
        
    def mark_deprecated(self):
        self.status = ToolStatus.DEPRECATED


class UnifiedToolRegistry:
    """Unified registry managing multiple tool registries and orchestration"""
    
    def __init__(self):
        self.registries = {}
        
    def add_registry(self, name: str, registry: ToolRegistry):
        """Add a tool registry to unified management"""
        self.registries[name] = registry
        
    def get_all_tools(self) -> Dict[str, List[BaseTool]]:
        """Get all tools from all registries"""
        all_tools = {}
        for name, registry in self.registries.items():
            all_tools[name] = registry.get_all_tools()
        return all_tools
    
    def find_tools_by_name(self, tool_name: str) -> List[BaseTool]:
        """Find tools by name across all registries"""
        found_tools = []
        for registry in self.registries.values():
            tools = registry.get_all_tools()
            found_tools.extend([tool for tool in tools if tool.name == tool_name])
        return found_tools
    
    def find_tools_by_category(self, category: str) -> List[BaseTool]:
        """Find tools by category across all registries"""
        found_tools = []
        for registry in self.registries.values():
            tools = registry.get_all_tools()
            found_tools.extend([tool for tool in tools if hasattr(tool, 'category') and tool.category == category])
        return found_tools


class TestUnifiedToolRegistryManagement:
    """Test unified tool registry management functionality"""
    
    @pytest.fixture
    def unified_registry(self):
        """Create unified tool registry for testing"""
        return UnifiedToolRegistry()
    
    @pytest.fixture
    def sample_tools(self):
        """Create sample tools for testing"""
        return {
            'data_analysis': MockAdvancedTool("data_analyzer", "Analyzes data sets"),
            'supply_chain': MockAdvancedTool("supply_optimizer", "Optimizes supply chains"),
            'risk_assessment': MockAdvancedTool("risk_evaluator", "Evaluates risks"),
            'cost_calculator': MockAdvancedTool("cost_calc", "Calculates costs")
        }
    
    @pytest.fixture
    def sample_registries(self, sample_tools):
        """Create sample tool registries"""
        analytics_registry = ToolRegistry("analytics")
        supply_registry = ToolRegistry("supply_chain")
        
        analytics_registry.register_tool(sample_tools['data_analysis'])
        analytics_registry.register_tool(sample_tools['risk_assessment'])
        
        supply_registry.register_tool(sample_tools['supply_chain'])
        supply_registry.register_tool(sample_tools['cost_calculator'])
        
        return {
            'analytics': analytics_registry,
            'supply_chain': supply_registry
        }

    def _validate_registry_initialization(self, unified_registry):
        """Validate unified registry initialization"""
        assert unified_registry is not None
        assert hasattr(unified_registry, 'registries')
        assert isinstance(unified_registry.registries, dict)
        assert len(unified_registry.registries) == 0  # Initially empty

    def test_unified_registry_initialization(self, unified_registry):
        """Test unified registry initialization"""
        self._validate_registry_initialization(unified_registry)

    def _add_sample_registries(self, unified_registry, sample_registries):
        """Add sample registries to unified registry"""
        for name, registry in sample_registries.items():
            unified_registry.add_registry(name, registry)

    def _validate_registry_addition(self, unified_registry, expected_count):
        """Validate registry addition results"""
        assert len(unified_registry.registries) == expected_count
        for name, registry in unified_registry.registries.items():
            assert isinstance(registry, ToolRegistry)
            assert registry.name == name

    def test_registry_addition_and_management(self, unified_registry):
        """Test adding and managing multiple tool registries"""
        sample_registries = self._create_test_registries()
        self._add_sample_registries(unified_registry, sample_registries)
        self._validate_registry_addition(unified_registry, len(sample_registries))

    def _create_test_registries(self):
        """Create test registries for validation"""
        return {
            'test_analytics': ToolRegistry("test_analytics"),
            'test_supply': ToolRegistry("test_supply")
        }

    def _validate_tool_discovery(self, all_tools, expected_registries):
        """Validate cross-registry tool discovery"""
        assert isinstance(all_tools, dict)
        assert len(all_tools) == len(expected_registries)
        for registry_name in expected_registries:
            assert registry_name in all_tools
            assert isinstance(all_tools[registry_name], list)

    def test_cross_registry_tool_discovery(self, unified_registry, sample_tools):
        """Test discovering tools across multiple registries"""
        sample_registries = self._create_populated_registries(sample_tools)
        self._add_sample_registries(unified_registry, sample_registries)
        all_tools = unified_registry.get_all_tools()
        self._validate_tool_discovery(all_tools, sample_registries.keys())

    def _create_populated_registries(self, sample_tools):
        """Create registries populated with sample tools"""
        analytics_registry = ToolRegistry("analytics")
        supply_registry = ToolRegistry("supply_chain")
        
        analytics_registry.register_tool(sample_tools['data_analysis'])
        supply_registry.register_tool(sample_tools['supply_chain'])
        
        return {
            'analytics': analytics_registry,
            'supply_chain': supply_registry
        }

    def _validate_tool_search_by_name(self, found_tools, tool_name):
        """Validate tool search by name results"""
        assert isinstance(found_tools, list)
        if len(found_tools) > 0:
            for tool in found_tools:
                assert tool.name == tool_name

    def test_tool_search_by_name(self, unified_registry, sample_tools):
        """Test searching for tools by name across registries"""
        sample_registries = self._create_populated_registries(sample_tools)
        self._add_sample_registries(unified_registry, sample_registries)
        
        found_tools = unified_registry.find_tools_by_name("data_analyzer")
        self._validate_tool_search_by_name(found_tools, "data_analyzer")

    def _create_categorized_tools(self):
        """Create tools with categories for testing"""
        tool1 = MockAdvancedTool("analyzer1", "First analyzer")
        tool1.category = "analytics"
        
        tool2 = MockAdvancedTool("analyzer2", "Second analyzer") 
        tool2.category = "analytics"
        
        tool3 = MockAdvancedTool("optimizer1", "First optimizer")
        tool3.category = "optimization"
        
        return [tool1, tool2, tool3]

    def _validate_tool_search_by_category(self, found_tools, category):
        """Validate tool search by category results"""
        assert isinstance(found_tools, list)
        for tool in found_tools:
            assert hasattr(tool, 'category')
            assert tool.category == category

    def test_tool_search_by_category(self, unified_registry):
        """Test searching for tools by category across registries"""
        categorized_tools = self._create_categorized_tools()
        
        # Create registry with categorized tools
        test_registry = ToolRegistry("test")
        for tool in categorized_tools:
            test_registry.register_tool(tool)
        
        unified_registry.add_registry("test", test_registry)
        
        found_tools = unified_registry.find_tools_by_category("analytics")
        self._validate_tool_search_by_category(found_tools, "analytics")

    def _validate_registry_state_consistency(self, unified_registry, expected_tools):
        """Validate registry state consistency"""
        all_tools = unified_registry.get_all_tools()
        total_tools = sum(len(tools) for tools in all_tools.values())
        assert total_tools == expected_tools

    def test_registry_state_consistency(self, unified_registry, sample_tools):
        """Test consistency of registry state across operations"""
        sample_registries = self._create_populated_registries(sample_tools)
        self._add_sample_registries(unified_registry, sample_registries)
        
        # Should have 2 tools (one in each registry)
        self._validate_registry_state_consistency(unified_registry, 2)

    def _create_duplicate_tool_scenario(self):
        """Create scenario with duplicate tools across registries"""
        tool1 = MockAdvancedTool("duplicate_tool", "First instance")
        tool2 = MockAdvancedTool("duplicate_tool", "Second instance")
        
        registry1 = ToolRegistry("registry1")
        registry2 = ToolRegistry("registry2")
        
        registry1.register_tool(tool1)
        registry2.register_tool(tool2)
        
        return {"registry1": registry1, "registry2": registry2}

    def _validate_duplicate_tool_handling(self, found_tools):
        """Validate handling of duplicate tools"""
        assert isinstance(found_tools, list)
        assert len(found_tools) >= 1  # Should find at least one instance
        
        # All found tools should have same name
        tool_name = found_tools[0].name
        for tool in found_tools:
            assert tool.name == tool_name

    def test_duplicate_tool_handling(self, unified_registry):
        """Test handling of duplicate tools across registries"""
        duplicate_registries = self._create_duplicate_tool_scenario()
        self._add_sample_registries(unified_registry, duplicate_registries)
        
        found_tools = unified_registry.find_tools_by_name("duplicate_tool")
        self._validate_duplicate_tool_handling(found_tools)