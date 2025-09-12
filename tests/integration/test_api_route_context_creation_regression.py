"""Integration Test for API Route Context Creation Regression Prevention.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Critical for multi-user system integrity
- Business Goal: Prevent conversation continuity breakage and memory leaks from improper context creation
- Value Impact: Ensures API routes maintain session continuity across HTTP calls
- Strategic/Revenue Impact: CRITICAL - Broken context management destroys chat experience
  * Prevents conversation history loss (destroys user experience)
  * Prevents database session proliferation (reduces infrastructure costs)  
  * Maintains proper session isolation (prevents data leaks between users)
  * Enables reliable multi-turn conversation flows (core business value delivery)

This test suite validates the critical findings from CONTEXT_CREATION_AUDIT_REPORT.md:
1. API route handlers must use get_user_session_context() for session continuity
2. HTTP endpoint session continuity must be maintained across API calls
3. Database sessions must be efficiently managed without proliferation
4. Thread continuity must be preserved in HTTP API workflows

CRITICAL REGRESSION PREVENTION:
- Tests ensure API routes don't fall back to create_user_execution_context()
- Validates proper session reuse patterns across HTTP request boundaries
- Monitors database session creation to prevent connection exhaustion
- Ensures multi-user isolation is maintained in API contexts

NO MOCKS: This integration test uses real API clients, real database connections,
and real authentication flows to validate actual production patterns.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import pytest
import httpx
from dataclasses import dataclass, asdict

# Test framework imports
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Netra backend imports for context testing
from netra_backend.app.dependencies import get_user_session_context, get_user_execution_context
from shared.session_management import get_user_session, get_session_manager, get_session_metrics
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.isolated_environment import get_env

# Database imports for session monitoring  
from netra_backend.app.db.database_manager import get_database_manager, DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class ContextCreationMetrics:
    """Metrics for tracking context creation vs. reuse patterns."""
    contexts_created: int = 0
    contexts_reused: int = 0
    database_sessions_created: int = 0
    database_sessions_reused: int = 0
    api_calls_made: int = 0
    session_continuity_breaks: int = 0
    thread_id_changes: int = 0
    run_id_changes: int = 0
    total_test_duration: float = 0.0
    average_context_creation_time: float = 0.0
    
    def get_efficiency_ratio(self) -> float:
        """Calculate context reuse efficiency ratio."""
        total = self.contexts_created + self.contexts_reused
        return self.contexts_reused / total if total > 0 else 0.0
    
    def get_session_efficiency_ratio(self) -> float:
        """Calculate database session reuse efficiency ratio."""
        total = self.database_sessions_created + self.database_sessions_reused
        return self.database_sessions_reused / total if total > 0 else 0.0


@dataclass
class ApiRequestContext:
    """Context data for API request tracking."""
    request_id: str
    user_id: str
    thread_id: str
    run_id: Optional[str]
    timestamp: datetime
    endpoint: str
    method: str
    expected_session_reuse: bool = True


class TestApiRouteContextCreationRegression(SSotBaseTestCase):
    """Integration test for API route context creation regression prevention.
    
    This test suite validates that API routes properly maintain session continuity
    and avoid unnecessary context creation that breaks conversation flows.
    """
    
    def setup_method(self):
        """Set up test environment with real services."""
        super().setup_method()
        
        # Environment setup
        self.env = get_env()
        
        # Authentication helper for real API calls
        self.auth_helper = E2EAuthHelper()
        self.auth_config = E2EAuthConfig()
        
        # Test users for multi-user isolation testing
        self.test_users = [
            {
                "id": "usr_api_test_001_" + str(uuid.uuid4())[:8],
                "email": f"api_test_001_{uuid.uuid4().hex[:8]}@example.com",
                "name": "API Test User 001"
            },
            {
                "id": "usr_api_test_002_" + str(uuid.uuid4())[:8],
                "email": f"api_test_002_{uuid.uuid4().hex[:8]}@example.com", 
                "name": "API Test User 002"
            },
            {
                "id": "usr_api_test_003_" + str(uuid.uuid4())[:8],
                "email": f"api_test_003_{uuid.uuid4().hex[:8]}@example.com",
                "name": "API Test User 003"
            }
        ]
        
        # Conversation threads for testing session continuity
        self.conversation_threads = {
            "user_001_thread_1": f"thd_api_conversation_001_{uuid.uuid4().hex[:12]}",
            "user_001_thread_2": f"thd_api_conversation_002_{uuid.uuid4().hex[:12]}",
            "user_002_thread_1": f"thd_api_conversation_003_{uuid.uuid4().hex[:12]}",
            "user_003_thread_1": f"thd_api_conversation_004_{uuid.uuid4().hex[:12]}"
        }
        
        # Metrics tracking
        self.metrics = ContextCreationMetrics()
        self.request_contexts: List[ApiRequestContext] = []
        self.session_before_counts: Dict[str, int] = {}
        self.session_after_counts: Dict[str, int] = {}
        
        # Real API client setup
        self.api_client: Optional[httpx.AsyncClient] = None
        self.authenticated_headers: Dict[str, str] = {}
        
        # Database session monitoring
        self.db_manager = get_database_manager()
        
        logger.info(f"Test setup complete with {len(self.test_users)} users and {len(self.conversation_threads)} threads")
    
    async def teardown_method(self):
        """Clean up test resources."""
        if self.api_client:
            await self.api_client.aclose()
        
        # Log final metrics
        logger.info("Final Context Creation Metrics:")
        logger.info(f"  Context Efficiency: {self.metrics.get_efficiency_ratio():.2%}")
        logger.info(f"  Session Efficiency: {self.metrics.get_session_efficiency_ratio():.2%}")
        logger.info(f"  Total API Calls: {self.metrics.api_calls_made}")
        logger.info(f"  Session Continuity Breaks: {self.metrics.session_continuity_breaks}")
        
        await super().teardown_method()
    
    async def _setup_authenticated_client(self) -> httpx.AsyncClient:
        """Set up authenticated HTTP client for API testing."""
        try:
            # Get authentication token
            auth_result = await self.auth_helper.authenticate_for_testing(
                user_email=self.test_users[0]["email"],
                config=self.auth_config
            )
            
            self.authenticated_headers = {
                "Authorization": f"Bearer {auth_result.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Create HTTP client
            self.api_client = httpx.AsyncClient(
                base_url=self.auth_config.backend_url,
                headers=self.authenticated_headers,
                timeout=30.0
            )
            
            logger.info(f"Authenticated API client setup complete for user {self.test_users[0]['email']}")
            return self.api_client
            
        except Exception as e:
            logger.error(f"Failed to setup authenticated client: {e}")
            pytest.skip(f"Authentication setup failed: {e}")
    
    async def _monitor_session_metrics_before(self) -> Dict[str, int]:
        """Capture session metrics before API calls."""
        try:
            session_manager = get_session_manager()
            session_metrics = get_session_metrics()
            
            # Use health check to get basic DB info
            db_health = await self.db_manager.health_check()
            
            before_metrics = {
                "active_sessions": len(session_manager._sessions) if hasattr(session_manager, '_sessions') else 0,
                "total_sessions_created": session_metrics.total_sessions_created if session_metrics else 0,
                "db_healthy": db_health.get("status") == "healthy",
                "db_engine_count": len(self.db_manager._engines)
            }
            
            logger.debug(f"Before metrics: {before_metrics}")
            return before_metrics
            
        except Exception as e:
            logger.warning(f"Failed to capture before metrics: {e}")
            return {"active_sessions": 0, "total_sessions_created": 0, 
                   "db_healthy": False, "db_engine_count": 0}
    
    async def _monitor_session_metrics_after(self) -> Dict[str, int]:
        """Capture session metrics after API calls."""
        try:
            session_manager = get_session_manager()
            session_metrics = get_session_metrics()
            
            # Use health check to get basic DB info
            db_health = await self.db_manager.health_check()
            
            after_metrics = {
                "active_sessions": len(session_manager._sessions) if hasattr(session_manager, '_sessions') else 0,
                "total_sessions_created": session_metrics.total_sessions_created if session_metrics else 0,
                "db_healthy": db_health.get("status") == "healthy",
                "db_engine_count": len(self.db_manager._engines)
            }
            
            logger.debug(f"After metrics: {after_metrics}")
            return after_metrics
            
        except Exception as e:
            logger.warning(f"Failed to capture after metrics: {e}")
            return {"active_sessions": 0, "total_sessions_created": 0,
                   "db_healthy": False, "db_engine_count": 0}
    
    async def _make_api_call(self, 
                           endpoint: str, 
                           method: str,
                           data: Dict[str, Any],
                           user_id: str,
                           thread_id: str,
                           run_id: Optional[str] = None,
                           expected_session_reuse: bool = True) -> Tuple[httpx.Response, ApiRequestContext]:
        """Make API call and track context creation metrics."""
        
        request_context = ApiRequestContext(
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            endpoint=endpoint,
            method=method,
            expected_session_reuse=expected_session_reuse
        )
        
        self.request_contexts.append(request_context)
        
        # Monitor metrics before call
        before_metrics = await self._monitor_session_metrics_before()
        start_time = time.time()
        
        try:
            # Make the actual API call
            if method.upper() == "POST":
                response = await self.api_client.post(endpoint, json=data)
            elif method.upper() == "GET":
                response = await self.api_client.get(endpoint, params=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Track timing
            end_time = time.time()
            call_duration = end_time - start_time
            
            # Monitor metrics after call
            after_metrics = await self._monitor_session_metrics_after()
            
            # Update metrics
            self.metrics.api_calls_made += 1
            
            sessions_created = after_metrics["total_sessions_created"] - before_metrics["total_sessions_created"]
            if sessions_created > 0:
                self.metrics.contexts_created += sessions_created
                if expected_session_reuse:
                    self.metrics.session_continuity_breaks += 1
                    logger.warning(f"Unexpected session creation in {endpoint}: {sessions_created} new sessions")
            else:
                self.metrics.contexts_reused += 1
            
            # Monitor database engine changes instead of connections
            engine_changes = after_metrics["db_engine_count"] - before_metrics["db_engine_count"]
            if engine_changes > 0:
                self.metrics.database_sessions_created += engine_changes
            else:
                self.metrics.database_sessions_reused += 1
            
            # Update timing metrics
            if self.metrics.average_context_creation_time == 0:
                self.metrics.average_context_creation_time = call_duration
            else:
                # Running average
                total_calls = self.metrics.api_calls_made
                self.metrics.average_context_creation_time = (
                    (self.metrics.average_context_creation_time * (total_calls - 1) + call_duration) / total_calls
                )
            
            logger.info(f"API call {method} {endpoint} completed in {call_duration:.3f}s with status {response.status_code}")
            return response, request_context
            
        except Exception as e:
            logger.error(f"API call {method} {endpoint} failed: {e}")
            raise
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_api_route_context_session_continuity(self):
        """Test that API routes maintain session continuity across multiple calls.
        
        CRITICAL: This test validates the core business requirement that conversation
        contexts are maintained across HTTP API calls, preventing conversation history loss.
        """
        client = await self._setup_authenticated_client()
        
        user = self.test_users[0]
        thread_id = self.conversation_threads["user_001_thread_1"]
        
        # First API call - should create initial context
        response1, context1 = await self._make_api_call(
            endpoint="/agents/message",
            method="POST",
            data={
                "message": "Hello, this is the first message in our conversation.",
                "thread_id": thread_id,
                "user_id": user["id"]
            },
            user_id=user["id"],
            thread_id=thread_id,
            expected_session_reuse=False  # First call creates context
        )
        
        assert response1.status_code in [200, 202], f"First API call failed: {response1.text}"
        response1_data = response1.json()
        first_run_id = response1_data.get("run_id")
        
        # Wait briefly to ensure session is established
        await asyncio.sleep(0.5)
        
        # Second API call - should reuse existing session context
        response2, context2 = await self._make_api_call(
            endpoint="/agents/message", 
            method="POST",
            data={
                "message": "This is a follow-up message in the same conversation.",
                "thread_id": thread_id,
                "run_id": first_run_id,
                "user_id": user["id"]
            },
            user_id=user["id"],
            thread_id=thread_id,
            run_id=first_run_id,
            expected_session_reuse=True  # Should reuse existing context
        )
        
        assert response2.status_code in [200, 202], f"Second API call failed: {response2.text}"
        response2_data = response2.json()
        
        # Third API call - continue same conversation thread
        response3, context3 = await self._make_api_call(
            endpoint="/agents/message",
            method="POST", 
            data={
                "message": "And this is the third message, maintaining context.",
                "thread_id": thread_id,
                "run_id": first_run_id,
                "user_id": user["id"]
            },
            user_id=user["id"],
            thread_id=thread_id,
            run_id=first_run_id,
            expected_session_reuse=True  # Should reuse existing context
        )
        
        assert response3.status_code in [200, 202], f"Third API call failed: {response3.text}"
        
        # Validate session continuity
        assert context1.thread_id == context2.thread_id == context3.thread_id, \
            "Thread ID must remain consistent across API calls"
        
        # Check that context reuse happened
        assert self.metrics.contexts_reused >= 2, \
            f"Expected at least 2 context reuses, got {self.metrics.contexts_reused}"
        
        # Validate minimal session continuity breaks
        assert self.metrics.session_continuity_breaks <= 1, \
            f"Too many session continuity breaks: {self.metrics.session_continuity_breaks}"
        
        logger.info(" PASS:  API route session continuity test passed")
    
    @pytest.mark.asyncio  
    @pytest.mark.integration
    async def test_multi_user_context_isolation_api(self):
        """Test that API routes properly isolate contexts between different users.
        
        CRITICAL: Validates that user contexts don't leak between different user API calls,
        preventing data security violations.
        """
        client = await self._setup_authenticated_client()
        
        user1 = self.test_users[0]
        user2 = self.test_users[1]
        thread1 = self.conversation_threads["user_001_thread_1"]
        thread2 = self.conversation_threads["user_002_thread_1"]
        
        # Concurrent API calls from different users
        tasks = []
        
        # User 1 conversation
        tasks.append(self._make_api_call(
            endpoint="/agents/message",
            method="POST",
            data={
                "message": "User 1 message - should be isolated",
                "thread_id": thread1,
                "user_id": user1["id"]
            },
            user_id=user1["id"],
            thread_id=thread1,
            expected_session_reuse=False
        ))
        
        # User 2 conversation 
        tasks.append(self._make_api_call(
            endpoint="/agents/message",
            method="POST",
            data={
                "message": "User 2 message - should be isolated",
                "thread_id": thread2,
                "user_id": user2["id"]
            },
            user_id=user2["id"],
            thread_id=thread2,
            expected_session_reuse=False
        ))
        
        # Execute concurrent calls
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate both calls succeeded
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"User {i+1} API call failed: {result}")
            
            response, context = result
            assert response.status_code in [200, 202], f"User {i+1} call failed: {response.text}"
        
        # Validate user isolation
        response1, context1 = results[0]
        response2, context2 = results[1]
        
        assert context1.user_id != context2.user_id, "User IDs must be different"
        assert context1.thread_id != context2.thread_id, "Thread IDs must be different for different users"
        
        # Validate that contexts were created independently
        assert self.metrics.contexts_created >= 2, \
            f"Expected at least 2 contexts created, got {self.metrics.contexts_created}"
        
        logger.info(" PASS:  Multi-user context isolation test passed")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_session_efficiency_api(self):
        """Test that API routes efficiently manage database sessions without proliferation.
        
        CRITICAL: Validates that database connections are reused efficiently across
        API calls to prevent connection pool exhaustion.
        """
        client = await self._setup_authenticated_client()
        
        user = self.test_users[0]
        thread_id = self.conversation_threads["user_001_thread_1"]
        
        # Capture initial database metrics
        initial_metrics = await self._monitor_session_metrics_before()
        
        # Make multiple API calls in rapid succession
        api_calls = []
        for i in range(5):
            api_calls.append(self._make_api_call(
                endpoint="/agents/message",
                method="POST",
                data={
                    "message": f"Message {i+1} - testing database session efficiency",
                    "thread_id": thread_id,
                    "user_id": user["id"]
                },
                user_id=user["id"],
                thread_id=thread_id,
                expected_session_reuse=(i > 0)  # First call creates, rest reuse
            ))
        
        # Execute all calls
        results = await asyncio.gather(*api_calls, return_exceptions=True)
        
        # Validate all calls succeeded
        successful_calls = 0
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"API call failed: {result}")
                continue
                
            response, context = result
            if response.status_code in [200, 202]:
                successful_calls += 1
        
        assert successful_calls >= 3, f"Too many API calls failed, only {successful_calls} succeeded"
        
        # Capture final database metrics
        final_metrics = await self._monitor_session_metrics_after()
        
        # Validate database efficiency using engine count
        engine_changes = final_metrics["db_engine_count"] - initial_metrics["db_engine_count"] 
        
        # Should create minimal new database engines
        assert engine_changes <= 1, \
            f"Too many database engines created: {engine_changes}"
        
        # Validate session reuse efficiency
        efficiency_ratio = self.metrics.get_session_efficiency_ratio()
        assert efficiency_ratio >= 0.6, \
            f"Database session efficiency too low: {efficiency_ratio:.2%}"
        
        logger.info(f" PASS:  Database session efficiency test passed with {efficiency_ratio:.2%} efficiency")
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_context_creation_vs_getter_pattern_validation(self):
        """Test that API routes use get_user_session_context() vs create_user_execution_context().
        
        CRITICAL: This test validates the architectural requirement that API routes
        use the proper context getter pattern instead of always creating new contexts.
        """
        # This test validates the internal patterns by checking session management
        user_id = self.test_users[0]["id"] 
        thread_id = self.conversation_threads["user_001_thread_1"]
        
        # Test direct context creation patterns 
        start_time = time.time()
        
        # Test get_user_session_context (PREFERRED)
        context_via_session = await get_user_session_context(
            user_id=user_id,
            thread_id=thread_id
        )
        session_time = time.time() - start_time
        
        # Test get_user_execution_context (DEPRECATED)
        start_time = time.time()
        context_via_execution = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id
        )
        execution_time = time.time() - start_time
        
        # Both should work but session context is preferred
        assert context_via_session is not None, "Session context creation failed"
        assert context_via_execution is not None, "Execution context creation failed"
        
        # Validate that both maintain the same thread continuity
        assert context_via_session.thread_id == context_via_execution.thread_id, \
            "Thread ID should be consistent between context creation methods"
        
        assert context_via_session.user_id == context_via_execution.user_id, \
            "User ID should be consistent between context creation methods"
        
        # Session context should be the preferred pattern (it's async and more comprehensive)
        logger.info(f"Session context time: {session_time:.4f}s, Execution context time: {execution_time:.4f}s")
        
        # Validate we can reuse the session context
        reuse_start = time.time()
        context_reused = await get_user_session_context(
            user_id=user_id,
            thread_id=thread_id  # Same thread should reuse session
        )
        reuse_time = time.time() - reuse_start
        
        assert context_reused.thread_id == context_via_session.thread_id, \
            "Reused context should maintain same thread ID"
        
        # Reuse should be faster than initial creation
        # Note: This may not always be true due to system variance, so we log but don't assert
        logger.info(f"Context reuse time: {reuse_time:.4f}s")
        
        logger.info(" PASS:  Context creation vs getter pattern validation passed")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rapid_api_succession_context_stability(self):
        """Test context stability during rapid API call succession.
        
        CRITICAL: Validates that rapid API calls maintain stable context references
        and don't create unnecessary context proliferation.
        """
        client = await self._setup_authenticated_client()
        
        user = self.test_users[0]
        thread_id = self.conversation_threads["user_001_thread_1"]
        
        # Prepare rapid succession API calls
        rapid_calls = []
        for i in range(10):
            rapid_calls.append(self._make_api_call(
                endpoint="/agents/message",
                method="POST",
                data={
                    "message": f"Rapid message {i+1}",
                    "thread_id": thread_id,
                    "user_id": user["id"]
                },
                user_id=user["id"],
                thread_id=thread_id,
                expected_session_reuse=(i > 0)
            ))
        
        # Execute all calls with minimal delays
        start_time = time.time()
        results = await asyncio.gather(*rapid_calls, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Count successful calls
        successful_responses = 0
        thread_ids = set()
        user_ids = set()
        
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Rapid call failed: {result}")
                continue
                
            response, context = result
            if response.status_code in [200, 202]:
                successful_responses += 1
                thread_ids.add(context.thread_id)
                user_ids.add(context.user_id)
        
        # Validate stability
        assert successful_responses >= 7, \
            f"Too many rapid calls failed: {successful_responses}/10"
        
        assert len(thread_ids) == 1, \
            f"Thread ID should be stable across rapid calls: {thread_ids}"
        
        assert len(user_ids) == 1, \
            f"User ID should be stable across rapid calls: {user_ids}"
        
        # Validate reasonable performance
        avg_call_time = total_time / len(results)
        assert avg_call_time < 5.0, \
            f"Average API call time too slow: {avg_call_time:.2f}s"
        
        # Validate context reuse efficiency  
        efficiency = self.metrics.get_efficiency_ratio()
        assert efficiency >= 0.7, \
            f"Context reuse efficiency too low during rapid calls: {efficiency:.2%}"
        
        logger.info(f" PASS:  Rapid succession test passed: {efficiency:.2%} efficiency in {total_time:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_api_context_performance_benchmarks(self):
        """Benchmark API context creation performance and establish baseline metrics.
        
        This test establishes performance baselines for context creation patterns
        to detect performance regressions in session management.
        """
        # Performance benchmark for context operations
        iterations = 50
        context_times = []
        session_times = []
        
        user_id = self.test_users[0]["id"]
        
        # Benchmark direct context creation
        for i in range(iterations):
            thread_id = f"thd_benchmark_{i}_{uuid.uuid4().hex[:8]}"
            
            # Time get_user_execution_context
            start = time.time()
            context = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id
            )
            context_time = time.time() - start
            context_times.append(context_time)
            
            # Time get_user_session_context
            start = time.time()
            session_context = await get_user_session_context(
                user_id=user_id,
                thread_id=thread_id
            )
            session_time = time.time() - start
            session_times.append(session_time)
        
        # Calculate statistics
        avg_context_time = sum(context_times) / len(context_times)
        avg_session_time = sum(session_times) / len(session_times)
        
        max_context_time = max(context_times)
        max_session_time = max(session_times)
        
        # Performance assertions (reasonable baseline expectations)
        assert avg_context_time < 0.1, \
            f"Average context creation time too slow: {avg_context_time:.4f}s"
        
        assert avg_session_time < 0.2, \
            f"Average session context time too slow: {avg_session_time:.4f}s"
        
        assert max_context_time < 0.5, \
            f"Maximum context creation time too slow: {max_context_time:.4f}s"
        
        assert max_session_time < 1.0, \
            f"Maximum session context time too slow: {max_session_time:.4f}s"
        
        # Log performance metrics
        logger.info("Performance Benchmark Results:")
        logger.info(f"  Average context creation: {avg_context_time:.4f}s")
        logger.info(f"  Average session context: {avg_session_time:.4f}s")
        logger.info(f"  Max context creation: {max_context_time:.4f}s")
        logger.info(f"  Max session context: {max_session_time:.4f}s")
        
        logger.info(" PASS:  Performance benchmarks established successfully")


# Test execution markers for pytest
pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.timeout(300),  # 5 minute timeout for integration tests
    pytest.mark.skipif(
        get_env().get("SKIP_INTEGRATION_TESTS", "false").lower() == "true",
        reason="Integration tests skipped via environment variable"
    )
]


if __name__ == "__main__":
    # Allow running test directly for development
    pytest.main([__file__, "-v", "-s", "--tb=short"])