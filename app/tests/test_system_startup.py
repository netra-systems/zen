"""Comprehensive tests for startup_checks.py module to achieve 100% coverage."""

import os
import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, AsyncMock, patch, PropertyMock
from pathlib import Path
import tempfile
import shutil

from app.startup_checks import (
    StartupCheckResult,
    StartupChecker,
    run_startup_checks
)
from app.schemas.Config import NetraTestingConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestStartupCheckResult:
    """Test StartupCheckResult class."""
    
    def test_initialization(self):
        """Test StartupCheckResult initialization with all parameters."""
        result = StartupCheckResult(
            name="test_check",
            success=True,
            message="Test passed",
            critical=False,
            duration_ms=123.45
        )
        
        assert result.name == "test_check"
        assert result.success is True
        assert result.message == "Test passed"
        assert result.critical is False
        assert result.duration_ms == 123.45
    
    def test_default_values(self):
        """Test StartupCheckResult with default values."""
        result = StartupCheckResult(
            name="test",
            success=False,
            message="Failed"
        )
        
        assert result.critical is True
        assert result.duration_ms == 0


class TestStartupChecker:
    """Test StartupChecker class."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        app = Mock()
        app.state = Mock()
        
        # Mock database session factory
        db_session = AsyncMock(spec=AsyncSession)
        db_session.__aenter__ = AsyncMock(return_value=db_session)
        db_session.__aexit__ = AsyncMock(return_value=None)
        app.state.db_session_factory = Mock(return_value=db_session)
        
        # Mock Redis manager
        redis_manager = AsyncMock()
        redis_manager.connect = AsyncMock()
        redis_manager.set = AsyncMock()
        redis_manager.get = AsyncMock(return_value="test_value")
        redis_manager.delete = AsyncMock()
        app.state.redis_manager = redis_manager
        
        # Mock LLM manager
        llm_manager = Mock()
        llm_manager.get_llm = Mock(return_value=Mock())
        app.state.llm_manager = llm_manager
        
        return app
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_run_all_checks_success(self, checker, monkeypatch):
        """Test running all checks successfully."""
        # Mock all check methods to succeed
        async def mock_check():
            checker.results.append(StartupCheckResult(
                name="test_check",
                success=True,
                message="Success",
                critical=True
            ))
        
        checker.check_environment_variables = AsyncMock(side_effect=mock_check)
        checker.check_configuration = AsyncMock(side_effect=mock_check)
        checker.check_file_permissions = AsyncMock(side_effect=mock_check)
        checker.check_database_connection = AsyncMock(side_effect=mock_check)
        checker.check_redis = AsyncMock(side_effect=mock_check)
        checker.check_clickhouse = AsyncMock(side_effect=mock_check)
        checker.check_llm_providers = AsyncMock(side_effect=mock_check)
        checker.check_memory_and_resources = AsyncMock(side_effect=mock_check)
        checker.check_network_connectivity = AsyncMock(side_effect=mock_check)
        checker.check_or_create_assistant = AsyncMock(side_effect=mock_check)
        
        results = await checker.run_all_checks()
        
        assert results["success"] is True
        assert results["total_checks"] == 10
        assert results["passed"] == 10
        assert results["failed_critical"] == 0
        assert results["failed_non_critical"] == 0
        assert results["duration_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_failures(self, checker):
        """Test running checks with critical and non-critical failures."""
        async def mock_critical_failure():
            checker.results.append(StartupCheckResult(
                name="critical_check",
                success=False,
                message="Critical failure",
                critical=True
            ))
        
        async def mock_non_critical_failure():
            checker.results.append(StartupCheckResult(
                name="non_critical_check",
                success=False,
                message="Non-critical failure",
                critical=False
            ))
        
        checker.check_environment_variables = AsyncMock(side_effect=mock_critical_failure)
        checker.check_configuration = AsyncMock(side_effect=mock_non_critical_failure)
        checker.check_file_permissions = AsyncMock()
        checker.check_database_connection = AsyncMock()
        checker.check_redis = AsyncMock()
        checker.check_clickhouse = AsyncMock()
        checker.check_llm_providers = AsyncMock()
        checker.check_memory_and_resources = AsyncMock()
        checker.check_network_connectivity = AsyncMock()
        checker.check_or_create_assistant = AsyncMock()
        
        results = await checker.run_all_checks()
        
        assert results["success"] is False
        assert results["failed_critical"] == 1
        assert results["failed_non_critical"] == 1
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_exception(self, checker):
        """Test handling of unexpected exceptions during checks."""
        async def mock_exception():
            raise RuntimeError("Unexpected error")
        
        checker.check_environment_variables = AsyncMock(side_effect=mock_exception)
        checker.check_configuration = AsyncMock()
        checker.check_file_permissions = AsyncMock()
        checker.check_database_connection = AsyncMock()
        checker.check_redis = AsyncMock()
        checker.check_clickhouse = AsyncMock()
        checker.check_llm_providers = AsyncMock()
        checker.check_memory_and_resources = AsyncMock()
        checker.check_network_connectivity = AsyncMock()
        checker.check_or_create_assistant = AsyncMock()
        
        results = await checker.run_all_checks()
        
        assert results["success"] is False
        assert results["failed_critical"] == 1
        assert "Unexpected error" in results["failures"][0].message
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_dev_mode(self, checker, monkeypatch):
        """Test environment variable check in development mode."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is True
        assert "Development mode" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_production_missing(self, checker, monkeypatch):
        """Test environment variable check in production with missing required vars."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is False
        assert "Missing required" in checker.results[0].message
        assert checker.results[0].critical is True
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_with_optional(self, checker, monkeypatch):
        """Test environment variable check with optional variables missing."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is True
        assert "Optional missing" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_configuration_success(self, checker, monkeypatch):
        """Test configuration validation success."""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = "postgresql://localhost/test"
            mock_settings.secret_key = "a" * 32
            mock_settings.environment = "development"
            
            await checker.check_configuration()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is True
    
    @pytest.mark.asyncio
    async def test_check_configuration_missing_database(self, checker):
        """Test configuration validation with missing database URL."""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = None
            
            await checker.check_configuration()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert "DATABASE_URL" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_configuration_short_secret_production(self, checker):
        """Test configuration validation with short secret key in production."""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = "postgresql://localhost/test"
            mock_settings.secret_key = "short"
            mock_settings.environment = "production"
            
            await checker.check_configuration()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert "SECRET_KEY" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_configuration_invalid_environment(self, checker):
        """Test configuration validation with invalid environment."""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = "postgresql://localhost/test"
            mock_settings.secret_key = "a" * 32
            mock_settings.environment = "invalid"
            
            await checker.check_configuration()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert "Invalid environment" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_file_permissions_success(self, checker):
        """Test file permissions check success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                await checker.check_file_permissions()
                
                assert len(checker.results) == 1
                assert checker.results[0].success is True
                assert "accessible" in checker.results[0].message
                
                # Verify directories were created
                assert Path("logs").exists()
                assert Path("uploads").exists()
                assert Path("temp").exists()
            finally:
                os.chdir(original_cwd)
    
    @pytest.mark.asyncio
    async def test_check_file_permissions_failure(self, checker):
        """Test file permissions check with write permission failure."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("No permission")
            
            await checker.check_file_permissions()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert "Permission issues" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_database_connection_success(self, mock_app, checker):
        """Test database connection check success."""
        db_session = mock_app.state.db_session_factory.return_value
        
        # Mock successful queries
        db_session.execute = AsyncMock()
        
        # Mock SELECT 1 result
        select_result = Mock()
        select_result.scalar_one = Mock(return_value=1)
        
        # Mock table existence results
        table_result = Mock()
        table_result.scalar_one = Mock(return_value=True)
        
        db_session.execute.side_effect = [select_result] + [table_result] * 4
        
        await checker.check_database_connection()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is True
        assert "PostgreSQL connected" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_database_connection_missing_table(self, mock_app, checker):
        """Test database connection check with missing table."""
        db_session = mock_app.state.db_session_factory.return_value
        
        # Mock successful connection but missing table
        select_result = Mock()
        select_result.scalar_one = Mock(return_value=1)
        
        table_result = Mock()
        table_result.scalar_one = Mock(return_value=False)
        
        db_session.execute = AsyncMock(side_effect=[select_result, table_result])
        
        await checker.check_database_connection()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is False
        assert "does not exist" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self, mock_app, checker):
        """Test database connection check with connection failure."""
        db_session = mock_app.state.db_session_factory.return_value
        db_session.execute = AsyncMock(side_effect=Exception("Connection failed"))
        
        await checker.check_database_connection()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is False
        assert "Connection failed" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_redis_success(self, mock_app, checker):
        """Test Redis check success."""
        redis_manager = mock_app.state.redis_manager
        # Return the same value that was set
        redis_manager.set = AsyncMock()
        redis_manager.get = AsyncMock()
        redis_manager.delete = AsyncMock()
        
        # Capture the value that's set and return it on get
        async def mock_set(key, value, **kwargs):
            redis_manager._test_value = value
        
        async def mock_get(key):
            return redis_manager._test_value if hasattr(redis_manager, '_test_value') else "test_value"
        
        redis_manager.set = AsyncMock(side_effect=mock_set)
        redis_manager.get = AsyncMock(side_effect=mock_get)
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            await checker.check_redis()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is True
            assert "Redis connected" in checker.results[0].message
            
            # Verify operations were called
            redis_manager.connect.assert_called_once()
            redis_manager.set.assert_called_once()
            redis_manager.get.assert_called_once()
            redis_manager.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_redis_read_write_failure(self, mock_app, checker):
        """Test Redis check with read/write test failure."""
        redis_manager = mock_app.state.redis_manager
        redis_manager.get = AsyncMock(return_value="wrong_value")
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            await checker.check_redis()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert "read/write test failed" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_redis_connection_failure_production(self, mock_app, checker):
        """Test Redis check with connection failure in production (critical)."""
        redis_manager = mock_app.state.redis_manager
        redis_manager.connect = AsyncMock(side_effect=Exception("Connection refused"))
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "production"
            
            await checker.check_redis()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert checker.results[0].critical is True
            assert "Connection refused" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_redis_connection_failure_development(self, mock_app, checker):
        """Test Redis check with connection failure in development (non-critical)."""
        redis_manager = mock_app.state.redis_manager
        redis_manager.connect = AsyncMock(side_effect=Exception("Connection refused"))
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            await checker.check_redis()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert checker.results[0].critical is False
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_success(self, checker):
        """Test ClickHouse check success."""
        mock_client = AsyncMock()
        mock_client.ping = Mock()
        mock_client.execute_query = AsyncMock(return_value=[
            {'name': 'workload_events'},
            {'name': 'other_table'}
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                
                await checker.check_clickhouse()
                
                assert len(checker.results) == 1
                assert checker.results[0].success is True
                assert "2 tables" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_missing_tables(self, checker):
        """Test ClickHouse check with missing required tables."""
        mock_client = AsyncMock()
        mock_client.ping = Mock()
        mock_client.execute_query = AsyncMock(return_value=[
            {'name': 'other_table'}
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                
                await checker.check_clickhouse()
                
                assert len(checker.results) == 1
                assert checker.results[0].success is False
                assert "Missing ClickHouse tables" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_connection_failure(self, checker):
        """Test ClickHouse check with connection failure."""
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                
                await checker.check_clickhouse()
                
                assert len(checker.results) == 1
                assert checker.results[0].success is False
                assert "Connection failed" in checker.results[0].message
                assert checker.results[0].critical is False
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_tuple_result(self, checker):
        """Test ClickHouse check with tuple result format."""
        mock_client = AsyncMock()
        mock_client.ping = Mock()
        mock_client.execute_query = AsyncMock(return_value=[
            ('workload_events',),
            ('other_table',)
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                
                await checker.check_clickhouse()
                
                assert len(checker.results) == 1
                assert checker.results[0].success is True
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_success(self, mock_app, checker):
        """Test LLM providers check with all providers available."""
        llm_manager = mock_app.state.llm_manager
        llm_manager.get_llm = Mock(return_value=Mock())
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {},
                'gpt-4': {}
            }
            mock_settings.environment = "development"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is True
            assert "2 LLM providers configured" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_partial_failure(self, mock_app, checker):
        """Test LLM providers check with some providers failing."""
        llm_manager = mock_app.state.llm_manager
        
        def get_llm_side_effect(name):
            if name == 'gpt-4':
                raise Exception("API key missing")
            return Mock()
        
        llm_manager.get_llm = Mock(side_effect=get_llm_side_effect)
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {},
                'gpt-4': {}
            }
            mock_settings.environment = "development"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is True
            assert "1 available, 1 failed" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_failed(self, mock_app, checker):
        """Test LLM providers check with all providers failing."""
        llm_manager = mock_app.state.llm_manager
        llm_manager.get_llm = Mock(side_effect=Exception("No providers available"))
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {},
            }
            mock_settings.environment = "development"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert "No LLM providers available" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_critical_provider_not_initialized(self, mock_app, checker):
        """Test LLM providers check with critical provider returning None."""
        llm_manager = mock_app.state.llm_manager
        llm_manager.get_llm = Mock(return_value=None)
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-opus': {},
            }
            mock_settings.environment = "development"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_exception(self, mock_app, checker):
        """Test LLM providers check with unexpected exception."""
        mock_app.state.llm_manager = None
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "production"
            
            await checker.check_llm_providers()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is False
            assert checker.results[0].critical is True
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_ok(self, checker):
        """Test system resources check with adequate resources."""
        with patch('app.startup_checks.psutil') as mock_psutil:
            # Mock adequate resources
            mock_memory = Mock()
            mock_memory.total = 16 * (1024**3)  # 16 GB
            mock_memory.available = 8 * (1024**3)  # 8 GB
            mock_psutil.virtual_memory.return_value = mock_memory
            
            mock_disk = Mock()
            mock_disk.free = 100 * (1024**3)  # 100 GB
            mock_psutil.disk_usage.return_value = mock_disk
            
            mock_psutil.cpu_count.return_value = 8
            
            await checker.check_memory_and_resources()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is True
            assert "Resources OK" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_warnings(self, checker):
        """Test system resources check with resource warnings."""
        with patch('app.startup_checks.psutil') as mock_psutil:
            # Mock low resources
            mock_memory = Mock()
            mock_memory.total = 4 * (1024**3)  # 4 GB
            mock_memory.available = 0.5 * (1024**3)  # 0.5 GB
            mock_psutil.virtual_memory.return_value = mock_memory
            
            mock_disk = Mock()
            mock_disk.free = 2 * (1024**3)  # 2 GB
            mock_psutil.disk_usage.return_value = mock_disk
            
            mock_psutil.cpu_count.return_value = 1
            
            await checker.check_memory_and_resources()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is True
            assert "Resource warnings" in checker.results[0].message
            assert "Low memory" in checker.results[0].message
            assert "Low disk space" in checker.results[0].message
            assert "Low CPU count" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_exception(self, checker):
        """Test system resources check with exception."""
        with patch('app.startup_checks.psutil.virtual_memory', side_effect=Exception("Cannot read memory")):
            await checker.check_memory_and_resources()
            
            assert len(checker.results) == 1
            assert checker.results[0].success is True  # Non-critical failure
            assert "Could not check resources" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_success(self, checker):
        """Test network connectivity check success."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 0
            mock_socket_class.return_value = mock_socket
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user:pass@localhost:5432/db"
                mock_settings.redis = Mock(host="localhost", port=6379)
                
                await checker.check_network_connectivity()
                
                assert len(checker.results) == 1
                assert checker.results[0].success is True
                assert "All network endpoints reachable" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_failure(self, checker):
        """Test network connectivity check with unreachable endpoints."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 1  # Connection failed
            mock_socket_class.return_value = mock_socket
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user:pass@localhost:5432/db"
                mock_settings.redis = Mock(host="localhost", port=6379)
                
                await checker.check_network_connectivity()
                
                assert len(checker.results) == 1
                assert checker.results[0].success is False
                assert "Cannot reach" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_socket_exception(self, checker):
        """Test network connectivity check with socket exception."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.side_effect = Exception("Socket error")
            mock_socket_class.return_value = mock_socket
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://localhost/db"
                mock_settings.redis = None
                
                await checker.check_network_connectivity()
                
                assert len(checker.results) == 1
                assert checker.results[0].success is False
                assert "Socket error" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_no_port(self, checker):
        """Test network connectivity check with endpoint without port."""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 0
            mock_socket_class.return_value = mock_socket
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://hostname/db"
                mock_settings.redis = None
                
                await checker.check_network_connectivity()
                
                assert len(checker.results) == 1
                # Check that hostname was used (endpoint will be 'hostname' with no port)
                assert checker.results[0].success is True
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_exists(self, mock_app, checker):
        """Test assistant check when assistant already exists."""
        db_session = mock_app.state.db_session_factory.return_value
        
        # Mock existing assistant
        mock_result = Mock()
        mock_assistant = Mock(id="netra-assistant")
        mock_result.scalar_one_or_none = Mock(return_value=mock_assistant)
        db_session.execute = AsyncMock(return_value=mock_result)
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is True
        assert "already exists" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_create_new(self, mock_app, checker):
        """Test assistant check when creating new assistant."""
        db_session = mock_app.state.db_session_factory.return_value
        
        # Mock no existing assistant
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        db_session.execute = AsyncMock(return_value=mock_result)
        db_session.add = Mock()
        db_session.commit = AsyncMock()
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is True
        assert "created successfully" in checker.results[0].message
        
        # Verify assistant was added
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_failure(self, mock_app, checker):
        """Test assistant check with database error."""
        db_session = mock_app.state.db_session_factory.return_value
        db_session.execute = AsyncMock(side_effect=Exception("Database error"))
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        assert checker.results[0].success is False
        assert "Database error" in checker.results[0].message
        assert checker.results[0].critical is False


class TestRunStartupChecks:
    """Test the main run_startup_checks function."""
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_success(self):
        """Test successful startup checks."""
        mock_app = Mock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            mock_checker.run_all_checks = AsyncMock(return_value={
                'success': True,
                'total_checks': 10,
                'passed': 10,
                'failed_critical': 0,
                'failed_non_critical': 0,
                'duration_ms': 1000,
                'failures': []
            })
            MockChecker.return_value = mock_checker
            
            results = await run_startup_checks(mock_app)
            
            assert results['success'] is True
            assert results['passed'] == 10
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_critical_failure(self):
        """Test startup checks with critical failures."""
        mock_app = Mock()
        
        mock_failure = StartupCheckResult(
            name="critical_check",
            success=False,
            message="Critical failure",
            critical=True
        )
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            mock_checker.run_all_checks = AsyncMock(return_value={
                'success': False,
                'total_checks': 10,
                'passed': 9,
                'failed_critical': 1,
                'failed_non_critical': 0,
                'duration_ms': 1000,
                'failures': [mock_failure]
            })
            MockChecker.return_value = mock_checker
            
            with pytest.raises(RuntimeError, match="Startup failed: 1 critical checks failed"):
                await run_startup_checks(mock_app)
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_non_critical_failure(self):
        """Test startup checks with only non-critical failures."""
        mock_app = Mock()
        
        mock_failure = StartupCheckResult(
            name="non_critical_check",
            success=False,
            message="Non-critical failure",
            critical=False
        )
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            mock_checker.run_all_checks = AsyncMock(return_value={
                'success': True,
                'total_checks': 10,
                'passed': 9,
                'failed_critical': 0,
                'failed_non_critical': 1,
                'duration_ms': 1000,
                'failures': [mock_failure]
            })
            MockChecker.return_value = mock_checker
            
            results = await run_startup_checks(mock_app)
            
            assert results['success'] is True
            assert results['failed_non_critical'] == 1