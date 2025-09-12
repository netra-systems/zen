"""
Validation utilities for schema operations.

Provides common validation functions to ensure all schema validators
follow the 25-line function limit while maintaining consistency.
Maximum 300 lines per conventions.xml, each function  <= 8 lines.
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Union


def validate_positive_number(value: Union[int, float], field_name: str) -> Union[int, float]:
    """Validate value is positive number."""
    if value < 0:
        raise ValueError(f'{field_name} must be non-negative')
    return value


def validate_range(value: Union[int, float], min_val: Union[int, float], 
                  max_val: Union[int, float], field_name: str) -> Union[int, float]:
    """Validate value is within specified range."""
    if not min_val <= value <= max_val:
        raise ValueError(f'{field_name} must be between {min_val} and {max_val}')
    return value


def validate_string_length(value: str, max_length: int, field_name: str) -> str:
    """Validate string does not exceed maximum length."""
    if len(value) > max_length:
        raise ValueError(f'{field_name} exceeds maximum length of {max_length}')
    return value


def validate_non_empty_string(value: str, field_name: str) -> str:
    """Validate string is not empty or whitespace only."""
    if not value or not value.strip():
        raise ValueError(f'{field_name} cannot be empty')
    return value.strip()


def validate_list_not_empty(value: List[Any], field_name: str) -> List[Any]:
    """Validate list is not empty."""
    if not value:
        raise ValueError(f'{field_name} cannot be empty')
    return value


def validate_dict_not_empty(value: Dict[str, Any], field_name: str) -> Dict[str, Any]:
    """Validate dictionary is not empty."""
    if not value:
        raise ValueError(f'{field_name} cannot be empty')
    return value


def validate_percentage(value: float, field_name: str) -> float:
    """Validate value is a valid percentage (0-100)."""
    return validate_range(value, 0.0, 100.0, field_name)


def validate_probability(value: float, field_name: str) -> float:
    """Validate value is a valid probability (0-1)."""
    return validate_range(value, 0.0, 1.0, field_name)


def validate_timestamp_not_future(value: datetime, field_name: str) -> datetime:
    """Validate timestamp is not in the future."""
    if value > datetime.now(UTC):
        raise ValueError(f'{field_name} cannot be in the future')
    return value


def create_validation_error(field: str, message: str) -> Dict[str, str]:
    """Create standardized validation error."""
    return _build_error_dict(field, message)

def _build_error_dict(field: str, message: str) -> Dict[str, str]:
    """Build error dictionary with timestamp."""
    return {
        'field': field, 'message': message,
        'timestamp': datetime.now(UTC).isoformat()
    }


def validate_uuid_format(value: str, field_name: str) -> str:
    """Validate string is valid UUID format."""
    try:
        _validate_uuid_value(value)
        return value
    except ValueError:
        _raise_uuid_error(field_name)

def _validate_uuid_value(value: str) -> None:
    """Validate UUID value using uuid module."""
    import uuid
    uuid.UUID(value)


def _raise_uuid_error(field_name: str) -> None:
    """Raise UUID validation error."""
    raise ValueError(f'{field_name} must be valid UUID format')


def sanitize_input_string(value: str, max_length: Optional[int] = None) -> str:
    """Sanitize input string by trimming and length validation."""
    sanitized = value.strip()
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


def validate_enum_value(value: Any, enum_class: type, field_name: str) -> Any:
    """Validate value is valid enum member."""
    if value not in enum_class:
        valid_values = [e.value for e in enum_class]
        raise ValueError(f'{field_name} must be one of: {valid_values}')
    return value


def validate_json_string(value: Any, field_name: str) -> Any:
    """Validate value is JSON serializable."""
    try:
        _test_json_serialization(value)
        return value
    except (TypeError, ValueError):
        _raise_json_error(field_name)

def _test_json_serialization(value: Any) -> None:
    """Test if value can be JSON serialized."""
    import json
    json.dumps(value)


def _raise_json_error(field_name: str) -> None:
    """Raise JSON serialization error."""
    raise ValueError(f'{field_name} must be JSON serializable')


def create_field_validator(validator_func, **kwargs):
    """Create field validator function with bound parameters."""
    def validator(cls, v):
        return validator_func(v, **kwargs)
    return validator


def validate_nested_dict_structure(value: Dict[str, Any], required_keys: List[str], 
                                  field_name: str) -> Dict[str, Any]:
    """Validate nested dictionary has required keys."""
    missing_keys = _find_missing_keys(value, required_keys)
    if missing_keys:
        raise ValueError(f'{field_name} missing required keys: {missing_keys}')
    return value

def _find_missing_keys(value: Dict[str, Any], required_keys: List[str]) -> List[str]:
    """Find keys that are missing from dictionary."""
    return [key for key in required_keys if key not in value]


# Type conversion utilities ( <= 8 lines each)

def safe_str_to_int(value: str, default: int = 0) -> int:
    """Safely convert string to integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str_to_float(value: str, default: float = 0.0) -> float:
    """Safely convert string to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str_to_bool(value: str, default: bool = False) -> bool:
    """Safely convert string to boolean."""
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value) if value is not None else default


def normalize_dict_keys(data: Dict[str, Any], lowercase: bool = True) -> Dict[str, Any]:
    """Normalize dictionary keys to consistent format."""
    if lowercase:
        return {k.lower().strip(): v for k, v in data.items()}
    return {k.strip(): v for k, v in data.items()}


def extract_numeric_value(value: Any, field_name: str) -> Union[int, float]:
    """Extract numeric value from mixed input."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return safe_str_to_float(value.strip())
    _raise_numeric_error(field_name)

def _raise_numeric_error(field_name: str) -> None:
    """Raise numeric value error."""
    raise ValueError(f'{field_name} must be numeric')


def validate_metadata_structure(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Validate metadata follows expected structure."""
    if not isinstance(metadata, dict):
        raise ValueError('metadata must be a dictionary')
    # Ensure all values are JSON serializable
    return validate_json_string(metadata, 'metadata')


def create_default_metadata() -> Dict[str, Any]:
    """Create default metadata structure."""
    return _build_default_metadata_dict()

def _build_default_metadata_dict() -> Dict[str, Any]:
    """Build default metadata dictionary."""
    timestamp = datetime.now(UTC).isoformat()
    return {'created_at': timestamp, 'version': '1.0', 'source': 'schema_validation'}


# Collection utilities ( <= 8 lines each)

def merge_dicts_safe(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Safely merge two dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result


def filter_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Filter out None values from dictionary."""
    return {k: v for k, v in data.items() if v is not None}


def ensure_list(value: Any) -> List[Any]:
    """Ensure value is a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def deduplicate_list(items: List[Any]) -> List[Any]:
    """Remove duplicates from list while preserving order."""
    seen, result = set(), []
    for item in items:
        _add_unique_item(item, seen, result)
    return result


def _add_unique_item(item: Any, seen: set, result: List[Any]) -> None:
    """Add item to result if not already seen."""
    if item not in seen:
        seen.add(item)
        result.append(item)