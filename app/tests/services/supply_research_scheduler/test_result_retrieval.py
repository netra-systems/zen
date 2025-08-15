"""
Tests for result retrieval and caching
"""

import pytest
import json
from datetime import datetime, timedelta, UTC
from unittest.mock import patch

from app.services.supply_research_scheduler import SupplyResearchScheduler
from app.tests.services.supply_research_scheduler.test_scheduler_initialization import (
    MockBackgroundTaskManager,
    MockLLMManager,
    MockRedisManager
)


@pytest.fixture
def scheduler():
    """Create SupplyResearchScheduler instance"""
    mock_background_manager = MockBackgroundTaskManager()
    mock_llm_manager = MockLLMManager()
    
    with patch('app.services.supply_research_scheduler.RedisManager') as mock_redis_class:
        mock_redis_class.return_value = MockRedisManager()
        return SupplyResearchScheduler(mock_background_manager, mock_llm_manager)


@pytest.mark.asyncio
class TestResultRetrieval:
    """Test result retrieval from cache"""
    
    async def test_get_recent_results_no_redis(self, scheduler):
        """Test getting recent results when Redis not available"""
        scheduler.redis_manager = None
        
        results = await scheduler.get_recent_results()
        
        assert results == []
    
    async def test_get_recent_results_with_redis(self, scheduler):
        """Test getting recent results from Redis"""
        # Use the existing redis_manager from the scheduler
        mock_redis = scheduler.redis_manager
        
        # Add some test data to Redis
        test_result = {
            "schedule_name": "test_schedule",
            "status": "completed",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        today = datetime.now(UTC).date()
        cache_key = f"schedule_result:test_schedule:{today}"
        await mock_redis.set(cache_key, json.dumps(test_result))
        
        results = await scheduler.get_recent_results("test_schedule", days_back=1)
        
        assert len(results) == 1
        assert results[0]["schedule_name"] == "test_schedule"
    
    async def test_get_recent_results_all_schedules(self, scheduler):
        """Test getting results for all schedules"""
        # Use the existing redis_manager from the scheduler
        mock_redis = scheduler.redis_manager
        
        # Add results for multiple schedules
        today = datetime.now(UTC).date()
        for i, schedule in enumerate(scheduler.schedules[:2]):
            test_result = {
                "schedule_name": schedule.name,
                "status": "completed"
            }
            cache_key = f"schedule_result:{schedule.name}:{today}"
            await mock_redis.set(cache_key, json.dumps(test_result))
        
        results = await scheduler.get_recent_results(days_back=1)
        
        assert len(results) >= 2
    
    async def test_get_recent_results_multiple_days(self, scheduler):
        """Test getting results across multiple days"""
        # Use the existing redis_manager from the scheduler
        mock_redis = scheduler.redis_manager
        
        schedule_name = "test_schedule"
        
        # Add results for multiple days
        for days_ago in [0, 1, 2]:
            date = (datetime.now(UTC) - timedelta(days=days_ago)).date()
            test_result = {
                "schedule_name": schedule_name,
                "day": str(date)
            }
            cache_key = f"schedule_result:{schedule_name}:{date}"
            await mock_redis.set(cache_key, json.dumps(test_result))
        
        results = await scheduler.get_recent_results(schedule_name, days_back=3)
        
        assert len(results) == 3
    
    async def test_get_recent_results_redis_errors(self, scheduler):
        """Test handling Redis errors when getting results"""
        # Use the existing redis_manager from the scheduler
        mock_redis = scheduler.redis_manager
        
        # Mock Redis get to raise exception
        async def failing_get(key):
            raise Exception("Redis error")
        
        mock_redis.get = failing_get
        
        # Should handle errors gracefully
        results = await scheduler.get_recent_results("test_schedule")
        
        assert results == []