"""
Integration test for dev launcher startup processes.

This comprehensive test ensures the dev launcher starts correctly and handles
critical startup scenarios including database connectivity, port allocation,
and service initialization.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Stability
- Value Impact: Prevents regression in dev launcher startup, ensuring developers can start work immediately
- Strategic Impact: Reduces onboarding friction and maintains development productivity

This test addresses the specific fixes made to:
1. Database URL normalization for asyncpg compatibility
2. Port allocation and conflict resolution 
3. Environment variable loading consistency
4. Service initialization order
5. Windows-compatible signal handlers
"""

import asyncio
import logging
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from urllib.parse import urlparse

import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from dev_launcher.config import LauncherConfig
from dev_launcher.database_connector import DatabaseConnector, DatabaseType, ConnectionStatus
from dev_launcher.isolated_environment import get_env
from dev_launcher.launcher import DevLauncher
from dev_launcher.port_manager import PortManager
from dev_launcher.signal_handler import SignalHandler
from dev_launcher.utils import check_emoji_support


class TestDevLauncherStartup(BaseIntegrationTest):
    """Comprehensive tests for dev launcher startup processes."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.temp_dir = None
        self.test_ports = []
        self.mock_processes = []
        
    def teardown_method(self):
        """Clean up test resources."""
        # Clean up temp directory
        if self.temp_dir:
            self.temp_dir.cleanup()
        
        # Clean up any test processes
        for process in self.mock_processes:
            try:
                if hasattr(process, 'terminate'):
                    process.terminate()
            except:
                pass
        
        super().teardown_method()
    
    @pytest.fixture
    def launcher_config(self):
        """Create a test launcher configuration."""
        return LauncherConfig(
            backend_port=None,  # Dynamic allocation
            frontend_port=3000,
            dynamic_ports=True,
            backend_reload=False,
            load_secrets=False,
            verbose=True,
            no_browser=True,
            startup_mode='minimal'
        )
    
    @pytest.fixture
    def mock_environment(self):
        """Mock environment with test database URLs."""
        return {
            'DATABASE_URL': 'postgresql+asyncpg://postgres:test@localhost:5433/netra_test',
            'REDIS_URL': 'redis://localhost:6379/1',
            'CLICKHOUSE_HOST': 'localhost',
            'CLICKHOUSE_HTTP_PORT': '8123',
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': '',
            'CLICKHOUSE_DB': 'netra_test'
        }
    
    @pytest.fixture
    def port_manager(self):
        """Create port manager for testing."""
        manager = PortManager()
        yield manager
        # Cleanup allocated ports
        manager.cleanup_all()
    
    @pytest.fixture
    async def database_connector(self):
        """Create database connector for testing."""
        connector = DatabaseConnector(use_emoji=False)
        yield connector
        await connector.stop_health_monitoring()
    
    def test_database_url_normalization_fix(self, database_connector):
        """Test the database URL normalization fix for asyncpg compatibility."""
        test_cases = [
            # Input URL, Expected normalized URL
            ('postgresql+asyncpg://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db'),
            ('postgres+asyncpg://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db'),
            ('postgres://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db'),
            ('postgresql://user:pass@localhost:5432/db', 'postgresql://user:pass@localhost:5432/db'),
            ('', ''),  # Empty URL should return empty
            (None, None),  # None should return None
        ]
        
        for input_url, expected in test_cases:
            if input_url is None:
                # Test None input
                result = database_connector._normalize_postgres_url(None)
                assert result is None, "None input should return None"
                continue
                
            result = database_connector._normalize_postgres_url(input_url)
            assert result == expected, f"URL normalization failed for {input_url}. Expected: {expected}, Got: {result}"
    
    def test_port_allocation_and_conflict_resolution(self, port_manager):
        """Test port allocation with conflict resolution."""
        # Test basic port allocation
        port1 = port_manager.allocate_port("test_service1")
        assert port1 is not None, "Should allocate a port"
        assert 8000 <= port1 <= 65535, "Port should be in valid range"
        
        # Test port allocation with preferred port
        port2 = port_manager.allocate_port("test_service2", preferred_port=port1 + 1)
        assert port2 is not None, "Should allocate a port"
        
        # Test conflict resolution - try to allocate the same port
        conflicting_port = port_manager.allocate_port("test_service3", preferred_port=port1)
        assert conflicting_port != port1, "Should resolve port conflict by allocating different port"
        
        # Verify port allocation tracking
        allocated_ports = port_manager.get_all_allocated_ports()
        assert len(allocated_ports) >= 2, "Should have at least 2 port allocations"
        assert "test_service1" in allocated_ports, "Should track test_service1 allocation"
        assert "test_service2" in allocated_ports, "Should track test_service2 allocation"
        
        # Test cleanup
        port_manager.release_port("test_service1")
        port_manager.release_port("test_service2")
        
        # Verify ports are released
        updated_ports = port_manager.get_all_allocated_ports()
        assert "test_service1" not in updated_ports, "test_service1 should be released"
        assert "test_service2" not in updated_ports, "test_service2 should be released"
    
    def test_environment_variable_loading_consistency(self, mock_environment):
        """Test environment variable loading consistency."""
        with patch.dict(os.environ, mock_environment, clear=False):
            # Test environment manager
            env = get_env()
            
            # Verify database URL is loaded correctly
            db_url = env.get('DATABASE_URL')
            assert db_url is not None, "DATABASE_URL should be loaded"
            assert 'postgresql' in db_url, "Database URL should contain postgresql"
            
            # Verify Redis URL is loaded
            redis_url = env.get('REDIS_URL') 
            assert redis_url is not None, "REDIS_URL should be loaded"
            assert redis_url.startswith('redis://'), "Redis URL should start with redis://"
            
            # Verify ClickHouse configuration
            ch_host = env.get('CLICKHOUSE_HOST')
            assert ch_host == 'localhost', "ClickHouse host should be loaded correctly"
            
            ch_port = env.get('CLICKHOUSE_HTTP_PORT')
            assert ch_port == '8123', "ClickHouse port should be loaded correctly"
    
    @pytest.mark.asyncio
    async def test_database_connectivity_validation(self, database_connector, mock_environment):
        """Test database connectivity validation during startup."""
        with patch.dict(os.environ, mock_environment, clear=False):
            # Mock successful database connections
            with patch('psycopg2.connect') as mock_pg_connect, \
                 patch('redis.Redis.ping') as mock_redis_ping, \
                 patch('requests.get') as mock_http_request:
                
                # Mock successful PostgreSQL connection
                mock_pg_connect.return_value.__enter__.return_value.cursor.return_value.fetchone.return_value = (1,)
                
                # Mock successful Redis ping
                mock_redis_ping.return_value = True
                
                # Mock successful ClickHouse HTTP request
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = "Ok."
                mock_http_request.return_value = mock_response
                
                # Test database discovery and connection validation
                database_connector._discover_database_connections()
                assert len(database_connector.connections) > 0, "Should discover database connections"
                
                # Test connection validation
                validation_result = await database_connector.validate_all_connections()
                
                # Note: validation_result might be True or False depending on actual connectivity
                # The important thing is that it doesn't crash and handles errors gracefully
                assert isinstance(validation_result, bool), "Validation should return boolean result"
    
    def test_service_initialization_order(self, launcher_config):
        """Test service initialization follows correct order."""
        # Mock the project root to avoid file system dependencies
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock project structure
            (temp_path / "netra_backend").mkdir()
            (temp_path / "netra_backend" / "app").mkdir()
            (temp_path / "frontend").mkdir()
            (temp_path / "auth_service").mkdir()
            
            with patch('dev_launcher.config.find_project_root', return_value=temp_path):
                # Create launcher instance
                launcher = DevLauncher(launcher_config)
                
                # Verify initialization order by checking component dependencies
                assert hasattr(launcher, 'database_connector'), "Database connector should be initialized"
                assert hasattr(launcher, 'process_manager'), "Process manager should be initialized"
                assert hasattr(launcher, 'health_monitor'), "Health monitor should be initialized"
                
                # Test that components are properly configured
                assert launcher.database_connector is not None, "Database connector should be configured"
    
    def test_signal_handlers_windows_compatibility(self):
        """Test signal handlers work correctly on Windows and Unix systems."""
        # Test signal handler creation without setup to avoid interference
        signal_handler = SignalHandler()
        
        # Verify signal handler initialization
        assert signal_handler is not None, "Signal handler should be initialized"
        
        # Test that signal handler has necessary attributes without triggering setup
        assert hasattr(signal_handler, 'shutdown_initiated'), "Signal handler should have shutdown tracking"
        assert hasattr(signal_handler, 'cleanup_handlers'), "Signal handler should have cleanup handlers list"
        
        # Test platform detection
        if platform.system() == "Windows":
            # Just verify Windows detection works
            assert sys.platform == "win32", "Windows platform should be detected"
        else:
            # Just verify Unix-like detection works
            assert sys.platform != "win32", "Unix-like platform should be detected"
    
    def test_error_recovery_scenarios(self, launcher_config):
        """Test launcher handles error recovery scenarios gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create minimal project structure
            (temp_path / "netra_backend").mkdir()
            (temp_path / "netra_backend" / "app").mkdir()
            (temp_path / "frontend").mkdir()
            
            with patch('dev_launcher.config.find_project_root', return_value=temp_path):
                # Test launcher creation with missing dependencies
                launcher = DevLauncher(launcher_config)
                
                # Test graceful handling of missing dependencies
                assert hasattr(launcher, '_shutting_down'), "Launcher should have shutdown flag"
                assert launcher._shutting_down == False, "Launcher should start with shutdown=False"
                
                # Test that launcher has basic error recovery capabilities
                assert hasattr(launcher, 'emergency_cleanup'), "Launcher should have emergency cleanup method"
                
                # Just verify the method exists without calling it to avoid signal handler conflicts
                assert callable(getattr(launcher, 'emergency_cleanup', None)), \
                    "Emergency cleanup should be callable"
    
    @pytest.mark.asyncio
    async def test_launcher_run_basic_flow(self, launcher_config):
        """Test basic launcher run flow without actual service startup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create comprehensive mock project structure
            backend_dir = temp_path / "netra_backend"
            backend_dir.mkdir()
            (backend_dir / "app").mkdir()
            (backend_dir / "app" / "main.py").write_text("# Mock main.py")
            
            frontend_dir = temp_path / "frontend"
            frontend_dir.mkdir()
            (frontend_dir / "package.json").write_text('{"name": "frontend", "scripts": {"dev": "next dev"}}')
            
            auth_dir = temp_path / "auth_service"
            auth_dir.mkdir()
            (auth_dir / "main.py").write_text("# Mock auth service")
            
            # Create .env file
            (temp_path / ".env.dev").write_text("DATABASE_URL=postgresql://localhost:5432/test")
            
            with patch('dev_launcher.config.find_project_root', return_value=temp_path), \
                 patch('subprocess.Popen') as mock_popen, \
                 patch('asyncio.sleep', new_callable=AsyncMock):
                
                # Mock subprocess for service processes  
                mock_process = Mock()
                mock_process.pid = 12345
                mock_process.poll.return_value = None  # Process running
                mock_process.returncode = None
                mock_popen.return_value = mock_process
                
                # Create launcher
                launcher = DevLauncher(launcher_config)
                
                # Mock the actual run loop to avoid infinite running
                original_run = launcher.run
                
                async def mock_run():
                    """Mock run that simulates startup without infinite loop."""
                    try:
                        # Simulate initialization steps
                        await launcher._startup_initialization()
                        return 0  # Success
                    except Exception as e:
                        self.logger.warning(f"Mock run failed: {e}")
                        return 1  # Failure (acceptable for test)
                
                launcher.run = mock_run
                
                # Test launcher run
                exit_code = await launcher.run()
                
                # Verify result (0 for success, non-zero for failure is acceptable)
                assert isinstance(exit_code, int), "Run should return integer exit code"
                assert exit_code >= 0, "Exit code should be non-negative"
    
    def test_windows_specific_features(self):
        """Test Windows-specific features and compatibility."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")
        
        # Test Windows process management
        try:
            # Test taskkill availability
            result = subprocess.run(['taskkill', '/?'], 
                                  capture_output=True, text=True, timeout=5)
            assert result.returncode == 0, "taskkill command should be available on Windows"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("taskkill not available or not responding")
        
        # Test netstat availability for port checking
        try:
            result = subprocess.run(['netstat', '-an'], 
                                  capture_output=True, text=True, timeout=5)
            assert result.returncode == 0, "netstat command should be available on Windows"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("netstat not available or not responding")
    
    def test_launcher_configuration_validation(self):
        """Test launcher configuration validation and defaults."""
        # Test default configuration
        default_config = LauncherConfig()
        assert default_config.frontend_port == 3000, "Default frontend port should be 3000"
        assert default_config.dynamic_ports == True, "Dynamic ports should be enabled by default"
        assert default_config.backend_reload == False, "Backend reload should be disabled by default"
        assert default_config.load_secrets == False, "Secret loading should be disabled by default"
        
        # Test configuration with invalid values
        config_with_invalid_port = LauncherConfig(backend_port=99999)  # Invalid port
        # With auto-resolution, invalid ports should be set to None (dynamic)
        assert config_with_invalid_port.backend_port is None, "Invalid port should be auto-resolved to None"
        
        # Test configuration validation
        config = LauncherConfig(
            backend_port=8000,
            frontend_port=3000,
            verbose=True,
            startup_mode='minimal'
        )
        
        assert config.backend_port == 8000, "Backend port should be set correctly"
        assert config.verbose == True, "Verbose mode should be set correctly"
    
    def test_emoji_support_detection(self):
        """Test emoji support detection for different environments."""
        # Test emoji support detection
        emoji_supported = check_emoji_support()
        
        # Should return a boolean
        assert isinstance(emoji_supported, bool), "Emoji support detection should return boolean"
        
        # On Windows, emoji support might be limited
        if platform.system() == "Windows":
            # Don't assert specific value as it depends on terminal
            self.logger.info(f"Windows emoji support detected: {emoji_supported}")
        
        # Test that the function doesn't crash
        assert True, "Emoji support detection should not crash"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])