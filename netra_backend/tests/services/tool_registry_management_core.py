"""
Core tool registry management classes.
All functions ≤8 lines per requirements.
"""

from datetime import UTC, datetime
from typing import Any, Dict, List

from langchain_core.tools import BaseTool

from netra_backend.app.services.tool_registry import ToolRegistry


class UnifiedToolRegistry:
    """Unified registry managing multiple tool registries and orchestration"""
    
    def __init__(self):
        self.registries = {}
        self._init_management_components()
        
    def _init_management_components(self) -> None:
        """Initialize management components"""
        self.tool_orchestrator = ToolOrchestrator()
        self.lifecycle_manager = ToolLifecycleManager()
        self.health_monitor = ToolHealthMonitor()
        self.metrics_collector = ToolMetricsCollector()
        
    def add_registry(self, name: str, registry: ToolRegistry) -> None:
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
        chain_id = self._get_chain_id(chain_config)
        tools = chain_config.get('tools', [])
        input_data = chain_config.get('input_data')
        
        self._start_chain_execution(chain_id, tools)
        
        return await self._process_chain(chain_id, tools, input_data)
    
    def _get_chain_id(self, chain_config: Dict[str, Any]) -> str:
        """Get or generate chain ID"""
        return chain_config.get('chain_id', f"chain_{len(self.execution_history)}")
    
    def _start_chain_execution(self, chain_id: str, tools: List) -> None:
        """Start chain execution tracking"""
        self.active_chains[chain_id] = {
            'status': 'running',
            'start_time': datetime.now(UTC),
            'tools': tools
        }
    
    async def _process_chain(self, chain_id: str, tools: List, input_data: Any) -> Any:
        """Process the tool chain"""
        try:
            result = await self._execute_tool_sequence(tools, input_data)
            self.active_chains[chain_id]['status'] = 'completed'
            return result
        except Exception as e:
            self._handle_chain_error(chain_id, e)
            raise
        finally:
            self._finish_chain_execution(chain_id)
    
    async def _execute_tool_sequence(self, tools: List, input_data: Any) -> Any:
        """Execute sequence of tools"""
        result = input_data
        for tool_config in tools:
            result = await self._execute_single_tool(tool_config, result)
        return result
    
    async def _execute_single_tool(self, tool_config: Dict, input_data: Any) -> Any:
        """Execute a single tool in the chain"""
        tool = tool_config['tool']
        
        if isinstance(input_data, str):
            return await tool._arun(input_data)
        else:
            return await tool._arun(str(input_data))
    
    def _handle_chain_error(self, chain_id: str, error: Exception) -> None:
        """Handle chain execution error"""
        self.active_chains[chain_id]['status'] = 'failed'
        self.active_chains[chain_id]['error'] = str(error)
    
    def _finish_chain_execution(self, chain_id: str) -> None:
        """Finish chain execution and record history"""
        self.active_chains[chain_id]['end_time'] = datetime.now(UTC)
        self.execution_history.append(self.active_chains[chain_id])


class ToolLifecycleManager:
    """Manages tool lifecycle operations"""
    
    def __init__(self):
        self.managed_tools = {}
        self.lifecycle_history = []
        
    def manage_tool(self, tool_name: str, action: str) -> bool:
        """Manage tool lifecycle action"""
        if tool_name not in self.managed_tools:
            return False
        
        tool = self.managed_tools[tool_name]
        success = self._execute_lifecycle_action(tool, action)
        self._record_lifecycle_event(tool_name, action, success)
        
        return success
    
    def _execute_lifecycle_action(self, tool, action: str) -> bool:
        """Execute specific lifecycle action"""
        action_map = {
            'activate': tool.activate,
            'deactivate': tool.deactivate,
            'deprecate': tool.mark_deprecated
        }
        
        if action in action_map:
            action_map[action]()
            return True
        return False
    
    def _record_lifecycle_event(self, tool_name: str, action: str, success: bool) -> None:
        """Record lifecycle event in history"""
        event = {
            'tool_name': tool_name,
            'action': action,
            'success': success,
            'timestamp': datetime.now(UTC)
        }
        self.lifecycle_history.append(event)
    
    def register_tool(self, tool_name: str, tool) -> None:
        """Register tool for lifecycle management"""
        self.managed_tools[tool_name] = tool
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister tool from lifecycle management"""
        if tool_name in self.managed_tools:
            del self.managed_tools[tool_name]
            return True
        return False


class ToolHealthMonitor:
    """Monitors tool health and status"""
    
    def __init__(self):
        self.health_checks = {}
        self.status_history = []
        
    def get_overall_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        return {
            'healthy_tools': self._count_healthy_tools(),
            'total_tools': len(self.health_checks),
            'last_check': datetime.now(UTC),
            'status': self._determine_overall_status()
        }
    
    def _count_healthy_tools(self) -> int:
        """Count number of healthy tools"""
        return sum(1 for status in self.health_checks.values() if status.get('healthy', False))
    
    def _determine_overall_status(self) -> str:
        """Determine overall system status"""
        if not self.health_checks:
            return 'unknown'
        
        healthy_count = self._count_healthy_tools()
        total_count = len(self.health_checks)
        
        if healthy_count == total_count:
            return 'healthy'
        elif healthy_count > total_count // 2:
            return 'degraded'
        else:
            return 'unhealthy'
    
    def check_tool_health(self, tool_name: str, tool) -> Dict[str, Any]:
        """Check health of specific tool"""
        health_status = {
            'healthy': hasattr(tool, 'status') and tool.status.value == 'active',
            'last_check': datetime.now(UTC),
            'metrics': getattr(tool, 'get_metrics', lambda: {})()
        }
        
        self.health_checks[tool_name] = health_status
        return health_status


class ToolMetricsCollector:
    """Collects and aggregates tool metrics"""
    
    def __init__(self):
        self.collected_metrics = {}
        self.collection_history = []
        
    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect metrics from all registered tools"""
        timestamp = datetime.now(UTC)
        aggregated = self._aggregate_metrics()
        
        self.collection_history.append({
            'timestamp': timestamp,
            'metrics': aggregated
        })
        
        return aggregated
    
    def _aggregate_metrics(self) -> Dict[str, Any]:
        """Aggregate metrics from all tools"""
        return {
            'total_tools': len(self.collected_metrics),
            'total_calls': self._sum_metric('call_count'),
            'average_uptime': self._average_metric('uptime'),
            'tool_details': self.collected_metrics.copy()
        }
    
    def _sum_metric(self, metric_name: str) -> int:
        """Sum specific metric across all tools"""
        return sum(
            metrics.get(metric_name, 0) 
            for metrics in self.collected_metrics.values()
        )
    
    def _average_metric(self, metric_name: str) -> float:
        """Calculate average of specific metric"""
        values = [
            metrics.get(metric_name, 0) 
            for metrics in self.collected_metrics.values()
        ]
        return sum(values) / len(values) if values else 0.0
    
    def register_tool_metrics(self, tool_name: str, metrics: Dict[str, Any]) -> None:
        """Register metrics for a specific tool"""
        self.collected_metrics[tool_name] = metrics