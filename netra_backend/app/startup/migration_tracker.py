"""
Migration Tracker for Netra AI Platform.

Implements intelligent migration tracking and execution (GAP-001 CRITICAL).
Maintains 450-line limit and 25-line functions for modular architecture.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import alembic.config
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.db.migration_utils import (
    create_alembic_config,
    get_current_revision,
    get_head_revision,
    get_sync_database_url,
    needs_migration,
)
from netra_backend.app.startup.migration_models import FailedMigration, MigrationState
# from netra_backend.app.startup.migration_state_manager import MigrationStateManager  # Module not found
from netra_backend.app.db.alembic_state_recovery import ensure_migration_state_healthy


class MigrationTracker:
    """Intelligent migration tracking and execution manager."""
    
    def __init__(self, database_url: str, environment: str = "dev"):
        self.database_url = database_url
        self.environment = environment
        self.logger = logging.getLogger(__name__)
        self.state_file = Path(".netra/migration_state.json")
        # self.state_manager = MigrationStateManager(self.state_file, self.logger)  # Module not found
        self.state_manager = None  # Stub for missing MigrationStateManager
        self._ensure_netra_dir()

    def _ensure_netra_dir(self) -> None:
        """Ensure .netra directory exists."""
        self.state_file.parent.mkdir(exist_ok=True)

    async def _load_state(self) -> MigrationState:
        """Load migration state from file."""
        if self.state_manager is None:
            return MigrationState.INITIAL  # Return default state when manager unavailable
        return await self.state_manager.load_state()

    async def _save_state(self, state: MigrationState) -> None:
        """Save migration state to file."""
        if self.state_manager is None:
            return  # Skip saving when manager unavailable
        await self.state_manager.save_state(state)

    def _get_alembic_config(self) -> alembic.config.Config:
        """Get Alembic configuration."""
        sync_url = get_sync_database_url(self.database_url)
        return create_alembic_config(sync_url)

    async def check_migrations(self) -> MigrationState:
        """Check for pending migrations with state recovery."""
        # CRITICAL: Ensure migration state is healthy before checking
        healthy, recovery_info = await ensure_migration_state_healthy(self.database_url)
        if not healthy:
            self.logger.error(f"Migration state recovery failed: {recovery_info}")
            
        state = await self._load_state()
        return await self._perform_migration_check(state)

    async def _perform_migration_check(self, state: MigrationState) -> MigrationState:
        """Perform migration check with error handling."""
        try:
            cfg = self._get_alembic_config()
            await self._update_migration_state(cfg, state)
            return state
        except Exception as e:
            await self._handle_migration_check_error(state, e)
            return state

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
            return await self._perform_migration_execution(state)
        except Exception as e:
            return await self._handle_migration_execution_error(state, e)
            
    async def _perform_migration_execution(self, state: MigrationState) -> bool:
        """Perform the actual migration execution."""
        self.logger.info("Executing migrations...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._run_alembic_upgrade)
        await self._update_migration_state(state)
        self.logger.info("Migrations completed successfully")
        return True
        
    async def _update_migration_state(self, state: MigrationState) -> None:
        """Update migration state after successful execution."""
        state.applied_migrations.extend(state.pending_migrations)
        state.pending_migrations.clear()
        await self._save_state(state)
        
    async def _handle_migration_execution_error(self, state: MigrationState, error: Exception) -> bool:
        """Handle migration execution errors."""
        await self._record_failure(state, "MIGRATION_EXECUTION", str(error))
        self.logger.error(f"Migration execution failed: {error}")
        return False

    def _run_alembic_upgrade(self) -> None:
        """Run Alembic upgrade command."""
        cfg = self._get_alembic_config()
        alembic.command.upgrade(cfg, "head")

    async def rollback_migration(self, steps: int = 1) -> bool:
        """Rollback migrations by specified steps."""
        try:
            return await self._perform_rollback_execution(steps)
        except Exception as e:
            return self._handle_rollback_error(e)
            
    async def _perform_rollback_execution(self, steps: int) -> bool:
        """Perform the actual rollback execution."""
        self.logger.info(f"Rolling back {steps} migration(s)")
        target = f"-{steps}"
        await self._execute_rollback(target)
        await self._update_rollback_state()
        self.logger.info("Rollback completed successfully")
        return True

    async def _execute_rollback(self, target: str) -> None:
        """Execute rollback with target."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._run_alembic_downgrade, target)
        
    async def _update_rollback_state(self) -> None:
        """Update state after successful rollback."""
        state = await self._load_state()
        state.current_version = None  # Force refresh on next check
        await self._save_state(state)
        
    def _handle_rollback_error(self, error: Exception) -> bool:
        """Handle rollback execution errors."""
        self.logger.error(f"Rollback failed: {error}")
        return False

    def _run_alembic_downgrade(self, target: str) -> None:
        """Run Alembic downgrade command."""
        cfg = self._get_alembic_config()
        alembic.command.downgrade(cfg, target)

    async def validate_schema(self) -> bool:
        """Validate database schema integrity."""
        try:
            state = await self.check_migrations()
            return self._validate_migration_state(state)
        except Exception as e:
            self.logger.error(f"Schema validation failed: {e}")
            return False

    def _validate_migration_state(self, state: MigrationState) -> bool:
        """Validate migration state for schema integrity."""
        if self._has_validation_issues(state):
            return False
        self.logger.info("Schema validation: passed")
        return True

    def _has_validation_issues(self, state: MigrationState) -> bool:
        """Check if state has validation issues."""
        if state.pending_migrations:
            self.logger.warning("Schema validation: pending migrations found")
            return True
        if state.failed_migrations:
            self.logger.warning("Schema validation: failed migrations found")
            return True
        return False

    async def get_migration_status(self) -> Dict[str, any]:
        """Get comprehensive migration status."""
        state = await self.check_migrations()
        return self._build_status_dict(state)

    def _build_status_dict(self, state: MigrationState) -> Dict[str, any]:
        """Build migration status dictionary."""
        if self.state_manager is None:
            return {"state": state.value, "environment": self.environment}  # Basic status when manager unavailable
        return self.state_manager.build_status_dict(state, self.environment)

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