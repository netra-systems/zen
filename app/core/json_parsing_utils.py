"""
JSON parsing utilities for handling LLM responses with string-to-dict conversion.
Provides robust JSON parsing with fallbacks for Pydantic pre-validators.
"""

import json
import logging
from typing import Any, Dict, List, Union, Optional

logger = logging.getLogger(__name__)


def safe_json_parse(value: Any, fallback: Any = None) -> Any:
    """Safely parse JSON string to dict/list with fallback."""
    if not isinstance(value, str):
        return value
    if not value.strip():
        return fallback if fallback is not None else value
    return _try_json_parse(value, fallback)


def _try_json_parse(value: str, fallback: Any) -> Any:
    """Helper to attempt JSON parsing with error handling."""
    stripped = value.strip()
    
    # Check for command-line style arguments (like --full-scan, --batch-size, etc.)
    if (stripped.startswith('--') or 
        ' --' in stripped or 
        '-' in stripped.split()[0] if stripped.split() else False):
        logger.debug(f"String appears to be command-line arguments, not JSON: {value[:100]}...")
        return fallback if fallback is not None else value
    
    # Check for key-value pair strings like "workload_type=batch" or "optimization_focus=cost"
    if ('=' in stripped and 
        not stripped.startswith(('{', '[', '"')) and 
        not stripped.endswith(('}', ']', '"')) and
        not ',' in stripped):
        # This looks like a single key-value pair, not JSON
        logger.debug(f"String appears to be key-value pair, not JSON: {value[:100]}...")
        return fallback if fallback is not None else value
    
    # Check if the string looks like complex descriptive text (contains commas but not JSON-like)
    if (',' in stripped and 
        not stripped.startswith(('{', '[', '"')) and 
        not stripped.endswith(('}', ']', '"')) and
        len(stripped.split(',')) > 1):
        # This looks like comma-separated descriptive text, not JSON
        logger.debug(f"String appears to be descriptive text, not JSON: {value[:100]}...")
        return fallback if fallback is not None else value
    
    try:
        parsed = json.loads(value)
        logger.debug(f"Successfully parsed JSON string: {value[:100]}...")
        return parsed
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON string: {value[:100]}... Error: {e}")
        return fallback if fallback is not None else value


def parse_dict_field(value: Any) -> Dict[str, Any]:
    """Parse a field that should be a dictionary."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return _parse_string_to_dict(value)
    logger.warning(f"Expected dict or string, got {type(value)}")
    return {}


def _parse_string_to_dict(value: str) -> Dict[str, Any]:
    """Helper to parse string to dict."""
    parsed = safe_json_parse(value, {})
    if isinstance(parsed, dict):
        return parsed
    logger.warning(f"Parsed JSON is not a dict: {type(parsed)}")
    return {}


def parse_list_field(value: Any) -> List[Any]:
    """Parse a field that should be a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return _parse_string_to_list(value)
    logger.warning(f"Expected list or string, got {type(value)}")
    return []


def _parse_string_to_list(value: str) -> List[Any]:
    """Helper to parse string to list."""
    parsed = safe_json_parse(value, [])
    if isinstance(parsed, list):
        return parsed
    logger.warning(f"Parsed JSON is not a list: {type(parsed)}")
    return []


def parse_string_list_field(value: Any) -> List[str]:
    """Parse a field that should be a list of strings."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return _parse_string_to_string_list(value)
    if isinstance(value, dict):
        return _parse_dict_to_string_list(value)
    return _handle_unexpected_type(value)


def _parse_string_to_string_list(value: str) -> List[str]:
    """Helper to parse string to string list."""
    stripped = value.strip()
    if stripped.startswith(('[', '{')):
        parsed = safe_json_parse(value, None)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    
    # Handle comma-separated values for descriptive text
    if ',' in stripped and not stripped.startswith(('{', '[')):
        items = [item.strip() for item in stripped.split(',')]
        return [item for item in items if item]  # Filter out empty strings
    
    return [value]


def _parse_dict_to_string_list(value: Dict[str, Any]) -> List[str]:
    """Helper to parse dict to string list."""
    if "description" in value:
        return [str(value["description"])]
    return [str(v) for v in value.values() if v is not None]


def fix_tool_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix tool recommendation parameters that come as JSON strings."""
    if not isinstance(data, dict):
        return data
    if "tool_recommendations" in data and isinstance(data["tool_recommendations"], list):
        _fix_tool_params_list(data["tool_recommendations"])
    return data


def _fix_tool_params_list(tool_list: List[Any]) -> None:
    """Helper to fix parameters in tool list."""
    for rec in tool_list:
        if isinstance(rec, dict) and "parameters" in rec:
            rec["parameters"] = parse_dict_field(rec["parameters"])


def fix_list_recommendations(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix recommendations field that should be list of strings."""
    if not isinstance(data, dict):
        return data
    if "recommendations" in data:
        data["recommendations"] = parse_string_list_field(data["recommendations"])
    return data


def comprehensive_json_fix(data: Any) -> Any:
    """Apply comprehensive JSON string parsing fixes to data."""
    if isinstance(data, dict):
        return _fix_dict_data(data)
    elif isinstance(data, list):
        return [comprehensive_json_fix(item) for item in data]
    elif isinstance(data, str):
        return _fix_string_response_to_json(data)
    return data


def _fix_dict_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to fix dictionary data."""
    data = fix_tool_parameters(data)
    data = fix_list_recommendations(data)
    for key, value in data.items():
        data[key] = comprehensive_json_fix(value)
    return data


def _handle_unexpected_type(value: Any) -> List[str]:
    """Helper to handle unexpected types in string list parsing."""
    logger.warning(f"Expected list/string/dict, got {type(value)}")
    return []


def _handle_json_error(value: str, error: Exception, fallback: Any) -> Any:
    """Helper to handle JSON parsing errors."""
    logger.warning(f"Failed to parse JSON string: {value[:100]}... Error: {error}")
    return fallback if fallback is not None else {}


def _fix_string_response_to_json(data: str) -> Dict[str, Any]:
    """Fix string responses that should be JSON objects."""
    stripped = data.strip()
    
    # If it's command-line arguments, wrap in a result object
    if stripped.startswith('--') or ' --' in stripped:
        return {
            "type": "command_result",
            "raw_response": stripped,
            "parsed": False,
            "message": "Response contains command-line arguments instead of JSON"
        }
    
    # If it's a simple descriptive string, wrap it
    if not stripped.startswith(('{', '[')):
        return {
            "type": "text_response", 
            "content": stripped,
            "parsed": False,
            "message": "Response is plain text instead of JSON"
        }
    
    # Try to parse as JSON, return wrapped version if it fails
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else {"content": parsed}
    except (json.JSONDecodeError, TypeError):
        return {
            "type": "malformed_json",
            "raw_response": stripped,
            "parsed": False,
            "message": "Response contains malformed JSON"
        }


def ensure_agent_response_is_json(response: Any) -> Dict[str, Any]:
    """Ensure agent response is a proper JSON object."""
    if isinstance(response, dict):
        return response
    elif isinstance(response, str):
        return _fix_string_response_to_json(response)
    elif isinstance(response, list):
        return {"items": response, "type": "list_response"}
    else:
        return {
            "type": "unknown_response",
            "content": str(response),
            "parsed": False,
            "message": f"Response type {type(response)} is not JSON serializable"
        }

