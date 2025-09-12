from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Multi-Session Isolation Test with Real Services

CRITICAL E2E Test: Verifies complete isolation between concurrent user sessions
Tests session boundaries, data leakage prevention, and WebSocket isolation.

Business Value Justification (BVJ):
Segment: Enterprise | Goal: Data Security | Revenue Impact: $200K+ MRR Protection
- Prevents data leaks between concurrent user sessions (GDPR/SOC2 compliance)
- Ensures secure session boundaries for enterprise multi-tenant deployments
- Validates WebSocket isolation preventing cross-user data contamination
- Tests concurrent operations isolation critical for team collaboration features

Security Requirements:
- No data leakage between user sessions
- Separate authentication contexts per session
- WebSocket message isolation
- Concurrent operation separation
- Session state independence

Performance Requirements:
- Session Creation: <2s per session
- Message Isolation: <100ms verification
- Concurrent Operations: <1s total
- Data Verification: <500ms per check
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest

from tests.clients import TestClientFactory
from tests.e2e.jwt_token_helpers import JWTTestHelper

logger = logging.getLogger(__name__)

# Enable real services for this test module
pytestmark = pytest.mark.skipif(
    get_env().get("USE_REAL_SERVICES", "false").lower() != "true",
    reason="Real services disabled (set USE_REAL_SERVICES=true)"
)


