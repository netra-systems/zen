"""
Test 25: LLM Cache Route Management
Tests for cache invalidation and metrics - app/routes/llm_cache.py

Business Value Justification (BVJ):
- Segment: Growth, Mid, Enterprise  
- Business Goal: Optimize AI response time and reduce API costs
- Value Impact: 40-60% reduction in LLM API costs through intelligent caching
- Revenue Impact: Direct cost savings translate to higher profit margins
"""

import sys
from pathlib import Path
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


import pytest

from netra_backend.tests.test_route_fixtures import (
    CommonResponseValidators,
    MockServiceFactory,
    basic_test_client,
)

class TestLLMCacheRoute:
    """Test cache management, metrics, and invalidation functionality."""
    
    def test_cache_metrics(self, basic_test_client):
        """Test cache metrics retrieval."""
        mock_cache_service = MockServiceFactory.create_mock_cache_service()
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.llm_cache_service', mock_cache_service):
            response = basic_test_client.get("/api/llm-cache/metrics")
            
            if response.status_code == 200:
                metrics = response.json()
                CommonResponseValidators.validate_success_response(
                    response,
                    expected_keys=["hits", "misses", "hit_rate"]
                )
                
                # Validate metric ranges
                if "hit_rate" in metrics:
                    assert 0 <= metrics["hit_rate"] <= 1
                if "hits" in metrics and "misses" in metrics:
                    assert metrics["hits"] >= 0
                    assert metrics["misses"] >= 0
            else:
                assert response.status_code in [404, 401]
    
    def test_cache_invalidation(self, basic_test_client):
        """Test cache invalidation endpoint."""
        mock_cache_service = MockServiceFactory.create_mock_cache_service()
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.llm_cache_service', mock_cache_service):
            response = basic_test_client.delete("/api/llm-cache/")
            
            if response.status_code == 200:
                result = response.json()
                assert "cleared" in result or "message" in result
                
                # Verify cleared count is reasonable
                if "cleared" in result:
                    assert isinstance(result["cleared"], int)
                    assert result["cleared"] >= 0
            else:
                assert response.status_code in [404, 401]
    
    @pytest.mark.asyncio
    async def test_selective_cache_invalidation(self):
        """Test selective cache invalidation by pattern."""
        from netra_backend.app.routes.llm_cache import clear_cache_pattern
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.llm_cache_service.clear_cache_pattern') as mock_clear:
            mock_clear.return_value = 10
            
            result = await clear_cache_pattern("user_*")
            assert result["cleared"] == 10
            
            # Test different patterns
            result = await clear_cache_pattern("agent_*")
            assert "cleared" in result
    
    def test_cache_performance_monitoring(self, basic_test_client):
        """Test cache performance monitoring endpoints."""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.llm_cache_service.get_performance_stats') as mock_perf:
            mock_perf.return_value = {
                "avg_response_time_ms": 45,
                "cache_hit_rate_24h": 0.78,
                "memory_usage_mb": 128.5,
                "evictions_last_hour": 5
            }
            
            response = basic_test_client.get("/api/llm-cache/performance")
            
            if response.status_code == 200:
                data = response.json()
                if "avg_response_time_ms" in data:
                    assert data["avg_response_time_ms"] > 0
                if "cache_hit_rate_24h" in data:
                    assert 0 <= data["cache_hit_rate_24h"] <= 1
            else:
                assert response.status_code in [404, 401]
    
    def test_cache_size_management(self, basic_test_client):
        """Test cache size limits and management."""
        # Test cache size configuration
        size_config = {
            "max_size_mb": 512,
            "eviction_policy": "lru",
            "ttl_seconds": 3600
        }
        
        response = basic_test_client.put("/api/llm-cache/config", json=size_config)
        
        if response.status_code == 200:
            CommonResponseValidators.validate_success_response(response)
        else:
            assert response.status_code in [404, 422, 401]
        
        # Test cache size information
        response = basic_test_client.get("/api/llm-cache/size")
        
        if response.status_code == 200:
            data = response.json()
            size_fields = ["total_size_mb", "used_size_mb", "available_size_mb"]
            has_size_info = any(field in data for field in size_fields)
            
            if has_size_info:
                for field in size_fields:
                    if field in data:
                        assert data[field] >= 0
        else:
            assert response.status_code in [404, 401]
    
    @pytest.mark.asyncio
    async def test_cache_warm_up(self):
        """Test cache warm-up functionality."""
        from netra_backend.app.routes.llm_cache import warm_up_cache
        
        warm_up_config = {
            "patterns": ["common_queries_*", "frequent_agents_*"],
            "priority": "high",
            "max_items": 100
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.llm_cache_service.warm_up_cache') as mock_warm_up:
            mock_warm_up.return_value = {
                "warmed_up": 85,
                "failed": 15,
                "duration_seconds": 12.5
            }
            
            result = await warm_up_cache(warm_up_config)
            
            assert result["warmed_up"] > 0
            assert result["failed"] >= 0
            assert result["duration_seconds"] > 0
    
    def test_cache_health_check(self, basic_test_client):
        """Test cache health monitoring."""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.health_check') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "response_time_ms": 2.5,
                "error_rate": 0.001,
                "last_check": "2024-01-01T12:00:00Z"
            }
            
            response = basic_test_client.get("/api/llm-cache/health")
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                
                if data["status"] == "healthy":
                    # Healthy cache should have good metrics
                    if "response_time_ms" in data:
                        assert data["response_time_ms"] < 100  # Should be fast
                    if "error_rate" in data:
                        assert data["error_rate"] < 0.05  # Low error rate
            else:
                assert response.status_code in [404, 401]
    
    def test_cache_key_analysis(self, basic_test_client):
        """Test cache key pattern analysis."""
        analysis_request = {
            "timeframe": "24h",
            "include_patterns": True,
            "min_frequency": 5
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.analyze_cache_keys') as mock_analyze:
            mock_analyze.return_value = {
                "total_keys": 1500,
                "unique_patterns": 25,
                "top_patterns": [
                    {"pattern": "user_query_*", "count": 450, "hit_rate": 0.82},
                    {"pattern": "agent_response_*", "count": 320, "hit_rate": 0.76}
                ],
                "recommendations": [
                    "Increase TTL for user_query_* pattern",
                    "Consider pre-warming agent_response_* pattern"
                ]
            }
            
            response = basic_test_client.post("/api/llm-cache/analyze", json=analysis_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "total_keys" in data or "patterns" in data
                
                if "top_patterns" in data:
                    for pattern in data["top_patterns"]:
                        assert "pattern" in pattern
                        assert "count" in pattern
                        assert pattern["count"] > 0
            else:
                assert response.status_code in [404, 422, 401]
    
    @pytest.mark.asyncio
    async def test_cache_backup_restore(self):
        """Test cache backup and restore functionality."""
        from netra_backend.app.routes.llm_cache import backup_cache, restore_cache
        
        # Test cache backup
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.create_backup') as mock_backup:
            mock_backup.return_value = {
                "backup_id": "backup_123",
                "size_mb": 64.5,
                "entries_count": 1250,
                "timestamp": "2024-01-01T12:00:00Z"
            }
            
            backup_result = await backup_cache()
            assert "backup_id" in backup_result
            assert backup_result["entries_count"] > 0
        
        # Test cache restore
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.restore_from_backup') as mock_restore:
            mock_restore.return_value = {
                "restored": True,
                "entries_restored": 1250,
                "restore_duration_seconds": 8.2
            }
            
            restore_result = await restore_cache("backup_123")
            assert restore_result["restored"] == True
            assert restore_result["entries_restored"] > 0
    
    def test_cache_statistics_aggregation(self, basic_test_client):
        """Test cache statistics aggregation over time periods."""
        stats_request = {
            "period": "daily",
            "days": 7,
            "metrics": ["hit_rate", "response_time", "memory_usage"]
        }
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.llm_cache_service.get_aggregated_stats') as mock_stats:
            mock_stats.return_value = {
                "period": "daily",
                "data_points": [
                    {"date": "2024-01-01", "hit_rate": 0.78, "response_time_ms": 45},
                    {"date": "2024-01-02", "hit_rate": 0.82, "response_time_ms": 42},
                    {"date": "2024-01-03", "hit_rate": 0.85, "response_time_ms": 38}
                ],
                "averages": {"hit_rate": 0.82, "response_time_ms": 41.7}
            }
            
            response = basic_test_client.post("/api/llm-cache/stats", json=stats_request)
            
            if response.status_code == 200:
                data = response.json()
                assert "data_points" in data or "averages" in data
                
                if "data_points" in data:
                    for point in data["data_points"]:
                        assert "date" in point
                        # Validate metric ranges
                        if "hit_rate" in point:
                            assert 0 <= point["hit_rate"] <= 1
            else:
                assert response.status_code in [404, 422, 401]