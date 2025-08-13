"""
Schema Sync Data Models

Pydantic models and enums for schema synchronization.
Maintains type safety under 300-line limit.
"""

from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class SchemaValidationLevel(Enum):
    """Schema validation levels."""
    STRICT = "strict"
    MODERATE = "moderate"  
    LENIENT = "lenient"


@dataclass
class SchemaChangeInfo:
    """Information about schema changes."""
    schema_name: str
    change_type: str  # added, removed, modified
    field_name: Optional[str] = None
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SyncReport:
    """Report of schema synchronization."""
    timestamp: datetime
    schemas_processed: int
    changes_detected: List[SchemaChangeInfo]
    validation_errors: List[str]
    files_generated: List[str]
    success: bool