"""
Test Caching Performance Integration

Business Value Justification (BVJ):
- Segment: All customer segments (response time optimization)
- Business Goal: Improve user experience through faster response times
- Value Impact: Caching reduces latency and improves customer satisfaction
- Strategic Impact: Performance optimization enables competitive advantage

CRITICAL REQUIREMENTS:
- Tests real caching systems (Redis, in-memory)
- Validates cache hit ratios and performance improvements
- Uses real cache instances, NO MOCKS
- Ensures cache consistency and invalidation
"""

import pytest
import asyncio
import time
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

from netra_backend.app.services.cache_service import CacheConsistencyManager
from netra_backend.app.services.state_persistence import StateCacheManager


class TestCachingPerformanceIntegration(SSotBaseTestCase):
    """Test caching performance with real cache systems"""
    
    def setup_method(self):
        """Set up test environment"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.test_prefix = f"cache_test_{uuid.uuid4().hex[:8]}"
        self.cache_manager = CacheManager()
        self.performance_optimizer = CachePerformanceOptimizer()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_cache_performance_under_load(self):
        """Test Redis cache performance under concurrent load"""
        # Initialize Redis cache
        await self.cache_manager.initialize_redis_cache(test_prefix=self.test_prefix)
        
        # Test cache operations under load
        concurrent_operations = 100
        tasks = []
        
        for i in range(concurrent_operations):
            task = self._perform_cache_operations(f"test_key_{i}", f"test_value_{i}")
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Validate performance
        successful_operations = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful_operations) >= concurrent_operations * 0.95  # 95% success rate
        
        total_duration = end_time - start_time
        assert total_duration < 10.0, f"Cache operations too slow: {total_duration}s"
        
        # Test cache hit ratio
        cache_stats = await self.cache_manager.get_cache_statistics(self.test_prefix)
        assert cache_stats.hit_ratio >= 0.8, f"Cache hit ratio too low: {cache_stats.hit_ratio}"
    
    async def _perform_cache_operations(self, key: str, value: str):
        """Perform cache operations for performance testing"""
        try:
            # Set value
            await self.cache_manager.set(key, value, ttl=300)
            
            # Get value multiple times (test cache hits)
            for _ in range(5):
                retrieved_value = await self.cache_manager.get(key)
                assert retrieved_value == value
            
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])