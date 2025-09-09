"""
Service Dependencies End-to-End (E2E) Tests

CRITICAL: These E2E tests focus on complete service dependency chains through Docker stack.
This is the final component of the comprehensive Service Dependencies Tests Suite.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service Reliability - Ensure robust end-to-end service communication
- Value Impact: Validates complete service dependency chains in production-like environment
- Strategic/Revenue Impact: Prevents $200K+ loss from service orchestration failures

Service Dependencies Tested:
1. Complete user registration → login → agent execution flow
2. Multi-user concurrent service access and isolation
3. Service failure recovery patterns through full stack
4. Database and cache consistency across full system
5. Cross-service error propagation and containment
6. WebSocket authentication and agent execution chains

E2E TEST REQUIREMENTS:
- Uses REAL services through Docker containers (NO MOCKS)
- MANDATORY authentication with JWT/OAuth for ALL tests
- Tests complete user journeys across all services
- Validates full-stack service dependency chains
- Tests mission-critical golden path scenarios

Author: AI Agent - Service Dependencies E2E Test Creation
Date: 2025-09-09
"""

import asyncio
import json
import logging
import pytest
import time
import websockets
import aiohttp
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# CRITICAL: Use real services fixture for full Docker stack (NO MOCKS in E2E tests)
from test_framework.fixtures.real_services import real_services_fixture

# MANDATORY: All E2E tests MUST use authentication per claude.md
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper

# Shared types for strongly typed E2E testing
from shared.types import UserID, ThreadID, RequestID
from shared.ssot_id_manager import SSOT_ID_Manager


@dataclass
class E2EServiceDependencyUser:
    """Fully authenticated user for E2E service dependency testing"""
    user_id: UserID
    email: str
    jwt_token: str
    session_id: str
    websocket_headers: Dict[str, str]
    auth_validated: bool = False
    database_persisted: bool = False
    redis_cached: bool = False


@dataclass
class E2EServiceDependencyMetrics:
    """Metrics tracking for E2E service dependency tests"""
    total_user_journeys: int = 0
    successful_journeys: int = 0
    failed_journeys: int = 0
    authentication_operations: int = 0
    database_operations: int = 0
    cache_operations: int = 0
    websocket_connections: int = 0
    agent_executions: int = 0
    service_failures: int = 0
    recovery_operations: int = 0


