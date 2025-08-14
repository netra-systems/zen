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
        return fallback if fallback is not None else {}
    return _try_json_parse(value, fallback)

def _try_json_parse(value: str, fallback: Any) -> Any:
    """Helper to attempt JSON parsing with error handling."""
    try:
        parsed = json.loads(value)
        logger.debug(f"Successfully parsed JSON string: {value[:100]}...")
        return parsed
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON string: {value[:100]}... Error: {e}")
        return fallback if fallback is not None else {}


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
    """
    Parse a field that should be a list of strings.
    Handles various input formats and ensures string output.
    """
    if isinstance(value, list):
        # Convert all items to strings
        return [str(item) for item in value]
    
    if isinstance(value, str):
        # Try to parse as JSON first, but only if it looks like JSON
        if value.strip().startswith(('[', '{')):
            parsed = safe_json_parse(value, None)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        # Single string becomes list with one item
        return [value]
    
    if isinstance(value, dict):
        # Convert dict values to strings or use description field
        if "description" in value:
            return [str(value["description"])]
        return [str(v) for v in value.values() if v is not None]
    
    logger.warning(f"Expected list/string/dict, got {type(value)}")
    return []


def fix_tool_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix tool recommendation parameters that come as JSON strings.
    
    Args:
        data: Data dictionary containing tool_recommendations
        
    Returns:
        Fixed data dictionary
    """
    if not isinstance(data, dict):
        return data
    
    # Fix tool_recommendations parameters field
    if "tool_recommendations" in data and isinstance(data["tool_recommendations"], list):
        for rec in data["tool_recommendations"]:
            if isinstance(rec, dict) and "parameters" in rec:
                rec["parameters"] = parse_dict_field(rec["parameters"])
    
    return data


def fix_list_recommendations(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix recommendations field that should be list of strings.
    
    Args:
        data: Data dictionary containing recommendations
        
    Returns:
        Fixed data dictionary
    """
    if not isinstance(data, dict):
        return data
    
    if "recommendations" in data:
        data["recommendations"] = parse_string_list_field(data["recommendations"])
    
    return data


def comprehensive_json_fix(data: Any) -> Any:
    """
    Apply comprehensive JSON string parsing fixes to data.
    
    Args:
        data: Input data (dict, list, or other)
        
    Returns:
        Fixed data with JSON strings parsed
    """
    if isinstance(data, dict):
        # Fix known problematic fields
        data = fix_tool_parameters(data)
        data = fix_list_recommendations(data)
        
        # Recursively fix nested structures
        for key, value in data.items():
            data[key] = comprehensive_json_fix(value)
    
    elif isinstance(data, list):
        # Fix each item in list
        data = [comprehensive_json_fix(item) for item in data]
    
    return data