"""
Resource tests for app/startup_checks.py - LLM, ClickHouse, and system resource checks

This module tests LLM providers, ClickHouse, and system resource checks.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupChecker


class TestLLMProviderChecks:
    """Test LLM provider connectivity checks"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with LLM manager"""
        app = MagicMock()
        app.state.llm_manager = MagicMock()
        return app
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance"""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_success(self, checker, mock_app):
        """Test LLM providers check success"""
        self._setup_successful_llm_manager(mock_app)
        
        with patch('app.startup_checks.settings') as mock_settings:
            self._setup_llm_settings(mock_settings)
            await checker.check_llm_providers()
        
        result = self._get_first_result(checker)
        self._verify_llm_success(result)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_partial_failure(self, checker, mock_app):
        """Test LLM providers check with some failures"""
        self._setup_partial_failure_llm_manager(mock_app)
        
        with patch('app.startup_checks.settings') as mock_settings:
            self._setup_llm_settings(mock_settings)
            await checker.check_llm_providers()
        
        result = self._get_first_result(checker)
        self._verify_llm_partial_failure(result)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_all_failed(self, checker, mock_app):
        """Test LLM providers check with all providers failing"""
        self._setup_failed_llm_manager(mock_app)
        
        with patch('app.startup_checks.settings') as mock_settings:
            self._setup_single_llm_settings(mock_settings)
            await checker.check_llm_providers()
        
        result = self._get_first_result(checker)
        self._verify_llm_all_failed(result)
    
    @pytest.mark.asyncio
    async def test_check_llm_providers_exception(self, checker, mock_app):
        """Test LLM providers check with unexpected exception"""
        del mock_app.state.llm_manager
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "production"
            await checker.check_llm_providers()
        
        result = self._get_first_result(checker)
        self._verify_llm_exception(result)
    
    def _setup_successful_llm_manager(self, mock_app):
        """Setup successful LLM manager"""
        mock_llm_manager = mock_app.state.llm_manager
        mock_llm_manager.get_llm.return_value = MagicMock()
    
    def _setup_partial_failure_llm_manager(self, mock_app):
        """Setup LLM manager with partial failures"""
        mock_llm_manager = mock_app.state.llm_manager
        
        def mock_get_llm(name):
            if name == 'anthropic-claude-3-sonnet':
                return MagicMock()
            else:
                raise Exception("API key missing")
        
        mock_llm_manager.get_llm.side_effect = mock_get_llm
    
    def _setup_failed_llm_manager(self, mock_app):
        """Setup failed LLM manager"""
        mock_llm_manager = mock_app.state.llm_manager
        mock_llm_manager.get_llm.side_effect = Exception("API key missing")
    
    def _setup_llm_settings(self, mock_settings):
        """Setup LLM settings with multiple providers"""
        mock_settings.llm_configs = {
            'anthropic-claude-3-sonnet': {},
            'anthropic-claude-3-opus': {}
        }
    
    def _setup_single_llm_settings(self, mock_settings):
        """Setup LLM settings with single provider"""
        mock_settings.llm_configs = {
            'anthropic-claude-3-sonnet': {}
        }
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _verify_llm_success(self, result):
        """Verify successful LLM result"""
        assert result.name == "llm_providers"
        assert result.success is True
        assert "2 LLM providers configured" in result.message
    
    def _verify_llm_partial_failure(self, result):
        """Verify partial LLM failure result"""
        assert result.name == "llm_providers"
        assert result.success is True
        assert "1 available, 1 failed" in result.message
    
    def _verify_llm_all_failed(self, result):
        """Verify all LLM failed result"""
        assert result.name == "llm_providers"
        assert result.success is False
        assert "No LLM providers available" in result.message
        assert result.critical is True
    
    def _verify_llm_exception(self, result):
        """Verify LLM exception result"""
        assert result.name == "llm_providers"
        assert result.success is False
        assert "LLM check failed" in result.message
        assert result.critical is True


class TestClickHouseChecks:
    """Test ClickHouse connectivity checks"""
    
    @pytest.fixture
    def checker(self):
        """Create a StartupChecker instance"""
        mock_app = MagicMock()
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_success(self, checker):
        """Test ClickHouse check success"""
        mock_module = self._setup_successful_clickhouse()
        
        with patch.dict('sys.modules', {'app.db.clickhouse': mock_module}):
            await checker.check_clickhouse()
        
        result = self._get_first_result(checker)
        self._verify_clickhouse_success(result)
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_missing_tables(self, checker):
        """Test ClickHouse check with missing required tables"""
        mock_module = self._setup_missing_tables_clickhouse()
        
        with patch.dict('sys.modules', {'app.db.clickhouse': mock_module}):
            await checker.check_clickhouse()
        
        result = self._get_first_result(checker)
        self._verify_clickhouse_missing_tables(result)
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_failure(self, checker):
        """Test ClickHouse check failure"""
        mock_module = self._setup_failed_clickhouse()
        
        with patch.dict('sys.modules', {'app.db.clickhouse': mock_module}):
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                await checker.check_clickhouse()
        
        result = self._get_first_result(checker)
        self._verify_clickhouse_failure(result)
    
    def _setup_successful_clickhouse(self):
        """Setup successful ClickHouse mock"""
        mock_client = AsyncMock()
        mock_client.ping.return_value = None
        mock_client.execute_query.return_value = [
            {'name': 'workload_events'},
            {'name': 'other_table'}
        ]
        
        mock_context = self._create_clickhouse_context(mock_client)
        return self._create_clickhouse_module(mock_context)
    
    def _setup_missing_tables_clickhouse(self):
        """Setup ClickHouse with missing tables"""
        mock_client = AsyncMock()
        mock_client.ping.return_value = None
        mock_client.execute_query.return_value = [
            {'name': 'other_table'}
        ]
        
        mock_context = self._create_clickhouse_context(mock_client)
        return self._create_clickhouse_module(mock_context)
    
    def _setup_failed_clickhouse(self):
        """Setup failed ClickHouse mock"""
        mock_module = MagicMock()
        mock_module.get_clickhouse_client = MagicMock(
            side_effect=Exception("Connection failed")
        )
        return mock_module
    
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
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _verify_clickhouse_success(self, result):
        """Verify successful ClickHouse result"""
        assert result.name == "clickhouse_connection"
        assert result.success is True
        assert "2 tables" in result.message
    
    def _verify_clickhouse_missing_tables(self, result):
        """Verify ClickHouse missing tables result"""
        assert result.name == "clickhouse_connection"
        assert result.success is False
        assert "Missing ClickHouse tables" in result.message
    
    def _verify_clickhouse_failure(self, result):
        """Verify ClickHouse failure result"""
        assert result.name == "clickhouse_connection"
        assert result.success is False
        assert "Connection failed" in result.message


class TestSystemResourceChecks:
    """Test system resource checks"""
    
    @pytest.fixture
    def checker(self):
        """Create a StartupChecker instance"""
        mock_app = MagicMock()
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_success(self, checker):
        """Test memory and resources check success"""
        with patch('app.startup_checks.psutil') as mock_psutil:
            self._setup_healthy_resources(mock_psutil)
            await checker.check_memory_and_resources()
        
        result = self._get_first_result(checker)
        self._verify_resources_success(result)
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_warnings(self, checker):
        """Test memory and resources check with warnings"""
        with patch('app.startup_checks.psutil') as mock_psutil:
            self._setup_low_resources(mock_psutil)
            await checker.check_memory_and_resources()
        
        result = self._get_first_result(checker)
        self._verify_resources_warnings(result)
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_exception(self, checker):
        """Test memory and resources check with exception"""
        with patch('app.startup_checks.psutil.virtual_memory') as mock_memory:
            mock_memory.side_effect = Exception("Cannot access memory info")
            await checker.check_memory_and_resources()
        
        result = self._get_first_result(checker)
        self._verify_resources_exception(result)
    
    def _setup_healthy_resources(self, mock_psutil):
        """Setup healthy resource mocks"""
        mock_memory = MagicMock()
        mock_memory.total = 16 * (1024**3)  # 16 GB
        mock_memory.available = 8 * (1024**3)  # 8 GB available
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.free = 100 * (1024**3)  # 100 GB free
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_psutil.cpu_count.return_value = 4
    
    def _setup_low_resources(self, mock_psutil):
        """Setup low resource mocks"""
        mock_memory = MagicMock()
        mock_memory.total = 4 * (1024**3)  # 4 GB
        mock_memory.available = 0.5 * (1024**3)  # 0.5 GB available
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.free = 2 * (1024**3)  # 2 GB free
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_psutil.cpu_count.return_value = 1
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _verify_resources_success(self, result):
        """Verify successful resources result"""
        assert result.name == "system_resources"
        assert result.success is True
        assert "Resources OK" in result.message
    
    def _verify_resources_warnings(self, result):
        """Verify resources warnings result"""
        assert result.name == "system_resources"
        assert result.success is True
        assert "Resource warnings" in result.message
        assert "Low memory" in result.message
        assert "Low disk space" in result.message
        assert "Low CPU count" in result.message
    
    def _verify_resources_exception(self, result):
        """Verify resources exception result"""
        assert result.name == "system_resources"
        assert result.success is True
        assert "Could not check resources" in result.message


class TestNetworkConnectivityChecks:
    """Test network connectivity checks"""
    
    @pytest.fixture
    def checker(self):
        """Create a StartupChecker instance"""
        mock_app = MagicMock()
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_success(self, checker):
        """Test network connectivity check success"""
        with patch('socket.socket') as mock_socket_class:
            self._setup_successful_socket(mock_socket_class)
            
            with patch('app.startup_checks.settings') as mock_settings:
                self._setup_network_settings(mock_settings)
                await checker.check_network_connectivity()
        
        result = self._get_first_result(checker)
        self._verify_network_success(result)
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_failure(self, checker):
        """Test network connectivity check failure"""
        with patch('socket.socket') as mock_socket_class:
            self._setup_failed_socket(mock_socket_class)
            
            with patch('app.startup_checks.settings') as mock_settings:
                self._setup_network_settings(mock_settings)
                await checker.check_network_connectivity()
        
        result = self._get_first_result(checker)
        self._verify_network_failure(result)
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_exception(self, checker):
        """Test network connectivity check with exception"""
        with patch('socket.socket') as mock_socket_class:
            mock_socket_class.side_effect = Exception("Socket error")
            
            with patch('app.startup_checks.settings') as mock_settings:
                self._setup_network_settings(mock_settings)
                await checker.check_network_connectivity()
        
        result = self._get_first_result(checker)
        self._verify_network_exception(result)
    
    def _setup_successful_socket(self, mock_socket_class):
        """Setup successful socket mock"""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0  # Success
        mock_socket_class.return_value = mock_socket
    
    def _setup_failed_socket(self, mock_socket_class):
        """Setup failed socket mock"""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 1  # Connection failed
        mock_socket_class.return_value = mock_socket
    
    def _setup_network_settings(self, mock_settings):
        """Setup network settings"""
        mock_settings.database_url = "postgresql://user@localhost:5432/db"
        mock_settings.redis.host = "localhost"
        mock_settings.redis.port = 6379
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _verify_network_success(self, result):
        """Verify successful network result"""
        assert result.name == "network_connectivity"
        assert result.success is True
        assert "All network endpoints reachable" in result.message
    
    def _verify_network_failure(self, result):
        """Verify network failure result"""
        assert result.name == "network_connectivity"
        assert result.success is False
        assert "Cannot reach" in result.message
    
    def _verify_network_exception(self, result):
        """Verify network exception result"""
        assert result.name == "network_connectivity"
        assert result.success is False
        assert "Cannot reach" in result.message