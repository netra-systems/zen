"""
Multi-User Agent Isolation E2E Tests for Supervisor Agent Orchestration
========================================================================

Business Value Justification (BVJ):
- Segment: Enterprise (critical for $500K+ contracts) 
- Business Goal: Ensure complete multi-user isolation in agent orchestration
- Value Impact: Prevents cross-user data leaks and context bleeding in agent workflows
- Revenue Impact: Essential for enterprise trust and regulatory compliance

These tests validate that the Supervisor Agent properly orchestrates sub-agents
with complete user isolation, ensuring no cross-contamination between concurrent
user requests in the golden path user flow.

Test Environment: GCP Staging (NO DOCKER)
Coverage Focus: Supervisor Agent Multi-User Orchestration (Issue #872)
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import pytest

from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)

@dataclass
class IsolatedUserSession:
    """Represents an isolated user session for testing."""
    user_id: str
    email: str
    jwt_token: str
    websocket: Optional[object] = None
    auth_helper: Optional[E2EWebSocketAuthHelper] = None
    session_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.session_data is None:
            self.session_data = {}


class SupervisorMultiUserIsolationTests(SSotAsyncTestCase):
    """
    E2E Tests for Supervisor Agent Multi-User Isolation.
    
    These tests ensure that the Supervisor Agent correctly orchestrates 
    sub-agents with complete user isolation and no context bleeding.
    """
    
    def setUp(self):
        """Set up test environment for staging GCP."""
        super().setUp()
        
        # Use staging environment for real E2E testing
        self.environment = IsolatedEnvironment().get("TEST_ENV", "staging")
        self.auth_config = E2EAuthConfig.for_environment(self.environment)
        
        # Test configuration
        self.test_timeout = 180.0  # 3 minutes for complex multi-user tests
        self.isolation_check_interval = 2.0  # Check isolation every 2 seconds
        self.max_concurrent_users = 5  # Test with up to 5 concurrent users
        
        logger.info(f"Setting up Supervisor Multi-User Isolation tests in {self.environment}")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.supervisor_orchestration
    @pytest.mark.timeout(240)  # 4 minutes for comprehensive isolation testing
    async def test_concurrent_supervisor_agent_isolation(self):
        """
        Test that concurrent Supervisor Agent executions maintain complete user isolation.
        
        This test simulates multiple users making simultaneous requests to the Supervisor
        Agent and verifies that their contexts remain completely isolated.
        """
        logger.info("🧪 Starting concurrent supervisor agent isolation test")
        
        # Create multiple isolated user sessions
        user_sessions = await self._create_isolated_user_sessions(count=4)
        
        # Verify all sessions were created successfully
        self.assertGreaterEqual(len(user_sessions), 3, 
                               "Must have at least 3 user sessions for meaningful isolation testing")
        
        # Define unique requests for each user to test isolation
        user_requests = [
            {
                "user_request": f"Analyze performance metrics for user {session.user_id} project Alpha",
                "expected_context": f"project Alpha for {session.user_id}",
                "sensitive_data": f"SECRET_PROJECT_ALPHA_{session.user_id}_{int(time.time())}"
            }
            for session in user_sessions
        ]
        
        # Execute concurrent supervisor requests
        start_time = time.time()
        concurrent_tasks = []
        
        for i, session in enumerate(user_sessions):
            task = asyncio.create_task(
                self._execute_supervisor_request_with_isolation_monitoring(
                    session=session,
                    request_data=user_requests[i],
                    test_duration=60.0  # 1 minute per request
                )
            )
            concurrent_tasks.append(task)
        
        # Wait for all concurrent executions to complete
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results for isolation violations
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success", False)]
        failed_results = [r for r in results if not isinstance(r, dict) or not r.get("success", False)]
        
        # Assert minimum success rate for concurrent isolation
        success_rate = len(successful_results) / len(user_sessions) * 100
        self.assertGreaterEqual(success_rate, 75.0, 
                               f"Concurrent supervisor isolation success rate too low: {success_rate:.1f}%")
        
        # Verify no cross-user data contamination
        await self._verify_no_cross_user_contamination(successful_results, user_requests)
        
        # Verify supervisor agent context isolation
        await self._verify_supervisor_context_isolation(successful_results)
        
        # Performance verification
        self.assertLess(execution_time, self.test_timeout, 
                       f"Concurrent execution took too long: {execution_time:.1f}s")
        
        logger.info(f"✅ Concurrent supervisor isolation test completed: "
                   f"{len(successful_results)}/{len(user_sessions)} successful, "
                   f"execution_time={execution_time:.1f}s")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.supervisor_orchestration
    @pytest.mark.timeout(180)  # 3 minutes
    async def test_supervisor_agent_state_isolation(self):
        """
        Test that Supervisor Agent maintains isolated state across multiple users.
        
        Verifies that agent state, context variables, and execution metadata
        remain completely isolated between different user executions.
        """
        logger.info("🧪 Starting supervisor agent state isolation test")
        
        # Create two user sessions with different contexts
        user_sessions = await self._create_isolated_user_sessions(count=2)
        self.assertEqual(len(user_sessions), 2, "Need exactly 2 user sessions for state isolation test")
        
        session_a, session_b = user_sessions
        
        # Define different execution contexts
        context_a = {
            "user_request": "Optimize database performance for production environment",
            "environment": "production",
            "priority": "high",
            "sensitive_token": f"PROD_TOKEN_{session_a.user_id}_{int(time.time())}"
        }
        
        context_b = {
            "user_request": "Generate development testing report for staging",
            "environment": "staging", 
            "priority": "low",
            "sensitive_token": f"STAGING_TOKEN_{session_b.user_id}_{int(time.time())}"
        }
        
        # Execute requests sequentially with state isolation monitoring
        result_a = await self._execute_supervisor_request_with_state_monitoring(
            session=session_a,
            context=context_a,
            isolation_check="context_a_only"
        )
        
        # Verify first execution succeeded
        self.assertTrue(result_a.get("success", False), 
                       f"First supervisor execution failed: {result_a.get('error', 'Unknown error')}")
        
        result_b = await self._execute_supervisor_request_with_state_monitoring(
            session=session_b,
            context=context_b,
            isolation_check="context_b_only"
        )
        
        # Verify second execution succeeded
        self.assertTrue(result_b.get("success", False),
                       f"Second supervisor execution failed: {result_b.get('error', 'Unknown error')}")
        
        # Critical isolation verification
        await self._verify_state_isolation_between_executions(
            result_a=result_a,
            result_b=result_b,
            context_a=context_a,
            context_b=context_b
        )
        
        logger.info("✅ Supervisor agent state isolation test completed successfully")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.supervisor_orchestration
    @pytest.mark.timeout(300)  # 5 minutes for comprehensive testing
    async def test_supervisor_sub_agent_isolation(self):
        """
        Test that Supervisor Agent's sub-agent orchestration maintains isolation.
        
        Verifies that when the Supervisor orchestrates multiple sub-agents
        (triage, data, optimization, etc.), each user's execution remains
        completely isolated from other users' sub-agent executions.
        """
        logger.info("🧪 Starting supervisor sub-agent isolation test")
        
        # Create user sessions for sub-agent isolation testing
        user_sessions = await self._create_isolated_user_sessions(count=3)
        self.assertGreaterEqual(len(user_sessions), 2, 
                               "Need at least 2 user sessions for sub-agent isolation testing")
        
        # Define complex requests that trigger multiple sub-agents
        complex_requests = [
            {
                "user_request": f"Complete analysis: triage urgent issues, gather performance data, "
                              f"optimize configurations, and generate action plan for user {session.user_id}",
                "expected_sub_agents": ["triage", "data", "optimization", "actions", "reporting"],
                "user_context": f"urgent_analysis_{session.user_id}",
                "tracking_token": f"COMPLEX_REQ_{session.user_id}_{int(time.time())}"
            }
            for session in user_sessions
        ]
        
        # Execute complex requests that trigger sub-agent orchestration
        orchestration_tasks = []
        for i, session in enumerate(user_sessions):
            task = asyncio.create_task(
                self._execute_complex_supervisor_orchestration(
                    session=session,
                    request_data=complex_requests[i],
                    monitor_sub_agents=True
                )
            )
            orchestration_tasks.append(task)
        
        # Wait for all orchestrations to complete
        orchestration_results = await asyncio.gather(*orchestration_tasks, return_exceptions=True)
        
        # Analyze orchestration results
        successful_orchestrations = [
            r for r in orchestration_results 
            if isinstance(r, dict) and r.get("orchestration_completed", False)
        ]
        
        # Verify minimum successful orchestrations
        self.assertGreaterEqual(len(successful_orchestrations), len(user_sessions) * 0.7,
                               f"Too few successful orchestrations: {len(successful_orchestrations)}/{len(user_sessions)}")
        
        # Verify sub-agent isolation across orchestrations
        await self._verify_sub_agent_isolation(successful_orchestrations, complex_requests)
        
        # Verify no cross-contamination in sub-agent results
        await self._verify_sub_agent_result_isolation(successful_orchestrations)
        
        logger.info(f"✅ Supervisor sub-agent isolation test completed: "
                   f"{len(successful_orchestrations)} successful orchestrations")

    # === Helper Methods ===

    async def _create_isolated_user_sessions(self, count: int) -> List[IsolatedUserSession]:
        """Create multiple isolated user sessions for testing."""
        sessions = []
        
        for i in range(count):
            # Create unique user identity
            user_id = f"isolation_test_user_{i}_{uuid.uuid4().hex[:8]}"
            email = f"{user_id}@test.netra.ai"
            
            # Create auth helper for this user
            auth_helper = E2EWebSocketAuthHelper(
                config=self.auth_config,
                environment=self.environment
            )
            
            # Generate JWT token for this user
            jwt_token = auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=email,
                permissions=["read", "write", "agent_execution"]
            )
            
            # Establish WebSocket connection
            websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
            
            # Create session object
            session = IsolatedUserSession(
                user_id=user_id,
                email=email,
                jwt_token=jwt_token,
                websocket=websocket,
                auth_helper=auth_helper,
                session_data={
                    "created_at": time.time(),
                    "isolation_id": f"iso_{i}_{int(time.time())}"
                }
            )
            
            sessions.append(session)
            logger.info(f"Created isolated user session {i+1}/{count}: {user_id}")
        
        return sessions

    async def _execute_supervisor_request_with_isolation_monitoring(
        self, 
        session: IsolatedUserSession, 
        request_data: Dict[str, Any],
        test_duration: float
    ) -> Dict[str, Any]:
        """Execute supervisor request with active isolation monitoring."""
        
        start_time = time.time()
        messages_sent = 0
        responses_received = []
        isolation_violations = []
        
        try:
            # Send supervisor execution request
            supervisor_request = {
                "type": "supervisor_execute",
                "user_id": session.user_id,
                "request_id": f"req_{session.user_id}_{int(time.time())}",
                "user_request": request_data["user_request"],
                "expected_context": request_data["expected_context"],
                "sensitive_data": request_data["sensitive_data"],
                "isolation_monitoring": True,
                "timestamp": time.time()
            }
            
            await session.websocket.send(json.dumps(supervisor_request))
            messages_sent += 1
            
            # Monitor responses with isolation checking
            end_time = start_time + test_duration
            while time.time() < end_time:
                try:
                    # Receive response with timeout
                    response_raw = await asyncio.wait_for(
                        session.websocket.recv(), 
                        timeout=self.isolation_check_interval
                    )
                    
                    response = json.loads(response_raw)
                    responses_received.append(response)
                    
                    # Check for isolation violations in response
                    violation = self._check_response_for_isolation_violations(
                        response, 
                        session.user_id, 
                        request_data["sensitive_data"]
                    )
                    if violation:
                        isolation_violations.append(violation)
                    
                    # Check for completion
                    if response.get("type") == "agent_completed" and response.get("agent") == "Supervisor":
                        logger.info(f"Supervisor execution completed for user {session.user_id}")
                        break
                        
                except asyncio.TimeoutError:
                    # Timeout is expected for monitoring loop
                    continue
            
            execution_time = time.time() - start_time
            
            return {
                "success": len(isolation_violations) == 0,
                "user_id": session.user_id,
                "execution_time": execution_time,
                "messages_sent": messages_sent,
                "responses_received": len(responses_received),
                "isolation_violations": isolation_violations,
                "responses": responses_received,
                "test_data": request_data
            }
            
        except Exception as e:
            logger.error(f"Supervisor request execution failed for user {session.user_id}: {e}")
            return {
                "success": False,
                "user_id": session.user_id,
                "error": str(e),
                "isolation_violations": isolation_violations
            }

    async def _execute_supervisor_request_with_state_monitoring(
        self,
        session: IsolatedUserSession,
        context: Dict[str, Any],
        isolation_check: str
    ) -> Dict[str, Any]:
        """Execute supervisor request with state isolation monitoring."""
        
        try:
            # Send state-monitored supervisor request
            request = {
                "type": "supervisor_execute_with_state_monitoring",
                "user_id": session.user_id,
                "request_id": f"state_req_{session.user_id}_{int(time.time())}",
                "context": context,
                "isolation_check": isolation_check,
                "state_monitoring": True,
                "timestamp": time.time()
            }
            
            await session.websocket.send(json.dumps(request))
            
            # Wait for completion with state monitoring
            completion_timeout = 90.0  # 1.5 minutes
            start_time = time.time()
            state_snapshots = []
            
            while time.time() - start_time < completion_timeout:
                response_raw = await asyncio.wait_for(session.websocket.recv(), timeout=5.0)
                response = json.loads(response_raw)
                
                # Capture state snapshots for analysis
                if response.get("type") == "agent_state_snapshot":
                    state_snapshots.append(response)
                
                # Check for completion
                if response.get("type") == "agent_completed":
                    return {
                        "success": True,
                        "user_id": session.user_id,
                        "context": context,
                        "state_snapshots": state_snapshots,
                        "completion_response": response,
                        "execution_time": time.time() - start_time
                    }
            
            # Timeout case
            return {
                "success": False,
                "user_id": session.user_id,
                "error": "State monitoring timeout",
                "state_snapshots": state_snapshots
            }
            
        except Exception as e:
            logger.error(f"State monitoring execution failed for user {session.user_id}: {e}")
            return {
                "success": False,
                "user_id": session.user_id,
                "error": str(e)
            }

    async def _execute_complex_supervisor_orchestration(
        self,
        session: IsolatedUserSession,
        request_data: Dict[str, Any],
        monitor_sub_agents: bool = True
    ) -> Dict[str, Any]:
        """Execute complex supervisor orchestration with sub-agent monitoring."""
        
        try:
            # Send complex orchestration request
            request = {
                "type": "supervisor_complex_orchestration",
                "user_id": session.user_id,
                "request_id": f"complex_{session.user_id}_{int(time.time())}",
                "user_request": request_data["user_request"],
                "expected_sub_agents": request_data["expected_sub_agents"],
                "tracking_token": request_data["tracking_token"],
                "monitor_sub_agents": monitor_sub_agents,
                "timestamp": time.time()
            }
            
            await session.websocket.send(json.dumps(request))
            
            # Monitor orchestration progress
            start_time = time.time()
            orchestration_timeout = 120.0  # 2 minutes
            sub_agent_executions = []
            orchestration_steps = []
            
            while time.time() - start_time < orchestration_timeout:
                response_raw = await asyncio.wait_for(session.websocket.recv(), timeout=3.0)
                response = json.loads(response_raw)
                
                # Track sub-agent executions
                if response.get("type") in ["agent_started", "agent_completed"] and response.get("agent") != "Supervisor":
                    sub_agent_executions.append(response)
                
                # Track orchestration steps
                if response.get("type") == "orchestration_step":
                    orchestration_steps.append(response)
                
                # Check for orchestration completion
                if response.get("type") == "agent_completed" and response.get("agent") == "Supervisor":
                    return {
                        "orchestration_completed": True,
                        "user_id": session.user_id,
                        "sub_agent_executions": sub_agent_executions,
                        "orchestration_steps": orchestration_steps,
                        "completion_response": response,
                        "execution_time": time.time() - start_time,
                        "tracking_token": request_data["tracking_token"]
                    }
            
            # Timeout case
            return {
                "orchestration_completed": False,
                "user_id": session.user_id,
                "error": "Orchestration timeout",
                "sub_agent_executions": sub_agent_executions,
                "orchestration_steps": orchestration_steps,
                "partial_completion": len(orchestration_steps) > 0
            }
            
        except Exception as e:
            logger.error(f"Complex orchestration failed for user {session.user_id}: {e}")
            return {
                "orchestration_completed": False,
                "user_id": session.user_id,
                "error": str(e)
            }

    def _check_response_for_isolation_violations(
        self, 
        response: Dict[str, Any], 
        expected_user_id: str, 
        expected_sensitive_data: str
    ) -> Optional[Dict[str, Any]]:
        """Check response for user isolation violations."""
        
        violations = []
        
        # Check user ID consistency
        response_user_id = response.get("user_id")
        if response_user_id and response_user_id != expected_user_id:
            violations.append({
                "type": "user_id_mismatch",
                "expected": expected_user_id,
                "actual": response_user_id
            })
        
        # Check for foreign sensitive data
        response_text = json.dumps(response).lower()
        if expected_sensitive_data.lower() not in response_text:
            # This is expected - we don't want to see our sensitive data
            pass
        
        # Check for foreign user data in response
        # Look for other user IDs that shouldn't be present
        if "isolation_test_user_" in response_text:
            # Extract any user IDs found
            import re
            found_user_ids = re.findall(r'isolation_test_user_\d+_[a-f0-9]{8}', response_text)
            foreign_user_ids = [uid for uid in found_user_ids if uid != expected_user_id]
            
            if foreign_user_ids:
                violations.append({
                    "type": "foreign_user_data",
                    "expected_user": expected_user_id,
                    "foreign_users": foreign_user_ids
                })
        
        return {"violations": violations, "response_type": response.get("type")} if violations else None

    async def _verify_no_cross_user_contamination(
        self, 
        results: List[Dict[str, Any]], 
        user_requests: List[Dict[str, Any]]
    ) -> None:
        """Verify no cross-user data contamination across results."""
        
        # Create mapping of user_id -> expected data
        user_data_map = {}
        for i, result in enumerate(results):
            user_id = result.get("user_id")
            if user_id and i < len(user_requests):
                user_data_map[user_id] = user_requests[i]
        
        # Check each result for contamination
        contamination_found = []
        
        for result in results:
            user_id = result.get("user_id")
            if not user_id:
                continue
                
            result_text = json.dumps(result).lower()
            
            # Check for other users' sensitive data
            for other_user_id, other_data in user_data_map.items():
                if other_user_id != user_id:
                    other_sensitive = other_data.get("sensitive_data", "").lower()
                    if other_sensitive and other_sensitive in result_text:
                        contamination_found.append({
                            "victim_user": user_id,
                            "contaminated_with": other_user_id,
                            "sensitive_data_leaked": other_data["sensitive_data"]
                        })
        
        self.assertEqual(len(contamination_found), 0, 
                        f"Cross-user contamination detected: {contamination_found}")

    async def _verify_supervisor_context_isolation(self, results: List[Dict[str, Any]]) -> None:
        """Verify supervisor agent context isolation across results."""
        
        context_conflicts = []
        
        # Extract execution contexts from results
        contexts = []
        for result in results:
            user_id = result.get("user_id")
            responses = result.get("responses", [])
            
            # Extract context information from responses
            for response in responses:
                if response.get("type") == "agent_thinking" and response.get("agent") == "Supervisor":
                    contexts.append({
                        "user_id": user_id,
                        "reasoning": response.get("reasoning", ""),
                        "context": response.get("context", {}),
                        "step_number": response.get("step_number")
                    })
        
        # Check for context bleeding between users
        for i, context_a in enumerate(contexts):
            for j, context_b in enumerate(contexts[i+1:], i+1):
                if context_a["user_id"] != context_b["user_id"]:
                    # Check if context_a contains references to context_b's user
                    reasoning_a = context_a["reasoning"].lower()
                    user_b_id = context_b["user_id"].lower()
                    
                    if user_b_id in reasoning_a:
                        context_conflicts.append({
                            "user_a": context_a["user_id"],
                            "user_b": context_b["user_id"],
                            "conflict_type": "user_id_in_reasoning",
                            "reasoning": context_a["reasoning"]
                        })
        
        self.assertEqual(len(context_conflicts), 0,
                        f"Supervisor context isolation violations: {context_conflicts}")

    async def _verify_state_isolation_between_executions(
        self,
        result_a: Dict[str, Any],
        result_b: Dict[str, Any], 
        context_a: Dict[str, Any],
        context_b: Dict[str, Any]
    ) -> None:
        """Verify state isolation between two sequential executions."""
        
        # Verify that result_a doesn't contain context_b data
        result_a_text = json.dumps(result_a).lower()
        context_b_sensitive = context_b["sensitive_token"].lower()
        
        self.assertNotIn(context_b_sensitive, result_a_text,
                        "Result A contains context B sensitive data - state isolation failed")
        
        # Verify that result_b doesn't contain context_a data
        result_b_text = json.dumps(result_b).lower()
        context_a_sensitive = context_a["sensitive_token"].lower()
        
        self.assertNotIn(context_a_sensitive, result_b_text,
                        "Result B contains context A sensitive data - state isolation failed")
        
        # Verify different environments are properly isolated
        if context_a["environment"] != context_b["environment"]:
            self.assertNotIn(context_a["environment"], result_b_text,
                           f"Environment isolation failed: {context_a['environment']} found in result B")
            self.assertNotIn(context_b["environment"], result_a_text,
                           f"Environment isolation failed: {context_b['environment']} found in result A")

    async def _verify_sub_agent_isolation(
        self, 
        orchestration_results: List[Dict[str, Any]], 
        request_data: List[Dict[str, Any]]
    ) -> None:
        """Verify sub-agent isolation across orchestrations."""
        
        isolation_violations = []
        
        # Create mapping of user -> tracking tokens
        user_tokens = {}
        for i, result in enumerate(orchestration_results):
            user_id = result.get("user_id")
            if user_id and i < len(request_data):
                user_tokens[user_id] = request_data[i]["tracking_token"]
        
        # Check each orchestration's sub-agent executions for contamination
        for result in orchestration_results:
            user_id = result.get("user_id")
            sub_agent_executions = result.get("sub_agent_executions", [])
            
            # Check each sub-agent execution
            for execution in sub_agent_executions:
                execution_text = json.dumps(execution).lower()
                
                # Look for other users' tracking tokens
                for other_user, other_token in user_tokens.items():
                    if other_user != user_id and other_token.lower() in execution_text:
                        isolation_violations.append({
                            "user_id": user_id,
                            "agent": execution.get("agent"),
                            "contaminated_with": other_user,
                            "foreign_token": other_token
                        })
        
        self.assertEqual(len(isolation_violations), 0,
                        f"Sub-agent isolation violations detected: {isolation_violations}")

    async def _verify_sub_agent_result_isolation(self, orchestration_results: List[Dict[str, Any]]) -> None:
        """Verify that sub-agent results don't leak between orchestrations."""
        
        result_leaks = []
        
        # Extract all sub-agent results
        all_sub_results = []
        for result in orchestration_results:
            user_id = result.get("user_id")
            sub_executions = result.get("sub_agent_executions", [])
            
            for execution in sub_executions:
                if execution.get("type") == "agent_completed":
                    all_sub_results.append({
                        "user_id": user_id,
                        "agent": execution.get("agent"),
                        "result": execution.get("result", {}),
                        "execution": execution
                    })
        
        # Check for result contamination
        for i, sub_result_a in enumerate(all_sub_results):
            for j, sub_result_b in enumerate(all_sub_results[i+1:], i+1):
                if sub_result_a["user_id"] != sub_result_b["user_id"]:
                    # Check if result A contains user B's ID
                    result_a_text = json.dumps(sub_result_a["result"]).lower()
                    user_b_id = sub_result_b["user_id"].lower()
                    
                    if user_b_id in result_a_text:
                        result_leaks.append({
                            "agent_a": sub_result_a["agent"],
                            "user_a": sub_result_a["user_id"],
                            "agent_b": sub_result_b["agent"], 
                            "user_b": sub_result_b["user_id"],
                            "leak_type": "user_id_in_result"
                        })
        
        self.assertEqual(len(result_leaks), 0,
                        f"Sub-agent result isolation violations: {result_leaks}")

    async def tearDown(self):
        """Clean up test resources."""
        logger.info("Cleaning up Supervisor Multi-User Isolation test resources")
        # WebSocket connections will be closed automatically
        await super().tearDown() if hasattr(super(), 'tearDown') else None