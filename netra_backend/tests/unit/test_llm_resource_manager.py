"""Tests for LLM resource manager."""

import asyncio
import pytest
from datetime import datetime, timedelta

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.llm.resource_manager import (

# Add project root to path
    RequestPool, RequestBatcher, CacheManager, ResourceMonitor
)


class TestRequestPool:
    """Test request pool functionality."""
    
    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        """Test concurrent request limiting."""
        pool = RequestPool(max_concurrent=2, requests_per_minute=100)
        
        async def mock_request(delay: float):
            async with pool:
                await asyncio.sleep(delay)
                return datetime.now()
        
        # Start 3 requests, only 2 should run concurrently
        tasks = [mock_request(0.1) for _ in range(3)]
        start = datetime.now()
        results = await asyncio.gather(*tasks)
        duration = (results[-1] - start).total_seconds()
        
        # Third request should wait for one of first two
        assert duration >= 0.15  # At least 0.1 + 0.1 seconds
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting per minute."""
        pool = RequestPool(max_concurrent=10, requests_per_minute=2)
        
        requests = []
        for _ in range(3):
            await pool.acquire()
            requests.append(datetime.now())
            pool.release()
        
        # Third request should be delayed
        gap = (requests[2] - requests[0]).total_seconds()
        assert gap >= 60.0  # Should wait a minute


class TestRequestBatcher:
    """Test request batching functionality."""
    
    @pytest.mark.asyncio
    async def test_batch_collection(self):
        """Test batch collection."""
        batcher = RequestBatcher(batch_size=3, batch_timeout=0.5)
        
        futures = []
        for i in range(3):
            future = await batcher.add_request({'id': i})
            futures.append(future)
        
        # Get batch
        batch = await batcher._get_batch()
        assert len(batch) == 3
        assert batch[0]['request']['id'] == 0
    
    @pytest.mark.asyncio
    async def test_batch_timeout(self):
        """Test batch timeout triggers processing."""
        batcher = RequestBatcher(batch_size=5, batch_timeout=0.1)
        
        # Add only 2 requests (less than batch_size)
        futures = []
        for i in range(2):
            future = await batcher.add_request({'id': i})
            futures.append(future)
        
        # Wait for timeout
        await asyncio.sleep(0.15)
        batch = await batcher._get_batch()
        assert len(batch) == 2


class TestCacheManager:
    """Test cache manager functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_storage(self):
        """Test basic cache storage and retrieval."""
        cache = CacheManager(max_size=10, ttl_seconds=60)
        
        await cache.set('key1', 'value1')
        result = await cache.get('key1')
        assert result == 'value1'
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = CacheManager(max_size=10, ttl_seconds=0)
        
        await cache.set('key1', 'value1')
        await asyncio.sleep(0.1)
        result = await cache.get('key1')
        assert result is None  # Should be expired
    
    @pytest.mark.asyncio
    async def test_cache_eviction(self):
        """Test LRU cache eviction."""
        cache = CacheManager(max_size=3, ttl_seconds=60)
        
        # Fill cache
        for i in range(4):
            await cache.set(f'key{i}', f'value{i}')
        
        # First key should be evicted
        result = await cache.get('key0')
        assert result is None
        
        # Others should exist
        assert await cache.get('key1') == 'value1'
        assert await cache.get('key2') == 'value2'
        assert await cache.get('key3') == 'value3'
    
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = CacheManager(max_size=10, ttl_seconds=60)
        
        await cache.set('key1', 'value1')
        await cache.set('key2', 'value2')
        
        stats = await cache.get_stats()
        assert stats['size'] == 2
        assert stats['max_size'] == 10


class TestResourceMonitor:
    """Test resource monitor functionality."""
    
    def test_pool_creation(self):
        """Test request pool creation by config."""
        monitor = ResourceMonitor()
        
        fast_pool = monitor.get_request_pool('fast_llm')
        assert fast_pool.max_concurrent == 10
        assert fast_pool.requests_per_minute == 120
        
        slow_pool = monitor.get_request_pool('slow_llm')
        assert slow_pool.max_concurrent == 3
        assert slow_pool.requests_per_minute == 30
        
        standard_pool = monitor.get_request_pool('standard')
        assert standard_pool.max_concurrent == 5
        assert standard_pool.requests_per_minute == 60
    
    def test_cache_manager_creation(self):
        """Test cache manager creation."""
        monitor = ResourceMonitor()
        
        cache1 = monitor.get_cache_manager('config1')
        cache2 = monitor.get_cache_manager('config1')
        assert cache1 is cache2  # Should return same instance
    
    @pytest.mark.asyncio
    async def test_metrics_recording(self):
        """Test metrics recording."""
        monitor = ResourceMonitor()
        
        await monitor.record_request('test_config', True, 100.5)
        await monitor.record_request('test_config', False, 200.0)
        
        metrics = await monitor.get_metrics()
        config_metrics = metrics['metrics']['test_config']
        
        assert config_metrics['total_requests'] == 2
        assert config_metrics['successful_requests'] == 1
        assert config_metrics['failed_requests'] == 1
        assert config_metrics['total_duration_ms'] == 300.5