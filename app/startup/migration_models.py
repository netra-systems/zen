"""
Migration Models for Netra AI Platform.

Pydantic models for migration tracking and state management.
Extracted from migration_tracker.py for 300-line compliance.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FailedMigration(BaseModel):
    """Failed migration record with error details."""
    
    migration_id: str = Field(..., description="Migration identifier")
    error_message: str = Field(..., description="Error details")
    timestamp: datetime = Field(default_factory=datetime.now)
    stack_trace: Optional[str] = Field(None, description="Full stack trace")


class MigrationState(BaseModel):
    """Migration state tracking model."""
    
    current_version: Optional[str] = Field(None, description="Current DB revision")
    applied_migrations: List[str] = Field(default_factory=list)
    pending_migrations: List[str] = Field(default_factory=list)
    failed_migrations: List[FailedMigration] = Field(default_factory=list)
    last_check: Optional[datetime] = Field(None, description="Last check timestamp")
    auto_run_enabled: bool = Field(True, description="Auto-run in dev environment")