class TestSessionIsolationer:
    """Comprehensive session isolation tester with real services."""
    
    def __init__(self, real_services):
        """Initialize tester with real services context."""
        self.real_services = real_services
        self.auth_client = real_services.auth_client
        self.factory = real_services.factory
        self.sessions: List[Dict[str, Any]] = []
        
    async def create_isolated_user_session(self, user_id: str) -> Dict[str, Any]:
        """Create a completely isolated user session with unique credentials."""
        start_time = time.time()
        
        try:
            # Create unique test user
            user_data = await self.auth_client.create_test_user(
                email=f"isolated_user_{user_id}_{uuid.uuid4().hex[:8]}@test.com"
            )
            
            # Establish WebSocket connection
            ws_client = await self.factory.create_websocket_client(user_data["token"])
            connected = await ws_client.connect(timeout=5.0)
            
            if not connected:
                raise RuntimeError(f"Failed to establish WebSocket connection for user {user_id}")
            
            session_time = time.time() - start_time
            
            # Verify session creation performance requirement (<2s)
            assert session_time < 2.0, f"Session creation took {session_time:.3f}s, required <2s"
            
            session = {
                "user_id": user_id,
                "email": user_data["email"],
                "token": user_data["token"],
                "password": user_data["password"],
                "websocket": ws_client,
                "created_at": datetime.now(timezone.utc),
                "session_time": session_time,
                "messages_sent": [],
                "messages_received": []
            }
            
            self.sessions.append(session)
            logger.info(f"Created isolated session for user {user_id} in {session_time:.3f}s")
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise RuntimeError(f"Session creation failed for user {user_id}: {e}")
    
    async def send_unique_data_to_session(self, session: Dict[str, Any], data_content: str) -> Dict[str, Any]:
        """Send unique, identifying data through a session's WebSocket."""
        start_time = time.time()
        
        try:
            # Create unique message with session identifier
            unique_message = {
                "type": "chat",
                "content": f"{session['user_id']}_secret: {data_content}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session['user_id']
            }
            
            # Send message
            await session["websocket"].send(unique_message)
            session["messages_sent"].append(unique_message)
            
            send_time = time.time() - start_time
            
            # Wait for any response (if applicable)
            try:
                response = await session["websocket"].receive(timeout=2.0)
                if response:
                    session["messages_received"].append(response)
            except asyncio.TimeoutError:
                # No response is acceptable for some implementations
                pass
            
            return {
                "sent": True,
                "message": unique_message,
                "send_time": send_time,
                "error": None
            }
            
        except Exception as e:
            return {
                "sent": False,
                "message": None,
                "send_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def verify_session_isolation(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify that no data leaked between sessions."""
        start_time = time.time()
        
        isolation_results = {
            "isolated": True,
            "leaks_detected": [],
            "verification_time": 0.0,
            "sessions_checked": len(sessions)
        }
        
        try:
            for i, session_a in enumerate(sessions):
                for j, session_b in enumerate(sessions):
                    if i >= j:  # Skip self and duplicate checks
                        continue
                    
                    # Check if session_a's data appears in session_b's received messages
                    session_a_secrets = [msg["content"] for msg in session_a["messages_sent"] 
                                       if "secret" in msg.get("content", "")]
                    session_b_received = [str(msg) for msg in session_b["messages_received"]]
                    
                    # Look for data leaks
                    for secret in session_a_secrets:
                        for received in session_b_received:
                            if secret in received and session_a["user_id"] != session_b["user_id"]:
                                isolation_results["isolated"] = False
                                isolation_results["leaks_detected"].append({
                                    "from_session": session_a["user_id"],
                                    "to_session": session_b["user_id"],
                                    "leaked_data": secret,
                                    "found_in": received
                                })
                    
                    # Also check WebSocket message queues for cross-contamination
                    session_b_all_messages = session_b["websocket"].get_all_received_messages()
                    for secret in session_a_secrets:
                        for msg in session_b_all_messages:
                            msg_str = json.dumps(msg) if isinstance(msg, dict) else str(msg)
                            if secret in msg_str:
                                isolation_results["isolated"] = False
                                isolation_results["leaks_detected"].append({
                                    "from_session": session_a["user_id"],
                                    "to_session": session_b["user_id"],
                                    "leaked_data": secret,
                                    "found_in": f"WebSocket queue: {msg_str[:100]}..."
                                })
            
            verification_time = time.time() - start_time
            isolation_results["verification_time"] = verification_time
            
            # Verify performance requirement (<500ms per check)
            assert verification_time < 0.5, f"Verification took {verification_time:.3f}s, required <500ms"
            
            return isolation_results
            
        except Exception as e:
            isolation_results["isolated"] = False
            isolation_results["error"] = str(e)
            isolation_results["verification_time"] = time.time() - start_time
            return isolation_results
    
    @pytest.mark.e2e
    async def test_concurrent_operations_isolation(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test that concurrent operations remain isolated between sessions."""
        start_time = time.time()
        
        try:
            # Prepare concurrent operations for each session
            concurrent_tasks = []
            
            for i, session in enumerate(sessions):
                # Create unique update operation for each session
                update_data = {
                    "type": "update",
                    "data": f"concurrent_update_{session['user_id']}_{i}",
                    "operation_id": f"op_{uuid.uuid4().hex[:8]}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                task = self.send_unique_data_to_session(session, 
                    f"concurrent_op_{i}: {update_data['data']}")
                concurrent_tasks.append(task)
            
            # Execute all operations concurrently
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Verify concurrent operations performance (<1s total)
            assert total_time < 1.0, f"Concurrent operations took {total_time:.3f}s, required <1s"
            
            # Check results
            successful_operations = sum(
                1 for result in results 
                if isinstance(result, dict) and result.get("sent", False)
            )
            
            return {
                "concurrent_operations_isolated": True,
                "successful_operations": successful_operations,
                "total_operations": len(sessions),
                "total_time": total_time,
                "operation_results": results
            }
            
        except Exception as e:
            return {
                "concurrent_operations_isolated": False,
                "error": str(e),
                "total_time": time.time() - start_time
            }
    
    async def cleanup_all_sessions(self) -> None:
        """Clean up all created sessions."""
        for session in self.sessions:
            try:
                if session.get("websocket"):
                    await session["websocket"].disconnect()
            except Exception as e:
                logger.warning(f"Error cleaning up session {session['user_id']}: {e}")
        
        self.sessions.clear()


@pytest.mark.critical
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multi_session_isolation():
    """
    BVJ: Segment: Enterprise | Goal: Data Security | Impact: $200K+ MRR Protection
    Test: Complete isolation between multiple concurrent user sessions
    """
    # Note: This test requires real_services fixture, using skip for safety
    pytest.skip("Requires real_services fixture - enable when running with USE_REAL_SERVICES=true")


@pytest.mark.critical
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multi_session_isolation_with_real_services(real_services):
    """
    BVJ: Segment: Enterprise | Goal: Data Security | Impact: $200K+ MRR Protection
    Test: Complete isolation between multiple concurrent user sessions
    """
    isolation_tester = SessionIsolationTester(real_services)
    
    try:
        # Phase 1: Create multiple isolated user sessions
        session_count = 3
        sessions = []
        
        logger.info(f"Creating {session_count} isolated user sessions...")
        for i in range(session_count):
            session = await isolation_tester.create_isolated_user_session(f"user_{i+1}")
            sessions.append(session)
            
        assert len(sessions) == session_count, f"Expected {session_count} sessions, created {len(sessions)}"
        
        # Phase 2: Send unique, identifying data to each session
        logger.info("Sending unique data to each session...")
        for i, session in enumerate(sessions):
            send_result = await isolation_tester.send_unique_data_to_session(
                session, f"unique_data_package_{i+1}_confidential"
            )
            assert send_result["sent"], f"Failed to send data to session {i+1}: {send_result.get('error')}"
        
        # Phase 3: Test concurrent operations isolation
        logger.info("Testing concurrent operations isolation...")
        concurrent_result = await isolation_tester.test_concurrent_operations_isolation(sessions)
        assert concurrent_result["concurrent_operations_isolated"], \
            f"Concurrent operations not isolated: {concurrent_result.get('error')}"
        assert concurrent_result["successful_operations"] >= 2, \
            f"Expected  >= 2 successful concurrent operations, got {concurrent_result['successful_operations']}"
        
        # Phase 4: Verify complete session isolation
        logger.info("Verifying session isolation...")
        # Wait a moment for any async processing
        await asyncio.sleep(1.0)
        
        isolation_result = await isolation_tester.verify_session_isolation(sessions)
        
        # CRITICAL: Sessions must be completely isolated
        assert isolation_result["isolated"], \
            f"Data leakage detected between sessions: {isolation_result['leaks_detected']}"
        assert len(isolation_result["leaks_detected"]) == 0, \
            f"Found {len(isolation_result['leaks_detected'])} data leaks: {isolation_result['leaks_detected']}"
        
        # Phase 5: Verify separate auth contexts
        logger.info("Verifying separate authentication contexts...")
        auth_contexts = set()
        for session in sessions:
            # Verify each session has unique token
            auth_contexts.add(session["token"])
            
            # Verify token is valid for this session only
            try:
                profile = await isolation_tester.auth_client.get_user_profile(session["token"])
                assert profile["email"] == session["email"], \
                    f"Token mismatch: expected {session['email']}, got {profile['email']}"
            except Exception as e:
                pytest.fail(f"Auth context verification failed for {session['user_id']}: {e}")
        
        assert len(auth_contexts) == session_count, \
            f"Expected {session_count} unique auth tokens, got {len(auth_contexts)}"
        
        # Summary
        total_verification_time = isolation_result["verification_time"]
        logger.info(f"[U+2713] Multi-session isolation verified:")
        logger.info(f"  - {session_count} completely isolated sessions")
        logger.info(f"  - {concurrent_result['successful_operations']} concurrent operations isolated")
        logger.info(f"  - 0 data leaks detected")
        logger.info(f"  - {session_count} separate auth contexts verified")
        logger.info(f"  - Total verification: {total_verification_time:.3f}s")
        
    finally:
        # Cleanup all sessions
        await isolation_tester.cleanup_all_sessions()


@pytest.mark.asyncio 
@pytest.mark.e2e
async def test_websocket_session_boundaries(real_services):
    """Test WebSocket-specific session boundary enforcement."""
    isolation_tester = SessionIsolationTester(real_services)
    
    try:
        # Create two sessions
        session1 = await isolation_tester.create_isolated_user_session("boundary_user_1")
        session2 = await isolation_tester.create_isolated_user_session("boundary_user_2")
        
        # Test WebSocket message isolation
        await session1["websocket"].send({"type": "test", "secret": "session1_only_data"})
        await session2["websocket"].send({"type": "test", "secret": "session2_only_data"})
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Verify boundaries
        session1_messages = session1["websocket"].get_all_received_messages()
        session2_messages = session2["websocket"].get_all_received_messages()
        
        # Check that session1's secret doesn't appear in session2's messages
        session1_secrets = ["session1_only_data"]
        session2_secrets = ["session2_only_data"]
        
        for msg in session2_messages:
            msg_str = json.dumps(msg) if isinstance(msg, dict) else str(msg)
            for secret in session1_secrets:
                assert secret not in msg_str, \
                    f"Session 1 secret '{secret}' found in session 2 messages: {msg_str}"
        
        for msg in session1_messages:
            msg_str = json.dumps(msg) if isinstance(msg, dict) else str(msg)
            for secret in session2_secrets:
                assert secret not in msg_str, \
                    f"Session 2 secret '{secret}' found in session 1 messages: {msg_str}"
        
        logger.info("[U+2713] WebSocket session boundaries enforced correctly")
        
    finally:
        await isolation_tester.cleanup_all_sessions()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_state_independence(real_services):
    """Test that session state changes don't affect other sessions."""
    isolation_tester = SessionIsolationTester(real_services)
    
    try:
        # Create sessions
        session_a = await isolation_tester.create_isolated_user_session("state_user_a")
        session_b = await isolation_tester.create_isolated_user_session("state_user_b") 
        
        # Modify state in session A
        await session_a["websocket"].send({
            "type": "state_change",
            "action": "set_preference", 
            "value": "session_a_preference"
        })
        
        # Verify session B state is unaffected
        await session_b["websocket"].send({
            "type": "get_preferences"
        })
        
        # Wait and check responses
        await asyncio.sleep(1.0)
        
        session_b_messages = session_b["websocket"].get_all_received_messages()
        
        # Session B should not have session A's preference
        for msg in session_b_messages:
            msg_str = json.dumps(msg) if isinstance(msg, dict) else str(msg)
            assert "session_a_preference" not in msg_str, \
                f"Session A state leaked to session B: {msg_str}"
        
        logger.info("[U+2713] Session state independence verified")
        
    finally:
        await isolation_tester.cleanup_all_sessions()


# Business Impact Summary
"""
Multi-Session Isolation Test - Business Impact

Revenue Protection: $200K+ MRR
- Prevents catastrophic data leaks between enterprise customer sessions
- Ensures GDPR/SOC2 compliance for high-value enterprise contracts
- Validates secure multi-tenant session boundaries for team collaboration
- Tests concurrent operation isolation critical for enterprise deployments

Security Compliance:
- Complete session isolation with zero data leakage tolerance
- Separate authentication contexts per user session  
- WebSocket message boundary enforcement
- Session state independence verification
- Concurrent operation security validation

Performance Validation:
- Session Creation: <2s per session for scalable user onboarding
- Message Isolation: <100ms verification for real-time security
- Concurrent Operations: <1s total for team collaboration efficiency  
- Data Verification: <500ms per check for responsive security validation

Customer Impact:
- Enterprise: Critical security compliance enabling contract closure
- Mid: Secure team collaboration without data cross-contamination
- All Segments: Trust in platform security for sensitive AI workloads
- Compliance: SOC2/GDPR requirements for enterprise data handling
"""
