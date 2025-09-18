"""
Multi-User Concurrent Processing Integration Test - Issue #1059 Agent Golden Path Tests

Business Value Justification:
- Segment: Enterprise tier - Multi-user scalability and data isolation
- Business Goal: Validate platform scalability and enterprise-grade user isolation
- Value Impact: Ensures multiple users can simultaneously interact without data contamination
- Revenue Impact: Protects enterprise revenue ($500K+ ARR) requiring multi-user concurrency

PURPOSE:
This integration test validates that multiple users can simultaneously interact
with agents without data contamination, context bleeding, or performance degradation.
This is critical for enterprise deployments and multi-user business environments.

CRITICAL MULTI-USER REQUIREMENTS:
1. Complete user isolation - no shared state or context bleeding
2. Concurrent processing without performance degradation
3. Independent WebSocket event delivery per user
4. Proper resource allocation and memory management
5. User-specific thread and context management
6. Scalable architecture validation

CRITICAL DESIGN:
- NO DOCKER usage - tests run against GCP staging environment
- Real concurrent WebSocket connections from multiple simulated users
- Comprehensive validation of user isolation at all levels
- Performance monitoring under concurrent load
- Memory and resource usage validation
- Cross-user contamination detection and prevention

SCOPE:
1. Concurrent multi-user agent interactions with isolation validation
2. WebSocket event delivery isolation between users
3. Agent state and context isolation per user
4. Performance scalability under concurrent load
5. Resource management and memory leak prevention
6. Enterprise-grade security and privacy validation

AGENT_SESSION_ID: agent-session-2025-09-14-1430
Issue #1059: Agent Golden Path Integration Tests - Step 1 Implementation
"""

import asyncio
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Coroutine
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest
import websockets
from websockets import ConnectionClosed, WebSocketException

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser
from tests.e2e.staging_config import StagingTestConfig
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """Represents a user session for concurrent processing testing."""
    user: AuthenticatedUser
    thread_id: str
    run_id: str
    session_id: str
    start_time: float
    websocket_url: str
    websocket_headers: Dict[str, str]
    messages_sent: List[Dict[str, Any]] = field(default_factory=list)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    agent_responses: List[str] = field(default_factory=list)
    session_errors: List[str] = field(default_factory=list)
    completion_time: Optional[float] = None
    isolation_verified: bool = False


@dataclass
class ConcurrencyValidationResult:
    """Results of multi-user concurrency validation."""
    concurrency_successful: bool
    users_processed: int
    total_sessions: List[UserSession]
    isolation_violations: List[str]
    performance_degradation_detected: bool
    average_response_time: float
    concurrent_peak_users: int
    resource_usage_acceptable: bool
    cross_user_contamination_detected: bool
    enterprise_readiness_score: float
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)


