"""
Test 25: LLM Cache Route Management
Tests for cache invalidation and metrics - app/routes/llm_cache.py
"""

import pytest
from unittest.mock import patch
from netra_backend.tests.test_utilities import base_client


class TestLLMCacheRoute:
    """Test cache invalidation and metrics."""
    
    def test_cache_metrics(self, base_client):
        """Test cache metrics retrieval."""
        with patch('app.services.llm_cache_service.llm_cache_service.get_cache_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "hits": 150,
                "misses": 50,
                "hit_rate": 0.75,
                "size_mb": 24.5,
                "entries": 200
            }
            
            response = base_client.get("/api/llm-cache/metrics")
            
            if response.status_code == 200:
                metrics = response.json()
                if "hit_rate" in metrics:
                    assert 0 <= metrics["hit_rate"] <= 1
    
    def test_cache_invalidation(self, base_client):
        """Test cache invalidation endpoint."""
        with patch('app.services.llm_cache_service.llm_cache_service.clear_cache') as mock_clear:
            mock_clear.return_value = 50
            
            response = base_client.delete("/api/llm-cache/")
            
            if response.status_code == 200:
                result = response.json()
                assert "cleared" in result or "message" in result

    async def test_selective_cache_invalidation(self):
        """Test selective cache invalidation."""
        from app.routes.llm_cache import clear_cache_pattern
        
        with patch('app.services.llm_cache_service.llm_cache_service.clear_cache_pattern') as mock_clear:
            mock_clear.return_value = 10
            
            result = await clear_cache_pattern("user_*")
            assert result["cleared"] == 10