"""Agent and LLM related exceptions - compliant with 25-line function limit.

This module contains exceptions specific to agent operations, LLM interactions,
and multi-agent system coordination.
"""

from typing import Optional, Union

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException


class AgentError(NetraException):
    """Base class for agent-related errors.
    
    Used for general agent system failures, coordination issues,
    and agent lifecycle problems.
    """
    
    def __init__(self, message: str = None, agent_name: str = None, severity: ErrorSeverity = None, 
                 category=None, original_error=None, context=None, metadata=None, recoverable=True, **kwargs):
        from netra_backend.app.schemas.core_enums import ErrorCategory
        
        message = self._handle_message_fallback(message, agent_name)
        agent_msg = self._build_agent_message(agent_name, message)
        final_severity = severity or ErrorSeverity.MEDIUM
        
        # Store additional properties
        self._category = category or ErrorCategory.UNKNOWN
        self._original_error = original_error
        self._context = context or {}
        self._metadata = metadata or {}
        self.recoverable = recoverable
        
        init_params = self._build_init_params(agent_msg, final_severity, agent_name, kwargs)
        super().__init__(**init_params)
    
    def _handle_message_fallback(self, message: str, agent_name: str) -> str:
        """Handle message fallback when message is None."""
        if message is None and agent_name is not None:
            return f"Agent error in {agent_name}"
        return message
    
    def _build_init_params(self, agent_msg: str, final_severity: ErrorSeverity, agent_name: str, kwargs: dict) -> dict:
        """Build initialization parameters for AgentError."""
        # Filter out custom kwargs that NetraException doesn't accept
        filtered_kwargs = {k: v for k, v in kwargs.items() 
                          if k in ['details', 'user_message', 'trace_id', 'context']}
        return {
            "message": agent_msg, "code": ErrorCode.AGENT_EXECUTION_FAILED, 
            "severity": final_severity, "details": {"agent": agent_name}, **filtered_kwargs
        }
    
    @property
    def severity(self):
        """Get error severity from error details."""
        severity_value = self.error_details.severity
        if isinstance(severity_value, str):
            return self._convert_string_to_severity_enum(severity_value)
        return severity_value
    
    def _convert_string_to_severity_enum(self, severity_value: str):
        """Convert string severity to enum."""
        from netra_backend.app.core.error_codes import ErrorSeverity
        enum_match = self._find_matching_severity_enum(severity_value)
        return enum_match if enum_match else ErrorSeverity.MEDIUM
    
    def _find_matching_severity_enum(self, severity_value: str):
        """Find matching severity enum for string value."""
        from netra_backend.app.core.error_codes import ErrorSeverity
        for severity_enum in ErrorSeverity:
            if severity_enum.value == severity_value:
                return severity_enum
        return None
    
    @property
    def message(self):
        """Get error message."""
        return self.error_details.message
    
    @property
    def category(self):
        """Get error category."""
        return self._category
    
    @category.setter
    def category(self, value):
        """Set error category."""
        self._category = value
    
    @property
    def original_error(self):
        """Get original error."""
        return self._original_error
    
    @property
    def context(self):
        """Get error context."""
        return self._context
    
    @context.setter
    def context(self, value):
        """Set error context."""
        self._context = value
    
    @property
    def metadata(self):
        """Get error metadata."""
        return self._metadata
    
    @property
    def timestamp(self):
        """Get error timestamp."""
        return self.error_details.timestamp.timestamp() if hasattr(self.error_details.timestamp, 'timestamp') else self.error_details.timestamp
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict['category'] = self.category.value if hasattr(self.category, 'value') else str(self.category)
        return base_dict
    
    def __str__(self) -> str:
        """String representation of the exception."""
        return f"{self.category.value.upper()}: {self.message}"
    
    def _build_agent_message(self, agent_name: str, message: str) -> str:
        """Build error message with agent name if provided."""
        base_msg = message or "Agent error occurred"
        if agent_name:
            return f"{base_msg} in {agent_name}"
        return base_msg


