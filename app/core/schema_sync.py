"""
Enhanced Schema Synchronization System - Legacy Compatibility Module

This module maintains backward compatibility while delegating to the new
modular schema_sync package. All functionality has been moved to focused
modules under 300 lines each.
"""

# Import from modular implementation
from .schema_sync import (
    SchemaValidationLevel,
    SchemaChangeInfo,
    SyncReport,
    SchemaExtractor,
    TypeScriptGenerator,
    SchemaValidator,
    SchemaSynchronizer,
    validate_schema,
    is_migration_safe,
    create_sync_command
)

# Maintain backward compatibility - all legacy code removed
# All classes and functions now imported from schema_sync module

__all__ = [
    "SchemaValidationLevel",
    "SchemaChangeInfo",
    "SyncReport", 
    "SchemaExtractor",
    "TypeScriptGenerator",
    "SchemaValidator",
    "SchemaSynchronizer",
    "validate_schema",
    "is_migration_safe",
    "create_sync_command"
]