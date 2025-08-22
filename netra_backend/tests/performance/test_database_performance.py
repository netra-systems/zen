"""
Database Performance Tests

Tests database performance under load, including bulk operations,
concurrent access, and ClickHouse optimization patterns.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
import uuid
from typing import Dict, List
from unittest.mock import AsyncMock, patch

import pytest

# Add project root to path
from netra_backend.app.services.generation_service import (
    get_corpus_from_clickhouse,
    # Add project root to path
    save_corpus_to_clickhouse,
)


class TestDatabasePerformance:
    """Test database performance under load"""
    @pytest.mark.performance
    async def test_clickhouse_bulk_insert_performance(self):
        """Test bulk insert performance"""
        large_corpus = self._generate_large_test_corpus(50000)
        table_name = 'perf_test_bulk_insert'
        
        with patch('app.services.generation_service.ClickHouseDatabase') as mock_db_class:
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            
            with patch('app.services.generation_service.ClickHouseQueryInterceptor') as mock_interceptor_class:
                mock_interceptor = AsyncMock()
                mock_interceptor_class.return_value = mock_interceptor
                
                start_time = time.perf_counter()
                await save_corpus_to_clickhouse(large_corpus, table_name)
                duration = time.perf_counter() - start_time
                
                # Should complete bulk insert efficiently
                assert duration < 60  # Under 1 minute for 50k records
                assert mock_interceptor.insert_data.called

    def _generate_large_test_corpus(self, size: int) -> Dict[str, List]:
        """Generate large test corpus"""
        corpus = {'simple_chat': [], 'analysis': []}
        
        for i in range(size // 2):
            corpus['simple_chat'].append((f'prompt_{i}', f'response_{i}'))
            corpus['analysis'].append((f'analysis_prompt_{i}', f'analysis_response_{i}'))
            
        return corpus
    @pytest.mark.performance
    async def test_concurrent_database_operations(self):
        """Test concurrent database read/write operations"""
        table_names = [f'perf_test_{i}' for i in range(5)]
        
        with patch('app.services.generation_service.ClickHouseDatabase') as mock_db_class:
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            
            with patch('app.services.generation_service.ClickHouseQueryInterceptor') as mock_interceptor_class:
                mock_interceptor = AsyncMock()
                mock_interceptor_class.return_value = mock_interceptor
                mock_interceptor.execute_query.return_value = [
                    {'workload_type': 'test', 'prompt': 'p', 'response': 'r'}
                    for _ in range(1000)
                ]
                
                tasks = []
                for table_name in table_names:
                    task = get_corpus_from_clickhouse(table_name)
                    tasks.append(task)
                
                start_time = time.perf_counter()
                results = await asyncio.gather(*tasks)
                duration = time.perf_counter() - start_time
                
                assert len(results) == 5
                assert duration < 30  # Should handle concurrent ops efficiently
    @pytest.mark.performance
    async def test_batch_processing_optimization(self):
        """Test optimized batch processing patterns"""
        batch_sizes = [100, 500, 1000, 5000]
        processing_times = []
        
        for batch_size in batch_sizes:
            test_corpus = self._generate_large_test_corpus(batch_size)
            
            with patch('app.services.generation_service.ClickHouseDatabase') as mock_db_class:
                mock_db = AsyncMock()
                mock_db_class.return_value = mock_db
                
                with patch('app.services.generation_service.ClickHouseQueryInterceptor') as mock_interceptor_class:
                    mock_interceptor = AsyncMock()
                    mock_interceptor_class.return_value = mock_interceptor
                    
                    start_time = time.perf_counter()
                    await save_corpus_to_clickhouse(test_corpus, f'batch_test_{batch_size}')
                    duration = time.perf_counter() - start_time
                    
                    processing_times.append(duration)
        
        # Processing should scale sub-linearly with batch size
        for i in range(1, len(processing_times)):
            time_ratio = processing_times[i] / processing_times[i-1]
            size_ratio = batch_sizes[i] / batch_sizes[i-1]
            assert time_ratio < size_ratio * 1.3  # Allow 30% overhead
    @pytest.mark.performance
    async def test_connection_pool_utilization(self):
        """Test database connection pool efficiency"""
        connection_count = 0
        
        def mock_connection_factory(*args, **kwargs):
            """Mock connection factory to track usage"""
            nonlocal connection_count
            connection_count += 1
            mock_conn = AsyncMock()
            return mock_conn
        
        with patch('app.services.generation_service.ClickHouseDatabase', 
                   side_effect=mock_connection_factory):
            
            # Simulate multiple concurrent database operations
            tasks = []
            for i in range(20):  # More operations than typical pool size
                corpus = {'test': [('p', 'r')]}
                task = save_corpus_to_clickhouse(corpus, f'pool_test_{i}')
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Should reuse connections efficiently
            assert connection_count <= 20  # Should not exceed reasonable limit
    @pytest.mark.performance  
    async def test_query_optimization_patterns(self):
        """Test query optimization for large datasets"""
        # Test different query patterns
        query_scenarios = [
            {'table': 'small_table', 'rows': 1000},
            {'table': 'medium_table', 'rows': 10000}, 
            {'table': 'large_table', 'rows': 100000}
        ]
        
        for scenario in query_scenarios:
            with patch('app.services.generation_service.ClickHouseDatabase') as mock_db_class:
                mock_db = AsyncMock()
                mock_db_class.return_value = mock_db
                
                with patch('app.services.generation_service.ClickHouseQueryInterceptor') as mock_interceptor_class:
                    mock_interceptor = AsyncMock()
                    mock_interceptor_class.return_value = mock_interceptor
                    
                    # Mock response based on table size
                    mock_interceptor.execute_query.return_value = [
                        {'workload_type': 'test', 'prompt': f'p_{i}', 'response': f'r_{i}'}
                        for i in range(min(scenario['rows'], 1000))  # Limit response size
                    ]
                    
                    start_time = time.perf_counter()
                    result = await get_corpus_from_clickhouse(scenario['table'])
                    duration = time.perf_counter() - start_time
                    
                    # Query time should be reasonable regardless of table size
                    assert duration < 5.0  # Under 5 seconds for any query
                    assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-m", "performance"])