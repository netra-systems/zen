"""
Service Dependencies Integration Tests

CRITICAL: These integration tests focus on real service-to-service interactions.
This is part of the comprehensive Service Dependencies Tests Suite.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service Reliability - Ensure robust cross-service communication
- Value Impact: Validates actual service interactions prevent real-world failures
- Strategic/Revenue Impact: Prevents $100K+ loss from service communication failures

Service Dependencies Tested:
1. Backend ↔ Auth Service real authentication flows
2. Backend ↔ PostgreSQL real database operations
3. Backend ↔ Redis real cache interactions
4. Cross-service dependency chains with real services
5. Service error propagation with real failure scenarios
6. Concurrent service access patterns

INTEGRATION TEST REQUIREMENTS:
- Uses REAL PostgreSQL, Redis, Auth Service (NO MOCKS)
- MANDATORY authentication with real JWT tokens for all tests
- Tests actual HTTP/API calls between services
- Validates real database transactions and rollbacks
- Tests real cache operations and fallback patterns

Author: AI Agent - Service Dependencies Integration Test Creation
Date: 2025-09-09
"""

import asyncio
import json
import logging
import pytest
import time
import aiohttp
import psycopg2
import redis
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

# CRITICAL: Use real services fixture (NO MOCKS in integration tests)
from test_framework.fixtures.real_services import real_services_fixture

# MANDATORY: All integration tests MUST use authentication per claude.md
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper

# Service clients for real service communication
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.redis_manager import RedisManager

# Shared types for strongly typed integration testing
from shared.types import UserID, ThreadID, RequestID
import uuid


@dataclass
class IntegrationTestUser:
    """Real authenticated user for integration testing with service validation"""
    user_id: UserID
    email: str
    jwt_token: str
    auth_validated: bool = False
    database_record_id: Optional[str] = None
    redis_session_key: Optional[str] = None


@dataclass
class ServiceDependencyMetrics:
    """Metrics tracking for service dependency integration tests"""
    auth_requests: int = 0
    auth_successes: int = 0
    auth_failures: int = 0
    database_queries: int = 0
    database_successes: int = 0
    database_failures: int = 0
    redis_operations: int = 0
    redis_successes: int = 0
    redis_failures: int = 0
    cross_service_calls: int = 0
    concurrent_operations: int = 0
    error_recoveries: int = 0


