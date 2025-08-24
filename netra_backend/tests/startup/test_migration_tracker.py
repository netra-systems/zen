"""
Comprehensive Unit Tests for Migration Tracker
Tests all critical migration operations, state management, and error handling.
COMPLIANCE: 450-line max file, 25-line max functions, async test support.
"""

import sys
from pathlib import Path

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.exceptions import NetraException

from netra_backend.app.startup.migration_tracker import (
    FailedMigration,
    MigrationState,
    MigrationTracker,
)

@pytest.fixture
def temp_state_path(tmp_path: Path) -> Path:
    """Create temporary migration state path."""
    return tmp_path / ".netra" / "migration_state.json"

@pytest.fixture
def mock_database_url() -> str:
    """Create mock database URL."""
    return "postgresql://user:pass@localhost:5432/test_db"

@pytest.fixture
def migration_tracker(mock_database_url: str, temp_state_path: Path) -> MigrationTracker:
    """Create migration tracker with mocked dependencies."""
    with patch.object(Path, 'mkdir'):
        tracker = MigrationTracker(mock_database_url, "dev")
        tracker.state_file = temp_state_path
        return tracker

@pytest.fixture
def mock_migration_state() -> Dict:
    """Create mock migration state data."""
    return {
        "current_version": "abc123",
        "applied_migrations": ["migration1", "migration2"],
        "pending_migrations": ["migration3"],
        "failed_migrations": [],
        "last_check": "2024-01-01T00:00:00",
        "auto_run_enabled": True
    }

class TestMigrationTrackerInit:
    """Test initialization and setup."""
    
    def test_init_with_defaults(self, mock_database_url: str) -> None:
        """Test initialization with default parameters."""
        with patch.object(Path, 'mkdir'):
            tracker = MigrationTracker(mock_database_url)
            assert tracker.database_url == mock_database_url
            assert tracker.environment == "dev"
            assert tracker.state_file.name == "migration_state.json"

    def test_init_with_custom_environment(self, mock_database_url: str) -> None:
        """Test initialization with custom environment."""
        with patch.object(Path, 'mkdir'):
            tracker = MigrationTracker(mock_database_url, "prod")
            assert tracker.environment == "prod"

    def test_ensure_netra_dir(self, migration_tracker: MigrationTracker) -> None:
        """Test .netra directory creation."""
        with patch.object(Path, 'mkdir') as mock_mkdir:
            migration_tracker._ensure_netra_dir()
            mock_mkdir.assert_called_once_with(exist_ok=True)

class TestStateManagement:
    """Test migration state loading and saving."""
    async def test_load_state_existing_file(self, migration_tracker: MigrationTracker,
                                           mock_migration_state: Dict, temp_state_path: Path) -> None:
        """Test loading existing state file."""
        temp_state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_state_path.write_text(json.dumps(mock_migration_state))
        
        state = await migration_tracker._load_state()
        assert state.current_version == "abc123"
        assert len(state.applied_migrations) == 2
    async def test_load_state_missing_file(self, migration_tracker: MigrationTracker) -> None:
        """Test loading when state file doesn't exist."""
        state = await migration_tracker._load_state()
        assert isinstance(state, MigrationState)
        assert state.current_version is None
        assert len(state.applied_migrations) == 0
    async def test_load_state_invalid_json(self, migration_tracker: MigrationTracker,
                                          temp_state_path: Path) -> None:
        """Test loading with invalid JSON returns default."""
        temp_state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_state_path.write_text("invalid json")
        
        state = await migration_tracker._load_state()
        assert isinstance(state, MigrationState)
    async def test_save_state_success(self, migration_tracker: MigrationTracker,
                                     temp_state_path: Path) -> None:
        """Test successful state saving."""
        state = MigrationState(current_version="test123")
        temp_state_path.parent.mkdir(parents=True, exist_ok=True)
        
        await migration_tracker._save_state(state)
        saved_data = json.loads(temp_state_path.read_text())
        assert saved_data["current_version"] == "test123"
    async def test_save_state_error_handling(self, migration_tracker: MigrationTracker) -> None:
        """Test save state error handling."""
        state = MigrationState()
        with patch.object(migration_tracker, '_write_file_async', side_effect=Exception("write error")):
            await migration_tracker._save_state(state)  # Should not raise

class TestFileOperations:
    """Test async file operations."""
    async def test_read_file_async(self, migration_tracker: MigrationTracker,
                                  temp_state_path: Path) -> None:
        """Test async file reading."""
        test_content = "test file content"
        temp_state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_state_path.write_text(test_content)
        
        content = await migration_tracker._read_file_async()
        assert content == test_content
    async def test_write_file_async(self, migration_tracker: MigrationTracker,
                                   temp_state_path: Path) -> None:
        """Test async file writing."""
        test_content = "test write content"
        temp_state_path.parent.mkdir(parents=True, exist_ok=True)
        
        await migration_tracker._write_file_async(test_content)
        content = temp_state_path.read_text()
        assert content == test_content

