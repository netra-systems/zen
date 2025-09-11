"""Tool-specific exception classes for enhanced error handling and diagnostics.

This module provides a comprehensive hierarchy of tool-specific exceptions that extend
the base NetraException class, offering improved error diagnostics and recovery.

Business Value:
- Prevents silent failures in tool registration and execution
- Improves error diagnostics for developers and users
- Reduces time to resolution for tool-related issues
- Enhances system reliability and user experience
- Enables targeted error recovery strategies

Related to Issue #390: Tool Registration Exception Handling Improvements
"""

from typing import Any, Dict, Optional
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity


class ToolException(NetraException):
    """Base exception for all tool-related errors.
    
    This serves as the parent class for all tool-specific exceptions,
    providing common functionality and consistent error handling patterns.
    """
    
    def __init__(self, message: str = "Tool operation failed", 
                 code: ErrorCode = ErrorCode.INTERNAL_ERROR,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None,
                 user_message: Optional[str] = None,
                 trace_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """Initialize tool exception with enhanced context.
        
        Args:
            message: Technical error message
            code: Specific error code for this exception type
            severity: Error severity level
            tool_id: ID of the tool that caused the error
            tool_name: Name of the tool that caused the error  
            user_id: ID of the user experiencing the error
            details: Additional error details
            user_message: User-friendly error message
            trace_id: Trace ID for debugging
            context: Additional context information
        """
        # Build enhanced context with tool-specific information
        enhanced_context = context or {}
        enhanced_context.update({
            'tool_id': tool_id,
            'tool_name': tool_name,
            'user_id': user_id,
            'error_category': 'tool_operation'
        })
        
        # Build enhanced details with tool information
        enhanced_details = details or {}
        if tool_id:
            enhanced_details['tool_id'] = tool_id
        if tool_name:
            enhanced_details['tool_name'] = tool_name
        if user_id:
            enhanced_details['user_id'] = user_id
            
        super().__init__(
            message=message,
            code=code,
            severity=severity,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id,
            context=enhanced_context
        )


class ToolTypeValidationException(ToolException):
    """Exception raised when tool type validation fails.
    
    This exception is raised when:
    - Tool is not a valid BaseTool instance
    - Tool class doesn't implement required interface
    - Tool type is incompatible with registry requirements
    """
    
    def __init__(self, message: str = "Tool type validation failed",
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 expected_type: Optional[str] = None,
                 actual_type: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None):
        """Initialize tool type validation exception.
        
        Args:
            message: Technical error message
            tool_id: ID of the invalid tool
            tool_name: Name of the invalid tool
            user_id: User attempting the registration
            expected_type: Expected tool type/interface
            actual_type: Actual type that was provided
            details: Additional validation details
            trace_id: Trace ID for debugging
        """
        enhanced_details = details or {}
        enhanced_details.update({
            'expected_type': expected_type,
            'actual_type': actual_type,
            'validation_type': 'tool_type'
        })
        
        user_message = (
            f"The tool '{tool_name or tool_id or 'unknown'}' is not a valid tool type. "
            f"Expected a tool that implements the required interface."
        )
        
        super().__init__(
            message=message,
            code=ErrorCode.TOOL_TYPE_VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id
        )


class ToolNameValidationException(ToolException):
    """Exception raised when tool name validation fails.
    
    This exception is raised when:
    - Tool name is empty or None
    - Tool name contains invalid characters
    - Tool name conflicts with existing tools
    - Tool name doesn't meet naming conventions
    """
    
    def __init__(self, message: str = "Tool name validation failed",
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 invalid_name: Optional[str] = None,
                 validation_rule: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None):
        """Initialize tool name validation exception.
        
        Args:
            message: Technical error message
            tool_id: ID of the tool with invalid name
            tool_name: The invalid tool name
            user_id: User attempting the registration
            invalid_name: The specific invalid name value
            validation_rule: Which naming rule was violated
            details: Additional validation details
            trace_id: Trace ID for debugging
        """
        enhanced_details = details or {}
        enhanced_details.update({
            'invalid_name': invalid_name,
            'validation_rule': validation_rule,
            'validation_type': 'tool_name'
        })
        
        user_message = (
            f"The tool name '{invalid_name or tool_name or 'provided'}' is invalid. "
            f"Tool names must be non-empty and follow naming conventions."
        )
        
        super().__init__(
            message=message,
            code=ErrorCode.TOOL_NAME_VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id
        )


class ToolHandlerValidationException(ToolException):
    """Exception raised when tool handler validation fails.
    
    This exception is raised when:
    - Tool handler is not callable
    - Tool handler signature is invalid
    - Tool handler fails validation checks
    """
    
    def __init__(self, message: str = "Tool handler validation failed",
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 handler_type: Optional[str] = None,
                 validation_issue: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None):
        """Initialize tool handler validation exception.
        
        Args:
            message: Technical error message
            tool_id: ID of the tool with invalid handler
            tool_name: Name of the tool with invalid handler
            user_id: User attempting the registration
            handler_type: Type of the invalid handler
            validation_issue: Specific validation issue
            details: Additional validation details
            trace_id: Trace ID for debugging
        """
        enhanced_details = details or {}
        enhanced_details.update({
            'handler_type': handler_type,
            'validation_issue': validation_issue,
            'validation_type': 'tool_handler'
        })
        
        user_message = (
            f"The handler for tool '{tool_name or tool_id or 'unknown'}' is invalid. "
            f"Tool handlers must be callable functions or methods."
        )
        
        super().__init__(
            message=message,
            code=ErrorCode.TOOL_HANDLER_VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id
        )


class ToolNotFoundException(ToolException):
    """Exception raised when a requested tool is not found.
    
    This exception is raised when:
    - Tool is not registered in the registry
    - Tool has been removed or disabled
    - Tool access is restricted for the current user
    """
    
    def __init__(self, message: str = "Tool not found",
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 registry_name: Optional[str] = None,
                 available_tools: Optional[list] = None,
                 details: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None):
        """Initialize tool not found exception.
        
        Args:
            message: Technical error message
            tool_id: ID of the missing tool
            tool_name: Name of the missing tool
            user_id: User requesting the tool
            registry_name: Name of the registry searched
            available_tools: List of available tools (for suggestions)
            details: Additional search details
            trace_id: Trace ID for debugging
        """
        enhanced_details = details or {}
        enhanced_details.update({
            'registry_name': registry_name,
            'available_tools': available_tools,
            'search_type': 'tool_lookup'
        })
        
        user_message = (
            f"The tool '{tool_name or tool_id or 'requested'}' could not be found. "
            f"Please check the tool name and try again."
        )
        
        super().__init__(
            message=message,
            code=ErrorCode.TOOL_NOT_FOUND,
            severity=ErrorSeverity.LOW,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id
        )


class ToolExecutionException(ToolException):
    """Exception raised when tool execution fails.
    
    This exception is raised when:
    - Tool handler execution fails
    - Tool execution times out
    - Tool execution produces invalid results
    - Tool execution is interrupted
    """
    
    def __init__(self, message: str = "Tool execution failed",
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 execution_error: Optional[str] = None,
                 execution_time: Optional[float] = None,
                 input_args: Optional[Dict[str, Any]] = None,
                 details: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None):
        """Initialize tool execution exception.
        
        Args:
            message: Technical error message
            tool_id: ID of the tool that failed execution
            tool_name: Name of the tool that failed execution
            user_id: User who initiated the execution
            execution_error: Specific execution error
            execution_time: Time spent in execution (seconds)
            input_args: Arguments passed to the tool
            details: Additional execution details
            trace_id: Trace ID for debugging
        """
        enhanced_details = details or {}
        enhanced_details.update({
            'execution_error': execution_error,
            'execution_time': execution_time,
            'input_args': input_args,
            'failure_type': 'tool_execution'
        })
        
        user_message = (
            f"The tool '{tool_name or tool_id or 'requested'}' failed to execute properly. "
            f"Please try again or contact support if the issue persists."
        )
        
        super().__init__(
            message=message,
            code=ErrorCode.TOOL_EXECUTION_FAILED,
            severity=ErrorSeverity.HIGH,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id
        )


class ToolPermissionException(ToolException):
    """Exception raised when tool access permission is denied.
    
    This exception is raised when:
    - User lacks permission to access the tool
    - Tool requires higher privilege level
    - Tool access is restricted by policy
    - Tool is disabled for the user's tier
    """
    
    def __init__(self, message: str = "Tool access permission denied",
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 required_permission: Optional[str] = None,
                 user_permissions: Optional[list] = None,
                 access_level: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None):
        """Initialize tool permission exception.
        
        Args:
            message: Technical error message
            tool_id: ID of the restricted tool
            tool_name: Name of the restricted tool
            user_id: User attempting access
            required_permission: Permission required for access
            user_permissions: User's current permissions
            access_level: Required access level
            details: Additional permission details
            trace_id: Trace ID for debugging
        """
        enhanced_details = details or {}
        enhanced_details.update({
            'required_permission': required_permission,
            'user_permissions': user_permissions,
            'access_level': access_level,
            'security_check': 'tool_access'
        })
        
        user_message = (
            f"You don't have permission to access the tool '{tool_name or tool_id or 'requested'}'. "
            f"Please contact your administrator for access."
        )
        
        super().__init__(
            message=message,
            code=ErrorCode.TOOL_ACCESS_DENIED,
            severity=ErrorSeverity.HIGH,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id
        )


class ToolDependencyException(ToolException):
    """Exception raised when tool dependencies are missing or invalid.
    
    This exception is raised when:
    - Required dependencies are not installed
    - Dependency versions are incompatible
    - Dependency conflicts exist
    - System requirements are not met
    """
    
    def __init__(self, message: str = "Tool dependency validation failed",
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 missing_dependencies: Optional[list] = None,
                 conflicting_dependencies: Optional[list] = None,
                 version_conflicts: Optional[Dict[str, str]] = None,
                 details: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None):
        """Initialize tool dependency exception.
        
        Args:
            message: Technical error message
            tool_id: ID of the tool with dependency issues
            tool_name: Name of the tool with dependency issues
            user_id: User attempting to use the tool
            missing_dependencies: List of missing dependencies
            conflicting_dependencies: List of conflicting dependencies
            version_conflicts: Dictionary of version conflicts
            details: Additional dependency details
            trace_id: Trace ID for debugging
        """
        enhanced_details = details or {}
        enhanced_details.update({
            'missing_dependencies': missing_dependencies,
            'conflicting_dependencies': conflicting_dependencies,
            'version_conflicts': version_conflicts,
            'check_type': 'tool_dependencies'
        })
        
        missing_count = len(missing_dependencies) if missing_dependencies else 0
        user_message = (
            f"The tool '{tool_name or tool_id or 'requested'}' has dependency issues. "
            f"{missing_count} required dependencies are missing or incompatible."
        )
        
        super().__init__(
            message=message,
            code=ErrorCode.TOOL_DEPENDENCY_MISSING,
            severity=ErrorSeverity.MEDIUM,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id
        )


class ToolCategoryException(ToolException):
    """Exception raised when tool category validation fails.
    
    This exception is raised when:
    - Tool category is invalid or unknown
    - Tool category doesn't match expected categories
    - Tool category access is restricted
    - Tool category has configuration issues
    """
    
    def __init__(self, message: str = "Tool category validation failed",
                 tool_id: Optional[str] = None,
                 tool_name: Optional[str] = None,
                 user_id: Optional[str] = None,
                 invalid_category: Optional[str] = None,
                 valid_categories: Optional[list] = None,
                 category_restrictions: Optional[Dict[str, str]] = None,
                 details: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None):
        """Initialize tool category exception.
        
        Args:
            message: Technical error message
            tool_id: ID of the tool with category issues
            tool_name: Name of the tool with category issues
            user_id: User attempting the operation
            invalid_category: The invalid category value
            valid_categories: List of valid categories
            category_restrictions: Category-specific restrictions
            details: Additional category details
            trace_id: Trace ID for debugging
        """
        enhanced_details = details or {}
        enhanced_details.update({
            'invalid_category': invalid_category,
            'valid_categories': valid_categories,
            'category_restrictions': category_restrictions,
            'validation_type': 'tool_category'
        })
        
        user_message = (
            f"The category '{invalid_category}' for tool '{tool_name or tool_id or 'requested'}' is invalid. "
            f"Please use a valid category from the allowed list."
        )
        
        super().__init__(
            message=message,
            code=ErrorCode.TOOL_CATEGORY_INVALID,
            severity=ErrorSeverity.MEDIUM,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            details=enhanced_details,
            user_message=user_message,
            trace_id=trace_id
        )


# Export all exception classes
__all__ = [
    'ToolException',
    'ToolTypeValidationException',
    'ToolNameValidationException', 
    'ToolHandlerValidationException',
    'ToolNotFoundException',
    'ToolExecutionException',
    'ToolPermissionException',
    'ToolDependencyException',
    'ToolCategoryException'
]