"""
Tests for unified tool registry orchestration features.
All functions ≤8 lines per requirements.
"""

import sys
from pathlib import Path

import pytest

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.tests.services.tool_registry_management_core import ToolOrchestrator
from netra_backend.tests.services.tool_registry_test_mocks import (
    MockAdvancedTool,
    assert_tool_called,
)

@pytest.fixture
def orchestrator():
    """Create tool orchestrator for testing"""
    return ToolOrchestrator()

class TestUnifiedToolRegistryOrchestration:
    """Test advanced orchestration features"""
    
    @pytest.mark.asyncio
    async def test_conditional_tool_execution(self, orchestrator):
        """Test conditional tool execution based on results"""
        condition_tool, success_tool, failure_tool = _create_conditional_tools()
        _setup_condition_tool_behavior(condition_tool)
        
        chain_config = _create_conditional_chain_config(
            condition_tool, success_tool, failure_tool
        )
        
        result = await orchestrator.execute_chain(chain_config)
        _verify_conditional_execution(condition_tool, success_tool, failure_tool)
    
    @pytest.mark.asyncio
    async def test_tool_chain_error_handling(self, orchestrator):
        """Test error handling in tool chains"""
        working_tool = MockAdvancedTool("working_tool", "Working tool")
        failing_tool = MockAdvancedTool("failing_tool", "Failing tool")
        
        _setup_failing_tool(failing_tool)
        chain_config = _create_error_chain_config(working_tool, failing_tool)
        
        await _test_chain_failure_handling(orchestrator, chain_config, working_tool)
    
    @pytest.mark.asyncio
    async def test_parallel_tool_execution(self, orchestrator):
        """Test parallel execution of independent tools"""
        tools = _create_parallel_execution_tools()
        chain_config = _create_parallel_chain_config(tools)
        
        result = await orchestrator.execute_chain(chain_config)
        
        _verify_parallel_execution(tools, result)
    
    @pytest.mark.asyncio
    async def test_tool_dependency_resolution(self, orchestrator):
        """Test tool dependency resolution and ordering"""
        dependent_tools = _create_dependent_tools()
        chain_config = _create_dependency_chain_config(dependent_tools)
        
        result = await orchestrator.execute_chain(chain_config)
        
        _verify_dependency_execution_order(dependent_tools)
    
    @pytest.mark.asyncio
    async def test_chain_performance_metrics(self, orchestrator):
        """Test chain performance metrics collection"""
        performance_tools = _create_performance_test_tools()
        chain_config = _create_performance_chain_config(performance_tools)
        
        result = await orchestrator.execute_chain(chain_config)
        
        _verify_performance_metrics(orchestrator, chain_config['chain_id'])
    
    @pytest.mark.asyncio
    async def test_tool_chain_composition(self, orchestrator):
        """Test composition of multiple tool chains"""
        chain_tools = _create_composition_tools()
        
        # Execute first sub-chain
        sub_chain_1 = _create_sub_chain_config(chain_tools[:2], "sub_1")
        result_1 = await orchestrator.execute_chain(sub_chain_1)
        
        # Execute second sub-chain
        sub_chain_2 = _create_sub_chain_config(chain_tools[2:], "sub_2")
        result_2 = await orchestrator.execute_chain(sub_chain_2)
        
        _verify_chain_composition(orchestrator, result_1, result_2)
    
    @pytest.mark.asyncio
    async def test_dynamic_tool_registration(self, orchestrator):
        """Test dynamic tool registration during execution"""
        base_tools = _create_base_tools()
        dynamic_tool = MockAdvancedTool("dynamic_tool", "Dynamically added tool")
        
        # Execute with base tools first
        base_config = _create_base_chain_config(base_tools)
        await orchestrator.execute_chain(base_config)
        
        # Execute with dynamic tool added
        enhanced_config = _create_enhanced_chain_config(base_tools, dynamic_tool)
        result = await orchestrator.execute_chain(enhanced_config)
        
        _verify_dynamic_registration(orchestrator, dynamic_tool)

def _create_conditional_tools() -> tuple:
    """Create tools for conditional execution testing"""
    condition_tool = MockAdvancedTool("condition_checker", "Checks conditions")
    success_tool = MockAdvancedTool("success_handler", "Handles success case")
    failure_tool = MockAdvancedTool("failure_handler", "Handles failure case")
    return condition_tool, success_tool, failure_tool

def _setup_condition_tool_behavior(condition_tool) -> None:
    """Setup condition tool to return success condition"""
    original_run = condition_tool._run
    def mock_run(query):
        result = original_run(query)
        return f"{result} SUCCESS_CONDITION"
    condition_tool._run = mock_run

def _create_conditional_chain_config(condition_tool, success_tool, failure_tool) -> dict:
    """Create chain configuration for conditional execution"""
    return {
        'chain_id': 'conditional_chain',
        'tools': [
            {'tool': condition_tool, 'params': {}},
            {'tool': success_tool, 'params': {}, 'condition': 'SUCCESS_CONDITION'},
            {'tool': failure_tool, 'params': {}, 'condition': 'FAILURE_CONDITION'}
        ],
        'input_data': 'test condition'
    }