class AgentExecutionError(AgentError):
    """Raised when agent execution fails.
    
    Used for agent task failures, execution timeouts,
    and agent process crashes.
    """
    
    def __init__(self, agent_name: str = None, task: str = None, **kwargs):
        details = self._build_execution_details(agent_name, task)
        message = self._build_execution_message(agent_name, task)
        init_params = self._build_execution_init_params(agent_name, message, details, kwargs)
        super().__init__(**init_params)
    
    def _build_execution_details(self, agent_name: str, task: str) -> dict:
        """Build execution error details dictionary."""
        details = {"agent": agent_name}
        if task:
            details["task"] = task
        return details
    
    def _build_execution_message(self, agent_name: str, task: str) -> str:
        """Build execution error message with context."""
        if agent_name and task:
            return f"Agent {agent_name} failed executing task: {task}"
        elif agent_name:
            return f"Agent {agent_name} execution failed"
        return "Agent execution failed"
    
    def _build_execution_init_params(self, agent_name: str, message: str, details: dict, kwargs: dict) -> dict:
        """Build initialization parameters for AgentExecutionError."""
        return {
            "agent_name": agent_name, "message": message, "details": details,
            "user_message": "The AI agent encountered an error. Please try again", **kwargs
        }


class AgentTimeoutError(AgentError):
    """Raised when agent execution times out.
    
    Used for agent operations exceeding time limits,
    response timeouts, and long-running task failures.
    """
    
    def __init__(self, agent_name: str = None, timeout_seconds: Optional[Union[int, float]] = None, **kwargs):
        details = self._build_timeout_details(agent_name, timeout_seconds)
        message = self._build_timeout_message(agent_name, timeout_seconds)
        init_params = self._build_timeout_init_params(message, details, kwargs)
        super().__init__(agent_name=agent_name, **init_params)
    
    def _build_timeout_details(self, agent_name: str, timeout_seconds: Optional[Union[int, float]]) -> dict:
        """Build timeout error details dictionary."""
        details = {"agent": agent_name}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        return details
    
    def _build_timeout_message(self, agent_name: str, timeout: Optional[Union[int, float]]) -> str:
        """Build timeout message with duration if provided."""
        base = f"Agent {agent_name} timed out" if agent_name else "Agent execution timed out"
        if timeout:
            return f"{base} after {timeout}s"
        return base
    
    def _build_timeout_init_params(self, message: str, details: dict, kwargs: dict) -> dict:
        """Build initialization parameters for AgentTimeoutError."""
        return {
            "message": message, "code": ErrorCode.AGENT_TIMEOUT, "severity": ErrorSeverity.HIGH,
            "details": details, "user_message": "The AI operation is taking longer than expected. Please try again",
            **kwargs
        }


class LLMError(NetraException):
    """Base class for LLM-related errors.
    
    Used for language model API failures, provider issues,
    and model configuration problems.
    """
    
    def __init__(self, provider: str = None, model: str = None, **kwargs):
        details = self._build_llm_details(provider, model)
        message = self._build_llm_message(provider, model)
        init_params = self._build_llm_init_params(message, details, kwargs)
        super().__init__(**init_params)
    
    def _build_llm_details(self, provider: str, model: str) -> dict:
        """Build LLM error details dictionary."""
        details = {}
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model
        return details
    
    def _build_llm_message(self, provider: str, model: str) -> str:
        """Build LLM error message with provider/model info."""
        if provider and model:
            return f"LLM request failed ({provider}/{model})"
        return "LLM request failed"
    
    def _build_llm_init_params(self, message: str, details: dict, kwargs: dict) -> dict:
        """Build initialization parameters for LLMError."""
        return {
            "message": message, "code": ErrorCode.LLM_REQUEST_FAILED, "severity": ErrorSeverity.HIGH,
            "details": details, "user_message": "AI service is temporarily unavailable. Please try again",
            **kwargs
        }