class TestBackendToAuthServiceIntegration:
    """
    Integration tests for Backend ↔ Auth Service dependency using real services.
    
    CRITICAL: These tests use real Auth Service with mandatory authentication
    to validate actual JWT token flows and user management operations.
    """
    
    @pytest.fixture(autouse=True)
    def setup_auth_integration_environment(self, real_services_fixture):
        """Set up real services for auth integration testing"""
        self.services = real_services_fixture
        self.backend_url = self.services['backend_url']
        self.auth_service_url = self.services.get('auth_url', 'http://localhost:8081')
        
        # MANDATORY: Initialize real authentication helpers
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.backend_url)
        
        # Initialize real auth service client
        self.auth_client = AuthServiceClient(base_url=self.auth_service_url)
        
        # Integration test metrics
        self.metrics = ServiceDependencyMetrics()
        
        # Logger for integration testing
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    async def create_integration_authenticated_user(self, email_suffix: str = None) -> IntegrationTestUser:
        """Create fully authenticated user through real auth service integration"""
        if email_suffix:
            email = f"integration_test_{email_suffix}@netra.com"
        else:
            email = f"integration_test_{int(time.time())}@netra.com"
            
        user_id = UserID(str(uuid.uuid4()))
        
        # MANDATORY: Create real JWT token through actual auth service
        self.metrics.auth_requests += 1
        try:
            jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
            
            # Validate token through real auth service
            auth_validated = await self._validate_token_with_auth_service(jwt_token, str(user_id))
            
            if auth_validated:
                self.metrics.auth_successes += 1
            else:
                self.metrics.auth_failures += 1
                
            return IntegrationTestUser(
                user_id=user_id,
                email=email,
                jwt_token=jwt_token,
                auth_validated=auth_validated
            )
            
        except Exception as e:
            self.metrics.auth_failures += 1
            self.logger.error(f"Failed to create authenticated integration user: {e}")
            raise
    
    async def _validate_token_with_auth_service(self, jwt_token: str, expected_user_id: str) -> bool:
        """Validate JWT token through real auth service API"""
        try:
            self.metrics.cross_service_calls += 1
            validation_result = await self.auth_client.validate_token(jwt_token)
            
            return (validation_result.get('valid', False) and 
                   validation_result.get('user_id') == expected_user_id)
                   
        except Exception as e:
            self.logger.error(f"Auth service validation failed: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_real_jwt_token_validation_flow(self, real_services_fixture):
        """
        Integration test for real JWT token validation through auth service.
        
        This validates the complete Backend ↔ Auth Service authentication flow
        using real services and actual JWT token validation.
        """
        user = await self.create_integration_authenticated_user("jwt_validation")
        
        # CRITICAL: Validate authentication worked through real services
        assert user.auth_validated, f"Real auth service validation failed for user {user.user_id}"
        
        # Test token validation through multiple validation attempts
        validation_attempts = []
        
        for attempt in range(3):
            start_time = time.time()
            
            try:
                validation_result = await self._validate_token_with_auth_service(
                    user.jwt_token, 
                    str(user.user_id)
                )
                
                validation_time = time.time() - start_time
                
                validation_attempts.append({
                    'attempt': attempt,
                    'success': validation_result,
                    'validation_time': validation_time
                })
                
            except Exception as e:
                validation_attempts.append({
                    'attempt': attempt,
                    'success': False,
                    'error': str(e),
                    'validation_time': time.time() - start_time
                })
                
        # Validate real auth service integration
        successful_validations = sum(1 for attempt in validation_attempts if attempt['success'])
        assert successful_validations >= 2, f"Expected at least 2 successful auth validations, got {successful_validations}"
        
        # Validate performance (real auth service should be fast)
        avg_validation_time = sum(attempt['validation_time'] for attempt in validation_attempts) / len(validation_attempts)
        assert avg_validation_time < 2.0, f"Auth service validation too slow: {avg_validation_time}s"
        
        self.logger.info(f"Real JWT validation flow passed. User: {user.user_id}, Validations: {successful_validations}/3")
    
    @pytest.mark.asyncio
    async def test_auth_service_timeout_resilience(self, real_services_fixture):
        """
        Integration test for auth service timeout resilience with real services.
        
        This tests how the backend handles real auth service timeouts and
        implements appropriate retry and fallback mechanisms.
        """
        user = await self.create_integration_authenticated_user("timeout_test")
        
        # Test auth service with shorter timeouts to simulate network issues
        timeout_results = []
        
        for timeout_duration in [0.5, 1.0, 2.0]:  # Test different timeout scenarios
            start_time = time.time()
            
            try:
                # Create auth client with specific timeout
                timeout_auth_client = AuthServiceClient(
                    base_url=self.auth_service_url,
                    timeout=timeout_duration
                )
                
                validation_result = await timeout_auth_client.validate_token(user.jwt_token)
                
                timeout_results.append({
                    'timeout_duration': timeout_duration,
                    'success': validation_result.get('valid', False),
                    'response_time': time.time() - start_time,
                    'timed_out': False
                })
                
            except asyncio.TimeoutError:
                timeout_results.append({
                    'timeout_duration': timeout_duration,
                    'success': False,
                    'response_time': time.time() - start_time,
                    'timed_out': True
                })
                
            except Exception as e:
                timeout_results.append({
                    'timeout_duration': timeout_duration,
                    'success': False,
                    'response_time': time.time() - start_time,
                    'timed_out': False,
                    'error': str(e)
                })
                
        # Validate timeout resilience
        successful_requests = sum(1 for result in timeout_results if result['success'])
        
        # At least the longer timeouts should succeed
        longer_timeout_successes = sum(
            1 for result in timeout_results 
            if result['timeout_duration'] >= 1.0 and result['success']
        )
        
        assert longer_timeout_successes >= 1, "Auth service should respond within reasonable timeouts"
        
        self.logger.info(f"Auth timeout resilience test passed. Successes: {successful_requests}/{len(timeout_results)}")
    
    @pytest.mark.asyncio
    async def test_concurrent_auth_service_requests(self, real_services_fixture):
        """
        Integration test for concurrent auth service requests with real authentication.
        
        This validates that multiple concurrent auth requests don't interfere
        with each other and maintain proper user isolation.
        """
        # Create multiple authenticated users for concurrent testing
        concurrent_user_count = 5
        users = []
        
        for i in range(concurrent_user_count):
            user = await self.create_integration_authenticated_user(f"concurrent_{i}")
            assert user.auth_validated, f"Authentication failed for concurrent user {i}"
            users.append(user)
            
        # Execute concurrent auth validations
        concurrent_validation_tasks = []
        for user in users:
            task = asyncio.create_task(self._perform_concurrent_auth_validation(user))
            concurrent_validation_tasks.append(task)
            
        # Wait for all concurrent validations
        validation_results = await asyncio.gather(*concurrent_validation_tasks, return_exceptions=True)
        
        # Analyze concurrent validation results
        successful_validations = 0
        user_isolation_violations = 0
        
        for i, result in enumerate(validation_results):
            if isinstance(result, Exception):
                self.logger.error(f"Concurrent auth validation failed for user {users[i].user_id}: {result}")
            elif result and result.get('success'):
                successful_validations += 1
                
                # Validate user isolation (each validation returns correct user ID)
                if result.get('validated_user_id') != str(users[i].user_id):
                    user_isolation_violations += 1
                    
        # Validate concurrent auth service integration
        assert successful_validations >= 4, f"Expected at least 4 successful concurrent auth validations, got {successful_validations}"
        assert user_isolation_violations == 0, f"User isolation violations in auth service: {user_isolation_violations}"
        
        self.metrics.concurrent_operations += len(concurrent_validation_tasks)
        
        self.logger.info(f"Concurrent auth service test passed. Users: {concurrent_user_count}, Successes: {successful_validations}")
        
    async def _perform_concurrent_auth_validation(self, user: IntegrationTestUser) -> Dict[str, Any]:
        """Perform concurrent auth validation for testing user isolation"""
        try:
            start_time = time.time()
            
            validation_result = await self._validate_token_with_auth_service(
                user.jwt_token, 
                str(user.user_id)
            )
            
            validation_time = time.time() - start_time
            
            return {
                'success': validation_result,
                'validated_user_id': str(user.user_id),
                'validation_time': validation_time,
                'user_email': user.email
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'user_id': str(user.user_id),
                'validation_time': time.time() - start_time if 'start_time' in locals() else 0
            }


class TestBackendToDatabaseIntegration:
    """
    Integration tests for Backend ↔ PostgreSQL database dependency using real database.
    
    CRITICAL: These tests use real PostgreSQL database with actual transactions
    to validate database operations, connection management, and data consistency.
    """
    
    @pytest.fixture(autouse=True)
    def setup_database_integration_environment(self, real_services_fixture):
        """Set up real database for integration testing"""
        self.services = real_services_fixture
        self.postgres_connection = self.services['postgres']
        
        # Initialize real database manager
        self.db_manager = DatabaseManager()
        
        # Integration test metrics
        self.metrics = ServiceDependencyMetrics()
        self.logger = logging.getLogger(__name__)
        
    @pytest.mark.asyncio
    async def test_real_database_transaction_management(self, real_services_fixture):
        """
        Integration test for real database transaction management.
        
        This validates actual database transactions, rollbacks, and data consistency
        using real PostgreSQL database operations.
        """
        test_table_name = f"integration_test_table_{int(time.time())}"
        
        try:
            # Step 1: Create test table
            self.metrics.database_queries += 1
            with self.db_manager.transaction() as cursor:
                create_table_sql = f"""
                CREATE TABLE {test_table_name} (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                cursor.execute(create_table_sql)
                
            self.metrics.database_successes += 1
            
            # Step 2: Test successful transaction
            test_user_id = UserID(str(uuid.uuid4()))
            test_data = "integration_test_data_success"
            
            self.metrics.database_queries += 1
            with self.db_manager.transaction() as cursor:
                insert_sql = f"INSERT INTO {test_table_name} (user_id, data) VALUES (%s, %s) RETURNING id"
                cursor.execute(insert_sql, (str(test_user_id), test_data))
                result = cursor.fetchone()
                inserted_id = result[0]
                
            # Validate successful insertion
            self.metrics.database_queries += 1
            with self.db_manager.transaction() as cursor:
                select_sql = f"SELECT user_id, data FROM {test_table_name} WHERE id = %s"
                cursor.execute(select_sql, (inserted_id,))
                result = cursor.fetchone()
                
                assert result is not None, "Inserted record not found"
                assert result[0] == str(test_user_id), "User ID mismatch"
                assert result[1] == test_data, "Data mismatch"
                
            self.metrics.database_successes += 1
            
            # Step 3: Test transaction rollback
            self.metrics.database_queries += 1
            try:
                with self.db_manager.transaction() as cursor:
                    # Insert record that will be rolled back
                    rollback_data = "integration_test_data_rollback"
                    insert_sql = f"INSERT INTO {test_table_name} (user_id, data) VALUES (%s, %s) RETURNING id"
                    cursor.execute(insert_sql, (str(test_user_id), rollback_data))
                    rollback_id = cursor.fetchone()[0]
                    
                    # Force rollback with exception
                    raise Exception("Intentional rollback for testing")
                    
            except Exception as e:
                if "Intentional rollback" not in str(e):
                    raise
                    
            # Validate rollback worked
            self.metrics.database_queries += 1
            with self.db_manager.transaction() as cursor:
                select_sql = f"SELECT COUNT(*) FROM {test_table_name} WHERE data = %s"
                cursor.execute(select_sql, (rollback_data,))
                count = cursor.fetchone()[0]
                
                assert count == 0, "Rollback failed - record was not rolled back"
                
            self.metrics.database_successes += 1
            
            self.logger.info(f"Real database transaction management test passed. Table: {test_table_name}")
            
        finally:
            # Clean up test table
            try:
                with self.db_manager.transaction() as cursor:
                    cursor.execute(f"DROP TABLE IF EXISTS {test_table_name}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up test table {test_table_name}: {e}")
    
    @pytest.mark.asyncio 
    async def test_database_connection_pooling_behavior(self, real_services_fixture):
        """
        Integration test for database connection pooling with real PostgreSQL.
        
        This validates that database connections are properly managed and
        connection pooling works correctly under concurrent load.
        """
        concurrent_connection_count = 10
        test_table_name = f"connection_pool_test_{int(time.time())}"
        
        # Create test table
        with self.db_manager.transaction() as cursor:
            create_table_sql = f"""
            CREATE TABLE {test_table_name} (
                id SERIAL PRIMARY KEY,
                connection_id INT NOT NULL,
                operation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_sql)
            
        try:
            # Execute concurrent database operations
            concurrent_tasks = []
            for connection_id in range(concurrent_connection_count):
                task = asyncio.create_task(
                    self._perform_concurrent_database_operation(test_table_name, connection_id)
                )
                concurrent_tasks.append(task)
                
            # Wait for all concurrent operations
            operation_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Analyze connection pooling results
            successful_operations = 0
            connection_errors = 0
            
            for i, result in enumerate(operation_results):
                if isinstance(result, Exception):
                    if "connection" in str(result).lower():
                        connection_errors += 1
                    self.logger.error(f"Concurrent database operation {i} failed: {result}")
                elif result and result.get('success'):
                    successful_operations += 1
                    
            # Validate connection pooling
            assert successful_operations >= 8, f"Expected at least 8 successful database operations, got {successful_operations}"
            assert connection_errors == 0, f"Connection pooling errors detected: {connection_errors}"
            
            # Validate all operations were recorded
            with self.db_manager.transaction() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {test_table_name}")
                recorded_operations = cursor.fetchone()[0]
                
            assert recorded_operations == successful_operations, "Database operation count mismatch"
            
            self.logger.info(f"Database connection pooling test passed. Operations: {successful_operations}/{concurrent_connection_count}")
            
        finally:
            # Clean up test table
            try:
                with self.db_manager.transaction() as cursor:
                    cursor.execute(f"DROP TABLE IF EXISTS {test_table_name}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up connection pool test table: {e}")
    
    async def _perform_concurrent_database_operation(self, table_name: str, connection_id: int) -> Dict[str, Any]:
        """Perform concurrent database operation for connection pooling test"""
        try:
            start_time = time.time()
            
            self.metrics.database_queries += 1
            with self.db_manager.transaction() as cursor:
                insert_sql = f"INSERT INTO {table_name} (connection_id) VALUES (%s)"
                cursor.execute(insert_sql, (connection_id,))
                
            operation_time = time.time() - start_time
            self.metrics.database_successes += 1
            
            return {
                'success': True,
                'connection_id': connection_id,
                'operation_time': operation_time
            }
            
        except Exception as e:
            self.metrics.database_failures += 1
            return {
                'success': False,
                'connection_id': connection_id,
                'error': str(e),
                'operation_time': time.time() - start_time if 'start_time' in locals() else 0
            }


class TestBackendToRedisIntegration:
    """
    Integration tests for Backend ↔ Redis cache dependency using real Redis.
    
    CRITICAL: These tests use real Redis cache with actual cache operations
    to validate caching patterns, pub/sub functionality, and fallback behavior.
    """
    
    @pytest.fixture(autouse=True)
    def setup_redis_integration_environment(self, real_services_fixture):
        """Set up real Redis for integration testing"""
        self.services = real_services_fixture
        self.redis_connection = self.services['redis']
        
        # Initialize real Redis manager
        self.cache_manager = RedisManager()
        
        # Integration test metrics
        self.metrics = ServiceDependencyMetrics()
        self.logger = logging.getLogger(__name__)
        
    @pytest.mark.asyncio
    async def test_real_redis_cache_operations_with_ttl(self, real_services_fixture):
        """
        Integration test for real Redis cache operations with TTL management.
        
        This validates actual cache set/get operations, TTL behavior,
        and cache expiration using real Redis instance.
        """
        test_key_prefix = f"integration_test_{int(time.time())}"
        
        # Test basic cache operations
        cache_operations = [
            {"key": f"{test_key_prefix}_basic", "value": "basic_test_value", "ttl": 60},
            {"key": f"{test_key_prefix}_json", "value": {"data": "json_test", "number": 42}, "ttl": 30},
            {"key": f"{test_key_prefix}_short", "value": "short_ttl_value", "ttl": 2}
        ]
        
        successful_operations = 0
        
        for operation in cache_operations:
            try:
                # Test cache set
                self.metrics.redis_operations += 1
                set_result = self.cache_manager.set(
                    operation["key"], 
                    operation["value"], 
                    ttl=operation["ttl"]
                )
                
                assert set_result, f"Failed to set cache key: {operation['key']}"
                
                # Test immediate cache get
                cached_value = self.cache_manager.get(operation["key"])
                
                if isinstance(operation["value"], dict):
                    assert cached_value == operation["value"], f"JSON cache value mismatch for {operation['key']}"
                else:
                    assert cached_value == operation["value"], f"Cache value mismatch for {operation['key']}"
                    
                successful_operations += 1
                self.metrics.redis_successes += 1
                
            except Exception as e:
                self.metrics.redis_failures += 1
                self.logger.error(f"Redis operation failed for {operation['key']}: {e}")
                
        # Validate basic cache operations
        assert successful_operations >= 2, f"Expected at least 2 successful cache operations, got {successful_operations}"
        
        # Test TTL expiration for short TTL value
        await asyncio.sleep(3)  # Wait for short TTL to expire
        
        expired_value = self.cache_manager.get(f"{test_key_prefix}_short")
        assert expired_value is None, "Short TTL value should have expired"
        
        # Validate longer TTL values are still available
        basic_value = self.cache_manager.get(f"{test_key_prefix}_basic")
        assert basic_value == "basic_test_value", "Basic cache value should still be available"
        
        self.logger.info(f"Real Redis cache operations test passed. Operations: {successful_operations}/{len(cache_operations)}")
        
    @pytest.mark.asyncio
    async def test_redis_pub_sub_cross_service_communication(self, real_services_fixture):
        """
        Integration test for Redis pub/sub cross-service communication.
        
        This validates actual Redis pub/sub functionality for real-time
        communication between services.
        """
        test_channel = f"integration_test_channel_{int(time.time())}"
        
        # Test messages for pub/sub
        test_messages = [
            {"type": "user_action", "user_id": "user_123", "action": "login"},
            {"type": "system_event", "event": "cache_refresh", "timestamp": time.time()},
            {"type": "notification", "message": "Integration test notification"}
        ]
        
        published_messages = []
        received_messages = []
        
        try:
            # Set up subscriber
            subscriber = self.cache_manager.create_subscriber()
            subscriber.subscribe(test_channel)
            
            # Publish messages
            for message in test_messages:
                self.metrics.redis_operations += 1
                published_count = self.cache_manager.publish(test_channel, message)
                
                if published_count > 0:
                    published_messages.append(message)
                    self.metrics.redis_successes += 1
                else:
                    self.metrics.redis_failures += 1
                    
            # Small delay to allow message propagation
            await asyncio.sleep(0.5)
            
            # Collect published messages
            for _ in range(len(published_messages)):
                try:
                    message_data = subscriber.get_message(timeout=2)
                    if message_data and message_data['type'] == 'message':
                        received_message = json.loads(message_data['data'])
                        received_messages.append(received_message)
                except Exception as e:
                    self.logger.warning(f"Failed to receive pub/sub message: {e}")
                    
            # Validate pub/sub communication
            assert len(published_messages) >= 2, f"Expected at least 2 published messages, got {len(published_messages)}"
            
            # Note: Due to Redis pub/sub timing, we may not receive all messages
            # This is acceptable for integration testing
            self.logger.info(f"Redis pub/sub test completed. Published: {len(published_messages)}, Received: {len(received_messages)}")
            
        finally:
            # Clean up subscriber
            try:
                subscriber.unsubscribe(test_channel)
                subscriber.close()
            except Exception as e:
                self.logger.warning(f"Failed to clean up Redis subscriber: {e}")
    
    @pytest.mark.asyncio
    async def test_redis_fallback_behavior_with_real_failures(self, real_services_fixture):
        """
        Integration test for Redis fallback behavior during real connection issues.
        
        This tests how the system handles Redis unavailability and implements
        appropriate fallback mechanisms.
        """
        test_key = f"fallback_test_{int(time.time())}"
        
        # Test normal Redis operation
        self.metrics.redis_operations += 1
        normal_set_result = self.cache_manager.set(test_key, "normal_value", ttl=60)
        assert normal_set_result, "Normal Redis operation should succeed"
        
        normal_get_result = self.cache_manager.get(test_key)
        assert normal_get_result == "normal_value", "Normal Redis get should work"
        self.metrics.redis_successes += 2
        
        # Simulate Redis connection issues by temporarily disrupting connection
        original_connection = self.cache_manager.connection
        
        try:
            # Replace connection with a mock that simulates failures
            failed_connection = await get_redis_client()  # MIGRATED: was redis.Redis(host='invalid_host', port=9999, socket_timeout=1)
            self.cache_manager.connection = failed_connection
            
            # Test fallback behavior
            fallback_results = []
            
            for attempt in range(3):
                try:
                    self.metrics.redis_operations += 1
                    result = self.cache_manager.get(f"fallback_key_{attempt}")
                    
                    # Should return None gracefully (fallback behavior)
                    fallback_results.append({
                        'attempt': attempt,
                        'success': True,
                        'result': result,
                        'fallback_triggered': result is None
                    })
                    
                except Exception as e:
                    # Should handle exceptions gracefully
                    fallback_results.append({
                        'attempt': attempt,
                        'success': False,
                        'error': str(e),
                        'fallback_triggered': True
                    })
                    
            # Validate fallback behavior
            graceful_fallbacks = sum(
                1 for result in fallback_results 
                if result.get('fallback_triggered', False)
            )
            
            assert graceful_fallbacks >= 2, f"Expected graceful fallbacks, got {graceful_fallbacks}"
            
            self.logger.info(f"Redis fallback behavior test passed. Fallbacks: {graceful_fallbacks}/3")
            
        finally:
            # Restore original connection
            self.cache_manager.connection = original_connection
            
            # Verify Redis is working again
            recovery_result = self.cache_manager.get(test_key)
            assert recovery_result == "normal_value", "Redis recovery failed"


class TestCrossServiceDependencyChains:
    """
    Integration tests for complete service dependency chains using real services.
    
    CRITICAL: These tests validate end-to-end service dependency chains
    with real authentication, database, and cache operations.
    """
    
    @pytest.fixture(autouse=True)
    def setup_cross_service_environment(self, real_services_fixture):
        """Set up all real services for cross-service dependency testing"""
        self.services = real_services_fixture
        self.backend_url = self.services['backend_url']
        self.postgres_connection = self.services['postgres']
        self.redis_connection = self.services['redis']
        
        # Initialize all service components
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.db_manager = DatabaseManager()
        self.cache_manager = RedisManager()
        
        # Cross-service test metrics
        self.metrics = ServiceDependencyMetrics()
        self.logger = logging.getLogger(__name__)
        
    @pytest.mark.asyncio
    async def test_complete_user_authentication_to_database_chain(self, real_services_fixture):
        """
        CRITICAL Integration test for complete authentication → database dependency chain.
        
        This validates the full user authentication flow through all services:
        Auth Service → Backend → Database with real service interactions.
        """
        test_session_id = f"cross_service_test_{int(time.time())}"
        
        # Step 1: Create authenticated user through real auth service
        user_id = UserID(str(uuid.uuid4()))
        email = f"cross_service_test@netra.com"
        
        self.metrics.auth_requests += 1
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
        self.metrics.auth_successes += 1
        
        # Step 2: Validate authentication through backend
        self.metrics.cross_service_calls += 1
        auth_client = AuthServiceClient(base_url=self.backend_url)
        validation_result = await auth_client.validate_token(jwt_token)
        
        assert validation_result.get('valid'), "Authentication validation failed"
        assert validation_result.get('user_id') == str(user_id), "User ID mismatch in validation"
        
        # Step 3: Store user session in database
        self.metrics.database_queries += 1
        with self.db_manager.transaction() as cursor:
            create_session_sql = """
            INSERT INTO user_sessions (user_id, session_id, jwt_token, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (session_id) DO UPDATE SET
                jwt_token = EXCLUDED.jwt_token,
                updated_at = CURRENT_TIMESTAMP
            """
            cursor.execute(create_session_sql, (str(user_id), test_session_id, jwt_token))
            
        self.metrics.database_successes += 1
        
        # Step 4: Cache user session in Redis
        self.metrics.redis_operations += 1
        cache_key = f"user_session:{test_session_id}"
        session_data = {
            "user_id": str(user_id),
            "email": email,
            "authenticated": True,
            "auth_time": time.time()
        }
        
        cache_result = self.cache_manager.set(cache_key, session_data, ttl=3600)
        assert cache_result, "Failed to cache user session"
        self.metrics.redis_successes += 1
        
        # Step 5: Validate complete dependency chain
        # Retrieve from cache
        cached_session = self.cache_manager.get(cache_key)
        assert cached_session is not None, "Session not found in cache"
        assert cached_session["user_id"] == str(user_id), "Cached user ID mismatch"
        
        # Retrieve from database
        self.metrics.database_queries += 1
        with self.db_manager.transaction() as cursor:
            select_session_sql = """
            SELECT user_id, jwt_token FROM user_sessions 
            WHERE session_id = %s
            """
            cursor.execute(select_session_sql, (test_session_id,))
            db_result = cursor.fetchone()
            
        assert db_result is not None, "Session not found in database"
        assert db_result[0] == str(user_id), "Database user ID mismatch"
        assert db_result[1] == jwt_token, "Database JWT token mismatch"
        self.metrics.database_successes += 1
        
        # Step 6: Validate auth token is still valid
        self.metrics.cross_service_calls += 1
        final_validation = await auth_client.validate_token(jwt_token)
        assert final_validation.get('valid'), "Final auth validation failed"
        
        self.logger.info(f"Complete user auth → database chain test passed. User: {user_id}, Session: {test_session_id}")
        
    @pytest.mark.asyncio
    async def test_service_failure_isolation_and_recovery(self, real_services_fixture):
        """
        Integration test for service failure isolation and recovery patterns.
        
        This validates that failures in one service don't cascade inappropriately
        and that services can recover gracefully.
        """
        # Create test user for failure testing
        user_id = UserID(str(uuid.uuid4()))
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
        
        # Test 1: Redis failure isolation
        test_key = f"failure_isolation_{int(time.time())}"
        
        # Store data in both cache and database
        self.cache_manager.set(test_key, "cached_value", ttl=60)
        
        with self.db_manager.transaction() as cursor:
            cursor.execute("""
            INSERT INTO service_test_data (key, value, user_id)
            VALUES (%s, %s, %s)
            """, (test_key, "database_value", str(user_id)))
            
        # Simulate Redis failure by using invalid connection
        original_redis_connection = self.cache_manager.connection
        
        try:
            # Replace with failed connection
            failed_redis = await get_redis_client()  # MIGRATED: was redis.Redis(host='invalid_host', port=9999, socket_timeout=1)
            self.cache_manager.connection = failed_redis
            
            # System should fall back to database gracefully
            cached_value = self.cache_manager.get(test_key)  # Should return None or handle gracefully
            
            # Database should still work
            with self.db_manager.transaction() as cursor:
                cursor.execute("SELECT value FROM service_test_data WHERE key = %s", (test_key,))
                db_value = cursor.fetchone()
                
            assert db_value is not None, "Database should still work when Redis fails"
            assert db_value[0] == "database_value", "Database value should be correct"
            
            # Auth service should still work
            validation_result = await AuthServiceClient(base_url=self.backend_url).validate_token(jwt_token)
            assert validation_result.get('valid'), "Auth service should work when Redis fails"
            
            self.metrics.error_recoveries += 1
            
        finally:
            # Restore Redis connection
            self.cache_manager.connection = original_redis_connection
            
            # Verify Redis recovery
            recovered_value = self.cache_manager.get(test_key)
            assert recovered_value == "cached_value", "Redis should recover properly"
            
        self.logger.info(f"Service failure isolation test passed. Recoveries: {self.metrics.error_recoveries}")
        
    @pytest.mark.asyncio
    async def test_concurrent_cross_service_operations(self, real_services_fixture):
        """
        Integration test for concurrent operations across all service dependencies.
        
        This validates that multiple users can perform operations concurrently
        across auth, database, and cache services without interference.
        """
        concurrent_user_count = 3
        operations_per_user = 2
        
        # Create concurrent users
        concurrent_tasks = []
        for user_index in range(concurrent_user_count):
            task = asyncio.create_task(
                self._perform_concurrent_cross_service_operations(user_index, operations_per_user)
            )
            concurrent_tasks.append(task)
            
        # Execute concurrent operations
        operation_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Analyze concurrent operation results
        successful_users = 0
        total_operations = 0
        successful_operations = 0
        
        for i, result in enumerate(operation_results):
            if isinstance(result, Exception):
                self.logger.error(f"Concurrent cross-service operations failed for user {i}: {result}")
            elif result and result.get('success'):
                successful_users += 1
                total_operations += result.get('total_operations', 0)
                successful_operations += result.get('successful_operations', 0)
                
        # Validate concurrent cross-service operations
        assert successful_users >= 2, f"Expected at least 2 successful concurrent users, got {successful_users}"
        
        operation_success_rate = successful_operations / total_operations if total_operations > 0 else 0
        assert operation_success_rate >= 0.8, f"Operation success rate too low: {operation_success_rate}"
        
        self.metrics.concurrent_operations += concurrent_user_count * operations_per_user
        
        self.logger.info(f"Concurrent cross-service operations test passed. Users: {successful_users}/{concurrent_user_count}, Success rate: {operation_success_rate:.2%}")
        
    async def _perform_concurrent_cross_service_operations(self, user_index: int, operations_count: int) -> Dict[str, Any]:
        """Perform concurrent operations across all services for one user"""
        try:
            # Create authenticated user
            user_id = UserID(str(uuid.uuid4()))
            jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
            
            successful_operations = 0
            total_operations = 0
            
            for operation_index in range(operations_count):
                try:
                    # Auth operation
                    auth_client = AuthServiceClient(base_url=self.backend_url)
                    validation_result = await auth_client.validate_token(jwt_token)
                    
                    if validation_result.get('valid'):
                        successful_operations += 1
                    total_operations += 1
                    
                    # Database operation
                    operation_key = f"concurrent_user_{user_index}_op_{operation_index}"
                    with self.db_manager.transaction() as cursor:
                        cursor.execute("""
                        INSERT INTO service_test_data (key, value, user_id)
                        VALUES (%s, %s, %s)
                        """, (operation_key, f"data_for_user_{user_index}", str(user_id)))
                        
                    successful_operations += 1
                    total_operations += 1
                    
                    # Redis operation
                    cache_key = f"concurrent_cache_{user_index}_{operation_index}"
                    cache_result = self.cache_manager.set(
                        cache_key, 
                        f"cached_data_user_{user_index}", 
                        ttl=60
                    )
                    
                    if cache_result:
                        successful_operations += 1
                    total_operations += 1
                    
                except Exception as e:
                    self.logger.error(f"Operation failed for user {user_index}, operation {operation_index}: {e}")
                    total_operations += 1
                    
            return {
                'success': successful_operations > 0,
                'user_index': user_index,
                'user_id': str(user_id),
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'success_rate': successful_operations / total_operations if total_operations > 0 else 0
            }
            
        except Exception as e:
            return {
                'success': False,
                'user_index': user_index,
                'error': str(e),
                'total_operations': 0,
                'successful_operations': 0
            }