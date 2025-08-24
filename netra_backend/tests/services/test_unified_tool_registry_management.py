"""
Tests for unified tool registry management.
All functions ≤8 lines per requirements.
"""

import sys
from pathlib import Path

from unittest.mock import MagicMock

import pytest

from netra_backend.app.services.tool_registry import ToolRegistry
from netra_backend.tests.services.tool_registry_management_core import (
    ToolHealthMonitor,
    ToolLifecycleManager,
    ToolMetricsCollector,
    ToolOrchestrator,
    UnifiedToolRegistry,
)
from netra_backend.tests.services.tool_registry_test_mocks import (
    MockAdvancedTool,
    ToolStatus,
    assert_tool_status,
    create_test_tools,
)

@pytest.fixture
def unified_registry():
    """Create unified registry with sample registries"""
    unified = UnifiedToolRegistry()
    
    # Add multiple registries
    for name in ['primary', 'secondary', 'specialized']:
        registry = ToolRegistry(MagicMock())
        unified.add_registry(name, registry)
        
    return unified

@pytest.fixture
def sample_tools():
    """Create sample tools for testing"""
    return [
        MockAdvancedTool("analyzer", "Data analysis tool"),
        MockAdvancedTool("transformer", "Data transformation tool"),
        MockAdvancedTool("validator", "Data validation tool"),
        MockAdvancedTool("optimizer", "Performance optimization tool"),
        MockAdvancedTool("reporter", "Report generation tool")
    ]

class TestUnifiedToolRegistryManagement:
    """Test unified tool registry management"""
    
    def test_unified_registry_initialization(self, unified_registry):
        """Test unified registry initialization"""
        _assert_registry_count(unified_registry, 3)
        _assert_required_registries_present(unified_registry)
        _assert_management_components_initialized(unified_registry)
    
    def test_registry_addition_and_management(self, unified_registry):
        """Test adding and managing multiple registries"""
        # Add new registry
        new_registry = ToolRegistry(MagicMock())
        unified_registry.add_registry('experimental', new_registry)
        
        _assert_registry_count(unified_registry, 4)
        assert 'experimental' in unified_registry.registries
        
        # Test registry replacement
        _test_registry_replacement(unified_registry)
    
    def test_tool_orchestration_setup(self, unified_registry, sample_tools):
        """Test tool orchestration setup and configuration"""
        orchestrator = unified_registry.tool_orchestrator
        
        chain_config = _create_basic_chain_config(sample_tools[:3])
        
        # Verify orchestrator can handle configuration
        assert orchestrator is not None
        assert hasattr(orchestrator, 'execute_chain')
    
    async def test_tool_chain_execution(self, sample_tools):
        """Test execution of tool chains"""
        orchestrator = ToolOrchestrator()
        chain_config = _create_chain_config_with_data(sample_tools[:2])
        
        result = await orchestrator.execute_chain(chain_config)
        
        assert result is not None
        assert len(orchestrator.execution_history) == 1
    
    def test_lifecycle_management_operations(self, sample_tools):
        """Test tool lifecycle management operations"""
        lifecycle_manager = ToolLifecycleManager()
        test_tool = sample_tools[0]
        
        _register_and_test_lifecycle(lifecycle_manager, test_tool)
    
    def test_health_monitoring_functionality(self, sample_tools):
        """Test health monitoring functionality"""
        health_monitor = ToolHealthMonitor()
        
        for tool in sample_tools[:3]:
            health_status = health_monitor.check_tool_health(tool.name, tool)
            assert health_status['healthy'] is True
        
        overall_status = health_monitor.get_overall_status()
        _assert_health_status_format(overall_status)
    
    def test_metrics_collection_system(self, sample_tools):
        """Test metrics collection system"""
        metrics_collector = ToolMetricsCollector()
        
        # Register tool metrics
        for tool in sample_tools[:3]:
            metrics = tool.get_metrics()
            metrics_collector.register_tool_metrics(tool.name, metrics)
        
        _verify_metrics_collection(metrics_collector)
    
    def test_integrated_management_workflow(self, unified_registry, sample_tools):
        """Test integrated management workflow"""
        # Test full workflow integration
        _setup_integrated_workflow(unified_registry, sample_tools)
        _verify_workflow_integration(unified_registry)

def _assert_registry_count(unified_registry, expected_count: int) -> None:
    """Assert unified registry has expected count"""
    assert len(unified_registry.registries) == expected_count

def _assert_required_registries_present(unified_registry) -> None:
    """Assert required registries are present"""
    assert 'primary' in unified_registry.registries
    assert 'secondary' in unified_registry.registries
    assert 'specialized' in unified_registry.registries

def _assert_management_components_initialized(unified_registry) -> None:
    """Assert management components are initialized"""
    assert unified_registry.tool_orchestrator is not None
    assert unified_registry.lifecycle_manager is not None
    assert unified_registry.health_monitor is not None
    assert unified_registry.metrics_collector is not None

def _test_registry_replacement(unified_registry) -> None:
    """Test registry replacement functionality"""
    replacement_registry = ToolRegistry(MagicMock())
    unified_registry.add_registry('primary', replacement_registry)
    
    assert unified_registry.registries['primary'] is replacement_registry

def _create_basic_chain_config(tools: list) -> dict:
    """Create basic chain configuration"""
    return {
        'chain_id': 'test_chain',
        'tools': [{'tool': tool} for tool in tools],
        'input_data': 'test input'
    }

def _create_chain_config_with_data(tools: list) -> dict:
    """Create chain configuration with test data"""
    return {
        'chain_id': 'execution_test',
        'tools': [{'tool': tool, 'params': {}} for tool in tools],
        'input_data': 'test execution data'
    }

def _register_and_test_lifecycle(lifecycle_manager, tool) -> None:
    """Register tool and test lifecycle operations"""
    lifecycle_manager.register_tool(tool.name, tool)
    
    # Test activation
    success = lifecycle_manager.manage_tool(tool.name, 'activate')
    assert success is True
    assert_tool_status(tool, ToolStatus.ACTIVE)
    
    # Test deactivation
    success = lifecycle_manager.manage_tool(tool.name, 'deactivate')
    assert success is True
    assert_tool_status(tool, ToolStatus.INACTIVE)

def _assert_health_status_format(status: dict) -> None:
    """Assert health status has correct format"""
    required_keys = ['healthy_tools', 'total_tools', 'last_check', 'status']
    for key in required_keys:
        assert key in status

def _verify_metrics_collection(metrics_collector) -> None:
    """Verify metrics collection functionality"""
    aggregated = metrics_collector.collect_all_metrics()
    
    assert 'total_tools' in aggregated
    assert aggregated['total_tools'] == 3
    assert 'total_calls' in aggregated
    assert 'tool_details' in aggregated

def _setup_integrated_workflow(unified_registry, sample_tools) -> None:
    """Setup integrated workflow for testing"""
    # Register tools with lifecycle manager
    for tool in sample_tools[:3]:
        unified_registry.lifecycle_manager.register_tool(tool.name, tool)
        
    # Check health for all tools
    for tool in sample_tools[:3]:
        unified_registry.health_monitor.check_tool_health(tool.name, tool)

def _verify_workflow_integration(unified_registry) -> None:
    """Verify workflow integration works correctly"""
    health_status = unified_registry.get_health_status()
    metrics = unified_registry.collect_metrics()
    
    assert health_status is not None
    assert metrics is not None
    assert 'status' in health_status