class TestAlembicOperations:
    """Test Alembic configuration and operations."""
    
    @patch('app.startup.migration_tracker.create_alembic_config')
    @patch('app.startup.migration_tracker.get_sync_database_url')
    def test_get_alembic_config(self, mock_sync_url: Mock, mock_create_config: Mock,
                               migration_tracker: MigrationTracker) -> None:
        """Test Alembic configuration creation."""
        mock_sync_url.return_value = "sync_url"
        mock_config = Mock()
        mock_create_config.return_value = mock_config
        
        config = migration_tracker._get_alembic_config()
        mock_sync_url.assert_called_once_with(migration_tracker.database_url)
        mock_create_config.assert_called_once_with("sync_url")
        assert config == mock_config

    @patch('app.startup.migration_tracker.get_current_revision')
    def test_get_current_safely_success(self, mock_get_current: Mock,
                                       migration_tracker: MigrationTracker) -> None:
        """Test successful current revision retrieval."""
        mock_get_current.return_value = "abc123"
        mock_config = Mock()
        
        result = migration_tracker._get_current_safely(mock_config)
        assert result == "abc123"

    @patch('app.startup.migration_tracker.get_current_revision')
    def test_get_current_safely_error(self, mock_get_current: Mock,
                                     migration_tracker: MigrationTracker) -> None:
        """Test current revision retrieval with error."""
        mock_get_current.side_effect = Exception("DB error")
        mock_config = Mock()
        
        result = migration_tracker._get_current_safely(mock_config)
        assert result is None

class TestMigrationChecking:
    """Test migration checking functionality."""
    @patch('app.startup.migration_tracker.get_head_revision')
    @patch('app.startup.migration_tracker.needs_migration')
    async def test_check_migrations_pending(self, mock_needs: Mock, mock_head: Mock,
                                           migration_tracker: MigrationTracker) -> None:
        """Test checking with pending migrations."""
        mock_head.return_value = "def456"
        mock_needs.return_value = True
        
        with patch.object(migration_tracker, '_get_current_safely', return_value="abc123"):
            with patch.object(migration_tracker, '_load_state', return_value=MigrationState()):
                with patch.object(migration_tracker, '_save_state'):
                    state = await migration_tracker.check_migrations()
                    assert len(state.pending_migrations) == 1
                    assert state.pending_migrations[0] == "def456"
    @patch('app.startup.migration_tracker.get_head_revision')
    @patch('app.startup.migration_tracker.needs_migration')
    async def test_check_migrations_none_pending(self, mock_needs: Mock, mock_head: Mock,
                                                 migration_tracker: MigrationTracker) -> None:
        """Test checking with no pending migrations."""
        mock_head.return_value = "abc123"
        mock_needs.return_value = False
        
        with patch.object(migration_tracker, '_get_current_safely', return_value="abc123"):
            with patch.object(migration_tracker, '_load_state', return_value=MigrationState()):
                with patch.object(migration_tracker, '_save_state'):
                    state = await migration_tracker.check_migrations()
                    assert len(state.pending_migrations) == 0
    async def test_check_migrations_error_handling(self, migration_tracker: MigrationTracker) -> None:
        """Test migration check error handling."""
        with patch.object(migration_tracker, '_load_state', return_value=MigrationState()):
            with patch.object(migration_tracker, '_get_alembic_config', side_effect=Exception("Config error")):
                with patch.object(migration_tracker, '_record_failure'):
                    with pytest.raises(NetraException):
                        await migration_tracker.check_migrations()

class TestMigrationExecution:
    """Test migration execution functionality."""
    async def test_run_migrations_no_pending(self, migration_tracker: MigrationTracker) -> None:
        """Test run migrations with no pending migrations."""
        state = MigrationState(pending_migrations=[])
        
        with patch.object(migration_tracker, 'check_migrations', return_value=state):
            result = await migration_tracker.run_migrations()
            assert result is True
    async def test_run_migrations_auto_run_disabled(self, migration_tracker: MigrationTracker) -> None:
        """Test run migrations with auto-run disabled."""
        state = MigrationState(pending_migrations=["migration1"], auto_run_enabled=False)
        
        with patch.object(migration_tracker, 'check_migrations', return_value=state):
            result = await migration_tracker.run_migrations()
            assert result is False
    async def test_run_migrations_force_execution(self, migration_tracker: MigrationTracker) -> None:
        """Test forced migration execution."""
        state = MigrationState(pending_migrations=[], auto_run_enabled=False)
        
        with patch.object(migration_tracker, 'check_migrations', return_value=state):
            with patch.object(migration_tracker, '_execute_migrations', return_value=True):
                result = await migration_tracker.run_migrations(force=True)
                assert result is True

    def test_should_auto_run_checks(self, migration_tracker: MigrationTracker) -> None:
        """Test auto-run decision logic."""
        # Auto-run disabled
        state = MigrationState(auto_run_enabled=False)
        assert migration_tracker._should_auto_run(state) is False
        
        # Non-dev environment
        migration_tracker.environment = "prod"
        state = MigrationState(auto_run_enabled=True)
        assert migration_tracker._should_auto_run(state) is False
    async def test_execute_migrations_success(self, migration_tracker: MigrationTracker) -> None:
        """Test successful migration execution."""
        state = MigrationState(pending_migrations=["migration1"])
        
        with patch.object(migration_tracker, '_run_alembic_upgrade'):
            with patch.object(migration_tracker, '_save_state'):
                result = await migration_tracker._execute_migrations(state)
                assert result is True
                assert len(state.pending_migrations) == 0
    async def test_execute_migrations_failure(self, migration_tracker: MigrationTracker) -> None:
        """Test migration execution failure."""
        state = MigrationState(pending_migrations=["migration1"])
        
        with patch.object(migration_tracker, '_run_alembic_upgrade', side_effect=Exception("Migration error")):
            with patch.object(migration_tracker, '_record_failure'):
                result = await migration_tracker._execute_migrations(state)
                assert result is False

