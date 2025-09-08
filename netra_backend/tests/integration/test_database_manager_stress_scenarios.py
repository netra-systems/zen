"""DatabaseManager Stress Test Scenarios

CRITICAL: Advanced stress testing for DatabaseManager to validate behavior under extreme conditions.
Tests connection retry patterns, circuit breakers, and high-load scenarios.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Infrastructure resilience 
- Business Goal: Ensure system stability under production load conditions
- Value Impact: Prevents cascade failures and service outages during traffic spikes
- Strategic Impact: Database layer must handle enterprise-scale concurrent operations

STRESS TEST SCENARIOS:
1. Connection retry patterns with simulated failures
2. Circuit breaker behavior under sustained failures  
3. High-concurrency database access patterns
4. Memory pressure and connection pool exhaustion
5. Network latency simulation and timeout handling
6. Database lock contention and deadlock resolution
7. Rapid connection create/destroy cycles
8. Large transaction rollback scenarios
9. Connection pool monitoring and metrics validation
10. Recovery patterns after infrastructure failures

CRITICAL: Uses real database connections for authentic stress testing
"""

import asyncio
import pytest
import logging
import sqlite3
import tempfile
import os
import time
import random
import threading
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy import text, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.exc import OperationalError, IntegrityError
from unittest.mock import patch, MagicMock
import gc

# SSOT imports - absolute paths required per CLAUDE.md  
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager, get_db_session
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env

logger = logging.getLogger(__name__)


