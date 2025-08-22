"""
Migration State Management Helper.

Helper functions for migration state file operations.
Extracted from migration_tracker.py for 450-line compliance.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

from netra_backend.app.migration_models import MigrationState


class MigrationStateManager:
    """Handles migration state file operations."""
    
    def __init__(self, state_file: Path, logger: logging.Logger):
        self.state_file = state_file
        self.logger = logger
    
    async def load_state(self) -> MigrationState:
        """Load migration state from file."""
        if not self.state_file.exists():
            return MigrationState()
        return await self._load_existing_state()
    
    async def _load_existing_state(self) -> MigrationState:
        """Load existing state file with error handling."""
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
    
    async def save_state(self, state: MigrationState) -> None:
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
    
    def build_status_dict(self, state: MigrationState, environment: str) -> Dict[str, any]:
        """Build migration status dictionary."""
        base_info = self._get_base_status_info(state)
        runtime_info = self._get_runtime_status_info(state, environment)
        return {**base_info, **runtime_info}
    
    def _get_base_status_info(self, state: MigrationState) -> Dict[str, any]:
        """Get base status information."""
        return {
            "current_version": state.current_version,
            "pending_count": len(state.pending_migrations),
            "failed_count": len(state.failed_migrations)
        }
    
    def _get_runtime_status_info(self, state: MigrationState, environment: str) -> Dict[str, any]:
        """Get runtime status information."""
        return {
            "last_check": state.last_check,
            "auto_run_enabled": state.auto_run_enabled,
            "environment": environment
        }