"""
Comprehensive Unit Tests for Startup Diagnostics
Tests system error collection, automatic fixes, and CLI interface.
COMPLIANCE: 450-line max file, 25-line max functions, async test support.
"""

import pytest
import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Optional

from scripts.startup_diagnostics import (
    StartupDiagnostics, collect_system_errors, check_port_conflicts,
    check_database_connection, check_dependencies, check_environment_variables,
    check_migrations, apply_fixes, apply_single_fix, fix_port_conflict,
    fix_dependencies, fix_migrations, diagnose_startup, generate_recommendations,
    main
)
from app.schemas.diagnostic_types import (
    DiagnosticResult, DiagnosticError, DiagnosticSeverity, FixResult,
    ServiceType, StartupPhase
)


@pytest.fixture
def mock_diagnostic_error() -> DiagnosticError:
    """Create mock diagnostic error."""
    return DiagnosticError(
        service="backend",
        phase="startup", 
        severity=DiagnosticSeverity.MEDIUM,
        message="Test error",
        suggested_fix="Test fix",
        can_auto_fix=True
    )


@pytest.fixture
def startup_diagnostics() -> StartupDiagnostics:
    """Create startup diagnostics instance."""
    return StartupDiagnostics()


class TestStartupDiagnosticsInit:
    """Test initialization and setup."""
    
    def test_init_creates_empty_lists(self, startup_diagnostics: StartupDiagnostics) -> None:
        """Test initialization creates empty error and fix lists."""
        assert len(startup_diagnostics.errors) == 0
        assert len(startup_diagnostics.fixes_applied) == 0
        assert isinstance(startup_diagnostics.start_time, datetime)


class TestSystemErrorCollection:
    """Test system error collection functionality."""
    @patch('scripts.startup_diagnostics.check_port_conflicts')
    @patch('scripts.startup_diagnostics.check_database_connection')
    @patch('scripts.startup_diagnostics.check_dependencies')
    @patch('scripts.startup_diagnostics.check_environment_variables')
    @patch('scripts.startup_diagnostics.check_migrations')
    async def test_collect_system_errors(self, mock_migrations: AsyncMock, 
                                        mock_env: AsyncMock, mock_deps: AsyncMock,
                                        mock_db: AsyncMock, mock_ports: AsyncMock) -> None:
        """Test system error collection calls all check functions."""
        mock_ports.return_value = []
        mock_db.return_value = []
        mock_deps.return_value = []
        mock_env.return_value = []
        mock_migrations.return_value = []
        
        errors = await collect_system_errors()
        assert len(errors) == 0
        
        mock_ports.assert_called_once()
        mock_db.assert_called_once()
        mock_deps.assert_called_once()
        mock_env.assert_called_once()
        mock_migrations.assert_called_once()


class TestPortConflictChecking:
    """Test port conflict detection."""
    @patch('scripts.startup_diagnostics.is_port_in_use')
    @patch('scripts.startup_diagnostics.create_port_error')
    async def test_check_port_conflicts_none_in_use(self, mock_create_error: Mock,
                                                   mock_port_check: Mock) -> None:
        """Test port conflict check when no ports in use."""
        mock_port_check.return_value = False
        
        errors = await check_port_conflicts()
        assert len(errors) == 0
        mock_create_error.assert_not_called()
    @patch('scripts.startup_diagnostics.is_port_in_use')
    @patch('scripts.startup_diagnostics.create_port_error')
    async def test_check_port_conflicts_some_in_use(self, mock_create_error: Mock,
                                                   mock_port_check: Mock,
                                                   mock_diagnostic_error: DiagnosticError) -> None:
        """Test port conflict check when some ports in use."""
        mock_port_check.side_effect = lambda port: port == 8000
        mock_create_error.return_value = mock_diagnostic_error
        
        errors = await check_port_conflicts()
        assert len(errors) == 1
        mock_create_error.assert_called_once_with(8000)


class TestDatabaseConnectionChecking:
    """Test database connection checking."""
    @patch('scripts.startup_diagnostics.run_command_async')
    async def test_check_database_connection_success(self, mock_run_cmd: AsyncMock) -> None:
        """Test successful database connection check."""
        mock_run_cmd.return_value = "OK\n"
        
        errors = await check_database_connection()
        assert len(errors) == 0
    @patch('scripts.startup_diagnostics.run_command_async')
    @patch('scripts.startup_diagnostics.create_db_error')
    async def test_check_database_connection_failure(self, mock_create_error: Mock,
                                                    mock_run_cmd: AsyncMock,
                                                    mock_diagnostic_error: DiagnosticError) -> None:
        """Test database connection check failure."""
        mock_run_cmd.return_value = "Error"
        mock_create_error.return_value = mock_diagnostic_error
        
        errors = await check_database_connection()
        assert len(errors) == 1
    @patch('scripts.startup_diagnostics.run_command_async')
    @patch('scripts.startup_diagnostics.create_db_error')
    async def test_check_database_connection_exception(self, mock_create_error: Mock,
                                                      mock_run_cmd: AsyncMock,
                                                      mock_diagnostic_error: DiagnosticError) -> None:
        """Test database connection check with exception."""
        mock_run_cmd.side_effect = Exception("Connection error")
        mock_create_error.return_value = mock_diagnostic_error
        
        errors = await check_database_connection()
        assert len(errors) == 1


