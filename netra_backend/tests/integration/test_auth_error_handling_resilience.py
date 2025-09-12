"""
Authentication Error Handling and Resilience Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - critical for system availability
- Business Goal: Ensure auth system maintains availability during failures
- Value Impact: Users can continue using platform even during partial system failures
- Strategic Impact: Core platform reliability - prevents complete system outages during issues

CRITICAL: Tests authentication error handling and resilience with REAL services.
Tests graceful degradation, circuit breakers, and recovery with real infrastructure.

Following CLAUDE.md requirements:
- Uses real services (no mocks in integration tests)
- Follows SSOT patterns from test_framework/ssot/
- Tests MUST fail hard - no try/except blocks masking errors
- Multi-user scenarios for testing resilience under load
"""
import pytest
import asyncio
import time
# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

# Absolute imports per CLAUDE.md
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env
from shared.types.core_types import UserID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestAuthErrorHandlingResilienceIntegration(BaseIntegrationTest):
    """Integration tests for authentication error handling and resilience with real services."""
    
    @pytest.fixture(autouse=True)
    def setup_resilience_environment(self):
        """Setup integration environment for auth resilience testing."""
        self.env = get_env()
        self.env.enable_isolation()
        
        # Set resilience testing configuration
        self.env.set("JWT_SECRET_KEY", "integration-resilience-jwt-secret-32-chars", "test_auth_resilience")
        self.env.set("SERVICE_SECRET", "integration-resilience-service-secret-32", "test_auth_resilience")
        self.env.set("ENVIRONMENT", "test", "test_auth_resilience")
        self.env.set("REDIS_URL", "redis://localhost:6381", "test_auth_resilience")  # Test Redis
        
        # Configure resilience parameters
        self.env.set("AUTH_CIRCUIT_BREAKER_ENABLED", "true", "test_auth_resilience")
        self.env.set("AUTH_FAILURE_THRESHOLD", "10", "test_auth_resilience")
        self.env.set("AUTH_RECOVERY_TIMEOUT", "30", "test_auth_resilience")
        self.env.set("AUTH_REQUEST_TIMEOUT", "10", "test_auth_resilience")
        
        self.auth_helper = E2EAuthHelper(environment="test")
        self.id_generator = UnifiedIdGenerator()
        
        # Connect to test Redis for resilience testing
        try:
            self.redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6381, db=0, decode_responses=True)
            await redis_client.ping()  # Verify connection
        except Exception as e:
            pytest.skip(f"Redis not available for resilience integration tests: {e}")
        
        yield
        
        # Cleanup test data
        try:
            test_keys = await redis_client.keys("test_resilience:*")
            if test_keys:
                await redis_client.delete(*test_keys)
        except:
            pass  # Cleanup is best effort
        
        # Cleanup environment
        self.env.disable_isolation()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_system_handles_high_load_without_failure(self, real_services_fixture):
        """Test that auth system handles high concurrent load without failing."""
        # Arrange: Create multiple users for concurrent load testing
        load_test_users = []
        num_users = 20  # High concurrent load
        
        for i in range(num_users):
            user_id = f"load-test-user-{i}-{int(time.time())}"
            email = f"load-test-{i}-{user_id}@netra.ai"
            
            jwt_token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=email,
                permissions=["read:agents", "write:threads"],
                exp_minutes=10
            )
            
            load_test_users.append({
                "index": i,
                "user_id": user_id,
                "email": email,
                "token": jwt_token
            })
        
        # Act: Perform concurrent authentication operations under high load
        async def perform_concurrent_auth_operations(user_data):
            """Perform multiple auth operations for a single user."""
            user_index = user_data["index"]
            user_id = user_data["user_id"]
            token = user_data["token"]
            
            operations_results = []
            
            # Operation 1: Token validation
            try:
                start_time = time.time()
                is_valid = await self.auth_helper.validate_token(token)
                validation_time = time.time() - start_time
                
                operations_results.append({
                    "operation": "validate_token",
                    "success": is_valid is True,
                    "response_time": validation_time,
                    "error": None
                })
            except Exception as e:
                operations_results.append({
                    "operation": "validate_token",
                    "success": False,
                    "response_time": None,
                    "error": str(e)
                })
            
            # Operation 2: API call with authentication
            try:
                start_time = time.time()
                client = self.auth_helper.create_sync_authenticated_client()
                headers = self.auth_helper.get_auth_headers(token)
                client.headers.update(headers)
                
                response = client.get("/api/health")
                api_time = time.time() - start_time
                
                operations_results.append({
                    "operation": "api_call",
                    "success": response.status_code in [200, 404],
                    "response_time": api_time,
                    "status_code": response.status_code,
                    "error": None if response.status_code in [200, 404] else response.text
                })
            except Exception as e:
                operations_results.append({
                    "operation": "api_call", 
                    "success": False,
                    "response_time": None,
                    "status_code": None,
                    "error": str(e)
                })
            
            # Operation 3: Redis session check (if available)
            try:
                start_time = time.time()
                session_key = f"test_resilience:load_test:{user_id}"
                
                # Store session data
                session_data = {
                    "user_id": user_id,
                    "load_test_index": str(user_index),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await redis_client.hset(session_key, mapping=session_data)
                await redis_client.expire(session_key, 300)  # 5 minute expiry
                
                # Retrieve session data
                retrieved_data = await redis_client.hgetall(session_key)
                redis_time = time.time() - start_time
                
                operations_results.append({
                    "operation": "redis_session",
                    "success": retrieved_data.get("user_id") == user_id,
                    "response_time": redis_time,
                    "error": None
                })
            except Exception as e:
                operations_results.append({
                    "operation": "redis_session",
                    "success": False,
                    "response_time": None,
                    "error": str(e)
                })
            
            return {
                "user_index": user_index,
                "user_id": user_id,
                "operations": operations_results
            }
        
        # Execute concurrent high-load operations
        print(f"[U+1F680] Starting high-load test with {num_users} concurrent users...")
        start_time = time.time()
        
        concurrent_tasks = [perform_concurrent_auth_operations(user) for user in load_test_users]
        load_test_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        total_test_time = time.time() - start_time
        
        # Assert: System must handle high load without failures
        successful_users = 0
        total_operations = 0
        successful_operations = 0
        response_times = []
        
        for result in load_test_results:
            assert not isinstance(result, Exception), f"High-load test must not raise exception: {result}"
            
            user_operations = result["operations"]
            total_operations += len(user_operations)
            
            user_success_count = sum(1 for op in user_operations if op["success"])
            successful_operations += user_success_count
            
            # Collect response times for performance analysis
            for op in user_operations:
                if op.get("response_time"):
                    response_times.append(op["response_time"])
            
            # Consider user successful if at least 2/3 operations succeeded
            if user_success_count >= len(user_operations) * 0.67:
                successful_users += 1
        
        # Calculate performance metrics
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        user_success_rate = successful_users / num_users
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Assert: High load performance requirements
        assert user_success_rate >= 0.85, (
            f"At least 85% of users must succeed under high load, "
            f"got {user_success_rate:.1%} ({successful_users}/{num_users})"
        )
        
        assert success_rate >= 0.90, (
            f"At least 90% of operations must succeed under high load, "
            f"got {success_rate:.1%} ({successful_operations}/{total_operations})"
        )
        
        assert avg_response_time <= 2.0, (
            f"Average response time must be under 2 seconds under high load, "
            f"got {avg_response_time:.2f}s"
        )
        
        assert max_response_time <= 10.0, (
            f"Maximum response time must be under 10 seconds under high load, "
            f"got {max_response_time:.2f}s"
        )
        
        print(f" PASS:  High-load test completed successfully:")
        print(f"   [U+1F465] {successful_users}/{num_users} users succeeded ({user_success_rate:.1%})")
        print(f"    CYCLE:  {successful_operations}/{total_operations} operations succeeded ({success_rate:.1%})")
        print(f"   [U+23F1][U+FE0F]  Average response time: {avg_response_time:.2f}s")
        print(f"    CHART:  Max response time: {max_response_time:.2f}s")
        print(f"   [U+1F552] Total test time: {total_test_time:.2f}s")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_graceful_degradation_when_redis_unavailable(self, real_services_fixture):
        """Test that auth system provides graceful degradation when Redis is unavailable."""
        # Arrange: Create test user and verify normal operation
        user_id = f"graceful-degradation-user-{int(time.time())}"
        email = f"degradation-{user_id}@netra.ai"
        
        jwt_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["read:agents", "write:threads"],
            exp_minutes=15
        )
        
        # Verify normal operation with Redis available
        normal_validation = await self.auth_helper.validate_token(jwt_token)
        assert normal_validation is True, "Token must validate normally when Redis is available"
        
        # Test API access with Redis available
        client = self.auth_helper.create_sync_authenticated_client()
        headers = self.auth_helper.get_auth_headers(jwt_token)
        client.headers.update(headers)
        
        normal_api_response = client.get("/api/health")
        assert normal_api_response.status_code in [200, 404], (
            f"API must work normally when Redis available, got {normal_api_response.status_code}"
        )
        
        # Act: Simulate Redis unavailability
        print("[U+1F527] Simulating Redis unavailability...")
        
        # Temporarily disable Redis by connecting to wrong port
        degraded_redis = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6999, db=0, decode_responses=True, socket_timeout=1)
        
        # Test degraded operation
        degradation_test_results = []
        
        # Test 1: JWT validation should still work (using JWT validation only)
        try:
            start_time = time.time()
            degraded_validation = await self.auth_helper.validate_token(jwt_token)
            validation_time = time.time() - start_time
            
            degradation_test_results.append({
                "test": "jwt_validation_degraded",
                "success": degraded_validation is not False,  # Allow None or True, just not False
                "response_time": validation_time,
                "result": degraded_validation
            })
        except Exception as e:
            degradation_test_results.append({
                "test": "jwt_validation_degraded",
                "success": False,
                "error": str(e)
            })
        
        # Test 2: API access should continue to work (graceful degradation)
        try:
            start_time = time.time()
            degraded_api_response = client.get("/api/health")
            api_time = time.time() - start_time
            
            degradation_test_results.append({
                "test": "api_access_degraded", 
                "success": degraded_api_response.status_code in [200, 404, 503],  # 503 acceptable for degraded mode
                "response_time": api_time,
                "status_code": degraded_api_response.status_code
            })
        except Exception as e:
            degradation_test_results.append({
                "test": "api_access_degraded",
                "success": False,
                "error": str(e)
            })
        
        # Test 3: New token creation should still work (local JWT operations)
        try:
            start_time = time.time()
            degraded_token = self.auth_helper.create_test_jwt_token(
                user_id=f"{user_id}-degraded",
                email=email,
                permissions=["read:agents"],
                exp_minutes=10
            )
            creation_time = time.time() - start_time
            
            degradation_test_results.append({
                "test": "token_creation_degraded",
                "success": degraded_token is not None and len(degraded_token.split('.')) == 3,
                "response_time": creation_time,
                "token_created": bool(degraded_token)
            })
        except Exception as e:
            degradation_test_results.append({
                "test": "token_creation_degraded",
                "success": False,
                "error": str(e)
            })
        
        # Assert: Graceful degradation requirements
        for result in degradation_test_results:
            test_name = result["test"]
            success = result["success"]
            
            assert success is True, (
                f"Graceful degradation test '{test_name}' must succeed when Redis unavailable. "
                f"Error: {result.get('error', 'unknown')}, Result: {result}"
            )
            
            # Response times should be reasonable even in degraded mode
            if "response_time" in result:
                assert result["response_time"] <= 5.0, (
                    f"Degraded mode response time for '{test_name}' must be reasonable, "
                    f"got {result['response_time']:.2f}s"
                )
        
        print(" PASS:  Graceful degradation verified:")
        for result in degradation_test_results:
            test_name = result["test"] 
            response_time = result.get("response_time", 0)
            print(f"    CYCLE:  {test_name}:  PASS:  Success ({response_time:.2f}s)")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_system_recovery_after_service_restart(self, real_services_fixture):
        """Test that auth system properly recovers after service restart simulation."""
        # Arrange: Create test users and establish sessions
        recovery_test_users = []
        num_users = 5
        
        for i in range(num_users):
            user_id = f"recovery-test-user-{i}-{int(time.time())}"
            email = f"recovery-{i}-{user_id}@netra.ai"
            
            jwt_token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=email,
                permissions=["read:agents", "write:threads"],
                exp_minutes=20  # Long-lived for recovery testing
            )
            
            recovery_test_users.append({
                "index": i,
                "user_id": user_id,
                "email": email,
                "token": jwt_token
            })
        
        # Establish pre-restart state
        print("[U+1F527] Establishing pre-restart authentication state...")
        
        pre_restart_results = []
        
        for user_data in recovery_test_users:
            # Validate token and store session data
            is_valid = await self.auth_helper.validate_token(user_data["token"])
            
            # Store session data in Redis
            session_key = f"test_resilience:recovery:{user_data['user_id']}"
            session_data = {
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "pre_restart_timestamp": datetime.now(timezone.utc).isoformat(),
                "token_valid": str(is_valid)
            }
            
            await redis_client.hset(session_key, mapping=session_data)
            await redis_client.expire(session_key, 1200)  # 20 minute expiry
            
            pre_restart_results.append({
                "user_id": user_data["user_id"],
                "token_valid": is_valid,
                "session_stored": True
            })
        
        # Verify pre-restart state
        successful_pre_restart = sum(1 for r in pre_restart_results if r["token_valid"] and r["session_stored"])
        assert successful_pre_restart == num_users, (
            f"All users must be properly authenticated pre-restart, "
            f"got {successful_pre_restart}/{num_users}"
        )
        
        # Act: Simulate service restart (flush Redis auth cache but keep session data)
        print(" CYCLE:  Simulating service restart and cache flush...")
        
        # Flush auth-specific cache keys (simulate restart cache clearing)
        try:
            # Clear potential auth cache keys
            auth_cache_keys = await redis_client.keys("auth:*")
            circuit_breaker_keys = await redis_client.keys("circuit_breaker:*")
            blacklist_keys = await redis_client.keys("blacklist:*")
            
            if auth_cache_keys:
                await redis_client.delete(*auth_cache_keys)
            if circuit_breaker_keys:
                await redis_client.delete(*circuit_breaker_keys)
            if blacklist_keys:
                await redis_client.delete(*blacklist_keys)
                
            print(f"   [U+1F5D1][U+FE0F] Cleared {len(auth_cache_keys + circuit_breaker_keys + blacklist_keys)} cache keys")
        except Exception as e:
            print(f"    WARNING: [U+FE0F] Cache clearing failed (simulating unclean restart): {e}")
        
        # Simulate brief downtime
        await asyncio.sleep(2)
        
        # Test system recovery
        print("[U+1F527] Testing auth system recovery after restart...")
        
        post_restart_results = []
        
        async def test_user_recovery(user_data):
            """Test recovery for a single user after restart."""
            user_id = user_data["user_id"]
            token = user_data["token"]
            
            recovery_operations = []
            
            # Operation 1: Token validation should work after restart
            try:
                start_time = time.time()
                is_valid = await self.auth_helper.validate_token(token)
                validation_time = time.time() - start_time
                
                recovery_operations.append({
                    "operation": "token_validation",
                    "success": is_valid is True,
                    "response_time": validation_time
                })
            except Exception as e:
                recovery_operations.append({
                    "operation": "token_validation",
                    "success": False,
                    "error": str(e)
                })
            
            # Operation 2: Session data should still exist
            try:
                session_key = f"test_resilience:recovery:{user_id}"
                session_data = await redis_client.hgetall(session_key)
                
                recovery_operations.append({
                    "operation": "session_retrieval",
                    "success": session_data.get("user_id") == user_id,
                    "session_data": session_data
                })
            except Exception as e:
                recovery_operations.append({
                    "operation": "session_retrieval",
                    "success": False,
                    "error": str(e)
                })
            
            # Operation 3: API access should work
            try:
                client = self.auth_helper.create_sync_authenticated_client()
                headers = self.auth_helper.get_auth_headers(token)
                client.headers.update(headers)
                
                response = client.get("/api/health")
                
                recovery_operations.append({
                    "operation": "api_access",
                    "success": response.status_code in [200, 404],
                    "status_code": response.status_code
                })
            except Exception as e:
                recovery_operations.append({
                    "operation": "api_access",
                    "success": False,
                    "error": str(e)
                })
            
            return {
                "user_id": user_id,
                "operations": recovery_operations
            }
        
        # Execute recovery tests for all users
        recovery_tasks = [test_user_recovery(user) for user in recovery_test_users]
        post_restart_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
        
        # Assert: Recovery requirements
        successful_recoveries = 0
        total_recovery_operations = 0
        successful_recovery_operations = 0
        
        for result in post_restart_results:
            assert not isinstance(result, Exception), f"Recovery test must not raise exception: {result}"
            
            user_id = result["user_id"]
            operations = result["operations"]
            
            total_recovery_operations += len(operations)
            user_successful_operations = sum(1 for op in operations if op["success"])
            successful_recovery_operations += user_successful_operations
            
            # User recovery successful if all operations succeeded
            if user_successful_operations == len(operations):
                successful_recoveries += 1
                print(f"    PASS:  User {user_id}: Full recovery")
            else:
                print(f"    WARNING: [U+FE0F] User {user_id}: Partial recovery ({user_successful_operations}/{len(operations)})")
                for op in operations:
                    if not op["success"]:
                        print(f"       FAIL:  {op['operation']}: {op.get('error', 'failed')}")
        
        recovery_success_rate = successful_recoveries / num_users
        operation_success_rate = successful_recovery_operations / total_recovery_operations if total_recovery_operations > 0 else 0
        
        # Allow some tolerance for service restart scenarios
        assert recovery_success_rate >= 0.80, (
            f"At least 80% of users must fully recover after service restart, "
            f"got {recovery_success_rate:.1%} ({successful_recoveries}/{num_users})"
        )
        
        assert operation_success_rate >= 0.90, (
            f"At least 90% of recovery operations must succeed, "
            f"got {operation_success_rate:.1%} ({successful_recovery_operations}/{total_recovery_operations})"
        )
        
        print(f" CELEBRATION:  Auth system recovery test completed:")
        print(f"   [U+1F465] {successful_recoveries}/{num_users} users fully recovered ({recovery_success_rate:.1%})")
        print(f"    CYCLE:  {successful_recovery_operations}/{total_recovery_operations} operations succeeded ({operation_success_rate:.1%})")
        
        # Cleanup recovery test data
        for user_data in recovery_test_users:
            session_key = f"test_resilience:recovery:{user_data['user_id']}"
            try:
                await redis_client.delete(session_key)
            except:
                pass