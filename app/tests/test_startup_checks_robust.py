"""
Robust tests for startup checks
Tests the improved startup check system with proper mocking and error handling
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile

from app.startup_checks import StartupChecker, StartupCheckResult, run_startup_checks


class TestStartupCheckResult:
    """Test the StartupCheckResult class"""
    
    def test_startup_check_result_creation(self):
        """Test creating a startup check result"""
        result = StartupCheckResult(
            name="test_check",
            success=True,
            message="Test passed",
            critical=True,
            duration_ms=100.5
        )
        
        assert result.name == "test_check"
        assert result.success == True
        assert result.message == "Test passed"
        assert result.critical == True
        assert result.duration_ms == 100.5
    
    def test_startup_check_result_defaults(self):
        """Test default values for startup check result"""
        result = StartupCheckResult(
            name="test",
            success=False,
            message="Failed"
        )
        
        assert result.critical == True
        assert result.duration_ms == 0


class TestStartupChecker:
    """Test the StartupChecker class"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state attributes"""
        app = Mock()
        app.state = Mock()
        app.state.redis_manager = AsyncMock()
        app.state.llm_manager = Mock()
        # Don't make db_session_factory an AsyncMock directly - it returns an async context manager
        app.state.db_session_factory = Mock()
        return app
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance"""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_all_present(self, checker, monkeypatch):
        """Test environment variable check when all required vars are present"""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        
        result = await checker.env_checker.check_environment_variables()
        checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "environment_variables"
        assert result.success == True
        assert "All required environment variables are set" in result.message
    
    @pytest.mark.asyncio
    async def test_check_environment_variables_missing_required(self, checker, monkeypatch):
        """Test environment variable check when required vars are missing"""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        
        result = await checker.env_checker.check_environment_variables()
        checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "environment_variables"
        assert result.success == False
        assert "DATABASE_URL" in result.message
        assert result.critical == True
    
    @pytest.mark.asyncio
    async def test_check_configuration_valid(self, checker):
        """Test configuration check with valid settings"""
        with patch('app.startup_checks.environment_checks.settings') as mock_settings:
            mock_settings.database_url = "postgresql://test"
            mock_settings.secret_key = "a" * 32  # 32 character key
            mock_settings.environment = "development"
            
            result = await checker.env_checker.check_configuration()
            checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "configuration"
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_check_configuration_invalid_secret(self, checker):
        """Test configuration check with invalid secret key"""
        with patch('app.startup_checks.environment_checks.settings') as mock_settings:
            mock_settings.database_url = "postgresql://test"
            mock_settings.secret_key = "short"  # Too short
            mock_settings.environment = "development"
            
            result = await checker.env_checker.check_configuration()
            checker.results.append(result)
            
            assert len(checker.results) == 1
            result = checker.results[0]
            assert result.name == "configuration"
            assert result.success == False
            assert "SECRET_KEY" in result.message
    
    @pytest.mark.asyncio
    async def test_check_file_permissions(self, checker):
        """Test file permissions check"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory for test
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            
            try:
                result = await checker.system_checker.check_file_permissions()
                checker.results.append(result)
                
                assert len(checker.results) == 1
                result = checker.results[0]
                assert result.name == "file_permissions"
                assert result.success == True
                
                # Verify directories were created
                assert Path("logs").exists()
                assert Path("uploads").exists()
                assert Path("temp").exists()
            finally:
                os.chdir(original_cwd)
    
    @pytest.mark.asyncio
    async def test_check_database_connection_success(self, checker):
        """Test successful database connection check"""
        mock_db = AsyncMock()
        
        # Mock for SELECT 1
        mock_select_result = Mock()
        mock_select_result.scalar_one.return_value = 1
        
        # Mock for table existence checks
        mock_table_result = Mock()
        mock_table_result.scalar_one.return_value = True
        
        # Set up execute to return different results for different queries
        async def mock_execute(query, *args, **kwargs):
            if "SELECT 1" in str(query):
                return mock_select_result
            else:  # Table existence checks
                return mock_table_result
        
        mock_db.execute = mock_execute
        
        # Set up the context manager properly
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_db
        mock_context.__aexit__.return_value = None
        checker.app.state.db_session_factory.return_value = mock_context
        
        result = await checker.db_checker.check_database_connection()
        checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "database_connection"
        assert result.success == True
        assert "PostgreSQL connected" in result.message
    
    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self, checker):
        """Test database connection failure"""
        checker.app.state.db_session_factory.side_effect = Exception("Connection failed")
        
        result = await checker.db_checker.check_database_connection()
        checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "database_connection"
        assert result.success == False
        assert result.critical == True
    
    @pytest.mark.asyncio
    async def test_check_redis_success(self, checker):
        """Test successful Redis connection check"""
        mock_redis = checker.app.state.redis_manager
        mock_redis.connect.return_value = None
        mock_redis.set.return_value = None
        mock_redis.get.return_value = "1234567890.0"  # Return the expected value
        mock_redis.delete.return_value = None
        
        with patch('time.time', return_value=1234567890.0):
            result = await checker.service_checker.check_redis()
            checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "redis_connection"
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_check_redis_failure_non_production(self, checker):
        """Test Redis failure in non-production environment"""
        checker.app.state.redis_manager.connect.side_effect = Exception("Connection refused")
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            result = await checker.service_checker.check_redis()
            checker.results.append(result)
            
            assert len(checker.results) == 1
            result = checker.results[0]
            assert result.name == "redis_connection"
            assert result.success == False
            assert result.critical == False  # Not critical in development
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_success(self, checker):
        """Test successful ClickHouse connection check"""
        mock_client = Mock()
        mock_client.ping.return_value = None
        mock_client.execute.return_value = [('workload_events',), ('other_table',)]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        with patch('app.db.clickhouse.get_clickhouse_client', return_value=mock_client):
            result = await checker.service_checker.check_clickhouse()
            checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "clickhouse_connection"
        assert result.success == True
        assert "2 tables" in result.message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_available(self, checker):
        """Test LLM providers check when all are available"""
        mock_llm_manager = checker.app.state.llm_manager
        mock_llm_manager.get_llm.return_value = Mock()  # Return a valid LLM object
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.llm_configs = ['anthropic-claude-3-sonnet', 'gpt-4']
            
            result = await checker.service_checker.check_llm_providers()
            checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "llm_providers"
        assert result.success == True
        assert "2 LLM providers configured" in result.message
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_partial_failure(self, checker):
        """Test LLM providers check with partial failures"""
        mock_llm_manager = checker.app.state.llm_manager
        mock_llm_manager.get_llm.side_effect = [Mock(), Exception("API key invalid")]
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.llm_configs = ['anthropic-claude-3-sonnet', 'gpt-4']
            
            result = await checker.service_checker.check_llm_providers()
            checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "llm_providers"
        assert result.success == True  # Partial success
        assert "1 available, 1 failed" in result.message
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources(self, checker):
        """Test system resources check"""
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.cpu_count') as mock_cpu:
            
            mock_memory.return_value = Mock(
                total=16 * 1024**3,  # 16 GB
                available=8 * 1024**3  # 8 GB
            )
            mock_disk.return_value = Mock(
                free=100 * 1024**3  # 100 GB
            )
            mock_cpu.return_value = 8
            
            result = await checker.system_checker.check_memory_and_resources()
            checker.results.append(result)
            
            assert len(checker.results) == 1
            result = checker.results[0]
            assert result.name == "system_resources"
            assert result.success == True
            assert "Resources OK" in result.message
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_warnings(self, checker):
        """Test system resources check with warnings"""
        with patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.cpu_count') as mock_cpu:
            
            mock_memory.return_value = Mock(
                total=4 * 1024**3,  # 4 GB
                available=0.5 * 1024**3  # 0.5 GB (low)
            )
            mock_disk.return_value = Mock(
                free=2 * 1024**3  # 2 GB (low)
            )
            mock_cpu.return_value = 1  # Low CPU count
            
            result = await checker.system_checker.check_memory_and_resources()
            checker.results.append(result)
            
            assert len(checker.results) == 1
            result = checker.results[0]
            assert result.name == "system_resources"
            assert result.success == True  # Still succeeds but with warnings
            assert "Resource warnings" in result.message
            assert "Low memory" in result.message
            assert "Low disk space" in result.message
            assert "Low CPU count" in result.message
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_exists(self, checker):
        """Test assistant check when it already exists"""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Mock(id="netra-assistant")
        mock_db.execute.return_value = mock_result
        
        # Set up the context manager properly
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_db
        mock_context.__aexit__.return_value = None
        checker.app.state.db_session_factory.return_value = mock_context
        
        result = await checker.db_checker.check_or_create_assistant()
        checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "netra_assistant"
        assert result.success == True
        assert "already exists" in result.message
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_creates(self, checker):
        """Test assistant creation when it doesn't exist"""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # Assistant doesn't exist
        mock_db.execute.return_value = mock_result
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        
        # Set up the context manager properly
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_db
        mock_context.__aexit__.return_value = None
        checker.app.state.db_session_factory.return_value = mock_context
        
        result = await checker.db_checker.check_or_create_assistant()
        checker.results.append(result)
        
        assert len(checker.results) == 1
        result = checker.results[0]
        assert result.name == "netra_assistant"
        assert result.success == True
        assert "created successfully" in result.message
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_all_checks_success(self, checker):
        """Test running all checks successfully"""
        # Mock all check methods to succeed
        checker.check_environment_variables = AsyncMock()
        checker.check_configuration = AsyncMock()
        checker.check_file_permissions = AsyncMock()
        checker.check_database_connection = AsyncMock()
        checker.check_redis = AsyncMock()
        checker.check_clickhouse = AsyncMock()
        checker.check_llm_providers = AsyncMock()
        checker.check_memory_and_resources = AsyncMock()
        checker.check_network_connectivity = AsyncMock()
        checker.check_or_create_assistant = AsyncMock()
        
        # Add success results for each check
        def add_success_result(name):
            checker.results.append(StartupCheckResult(
                name=name,
                success=True,
                message="Check passed",
                critical=True
            ))
        
        checker.check_environment_variables.side_effect = lambda: add_success_result("env")
        checker.check_configuration.side_effect = lambda: add_success_result("config")
        checker.check_file_permissions.side_effect = lambda: add_success_result("files")
        checker.check_database_connection.side_effect = lambda: add_success_result("db")
        checker.check_redis.side_effect = lambda: add_success_result("redis")
        checker.check_clickhouse.side_effect = lambda: add_success_result("clickhouse")
        checker.check_llm_providers.side_effect = lambda: add_success_result("llm")
        checker.check_memory_and_resources.side_effect = lambda: add_success_result("resources")
        checker.check_network_connectivity.side_effect = lambda: add_success_result("network")
        checker.check_or_create_assistant.side_effect = lambda: add_success_result("assistant")
        
        results = await checker.run_all_checks()
        
        assert results["success"] == True
        assert results["total_checks"] == 10
        assert results["passed"] == 10
        assert results["failed_critical"] == 0
        assert results["failed_non_critical"] == 0
    
    @pytest.mark.asyncio
    async def test_run_all_checks_with_critical_failure(self, checker):
        """Test running checks with a critical failure"""
        # Mock checks
        checker.check_environment_variables = AsyncMock()
        checker.check_configuration = AsyncMock()
        checker.check_file_permissions = AsyncMock()
        checker.check_database_connection = AsyncMock()
        checker.check_redis = AsyncMock()
        checker.check_clickhouse = AsyncMock()
        checker.check_llm_providers = AsyncMock()
        checker.check_memory_and_resources = AsyncMock()
        checker.check_network_connectivity = AsyncMock()
        checker.check_or_create_assistant = AsyncMock()
        
        # Add a critical failure
        def add_critical_failure():
            checker.results.append(StartupCheckResult(
                name="database",
                success=False,
                message="Database connection failed",
                critical=True
            ))
        
        checker.check_database_connection.side_effect = add_critical_failure
        
        results = await checker.run_all_checks()
        
        assert results["success"] == False
        assert results["failed_critical"] == 1
        assert len(results["failures"]) == 1