class TestDependencyChecking:
    """Test dependency checking functionality."""
    @patch('scripts.startup_diagnostics.run_command_async')
    @patch('pathlib.Path.exists')
    async def test_check_dependencies_success(self, mock_exists: Mock, mock_run_cmd: AsyncMock) -> None:
        """Test successful dependency check."""
        mock_run_cmd.return_value = ""  # No output means success for pip check
        mock_exists.return_value = True
        
        errors = await check_dependencies()
        assert len(errors) == 0
    @patch('scripts.startup_diagnostics.run_command_async')
    @patch('pathlib.Path.exists')
    @patch('scripts.startup_diagnostics.create_dependency_error')
    async def test_check_dependencies_python_failure(self, mock_create_error: Mock,
                                                    mock_exists: Mock, mock_run_cmd: AsyncMock,
                                                    mock_diagnostic_error: DiagnosticError) -> None:
        """Test Python dependency check failure."""
        mock_run_cmd.side_effect = Exception("Dependency error")
        mock_create_error.return_value = mock_diagnostic_error
        mock_exists.return_value = False  # No frontend/package.json
        
        errors = await check_dependencies()
        assert len(errors) == 1
        mock_create_error.assert_called_with("Python")
    @patch('scripts.startup_diagnostics.run_command_async')
    @patch('pathlib.Path.exists')
    @patch('scripts.startup_diagnostics.create_dependency_error')
    async def test_check_dependencies_node_failure(self, mock_create_error: Mock,
                                                   mock_exists: Mock, mock_run_cmd: AsyncMock,
                                                   mock_diagnostic_error: DiagnosticError) -> None:
        """Test Node dependency check failure."""
        mock_exists.return_value = True
        mock_run_cmd.side_effect = [None, Exception("Node error")]  # Python succeeds, Node fails
        mock_create_error.return_value = mock_diagnostic_error
        
        errors = await check_dependencies()
        assert len(errors) == 1
        mock_create_error.assert_called_with("Node")


class TestEnvironmentVariableChecking:
    """Test environment variable checking."""
    @patch('os.getenv')
    async def test_check_environment_variables_all_present(self, mock_getenv: Mock) -> None:
        """Test environment variable check when all are present."""
        mock_getenv.return_value = "some_value"
        
        errors = await check_environment_variables()
        assert len(errors) == 0
    @patch('os.getenv')
    @patch('scripts.startup_diagnostics.create_env_error')
    async def test_check_environment_variables_missing(self, mock_create_error: Mock,
                                                      mock_getenv: Mock,
                                                      mock_diagnostic_error: DiagnosticError) -> None:
        """Test environment variable check with missing variables."""
        mock_getenv.return_value = None
        mock_create_error.return_value = mock_diagnostic_error
        
        errors = await check_environment_variables()
        assert len(errors) == 2  # DATABASE_URL and SECRET_KEY


class TestMigrationChecking:
    """Test migration status checking."""
    @patch('scripts.startup_diagnostics.run_command_async')
    async def test_check_migrations_up_to_date(self, mock_run_cmd: AsyncMock) -> None:
        """Test migration check when up to date."""
        mock_run_cmd.return_value = "current head\n"
        
        errors = await check_migrations()
        assert len(errors) == 0
    @patch('scripts.startup_diagnostics.run_command_async')
    @patch('scripts.startup_diagnostics.create_migration_error')
    async def test_check_migrations_pending(self, mock_create_error: Mock,
                                           mock_run_cmd: AsyncMock,
                                           mock_diagnostic_error: DiagnosticError) -> None:
        """Test migration check with pending migrations."""
        mock_run_cmd.return_value = "current abc123\n"  # No "head" means pending
        mock_create_error.return_value = mock_diagnostic_error
        
        errors = await check_migrations()
        assert len(errors) == 1
    @patch('scripts.startup_diagnostics.run_command_async')
    @patch('scripts.startup_diagnostics.create_migration_error')
    async def test_check_migrations_exception(self, mock_create_error: Mock,
                                             mock_run_cmd: AsyncMock,
                                             mock_diagnostic_error: DiagnosticError) -> None:
        """Test migration check with exception."""
        mock_run_cmd.side_effect = Exception("Alembic error")
        mock_create_error.return_value = mock_diagnostic_error
        
        errors = await check_migrations()
        assert len(errors) == 1


