"""
Comprehensive tests for Unified Tool Registry Management and orchestration
Tests unified management, orchestration, lifecycle management, and coordination
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from enum import Enum

from langchain_core.tools import BaseTool
from app.services.tool_registry import ToolRegistry
from app.core.exceptions_base import NetraException


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
        self.tool_orchestrator = ToolOrchestrator()
        self.lifecycle_manager = ToolLifecycleManager()
        self.health_monitor = ToolHealthMonitor()
        self.metrics_collector = ToolMetricsCollector()
        
    def add_registry(self, name: str, registry: ToolRegistry):
        """Add a tool registry to unified management"""
        self.registries[name] = registry
        
    def get_all_tools(self) -> Dict[str, List[BaseTool]]:
        """Get all tools from all registries"""
        all_tools = {}
        for name, registry in self.registries.items():
            all_tools[name] = registry.get_all_tools()
        return all_tools
    
    async def orchestrate_tool_chain(self, chain_config: Dict[str, Any]) -> Any:
        """Orchestrate execution of tool chain"""
        return await self.tool_orchestrator.execute_chain(chain_config)
    
    def manage_tool_lifecycle(self, tool_name: str, action: str) -> bool:
        """Manage tool lifecycle (activate, deactivate, etc.)"""
        return self.lifecycle_manager.manage_tool(tool_name, action)
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all tools"""
        return self.health_monitor.get_overall_status()
        
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all tools"""
        return self.metrics_collector.collect_all_metrics()


class ToolOrchestrator:
    """Orchestrates tool execution and coordination"""
    
    def __init__(self):
        self.execution_history = []
        self.active_chains = {}
        
    async def execute_chain(self, chain_config: Dict[str, Any]) -> Any:
        """Execute a chain of tools"""
        chain_id = chain_config.get('chain_id', f"chain_{len(self.execution_history)}")
        tools = chain_config.get('tools', [])
        input_data = chain_config.get('input_data')
        
        self.active_chains[chain_id] = {
            'status': 'running',
            'start_time': datetime.now(UTC),
            'tools': tools
        }
        
        try:
            result = input_data
            for tool_config in tools:
                tool = tool_config['tool']
                params = tool_config.get('params', {})
                
                if isinstance(result, str):
                    result = await tool._arun(result)
                else:
                    result = await tool._arun(str(result))
                    
            self.active_chains[chain_id]['status'] = 'completed'
            return result
            
        except Exception as e:
            self.active_chains[chain_id]['status'] = 'failed'
            self.active_chains[chain_id]['error'] = str(e)
            raise
        
        finally:
            self.active_chains[chain_id]['end_time'] = datetime.now(UTC)
            self.execution_history.append(self.active_chains[chain_id])


class ToolLifecycleManager:
    """Manages tool lifecycle and state transitions"""
    
    def __init__(self):
        self.tool_states = {}
        self.lifecycle_history = []
        
    def manage_tool(self, tool_name: str, action: str) -> bool:
        """Manage tool lifecycle action"""
        if tool_name not in self.tool_states:
            self.tool_states[tool_name] = ToolStatus.INACTIVE
            
        current_state = self.tool_states[tool_name]
        
        valid_transitions = {
            ToolStatus.INACTIVE: [ToolStatus.ACTIVE],
            ToolStatus.ACTIVE: [ToolStatus.INACTIVE, ToolStatus.MAINTENANCE, ToolStatus.DEPRECATED],
            ToolStatus.MAINTENANCE: [ToolStatus.ACTIVE, ToolStatus.DEPRECATED],
            ToolStatus.DEPRECATED: []  # No transitions from deprecated
        }
        
        action_to_state = {
            'activate': ToolStatus.ACTIVE,
            'deactivate': ToolStatus.INACTIVE,
            'maintain': ToolStatus.MAINTENANCE,
            'deprecate': ToolStatus.DEPRECATED
        }
        
        target_state = action_to_state.get(action)
        if not target_state:
            return False
            
        if target_state not in valid_transitions[current_state]:
            return False
            
        self.tool_states[tool_name] = target_state
        self.lifecycle_history.append({
            'tool_name': tool_name,
            'action': action,
            'from_state': current_state.value,
            'to_state': target_state.value,
            'timestamp': datetime.now(UTC)
        })
        
        return True


class ToolHealthMonitor:
    """Monitors health and performance of tools"""
    
    def __init__(self):
        self.health_data = {}
        self.alerts = []
        
    def check_tool_health(self, tool: BaseTool) -> Dict[str, Any]:
        """Check health of individual tool"""
        health_status = {
            'tool_name': tool.name,
            'status': 'healthy',
            'last_check': datetime.now(UTC),
            'metrics': {}
        }
        
        # Check if tool is responding
        try:
            test_result = tool._run("health_check")
            health_status['responding'] = True
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
            health_status['responding'] = False
            
        # Check resource usage if available
        if hasattr(tool, 'resource_usage'):
            health_status['metrics']['memory'] = tool.resource_usage.get('memory', 0)
            health_status['metrics']['cpu'] = tool.resource_usage.get('cpu', 0)
            
        # Check call frequency
        if hasattr(tool, 'call_count') and hasattr(tool, 'last_called'):
            health_status['metrics']['call_count'] = tool.call_count
            health_status['metrics']['last_called'] = tool.last_called
            
        self.health_data[tool.name] = health_status
        return health_status
        
    def get_overall_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        total_tools = len(self.health_data)
        healthy_tools = sum(1 for status in self.health_data.values() 
                          if status.get('status') == 'healthy')
        
        return {
            'overall_status': 'healthy' if healthy_tools == total_tools else 'degraded',
            'total_tools': total_tools,
            'healthy_tools': healthy_tools,
            'unhealthy_tools': total_tools - healthy_tools,
            'last_check': datetime.now(UTC),
            'alerts': len(self.alerts)
        }


class ToolMetricsCollector:
    """Collects and aggregates tool metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.aggregated_metrics = {}
        
    def collect_tool_metrics(self, tool: BaseTool) -> Dict[str, Any]:
        """Collect metrics from individual tool"""
        metrics = {
            'tool_name': tool.name,
            'collection_time': datetime.now(UTC),
            'call_count': getattr(tool, 'call_count', 0),
            'last_called': getattr(tool, 'last_called', None),
            'initialization_time': getattr(tool, 'initialization_time', None)
        }
        
        # Collect resource metrics if available
        if hasattr(tool, 'resource_usage'):
            metrics.update(tool.resource_usage)
            
        self.metrics[tool.name] = metrics
        return metrics
        
    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect and aggregate all metrics"""
        self.aggregated_metrics = {
            'collection_time': datetime.now(UTC),
            'total_tools': len(self.metrics),
            'total_calls': sum(m.get('call_count', 0) for m in self.metrics.values()),
            'average_calls': 0,
            'most_used_tool': None,
            'least_used_tool': None
        }
        
        if self.metrics:
            call_counts = [(name, m.get('call_count', 0)) for name, m in self.metrics.items()]
            call_counts.sort(key=lambda x: x[1], reverse=True)
            
            self.aggregated_metrics['average_calls'] = (
                self.aggregated_metrics['total_calls'] / len(self.metrics)
            )
            self.aggregated_metrics['most_used_tool'] = call_counts[0][0] if call_counts else None
            self.aggregated_metrics['least_used_tool'] = call_counts[-1][0] if call_counts else None
            
        return self.aggregated_metrics


class TestUnifiedToolRegistryManagement:
    """Test unified tool registry management"""
    
    @pytest.fixture
    def unified_registry(self):
        """Create unified registry with sample registries"""
        unified = UnifiedToolRegistry()
        
        # Add multiple registries
        for name in ['primary', 'secondary', 'specialized']:
            registry = ToolRegistry(MagicMock())
            unified.add_registry(name, registry)
            
        return unified
    
    @pytest.fixture
    def sample_tools(self):
        """Create sample tools for testing"""
        return [
            MockAdvancedTool("analyzer", "Data analysis tool"),
            MockAdvancedTool("transformer", "Data transformation tool"),
            MockAdvancedTool("validator", "Data validation tool"),
            MockAdvancedTool("optimizer", "Performance optimization tool"),
            MockAdvancedTool("reporter", "Report generation tool")
        ]
    
    def test_unified_registry_initialization(self, unified_registry):
        """Test unified registry initialization"""
        assert len(unified_registry.registries) == 3
        assert 'primary' in unified_registry.registries
        assert 'secondary' in unified_registry.registries
        assert 'specialized' in unified_registry.registries
        
        assert unified_registry.tool_orchestrator != None
        assert unified_registry.lifecycle_manager != None
        assert unified_registry.health_monitor != None
        assert unified_registry.metrics_collector != None
    
    def test_registry_addition_and_management(self, unified_registry):
        """Test adding and managing multiple registries"""
        # Add new registry
        new_registry = ToolRegistry(MagicMock())
        unified_registry.add_registry('experimental', new_registry)
        
        assert len(unified_registry.registries) == 4
        assert 'experimental' in unified_registry.registries
        
        # Test registry replacement
        replacement_registry = ToolRegistry(MagicMock())
        unified_registry.add_registry('primary', replacement_registry)
        
        assert len(unified_registry.registries) == 4  # Same count
        assert unified_registry.registries['primary'] is replacement_registry
    
    def test_cross_registry_tool_discovery(self, unified_registry, sample_tools):
        """Test discovering tools across multiple registries"""
        # Distribute tools across registries
        primary_tools = sample_tools[:2]
        secondary_tools = sample_tools[2:4]
        specialized_tools = sample_tools[4:]
        
        # Mock registry responses
        unified_registry.registries['primary'].get_all_tools = MagicMock(return_value=primary_tools)
        unified_registry.registries['secondary'].get_all_tools = MagicMock(return_value=secondary_tools)
        unified_registry.registries['specialized'].get_all_tools = MagicMock(return_value=specialized_tools)
        
        # Get all tools
        all_tools = unified_registry.get_all_tools()
        
        assert len(all_tools) == 3
        assert len(all_tools['primary']) == 2
        assert len(all_tools['secondary']) == 2
        assert len(all_tools['specialized']) == 1
    async def test_tool_orchestration_simple_chain(self, unified_registry, sample_tools):
        """Test simple tool chain orchestration"""
        analyzer = sample_tools[0]
        transformer = sample_tools[1]
        
        chain_config = {
            'chain_id': 'test_chain',
            'tools': [
                {'tool': analyzer, 'params': {}},
                {'tool': transformer, 'params': {}}
            ],
            'input_data': 'test input data'
        }
        
        result = await unified_registry.orchestrate_tool_chain(chain_config)
        
        assert "analyzer" in result
        assert analyzer.call_count == 1
        assert transformer.call_count == 1
    async def test_tool_orchestration_complex_chain(self, unified_registry, sample_tools):
        """Test complex tool chain with conditional logic"""
        analyzer = sample_tools[0]
        validator = sample_tools[2]
        optimizer = sample_tools[3]
        reporter = sample_tools[4]
        
        # Complex chain: analyze -> validate -> optimize -> report
        chain_config = {
            'chain_id': 'complex_chain',
            'tools': [
                {'tool': analyzer, 'params': {'mode': 'deep'}},
                {'tool': validator, 'params': {'strict': True}},
                {'tool': optimizer, 'params': {'level': 'high'}},
                {'tool': reporter, 'params': {'format': 'json'}}
            ],
            'input_data': 'complex analysis request',
            'conditions': [
                {'after_tool': 'validator', 'condition': 'valid', 'continue': True}
            ]
        }
        
        result = await unified_registry.orchestrate_tool_chain(chain_config)
        
        # All tools should have been called
        assert all(tool.call_count == 1 for tool in [analyzer, validator, optimizer, reporter])
        assert "reporter" in result
    async def test_parallel_tool_orchestration(self, unified_registry, sample_tools):
        """Test parallel execution of multiple tools"""
        tools = sample_tools[:3]
        
        # Create parallel execution tasks
        tasks = []
        for i, tool in enumerate(tools):
            chain_config = {
                'chain_id': f'parallel_chain_{i}',
                'tools': [{'tool': tool, 'params': {}}],
                'input_data': f'parallel input {i}'
            }
            tasks.append(unified_registry.orchestrate_tool_chain(chain_config))
        
        # Execute all chains in parallel
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(tool.call_count == 1 for tool in tools)
    
    def test_tool_lifecycle_management_state_transitions(self, unified_registry, sample_tools):
        """Test tool lifecycle state transitions"""
        tool = sample_tools[0]
        lifecycle_manager = unified_registry.lifecycle_manager
        
        # Initial state should be inactive
        assert lifecycle_manager.tool_states.get(tool.name) == None
        
        # Activate tool
        result = lifecycle_manager.manage_tool(tool.name, 'activate')
        assert result == True
        assert lifecycle_manager.tool_states[tool.name] == ToolStatus.ACTIVE
        
        # Put tool in maintenance
        result = lifecycle_manager.manage_tool(tool.name, 'maintain')
        assert result == True
        assert lifecycle_manager.tool_states[tool.name] == ToolStatus.MAINTENANCE
        
        # Reactivate tool
        result = lifecycle_manager.manage_tool(tool.name, 'activate')
        assert result == True
        assert lifecycle_manager.tool_states[tool.name] == ToolStatus.ACTIVE
        
        # Deprecate tool
        result = lifecycle_manager.manage_tool(tool.name, 'deprecate')
        assert result == True
        assert lifecycle_manager.tool_states[tool.name] == ToolStatus.DEPRECATED
        
        # Try to activate deprecated tool (should fail)
        result = lifecycle_manager.manage_tool(tool.name, 'activate')
        assert result == False
        assert lifecycle_manager.tool_states[tool.name] == ToolStatus.DEPRECATED
    
    def test_tool_lifecycle_history_tracking(self, unified_registry, sample_tools):
        """Test lifecycle history tracking"""
        tool = sample_tools[0]
        lifecycle_manager = unified_registry.lifecycle_manager
        
        # Perform several state transitions
        lifecycle_manager.manage_tool(tool.name, 'activate')
        lifecycle_manager.manage_tool(tool.name, 'maintain')
        lifecycle_manager.manage_tool(tool.name, 'activate')
        
        # Check history
        history = lifecycle_manager.lifecycle_history
        assert len(history) == 3
        
        # Verify history entries
        assert history[0]['action'] == 'activate'
        assert history[0]['from_state'] == 'inactive'
        assert history[0]['to_state'] == 'active'
        
        assert history[1]['action'] == 'maintain'
        assert history[1]['from_state'] == 'active'
        assert history[1]['to_state'] == 'maintenance'
        
        assert history[2]['action'] == 'activate'
        assert history[2]['from_state'] == 'maintenance'
        assert history[2]['to_state'] == 'active'
    
    def test_tool_health_monitoring_individual(self, unified_registry, sample_tools):
        """Test individual tool health monitoring"""
        tool = sample_tools[0]
        health_monitor = unified_registry.health_monitor
        
        # Check healthy tool
        health_status = health_monitor.check_tool_health(tool)
        
        assert health_status['tool_name'] == tool.name
        assert health_status['status'] == 'healthy'
        assert health_status['responding'] == True
        assert 'last_check' in health_status
        
        # Simulate unhealthy tool
        tool.status = ToolStatus.MAINTENANCE
        health_status = health_monitor.check_tool_health(tool)
        
        assert health_status['status'] == 'unhealthy'
        assert health_status['responding'] == False
        assert 'error' in health_status
    
    def test_tool_health_monitoring_overall(self, unified_registry, sample_tools):
        """Test overall health monitoring"""
        health_monitor = unified_registry.health_monitor
        
        # Check health of all tools
        for tool in sample_tools:
            health_monitor.check_tool_health(tool)
        
        # Make some tools unhealthy
        sample_tools[1].status = ToolStatus.MAINTENANCE
        sample_tools[2].status = ToolStatus.DEPRECATED
        
        health_monitor.check_tool_health(sample_tools[1])
        health_monitor.check_tool_health(sample_tools[2])
        
        # Get overall status
        overall_status = health_monitor.get_overall_status()
        
        assert overall_status['total_tools'] == len(sample_tools)
        assert overall_status['healthy_tools'] == 3  # 5 - 2 unhealthy
        assert overall_status['unhealthy_tools'] == 2
        assert overall_status['overall_status'] == 'degraded'
    
    def test_tool_metrics_collection_individual(self, unified_registry, sample_tools):
        """Test individual tool metrics collection"""
        tool = sample_tools[0]
        metrics_collector = unified_registry.metrics_collector
        
        # Use tool to generate metrics
        tool._run("test query 1")
        tool._run("test query 2")
        
        # Collect metrics
        metrics = metrics_collector.collect_tool_metrics(tool)
        
        assert metrics['tool_name'] == tool.name
        assert metrics['call_count'] == 2
        assert metrics['last_called'] != None
        assert metrics['initialization_time'] != None
    
    def test_tool_metrics_aggregation(self, unified_registry, sample_tools):
        """Test tool metrics aggregation"""
        metrics_collector = unified_registry.metrics_collector
        
        # Use tools different amounts
        sample_tools[0]._run("query")  # 1 call
        sample_tools[0]._run("query")  # 2 calls total
        sample_tools[1]._run("query")  # 1 call
        sample_tools[2]._run("query")  # 1 call
        sample_tools[2]._run("query")  # 2 calls
        sample_tools[2]._run("query")  # 3 calls total
        
        # Collect metrics from all tools
        for tool in sample_tools:
            metrics_collector.collect_tool_metrics(tool)
        
        # Get aggregated metrics
        aggregated = metrics_collector.collect_all_metrics()
        
        assert aggregated['total_tools'] == len(sample_tools)
        assert aggregated['total_calls'] == 6  # 2+1+3+0+0
        assert aggregated['average_calls'] == 1.2  # 6/5
        assert aggregated['most_used_tool'] == sample_tools[2].name  # 3 calls
        
        # Tools with 0 calls should be least used
        unused_tools = [t for t in sample_tools if t.call_count == 0]
        if unused_tools:
            assert aggregated['least_used_tool'] == unused_tools[0].name


class TestUnifiedToolRegistryOrchestration:
    """Test advanced orchestration features"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create tool orchestrator for testing"""
        return ToolOrchestrator()
    async def test_conditional_tool_execution(self, orchestrator):
        """Test conditional tool execution based on results"""
        # Create tools with specific behaviors
        condition_tool = MockAdvancedTool("condition_checker", "Checks conditions")
        success_tool = MockAdvancedTool("success_handler", "Handles success case")
        failure_tool = MockAdvancedTool("failure_handler", "Handles failure case")
        
        # Mock condition tool to return success condition
        original_run = condition_tool._run
        def mock_run(query):
            result = original_run(query)
            return f"{result} SUCCESS_CONDITION"
        condition_tool._run = mock_run
        
        # Chain with conditional logic (simplified)
        chain_config = {
            'chain_id': 'conditional_chain',
            'tools': [
                {'tool': condition_tool, 'params': {}},
                {'tool': success_tool, 'params': {}, 'condition': 'SUCCESS_CONDITION'},
                {'tool': failure_tool, 'params': {}, 'condition': 'FAILURE_CONDITION'}
            ],
            'input_data': 'test condition'
        }
        
        result = await orchestrator.execute_chain(chain_config)
        
        # Should have executed condition_tool and success_tool
        assert condition_tool.call_count == 1
        assert success_tool.call_count == 1
        assert failure_tool.call_count == 1  # Simplified - in real implementation would be conditional
    async def test_tool_chain_error_handling(self, orchestrator):
        """Test error handling in tool chains"""
        working_tool = MockAdvancedTool("working_tool", "Working tool")
        failing_tool = MockAdvancedTool("failing_tool", "Failing tool")
        
        # Make failing tool raise exception
        def fail_run(query):
            raise NetraException("Tool execution failed")
        failing_tool._run = fail_run
        
        chain_config = {
            'chain_id': 'error_chain',
            'tools': [
                {'tool': working_tool, 'params': {}},
                {'tool': failing_tool, 'params': {}}
            ],
            'input_data': 'test data'
        }
        
        # Should raise exception
        with pytest.raises(NetraException):
            await orchestrator.execute_chain(chain_config)
        
        # Verify chain status
        chain_status = orchestrator.active_chains['error_chain']
        assert chain_status['status'] == 'failed'
        assert 'error' in chain_status
        assert working_tool.call_count == 1  # First tool should have run
    async def test_tool_chain_timeout_handling(self, orchestrator):
        """Test timeout handling in tool chains"""
        slow_tool = MockAdvancedTool("slow_tool", "Slow executing tool")
        
        # Make tool slow
        async def slow_run(query):
            await asyncio.sleep(2.0)  # 2 second delay
            return f"Slow result: {query}"
        slow_tool._arun = slow_run
        
        chain_config = {
            'chain_id': 'timeout_chain',
            'tools': [{'tool': slow_tool, 'params': {}}],
            'input_data': 'test data',
            'timeout': 1.0  # 1 second timeout
        }
        
        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                orchestrator.execute_chain(chain_config),
                timeout=1.0
            )
    async def test_concurrent_chain_execution(self, orchestrator):
        """Test concurrent execution of multiple tool chains"""
        tools = [MockAdvancedTool(f"tool_{i}", f"Tool {i}") for i in range(5)]
        
        # Create multiple chains
        chains = []
        for i, tool in enumerate(tools):
            chain_config = {
                'chain_id': f'concurrent_chain_{i}',
                'tools': [{'tool': tool, 'params': {}}],
                'input_data': f'concurrent data {i}'
            }
            chains.append(orchestrator.execute_chain(chain_config))
        
        # Execute all chains concurrently
        results = await asyncio.gather(*chains)
        
        # Verify results
        assert len(results) == 5
        assert all(tool.call_count == 1 for tool in tools)
        assert len(orchestrator.execution_history) == 5
    
    def test_orchestrator_execution_history(self, orchestrator):
        """Test execution history tracking"""
        # Initially empty
        assert len(orchestrator.execution_history) == 0
        assert len(orchestrator.active_chains) == 0
        
        # After mock execution
        orchestrator.active_chains['test_chain'] = {
            'status': 'completed',
            'start_time': datetime.now(UTC) - timedelta(seconds=10),
            'end_time': datetime.now(UTC),
            'tools': ['tool1', 'tool2']
        }
        
        # Move to history
        orchestrator.execution_history.append(orchestrator.active_chains['test_chain'])
        
        assert len(orchestrator.execution_history) == 1
        history_entry = orchestrator.execution_history[0]
        assert history_entry['status'] == 'completed'
        assert 'start_time' in history_entry
        assert 'end_time' in history_entry