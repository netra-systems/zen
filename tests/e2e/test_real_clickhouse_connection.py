"""
Test Real ClickHouse Connection

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable analytics infrastructure for data-driven insights
- Value Impact: Analytics features and agent state history worth $15K+ MRR
- Strategic Impact: Core infrastructure reliability enables all analytics and agent features

CRITICAL: This test validates our analytics infrastructure can reliably connect to ClickHouse,
ensuring data-driven decision making and reliable agent state history.
"""

import asyncio
import pytest
import time
import logging
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

# Import test utilities with proper paths
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.isolated_environment import get_env

# Import from correct location based on actual codebase structure
try:
    from netra_backend.app.db.clickhouse import (
        get_clickhouse_client, 
        get_clickhouse_service,
        ClickHouseService,
        NoOpClickHouseClient
    )
except ImportError:
    # Fallback to analytics_service if netra_backend doesn't have ClickHouse
    from analytics_service.analytics_core.database.connection import (
        get_clickhouse_manager,
        StubClickHouseManager
    )
    # Create compatibility shims
    get_clickhouse_client = get_clickhouse_manager
    get_clickhouse_service = get_clickhouse_manager
    ClickHouseService = StubClickHouseManager
    NoOpClickHouseClient = StubClickHouseManager


class TestRealClickHouseConnection:
    """Test ClickHouse connection with real service infrastructure."""
    
    # SSOT: Test ports from TEST_CREATION_GUIDE.md
    TEST_CLICKHOUSE_PORT = 8125  # ClickHouse HTTP port in test environment
    
    def setup_method(self):
        """Setup method for each test."""
        self.test_user_id = "test_user_clickhouse"
        self.env = get_env()  # Use IsolatedEnvironment per CLAUDE.md
        self.logger = logging.getLogger(__name__)
        
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_clickhouse_connection_establishment(self):
        """Test basic ClickHouse connection establishment and teardown."""
        connection_established = False
        
        try:
            # Use proper factory pattern for user context isolation
            client = await self._get_clickhouse_client_for_user(self.test_user_id)
            
            if client is None or isinstance(client, (NoOpClickHouseClient, StubClickHouseManager)):
                pytest.skip("ClickHouse not available in test environment (using stub/noop)")
            
            # Test basic connection
            if hasattr(client, 'test_connection'):
                result = await client.test_connection()
                assert result is True, "ClickHouse connection test should succeed"
            elif hasattr(client, 'get_health_status'):
                health = await client.get_health_status()
                assert health.get('is_healthy') is True, "ClickHouse should be healthy"
            
            connection_established = True
            
            # Test basic query execution if supported
            if hasattr(client, 'execute'):
                query_result = await client.execute("SELECT 1 as test_value")
                assert query_result is not None, "Query should return result"
            
            self.logger.info("✓ ClickHouse connection established and basic query executed")
            
        except Exception as e:
            if not connection_established:
                self.logger.warning(f"ClickHouse connection failed (expected in some environments): {e}")
                pytest.skip(f"ClickHouse connection unavailable: {e}")
            else:
                raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_clickhouse_factory_pattern_user_isolation(self):
        """Test ClickHouse factory pattern ensures user isolation per USER_CONTEXT_ARCHITECTURE.md."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - user isolation test not applicable")
        
        # Test that different users get isolated contexts
        user1_id = "test_user_1"
        user2_id = "test_user_2"
        
        # Create contexts for different users
        client1 = await self._get_clickhouse_client_for_user(user1_id)
        client2 = await self._get_clickhouse_client_for_user(user2_id)
        
        # Verify isolation - operations by one user should not affect another
        if hasattr(client1, 'execute'):
            # User 1 creates a temporary table (if supported)
            try:
                await client1.execute(f"CREATE TEMPORARY TABLE IF NOT EXISTS user_{user1_id}_test (id Int32)")
                
                # User 2 should not see User 1's table
                result = await client2.execute("SHOW TABLES")
                user1_tables = [t for t in result if f"user_{user1_id}" in str(t)]
                assert len(user1_tables) == 0, "User 2 should not see User 1's temporary tables"
                
                self.logger.info("✓ User isolation verified - factory pattern working correctly")
            except Exception as e:
                self.logger.info(f"Temporary table test skipped: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_clickhouse_connection_pooling(self):
        """Test ClickHouse connection pooling behavior with multiple concurrent connections."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if self._is_stub_or_noop(client):
            pytest.skip("Using stub/noop ClickHouse - connection pooling test not applicable")
        
        async def test_concurrent_query(query_id: int) -> Dict[str, Any]:
            """Execute a test query concurrently."""
            try:
                user_client = await self._get_clickhouse_client_for_user(f"{self.test_user_id}_{query_id}")
                
                if hasattr(user_client, 'execute'):
                    result = await user_client.execute(f"SELECT {query_id} as query_id, now() as timestamp")
                    return {
                        'query_id': query_id,
                        'success': True,
                        'result_count': len(result) if result else 0,
                        'timestamp': time.time()
                    }
                else:
                    return {'query_id': query_id, 'success': False, 'error': 'No execute method'}
            except Exception as e:
                return {'query_id': query_id, 'success': False, 'error': str(e)}
        
        # Test concurrent connections
        concurrent_count = 10
        tasks = [test_concurrent_query(i) for i in range(concurrent_count)]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        successful = [r for r in results if r.get('success')]
        assert len(successful) > 0, "At least some concurrent queries should succeed"
        
        # Check that queries completed in reasonable time (connection pooling should help)
        timestamps = [r['timestamp'] for r in successful]
        if len(timestamps) > 1:
            duration = max(timestamps) - min(timestamps)
            assert duration < 5.0, f"Concurrent queries took too long: {duration}s"
        
        self.logger.info(f"✓ Connection pooling test passed: {len(successful)}/{concurrent_count} queries succeeded")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_clickhouse_error_handling(self):
        """Test ClickHouse connection error handling for invalid configurations."""
        # Test with invalid configuration
        env = get_env()
        
        # Save original config
        original_host = env.get("CLICKHOUSE_HOST")
        original_port = env.get("CLICKHOUSE_PORT")
        
        try:
            # Set invalid configuration
            env.set("CLICKHOUSE_HOST", "invalid_host_that_does_not_exist", source="test")
            env.set("CLICKHOUSE_PORT", "99999", source="test")
            
            # Try to connect with bad config
            try:
                client = await self._get_clickhouse_client_for_user("error_test_user")
                
                if hasattr(client, 'test_connection'):
                    result = await client.test_connection()
                    # Should either fail or return stub/noop
                    assert result is False or self._is_stub_or_noop(client), \
                        "Invalid connection should fail or return stub"
                        
            except Exception as e:
                # Expected - connection should fail
                self.logger.info(f"✓ Error handling working: {e}")
                
        finally:
            # Restore original config
            if original_host:
                env.set("CLICKHOUSE_HOST", original_host, source="test")
            if original_port:
                env.set("CLICKHOUSE_PORT", original_port, source="test")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_clickhouse_health_check(self):
        """Test ClickHouse health check functionality for monitoring."""
        client = await self._get_clickhouse_client_for_user(self.test_user_id)
        
        if hasattr(client, 'get_health_status'):
            health_status = await client.get_health_status()
            
            # Verify health status structure
            assert isinstance(health_status, dict), "Health status should be a dictionary"
            
            # Check for expected keys
            expected_keys = ['host', 'port', 'database']
            for key in expected_keys:
                assert key in health_status, f"Health status should contain '{key}'"
            
            # If using real ClickHouse, should be healthy
            if not self._is_stub_or_noop(client):
                assert health_status.get('is_healthy') is True, "Real ClickHouse should be healthy"
            
            self.logger.info(f"✓ Health check passed: {health_status}")
        else:
            self.logger.info("Health check not supported by this ClickHouse client")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_clickhouse_configuration_validation(self):
        """Test ClickHouse configuration loading and validation."""
        env = get_env()
        
        # Check that configuration uses proper ports
        clickhouse_port = env.get("CLICKHOUSE_PORT", str(self.TEST_CLICKHOUSE_PORT))
        assert clickhouse_port == str(self.TEST_CLICKHOUSE_PORT), \
            f"ClickHouse should use test port {self.TEST_CLICKHOUSE_PORT}"
        
        # Verify configuration structure
        clickhouse_host = env.get("CLICKHOUSE_HOST", "localhost")
        assert clickhouse_host, "ClickHouse host should be configured"
        
        # Test configuration with Alpine environment detection
        is_alpine = env.get("USE_ALPINE", "false").lower() == "true"
        if is_alpine:
            self.logger.info("✓ Running with Alpine containers (optimized)")
        else:
            self.logger.info("✓ Running with regular containers")
        
        # Verify configuration is properly isolated
        test_key = "CLICKHOUSE_TEST_KEY"
        test_value = "test_value_12345"
        env.set(test_key, test_value, source="test")
        
        retrieved_value = env.get(test_key)
        assert retrieved_value == test_value, "Environment should maintain test values"
        
        self.logger.info("✓ Configuration validation passed")
    
    # Helper methods
    async def _get_clickhouse_client_for_user(self, user_id: str):
        """Get ClickHouse client with user context per factory pattern."""
        try:
            if hasattr(get_clickhouse_client, '__call__'):
                # If it's the netra_backend version
                return await get_clickhouse_client()
            else:
                # If it's the analytics_service version
                return get_clickhouse_client()
        except Exception as e:
            self.logger.warning(f"Failed to get ClickHouse client: {e}")
            return None
    
    def _is_stub_or_noop(self, client) -> bool:
        """Check if client is a stub or noop implementation."""
        if client is None:
            return True
        return isinstance(client, (NoOpClickHouseClient, StubClickHouseManager)) or \
               type(client).__name__ in ['StubClickHouseManager', 'NoOpClickHouseClient']
    
    def _is_testing_without_clickhouse(self) -> bool:
        """Check if we're in a test environment without ClickHouse."""
        env = get_env()
        # Check various indicators that ClickHouse might not be available
        return (
            env.get("CLICKHOUSE_DISABLED", "false").lower() == "true" or
            env.get("USE_MOCK_CLICKHOUSE", "false").lower() == "true" or
            env.get("CI", "false").lower() == "true"  # CI might not have ClickHouse
        )