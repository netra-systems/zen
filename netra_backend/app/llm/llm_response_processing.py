"""LLM Response Processing Module

Handles response processing, streaming, and structured output utilities.
Each function must be  <= 8 lines as per module architecture requirements.
"""
import json
import time
from typing import Any, AsyncIterator, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage
from netra_backend.app.schemas.llm_response_types import LLMResponse
from netra_backend.app.services.llm_cache_service import llm_cache_service

logger = central_logger.get_logger(__name__)
T = TypeVar('T', bound=BaseModel)


async def stream_llm_response(llm: Any, prompt: str) -> AsyncIterator[str]:
    """Stream LLM response content."""
    async for chunk in llm.astream(prompt):
        yield chunk.content


def parse_nested_json_value(value: str) -> Any:
    """Parse JSON string value with error handling."""
    try:
        trimmed = value.strip()
        return _parse_json_if_valid(trimmed)
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug(f"Could not parse nested JSON: {e}")
        return value

def _parse_json_if_valid(trimmed: str) -> Any:
    """Parse JSON if string looks like valid JSON."""
    if _is_json_like(trimmed):
        parsed = json.loads(trimmed)
        return parse_nested_json_recursive(parsed)
    return trimmed


def _is_json_like(trimmed: str) -> bool:
    """Check if string looks like JSON."""
    return trimmed.startswith(('{', '['))


