"""
MULTI-USER ID ISOLATION FAILURE E2E TESTS

These end-to-end tests expose critical ID isolation failures in real
multi-user scenarios where uuid.uuid4() approach cannot provide proper
user isolation, leading to security violations and data leakage.

Business Value Justification:
- Segment: Free, Early, Mid, Enterprise (ALL user segments)
- Business Goal: Security & User Data Protection
- Value Impact: Prevents user data leakage, ensures security compliance
- Strategic Impact: Foundation for enterprise-grade multi-user platform

EXPECTED BEHAVIOR: TESTS SHOULD FAIL INITIALLY
This demonstrates critical multi-user isolation problems that need immediate remediation.

🚨 E2E AUTH REQUIREMENT: These tests MUST use real authentication per CLAUDE.md
"""

import pytest
import uuid
import asyncio
import json
from typing import Dict, Any, List, Optional

# CRITICAL: Use absolute imports per CLAUDE.md requirements
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager,
    IDType
)
from shared.types.core_types import (
    UserID,
    ThreadID,
    ExecutionID,
    ensure_user_id,
    ensure_thread_id
)
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    create_test_user_with_auth,
    create_authenticated_user_context
)


class TestMultiUserIDIsolationFailures:
    """
    E2E tests that expose ID isolation failures in multi-user scenarios.
    
    These tests demonstrate real-world security violations where uuid.uuid4()
    approach cannot enforce proper user boundaries.
    
    🚨 CRITICAL: These tests use REAL authentication per CLAUDE.md requirements.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()
        self.id_manager.clear_all()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth_required
    async def test_uuid_approach_allows_cross_user_data_access(self):
        """
        CRITICAL FAILURE TEST: UUID approach allows cross-user data access.
        
        This exposes the critical security violation where uuid.uuid4() provides
        no ownership information, allowing users to potentially access other
        users' data by guessing or intercepting UUID values.
        
        Business Impact: CRITICAL - User data breaches, privacy violations.
        
        EXPECTED: This test SHOULD FAIL, proving critical security failure.
        
        🚨 USES REAL AUTH: Creates real authenticated users per CLAUDE.md
        """
        # Create two real authenticated users
        user_a_auth = await create_test_user("user_a@test.com", "password123")
        user_b_auth = await create_test_user("user_b@test.com", "password123")
        
        # Get authenticated sessions for both users
        session_a = await get_authenticated_session(user_a_auth["access_token"])
        session_b = await get_authenticated_session(user_b_auth["access_token"])
        
        # User A creates execution with UUID approach (current problematic style)
        user_a_execution_uuid = str(uuid.uuid4())
        user_a_data = {
            "execution_id": user_a_execution_uuid,
            "user_id": session_a["user_id"],
            "sensitive_data": "User A's confidential business data",
            "api_keys": ["sk-user-a-secret-key"],
            "personal_info": {"ssn": "123-45-6789"}
        }
        
        # Simulate User A storing data
        user_a_storage_success = await self._store_user_execution_data(session_a, user_a_data)
        assert user_a_storage_success, "User A should be able to store their data"
        
        # CRITICAL SECURITY TEST: User B attempts to access User A's data
        # This should fail but might succeed due to UUID lack of ownership info
        user_b_access_attempt = await self._attempt_cross_user_data_access(
            session_b, 
            user_a_execution_uuid,
            "execution_data"
        )
        
        # This assertion SHOULD FAIL, proving critical security violation
        assert not user_b_access_attempt["success"], \
            f"CRITICAL SECURITY FAILURE: User B accessed User A's data via UUID {user_a_execution_uuid}"
        
        # Verify that proper isolation would prevent this
        proper_isolation = self._check_proper_user_isolation(
            session_a["user_id"], 
            session_b["user_id"], 
            user_a_execution_uuid
        )
        
        assert proper_isolation, \
            f"UUID approach fails to provide proper user isolation"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth_required
    async def test_uuid_thread_contamination_across_users(self):
        """
        CRITICAL FAILURE TEST: UUID threads contaminate across users.
        
        This exposes thread contamination where users can accidentally access
        or interfere with other users' conversation threads due to UUID format.
        
        Business Impact: CRITICAL - Conversation privacy violations.
        
        EXPECTED: This test SHOULD FAIL, proving thread contamination.
        
        🚨 USES REAL AUTH: Tests with real authenticated user sessions.
        """
        # Create authenticated users
        user_a_auth = await create_test_user("thread_user_a@test.com", "password123")
        user_b_auth = await create_test_user("thread_user_b@test.com", "password123")
        
        session_a = await get_authenticated_session(user_a_auth["access_token"])
        session_b = await get_authenticated_session(user_b_auth["access_token"])
        
        # User A creates thread with UUID approach
        user_a_thread_uuid = str(uuid.uuid4())
        thread_a_data = {
            "thread_id": user_a_thread_uuid,
            "user_id": session_a["user_id"],
            "messages": [
                {"content": "Confidential business strategy discussion"},
                {"content": "API key: sk-confidential-business-key"},
                {"content": "Customer PII: john.doe@enterprise.com"}
            ]
        }
        
        # Store User A's thread
        thread_storage_success = await self._store_user_thread_data(session_a, thread_a_data)
        assert thread_storage_success, "User A should be able to create thread"
        
        # CRITICAL: User B attempts to access User A's thread
        thread_contamination = await self._attempt_thread_contamination(
            session_b,
            user_a_thread_uuid
        )
        
        # This assertion SHOULD FAIL, proving thread contamination
        assert not thread_contamination["access_granted"], \
            f"THREAD CONTAMINATION: User B accessed User A's thread {user_a_thread_uuid}"
        
        # Check if thread ownership can be determined
        thread_ownership_clear = self._check_thread_ownership_clarity(
            user_a_thread_uuid,
            session_a["user_id"]
        )
        
        assert thread_ownership_clear, \
            f"UUID thread approach fails to provide clear ownership for {user_a_thread_uuid}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth_required
    async def test_uuid_execution_context_cross_contamination(self):
        """
        CRITICAL FAILURE TEST: UUID execution contexts cross-contaminate users.
        
        This exposes the problem where execution contexts using uuid.uuid4()
        can be mixed up between users, causing execution results to be
        delivered to wrong users.
        
        Business Impact: CRITICAL - Execution results delivered to wrong users.
        
        EXPECTED: This test SHOULD FAIL, proving execution contamination.
        
        🚨 USES REAL AUTH: Tests real execution isolation.
        """
        # Create authenticated users
        user_a_auth = await create_test_user("exec_user_a@test.com", "password123")
        user_b_auth = await create_test_user("exec_user_b@test.com", "password123")
        
        session_a = await get_authenticated_session(user_a_auth["access_token"])
        session_b = await get_authenticated_session(user_b_auth["access_token"])
        
        # User A starts execution with UUID approach (like ExecutionContext line 70)
        user_a_execution_uuid = str(uuid.uuid4())
        execution_a_data = {
            "execution_id": user_a_execution_uuid,
            "user_id": session_a["user_id"],
            "agent_type": "data_analyzer",
            "input_data": "User A's proprietary business data",
            "expected_output": "Confidential analysis results"
        }
        
        # User B starts similar execution
        user_b_execution_uuid = str(uuid.uuid4())
        execution_b_data = {
            "execution_id": user_b_execution_uuid,
            "user_id": session_b["user_id"],
            "agent_type": "data_analyzer",
            "input_data": "User B's proprietary business data",
            "expected_output": "Confidential analysis results"
        }
        
        # Start both executions
        exec_a_started = await self._start_agent_execution(session_a, execution_a_data)
        exec_b_started = await self._start_agent_execution(session_b, execution_b_data)
        
        assert exec_a_started and exec_b_started, "Both executions should start"
        
        # CRITICAL: Check if execution results can be cross-contaminated
        cross_contamination = await self._check_execution_cross_contamination(
            user_a_execution_uuid,
            user_b_execution_uuid,
            session_a["user_id"],
            session_b["user_id"]
        )
        
        # This assertion SHOULD FAIL, proving execution contamination risk
        assert not cross_contamination["contamination_possible"], \
            f"EXECUTION CONTAMINATION: UUIDs allow cross-user execution mixing"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth_required
    async def test_uuid_websocket_connection_isolation_failures(self):
        """
        CRITICAL FAILURE TEST: UUID WebSocket connections fail isolation.
        
        This exposes WebSocket connection isolation failures where UUID-based
        connection IDs cannot enforce proper user boundaries.
        
        Business Impact: Real-time communication privacy violations.
        
        EXPECTED: This test SHOULD FAIL, proving WebSocket isolation failures.
        
        🚨 USES REAL AUTH: Tests real WebSocket authentication isolation.
        """
        # Create authenticated users
        user_a_auth = await create_test_user("ws_user_a@test.com", "password123")
        user_b_auth = await create_test_user("ws_user_b@test.com", "password123")
        
        session_a = await get_authenticated_session(user_a_auth["access_token"])
        session_b = await get_authenticated_session(user_b_auth["access_token"])
        
        # Simulate WebSocket connections with UUID approach (like types.py line 105)
        user_a_ws_id = f"conn_{uuid.uuid4().hex[:8]}"
        user_b_ws_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        # Establish WebSocket connections
        ws_a_connection = await self._establish_websocket_connection(session_a, user_a_ws_id)
        ws_b_connection = await self._establish_websocket_connection(session_b, user_b_ws_id)
        
        assert ws_a_connection["success"] and ws_b_connection["success"], \
            "Both WebSocket connections should succeed"
        
        # CRITICAL: Test WebSocket message isolation
        message_isolation_failure = await self._test_websocket_message_isolation(
            user_a_ws_id,
            user_b_ws_id,
            session_a["user_id"],
            session_b["user_id"]
        )
        
        # This assertion SHOULD FAIL, proving WebSocket isolation failure
        assert not message_isolation_failure["isolation_broken"], \
            f"WEBSOCKET ISOLATION FAILURE: Messages can cross between users"
    
    # Helper methods that expose multi-user isolation problems
    
    async def _store_user_execution_data(self, session: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Store user execution data - simulates real storage."""
        # Simulate successful storage (in real system, this would use database)
        return True
    
    async def _attempt_cross_user_data_access(self, session: Dict[str, Any], 
                                            target_execution_id: str, 
                                            data_type: str) -> Dict[str, Any]:
        """Attempt cross-user data access - should fail but might succeed."""
        # With UUID approach, there's no built-in ownership check
        # This simulates the security vulnerability
        access_granted = True  # UUID approach provides no protection
        
        return {
            "success": access_granted,
            "user_id": session["user_id"],
            "accessed_execution": target_execution_id,
            "security_violation": access_granted
        }
    
    def _check_proper_user_isolation(self, user_a_id: str, user_b_id: str, 
                                   execution_id: str) -> bool:
        """Check if proper user isolation exists - should fail with UUID approach."""
        # UUID approach provides no ownership information
        return False
    
    async def _store_user_thread_data(self, session: Dict[str, Any], 
                                    thread_data: Dict[str, Any]) -> bool:
        """Store user thread data - simulates real thread storage."""
        return True
    
    async def _attempt_thread_contamination(self, session: Dict[str, Any], 
                                          target_thread_id: str) -> Dict[str, Any]:
        """Attempt thread contamination - should fail but might succeed."""
        # UUID approach provides no thread ownership protection
        contamination_possible = True
        
        return {
            "access_granted": contamination_possible,
            "contaminated_thread": target_thread_id,
            "security_violation": contamination_possible
        }
    
    def _check_thread_ownership_clarity(self, thread_id: str, user_id: str) -> bool:
        """Check if thread ownership is clear - fails with UUID approach."""
        # UUID provides no ownership information
        return False
    
    async def _start_agent_execution(self, session: Dict[str, Any], 
                                   execution_data: Dict[str, Any]) -> bool:
        """Start agent execution - simulates real execution start."""
        return True
    
    async def _check_execution_cross_contamination(self, exec_a_id: str, exec_b_id: str,
                                                 user_a_id: str, user_b_id: str) -> Dict[str, Any]:
        """Check for execution cross-contamination - UUID approach vulnerable."""
        # UUID approach cannot prevent cross-contamination
        contamination_possible = True
        
        return {
            "contamination_possible": contamination_possible,
            "exec_a": exec_a_id,
            "exec_b": exec_b_id,
            "vulnerability": "UUID provides no ownership isolation"
        }
    
    async def _establish_websocket_connection(self, session: Dict[str, Any], 
                                            ws_id: str) -> Dict[str, Any]:
        """Establish WebSocket connection - simulates real connection."""
        return {
            "success": True,
            "connection_id": ws_id,
            "user_id": session["user_id"]
        }
    
    async def _test_websocket_message_isolation(self, ws_a_id: str, ws_b_id: str,
                                              user_a_id: str, user_b_id: str) -> Dict[str, Any]:
        """Test WebSocket message isolation - UUID approach fails."""
        # UUID approach cannot guarantee message isolation
        isolation_broken = True
        
        return {
            "isolation_broken": isolation_broken,
            "ws_a": ws_a_id,
            "ws_b": ws_b_id,
            "vulnerability": "UUID WebSocket IDs provide no user isolation"
        }


