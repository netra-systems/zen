"""
Database Performance Tests

Tests database performance under load, including bulk operations,
concurrent access, and ClickHouse optimization patterns.
"""
import sys
from pathlib import Path
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment
import asyncio
import time
import uuid
from typing import Dict, List
import pytest
from netra_backend.app.services.generation_job_manager import get_corpus_from_clickhouse, save_corpus_to_clickhouse

class DatabasePerformanceTests:
    """Test database performance under load"""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_clickhouse_bulk_insert_performance(self):
        """Test bulk insert performance"""
        large_corpus = self._generate_large_test_corpus(50000)
        table_name = 'perf_test_bulk_insert'
        with patch('netra_backend.app.db.clickhouse_base.ClickHouseDatabase') as mock_db_class:
            mock_db = AsyncNone
            mock_db_class.return_value = mock_db
            with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                mock_interceptor = AsyncNone
                mock_interceptor_class.return_value = mock_interceptor
                with patch('netra_backend.app.services.generation_job_manager.manager') as mock_manager:
                    mock_manager.broadcast_to_job = AsyncNone
                    start_time = time.perf_counter()
                    await save_corpus_to_clickhouse(large_corpus, table_name)
                    duration = time.perf_counter() - start_time
                assert duration < 60

    def _generate_large_test_corpus(self, size: int) -> Dict[str, List]:
        """Generate large test corpus"""
        corpus = {'simple_chat': [], 'analysis': []}
        for i in range(size // 2):
            corpus['simple_chat'].append((f'prompt_{i}', f'response_{i}'))
            corpus['analysis'].append((f'analysis_prompt_{i}', f'analysis_response_{i}'))
        return corpus

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self):
        """Test concurrent database read/write operations"""
        table_names = [f'perf_test_{i}' for i in range(5)]
        mock_db_connection = AsyncNone
        mock_db_connection.execute_query.return_value = [{'workload_type': 'test', 'prompt': 'p', 'response': 'r'} for _ in range(1000)]
        mock_db_connection.disconnect.return_value = None
        with patch('netra_backend.app.services.generation_job_manager._create_clickhouse_connection', return_value=mock_db_connection):
            tasks = []
            for table_name in table_names:
                task = get_corpus_from_clickhouse(table_name)
                tasks.append(task)
            start_time = time.perf_counter()
            results = await asyncio.gather(*tasks)
            duration = time.perf_counter() - start_time
            assert len(results) == 5
            assert duration < 30

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self):
        """Test optimized batch processing patterns"""
        batch_sizes = [100, 500, 1000, 5000]
        processing_times = []
        for batch_size in batch_sizes:
            test_corpus = self._generate_large_test_corpus(batch_size)
            with patch('netra_backend.app.db.clickhouse_base.ClickHouseDatabase') as mock_db_class:
                mock_db = AsyncNone
                mock_db_class.return_value = mock_db
                with patch('netra_backend.app.db.clickhouse_query_fixer.ClickHouseQueryInterceptor') as mock_interceptor_class:
                    mock_interceptor = AsyncNone
                    mock_interceptor_class.return_value = mock_interceptor
                    with patch('netra_backend.app.services.generation_job_manager.manager') as mock_manager:
                        mock_manager.broadcast_to_job = AsyncNone
                        start_time = time.perf_counter()
                        await save_corpus_to_clickhouse(test_corpus, f'batch_test_{batch_size}')
                        duration = time.perf_counter() - start_time
                    processing_times.append(duration)
        for i in range(1, len(processing_times)):
            time_ratio = processing_times[i] / processing_times[i - 1]
            size_ratio = batch_sizes[i] / batch_sizes[i - 1]
            assert time_ratio < size_ratio * 1.3

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_connection_pool_utilization(self):
        """Test database connection pool efficiency"""
        connection_count = 0

        async def mock_connection_factory(*args, **kwargs):
            """Mock connection factory to track usage"""
            nonlocal connection_count
            connection_count += 1
            mock_conn = AsyncNone
            return mock_conn
        with patch('netra_backend.app.db.clickhouse_base.ClickHouseDatabase', side_effect=mock_connection_factory):
            tasks = []
            for i in range(20):
                corpus = {'test': [('p', 'r')]}
                task = save_corpus_to_clickhouse(corpus, f'pool_test_{i}')
                tasks.append(task)
            await asyncio.gather(*tasks, return_exceptions=True)
            assert connection_count <= 20

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_query_optimization_patterns(self):
        """Test query optimization for large datasets"""
        query_scenarios = [{'table': 'small_table', 'rows': 1000}, {'table': 'medium_table', 'rows': 10000}, {'table': 'large_table', 'rows': 100000}]
        for scenario in query_scenarios:
            mock_db_connection = AsyncNone
            mock_db_connection.execute_query.return_value = [{'workload_type': 'test', 'prompt': f'p_{i}', 'response': f'r_{i}'} for i in range(min(scenario['rows'], 1000))]
            mock_db_connection.disconnect.return_value = None
            with patch('netra_backend.app.services.generation_job_manager._create_clickhouse_connection', return_value=mock_db_connection):
                start_time = time.perf_counter()
                result = await get_corpus_from_clickhouse(scenario['table'])
                duration = time.perf_counter() - start_time
                assert duration < 5.0
                assert len(result) > 0
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')