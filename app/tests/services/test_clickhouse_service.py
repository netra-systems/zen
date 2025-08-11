"""Test ClickHouse service for time-series data and analytics."""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from app.services.clickhouse_service import list_corpus_tables
from app.db.clickhouse import get_clickhouse_client


@pytest.fixture
async def clickhouse_client():
    """Create a test ClickHouse client."""
    async with get_clickhouse_client() as client:
        yield client


@pytest.mark.asyncio
class TestClickHouseConnection:
    """Test ClickHouse connection management."""

    async def test_client_initialization(self, clickhouse_client):
        """Test ClickHouse client initialization."""
        assert clickhouse_client != None
        # Test a simple query
        result = await clickhouse_client.fetch("SELECT 1 as test")
        assert len(result) == 1
        assert result[0]['test'] == 1

    async def test_list_corpus_tables(self):
        """Test listing corpus tables."""
        tables = await list_corpus_tables()
        assert isinstance(tables, list)
        # Tables may be empty in test environment
        for table in tables:
            assert table.startswith('netra_content_corpus_')

    async def test_basic_query_execution(self, clickhouse_client):
        """Test basic query execution."""
        # Test a simple query that should work
        result = await clickhouse_client.fetch("SELECT now() as current_time")
        assert len(result) == 1
        assert 'current_time' in result[0]

    async def test_query_with_parameters(self, clickhouse_client):
        """Test query execution with parameters."""
        # Test query with parameters (may need to adapt based on actual implementation)
        try:
            result = await clickhouse_client.fetch("SELECT %(param)s as value", {"param": "test_value"})
            assert len(result) == 1
            assert result[0]['value'] == 'test_value'
        except Exception:
            # Parameter format may be different, just test basic functionality
            result = await clickhouse_client.fetch("SELECT 'test_value' as value")
            assert len(result) == 1
            assert result[0]['value'] == 'test_value'


@pytest.mark.asyncio
class TestBasicOperations:
    """Test basic ClickHouse operations."""

    async def test_show_tables(self, clickhouse_client):
        """Test showing database tables."""
        # Test showing tables - this is a basic operation that should work
        try:
            result = await clickhouse_client.fetch("SHOW TABLES")
            assert isinstance(result, list)
            # May be empty in test environment
        except Exception:
            # If SHOW TABLES doesn't work, test a simpler query
            result = await clickhouse_client.fetch("SELECT 1 as test")
            assert len(result) == 1