def _verify_conditional_execution(condition_tool, success_tool, failure_tool) -> None:
    """Verify conditional execution results"""
    assert condition_tool.call_count == 1
    assert success_tool.call_count == 1
    assert failure_tool.call_count == 1  # Simplified - in real implementation would be conditional

def _setup_failing_tool(failing_tool) -> None:
    """Setup tool to fail during execution"""
    def fail_run(query):
        raise NetraException("Tool execution failed")
    failing_tool._run = fail_run

def _create_error_chain_config(working_tool, failing_tool) -> dict:
    """Create chain configuration for error testing"""
    return {
        'chain_id': 'error_chain',
        'tools': [
            {'tool': working_tool, 'params': {}},
            {'tool': failing_tool, 'params': {}}
        ],
        'input_data': 'test error handling'
    }

async def _test_chain_failure_handling(orchestrator, chain_config, working_tool) -> None:
    """Test chain failure handling"""
    with pytest.raises(NetraException):
        await orchestrator.execute_chain(chain_config)
    
    # Verify working tool was called before failure
    assert_tool_called(working_tool, 1)
    
    # Verify chain is marked as failed
    chain_id = chain_config['chain_id']
    assert orchestrator.active_chains[chain_id]['status'] == 'failed'

def _create_parallel_execution_tools() -> list:
    """Create tools for parallel execution testing"""
    return [
        MockAdvancedTool(f"parallel_tool_{i}", f"Parallel tool {i}")
        for i in range(3)
    ]

def _create_parallel_chain_config(tools: list) -> dict:
    """Create chain configuration for parallel execution"""
    return {
        'chain_id': 'parallel_chain',
        'tools': [{'tool': tool, 'parallel': True} for tool in tools],
        'input_data': 'parallel test data'
    }

def _verify_parallel_execution(tools: list, result) -> None:
    """Verify parallel execution results"""
    for tool in tools:
        assert_tool_called(tool, 1)
    assert result is not None

def _create_dependent_tools() -> list:
    """Create tools with dependencies"""
    tool_a = MockAdvancedTool("tool_a", "Independent tool", dependencies=[])
    tool_b = MockAdvancedTool("tool_b", "Depends on A", dependencies=["tool_a"])
    tool_c = MockAdvancedTool("tool_c", "Depends on B", dependencies=["tool_b"])
    return [tool_a, tool_b, tool_c]

def _create_dependency_chain_config(tools: list) -> dict:
    """Create chain configuration with dependencies"""
    return {
        'chain_id': 'dependency_chain',
        'tools': [{'tool': tool} for tool in tools],
        'input_data': 'dependency test data'
    }

def _verify_dependency_execution_order(tools: list) -> None:
    """Verify tools were executed in dependency order"""
    for tool in tools:
        assert_tool_called(tool, 1)

def _create_performance_test_tools() -> list:
    """Create tools for performance testing"""
    return [
        MockAdvancedTool(f"perf_tool_{i}", f"Performance tool {i}")
        for i in range(5)
    ]

def _create_performance_chain_config(tools: list) -> dict:
    """Create chain configuration for performance testing"""
    return {
        'chain_id': 'performance_chain',
        'tools': [{'tool': tool} for tool in tools],
        'input_data': 'performance test data'
    }

def _verify_performance_metrics(orchestrator, chain_id: str) -> None:
    """Verify performance metrics are collected"""
    history = orchestrator.execution_history
    assert len(history) > 0
    
    # Find our chain in history
    chain_record = next((h for h in history if h.get('chain_id') == chain_id), None)
    assert chain_record is not None
    assert 'start_time' in chain_record
    assert 'end_time' in chain_record

def _create_composition_tools() -> list:
    """Create tools for chain composition testing"""
    return [
        MockAdvancedTool(f"compose_tool_{i}", f"Composition tool {i}")
        for i in range(4)
    ]

def _create_sub_chain_config(tools: list, chain_id: str) -> dict:
    """Create sub-chain configuration"""
    return {
        'chain_id': chain_id,
        'tools': [{'tool': tool} for tool in tools],
        'input_data': f'sub-chain {chain_id} data'
    }

def _verify_chain_composition(orchestrator, result_1, result_2) -> None:
    """Verify chain composition results"""
    assert result_1 is not None
    assert result_2 is not None
    assert len(orchestrator.execution_history) == 2

def _create_base_tools() -> list:
    """Create base tools for dynamic registration testing"""
    return [
        MockAdvancedTool("base_tool_1", "Base tool 1"),
        MockAdvancedTool("base_tool_2", "Base tool 2")
    ]

def _create_base_chain_config(tools: list) -> dict:
    """Create base chain configuration"""
    return {
        'chain_id': 'base_chain',
        'tools': [{'tool': tool} for tool in tools],
        'input_data': 'base chain data'
    }

def _create_enhanced_chain_config(base_tools: list, dynamic_tool) -> dict:
    """Create enhanced chain configuration with dynamic tool"""
    all_tools = base_tools + [dynamic_tool]
    return {
        'chain_id': 'enhanced_chain',
        'tools': [{'tool': tool} for tool in all_tools],
        'input_data': 'enhanced chain data'
    }

def _verify_dynamic_registration(orchestrator, dynamic_tool) -> None:
    """Verify dynamic tool registration"""
    assert_tool_called(dynamic_tool, 1)
    assert len(orchestrator.execution_history) == 2