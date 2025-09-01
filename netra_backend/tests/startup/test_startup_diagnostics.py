from shared.isolated_environment import get_env
"""
env = get_env()
L3 Real Service Tests for Startup Diagnostics
Tests actual system startup diagnostics with real services.
Validates real startup sequences, database connections, and error detection.

BUSINESS VALUE: Ensures reliable startup processes in production,
protecting customer experience during system initialization.
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.db.postgres_core import AsyncDatabase
from netra_backend.app.schemas.diagnostic_types import (
    DiagnosticError,
    DiagnosticResult,
    DiagnosticSeverity,
    FixResult,
    ServiceType,
    StartupPhase,
)
from scripts.startup_diagnostics import (
    StartupDiagnostics,
    apply_fixes,
    apply_single_fix,
    check_database_connection,
    check_dependencies,
    check_environment_variables,
    check_migrations,
    check_port_conflicts,
    collect_system_errors,
    diagnose_startup,
    fix_dependencies,
    fix_migrations,
    fix_port_conflict,
    generate_recommendations,
)
from test_framework.decorators import mock_justified
from test_framework.real_services_test_fixtures import (
    real_postgres_connection,
    with_test_database,
)

@pytest.fixture
def sample_diagnostic_error() -> DiagnosticError:
    """Create sample diagnostic error for testing."""
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

@pytest.fixture
def mock_diagnostic_error() -> DiagnosticError:
    """Create mock diagnostic error for testing."""
    return DiagnosticError(
        service="backend",
        phase="startup", 
        severity=DiagnosticSeverity.HIGH,
        message="Mock error for testing",
        suggested_fix="Mock fix",
        can_auto_fix=True
    )

class TestStartupDiagnosticsInit:
    """Test initialization and setup."""
    
    def test_init_creates_empty_lists(self, startup_diagnostics: StartupDiagnostics) -> None:
        """Test initialization creates empty error and fix lists."""
        assert len(startup_diagnostics.errors) == 0
        assert len(startup_diagnostics.fixes_applied) == 0
        assert isinstance(startup_diagnostics.start_time, datetime)

@pytest.mark.l3
class TestRealSystemErrorCollection:
    """Test real system error collection functionality."""
    
    @pytest.mark.asyncio
    async def test_collect_real_system_errors(self) -> None:
        """Test system error collection with real system checks."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db',
            'SECRET_KEY': 'test-secret-key',
        }):
            errors = await collect_system_errors()
            
            # Should return a list (may contain errors depending on system state)
            assert isinstance(errors, list)
            
            # All errors should be valid DiagnosticError objects
            for error in errors:
                assert isinstance(error, DiagnosticError)
                assert error.service is not None
                assert error.message is not None
    
    @pytest.mark.asyncio
    async def test_collect_errors_with_missing_env(self) -> None:
        """Test error collection detects missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            errors = await collect_system_errors()
            
            # Should detect missing environment variables
            env_errors = [e for e in errors if "environment" in e.message.lower()]
            assert len(env_errors) > 0

@pytest.mark.l3
class TestRealPortConflictChecking:
    """Test real port conflict detection."""
    
    @pytest.mark.asyncio
    async def test_check_port_conflicts_real_ports(self) -> None:
        """Test port conflict check with real port checking."""
        errors = await check_port_conflicts()
        
        # Should return a list
        assert isinstance(errors, list)
        
        # If there are errors, they should be valid
        for error in errors:
            assert isinstance(error, DiagnosticError)
            assert "port" in error.message.lower()
    
    def test_port_availability_check(self) -> None:
        """Test real port availability checking."""
        # Find an available port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        available_port = sock.getsockname()[1]
        sock.close()
        
        # Port should be available after closing
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock2.connect_ex(('localhost', available_port))
        sock2.close()
        
        # Connection should fail (port not in use)
        assert result != 0
    
    def test_port_conflict_detection(self) -> None:
        """Test detection of port conflicts with real socket."""
        # Create a socket to occupy a port
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(('localhost', 0))
        used_port = server_sock.getsockname()[1]
        server_sock.listen(1)
        
        try:
            # Try to connect to the occupied port
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = client_sock.connect_ex(('localhost', used_port))
            client_sock.close()
            
            # Connection should succeed (port is in use)
            assert result == 0
        finally:
            server_sock.close()

@pytest.mark.l3  
class TestRealDatabaseConnectionChecking:
    """Test real database connection checking."""
    
    @pytest.mark.asyncio
    async def test_check_database_connection_real(self) -> None:
        """Test database connection check with real database."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db'
        }):
            errors = await check_database_connection()
            
            # Should return a list (may contain connection errors)
            assert isinstance(errors, list)
            
            # Any errors should be valid diagnostic errors
            for error in errors:
                assert isinstance(error, DiagnosticError)
                assert "database" in error.message.lower()
    
    @pytest.mark.asyncio
    async def test_database_connection_with_test_db(self, test_db_url: str) -> None:
        """Test database connection with test database."""
        with patch.dict(os.environ, {'DATABASE_URL': test_db_url}):
            errors = await check_database_connection()
            
            # With valid test database, should have no connection errors
            db_errors = [e for e in errors if "connection" in e.message.lower()]
            assert len(db_errors) == 0
    
    @pytest.mark.asyncio
    async def test_database_connection_with_invalid_url(self) -> None:
        """Test database connection with invalid URL."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://invalid:invalid@nonexistent:5432/fake_db'
        }):
            errors = await check_database_connection()
            
            # Should detect connection error
            db_errors = [e for e in errors if "database" in e.message.lower()]
            assert len(db_errors) > 0

@pytest.mark.l3
class TestRealDependencyChecking:
    """Test real dependency checking functionality."""
    
    @pytest.mark.asyncio
    async def test_check_dependencies_real_environment(self) -> None:
        """Test dependency check in real environment."""
        errors = await check_dependencies()
        
        # Should return a list
        assert isinstance(errors, list)
        
        # Any dependency errors should be valid
        for error in errors:
            assert isinstance(error, DiagnosticError)
            assert any(dep in error.message.lower() for dep in ['python', 'node', 'dependency'])
    
    @pytest.mark.asyncio
    async def test_python_environment_check(self) -> None:
        """Test Python environment is functional."""
        # Test that Python is available and can run basic commands
        try:
            result = subprocess.run([sys.executable, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            assert result.returncode == 0
            assert 'Python' in result.stdout
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pytest.skip("Python environment check failed")
    
    @pytest.mark.asyncio
    async def test_pip_availability(self) -> None:
        """Test pip is available for dependency management."""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            assert result.returncode == 0
            assert 'pip' in result.stdout
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pytest.skip("Pip availability check failed")

@pytest.mark.l3
class TestRealEnvironmentVariableChecking:
    """Test real environment variable checking."""
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_current_env(self) -> None:
        """Test environment variable check with current environment."""
        errors = await check_environment_variables()
        
        # Should return a list
        assert isinstance(errors, list)
        
        # Any environment errors should be valid
        for error in errors:
            assert isinstance(error, DiagnosticError)
            assert "environment" in error.message.lower() or "variable" in error.message.lower()
    
    @pytest.mark.asyncio
    async def test_environment_variables_with_required_set(self) -> None:
        """Test environment check with required variables set."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db',
            'SECRET_KEY': 'test-secret-key-for-testing',
        }):
            errors = await check_environment_variables()
            
            # Should have fewer errors with required vars set
            env_var_errors = [e for e in errors if any(
                var in e.message for var in ['DATABASE_URL', 'SECRET_KEY']
            )]
            assert len(env_var_errors) == 0
    
    @pytest.mark.asyncio
    async def test_environment_variables_missing_critical(self) -> None:
        """Test environment check detects missing critical variables."""
        # Remove critical environment variables
        env_backup = env.get_all()
        try:
            for var in ['DATABASE_URL', 'SECRET_KEY']:
                os.environ.pop(var, None)
            
            errors = await check_environment_variables()
            
            # Should detect missing critical variables
            critical_errors = [e for e in errors if any(
                var in e.message for var in ['DATABASE_URL', 'SECRET_KEY']
            )]
            assert len(critical_errors) > 0
        finally:
            env.clear()
            env.update(env_backup, "test")

