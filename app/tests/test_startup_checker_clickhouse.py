"""Tests for StartupChecker ClickHouse checks."""

import pytest
from unittest.mock import patch, Mock, AsyncMock

from app.startup_checks import StartupChecker
from app.tests.helpers.startup_check_helpers import (
    create_mock_app, create_mock_clickhouse_client
)


class TestStartupCheckerClickHouse:
    """Test StartupChecker ClickHouse checks."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required state."""
        return create_mock_app()
    
    @pytest.fixture
    def checker(self, mock_app):
        """Create a StartupChecker instance."""
        return StartupChecker(mock_app)
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_success(self, checker):
        """Test ClickHouse check success."""
        tables = [{'name': 'workload_events'}, {'name': 'other_table'}]
        mock_client = create_mock_clickhouse_client(tables)
        
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                
                await checker.check_clickhouse()
                
                assert len(checker.results) == 1
                assert checker.results[0].success == True
                assert "2 tables" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_missing_tables(self, checker):
        """Test ClickHouse check with missing required tables."""
        tables = [{'name': 'other_table'}]
        mock_client = create_mock_clickhouse_client(tables)
        
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                
                await checker.check_clickhouse()
                
                assert len(checker.results) == 1
                assert checker.results[0].success == False
                assert "Missing ClickHouse tables" in checker.results[0].message
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_connection_failure(self, checker):
        """Test ClickHouse check with connection failure."""
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                
                await checker.check_clickhouse()
                
                assert len(checker.results) == 1
                assert checker.results[0].success == False
                assert "Connection failed" in checker.results[0].message
                assert checker.results[0].critical == False
    
    @pytest.mark.asyncio
    async def test_check_clickhouse_tuple_result(self, checker):
        """Test ClickHouse check with tuple result format."""
        tables = [('workload_events',), ('other_table',)]
        mock_client = create_mock_clickhouse_client(tables)
        
        with patch('app.db.clickhouse.get_clickhouse_client') as mock_get_client:
            mock_get_client.return_value = mock_client
            with patch('app.startup_checks.settings') as mock_settings:
                mock_settings.environment = "development"
                
                await checker.check_clickhouse()
                
                assert len(checker.results) == 1
                assert checker.results[0].success == True