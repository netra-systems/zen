"""Tests for StartupChecker system resource checks."""

import pytest
from unittest.mock import patch, Mock

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import (
    create_mock_app, create_mock_memory_info, create_mock_disk_info
)


class TestStartupCheckerResources:
    """Test StartupChecker system resource checks."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_ok(self, checker):
        """Test system resources check with adequate resources."""
        with patch('app.startup_checks.system_checks.psutil') as mock_psutil:
            mock_psutil.virtual_memory.return_value = create_mock_memory_info(16, 8)
            mock_psutil.disk_usage.return_value = create_mock_disk_info(100)
            mock_psutil.cpu_count.return_value = 8
            
            result = await checker.system_checker.check_memory_and_resources()
            
            assert result.success == True
            assert "Resources OK" in result.message
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_warnings(self, checker):
        """Test system resources check with resource warnings."""
        with patch('app.startup_checks.system_checks.psutil') as mock_psutil:
            mock_psutil.virtual_memory.return_value = create_mock_memory_info(4, 0.5)
            mock_psutil.disk_usage.return_value = create_mock_disk_info(2)
            mock_psutil.cpu_count.return_value = 1
            
            result = await checker.system_checker.check_memory_and_resources()
            
            assert result.success == True
            assert "Resource warnings" in result.message
            assert "Low memory" in result.message
            assert "Low disk space" in result.message
            assert "Low CPU count" in result.message
    
    @pytest.mark.asyncio
    async def test_check_memory_and_resources_exception(self, checker):
        """Test system resources check with exception."""
        with patch('app.startup_checks.system_checks.psutil.virtual_memory', 
                  side_effect=Exception("Cannot read memory")):
            result = await checker.system_checker.check_memory_and_resources()
            
            assert result.success == True  # Non-critical failure
            assert "Could not check resources" in result.message