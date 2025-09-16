"""
Real Redis Connectivity Tests - NO MOCKS

Tests actual Redis operations, connection pooling, caching behavior,
and error handling with real Redis instances.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Performance & Risk Reduction  
- Value Impact: Ensures caching and session management work correctly
- Strategic Impact: Maintains system performance and prevents cache failures

This test suite uses:
- Real Redis connections and operations
- Actual cache expiration and TTL behavior
- Real connection pooling and cluster scenarios
- Comprehensive error handling with real Redis errors
- Performance testing under load
"""
import asyncio
import pytest
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import psutil
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from shared.isolated_environment import IsolatedEnvironment
from test_framework.environment_isolation import get_test_env_manager
logger = logging.getLogger(__name__)

class RealRedisTestHelper:
    """Helper for real Redis testing operations."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        self.connection_pool = None
        self.test_keys = []

    async def connect(self):
        """Connect to Redis with real connection."""
        self.redis_client = await aioredis.from_url(self.redis_url, encoding='utf-8', decode_responses=True, socket_connect_timeout=5.0, socket_timeout=5.0, retry_on_timeout=True, health_check_interval=30)
        await redis_client.ping()
        logger.info(f'Connected to Redis: {self.redis_url}')

    async def disconnect(self):
        """Disconnect from Redis and cleanup."""
        if self.redis_client:
            if self.test_keys:
                try:
                    await redis_client.delete(*self.test_keys)
                    logger.info(f'Cleaned up {len(self.test_keys)} test keys')
                except Exception as e:
                    logger.warning(f'Cleanup failed: {e}')
            await redis_client.close()
            self.redis_client = None

    def track_key(self, key: str):
        """Track key for cleanup."""
        if key not in self.test_keys:
            self.test_keys.append(key)

    async def get_redis_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        info = await redis_client.info()
        return {'redis_version': info.get('redis_version'), 'connected_clients': info.get('connected_clients'), 'used_memory': info.get('used_memory'), 'used_memory_human': info.get('used_memory_human'), 'keyspace_hits': info.get('keyspace_hits', 0), 'keyspace_misses': info.get('keyspace_misses', 0), 'total_commands_processed': info.get('total_commands_processed', 0)}

    async def test_basic_operations(self) -> Dict[str, bool]:
        """Test basic Redis operations."""
        results = {}
        test_key = f'test:basic:{int(time.time())}'
        self.track_key(test_key)
        set_result = await redis_client.set(test_key, 'test_value')
        results['set'] = set_result is True
        get_result = await redis_client.get(test_key)
        results['get'] = get_result == 'test_value'
        exists_result = await redis_client.exists(test_key)
        results['exists'] = exists_result == 1
        del_result = await redis_client.delete(test_key)
        results['delete'] = del_result == 1
        return results

    async def test_data_structures(self) -> Dict[str, bool]:
        """Test Redis data structures."""
        results = {}
        base_key = f'test:structures:{int(time.time())}'
        hash_key = f'{base_key}:hash'
        self.track_key(hash_key)
        await redis_client.hset(hash_key, mapping={'field1': 'value1', 'field2': 'value2', 'field3': json.dumps({'nested': 'data'})})
        hash_result = await redis_client.hgetall(hash_key)
        results['hash'] = len(hash_result) == 3 and hash_result.get('field1') == 'value1'
        list_key = f'{base_key}:list'
        self.track_key(list_key)
        await redis_client.lpush(list_key, 'item1', 'item2', 'item3')
        list_length = await redis_client.llen(list_key)
        list_items = await redis_client.lrange(list_key, 0, -1)
        results['list'] = list_length == 3 and 'item1' in list_items
        set_key = f'{base_key}:set'
        self.track_key(set_key)
        await redis_client.sadd(set_key, 'member1', 'member2', 'member3')
        set_size = await redis_client.scard(set_key)
        is_member = await redis_client.sismember(set_key, 'member1')
        results['set'] = set_size == 3 and is_member
        zset_key = f'{base_key}:zset'
        self.track_key(zset_key)
        await redis_client.zadd(zset_key, {'item1': 1.0, 'item2': 2.0, 'item3': 3.0})
        zset_size = await redis_client.zcard(zset_key)
        top_item = await redis_client.zrange(zset_key, -1, -1)
        results['zset'] = zset_size == 3 and top_item == ['item3']
        return results

    async def test_expiration_and_ttl(self) -> Dict[str, bool]:
        """Test Redis key expiration and TTL."""
        results = {}
        expire_key = f'test:expire:{int(time.time())}'
        self.track_key(expire_key)
        await redis_client.set(expire_key, 'expire_test')
        await redis_client.expire(expire_key, 2)
        ttl = await redis_client.ttl(expire_key)
        results['ttl_set'] = 1 <= ttl <= 2
        await asyncio.sleep(2.5)
        expired_value = await redis_client.get(expire_key)
        results['expiration'] = expired_value is None
        setex_key = f'test:setex:{int(time.time())}'
        self.track_key(setex_key)
        await redis_client.setex(setex_key, 1, 'setex_test')
        immediate_value = await redis_client.get(setex_key)
        await asyncio.sleep(1.5)
        expired_value = await redis_client.get(setex_key)
        results['setex'] = immediate_value == 'setex_test' and expired_value is None
        return results

    async def simulate_cache_operations(self, num_operations: int=100) -> Dict[str, Any]:
        """Simulate realistic cache operations."""
        start_time = time.time()
        cache_hits = 0
        cache_misses = 0
        operations_completed = 0
        base_key = f'cache:sim:{int(time.time())}'
        for i in range(num_operations):
            key = f'{base_key}:item:{i % 20}'
            self.track_key(key)
            cached_value = await redis_client.get(key)
            if cached_value is not None:
                cache_hits += 1
            else:
                cache_misses += 1
                cache_data = {'id': i, 'data': f'cached_data_item_{i}', 'timestamp': time.time()}
                await redis_client.setex(key, 30, json.dumps(cache_data))
            operations_completed += 1
        total_time = time.time() - start_time
        return {'operations_completed': operations_completed, 'cache_hits': cache_hits, 'cache_misses': cache_misses, 'hit_ratio': cache_hits / operations_completed if operations_completed > 0 else 0, 'total_time': total_time, 'ops_per_second': operations_completed / total_time if total_time > 0 else 0}

class RealRedisConnectionPoolTest:
    """Test Redis connection pooling behavior."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.connection_pools = []

    async def create_connection_pool(self, max_connections: int=10):
        """Create Redis connection pool."""
        pool = aioredis.ConnectionPool.from_url(self.redis_url, max_connections=max_connections, retry_on_timeout=True, socket_connect_timeout=5.0)
        self.connection_pools.append(pool)
        return pool

    async def test_concurrent_connections(self, pool, num_concurrent: int=5):
        """Test concurrent Redis operations through pool."""

        async def redis_operation(operation_id: int):
            """Single Redis operation."""
            redis_client = await get_redis_client()
            try:
                key = f'concurrent:test:{operation_id}:{int(time.time())}'
                await redis_client.set(key, f'data_{operation_id}')
                value = await redis_client.get(key)
                await redis_client.delete(key)
                return (operation_id, value == f'data_{operation_id}')
            except Exception as e:
                logger.error(f'Concurrent operation {operation_id} failed: {e}')
                return (operation_id, False)
        tasks = [redis_operation(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_operations = 0
        failed_operations = 0
        for result in results:
            if isinstance(result, Exception):
                failed_operations += 1
            else:
                operation_id, success = result
                if success:
                    successful_operations += 1
                else:
                    failed_operations += 1
        return {'successful_operations': successful_operations, 'failed_operations': failed_operations, 'success_rate': successful_operations / num_concurrent}

    async def cleanup(self):
        """Cleanup connection pools."""
        for pool in self.connection_pools:
            await pool.disconnect()

@pytest.fixture
async def redis_test_helper():
    """Fixture providing Redis test helper."""
    redis_url = 'redis://localhost:6379/1'
    helper = RealRedisTestHelper(redis_url)
    await helper.connect()
    yield helper
    await helper.disconnect()

@pytest.fixture
async def redis_connection_pool_test():
    """Fixture providing Redis connection pool test helper."""
    redis_url = 'redis://localhost:6379/1'
    pool_test = RealRedisConnectionPoolTest(redis_url)
    yield pool_test
    await pool_test.cleanup()

class RealRedisBasicOperationsTests:
    """Test basic Redis operations with real Redis instance."""

    @pytest.mark.asyncio
    async def test_redis_connection_and_ping(self, redis_test_helper):
        """
        Test Redis connection establishment and ping.
        MUST PASS: Should successfully connect to Redis and respond to ping.
        """
        redis_info = await redis_test_helper.get_redis_info()
        logger.info(f"Connected to Redis version: {redis_info.get('redis_version')}")
        logger.info(f"Redis memory usage: {redis_info.get('used_memory_human')}")
        ping_result = await redis_client.ping()
        assert ping_result is True, 'Redis ping should return True'
        assert redis_info.get('redis_version') is not None, 'Should have Redis version info'

    @pytest.mark.asyncio
    async def test_redis_basic_string_operations(self, redis_test_helper):
        """
        Test Redis basic string operations.
        MUST PASS: Should perform SET, GET, EXISTS, DELETE operations.
        """
        basic_ops_results = await redis_test_helper.test_basic_operations()
        logger.info(f'Basic operations results: {basic_ops_results}')
        assert basic_ops_results['set'] is True, 'SET operation should succeed'
        assert basic_ops_results['get'] is True, 'GET operation should return correct value'
        assert basic_ops_results['exists'] is True, 'EXISTS should detect key presence'
        assert basic_ops_results['delete'] is True, 'DELETE should remove key'

    @pytest.mark.asyncio
    async def test_redis_data_structures(self, redis_test_helper):
        """
        Test Redis data structures (hash, list, set, sorted set).
        MUST PASS: Should handle all Redis data types correctly.
        """
        structures_results = await redis_test_helper.test_data_structures()
        logger.info(f'Data structures results: {structures_results}')
        assert structures_results['hash'] is True, 'Hash operations should work correctly'
        assert structures_results['list'] is True, 'List operations should work correctly'
        assert structures_results['set'] is True, 'Set operations should work correctly'
        assert structures_results['zset'] is True, 'Sorted set operations should work correctly'

    @pytest.mark.asyncio
    async def test_redis_expiration_and_ttl(self, redis_test_helper):
        """
        Test Redis key expiration and TTL functionality.
        MUST PASS: Should handle key expiration correctly.
        """
        ttl_results = await redis_test_helper.test_expiration_and_ttl()
        logger.info(f'TTL and expiration results: {ttl_results}')
        assert ttl_results['ttl_set'] is True, 'TTL should be set correctly'
        assert ttl_results['expiration'] is True, 'Key should expire after TTL'
        assert ttl_results['setex'] is True, 'SETEX should set key with expiration'

    @pytest.mark.asyncio
    async def test_redis_atomic_operations(self, redis_test_helper):
        """
        Test Redis atomic operations (INCR, DECR, etc.).
        MUST PASS: Should handle atomic operations correctly.
        """
        counter_key = f'test:counter:{int(time.time())}'
        redis_test_helper.track_key(counter_key)
        incr_result = await redis_client.incr(counter_key)
        assert incr_result == 1, 'First INCR should return 1'
        for i in range(5):
            incr_result = await redis_client.incr(counter_key)
            assert incr_result == i + 2, f'INCR should return {i + 2}'
        decr_result = await redis_client.decr(counter_key)
        assert decr_result == 5, 'DECR should return 5'
        incrby_result = await redis_client.incrby(counter_key, 10)
        assert incrby_result == 15, 'INCRBY should return 15'
        logger.info('Atomic operations test completed successfully')

class RealRedisCacheOperationsTests:
    """Test Redis caching operations and patterns."""

    @pytest.mark.asyncio
    async def test_redis_cache_simulation(self, redis_test_helper):
        """
        Test Redis cache operations with realistic patterns.
        MUST PASS: Should demonstrate effective caching behavior.
        """
        cache_results = await redis_test_helper.simulate_cache_operations(num_operations=50)
        logger.info(f'Cache simulation results:')
        logger.info(f"  Operations completed: {cache_results['operations_completed']}")
        logger.info(f"  Cache hits: {cache_results['cache_hits']}")
        logger.info(f"  Cache misses: {cache_results['cache_misses']}")
        logger.info(f"  Hit ratio: {cache_results['hit_ratio']:.2%}")
        logger.info(f"  Operations per second: {cache_results['ops_per_second']:.2f}")
        assert cache_results['operations_completed'] == 50, 'Should complete all operations'
        assert cache_results['cache_hits'] > 0, 'Should have cache hits due to repeated keys'
        assert cache_results['cache_misses'] > 0, 'Should have cache misses for new keys'
        assert cache_results['ops_per_second'] > 10, 'Should achieve reasonable throughput'
        assert cache_results['hit_ratio'] > 0.3, 'Should have reasonable cache hit ratio'

    @pytest.mark.asyncio
    async def test_redis_json_caching(self, redis_test_helper):
        """
        Test Redis JSON object caching.
        MUST PASS: Should cache and retrieve JSON objects correctly.
        """
        cache_key = f'test:json:{int(time.time())}'
        redis_test_helper.track_key(cache_key)
        test_object = {'user_id': 12345, 'profile': {'name': 'Test User', 'email': 'test@example.com', 'settings': {'theme': 'dark', 'notifications': True}}, 'metadata': {'created_at': datetime.now(timezone.utc).isoformat(), 'version': '1.0.0', 'tags': ['test', 'cache', 'json']}}
        await redis_client.setex(cache_key, 300, json.dumps(test_object))
        cached_json = await redis_client.get(cache_key)
        assert cached_json is not None, 'Should retrieve cached JSON'
        cached_object = json.loads(cached_json)
        assert cached_object['user_id'] == test_object['user_id'], 'User ID should match'
        assert cached_object['profile']['name'] == test_object['profile']['name'], 'Profile name should match'
        assert cached_object['metadata']['version'] == test_object['metadata']['version'], 'Version should match'
        assert len(cached_object['metadata']['tags']) == 3, 'Should have 3 tags'
        ttl = await redis_client.ttl(cache_key)
        assert 250 < ttl <= 300, f'TTL should be close to 300 seconds: {ttl}'
        logger.info('JSON caching test completed successfully')

    @pytest.mark.asyncio
    async def test_redis_session_management(self, redis_test_helper):
        """
        Test Redis for session management patterns.
        MUST PASS: Should handle session data correctly.
        """
        session_id = f'session:{int(time.time())}'
        redis_test_helper.track_key(session_id)
        session_data = {'user_id': 'user_123', 'login_time': time.time(), 'permissions': ['read', 'write'], 'preferences': {'theme': 'light', 'language': 'en'}}
        await redis_client.hset(session_id, mapping={'user_id': session_data['user_id'], 'login_time': str(session_data['login_time']), 'permissions': json.dumps(session_data['permissions']), 'preferences': json.dumps(session_data['preferences'])})
        await redis_client.expire(session_id, 1800)
        retrieved_session = await redis_client.hgetall(session_id)
        assert retrieved_session['user_id'] == session_data['user_id'], 'User ID should match'
        assert float(retrieved_session['login_time']) == session_data['login_time'], 'Login time should match'
        permissions = json.loads(retrieved_session['permissions'])
        assert permissions == session_data['permissions'], 'Permissions should match'
        await redis_client.hset(session_id, 'last_activity', str(time.time()))
        await redis_client.expire(session_id, 1800)
        updated_session = await redis_client.hgetall(session_id)
        assert 'last_activity' in updated_session, 'Should have last_activity field'
        logger.info('Session management test completed successfully')

class RealRedisConnectionPoolingTests:
    """Test Redis connection pooling and concurrent operations."""

    @pytest.mark.asyncio
    async def test_redis_connection_pool_creation(self, redis_connection_pool_test):
        """
        Test Redis connection pool creation and configuration.
        MUST PASS: Should create connection pool successfully.
        """
        pool = await redis_connection_pool_test.create_connection_pool(max_connections=5)
        redis_client = await get_redis_client()
        ping_result = await redis_client.ping()
        assert ping_result is True, 'Should ping successfully through pool'
        test_key = f'pool:test:{int(time.time())}'
        await redis_client.set(test_key, 'pool_test_value')
        value = await redis_client.get(test_key)
        await redis_client.delete(test_key)
        assert value == 'pool_test_value', 'Should perform operations through pool'
        logger.info('Connection pool creation test successful')

    @pytest.mark.asyncio
    async def test_redis_concurrent_operations_through_pool(self, redis_connection_pool_test):
        """
        Test concurrent Redis operations through connection pool.
        MUST PASS: Should handle concurrent operations efficiently.
        """
        pool = await redis_connection_pool_test.create_connection_pool(max_connections=10)
        concurrent_results = await redis_connection_pool_test.test_concurrent_connections(pool, num_concurrent=8)
        logger.info(f'Concurrent operations results:')
        logger.info(f"  Successful: {concurrent_results['successful_operations']}")
        logger.info(f"  Failed: {concurrent_results['failed_operations']}")
        logger.info(f"  Success rate: {concurrent_results['success_rate']:.2%}")
        assert concurrent_results['successful_operations'] >= 6, 'Most operations should succeed'
        assert concurrent_results['success_rate'] >= 0.75, 'Should have high success rate'

    @pytest.mark.asyncio
    async def test_redis_pool_under_load(self, redis_connection_pool_test):
        """
        Test Redis connection pool under sustained load.
        MUST PASS: Should maintain performance under load.
        """
        pool = await redis_connection_pool_test.create_connection_pool(max_connections=15)

        async def load_test_worker(worker_id: int, operations: int=20):
            """Worker that performs multiple Redis operations."""
            redis_client = await get_redis_client()
            operations_completed = 0
            for i in range(operations):
                try:
                    key = f'load:test:{worker_id}:{i}:{int(time.time())}'
                    await redis_client.set(key, f'worker_{worker_id}_operation_{i}')
                    value = await redis_client.get(key)
                    await redis_client.expire(key, 60)
                    await redis_client.delete(key)
                    operations_completed += 1
                except Exception as e:
                    logger.warning(f'Load test worker {worker_id} operation {i} failed: {e}')
            return (worker_id, operations_completed)
        num_workers = 10
        operations_per_worker = 15
        total_expected_operations = num_workers * operations_per_worker
        start_time = time.time()
        tasks = [load_test_worker(i, operations_per_worker) for i in range(num_workers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        successful_operations = 0
        successful_workers = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(f'Load test worker failed: {result}')
            else:
                worker_id, operations_completed = result
                successful_operations += operations_completed
                if operations_completed == operations_per_worker:
                    successful_workers += 1
        ops_per_second = successful_operations / total_time if total_time > 0 else 0
        logger.info(f'Load test results:')
        logger.info(f'  Workers: {num_workers}')
        logger.info(f'  Total time: {total_time:.2f} seconds')
        logger.info(f'  Successful operations: {successful_operations}/{total_expected_operations}')
        logger.info(f'  Successful workers: {successful_workers}/{num_workers}')
        logger.info(f'  Operations per second: {ops_per_second:.2f}')
        assert successful_operations >= total_expected_operations * 0.8, 'Should complete most operations successfully'
        assert successful_workers >= num_workers * 0.7, 'Most workers should complete successfully'
        assert ops_per_second > 50, f'Should achieve reasonable throughput: {ops_per_second:.2f} ops/sec'
        assert total_time < 30, f'Load test should complete in reasonable time: {total_time:.2f}s'

class RealRedisErrorHandlingAndRecoveryTests:
    """Test Redis error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self, redis_test_helper):
        """
        Test Redis connection error handling.
        MUST PASS: Should handle connection errors gracefully.
        """
        try:
            invalid_key = 'test:invalid:' + 'x' * 1000000
            await redis_client.set(invalid_key, 'test')
        except Exception as e:
            logger.info(f'Caught expected error: {e}')
        ping_result = await redis_client.ping()
        assert ping_result is True, 'Connection should remain valid after error'
        test_key = f'test:recovery:{int(time.time())}'
        redis_test_helper.track_key(test_key)
        await redis_client.set(test_key, 'recovery_test')
        value = await redis_client.get(test_key)
        assert value == 'recovery_test', 'Should work normally after error handling'
        logger.info('Redis error handling test completed')

    @pytest.mark.asyncio
    async def test_redis_timeout_handling(self, redis_test_helper):
        """
        Test Redis timeout handling.
        MUST PASS: Should handle timeouts appropriately.
        """
        short_timeout_client = await aioredis.from_url(redis_test_helper.redis_url, socket_timeout=0.1, encoding='utf-8', decode_responses=True)
        timeout_occurred = False
        try:
            await short_timeout_client.set('timeout_test', 'x' * 100000)
        except (asyncio.TimeoutError, aioredis.TimeoutError) as e:
            timeout_occurred = True
            logger.info(f'Timeout occurred as expected: {e}')
        except Exception as e:
            logger.info(f'Other error during timeout test: {e}')
        finally:
            await short_timeout_client.close()
        ping_result = await redis_client.ping()
        assert ping_result is True, 'Original connection should remain valid'
        logger.info(f'Timeout handling test completed: timeout_occurred={timeout_occurred}')

    @pytest.mark.asyncio
    async def test_redis_memory_usage_monitoring(self, redis_test_helper):
        """
        Test Redis memory usage and monitoring.
        MUST PASS: Should monitor Redis memory usage effectively.
        """
        initial_info = await redis_test_helper.get_redis_info()
        initial_memory = initial_info.get('used_memory', 0)
        keys_created = []
        large_data = 'x' * 10000
        for i in range(50):
            key = f'memory:test:{i}:{int(time.time())}'
            await redis_client.set(key, large_data)
            keys_created.append(key)
            redis_test_helper.track_key(key)
        after_creation_info = await redis_test_helper.get_redis_info()
        after_creation_memory = after_creation_info.get('used_memory', 0)
        memory_increase = after_creation_memory - initial_memory
        logger.info(f'Memory usage test:')
        logger.info(f"  Initial memory: {initial_info.get('used_memory_human')}")
        logger.info(f"  After creation: {after_creation_info.get('used_memory_human')}")
        logger.info(f'  Memory increase: {memory_increase} bytes')
        logger.info(f'  Keys created: {len(keys_created)}')
        assert memory_increase > 100000, f'Should have increased memory usage: {memory_increase} bytes'
        deleted_count = await redis_client.delete(*keys_created)
        assert deleted_count == len(keys_created), 'Should delete all created keys'
        final_info = await redis_test_helper.get_redis_info()
        logger.info(f"  Final memory: {final_info.get('used_memory_human')}")
        logger.info(f"  Total commands processed: {final_info.get('total_commands_processed')}")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')