class TestMigrationRollback:
    """Test migration rollback functionality."""
    async def test_rollback_migration_success(self, migration_tracker: MigrationTracker) -> None:
        """Test successful migration rollback."""
        with patch.object(migration_tracker, '_run_alembic_downgrade'):
            with patch.object(migration_tracker, '_load_state', return_value=MigrationState()):
                with patch.object(migration_tracker, '_save_state'):
                    result = await migration_tracker.rollback_migration(2)
                    assert result is True
    async def test_rollback_migration_failure(self, migration_tracker: MigrationTracker) -> None:
        """Test migration rollback failure."""
        with patch.object(migration_tracker, '_run_alembic_downgrade', side_effect=Exception("Rollback error")):
            result = await migration_tracker.rollback_migration()
            assert result is False

    @patch('alembic.command.downgrade')
    def test_run_alembic_downgrade(self, mock_downgrade: Mock, migration_tracker: MigrationTracker) -> None:
        """Test Alembic downgrade command execution."""
        mock_config = Mock()
        
        with patch.object(migration_tracker, '_get_alembic_config', return_value=mock_config):
            migration_tracker._run_alembic_downgrade("-2")
            mock_downgrade.assert_called_once_with(mock_config, "-2")

class TestValidationAndStatus:
    """Test validation and status methods."""
    async def test_validate_schema_success(self, migration_tracker: MigrationTracker) -> None:
        """Test successful schema validation."""
        state = MigrationState(pending_migrations=[], failed_migrations=[])
        
        with patch.object(migration_tracker, 'check_migrations', return_value=state):
            result = await migration_tracker.validate_schema()
            assert result is True
    async def test_validate_schema_pending_migrations(self, migration_tracker: MigrationTracker) -> None:
        """Test schema validation with pending migrations."""
        state = MigrationState(pending_migrations=["migration1"])
        
        with patch.object(migration_tracker, 'check_migrations', return_value=state):
            result = await migration_tracker.validate_schema()
            assert result is False
    async def test_get_migration_status(self, migration_tracker: MigrationTracker) -> None:
        """Test migration status retrieval."""
        state = MigrationState(current_version="abc123", pending_migrations=["mig1"])
        
        with patch.object(migration_tracker, 'check_migrations', return_value=state):
            status = await migration_tracker.get_migration_status()
            assert status["current_version"] == "abc123"
            assert status["pending_count"] == 1

class TestStateModification:
    """Test state modification methods."""
    async def test_clear_failed_migrations(self, migration_tracker: MigrationTracker) -> None:
        """Test clearing failed migration records."""
        failed_migration = FailedMigration(migration_id="test", error_message="error")
        state = MigrationState(failed_migrations=[failed_migration])
        
        with patch.object(migration_tracker, '_load_state', return_value=state):
            with patch.object(migration_tracker, '_save_state'):
                await migration_tracker.clear_failed_migrations()
                assert len(state.failed_migrations) == 0
    async def test_disable_auto_run(self, migration_tracker: MigrationTracker) -> None:
        """Test disabling auto-run."""
        state = MigrationState(auto_run_enabled=True)
        
        with patch.object(migration_tracker, '_load_state', return_value=state):
            with patch.object(migration_tracker, '_save_state'):
                await migration_tracker.disable_auto_run()
                assert state.auto_run_enabled is False
    async def test_enable_auto_run(self, migration_tracker: MigrationTracker) -> None:
        """Test enabling auto-run."""
        state = MigrationState(auto_run_enabled=False)
        
        with patch.object(migration_tracker, '_load_state', return_value=state):
            with patch.object(migration_tracker, '_save_state'):
                await migration_tracker.enable_auto_run()
                assert state.auto_run_enabled is True

class TestFailureRecording:
    """Test failure recording functionality."""
    async def test_record_failure(self, migration_tracker: MigrationTracker) -> None:
        """Test failure recording."""
        state = MigrationState()
        
        with patch.object(migration_tracker, '_save_state'):
            await migration_tracker._record_failure(state, "test_migration", "test error")
            assert len(state.failed_migrations) == 1
            assert state.failed_migrations[0].migration_id == "test_migration"