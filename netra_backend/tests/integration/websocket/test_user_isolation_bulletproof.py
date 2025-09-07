"""
Bulletproof User Context Isolation WebSocket Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Security and privacy foundation
- Business Goal: Ensure complete user isolation to maintain trust and regulatory compliance
- Value Impact: User isolation prevents data leaks and maintains customer confidence
- Strategic/Revenue Impact: Security breaches could destroy $500K+ ARR and company reputation

CRITICAL USER ISOLATION SCENARIOS:
1. User session isolation and context separation
2. Agent execution isolation between different users
3. Thread isolation and message privacy
4. Authentication context isolation and validation

CRITICAL REQUIREMENTS:
- NO MOCKS - Uses real WebSocket connections and real user isolation mechanisms
- Tests complete user context separation across all system layers
- Validates no cross-user data leakage or context bleeding
- Ensures proper authentication boundary enforcement
- Tests concurrent user scenarios with isolated agent executions
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import patch

import pytest
import websockets

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.fixtures.websocket_test_helpers import WebSocketTestSession
from shared.isolated_environment import get_env


class IsolationTestLLM:
    """
    Mock LLM for testing user isolation with user-specific responses.
    This is the ONLY acceptable mock per CLAUDE.md - external LLM APIs.
    """
    
    def __init__(self, user_identifier: str):
        self.user_identifier = user_identifier
        self.call_count = 0
    
    async def complete_async(self, messages, **kwargs):
        """Mock LLM with user-specific responses for isolation validation."""
        self.call_count += 1
        await asyncio.sleep(0.1)
        
        return {
            "content": f"Isolated response for user {self.user_identifier} (execution #{self.call_count}). This message validates user isolation and ensures no cross-user data leakage.",
            "usage": {"total_tokens": 100 + (self.call_count * 10)}
        }


class TestUserIsolationBulletproof(BaseIntegrationTest):
    """
    Bulletproof tests for user context isolation in WebSocket scenarios.
    
    CRITICAL: All tests use REAL WebSocket connections and REAL user isolation
    to validate production-quality user separation and privacy protection.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_user_isolation_test(self, real_services_fixture):
        """
        Set up bulletproof user isolation test environment.
        
        BVJ: Security Foundation - Ensures reliable user isolation validation
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_session_id = f"isolation_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services (CLAUDE.md requirement)
        assert real_services_fixture, "Real services required for user isolation tests"
        assert "backend" in real_services_fixture, "Real backend required for isolation testing"
        assert "db" in real_services_fixture, "Real database required for user context isolation"
        
        # Create multiple isolated test users
        self.isolated_users = {
            "alice": {
                "user_id": f"alice_{self.test_session_id}",
                "email": f"alice_{self.test_session_id}@isolation-test.com",
                "thread_ids": [f"alice_thread_1_{self.test_session_id}", f"alice_thread_2_{self.test_session_id}"],
                "sensitive_data": "Alice_Secret_Data_12345"
            },
            "bob": {
                "user_id": f"bob_{self.test_session_id}",
                "email": f"bob_{self.test_session_id}@isolation-test.com",
                "thread_ids": [f"bob_thread_1_{self.test_session_id}", f"bob_thread_2_{self.test_session_id}"],
                "sensitive_data": "Bob_Confidential_Info_67890"
            },
            "charlie": {
                "user_id": f"charlie_{self.test_session_id}",
                "email": f"charlie_{self.test_session_id}@isolation-test.com",
                "thread_ids": [f"charlie_thread_1_{self.test_session_id}"],
                "sensitive_data": "Charlie_Private_Details_ABCDE"
            }
        }
        
        # Initialize auth helpers for each isolated user
        self.user_auth_helpers = {}
        for user_name, user_data in self.isolated_users.items():
            auth_config = E2EAuthConfig(
                auth_service_url="http://localhost:8083",
                backend_url="http://localhost:8002",
                websocket_url="ws://localhost:8002/ws",
                test_user_email=user_data["email"],
                timeout=20.0
            )
            self.user_auth_helpers[user_name] = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        
        self.user_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.user_messages: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize message tracking for each user
        for user_name in self.isolated_users.keys():
            self.user_messages[user_name] = []
        
        # Test auth helper functionality for all users
        try:
            for user_name, helper in self.user_auth_helpers.items():
                user_data = self.isolated_users[user_name]
                token = helper.create_test_jwt_token(user_id=user_data["user_id"])
                assert token, f"Failed to create test JWT for isolated user {user_name}"
        except Exception as e:
            pytest.fail(f"User isolation test setup failed: {e}")
    
    async def async_teardown(self):
        """Clean up all isolated user connections and test resources."""
        cleanup_tasks = []
        for connection in self.user_connections.values():
            if not connection.closed:
                cleanup_tasks.append(connection.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.user_connections.clear()
        await super().async_teardown()
    
    async def create_isolated_user_connection(self, user_name: str) -> websockets.WebSocketServerProtocol:
        """
        Create authenticated WebSocket connection for isolated user.
        
        Args:
            user_name: Name of isolated test user
            
        Returns:
            Authenticated WebSocket connection with user isolation
        """
        if user_name not in self.isolated_users:
            raise ValueError(f"Unknown isolated user: {user_name}")
        
        user_data = self.isolated_users[user_name]
        auth_helper = self.user_auth_helpers[user_name]
        
        token = auth_helper.create_test_jwt_token(user_id=user_data["user_id"])
        headers = auth_helper.get_websocket_headers(token)
        
        # Add isolation validation headers
        headers.update({
            "X-Isolation-Test": "true",
            "X-User-Isolation-ID": user_data["user_id"],
            "X-Test-Session": self.test_session_id
        })
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                auth_helper.config.websocket_url,
                additional_headers=headers,
                open_timeout=10.0
            ),
            timeout=12.0
        )
        
        self.user_connections[user_name] = websocket
        return websocket
    
    async def collect_isolated_user_messages(
        self,
        user_name: str,
        expected_count: int,
        timeout: float = 15.0
    ) -> List[Dict[str, Any]]:
        """
        Collect messages for isolated user with cross-contamination detection.
        
        Args:
            user_name: Name of isolated user
            expected_count: Expected number of messages
            timeout: Maximum time to wait
            
        Returns:
            List of messages for isolated user
        """
        if user_name not in self.user_connections:
            raise ValueError(f"No connection for isolated user: {user_name}")
        
        websocket = self.user_connections[user_name]
        user_data = self.isolated_users[user_name]
        messages = []
        start_time = time.time()
        
        try:
            while len(messages) < expected_count and (time.time() - start_time) < timeout:
                try:
                    message_data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    message = json.loads(message_data)
                    
                    # Add isolation metadata
                    message_with_isolation = {
                        **message,
                        "_received_by_user": user_name,
                        "_received_at": time.time(),
                        "_isolation_check": self._validate_message_isolation(message, user_data),
                        "_message_index": len(messages)
                    }
                    
                    messages.append(message_with_isolation)
                    self.user_messages[user_name].append(message_with_isolation)
                    
                except asyncio.TimeoutError:
                    if (time.time() - start_time) >= timeout:
                        break
                    continue
                    
        except Exception as e:
            # Log isolation error but return collected messages
            pass
            
        return messages
    
    def _validate_message_isolation(self, message: Dict[str, Any], expected_user_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate message isolation for user context.
        
        Args:
            message: Received message
            expected_user_data: Expected user data for validation
            
        Returns:
            Dict with isolation validation results
        """
        isolation_check = {
            "user_id_correct": True,
            "thread_id_valid": True,
            "no_cross_contamination": True,
            "content_appropriate": True
        }
        
        # Check user ID isolation
        message_user_id = message.get("user_id")
        if message_user_id and message_user_id != expected_user_data["user_id"]:
            isolation_check["user_id_correct"] = False
        
        # Check thread ID isolation
        message_thread_id = message.get("thread_id")
        if message_thread_id and message_thread_id not in expected_user_data["thread_ids"]:
            isolation_check["thread_id_valid"] = False
        
        # Check for cross-contamination from other users
        message_content = str(message.get("content", "")) + str(message.get("message", ""))
        for other_user_data in self.isolated_users.values():
            if other_user_data != expected_user_data:
                if (other_user_data["user_id"] in message_content or 
                    other_user_data["sensitive_data"] in message_content):
                    isolation_check["no_cross_contamination"] = False
                    break
        
        return isolation_check
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_session_isolation(self, real_services_fixture):
        """
        Test complete isolation between concurrent user sessions.
        
        BVJ: Multi-user security - Users must have completely isolated sessions.
        Session isolation prevents data leaks and maintains regulatory compliance.
        """
        try:
            # Create connections for multiple isolated users
            alice_ws = await self.create_isolated_user_connection("alice")
            bob_ws = await self.create_isolated_user_connection("bob")
            charlie_ws = await self.create_isolated_user_connection("charlie")
            
            # Verify all connections are established and isolated
            assert not alice_ws.closed, "Alice connection should be active"
            assert not bob_ws.closed, "Bob connection should be active"
            assert not charlie_ws.closed, "Charlie connection should be active"
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                # Create user-specific LLM responses for isolation testing
                def get_user_llm(user_name):
                    return IsolationTestLLM(user_name).complete_async
                
                mock_llm_manager.return_value.complete_async = get_user_llm("generic")
                
                # Send concurrent agent requests with user-specific data
                alice_data = self.isolated_users["alice"]
                bob_data = self.isolated_users["bob"]
                charlie_data = self.isolated_users["charlie"]
                
                alice_request = {
                    "type": "agent_execution_request",
                    "user_id": alice_data["user_id"],
                    "thread_id": alice_data["thread_ids"][0],
                    "agent_type": "isolation_test_agent",
                    "task": f"Process Alice's sensitive data: {alice_data['sensitive_data']}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                bob_request = {
                    "type": "agent_execution_request",
                    "user_id": bob_data["user_id"],
                    "thread_id": bob_data["thread_ids"][0],
                    "agent_type": "isolation_test_agent",
                    "task": f"Handle Bob's confidential info: {bob_data['sensitive_data']}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                charlie_request = {
                    "type": "agent_execution_request",
                    "user_id": charlie_data["user_id"],
                    "thread_id": charlie_data["thread_ids"][0],
                    "agent_type": "isolation_test_agent",
                    "task": f"Manage Charlie's private details: {charlie_data['sensitive_data']}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Send requests concurrently
                await alice_ws.send(json.dumps(alice_request))
                await bob_ws.send(json.dumps(bob_request))
                await charlie_ws.send(json.dumps(charlie_request))
                
                # Collect messages from all users concurrently
                alice_task = asyncio.create_task(
                    self.collect_isolated_user_messages("alice", expected_count=2, timeout=20.0)
                )
                bob_task = asyncio.create_task(
                    self.collect_isolated_user_messages("bob", expected_count=2, timeout=20.0)
                )
                charlie_task = asyncio.create_task(
                    self.collect_isolated_user_messages("charlie", expected_count=2, timeout=20.0)
                )
                
                alice_messages, bob_messages, charlie_messages = await asyncio.gather(
                    alice_task, bob_task, charlie_task, return_exceptions=True
                )
                
                # Handle potential exceptions
                if isinstance(alice_messages, Exception):
                    alice_messages = []
                if isinstance(bob_messages, Exception):
                    bob_messages = []
                if isinstance(charlie_messages, Exception):
                    charlie_messages = []
                
                # Verify each user received isolated messages
                assert len(alice_messages) > 0, "Alice should receive isolated messages"
                assert len(bob_messages) > 0, "Bob should receive isolated messages"
                assert len(charlie_messages) > 0, "Charlie should receive isolated messages"
                
                # Verify user isolation - no cross-contamination
                for message in alice_messages:
                    isolation_check = message["_isolation_check"]
                    assert isolation_check["user_id_correct"], "Alice received message for wrong user"
                    assert isolation_check["no_cross_contamination"], "Alice's messages contaminated with other user data"
                
                for message in bob_messages:
                    isolation_check = message["_isolation_check"]
                    assert isolation_check["user_id_correct"], "Bob received message for wrong user"
                    assert isolation_check["no_cross_contamination"], "Bob's messages contaminated with other user data"
                
                for message in charlie_messages:
                    isolation_check = message["_isolation_check"]
                    assert isolation_check["user_id_correct"], "Charlie received message for wrong user"
                    assert isolation_check["no_cross_contamination"], "Charlie's messages contaminated with other user data"
                
                # Verify sensitive data isolation
                all_alice_content = " ".join([str(m.get("content", "")) for m in alice_messages])
                all_bob_content = " ".join([str(m.get("content", "")) for m in bob_messages])
                all_charlie_content = " ".join([str(m.get("content", "")) for m in charlie_messages])
                
                # Alice should not see Bob's or Charlie's sensitive data
                assert bob_data["sensitive_data"] not in all_alice_content, "Alice's messages leaked Bob's sensitive data"
                assert charlie_data["sensitive_data"] not in all_alice_content, "Alice's messages leaked Charlie's sensitive data"
                
                # Bob should not see Alice's or Charlie's sensitive data
                assert alice_data["sensitive_data"] not in all_bob_content, "Bob's messages leaked Alice's sensitive data"
                assert charlie_data["sensitive_data"] not in all_bob_content, "Bob's messages leaked Charlie's sensitive data"
                
                # Charlie should not see Alice's or Bob's sensitive data
                assert alice_data["sensitive_data"] not in all_charlie_content, "Charlie's messages leaked Alice's sensitive data"
                assert bob_data["sensitive_data"] not in all_charlie_content, "Charlie's messages leaked Bob's sensitive data"
            
        except Exception as e:
            pytest.fail(f"Concurrent user session isolation test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_isolation_between_users(self, real_services_fixture):
        """
        Test thread isolation between different users and within user sessions.
        
        BVJ: Conversation privacy - User conversations must be completely isolated.
        Thread isolation ensures conversation confidentiality and prevents data mixing.
        """
        try:
            # Create connections for Alice and Bob
            alice_ws = await self.create_isolated_user_connection("alice")
            bob_ws = await self.create_isolated_user_connection("bob")
            
            alice_data = self.isolated_users["alice"]
            bob_data = self.isolated_users["bob"]
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = IsolationTestLLM("thread_isolation").complete_async
                
                # Send requests to different threads for each user
                alice_thread_1_request = {
                    "type": "agent_execution_request",
                    "user_id": alice_data["user_id"],
                    "thread_id": alice_data["thread_ids"][0],
                    "agent_type": "thread_isolation_agent",
                    "task": f"Alice Thread 1 conversation with data: {alice_data['sensitive_data']}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                alice_thread_2_request = {
                    "type": "agent_execution_request",
                    "user_id": alice_data["user_id"],
                    "thread_id": alice_data["thread_ids"][1],
                    "agent_type": "thread_isolation_agent",
                    "task": "Alice Thread 2 separate conversation - different context",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                bob_thread_1_request = {
                    "type": "agent_execution_request",
                    "user_id": bob_data["user_id"],
                    "thread_id": bob_data["thread_ids"][0],
                    "agent_type": "thread_isolation_agent",
                    "task": f"Bob Thread 1 with private data: {bob_data['sensitive_data']}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Send all thread requests
                await alice_ws.send(json.dumps(alice_thread_1_request))
                await asyncio.sleep(0.2)
                await alice_ws.send(json.dumps(alice_thread_2_request))
                await asyncio.sleep(0.2)
                await bob_ws.send(json.dumps(bob_thread_1_request))
                
                # Collect messages for both users
                alice_messages = await self.collect_isolated_user_messages("alice", expected_count=4, timeout=25.0)
                bob_messages = await self.collect_isolated_user_messages("bob", expected_count=2, timeout=25.0)
                
                # Organize Alice's messages by thread
                alice_thread_1_messages = [m for m in alice_messages if m.get("thread_id") == alice_data["thread_ids"][0]]
                alice_thread_2_messages = [m for m in alice_messages if m.get("thread_id") == alice_data["thread_ids"][1]]
                
                # Organize Bob's messages by thread
                bob_thread_1_messages = [m for m in bob_messages if m.get("thread_id") == bob_data["thread_ids"][0]]
                
                # Verify thread isolation within Alice's session
                assert len(alice_thread_1_messages) > 0, "Alice Thread 1 should have messages"
                assert len(alice_thread_2_messages) > 0, "Alice Thread 2 should have messages"
                
                # Verify no thread ID mixing for Alice
                for message in alice_thread_1_messages:
                    assert message.get("thread_id") == alice_data["thread_ids"][0], "Alice Thread 1 message has wrong thread ID"
                    assert message.get("user_id") == alice_data["user_id"], "Alice Thread 1 message has wrong user ID"
                
                for message in alice_thread_2_messages:
                    assert message.get("thread_id") == alice_data["thread_ids"][1], "Alice Thread 2 message has wrong thread ID"
                    assert message.get("user_id") == alice_data["user_id"], "Alice Thread 2 message has wrong user ID"
                
                # Verify thread isolation between users
                for message in bob_thread_1_messages:
                    assert message.get("thread_id") == bob_data["thread_ids"][0], "Bob Thread 1 message has wrong thread ID"
                    assert message.get("user_id") == bob_data["user_id"], "Bob Thread 1 message has wrong user ID"
                
                # Verify no cross-user thread contamination
                all_alice_thread_ids = set(m.get("thread_id") for m in alice_messages if m.get("thread_id"))
                all_bob_thread_ids = set(m.get("thread_id") for m in bob_messages if m.get("thread_id"))
                
                # Alice should only see her own thread IDs
                for thread_id in all_alice_thread_ids:
                    assert thread_id in alice_data["thread_ids"], f"Alice received message for unknown thread: {thread_id}"
                
                # Bob should only see his own thread IDs
                for thread_id in all_bob_thread_ids:
                    assert thread_id in bob_data["thread_ids"], f"Bob received message for unknown thread: {thread_id}"
                
                # Verify no thread ID intersection between users
                thread_id_intersection = all_alice_thread_ids.intersection(all_bob_thread_ids)
                assert len(thread_id_intersection) == 0, f"Thread ID isolation violation: {thread_id_intersection}"
            
        except Exception as e:
            pytest.fail(f"Thread isolation between users test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_context_isolation(self, real_services_fixture):
        """
        Test authentication context isolation between users.
        
        BVJ: Security foundation - Authentication contexts must be completely isolated.
        Proper auth isolation prevents privilege escalation and unauthorized access.
        """
        try:
            # Create connections with different authentication contexts
            alice_ws = await self.create_isolated_user_connection("alice")
            bob_ws = await self.create_isolated_user_connection("bob")
            
            alice_data = self.isolated_users["alice"]
            bob_data = self.isolated_users["bob"]
            
            # Test authentication context separation
            alice_auth_test = {
                "type": "auth_context_test",
                "user_id": alice_data["user_id"],
                "requested_operation": "access_user_data",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            bob_auth_test = {
                "type": "auth_context_test",
                "user_id": bob_data["user_id"],
                "requested_operation": "access_user_data",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Send authentication context tests
            await alice_ws.send(json.dumps(alice_auth_test))
            await bob_ws.send(json.dumps(bob_auth_test))
            
            # Try cross-user authentication test (should be rejected)
            alice_cross_user_test = {
                "type": "auth_context_test",
                "user_id": bob_data["user_id"],  # Alice trying to access Bob's context
                "requested_operation": "access_user_data",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await alice_ws.send(json.dumps(alice_cross_user_test))
            
            # Collect authentication responses
            alice_messages = await self.collect_isolated_user_messages("alice", expected_count=2, timeout=15.0)
            bob_messages = await self.collect_isolated_user_messages("bob", expected_count=1, timeout=15.0)
            
            # Verify authentication context isolation
            for message in alice_messages:
                message_user_id = message.get("user_id")
                if message_user_id:
                    # Alice should only receive messages for her own user context
                    assert message_user_id == alice_data["user_id"], \
                        f"Alice received message for different user context: {message_user_id}"
            
            for message in bob_messages:
                message_user_id = message.get("user_id")
                if message_user_id:
                    # Bob should only receive messages for his own user context
                    assert message_user_id == bob_data["user_id"], \
                        f"Bob received message for different user context: {message_user_id}"
            
            # Verify no authentication bypass occurred
            alice_user_ids_seen = set(m.get("user_id") for m in alice_messages if m.get("user_id"))
            bob_user_ids_seen = set(m.get("user_id") for m in bob_messages if m.get("user_id"))
            
            # Each user should only see their own user ID
            assert alice_data["user_id"] in alice_user_ids_seen, "Alice did not see her own user context"
            assert bob_data["user_id"] not in alice_user_ids_seen, "Alice saw Bob's user context (auth bypass)"
            
            assert bob_data["user_id"] in bob_user_ids_seen, "Bob did not see his own user context"
            assert alice_data["user_id"] not in bob_user_ids_seen, "Bob saw Alice's user context (auth bypass)"
            
            # Test token isolation - each connection should only work with its own token
            alice_auth_helper = self.user_auth_helpers["alice"]
            bob_auth_helper = self.user_auth_helpers["bob"]
            
            # Verify tokens are different and user-specific
            alice_token = alice_auth_helper.create_test_jwt_token(user_id=alice_data["user_id"])
            bob_token = bob_auth_helper.create_test_jwt_token(user_id=bob_data["user_id"])
            
            assert alice_token != bob_token, "User tokens should be different for isolation"
            
            # Extract user IDs from tokens to verify isolation
            alice_token_user = alice_auth_helper._extract_user_id(alice_token)
            bob_token_user = bob_auth_helper._extract_user_id(bob_token)
            
            assert alice_token_user == alice_data["user_id"], "Alice token contains wrong user ID"
            assert bob_token_user == bob_data["user_id"], "Bob token contains wrong user ID"
            assert alice_token_user != bob_token_user, "Token user IDs should be isolated"
            
        except Exception as e:
            pytest.fail(f"Authentication context isolation test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_isolation_comprehensive(self, real_services_fixture):
        """
        Test comprehensive agent execution isolation between users.
        
        BVJ: Execution security - Agent executions must be completely isolated.
        Execution isolation prevents data mixing and ensures secure AI processing.
        """
        try:
            # Create connections for all isolated users
            alice_ws = await self.create_isolated_user_connection("alice")
            bob_ws = await self.create_isolated_user_connection("bob")
            charlie_ws = await self.create_isolated_user_connection("charlie")
            
            alice_data = self.isolated_users["alice"]
            bob_data = self.isolated_users["bob"]
            charlie_data = self.isolated_users["charlie"]
            
            with patch('netra_backend.app.llm.llm_manager.LLMManager') as mock_llm_manager:
                mock_llm_manager.return_value.complete_async = IsolationTestLLM("execution_isolation").complete_async
                
                # Create agent execution requests with isolation test data
                execution_requests = [
                    {
                        "connection": alice_ws,
                        "request": {
                            "type": "agent_execution_request",
                            "user_id": alice_data["user_id"],
                            "thread_id": alice_data["thread_ids"][0],
                            "agent_type": "execution_isolation_agent",
                            "task": f"Alice isolated execution with: {alice_data['sensitive_data']}",
                            "execution_context": {"user": "alice", "sensitivity": "high"},
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    },
                    {
                        "connection": bob_ws,
                        "request": {
                            "type": "agent_execution_request",
                            "user_id": bob_data["user_id"],
                            "thread_id": bob_data["thread_ids"][0],
                            "agent_type": "execution_isolation_agent",
                            "task": f"Bob isolated execution with: {bob_data['sensitive_data']}",
                            "execution_context": {"user": "bob", "sensitivity": "high"},
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    },
                    {
                        "connection": charlie_ws,
                        "request": {
                            "type": "agent_execution_request",
                            "user_id": charlie_data["user_id"],
                            "thread_id": charlie_data["thread_ids"][0],
                            "agent_type": "execution_isolation_agent",
                            "task": f"Charlie isolated execution with: {charlie_data['sensitive_data']}",
                            "execution_context": {"user": "charlie", "sensitivity": "high"},
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
                ]
                
                # Send all execution requests simultaneously
                send_tasks = []
                for req_data in execution_requests:
                    task = asyncio.create_task(
                        req_data["connection"].send(json.dumps(req_data["request"]))
                    )
                    send_tasks.append(task)
                
                await asyncio.gather(*send_tasks)
                
                # Collect execution results for all users
                collection_tasks = [
                    asyncio.create_task(self.collect_isolated_user_messages("alice", expected_count=2, timeout=20.0)),
                    asyncio.create_task(self.collect_isolated_user_messages("bob", expected_count=2, timeout=20.0)),
                    asyncio.create_task(self.collect_isolated_user_messages("charlie", expected_count=2, timeout=20.0))
                ]
                
                alice_messages, bob_messages, charlie_messages = await asyncio.gather(
                    *collection_tasks, return_exceptions=True
                )
                
                # Handle potential exceptions
                if isinstance(alice_messages, Exception):
                    alice_messages = []
                if isinstance(bob_messages, Exception):
                    bob_messages = []
                if isinstance(charlie_messages, Exception):
                    charlie_messages = []
                
                # Verify each user received isolated execution results
                assert len(alice_messages) > 0, "Alice should receive isolated execution results"
                assert len(bob_messages) > 0, "Bob should receive isolated execution results"
                assert len(charlie_messages) > 0, "Charlie should receive isolated execution results"
                
                # Verify execution isolation - no context bleeding
                all_user_messages = [
                    ("alice", alice_messages),
                    ("bob", bob_messages),
                    ("charlie", charlie_messages)
                ]
                
                for user_name, messages in all_user_messages:
                    user_data = self.isolated_users[user_name]
                    
                    for message in messages:
                        # Verify user context isolation
                        message_user_id = message.get("user_id")
                        if message_user_id:
                            assert message_user_id == user_data["user_id"], \
                                f"User {user_name} received message for wrong user: {message_user_id}"
                        
                        # Verify isolation check passed
                        isolation_check = message.get("_isolation_check", {})
                        assert isolation_check.get("user_id_correct", False), \
                            f"User {user_name} failed user ID isolation check"
                        assert isolation_check.get("no_cross_contamination", False), \
                            f"User {user_name} failed cross-contamination check"
                
                # Verify comprehensive execution isolation
                alice_execution_content = " ".join([str(m.get("content", "")) for m in alice_messages])
                bob_execution_content = " ".join([str(m.get("content", "")) for m in bob_messages])
                charlie_execution_content = " ".join([str(m.get("content", "")) for m in charlie_messages])
                
                # Cross-contamination checks
                isolation_violations = []
                
                if bob_data["sensitive_data"] in alice_execution_content:
                    isolation_violations.append("Alice execution leaked Bob's sensitive data")
                if charlie_data["sensitive_data"] in alice_execution_content:
                    isolation_violations.append("Alice execution leaked Charlie's sensitive data")
                
                if alice_data["sensitive_data"] in bob_execution_content:
                    isolation_violations.append("Bob execution leaked Alice's sensitive data")
                if charlie_data["sensitive_data"] in bob_execution_content:
                    isolation_violations.append("Bob execution leaked Charlie's sensitive data")
                
                if alice_data["sensitive_data"] in charlie_execution_content:
                    isolation_violations.append("Charlie execution leaked Alice's sensitive data")
                if bob_data["sensitive_data"] in charlie_execution_content:
                    isolation_violations.append("Charlie execution leaked Bob's sensitive data")
                
                assert len(isolation_violations) == 0, f"Execution isolation violations: {isolation_violations}"
            
        except Exception as e:
            pytest.fail(f"Agent execution isolation comprehensive test failed: {e}")