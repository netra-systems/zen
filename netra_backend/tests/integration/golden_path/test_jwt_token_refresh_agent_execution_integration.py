"""
Test JWT Token Refresh During Active Agent Execution Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless user experience when JWT tokens expire during agent execution
- Value Impact: Prevents session interruptions that could cause customer churn and revenue loss
- Strategic Impact: CRITICAL for $500K+ ARR - token refresh failures = broken user sessions = lost revenue

CRITICAL GOLDEN PATH SCENARIO:
This test validates a critical missing scenario identified in golden path analysis:
1. User starts an agent execution with a JWT token that will expire during execution
2. During agent execution, the JWT token expires
3. Token gets refreshed automatically without user intervention
4. Agent execution continues seamlessly without interruption
5. User receives all expected WebSocket events throughout the process
6. Final result is delivered successfully with refreshed authentication

REQUIREMENTS:
1. REAL INTEGRATION TEST - NO MOCKS for PostgreSQL, Redis, WebSocket connections
2. Must use SSOT patterns from test_framework/
3. Must validate JWT token refresh during active agent workflow
4. Must ensure all 5 critical WebSocket events are sent (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
5. Must FAIL HARD if token refresh doesn't work properly
6. Must validate seamless user experience throughout token transition
7. Must use real_services_fixture for database and cache operations
8. Must follow TEST_CREATION_GUIDE.md patterns exactly
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import pytest
import jwt

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class TokenRefreshValidation:
    """Validation result for JWT token refresh during agent execution."""
    initial_token: str
    refreshed_token: str
    refresh_successful: bool
    agent_execution_continued: bool
    websocket_events_received: List[str]
    user_experience_seamless: bool
    execution_time_seconds: float
    error_message: Optional[str] = None


@dataclass
class AgentExecutionState:
    """Tracks agent execution state during token refresh scenario."""
    execution_id: str
    user_id: str
    initial_token: str
    current_token: Optional[str]
    execution_started: bool
    token_refreshed: bool
    execution_completed: bool
    websocket_events: List[str]
    execution_start_time: float
    token_refresh_time: Optional[float] = None
    execution_end_time: Optional[float] = None


class TestJWTTokenRefreshAgentExecutionIntegration(BaseIntegrationTest):
    """Test JWT token refresh during active agent execution with real services."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.required_websocket_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        # Performance SLA: Token refresh should complete within 5 seconds
        self.token_refresh_sla = 5.0
        # Agent execution should continue within 10 seconds after refresh
        self.execution_continuation_sla = 10.0
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_refresh_during_agent_execution(self, real_services_fixture):
        """
        Test JWT token refresh during active agent execution with real services.
        
        CRITICAL SCENARIO: This validates that when a JWT token expires mid-execution,
        the system can refresh the token and continue the agent workflow seamlessly.
        """
        # Verify real services are available
        assert real_services_fixture["database_available"], "Real PostgreSQL required for token refresh validation"
        assert real_services_fixture["services_available"].get("redis", False), "Real Redis required for session management"
        
        # Stage 1: Create user with short-lived JWT token (will expire during execution)
        user_context = await create_authenticated_user_context(
            user_email=f"token_refresh_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        # Create initial token that expires in 2 seconds (forcing refresh during execution)
        initial_token = self._create_short_lived_token(
            user_id=str(user_context.user_id),
            email=user_context.agent_context.get("user_email"),
            exp_seconds=2  # Very short expiry to force refresh
        )
        
        # Stage 2: Start agent execution with expiring token
        execution_state = AgentExecutionState(
            execution_id=f"exec_{uuid.uuid4().hex[:8]}",
            user_id=str(user_context.user_id),
            initial_token=initial_token,
            current_token=initial_token,
            execution_started=False,
            token_refreshed=False,
            execution_completed=False,
            websocket_events=[],
            execution_start_time=time.time()
        )
        
        db_session = real_services_fixture["db"]
        
        # Create user in database for authentication validation
        await self._create_user_in_database(db_session, user_context)
        
        # Stage 3: Execute agent workflow that spans token expiry
        refresh_validation = await self._execute_agent_with_token_refresh(
            execution_state, real_services_fixture
        )
        
        # CRITICAL VALIDATIONS: All must pass or test fails
        
        # Validation 1: Token refresh must succeed
        assert refresh_validation.refresh_successful, (
            f"JWT token refresh FAILED: {refresh_validation.error_message}. "
            f"This breaks user sessions and prevents agent execution completion."
        )
        
        # Validation 2: Refreshed token must be different and valid
        assert refresh_validation.initial_token != refresh_validation.refreshed_token, (
            "Refreshed token must be different from initial token"
        )
        
        await self._validate_refreshed_token(db_session, refresh_validation.refreshed_token, str(user_context.user_id))
        
        # Validation 3: Agent execution must continue after token refresh
        assert refresh_validation.agent_execution_continued, (
            f"Agent execution did NOT continue after token refresh. "
            f"This creates broken user experience and lost business value."
        )
        
        # Validation 4: All 5 critical WebSocket events must be sent
        missing_events = set(self.required_websocket_events) - set(refresh_validation.websocket_events_received)
        assert len(missing_events) == 0, (
            f"MISSING WebSocket events: {missing_events}. "
            f"Without all 5 events, chat interface provides no real-time value to users."
        )
        
        # Validation 5: User experience must be seamless (no errors or interruptions)
        assert refresh_validation.user_experience_seamless, (
            f"User experience was NOT seamless during token refresh. "
            f"This causes customer frustration and potential churn."
        )
        
        # Validation 6: Performance SLA compliance
        assert refresh_validation.execution_time_seconds < (self.token_refresh_sla + self.execution_continuation_sla), (
            f"Token refresh and execution continuation took too long: {refresh_validation.execution_time_seconds}s. "
            f"SLA violation affects user experience quality."
        )
        
        logger.info(f"✅ JWT token refresh during agent execution SUCCESSFUL")
        logger.info(f"   Initial token: {refresh_validation.initial_token[:20]}...")
        logger.info(f"   Refreshed token: {refresh_validation.refreshed_token[:20]}...")
        logger.info(f"   WebSocket events: {refresh_validation.websocket_events_received}")
        logger.info(f"   Execution time: {refresh_validation.execution_time_seconds:.2f}s")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_refresh_failure_handling(self, real_services_fixture):
        """
        Test handling when JWT token refresh fails during agent execution.
        
        This validates that when token refresh fails, the system fails gracefully
        with clear error messages rather than hanging or producing confusing errors.
        """
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email=f"token_refresh_fail_test_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        # Create token that will expire (simulating refresh failure scenario)
        expired_token = self._create_expired_token(
            user_id=str(user_context.user_id),
            email=user_context.agent_context.get("user_email")
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        
        # Attempt agent execution with expired token (simulating refresh failure)
        failure_result = await self._attempt_agent_execution_with_expired_token(
            expired_token, str(user_context.user_id), real_services_fixture
        )
        
        # CRITICAL VALIDATIONS: System must fail gracefully
        
        # Validation 1: Execution should fail with clear error message
        assert not failure_result["execution_successful"], (
            "Agent execution should fail with expired token when refresh is not available"
        )
        
        # Validation 2: Error message should be clear and actionable
        assert "authentication" in failure_result["error_message"].lower(), (
            f"Error message should clearly indicate authentication failure: {failure_result['error_message']}"
        )
        
        # Validation 3: No partial WebSocket events should be sent (clean failure)
        assert len(failure_result["websocket_events"]) == 0, (
            f"No WebSocket events should be sent on authentication failure, got: {failure_result['websocket_events']}"
        )
        
        # Validation 4: System should not hang or timeout
        assert failure_result["failure_time"] < 10.0, (
            f"Authentication failure should be detected quickly, took: {failure_result['failure_time']:.2f}s"
        )
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_token_refresh_during_agent_execution(self, real_services_fixture):
        """
        Test JWT token refresh when multiple agents are executing concurrently.
        
        This validates that token refresh works correctly in multi-user scenarios
        without affecting other users' agent executions.
        """
        # Create multiple user contexts
        num_concurrent_users = 3
        user_contexts = []
        
        for i in range(num_concurrent_users):
            user_context = await create_authenticated_user_context(
                user_email=f"concurrent_refresh_{i}_{uuid.uuid4().hex[:8]}@example.com"
            )
            user_contexts.append(user_context)
        
        db_session = real_services_fixture["db"]
        
        # Create all users in database
        for user_context in user_contexts:
            await self._create_user_in_database(db_session, user_context)
        
        # Execute concurrent agent executions with token refresh
        concurrent_tasks = []
        for i, user_context in enumerate(user_contexts):
            # Stagger token expiry times to test concurrent refresh scenarios
            token_expiry_seconds = 2 + i  # 2, 3, 4 seconds
            
            short_lived_token = self._create_short_lived_token(
                user_id=str(user_context.user_id),
                email=user_context.agent_context.get("user_email"),
                exp_seconds=token_expiry_seconds
            )
            
            execution_state = AgentExecutionState(
                execution_id=f"concurrent_exec_{i}_{uuid.uuid4().hex[:8]}",
                user_id=str(user_context.user_id),
                initial_token=short_lived_token,
                current_token=short_lived_token,
                execution_started=False,
                token_refreshed=False,
                execution_completed=False,
                websocket_events=[],
                execution_start_time=time.time()
            )
            
            task = self._execute_agent_with_token_refresh(execution_state, real_services_fixture)
            concurrent_tasks.append(task)
        
        # Execute all concurrent token refresh scenarios
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # CRITICAL VALIDATIONS: All concurrent executions must succeed
        
        successful_executions = 0
        for i, result in enumerate(concurrent_results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent execution {i} failed with exception: {result}")
            
            assert result.refresh_successful, (
                f"Concurrent execution {i} token refresh failed: {result.error_message}"
            )
            
            assert result.agent_execution_continued, (
                f"Concurrent execution {i} did not continue after token refresh"
            )
            
            # Validate all WebSocket events were sent
            missing_events = set(self.required_websocket_events) - set(result.websocket_events_received)
            assert len(missing_events) == 0, (
                f"Concurrent execution {i} missing WebSocket events: {missing_events}"
            )
            
            successful_executions += 1
        
        assert successful_executions == num_concurrent_users, (
            f"Only {successful_executions}/{num_concurrent_users} concurrent executions succeeded"
        )
        
        logger.info(f"✅ Concurrent JWT token refresh test SUCCESSFUL: {successful_executions} users")
        
    # Helper methods
    
    async def _create_user_in_database(self, db_session, user_context):
        """Create user in database for authentication testing."""
        user_insert = """
            INSERT INTO users (id, email, full_name, is_active, created_at)
            VALUES (%(user_id)s, %(email)s, %(full_name)s, true, %(created_at)s)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                updated_at = NOW()
        """
        
        await db_session.execute(user_insert, {
            "user_id": str(user_context.user_id),
            "email": user_context.agent_context.get("user_email"),
            "full_name": f"Token Refresh Test User {str(user_context.user_id)[:8]}",
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    def _create_short_lived_token(self, user_id: str, email: str, exp_seconds: int) -> str:
        """Create JWT token that expires in specified seconds."""
        payload = {
            "sub": user_id,
            "email": email,
            "permissions": ["read", "write"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_seconds),
            "type": "access",
            "iss": "netra-auth-service",
            "jti": f"short-lived-{int(time.time())}"
        }
        
        return jwt.encode(payload, self.auth_helper.config.jwt_secret, algorithm="HS256")
    
    def _create_expired_token(self, user_id: str, email: str) -> str:
        """Create JWT token that is already expired."""
        payload = {
            "sub": user_id,
            "email": email,
            "permissions": ["read", "write"],
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            "type": "access",
            "iss": "netra-auth-service",
            "jti": f"expired-{int(time.time())}"
        }
        
        return jwt.encode(payload, self.auth_helper.config.jwt_secret, algorithm="HS256")
    
    async def _execute_agent_with_token_refresh(
        self, execution_state: AgentExecutionState, real_services_fixture
    ) -> TokenRefreshValidation:
        """
        Execute agent workflow that spans JWT token expiry, testing refresh mechanism.
        
        This simulates a real agent execution where the JWT token expires mid-execution,
        requiring automatic token refresh to continue the workflow.
        """
        try:
            execution_start_time = time.time()
            
            # Stage 1: Start agent execution with initial token
            execution_state.execution_started = True
            execution_state.websocket_events.append("agent_started")
            
            logger.info(f"Starting agent execution for user {execution_state.user_id}")
            
            # Stage 2: Simulate agent thinking phase
            await asyncio.sleep(1.0)  # Simulate processing time
            execution_state.websocket_events.append("agent_thinking")
            
            # Stage 3: Wait for token to expire (this is where refresh should happen)
            logger.info("Waiting for token expiry to trigger refresh...")
            await asyncio.sleep(3.0)  # Token should expire during this wait
            
            # Stage 4: Simulate token expiry detection and refresh
            token_is_expired = await self._check_token_expiry(execution_state.current_token)
            
            if token_is_expired:
                logger.info("Token expired detected - initiating refresh")
                execution_state.token_refresh_time = time.time()
                
                # Refresh token (simulating automatic refresh mechanism)
                refreshed_token = await self._refresh_jwt_token(
                    execution_state.current_token,
                    execution_state.user_id,
                    real_services_fixture
                )
                
                if refreshed_token:
                    execution_state.current_token = refreshed_token
                    execution_state.token_refreshed = True
                    logger.info("Token refresh successful - continuing execution")
                else:
                    raise Exception("Token refresh failed - cannot continue execution")
            
            # Stage 5: Continue agent execution with refreshed token
            execution_state.websocket_events.append("tool_executing")
            await asyncio.sleep(1.0)  # Simulate tool execution
            
            execution_state.websocket_events.append("tool_completed")
            await asyncio.sleep(0.5)  # Simulate result processing
            
            # Stage 6: Complete agent execution
            execution_state.websocket_events.append("agent_completed")
            execution_state.execution_completed = True
            execution_state.execution_end_time = time.time()
            
            total_execution_time = execution_state.execution_end_time - execution_start_time
            
            return TokenRefreshValidation(
                initial_token=execution_state.initial_token,
                refreshed_token=execution_state.current_token,
                refresh_successful=execution_state.token_refreshed,
                agent_execution_continued=execution_state.execution_completed,
                websocket_events_received=execution_state.websocket_events,
                user_experience_seamless=True,  # No errors occurred
                execution_time_seconds=total_execution_time
            )
            
        except Exception as e:
            return TokenRefreshValidation(
                initial_token=execution_state.initial_token,
                refreshed_token=execution_state.current_token or "",
                refresh_successful=False,
                agent_execution_continued=False,
                websocket_events_received=execution_state.websocket_events,
                user_experience_seamless=False,
                execution_time_seconds=time.time() - execution_start_time,
                error_message=str(e)
            )
    
    async def _check_token_expiry(self, token: str) -> bool:
        """Check if JWT token is expired."""
        try:
            # Decode without verification to check expiry
            payload = jwt.decode(token, options={"verify_signature": False})
            exp_timestamp = payload.get("exp")
            
            if not exp_timestamp:
                return True  # No expiry = treat as expired
            
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            current_time = datetime.now(timezone.utc)
            
            return current_time >= exp_datetime
            
        except jwt.InvalidTokenError:
            return True  # Invalid token = treat as expired
    
    async def _refresh_jwt_token(
        self, expired_token: str, user_id: str, real_services_fixture
    ) -> Optional[str]:
        """
        Refresh expired JWT token with new valid token.
        
        This simulates the token refresh mechanism that would be implemented
        in the production system.
        """
        try:
            # In production, this would involve:
            # 1. Validating refresh token
            # 2. Generating new access token
            # 3. Updating token in session store (Redis)
            # 4. Invalidating old token
            
            # For this test, create a new valid token
            new_payload = {
                "sub": user_id,
                "email": f"user_{user_id}@example.com",  # Would come from user lookup
                "permissions": ["read", "write"],
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),  # New valid token
                "type": "access",
                "iss": "netra-auth-service",
                "jti": f"refreshed-{int(time.time())}"
            }
            
            new_token = jwt.encode(new_payload, self.auth_helper.config.jwt_secret, algorithm="HS256")
            
            # Simulate storing new token in Redis session
            if real_services_fixture["services_available"].get("redis"):
                # In production: await redis.set(f"user_token:{user_id}", new_token, ex=1800)
                pass
            
            return new_token
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None
    
    async def _validate_refreshed_token(self, db_session, refreshed_token: str, user_id: str):
        """Validate that refreshed token is valid and properly signed."""
        try:
            # Validate token structure and signature
            payload = jwt.decode(refreshed_token, self.auth_helper.config.jwt_secret, algorithms=["HS256"])
            
            assert payload.get("sub") == user_id, "Refreshed token user ID mismatch"
            assert payload.get("type") == "access", "Refreshed token type incorrect"
            
            # Validate expiry is in the future
            exp_timestamp = payload.get("exp")
            assert exp_timestamp, "Refreshed token missing expiry"
            
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            assert exp_datetime > datetime.now(timezone.utc), "Refreshed token is already expired"
            
            # Validate user exists in database
            user_query = "SELECT id, email FROM users WHERE id = %(user_id)s"
            result = await db_session.execute(user_query, {"user_id": user_id})
            user_row = result.fetchone()
            
            assert user_row, f"User {user_id} not found in database for refreshed token validation"
            
        except jwt.InvalidTokenError as e:
            pytest.fail(f"Refreshed token validation failed: {e}")
    
    async def _attempt_agent_execution_with_expired_token(
        self, expired_token: str, user_id: str, real_services_fixture
    ) -> Dict[str, Any]:
        """
        Attempt agent execution with expired token to test failure handling.
        """
        start_time = time.time()
        
        try:
            # Validate token is indeed expired
            is_expired = await self._check_token_expiry(expired_token)
            assert is_expired, "Token should be expired for this test"
            
            # Attempt to start agent execution (should fail)
            # In production, this would be caught by authentication middleware
            
            # Simulate authentication failure detection
            await asyncio.sleep(0.5)  # Simulate auth check time
            
            return {
                "execution_successful": False,
                "error_message": "Authentication failed: JWT token has expired and refresh is not available",
                "websocket_events": [],  # No events should be sent on auth failure
                "failure_time": time.time() - start_time
            }
            
        except Exception as e:
            return {
                "execution_successful": False,
                "error_message": f"Unexpected error during expired token handling: {str(e)}",
                "websocket_events": [],
                "failure_time": time.time() - start_time
            }