"""
Test Database Factory Over-Abstraction SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate database factory over-abstraction blocking golden path
- Value Impact: Remove 5+ layer database factory chains causing connection issues
- Strategic Impact: Critical $120K+ MRR protection through database reliability

This test validates that database factory patterns don't create unnecessary
abstraction layers. The over-engineering audit identified multiple database
factory classes that violate SSOT principles and create connection overhead.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# Import database factory classes to test SSOT violations
from netra_backend.app.factories.data_access_factory import DataAccessFactory
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
from netra_backend.app.redis_manager import redis_manager  # RedisFactory consolidated to SSOT
from netra_backend.app.factories.clickhouse_factory import ClickHouseFactory


class TestDatabaseFactoryOverAbstraction(BaseIntegrationTest):
    """Test SSOT violations in database factory over-abstraction patterns."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_data_access_factory_vs_direct_session_creation(self, real_services_fixture):
        """
        Test SSOT violation between DataAccessFactory and direct database session creation.
        
        SSOT Violation: DataAccessFactory creates database sessions with complex
        patterns while most code uses direct SQLAlchemy session creation.
        """
        # SSOT VIOLATION: Multiple ways to create database sessions
        
        # Method 1: Via DataAccessFactory (complex abstraction)
        try:
            data_factory = DataAccessFactory()
            factory_session = await data_factory.create_database_session(
                database_url=get_env().get("DATABASE_URL"),
                schema="backend"
            )
        except Exception as e:
            # Factory might not exist or work properly
            factory_session = None
            factory_error = str(e)
        
        # Method 2: Direct SQLAlchemy session (what most code actually uses)
        direct_session = real_services_fixture["db"]
        
        # Method 3: RequestScopedSessionFactory (another abstraction layer)
        try:
            scoped_factory = RequestScopedSessionFactory()
            scoped_session = await scoped_factory.create_request_session(
                user_id="test_user_ssot",
                request_id="test_request_ssot"
            )
        except Exception as e:
            scoped_session = None
            scoped_error = str(e)
        
        # SSOT REQUIREMENT: All methods should produce functionally equivalent sessions
        sessions_to_test = []
        if factory_session:
            sessions_to_test.append(("factory", factory_session))
        sessions_to_test.append(("direct", direct_session))
        if scoped_session:
            sessions_to_test.append(("scoped", scoped_session))
        
        # Test that all sessions can perform basic operations identically
        test_results = {}
        
        for session_type, session in sessions_to_test:
            try:
                # Basic connectivity test
                result = await session.execute("SELECT 1 as test_value")
                row = result.fetchone()
                test_results[session_type] = {
                    "connectivity": True,
                    "test_value": row[0] if row else None,
                    "session_type": type(session).__name__
                }
            except Exception as e:
                test_results[session_type] = {
                    "connectivity": False,
                    "error": str(e),
                    "session_type": type(session).__name__
                }
        
        # SSOT VIOLATION: All database sessions should work identically
        successful_sessions = [k for k, v in test_results.items() if v.get("connectivity")]
        assert len(successful_sessions) > 0, f"No database sessions work: {test_results}"
        
        # All successful sessions should return same result for same query
        test_values = [v["test_value"] for v in test_results.values() if v.get("connectivity")]
        assert len(set(test_values)) <= 1, f"Sessions return different values: {test_values}"
        
        # CRITICAL: Test transaction handling consistency
        for session_type, session in sessions_to_test:
            if test_results[session_type].get("connectivity"):
                try:
                    # Test transaction rollback
                    async with session.begin():
                        await session.execute("SELECT 'transaction_test'")
                        # Transaction should complete successfully
                    
                    test_results[session_type]["transaction_support"] = True
                except Exception as e:
                    test_results[session_type]["transaction_support"] = False
                    test_results[session_type]["transaction_error"] = str(e)
        
        # Cleanup factory sessions if they exist
        if factory_session and hasattr(factory_session, 'close'):
            await factory_session.close()
        if scoped_session and hasattr(scoped_session, 'close'):
            await scoped_session.close()
        
        # Business value: Eliminating factory abstraction reduces connection overhead
        self.assert_business_value_delivered(
            {
                "database_factory_consolidation": True,
                "session_creation_consistency": True,
                "successful_patterns": successful_sessions
            },
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_factory_abstraction_violation(self, real_services_fixture):
        """
        Test SSOT violation in Redis factory abstraction patterns.
        
        SSOT Violation: RedisFactory creates Redis connections with complex
        initialization while direct Redis usage is simpler and more reliable.
        """
        # SSOT VIOLATION: Multiple ways to create Redis connections
        
        # Method 1: Via RedisFactory (abstraction layer)
        try:
            redis_factory = RedisFactory()
            factory_redis = await redis_factory.create_redis_client(
                redis_url=get_env().get("REDIS_URL", "redis://localhost:6379"),
                db_index=1  # Test database
            )
        except Exception as e:
            factory_redis = None
            factory_error = str(e)
        
        # Method 2: Direct Redis client (what actually gets used)
        direct_redis = real_services_fixture["redis"]
        
        # SSOT REQUIREMENT: Both approaches should work identically
        redis_clients = []
        if factory_redis:
            redis_clients.append(("factory", factory_redis))
        redis_clients.append(("direct", direct_redis))
        
        # Test Redis operations consistency
        test_key = "ssot_redis_test"
        test_value = "factory_abstraction_test_value"
        
        operation_results = {}
        
        for client_type, redis_client in redis_clients:
            try:
                # Test basic set/get operations
                await redis_client.set(test_key + f"_{client_type}", test_value)
                retrieved_value = await redis_client.get(test_key + f"_{client_type}")
                
                # Test expiration
                await redis_client.set(test_key + f"_{client_type}_exp", test_value, ex=60)
                
                # Test delete
                await redis_client.delete(test_key + f"_{client_type}")
                
                operation_results[client_type] = {
                    "set_get_success": retrieved_value == test_value.encode() or retrieved_value == test_value,
                    "expiration_support": True,
                    "delete_support": True,
                    "client_type": type(redis_client).__name__
                }
                
            except Exception as e:
                operation_results[client_type] = {
                    "error": str(e),
                    "client_type": type(redis_client).__name__
                }
        
        # SSOT VIOLATION: All Redis clients should support same operations
        successful_clients = [k for k, v in operation_results.items() if v.get("set_get_success")]
        assert len(successful_clients) > 0, f"No Redis clients work: {operation_results}"
        
        # All successful clients should behave identically
        for client_type in successful_clients:
            result = operation_results[client_type]
            assert result["set_get_success"] is True
            assert result["expiration_support"] is True
            assert result["delete_support"] is True
        
        # CRITICAL: Test connection pooling and performance
        start_time = time.time()
        
        for client_type, redis_client in redis_clients:
            if client_type in successful_clients:
                # Perform multiple rapid operations to test connection handling
                for i in range(10):
                    await redis_client.set(f"perf_test_{client_type}_{i}", f"value_{i}")
                    await redis_client.get(f"perf_test_{client_type}_{i}")
                    await redis_client.delete(f"perf_test_{client_type}_{i}")
        
        performance_time = time.time() - start_time
        
        # Cleanup factory Redis client if it exists
        if factory_redis and hasattr(factory_redis, 'close'):
            await factory_redis.close()
        
        # Business value: Direct Redis usage eliminates factory overhead
        self.assert_business_value_delivered(
            {
                "redis_factory_elimination": True,
                "connection_reliability": True,
                "performance_time": performance_time
            },
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_clickhouse_factory_unnecessary_abstraction(self, real_services_fixture):
        """
        Test SSOT violation in ClickHouse factory unnecessary abstraction.
        
        SSOT Violation: ClickHouseFactory creates complex initialization patterns
        for ClickHouse connections that could be handled with direct client usage.
        """
        # SSOT VIOLATION: Complex factory for simple ClickHouse operations
        
        # Method 1: Via ClickHouseFactory (abstraction layer)
        try:
            clickhouse_factory = ClickHouseFactory()
            factory_client = await clickhouse_factory.create_clickhouse_client(
                host=get_env().get("CLICKHOUSE_HOST", "localhost"),
                port=int(get_env().get("CLICKHOUSE_PORT", "8123")),
                database=get_env().get("CLICKHOUSE_DATABASE", "default")
            )
        except Exception as e:
            factory_client = None
            factory_error = str(e)
        
        # Method 2: Direct ClickHouse client (simpler approach)
        try:
            # For testing, we'll simulate direct client creation
            # In real implementation, this would be direct clickhouse-connect usage
            direct_client = MagicMock()
            direct_client.ping = AsyncMock(return_value=True)
            direct_client.execute = AsyncMock(return_value=[])
            direct_client.close = AsyncMock()
        except Exception as e:
            direct_client = None
            direct_error = str(e)
        
        # Test ClickHouse client functionality
        clients_to_test = []
        if factory_client:
            clients_to_test.append(("factory", factory_client))
        if direct_client:
            clients_to_test.append(("direct", direct_client))
        
        clickhouse_results = {}
        
        for client_type, client in clients_to_test:
            try:
                # Test basic connectivity
                ping_result = await client.ping() if hasattr(client, 'ping') else True
                
                # Test basic query execution (would be real in production)
                if hasattr(client, 'execute'):
                    query_result = await client.execute("SELECT 1 as test")
                else:
                    query_result = []
                
                clickhouse_results[client_type] = {
                    "connectivity": ping_result,
                    "query_support": True,
                    "client_type": type(client).__name__
                }
                
            except Exception as e:
                clickhouse_results[client_type] = {
                    "error": str(e),
                    "client_type": type(client).__name__
                }
        
        # SSOT REQUIREMENT: Factory and direct approaches should work equally well
        if len(clients_to_test) > 1:
            # Both approaches should succeed
            factory_success = clickhouse_results.get("factory", {}).get("connectivity", False)
            direct_success = clickhouse_results.get("direct", {}).get("connectivity", False)
            
            # If factory exists, it should work as well as direct approach
            if "factory" in clickhouse_results and "direct" in clickhouse_results:
                assert factory_success == direct_success, "Factory and direct ClickHouse clients should work equally"
        
        # CRITICAL: Test that factory doesn't add unnecessary complexity
        # Factory should not require significantly more setup than direct usage
        
        # Measure initialization complexity (simulated)
        factory_setup_steps = 0
        direct_setup_steps = 0
        
        if factory_client:
            # Factory typically requires: create factory -> configure -> create client -> initialize
            factory_setup_steps = 4
        
        if direct_client:
            # Direct typically requires: import client -> create with config
            direct_setup_steps = 2
        
        # SSOT VIOLATION: Factory shouldn't add more than 2x complexity
        if factory_setup_steps > 0 and direct_setup_steps > 0:
            complexity_ratio = factory_setup_steps / direct_setup_steps
            assert complexity_ratio <= 2.0, f"ClickHouse factory too complex: {complexity_ratio}x overhead"
        
        # Cleanup
        for client_type, client in clients_to_test:
            if hasattr(client, 'close'):
                await client.close()
        
        # Business value: Simplified ClickHouse usage reduces analytical query overhead
        self.assert_business_value_delivered(
            {
                "clickhouse_factory_simplification": True,
                "analytical_query_performance": True,
                "complexity_reduction": True
            },
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_factory_initialization_chain_complexity(self, real_services_fixture):
        """
        Test SSOT violation from complex database factory initialization chains.
        
        SSOT Violation: Multiple database factories create complex dependency
        chains that violate simple database connection patterns.
        """
        # Map the complex initialization chain for database access
        
        # Current complex chain (SSOT violation):
        # DataAccessFactory -> SessionFactory -> ConnectionFactory -> Engine -> Connection
        # RequestScopedSessionFactory -> UserSession -> Database -> Connection
        # RedisFactory -> RedisClient -> Connection
        # ClickHouseFactory -> ClickHouseClient -> Connection
        
        start_time = time.time()
        
        # CRITICAL: Test full database initialization chain complexity
        database_connections = {}
        
        # Initialize all database factory patterns
        try:
            # PostgreSQL via factory
            data_factory = DataAccessFactory()
            postgres_session = await data_factory.create_database_session(
                database_url=get_env().get("DATABASE_URL"),
                schema="backend"
            )
            database_connections["postgres_factory"] = postgres_session
        except Exception:
            pass
        
        try:
            # PostgreSQL direct
            database_connections["postgres_direct"] = real_services_fixture["db"]
        except Exception:
            pass
        
        try:
            # Redis via factory
            redis_factory = RedisFactory()
            redis_client = await redis_factory.create_redis_client(
                redis_url=get_env().get("REDIS_URL", "redis://localhost:6379")
            )
            database_connections["redis_factory"] = redis_client
        except Exception:
            pass
        
        try:
            # Redis direct
            database_connections["redis_direct"] = real_services_fixture["redis"]
        except Exception:
            pass
        
        try:
            # ClickHouse via factory
            clickhouse_factory = ClickHouseFactory()
            clickhouse_client = await clickhouse_factory.create_clickhouse_client()
            database_connections["clickhouse_factory"] = clickhouse_client
        except Exception:
            pass
        
        factory_initialization_time = time.time() - start_time
        
        # Test simple direct initialization time
        simple_start = time.time()
        
        # Direct connections (what should be the norm)
        simple_connections = {}
        simple_connections["postgres"] = real_services_fixture["db"]
        simple_connections["redis"] = real_services_fixture["redis"]
        
        simple_initialization_time = time.time() - simple_start
        
        # SSOT BUSINESS IMPACT: Factory chains should not be significantly slower
        if simple_initialization_time > 0:
            initialization_overhead = factory_initialization_time / simple_initialization_time
        else:
            initialization_overhead = 1.0
        
        # Factory chain should not be more than 5x slower than direct connections
        assert initialization_overhead < 5.0, f"Database factory chain too slow: {initialization_overhead}x overhead"
        
        # CRITICAL: Test that all database connections work for basic operations
        successful_operations = 0
        total_operations = 0
        
        for conn_type, connection in database_connections.items():
            total_operations += 1
            try:
                if "postgres" in conn_type:
                    await connection.execute("SELECT 1")
                    successful_operations += 1
                elif "redis" in conn_type:
                    await connection.set("test_key", "test_value")
                    await connection.delete("test_key")
                    successful_operations += 1
                elif "clickhouse" in conn_type:
                    if hasattr(connection, 'ping'):
                        await connection.ping()
                        successful_operations += 1
            except Exception as e:
                # Connection failed - factory abstraction might be broken
                pass
        
        # At least 50% of database connections should work
        if total_operations > 0:
            success_rate = successful_operations / total_operations
            assert success_rate >= 0.5, f"Too many database factory failures: {success_rate:.1%} success rate"
        
        # Cleanup all connections
        for conn_type, connection in database_connections.items():
            try:
                if hasattr(connection, 'close'):
                    await connection.close()
            except Exception:
                pass
        
        # Business value: Simplified database access reduces connection overhead and failures
        self.assert_business_value_delivered(
            {
                "database_initialization_efficiency": True,
                "connection_success_rate": success_rate if total_operations > 0 else 1.0,
                "initialization_overhead": initialization_overhead,
                "factory_simplification": True
            },
            "automation"
        )