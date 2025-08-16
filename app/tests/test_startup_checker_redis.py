"""Tests for StartupChecker Redis checks."""

import pytest
from unittest.mock import patch, AsyncMock

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import (
    create_mock_app, setup_redis_read_write_test, verify_redis_operations
)


class TestStartupCheckerRedis:
    """Test StartupChecker Redis checks."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    async def test_check_redis_success(self, mock_app, checker):
        """Test Redis check success."""
        redis_manager = mock_app.state.redis_manager
        setup_redis_read_write_test(redis_manager)
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            result = await checker.service_checker.check_redis()
            
            assert result.success == True
            assert "Redis connected" in result.message
            verify_redis_operations(redis_manager)
    async def test_check_redis_read_write_failure(self, mock_app, checker):
        """Test Redis check with read/write test failure."""
        redis_manager = mock_app.state.redis_manager
        redis_manager.get = AsyncMock(return_value="wrong_value")
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            result = await checker.service_checker.check_redis()
            
            assert result.success == False
            assert "read/write test failed" in result.message
    async def test_check_redis_connection_failure_production(self, mock_app, monkeypatch):
        """Test Redis check with connection failure in production (critical)."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        # Create checker after setting environment
        checker = StartupChecker(mock_app)
        
        redis_manager = mock_app.state.redis_manager
        redis_manager.connect = AsyncMock(side_effect=Exception("Connection refused"))
        
        result = await checker.service_checker.check_redis()
        
        assert result.success == False
        assert result.critical == True
        assert "Connection refused" in result.message
    async def test_check_redis_connection_failure_development(self, mock_app, checker):
        """Test Redis check with connection failure in development (non-critical)."""
        redis_manager = mock_app.state.redis_manager
        redis_manager.connect = AsyncMock(side_effect=Exception("Connection refused"))
        
        with patch('app.startup_checks.service_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            result = await checker.service_checker.check_redis()
            
            assert result.success == False
            assert result.critical == False