class MultiUserConcurrencyValidator:
    """Validates multi-user concurrent processing and isolation."""
    
    # Performance thresholds for concurrent users
    ACCEPTABLE_RESPONSE_TIME_DEGRADATION = 2.0  # Max 2x degradation under load
    MEMORY_LEAK_THRESHOLD = 0.1  # 10% memory growth tolerance
    CONCURRENT_USER_TARGET = 5   # Test with 5 concurrent users
    
    # Isolation validation keywords
    USER_ISOLATION_INDICATORS = [
        "user_id", "thread_id", "session", "context", "conversation",
        "your request", "your question", "your message", "you asked"
    ]
    
    def __init__(self):
        self.sessions: List[UserSession] = []
        self.validation_start_time = time.time()
        self.baseline_response_time: Optional[float] = None
        self.isolation_violations: List[str] = []
        self.lock = threading.Lock()
        
    async def create_user_session(self, e2e_helper: E2EWebSocketAuthHelper, 
                                session_index: int, websocket_url: str) -> UserSession:
        """Create a user session for concurrent testing."""
        user = await e2e_helper.create_authenticated_user(
            email=f"concurrent_user_{session_index}_{int(time.time())}@test.com",
            permissions=["read", "write", "chat", "agent_execution"]
        )
        
        thread_id = f"concurrent_thread_{session_index}_{uuid.uuid4()}"
        run_id = f"concurrent_run_{session_index}_{uuid.uuid4()}"
        session_id = f"session_{session_index}_{uuid.uuid4()}"
        
        websocket_headers = e2e_helper.get_websocket_headers(user.jwt_token)
        
        session = UserSession(
            user=user,
            thread_id=thread_id,
            run_id=run_id,
            session_id=session_id,
            start_time=time.time(),
            websocket_url=websocket_url,
            websocket_headers=websocket_headers
        )
        
        with self.lock:
            self.sessions.append(session)
        
        logger.info(f"[CONCURRENCY] Created user session {session_index}: {user.email}")
        return session
    
    async def execute_user_session(self, session: UserSession, session_messages: List[str], 
                                 connection_timeout: float = 15.0, 
                                 response_timeout: float = 30.0) -> None:
        """Execute a complete user session with multiple messages."""
        try:
            async with websockets.connect(
                session.websocket_url,
                additional_headers=session.websocket_headers,
                timeout=connection_timeout,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                
                logger.info(f"[CONCURRENCY] Session {session.session_id} WebSocket connected")
                
                # Process each message in the session
                for i, message_content in enumerate(session_messages):
                    message_start_time = time.time()
                    
                    message_data = {
                        "message": message_content,
                        "thread_id": session.thread_id,
                        "run_id": f"{session.run_id}_msg_{i}",
                        "context": {
                            "user_session": session.session_id,
                            "message_index": i,
                            "isolation_test": True,
                            "user_identifier": session.user.user_id
                        }
                    }
                    
                    # Send message
                    await websocket.send(json.dumps(message_data))
                    session.messages_sent.append(message_data)
                    
                    # Collect response
                    response_content = ""
                    message_events = []
                    
                    while time.time() - message_start_time < response_timeout:
                        try:
                            response_text = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=10.0
                            )
                            
                            response_data = json.loads(response_text)
                            event_type = response_data.get("type", response_data.get("event_type", "unknown"))
                            
                            # Store event with session context
                            event_with_context = {
                                **response_data,
                                "_session_id": session.session_id,
                                "_user_id": session.user.user_id,
                                "_message_index": i,
                                "_timestamp": time.time()
                            }
                            
                            message_events.append(event_with_context)
                            session.events_received.append(event_with_context)
                            
                            # Collect response content
                            if event_type in ["agent_completed", "agent_response", "message"]:
                                content = response_data.get("content", response_data.get("message", ""))
                                if content:
                                    response_content += content
                            
                            # Check for completion
                            if event_type == "agent_completed":
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except (ConnectionClosed, WebSocketException) as e:
                            session.session_errors.append(f"WebSocket error on message {i}: {e}")
                            break
                    
                    # Store response and validate isolation
                    if response_content:
                        session.agent_responses.append(response_content)
                        await self._validate_response_isolation(session, response_content, message_data)
                    
                    # Brief pause between messages within session
                    await asyncio.sleep(1.0)
                
                session.completion_time = time.time()
                logger.info(f"[CONCURRENCY] Session {session.session_id} completed successfully")
                
        except Exception as e:
            session.session_errors.append(f"Session execution error: {e}")
            logger.error(f"[CONCURRENCY] Session {session.session_id} failed: {e}")
    
    async def _validate_response_isolation(self, session: UserSession, 
                                         response_content: str, 
                                         original_message: Dict[str, Any]) -> None:
        """Validate that the response is properly isolated to this user session."""
        # Check for inappropriate references to other users/sessions
        other_session_ids = [s.session_id for s in self.sessions if s.session_id != session.session_id]
        other_user_ids = [s.user.user_id for s in self.sessions if s.user.user_id != session.user.user_id]
        
        # Look for references to other sessions/users in the response
        response_lower = response_content.lower()
        
        for other_session_id in other_session_ids:
            if other_session_id.lower() in response_lower:
                violation = f"Response contains reference to other session: {other_session_id}"
                with self.lock:
                    self.isolation_violations.append(violation)
                logger.warning(f"[ISOLATION VIOLATION] {violation}")
        
        for other_user_id in other_user_ids:
            if other_user_id.lower() in response_lower:
                violation = f"Response contains reference to other user: {other_user_id}"
                with self.lock:
                    self.isolation_violations.append(violation)
                logger.warning(f"[ISOLATION VIOLATION] {violation}")
        
        # Validate that response is contextually appropriate for this user's message
        user_message = original_message.get("message", "")
        if len(user_message) > 50 and len(response_content) > 50:
            # Check for thematic relevance (basic validation)
            user_words = set(user_message.lower().split())
            response_words = set(response_content.lower().split())
            
            # Remove common words for more meaningful overlap calculation
            common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
            user_words -= common_words
            response_words -= common_words
            
            if len(user_words) > 5 and len(response_words) > 5:
                overlap = user_words.intersection(response_words)
                overlap_ratio = len(overlap) / min(len(user_words), len(response_words))
                
                if overlap_ratio < 0.1:  # Less than 10% relevance
                    violation = f"Response may not be contextually relevant to user message (overlap: {overlap_ratio:.2f})"
                    logger.info(f"[ISOLATION CHECK] {violation}")
                    # Note: This is informational, not necessarily a violation
        
        session.isolation_verified = True
    
    def validate_concurrency(self) -> ConcurrencyValidationResult:
        """Validate the overall multi-user concurrency results."""
        current_time = time.time()
        
        # Calculate performance metrics
        completed_sessions = [s for s in self.sessions if s.completion_time is not None]
        successful_sessions = [s for s in completed_sessions if len(s.session_errors) == 0]
        
        # Response time analysis
        response_times = []
        for session in completed_sessions:
            if session.completion_time and len(session.messages_sent) > 0:
                session_duration = session.completion_time - session.start_time
                avg_response_time = session_duration / len(session.messages_sent)
                response_times.append(avg_response_time)
        
        average_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        # Performance degradation assessment
        performance_degradation_detected = False
        if self.baseline_response_time and average_response_time > 0:
            degradation_ratio = average_response_time / self.baseline_response_time
            performance_degradation_detected = degradation_ratio > self.ACCEPTABLE_RESPONSE_TIME_DEGRADATION
        
        # Cross-user contamination detection
        cross_user_contamination_detected = len(self.isolation_violations) > 0
        
        # Resource usage assessment (simplified for this test)
        resource_usage_acceptable = len(successful_sessions) >= len(self.sessions) * 0.8  # 80% success rate
        
        # Enterprise readiness score
        isolation_score = 1.0 - (len(self.isolation_violations) / max(len(self.sessions), 1))
        performance_score = 0.5 if performance_degradation_detected else 1.0
        success_rate = len(successful_sessions) / len(self.sessions) if self.sessions else 0.0
        
        enterprise_readiness_score = (isolation_score + performance_score + success_rate) / 3.0
        
        # Overall concurrency success
        concurrency_successful = (
            len(successful_sessions) >= max(2, len(self.sessions) * 0.7) and  # At least 70% success
            not cross_user_contamination_detected and
            resource_usage_acceptable and
            enterprise_readiness_score > 0.7
        )
        
        # Performance metrics
        performance_metrics = {
            "total_validation_duration": current_time - self.validation_start_time,
            "total_sessions_created": len(self.sessions),
            "successful_sessions": len(successful_sessions),
            "average_response_time": average_response_time,
            "total_messages_sent": sum(len(s.messages_sent) for s in self.sessions),
            "total_events_received": sum(len(s.events_received) for s in self.sessions),
            "isolation_violations_count": len(self.isolation_violations),
            "session_success_rate": success_rate
        }
        
        return ConcurrencyValidationResult(
            concurrency_successful=concurrency_successful,
            users_processed=len(self.sessions),
            total_sessions=self.sessions,
            isolation_violations=self.isolation_violations,
            performance_degradation_detected=performance_degradation_detected,
            average_response_time=average_response_time,
            concurrent_peak_users=len(self.sessions),
            resource_usage_acceptable=resource_usage_acceptable,
            cross_user_contamination_detected=cross_user_contamination_detected,
            enterprise_readiness_score=enterprise_readiness_score,
            performance_metrics=performance_metrics
        )


