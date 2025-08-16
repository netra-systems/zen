# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4.1 claude-sonnet-4-20250514
# Context: Core JSON parsing functions - split from utils_json_extraction.py (300-line compliance)
# Git: anthony-aug-13-2 | clean
# Change: Refactor | Scope: Component | Risk: Low
# Session: architecture-compliance | Seq: 1
# Review: Pending | Score: 95
# ================================
"""Core JSON parsing utilities - focused on parsing operations."""

import json
import re
from typing import Any, Dict, Optional, List, Union
from app.logging_config import central_logger as logger


def try_direct_parse(json_str: str) -> Optional[Dict[str, Any]]:
    """Try direct JSON parsing."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None


def try_extract_object(json_str: str) -> Optional[Dict[str, Any]]:
    """Extract JSON object between braces."""
    if '{' in json_str and '}' in json_str:
        try:
            return json.loads(json_str[json_str.find('{'):json_str.rfind('}') + 1])
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def try_extract_array(json_str: str) -> Optional[List[Any]]:
    """Extract JSON array between brackets."""
    if '[' in json_str and ']' in json_str and '{' not in json_str:
        try:
            return json.loads(json_str[json_str.find('['):json_str.rfind(']') + 1])
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def try_clean_edges(json_str: str) -> Optional[Dict[str, Any]]:
    """Remove non-JSON prefixes/suffixes and retry."""
    try:
        cleaned = re.sub(r'^[^{\[]*|[^}\]]*$', '', json_str, flags=re.MULTILINE | re.DOTALL)
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None


def parse_simple_value(value_str: str) -> Union[str, bool, float, int, None]:
    """Parse simple JSON value."""
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]
    if value_str in ['true', 'false', 'null']:
        return json.loads(value_str)
    if re.match(r'^\d+\.?\d*$', value_str):
        return json.loads(value_str)
    return value_str


def try_parse_complex_value(value_str: str) -> Union[Dict[str, Any], List[Any], str]:
    """Try to parse complex JSON value."""
    try:
        return json.loads(value_str)
    except json.JSONDecodeError:
        pass
    
    from app.agents.utils_json_validators import fix_common_json_errors
    try:
        return json.loads(fix_common_json_errors(value_str))
    except (json.JSONDecodeError, TypeError, ValueError):
        return value_str


def extract_from_markdown(response: str) -> str:
    """Extract content from markdown code blocks."""
    pattern = r'```(?:json)?\s*([\s\S]*?)(?:\s*```|$)'
    match = re.search(pattern, response)
    return match.group(1).strip() if match else response.strip()


def attempt_recovery_parse(json_str: str, closing: str) -> Optional[Dict[str, Any]]:
    """Try parsing with recovery closing sequence."""
    try:
        return json.loads(json_str + closing)
    except json.JSONDecodeError:
        return None


def try_close_truncated_array(content: str) -> Optional[List[Any]]:
    """Try to close and parse truncated array."""
    array_str = '[' + content
    open_braces = array_str.count('{') - array_str.count('}')
    array_str += '}' * open_braces
    if not array_str.rstrip().endswith(']'):
        array_str += ']'
    
    from app.agents.utils_json_validators import fix_common_json_errors
    try:
        return json.loads(fix_common_json_errors(array_str))
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def extract_truncated_array(response: str, field_name: str) -> Optional[List[Any]]:
    """Extract potentially truncated array field."""
    pattern = rf'"{field_name}"\s*:\s*\[([^\]]*)'
    match = re.search(pattern, response, re.DOTALL)
    if not match:
        return None
    return try_close_truncated_array(match.group(1))


def extract_complex_field(response: str, pattern: str) -> Dict[str, Any]:
    """Extract complex JSON fields (objects/arrays)."""
    result = {}
    matches = re.finditer(pattern, response, re.DOTALL)
    for match in matches:
        key, value_str = match.group(1), match.group(2)
        value = try_parse_complex_value(value_str)
        if value is not None:
            result[key] = value
    return result


def extract_with_patterns(response: str, patterns: List[str], existing: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields using regex patterns."""
    result = existing.copy()
    for pattern in patterns:
        for match in re.finditer(pattern, response):
            key = match.group(1)
            if key not in result:
                result[key] = parse_simple_value(match.group(2).strip())
    return result


def extract_simple_fields(response: str, existing: Dict[str, Any]) -> Dict[str, Any]:
    """Extract simple key-value pairs."""
    patterns = [
        r'"([^"]+)"\s*:\s*"([^"]*)"(?=[,}\]])',
        r'"([^"]+)"\s*:\s*(\d+\.?\d*|true|false|null)(?=[,}\]]|\s)',
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*("[^"]*"|[^,}\]\s]+)'
    ]
    return extract_with_patterns(response, patterns, existing)