"""Tool model classes - Single source of truth.

Contains core tool model classes extracted from interfaces_tools.py 
to maintain the 300-line limit per CLAUDE.md requirements.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.ToolPermission import PermissionCheckResult

class ToolExecutionResult:
    """Result of tool execution with comprehensive tracking."""
    
    def __init__(self, tool_name: str, user_id: str, status: str, 
                 execution_time_ms: int, result: Any = None, 
                 error_message: str = None, permission_check = None):
        self.tool_name = tool_name
        self.user_id = user_id
        self.status = status
        self.execution_time_ms = execution_time_ms
        self.result = result
        self.error_message = error_message
        self.permission_check = permission_check


class UnifiedTool:
    """Unified tool representation."""
    
    def __init__(self, name: str, handler: Any = None, input_schema: Dict = None):
        self.name = name
        self.handler = handler
        self.input_schema = input_schema