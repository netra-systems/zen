"""
Shared Serialization Utilities

This module provides unified JSON handling functionality for all services.
"""

from .unified_json_handler import (
    UnifiedJSONHandler,
    UnifiedJSONEncoder,
    JSONError,
    JSONSerializationError,
    JSONDeserializationError,
    JSONFileError,
    safe_json_dumps,
    safe_json_loads,
    safe_json_load_file,
    safe_json_dump_file,
    auth_json_handler,
    backend_json_handler,
    launcher_json_handler,
)

__all__ = [
    'UnifiedJSONHandler',
    'UnifiedJSONEncoder',
    'JSONError',
    'JSONSerializationError',
    'JSONDeserializationError',
    'JSONFileError',
    'safe_json_dumps',
    'safe_json_loads',
    'safe_json_load_file',
    'safe_json_dump_file',
    'auth_json_handler',
    'backend_json_handler',
    'launcher_json_handler',
]