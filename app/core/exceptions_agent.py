"""Agent and LLM related exceptions - compliant with 8-line function limit.

This module contains exceptions specific to agent operations, LLM interactions,
and multi-agent system coordination.
"""

from typing import Optional, Union
from app.core.exceptions_base import NetraException
from app.core.error_codes import ErrorCode, ErrorSeverity


class AgentError(NetraException):
    """Base class for agent-related errors.
    
    Used for general agent system failures, coordination issues,
    and agent lifecycle problems.
    """
    
    def __init__(self, agent_name: str = None, message: str = None, **kwargs):
        agent_msg = self._build_agent_message(agent_name, message)
        super().__init__(
            message=agent_msg,
            code=ErrorCode.AGENT_EXECUTION_FAILED,
            severity=ErrorSeverity.HIGH,
            details={"agent": agent_name},
            **kwargs
        )
    
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
        details = {"agent": agent_name}
        if task:
            details["task"] = task
        
        message = self._build_execution_message(agent_name, task)
        super().__init__(
            agent_name=agent_name,
            message=message,
            details=details,
            user_message="The AI agent encountered an error. Please try again",
            **kwargs
        )
    
    def _build_execution_message(self, agent_name: str, task: str) -> str:
        """Build execution error message with context."""
        if agent_name and task:
            return f"Agent {agent_name} failed executing task: {task}"
        elif agent_name:
            return f"Agent {agent_name} execution failed"
        return "Agent execution failed"


class AgentTimeoutError(AgentError):
    """Raised when agent execution times out.
    
    Used for agent operations exceeding time limits,
    response timeouts, and long-running task failures.
    """
    
    def __init__(
        self, 
        agent_name: str = None, 
        timeout_seconds: Optional[Union[int, float]] = None, 
        **kwargs
    ):
        details = {"agent": agent_name}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        
        message = self._build_timeout_message(agent_name, timeout_seconds)
        super().__init__(
            agent_name=agent_name,
            message=message,
            code=ErrorCode.AGENT_TIMEOUT,
            details=details,
            user_message="The AI operation is taking longer than expected. Please try again",
            **kwargs
        )
    
    def _build_timeout_message(self, agent_name: str, timeout: Optional[Union[int, float]]) -> str:
        """Build timeout message with duration if provided."""
        base = f"Agent {agent_name} timed out" if agent_name else "Agent execution timed out"
        if timeout:
            return f"{base} after {timeout}s"
        return base


class LLMError(NetraException):
    """Base class for LLM-related errors.
    
    Used for language model API failures, provider issues,
    and model configuration problems.
    """
    
    def __init__(self, provider: str = None, model: str = None, **kwargs):
        details = self._build_llm_details(provider, model)
        message = self._build_llm_message(provider, model)
        
        super().__init__(
            message=message,
            code=ErrorCode.LLM_REQUEST_FAILED,
            severity=ErrorSeverity.HIGH,
            details=details,
            user_message="AI service is temporarily unavailable. Please try again",
            **kwargs
        )
    
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


class LLMRequestError(LLMError):
    """Raised when LLM API request fails.
    
    Used for API connection failures, invalid requests,
    and service unavailability.
    """
    
    def __init__(self, provider: str = None, model: str = None, status_code: int = None, **kwargs):
        details = self._build_llm_details(provider, model)
        if status_code:
            details["status_code"] = status_code
        
        message = self._build_request_message(provider, model, status_code)
        super().__init__(
            provider=provider,
            model=model,
            message=message,
            details=details,
            **kwargs
        )
    
    def _build_request_message(self, provider: str, model: str, status_code: int) -> str:
        """Build request error message with status code."""
        base = self._build_llm_message(provider, model)
        if status_code:
            return f"{base} (HTTP {status_code})"
        return base


class LLMRateLimitError(LLMError):
    """Raised when LLM API rate limit is exceeded.
    
    Used for request quota exceeded, rate limiting,
    and API usage restrictions.
    """
    
    def __init__(
        self, 
        provider: str = None, 
        retry_after: Optional[Union[int, float]] = None, 
        **kwargs
    ):
        details = kwargs.get('details', {})
        if provider:
            details["provider"] = provider
        if retry_after:
            details["retry_after_seconds"] = retry_after
        
        message = self._build_rate_limit_message(provider, retry_after)
        super().__init__(
            provider=provider,
            message=message,
            code=ErrorCode.LLM_RATE_LIMIT_EXCEEDED,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            user_message="Too many requests. Please wait a moment and try again",
            **kwargs
        )
    
    def _build_rate_limit_message(self, provider: str, retry_after: Optional[Union[int, float]]) -> str:
        """Build rate limit message with retry information."""
        base = f"{provider} rate limit exceeded" if provider else "LLM rate limit exceeded"
        if retry_after:
            return f"{base}. Retry after {retry_after}s"
        return base


class AgentCoordinationError(AgentError):
    """Raised when multi-agent coordination fails.
    
    Used for agent communication failures, workflow coordination issues,
    and inter-agent dependency problems.
    """
    
    def __init__(self, source_agent: str = None, target_agent: str = None, **kwargs):
        details = {}
        if source_agent:
            details["source_agent"] = source_agent
        if target_agent:
            details["target_agent"] = target_agent
        
        message = self._build_coordination_message(source_agent, target_agent)
        super().__init__(
            agent_name=source_agent,
            message=message,
            details=details,
            user_message="Agent coordination failed. Please try again",
            **kwargs
        )
    
    def _build_coordination_message(self, source: str, target: str) -> str:
        """Build coordination error message with agent names."""
        if source and target:
            return f"Coordination failed between {source} and {target}"
        elif source:
            return f"Agent {source} coordination failed"
        return "Agent coordination failed"


class AgentConfigurationError(AgentError):
    """Raised when agent configuration is invalid.
    
    Used for missing agent configurations, invalid parameters,
    and agent setup failures.
    """
    
    def __init__(self, agent_name: str = None, config_key: str = None, **kwargs):
        details = {"agent": agent_name}
        if config_key:
            details["config_key"] = config_key
        
        message = self._build_config_message(agent_name, config_key)
        super().__init__(
            agent_name=agent_name,
            message=message,
            code=ErrorCode.CONFIGURATION_ERROR,
            details=details,
            **kwargs
        )
    
    def _build_config_message(self, agent_name: str, config_key: str) -> str:
        """Build configuration error message with specific key."""
        base = f"Agent {agent_name} configuration error" if agent_name else "Agent configuration error"
        if config_key:
            return f"{base}: {config_key}"
        return base