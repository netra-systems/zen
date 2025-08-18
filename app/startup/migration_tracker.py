"""
Migration Tracker for Netra AI Platform.

Implements intelligent migration tracking and execution (GAP-001 CRITICAL).
Maintains 300-line limit and 8-line functions for modular architecture.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import alembic.config
from pydantic import BaseModel, Field

from app.core.exceptions import NetraException
from app.db.migration_utils import (
    create_alembic_config,
    get_current_revision,
    get_head_revision,
    get_sync_database_url,
    needs_migration,
)


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


class MigrationTracker:
    """Intelligent migration tracking and execution manager."""
    
    def __init__(self, database_url: str, environment: str = "dev"):
        self.database_url = database_url
        self.environment = environment
        self.logger = logging.getLogger(__name__)
        self.state_file = Path(".netra/migration_state.json")
        self._ensure_netra_dir()

    def _ensure_netra_dir(self) -> None:
        """Ensure .netra directory exists."""
        self.state_file.parent.mkdir(exist_ok=True)

    async def _load_state(self) -> MigrationState:
        """Load migration state from file."""
        if not self.state_file.exists():
            return MigrationState()
        try:
            content = await self._read_file_async()
            return MigrationState.model_validate(json.loads(content))
        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}")
            return MigrationState()

    async def _read_file_async(self) -> str:
        """Read state file asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.state_file.read_text)

    async def _save_state(self, state: MigrationState) -> None:
        """Save migration state to file."""
        try:
            content = state.model_dump_json(indent=2)
            await self._write_file_async(content)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    async def _write_file_async(self, content: str) -> None:
        """Write state file asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.state_file.write_text, content)

    def _get_alembic_config(self) -> alembic.config.Config:
        """Get Alembic configuration."""
        sync_url = get_sync_database_url(self.database_url)
        return create_alembic_config(sync_url)

    async def check_migrations(self) -> MigrationState:
        """Check for pending migrations."""
        state = await self._load_state()
        try:
            cfg = self._get_alembic_config()
            await self._update_migration_state(cfg, state)
            return state
        except Exception as e:
            await self._handle_migration_check_error(state, e)

    async def _update_migration_state(self, cfg: alembic.config.Config, state: MigrationState) -> None:
        """Update migration state with current and head revisions."""
        current = self._get_current_safely(cfg)
        head = get_head_revision(cfg)
        state.current_version = current
        state.last_check = datetime.now()
        self._set_pending_migrations(state, current, head)
        await self._save_state(state)

    def _set_pending_migrations(self, state: MigrationState, current: Optional[str], head: str) -> None:
        """Set pending migrations based on current and head revisions."""
        if needs_migration(current, head):
            state.pending_migrations = [head]
        else:
            state.pending_migrations = []

    async def _handle_migration_check_error(self, state: MigrationState, error: Exception) -> None:
        """Handle migration check errors."""
        self.logger.error(f"Migration check failed: {error}")
        await self._record_failure(state, "CHECK_FAILED", str(error))
        raise NetraException(f"Migration check failed: {error}")

    def _get_current_safely(self, cfg: alembic.config.Config) -> Optional[str]:
        """Get current revision safely."""
        try:
            sync_url = get_sync_database_url(self.database_url)
            return get_current_revision(sync_url)
        except Exception as e:
            self.logger.warning(f"Could not get current revision: {e}")
            return None

    async def _record_failure(self, state: MigrationState, migration_id: str, 
                            error: str) -> None:
        """Record migration failure."""
        failure = FailedMigration(
            migration_id=migration_id,
            error_message=error
        )
        state.failed_migrations.append(failure)
        await self._save_state(state)

    async def run_migrations(self, force: bool = False) -> bool:
        """Run pending migrations with failure handling."""
        state = await self.check_migrations()
        should_run = self._check_migration_conditions(state, force)
        if not should_run:
            return self._handle_migration_skip(state, force)
        return await self._execute_migrations(state)

    def _check_migration_conditions(self, state: MigrationState, force: bool) -> bool:
        """Check if migrations should run."""
        has_pending = bool(state.pending_migrations)
        should_auto_run = self._should_auto_run(state)
        return has_pending or (should_auto_run and force)

    def _handle_migration_skip(self, state: MigrationState, force: bool) -> bool:
        """Handle migration skip scenarios."""
        if not state.pending_migrations and not force:
            self.logger.info("No pending migrations")
            return True
        self.logger.info("Auto-run disabled, skipping migrations")
        return False

    def _should_auto_run(self, state: MigrationState) -> bool:
        """Check if migrations should auto-run."""
        if not state.auto_run_enabled:
            return False
        if self.environment != "dev":
            return False
        if state.failed_migrations:
            return False
        return True

    async def _execute_migrations(self, state: MigrationState) -> bool:
        """Execute migrations with error handling."""
        try:
            self.logger.info("Executing migrations...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_alembic_upgrade)
            
            state.applied_migrations.extend(state.pending_migrations)
            state.pending_migrations.clear()
            await self._save_state(state)
            
            self.logger.info("Migrations completed successfully")
            return True
        except Exception as e:
            await self._record_failure(state, "MIGRATION_EXECUTION", str(e))
            self.logger.error(f"Migration execution failed: {e}")
            return False

    def _run_alembic_upgrade(self) -> None:
        """Run Alembic upgrade command."""
        cfg = self._get_alembic_config()
        alembic.command.upgrade(cfg, "head")

    async def rollback_migration(self, steps: int = 1) -> bool:
        """Rollback migrations by specified steps."""
        try:
            self.logger.info(f"Rolling back {steps} migration(s)")
            loop = asyncio.get_event_loop()
            target = f"-{steps}"
            await loop.run_in_executor(None, self._run_alembic_downgrade, target)
            
            state = await self._load_state()
            state.current_version = None  # Force refresh on next check
            await self._save_state(state)
            
            self.logger.info("Rollback completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False

    def _run_alembic_downgrade(self, target: str) -> None:
        """Run Alembic downgrade command."""
        cfg = self._get_alembic_config()
        alembic.command.downgrade(cfg, target)

    async def validate_schema(self) -> bool:
        """Validate database schema integrity."""
        try:
            state = await self.check_migrations()
            if state.pending_migrations:
                self.logger.warning("Schema validation: pending migrations found")
                return False
            if state.failed_migrations:
                self.logger.warning("Schema validation: failed migrations found")
                return False
            self.logger.info("Schema validation: passed")
            return True
        except Exception as e:
            self.logger.error(f"Schema validation failed: {e}")
            return False

    async def get_migration_status(self) -> Dict[str, any]:
        """Get comprehensive migration status."""
        state = await self.check_migrations()
        return {
            "current_version": state.current_version,
            "pending_count": len(state.pending_migrations),
            "failed_count": len(state.failed_migrations),
            "last_check": state.last_check,
            "auto_run_enabled": state.auto_run_enabled,
            "environment": self.environment
        }

    async def clear_failed_migrations(self) -> None:
        """Clear failed migration records."""
        state = await self._load_state()
        state.failed_migrations.clear()
        await self._save_state(state)
        self.logger.info("Cleared failed migration records")

    async def disable_auto_run(self) -> None:
        """Disable automatic migration execution."""
        state = await self._load_state()
        state.auto_run_enabled = False
        await self._save_state(state)
        self.logger.info("Auto-run disabled")

    async def enable_auto_run(self) -> None:
        """Enable automatic migration execution."""
        state = await self._load_state()
        state.auto_run_enabled = True
        await self._save_state(state)
        self.logger.info("Auto-run enabled")


# Import Alembic command module for migration execution
import alembic.command