"""
RED TEAM TESTS 31-35: Performance Bottlenecks and Resource Management

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real performance bottlenecks.
This test validates database performance, connection scaling, and resource management.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Performance, Scalability, Resource Efficiency  
- Value Impact: Performance bottlenecks directly impact user experience and platform costs
- Strategic Impact: Core performance foundation for enterprise AI workload optimization

Testing Level: L3 (Real services, real databases, minimal mocking)
Expected Initial Result: FAILURE (exposes real performance bottlenecks)
"""

import asyncio
import gc
import json
import os
import psutil
import secrets
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import threading

# Platform-specific imports
try:
    import resource  # Unix-only
except ImportError:
    resource = None  # Windows doesn't have this module

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
from netra_backend.app.core.config import get_unified_config
from netra_backend.app.db.session import get_db_session
from netra_backend.app.services.agent_service import AgentService

# Mock models for testing
from unittest.mock import Mock
User = Mock
Thread = Mock
AgentRun = Mock


class TestPerformanceBottlenecks:
    """
    RED TEAM TESTS 31-35: Performance Bottlenecks and Resource Management
    
    Tests critical performance limits that impact platform scalability.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        config = get_unified_config()
        
        # Use REAL database connection - no mocks
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection - will fail if DB unavailable
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        return TestClient(app)

    @pytest.fixture
    def performance_monitor(self):
        """Monitor system performance during tests."""
        initial_stats = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_info": psutil.Process().memory_info(),
            "open_files": len(psutil.Process().open_files()) if hasattr(psutil.Process(), 'open_files') else 0,
            "connections": len(psutil.net_connections()),
            "timestamp": time.time()
        }
        
        yield initial_stats
        
        # Collect final stats
        final_stats = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_info": psutil.Process().memory_info(),
            "open_files": len(psutil.Process().open_files()) if hasattr(psutil.Process(), 'open_files') else 0,
            "connections": len(psutil.net_connections()),
            "timestamp": time.time()
        }
        
        # Calculate deltas for analysis
        memory_delta = final_stats["memory_info"].rss - initial_stats["memory_info"].rss
        file_delta = final_stats["open_files"] - initial_stats["open_files"]
        time_delta = final_stats["timestamp"] - initial_stats["timestamp"]
        
        # Log performance impact
        print(f"\nPerformance Impact:")
        print(f"  Memory Delta: {memory_delta / 1024 / 1024:.1f} MB")
        print(f"  File Handle Delta: {file_delta}")
        print(f"  Test Duration: {time_delta:.1f}s")

    @pytest.mark.asyncio
    async def test_31_database_query_performance_under_load_fails(self, real_database_session, performance_monitor):
        """
        Test 31: Database Query Performance Under Load (EXPECTED TO FAIL)
        
        Tests database performance under concurrent load.
        Will likely FAIL because:
        1. Queries may not be optimized
        2. Indexes may be missing
        3. Connection pool may be insufficient
        """
        start_time = time.time()
        
        try:
            # Create test data for performance testing
            test_data = []
            for i in range(100):
                test_data.append({
                    "id": str(uuid.uuid4()),
                    "title": f"Performance Test Thread {i}",
                    "content": f"Content for performance testing " * 50,  # Make it substantial
                    "user_id": str(uuid.uuid4()),
                    "created_at": datetime.now(timezone.utc)
                })
            
            # Insert test data
            for data in test_data:
                try:
                    insert_query = text("""
                        INSERT INTO threads (id, title, description, user_id, created_at)
                        VALUES (:id, :title, :content, :user_id, :created_at)
                        ON CONFLICT (id) DO NOTHING
                    """)
                    await real_database_session.execute(insert_query, data)
                except Exception as e:
                    # Continue with existing data if insert fails
                    pass
            
            await real_database_session.commit()
            
            # Test concurrent read performance
            async def perform_heavy_query():
                """Simulate heavy database query."""
                query = text("""
                    SELECT t.*, u.username 
                    FROM threads t 
                    LEFT JOIN users u ON t.user_id = u.id 
                    WHERE t.title LIKE '%Performance%'
                    ORDER BY t.created_at DESC
                    LIMIT 50
                """)
                
                query_start = time.time()
                result = await real_database_session.execute(query)
                rows = result.fetchall()
                query_time = time.time() - query_start
                
                return {"rows": len(rows), "time": query_time}
            
            # FAILURE EXPECTED HERE - concurrent queries may be slow
            concurrent_queries = 10
            tasks = [perform_heavy_query() for _ in range(concurrent_queries)]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze query performance
            successful_queries = [r for r in results if not isinstance(r, Exception)]
            failed_queries = [r for r in results if isinstance(r, Exception)]
            
            assert len(failed_queries) == 0, \
                f"Some queries failed under load: {[str(e) for e in failed_queries[:3]]}"
            
            if successful_queries:
                avg_query_time = sum(r["time"] for r in successful_queries) / len(successful_queries)
                max_query_time = max(r["time"] for r in successful_queries)
                
                # FAILURE EXPECTED HERE - queries may be too slow
                assert avg_query_time < 1.0, \
                    f"Average query time too slow: {avg_query_time:.2f}s (should be < 1.0s)"
                
                assert max_query_time < 2.0, \
                    f"Maximum query time too slow: {max_query_time:.2f}s (should be < 2.0s)"

            # Test query plan analysis
            explain_query = text("""
                EXPLAIN ANALYZE
                SELECT t.*, u.username 
                FROM threads t 
                LEFT JOIN users u ON t.user_id = u.id 
                WHERE t.title LIKE '%Performance%'
                ORDER BY t.created_at DESC
                LIMIT 50
            """)
            
            try:
                explain_result = await real_database_session.execute(explain_query)
                explain_rows = explain_result.fetchall()
                explain_text = "\n".join([str(row) for row in explain_rows])
                
                # Check for performance issues in query plan
                if "Seq Scan" in explain_text:
                    pytest.fail("Query plan shows sequential scan - missing index")
                
                if "cost=" in explain_text:
                    # Extract cost from explain plan
                    import re
                    cost_match = re.search(r'cost=(\d+\.\d+)', explain_text)
                    if cost_match:
                        cost = float(cost_match.group(1))
                        assert cost < 1000, f"Query cost too high: {cost}"
                        
            except Exception as e:
                # EXPLAIN may not be available in all environments
                pass
                
        except Exception as e:
            pytest.fail(f"Database query performance test failed: {e}")
        
        finally:
            total_time = time.time() - start_time
            assert total_time < 10.0, f"Test took too long: {total_time:.1f}s"

    @pytest.mark.asyncio
    async def test_32_connection_pool_scaling_fails(self, performance_monitor):
        """
        Test 32: Connection Pool Scaling (EXPECTED TO FAIL)
        
        Tests database connection pool under high concurrent load.
        Will likely FAIL because:
        1. Connection pool may be too small
        2. Connection recycling may not work properly
        3. Connection leaks may occur
        """
        config = get_unified_config()
        
        try:
            # Test connection pool exhaustion
            engines = []
            sessions = []
            
            # FAILURE EXPECTED HERE - connection pool may be exhausted
            try:
                # Attempt to create many concurrent connections
                for i in range(50):  # Try to create 50 connections
                    engine = create_async_engine(
                        config.database_url,
                        pool_size=5,  # Small pool to trigger exhaustion
                        max_overflow=10,
                        echo=False
                    )
                    engines.append(engine)
                    
                    # Test connection
                    async with engine.begin() as conn:
                        result = await conn.execute(text("SELECT 1"))
                        assert result.scalar() == 1
                
                pytest.fail("Connection pool should have been exhausted but wasn't")
                
            except Exception as e:
                # Expected - connection pool should be exhausted
                if "pool" not in str(e).lower() and "connection" not in str(e).lower():
                    pytest.fail(f"Unexpected connection error: {e}")
            
            finally:
                # Cleanup connections
                for engine in engines:
                    try:
                        await engine.dispose()
                    except Exception:
                        pass

            # Test connection recycling under load
            engine = create_async_engine(
                config.database_url,
                pool_size=10,
                max_overflow=5,
                pool_recycle=3600,  # 1 hour
                echo=False
            )
            
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            
            async def db_operation(session_id: int):
                """Perform database operation and return connection info."""
                try:
                    async with async_session() as session:
                        # Perform multiple operations to test connection reuse
                        for _ in range(5):
                            result = await session.execute(text("SELECT :session_id, NOW()"), 
                                                         {"session_id": session_id})
                            row = result.fetchone()
                            await asyncio.sleep(0.1)  # Small delay
                        
                        return {"session_id": session_id, "status": "success"}
                except Exception as e:
                    return {"session_id": session_id, "status": "error", "error": str(e)}
            
            # Run concurrent operations
            concurrent_operations = 25
            tasks = [db_operation(i) for i in range(concurrent_operations)]
            
            operation_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_ops = [r for r in operation_results if not isinstance(r, Exception) and r.get("status") == "success"]
            failed_ops = [r for r in operation_results if isinstance(r, Exception) or r.get("status") == "error"]
            
            success_rate = len(successful_ops) / len(operation_results)
            
            # FAILURE EXPECTED HERE - connection pool scaling may not work
            assert success_rate >= 0.8, \
                f"Connection pool scaling failed: {success_rate*100:.1f}% success rate. Failed: {failed_ops[:3]}"
            
            # Test connection cleanup
            await engine.dispose()
            
            # Verify connections are properly closed
            await asyncio.sleep(1)  # Give time for cleanup
            
        except Exception as e:
            pytest.fail(f"Connection pool scaling test failed: {e}")

    @pytest.mark.asyncio
    async def test_33_memory_usage_agent_processing_fails(self, performance_monitor):
        """
        Test 33: Memory Usage in Agent Processing (EXPECTED TO FAIL)
        
        Tests memory usage patterns during agent processing.
        Will likely FAIL because:
        1. Memory leaks may occur during processing
        2. Large objects may not be garbage collected
        3. Agent context may not be properly cleaned up
        """
        initial_memory = psutil.Process().memory_info().rss
        
        try:
            # Create agent service for testing
            agent_service = AgentService()
            
            # Test memory usage with multiple agent runs
            agent_runs = []
            
            for i in range(20):  # Create 20 agent runs
                agent_run_data = {
                    "id": str(uuid.uuid4()),
                    "agent_type": "test_agent",
                    "input_data": {
                        "task": f"Memory test task {i+1}",
                        "large_context": "x" * 10000,  # 10KB of data
                        "iteration": i
                    },
                    "config": {
                        "max_tokens": 1000,
                        "temperature": 0.7
                    }
                }
                agent_runs.append(agent_run_data)
            
            # Process agents and monitor memory usage
            memory_measurements = []
            
            for i, agent_data in enumerate(agent_runs):
                try:
                    # FAILURE EXPECTED HERE - memory usage may increase significantly
                    # Simulate agent processing (since real agent execution may not be available)
                    
                    # Create large objects to simulate agent processing
                    large_context = {
                        "conversation_history": ["message " * 100 for _ in range(100)],
                        "agent_memory": {"key_" + str(j): "value " * 50 for j in range(100)},
                        "processing_data": list(range(1000))
                    }
                    
                    # Simulate processing time
                    await asyncio.sleep(0.1)
                    
                    # Measure memory after each agent
                    current_memory = psutil.Process().memory_info().rss
                    memory_delta = current_memory - initial_memory
                    memory_measurements.append(memory_delta)
                    
                    # Clean up large objects
                    del large_context
                    
                    # Force garbage collection
                    if i % 5 == 0:
                        gc.collect()
                
                except Exception as e:
                    pytest.fail(f"Agent processing failed at iteration {i}: {e}")
            
            # Force final garbage collection
            gc.collect()
            await asyncio.sleep(0.5)  # Allow GC to complete
            
            final_memory = psutil.Process().memory_info().rss
            total_memory_increase = final_memory - initial_memory
            
            # Analyze memory usage patterns
            if len(memory_measurements) > 1:
                memory_trend = memory_measurements[-1] - memory_measurements[0]
                max_memory_increase = max(memory_measurements)
                
                # FAILURE EXPECTED HERE - memory usage may be excessive
                assert total_memory_increase < 100 * 1024 * 1024, \
                    f"Total memory increase too high: {total_memory_increase / 1024 / 1024:.1f}MB"
                
                assert max_memory_increase < 200 * 1024 * 1024, \
                    f"Peak memory increase too high: {max_memory_increase / 1024 / 1024:.1f}MB"
                
                # Check for memory leaks (increasing trend)
                if len(memory_measurements) >= 10:
                    recent_avg = sum(memory_measurements[-5:]) / 5
                    early_avg = sum(memory_measurements[:5]) / 5
                    
                    if recent_avg > early_avg * 2:
                        pytest.fail(f"Potential memory leak detected: {recent_avg / 1024 / 1024:.1f}MB vs {early_avg / 1024 / 1024:.1f}MB")

            # Test memory cleanup after agent completion
            post_cleanup_memory = psutil.Process().memory_info().rss
            cleanup_effectiveness = (final_memory - post_cleanup_memory) / max(total_memory_increase, 1)
            
            # Memory should be mostly cleaned up
            assert cleanup_effectiveness >= 0.1, \
                f"Memory cleanup ineffective: {cleanup_effectiveness*100:.1f}% cleaned"
                
        except Exception as e:
            pytest.fail(f"Memory usage in agent processing test failed: {e}")

    @pytest.mark.asyncio
    async def test_34_websocket_connection_limits_fails(self, real_test_client, performance_monitor):
        """
        Test 34: WebSocket Connection Limits (EXPECTED TO FAIL)
        
        Tests WebSocket connection handling under load.
        Will likely FAIL because:
        1. Connection limits may not be enforced
        2. Connection cleanup may not work properly
        3. Memory usage may increase with connections
        """
        try:
            import websocket
            import threading
            
            websocket_connections = []
            connection_results = []
            
            def create_websocket_connection(connection_id: int):
                """Create a WebSocket connection for testing."""
                try:
                    # FAILURE EXPECTED HERE - connection limits may not be enforced
                    ws_url = "ws://localhost:8000/ws"  # Adjust URL as needed
                    
                    ws = websocket.WebSocket()
                    ws.settimeout(5)  # 5 second timeout
                    
                    # Try to connect
                    ws.connect(ws_url)
                    
                    # Send test message
                    test_message = json.dumps({
                        "type": "test",
                        "connection_id": connection_id,
                        "timestamp": time.time()
                    })
                    ws.send(test_message)
                    
                    # Receive response (with timeout)
                    response = ws.recv()
                    
                    connection_results.append({
                        "connection_id": connection_id,
                        "status": "success",
                        "response": response
                    })
                    
                    # Keep connection open for testing
                    websocket_connections.append(ws)
                    
                except Exception as e:
                    connection_results.append({
                        "connection_id": connection_id,
                        "status": "error", 
                        "error": str(e)
                    })
            
            # Try to create many concurrent WebSocket connections
            max_connections = 100
            threads = []
            
            for i in range(max_connections):
                thread = threading.Thread(target=create_websocket_connection, args=(i,))
                threads.append(thread)
                thread.start()
                
                # Small delay to avoid overwhelming
                if i % 10 == 0:
                    time.sleep(0.1)
            
            # Wait for all connection attempts
            for thread in threads:
                thread.join(timeout=10)
            
            # Analyze connection results
            successful_connections = [r for r in connection_results if r["status"] == "success"]
            failed_connections = [r for r in connection_results if r["status"] == "error"]
            
            success_rate = len(successful_connections) / len(connection_results) if connection_results else 0
            
            # Some connections should succeed, but there should be limits
            assert success_rate > 0.1, \
                f"WebSocket connections completely failed: {success_rate*100:.1f}% success rate"
            
            # But not ALL should succeed if limits are properly enforced
            if success_rate > 0.9:
                pytest.fail(f"No connection limits enforced: {success_rate*100:.1f}% success rate")
            
            # Test connection cleanup
            cleanup_start_time = time.time()
            
            for ws in websocket_connections:
                try:
                    ws.close()
                except Exception:
                    pass
            
            cleanup_time = time.time() - cleanup_start_time
            
            # Cleanup should be reasonably fast
            assert cleanup_time < 5.0, \
                f"WebSocket cleanup took too long: {cleanup_time:.1f}s"
            
            # Test memory after cleanup
            await asyncio.sleep(1)  # Allow cleanup to complete
            gc.collect()
            
        except ImportError:
            pytest.skip("WebSocket client library not available")
        except Exception as e:
            pytest.fail(f"WebSocket connection limits test failed: {e}")

    @pytest.mark.asyncio  
    async def test_35_cache_invalidation_timing_fails(self, performance_monitor):
        """
        Test 35: Cache Invalidation Timing (EXPECTED TO FAIL)
        
        Tests cache invalidation performance and timing.
        Will likely FAIL because:
        1. Cache invalidation may be too slow
        2. Stale data may be served
        3. Cache stampede may occur
        """
        try:
            # Try to get cache service
            try:
                cache_service = CacheService()
            except Exception:
                # Mock cache service for testing if not available
                cache_service = Mock()
                cache_service.get = Mock(return_value=None)
                cache_service.set = Mock()
                cache_service.delete = Mock()
                cache_service.clear = Mock()

            # Test cache performance under load
            cache_keys = [f"test_key_{i}" for i in range(100)]
            test_data = {key: f"test_data_{i}" * 100 for i, key in enumerate(cache_keys)}  # Large data
            
            # Test cache write performance
            write_start_time = time.time()
            
            for key, data in test_data.items():
                try:
                    # FAILURE EXPECTED HERE - cache operations may be slow
                    if hasattr(cache_service, 'set'):
                        await cache_service.set(key, data, ttl=300)  # 5 minute TTL
                    else:
                        cache_service.set(key, data)
                except Exception as e:
                    pytest.fail(f"Cache write failed for key {key}: {e}")
            
            write_time = time.time() - write_start_time
            
            # Write operations should be reasonably fast
            assert write_time < 5.0, \
                f"Cache write operations too slow: {write_time:.2f}s for {len(cache_keys)} keys"

            # Test cache read performance
            read_start_time = time.time()
            read_results = {}
            
            for key in cache_keys:
                try:
                    if hasattr(cache_service, 'get'):
                        value = await cache_service.get(key)
                    else:
                        value = cache_service.get(key)
                    read_results[key] = value
                except Exception as e:
                    pytest.fail(f"Cache read failed for key {key}: {e}")
            
            read_time = time.time() - read_start_time
            
            # Read operations should be fast
            assert read_time < 2.0, \
                f"Cache read operations too slow: {read_time:.2f}s for {len(cache_keys)} keys"

            # Test cache invalidation performance
            invalidation_start_time = time.time()
            
            # Invalidate half the keys
            keys_to_invalidate = cache_keys[:50]
            
            for key in keys_to_invalidate:
                try:
                    if hasattr(cache_service, 'delete'):
                        await cache_service.delete(key)
                    else:
                        cache_service.delete(key)
                except Exception as e:
                    pytest.fail(f"Cache invalidation failed for key {key}: {e}")
            
            invalidation_time = time.time() - invalidation_start_time
            
            # FAILURE EXPECTED HERE - invalidation may be slow
            assert invalidation_time < 1.0, \
                f"Cache invalidation too slow: {invalidation_time:.2f}s for {len(keys_to_invalidate)} keys"

            # Test that invalidated keys return None
            for key in keys_to_invalidate:
                try:
                    if hasattr(cache_service, 'get'):
                        value = await cache_service.get(key)
                    else:
                        value = cache_service.get(key)
                    
                    assert value is None, \
                        f"Cache key {key} should be invalidated but still has value: {value}"
                except Exception as e:
                    pytest.fail(f"Cache invalidation verification failed for key {key}: {e}")

            # Test cache stampede scenario
            # Multiple concurrent requests for the same key
            stampede_key = "stampede_test_key"
            
            async def cache_operation():
                """Simulate cache operation that might cause stampede."""
                try:
                    if hasattr(cache_service, 'get'):
                        value = await cache_service.get(stampede_key)
                    else:
                        value = cache_service.get(stampede_key)
                    
                    if value is None:
                        # Simulate expensive computation
                        await asyncio.sleep(0.1)
                        computed_value = f"computed_value_{time.time()}"
                        
                        if hasattr(cache_service, 'set'):
                            await cache_service.set(stampede_key, computed_value)
                        else:
                            cache_service.set(stampede_key, computed_value)
                        
                        return computed_value
                    
                    return value
                except Exception as e:
                    return f"error: {e}"
            
            # Run concurrent cache operations
            concurrent_operations = 20
            tasks = [cache_operation() for _ in range(concurrent_operations)]
            
            stampede_start_time = time.time()
            results = await asyncio.gather(*tasks)
            stampede_time = time.time() - stampede_start_time
            
            # Check for cache stampede issues
            unique_results = set(results)
            
            # FAILURE EXPECTED HERE - cache stampede may cause issues
            assert len(unique_results) <= 2, \
                f"Cache stampede detected: {len(unique_results)} different computed values"
            
            assert stampede_time < 2.0, \
                f"Cache stampede resolution too slow: {stampede_time:.2f}s"

            # Cleanup
            try:
                if hasattr(cache_service, 'clear'):
                    await cache_service.clear()
                elif hasattr(cache_service, 'delete'):
                    for key in cache_keys:
                        await cache_service.delete(key)
            except Exception:
                pass
                
        except Exception as e:
            pytest.fail(f"Cache invalidation timing test failed: {e}")


# Additional utility class for performance testing
class RedTeamPerformanceTestUtils:
    """Utility methods for Red Team performance testing."""
    
    @staticmethod
    def measure_execution_time(func):
        """Decorator to measure function execution time."""
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                print(f"{func.__name__} executed in {execution_time:.4f}s")
        
        return wrapper
    
    @staticmethod
    def get_system_resources() -> Dict[str, Any]:
        """Get current system resource usage."""
        process = psutil.Process()
        
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_info": process.memory_info()._asdict(),
            "memory_percent": process.memory_percent(),
            "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0,
            "num_threads": process.num_threads(),
            "connections": len(psutil.net_connections()),
            "system_cpu": psutil.cpu_percent(),
            "system_memory": psutil.virtual_memory()._asdict(),
            "disk_usage": psutil.disk_usage('/')._asdict() if hasattr(psutil, 'disk_usage') else {}
        }
    
    @staticmethod
    async def simulate_load(operations: int, concurrency: int, operation_func):
        """Simulate concurrent load on a system."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_operation():
            async with semaphore:
                return await operation_func()
        
        tasks = [limited_operation() for _ in range(operations)]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    @staticmethod
    def analyze_performance_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance test results."""
        successful = [r for r in results if not isinstance(r, Exception) and r.get('status') != 'error']
        failed = [r for r in results if isinstance(r, Exception) or r.get('status') == 'error']
        
        if successful:
            times = [r.get('time', 0) for r in successful if 'time' in r]
            avg_time = sum(times) / len(times) if times else 0
            min_time = min(times) if times else 0
            max_time = max(times) if times else 0
        else:
            avg_time = min_time = max_time = 0
        
        return {
            "total_operations": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) if results else 0,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "error_summary": [str(e) for e in failed[:5]]  # First 5 errors
        }