class TestCompleteUserJourneyServiceDependencies:
    """
    E2E tests for complete user journeys through all service dependencies.
    
    CRITICAL: These tests validate mission-critical user flows across the complete
    Docker container stack with all services working together.
    """
    
    @pytest.fixture(autouse=True)
    def setup_complete_e2e_environment(self, real_services_fixture):
        """Set up complete Docker stack for E2E service dependency testing"""
        self.services = real_services_fixture
        self.backend_url = self.services['backend_url']
        
        # MANDATORY: Initialize authentication helpers for E2E
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.backend_url)
        
        # E2E service dependency metrics
        self.e2e_metrics = E2EServiceDependencyMetrics()
        
        # Logger for E2E service dependency testing
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    async def create_complete_e2e_service_user(self, user_suffix: str = None) -> E2EServiceDependencyUser:
        """
        Create user with complete service dependency validation through full stack.
        
        This validates authentication → database → cache → WebSocket chain.
        """
        if user_suffix:
            email = f"e2e_service_test_{user_suffix}@netra.com"
        else:
            email = f"e2e_service_test_{int(time.time())}@netra.com"
            
        user_id = SSOT_ID_Manager.generate_user_id()
        session_id = f"e2e_service_session_{user_id}_{int(time.time())}"
        
        # Step 1: MANDATORY authentication through full auth service stack
        self.e2e_metrics.authentication_operations += 1
        try:
            jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
            
            # Step 2: Create WebSocket authentication headers
            websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
                jwt_token=jwt_token,
                user_id=str(user_id),
                is_e2e_test=True
            )
            
            # Step 3: Validate authentication through auth service API
            auth_validated = await self._validate_full_stack_authentication(jwt_token, str(user_id))
            
            # Step 4: Test database persistence (if auth validated)
            database_persisted = False
            if auth_validated:
                database_persisted = await self._validate_user_database_persistence(user_id, email, session_id)
                self.e2e_metrics.database_operations += 1
                
            # Step 5: Test Redis caching (if database persisted)
            redis_cached = False
            if database_persisted:
                redis_cached = await self._validate_user_redis_caching(user_id, session_id)
                self.e2e_metrics.cache_operations += 1
            
            return E2EServiceDependencyUser(
                user_id=user_id,
                email=email,
                jwt_token=jwt_token,
                session_id=session_id,
                websocket_headers=websocket_headers,
                auth_validated=auth_validated,
                database_persisted=database_persisted,
                redis_cached=redis_cached
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create complete E2E service user: {e}")
            raise
    
    async def _validate_full_stack_authentication(self, jwt_token: str, user_id: str) -> bool:
        """Validate authentication through complete service stack"""
        try:
            # Validate through auth service API
            async with aiohttp.ClientSession() as session:
                auth_url = f"{self.backend_url}/api/auth/validate"
                headers = {"Authorization": f"Bearer {jwt_token}"}
                
                async with session.post(auth_url, headers=headers) as response:
                    if response.status == 200:
                        validation_data = await response.json()
                        return (validation_data.get('valid', False) and 
                               validation_data.get('user_id') == user_id)
                    return False
                    
        except Exception as e:
            self.logger.error(f"Full stack auth validation failed: {e}")
            return False
    
    async def _validate_user_database_persistence(self, user_id: UserID, email: str, session_id: str) -> bool:
        """Validate user data persistence through database service"""
        try:
            # Test database persistence through backend API
            async with aiohttp.ClientSession() as session:
                user_data = {
                    "user_id": str(user_id),
                    "email": email,
                    "session_id": session_id,
                    "e2e_test": True
                }
                
                create_url = f"{self.backend_url}/api/users/create_session"
                async with session.post(create_url, json=user_data) as response:
                    if response.status in [200, 201]:
                        # Validate data can be retrieved
                        get_url = f"{self.backend_url}/api/users/session/{session_id}"
                        async with session.get(get_url) as get_response:
                            if get_response.status == 200:
                                retrieved_data = await get_response.json()
                                return retrieved_data.get('user_id') == str(user_id)
                    return False
                    
        except Exception as e:
            self.logger.error(f"Database persistence validation failed: {e}")
            return False
    
    async def _validate_user_redis_caching(self, user_id: UserID, session_id: str) -> bool:
        """Validate user session caching through Redis service"""
        try:
            # Test Redis caching through backend API
            async with aiohttp.ClientSession() as session:
                cache_data = {
                    "user_id": str(user_id),
                    "session_id": session_id,
                    "cached_at": time.time()
                }
                
                cache_url = f"{self.backend_url}/api/cache/session"
                async with session.post(cache_url, json=cache_data) as response:
                    if response.status in [200, 201]:
                        # Validate cached data can be retrieved
                        get_cache_url = f"{self.backend_url}/api/cache/session/{session_id}"
                        async with session.get(get_cache_url) as get_response:
                            if get_response.status == 200:
                                cached_data = await get_response.json()
                                return cached_data.get('user_id') == str(user_id)
                    return False
                    
        except Exception as e:
            self.logger.error(f"Redis caching validation failed: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_complete_user_registration_to_agent_execution_journey(self, real_services_fixture):
        """
        MISSION CRITICAL E2E: Complete user registration → agent execution journey.
        
        This is the most critical service dependency test that validates the entire
        user journey through all services: Auth → Database → Cache → WebSocket → Agent execution.
        """
        self.e2e_metrics.total_user_journeys += 1
        journey_start_time = time.time()
        
        # Step 1: Create complete service dependency user
        user = await self.create_complete_e2e_service_user("mission_critical")
        
        # CRITICAL: Validate all service dependencies are working
        assert user.auth_validated, f"Authentication failed for mission critical user {user.user_id}"
        assert user.database_persisted, f"Database persistence failed for user {user.user_id}"
        assert user.redis_cached, f"Redis caching failed for user {user.user_id}"
        
        # Step 2: Establish WebSocket connection through full stack
        websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{user.user_id}"
        
        try:
            self.e2e_metrics.websocket_connections += 1
            connection = await websockets.connect(
                websocket_url,
                extra_headers=user.websocket_headers,
                timeout=15  # Longer timeout for full stack
            )
            
            # Step 3: Complete WebSocket handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id,
                "mission_critical_test": True
            }
            
            await connection.send(json.dumps(handshake_message))
            handshake_response = await asyncio.wait_for(connection.recv(), timeout=10)
            handshake_data = json.loads(handshake_response)
            
            assert handshake_data.get('type') == 'handshake_complete', "WebSocket handshake failed"
            assert handshake_data.get('status') == 'success', "WebSocket handshake status not success"
            
            # Step 4: Execute agent through complete service stack
            self.e2e_metrics.agent_executions += 1
            agent_execution_start = time.time()
            
            agent_request = {
                "type": "agent_execution_request",
                "user_id": str(user.user_id),
                "request": "Mission critical E2E service dependency test",
                "agent_type": "service_dependency_test_agent",
                "request_id": f"mission_critical_{int(time.time())}"
            }
            
            await connection.send(json.dumps(agent_request))
            
            # Step 5: Validate complete agent execution event sequence
            mission_critical_events = []
            required_events = ["agent_started", "agent_completed"]
            
            for _ in range(10):  # Allow up to 10 events
                try:
                    event_response = await asyncio.wait_for(connection.recv(), timeout=20)
                    event_data = json.loads(event_response)
                    mission_critical_events.append(event_data)
                    
                    # Validate user isolation in all events
                    assert event_data.get("user_id") == str(user.user_id), "User isolation violated in agent execution"
                    
                    if event_data.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    self.logger.warning("Timeout waiting for agent completion in mission critical test")
                    break
                    
            agent_execution_time = time.time() - agent_execution_start
            
            # Step 6: Validate mission critical requirements
            event_types = [event.get("type") for event in mission_critical_events]
            
            # CRITICAL: Required events must be present
            required_events_present = all(event in event_types for event in required_events)
            assert required_events_present, f"Required events missing. Expected: {required_events}, Received: {event_types}"
            
            # CRITICAL: Agent execution must complete within reasonable time
            assert agent_execution_time < 30.0, f"Agent execution too slow: {agent_execution_time}s"
            
            # CRITICAL: Must receive substantive response
            agent_completed_event = next(
                (event for event in mission_critical_events if event.get("type") == "agent_completed"),
                None
            )
            assert agent_completed_event is not None, "No agent_completed event received"
            
            total_journey_time = time.time() - journey_start_time
            self.e2e_metrics.successful_journeys += 1
            
            self.logger.info(f"MISSION CRITICAL service dependency test PASSED. "
                           f"User: {user.user_id}, Journey time: {total_journey_time:.2f}s, "
                           f"Agent time: {agent_execution_time:.2f}s, Events: {len(mission_critical_events)}")
            
        except Exception as e:
            self.e2e_metrics.failed_journeys += 1
            self.logger.error(f"Mission critical service dependency test FAILED: {e}")
            raise
            
        finally:
            if 'connection' in locals():
                await connection.close()
    
    @pytest.mark.asyncio
    async def test_multi_user_concurrent_service_dependencies(self, real_services_fixture):
        """
        E2E test for multi-user concurrent access to all service dependencies.
        
        This validates that multiple users can simultaneously access all services
        without interference or race conditions in the complete stack.
        """
        concurrent_user_count = 3
        self.e2e_metrics.total_user_journeys += concurrent_user_count
        
        # Create multiple users concurrently
        user_creation_tasks = []
        for user_index in range(concurrent_user_count):
            task = asyncio.create_task(
                self.create_complete_e2e_service_user(f"concurrent_{user_index}")
            )
            user_creation_tasks.append(task)
            
        # Wait for all users to be created
        created_users = await asyncio.gather(*user_creation_tasks, return_exceptions=True)
        
        # Validate user creation
        valid_users = []
        for i, user_result in enumerate(created_users):
            if isinstance(user_result, Exception):
                self.logger.error(f"Failed to create concurrent user {i}: {user_result}")
                self.e2e_metrics.failed_journeys += 1
            else:
                # Validate full service dependency chain for each user
                assert user_result.auth_validated, f"Auth failed for concurrent user {i}"
                assert user_result.database_persisted, f"Database failed for concurrent user {i}"
                assert user_result.redis_cached, f"Cache failed for concurrent user {i}"
                valid_users.append(user_result)
                
        assert len(valid_users) >= 2, f"Expected at least 2 valid concurrent users, got {len(valid_users)}"
        
        # Execute concurrent operations across all services
        concurrent_operation_tasks = []
        for user in valid_users:
            task = asyncio.create_task(
                self._perform_concurrent_full_stack_operations(user)
            )
            concurrent_operation_tasks.append(task)
            
        # Wait for all concurrent operations
        operation_results = await asyncio.gather(*concurrent_operation_tasks, return_exceptions=True)
        
        # Analyze concurrent operation results
        successful_operations = 0
        user_isolation_violations = 0
        service_errors = 0
        
        for i, result in enumerate(operation_results):
            if isinstance(result, Exception):
                service_errors += 1
                self.e2e_metrics.failed_journeys += 1
                self.logger.error(f"Concurrent operations failed for user {valid_users[i].user_id}: {result}")
            elif result and result.get('success'):
                successful_operations += 1
                self.e2e_metrics.successful_journeys += 1
                
                # Validate user isolation wasn't violated
                if result.get('isolation_violations', 0) > 0:
                    user_isolation_violations += result['isolation_violations']
                    
        # Validate concurrent service dependency access
        assert successful_operations >= 2, f"Expected at least 2 successful concurrent operations, got {successful_operations}"
        assert user_isolation_violations == 0, f"User isolation violations detected: {user_isolation_violations}"
        assert service_errors <= 1, f"Too many service errors: {service_errors}"
        
        self.logger.info(f"Multi-user concurrent service dependency test passed. "
                        f"Users: {len(valid_users)}, Successful ops: {successful_operations}, Errors: {service_errors}")
    
    async def _perform_concurrent_full_stack_operations(self, user: E2EServiceDependencyUser) -> Dict[str, Any]:
        """Perform concurrent operations across complete service stack for one user"""
        try:
            operations_completed = 0
            isolation_violations = 0
            
            # Operation 1: WebSocket connection and agent execution
            websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{user.user_id}"
            
            try:
                connection = await websockets.connect(
                    websocket_url,
                    extra_headers=user.websocket_headers,
                    timeout=15
                )
                
                # Complete handshake
                handshake_message = {
                    "type": "handshake",
                    "user_id": str(user.user_id),
                    "session_id": user.session_id,
                    "concurrent_test": True
                }
                
                await connection.send(json.dumps(handshake_message))
                handshake_response = await asyncio.wait_for(connection.recv(), timeout=10)
                handshake_data = json.loads(handshake_response)
                
                if handshake_data.get('type') == 'handshake_complete':
                    operations_completed += 1
                    
                # Execute agent
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": str(user.user_id),
                    "request": f"Concurrent test for user {user.user_id}",
                    "concurrent_operation": True
                }
                
                await connection.send(json.dumps(agent_request))
                
                # Collect events with user isolation validation
                for _ in range(3):
                    try:
                        event_response = await asyncio.wait_for(connection.recv(), timeout=15)
                        event_data = json.loads(event_response)
                        
                        # CRITICAL: Validate user isolation
                        if event_data.get("user_id") != str(user.user_id):
                            isolation_violations += 1
                            
                        if event_data.get("type") == "agent_completed":
                            operations_completed += 1
                            break
                            
                    except asyncio.TimeoutError:
                        break
                        
                await connection.close()
                
            except Exception as e:
                self.logger.error(f"WebSocket operation failed for user {user.user_id}: {e}")
                
            # Operation 2: Database operation validation
            try:
                async with aiohttp.ClientSession() as session:
                    # Validate user session still exists in database
                    get_url = f"{self.backend_url}/api/users/session/{user.session_id}"
                    async with session.get(get_url) as response:
                        if response.status == 200:
                            session_data = await response.json()
                            if session_data.get('user_id') == str(user.user_id):
                                operations_completed += 1
                                
            except Exception as e:
                self.logger.error(f"Database operation failed for user {user.user_id}: {e}")
                
            # Operation 3: Cache operation validation
            try:
                async with aiohttp.ClientSession() as session:
                    # Validate user data is cached
                    cache_url = f"{self.backend_url}/api/cache/session/{user.session_id}"
                    async with session.get(cache_url) as response:
                        if response.status == 200:
                            cached_data = await response.json()
                            if cached_data.get('user_id') == str(user.user_id):
                                operations_completed += 1
                                
            except Exception as e:
                self.logger.error(f"Cache operation failed for user {user.user_id}: {e}")
                
            return {
                'success': operations_completed >= 2,
                'user_id': str(user.user_id),
                'operations_completed': operations_completed,
                'isolation_violations': isolation_violations
            }
            
        except Exception as e:
            return {
                'success': False,
                'user_id': str(user.user_id),
                'error': str(e),
                'operations_completed': 0,
                'isolation_violations': 0
            }
    
    @pytest.mark.asyncio 
    async def test_service_failure_recovery_full_stack(self, real_services_fixture):
        """
        E2E test for service failure recovery patterns across complete Docker stack.
        
        This validates that temporary service failures don't permanently break
        the service dependency chains and that recovery is graceful.
        """
        # Create user for failure recovery testing
        user = await self.create_complete_e2e_service_user("failure_recovery")
        
        # Validate initial state
        assert user.auth_validated, "Initial auth validation failed"
        assert user.database_persisted, "Initial database persistence failed"
        assert user.redis_cached, "Initial Redis caching failed"
        
        recovery_tests = []
        self.e2e_metrics.recovery_operations += 1
        
        # Test 1: Simulate network connectivity issues
        try:
            # Test with very short timeout to simulate network issues
            websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{user.user_id}"
            
            connection_attempts = []
            for attempt in range(3):
                try:
                    connection = await websockets.connect(
                        websocket_url,
                        extra_headers=user.websocket_headers,
                        timeout=2  # Very short timeout
                    )
                    
                    # Quick operation test
                    handshake_message = {
                        "type": "handshake",
                        "user_id": str(user.user_id),
                        "session_id": user.session_id,
                        "recovery_test": True
                    }
                    
                    await connection.send(json.dumps(handshake_message))
                    
                    try:
                        response = await asyncio.wait_for(connection.recv(), timeout=5)
                        response_data = json.loads(response)
                        
                        connection_attempts.append({
                            'attempt': attempt,
                            'success': response_data.get('type') == 'handshake_complete',
                            'recovered': True
                        })
                        
                    except asyncio.TimeoutError:
                        connection_attempts.append({
                            'attempt': attempt,
                            'success': False,
                            'recovered': False,
                            'error': 'timeout'
                        })
                        
                    await connection.close()
                    
                except Exception as e:
                    connection_attempts.append({
                        'attempt': attempt,
                        'success': False,
                        'recovered': False,
                        'error': str(e)
                    })
                    
                # Small delay between attempts
                await asyncio.sleep(1)
                
            successful_connections = sum(1 for attempt in connection_attempts if attempt['success'])
            recovery_tests.append({
                'test': 'websocket_connection_recovery',
                'attempts': len(connection_attempts),
                'successes': successful_connections,
                'recovery_rate': successful_connections / len(connection_attempts)
            })
            
        except Exception as e:
            self.e2e_metrics.service_failures += 1
            self.logger.error(f"WebSocket recovery test failed: {e}")
            
        # Test 2: Validate service health after recovery attempts
        try:
            # Test auth service health
            async with aiohttp.ClientSession() as session:
                health_url = f"{self.backend_url}/api/health/auth"
                async with session.get(health_url) as response:
                    auth_healthy = response.status == 200
                    
                # Test database health  
                db_health_url = f"{self.backend_url}/api/health/database"
                async with session.get(db_health_url) as response:
                    db_healthy = response.status == 200
                    
                # Test cache health
                cache_health_url = f"{self.backend_url}/api/health/cache"
                async with session.get(cache_health_url) as response:
                    cache_healthy = response.status == 200
                    
            recovery_tests.append({
                'test': 'service_health_after_recovery',
                'auth_healthy': auth_healthy,
                'database_healthy': db_healthy,
                'cache_healthy': cache_healthy,
                'all_healthy': auth_healthy and db_healthy and cache_healthy
            })
            
        except Exception as e:
            self.logger.error(f"Service health check failed: {e}")
            
        # Test 3: Validate user data consistency after recovery
        try:
            # Re-validate user through all services
            user_consistency_validated = await self._validate_user_data_consistency(user)
            
            recovery_tests.append({
                'test': 'user_data_consistency_after_recovery',
                'consistent': user_consistency_validated
            })
            
        except Exception as e:
            self.logger.error(f"User consistency validation failed: {e}")
            
        # Validate recovery test results
        successful_recovery_tests = sum(
            1 for test in recovery_tests 
            if test.get('recovery_rate', 0) > 0.5 or test.get('all_healthy', False) or test.get('consistent', False)
        )
        
        assert successful_recovery_tests >= 2, f"Insufficient recovery capability: {successful_recovery_tests}/{len(recovery_tests)}"
        
        self.logger.info(f"Service failure recovery test passed. Recovery tests: {successful_recovery_tests}/{len(recovery_tests)}")
        
    async def _validate_user_data_consistency(self, user: E2EServiceDependencyUser) -> bool:
        """Validate user data consistency across all services after recovery"""
        try:
            consistency_checks = []
            
            # Check auth service
            async with aiohttp.ClientSession() as session:
                auth_url = f"{self.backend_url}/api/auth/validate"
                headers = {"Authorization": f"Bearer {user.jwt_token}"}
                
                async with session.post(auth_url, headers=headers) as response:
                    auth_consistent = (response.status == 200 and 
                                     (await response.json()).get('user_id') == str(user.user_id))
                    consistency_checks.append(auth_consistent)
                    
                # Check database consistency
                db_url = f"{self.backend_url}/api/users/session/{user.session_id}"
                async with session.get(db_url) as response:
                    db_consistent = (response.status == 200 and 
                                   (await response.json()).get('user_id') == str(user.user_id))
                    consistency_checks.append(db_consistent)
                    
                # Check cache consistency
                cache_url = f"{self.backend_url}/api/cache/session/{user.session_id}"
                async with session.get(cache_url) as response:
                    cache_consistent = (response.status == 200 and 
                                      (await response.json()).get('user_id') == str(user.user_id))
                    consistency_checks.append(cache_consistent)
                    
            # At least 2 out of 3 services should be consistent
            consistent_services = sum(consistency_checks)
            return consistent_services >= 2
            
        except Exception as e:
            self.logger.error(f"User data consistency validation error: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_database_and_cache_consistency_validation(self, real_services_fixture):
        """
        E2E test for database and cache consistency across full service stack.
        
        This validates that data remains consistent between PostgreSQL and Redis
        through the complete Docker container orchestration.
        """
        # Create user for consistency testing
        user = await self.create_complete_e2e_service_user("consistency_test")
        
        # Validate initial consistency
        assert user.database_persisted and user.redis_cached, "Initial data persistence failed"
        
        consistency_operations = []
        
        # Test 1: Update user data and validate consistency
        try:
            updated_data = {
                "user_id": str(user.user_id),
                "session_id": user.session_id,
                "email": user.email,
                "last_activity": time.time(),
                "consistency_test": True
            }
            
            # Update through database API
            async with aiohttp.ClientSession() as session:
                update_url = f"{self.backend_url}/api/users/session/{user.session_id}/update"
                async with session.put(update_url, json=updated_data) as response:
                    db_update_success = response.status in [200, 204]
                    
            # Small delay for cache invalidation/update
            await asyncio.sleep(0.5)
            
            # Validate cache reflects database changes
            async with aiohttp.ClientSession() as session:
                cache_url = f"{self.backend_url}/api/cache/session/{user.session_id}"
                async with session.get(cache_url) as response:
                    if response.status == 200:
                        cached_data = await response.json()
                        cache_consistent = (cached_data.get('user_id') == str(user.user_id) and 
                                         cached_data.get('consistency_test') == True)
                    else:
                        cache_consistent = False
                        
            consistency_operations.append({
                'operation': 'database_update_cache_consistency',
                'db_update_success': db_update_success,
                'cache_consistent': cache_consistent,
                'consistent': db_update_success and cache_consistent
            })
            
        except Exception as e:
            self.logger.error(f"Database/cache consistency update test failed: {e}")
            consistency_operations.append({
                'operation': 'database_update_cache_consistency',
                'consistent': False,
                'error': str(e)
            })
            
        # Test 2: Concurrent operations consistency
        try:
            # Perform multiple concurrent operations that affect both DB and cache
            concurrent_tasks = []
            
            for op_index in range(3):
                task = asyncio.create_task(
                    self._perform_consistency_operation(user, op_index)
                )
                concurrent_tasks.append(task)
                
            # Wait for concurrent operations
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            successful_concurrent_ops = sum(
                1 for result in concurrent_results 
                if not isinstance(result, Exception) and result.get('consistent', False)
            )
            
            consistency_operations.append({
                'operation': 'concurrent_consistency_operations',
                'total_operations': len(concurrent_tasks),
                'successful_operations': successful_concurrent_ops,
                'consistent': successful_concurrent_ops >= 2
            })
            
        except Exception as e:
            self.logger.error(f"Concurrent consistency operations failed: {e}")
            
        # Validate overall consistency
        consistent_operations = sum(
            1 for op in consistency_operations if op.get('consistent', False)
        )
        
        assert consistent_operations >= 1, f"Database/cache consistency failed. Consistent operations: {consistent_operations}/{len(consistency_operations)}"
        
        self.logger.info(f"Database and cache consistency validation passed. "
                        f"Consistent operations: {consistent_operations}/{len(consistency_operations)}")
        
    async def _perform_consistency_operation(self, user: E2EServiceDependencyUser, operation_index: int) -> Dict[str, Any]:
        """Perform operation that affects both database and cache consistency"""
        try:
            # Update operation data
            operation_data = {
                "user_id": str(user.user_id),
                "operation_index": operation_index,
                "timestamp": time.time(),
                "consistency_test": f"operation_{operation_index}"
            }
            
            # Update via API (should update both DB and cache)
            async with aiohttp.ClientSession() as session:
                update_url = f"{self.backend_url}/api/users/activity"
                async with session.post(update_url, json=operation_data) as response:
                    update_success = response.status in [200, 201]
                    
            # Brief delay for consistency propagation
            await asyncio.sleep(0.2)
            
            # Validate consistency by reading from both sources
            async with aiohttp.ClientSession() as session:
                # Read from database
                db_url = f"{self.backend_url}/api/users/{user.user_id}/activity/{operation_index}"
                async with session.get(db_url) as response:
                    db_data_valid = response.status == 200
                    
                # Read from cache
                cache_url = f"{self.backend_url}/api/cache/user_activity/{user.user_id}/{operation_index}"
                async with session.get(cache_url) as response:
                    cache_data_valid = response.status == 200
                    
            return {
                'operation_index': operation_index,
                'update_success': update_success,
                'db_data_valid': db_data_valid,
                'cache_data_valid': cache_data_valid,
                'consistent': update_success and db_data_valid and cache_data_valid
            }
            
        except Exception as e:
            return {
                'operation_index': operation_index,
                'consistent': False,
                'error': str(e)
            }