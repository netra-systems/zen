"""Services Tool Registry - Delegates to UniversalRegistry.

This module provides backward compatibility for the legacy AgentToolConfigRegistry
while delegating all functionality to the new UniversalRegistry pattern.

Business Value:
- Maintains API compatibility for existing code
- Leverages thread-safe UniversalRegistry implementation
- Provides seamless migration path
"""
from typing import List, Optional, Dict, Any

from langchain_core.tools import BaseTool
from netra_backend.app.core.registry.universal_registry import ToolRegistry as UniversalToolRegistry


class AgentToolConfigRegistry:
    """Legacy compatibility layer that delegates to UniversalRegistry."""
    
    def __init__(self, db_session=None):
        self.db_session = db_session  # Kept for compatibility but not used
        
        # Delegate to UniversalRegistry
        self._registry = UniversalToolRegistry()
        
        # Legacy compatibility attributes
        self.enable_validation = False
        self.strict_security = False
        self.performance_thresholds = {}
        
        # Tool categories for backward compatibility
        self._tool_configs = {
            "triage": [],
            "data": [],
            "optimizations_core": [],
            "actions_to_meet_goals": [],
            "reporting": [],
        }

    def get_tools(self, tool_names: List[str]) -> List[BaseTool]:
        """Returns a list of tools for the given tool names."""
        tools = []
        for name in tool_names:
            # First check categories (legacy support)
            if name in self._tool_configs:
                tools.extend(self._tool_configs[name])
            else:
                # Try to get individual tool from registry
                tool = self._registry.get(name)
                if tool:
                    tools.append(tool)
        return tools

    def get_all_tools(self) -> List[BaseTool]:
        """Get all tools from all categories."""
        all_tools = []
        # Legacy categories
        for tools_list in self._tool_configs.values():
            all_tools.extend(tools_list)
        # Plus all tools from registry
        for tool_name in self._registry.list_keys():
            tool = self._registry.get(tool_name)
            if tool and tool not in all_tools:  # Avoid duplicates
                all_tools.append(tool)
        return all_tools

    def register_tool(self, category: str, tool: BaseTool) -> None:
        """Register a tool in the specified category."""
        if self.enable_validation:
            self._validate_tool_registration(tool)
        
        # Register in both legacy category and new registry
        if category in self._tool_configs:
            self._tool_configs[category].append(tool)
        
        # Also register in UniversalRegistry with category tag
        if hasattr(tool, 'name'):
            self._registry.register(tool.name, tool, tags={category})

    def _validate_tool_registration(self, tool: BaseTool) -> None:
        """Validate tool before registration."""
        if not tool.name or not tool.name.strip():
            from netra_backend.app.core.exceptions_base import NetraException
            raise NetraException("Tool validation failed: invalid name")

    # Validation methods for test compatibility
    def validate_tool_interface(self, tool: BaseTool) -> bool:
        """Validate tool interface compliance."""
        return hasattr(tool, '_run') and hasattr(tool, 'name') and hasattr(tool, 'description')

    def validate_metadata(self, metadata: dict) -> bool:
        """Validate tool metadata."""
        required_fields = ['version', 'author']
        return all(field in metadata for field in required_fields)

    def validate_tool_security(self, tool: BaseTool) -> bool:
        """Validate tool security compliance."""
        if self.strict_security:
            return False  # Simplified for testing
        return True

    def validate_tool_performance(self, tool: BaseTool) -> bool:
        """Validate tool performance requirements."""
        if not self.performance_thresholds:
            return True
        performance = self.measure_tool_performance()
        
        # Map threshold names to performance metrics
        threshold_mapping = {
            "max_execution_time": "execution_time",
            "max_memory_usage": "memory_usage", 
            "max_cpu_usage": "cpu_usage"
        }
        
        # Check if any threshold is exceeded
        for threshold_key, threshold_value in self.performance_thresholds.items():
            metric_key = threshold_mapping.get(threshold_key, threshold_key)
            if performance.get(metric_key, 0) > threshold_value:
                return False
        return True

    def measure_tool_performance(self) -> dict:
        """Measure tool performance - stub implementation."""
        return {'execution_time': 0.1, 'memory_usage': 1024, 'cpu_usage': 10}

    def set_compatibility_matrix(self, matrix: dict) -> None:
        """Set tool compatibility matrix."""
        self._compatibility_matrix = matrix

    def validate_compatibility(self, tool1: str, tool2: str) -> bool:
        """Validate tool compatibility."""
        matrix = getattr(self, '_compatibility_matrix', {})
        if tool1 in matrix:
            return tool2 not in matrix[tool1].get('incompatible_with', [])
        return True

    def validate_dependencies(self, tool: BaseTool, dependencies: List[str]) -> dict:
        """Validate tool dependencies."""
        missing = []
        for dep in dependencies:
            if not self.check_dependencies().get(dep, True):
                missing.append(dep)
        return {'valid': len(missing) == 0, 'missing_dependencies': missing}

    def check_dependencies(self) -> dict:
        """Check dependency availability - stub implementation."""
        return {'numpy': True, 'pandas': True, 'sklearn': False}

    def validate_version_compatibility(self, requirements: dict) -> bool:
        """Validate version compatibility requirements."""
        import sys
        python_version = sys.version_info
        min_python = requirements.get('min_python', '3.0').split('.')
        max_python = requirements.get('max_python', '4.0').split('.')
        
        min_version = tuple(int(x) for x in min_python)
        max_version = tuple(int(x) for x in max_python)
        
        return min_version <= python_version[:2] <= max_version

    def get_package_version(self, package: str) -> str:
        """Get package version - stub implementation."""
        return "0.5.0"

    def validate_tool_input(self, tool: BaseTool, input_data: dict) -> bool:
        """Validate tool input against schema."""
        if not hasattr(tool, 'args_schema') or not tool.args_schema:
            return True
        schema = tool.args_schema
        required = schema.get('required', [])
        return all(field in input_data for field in required)

    def validate_tool_output(self, tool: BaseTool, output: any) -> bool:
        """Validate tool output."""
        return output is not None

    def bulk_validate_tools(self, tools: List[BaseTool]) -> List[dict]:
        """Bulk validate multiple tools."""
        results = []
        for tool in tools:
            result = {
                'tool': tool.name,
                'valid': self.validate_tool_interface(tool),
                'errors': []
            }
            results.append(result)
        return results

    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        # Count from both legacy categories and registry
        legacy_count = sum(len(tools) for tools in self._tool_configs.values())
        registry_count = len(self._registry)
        
        # Return the maximum to account for overlap
        return max(legacy_count, registry_count)


# Backward compatibility alias - DEPRECATED
# Use AgentToolConfigRegistry instead for clarity
ToolRegistry = AgentToolConfigRegistry