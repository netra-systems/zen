"""Input/output validation for tool dispatcher."""
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field, ValidationError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class ValidationResult(BaseModel):
    """Result of validation operation"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ToolValidator:
    """Handles input/output validation for tools"""
    
    def validate_tool_name(self, tool_name: str) -> ValidationResult:
        """Validate tool name format and content"""
        errors = []
        
        if not tool_name:
            errors.append("Tool name cannot be empty")
        
        if not isinstance(tool_name, str):
            errors.append("Tool name must be a string")
        
        if len(tool_name) > 100:
            errors.append("Tool name too long (max 100 characters)")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> ValidationResult:
        """Validate tool parameters"""
        errors = []
        warnings = []
        
        if not isinstance(parameters, dict):
            errors.append("Parameters must be a dictionary")
            return ValidationResult(is_valid=False, errors=errors)
        
        if self._has_sensitive_keys(parameters):
            warnings.append("Parameters may contain sensitive information")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _has_sensitive_keys(self, parameters: Dict[str, Any]) -> bool:
        """Check for sensitive parameter keys"""
        sensitive_keys = {'password', 'secret', 'token', 'api_key', 'private_key'}
        return any(key.lower() in sensitive_keys for key in parameters.keys())
    
    def validate_tool_result(self, result: Any) -> ValidationResult:
        """Validate tool execution result"""
        errors = []
        warnings = []
        
        if result is None:
            warnings.append("Tool result is None")
        
        if isinstance(result, dict) and 'error' in result:
            warnings.append("Result contains error field")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def validate_state_object(self, state: Any) -> ValidationResult:
        """Validate state object"""
        errors = []
        
        if state is None:
            errors.append("State cannot be None")
        
        if not hasattr(state, '__dict__'):
            errors.append("State must be an object with attributes")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    def validate_run_id(self, run_id: str) -> ValidationResult:
        """Validate run ID format"""
        errors = []
        
        if not run_id:
            errors.append("Run ID cannot be empty")
        
        if not isinstance(run_id, str):
            errors.append("Run ID must be a string")
        
        if len(run_id) > 50:
            errors.append("Run ID too long (max 50 characters)")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    def sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to remove potentially harmful content"""
        if not isinstance(parameters, dict):
            return {}
        
        sanitized = {}
        for key, value in parameters.items():
            sanitized_key = self._sanitize_string(str(key))
            sanitized_value = self._sanitize_value(value)
            sanitized[sanitized_key] = sanitized_value
        
        return sanitized
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string content"""
        if not isinstance(text, str):
            return str(text)
        
        # Remove potential script tags and SQL injection patterns
        dangerous_patterns = ['<script', 'javascript:', 'DROP TABLE', 'DELETE FROM']
        for pattern in dangerous_patterns:
            text = text.replace(pattern, '')
        
        return text.strip()
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize individual parameter values"""
        if isinstance(value, str):
            return self._sanitize_string(value)
        elif isinstance(value, dict):
            return self.sanitize_parameters(value)
        elif isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        else:
            return value