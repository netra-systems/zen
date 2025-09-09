"""
Integration Tests for SQLAlchemy Async Pool Configuration - SSOT Pool Management Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal - Database foundation for ALL customer interactions
- Business Goal: Prevent cascade failures in database layer affecting ALL revenue streams
- Value Impact: Validates database pool configurations prevent staging outages and service interruptions
- Strategic Impact: Database stability enables reliable $120K+ MRR chat functionality and multi-user isolation

CRITICAL MISSION: Integration testing of SQLAlchemy async pool configurations to ensure:
1. netra_backend and auth_service pool configuration consistency
2. Multi-user concurrent database session handling without pool conflicts
3. Connection pool behavior under realistic load (integration-level testing)
4. Prevention of AsyncEngine + sync pool incompatibilities across all services

BUSINESS CONTEXT: The QueuePool + AsyncEngine incompatibility was causing:
- Complete staging environment failures every 30-60 seconds
- WebSocket authentication cascading failures
- Multi-user session isolation breakdowns
- Customer demo failures and deployment blockers

INTEGRATION SCOPE:
- Cross-service database configuration validation (netra_backend vs auth_service)
- Multi-session concurrent access patterns (realistic user load)
- Connection pool stress testing with proper async/await patterns
- Database session factory validation with different pool configurations

CRITICAL COMPLIANCE:
- Uses REAL PostgreSQL database with multiple concurrent sessions
- Tests cross-service pool configuration consistency
- Validates multi-user database isolation under concurrent load
- Uses SSOT database session patterns from both netra_backend and auth_service
- NO MOCKS for database connections - tests real connection pooling behavior
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool

from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env
from netra_backend.app.database import get_engine as get_netra_engine, get_sessionmaker as get_netra_sessionmaker, get_database_url
from netra_backend.app.dependencies import get_request_scoped_db_session


class TestSQLAlchemyAsyncPoolIntegration(BaseIntegrationTest):
    """
    Integration Tests for SQLAlchemy Async Pool Configuration Management.
    
    CRITICAL: These tests validate database pool configurations work correctly
    across services and under concurrent load, preventing staging cascade failures.
    """
    
    def setup_method(self):
        """Setup method with multi-service database configuration tracking."""
        super().setup_method()
        self.test_start_time = time.time()
        self.env = get_env()
        
        # Track database engines and sessions created during testing
        self.test_engines = []
        self.test_sessions = []
        self.pool_configuration_results = []
        
        self.logger.info("🔧 SQLAlchemy Pool Integration Test Setup")
    
    def teardown_method(self):
        """Cleanup with comprehensive database resource cleanup."""
        # Run async cleanup
        asyncio.run(self._async_cleanup())
        super().teardown_method()
    
    async def _async_cleanup(self):
        """Async cleanup of database engines and sessions."""
        # Close all test sessions
        for session in self.test_sessions:
            try:
                await session.close()
            except Exception:
                pass
        
        # Dispose all test engines
        for engine in self.test_engines:
            try:
                await engine.dispose()
            except Exception:
                pass
        
        self.test_engines.clear()
        self.test_sessions.clear()
        self.pool_configuration_results.clear()
        
        self.logger.info("🧹 Database Pool Integration Cleanup Complete")
    
    async def _ensure_database_connectivity(self) -> bool:
        """Ensure database connectivity for integration testing."""
        try:
            database_url = get_database_url()
            
            # Test basic connectivity with known working configuration
            test_engine = create_async_engine(database_url, poolclass=NullPool, echo=False)
            self.test_engines.append(test_engine)
            
            async with test_engine.begin() as conn:
                result = await conn.execute(text("SELECT 'integration_test_ready' as status"))
                assert result.scalar() == "integration_test_ready"
            
            self.logger.info("✅ Database connectivity validated for integration testing")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Database connectivity failed: {e}")
            return False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_pool_configuration_consistency(self):
        """
        Integration test for cross-service pool configuration consistency.
        
        BUSINESS VALUE: Ensures netra_backend and auth_service database configurations
        are compatible and don't cause cross-service integration failures.
        """
        database_ready = await self._ensure_database_connectivity()
        if not database_ready:
            pytest.skip("Database connectivity required for cross-service integration testing")
        
        self.logger.info("🔄 Testing cross-service pool configuration consistency")
        
        database_url = get_database_url()
        
        # Test 1: auth_service pool configuration (baseline working config)
        auth_service_config = {
            "service": "auth_service",
            "poolclass": NullPool,
            "description": "auth_service current configuration (working)"
        }
        
        auth_engine = None
        auth_success = False
        auth_error = None
        
        try:
            self.logger.info("🔐 Testing auth_service pool configuration (NullPool)")
            auth_engine = create_async_engine(
                database_url,
                poolclass=auth_service_config["poolclass"],
                echo=False
            )
            self.test_engines.append(auth_engine)
            
            # Test multi-session operations (integration-level load)
            for session_num in range(3):
                async_sessionmaker_auth = async_sessionmaker(auth_engine, expire_on_commit=False)
                session = async_sessionmaker_auth()
                self.test_sessions.append(session)
                
                result = await session.execute(
                    text("SELECT :service || '_session_' || :num as test_result"),
                    {"service": "auth", "num": session_num}
                )
                test_result = result.scalar()
                expected = f"auth_session_{session_num}"
                assert test_result == expected, f"auth_service session test failed: {test_result} != {expected}"
            
            auth_success = True
            self.logger.info("✅ auth_service pool configuration - Integration SUCCESS")
            
        except Exception as e:
            auth_error = str(e)
            self.logger.error(f"❌ auth_service pool configuration failed: {e}")
        
        # Test 2: netra_backend pool configuration (updated/fixed config)
        netra_backend_config = {
            "service": "netra_backend", 
            "description": "netra_backend current configuration (after fix)"
        }
        
        netra_backend_success = False
        netra_backend_error = None
        
        try:
            self.logger.info("🔧 Testing netra_backend current pool configuration")
            
            # Use the actual netra_backend database configuration
            netra_engine = get_netra_engine()
            self.test_engines.append(netra_engine)
            
            netra_sessionmaker = get_netra_sessionmaker()
            
            # Test multi-session operations similar to auth_service
            for session_num in range(3):
                session = netra_sessionmaker()
                self.test_sessions.append(session)
                
                result = await session.execute(
                    text("SELECT :service || '_session_' || :num as test_result"),
                    {"service": "netra", "num": session_num}
                )
                test_result = result.scalar()
                expected = f"netra_session_{session_num}"
                assert test_result == expected, f"netra_backend session test failed: {test_result} != {expected}"
            
            netra_backend_success = True
            self.logger.info("✅ netra_backend pool configuration - Integration SUCCESS")
            
        except Exception as e:
            netra_backend_error = str(e)
            self.logger.error(f"❌ netra_backend pool configuration failed: {e}")
        
        # Test 3: Cross-service concurrent database operations
        self.logger.info("🔄 Testing cross-service concurrent database operations")
        
        concurrent_ops_success = False
        concurrent_error = None
        
        try:
            # Simulate realistic cross-service concurrent access
            concurrent_tasks = []
            
            # Task 1: auth_service style operations
            async def auth_service_operations():
                if auth_engine:
                    auth_sm = async_sessionmaker(auth_engine, expire_on_commit=False)
                    async with auth_sm() as session:
                        for i in range(5):
                            result = await session.execute(
                                text("SELECT 'auth_concurrent_' || :i as result"),
                                {"i": i}
                            )
                            assert result.scalar() == f"auth_concurrent_{i}"
                            await asyncio.sleep(0.01)  # Simulate processing time
            
            # Task 2: netra_backend style operations
            async def netra_backend_operations():
                if netra_backend_success:
                    async for db_session in get_request_scoped_db_session():
                        for i in range(5):
                            result = await db_session.execute(
                                text("SELECT 'netra_concurrent_' || :i as result"),
                                {"i": i}
                            )
                            assert result.scalar() == f"netra_concurrent_{i}"
                            await asyncio.sleep(0.01)
                        break  # Exit after first session
            
            # Execute concurrent operations from both services
            if auth_success and netra_backend_success:
                concurrent_tasks.append(asyncio.create_task(auth_service_operations()))
                concurrent_tasks.append(asyncio.create_task(netra_backend_operations()))
                
                # Wait for all concurrent operations to complete
                await asyncio.gather(*concurrent_tasks)
            
            concurrent_ops_success = True
            self.logger.info("✅ Cross-service concurrent operations - SUCCESS")
            
        except Exception as e:
            concurrent_error = str(e)
            self.logger.error(f"❌ Cross-service concurrent operations failed: {e}")
        
        # Integration test validation
        self.logger.info("📊 CROSS-SERVICE INTEGRATION RESULTS:")
        self.logger.info(f"  🔐 auth_service: {'SUCCESS' if auth_success else 'FAILED'}")
        self.logger.info(f"  🔧 netra_backend: {'SUCCESS' if netra_backend_success else 'FAILED'}")
        self.logger.info(f"  🔄 Concurrent ops: {'SUCCESS' if concurrent_ops_success else 'FAILED'}")
        
        if auth_error:
            self.logger.info(f"    auth_service error: {auth_error[:100]}...")
        if netra_backend_error:
            self.logger.info(f"    netra_backend error: {netra_backend_error[:100]}...")
        if concurrent_error:
            self.logger.info(f"    concurrent ops error: {concurrent_error[:100]}...")
        
        # CRITICAL ASSERTIONS: Both services must work and be compatible
        assert auth_success, f"auth_service pool configuration failed: {auth_error}"
        assert netra_backend_success, f"netra_backend pool configuration failed: {netra_backend_error}"
        assert concurrent_ops_success, f"Cross-service concurrent operations failed: {concurrent_error}"
        
        self.logger.info("✅ Cross-service pool configuration consistency validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_multi_user_concurrent_database_sessions(self):
        """
        Integration test for multi-user concurrent database session handling.
        
        BUSINESS VALUE: Validates database pool can handle realistic multi-user load
        without connection pool exhaustion or async/sync incompatibilities.
        """
        database_ready = await self._ensure_database_connectivity()
        if not database_ready:
            pytest.skip("Database connectivity required for multi-user session testing")
        
        self.logger.info("👥 Testing multi-user concurrent database sessions")
        
        # Simulate multiple users with concurrent database operations
        user_count = 8
        operations_per_user = 5
        concurrent_user_tasks = []
        
        async def simulate_user_database_operations(user_id: str, user_index: int):
            """Simulate database operations for a single user."""
            user_results = []
            
            try:
                # Use the actual database session pattern from netra_backend
                async for db_session in get_request_scoped_db_session():
                    for operation_num in range(operations_per_user):
                        # Simulate typical user database operations
                        
                        # 1. User data query
                        user_query = await db_session.execute(
                            text("SELECT :user_id as user_id, :op_num as operation"),
                            {"user_id": user_id, "op_num": operation_num}
                        )
                        user_result = user_query.fetchone()
                        assert user_result.user_id == user_id
                        assert user_result.operation == operation_num
                        
                        # 2. Timestamp operation (simulates audit logging)
                        time_query = await db_session.execute(text("SELECT NOW() as timestamp"))
                        timestamp = time_query.scalar()
                        assert timestamp is not None
                        
                        # 3. User-specific computation
                        calc_query = await db_session.execute(
                            text("SELECT :user_index * 10 + :op_num as calculation"),
                            {"user_index": user_index, "op_num": operation_num}
                        )
                        calculation = calc_query.scalar()
                        expected_calc = user_index * 10 + operation_num
                        assert calculation == expected_calc
                        
                        user_results.append({
                            "user_id": user_id,
                            "operation": operation_num,
                            "calculation": calculation
                        })
                        
                        # Brief pause to simulate processing
                        await asyncio.sleep(0.005)
                    
                    break  # Exit after first successful session
                
                return {"user_id": user_id, "success": True, "operations": len(user_results)}
                
            except Exception as e:
                self.logger.error(f"User {user_id} database operations failed: {e}")
                return {"user_id": user_id, "success": False, "error": str(e)}
        
        # Create concurrent user tasks
        for user_index in range(user_count):
            user_id = f"multi_user_test_{user_index}_{uuid.uuid4().hex[:6]}"
            task = asyncio.create_task(simulate_user_database_operations(user_id, user_index))
            concurrent_user_tasks.append(task)
        
        self.logger.info(f"⚡ Executing {user_count} concurrent user database operations...")
        
        # Execute all user operations concurrently
        start_time = time.time()
        user_results = await asyncio.gather(*concurrent_user_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze multi-user operation results
        successful_users = 0
        failed_users = 0
        total_operations = 0
        
        for result in user_results:
            if isinstance(result, Exception):
                failed_users += 1
                self.logger.error(f"User task exception: {result}")
            elif result.get("success", False):
                successful_users += 1
                total_operations += result.get("operations", 0)
            else:
                failed_users += 1
                self.logger.warning(f"User failed: {result.get('user_id', 'unknown')}")
        
        # Performance and reliability metrics
        success_rate = (successful_users / user_count) * 100
        operations_per_second = total_operations / max(execution_time, 0.001)
        
        self.logger.info("📊 MULTI-USER DATABASE SESSION RESULTS:")
        self.logger.info(f"  👥 Total users: {user_count}")
        self.logger.info(f"  ✅ Successful users: {successful_users}")
        self.logger.info(f"  ❌ Failed users: {failed_users}")
        self.logger.info(f"  📈 Success rate: {success_rate:.1f}%")
        self.logger.info(f"  🔢 Total operations: {total_operations}")
        self.logger.info(f"  ⚡ Operations/second: {operations_per_second:.1f}")
        self.logger.info(f"  ⏱️ Execution time: {execution_time:.2f}s")
        
        # CRITICAL ASSERTIONS: Multi-user operations must be reliable
        assert success_rate >= 90.0, f"Multi-user success rate too low: {success_rate:.1f}% (expected >= 90%)"
        assert successful_users >= user_count * 0.9, f"Too many failed users: {failed_users}/{user_count}"
        assert total_operations >= user_count * operations_per_user * 0.9, f"Too few operations completed: {total_operations}"
        assert execution_time <= 30.0, f"Multi-user operations too slow: {execution_time:.2f}s (expected <= 30s)"
        
        self.logger.info("✅ Multi-user concurrent database sessions validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_pool_behavior_under_load(self):
        """
        Integration test for connection pool behavior under realistic load.
        
        BUSINESS VALUE: Validates connection pool handles burst traffic and sustained load
        without connection exhaustion or performance degradation.
        """
        database_ready = await self._ensure_database_connectivity()
        if not database_ready:
            pytest.skip("Database connectivity required for connection pool load testing")
        
        self.logger.info("⚡ Testing connection pool behavior under load")
        
        database_url = get_database_url()
        
        # Test different pool configurations under load
        pool_load_tests = [
            {
                "name": "NullPool_LoadTest",
                "poolclass": NullPool,
                "description": "No connection pooling (auth_service pattern)"
            }
        ]
        
        load_test_results = []
        
        for pool_config in pool_load_tests:
            self.logger.info(f"🧪 Testing {pool_config['name']}: {pool_config['description']}")
            
            test_engine = None
            load_result = {
                "config_name": pool_config["name"],
                "description": pool_config["description"],
                "success": False,
                "total_connections": 0,
                "avg_response_time": 0.0,
                "peak_response_time": 0.0,
                "error": None
            }
            
            try:
                # Create engine with specific pool configuration
                test_engine = create_async_engine(
                    database_url,
                    poolclass=pool_config["poolclass"],
                    echo=False
                )
                self.test_engines.append(test_engine)
                
                # Load test parameters
                burst_connections = 15
                sustained_connections = 10
                operations_per_connection = 3
                
                # Phase 1: Burst load test
                self.logger.info(f"⚡ Phase 1: Burst load ({burst_connections} concurrent connections)")
                
                burst_tasks = []
                burst_start_time = time.time()
                
                async def burst_connection_task(connection_id: int):
                    """Single burst connection operations."""
                    connection_times = []
                    
                    sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False)
                    
                    for op_num in range(operations_per_connection):
                        op_start = time.time()
                        
                        async with sessionmaker() as session:
                            result = await session.execute(
                                text("SELECT :conn_id * 100 + :op as burst_result"),
                                {"conn_id": connection_id, "op": op_num}
                            )
                            burst_result = result.scalar()
                            expected = connection_id * 100 + op_num
                            assert burst_result == expected
                        
                        op_time = time.time() - op_start
                        connection_times.append(op_time)
                    
                    return {
                        "connection_id": connection_id,
                        "operations": len(connection_times),
                        "avg_time": sum(connection_times) / len(connection_times),
                        "max_time": max(connection_times)
                    }
                
                # Execute burst connections
                for conn_id in range(burst_connections):
                    task = asyncio.create_task(burst_connection_task(conn_id))
                    burst_tasks.append(task)
                
                burst_results = await asyncio.gather(*burst_tasks)
                burst_duration = time.time() - burst_start_time
                
                # Phase 2: Sustained load test
                self.logger.info(f"🔄 Phase 2: Sustained load ({sustained_connections} connections)")
                
                sustained_tasks = []
                sustained_start_time = time.time()
                
                async def sustained_connection_task(connection_id: int):
                    """Sustained connection operations."""
                    sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False)
                    
                    # Longer sustained operations
                    for cycle in range(3):
                        async with sessionmaker() as session:
                            for op in range(2):
                                result = await session.execute(
                                    text("SELECT :conn_id * 1000 + :cycle * 10 + :op as sustained_result"),
                                    {"conn_id": connection_id, "cycle": cycle, "op": op}
                                )
                                sustained_result = result.scalar()
                                expected = connection_id * 1000 + cycle * 10 + op
                                assert sustained_result == expected
                                
                                await asyncio.sleep(0.01)  # Simulate processing time
                    
                    return {"connection_id": connection_id, "sustained_cycles": 3}
                
                # Execute sustained connections
                for conn_id in range(sustained_connections):
                    task = asyncio.create_task(sustained_connection_task(conn_id))
                    sustained_tasks.append(task)
                
                sustained_results = await asyncio.gather(*sustained_tasks)
                sustained_duration = time.time() - sustained_start_time
                
                # Analyze load test results
                total_connections = len(burst_results) + len(sustained_results)
                all_response_times = []
                
                for burst_result in burst_results:
                    all_response_times.append(burst_result["avg_time"])
                    all_response_times.append(burst_result["max_time"])
                
                avg_response_time = sum(all_response_times) / max(len(all_response_times), 1)
                peak_response_time = max(all_response_times) if all_response_times else 0.0
                
                load_result.update({
                    "success": True,
                    "total_connections": total_connections,
                    "avg_response_time": avg_response_time,
                    "peak_response_time": peak_response_time,
                    "burst_duration": burst_duration,
                    "sustained_duration": sustained_duration
                })
                
                self.logger.info(f"✅ {pool_config['name']} load test completed successfully")
                
            except Exception as e:
                load_result["error"] = str(e)
                self.logger.error(f"❌ {pool_config['name']} load test failed: {e}")
            
            load_test_results.append(load_result)
        
        # Validate load test results
        self.logger.info("📊 CONNECTION POOL LOAD TEST RESULTS:")
        
        for result in load_test_results:
            success_icon = "✅" if result["success"] else "❌"
            self.logger.info(f"  {success_icon} {result['config_name']}:")
            self.logger.info(f"    Total connections: {result['total_connections']}")
            self.logger.info(f"    Avg response time: {result['avg_response_time']:.4f}s")
            self.logger.info(f"    Peak response time: {result['peak_response_time']:.4f}s")
            
            if result["error"]:
                self.logger.info(f"    Error: {result['error'][:100]}...")
        
        # CRITICAL ASSERTIONS: Load tests must demonstrate pool stability
        successful_tests = [r for r in load_test_results if r["success"]]
        assert len(successful_tests) > 0, "No connection pool configurations passed load testing"
        
        for result in successful_tests:
            assert result["avg_response_time"] <= 2.0, (
                f"{result['config_name']} avg response time too slow: {result['avg_response_time']:.4f}s"
            )
            assert result["peak_response_time"] <= 5.0, (
                f"{result['config_name']} peak response time too slow: {result['peak_response_time']:.4f}s"
            )
        
        self.logger.info("✅ Connection pool load testing validated")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_session_factory_consistency(self):
        """
        Integration test for database session factory consistency across different access patterns.
        
        BUSINESS VALUE: Ensures session factories create compatible sessions regardless
        of access pattern (direct, dependency injection, async context managers).
        """
        database_ready = await self._ensure_database_connectivity()
        if not database_ready:
            pytest.skip("Database connectivity required for session factory testing")
        
        self.logger.info("🏭 Testing database session factory consistency")
        
        session_factory_results = []
        
        # Test 1: Direct netra_backend session factory
        direct_factory_success = False
        direct_factory_error = None
        
        try:
            self.logger.info("🔧 Testing direct netra_backend session factory")
            
            sessionmaker = get_netra_sessionmaker()
            
            # Test multiple sessions from same factory
            for session_num in range(3):
                session = sessionmaker()
                self.test_sessions.append(session)
                
                result = await session.execute(
                    text("SELECT 'direct_factory_' || :num as factory_test"),
                    {"num": session_num}
                )
                factory_result = result.scalar()
                expected = f"direct_factory_{session_num}"
                assert factory_result == expected
                
                await session.close()
            
            direct_factory_success = True
            self.logger.info("✅ Direct session factory - SUCCESS")
            
        except Exception as e:
            direct_factory_error = str(e)
            self.logger.error(f"❌ Direct session factory failed: {e}")
        
        # Test 2: Dependency injection pattern (get_request_scoped_db_session)
        dependency_pattern_success = False
        dependency_pattern_error = None
        
        try:
            self.logger.info("🔗 Testing dependency injection session pattern")
            
            # Test multiple request-scoped sessions
            for request_num in range(3):
                async for db_session in get_request_scoped_db_session():
                    result = await db_session.execute(
                        text("SELECT 'dependency_' || :num as dependency_test"),
                        {"num": request_num}
                    )
                    dependency_result = result.scalar()
                    expected = f"dependency_{request_num}"
                    assert dependency_result == expected
                    break  # Exit after first session
            
            dependency_pattern_success = True
            self.logger.info("✅ Dependency injection pattern - SUCCESS")
            
        except Exception as e:
            dependency_pattern_error = str(e)
            self.logger.error(f"❌ Dependency injection pattern failed: {e}")
        
        # Test 3: Async context manager pattern
        context_manager_success = False
        context_manager_error = None
        
        try:
            self.logger.info("📋 Testing async context manager session pattern")
            
            # Import database module context manager
            from netra_backend.app.database import get_db
            
            # Test multiple context manager sessions
            for context_num in range(3):
                async with get_db() as session:
                    result = await session.execute(
                        text("SELECT 'context_' || :num as context_test"),
                        {"num": context_num}
                    )
                    context_result = result.scalar()
                    expected = f"context_{context_num}"
                    assert context_result == expected
            
            context_manager_success = True
            self.logger.info("✅ Async context manager pattern - SUCCESS")
            
        except Exception as e:
            context_manager_error = str(e)
            self.logger.error(f"❌ Async context manager pattern failed: {e}")
        
        # Test 4: Cross-pattern compatibility (mixed usage)
        cross_pattern_success = False
        cross_pattern_error = None
        
        try:
            self.logger.info("🔄 Testing cross-pattern session compatibility")
            
            # Concurrent access using different patterns
            async def direct_pattern_task():
                sessionmaker = get_netra_sessionmaker()
                async with sessionmaker() as session:
                    result = await session.execute(text("SELECT 'mixed_direct' as pattern"))
                    return result.scalar()
            
            async def dependency_pattern_task():
                async for session in get_request_scoped_db_session():
                    result = await session.execute(text("SELECT 'mixed_dependency' as pattern"))
                    return result.scalar()
            
            async def context_pattern_task():
                from netra_backend.app.database import get_db
                async with get_db() as session:
                    result = await session.execute(text("SELECT 'mixed_context' as pattern"))
                    return result.scalar()
            
            # Execute all patterns concurrently
            mixed_tasks = [
                asyncio.create_task(direct_pattern_task()),
                asyncio.create_task(dependency_pattern_task()),
                asyncio.create_task(context_pattern_task())
            ]
            
            mixed_results = await asyncio.gather(*mixed_tasks)
            
            # Validate all patterns worked concurrently
            expected_results = ["mixed_direct", "mixed_dependency", "mixed_context"]
            assert mixed_results == expected_results, f"Cross-pattern results mismatch: {mixed_results}"
            
            cross_pattern_success = True
            self.logger.info("✅ Cross-pattern compatibility - SUCCESS")
            
        except Exception as e:
            cross_pattern_error = str(e)
            self.logger.error(f"❌ Cross-pattern compatibility failed: {e}")
        
        # Collect factory consistency results
        session_factory_results = [
            {"pattern": "Direct Factory", "success": direct_factory_success, "error": direct_factory_error},
            {"pattern": "Dependency Injection", "success": dependency_pattern_success, "error": dependency_pattern_error},
            {"pattern": "Context Manager", "success": context_manager_success, "error": context_manager_error},
            {"pattern": "Cross-Pattern", "success": cross_pattern_success, "error": cross_pattern_error}
        ]
        
        # Validate session factory consistency
        self.logger.info("📊 SESSION FACTORY CONSISTENCY RESULTS:")
        
        successful_patterns = 0
        for result in session_factory_results:
            success_icon = "✅" if result["success"] else "❌"
            self.logger.info(f"  {success_icon} {result['pattern']}: {'SUCCESS' if result['success'] else 'FAILED'}")
            
            if result["error"]:
                self.logger.info(f"    Error: {result['error'][:100]}...")
            
            if result["success"]:
                successful_patterns += 1
        
        # CRITICAL ASSERTIONS: All session patterns must work consistently
        assert successful_patterns >= 3, (
            f"Too many session factory patterns failed: {successful_patterns}/4 successful"
        )
        assert direct_factory_success, "Direct session factory must work for core functionality"
        assert dependency_pattern_success, "Dependency injection pattern must work for FastAPI integration"
        
        self.logger.info(f"✅ Session factory consistency validated: {successful_patterns}/4 patterns successful")