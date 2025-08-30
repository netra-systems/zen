"""
JSON utilities for serialization, deserialization, and circular reference handling.

Provides centralized JSON operations including custom serialization,
circular reference detection, and safe JSON processing.
"""

import json
import weakref
from typing import Any, Dict, Set
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from netra_backend.app.core.json_utils import (
    DateTimeJSONEncoder,
    serialize_for_websocket,
    safe_json_dumps,
    validate_json_serializable
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class JsonUtils:
    """Utility class for JSON operations and serialization."""
    
    def __init__(self):
        """Initialize JSON utilities."""
        self._circular_refs: Set[int] = set()
    
    def serialize(self, data: Any, custom_encoder: bool = False, max_depth: int = 100) -> str:
        """Serialize data to JSON string with custom handling.
        
        Args:
            data: Data to serialize
            custom_encoder: Whether to use custom encoder for objects
            max_depth: Maximum recursion depth
            
        Returns:
            JSON string
        """
        try:
            if custom_encoder:
                return self._serialize_with_custom_encoder(data, max_depth)
            else:
                return safe_json_dumps(data)
        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            return self._fallback_serialize(data)
    
    def _serialize_with_custom_encoder(self, data: Any, max_depth: int) -> str:
        """Serialize with custom encoder for objects."""
        class CustomObjectEncoder(DateTimeJSONEncoder):
            def default(self, obj):
                # Handle custom objects by converting to dict
                if hasattr(obj, '__dict__'):
                    return {
                        key: value for key, value in obj.__dict__.items()
                        if not key.startswith('_')
                    }
                return super().default(obj)
        
        return json.dumps(data, cls=CustomObjectEncoder, ensure_ascii=False)
    
    def _fallback_serialize(self, data: Any) -> str:
        """Fallback serialization for problematic data."""
        try:
            return json.dumps(str(data), ensure_ascii=False)
        except Exception:
            return '"[Serialization Error]"'
    
    def deserialize(self, json_str: str) -> Any:
        """Deserialize JSON string to Python object.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Deserialized Python object
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON deserialization failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected deserialization error: {e}")
            return None
    
    def serialize_safe(self, data: Any, max_depth: int = 50) -> str:
        """Safely serialize data with circular reference handling.
        
        Args:
            data: Data to serialize
            max_depth: Maximum recursion depth
            
        Returns:
            JSON string with circular references handled
        """
        self._circular_refs.clear()
        try:
            safe_data = self._handle_circular_refs(data, 0, max_depth)
            return safe_json_dumps(safe_data)
        except Exception as e:
            logger.error(f"Safe serialization failed: {e}")
            return '"[Safe Serialization Error]"'
        finally:
            self._circular_refs.clear()
    
    def _handle_circular_refs(self, obj: Any, depth: int, max_depth: int) -> Any:
        """Handle circular references in data structures."""
        if depth > max_depth:
            return "[Max Depth Exceeded]"
        
        obj_id = id(obj)
        
        if obj_id in self._circular_refs:
            return "[Circular Reference]"
        
        if isinstance(obj, (dict, list)):
            self._circular_refs.add(obj_id)
            try:
                if isinstance(obj, dict):
                    return self._handle_dict_circular_refs(obj, depth, max_depth)
                else:
                    return self._handle_list_circular_refs(obj, depth, max_depth)
            finally:
                self._circular_refs.discard(obj_id)
        
        return obj
    
    def _handle_dict_circular_refs(self, obj: Dict[Any, Any], depth: int, max_depth: int) -> Dict[Any, Any]:
        """Handle circular references in dictionaries."""
        result = {}
        for key, value in obj.items():
            try:
                result[key] = self._handle_circular_refs(value, depth + 1, max_depth)
            except Exception:
                result[key] = "[Processing Error]"
        return result
    
    def _handle_list_circular_refs(self, obj: list, depth: int, max_depth: int) -> list:
        """Handle circular references in lists."""
        result = []
        for item in obj:
            try:
                result.append(self._handle_circular_refs(item, depth + 1, max_depth))
            except Exception:
                result.append("[Processing Error]")
        return result
    
    def validate(self, data: Any) -> bool:
        """Validate that data can be JSON serialized.
        
        Args:
            data: Data to validate
            
        Returns:
            True if serializable, False otherwise
        """
        return validate_json_serializable(data)
    
    def pretty_format(self, data: Any, indent: int = 2) -> str:
        """Format data as pretty-printed JSON.
        
        Args:
            data: Data to format
            indent: Number of spaces for indentation
            
        Returns:
            Pretty-formatted JSON string
        """
        try:
            return json.dumps(data, cls=DateTimeJSONEncoder, indent=indent, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Pretty formatting failed: {e}")
            return str(data)
    
    def minify(self, json_str: str) -> str:
        """Minify JSON string by removing whitespace.
        
        Args:
            json_str: JSON string to minify
            
        Returns:
            Minified JSON string
        """
        try:
            data = json.loads(json_str)
            return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        except Exception as e:
            logger.error(f"JSON minification failed: {e}")
            return json_str
    
    def merge_json_objects(self, obj1: Dict[str, Any], obj2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two JSON objects.
        
        Args:
            obj1: First JSON object
            obj2: Second JSON object
            
        Returns:
            Merged JSON object
        """
        if not isinstance(obj1, dict) or not isinstance(obj2, dict):
            logger.error("Both objects must be dictionaries")
            return obj1 or {}
        
        result = obj1.copy()
        result.update(obj2)
        return result