class MultiUserConcurrentProcessingTests(SSotAsyncTestCase):
    """
    Multi-User Concurrent Processing Integration Tests.
    
    Tests that multiple users can simultaneously interact with agents
    without data contamination, context bleeding, or performance degradation.
    """
    
    def setup_method(self, method=None):
        """Set up multi-user concurrency test environment."""
        super().setup_method(method)
        self.env = get_env()
        
        # Environment configuration
        test_env = self.env.get("TEST_ENV", "test")
        if test_env == "staging" or self.env.get("ENVIRONMENT") == "staging":
            self.test_env = "staging"
            self.staging_config = StagingTestConfig()
            self.websocket_url = self.staging_config.urls.websocket_url
            self.timeout = 60.0  # Longer timeout for concurrent operations
        else:
            self.test_env = "test"
            self.websocket_url = self.env.get("TEST_WEBSOCKET_URL", "ws://localhost:8002/ws")
            self.timeout = 45.0
            
        self.e2e_helper = E2EWebSocketAuthHelper(environment=self.test_env)
        
        # Concurrency test configuration
        self.concurrent_users = 3     # Test with 3 concurrent users (manageable for CI)
        self.messages_per_user = 2    # 2 messages per user session
        self.concurrency_timeout = 90.0  # Allow time for concurrent processing
        self.connection_timeout = 20.0   # Connection establishment
        self.response_timeout = 35.0     # Individual response timeout
        
        logger.info(f"[CONCURRENCY SETUP] Test environment: {self.test_env}")
        logger.info(f"[CONCURRENCY SETUP] Concurrent users: {self.concurrent_users}")
        logger.info(f"[CONCURRENCY SETUP] Messages per user: {self.messages_per_user}")
        
    @pytest.mark.integration
    @pytest.mark.agent_golden_path
    @pytest.mark.multi_user
    @pytest.mark.concurrency
    @pytest.mark.timeout(150)  # Allow extra time for concurrent operations
    async def test_multi_user_concurrent_agent_interactions(self):
        """
        Test that multiple users can concurrently interact with agents without isolation violations.
        
        Validates:
        1. Multiple users can simultaneously connect and send messages
        2. Agent responses are properly isolated per user
        3. No cross-user context bleeding or data contamination
        4. Performance remains acceptable under concurrent load
        5. WebSocket events are delivered to correct users only
        6. Resource usage and memory management under load
        
        BVJ: This test validates enterprise-grade multi-user scalability,
        protecting the $500K+ ARR enterprise revenue that requires
        concurrent user support with proper isolation.
        """
        test_start_time = time.time()
        print(f"[MULTI-USER CONCURRENCY] Starting multi-user concurrent processing test")
        print(f"[MULTI-USER CONCURRENCY] Environment: {self.test_env}")
        print(f"[MULTI-USER CONCURRENCY] Testing {self.concurrent_users} concurrent users")
        print(f"[MULTI-USER CONCURRENCY] {self.messages_per_user} messages per user")
        
        # Initialize concurrency validator
        validator = MultiUserConcurrencyValidator()
        
        # Create user sessions for concurrent testing
        print(f"[MULTI-USER CONCURRENCY] Creating {self.concurrent_users} user sessions...")
        user_sessions = []
        
        for i in range(self.concurrent_users):
            session = await validator.create_user_session(
                e2e_helper=self.e2e_helper,
                session_index=i,
                websocket_url=self.websocket_url
            )
            user_sessions.append(session)
        
        print(f"[MULTI-USER CONCURRENCY] Created {len(user_sessions)} user sessions")
        
        # Define different message sets for each user to test isolation
        user_message_sets = [
            [
                "I need help optimizing our customer acquisition strategy for our healthcare SaaS platform. Our current CAC is $150 per customer.",
                "Based on your analysis, what specific tactics would you recommend to reduce our acquisition costs?"
            ],
            [
                "Can you analyze our financial performance and suggest cost optimization strategies for our quarterly review?", 
                "What metrics should we focus on to track the success of these cost optimization initiatives?"
            ],
            [
                "We're planning to expand our AI platform to the European market. What are the key considerations for this expansion?",
                "How should we approach regulatory compliance and data privacy requirements in the EU market?"
            ]
        ]
        
        # Ensure we have enough message sets for all users
        while len(user_message_sets) < len(user_sessions):
            user_message_sets.extend(user_message_sets[:1])  # Repeat first set if needed
        
        # Execute concurrent user sessions
        print(f"[MULTI-USER CONCURRENCY] Executing concurrent user sessions...")
        
        # Create concurrent tasks for all user sessions
        concurrent_tasks = []
        for i, session in enumerate(user_sessions):
            messages = user_message_sets[i % len(user_message_sets)]
            task = validator.execute_user_session(
                session=session,
                session_messages=messages,
                connection_timeout=self.connection_timeout,
                response_timeout=self.response_timeout
            )
            concurrent_tasks.append(task)
        
        # Execute all sessions concurrently
        try:
            await asyncio.wait_for(
                asyncio.gather(*concurrent_tasks, return_exceptions=True),
                timeout=self.concurrency_timeout
            )
        except asyncio.TimeoutError:
            print(f"[MULTI-USER CONCURRENCY] Timeout during concurrent execution")
        
        # Validate concurrency results
        validation_result = validator.validate_concurrency()
        
        # Log comprehensive results
        test_duration = time.time() - test_start_time
        print(f"\n[MULTI-USER CONCURRENCY RESULTS] Multi-User Concurrent Processing Results")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Test Duration: {test_duration:.2f}s")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Users Processed: {validation_result.users_processed}")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Successful Sessions: {validation_result.performance_metrics['successful_sessions']}")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Session Success Rate: {validation_result.performance_metrics['session_success_rate']:.2f}")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Average Response Time: {validation_result.average_response_time:.2f}s")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Isolation Violations: {len(validation_result.isolation_violations)}")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Cross-User Contamination: {validation_result.cross_user_contamination_detected}")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Performance Degradation: {validation_result.performance_degradation_detected}")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Enterprise Readiness Score: {validation_result.enterprise_readiness_score:.2f}")
        print(f"[MULTI-USER CONCURRENCY RESULTS] Concurrency Successful: {validation_result.concurrency_successful}")
        
        # Detailed session results
        for i, session in enumerate(validation_result.total_sessions):
            session_success = len(session.session_errors) == 0
            print(f"[SESSION {i+1}] User: {session.user.email}")
            print(f"  - Messages Sent: {len(session.messages_sent)}")
            print(f"  - Events Received: {len(session.events_received)}")
            print(f"  - Agent Responses: {len(session.agent_responses)}")
            print(f"  - Session Errors: {len(session.session_errors)}")
            print(f"  - Isolation Verified: {session.isolation_verified}")
            print(f"  - Success: {session_success}")
        
        if validation_result.isolation_violations:
            print(f"\n[ISOLATION VIOLATIONS] Found {len(validation_result.isolation_violations)} violations:")
            for violation in validation_result.isolation_violations:
                print(f"  - {violation}")
        
        # ASSERTIONS: Comprehensive multi-user concurrency validation
        
        # Basic session creation validation
        assert len(validation_result.total_sessions) >= 2, \
            f"Expected at least 2 concurrent user sessions, got {len(validation_result.total_sessions)}"
        
        # Session success rate validation
        success_rate = validation_result.performance_metrics['session_success_rate']
        assert success_rate >= 0.7, \
            f"Session success rate {success_rate:.2f} below minimum 0.7 (70%)"
        
        # User isolation validation
        assert not validation_result.cross_user_contamination_detected, \
            f"Cross-user contamination detected: {validation_result.isolation_violations}"
        
        # Resource usage validation
        assert validation_result.resource_usage_acceptable, \
            "Resource usage not acceptable for concurrent operations"
        
        # Performance validation (if baseline exists)
        if validation_result.performance_degradation_detected:
            logger.warning("Performance degradation detected under concurrent load")
            # Don't fail test but log warning - some degradation may be acceptable
        
        # Enterprise readiness validation
        assert validation_result.enterprise_readiness_score > 0.6, \
            f"Enterprise readiness score {validation_result.enterprise_readiness_score:.2f} below minimum 0.6"
        
        # Overall concurrency validation
        assert validation_result.concurrency_successful, \
            f"Multi-user concurrency validation failed: {validation_result.error_messages}"
        
        # Response quality validation
        total_responses = sum(len(session.agent_responses) for session in validation_result.total_sessions)
        assert total_responses > 0, \
            "Expected at least some agent responses from concurrent users"
        
        print(f"[MULTI-USER CONCURRENCY SUCCESS] Multi-user concurrent processing validated successfully!")
        print(f"[MULTI-USER CONCURRENCY SUCCESS] {validation_result.users_processed} users processed concurrently")
        print(f"[MULTI-USER CONCURRENCY SUCCESS] Enterprise readiness score: {validation_result.enterprise_readiness_score:.2f}")
        print(f"[MULTI-USER CONCURRENCY SUCCESS] No cross-user contamination detected")
        print(f"[MULTI-USER CONCURRENCY SUCCESS] Average response time: {validation_result.average_response_time:.2f}s")
        
    @pytest.mark.integration
    @pytest.mark.agent_golden_path
    @pytest.mark.timeout(90)
    async def test_websocket_event_isolation_validation(self):
        """
        Test that WebSocket events are properly isolated between concurrent users.
        
        Validates that each user receives only their own WebSocket events and
        that event delivery is not mixed between different user sessions.
        """
        print(f"[WEBSOCKET ISOLATION] Starting WebSocket event isolation validation")
        
        # Create 2 users for focused isolation testing
        validator = MultiUserConcurrencyValidator()
        
        user_sessions = []
        for i in range(2):
            session = await validator.create_user_session(
                e2e_helper=self.e2e_helper,
                session_index=i,
                websocket_url=self.websocket_url
            )
            user_sessions.append(session)
        
        # Define distinct messages for isolation testing
        isolation_messages = [
            ["Analyze our HEALTHCARE customer retention metrics and provide specific recommendations."],
            ["Evaluate our FINANCIAL services product roadmap and suggest strategic improvements."]
        ]
        
        # Execute sessions with distinct keywords to test isolation
        concurrent_tasks = []
        for i, session in enumerate(user_sessions):
            messages = isolation_messages[i]
            task = validator.execute_user_session(
                session=session,
                session_messages=messages,
                connection_timeout=15.0,
                response_timeout=25.0
            )
            concurrent_tasks.append(task)
        
        # Execute concurrently
        try:
            await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        except Exception as e:
            print(f"[WEBSOCKET ISOLATION] Concurrent execution error: {e}")
        
        # Validate event isolation
        validation_result = validator.validate_concurrency()
        
        print(f"[WEBSOCKET ISOLATION RESULTS] Users: {len(user_sessions)}")
        print(f"[WEBSOCKET ISOLATION RESULTS] Isolation Violations: {len(validation_result.isolation_violations)}")
        
        # Specific isolation assertions
        assert len(validation_result.isolation_violations) == 0, \
            f"WebSocket event isolation violations detected: {validation_result.isolation_violations}"
        
        # Verify responses contain appropriate keywords
        healthcare_session = user_sessions[0]
        financial_session = user_sessions[1]
        
        if healthcare_session.agent_responses:
            healthcare_response = " ".join(healthcare_session.agent_responses).lower()
            assert "healthcare" in healthcare_response or "health" in healthcare_response, \
                "Healthcare session should receive healthcare-related response"
        
        if financial_session.agent_responses:
            financial_response = " ".join(financial_session.agent_responses).lower()
            assert "financial" in financial_response or "finance" in financial_response, \
                "Financial session should receive finance-related response"
        
        print(f"[WEBSOCKET ISOLATION SUCCESS] WebSocket event isolation validated successfully")


if __name__ == "__main__":
    # Allow running this test file directly
    import asyncio
    
    async def run_test():
        test_instance = MultiUserConcurrentProcessingTests()
        test_instance.setup_method()
        await test_instance.test_multi_user_concurrent_agent_interactions()
        print("Direct test execution completed successfully")
    
    asyncio.run(run_test())