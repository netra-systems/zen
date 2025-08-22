"""
Comprehensive Unit Tests for Startup Status Manager
Tests all critical paths, edge cases, and error conditions with strong typing.
COMPLIANCE: 450-line max file, 25-line max functions, async test support.
"""

# Add project root to path
import sys
from pathlib import Path

from ..test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.exceptions_file import DataParsingError, FileError
from netra_backend.app.core.exceptions_file import (
    FileNotFoundError as NetraFileNotFoundError,
)
from netra_backend.app.schemas.startup_types import (
    CrashEntry,
    Environment,
    HealthCheckHistory,
    LastStartup,
    MigrationStatus,
    ServiceConfig,
    ServiceType,
    # Add project root to path
    StartupStatus,
)

# Add project root to path
from netra_backend.app.startup.status_manager import StartupStatusManager


@pytest.fixture
def temp_status_path(tmp_path: Path) -> Path:
    """Create temporary status file path."""
    return tmp_path / "test_status.json"


@pytest.fixture
def mock_status_data() -> Dict:
    """Create mock status data for testing."""
    return {
        "last_startup": {"timestamp": "2024-01-01T00:00:00Z", "success": True, 
                        "duration_ms": 5000, "environment": "dev", "errors": [], "warnings": []},
        "migration_status": {"current_version": "abc123", "pending_migrations": [], 
                            "failed_migrations": [], "auto_run": True},
        "service_config": {"hash": "def456", "validation_errors": []},
        "crash_history": [], "health_check_history": {"consecutive_failures": {}, "last_healthy": {}}
    }


@pytest.fixture
def status_manager(temp_status_path: Path) -> StartupStatusManager:
    """Create status manager with temporary path."""
    return StartupStatusManager(str(temp_status_path))


class TestStartupStatusManagerInit:
    """Test initialization and basic setup."""
    
    def test_init_with_default_path(self) -> None:
        """Test initialization with default path."""
        manager = StartupStatusManager()
        assert manager.status_path == Path(".netra/startup_status.json")
        assert manager.status is None
        assert manager._lock_file_path == Path(".netra/startup_status.json.lock")

    def test_init_with_custom_path(self, temp_status_path: Path) -> None:
        """Test initialization with custom path."""
        manager = StartupStatusManager(str(temp_status_path))
        assert manager.status_path == temp_status_path
        assert str(manager._lock_file_path).endswith(".lock")


