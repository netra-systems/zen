"""
Corpus creation I/O module.

Provides I/O functions for corpus creation operations.
This module has been removed but tests still reference it.
"""

import json
from typing import Any, Optional


def parse_json(json_string: str) -> Optional[dict]:
    """
    Parse JSON string.
    
    Args:
        json_string: JSON string to parse
        
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return None


def validate_array(data: Any) -> bool:
    """
    Validate if data is an array/list.
    
    Args:
        data: Data to validate
        
    Returns:
        True if data is a list, False otherwise
    """
    return isinstance(data, list)