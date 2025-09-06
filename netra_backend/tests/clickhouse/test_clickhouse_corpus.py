import asyncio

"""
ClickHouse Corpus Table Tests
Tests for corpus table creation and management operations
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import uuid

import pytest
from netra_backend.app.logging_config import central_logger as logger

from netra_backend.tests.clickhouse.test_clickhouse_permissions import (
_check_table_create_permission,
)

@pytest.mark.real_database
class TestCorpusTableOperations:
    """Test corpus table creation and management"""

    @pytest.mark.asyncio
    async def test_create_dynamic_corpus_table(self, async_real_clickhouse_client):
        """Test creating a dynamic corpus table"""
        client = async_real_clickhouse_client
        # Check CREATE TABLE permission
        has_create_permission = await _check_table_create_permission(client)
        if not has_create_permission:
            pytest.skip("development_user lacks CREATE TABLE privileges")

            await self._execute_corpus_table_test(client)

            async def _execute_corpus_table_test(self, client):
                """Execute corpus table creation and testing"""
                corpus_id = str(uuid.uuid4()).replace('-', '_')
                table_name = f"netra_content_corpus_{corpus_id}"
                create_query = self._build_corpus_create_query(table_name)

                try:
                    await client.execute_query(create_query)
                    await self._test_corpus_table_operations(client, table_name, corpus_id)
                except Exception as e:
                    if "not enough privileges" in str(e).lower():
                        pytest.skip(f"Permission denied: {e}")
                        raise
                finally:
                    await self._cleanup_corpus_table(client, table_name)

                    def _build_corpus_create_query(self, table_name):
                        """Build CREATE TABLE query for corpus table"""
                        return f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                    record_id UUID DEFAULT generateUUIDv4(), workload_type String,
                    prompt String, response String, metadata String,
                    domain String DEFAULT 'general', created_at DateTime64(3) DEFAULT now(),
                    version UInt32 DEFAULT 1, embedding Array(Float32) DEFAULT [],
                    tags Array(String) DEFAULT []
                    ) ENGINE = MergeTree() PARTITION BY toYYYYMM(created_at)
                    ORDER BY (workload_type, created_at, record_id)"""""

                    async def _test_corpus_table_operations(self, client, table_name, corpus_id):
                        """Test corpus table operations"""
                        tables_result = await client.execute_query(f"SHOW TABLES LIKE '{table_name}'")
                        assert len(tables_result) > 0
                        logger.info(f"Created corpus table: {table_name}")

                        await self._insert_corpus_test_data(client, table_name, corpus_id)
                        await self._verify_corpus_test_data(client, table_name)

                        async def _insert_corpus_test_data(self, client, table_name, corpus_id):
                            """Insert test data into corpus table"""
                            insert_query = f"""
                            INSERT INTO {table_name} (workload_type, prompt, response, 
                            metadata, domain, tags) VALUES ('test_workload', 
                            'Test prompt for corpus', 'Test response from model',
                            '{{"test": true, "corpus_id": "{corpus_id}"}}', 'testing',
                            ['test', 'automated', 'corpus'])"""""
                            await client.execute_query(insert_query)

                            async def _verify_corpus_test_data(self, client, table_name):
                                """Verify corpus test data insertion"""
                                select_result = await client.execute_query(
                                f"SELECT * FROM {table_name} WHERE workload_type = 'test_workload'"
                                )
                                assert len(select_result) == 1
                                assert select_result[0]['prompt'] == 'Test prompt for corpus'

                                async def _cleanup_corpus_table(self, client, table_name):
                                    """Cleanup corpus test table"""
                                    try:
                                        await client.execute_query(f"DROP TABLE IF EXISTS {table_name}")
                                        logger.info(f"Cleaned up test table: {table_name}")
                                    except Exception as e:
                                        logger.warning(f"Failed to cleanup table {table_name}: {e}")

                                        if __name__ == "__main__":
    # Run tests with pytest
                                            pytest.main([__file__, "-v", "--tb=short"])