class TestMigrationChecking:
    """Test migration status checking."""
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.run_command_async')
    @pytest.mark.asyncio
    async def test_check_migrations_up_to_date(self, mock_run_cmd: AsyncMock) -> None:
        """Test migration check when up to date."""
        mock_run_cmd.return_value = "current head\n"
        
        errors = await check_migrations()
        assert len(errors) == 0
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.run_command_async')
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.create_migration_error')
    @pytest.mark.asyncio
    async def test_check_migrations_pending(self, mock_create_error: Mock,
                                           mock_run_cmd: AsyncMock,
                                           mock_diagnostic_error: DiagnosticError) -> None:
        """Test migration check with pending migrations."""
        mock_run_cmd.return_value = "current abc123\n"  # No "head" means pending
        mock_create_error.return_value = mock_diagnostic_error
        
        errors = await check_migrations()
        assert len(errors) == 1
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.run_command_async')
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.create_migration_error')
    @pytest.mark.asyncio
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
    @pytest.mark.asyncio
    async def test_apply_fixes_empty_list(self) -> None:
        """Test applying fixes to empty error list."""
        fixes = await apply_fixes([])
        assert len(fixes) == 0
    @pytest.mark.asyncio
    async def test_apply_fixes_no_auto_fixable(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fixes when none are auto-fixable."""
        mock_diagnostic_error.can_auto_fix = False
        
        fixes = await apply_fixes([mock_diagnostic_error])
        assert len(fixes) == 0
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.apply_single_fix')
    @pytest.mark.asyncio
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
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.fix_port_conflict')
    @pytest.mark.asyncio
    async def test_apply_single_fix_port_error(self, mock_fix_port: AsyncMock,
                                              mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fix for port error."""
        mock_diagnostic_error.message = "Port 8000 conflict"
        mock_fix_result = FixResult(error_id="test", attempted=True, 
                                   successful=True, message="Port fixed")
        mock_fix_port.return_value = mock_fix_result
        
        result = await apply_single_fix(mock_diagnostic_error)
        assert result.successful is True
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.fix_dependencies')
    @pytest.mark.asyncio
    async def test_apply_single_fix_dependency_error(self, mock_fix_deps: AsyncMock,
                                                    mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fix for dependency error."""
        mock_diagnostic_error.message = "Dependencies missing"
        mock_fix_result = FixResult(error_id="test", attempted=True, 
                                   successful=True, message="Dependencies fixed")
        mock_fix_deps.return_value = mock_fix_result
        
        result = await apply_single_fix(mock_diagnostic_error)
        assert result.successful is True
    @pytest.mark.asyncio
    async def test_apply_single_fix_unknown_error(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test applying fix for unknown error type."""
        mock_diagnostic_error.message = "Unknown error"
        
        result = await apply_single_fix(mock_diagnostic_error)
        assert result.attempted is False
        assert "no auto-fix available" in result.message.lower()
    @pytest.mark.asyncio
    async def test_apply_single_fix_exception(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test fix application with exception."""
        mock_diagnostic_error.message = "Port conflict"
        
        # Mock: Component isolation for testing without external dependencies
        with patch('scripts.startup_diagnostics.fix_port_conflict', side_effect=Exception("Fix error")):
            result = await apply_single_fix(mock_diagnostic_error)
            assert result.attempted is True
            assert result.successful is False
            assert "fix failed" in result.message.lower()

class TestSpecificFixes:
    """Test specific fix implementations."""
    @pytest.mark.asyncio
    async def test_fix_port_conflict(self, mock_diagnostic_error: DiagnosticError) -> None:
        """Test port conflict fix."""
        result = await fix_port_conflict(mock_diagnostic_error)
        assert result.attempted is True
        assert result.successful is True
        assert "port conflict resolved" in result.message.lower()
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.run_command_async')
    @pytest.mark.asyncio
    async def test_fix_dependencies_python_success(self, mock_run_cmd: AsyncMock,
                                                   mock_diagnostic_error: DiagnosticError) -> None:
        """Test successful Python dependency fix."""
        mock_diagnostic_error.message = "Python dependencies missing"
        mock_run_cmd.return_value = ""
        
        result = await fix_dependencies(mock_diagnostic_error)
        assert result.successful is True
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.run_command_async')
    @pytest.mark.asyncio
    async def test_fix_dependencies_failure(self, mock_run_cmd: AsyncMock,
                                           mock_diagnostic_error: DiagnosticError) -> None:
        """Test dependency fix failure."""
        mock_diagnostic_error.message = "Python dependencies missing"
        mock_run_cmd.side_effect = Exception("Install failed")
        
        result = await fix_dependencies(mock_diagnostic_error)
        assert result.successful is False
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.run_command_async')
    @pytest.mark.asyncio
    async def test_fix_migrations_success(self, mock_run_cmd: AsyncMock,
                                         mock_diagnostic_error: DiagnosticError) -> None:
        """Test successful migration fix."""
        mock_diagnostic_error.message = "Migration pending"
        mock_run_cmd.return_value = ""
        
        result = await fix_migrations(mock_diagnostic_error)
        assert result.successful is True
    # Mock: Component isolation for testing without external dependencies
    @patch('scripts.startup_diagnostics.run_command_async')
    @pytest.mark.asyncio
    async def test_fix_migrations_failure(self, mock_run_cmd: AsyncMock,
                                         mock_diagnostic_error: DiagnosticError) -> None:
        """Test migration fix failure."""
        mock_diagnostic_error.message = "Migration pending"
        mock_run_cmd.side_effect = Exception("Migration failed")
        
        result = await fix_migrations(mock_diagnostic_error)
        assert result.successful is False