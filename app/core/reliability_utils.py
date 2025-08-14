"""Reliability utilities for agents and tools."""
from typing import Dict, Any
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)


def create_agent_reliability_wrapper(name: str) -> Any:
    """Create standard reliability wrapper for agents."""
    return get_reliability_wrapper(
        name,
        CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=45.0,
            name=name
        ),
        RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=15.0
        )
    )


def create_tool_reliability_wrapper(name: str) -> Any:
    """Create standard reliability wrapper for tools."""
    return get_reliability_wrapper(
        f"Tool_{name}",
        CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            name=f"Tool_{name}"
        ),
        RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=5.0
        )
    )


def create_default_tool_result(tool_name: str, success: bool, **kwargs: Any) -> Dict[str, Any]:
    """Create standardized tool result structure."""
    result = {
        "success": success,
        "metadata": {"tool": tool_name, **kwargs.get("metadata", {})}
    }
    if success:
        result["data"] = kwargs.get("data")
        result["message"] = kwargs.get("message", "Operation completed successfully")
    else:
        result["error"] = kwargs.get("error", "Operation failed")
    return result