class LLMRequestError(LLMError):
    """Raised when LLM API request fails.
    
    Used for API connection failures, invalid requests,
    and service unavailability.
    """
    
    def __init__(self, provider: str = None, model: str = None, status_code: int = None, **kwargs):
        details = self._build_request_details(provider, model, status_code)
        message = self._build_request_message(provider, model, status_code)
        init_params = self._build_request_init_params(provider, model, message, details, kwargs)
        super().__init__(**init_params)
    
    def _build_request_details(self, provider: str, model: str, status_code: int) -> dict:
        """Build request error details with status code."""
        details = self._build_llm_details(provider, model)
        if status_code:
            details["status_code"] = status_code
        return details
    
    def _build_request_message(self, provider: str, model: str, status_code: int) -> str:
        """Build request error message with status code."""
        base = self._build_llm_message(provider, model)
        if status_code:
            return f"{base} (HTTP {status_code})"
        return base
    
    def _build_request_init_params(self, provider: str, model: str, message: str, details: dict, kwargs: dict) -> dict:
        """Build initialization parameters for LLMRequestError."""
        return {
            "provider": provider, "model": model, "message": message, "details": details, **kwargs
        }


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limit is exceeded.
    
    Used for request quota exceeded, rate limiting,
    and API usage restrictions.
    """
    
    def __init__(self, provider: str = None, retry_after: Optional[Union[int, float]] = None, **kwargs):
        details = self._build_rate_limit_details(provider, retry_after, kwargs.get('details', {}))
        message = self._build_rate_limit_message(provider, retry_after)
        init_params = self._build_rate_limit_init_params(provider, message, details, kwargs)
        super().__init__(**init_params)
    
    def _build_rate_limit_details(self, provider: str, retry_after: Optional[Union[int, float]], existing_details: dict) -> dict:
        """Build rate limit error details."""
        details = existing_details.copy()
        if provider:
            details["provider"] = provider
        if retry_after:
            details["retry_after_seconds"] = retry_after
        return details
    
    def _build_rate_limit_message(self, provider: str, retry_after: Optional[Union[int, float]]) -> str:
        """Build rate limit message with retry information."""
        base = f"{provider} rate limit exceeded" if provider else "LLM rate limit exceeded"
        if retry_after:
            return f"{base}. Retry after {retry_after}s"
        return base
    
    def _build_rate_limit_init_params(self, provider: str, message: str, details: dict, kwargs: dict) -> dict:
        """Build initialization parameters for LLMRateLimitError."""
        return {
            "provider": provider, "message": message, "code": ErrorCode.LLM_RATE_LIMIT_EXCEEDED,
            "severity": ErrorSeverity.MEDIUM, "details": details,
            "user_message": "Too many requests. Please wait a moment and try again", **kwargs
        }


class AgentCoordinationError(AgentError):
    """Raised when multi-agent coordination fails.
    
    Used for agent communication failures, workflow coordination issues,
    and inter-agent dependency problems.
    """
    
    def __init__(self, source_agent: str = None, target_agent: str = None, **kwargs):
        details = self._build_coordination_details(source_agent, target_agent)
        message = self._build_coordination_message(source_agent, target_agent)
        init_params = self._build_coordination_init_params(source_agent, message, details, kwargs)
        super().__init__(**init_params)
    
    def _build_coordination_details(self, source_agent: str, target_agent: str) -> dict:
        """Build coordination error details dictionary."""
        details = {}
        if source_agent:
            details["source_agent"] = source_agent
        if target_agent:
            details["target_agent"] = target_agent
        return details
    
    def _build_coordination_message(self, source: str, target: str) -> str:
        """Build coordination error message with agent names."""
        if source and target:
            return f"Coordination failed between {source} and {target}"
        elif source:
            return f"Agent {source} coordination failed"
        return "Agent coordination failed"
    
    def _build_coordination_init_params(self, source_agent: str, message: str, details: dict, kwargs: dict) -> dict:
        """Build initialization parameters for AgentCoordinationError."""
        return {
            "agent_name": source_agent, "message": message, "details": details,
            "user_message": "Agent coordination failed. Please try again", **kwargs
        }


class AgentConfigurationError(AgentError):
    """Raised when agent configuration is invalid.
    
    Used for missing agent configurations, invalid parameters,
    and agent setup failures.
    """
    
    def __init__(self, agent_name: str = None, config_key: str = None, **kwargs):
        details = self._build_config_details(agent_name, config_key)
        message = self._build_config_message(agent_name, config_key)
        init_params = self._build_config_init_params(agent_name, message, details, kwargs)
        super().__init__(**init_params)
    
    def _build_config_details(self, agent_name: str, config_key: str) -> dict:
        """Build configuration error details dictionary."""
        details = {"agent": agent_name}
        if config_key:
            details["config_key"] = config_key
        return details
    
    def _build_config_message(self, agent_name: str, config_key: str) -> str:
        """Build configuration error message with specific key."""
        base = f"Agent {agent_name} configuration error" if agent_name else "Agent configuration error"
        if config_key:
            return f"{base}: {config_key}"
        return base
    
    def _build_config_init_params(self, agent_name: str, message: str, details: dict, kwargs: dict) -> dict:
        """Build initialization parameters for AgentConfigurationError."""
        return {
            "agent_name": agent_name, "message": message, "code": ErrorCode.CONFIGURATION_ERROR,
            "details": details, **kwargs
        }