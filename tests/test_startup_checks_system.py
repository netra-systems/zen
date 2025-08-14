"""
System tests for app/startup_checks.py - System resource and network checks

This module tests system resources and network connectivity.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
from unittest.mock import MagicMock, patch
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupChecker


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
        with patch('app.startup_checks.system_checks.psutil') as mock_psutil:
            self._setup_healthy_resources(mock_psutil)
            result = await checker.system_checker.check_memory_and_resources()
        
        self._verify_resources_success(result)
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_warnings(self, checker):
        """Test memory and resources check with warnings"""
        with patch('app.startup_checks.system_checks.psutil') as mock_psutil:
            self._setup_low_resources(mock_psutil)
            result = await checker.system_checker.check_memory_and_resources()
        
        self._verify_resources_warnings(result)
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_exception(self, checker):
        """Test memory and resources check with exception"""
        with patch('app.startup_checks.system_checks.psutil.virtual_memory') as mock_memory:
            mock_memory.side_effect = Exception("Cannot access memory info")
            result = await checker.system_checker.check_memory_and_resources()
        
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
            
            with patch('app.startup_checks.system_checks.settings') as mock_settings:
                self._setup_network_settings(mock_settings)
                result = await checker.system_checker.check_network_connectivity()
        
        self._verify_network_success(result)
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_failure(self, checker):
        """Test network connectivity check failure"""
        with patch('socket.socket') as mock_socket_class:
            self._setup_failed_socket(mock_socket_class)
            
            with patch('app.startup_checks.system_checks.settings') as mock_settings:
                self._setup_network_settings(mock_settings)
                result = await checker.system_checker.check_network_connectivity()
        
        self._verify_network_failure(result)
    
    @pytest.mark.asyncio
    async def test_check_network_connectivity_exception(self, checker):
        """Test network connectivity check with exception"""
        with patch('socket.socket') as mock_socket_class:
            mock_socket_class.side_effect = Exception("Socket error")
            
            with patch('app.startup_checks.system_checks.settings') as mock_settings:
                self._setup_network_settings(mock_settings)
                result = await checker.system_checker.check_network_connectivity()
        
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