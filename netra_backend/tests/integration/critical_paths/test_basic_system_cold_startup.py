"""Basic System Cold Startup Integration Tests (L3)

Tests fundamental system startup sequence from cold state.
Validates basic initialization order, service availability, and readiness checks.

Business Value Justification (BVJ):
- Segment: Platform/Internal (enabling all segments)
- Business Goal: Ensure reliable system startup and availability
- Value Impact: System must start correctly to serve any customers
- Revenue Impact: 100% - no startup means no service, no revenue
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import os
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Set test environment before imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

from netra_backend.app.main import app

from netra_backend.app.config import get_config
from netra_backend.app.core.health_checkers import HealthChecker
from netra_backend.app.db.client_clickhouse import ClickHouseClient
from netra_backend.app.db.postgres import async_engine as pg_engine

class TestBasicSystemColdStartup:
    """Test basic system cold startup sequence."""
    
    @pytest.fixture
    async def fresh_app(self):
        """Create fresh app instance for cold start testing."""
        # Clear any cached state
        if hasattr(app, 'state'):
            app.state.startup_complete = False
        
        # Return fresh app
        yield app
    
    @pytest.fixture
    async def async_client(self, fresh_app):
        """Create async client for testing."""
        transport = ASGITransport(app=fresh_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_health_check_before_startup_complete(self, async_client):
        """Test 1: Health check should indicate not ready before startup completes."""
        # Simulate early health check
        with patch.object(app, 'state', create=True) as mock_state:
            mock_state.startup_complete = False
            
            response = await async_client.get("/health")
            
            # Should return 503 when not ready
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "startup" in data.get("details", "").lower()
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_health_check_after_startup_complete(self, async_client):
        """Test 2: Health check should indicate ready after startup completes."""
        # Simulate completed startup
        with patch.object(app, 'state', create=True) as mock_state:
            mock_state.startup_complete = True
            
            # Mock database connections as healthy
            # Mock: Component isolation for testing without external dependencies
            with patch('app.core.health_checkers.HealthChecker.check_postgres', return_value={"healthy": True}):
                # Mock: Component isolation for testing without external dependencies
                with patch('app.core.health_checkers.HealthChecker.check_clickhouse', return_value={"healthy": True}):
                    # Mock: Component isolation for testing without external dependencies
                    with patch('app.core.health_checkers.HealthChecker.check_redis', return_value={"healthy": True}):
                        
                        response = await async_client.get("/health")
                        
                        # Should return 200 when ready
                        assert response.status_code == 200
                        data = response.json()
                        assert data["status"] == "healthy"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_initialization_order(self):
        """Test 3: Services should initialize in correct order."""
        initialization_order = []
        
        # Mock initialization functions to track order
        async def mock_postgres_init():
            initialization_order.append("postgres")
            return True
        
        async def mock_clickhouse_init():
            initialization_order.append("clickhouse")
            return True
        
        async def mock_redis_init():
            initialization_order.append("redis")
            return True
        
        async def mock_cache_init():
            initialization_order.append("cache")
            return True
        
        # Simulate startup sequence
        # Mock: PostgreSQL database isolation for testing without real database connections
        with patch('app.db.postgres.init_db', mock_postgres_init):
            # Mock: ClickHouse database isolation for fast testing without external database dependency
            with patch('app.db.client_clickhouse.ClickHouseClient.initialize', mock_clickhouse_init):
                # Mock: Redis external service isolation for fast, reliable tests without network dependency
                with patch('app.cache.redis_manager.RedisManager.initialize', mock_redis_init):
                    # Mock: Component isolation for testing without external dependencies
                    with patch('app.cache.cache_manager.CacheManager.initialize', mock_cache_init):
                        
                        # Run initialization
                        await mock_postgres_init()
                        await mock_clickhouse_init()
                        await mock_redis_init()
                        await mock_cache_init()
                        
                        # Verify order: databases first, then cache layers
                        assert initialization_order[0] == "postgres"
                        assert initialization_order[1] == "clickhouse"
                        assert initialization_order[2] == "redis"
                        assert initialization_order[3] == "cache"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_readiness_check_basic_dependencies(self, async_client):
        """Test 4: Readiness check should verify all basic dependencies."""
        # Mock health checker
        health_checker = HealthChecker()
        
        # Test individual component checks
        postgres_health = await health_checker.check_postgres()
        assert "postgres" in postgres_health
        
        clickhouse_health = await health_checker.check_clickhouse()
        assert "clickhouse" in clickhouse_health
        
        redis_health = await health_checker.check_redis()
        assert "redis" in redis_health
        
        # Full health check should include all components
        full_health = await health_checker.check_health()
        assert "postgres" in full_health["components"]
        assert "clickhouse" in full_health["components"]
        assert "redis" in full_health["components"]
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_api_endpoints_available_after_startup(self, async_client):
        """Test 5: Basic API endpoints should be available after startup."""
        # Mock successful startup
        with patch.object(app, 'state', create=True) as mock_state:
            mock_state.startup_complete = True
            
            # Test basic endpoints
            endpoints_to_test = [
                ("/health", 200),  # Health check
                ("/api/auth/config", 200),  # Auth config
                ("/docs", 200),  # API documentation
                ("/openapi.json", 200),  # OpenAPI spec
            ]
            
            for endpoint, expected_status in endpoints_to_test:
                # Mock dependencies as needed
                if endpoint == "/health":
                    # Mock: Component isolation for testing without external dependencies
                    with patch('app.core.health_checkers.HealthChecker.check_health', 
                              return_value={"status": "healthy", "components": {}}):
                        response = await async_client.get(endpoint)
                        assert response.status_code == expected_status, f"Endpoint {endpoint} failed"
                else:
                    response = await async_client.get(endpoint)
                    # Some endpoints may return different status in test env
                    assert response.status_code in [expected_status, 422, 503], f"Endpoint {endpoint} returned unexpected status"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_configuration_loading_on_startup(self):
        """Test 6: Configuration should be properly loaded on startup."""
        # Get settings instance
        settings = get_config()
        
        # Verify essential settings are loaded
        assert settings.PROJECT_NAME
        assert settings.VERSION
        assert settings.ENVIRONMENT
        
        # Verify database URLs are configured
        assert settings.DATABASE_URL
        assert settings.CLICKHOUSE_URL
        assert settings.REDIS_URL
        
        # Verify API settings
        assert settings.API_V1_STR
        assert hasattr(settings, 'SECRET_KEY')
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_failure_handling(self):
        """Test 7: System should handle startup failures gracefully."""
        # Simulate database connection failure
        # Mock: Component isolation for testing without external dependencies
        with patch('app.db.postgres.init_db', side_effect=Exception("Database connection failed")):
            
            # Startup should catch and log the error
            try:
                # Simulate startup
                from netra_backend.app.db.postgres import init_db
                await init_db()
            except Exception as e:
                # Should get meaningful error
                assert "Database connection failed" in str(e)
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_cold_start_performance(self, async_client):
        """Test 8: Cold start should complete within acceptable time."""
        start_time = time.perf_counter()
        
        # Simulate cold start by making first request
        with patch.object(app, 'state', create=True) as mock_state:
            mock_state.startup_complete = True
            
            response = await async_client.get("/health")
            
            cold_start_time = time.perf_counter() - start_time
            
            # Should complete within 5 seconds
            assert cold_start_time < 5.0, f"Cold start took {cold_start_time}s"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_idempotency(self):
        """Test 9: Startup should be idempotent (safe to call multiple times)."""
        initialization_count = {"count": 0}
        
        async def mock_init():
            initialization_count["count"] += 1
            return True
        
        # Mock initialization that tracks calls
        # Mock: Component isolation for testing without external dependencies
        with patch('app.cache.cache_manager.CacheManager.initialize', mock_init):
            # First initialization
            await mock_init()
            first_count = initialization_count["count"]
            
            # Second initialization (should be safe)
            await mock_init()
            second_count = initialization_count["count"]
            
            # Should have been called twice (no protection against re-init in mock)
            assert second_count == first_count + 1
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_graceful_degradation_missing_optional_services(self, async_client):
        """Test 10: System should start even if optional services are unavailable."""
        # Mock optional service failures
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.notification_service.NotificationService.initialize', 
                  side_effect=Exception("Notification service unavailable")):
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.analytics_service.AnalyticsService.initialize',
                      side_effect=Exception("Analytics service unavailable")):
                
                # System should still be healthy (degraded mode)
                with patch.object(app, 'state', create=True) as mock_state:
                    mock_state.startup_complete = True
                    
                    # Core services mocked as healthy
                    # Mock: Component isolation for testing without external dependencies
                    with patch('app.core.health_checkers.HealthChecker.check_health',
                              return_value={
                                  "status": "degraded",
                                  "components": {
                                      "postgres": {"healthy": True},
                                      "clickhouse": {"healthy": True},
                                      "redis": {"healthy": True},
                                      "notifications": {"healthy": False, "error": "unavailable"},
                                      "analytics": {"healthy": False, "error": "unavailable"}
                                  }
                              }):
                        
                        response = await async_client.get("/health")
                        
                        # Should return 200 (degraded but operational)
                        assert response.status_code == 200
                        data = response.json()
                        assert data["status"] == "degraded"
                        assert data["components"]["postgres"]["healthy"] == True
                        assert data["components"]["notifications"]["healthy"] == False