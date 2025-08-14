"""LLM Response Processing Module

Handles response processing, streaming, and structured output utilities.
Each function must be ≤8 lines as per module architecture requirements.
"""
from typing import Any, AsyncIterator, Type, TypeVar, Dict, Optional
from pydantic import BaseModel
from app.schemas.llm_types import LLMResponse, LLMProvider, TokenUsage
from app.services.llm_cache_service import llm_cache_service
from app.logging_config import central_logger
import json
import time

logger = central_logger.get_logger(__name__)
T = TypeVar('T', bound=BaseModel)


async def stream_llm_response(llm: Any, prompt: str) -> AsyncIterator[str]:
    """Stream LLM response content."""
    async for chunk in llm.astream(prompt):
        yield chunk.content


def create_mock_structured_response(schema: Type[T]) -> T:
    """Create mock structured response for development."""
    mock_data = {}
    for field_name, field_info in schema.model_fields.items():
        if field_info.is_required():
            mock_data[field_name] = get_mock_value_for_field(field_info)
    return schema(**mock_data)


def get_mock_value_for_field(field_info: Any) -> Any:
    """Get mock value based on field type annotation."""
    annotation = field_info.annotation
    if annotation == str:
        return f"[Mock {field_info}]"
    elif annotation == float:
        return 0.5
    elif annotation == int:
        return 1
    elif annotation == bool:
        return False
    return get_complex_mock_value(annotation)


def get_complex_mock_value(annotation: Any) -> Any:
    """Handle complex field types for mock values."""
    if annotation == dict:
        return {}
    elif annotation == list:
        return []
    elif hasattr(annotation, '__origin__'):
        return handle_generic_type(annotation)
    return {}


def handle_generic_type(annotation: Any) -> Any:
    """Handle generic types like List, Dict, Optional."""
    origin = annotation.__origin__
    if origin == list:
        return []
    elif origin == dict:
        return {}
    return None


def parse_nested_json_value(value: str) -> Any:
    """Parse JSON string value with error handling."""
    try:
        if value.strip().startswith(('{', '[')):
            return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        pass
    return value


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


async def create_cached_llm_response(cached_content: str, config: Any, 
                                   llm_config_name: str) -> LLMResponse:
    """Create LLM response from cached content."""
    provider = LLMProvider(config.provider) if config else LLMProvider.LOCAL
    return LLMResponse(
        provider=provider,
        model=config.model_name if config else llm_config_name,
        choices=[{
            "message": {"content": cached_content},
            "finish_reason": "stop",
            "index": 0
        }],
        usage=TokenUsage(),
        response_time_ms=0,
        cached=True
    )


def extract_response_content(response: Any) -> str:
    """Extract content from LLM response."""
    return response.content


def create_token_usage(response: Any) -> TokenUsage:
    """Create TokenUsage from response attributes."""
    return TokenUsage(
        prompt_tokens=getattr(response, 'prompt_tokens', 0),
        completion_tokens=getattr(response, 'completion_tokens', 0),
        total_tokens=getattr(response, 'total_tokens', 0)
    )


def get_response_model_name(response: Any, config: Any, 
                          llm_config_name: str) -> str:
    """Get model name from response or config."""
    return getattr(response, 'model', 
                  config.model_name if config else llm_config_name)


def get_finish_reason(response: Any) -> str:
    """Get finish reason from response."""
    return getattr(response, 'finish_reason', 'stop')


async def create_llm_response(response: Any, config: Any, llm_config_name: str,
                            execution_time_ms: float) -> LLMResponse:
    """Create standardized LLM response object."""
    provider = LLMProvider(config.provider) if config else LLMProvider.LOCAL
    return LLMResponse(
        provider=provider,
        model=get_response_model_name(response, config, llm_config_name),
        choices=[{
            "message": {"content": extract_response_content(response)},
            "finish_reason": get_finish_reason(response),
            "index": 0
        }],
        usage=create_token_usage(response),
        response_time_ms=execution_time_ms
    )


async def attempt_json_fallback_parse(text_response: str, schema: Type[T]) -> T:
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
    cached_response = await llm_cache_service.get_cached_response(
        cache_key, llm_config_name
    )
    if cached_response:
        try:
            return schema.model_validate_json(cached_response)
        except Exception as e:
            logger.warning(f"Failed to parse cached structured response: {e}")
    return None