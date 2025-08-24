"""
Serialization Utilities for Netra Backend

This module provides JSON serialization functionality for the backend service.
"""

from netra_backend.app.core.serialization.unified_json_handler import (
    UnifiedJSONHandler,
    JSONSerializerConfig,
    serialize_json,
    deserialize_json,
    validate_json_schema,
    default_json_handler,
)

__all__ = [
    'UnifiedJSONHandler',
    'JSONSerializerConfig',
    'serialize_json',
    'deserialize_json',
    'validate_json_schema',
    'default_json_handler',
]