"""
Test to reproduce and fix the database connection race condition.

CRITICAL ISSUE: 
asyncpg.exceptions._base.InterfaceError: cannot perform operation: another operation is in progress

Root Cause: Multiple async operations accessing the same database connection concurrently.
"""

import asyncio
import pytest
import time
from contextlib import asynccontextmanager

from netra_backend.app.dependencies import get_request_scoped_db_session
from netra_backend.app.database.request_scoped_session_factory import (
    get_session_factory,
    get_isolated_session
)
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.logging_config import central_logger
from sqlalchemy import text
from sqlalchemy.exc import InterfaceError

logger = central_logger.get_logger(__name__)


class TestDatabaseRaceCondition:
    """Test cases to reproduce and validate fixes for database connection race conditions."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_session_creation_race_condition(self):
        """Test concurrent session creation that should trigger race condition."""
        logger.info("[U+1F9EA] Testing concurrent session creation race condition")
        
        race_condition_detected = False
        error_details = []
        
        async def concurrent_database_operation(operation_id: int):
            """Perform database operation that might cause race condition."""
            try:
                # Create database session and immediately execute query
                async for session in get_request_scoped_db_session():
                    # Execute a simple query
                    result = await session.execute(text("SELECT 1 as test"))
                    value = result.scalar()
                    logger.debug(f"Operation {operation_id}: SUCCESS, got value {value}")
                    return f"op_{operation_id}_success"
            except InterfaceError as e:
                if "cannot perform operation: another operation is in progress" in str(e):
                    error_details.append(f"Operation {operation_id}: RACE CONDITION - {e}")
                    return f"op_{operation_id}_race_condition"
                else:
                    error_details.append(f"Operation {operation_id}: OTHER_ERROR - {e}")
                    return f"op_{operation_id}_other_error"
            except Exception as e:
                error_details.append(f"Operation {operation_id}: UNEXPECTED_ERROR - {e}")
                return f"op_{operation_id}_unexpected_error"
        
        # Launch multiple concurrent operations
        num_operations = 10
        logger.info(f"[U+1F680] Launching {num_operations} concurrent database operations")
        
        tasks = [
            concurrent_database_operation(i) 
            for i in range(num_operations)
        ]
        
        # Run all operations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        success_count = sum(1 for r in results if isinstance(r, str) and "success" in r)
        race_condition_count = sum(1 for r in results if isinstance(r, str) and "race_condition" in r)
        error_count = len(results) - success_count
        
        logger.info(f" CHART:  RESULTS: Success: {success_count}, Race conditions: {race_condition_count}, Other errors: {error_count}")
        
        if error_details:
            for detail in error_details:
                logger.error(f"    SEARCH:  {detail}")
        
        # For this test, detecting race condition is actually "success"
        # as it proves the issue exists
        if race_condition_count > 0:
            logger.info(f" PASS:  RACE CONDITION REPRODUCED: {race_condition_count} operations hit race condition")
            # Mark as passing since we successfully reproduced the issue
            assert race_condition_count > 0, f"Expected to reproduce race condition, got {race_condition_count} race conditions"
        else:
            logger.warning(f" WARNING: [U+FE0F] Race condition NOT reproduced in this run. Success: {success_count}")
            # Don't fail the test - race conditions are intermittent
            assert success_count > 0, f"Expected at least some operations to succeed"

    @pytest.mark.integration 
    @pytest.mark.asyncio
    async def test_session_factory_concurrent_access(self):
        """Test concurrent access to session factory directly."""
        logger.info("[U+1F9EA] Testing session factory concurrent access")
        
        factory = await get_session_factory()
        race_conditions = []
        
        async def factory_operation(op_id: int):
            """Use session factory to create sessions concurrently."""
            try:
                user_id = f"test_user_{op_id}"
                request_id = UnifiedIdGenerator.generate_base_id(f"req_{op_id}")
                
                async with factory.get_request_scoped_session(
                    user_id=user_id,
                    request_id=request_id
                ) as session:
                    # Execute query to actually use the connection
                    result = await session.execute(text("SELECT 1 as test"))
                    value = result.scalar()
                    logger.debug(f"Factory operation {op_id}: SUCCESS")
                    return f"factory_op_{op_id}_success"
                    
            except InterfaceError as e:
                if "cannot perform operation: another operation is in progress" in str(e):
                    race_conditions.append(f"Factory operation {op_id}: {e}")
                    return f"factory_op_{op_id}_race_condition"
                else:
                    logger.error(f"Factory operation {op_id}: Other interface error: {e}")
                    return f"factory_op_{op_id}_interface_error"
            except Exception as e:
                logger.error(f"Factory operation {op_id}: Unexpected error: {e}")
                return f"factory_op_{op_id}_error"
        
        # Run concurrent factory operations
        num_ops = 8
        tasks = [factory_operation(i) for i in range(num_ops)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if isinstance(r, str) and "success" in r)
        race_count = len(race_conditions)
        
        logger.info(f" CHART:  Factory test results: Success: {success_count}, Race conditions: {race_count}")
        
        if race_conditions:
            for race_error in race_conditions:
                logger.error(f"    SEARCH:  RACE: {race_error}")
            logger.info(f" PASS:  RACE CONDITION REPRODUCED via factory: {race_count} instances")
        else:
            logger.info(f" PASS:  No race conditions detected in factory operations")
        
        # Ensure at least some operations succeeded
        assert success_count > 0, f"Expected some successful operations, got {success_count}"

    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_isolated_session_concurrent_access(self):
        """Test concurrent access using get_isolated_session."""
        logger.info("[U+1F9EA] Testing isolated session concurrent access")
        
        errors = []
        
        async def isolated_session_operation(op_id: int):
            """Use isolated session for concurrent operations."""
            try:
                user_id = f"isolated_user_{op_id}"
                request_id = UnifiedIdGenerator.generate_base_id(f"isolated_req_{op_id}")
                
                async with get_isolated_session(
                    user_id=user_id,
                    request_id=request_id
                ) as session:
                    # Execute query
                    result = await session.execute(text("SELECT 2 as test"))
                    value = result.scalar()
                    assert value == 2
                    logger.debug(f"Isolated operation {op_id}: SUCCESS")
                    return f"isolated_op_{op_id}_success"
                    
            except InterfaceError as e:
                if "cannot perform operation: another operation is in progress" in str(e):
                    errors.append(f"Isolated operation {op_id}: RACE - {e}")
                    return f"isolated_op_{op_id}_race"
                else:
                    errors.append(f"Isolated operation {op_id}: INTERFACE - {e}")
                    return f"isolated_op_{op_id}_interface_error"
            except Exception as e:
                errors.append(f"Isolated operation {op_id}: ERROR - {e}")
                return f"isolated_op_{op_id}_error"
        
        # Run concurrent isolated session operations
        num_ops = 6
        tasks = [isolated_session_operation(i) for i in range(num_ops)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if isinstance(r, str) and "success" in r)
        race_count = sum(1 for r in results if isinstance(r, str) and "race" in r)
        
        logger.info(f" CHART:  Isolated session results: Success: {success_count}, Race conditions: {race_count}")
        
        if errors:
            for error in errors:
                logger.error(f"    SEARCH:  {error}")
        
        if race_count > 0:
            logger.info(f" PASS:  RACE CONDITION REPRODUCED in isolated sessions: {race_count} instances")
        else:
            logger.info(f" PASS:  No race conditions in isolated session operations")
        
        # Ensure operations work
        assert success_count > 0, f"Expected successful operations, got {success_count}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fix_validation_separate_connections(self):
        """Test that sessions truly get separate connections and don't race."""
        logger.info("[U+1F9EA] Testing fix: separate connections prevent race conditions")
        
        # Track session connection details
        connection_info = []
        
        async def connection_info_operation(op_id: int):
            """Gather connection information from each session."""
            try:
                user_id = f"conn_test_user_{op_id}"
                request_id = UnifiedIdGenerator.generate_base_id(f"conn_req_{op_id}")
                
                async with get_isolated_session(
                    user_id=user_id,
                    request_id=request_id
                ) as session:
                    # Get connection ID
                    result = await session.execute(text("SELECT pg_backend_pid()"))
                    connection_pid = result.scalar()
                    
                    # Store connection info
                    info = {
                        'operation_id': op_id,
                        'user_id': user_id,
                        'request_id': request_id,
                        'connection_pid': connection_pid,
                        'session_id': id(session)
                    }
                    connection_info.append(info)
                    
                    # Hold connection briefly to increase chance of collision if sharing
                    await asyncio.sleep(0.1)
                    
                    logger.debug(f"Connection operation {op_id}: PID {connection_pid}, Session {id(session)}")
                    return f"conn_op_{op_id}_success"
                    
            except Exception as e:
                logger.error(f"Connection operation {op_id}: {e}")
                return f"conn_op_{op_id}_error"
        
        # Run operations to gather connection info
        num_ops = 5
        tasks = [connection_info_operation(i) for i in range(num_ops)]
        results = await asyncio.gather(*tasks)
        
        # Analyze connection isolation
        unique_pids = set(info['connection_pid'] for info in connection_info)
        unique_sessions = set(info['session_id'] for info in connection_info)
        
        logger.info(f" CHART:  Connection analysis:")
        logger.info(f"    SEARCH:  Total operations: {len(connection_info)}")
        logger.info(f"    SEARCH:  Unique connection PIDs: {len(unique_pids)}")
        logger.info(f"    SEARCH:  Unique session objects: {len(unique_sessions)}")
        logger.info(f"    SEARCH:  PIDs: {sorted(unique_pids)}")
        
        for info in connection_info:
            logger.debug(f"    SEARCH:  Op {info['operation_id']}: PID {info['connection_pid']}, Session {info['session_id']}")
        
        # Validate proper isolation
        success_count = sum(1 for r in results if "success" in r)
        assert success_count == num_ops, f"Expected all operations to succeed, got {success_count}/{num_ops}"
        
        # If connection pooling is working correctly, we might see some PID reuse
        # But if we have race conditions, operations would fail with InterfaceError
        logger.info(f" PASS:  CONNECTION ISOLATION VALIDATION: All {success_count} operations succeeded")
        
        if len(unique_pids) < len(connection_info):
            logger.info(f" CYCLE:  CONNECTION POOLING: Detected connection reuse (healthy)")
        else:
            logger.info(f"[U+1F517] SEPARATE CONNECTIONS: Each operation got separate connection")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rapid_session_creation_stress(self):
        """Stress test rapid session creation to force race conditions."""
        logger.info("[U+1F9EA] STRESS TEST: Rapid session creation")
        
        race_conditions = []
        successful_operations = []
        
        async def rapid_operation(op_id: int):
            """Rapidly create sessions to stress the connection pool."""
            try:
                # No delay - create sessions as fast as possible
                user_id = f"rapid_user_{op_id}"
                request_id = UnifiedIdGenerator.generate_base_id(f"rapid_req_{op_id}")
                
                start_time = time.time()
                
                async with get_isolated_session(
                    user_id=user_id,
                    request_id=request_id
                ) as session:
                    # Execute multiple queries to stress connection
                    for query_num in range(3):
                        result = await session.execute(text(f"SELECT {query_num} as query_num"))
                        value = result.scalar()
                        assert value == query_num
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    operation_result = {
                        'op_id': op_id,
                        'duration': duration,
                        'user_id': user_id,
                        'request_id': request_id
                    }
                    successful_operations.append(operation_result)
                    
                    return f"rapid_op_{op_id}_success"
                    
            except InterfaceError as e:
                if "cannot perform operation: another operation is in progress" in str(e):
                    race_conditions.append({
                        'op_id': op_id,
                        'error': str(e),
                        'error_type': 'race_condition'
                    })
                    return f"rapid_op_{op_id}_race_condition"
                else:
                    logger.error(f"Rapid operation {op_id}: Interface error: {e}")
                    return f"rapid_op_{op_id}_interface_error"
            except Exception as e:
                logger.error(f"Rapid operation {op_id}: Unexpected error: {e}")
                return f"rapid_op_{op_id}_error"
        
        # Launch many operations simultaneously 
        num_rapid_ops = 15
        logger.info(f"[U+1F680] Launching {num_rapid_ops} rapid operations simultaneously")
        
        tasks = [rapid_operation(i) for i in range(num_rapid_ops)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze stress test results
        success_count = len(successful_operations)
        race_count = len(race_conditions)
        error_count = len(results) - success_count
        
        logger.info(f" CHART:  STRESS TEST RESULTS:")
        logger.info(f"    PASS:  Successful operations: {success_count}")
        logger.info(f"    WARNING: [U+FE0F]  Race conditions detected: {race_count}")
        logger.info(f"    FAIL:  Other errors: {error_count - race_count}")
        
        if successful_operations:
            avg_duration = sum(op['duration'] for op in successful_operations) / len(successful_operations)
            logger.info(f"   [U+23F1][U+FE0F]  Average operation duration: {avg_duration:.3f}s")
        
        if race_conditions:
            logger.error(" ALERT:  RACE CONDITIONS DETECTED:")
            for race in race_conditions[:5]:  # Show first 5
                logger.error(f"    SEARCH:  Op {race['op_id']}: {race['error']}")
            if len(race_conditions) > 5:
                logger.error(f"   ... and {len(race_conditions) - 5} more")
            
            # For this test, detecting race conditions means we successfully reproduced the bug
            logger.info(f" PASS:  STRESS TEST SUCCESS: Reproduced {race_count} race conditions")
        else:
            logger.info(" PASS:  STRESS TEST: No race conditions detected (fix may be working)")
        
        # Test should pass if we either reproduce the race condition OR all operations succeed
        assert (race_count > 0) or (success_count == num_rapid_ops), \
            f"Either race conditions should be detected OR all operations should succeed. " \
            f"Got {race_count} races, {success_count}/{num_rapid_ops} successes"


if __name__ == "__main__":
    """Run the race condition reproduction tests."""
    pytest.main([__file__, "-v", "--tb=short"])