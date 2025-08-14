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
    
    @pytest.mark.asyncio
    async def test_check_redis_success(self, mock_app, checker):
        """Test Redis check success."""
        redis_manager = mock_app.state.redis_manager
        setup_redis_read_write_test(redis_manager)
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            await checker.check_redis()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == True
            assert "Redis connected" in checker.results[0].message
            verify_redis_operations(redis_manager)
    
    @pytest.mark.asyncio
    async def test_check_redis_read_write_failure(self, mock_app, checker):
        """Test Redis check with read/write test failure."""
        redis_manager = mock_app.state.redis_manager
        redis_manager.get = AsyncMock(return_value="wrong_value")
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            
            await checker.check_redis()
            
            assert len(checker.results) == 1
            assert checker.results[0].success == False
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
            assert checker.results[0].success == False
            assert checker.results[0].critical == True
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
            assert checker.results[0].success == False
            assert checker.results[0].critical == False