class TestFixApplication:
    """Test automatic fix application."""
    async def test_apply_fixes_empty_list(self) -> None:
        """Test applying fixes to empty error list."""
        fixes = await apply_fixes([])
        assert len(fixes) == 0
    async def test_apply_fixes_no_auto_fixable(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fixes when none are auto-fixable."""
        mock_diagnostic_error.can_auto_fix = False
        
        fixes = await apply_fixes([mock_diagnostic_error])
        assert len(fixes) == 0
    @patch('scripts.startup_diagnostics.apply_single_fix')
    async def test_apply_fixes_with_auto_fixable(self, mock_apply_single: AsyncMock,
                                                mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fixes with auto-fixable errors."""
        mock_fix_result = FixResult(error_id="test", attempted=True, 
                                   successful=True, message="Fixed")
        mock_apply_single.return_value = mock_fix_result
        mock_diagnostic_error.can_auto_fix = True
        
        fixes = await apply_fixes([mock_diagnostic_error])
        assert len(fixes) == 1


class TestSingleFixApplication:
    """Test individual fix application."""
    @patch('scripts.startup_diagnostics.fix_port_conflict')
    async def test_apply_single_fix_port_error(self, mock_fix_port: AsyncMock,
                                              mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fix for port error."""
        mock_diagnostic_error.message = "Port 8000 conflict"
        mock_fix_result = FixResult(error_id="test", attempted=True, 
                                   successful=True, message="Port fixed")
        mock_fix_port.return_value = mock_fix_result
        
        result = await apply_single_fix(mock_diagnostic_error)
        assert result.successful is True
    @patch('scripts.startup_diagnostics.fix_dependencies')
    async def test_apply_single_fix_dependency_error(self, mock_fix_deps: AsyncMock,
                                                    mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fix for dependency error."""
        mock_diagnostic_error.message = "Dependencies missing"
        mock_fix_result = FixResult(error_id="test", attempted=True, 
                                   successful=True, message="Dependencies fixed")
        mock_fix_deps.return_value = mock_fix_result
        
        result = await apply_single_fix(mock_diagnostic_error)
        assert result.successful is True
    async def test_apply_single_fix_unknown_error(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fix for unknown error type."""
        mock_diagnostic_error.message = "Unknown error"
        
        result = await apply_single_fix(mock_diagnostic_error)
        assert result.attempted is False
        assert "no auto-fix available" in result.message.lower()
    async def test_apply_single_fix_exception(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test fix application with exception."""
        mock_diagnostic_error.message = "Port conflict"
        
        with patch('scripts.startup_diagnostics.fix_port_conflict', side_effect=Exception("Fix error")):
            result = await apply_single_fix(mock_diagnostic_error)
            assert result.attempted is True
            assert result.successful is False
            assert "fix failed" in result.message.lower()


class TestSpecificFixes:
    """Test specific fix implementations."""
    async def test_fix_port_conflict(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test port conflict fix."""
        result = await fix_port_conflict(mock_diagnostic_error)
        assert result.attempted is True
        assert result.successful is True
        assert "port conflict resolved" in result.message.lower()
    @patch('scripts.startup_diagnostics.run_command_async')
    async def test_fix_dependencies_python_success(self, mock_run_cmd: AsyncMock,
                                                   mock_diagnostic_error: DiagnosticError) -> None:
        """Test successful Python dependency fix."""
        mock_diagnostic_error.message = "Python dependencies missing"
        mock_run_cmd.return_value = ""
        
        result = await fix_dependencies(mock_diagnostic_error)
        assert result.successful is True
    @patch('scripts.startup_diagnostics.run_command_async')
    async def test_fix_dependencies_failure(self, mock_run_cmd: AsyncMock,
                                           mock_diagnostic_error: DiagnosticError) -> None:
        """Test dependency fix failure."""
        mock_diagnostic_error.message = "Python dependencies missing"
        mock_run_cmd.side_effect = Exception("Install failed")
        
        result = await fix_dependencies(mock_diagnostic_error)
        assert result.successful is False
    @patch('scripts.startup_diagnostics.run_command_async')
    async def test_fix_migrations_success(self, mock_run_cmd: AsyncMock,
                                         mock_diagnostic_error: DiagnosticError) -> None:
        """Test successful migration fix."""
        mock_diagnostic_error.message = "Migration pending"
        mock_run_cmd.return_value = ""
        
        result = await fix_migrations(mock_diagnostic_error)
        assert result.successful is True
    @patch('scripts.startup_diagnostics.run_command_async')
    async def test_fix_migrations_failure(self, mock_run_cmd: AsyncMock,
                                         mock_diagnostic_error: DiagnosticError) -> None:
        """Test migration fix failure."""
        mock_diagnostic_error.message = "Migration pending"
        mock_run_cmd.side_effect = Exception("Migration failed")
        
        result = await fix_migrations(mock_diagnostic_error)
        assert result.successful is False


class TestDiagnoseStartup:
    """Test main diagnosis functionality."""
    @patch('scripts.startup_diagnostics.collect_system_errors')
    @patch('scripts.startup_diagnostics.get_system_state')
    @patch('scripts.startup_diagnostics.get_configuration')
    async def test_diagnose_startup_success(self, mock_get_config: Mock,
                                           mock_get_state: Mock, mock_collect: AsyncMock) -> None:
        """Test successful startup diagnosis."""
        mock_collect.return_value = []
        mock_get_state.return_value = {}
        mock_get_config.return_value = {}
        
        result = await diagnose_startup()
        assert isinstance(result, DiagnosticResult)
        assert result.success is True
    @patch('scripts.startup_diagnostics.collect_system_errors')
    @patch('scripts.startup_diagnostics.get_system_state')
    @patch('scripts.startup_diagnostics.get_configuration')
    async def test_diagnose_startup_with_critical_errors(self, mock_get_config: Mock,
                                                        mock_get_state: Mock, mock_collect: AsyncMock,
                                                        mock_diagnostic_error: DiagnosticError) -> None:
        """Test diagnosis with critical errors."""
        mock_diagnostic_error.severity = DiagnosticSeverity.CRITICAL
        mock_collect.return_value = [mock_diagnostic_error]
        mock_get_state.return_value = {}
        mock_get_config.return_value = {}
        
        result = await diagnose_startup()
        assert result.success is False
        assert len(result.errors) == 1


class TestRecommendationGeneration:
    """Test recommendation generation."""
    
    def test_generate_recommendations_no_errors(self) -> None:
        """Test recommendations with no errors."""
        recommendations = generate_recommendations([])
        assert len(recommendations) == 0

    def test_generate_recommendations_critical_errors(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test recommendations with critical errors."""
        mock_diagnostic_error.severity = DiagnosticSeverity.CRITICAL
        
        recommendations = generate_recommendations([mock_diagnostic_error])
        assert len(recommendations) >= 1
        assert any("critical errors" in r.lower() for r in recommendations)

    def test_generate_recommendations_many_errors(self) -> None:
        """Test recommendations with many errors."""
        errors = [DiagnosticError(service=ServiceType.SYSTEM, phase=StartupPhase.STARTUP, 
                                 severity=DiagnosticSeverity.LOW, message=f"Error {i}", 
                                 suggested_fix="fix", can_auto_fix=False) 
                 for i in range(10)]
        
        recommendations = generate_recommendations(errors)
        assert any("system cleanup" in r.lower() for r in recommendations)


class TestCLIInterface:
    """Test command-line interface."""
    @patch('scripts.startup_diagnostics.diagnose_startup')
    @patch('sys.argv', ['startup_diagnostics.py', '--diagnose'])
    async def test_main_diagnose_flag(self, mock_diagnose: AsyncMock) -> None:
        """Test main function with diagnose flag."""
        mock_result = DiagnosticResult(success=True, errors=[])
        mock_diagnose.return_value = mock_result
        
        with patch('builtins.print') as mock_print:
            await main()
            mock_diagnose.assert_called_once()
            mock_print.assert_called_once()
    @patch('scripts.startup_diagnostics.diagnose_startup')
    @patch('scripts.startup_diagnostics.apply_fixes')
    @patch('sys.argv', ['startup_diagnostics.py', '--fix'])
    async def test_main_fix_flag(self, mock_apply: AsyncMock, mock_diagnose: AsyncMock) -> None:
        """Test main function with fix flag."""
        mock_result = DiagnosticResult(success=True, errors=[])
        mock_diagnose.return_value = mock_result
        mock_apply.return_value = []
        
        with patch('builtins.print') as mock_print:
            await main()
            mock_diagnose.assert_called_once()
            mock_apply.assert_called_once()
    @patch('scripts.startup_diagnostics.diagnose_startup')
    @patch('sys.argv', ['startup_diagnostics.py', '--verify'])
    async def test_main_verify_flag(self, mock_diagnose: AsyncMock) -> None:
        """Test main function with verify flag."""
        mock_result = DiagnosticResult(success=True, errors=[])
        mock_diagnose.return_value = mock_result
        
        with patch('builtins.print') as mock_print:
            await main()
            mock_diagnose.assert_called_once()
            mock_print.assert_called_once()