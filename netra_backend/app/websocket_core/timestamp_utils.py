"""
WebSocket Timestamp Conversion Utilities

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Chat Infrastructure Stability
- Value Impact: Prevents WebSocket message parsing failures that break AI chat interactions
- Strategic Impact: Ensures 90% of business value (chat) remains functional

SSOT timestamp conversion functions to handle multiple input formats
and convert to Unix timestamp floats as expected by WebSocketMessage model.
"""

import time
from datetime import datetime, timezone
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)


def convert_to_unix_timestamp(timestamp_input: Union[str, int, float, datetime, None]) -> float:
    """
    Convert various timestamp formats to Unix timestamp float.
    
    Supports:
    - None -> current time
    - Unix timestamps (int/float) -> pass through as float
    - ISO datetime strings -> parse and convert
    - datetime objects -> convert to timestamp
    
    Args:
        timestamp_input: Timestamp in various formats
        
    Returns:
        float: Unix timestamp
        
    Raises:
        ValueError: If timestamp format is invalid
    """
    # Handle None case - use current time
    if timestamp_input is None:
        return time.time()
    
    # Handle numeric timestamps (already Unix format)
    if isinstance(timestamp_input, (int, float)):
        return float(timestamp_input)
    
    # Handle datetime objects
    if isinstance(timestamp_input, datetime):
        return timestamp_input.timestamp()
    
    # Handle string timestamps
    if isinstance(timestamp_input, str):
        return _parse_string_timestamp(timestamp_input)
    
    # Unknown type - log warning and use current time
    logger.warning(
        f"Unknown timestamp type {type(timestamp_input)}: {timestamp_input}. "
        f"Using current time as fallback."
    )
    return time.time()


def _parse_string_timestamp(timestamp_str: str) -> float:
    """
    Parse string timestamp to Unix float.
    
    Supported formats:
    - ISO 8601: '2025-09-08T16:50:01.447585'
    - ISO with timezone: '2025-09-08T16:50:01.447585Z'
    - ISO with timezone offset: '2025-09-08T16:50:01.447585+00:00'
    - Unix timestamp string: '1693567801.447585'
    
    Args:
        timestamp_str: String timestamp
        
    Returns:
        float: Unix timestamp
        
    Raises:
        ValueError: If string format is invalid
    """
    timestamp_str = timestamp_str.strip()
    
    # Try parsing as numeric string first (Unix timestamp)
    try:
        return float(timestamp_str)
    except ValueError:
        pass
    
    # Try parsing as ISO datetime string
    try:
        return _parse_iso_datetime(timestamp_str)
    except (ValueError, TypeError):
        pass
    
    # All parsing attempts failed
    logger.error(f"Failed to parse timestamp string: '{timestamp_str}'")
    raise ValueError(
        f"Unable to parse timestamp string '{timestamp_str}'. "
        f"Expected ISO format (2025-09-08T16:50:01.447585) or Unix timestamp."
    )


def _parse_iso_datetime(iso_string: str) -> float:
    """
    Parse ISO datetime string to Unix timestamp.
    
    Handles various ISO 8601 formats with/without timezone info.
    
    Args:
        iso_string: ISO format datetime string
        
    Returns:
        float: Unix timestamp
        
    Raises:
        ValueError: If ISO format is invalid
    """
    # Remove timezone suffix variations for parsing
    iso_clean = iso_string
    
    # Handle 'Z' suffix (Zulu time)
    if iso_clean.endswith('Z'):
        iso_clean = iso_clean[:-1] + '+00:00'
    
    # Handle timezone offset formats
    if '+' in iso_clean or iso_clean.count('-') > 2:
        try:
            dt = datetime.fromisoformat(iso_clean)
        except ValueError:
            # Fallback: assume UTC if timezone parsing fails
            dt = datetime.fromisoformat(iso_clean.split('+')[0].split('-')[0:3])
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        # No timezone info - assume UTC for consistency
        dt = datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.timestamp()


def safe_convert_timestamp(
    timestamp_input: Union[str, int, float, datetime, None], 
    fallback_to_current: bool = True
) -> Optional[float]:
    """
    Safely convert timestamp with optional fallback to current time.
    
    This version won't raise exceptions and provides graceful error handling
    for use in WebSocket message processing where stability is critical.
    
    Args:
        timestamp_input: Timestamp in various formats
        fallback_to_current: If True, use current time on parsing errors
        
    Returns:
        float: Unix timestamp, or None if parsing failed and fallback disabled
    """
    try:
        return convert_to_unix_timestamp(timestamp_input)
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(
            f"Timestamp conversion failed for '{timestamp_input}': {e}. "
            f"Fallback={'current time' if fallback_to_current else 'None'}"
        )
        
        if fallback_to_current:
            return time.time()
        return None


def validate_timestamp_format(timestamp_input: Union[str, int, float, datetime, None]) -> bool:
    """
    Validate if timestamp input can be successfully converted.
    
    Args:
        timestamp_input: Timestamp to validate
        
    Returns:
        bool: True if timestamp can be converted, False otherwise
    """
    try:
        convert_to_unix_timestamp(timestamp_input)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


# Performance optimization: Cache common timestamp patterns
_TIMESTAMP_CACHE = {}
_CACHE_SIZE_LIMIT = 100


def cached_convert_timestamp(timestamp_input: Union[str, int, float, datetime, None]) -> float:
    """
    Convert timestamp with simple caching for performance optimization.
    
    Only caches string timestamps to avoid memory overhead for other types.
    
    Args:
        timestamp_input: Timestamp in various formats
        
    Returns:
        float: Unix timestamp
    """
    # Only cache string inputs to avoid memory overhead
    if isinstance(timestamp_input, str) and timestamp_input in _TIMESTAMP_CACHE:
        return _TIMESTAMP_CACHE[timestamp_input]
    
    result = convert_to_unix_timestamp(timestamp_input)
    
    # Cache string results with size limit
    if isinstance(timestamp_input, str) and len(_TIMESTAMP_CACHE) < _CACHE_SIZE_LIMIT:
        _TIMESTAMP_CACHE[timestamp_input] = result
    
    return result