"""
Mock classes for tool registry tests.
All functions ≤8 lines per requirements.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List

from langchain_core.tools import BaseTool

from netra_backend.app.core.exceptions_base import NetraException


class ToolStatus(Enum):
    """Enumeration for tool status states"""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


class MockAdvancedTool(BaseTool):
    """Advanced mock tool with lifecycle management"""
    
    def __init__(self, name: str, description: str = "", **kwargs):
        super().__init__(name=name, description=description, **kwargs)
        self._init_status_tracking()
        self._init_resource_tracking(kwargs)
        
    def _init_status_tracking(self) -> None:
        """Initialize status tracking attributes"""
        self.status = ToolStatus.ACTIVE
        self.call_count = 0
        self.last_called = None
        self.initialization_time = datetime.now(UTC)
    
    def _init_resource_tracking(self, kwargs: dict) -> None:
        """Initialize resource tracking attributes"""
        self.dependencies = kwargs.get('dependencies', [])
        self.resource_usage = {'memory': 0, 'cpu': 0}
        
    def _run(self, query: str) -> str:
        """Execute tool with status checking"""
        self._check_tool_status()
        self._update_call_tracking()
        return f"Result from {self.name}: {query}"
    
    def _check_tool_status(self) -> None:
        """Check if tool is in active status"""
        if self.status != ToolStatus.ACTIVE:
            raise NetraException(f"Tool {self.name} is {self.status.value}")
    
    def _update_call_tracking(self) -> None:
        """Update call count and timestamp"""
        self.call_count += 1
        self.last_called = datetime.now(UTC)
    
    async def _arun(self, query: str) -> str:
        """Async version of tool execution"""
        return self._run(query)
    
    def activate(self) -> None:
        """Activate the tool"""
        self.status = ToolStatus.ACTIVE
        
    def deactivate(self) -> None:
        """Deactivate the tool"""
        self.status = ToolStatus.INACTIVE
        
    def mark_deprecated(self) -> None:
        """Mark tool as deprecated"""
        self.status = ToolStatus.DEPRECATED
    
    def set_maintenance_mode(self) -> None:
        """Set tool to maintenance mode"""
        self.status = ToolStatus.MAINTENANCE
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tool metrics"""
        return {
            'status': self.status.value,
            'call_count': self.call_count,
            'last_called': self.last_called,
            'uptime': self._calculate_uptime(),
            'resource_usage': self.resource_usage
        }
    
    def _calculate_uptime(self) -> float:
        """Calculate tool uptime in seconds"""
        return (datetime.now(UTC) - self.initialization_time).total_seconds()


def create_mock_tool(name: str, **kwargs) -> MockAdvancedTool:
    """Factory function to create mock tools"""
    description = kwargs.get('description', f"Mock tool: {name}")
    return MockAdvancedTool(name=name, description=description, **kwargs)


def create_test_tools(count: int = 3) -> List[MockAdvancedTool]:
    """Create a list of test tools"""
    tools = []
    for i in range(count):
        tool = create_mock_tool(f"test_tool_{i}", description=f"Test tool {i}")
        tools.append(tool)
    return tools


def create_tool_with_dependencies(name: str, dependencies: List[str]) -> MockAdvancedTool:
    """Create tool with specified dependencies"""
    return create_mock_tool(name, dependencies=dependencies)


def assert_tool_status(tool: MockAdvancedTool, expected_status: ToolStatus) -> None:
    """Assert tool has expected status"""
    assert tool.status == expected_status


def assert_tool_called(tool: MockAdvancedTool, expected_count: int = None) -> None:
    """Assert tool was called expected number of times"""
    if expected_count is not None:
        assert tool.call_count == expected_count
    else:
        assert tool.call_count > 0
    assert tool.last_called is not None