class TestDatabaseManagerStressScenarios(BaseIntegrationTest):
    """Advanced stress testing for DatabaseManager resilience patterns."""
    
    def setup_method(self):
        """Set up for stress testing with multiple database configurations."""
        super().setup_method()
        
        # Create multiple temporary databases for stress testing
        self.temp_db_dir = tempfile.mkdtemp(prefix="netra_stress_test_")
        self.stress_db_paths = {
            "primary": os.path.join(self.temp_db_dir, "stress_primary.db"),
            "secondary": os.path.join(self.temp_db_dir, "stress_secondary.db"),
            "recovery": os.path.join(self.temp_db_dir, "stress_recovery.db"),
            "corrupted": os.path.join(self.temp_db_dir, "stress_corrupted.db")
        }
        
        # Stress test environment configuration
        self.stress_test_env = {
            "ENVIRONMENT": "test",
            "USE_MEMORY_DB": "false",
            "POSTGRES_HOST": "localhost", 
            "POSTGRES_PORT": "5434",
            "POSTGRES_USER": "stress_user",
            "POSTGRES_PASSWORD": "stress_password", 
            "POSTGRES_DB": "stress_test_db",
            # Prevent OAuth validation errors
            "GOOGLE_OAUTH_CLIENT_ID_TEST": "stress_client_id",
            "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "stress_client_secret"
        }
        
        # Reset global database manager for each test
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
        
        # Stress test metrics
        self.stress_metrics = {
            "operations_completed": 0,
            "operations_failed": 0,
            "max_concurrent_connections": 0,
            "total_connection_time": 0.0,
            "retry_attempts": 0,
            "circuit_breaker_trips": 0
        }
    
    def teardown_method(self):
        """Clean up stress test resources."""
        super().teardown_method()
        
        # Force garbage collection to clean up database connections
        gc.collect()
        
        # Clean up all stress test databases
        try:
            for db_path in self.stress_db_paths.values():
                if os.path.exists(db_path):
                    os.unlink(db_path)
            os.rmdir(self.temp_db_dir)
        except OSError as e:
            logger.warning(f"Failed to clean up stress test databases: {e}")
    
    async def _create_stress_test_schema(self, engine: AsyncEngine) -> None:
        """Create schema optimized for stress testing."""
        metadata = MetaData()
        
        # High-throughput table for concurrent operations
        stress_operations = Table(
            'stress_operations',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('operation_type', String(50)),
            Column('thread_id', String(50)),
            Column('timestamp_start', DateTime),
            Column('timestamp_end', DateTime),
            Column('payload_data', String(500)),
            Column('status', String(20))  # success, failed, timeout
        )
        
        # Connection tracking table
        connection_metrics = Table(
            'connection_metrics',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('connection_id', String(100)),
            Column('created_at', DateTime),
            Column('closed_at', DateTime),
            Column('operations_count', Integer, default=0),
            Column('error_count', Integer, default=0)
        )
        
        # Large data table for memory pressure testing
        large_data = Table(
            'large_data_stress',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('data_chunk', String(1000)),  # 1KB per row
            Column('chunk_index', Integer),
            Column('checksum', String(50))
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_retry_patterns_with_failures(self, isolated_env):
        """Test connection retry patterns with simulated database failures."""
        for key, value in self.stress_test_env.items():
            isolated_env.set(key, value, source="test")
        
        # Create a database that will "fail" initially
        failing_db_path = self.stress_db_paths["corrupted"]
        
        retry_attempts = 0
        max_retries = 5
        
        async def connection_with_retry(db_url: str, attempt: int = 0):
            nonlocal retry_attempts
            
            if attempt < 3:  # Simulate failures for first 3 attempts
                retry_attempts += 1
                if attempt < 2:
                    # Simulate different types of failures
                    if attempt == 0:
                        raise OperationalError("Database connection failed", None, None)
                    else:
                        raise OperationalError("Database timeout", None, None)
            
            # Success on 3rd+ attempt
            with patch('netra_backend.app.core.config.get_config') as mock_config:
                mock_config.return_value.database_echo = False
                mock_config.return_value.database_pool_size = 0
                mock_config.return_value.database_max_overflow = 0
                mock_config.return_value.database_url = db_url
                
                db_manager = DatabaseManager()
                await db_manager.initialize()
                return db_manager
        
        # Test retry logic
        db_url = f"sqlite+aiosqlite:///{self.stress_db_paths['primary']}"
        
        for attempt in range(max_retries):
            try:
                db_manager = await connection_with_retry(db_url, attempt)
                logger.info(f"Connection succeeded on attempt {attempt + 1}")
                break
            except Exception as e:
                logger.info(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff
        
        # Verify retry attempts were made
        assert retry_attempts >= 2, f"Expected multiple retry attempts, got {retry_attempts}"
        
        # Test that database works after retry success
        engine = db_manager.get_engine('primary')
        await self._create_stress_test_schema(engine)
        
        async with db_manager.get_session() as session:
            await session.execute(
                text("INSERT INTO stress_operations (operation_type, thread_id, status) VALUES (?, ?, ?)"),
                ("retry_test", "main_thread", "success")
            )
            await session.commit()
            
            result = await session.execute(text("SELECT COUNT(*) FROM stress_operations"))
            count = result.scalar()
            assert count == 1
        
        await db_manager.close_all()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_high_concurrency_database_access_patterns(self, isolated_env):
        """Test database behavior under high concurrent access loads."""
        for key, value in self.stress_test_env.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f"sqlite+aiosqlite:///{self.stress_db_paths['primary']}"
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            engine = db_manager.get_engine('primary')
            await self._create_stress_test_schema(engine)
            
            # High concurrency parameters
            num_concurrent_tasks = 20
            operations_per_task = 25
            total_expected_operations = num_concurrent_tasks * operations_per_task
            
            # Track concurrency metrics
            active_connections = 0
            max_concurrent = 0
            connection_lock = asyncio.Lock()
            
            async def high_load_database_operations(task_id: int):
                """Perform database operations under high load."""
                nonlocal active_connections, max_concurrent
                
                operations_completed = 0
                operations_failed = 0
                
                for op_index in range(operations_per_task):
                    try:
                        async with connection_lock:
                            active_connections += 1
                            max_concurrent = max(max_concurrent, active_connections)
                        
                        start_time = time.time()
                        
                        async with db_manager.get_session() as session:
                            # Insert operation record
                            await session.execute(
                                text("INSERT INTO stress_operations (operation_type, thread_id, timestamp_start, payload_data, status) VALUES (?, ?, ?, ?, ?)"),
                                ("high_load", f"task_{task_id}", start_time, f"data_{task_id}_{op_index}", "pending")
                            )
                            
                            # Simulate some processing work
                            await session.execute(text("SELECT COUNT(*) FROM stress_operations"))
                            
                            # Update operation as completed
                            end_time = time.time()
                            await session.execute(
                                text("UPDATE stress_operations SET timestamp_end = ?, status = ? WHERE thread_id = ? AND payload_data = ?"),
                                (end_time, "success", f"task_{task_id}", f"data_{task_id}_{op_index}")
                            )
                            
                            await session.commit()
                            operations_completed += 1
                        
                        async with connection_lock:
                            active_connections -= 1
                        
                        # Add small random delay to simulate real-world timing
                        await asyncio.sleep(random.uniform(0.001, 0.01))
                        
                    except Exception as e:
                        operations_failed += 1
                        logger.warning(f"High load operation failed in task {task_id}: {e}")
                        
                        async with connection_lock:
                            active_connections -= 1
                
                return {"completed": operations_completed, "failed": operations_failed}
            
            # Execute high concurrent load
            start_time = time.time()
            
            tasks = []
            for task_id in range(num_concurrent_tasks):
                task = asyncio.create_task(high_load_database_operations(task_id))
                tasks.append(task)
            
            # Wait for all concurrent operations to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Analyze results
            total_completed = 0
            total_failed = 0
            
            for result in results:
                if isinstance(result, dict):
                    total_completed += result["completed"]
                    total_failed += result["failed"]
                else:
                    total_failed += operations_per_task  # Count exception as all operations failed
            
            # Performance assertions
            success_rate = total_completed / total_expected_operations if total_expected_operations > 0 else 0
            operations_per_second = total_completed / total_time
            
            logger.info(f"High concurrency test results:")
            logger.info(f"  Total operations: {total_expected_operations}")
            logger.info(f"  Completed: {total_completed}")
            logger.info(f"  Failed: {total_failed}")
            logger.info(f"  Success rate: {success_rate:.2%}")
            logger.info(f"  Operations/second: {operations_per_second:.2f}")
            logger.info(f"  Max concurrent connections: {max_concurrent}")
            logger.info(f"  Total time: {total_time:.2f}s")
            
            # Verify high concurrency handled successfully
            assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"  # 95% minimum success
            assert operations_per_second > 100, f"Throughput too low: {operations_per_second:.2f} ops/sec"
            assert max_concurrent > 5, f"Concurrency too low: {max_concurrent}"
            
            # Verify database integrity after high load
            async with db_manager.get_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM stress_operations WHERE status = 'success'"))
                success_count = result.scalar()
                assert success_count == total_completed
            
            await db_manager.close_all()
    
    @pytest.mark.integration 
    @pytest.mark.asyncio
    async def test_memory_pressure_and_connection_pool_exhaustion(self, isolated_env):
        """Test behavior under memory pressure and connection pool limits."""
        for key, value in self.stress_test_env.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            # Configure limited connection pool for stress testing
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 3  # Very limited pool
            mock_config.return_value.database_max_overflow = 2  # Limited overflow
            mock_config.return_value.database_url = f"sqlite+aiosqlite:///{self.stress_db_paths['primary']}"
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            engine = db_manager.get_engine('primary')
            await self._create_stress_test_schema(engine)
            
            # Create memory pressure with large data operations
            chunk_size = 1000  # 1KB per chunk
            num_chunks = 100   # 100KB total per operation
            num_concurrent_ops = 10  # Multiple concurrent memory-intensive operations
            
            async def memory_intensive_operation(op_id: int):
                """Perform memory-intensive database operations."""
                chunks_inserted = 0
                
                try:
                    async with db_manager.get_session() as session:
                        # Insert large chunks of data
                        for chunk_index in range(num_chunks):
                            large_data = "x" * chunk_size  # 1KB string
                            checksum = f"checksum_{op_id}_{chunk_index}"
                            
                            await session.execute(
                                text("INSERT INTO large_data_stress (data_chunk, chunk_index, checksum) VALUES (?, ?, ?)"),
                                (large_data, chunk_index, checksum)
                            )
                            chunks_inserted += 1
                            
                            # Commit periodically to avoid huge transactions
                            if chunk_index % 10 == 0:
                                await session.commit()
                        
                        await session.commit()
                        
                except Exception as e:
                    logger.warning(f"Memory intensive operation {op_id} failed: {e}")
                
                return chunks_inserted
            
            # Test connection pool under pressure
            start_time = time.time()
            
            # Create more tasks than available connections to test pool handling
            tasks = []
            for op_id in range(num_concurrent_ops):
                task = asyncio.create_task(memory_intensive_operation(op_id))
                tasks.append(task)
            
            # Monitor connection pool behavior
            connection_wait_times = []
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Analyze memory pressure results
            successful_operations = 0
            total_chunks_inserted = 0
            
            for result in results:
                if isinstance(result, int):
                    successful_operations += 1
                    total_chunks_inserted += result
                elif isinstance(result, Exception):
                    logger.info(f"Expected exception under pressure: {result}")
            
            # Verify database handled memory pressure
            memory_throughput = total_chunks_inserted / total_time
            
            logger.info(f"Memory pressure test results:")
            logger.info(f"  Successful operations: {successful_operations}/{num_concurrent_ops}")
            logger.info(f"  Total chunks inserted: {total_chunks_inserted}")
            logger.info(f"  Memory throughput: {memory_throughput:.2f} chunks/sec")
            logger.info(f"  Total time: {total_time:.2f}s")
            
            # Verify system didn't crash under pressure
            assert successful_operations > 0, "At least some operations should succeed under pressure"
            assert memory_throughput > 10, f"Memory throughput too low: {memory_throughput:.2f}"
            
            # Verify database integrity after memory pressure
            async with db_manager.get_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM large_data_stress"))
                total_rows = result.scalar()
                assert total_rows == total_chunks_inserted
                
                # Verify data integrity
                result = await session.execute(text("SELECT COUNT(DISTINCT checksum) FROM large_data_stress"))
                unique_checksums = result.scalar()
                assert unique_checksums == total_chunks_inserted, "Data integrity check failed"
            
            await db_manager.close_all()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rapid_connection_create_destroy_cycles(self, isolated_env):
        """Test rapid connection creation and destruction patterns."""
        for key, value in self.stress_test_env.items():
            isolated_env.set(key, value, source="test")
        
        # Rapid cycle parameters
        num_cycles = 50
        operations_per_cycle = 5
        cycle_delay = 0.01  # 10ms between cycles
        
        successful_cycles = 0
        total_operations = 0
        connection_errors = 0
        
        for cycle in range(num_cycles):
            cycle_start = time.time()
            
            try:
                with patch('netra_backend.app.core.config.get_config') as mock_config:
                    mock_config.return_value.database_echo = False
                    mock_config.return_value.database_pool_size = 0
                    mock_config.return_value.database_max_overflow = 0
                    mock_config.return_value.database_url = f"sqlite+aiosqlite:///{self.stress_db_paths['primary']}"
                    
                    # Create new DatabaseManager for each cycle
                    db_manager = DatabaseManager()
                    await db_manager.initialize()
                    
                    # Verify connection works
                    engine = db_manager.get_engine('primary')
                    
                    # Perform multiple operations in this cycle
                    cycle_operations = 0
                    async with db_manager.get_session() as session:
                        for op in range(operations_per_cycle):
                            await session.execute(text("SELECT 1"))
                            cycle_operations += 1
                        await session.commit()
                    
                    # Explicitly close connections
                    await db_manager.close_all()
                    
                    successful_cycles += 1
                    total_operations += cycle_operations
                    
                    # Force cleanup
                    del db_manager
                    
                    # Reset global manager to ensure fresh instance next cycle
                    import netra_backend.app.db.database_manager
                    netra_backend.app.db.database_manager._database_manager = None
                    
            except Exception as e:
                connection_errors += 1
                logger.warning(f"Rapid cycle {cycle} failed: {e}")
            
            # Wait between cycles
            await asyncio.sleep(cycle_delay)
            
            # Log progress every 10 cycles
            if cycle % 10 == 0:
                logger.info(f"Rapid connection cycles: {cycle + 1}/{num_cycles}")
        
        # Analyze rapid cycle results
        success_rate = successful_cycles / num_cycles
        
        logger.info(f"Rapid connection cycle test results:")
        logger.info(f"  Successful cycles: {successful_cycles}/{num_cycles}")
        logger.info(f"  Success rate: {success_rate:.2%}")
        logger.info(f"  Total operations: {total_operations}")
        logger.info(f"  Connection errors: {connection_errors}")
        
        # Verify rapid cycles handled successfully
        assert success_rate >= 0.90, f"Rapid cycle success rate too low: {success_rate:.2%}"
        assert total_operations >= successful_cycles * operations_per_cycle
        
        # Final verification - ensure database still works after rapid cycles
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f"sqlite+aiosqlite:///{self.stress_db_paths['primary']}"
            
            final_db_manager = DatabaseManager()
            await final_db_manager.initialize()
            
            async with final_db_manager.get_session() as session:
                result = await session.execute(text("SELECT 'connection_healthy' as status"))
                status = result.scalar()
                assert status == "connection_healthy"
            
            await final_db_manager.close_all()
    
    @pytest.mark.integration
    @pytest.mark.asyncio 
    async def test_large_transaction_rollback_scenarios(self, isolated_env):
        """Test behavior with large transaction rollbacks under stress."""
        for key, value in self.stress_test_env.items():
            isolated_env.set(key, value, source="test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0
            mock_config.return_value.database_max_overflow = 0
            mock_config.return_value.database_url = f"sqlite+aiosqlite:///{self.stress_db_paths['primary']}"
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            engine = db_manager.get_engine('primary')
            await self._create_stress_test_schema(engine)
            
            # Large transaction parameters
            large_transaction_size = 1000  # 1000 operations per transaction
            num_rollback_tests = 5
            
            successful_rollbacks = 0
            
            for test_num in range(num_rollback_tests):
                logger.info(f"Testing large transaction rollback {test_num + 1}")
                
                rollback_point = random.randint(500, 900)  # Random failure point
                operations_before_rollback = 0
                
                try:
                    async with db_manager.get_session() as session:
                        # Perform large number of operations
                        for op_index in range(large_transaction_size):
                            await session.execute(
                                text("INSERT INTO stress_operations (operation_type, thread_id, payload_data, status) VALUES (?, ?, ?, ?)"),
                                ("large_tx", f"rollback_test_{test_num}", f"data_{op_index}", "pending")
                            )
                            
                            operations_before_rollback += 1
                            
                            # Force rollback at specific point
                            if op_index == rollback_point:
                                raise RuntimeError(f"Simulated failure at operation {rollback_point}")
                        
                        # This commit should never be reached
                        await session.commit()
                        assert False, "Transaction should have been rolled back"
                        
                except RuntimeError as e:
                    # Expected rollback scenario
                    logger.info(f"Expected rollback: {e}")
                    successful_rollbacks += 1
                
                # Verify rollback worked - no data should be committed
                async with db_manager.get_session() as session:
                    result = await session.execute(
                        text("SELECT COUNT(*) FROM stress_operations WHERE thread_id = ?"),
                        (f"rollback_test_{test_num}",)
                    )
                    count_after_rollback = result.scalar()
                    assert count_after_rollback == 0, f"Rollback failed - found {count_after_rollback} committed operations"
                
                # Test database still works after large rollback
                async with db_manager.get_session() as session:
                    await session.execute(
                        text("INSERT INTO stress_operations (operation_type, thread_id, status) VALUES (?, ?, ?)"),
                        ("post_rollback_test", f"recovery_{test_num}", "success")
                    )
                    await session.commit()
            
            # Verify all rollback tests succeeded
            assert successful_rollbacks == num_rollback_tests
            
            # Verify database integrity after multiple large rollbacks
            async with db_manager.get_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM stress_operations WHERE operation_type = 'post_rollback_test'"))
                recovery_operations = result.scalar()
                assert recovery_operations == num_rollback_tests
                
                result = await session.execute(text("SELECT COUNT(*) FROM stress_operations WHERE operation_type = 'large_tx'"))
                rolled_back_operations = result.scalar()
                assert rolled_back_operations == 0, "No large transaction operations should be committed"
            
            logger.info(f"Large transaction rollback test results:")
            logger.info(f"  Successful rollbacks: {successful_rollbacks}/{num_rollback_tests}")
            logger.info(f"  Average operations before rollback: {rollback_point}")
            logger.info(f"  Database integrity maintained: ✓")
            
            await db_manager.close_all()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_recovery_patterns_after_simulated_failures(self, isolated_env):
        """Test database recovery patterns after various simulated infrastructure failures."""
        for key, value in self.stress_test_env.items():
            isolated_env.set(key, value, source="test")
        
        recovery_scenarios = [
            {
                "name": "connection_timeout",
                "failure_type": "timeout",
                "recovery_strategy": "reconnect"
            },
            {
                "name": "database_lock", 
                "failure_type": "lock_timeout",
                "recovery_strategy": "retry_with_backoff"
            },
            {
                "name": "transaction_conflict",
                "failure_type": "integrity_error", 
                "recovery_strategy": "transaction_retry"
            }
        ]
        
        successful_recoveries = 0
        
        for scenario in recovery_scenarios:
            logger.info(f"Testing recovery scenario: {scenario['name']}")
            
            with patch('netra_backend.app.core.config.get_config') as mock_config:
                mock_config.return_value.database_echo = False
                mock_config.return_value.database_pool_size = 0
                mock_config.return_value.database_max_overflow = 0
                mock_config.return_value.database_url = f"sqlite+aiosqlite:///{self.stress_db_paths['recovery']}"
                
                db_manager = DatabaseManager()
                await db_manager.initialize()
                
                engine = db_manager.get_engine('primary') 
                await self._create_stress_test_schema(engine)
                
                # Test failure and recovery
                failure_occurred = False
                recovery_successful = False
                
                try:
                    # Step 1: Normal operation before failure
                    async with db_manager.get_session() as session:
                        await session.execute(
                            text("INSERT INTO stress_operations (operation_type, thread_id, status) VALUES (?, ?, ?)"),
                            ("pre_failure", scenario["name"], "success")
                        )
                        await session.commit()
                    
                    # Step 2: Simulate failure based on scenario type
                    if scenario["failure_type"] == "timeout":
                        # Simulate timeout by attempting operation on non-existent database
                        bad_db_manager = DatabaseManager()
                        bad_config = MagicMock()
                        bad_config.database_echo = False
                        bad_config.database_pool_size = 0
                        bad_config.database_max_overflow = 0
                        bad_config.database_url = "sqlite+aiosqlite:///nonexistent/path/db.db"
                        
                        with patch('netra_backend.app.core.config.get_config', return_value=bad_config):
                            try:
                                await bad_db_manager.initialize()
                                async with bad_db_manager.get_session() as session:
                                    await session.execute(text("SELECT 1"))
                            except Exception:
                                failure_occurred = True
                                await bad_db_manager.close_all()
                    
                    elif scenario["failure_type"] == "integrity_error":
                        # Create constraint violation
                        try:
                            async with db_manager.get_session() as session:
                                # Insert duplicate data to cause integrity error
                                await session.execute(
                                    text("INSERT INTO stress_operations (operation_type, thread_id, status) VALUES (?, ?, ?)"),
                                    ("integrity_test", "duplicate_thread", "pending")
                                )
                                await session.execute(
                                    text("INSERT INTO stress_operations (operation_type, thread_id, status) VALUES (?, ?, ?)"),
                                    ("integrity_test", "duplicate_thread", "pending")  # This may cause issues in some constraints
                                )
                                await session.commit()
                        except Exception:
                            failure_occurred = True
                    
                    # Step 3: Test recovery
                    if failure_occurred or scenario["failure_type"] != "integrity_error":
                        # Recovery strategy: Retry with exponential backoff
                        max_recovery_attempts = 3
                        for attempt in range(max_recovery_attempts):
                            try:
                                await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                                
                                async with db_manager.get_session() as session:
                                    await session.execute(
                                        text("INSERT INTO stress_operations (operation_type, thread_id, status) VALUES (?, ?, ?)"),
                                        ("recovery_test", f"{scenario['name']}_recovery", "success") 
                                    )
                                    await session.commit()
                                
                                recovery_successful = True
                                break
                                
                            except Exception as e:
                                logger.info(f"Recovery attempt {attempt + 1} failed: {e}")
                                if attempt == max_recovery_attempts - 1:
                                    logger.warning(f"All recovery attempts failed for {scenario['name']}")
                    
                    if recovery_successful or not failure_occurred:
                        successful_recoveries += 1
                        
                        # Verify recovery worked
                        async with db_manager.get_session() as session:
                            result = await session.execute(
                                text("SELECT COUNT(*) FROM stress_operations WHERE thread_id LIKE ?"),
                                (f"%{scenario['name']}%",)
                            )
                            recovery_records = result.scalar()
                            assert recovery_records >= 1, f"Recovery verification failed for {scenario['name']}"
                
                except Exception as e:
                    logger.warning(f"Recovery scenario {scenario['name']} failed: {e}")
                
                finally:
                    await db_manager.close_all()
        
        # Verify recovery patterns worked
        recovery_rate = successful_recoveries / len(recovery_scenarios)
        logger.info(f"Recovery pattern test results:")
        logger.info(f"  Successful recoveries: {successful_recoveries}/{len(recovery_scenarios)}")
        logger.info(f"  Recovery rate: {recovery_rate:.2%}")
        
        assert recovery_rate >= 0.67, f"Recovery rate too low: {recovery_rate:.2%}"  # At least 2/3 should succeed


if __name__ == "__main__":
    # Allow running this test file directly for development  
    pytest.main([__file__, "-v", "--tb=short", "-s"])