class TestLoadStatus:
    """Test status loading functionality."""
    async def test_load_existing_status_success(self, status_manager: StartupStatusManager, 
                                              mock_status_data: Dict, temp_status_path: Path) -> None:
        """Test successful loading of existing status."""
        temp_status_path.write_text(json.dumps(mock_status_data))
        status = await status_manager.load_status()
        assert isinstance(status, StartupStatus)
        assert status.last_startup.success is True
    async def test_load_nonexistent_creates_new(self, status_manager: StartupStatusManager) -> None:
        """Test creating new status when file doesn't exist."""
        with patch.object(status_manager, '_load_existing_status', side_effect=NetraFileNotFoundError("File not found")):
            with patch.object(status_manager, '_create_new_status', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = StartupStatus()
                status = await status_manager.load_status()
                mock_create.assert_called_once()
    async def test_load_invalid_json_creates_new(self, status_manager: StartupStatusManager,
                                                temp_status_path: Path) -> None:
        """Test handling invalid JSON creates new status."""
        temp_status_path.write_text("invalid json")
        with patch.object(status_manager, '_create_new_status', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = StartupStatus()
            await status_manager.load_status()
            mock_create.assert_called_once()


class TestSaveStatus:
    """Test status saving functionality."""
    async def test_save_status_success(self, status_manager: StartupStatusManager) -> None:
        """Test successful status saving."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, '_atomic_write') as mock_write:
            await status_manager.save_status()
            mock_write.assert_called_once()
    async def test_save_status_no_status_raises_error(self, status_manager: StartupStatusManager) -> None:
        """Test saving without loaded status raises error."""
        with pytest.raises(NetraException, match="No status to save"):
            await status_manager.save_status()


class TestValidateStatus:
    """Test status validation functionality."""
    async def test_validate_status_success(self, status_manager: StartupStatusManager) -> None:
        """Test successful status validation."""
        with patch.object(status_manager, 'load_status') as mock_load:
            mock_load.return_value = StartupStatus()
            result = await status_manager.validate_status()
            assert result is True
    async def test_validate_status_failure(self, status_manager: StartupStatusManager) -> None:
        """Test status validation failure."""
        with patch.object(status_manager, 'load_status', side_effect=Exception("error")):
            result = await status_manager.validate_status()
            assert result is False


class TestStartupEvents:
    """Test startup event recording."""
    async def test_save_startup_event_success(self, status_manager: StartupStatusManager) -> None:
        """Test successful startup event recording."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, 'save_status') as mock_save:
            await status_manager.save_startup_event(True, 5000, Environment.DEV)
            assert status_manager.status.last_startup.success is True
            mock_save.assert_called_once()
    async def test_save_startup_event_with_errors(self, status_manager: StartupStatusManager) -> None:
        """Test startup event with errors and warnings."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, 'save_status'):
            await status_manager.save_startup_event(False, 8000, Environment.DEV, 
                                                   ["error1"], ["warning1"])
            assert len(status_manager.status.last_startup.errors) == 1
            assert len(status_manager.status.last_startup.warnings) == 1


class TestCrashRecording:
    """Test crash recording functionality."""
    async def test_record_crash_basic(self, status_manager: StartupStatusManager) -> None:
        """Test basic crash recording."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, 'save_status') as mock_save:
            await status_manager.record_crash(ServiceType.BACKEND, "Connection failed")
            assert len(status_manager.status.crash_history) == 1
            mock_save.assert_called_once()
    async def test_record_crash_with_recovery(self, status_manager: StartupStatusManager) -> None:
        """Test crash recording with recovery info."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, 'save_status'):
            await status_manager.record_crash(ServiceType.FRONTEND, "UI error", 
                                             "stack trace", True, True)
            crash = status_manager.status.crash_history[0]
            assert crash.recovery_attempted is True
            assert crash.recovery_success is True


class TestMigrationStatus:
    """Test migration status updates."""
    async def test_update_migration_status(self, status_manager: StartupStatusManager) -> None:
        """Test migration status update."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, 'save_status') as mock_save:
            await status_manager.update_migration_status("v1.0.0", ["mig1"], ["mig2"])
            migration = status_manager.status.migration_status
            assert migration.current_version == "v1.0.0"
            mock_save.assert_called_once()
    async def test_is_migration_pending(self, status_manager: StartupStatusManager) -> None:
        """Test migration pending check."""
        status_manager.status = StartupStatus()
        status_manager.status.migration_status.pending_migrations = ["mig1"]
        result = await status_manager.is_migration_pending()
        assert result is True


class TestHealthChecks:
    """Test health check functionality."""
    async def test_record_health_check_failure(self, status_manager: StartupStatusManager) -> None:
        """Test health check failure recording."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, 'save_status') as mock_save:
            await status_manager.record_health_check_failure("redis")
            failures = status_manager.status.health_check_history.consecutive_failures
            assert failures["redis"] == 1
            mock_save.assert_called_once()
    async def test_record_health_check_success(self, status_manager: StartupStatusManager) -> None:
        """Test health check success recording."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, 'save_status') as mock_save:
            await status_manager.record_health_check_success("postgres")
            failures = status_manager.status.health_check_history.consecutive_failures
            assert failures["postgres"] == 0
            mock_save.assert_called_once()


class TestUtilityMethods:
    """Test utility and helper methods."""
    async def test_get_crash_count_no_filter(self, status_manager: StartupStatusManager) -> None:
        """Test crash count without filters."""
        status_manager.status = StartupStatus()
        crash = CrashEntry(service=ServiceType.BACKEND, timestamp=datetime.now(timezone.utc), error="test")
        status_manager.status.crash_history = [crash]
        count = await status_manager.get_crash_count()
        assert count == 1
    async def test_get_crash_count_with_service_filter(self, status_manager: StartupStatusManager) -> None:
        """Test crash count with service filter."""
        status_manager.status = StartupStatus()
        crash1 = CrashEntry(service=ServiceType.BACKEND, timestamp=datetime.now(timezone.utc), error="test1")
        crash2 = CrashEntry(service=ServiceType.FRONTEND, timestamp=datetime.now(timezone.utc), error="test2")
        status_manager.status.crash_history = [crash1, crash2]
        count = await status_manager.get_crash_count(ServiceType.BACKEND)
        assert count == 1
    async def test_get_recent_crashes_limit(self, status_manager: StartupStatusManager) -> None:
        """Test recent crashes with limit."""
        status_manager.status = StartupStatus()
        crashes = [CrashEntry(service=ServiceType.BACKEND, timestamp=datetime.now(timezone.utc), 
                             error=f"test{i}") for i in range(5)]
        status_manager.status.crash_history = crashes
        recent = await status_manager.get_recent_crashes(3)
        assert len(recent) == 3


class TestFileLocking:
    """Test file locking mechanisms."""
    async def test_file_lock_context_manager(self, status_manager: StartupStatusManager) -> None:
        """Test file lock context manager."""
        with patch('pathlib.Path.touch') as mock_touch:
            with patch('pathlib.Path.unlink') as mock_unlink:
                async with status_manager._file_lock():
                    pass
                mock_touch.assert_called_once_with(exist_ok=False)
                mock_unlink.assert_called_once_with(missing_ok=True)
    async def test_file_lock_timeout(self, status_manager: StartupStatusManager) -> None:
        """Test file lock timeout handling."""
        with patch('pathlib.Path.touch', side_effect=FileExistsError):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(NetraException, match="Could not acquire file lock"):
                    async with status_manager._file_lock():
                        pass


class TestAtomicWrite:
    """Test atomic file write operations."""
    async def test_atomic_write_success(self, status_manager: StartupStatusManager) -> None:
        """Test successful atomic write."""
        test_data = {"test": "data"}
        from contextlib import asynccontextmanager
        
        @asynccontextmanager
        async def mock_file_lock():
            yield
        
        with patch.object(status_manager, '_file_lock', side_effect=mock_file_lock):
            with patch('pathlib.Path.write_text') as mock_write:
                with patch('pathlib.Path.replace') as mock_replace:
                    await status_manager._atomic_write(test_data)
                    mock_write.assert_called_once()
                    mock_replace.assert_called_once()
    async def test_atomic_write_failure_cleanup(self, status_manager: StartupStatusManager) -> None:
        """Test atomic write failure with cleanup."""
        test_data = {"test": "data"}
        from contextlib import asynccontextmanager
        
        @asynccontextmanager
        async def mock_file_lock():
            yield
            
        with patch.object(status_manager, '_file_lock', side_effect=mock_file_lock):
            with patch('pathlib.Path.write_text', side_effect=Exception("write error")):
                with patch('pathlib.Path.unlink') as mock_cleanup:
                    with pytest.raises(FileError):
                        await status_manager._atomic_write(test_data)
                    mock_cleanup.assert_called_once()


class TestEnsureStatusLoaded:
    """Test status loading helper."""
    async def test_ensure_status_loaded_already_loaded(self, status_manager: StartupStatusManager) -> None:
        """Test ensure status when already loaded."""
        status_manager.status = StartupStatus()
        with patch.object(status_manager, 'load_status') as mock_load:
            await status_manager._ensure_status_loaded()
            mock_load.assert_not_called()
    async def test_ensure_status_loaded_not_loaded(self, status_manager: StartupStatusManager) -> None:
        """Test ensure status when not loaded."""
        with patch.object(status_manager, 'load_status') as mock_load:
            mock_load.return_value = StartupStatus()
            await status_manager._ensure_status_loaded()
            mock_load.assert_called_once()