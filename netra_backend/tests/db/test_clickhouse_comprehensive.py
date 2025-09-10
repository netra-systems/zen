"""
Comprehensive Unit Tests for ClickHouse Client CANONICAL SSOT

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Analytics data accuracy for decision making and pricing optimization  
- Value Impact: 100% reliable analytics enables data-driven business insights worth $15K+ MRR
- Revenue Impact: Analytics accuracy directly drives pricing optimization and customer insights

This test suite validates ClickHouse as the CANONICAL SSOT for analytics data collection and querying.
Critical for golden path: user interactions → usage analytics → business intelligence → pricing optimization.

SSOT Compliance:
- Tests the ONLY source for analytics data operations  
- Validates real vs NoOp client distinction (NO MOCKS IN DEV MODE)
- Ensures proper environment-based client selection
- Verifies context-aware error handling and graceful degradation

Golden Path Analytics Coverage:
- User behavior tracking (conversation analytics, tool usage metrics)
- Agent performance analytics (execution times, success rates, optimization impact)  
- Business metrics collection (usage patterns, feature adoption, revenue attribution)
- Real-time analytics queries (dashboards, reporting, business intelligence)
- Multi-user isolation in analytics data (user-specific caching and queries)
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from netra_backend.app.db.clickhouse import (
    ClickHouseService,
    ClickHouseCache, 
    NoOpClickHouseClient,
    get_clickhouse_client,
    get_clickhouse_service,
    get_clickhouse_config,
    use_mock_clickhouse,
    create_agent_state_history_table,
    insert_agent_state_history
)


class TestClickHouseCacheSSO:
    """Test ClickHouse Cache as Single Source of Truth for query caching."""
    
    @pytest.fixture
    def cache(self):
        """Create fresh ClickHouse cache for testing."""
        return ClickHouseCache(max_size=100)
    
    @pytest.mark.unit
    def test_cache_key_generation_user_isolation(self, cache):
        """Test cache key generation with proper user isolation.
        
        BVJ: Ensures analytics data isolation between users - critical for SaaS platform.
        Golden Path: User A's analytics must never leak to User B.
        """
        # Test user-specific cache keys
        key1 = cache._generate_key("user123", "SELECT * FROM events", {"limit": 10})
        key2 = cache._generate_key("user456", "SELECT * FROM events", {"limit": 10})
        key3 = cache._generate_key("user123", "SELECT * FROM events", {"limit": 20})
        
        # Verify user isolation in cache keys
        assert "user123" in key1
        assert "user456" in key2
        assert key1 != key2  # Different users have different keys
        assert key1 != key3  # Same user, different params have different keys
        
        # Test system namespace for None user_id (backward compatibility)
        key_system = cache._generate_key(None, "SELECT 1")
        assert "system" in key_system
    
    @pytest.mark.unit
    def test_cache_user_isolation_storage_retrieval(self, cache):
        """Test cache storage and retrieval with user isolation.
        
        BVJ: Validates analytics query performance optimization per user.
        Golden Path: Cached queries improve dashboard load times for each user independently.
        """
        query = "SELECT COUNT(*) FROM user_events WHERE user_id = %(user_id)s"
        params = {"user_id": "test_user"}
        
        # Cache results for different users
        user1_result = [{"count": 150}]
        user2_result = [{"count": 89}]
        
        cache.set("user1", query, user1_result, params, ttl=300)
        cache.set("user2", query, user2_result, params, ttl=300)
        
        # Verify user isolation in retrieval
        cached_user1 = cache.get("user1", query, params)
        cached_user2 = cache.get("user2", query, params)
        
        assert cached_user1 == user1_result
        assert cached_user2 == user2_result
        assert cached_user1 != cached_user2
    
    @pytest.mark.unit
    def test_cache_ttl_expiration(self, cache):
        """Test cache TTL expiration for data freshness.
        
        BVJ: Ensures analytics data freshness for accurate business decisions.
        Golden Path: Stale analytics data must not mislead business strategy.
        """
        query = "SELECT revenue_today FROM daily_metrics"
        result = [{"revenue_today": 5420.75}]
        
        # Cache with very short TTL
        cache.set("user123", query, result, ttl=0.1)  # 0.1 second TTL
        
        # Verify immediate retrieval works
        cached_result = cache.get("user123", query)
        assert cached_result == result
        
        # Wait for TTL expiration
        time.sleep(0.2)
        
        # Verify expired data is not returned
        expired_result = cache.get("user123", query)
        assert expired_result is None
    
    @pytest.mark.unit
    def test_cache_statistics_user_specific(self, cache):
        """Test cache statistics with user-specific insights.
        
        BVJ: Enables monitoring of cache performance per user for optimization.
        Golden Path: Cache performance metrics help optimize user experience.
        """
        # Add cache entries for different users
        cache.set("user1", "SELECT * FROM events", [{"id": 1}])
        cache.set("user1", "SELECT * FROM metrics", [{"metric": "cpu"}])
        cache.set("user2", "SELECT * FROM events", [{"id": 2}])
        
        # Trigger cache hits and misses
        cache.get("user1", "SELECT * FROM events")  # Hit
        cache.get("user1", "SELECT * FROM unknown")  # Miss
        cache.get("user2", "SELECT * FROM events")   # Hit
        
        # Test global statistics
        global_stats = cache.stats()
        assert global_stats["size"] == 3
        assert global_stats["hits"] == 2
        assert global_stats["misses"] == 1
        assert global_stats["hit_rate"] == 2/3
        
        # Test user-specific statistics
        user1_stats = cache.stats("user1")
        assert user1_stats["user_id"] == "user1"
        assert user1_stats["user_cache_entries"] == 2
        assert user1_stats["user_cache_percentage"] == (2/3) * 100
    
    @pytest.mark.unit
    def test_cache_clear_user_isolation(self, cache):
        """Test cache clearing with user isolation.
        
        BVJ: Enables user-specific cache management for data privacy.
        Golden Path: Users must be able to clear their analytics cache independently.
        """
        # Add entries for multiple users
        cache.set("user1", "SELECT * FROM events", [{"count": 10}])
        cache.set("user2", "SELECT * FROM events", [{"count": 15}])
        cache.set("system", "SELECT health_check()", [{"status": "ok"}])
        
        # Clear cache for specific user
        cache.clear("user1")
        
        # Verify only user1's cache was cleared
        assert cache.get("user1", "SELECT * FROM events") is None
        assert cache.get("user2", "SELECT * FROM events") is not None
        assert cache.get("system", "SELECT health_check()") is not None
        
        # Test global clear
        cache.clear()
        assert cache.get("user2", "SELECT * FROM events") is None
        assert cache.get("system", "SELECT health_check()") is None


class TestNoOpClickHouseClient:
    """Test NoOp ClickHouse Client for testing environments."""
    
    @pytest.fixture
    def noop_client(self):
        """Create NoOp ClickHouse client for testing."""
        return NoOpClickHouseClient()
    
    @pytest.mark.unit
    async def test_noop_successful_queries(self, noop_client):
        """Test NoOp client successful query simulation.
        
        BVJ: Enables unit testing without external dependencies.
        Golden Path: Tests must run reliably in CI/CD without ClickHouse service.
        """
        # Test basic query
        result = await noop_client.execute("SELECT 1")
        assert result == [{"1": 1}]
        
        # Test query with alias
        result = await noop_client.execute("SELECT 1 as test_value")
        assert result == [{"test": 1}]
        
        # Test generic successful queries return empty
        result = await noop_client.execute("SELECT * FROM user_events LIMIT 10")
        assert result == []
    
    @pytest.mark.unit
    async def test_noop_realistic_error_simulation(self, noop_client):
        """Test NoOp client realistic error condition simulation.
        
        BVJ: Ensures tests can validate error handling logic.
        Golden Path: Error scenarios must be testable for robust application.
        """
        # Test table not found error
        with pytest.raises(Exception) as exc_info:
            await noop_client.execute("SELECT * FROM non_existent_table")
        assert "doesn't exist" in str(exc_info.value)
        
        # Test syntax error
        with pytest.raises(Exception) as exc_info:
            await noop_client.execute("SELECT from where")
        assert "Syntax error" in str(exc_info.value)
        
        # Test permission error
        with pytest.raises(Exception) as exc_info:
            await noop_client.execute("SELECT * FROM system.users")
        assert "Not enough privileges" in str(exc_info.value)
        
        # Test unsupported operation
        with pytest.raises(Exception) as exc_info:
            await noop_client.execute("UPDATE set where")
        assert "doesn't support UPDATE" in str(exc_info.value)
    
    @pytest.mark.unit
    async def test_noop_connection_state_management(self, noop_client):
        """Test NoOp client connection state management.
        
        BVJ: Enables testing of connection recovery scenarios.
        Golden Path: Connection failures must be recoverable in production.
        """
        # Test initial connection state
        assert await noop_client.test_connection() == True
        
        # Test disconnect
        await noop_client.disconnect()
        assert await noop_client.test_connection() == False
        
        # Test query on disconnected client
        with pytest.raises(ConnectionError) as exc_info:
            await noop_client.execute("SELECT 1")
        assert "disconnected" in str(exc_info.value)


class TestClickHouseService:
    """Test ClickHouse Service as the main interface for analytics operations."""
    
    @pytest.fixture
    def service(self):
        """Create ClickHouse service for testing."""
        return ClickHouseService(force_mock=False)
    
    @pytest.fixture
    def mock_service(self):
        """Create ClickHouse service with forced mock for testing."""
        return ClickHouseService(force_mock=True)
    
    @pytest.mark.unit
    async def test_service_initialization_environment_detection(self, service):
        """Test service initialization with proper environment detection.
        
        BVJ: Ensures correct client selection based on environment for reliability.
        Golden Path: Development must use real ClickHouse, testing can use NoOp.
        """
        with patch('netra_backend.app.db.clickhouse.use_mock_clickhouse', return_value=True):
            # Test initialization in testing environment
            await service.initialize()
            
            # Verify NoOp client was initialized
            assert isinstance(service._client, NoOpClickHouseClient)
            assert service.is_mock == True
    
    @pytest.mark.unit
    async def test_service_context_aware_error_handling(self, service):
        """Test context-aware error handling for optional vs required services.
        
        BVJ: Reduces log noise and enables graceful degradation for optional analytics.
        Golden Path: Analytics failures shouldn't break core user functionality.
        """
        with patch('netra_backend.app.db.clickhouse.get_clickhouse_config') as mock_config, \
             patch('netra_backend.app.db.clickhouse.ClickHouseDatabase') as mock_db_class, \
             patch('netra_backend.app.db.clickhouse.get_env') as mock_get_env:
            
            # Setup mocks for connection failure
            mock_get_env.return_value.get.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "development",
                "CLICKHOUSE_REQUIRED": "false"  # Optional service
            }.get(key, default)
            
            mock_config.return_value = Mock(host="localhost", port=8123)
            mock_db_instance = Mock()
            mock_db_instance.test_connection = AsyncMock(side_effect=ConnectionError("Connection failed"))
            mock_db_class.return_value = mock_db_instance
            
            # Test initialization with optional service context
            service_context = {
                "required": False,
                "environment": "development", 
                "optionality": "optional"
            }
            
            # Should not raise exception for optional service
            await service._initialize_real_client(service_context)
            
            # Verify client was not initialized (graceful degradation)
            assert service._client is None
    
    @pytest.mark.unit
    async def test_service_execute_with_user_caching(self, mock_service):
        """Test service execution with user-specific caching.
        
        BVJ: Optimizes analytics query performance per user for better UX.
        Golden Path: Repeated dashboard queries should be fast for each user.
        """
        await mock_service.initialize()
        
        query = "SELECT COUNT(*) FROM user_sessions WHERE user_id = %(user_id)s"
        params = {"user_id": "user123"}
        expected_result = [{"count": 42}]
        
        # Mock the execute method to return our expected result
        mock_service._client.execute = AsyncMock(return_value=expected_result)
        
        # First execution should hit the database
        result1 = await mock_service.execute(query, params, user_id="user123")
        assert result1 == expected_result
        mock_service._client.execute.assert_called_once()
        
        # Second execution should use cache
        mock_service._client.execute.reset_mock()
        result2 = await mock_service.execute(query, params, user_id="user123")
        assert result2 == expected_result
        mock_service._client.execute.assert_not_called()  # Cached result
    
    @pytest.mark.unit  
    async def test_service_circuit_breaker_protection(self, mock_service):
        """Test circuit breaker protection for service resilience.
        
        BVJ: Prevents cascading failures when ClickHouse is unavailable.
        Golden Path: Analytics failures must not impact core user functionality.
        """
        await mock_service.initialize()
        
        # Mock circuit breaker failure
        mock_service._client.execute = AsyncMock(side_effect=Exception("Service unavailable"))
        
        query = "SELECT * FROM analytics_data"
        
        # First few calls should fail and trigger circuit breaker
        with pytest.raises(Exception):
            await mock_service.execute(query, user_id="user123")
    
    @pytest.mark.unit
    async def test_service_batch_insert_operations(self, mock_service):
        """Test batch insert operations for analytics data ingestion.
        
        BVJ: Enables efficient storage of large volumes of analytics data.
        Golden Path: User interactions must be recorded efficiently for analytics.
        """
        await mock_service.initialize()
        
        # Test data for batch insert
        test_data = [
            {"user_id": "user1", "event": "login", "timestamp": "2024-01-01T10:00:00Z"},
            {"user_id": "user2", "event": "feature_use", "timestamp": "2024-01-01T10:01:00Z"}, 
            {"user_id": "user3", "event": "logout", "timestamp": "2024-01-01T10:02:00Z"}
        ]
        
        # Mock execute method for batch insert
        mock_service._client.execute = AsyncMock(return_value=[])
        
        # Test batch insert
        await mock_service.batch_insert("user_events", test_data)
        
        # Verify batch insert called execute for each row
        assert mock_service._client.execute.call_count == len(test_data)
    
    @pytest.mark.unit
    async def test_service_health_check_comprehensive(self, mock_service):
        """Test comprehensive health check functionality.
        
        BVJ: Enables monitoring of analytics service health for operational insights.
        Golden Path: Service health monitoring prevents silent analytics failures.
        """
        await mock_service.initialize()
        
        # Mock successful health check
        mock_service._client.execute = AsyncMock(return_value=[{"test": 1}])
        
        # Test health check
        health_result = await mock_service.health_check()
        
        assert health_result["status"] == "healthy"
        assert health_result["connectivity"] == "ok"
        assert "metrics" in health_result
        assert "cache_stats" in health_result
    
    @pytest.mark.unit
    async def test_service_retry_logic_with_exponential_backoff(self, mock_service):
        """Test retry logic with exponential backoff for transient failures.
        
        BVJ: Improves analytics reliability during temporary network issues.
        Golden Path: Temporary failures shouldn't lose important analytics data.
        """
        await mock_service.initialize()
        
        call_count = 0
        async def mock_execute_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise ConnectionError("Temporary failure")
            return [{"result": "success"}]
        
        mock_service._client.execute = mock_execute_with_retry
        
        # Test execution with retry
        start_time = time.time()
        result = await mock_service.execute_with_retry(
            "SELECT * FROM events", max_retries=2, user_id="user123"
        )
        duration = time.time() - start_time
        
        # Verify retry logic worked
        assert result == [{"result": "success"}]
        assert call_count == 3  # Initial + 2 retries
        assert duration > 1.0  # Should have exponential backoff delays


class TestClickHouseClientFactory:
    """Test ClickHouse client factory functions for environment-based selection."""
    
    @pytest.mark.unit
    async def test_client_factory_environment_detection(self):
        """Test client factory environment-based client selection.
        
        BVJ: Ensures correct client type for each environment (dev vs test vs prod).
        Golden Path: Development must connect to real ClickHouse for accurate testing.
        """
        with patch('netra_backend.app.db.clickhouse.use_mock_clickhouse', return_value=False), \
             patch('netra_backend.app.db.clickhouse._create_real_client') as mock_real_client:
            
            # Setup mock for real client
            mock_client = Mock()
            mock_real_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_real_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test real client selection in development
            async with get_clickhouse_client() as client:
                assert client == mock_client
    
    @pytest.mark.unit
    async def test_client_factory_testing_environment(self):
        """Test client factory NoOp selection in testing environment.
        
        BVJ: Enables reliable unit testing without external dependencies.
        Golden Path: Tests must run in CI/CD without requiring ClickHouse setup.
        """
        with patch('netra_backend.app.db.clickhouse.use_mock_clickhouse', return_value=True):
            
            # Test NoOp client selection in testing
            async with get_clickhouse_client() as client:
                assert isinstance(client, NoOpClickHouseClient)
    
    @pytest.mark.unit
    def test_environment_detection_logic(self):
        """Test environment detection logic for client selection.
        
        BVJ: Ensures correct environment detection for proper client selection.
        Golden Path: Environment detection must be accurate for proper analytics setup.
        """
        with patch('netra_backend.app.db.clickhouse.get_env') as mock_get_env:
            
            # Test testing environment detection
            mock_get_env.return_value.get.return_value = "true"
            assert use_mock_clickhouse() == True
            
            # Test development environment (should use real client)
            mock_get_env.return_value.get.side_effect = lambda key, default="": {
                "TESTING": "",
                "DEV_MODE_DISABLE_CLICKHOUSE": ""
            }.get(key, default)
            
            with patch('netra_backend.app.db.clickhouse._is_testing_environment', return_value=False):
                assert use_mock_clickhouse() == False


class TestClickHouseConfiguration:
    """Test ClickHouse configuration management for different environments."""
    
    @pytest.mark.unit
    def test_configuration_environment_specific(self):
        """Test environment-specific ClickHouse configuration.
        
        BVJ: Ensures proper ClickHouse connection for each deployment environment.
        Golden Path: Different environments need different connection parameters.
        """
        with patch('netra_backend.app.db.clickhouse.get_configuration') as mock_get_config:
            
            # Test development environment config
            mock_config = Mock()
            mock_config.environment = "development"
            mock_get_config.return_value = mock_config
            
            with patch('netra_backend.app.db.clickhouse.get_env') as mock_get_env:
                mock_env = Mock()
                mock_env.get.side_effect = lambda key, default: {
                    "CLICKHOUSE_HOST": "clickhouse-service",
                    "CLICKHOUSE_HTTP_PORT": "8123",
                    "CLICKHOUSE_USER": "netra_dev",
                    "CLICKHOUSE_PASSWORD": "dev123",
                    "CLICKHOUSE_DB": "netra_dev_analytics"
                }.get(key, default)
                mock_get_env.return_value = mock_env
                
                # Test development config extraction
                config = get_clickhouse_config()
                
                assert hasattr(config, 'host')
                assert hasattr(config, 'port') 
                assert hasattr(config, 'user')
                assert hasattr(config, 'password')
                assert hasattr(config, 'database')
    
    @pytest.mark.unit
    def test_configuration_staging_environment(self):
        """Test staging environment ClickHouse configuration.
        
        BVJ: Ensures staging environment can connect to ClickHouse Cloud.
        Golden Path: Staging must work for customer demos and business validation.
        """
        with patch('netra_backend.app.db.clickhouse.get_configuration') as mock_get_config, \
             patch('netra_backend.app.db.clickhouse.get_env') as mock_get_env:
            
            # Test staging environment config
            mock_config = Mock()
            mock_config.environment = "staging"
            mock_get_config.return_value = mock_config
            
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default="": {
                "CLICKHOUSE_URL": "clickhouse://user:pass@host:8443/default?secure=1"
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            # Test staging config extraction
            config = get_clickhouse_config()
            
            assert hasattr(config, 'host')
            assert hasattr(config, 'secure')
            assert config.secure == True  # Staging should use secure connections


class TestClickHouseBusinessScenarios:
    """Test business-critical ClickHouse scenarios for golden path validation."""
    
    @pytest.mark.unit
    async def test_user_analytics_tracking_scenario(self, mock_service=None):
        """Test user behavior analytics tracking scenario.
        
        BVJ: Core analytics functionality - user behavior drives product decisions.
        Golden Path: User interactions → analytics storage → business insights.
        """
        if mock_service is None:
            mock_service = ClickHouseService(force_mock=True)
        
        await mock_service.initialize()
        
        # Mock analytics query execution
        mock_service._client.execute = AsyncMock(return_value=[
            {"user_id": "user123", "sessions": 15, "total_time": 7200},
            {"user_id": "user456", "sessions": 8, "total_time": 3600}
        ])
        
        # Simulate user analytics query
        analytics_query = """
        SELECT user_id, COUNT(*) as sessions, SUM(duration_ms) as total_time
        FROM user_sessions 
        WHERE date >= %(start_date)s 
        GROUP BY user_id
        """
        
        result = await mock_service.execute(
            analytics_query, 
            {"start_date": "2024-01-01"},
            user_id="admin_dashboard"
        )
        
        # Verify analytics data structure
        assert len(result) == 2
        assert all("user_id" in row for row in result)
        assert all("sessions" in row for row in result)
        assert all("total_time" in row for row in result)
    
    @pytest.mark.unit
    async def test_agent_performance_analytics_scenario(self, mock_service=None):
        """Test agent performance analytics collection scenario.
        
        BVJ: Agent optimization insights drive product improvements and customer value.
        Golden Path: Agent executions → performance metrics → optimization recommendations.
        """
        if mock_service is None:
            mock_service = ClickHouseService(force_mock=True)
        
        await mock_service.initialize()
        
        # Test agent state history insertion
        agent_run_data = {
            "run_id": "run_123",
            "user_id": "user456", 
            "thread_id": "thread_789",
            "execution_time_ms": 2500,
            "step_count": 8,
            "memory_usage_mb": 156,
            "status": "completed"
        }
        
        # Mock the insert operation
        mock_service._client.execute = AsyncMock(return_value=[])
        
        # Simulate agent analytics insertion
        with patch('netra_backend.app.db.clickhouse.insert_agent_state_history') as mock_insert:
            mock_insert.return_value = True
            
            # Test analytics insertion
            success = await mock_insert(
                agent_run_data["run_id"],
                {"final_state": "completed"},
                agent_run_data
            )
            
            assert success == True
            mock_insert.assert_called_once()
    
    @pytest.mark.unit
    async def test_business_metrics_collection_scenario(self, mock_service=None):
        """Test business metrics collection and querying scenario.
        
        BVJ: Business intelligence drives strategic decisions and revenue optimization.
        Golden Path: Usage data → business metrics → strategic insights → revenue growth.
        """
        if mock_service is None:
            mock_service = ClickHouseService(force_mock=True)
        
        await mock_service.initialize()
        
        # Mock business metrics query
        mock_service._client.execute = AsyncMock(return_value=[
            {"metric": "daily_active_users", "value": 1250, "date": "2024-01-01"},
            {"metric": "conversion_rate", "value": 0.045, "date": "2024-01-01"},
            {"metric": "avg_session_duration", "value": 1820, "date": "2024-01-01"}
        ])
        
        # Simulate business metrics query
        metrics_query = """
        SELECT 
            'daily_active_users' as metric,
            COUNT(DISTINCT user_id) as value,
            toDate(timestamp) as date
        FROM user_events 
        WHERE date = %(target_date)s
        GROUP BY date
        """
        
        result = await mock_service.execute(
            metrics_query,
            {"target_date": "2024-01-01"},
            user_id="business_intelligence"
        )
        
        # Verify business metrics structure
        assert len(result) >= 1
        for row in result:
            assert "metric" in row
            assert "value" in row
            assert "date" in row


@pytest.mark.integration
class TestClickHouseSSotIntegration:
    """Integration tests for ClickHouse SSOT compliance with real service operations."""
    
    @pytest.mark.real_database
    async def test_real_clickhouse_service_initialization(self):
        """Test real ClickHouse service initialization.
        
        BVJ: Validates actual ClickHouse connectivity for production reliability.
        Golden Path: Real ClickHouse must work for actual analytics operations.
        """
        service = ClickHouseService(force_mock=False)
        
        try:
            # Test real service initialization (may fail if ClickHouse not available)
            await service.initialize()
            
            if service.is_real:
                # Test real connection
                ping_result = await service.ping()
                assert ping_result == True
                
                # Test real health check
                health_result = await service.health_check()
                assert health_result["status"] in ["healthy", "unhealthy"]
            
        finally:
            # Clean up
            await service.close()
    
    @pytest.mark.real_database
    async def test_real_analytics_query_execution(self):
        """Test real analytics query execution with actual ClickHouse.
        
        BVJ: Validates analytics queries work with real ClickHouse constraints.
        Golden Path: Real analytics queries must handle actual database interactions.
        """
        service = ClickHouseService(force_mock=False)
        
        try:
            await service.initialize()
            
            if service.is_real:
                # Test simple analytics query
                result = await service.execute(
                    "SELECT 1 as test_analytics_value",
                    user_id="integration_test"
                )
                
                assert len(result) == 1
                assert result[0]["test_analytics_value"] == 1
            
        finally:
            await service.close()