def parse_nested_json_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse JSON strings within dictionary recursively."""
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = parse_nested_json_value(value)
        else:
            result[key] = parse_nested_json_recursive(value)
    return result


def parse_nested_json_recursive(data: Any) -> Any:
    """Recursively parse JSON strings within data structure."""
    if isinstance(data, dict):
        return parse_nested_json_dict(data)
    elif isinstance(data, list):
        return [parse_nested_json_recursive(item) for item in data]
    return data


def _build_cached_choices(cached_content: str) -> list:
    """Build choices array for cached response."""
    return [{
        "message": {"content": cached_content},
        "finish_reason": "stop",
        "index": 0
    }]

def _create_cached_response_object(provider: LLMProvider, model: str, cached_content: str) -> LLMResponse:
    """Create cached LLMResponse object."""
    return LLMResponse(
        provider=provider,
        model=model,
        choices=_build_cached_choices(cached_content),
        usage=TokenUsage(),
        response_time_ms=0,
        cached=True
    )

async def create_cached_llm_response(cached_content: str, config: Any, 
                                   llm_config_name: str) -> LLMResponse:
    """Create LLM response from cached content."""
    provider = LLMProvider(config.provider) if config else LLMProvider.LOCAL
    model = config.model_name if config else llm_config_name
    return _create_cached_response_object(provider, model, cached_content)


def extract_response_content(response: Any) -> str:
    """Extract content from LLM response."""
    return response.content


def create_token_usage(response: Any) -> TokenUsage:
    """Create TokenUsage from response attributes."""
    prompt_tokens = _extract_safe_token_count(response, 'prompt_tokens')
    completion_tokens = _extract_safe_token_count(response, 'completion_tokens')
    total_tokens = _extract_safe_token_count(response, 'total_tokens')
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens
    )


def _extract_safe_token_count(response: Any, attr_name: str) -> int:
    """Extract token count safely, returning 0 if not valid int."""
    value = getattr(response, attr_name, 0)
    return value if isinstance(value, int) else 0


def get_response_model_name(response: Any, config: Any, 
                          llm_config_name: str) -> str:
    """Get model name from response or config."""
    model_attr = getattr(response, 'model', None)
    if isinstance(model_attr, str):
        return model_attr
    return config.model_name if config else llm_config_name


def get_finish_reason(response: Any) -> str:
    """Get finish reason from response."""
    finish_reason = getattr(response, 'finish_reason', 'stop')
    return finish_reason if isinstance(finish_reason, str) else 'stop'


def _build_llm_response_object(provider: LLMProvider, model: str, choices_data: list,
                              token_usage: Any, execution_time_ms: float) -> LLMResponse:
    """Build LLMResponse object with all components."""
    return LLMResponse(
        provider=provider,
        model=model,
        choices=choices_data,
        usage=token_usage,
        response_time_ms=execution_time_ms
    )

async def create_llm_response(response: Any, config: Any, llm_config_name: str,
                            execution_time_ms: float) -> LLMResponse:
    """Create standardized LLM response object."""
    provider = LLMProvider(config.provider) if config else LLMProvider.LOCAL
    choices_data = _build_response_choices(response)
    model = get_response_model_name(response, config, llm_config_name)
    token_usage = create_token_usage(response)
    return _build_llm_response_object(provider, model, choices_data, token_usage, execution_time_ms)


def _build_response_choices(response: Any) -> list:
    """Build choices array for LLM response."""
    return [{
        "message": {"content": extract_response_content(response)},
        "finish_reason": get_finish_reason(response),
        "index": 0
    }]


def attempt_json_fallback_parse(text_response: str, schema: Type[T]) -> T:
    """Attempt to parse text response as JSON for structured output."""
    if text_response.strip().startswith('{'):
        data = json.loads(text_response)
        data = parse_nested_json_recursive(data)
        return schema(**data)
    raise ValueError("Response is not JSON format")


def should_cache_structured_response(prompt: str, response_json: str) -> bool:
    """Check if structured response should be cached."""
    return llm_cache_service.should_cache_response(prompt, response_json)


async def cache_structured_response(cache_key: str, response_json: str, 
                                  llm_config_name: str) -> None:
    """Cache structured response."""
    await llm_cache_service.cache_response(
        cache_key, response_json, llm_config_name
    )


def create_structured_cache_key(prompt: str, llm_config_name: str, 
                               schema_name: str) -> str:
    """Create cache key for structured responses."""
    return f"{prompt}_{llm_config_name}_{schema_name}"


async def get_cached_structured_response(cache_key: str, llm_config_name: str,
                                       schema: Type[T]) -> Optional[T]:
    """Get and parse cached structured response."""
    cached_response = await _fetch_cached_response(cache_key, llm_config_name)
    if cached_response:
        return _parse_cached_response_safely(cached_response, schema)
    return None

async def _fetch_cached_response(cache_key: str, llm_config_name: str) -> Optional[str]:
    """Fetch cached response from cache service."""
    return await llm_cache_service.get_cached_response(
        cache_key, llm_config_name
    )


def _parse_cached_response_safely(cached_response: str, schema: Type[T]) -> Optional[T]:
    """Parse cached response safely, returning None on error."""
    try:
        return schema.model_validate_json(cached_response)
    except Exception as e:
        logger.warning(f"Failed to parse cached structured response: {e}")
        return None


def fix_validation_errors(data: Dict[str, Any], error: ValidationError) -> Dict[str, Any]:
    """Fix common validation errors in LLM responses."""
    if "Input should be a valid dictionary" in str(error):
        return fix_string_parameters_to_dict(data)
    elif "Input should be a valid string" in str(error):
        return fix_dict_recommendations_to_strings(data)
    return data


def fix_string_parameters_to_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix tool_recommendations.parameters from string to dict."""
    if "tool_recommendations" in data and isinstance(data["tool_recommendations"], list):
        for rec in data["tool_recommendations"]:
            if isinstance(rec, dict) and "parameters" in rec:
                rec["parameters"] = _convert_string_param_to_dict(rec["parameters"])
    return data


def _convert_string_param_to_dict(param: Any) -> Dict[str, Any]:
    """Convert string parameter to dict, returning empty dict on error."""
    if isinstance(param, str):
        try:
            return json.loads(param)
        except (json.JSONDecodeError, TypeError):
            return {}
    return param if isinstance(param, dict) else {}


def fix_dict_recommendations_to_strings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix recommendations from dict list to string list."""
    if "recommendations" in data and isinstance(data["recommendations"], list):
        data["recommendations"] = _convert_recommendations_to_strings(data["recommendations"])
    return data


def _convert_recommendations_to_strings(recommendations: list) -> list:
    """Convert recommendation items to strings."""
    fixed_recs = []
    for rec in recommendations:
        if isinstance(rec, dict):
            fixed_recs.append(rec.get("description", str(rec)))
        else:
            fixed_recs.append(str(rec))
    return fixed_recs