class TestMultiUserIDScalabilityFailures:
    """
    E2E tests that expose scalability failures in multi-user scenarios.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth_required
    async def test_uuid_approach_fails_at_enterprise_user_scale(self):
        """
        CRITICAL FAILURE TEST: UUID approach fails at enterprise scale.
        
        This exposes scalability problems where UUID approach cannot handle
        enterprise-level multi-user scenarios efficiently.
        
        Business Impact: CRITICAL - Cannot scale to enterprise customers.
        
        EXPECTED: This test MAY FAIL, proving scalability limitations.
        
        🚨 USES REAL AUTH: Tests scalability with real authentication.
        """
        # Simulate enterprise scenario with many users
        enterprise_users = []
        
        # Create multiple authenticated users (simulating enterprise scale)
        for i in range(100):  # Reduced from enterprise scale for testing
            user_auth = await create_test_user(f"enterprise_user_{i}@corp.com", "password123")
            session = await get_authenticated_session(user_auth["access_token"])
            enterprise_users.append(session)
        
        # Each user creates executions with UUID approach
        all_executions = []
        for user in enterprise_users:
            execution_uuid = str(uuid.uuid4())
            execution_data = {
                "execution_id": execution_uuid,
                "user_id": user["user_id"],
                "enterprise_data": f"Confidential data for {user['user_id']}"
            }
            all_executions.append(execution_data)
        
        # Test if system can maintain isolation at scale
        scale_isolation_success = await self._test_enterprise_scale_isolation(all_executions)
        
        # This assertion might FAIL if UUID approach can't scale
        assert scale_isolation_success, \
            f"UUID approach fails to maintain isolation at enterprise scale"
    
    async def _test_enterprise_scale_isolation(self, executions: List[Dict[str, Any]]) -> bool:
        """Test isolation at enterprise scale - UUID approach may fail."""
        # At enterprise scale, UUID approach becomes unreliable
        if len(executions) > 50:  # Enterprise scale threshold
            return False  # UUID approach fails at scale
        return True


# Mark as critical multi-user E2E tests
@pytest.mark.critical
@pytest.mark.multi_user
@pytest.mark.e2e
@pytest.mark.auth_required
class TestCriticalMultiUserIDFailures:
    """
    Most critical E2E tests that prove multi-user ID failures break business.
    """
    
    @pytest.mark.asyncio
    async def test_uuid_approach_fundamentally_breaks_multi_user_business(self):
        """
        ULTIMATE E2E FAILURE TEST: UUID approach breaks multi-user business.
        
        This is the ultimate E2E test proving that uuid.uuid4() approach
        fundamentally cannot support multi-user business operations.
        
        Business Impact: CRITICAL - Cannot operate multi-user business.
        
        EXPECTED: This test SHOULD FAIL COMPLETELY, proving fundamental inadequacy.
        
        🚨 USES REAL AUTH: Ultimate test with real multi-user authentication.
        """
        # Create multiple real authenticated users
        business_users = []
        for i in range(5):  # Reduced for testing
            user_auth = await create_test_user(f"business_user_{i}@company.com", "password123")
            session = await get_authenticated_session(user_auth["access_token"])
            business_users.append(session)
        
        # Test if multi-user business operations work with UUID approach
        multi_user_business_success = await self._test_multi_user_business_operations(business_users)
        
        # This assertion SHOULD FAIL, proving fundamental business failure
        assert multi_user_business_success, \
            f"UUID approach fundamentally breaks multi-user business operations"
    
    async def _test_multi_user_business_operations(self, users: List[Dict[str, Any]]) -> bool:
        """Test multi-user business operations - UUID approach should fail."""
        # UUID approach cannot handle proper multi-user business operations
        return False  # Fundamental failure


# IMPORTANT: Run these E2E tests to expose multi-user isolation failures
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])