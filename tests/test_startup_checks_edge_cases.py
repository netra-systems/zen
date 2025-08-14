"""
Edge case tests for app/startup_checks.py - Boundary conditions and special scenarios

This module tests edge cases and boundary conditions.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupChecker, StartupCheckResult


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_database_url_parsing_edge_cases(self):
        """Test various database URL formats in network connectivity check"""
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        test_cases = self._get_db_url_test_cases()
        
        for db_url, expected_endpoint in test_cases:
            await self._test_db_url_case(checker, db_url)
    
    @pytest.mark.asyncio
    async def test_clickhouse_result_formats(self):
        """Test different ClickHouse result formats"""
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        test_results = self._get_clickhouse_test_results()
        
        for result_format in test_results:
            await self._test_clickhouse_format(checker, result_format)
    
    @pytest.mark.asyncio
    async def test_concurrent_check_timing(self):
        """Test that check durations are properly recorded"""
        mock_app = MagicMock()
        checker = StartupChecker(mock_app)
        
        self._setup_slow_checks(checker)
        results = await checker.run_all_checks()
        self._verify_timing_results(results)
    
    def _get_db_url_test_cases(self):
        """Get database URL test cases"""
        return [
            ("postgresql://localhost/db", "localhost:5432"),  # No @ symbol
            ("postgresql://user:pass@host:1234/db", "host:1234"),  # Custom port
            ("postgresql://user@host/db", "host"),  # No port specified
        ]
    
    async def _test_db_url_case(self, checker, db_url):
        """Test individual database URL case"""
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.database_url = db_url
            mock_settings.redis = None  # Disable Redis check
            
            with patch('socket.socket'):
                await checker.check_network_connectivity()
                # Test passes if no exception is raised
    
    def _get_clickhouse_test_results(self):
        """Get ClickHouse result format test cases"""
        return [
            [('workload_events',)],  # Tuple format
            [['workload_events']],  # List format
            [{'name': 'workload_events'}],  # Dict format
        ]
    
    async def _test_clickhouse_format(self, checker, result_format):
        """Test individual ClickHouse result format"""
        mock_client = self._create_clickhouse_mock_client(result_format)
        mock_context = self._create_clickhouse_context(mock_client)
        mock_module = self._create_clickhouse_module(mock_context)
        
        with patch.dict('sys.modules', {'app.db.clickhouse': mock_module}):
            checker.results = []  # Reset results
            await checker.check_clickhouse()
            assert checker.results[0].success is True
    
    def _create_clickhouse_mock_client(self, result_format):
        """Create mock ClickHouse client"""
        mock_client = AsyncMock()
        mock_client.ping.return_value = None
        mock_client.execute_query.return_value = result_format
        return mock_client
    
    def _create_clickhouse_context(self, mock_client):
        """Create ClickHouse context manager"""
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_client
        mock_context.__aexit__.return_value = None
        return mock_context
    
    def _create_clickhouse_module(self, mock_context):
        """Create ClickHouse module mock"""
        mock_module = MagicMock()
        mock_module.get_clickhouse_client = MagicMock(return_value=mock_context)
        return mock_module
    
    def _setup_slow_checks(self, checker):
        """Setup slow check methods for timing test"""
        async def slow_check():
            await asyncio.sleep(0.01)  # 10ms delay
            checker.results.append(StartupCheckResult(
                name="slow_check",
                success=True,
                message="Slow check completed"
            ))
        
        method_names = self._get_check_method_names()
        for method_name in method_names:
            setattr(checker, method_name, slow_check)
    
    def _get_check_method_names(self):
        """Get list of check method names"""
        return [
            'check_environment_variables', 'check_configuration',
            'check_file_permissions', 'check_database_connection',
            'check_redis', 'check_clickhouse', 'check_llm_providers',
            'check_memory_and_resources', 'check_network_connectivity',
            'check_or_create_assistant'
        ]
    
    def _verify_timing_results(self, results):
        """Verify timing results are properly recorded"""
        # Each check should have a duration > 10ms
        for result in results['results']:
            assert result.duration_ms >= 10.0
        
        # Total duration should be at least 100ms (10 checks * 10ms each)
        assert results['duration_ms'] >= 100.0


class TestFilePermissionEdgeCases:
    """Test file permission edge cases"""
    
    @pytest.fixture
    def checker(self):
        """Create a StartupChecker instance"""
        mock_app = MagicMock()
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_file_permissions_success(self, checker, tmp_path, monkeypatch):
        """Test file permissions check success"""
        monkeypatch.chdir(tmp_path)
        
        await checker.check_file_permissions()
        
        result = self._get_first_result(checker)
        self._verify_permission_success(result, tmp_path)
    
    @pytest.mark.asyncio
    async def test_check_file_permissions_failure(self, checker, monkeypatch):
        """Test file permissions check failure"""
        with patch.object(Path, 'mkdir', self._mock_mkdir_failure):
            await checker.check_file_permissions()
        
        result = self._get_first_result(checker)
        self._verify_permission_failure(result)
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _mock_mkdir_failure(self, exist_ok=True):
        """Mock mkdir to raise permission error"""
        raise PermissionError("Permission denied")
    
    def _verify_permission_success(self, result, tmp_path):
        """Verify successful permission check"""
        assert result.name == "file_permissions"
        assert result.success is True
        assert "accessible" in result.message
        
        # Verify directories were created
        self._verify_directories_created(tmp_path)
    
    def _verify_directories_created(self, tmp_path):
        """Verify required directories were created"""
        from pathlib import Path
        assert (tmp_path / "logs").exists()
        assert (tmp_path / "uploads").exists()
        assert (tmp_path / "temp").exists()
    
    def _verify_permission_failure(self, result):
        """Verify failed permission check"""
        assert result.name == "file_permissions"
        assert result.success is False
        assert "Permission" in result.message
        assert result.critical is False


class TestAssistantEdgeCases:
    """Test assistant creation edge cases"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with database factory"""
        app = MagicMock()
        app.state.db_session_factory = MagicMock()
        return app
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance"""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_exists(self, checker, mock_app):
        """Test check_or_create_assistant when assistant already exists"""
        mock_session = self._setup_existing_assistant_session(mock_app)
        
        await checker.check_or_create_assistant()
        
        result = self._get_first_result(checker)
        self._verify_assistant_exists(result, mock_session)
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_create(self, checker, mock_app):
        """Test check_or_create_assistant when assistant needs to be created"""
        mock_session = self._setup_create_assistant_session(mock_app)
        
        await checker.check_or_create_assistant()
        
        result = self._get_first_result(checker)
        self._verify_assistant_created(result, mock_session)
    
    @pytest.mark.asyncio
    async def test_check_or_create_assistant_failure(self, checker, mock_app):
        """Test check_or_create_assistant with database error"""
        self._setup_failed_assistant_session(mock_app)
        
        await checker.check_or_create_assistant()
        
        result = self._get_first_result(checker)
        self._verify_assistant_failure(result)
    
    def _setup_existing_assistant_session(self, mock_app):
        """Setup session with existing assistant"""
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_app.state.db_session_factory.return_value = mock_context
        
        # Mock existing assistant
        from app.db.models_postgres import Assistant
        mock_result = MagicMock()
        mock_assistant = MagicMock(spec=Assistant)
        mock_result.scalar_one_or_none.return_value = mock_assistant
        mock_session.execute.return_value = mock_result
        return mock_session
    
    def _setup_create_assistant_session(self, mock_app):
        """Setup session for creating assistant"""
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_app.state.db_session_factory.return_value = mock_context
        
        # Mock no existing assistant
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        return mock_session
    
    def _setup_failed_assistant_session(self, mock_app):
        """Setup failed assistant session"""
        mock_context = AsyncMock()
        mock_context.__aenter__.side_effect = Exception("Database error")
        mock_app.state.db_session_factory.return_value = mock_context
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _verify_assistant_exists(self, result, mock_session):
        """Verify assistant exists result"""
        assert result.name == "netra_assistant"
        assert result.success is True
        assert "already exists" in result.message
        mock_session.commit.assert_not_called()
    
    def _verify_assistant_created(self, result, mock_session):
        """Verify assistant created result"""
        assert result.name == "netra_assistant"
        assert result.success is True
        assert "created successfully" in result.message
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def _verify_assistant_failure(self, result):
        """Verify assistant failure result"""
        assert result.name == "netra_assistant"
        assert result.success is False
        assert "Failed to check/create assistant" in result.message
        assert result.critical is False