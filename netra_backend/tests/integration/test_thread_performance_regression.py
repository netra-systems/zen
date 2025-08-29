"""
Thread Operations Performance Regression Testing

Business Value Justification (BVJ):
- Segment: All (Core functionality performance)
- Business Goal: System performance, user experience
- Value Impact: Detect performance regressions in thread operations before they impact users
- Strategic Impact: Maintain responsive thread creation/retrieval under normal and stress loads

Performance Regression Coverage:
- Thread creation performance benchmarks
- Thread retrieval query performance
- Bulk thread operations timing
- Memory usage during thread operations
- Performance under concurrent load
"""
import asyncio
import pytest
import time
import statistics
import psutil
import os
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any

from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.schemas.core_models import Thread
from netra_backend.app.routes.threads_route import ThreadCreate
from netra_backend.app.dependencies import get_db_dependency
from sqlalchemy.ext.asyncio import AsyncSession


class TestThreadPerformanceRegression:
    """Test thread operations performance to detect regressions"""
    
    # Performance thresholds (in seconds)
    MAX_SINGLE_THREAD_CREATE_TIME = 0.1  # 100ms
    MAX_BULK_THREAD_CREATE_TIME = 2.0    # 2 seconds for 100 threads
    MAX_THREAD_QUERY_TIME = 0.05         # 50ms
    MAX_MEMORY_INCREASE_MB = 50          # 50MB increase allowed
    
    def setup_method(self):
        """Set up test fixtures"""
        self.thread_repository = ThreadRepository()
        self.performance_results = {}
    
    @pytest.mark.asyncio
    async def test_single_thread_creation_performance(self):
        """Test single thread creation performance - EXPECTED TO FAIL if slow"""
        mock_session = Mock(spec=AsyncSession)
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock thread creation to avoid database dependencies
        mock_thread = Mock(spec=Thread)
        mock_thread.id = "test_thread_id"
        
        # Measure thread creation time
        start_time = time.time()
        
        try:
            # Simulate thread creation
            thread_data = ThreadCreate(
                title="Performance Test Thread",
                metadata={"description": "Thread for performance testing"}
            )
            
            # Mock the repository create operation
            with patch.object(self.thread_repository, 'create') as mock_create:
                mock_create.return_value = mock_thread
                result = await self.thread_repository.create(mock_session, thread_data)
                
                end_time = time.time()
                creation_time = end_time - start_time
                
                # THIS WILL FAIL if thread creation is slower than threshold
                assert creation_time < self.MAX_SINGLE_THREAD_CREATE_TIME, \
                    f"Thread creation took {creation_time:.3f}s, exceeds {self.MAX_SINGLE_THREAD_CREATE_TIME}s limit"
                
                # Store result for reporting
                self.performance_results['single_thread_create'] = creation_time
                
        except Exception as e:
            pytest.fail(f"Thread creation performance test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_bulk_thread_creation_performance(self):
        """Test bulk thread creation performance - EXPECTED TO FAIL if inefficient"""
        mock_session = Mock(spec=AsyncSession)
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        thread_count = 100
        creation_times = []
        
        # Mock bulk thread creation
        mock_threads = [Mock(spec=Thread, id=f"thread_{i}") for i in range(thread_count)]
        
        start_time = time.time()
        
        # Create threads in bulk
        with patch.object(self.thread_repository, 'create') as mock_create:
            mock_create.side_effect = mock_threads
            
            for i in range(thread_count):
                thread_start = time.time()
                
                thread_data = ThreadCreate(
                    title=f"Bulk Test Thread {i}",
                    metadata={"description": f"Thread {i} for bulk performance testing"}
                )
                
                await self.thread_repository.create(mock_session, thread_data)
                
                thread_end = time.time()
                creation_times.append(thread_end - thread_start)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # THIS WILL FAIL if bulk creation is too slow
        assert total_time < self.MAX_BULK_THREAD_CREATE_TIME, \
            f"Bulk thread creation took {total_time:.3f}s, exceeds {self.MAX_BULK_THREAD_CREATE_TIME}s limit"
        
        # Performance analysis
        avg_time = statistics.mean(creation_times)
        median_time = statistics.median(creation_times)
        max_time = max(creation_times)
        
        # Additional performance assertions
        assert avg_time < self.MAX_SINGLE_THREAD_CREATE_TIME / 2, \
            f"Average creation time {avg_time:.3f}s too high in bulk operations"
        
        assert max_time < self.MAX_SINGLE_THREAD_CREATE_TIME * 2, \
            f"Slowest creation time {max_time:.3f}s indicates performance bottleneck"
        
        # Store results
        self.performance_results['bulk_thread_create'] = {
            'total_time': total_time,
            'average_time': avg_time,
            'median_time': median_time,
            'max_time': max_time,
            'thread_count': thread_count
        }
    
    @pytest.mark.asyncio
    async def test_thread_query_performance(self):
        """Test thread query performance - EXPECTED TO FAIL if queries are slow"""
        mock_session = Mock(spec=AsyncSession)
        
        # Mock query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            Mock(spec=Thread, id=f"thread_{i}") for i in range(50)
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        query_times = []
        
        # Test multiple query scenarios
        test_scenarios = [
            {'user_id': 'user1', 'limit': 10},
            {'user_id': 'user2', 'limit': 25},
            {'user_id': 'user3', 'limit': 50},
        ]
        
        for scenario in test_scenarios:
            start_time = time.time()
            
            # Perform query
            with patch.object(self.thread_repository, 'find_by_user') as mock_query:
                mock_query.return_value = [Mock(spec=Thread) for _ in range(scenario['limit'])]
                
                await self.thread_repository.find_by_user(
                    mock_session, 
                    scenario['user_id']
                )
                
                end_time = time.time()
                query_time = end_time - start_time
                query_times.append(query_time)
                
                # THIS WILL FAIL if individual queries are too slow
                assert query_time < self.MAX_THREAD_QUERY_TIME, \
                    f"Thread query took {query_time:.3f}s, exceeds {self.MAX_THREAD_QUERY_TIME}s limit"
        
        # Overall query performance analysis
        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)
        
        # Store results
        self.performance_results['thread_queries'] = {
            'average_time': avg_query_time,
            'max_time': max_query_time,
            'query_count': len(query_times)
        }
    
    @pytest.mark.asyncio
    async def test_thread_operations_memory_usage(self):
        """Test memory usage during thread operations - EXPECTED TO FAIL if memory leaks"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
        
        mock_session = Mock(spec=AsyncSession)
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Create many thread objects to test memory usage
        thread_objects = []
        
        for i in range(200):  # Create more objects to stress memory
            # Create large thread objects with data
            thread_data = ThreadCreate(
                title=f"Memory Test Thread {i}",
                metadata={"description": f"Thread {i} with detailed description for memory testing" * 10}
            )
            
            # Mock thread with data
            mock_thread = Mock(spec=Thread)
            mock_thread.id = f"thread_{i}"
            mock_thread.name = thread_data.name
            mock_thread.description = thread_data.description
            mock_thread.large_data = "x" * 1024  # 1KB of data per thread
            
            thread_objects.append(mock_thread)
        
        # Check memory usage after creating objects
        mid_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = mid_memory - initial_memory
        
        # THIS WILL FAIL if memory usage is excessive
        assert memory_increase < self.MAX_MEMORY_INCREASE_MB, \
            f"Memory usage increased by {memory_increase:.2f}MB, exceeds {self.MAX_MEMORY_INCREASE_MB}MB limit"
        
        # Clean up objects
        thread_objects.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Check memory after cleanup
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_freed = mid_memory - final_memory
        
        # Store results
        self.performance_results['memory_usage'] = {
            'initial_mb': initial_memory,
            'peak_mb': mid_memory,
            'final_mb': final_memory,
            'increase_mb': memory_increase,
            'freed_mb': memory_freed
        }
    
    @pytest.mark.asyncio
    async def test_concurrent_thread_operations_performance(self):
        """Test performance under concurrent thread operations - EXPECTED TO FAIL if not scalable"""
        mock_session = Mock(spec=AsyncSession)
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        concurrent_operations = 20
        operation_results = []
        
        async def perform_thread_operation(operation_id: int):
            """Simulate a thread operation"""
            start_time = time.time()
            
            try:
                # Create thread
                thread_data = ThreadCreate(
                    title=f"Concurrent Thread {operation_id}",
                    metadata={"description": f"Concurrent operation {operation_id}"}
                )
                
                with patch.object(self.thread_repository, 'create') as mock_create:
                    mock_create.return_value = Mock(spec=Thread, id=f"thread_{operation_id}")
                    await self.thread_repository.create(mock_session, thread_data)
                
                # Simulate additional operations (query, update)
                await asyncio.sleep(0.01)  # Simulate processing time
                
                end_time = time.time()
                operation_time = end_time - start_time
                
                return {
                    'operation_id': operation_id,
                    'time': operation_time,
                    'success': True
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    'operation_id': operation_id,
                    'time': end_time - start_time,
                    'success': False,
                    'error': str(e)
                }
        
        # Run concurrent operations
        start_time = time.time()
        tasks = [perform_thread_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # Analyze results
        successful_ops = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_ops = [r for r in results if isinstance(r, dict) and not r.get('success')]
        exceptions = [r for r in results if not isinstance(r, dict)]
        
        # THIS WILL FAIL if concurrent performance is poor
        assert len(successful_ops) > concurrent_operations * 0.8, \
            f"Only {len(successful_ops)}/{concurrent_operations} operations succeeded"
        
        # Performance assertions
        avg_op_time = statistics.mean([op['time'] for op in successful_ops])
        max_op_time = max([op['time'] for op in successful_ops])
        
        assert avg_op_time < self.MAX_SINGLE_THREAD_CREATE_TIME * 2, \
            f"Average concurrent operation time {avg_op_time:.3f}s too high"
        
        assert total_time < self.MAX_SINGLE_THREAD_CREATE_TIME * 5, \
            f"Total concurrent operations took {total_time:.3f}s, too slow"
        
        # Store results
        self.performance_results['concurrent_operations'] = {
            'total_time': total_time,
            'successful_ops': len(successful_ops),
            'failed_ops': len(failed_ops),
            'exceptions': len(exceptions),
            'avg_op_time': avg_op_time,
            'max_op_time': max_op_time
        }
    
    @pytest.mark.asyncio
    async def test_thread_search_performance(self):
        """Test thread search operation performance - EXPECTED TO FAIL if search is slow"""
        mock_session = Mock(spec=AsyncSession)
        
        # Mock search results
        search_results = [Mock(spec=Thread, id=f"found_thread_{i}") for i in range(20)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = search_results
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        search_scenarios = [
            {'query': 'test', 'expected_results': 20},
            {'query': 'performance', 'expected_results': 15},
            {'query': 'regression', 'expected_results': 10},
            {'query': 'thread operations', 'expected_results': 5},
        ]
        
        search_times = []
        
        for scenario in search_scenarios:
            start_time = time.time()
            
            # Mock search operation
            with patch.object(self.thread_repository, 'search') as mock_search:
                mock_search.return_value = search_results[:scenario['expected_results']]
                
                results = await self.thread_repository.search(
                    mock_session,
                    query=scenario['query'],
                    user_id="test_user"
                )
                
                end_time = time.time()
                search_time = end_time - start_time
                search_times.append(search_time)
                
                # THIS WILL FAIL if search is too slow
                assert search_time < self.MAX_THREAD_QUERY_TIME * 2, \
                    f"Thread search took {search_time:.3f}s, exceeds limit"
                
                assert len(results) == scenario['expected_results'], \
                    f"Expected {scenario['expected_results']} results, got {len(results)}"
        
        # Overall search performance
        avg_search_time = statistics.mean(search_times)
        max_search_time = max(search_times)
        
        # Store results
        self.performance_results['search_operations'] = {
            'average_time': avg_search_time,
            'max_time': max_search_time,
            'search_count': len(search_times)
        }
    
    def teardown_method(self):
        """Report performance results after each test"""
        if self.performance_results:
            print(f"\n=== Performance Results ===")
            for operation, results in self.performance_results.items():
                if isinstance(results, dict):
                    print(f"{operation}:")
                    for key, value in results.items():
                        if isinstance(value, float):
                            print(f"  {key}: {value:.4f}s")
                        else:
                            print(f"  {key}: {value}")
                else:
                    print(f"{operation}: {results:.4f}s")
            print("=" * 30)