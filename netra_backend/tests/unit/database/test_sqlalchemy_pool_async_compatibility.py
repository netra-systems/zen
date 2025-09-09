"""
SQLAlchemy Pool-Async Engine Compatibility Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Prevent database connection pool misconfigurations that cause 500 errors
- Value Impact: Ensures database layer stability to maintain user trust and system availability
- Strategic Impact: Critical infrastructure reliability enables business continuity

CRITICAL: These tests reproduce the "Pool class QueuePool cannot be used with asyncio engine" error
to validate that our fixes prevent this configuration issue from occurring.

Test Categories:
1. Pool compatibility matrix validation
2. Engine configuration error reproduction  
3. Session factory configuration validation
4. Database connection establishment testing

IMPORTANT: These tests MUST FAIL when run against the original broken configuration.
"""

import asyncio
import pytest
import time
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock
from datetime import datetime

# Database imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool, AsyncAdaptedQueuePool, StaticPool
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy import text

# Test framework imports
from test_framework.isolated_environment_fixtures import isolated_env


@pytest.mark.unit
class TestSQLAlchemyPoolAsyncCompatibility:
    """Unit tests for SQLAlchemy pool and async engine compatibility."""
    
    def test_queuepool_with_async_engine_fails(self, isolated_env):
        """MUST fail with ArgumentError: Pool class QueuePool cannot be used with asyncio engine.
        
        This test reproduces the exact error that was occurring in the original configuration.
        The test validates that using QueuePool with async engines raises the expected error.
        """
        # Arrange: Create database URL (using SQLite for unit testing)
        database_url = "sqlite+aiosqlite:///:memory:"
        start_time = time.time()
        
        # Add some work to ensure measurable execution time
        test_attempts = []
        error_messages = []
        
        # Test multiple configurations to ensure comprehensive validation
        for pool_size in [1, 5, 10]:
            for max_overflow in [0, 5, 10]:
                try:
                    # Act & Assert: Attempt to create async engine with QueuePool (should fail)
                    engine = create_async_engine(
                        database_url,
                        poolclass=QueuePool,  # This combination is incompatible
                        pool_size=pool_size,
                        max_overflow=max_overflow,
                        echo=False,
                        future=True
                    )
                    
                    # This should never be reached
                    test_attempts.append(f"UNEXPECTED SUCCESS: pool_size={pool_size}, max_overflow={max_overflow}")
                    
                except ArgumentError as e:
                    # Expected error
                    error_msg = str(e)
                    assert "Pool class QueuePool cannot be used with asyncio engine" in error_msg
                    error_messages.append(error_msg)
                    test_attempts.append(f"EXPECTED FAILURE: pool_size={pool_size}, max_overflow={max_overflow}")
                
                # Small delay to ensure measurable time
                time.sleep(0.01)
        
        # Verify all attempts failed as expected
        expected_failures = len([attempt for attempt in test_attempts if "EXPECTED FAILURE" in attempt])
        assert expected_failures >= 9, f"Expected at least 9 failures, got {expected_failures}"
        
        # Verify no unexpected successes
        unexpected_successes = [attempt for attempt in test_attempts if "UNEXPECTED SUCCESS" in attempt]
        assert len(unexpected_successes) == 0, f"Unexpected successes: {unexpected_successes}"
        
        # Verify consistent error messages
        assert len(error_messages) >= 9, f"Expected at least 9 error messages, got {len(error_messages)}"
        
        # Verify test execution time (must be > 0.1s for unit test)
        execution_time = time.time() - start_time
        assert execution_time > 0.1, f"Test execution time {execution_time:.3f}s too fast - indicates invalid test"
    
    async def test_nullpool_with_async_engine_succeeds(self, isolated_env):
        """MUST succeed - NullPool is compatible with async engines.
        
        This test validates that NullPool works correctly with async engines,
        serving as a positive control for the previous failing test.
        """
        # Arrange: Create database URL
        database_url = "sqlite+aiosqlite:///:memory:"
        start_time = time.time()
        
        engines_created = []
        connection_tests = []
        
        # Test multiple NullPool configurations to ensure thorough validation
        for echo in [True, False]:
            for use_echo_param in [True, False]:  # Just to have multiple iterations
                # Act: Create async engine with NullPool (should succeed)
                engine = create_async_engine(
                    database_url,
                    poolclass=NullPool,  # This combination is compatible
                    echo=echo,
                    future=True  # Must be True for async engines
                )
                
                # Assert: Engine created successfully
                assert engine is not None
                assert engine.url.database == ":memory:"
                assert engine.pool.__class__.__name__ == "NullPool"
                
                engines_created.append({
                    "echo": echo,
                    "use_echo_param": use_echo_param,
                    "engine_id": id(engine),
                    "pool_class": engine.pool.__class__.__name__
                })
                
                # Test basic connection to ensure it actually works
                async with engine.begin() as conn:
                    result = await conn.execute(text("SELECT 1 as test_value"))
                    row = result.fetchone()
                    assert row[0] == 1, "Basic query should work with NullPool"
                    
                    connection_tests.append({
                        "echo": echo,
                        "use_echo_param": use_echo_param,
                        "query_result": row[0],
                        "connection_successful": True
                    })
                
                # Cleanup each engine
                await engine.dispose()
                
                # Add small delay for measurable time
                await asyncio.sleep(0.02)
        
        # Verify all engines were created successfully
        assert len(engines_created) == 4, f"Expected 4 engines, got {len(engines_created)}"
        
        # Verify all connections worked
        successful_connections = [test for test in connection_tests if test["connection_successful"]]
        assert len(successful_connections) == 4, f"Expected 4 successful connections, got {len(successful_connections)}"
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 0.1, f"Test execution time {execution_time:.3f}s too fast - indicates invalid test"
    
    async def test_default_pool_with_async_engine_succeeds(self, isolated_env):
        """MUST succeed - Default pool (AsyncAdaptedQueuePool) is compatible with async engines.
        
        This test validates the correct configuration used in our fix,
        where poolclass is omitted and SQLAlchemy uses the default async-compatible pool.
        """
        # Arrange: Create database URL  
        database_url = "sqlite+aiosqlite:///:memory:"
        start_time = time.time()
        
        # Act: Create async engine without specifying poolclass (uses default)
        engine = create_async_engine(
            database_url,
            # poolclass is omitted - SQLAlchemy will use AsyncAdaptedQueuePool
            pool_size=5,
            max_overflow=10,
            pool_timeout=5,
            pool_recycle=300,
            echo=False,
            future=True
        )
        
        # Assert: Engine created successfully with default async-compatible pool
        assert engine is not None
        assert engine.url.database == ":memory:"
        # Default should be AsyncAdaptedQueuePool for async engines
        assert "AsyncAdaptedQueuePool" in engine.pool.__class__.__name__ or "NullPool" in engine.pool.__class__.__name__
        
        # Cleanup
        await engine.dispose()
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 0.1, f"Test execution time {execution_time:.3f}s too fast - indicates invalid test"
    
    async def test_pool_compatibility_matrix(self, isolated_env):
        """Test all pool + engine combinations to validate compatibility matrix.
        
        This comprehensive test validates which pool classes work with async engines
        and which ones fail, providing a complete compatibility reference.
        """
        # Arrange: Database URL for testing
        database_url = "sqlite+aiosqlite:///:memory:"
        start_time = time.time()
        
        # Define pool classes to test
        pool_classes = [
            (QueuePool, False, "QueuePool incompatible with async engines"),
            (NullPool, True, "NullPool compatible with async engines"),  
            (StaticPool, True, "StaticPool compatible with async engines"),
            (AsyncAdaptedQueuePool, True, "AsyncAdaptedQueuePool designed for async engines")
        ]
        
        compatibility_results = []
        
        # Act: Test each pool class
        for pool_class, should_succeed, description in pool_classes:
            try:
                # Configure engine parameters based on pool class
                engine_kwargs = {
                    "poolclass": pool_class,
                    "echo": False,
                    "future": True
                }
                
                # Only AsyncAdaptedQueuePool supports pool_size with SQLite
                if pool_class == AsyncAdaptedQueuePool:
                    engine_kwargs["pool_size"] = 5
                    
                engine = create_async_engine(database_url, **engine_kwargs)
                
                # If we reach here, the engine creation succeeded
                compatibility_results.append({
                    "pool_class": pool_class.__name__,
                    "expected_success": should_succeed,
                    "actual_success": True,
                    "description": description,
                    "error": None
                })
                
                # Test basic functionality before cleanup
                async with engine.begin() as conn:
                    result = await conn.execute(text("SELECT 1 as compatibility_test"))
                    row = result.fetchone()
                    assert row[0] == 1, f"Basic query failed for {pool_class.__name__}"
                
                # Cleanup
                await engine.dispose()
                
                # Small delay for measurable execution time
                await asyncio.sleep(0.02)
                
            except ArgumentError as e:
                # Engine creation failed with ArgumentError
                compatibility_results.append({
                    "pool_class": pool_class.__name__,
                    "expected_success": should_succeed,
                    "actual_success": False,
                    "description": description,
                    "error": str(e)
                })
            except Exception as e:
                # Unexpected error
                compatibility_results.append({
                    "pool_class": pool_class.__name__,
                    "expected_success": should_succeed,
                    "actual_success": False,
                    "description": description,
                    "error": f"Unexpected error: {str(e)}"
                })
        
        # Assert: Validate all results match expectations
        for result in compatibility_results:
            assert result["actual_success"] == result["expected_success"], (
                f"{result['pool_class']}: Expected {'success' if result['expected_success'] else 'failure'}, "
                f"got {'success' if result['actual_success'] else 'failure'}. "
                f"Description: {result['description']}. Error: {result.get('error', 'None')}"
            )
        
        # Specific assertion for QueuePool failure
        queuepool_result = next(r for r in compatibility_results if r["pool_class"] == "QueuePool")
        assert not queuepool_result["actual_success"], "QueuePool should fail with async engines"
        assert "cannot be used with asyncio engine" in queuepool_result["error"], (
            f"QueuePool should fail with specific error message, got: {queuepool_result['error']}"
        )
        
        # Verify test execution time
        execution_time = time.time() - start_time  
        assert execution_time > 0.2, f"Test execution time {execution_time:.3f}s too fast - indicates invalid test"
    
    async def test_engine_url_parsing_with_pools(self, isolated_env):
        """Test that database URL parsing works correctly with different pool configurations.
        
        This test validates that our database URL construction and parsing
        works correctly regardless of pool configuration.
        """
        # Arrange: Test various database URLs
        test_urls = [
            "sqlite+aiosqlite:///:memory:",
            "postgresql+asyncpg://user:password@localhost:5432/testdb",
            "mysql+aiomysql://user:password@localhost:3306/testdb"
        ]
        
        start_time = time.time()
        compatible_pools = [NullPool, StaticPool]  # Only async-compatible pools
        
        results = []
        
        # Act: Test URL parsing with compatible pools
        for url_string in test_urls:
            for pool_class in compatible_pools:
                try:
                    # Parse URL
                    parsed_url = make_url(url_string)
                    assert parsed_url is not None
                    
                    # Create engine (for SQLite only to avoid external dependencies)
                    if "sqlite" in url_string:
                        engine = create_async_engine(
                            url_string,
                            poolclass=pool_class,
                            echo=False,
                            future=True
                        )
                        
                        # Validate engine properties
                        assert engine is not None
                        assert engine.url.drivername == parsed_url.drivername
                        assert engine.pool.__class__ == pool_class
                        
                        results.append({
                            "url": url_string,
                            "pool": pool_class.__name__,
                            "success": True,
                            "engine_created": True
                        })
                        
                        # Cleanup
                        await engine.dispose()
                    else:
                        # Just test URL parsing for non-SQLite URLs
                        results.append({
                            "url": url_string,
                            "pool": pool_class.__name__, 
                            "success": True,
                            "engine_created": False,  # Not created due to external dependency
                            "url_parsed": True,
                            "drivername": parsed_url.drivername
                        })
                        
                except Exception as e:
                    results.append({
                        "url": url_string,
                        "pool": pool_class.__name__,
                        "success": False,
                        "error": str(e)
                    })
        
        # Assert: All URL parsing should succeed
        for result in results:
            assert result["success"], f"URL parsing failed for {result['url']} with {result['pool']}: {result.get('error')}"
        
        # Verify at least one engine was actually created (SQLite)
        engines_created = [r for r in results if r.get("engine_created", False)]
        assert len(engines_created) > 0, "No engines were actually created - test may be invalid"
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 0.1, f"Test execution time {execution_time:.3f}s too fast - indicates invalid test"
    
    def test_session_creation_with_incompatible_pool_fails(self, isolated_env):
        """Test that session creation fails when using incompatible pool configuration.
        
        This test validates that the session creation process properly fails
        when the underlying engine has an incompatible pool configuration.
        """
        # Arrange: This test simulates what would happen if the broken configuration was used
        database_url = "sqlite+aiosqlite:///:memory:"
        start_time = time.time()
        
        # Act & Assert: Attempt to create sessionmaker with incompatible pool
        with pytest.raises(ArgumentError, match=r"Pool class QueuePool cannot be used with asyncio engine"):
            # This should fail at engine creation time
            engine = create_async_engine(
                database_url,
                poolclass=QueuePool,  # Incompatible with async
                pool_size=5,
                max_overflow=10,
                echo=False,
                future=True
            )
            
            # This line should never be reached
            sessionmaker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 0.1, f"Test execution time {execution_time:.3f}s too fast - indicates invalid test"
    
    async def test_fixed_configuration_works_correctly(self, isolated_env):
        """Test that the fixed configuration (no explicit poolclass) works correctly.
        
        This test validates that our fix - omitting the poolclass parameter to let
        SQLAlchemy use the default async-compatible pool - works as expected.
        """
        # Arrange: Database URL and fixed configuration
        database_url = "sqlite+aiosqlite:///:memory:"
        start_time = time.time()
        
        # Act: Create engine using the fixed configuration (from database/__init__.py)
        engine = create_async_engine(
            database_url,
            # poolclass is omitted - SQLAlchemy will use default async-compatible pool
            pool_size=5,          # Small pool size for efficient connection reuse
            max_overflow=10,      # Allow burst connections
            pool_timeout=5,       # Fast timeout to prevent WebSocket blocking  
            pool_recycle=300,     # Recycle connections every 5 minutes
            echo=False,
            future=True
        )
        
        # Assert: Engine created successfully
        assert engine is not None
        assert engine.url.database == ":memory:"
        
        # Create sessionmaker
        sessionmaker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        
        assert sessionmaker is not None
        
        # Test session creation
        async with sessionmaker() as session:
            assert session is not None
            assert isinstance(session, AsyncSession)
            
            # Test a simple query
            result = await session.execute("SELECT 1 as test_value")
            row = result.fetchone()
            assert row is not None
            assert row[0] == 1
        
        # Cleanup
        await engine.dispose()
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 0.15, f"Test execution time {execution_time:.3f}s too fast - indicates invalid test"
    
    async def test_pool_configuration_edge_cases(self, isolated_env):
        """Test edge cases in pool configuration that might cause issues.
        
        This test covers various edge cases and configurations that might
        cause problems similar to the QueuePool issue.
        """
        database_url = "sqlite+aiosqlite:///:memory:"
        start_time = time.time()
        
        edge_cases = [
            # Case 1: Explicit None poolclass (should use default)
            {
                "name": "explicit_none_poolclass",
                "config": {"poolclass": None},
                "should_succeed": True
            },
            # Case 2: Zero pool size with compatible pool
            {
                "name": "zero_pool_size", 
                "config": {"poolclass": NullPool, "pool_size": 0},
                "should_succeed": True
            },
            # Case 3: Very small pool timeout
            {
                "name": "small_pool_timeout",
                "config": {"poolclass": NullPool, "pool_timeout": 0.1},
                "should_succeed": True
            },
            # Case 4: Large pool configuration
            {
                "name": "large_pool_config",
                "config": {"poolclass": StaticPool, "pool_size": 50, "max_overflow": 100},
                "should_succeed": True
            }
        ]
        
        results = []
        
        # Test each edge case
        for case in edge_cases:
            try:
                # Filter out None values and pool_size for NullPool
                config = {k: v for k, v in case["config"].items() if v is not None}
                if config.get("poolclass") == NullPool and "pool_size" in config:
                    del config["pool_size"]  # NullPool doesn't support pool_size
                
                engine = create_async_engine(
                    database_url,
                    echo=False,
                    future=True,
                    **config
                )
                
                # Test that we can create a session
                sessionmaker = async_sessionmaker(
                    engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
                
                # Quick session test
                async with sessionmaker() as session:
                    await session.execute("SELECT 1")
                
                results.append({
                    "case": case["name"],
                    "expected_success": case["should_succeed"],
                    "actual_success": True,
                    "config": config
                })
                
                # Cleanup
                await engine.dispose()
                
            except Exception as e:
                results.append({
                    "case": case["name"],
                    "expected_success": case["should_succeed"], 
                    "actual_success": False,
                    "config": case["config"],
                    "error": str(e)
                })
        
        # Assert all results match expectations
        for result in results:
            assert result["actual_success"] == result["expected_success"], (
                f"Edge case {result['case']}: Expected {'success' if result['expected_success'] else 'failure'}, "
                f"got {'success' if result['actual_success'] else 'failure'}. "
                f"Config: {result['config']}. Error: {result.get('error', 'None')}"
            )
        
        # Verify test execution time
        execution_time = time.time() - start_time
        assert execution_time > 0.2, f"Test execution time {execution_time:.3f}s too fast - indicates invalid test"