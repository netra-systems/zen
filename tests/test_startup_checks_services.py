"""
Service tests for app/startup_checks.py - Database, Redis, ClickHouse, LLM checks

This module tests service connectivity and integration checks.
Part of the refactored test suite to maintain 300-line limit per file.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.startup_checks import StartupChecker
from app.db.models_postgres import Assistant


class TestDatabaseChecks:
    """Test database connectivity checks"""
    
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
    async def test_check_database_connection_success(self, checker, mock_app):
        """Test database connection check success"""
        mock_session = self._setup_successful_db_session(mock_app)
        
        await checker.check_database_connection()
        
        result = self._get_first_result(checker)
        self._verify_db_success(result)
    
    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self, checker, mock_app):
        """Test database connection check failure"""
        self._setup_failed_db_session(mock_app)
        
        await checker.check_database_connection()
        
        result = self._get_first_result(checker)
        self._verify_db_failure(result)
    
    @pytest.mark.asyncio
    async def test_check_database_missing_table(self, checker, mock_app):
        """Test database check with missing critical table"""
        mock_session = self._setup_missing_table_session(mock_app)
        
        await checker.check_database_connection()
        
        result = self._get_first_result(checker)
        self._verify_missing_table(result)
    
    def _setup_successful_db_session(self, mock_app):
        """Setup successful database session mock"""
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_app.state.db_session_factory.return_value = mock_context
        
        # Setup successful query results
        results = self._create_successful_db_results()
        mock_session.execute.side_effect = results
        return mock_session
    
    def _setup_failed_db_session(self, mock_app):
        """Setup failed database session mock"""
        mock_context = AsyncMock()
        mock_context.__aenter__.side_effect = Exception("Connection failed")
        mock_app.state.db_session_factory.return_value = mock_context
    
    def _setup_missing_table_session(self, mock_app):
        """Setup database session with missing table"""
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_app.state.db_session_factory.return_value = mock_context
        
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = [1, False]  # Connectivity OK, table missing
        mock_session.execute.return_value = mock_result
        return mock_session
    
    def _create_successful_db_results(self):
        """Create successful database query results"""
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
        
        return results
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _verify_db_success(self, result):
        """Verify successful database connection result"""
        assert result.name == "database_connection"
        assert result.success is True
        assert "PostgreSQL connected" in result.message
    
    def _verify_db_failure(self, result):
        """Verify failed database connection result"""
        assert result.name == "database_connection"
        assert result.success is False
        assert "Connection failed" in result.message
        assert result.critical is True
    
    def _verify_missing_table(self, result):
        """Verify missing table result"""
        assert result.name == "database_connection"
        assert result.success is False
        assert "does not exist" in result.message


class TestRedisChecks:
    """Test Redis connectivity checks"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with Redis manager"""
        app = MagicMock()
        app.state.redis_manager = AsyncMock()
        return app
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance"""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_redis_success(self, checker, mock_app):
        """Test Redis check success"""
        self._setup_successful_redis(mock_app)
        
        await checker.check_redis()
        
        result = self._get_first_result(checker)
        self._verify_redis_success(result)
    
    @pytest.mark.asyncio
    async def test_check_redis_failure(self, checker, mock_app):
        """Test Redis check failure"""
        self._setup_failed_redis(mock_app)
        
        with patch('app.startup_checks.settings') as mock_settings:
            mock_settings.environment = "development"
            await checker.check_redis()
        
        result = self._get_first_result(checker)
        self._verify_redis_failure(result)
    
    @pytest.mark.asyncio
    async def test_check_redis_read_write_failure(self, checker, mock_app):
        """Test Redis check with read/write mismatch"""
        self._setup_redis_read_write_failure(mock_app)
        
        await checker.check_redis()
        
        result = self._get_first_result(checker)
        self._verify_redis_read_write_failure(result)
    
    def _setup_successful_redis(self, mock_app):
        """Setup successful Redis mock"""
        mock_redis = mock_app.state.redis_manager
        mock_redis.connect.return_value = None
        
        # Mock the set method to store the value
        stored_value = None
        
        async def mock_set(key, value, expire=None):
            nonlocal stored_value
            stored_value = value
        
        async def mock_get(key):
            return stored_value
        
        mock_redis.set = mock_set
        mock_redis.get = mock_get
        mock_redis.delete.return_value = None
    
    def _setup_failed_redis(self, mock_app):
        """Setup failed Redis mock"""
        mock_redis = mock_app.state.redis_manager
        mock_redis.connect.side_effect = Exception("Connection refused")
    
    def _setup_redis_read_write_failure(self, mock_app):
        """Setup Redis with read/write failure"""
        mock_redis = mock_app.state.redis_manager
        mock_redis.connect.return_value = None
        mock_redis.set.return_value = None
        mock_redis.get.return_value = "wrong_value"  # Different from what was set
    
    def _get_first_result(self, checker):
        """Get the first result from checker"""
        assert len(checker.results) == 1
        return checker.results[0]
    
    def _verify_redis_success(self, result):
        """Verify successful Redis result"""
        assert result.name == "redis_connection"
        assert result.success is True
        assert "Redis connected" in result.message
    
    def _verify_redis_failure(self, result):
        """Verify failed Redis result"""
        assert result.name == "redis_connection"
        assert result.success is False
        assert "Connection refused" in result.message
    
    def _verify_redis_read_write_failure(self, result):
        """Verify Redis read/write failure result"""
        assert result.name == "redis_connection"
        assert result.success is False
        assert "read/write test failed" in result.message