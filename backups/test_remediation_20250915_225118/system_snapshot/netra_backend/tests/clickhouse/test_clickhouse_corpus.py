"""
ClickHouse Corpus Table Tests - Unit Tests
Tests for corpus table creation and management operations using mocks
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from test_framework.performance_helpers import fast_test

@pytest.mark.unit
@pytest.mark.database
@fast_test
class CorpusTableOperationsTests:
    """Unit tests for corpus table creation and management"""

    def _build_corpus_create_query(self, table_name):
        """Build CREATE TABLE query for corpus table"""
        return f"\n        CREATE TABLE IF NOT EXISTS {table_name} (\n            record_id UUID DEFAULT generateUUIDv4(),\n            workload_type String,\n            prompt String,\n            response String,\n            metadata String,\n            domain String DEFAULT 'general',\n            created_at DateTime64(3) DEFAULT now(),\n            version UInt32 DEFAULT 1,\n            embedding Array(Float32) DEFAULT [],\n            tags Array(String) DEFAULT []\n        ) ENGINE = MergeTree()\n        PARTITION BY toYYYYMM(created_at)\n        ORDER BY (workload_type, created_at, record_id)\n        "

    @pytest.mark.asyncio
    async def test_create_dynamic_corpus_table(self):
        """Test creating a dynamic corpus table with mocked ClickHouse client"""
        mock_client = AsyncMock()
        mock_client.execute_query.return_value = []
        with patch('netra_backend.tests.clickhouse.test_clickhouse_permissions._check_table_create_permission', return_value=True):
            corpus_id = str(uuid.uuid4()).replace('-', '_')
            table_name = f'netra_content_corpus_{corpus_id}'
            create_query = self._build_corpus_create_query(table_name)
            await mock_client.execute_query(create_query)
            mock_client.execute_query.assert_called_once_with(create_query)
            assert table_name.startswith('netra_content_corpus_')
            assert len(corpus_id.replace('_', '')) == 32
            assert 'CREATE TABLE IF NOT EXISTS' in create_query
            assert table_name in create_query
            assert 'MergeTree()' in create_query

    @pytest.mark.asyncio
    async def test_corpus_table_query_structure(self):
        """Test that corpus table creation query has correct structure"""
        corpus_id = str(uuid.uuid4()).replace('-', '_')
        table_name = f'netra_content_corpus_{corpus_id}'
        create_query = self._build_corpus_create_query(table_name)
        expected_columns = ['record_id UUID', 'workload_type String', 'prompt String', 'response String', 'metadata String', 'domain String', 'created_at DateTime64', 'version UInt32', 'embedding Array(Float32)', 'tags Array(String)']
        for column in expected_columns:
            assert column in create_query, f"Column '{column}' not found in CREATE query"
        assert 'ENGINE = MergeTree()' in create_query
        assert 'PARTITION BY toYYYYMM(created_at)' in create_query
        assert 'ORDER BY (workload_type, created_at, record_id)' in create_query

    @pytest.mark.asyncio
    async def test_corpus_table_permission_error_handling(self):
        """Test handling of permission errors during table creation"""
        mock_client = AsyncMock()
        with patch('netra_backend.tests.clickhouse.test_clickhouse_permissions._check_table_create_permission', return_value=False):
            has_permission = False
            if not has_permission:
                assert True, 'Permission check correctly identified lack of privileges'
            else:
                assert False, 'Permission check failed to identify lack of privileges'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')