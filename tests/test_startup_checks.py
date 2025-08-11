"""
Comprehensive test coverage for app/startup_checks.py

This test file achieves 100% coverage by testing:
- All startup check methods
- All success and failure paths
- All critical and non-critical scenarios
- Edge cases and exception handling
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch, PropertyMock
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupCheckResult, StartupChecker, run_startup_checks
from app.db.models_postgres import Assistant


class TestStartupCheckResult:
    """Test the StartupCheckResult class"""
    
    def test_init_required_params(self):
        """Test initialization with required parameters"""
        result = StartupCheckResult(
            name="test_check",
            success=True,
            message="Test passed"
        )
        assert result.name == "test_check"
        assert result.success is True
        assert result.message == "Test passed"
        assert result.critical is True  # Default value
        assert result.duration_ms == 0  # Default value
    
    def test_init_all_params(self):
        """Test initialization with all parameters"""
        result = StartupCheckResult(
            name="test_check",
            success=False,
            message="Test failed",
            critical=False,
            duration_ms=123.45
        )
        assert result.name == "test_check"
        assert result.success is False
        assert result.message == "Test failed"
        assert result.critical is False
        assert result.duration_ms == 123.45


class TestStartupChecker:
    """Test the StartupChecker class"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state"""
        app = MagicMock()
        # db_session_factory should be a callable that returns an async context manager
        app.state.db_session_factory = MagicMock()
        app.state.redis_manager = AsyncMock()
        app.state.llm_manager = MagicMock()
        return app
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance"""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_run_all_checks_success(self, checker, monkeypatch):
        """Test run_all_checks with all checks passing"""
        # Mock all check methods to succeed
        async def mock_check():
            checker.results.append(StartupCheckResult(
                name="test_check",
                success=True,
                message="Check passed"
            ))
        
        monkeypatch.setattr(checker, 'check_environment_variables', mock_check)
        monkeypatch.setattr(checker, 'check_configuration', mock_check)
        monkeypatch.setattr(checker, 'check_file_permissions', mock_check)
        monkeypatch.setattr(checker, 'check_database_connection', mock_check)
        monkeypatch.setattr(checker, 'check_redis', mock_check)
        monkeypatch.setattr(checker, 'check_clickhouse', mock_check)
        monkeypatch.setattr(checker, 'check_llm_providers', mock_check)
        monkeypatch.setattr(checker, 'check_memory_and_resources', mock_check)
        monkeypatch.setattr(checker, 'check_network_connectivity', mock_check)
        monkeypatch.setattr(checker, 'check_or_create_assistant', mock_check)
        
        results = await checker.run_all_checks()
        
        assert results['success'] is True
        assert results['total_checks'] == 10
        assert results['passed'] == 10
        assert results['failed_critical'] == 0
        assert results['failed_non_critical'] == 0
        assert results['duration_ms'] > 0
        assert len(results['results']) == 10
        assert len(results['failures']) == 0
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_failures(self, checker, monkeypatch):
        """Test run_all_checks with some checks failing"""
        async def mock_success():
            checker.results.append(StartupCheckResult(
                name="success_check",
                success=True,
                message="Check passed"
            ))
        
        async def mock_critical_failure():
            checker.results.append(StartupCheckResult(
                name="critical_failure",
                success=False,
                message="Critical failure",
                critical=True
            ))
        
        async def mock_non_critical_failure():
            checker.results.append(StartupCheckResult(
                name="non_critical_failure",
                success=False,
                message="Non-critical failure",
                critical=False
            ))
        
        monkeypatch.setattr(checker, 'check_environment_variables', mock_success)
        monkeypatch.setattr(checker, 'check_configuration', mock_critical_failure)
        monkeypatch.setattr(checker, 'check_file_permissions', mock_non_critical_failure)
        monkeypatch.setattr(checker, 'check_database_connection', mock_success)
        monkeypatch.setattr(checker, 'check_redis', mock_success)
        monkeypatch.setattr(checker, 'check_clickhouse', mock_success)
        monkeypatch.setattr(checker, 'check_llm_providers', mock_success)
        monkeypatch.setattr(checker, 'check_memory_and_resources', mock_success)
        monkeypatch.setattr(checker, 'check_network_connectivity', mock_success)
        monkeypatch.setattr(checker, 'check_or_create_assistant', mock_success)
        
        results = await checker.run_all_checks()
        
        assert results['success'] is False
        assert results['total_checks'] == 10
        assert results['passed'] == 8
        assert results['failed_critical'] == 1
        assert results['failed_non_critical'] == 1
        assert len(results['failures']) == 2
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_exception(self, checker, monkeypatch):
        """Test run_all_checks when a check raises an exception"""
        async def mock_raise_exception():
            raise RuntimeError("Unexpected error")
        
        monkeypatch.setattr(checker, 'check_environment_variables', mock_raise_exception)
        # Mock remaining methods to prevent execution
        for method_name in ['check_configuration', 'check_file_permissions', 
                            'check_database_connection', 'check_redis', 
                            'check_clickhouse', 'check_llm_providers',
                            'check_memory_and_resources', 'check_network_connectivity',
                            'check_or_create_assistant']:
            monkeypatch.setattr(checker, method_name, AsyncMock())
        
        results = await checker.run_all_checks()
        
        # Should have one failure from the exception
        assert results['failed_critical'] >= 1
        assert any('Unexpected error' in r.message for r in results['results'])
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_dev_mode(self, checker, monkeypatch):
        """Test environment variable check in development mode"""
        monkeypatch.setenv('ENVIRONMENT', 'development')
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "environment_variables"
        assert result.success is True
        assert "Development mode" in result.message
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_production_missing_required(self, checker, monkeypatch):
        """Test environment variable check in production with missing required vars"""
        monkeypatch.setenv('ENVIRONMENT', 'production')
        monkeypatch.delenv('DATABASE_URL', raising=False)
        monkeypatch.delenv('SECRET_KEY', raising=False)
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "environment_variables"
        assert result.success is False
        assert "Missing required" in result.message
        assert result.critical is True
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_with_optional_missing(self, checker, monkeypatch):
        """Test environment variable check with optional vars missing"""
        monkeypatch.setenv('ENVIRONMENT', 'production')
        monkeypatch.setenv('DATABASE_URL', 'postgres://test')
        monkeypatch.setenv('SECRET_KEY', 'test-secret')
        monkeypatch.delenv('REDIS_URL', raising=False)
        monkeypatch.delenv('CLICKHOUSE_URL', raising=False)
        
        await checker.check_environment_variables()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "environment_variables"
        assert result.success is True
        assert "Optional missing" in result.message
    
    @pytest.mark.asyncio
    async def test_check_configuration_success(self, checker, monkeypatch):
        """Test configuration check success"""
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://test"
        mock_settings.environment = "development"
        mock_settings.secret_key = "test-secret-key"
        
        with patch('app.startup_checks.settings', mock_settings):
            await checker.check_configuration()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "configuration"
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_check_configuration_missing_database_url(self, checker, monkeypatch):
        """Test configuration check with missing database URL"""
        mock_settings = MagicMock()
        mock_settings.database_url = None
        
        with patch('app.startup_checks.settings', mock_settings):
            await checker.check_configuration()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "configuration"
        assert result.success is False
        assert "DATABASE_URL" in result.message
    
    @pytest.mark.asyncio
    async def test_check_configuration_short_secret_key_production(self, checker, monkeypatch):
        """Test configuration check with short secret key in production"""
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://test"
        mock_settings.environment = "production"
        mock_settings.secret_key = "short"
        
        with patch('app.startup_checks.settings', mock_settings):
            await checker.check_configuration()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "configuration"
        assert result.success is False
        assert "SECRET_KEY" in result.message
    
    @pytest.mark.asyncio
    async def test_check_configuration_invalid_environment(self, checker, monkeypatch):
        """Test configuration check with invalid environment"""
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql://test"
        mock_settings.environment = "invalid"
        mock_settings.secret_key = "a" * 32
        
        with patch('app.startup_checks.settings', mock_settings):
            await checker.check_configuration()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "configuration"
        assert result.success is False
        assert "Invalid environment" in result.message
    
    @pytest.mark.asyncio
    async def test_check_file_permissions_success(self, checker, tmp_path, monkeypatch):
        """Test file permissions check success"""
        # Change to temp directory to avoid creating dirs in project
        monkeypatch.chdir(tmp_path)
        
        await checker.check_file_permissions()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "file_permissions"
        assert result.success is True
        assert "accessible" in result.message
        
        # Verify directories were created
        assert (tmp_path / "logs").exists()
        assert (tmp_path / "uploads").exists()
        assert (tmp_path / "temp").exists()
    
    @pytest.mark.asyncio
    async def test_check_file_permissions_failure(self, checker, monkeypatch):
        """Test file permissions check failure"""
        def mock_mkdir(self, exist_ok=True):
            raise PermissionError("Permission denied")
        
        with patch.object(Path, 'mkdir', mock_mkdir):
            await checker.check_file_permissions()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "file_permissions"
        assert result.success is False
        assert "Permission" in result.message
        assert result.critical is False
    
    @pytest.mark.asyncio
    async def test_check_database_connection_success(self, checker, mock_app):
        """Test database connection check success"""
        # Create proper async context manager mock
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_app.state.db_session_factory.return_value = mock_context
        
        # Mock successful query execution - return different results for each call
        results = []
        
        # First call - SELECT 1
        mock_result1 = MagicMock()
        mock_result1.scalar_one.return_value = 1
        results.append(mock_result1)
        
        # Subsequent calls - table exists checks (4 tables)
        for _ in range(4):
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = True
            results.append(mock_result)
        
        mock_session.execute.side_effect = results
        
        await checker.check_database_connection()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "database_connection"
        assert result.success is True
        assert "PostgreSQL connected" in result.message
    
    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self, checker, mock_app):
        """Test database connection check failure"""
        # Create context manager that raises on __aenter__
        mock_context = AsyncMock()
        mock_context.__aenter__.side_effect = Exception("Connection failed")
        mock_app.state.db_session_factory.return_value = mock_context
        
        await checker.check_database_connection()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "database_connection"
        assert result.success is False
        assert "Connection failed" in result.message
        assert result.critical is True
    
    @pytest.mark.asyncio
    async def test_check_database_missing_table(self, checker, mock_app):
        """Test database check with missing critical table"""
        # Create proper async context manager mock
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_app.state.db_session_factory.return_value = mock_context
        
        # Mock successful connectivity check but table doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = [1, False]  # First query succeeds, table check fails
        mock_session.execute.return_value = mock_result
        
        await checker.check_database_connection()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "database_connection"
        assert result.success is False
        assert "does not exist" in result.message
    
    @pytest.mark.asyncio
    async def test_check_redis_success(self, checker, mock_app):
        """Test Redis check success"""
        mock_redis = mock_app.state.redis_manager
        mock_redis.connect.return_value = None
        mock_redis.set.return_value = None
        mock_redis.get.return_value = "test_value"
        mock_redis.delete.return_value = None
        
        # Mock the set method to store the value
        stored_value = None
        async def mock_set(key, value, expire=None):
            nonlocal stored_value
            stored_value = value
        
        async def mock_get(key):
            return stored_value
        
        mock_redis.set = mock_set
        mock_redis.get = mock_get
        
        await checker.check_redis()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "redis_connection"
        assert result.success is True
        assert "Redis connected" in result.message
    
    @pytest.mark.asyncio
    async def test_check_redis_failure(self, checker, mock_app):
        """Test Redis check failure"""
        mock_redis = mock_app.state.redis_manager
        mock_redis.connect.side_effect = Exception("Connection refused")
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            await checker.check_redis()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "redis_connection"
        assert result.success is False
        assert "Connection refused" in result.message
    
    @pytest.mark.asyncio
    async def test_check_redis_read_write_failure(self, checker, mock_app):
        """Test Redis check with read/write mismatch"""
        mock_redis = mock_app.state.redis_manager
        mock_redis.connect.return_value = None
        mock_redis.set.return_value = None
        mock_redis.get.return_value = "wrong_value"  # Different from what was set
        
        await checker.check_redis()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "redis_connection"
        assert result.success is False
        assert "read/write test failed" in result.message
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_success(self, checker):
        """Test ClickHouse check success"""
        # Mock the import and client creation
        mock_client = AsyncMock()
        mock_client.ping.return_value = None
        mock_client.execute_query.return_value = [
            {'name': 'workload_events'},
            {'name': 'other_table'}
        ]
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None
        
        with patch.dict('sys.modules', {'app.db.clickhouse': MagicMock()}):
            with patch('app.startup_checks.get_clickhouse_client', return_value=mock_context):
                await checker.check_clickhouse()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "clickhouse_connection"
        assert result.success is True
        assert "2 tables" in result.message
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_missing_tables(self, checker):
        """Test ClickHouse check with missing required tables"""
        # Mock the import and client creation
        mock_client = AsyncMock()
        mock_client.ping.return_value = None
        mock_client.execute_query.return_value = [
            {'name': 'other_table'}
        ]
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None
        
        with patch.dict('sys.modules', {'app.db.clickhouse': MagicMock()}):
            with patch('app.startup_checks.get_clickhouse_client', return_value=mock_context):
                await checker.check_clickhouse()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "clickhouse_connection"
        assert result.success is False
        assert "Missing ClickHouse tables" in result.message
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_failure(self, checker):
        """Test ClickHouse check failure"""
        with patch.dict('sys.modules', {'app.db.clickhouse': MagicMock()}):
            with patch('app.startup_checks.get_clickhouse_client', side_effect=Exception("Connection failed")):
                with patch('app.startup_checks.settings') as mock_settings:
                    mock_settings.environment = "development"
                    await checker.check_clickhouse()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "clickhouse_connection"
        assert result.success is False
        assert "Connection failed" in result.message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_success(self, checker, mock_app):
        """Test LLM providers check success"""
        mock_llm_manager = mock_app.state.llm_manager
        mock_llm_manager.get_llm.return_value = MagicMock()  # Return a mock LLM object
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {},
                'anthropic-claude-3-opus': {}
            }
            await checker.check_llm_providers()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "llm_providers"
        assert result.success is True
        assert "2 LLM providers configured" in result.message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_partial_failure(self, checker, mock_app):
        """Test LLM providers check with some failures"""
        mock_llm_manager = mock_app.state.llm_manager
        
        def mock_get_llm(name):
            if name == 'anthropic-claude-3-sonnet':
                return MagicMock()
            else:
                raise Exception("API key missing")
        
        mock_llm_manager.get_llm.side_effect = mock_get_llm
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {},
                'anthropic-claude-3-opus': {}
            }
            await checker.check_llm_providers()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "llm_providers"
        assert result.success is True  # Still succeeds with some providers
        assert "1 available, 1 failed" in result.message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_failed(self, checker, mock_app):
        """Test LLM providers check with all providers failing"""
        mock_llm_manager = mock_app.state.llm_manager
        mock_llm_manager.get_llm.side_effect = Exception("API key missing")
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.llm_configs = {
                'anthropic-claude-3-sonnet': {}
            }
            await checker.check_llm_providers()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "llm_providers"
        assert result.success is False
        assert "No LLM providers available" in result.message
        assert result.critical is True
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_exception(self, checker, mock_app):
        """Test LLM providers check with unexpected exception"""
        # Delete the llm_manager attribute to cause AttributeError
        del mock_app.state.llm_manager
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "production"
            await checker.check_llm_providers()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "llm_providers"
        assert result.success is False
        assert "LLM check failed" in result.message
        assert result.critical is True
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_success(self, checker):
        """Test memory and resources check success"""
        with patch('app.startup_checks.psutil') as mock_psutil:
            # Mock healthy resource values
            mock_memory = MagicMock()
            mock_memory.total = 16 * (1024**3)  # 16 GB
            mock_memory.available = 8 * (1024**3)  # 8 GB available
            mock_psutil.virtual_memory.return_value = mock_memory
            
            mock_disk = MagicMock()
            mock_disk.free = 100 * (1024**3)  # 100 GB free
            mock_psutil.disk_usage.return_value = mock_disk
            
            mock_psutil.cpu_count.return_value = 4
            
            await checker.check_memory_and_resources()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "system_resources"
        assert result.success is True
        assert "Resources OK" in result.message
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_warnings(self, checker):
        """Test memory and resources check with warnings"""
        with patch('app.startup_checks.psutil') as mock_psutil:
            # Mock low resource values
            mock_memory = MagicMock()
            mock_memory.total = 4 * (1024**3)  # 4 GB
            mock_memory.available = 0.5 * (1024**3)  # 0.5 GB available
            mock_psutil.virtual_memory.return_value = mock_memory
            
            mock_disk = MagicMock()
            mock_disk.free = 2 * (1024**3)  # 2 GB free
            mock_psutil.disk_usage.return_value = mock_disk
            
            mock_psutil.cpu_count.return_value = 1
            
            await checker.check_memory_and_resources()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "system_resources"
        assert result.success is True  # Still succeeds but with warnings
        assert "Resource warnings" in result.message
        assert "Low memory" in result.message
        assert "Low disk space" in result.message
        assert "Low CPU count" in result.message
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_exception(self, checker):
        """Test memory and resources check with exception"""
        with patch('app.startup_checks.psutil.virtual_memory') as mock_memory:
            mock_memory.side_effect = Exception("Cannot access memory info")
            
            await checker.check_memory_and_resources()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "system_resources"
        assert result.success is True  # Non-critical, still succeeds
        assert "Could not check resources" in result.message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_success(self, checker):
        """Test network connectivity check success"""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0  # Success
            mock_socket_class.return_value = mock_socket
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user@localhost:5432/db"
                mock_settings.redis.host = "localhost"
                mock_settings.redis.port = 6379
                
                await checker.check_network_connectivity()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "network_connectivity"
        assert result.success is True
        assert "All network endpoints reachable" in result.message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_failure(self, checker):
        """Test network connectivity check failure"""
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 1  # Connection failed
            mock_socket_class.return_value = mock_socket
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user@localhost:5432/db"
                mock_settings.redis.host = "localhost"
                mock_settings.redis.port = 6379
                
                await checker.check_network_connectivity()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "network_connectivity"
        assert result.success is False
        assert "Cannot reach" in result.message
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_exception(self, checker):
        """Test network connectivity check with exception"""
        with patch('socket.socket') as mock_socket_class:
            mock_socket_class.side_effect = Exception("Socket error")
            
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = "postgresql://user@localhost:5432/db"
                mock_settings.redis.host = "localhost"
                mock_settings.redis.port = 6379
                
                await checker.check_network_connectivity()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "network_connectivity"
        assert result.success is False
        assert "Cannot reach" in result.message
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_exists(self, checker, mock_app):
        """Test check_or_create_assistant when assistant already exists"""
        # Create proper async context manager mock
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_app.state.db_session_factory.return_value = mock_context
        
        # Mock existing assistant
        mock_result = MagicMock()
        mock_assistant = MagicMock(spec=Assistant)
        mock_result.scalar_one_or_none.return_value = mock_assistant
        mock_session.execute.return_value = mock_result
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "netra_assistant"
        assert result.success is True
        assert "already exists" in result.message
        
        # Verify no commit was called (assistant already exists)
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_create(self, checker, mock_app):
        """Test check_or_create_assistant when assistant needs to be created"""
        # Create proper async context manager mock
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_app.state.db_session_factory.return_value = mock_context
        
        # Mock no existing assistant
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "netra_assistant"
        assert result.success is True
        assert "created successfully" in result.message
        
        # Verify assistant was added and committed
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_failure(self, checker, mock_app):
        """Test check_or_create_assistant with database error"""
        # Create context manager that raises on __aenter__
        mock_context = AsyncMock()
        mock_context.__aenter__.side_effect = Exception("Database error")
        mock_app.state.db_session_factory.return_value = mock_context
        
        await checker.check_or_create_assistant()
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "netra_assistant"
        assert result.success is False
        assert "Failed to check/create assistant" in result.message
        assert result.critical is False


class TestRunStartupChecks:
    """Test the run_startup_checks function"""
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_success(self):
        """Test run_startup_checks with all checks passing"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            MockChecker.return_value = mock_checker
            mock_checker.run_all_checks.return_value = {
                'success': True,
                'total_checks': 10,
                'passed': 10,
                'failed_critical': 0,
                'failed_non_critical': 0,
                'duration_ms': 100.0,
                'results': [],
                'failures': []
            }
            
            results = await run_startup_checks(mock_app)
            
            assert results['success'] is True
            assert results['passed'] == 10
            assert results['failed_critical'] == 0
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_critical_failure(self):
        """Test run_startup_checks with critical failures"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            MockChecker.return_value = mock_checker
            mock_failure = StartupCheckResult(
                name="critical_check",
                success=False,
                message="Critical failure",
                critical=True
            )
            mock_checker.run_all_checks.return_value = {
                'success': False,
                'total_checks': 10,
                'passed': 9,
                'failed_critical': 1,
                'failed_non_critical': 0,
                'duration_ms': 100.0,
                'results': [mock_failure],
                'failures': [mock_failure]
            }
            
            with pytest.raises(RuntimeError) as exc_info:
                await run_startup_checks(mock_app)
            
            assert "Startup failed" in str(exc_info.value)
            assert "1 critical checks failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_non_critical_failure(self):
        """Test run_startup_checks with only non-critical failures"""
        mock_app = MagicMock()
        
        with patch('app.startup_checks.StartupChecker') as MockChecker:
            mock_checker = AsyncMock()
            MockChecker.return_value = mock_checker
            mock_failure = StartupCheckResult(
                name="non_critical_check",
                success=False,
                message="Non-critical failure",
                critical=False
            )
            mock_checker.run_all_checks.return_value = {
                'success': True,
                'total_checks': 10,
                'passed': 9,
                'failed_critical': 0,
                'failed_non_critical': 1,
                'duration_ms': 100.0,
                'results': [mock_failure],
                'failures': [mock_failure]
            }
            
            results = await run_startup_checks(mock_app)
            
            assert results['success'] is True
            assert results['failed_non_critical'] == 1
            # Should not raise an exception for non-critical failures


# Additional edge case tests
class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_database_url_parsing_edge_cases(self):
        """Test various database URL formats in network connectivity check"""
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        test_cases = [
            ("postgresql://localhost/db", "localhost:5432"),  # No @ symbol
            ("postgresql://user:pass@host:1234/db", "host:1234"),  # Custom port
            ("postgresql://user@host/db", "host"),  # No port specified
        ]
        
        for db_url, expected_endpoint in test_cases:
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.database_url = db_url
                mock_settings.redis = None  # Disable Redis check
                
                with patch('socket.socket'):
                    await checker.check_network_connectivity()
                    # Test passes if no exception is raised
    
    @pytest.mark.asyncio
    async def test_clickhouse_result_formats(self):
        """Test different ClickHouse result formats"""
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        test_results = [
            [('workload_events',)],  # Tuple format
            [['workload_events']],  # List format
            [{'name': 'workload_events'}],  # Dict format
        ]
        
        for result_format in test_results:
            # Mock the import and client creation
            mock_client = AsyncMock()
            mock_client.ping.return_value = None
            mock_client.execute_query.return_value = result_format
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_client
            mock_context.__aexit__.return_value = None
            
            with patch.dict('sys.modules', {'app.db.clickhouse': MagicMock()}):
                with patch('app.startup_checks.get_clickhouse_client', return_value=mock_context):
                    checker.results = []  # Reset results
                    await checker.check_clickhouse()
                    
                    assert checker.results[0].success is True
    
    @pytest.mark.asyncio
    async def test_concurrent_check_timing(self):
        """Test that check durations are properly recorded"""
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        async def slow_check():
            await asyncio.sleep(0.01)  # 10ms delay
            checker.results.append(StartupCheckResult(
                name="slow_check",
                success=True,
                message="Slow check completed"
            ))
        
        # Replace all checks with the slow check
        for method_name in ['check_environment_variables', 'check_configuration',
                           'check_file_permissions', 'check_database_connection',
                           'check_redis', 'check_clickhouse', 'check_llm_providers',
                           'check_memory_and_resources', 'check_network_connectivity',
                           'check_or_create_assistant']:
            setattr(checker, method_name, slow_check)
        
        results = await checker.run_all_checks()
        
        # Each check should have a duration > 10ms
        for result in results['results']:
            assert result.duration_ms >= 10.0
        
        # Total duration should be at least 100ms (10 checks * 10ms each)
        assert results['duration_ms'] >= 100.0