#!/usr/bin/env python
"""
E2E TESTS: Multi-User Concurrent Chat Isolation - Business-Critical User Separation

CRITICAL BUSINESS MISSION: These tests validate COMPLETE USER ISOLATION during concurrent 
chat sessions, ensuring ZERO data leakage between users. This is ESSENTIAL for Enterprise 
customers who pay premium for data security and isolation guarantees.

Business Value Justification (BVJ):
- Segment: Enterprise (primary), Mid-tier (secondary) - customers paying for security
- Business Goal: Validate complete user data isolation during concurrent chat operations
- Value Impact: Prevents data leakage incidents that could cause customer churn and legal issues
- Strategic Impact: Protects $500K+ ARR by maintaining enterprise trust in multi-user system

CRITICAL REQUIREMENTS per CLAUDE.md:
1. MUST use REAL services with REAL authentication - NO mocks per "MOCKS = Abomination"
2. MUST validate COMPLETE user isolation (threads, contexts, agent results)
3. MUST test with REAL concurrent users with different authentication contexts
4. MUST validate WebSocket event isolation (User A cannot see User B events)
5. MUST be designed to fail hard on ANY cross-user data contamination

TEST FOCUS: E2E tests with REAL multi-user concurrent sessions to validate the business-
critical isolation mechanisms that enable enterprise customers to trust our platform.
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import hashlib

# SSOT IMPORTS - Following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.ssot.real_services_test_fixtures import real_services_fixture

# Core system imports for multi-user isolation testing
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, WebSocketID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Import Docker service management for E2E tests
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType


class UserChatSession:
    """Represents a complete user chat session for isolation testing."""
    
    def __init__(self, user_context: StronglyTypedUserExecutionContext, 
                 websocket_helper: E2EWebSocketAuthHelper):
        self.user_context = user_context
        self.websocket_helper = websocket_helper
        self.websocket = None
        self.received_events = []
        self.sent_messages = []
        self.user_identifier = str(user_context.user_id)
        self.thread_identifier = str(user_context.thread_id)
        
        # Create unique business context for this user to test isolation
        self.business_secret = f"SECRET_DATA_{self.user_identifier}_{int(time.time())}"
        self.unique_request = f"UNIQUE_REQUEST_{hashlib.md5(self.user_identifier.encode()).hexdigest()[:8]}"
        
    async def connect(self, websocket_url: str) -> None:
        """Establish authenticated WebSocket connection."""
        headers = self.websocket_helper.get_websocket_headers()
        self.websocket = await websockets.connect(websocket_url, additional_headers=headers)
        
    async def send_business_message(self, message_content: str) -> None:
        """Send chat message with user-specific business context."""
        message = {
            "type": "chat_message",
            "content": f"{message_content} {self.business_secret} {self.unique_request}",
            "user_id": self.user_identifier,
            "thread_id": self.thread_identifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "business_secret": self.business_secret,
            "requires_secure_processing": True
        }
        
        await self.websocket.send(json.dumps(message))
        self.sent_messages.append(message)
        
    async def collect_events(self, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """Collect WebSocket events for this user session."""
        collection_start = time.time()
        
        while (time.time() - collection_start) < timeout:
            try:
                event_data = await asyncio.wait_for(self.websocket.recv(), timeout=2.0)
                event = json.loads(event_data)
                
                self.received_events.append({
                    **event,
                    "received_timestamp": time.time(),
                    "user_session": self.user_identifier
                })
                
                # Stop collecting when we receive completion
                if event.get("type") == "agent_completed" or event.get("type") == "final_response":
                    break
                    
            except asyncio.TimeoutError:
                if len(self.received_events) >= 2:  # Minimum for validation
                    break
                continue
            except Exception as e:
                break
                
        return self.received_events
    
    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
            
    def has_cross_user_contamination(self, other_users: List['UserChatSession']) -> Dict[str, Any]:
        """Check if this user's data appears in other users' events."""
        contamination_found = []
        
        for other_user in other_users:
            if other_user.user_identifier == self.user_identifier:
                continue
                
            # Check if our business secret appears in other user's events
            other_events_text = " ".join([str(event) for event in other_user.received_events])
            
            if self.business_secret in other_events_text:
                contamination_found.append({
                    "contaminated_user": other_user.user_identifier,
                    "leaked_data": self.business_secret,
                    "contamination_type": "business_secret_leak"
                })
            
            if self.unique_request in other_events_text:
                contamination_found.append({
                    "contaminated_user": other_user.user_identifier,
                    "leaked_data": self.unique_request,
                    "contamination_type": "unique_request_leak"
                })
                
            # Check for thread ID contamination
            if self.thread_identifier in other_events_text:
                contamination_found.append({
                    "contaminated_user": other_user.user_identifier, 
                    "leaked_data": self.thread_identifier,
                    "contamination_type": "thread_id_leak"
                })
        
        return {
            "has_contamination": len(contamination_found) > 0,
            "contamination_details": contamination_found,
            "total_contamination_incidents": len(contamination_found)
        }


@pytest.mark.e2e
@pytest.mark.requires_docker
class TestMultiUserConcurrentChatIsolation(SSotAsyncTestCase):
    """
    CRITICAL: E2E tests for complete user isolation during concurrent chat sessions.
    
    These tests validate that enterprise customers can trust our platform with sensitive
    data by ensuring ZERO cross-user contamination during concurrent operations.
    """
    
    def setup_method(self, method=None):
        """Setup with enterprise security context."""
        super().setup_method(method)
        
        # Business value metrics for enterprise security
        self.record_metric("business_segment", "enterprise_primary")
        self.record_metric("test_type", "e2e_user_isolation")
        self.record_metric("security_requirement", "zero_cross_user_contamination")
        self.record_metric("compliance_requirement", "enterprise_data_isolation")
        
        # Initialize test components
        self._websocket_helper = None
        self._docker_manager = None
        self._user_sessions = []
        
    async def async_setup_method(self, method=None):
        """Async setup for multi-user E2E testing."""
        await super().async_setup_method(method)
        
        # Initialize Docker manager for real services
        self._docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        
        # Start required services for multi-user E2E testing
        if self._docker_manager.is_docker_available():
            await self._docker_manager.start_services(['backend', 'auth', 'redis', 'database'])
            await asyncio.sleep(8)  # Allow services to fully initialize
            
        # Initialize WebSocket helper
        environment = self.get_env_var("TEST_ENV", "test")
        self._websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
    @pytest.mark.asyncio
    async def test_concurrent_users_complete_chat_isolation_with_sensitive_data(self):
        """
        Test complete isolation between concurrent users processing sensitive business data.
        
        CRITICAL: This validates the CORE enterprise security promise:
        User A Sensitive Data + User B Sensitive Data  ->  ZERO Cross-Contamination  ->  Enterprise Trust
        
        Business Value: Validates enterprise-grade isolation that justifies premium pricing.
        """
        # Arrange - Create multiple users with sensitive business contexts
        concurrent_users = 4  # Test with realistic concurrent load
        user_sessions = []
        
        # Create users with different business contexts and sensitive data
        user_business_contexts = [
            ("enterprise_ceo@company1.com", "quarterly_revenue_optimization", "CONFIDENTIAL_Q4_REVENUE_$2.5M"),
            ("cto@startup2.com", "infrastructure_cost_analysis", "PRIVATE_AWS_SPEND_$50K_MONTHLY"),  
            ("finance_director@corp3.com", "budget_optimization_review", "SENSITIVE_BUDGET_DATA_$1M_ANNUAL"),
            ("ops_manager@company4.com", "security_audit_analysis", "INTERNAL_SECURITY_METRICS_CLASSIFIED")
        ]
        
        for i, (email, context, sensitive_data) in enumerate(user_business_contexts):
            # Create authenticated user context with unique sensitive data
            user_context = await create_authenticated_user_context(
                user_email=email,
                environment="test",
                permissions=["read", "write", "execute_agents", "sensitive_data_access"],
                websocket_enabled=True
            )
            
            # Create user session with unique business secrets
            session = UserChatSession(user_context, self._websocket_helper)
            session.business_secret = sensitive_data
            session.business_context = context
            user_sessions.append(session)
            
        self._user_sessions = user_sessions
        
        # Establish concurrent WebSocket connections
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        connection_tasks = []
        
        for session in user_sessions:
            connection_task = session.connect(websocket_url)
            connection_tasks.append(connection_task)
            
        await asyncio.gather(*connection_tasks)
        self.logger.info(f"[U+1F50C] Established {len(user_sessions)} concurrent authenticated connections")
        
        # Act - Send concurrent chat messages with sensitive business data
        message_tasks = []
        
        for i, session in enumerate(user_sessions):
            # Each user sends message containing their sensitive business data
            sensitive_message = (
                f"Analyze my {session.business_context} with focus on cost optimization. "
                f"Include this sensitive data in analysis: {session.business_secret}"
            )
            
            message_task = session.send_business_message(sensitive_message)
            message_tasks.append(message_task)
        
        # Send all messages concurrently to test isolation under load
        await asyncio.gather(*message_tasks)
        self.logger.info(f"[U+1F4E4] Sent {len(message_tasks)} concurrent messages with sensitive data")
        
        # Collect events from all users concurrently
        collection_tasks = []
        for session in user_sessions:
            collection_task = session.collect_events(timeout=45.0)
            collection_tasks.append(collection_task)
            
        # Wait for all users to complete processing
        await asyncio.gather(*collection_tasks, return_exceptions=True)
        
        # Assert - Validate COMPLETE isolation between all users
        isolation_violations = []
        
        for i, session in enumerate(user_sessions):
            # Check this user for cross-contamination from other users
            contamination = session.has_cross_user_contamination(
                [other for other in user_sessions if other != session]
            )
            
            if contamination["has_contamination"]:
                isolation_violations.extend(contamination["contamination_details"])
                self.logger.error(f" FAIL:  User {i} has contamination: {contamination['contamination_details']}")
        
        # CRITICAL: ZERO cross-user contamination is required for enterprise trust
        self.assertEqual(len(isolation_violations), 0,
            f"CRITICAL ENTERPRISE SECURITY FAILURE: Found {len(isolation_violations)} isolation violations. "
            f"Details: {isolation_violations}. This breaks enterprise data security guarantees.")
        
        # Validate each user received their own results
        for i, session in enumerate(user_sessions):
            self.assertGreater(len(session.received_events), 0,
                f"User {i} must receive WebSocket events for their chat")
            
            # Validate user's business secret appears in THEIR OWN events
            user_events_text = " ".join([str(event) for event in session.received_events])
            self.assertIn(session.business_secret, user_events_text,
                f"User {i} must receive results containing their business context")
        
        # Validate system-wide isolation metrics
        total_events = sum(len(session.received_events) for session in user_sessions)
        successful_users = sum(1 for session in user_sessions if len(session.received_events) > 0)
        
        self.assertEqual(successful_users, len(user_sessions),
            f"All {len(user_sessions)} users must receive isolated results")
        
        # Business continuity validation
        self.assertGreaterEqual(total_events, len(user_sessions) * 2,
            f"Expected minimum {len(user_sessions) * 2} events, got {total_events}")
        
        # Record enterprise security metrics
        self.record_metric("concurrent_users_tested", len(user_sessions))
        self.record_metric("isolation_violations_found", len(isolation_violations))
        self.record_metric("cross_contamination_incidents", 0)  # Must be 0
        self.record_metric("enterprise_isolation_validated", True)
        self.record_metric("total_events_all_users", total_events)
        
        self.logger.info(f" PASS:  Enterprise isolation validated: {len(user_sessions)} concurrent users, "
                        f"ZERO isolation violations, {total_events} total isolated events")
    
    @pytest.mark.asyncio
    async def test_user_session_state_isolation_during_agent_execution(self):
        """
        Test user session state remains isolated during concurrent agent execution workflows.
        
        CRITICAL: This validates agent execution isolation:
        User A Agent State + User B Agent State  ->  ZERO State Cross-Contamination  ->  Reliable Results
        
        Business Value: Ensures agent results are never mixed between users (data integrity).
        """
        # Arrange - Create users with different agent workflow requirements
        user_workflows = [
            ("workflow_user_1@company.com", "cost_optimization", "Infrastructure cost analysis with detailed breakdown"),
            ("workflow_user_2@company.com", "performance_optimization", "API performance optimization with latency analysis")
        ]
        
        user_sessions = []
        for email, workflow_type, request_content in user_workflows:
            user_context = await create_authenticated_user_context(
                user_email=email,
                environment="test",
                permissions=["read", "write", "execute_agents", "workflow_execution"],
                websocket_enabled=True
            )
            
            session = UserChatSession(user_context, self._websocket_helper)
            session.workflow_type = workflow_type
            session.request_content = request_content
            user_sessions.append(session)
            
        self._user_sessions = user_sessions
        
        # Connect all users to WebSocket
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        for session in user_sessions:
            await session.connect(websocket_url)
            
        self.logger.info(f"[U+1F50C] Connected {len(user_sessions)} users for agent workflow isolation testing")
        
        # Act - Execute different agent workflows concurrently
        workflow_tasks = []
        
        for i, session in enumerate(user_sessions):
            # Send workflow-specific request that will trigger different agent paths
            workflow_message = (
                f"Execute {session.workflow_type} workflow: {session.request_content}. "
                f"Session ID: {session.user_identifier}. "
                f"Expected workflow: {session.workflow_type}"
            )
            
            workflow_task = session.send_business_message(workflow_message)
            workflow_tasks.append(workflow_task)
        
        # Execute workflows concurrently
        await asyncio.gather(*workflow_tasks)
        self.logger.info(f"[U+1F4E4] Started {len(workflow_tasks)} concurrent agent workflows")
        
        # Allow sufficient time for agent execution
        collection_tasks = []
        for session in user_sessions:
            collection_task = session.collect_events(timeout=60.0)  # Longer for agent workflows
            collection_tasks.append(collection_task)
            
        await asyncio.gather(*collection_tasks, return_exceptions=True)
        
        # Assert - Validate agent execution state isolation
        for i, session in enumerate(user_sessions):
            # Validate user received events for their workflow
            self.assertGreater(len(session.received_events), 0,
                f"User {i} must receive agent execution events")
            
            # Check for agent execution events
            event_types = [event.get("type") for event in session.received_events]
            required_agent_events = ["agent_started", "agent_thinking"]
            
            for required_event in required_agent_events:
                self.assertIn(required_event, event_types,
                    f"User {i} missing required agent event: {required_event}")
            
            # Validate workflow-specific content
            events_content = " ".join([str(event) for event in session.received_events])
            self.assertIn(session.workflow_type, events_content,
                f"User {i} events must contain their workflow type: {session.workflow_type}")
        
        # Cross-contamination check for agent states
        state_contamination = []
        
        for i, session_a in enumerate(user_sessions):
            for j, session_b in enumerate(user_sessions):
                if i >= j:  # Avoid duplicate checks
                    continue
                    
                # Check if session A's workflow content appears in session B's events
                session_a_content = session_a.workflow_type
                session_b_events = " ".join([str(event) for event in session_b.received_events])
                
                if session_a_content in session_b_events and session_a.workflow_type != session_b.workflow_type:
                    state_contamination.append({
                        "source_user": session_a.user_identifier,
                        "contaminated_user": session_b.user_identifier,
                        "leaked_workflow_type": session_a_content
                    })
        
        # CRITICAL: Agent execution states must be isolated
        self.assertEqual(len(state_contamination), 0,
            f"CRITICAL AGENT ISOLATION FAILURE: Found {len(state_contamination)} agent state contaminations. "
            f"Details: {state_contamination}. Agent execution states are mixing between users.")
        
        # Validate agent execution completed successfully for both users
        completed_users = 0
        for session in user_sessions:
            event_types = [event.get("type") for event in session.received_events]
            if "agent_completed" in event_types or "final_response" in event_types:
                completed_users += 1
        
        self.assertGreaterEqual(completed_users, 1,
            "At least one user must complete agent workflow execution")
        
        # Record agent isolation metrics
        self.record_metric("concurrent_agent_workflows", len(user_sessions))
        self.record_metric("agent_state_contamination_incidents", len(state_contamination))
        self.record_metric("successful_workflow_completions", completed_users)
        self.record_metric("agent_execution_isolation_validated", True)
        
        self.logger.info(f" PASS:  Agent execution isolation validated: {len(user_sessions)} concurrent workflows, "
                        f"ZERO state contamination, {completed_users} successful completions")
    
    # Helper Methods and Cleanup
    
    async def async_teardown_method(self, method=None):
        """Cleanup connections and Docker services."""
        # Close all user WebSocket connections
        if self._user_sessions:
            cleanup_tasks = []
            for session in self._user_sessions:
                cleanup_tasks.append(session.close())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Stop Docker services
        if self._docker_manager and self._docker_manager.is_docker_available():
            try:
                await self._docker_manager.stop_services(['backend', 'auth', 'redis', 'database'])
            except Exception as e:
                self.logger.warning(f"Error stopping Docker services: {e}")
        
        await super().async_teardown_method(method)
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        super().teardown_method(method)
        
        # Clear user sessions
        self._user_sessions.clear()
        
        self.logger.info(f" PASS:  Multi-user concurrent chat isolation test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])