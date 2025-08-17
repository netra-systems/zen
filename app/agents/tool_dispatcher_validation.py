"""Input/output validation for tool dispatcher."""
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel, Field, ValidationError
from app.schemas.shared_types import ValidationResult
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# ValidationResult now imported from shared_types.py

class ToolValidator:
    """Handles input/output validation for tools"""
    
    def validate_tool_name(self, tool_name: str) -> ValidationResult:
        """Validate tool name format and content"""
        errors = self._collect_tool_name_errors(tool_name)
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    def _collect_tool_name_errors(self, tool_name: str) -> List[str]:
        """Collect all tool name validation errors"""
        errors = []
        self._check_tool_name_empty(tool_name, errors)
        self._check_tool_name_type(tool_name, errors)
        self._check_tool_name_length(tool_name, errors)
        return errors
    
    def _check_tool_name_empty(self, tool_name: str, errors: List[str]) -> None:
        """Check if tool name is empty"""
        if not tool_name:
            errors.append("Tool name cannot be empty")
    
    def _check_tool_name_type(self, tool_name: str, errors: List[str]) -> None:
        """Check if tool name is correct type"""
        if not isinstance(tool_name, str):
            errors.append("Tool name must be a string")
    
    def _check_tool_name_length(self, tool_name: str, errors: List[str]) -> None:
        """Check if tool name length is valid"""
        if len(tool_name) > 100:
            errors.append("Tool name too long (max 100 characters)")
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> ValidationResult:
        """Validate tool parameters"""
        errors, warnings = self._collect_parameter_issues(parameters)
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _collect_parameter_issues(self, parameters: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Collect parameter validation errors and warnings"""
        errors = []
        warnings = []
        if not self._check_parameter_type(parameters, errors):
            return errors, warnings
        self._check_sensitive_parameters(parameters, warnings)
        return errors, warnings
    
    def _check_parameter_type(self, parameters: Dict[str, Any], errors: List[str]) -> bool:
        """Check if parameters is correct type"""
        if not isinstance(parameters, dict):
            errors.append("Parameters must be a dictionary")
            return False
        return True
    
    def _check_sensitive_parameters(self, parameters: Dict[str, Any], warnings: List[str]) -> None:
        """Check for sensitive parameter keys"""
        if self._has_sensitive_keys(parameters):
            warnings.append("Parameters may contain sensitive information")
    
    def _has_sensitive_keys(self, parameters: Dict[str, Any]) -> bool:
        """Check for sensitive parameter keys"""
        sensitive_keys = {'password', 'secret', 'token', 'api_key', 'private_key'}
        return any(key.lower() in sensitive_keys for key in parameters.keys())
    
    def validate_tool_result(self, result: Any) -> ValidationResult:
        """Validate tool execution result"""
        errors, warnings = self._collect_result_issues(result)
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _collect_result_issues(self, result: Any) -> tuple[List[str], List[str]]:
        """Collect result validation issues"""
        errors = []
        warnings = []
        self._check_result_none(result, warnings)
        self._check_result_error_field(result, warnings)
        return errors, warnings
    
    def _check_result_none(self, result: Any, warnings: List[str]) -> None:
        """Check if result is None"""
        if result is None:
            warnings.append("Tool result is None")
    
    def _check_result_error_field(self, result: Any, warnings: List[str]) -> None:
        """Check if result contains error field"""
        if isinstance(result, dict) and 'error' in result:
            warnings.append("Result contains error field")
    
    def validate_state_object(self, state: Any) -> ValidationResult:
        """Validate state object"""
        errors = self._collect_state_errors(state)
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    def _collect_state_errors(self, state: Any) -> List[str]:
        """Collect state validation errors"""
        errors = []
        self._check_state_none(state, errors)
        self._check_state_attributes(state, errors)
        return errors
    
    def _check_state_none(self, state: Any, errors: List[str]) -> None:
        """Check if state is None"""
        if state is None:
            errors.append("State cannot be None")
    
    def _check_state_attributes(self, state: Any, errors: List[str]) -> None:
        """Check if state has attributes"""
        if not hasattr(state, '__dict__'):
            errors.append("State must be an object with attributes")
    
    def validate_run_id(self, run_id: str) -> ValidationResult:
        """Validate run ID format"""
        errors = self._collect_run_id_errors(run_id)
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    def _collect_run_id_errors(self, run_id: str) -> List[str]:
        """Collect run ID validation errors"""
        errors = []
        self._check_run_id_empty(run_id, errors)
        self._check_run_id_type(run_id, errors)
        self._check_run_id_length(run_id, errors)
        return errors
    
    def _check_run_id_empty(self, run_id: str, errors: List[str]) -> None:
        """Check if run ID is empty"""
        if not run_id:
            errors.append("Run ID cannot be empty")
    
    def _check_run_id_type(self, run_id: str, errors: List[str]) -> None:
        """Check if run ID is correct type"""
        if not isinstance(run_id, str):
            errors.append("Run ID must be a string")
    
    def _check_run_id_length(self, run_id: str, errors: List[str]) -> None:
        """Check if run ID length is valid"""
        if len(run_id) > 50:
            errors.append("Run ID too long (max 50 characters)")
    
    def sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to remove potentially harmful content"""
        if not self._is_valid_dict(parameters):
            return {}
        return self._build_sanitized_dict(parameters)
    
    def _is_valid_dict(self, parameters: Dict[str, Any]) -> bool:
        """Check if parameters is a valid dictionary"""
        return isinstance(parameters, dict)
    
    def _build_sanitized_dict(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Build sanitized dictionary from parameters"""
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
        cleaned_text = self._remove_dangerous_patterns(text)
        return cleaned_text.strip()
    
    def _remove_dangerous_patterns(self, text: str) -> str:
        """Remove dangerous patterns from text"""
        dangerous_patterns = self._get_dangerous_patterns()
        for pattern in dangerous_patterns:
            text = text.replace(pattern, '')
        return text
    
    def _get_dangerous_patterns(self) -> List[str]:
        """Get list of dangerous patterns to remove"""
        return ['<script', 'javascript:', 'DROP TABLE', 'DELETE FROM']
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize individual parameter values"""
        type_handlers = {
            str: self._sanitize_string,
            dict: self.sanitize_parameters,
            list: self._sanitize_list_values
        }
        handler = type_handlers.get(type(value))
        return handler(value) if handler else value
    
    def _sanitize_list_values(self, value_list: List[Any]) -> List[Any]:
        """Sanitize all values in a list"""
        return [self._sanitize_value(item) for item in value_list]