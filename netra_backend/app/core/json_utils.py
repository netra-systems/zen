"""JSON utilities for datetime serialization in WebSocket communications.

Provides centralized JSON encoding and serialization utilities to handle datetime objects
and other non-JSON-serializable types consistently across the application.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Union
from uuid import UUID

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime, date, Decimal, and UUID objects."""
    
    def default(self, obj: Any) -> Any:
        """Convert non-serializable objects to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


def serialize_for_websocket(data: Union[Dict[str, Any], Any]) -> str:
    """Serialize data for WebSocket transmission with datetime handling.
    
    Args:
        data: Data to serialize
        
    Returns:
        JSON string with datetime objects converted to ISO format
    """
    try:
        return json.dumps(data, cls=DateTimeJSONEncoder, ensure_ascii=False)
    except Exception as e:
        _handle_serialization_error(e)
        raise

def _handle_serialization_error(error: Exception) -> None:
    """Handle serialization error logging."""
    logger.error(f"Failed to serialize data for WebSocket: {error}")


def prepare_websocket_message(message: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    """Prepare message for WebSocket transmission by converting datetime fields.
    
    Args:
        message: Message to prepare
        
    Returns:
        Message with datetime fields converted to ISO strings
    """
    if not isinstance(message, dict):
        return message
    return _prepare_dict_message(message)

def _prepare_dict_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare dictionary message for WebSocket transmission."""
    prepared = {}
    for key, value in message.items():
        prepared[key] = _convert_datetime_fields(value)
    return prepared


def _convert_datetime_fields(value: Any) -> Any:
    """Recursively convert datetime fields to ISO strings."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, dict):
        return _convert_dict_fields(value)
    elif isinstance(value, list):
        return _convert_list_fields(value)
    elif isinstance(value, (Decimal, UUID)):
        return str(value)
    return value

def _convert_dict_fields(value: Dict[str, Any]) -> Dict[str, Any]:
    """Convert datetime fields in dictionary."""
    return {k: _convert_datetime_fields(v) for k, v in value.items()}

def _convert_list_fields(value: List[Any]) -> List[Any]:
    """Convert datetime fields in list."""
    return [_convert_datetime_fields(item) for item in value]


def safe_json_dumps(data: Any, **kwargs) -> str:
    """Safely dump data to JSON string with datetime handling.
    
    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string
    """
    _set_default_kwargs(kwargs)
    return json.dumps(data, **kwargs)

def _set_default_kwargs(kwargs: Dict[str, Any]) -> None:
    """Set default kwargs for JSON dumps."""
    kwargs.setdefault('cls', DateTimeJSONEncoder)
    kwargs.setdefault('ensure_ascii', False)


def validate_json_serializable(data: Any) -> bool:
    """Validate that data can be JSON serialized.
    
    Args:
        data: Data to validate
        
    Returns:
        True if serializable, False otherwise
    """
    try:
        serialize_for_websocket(data)
        return True
    except Exception:
        return False