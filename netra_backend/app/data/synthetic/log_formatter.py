# Log Entry Formatting Module for Synthetic Data Generation
import uuid
import time
from typing import Dict, Any, Optional, Union
import pandas as pd


def _create_event_metadata() -> Dict[str, Any]:
    """Creates event metadata section for log entry."""
    return {
        "log_schema_version": "3.0.0",
        "event_id": str(uuid.uuid4()),
        "timestamp_utc": int(time.time() * 1000),
        "ingestion_source": "synthetic_generator_v2"
    }


def _create_trace_context(row: Dict[str, Any], trace_context_override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Creates trace context section for log entry."""
    if trace_context_override:
        return trace_context_override
    return _create_default_trace_context(row)


def _create_default_trace_context(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates default trace context when no override provided."""
    return {
        "trace_id": row['trace_id'],
        "span_id": row['span_id'],
        "span_name": "ChatCompletion",
        "span_kind": "llm"
    }


def _create_identity_context(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates identity context section for log entry."""
    return {
        "user_id": row['user_id'],
        "organization_id": row['organization_id']
    }


def _create_application_context(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates application context section for log entry."""
    return {
        "app_name": row['app_name'],
        "service_name": row['service_name'],
        "sdk_version": "python-sdk-2.0.0",
        "environment": "production"
    }


def _create_request_section(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates request section for log entry."""
    return {
        "model": _create_model_info(row),
        "prompt": _create_prompt_info(row),
        "generation_config": _create_generation_config()
    }


def _create_model_info(row: Dict[str, Any]) -> Dict[str, str]:
    """Creates model information section."""
    return {
        "provider": row['model_provider'],
        "name": row['model_name'],
        "family": ""
    }


def _create_prompt_info(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates prompt information section."""
    return {
        "messages": [{"role": "user", "content": row['user_prompt']}]
    }


def _create_generation_config() -> Dict[str, Any]:
    """Creates generation configuration section."""
    return {
        "max_tokens_to_sample": 2048,
        "is_streaming": False
    }


def _create_response_section(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates response section for log entry."""
    return {
        "completion": _create_completion_info(row),
        "usage": _create_usage_info(row),
        "system": _create_system_info()
    }


def _create_completion_info(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates completion information section."""
    return {
        "choices": [_create_completion_choice(row)]
    }


def _create_completion_choice(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a single completion choice."""
    return {
        "index": 0,
        "finish_reason": "stop_sequence",
        "message": {"role": "assistant", "content": row['assistant_response']}
    }


def _create_usage_info(row: Dict[str, Any]) -> Dict[str, int]:
    """Creates token usage information section."""
    return {
        "prompt_tokens": row['prompt_tokens'],
        "completion_tokens": row['completion_tokens'],
        "total_tokens": row['total_tokens']
    }


def _create_system_info() -> Dict[str, str]:
    """Creates system information section."""
    return {
        "provider_request_id": f"req_{str(uuid.uuid4())}"
    }


def _create_performance_section(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates performance section for log entry."""
    return {
        "latency_ms": {
            "total_e2e": row['total_e2e_ms'],
            "time_to_first_token": row['ttft_ms']
        }
    }


def _create_finops_section(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates finops section for log entry."""
    return {
        "cost": _create_cost_info(row),
        "pricing_info": _create_pricing_info(row)
    }


def _create_cost_info(row: Dict[str, Any]) -> Dict[str, float]:
    """Creates cost information section."""
    return {
        "total_cost_usd": row['total_cost'],
        "prompt_cost_usd": row['prompt_cost'],
        "completion_cost_usd": row['completion_cost']
    }


def _create_pricing_info(row: Dict[str, Any]) -> Dict[str, Any]:
    """Creates pricing information section."""
    return {
        "provider_rate_id": "rate_abc123",
        "prompt_token_rate_usd_per_million": row['model_pricing'][0],
        "completion_token_rate_usd_per_million": row['model_pricing'][1]
    }


def _generate_contextual_response(user_prompt: str) -> str:
    """Generate a contextual assistant response for multi-turn conversation simulation."""
    prompt_lower = user_prompt.lower()
    return _get_response_by_category(prompt_lower, user_prompt)


def _get_response_by_category(prompt_lower: str, user_prompt: str) -> str:
    """Gets appropriate response based on prompt category."""
    specific_response = _check_specific_categories(prompt_lower)
    return specific_response or _create_generic_response(user_prompt)


def _check_specific_categories(prompt_lower: str) -> str:
    """Checks specific prompt categories and returns appropriate response."""
    priority_response = _check_priority_categories(prompt_lower)
    if priority_response:
        return priority_response
    return _check_secondary_categories(prompt_lower)


def _check_priority_categories(prompt_lower: str) -> str:
    """Checks optimization and error categories first."""
    if _contains_optimization_words(prompt_lower):
        return _get_optimization_response()
    elif _contains_error_words(prompt_lower):
        return _get_error_response()
    return ""


def _check_secondary_categories(prompt_lower: str) -> str:
    """Checks data and config categories."""
    if _contains_data_words(prompt_lower):
        return _get_data_response()
    elif _contains_config_words(prompt_lower):
        return _get_config_response()
    return ""


def _get_optimization_response() -> str:
    """Returns optimization-focused response."""
    return "I've analyzed your system performance. Let me provide optimization recommendations based on your current metrics."


def _get_error_response() -> str:
    """Returns error troubleshooting response."""
    return "I understand you're experiencing an issue. Let me help you troubleshoot this step by step."


def _get_data_response() -> str:
    """Returns data analysis response."""
    return "Based on your data patterns, I can provide insights into the trends and anomalies I've detected."


def _get_config_response() -> str:
    """Returns configuration help response."""
    return "I'll help you configure the system properly. Let me walk you through the optimal settings."


def _contains_optimization_words(prompt_lower: str) -> bool:
    """Checks if prompt contains optimization-related words."""
    return any(word in prompt_lower for word in ["optimize", "performance", "improve"])


def _contains_error_words(prompt_lower: str) -> bool:
    """Checks if prompt contains error-related words."""
    return any(word in prompt_lower for word in ["error", "issue", "problem", "bug"])


def _contains_data_words(prompt_lower: str) -> bool:
    """Checks if prompt contains data-related words."""
    return any(word in prompt_lower for word in ["data", "analytics", "metrics"])


def _contains_config_words(prompt_lower: str) -> bool:
    """Checks if prompt contains configuration-related words."""
    return any(word in prompt_lower for word in ["config", "setup", "configure"])


def _create_generic_response(user_prompt: str) -> str:
    """Creates a generic response for unmatched prompts."""
    truncated = user_prompt[:50]
    suffix = '...' if len(user_prompt) > 50 else ''
    return f"I understand your request about {truncated}{suffix}. Let me provide a comprehensive response."


def _handle_multi_turn_messages(log: Dict[str, Any], row: Dict[str, Any], trace_context_override: Optional[Dict[str, Any]]) -> None:
    """Modifies prompt messages for multi-turn conversations."""
    if _is_multi_turn_conversation(trace_context_override):
        _update_messages_for_multi_turn(log, row)


def _is_multi_turn_conversation(trace_context_override: Optional[Dict[str, Any]]) -> bool:
    """Checks if this is a multi-turn conversation."""
    return bool(trace_context_override and trace_context_override.get("parent_span_id"))


def _update_messages_for_multi_turn(log: Dict[str, Any], row: Dict[str, Any]) -> None:
    """Updates log messages for multi-turn conversation format."""
    context_response = _generate_contextual_response(row["user_prompt"])
    log["request"]["prompt"]["messages"] = [
        {"role": "user", "content": row["user_prompt"]},
        {"role": "assistant", "content": context_response}
    ]


def format_log_entry(row: Union[pd.Series, Dict[str, Any]], trace_context_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Converts a DataFrame row or dictionary into the final log entry structure."""
    log = _create_base_log_structure(row, trace_context_override)
    _handle_multi_turn_messages(log, row, trace_context_override)
    return log


def _create_base_log_structure(row: Union[pd.Series, Dict[str, Any]], trace_context_override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Creates the base log entry structure."""
    metadata_sections = _create_metadata_sections(row, trace_context_override)
    data_sections = _create_data_sections(row)
    return {**metadata_sections, **data_sections}


def _create_metadata_sections(row: Union[pd.Series, Dict[str, Any]], trace_context_override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Creates metadata sections of log entry."""
    return {
        "event_metadata": _create_event_metadata(),
        "trace_context": _create_trace_context(row, trace_context_override),
        "identity_context": _create_identity_context(row),
        "application_context": _create_application_context(row)
    }


def _create_data_sections(row: Union[pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
    """Creates data sections of log entry."""
    return {
        "request": _create_request_section(row),
        "response": _create_response_section(row),
        "performance": _create_performance_section(row),
        "finops": _create_finops_section(row)
    }