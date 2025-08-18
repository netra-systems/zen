"""
Startup Status Manager - GAP-005 Implementation

Persistent tracking of startup state and history with atomic file operations.
Implements requirements from SPEC/startup_coverage.xml.

CRITICAL ARCHITECTURAL COMPLIANCE:
- ALL functions MUST be ≤8 lines (MANDATORY)
- File MUST be ≤300 lines total
- Strong typing with Pydantic models
- Atomic file operations with proper error handling
- Concurrent access support with file locking

Usage:
    manager = StartupStatusManager()
    await manager.load_status()
    await manager.save_startup_event(success=True, duration_ms=5000)
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from app.schemas.startup_types import (
    StartupStatus, LastStartup, MigrationStatus, ServiceConfig,
    CrashEntry, HealthCheckHistory, StartupEvent, ServiceType, Environment
)
from app.core.exceptions_file import FileError, FileNotFoundError, DataParsingError
from app.core.exceptions_base import NetraException


class StartupStatusManager:
    """Manages persistent startup status with atomic operations."""
    
    def __init__(self, status_path: str = ".netra/startup_status.json"):
        self.status_path = Path(status_path)
        self.status: Optional[StartupStatus] = None
        self._lock_file_path = Path(f"{status_path}.lock")

    async def load_status(self) -> StartupStatus:
        """Load startup status with fallback to create new."""
        try:
            return await self._load_existing_status()
        except (FileNotFoundError, DataParsingError):
            return await self._create_new_status()

    async def save_status(self) -> None:
        """Save current status with atomic write."""
        if not self.status:
            raise NetraException("No status to save")
        await self._atomic_write(self.status.model_dump(mode='json'))

    async def validate_status(self) -> bool:
        """Validate status file integrity."""
        try:
            await self.load_status()
            return True
        except Exception:
            return False

    async def save_startup_event(self, success: bool, duration_ms: int, 
                                environment: Environment = Environment.DEV,
                                errors: List[str] = None, warnings: List[str] = None) -> None:
        """Record a startup event."""
        await self._ensure_status_loaded()
        startup_data = self._create_startup_data(success, duration_ms, environment, errors, warnings)
        self.status.last_startup = startup_data
        await self.save_status()

    def _create_startup_data(self, success: bool, duration_ms: int, environment: Environment,
                            errors: Optional[List[str]], warnings: Optional[List[str]]) -> LastStartup:
        """Create LastStartup data object."""
        return LastStartup(
            timestamp=datetime.now(timezone.utc), success=success,
            duration_ms=duration_ms, environment=environment,
            errors=errors or [], warnings=warnings or []
        )

    async def record_crash(self, service: ServiceType, error: str,
                          stack_trace: Optional[str] = None,
                          recovery_attempted: bool = False,
                          recovery_success: bool = False) -> None:
        """Record a service crash."""
        await self._ensure_status_loaded()
        crash = self._create_crash_entry(service, error, stack_trace, recovery_attempted, recovery_success)
        self.status.crash_history.append(crash)
        await self.save_status()

    def _create_crash_entry(self, service: ServiceType, error: str, stack_trace: Optional[str],
                           recovery_attempted: bool, recovery_success: bool) -> CrashEntry:
        """Create CrashEntry object."""
        return CrashEntry(
            service=service, timestamp=datetime.now(timezone.utc),
            error=error, stack_trace=stack_trace,
            recovery_attempted=recovery_attempted, recovery_success=recovery_success
        )

    async def update_migration_status(self, current_version: Optional[str] = None,
                                    pending: List[str] = None,
                                    failed: List[str] = None,
                                    auto_run: bool = True) -> None:
        """Update migration status information."""
        await self._ensure_status_loaded()
        migration = self.status.migration_status
        if current_version: migration.current_version = current_version
        if pending: migration.pending_migrations = pending
        if failed: migration.failed_migrations = failed
        migration.auto_run = auto_run
        migration.last_run = datetime.now(timezone.utc)
        await self.save_status()

    async def update_service_config(self, config_hash: str,
                                  validation_errors: List[str] = None) -> None:
        """Update service configuration status."""
        await self._ensure_status_loaded()
        config = self.status.service_config
        config.hash = config_hash
        config.last_validated = datetime.now(timezone.utc)
        config.validation_errors = validation_errors or []
        await self.save_status()

    async def record_health_check_failure(self, service: str) -> None:
        """Record health check failure."""
        await self._ensure_status_loaded()
        history = self.status.health_check_history
        current_failures = history.consecutive_failures.get(service, 0)
        history.consecutive_failures[service] = current_failures + 1
        await self.save_status()

    async def record_health_check_success(self, service: str) -> None:
        """Record health check success."""
        await self._ensure_status_loaded()
        history = self.status.health_check_history
        history.consecutive_failures[service] = 0
        history.last_healthy[service] = datetime.now(timezone.utc)
        await self.save_status()

    async def get_crash_count(self, service: Optional[ServiceType] = None,
                             since: Optional[datetime] = None) -> int:
        """Get crash count with optional filters."""
        await self._ensure_status_loaded()
        crashes = self.status.crash_history
        if service:
            crashes = [c for c in crashes if c.service == service]
        if since:
            crashes = [c for c in crashes if c.timestamp >= since]
        return len(crashes)

    async def get_recent_crashes(self, limit: int = 10) -> List[CrashEntry]:
        """Get recent crashes limited by count."""
        await self._ensure_status_loaded()
        return sorted(self.status.crash_history, 
                     key=lambda x: x.timestamp, reverse=True)[:limit]

    async def get_health_failures(self, service: str) -> int:
        """Get consecutive health check failures for service."""
        await self._ensure_status_loaded()
        return self.status.health_check_history.consecutive_failures.get(service, 0)

    async def is_migration_pending(self) -> bool:
        """Check if migrations are pending."""
        await self._ensure_status_loaded()
        return len(self.status.migration_status.pending_migrations) > 0

    async def has_failed_migrations(self) -> bool:
        """Check if there are failed migrations."""
        await self._ensure_status_loaded()
        return len(self.status.migration_status.failed_migrations) > 0

    async def _ensure_status_loaded(self) -> None:
        """Ensure status is loaded."""
        if not self.status:
            self.status = await self.load_status()

    async def _load_existing_status(self) -> StartupStatus:
        """Load existing status file."""
        if not self.status_path.exists():
            raise FileNotFoundError(f"Status file not found: {self.status_path}")
        try:
            data = json.loads(self.status_path.read_text())
            return StartupStatus.model_validate(data)
        except json.JSONDecodeError as e:
            raise DataParsingError(f"Invalid JSON in status file: {e}")

    async def _create_new_status(self) -> StartupStatus:
        """Create new status and save it."""
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        new_status = StartupStatus()
        self.status = new_status
        await self.save_status()
        return new_status

    @asynccontextmanager
    async def _file_lock(self):
        """Cross-platform file locking context manager."""
        await self._acquire_file_lock()
        try:
            yield
        finally:
            self._lock_file_path.unlink(missing_ok=True)

    async def _acquire_file_lock(self) -> None:
        """Acquire file lock with retry."""
        max_attempts = 30
        for attempt in range(max_attempts):
            if self._try_acquire_lock():
                return
            await asyncio.sleep(0.1)
        raise NetraException("Could not acquire file lock")

    def _try_acquire_lock(self) -> bool:
        """Try to acquire file lock."""
        try:
            self._lock_file_path.touch(exist_ok=False)
            return True
        except FileExistsError:
            return False

    async def _atomic_write(self, data: Dict[str, Any]) -> None:
        """Write data atomically with file locking."""
        async with self._file_lock():
            temp_path = Path(f"{self.status_path}.tmp")
            try:
                self._write_temp_file(temp_path, data)
                temp_path.replace(self.status_path)
            except Exception as e:
                temp_path.unlink(missing_ok=True)
                raise FileError(f"Failed to write status file: {e}")

    def _write_temp_file(self, temp_path: Path, data: Dict[str, Any]) -> None:
        """Write data to temporary file."""
        temp_path.write_text(json.dumps(data, indent=2, default=str))


# Singleton instance for application use
startup_status_manager = StartupStatusManager()