class TestRunStartupChecks:
    """Test the main run_startup_checks function"""
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_success(self):
        """Test successful startup checks"""
        mock_app = Mock()
        mock_app.state = Mock()
        
        with patch('app.startup_checks.StartupChecker') as mock_checker_class:
            mock_checker = Mock()
            mock_checker_class.return_value = mock_checker
            mock_checker.run_all_checks = AsyncMock(return_value={
                "success": True,
                "total_checks": 10,
                "passed": 10,
                "failed_critical": 0,
                "failed_non_critical": 0,
                "duration_ms": 1000,
                "failures": []
            })
            
            results = await run_startup_checks(mock_app)
            
            assert results["success"] == True
            mock_checker.run_all_checks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_critical_failure(self):
        """Test startup checks with critical failure"""
        mock_app = Mock()
        mock_app.state = Mock()
        
        with patch('app.startup_checks.StartupChecker') as mock_checker_class:
            mock_checker = Mock()
            mock_checker_class.return_value = mock_checker
            
            mock_failure = StartupCheckResult(
                name="database",
                success=False,
                message="Connection failed",
                critical=True
            )
            
            mock_checker.run_all_checks = AsyncMock(return_value={
                "success": False,
                "total_checks": 10,
                "passed": 9,
                "failed_critical": 1,
                "failed_non_critical": 0,
                "duration_ms": 1000,
                "failures": [mock_failure]
            })
            
            with pytest.raises(RuntimeError) as exc_info:
                await run_startup_checks(mock_app)
            
            assert "Startup failed" in str(exc_info.value)
            assert "1 critical checks failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_run_startup_checks_non_critical_failures(self):
        """Test startup checks with only non-critical failures"""
        mock_app = Mock()
        mock_app.state = Mock()
        
        with patch('app.startup_checks.StartupChecker') as mock_checker_class:
            mock_checker = Mock()
            mock_checker_class.return_value = mock_checker
            
            mock_failure = StartupCheckResult(
                name="clickhouse",
                success=False,
                message="Optional service unavailable",
                critical=False
            )
            
            mock_checker.run_all_checks = AsyncMock(return_value={
                "success": True,  # Success because no critical failures
                "total_checks": 10,
                "passed": 9,
                "failed_critical": 0,
                "failed_non_critical": 1,
                "duration_ms": 1000,
                "failures": [mock_failure]
            })
            
            results = await run_startup_checks(mock_app)
            
            assert results["success"] == True
            assert results["failed_non_critical"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])