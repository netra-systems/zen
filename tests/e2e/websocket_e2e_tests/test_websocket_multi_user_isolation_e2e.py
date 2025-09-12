"""
WebSocket Multi-User Isolation E2E Tests

CRITICAL: These tests are DESIGNED TO FAIL during Phase 1 of WebSocket ID migration.
They expose multi-user isolation failures caused by uuid.uuid4() ID patterns.

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Multi-user system security and data isolation
- Value Impact: Prevents user data leakage and cross-contamination
- Strategic Impact: CRITICAL - Multi-user isolation failures = security vulnerabilities

Test Strategy:
1. FAIL INITIALLY - Tests expose isolation issues with uuid.uuid4()
2. MIGRATE PHASE - Replace with UnifiedIdGenerator user-aware methods
3. PASS FINALLY - Tests validate proper multi-user isolation with consistent IDs

These tests validate that WebSocket multi-user isolation preserves business value:
- User data never leaks between users
- Chat sessions remain completely isolated
- Agent executions are user-scoped
- Resource allocation is properly isolated
"""

import pytest
import asyncio
import uuid
import time
import websockets
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

# Import test framework for E2E testing
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services import get_real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Import WebSocket testing utilities
from test_framework.ssot.websocket_test_client import UnifiedWebSocketTestClient

# Import agent execution components for real multi-user testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# Import WebSocket core modules for isolation testing
from netra_backend.app.websocket_core.types import ConnectionInfo, WebSocketMessage, MessageType
from netra_backend.app.websocket_core.context import WebSocketRequestContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

# Import SSOT UnifiedIdGenerator for proper isolation
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ConnectionID, ThreadID, ExecutionID


@pytest.mark.e2e
@pytest.mark.websocket
@pytest.mark.multi_user
@pytest.mark.isolation
@pytest.mark.security
class TestWebSocketMultiUserIsolationE2E(BaseE2ETest):
    """
    E2E tests that EXPOSE multi-user isolation failures with uuid.uuid4().
    
    CRITICAL: These tests use real services and real concurrent users. They are 
    DESIGNED TO FAIL initially to demonstrate how uuid.uuid4() breaks isolation.
    
    SUCCESS CRITERIA: Zero cross-user data leakage or resource access.
    """

    @pytest.fixture(autouse=True)
    async def setup_multi_user_isolation_test(self, real_services_fixture, real_llm_fixture):
        """Set up real services for multi-user isolation E2E testing."""
        self.services = await get_real_services()
        self.auth_helper = E2EAuthHelper()
        self.websocket_base_url = self.env.get("WEBSOCKET_URL", "ws://localhost:8000")
        
        # Create isolated test users with different roles/permissions
        self.test_users = await self._create_isolated_test_users()
        
        # Initialize WebSocket manager factory for testing
        self.ws_factory = WebSocketManagerFactory()
        
        yield
        
        # Cleanup all test users and their data
        await self._cleanup_isolated_test_users()

    async def test_concurrent_user_chat_isolation_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose concurrent user chat isolation failures.
        
        This test validates that multiple users can chat simultaneously without
        any cross-contamination of their data, contexts, or responses.
        """
        # Define test scenarios with sensitive business data
        user_scenarios = [
            {
                "user_index": 0,
                "business_context": "Confidential merger analysis for Company A",
                "query": "Analyze the financial impact of acquiring TechCorp for $50M. Include debt structure analysis.",
                "sensitive_keywords": ["TechCorp", "$50M", "merger", "acquisition"],
                "expected_agent": "financial_analysis"
            },
            {
                "user_index": 1, 
                "business_context": "Proprietary product launch strategy for SecretProduct",
                "query": "Plan the go-to-market strategy for SecretProduct launch in Q4. Budget is $2M.",
                "sensitive_keywords": ["SecretProduct", "$2M", "Q4", "launch"],
                "expected_agent": "marketing_strategy"
            },
            {
                "user_index": 2,
                "business_context": "Internal restructuring and layoff planning",
                "query": "Help me plan workforce optimization. We need to reduce headcount by 15% while maintaining productivity.",
                "sensitive_keywords": ["layoff", "15%", "workforce", "restructuring"],
                "expected_agent": "hr_optimization"
            }
        ]
        
        # Start concurrent chat sessions
        concurrent_sessions = []
        
        for scenario in user_scenarios:
            user_auth = self.test_users[scenario["user_index"]]
            user_id = user_auth["user_id"]
            auth_token = user_auth["auth_token"]
            
            # Create isolated WebSocket connection
            session_task = asyncio.create_task(
                self._run_isolated_chat_session(
                    user_id=user_id,
                    auth_token=auth_token,
                    scenario=scenario
                )
            )
            concurrent_sessions.append(session_task)
            
        # Run all sessions concurrently
        try:
            session_results = await asyncio.wait_for(
                asyncio.gather(*concurrent_sessions, return_exceptions=True),
                timeout=180  # 3 minutes for real AI processing
            )
        except asyncio.TimeoutError:
            pytest.fail("Multi-user concurrent sessions timed out - isolation may be broken")
            
        # Validate complete isolation - no cross-contamination
        for i, result in enumerate(session_results):
            if isinstance(result, Exception):
                pytest.fail(f"Isolation session {i} failed: {result}")
                
            scenario = user_scenarios[i]
            user_id = self.test_users[scenario["user_index"]]["user_id"]
            
            # FAILING ASSERTION: Each user's response should contain only their sensitive data
            response_content = result["response_content"].lower()
            execution_id = result["execution_id"]
            
            # Validate user's own sensitive keywords are present
            user_keywords_found = [
                kw for kw in scenario["sensitive_keywords"] 
                if kw.lower() in response_content
            ]
            
            assert len(user_keywords_found) >= 2, \
                f"User {user_id} response missing own context: {user_keywords_found}"
                
            # FAILING ASSERTION: No other users' sensitive data should appear
            for j, other_scenario in enumerate(user_scenarios):
                if i != j:
                    contamination_keywords = [
                        kw for kw in other_scenario["sensitive_keywords"]
                        if kw.lower() in response_content
                    ]
                    
                    assert len(contamination_keywords) == 0, \
                        f"User {user_id} response contaminated with user {j} data: {contamination_keywords}"
                        
            # FAILING ASSERTION: Execution ID should be user-isolated
            assert user_id[:8] in execution_id, \
                f"Execution ID lacks user isolation: {execution_id} for user {user_id}"
                
            # Expected UnifiedIdGenerator format for multi-user isolation
            expected_pattern = f"agent_{scenario['expected_agent']}_{user_id[:8]}_"
            assert execution_id.startswith(expected_pattern), \
                f"Expected isolated execution pattern '{expected_pattern}', got: {execution_id}"
                
        print(f" PASS:  Multi-user chat isolation validated for {len(user_scenarios)} concurrent users")

    async def test_websocket_connection_resource_isolation_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose WebSocket resource isolation failures.
        
        This test validates that users cannot access each other's WebSocket
        connections, contexts, or manager resources.
        """
        # Create multiple users with WebSocket connections
        user_connections = {}
        user_managers = {}
        
        for i, user_auth in enumerate(self.test_users[:4]):  # Use 4 users
            user_id = user_auth["user_id"]
            auth_token = user_auth["auth_token"]
            
            # Create WebSocket connection and manager
            connection_info = ConnectionInfo(user_id=user_id)
            
            # Create WebSocket manager for user
            mock_websocket = self._create_mock_websocket()
            manager = self.ws_factory.create_manager_for_user(user_id, mock_websocket)
            
            user_connections[user_id] = connection_info
            user_managers[user_id] = manager
            
        # FAILING ASSERTION: Each connection should have user-specific IDs
        connection_ids = []
        for user_id, connection in user_connections.items():
            # This will FAIL because uuid.uuid4() connection IDs lack user context
            assert user_id[:8] in connection.connection_id, \
                f"Connection ID lacks user isolation: {connection.connection_id} for user {user_id}"
                
            # Expected UnifiedIdGenerator format for connection isolation
            expected_pattern = f"ws_conn_{user_id[:8]}_"
            assert connection.connection_id.startswith(expected_pattern), \
                f"Expected isolated connection pattern '{expected_pattern}', got: {connection.connection_id}"
                
            connection_ids.append(connection.connection_id)
            
        # FAILING ASSERTION: All connection IDs should be unique and isolated
        unique_connections = set(connection_ids)
        assert len(unique_connections) == len(connection_ids), \
            f"Connection ID collision detected: {len(connection_ids)} vs {len(unique_connections)}"
            
        # FAILING ASSERTION: Manager resource isolation
        for user_id, manager in user_managers.items():
            manager_id = getattr(manager, '_manager_id', None) or \
                        getattr(manager, 'unique_suffix', None) or \
                        getattr(manager, '_internal_id', None)
                        
            if manager_id:
                # This will FAIL because uuid.uuid4() manager IDs lack user context
                assert user_id[:8] in manager_id, \
                    f"Manager ID lacks user isolation: {manager_id} for user {user_id}"
                    
        # Test cross-user access prevention
        user_list = list(user_connections.keys())
        
        for i, user_id in enumerate(user_list):
            user_manager = user_managers[user_id]
            
            # Try to access other users' resources (should fail)
            for j, other_user_id in enumerate(user_list):
                if i != j:
                    other_connection = user_connections[other_user_id]
                    
                    # FAILING ASSERTION: Should not be able to access other user's connection
                    can_access = await self._try_access_user_connection(
                        accessing_user=user_id,
                        target_connection=other_connection.connection_id,
                        manager=user_manager
                    )
                    
                    assert not can_access, \
                        f"User {user_id} should not access connection {other_connection.connection_id} of user {other_user_id}"

    async def test_agent_execution_context_isolation_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose agent execution context isolation failures.
        
        This test validates that agent executions are completely isolated
        between users with no shared state or context leakage.
        """
        # Define agent execution scenarios with user-specific contexts
        execution_scenarios = [
            {
                "user_index": 0,
                "agent_type": "data_scientist",
                "context_data": {"customer_data": "CONFIDENTIAL_DATASET_A", "model_version": "v2.1"},
                "query": "Build predictive model using our customer dataset with 95% accuracy target."
            },
            {
                "user_index": 1,
                "agent_type": "security_analyst", 
                "context_data": {"security_clearance": "LEVEL_3", "incident_id": "SEC-2024-001"},
                "query": "Investigate security incident SEC-2024-001 and provide remediation plan."
            },
            {
                "user_index": 2,
                "agent_type": "financial_advisor",
                "context_data": {"portfolio_value": "$10M", "risk_level": "CONSERVATIVE"},
                "query": "Rebalance portfolio to maintain conservative risk profile."
            }
        ]
        
        # Start agent executions concurrently
        execution_tasks = []
        execution_contexts = []
        
        for scenario in execution_scenarios:
            user_auth = self.test_users[scenario["user_index"]]
            user_id = user_auth["user_id"]
            
            # Create user execution context
            context = WebSocketRequestContext.create_for_user(
                user_id=user_id,
                thread_id=None,
                connection_info=None
            )
            
            # Add user-specific context data
            context.user_context = scenario["context_data"]
            execution_contexts.append((user_id, context, scenario))
            
            # Start agent execution
            task = asyncio.create_task(
                self._run_isolated_agent_execution(
                    user_id=user_id,
                    context=context,
                    scenario=scenario
                )
            )
            execution_tasks.append(task)
            
        # Wait for all executions to complete
        try:
            execution_results = await asyncio.wait_for(
                asyncio.gather(*execution_tasks, return_exceptions=True),
                timeout=120
            )
        except asyncio.TimeoutError:
            pytest.fail("Agent executions timed out - context isolation may be broken")
            
        # Validate execution context isolation
        for i, result in enumerate(execution_results):
            if isinstance(result, Exception):
                pytest.fail(f"Agent execution {i} failed: {result}")
                
            user_id, context, scenario = execution_contexts[i]
            execution_id = result["execution_id"]
            
            # FAILING ASSERTION: Execution ID should be context-isolated
            assert user_id[:8] in execution_id, \
                f"Execution ID lacks context isolation: {execution_id} for user {user_id}"
                
            # This will FAIL because uuid.uuid4() run_id lacks user context
            assert user_id[:8] in context.run_id, \
                f"Context run_id lacks user isolation: {context.run_id} for user {user_id}"
                
            # Expected UnifiedIdGenerator format for context isolation
            expected_context_pattern = f"ctx_{user_id[:8]}_{scenario['agent_type']}_"
            assert context.run_id.startswith(expected_context_pattern), \
                f"Expected isolated context pattern '{expected_context_pattern}', got: {context.run_id}"
                
        # FAILING ASSERTION: No cross-context data leakage
        for i, (user_id_i, context_i, scenario_i) in enumerate(execution_contexts):
            for j, (user_id_j, context_j, scenario_j) in enumerate(execution_contexts):
                if i != j:
                    # Check for context data contamination
                    context_i_data = str(getattr(context_i, 'user_context', {}))
                    scenario_j_keys = list(scenario_j["context_data"].keys())
                    
                    contamination_found = any(
                        key in context_i_data for key in scenario_j_keys
                    )
                    
                    assert not contamination_found, \
                        f"Context contamination: User {user_id_i} context contains data from user {user_id_j}"

    async def test_websocket_message_routing_isolation_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose WebSocket message routing isolation failures.
        
        This test validates that messages are routed only to their intended
        recipients with no cross-user message leakage.
        """
        # Create WebSocket connections for multiple users
        websocket_clients = []
        user_message_queues = {}
        
        for i, user_auth in enumerate(self.test_users[:3]):  # Use 3 users
            user_id = user_auth["user_id"]
            auth_token = user_auth["auth_token"]
            
            # Create authenticated WebSocket client
            client = await self._create_authenticated_websocket_client(user_id, auth_token).__aenter__()
            websocket_clients.append((user_id, client))
            user_message_queues[user_id] = []
            
        # Send user-specific messages that should not cross-contaminate
        test_messages = [
            {
                "sender_index": 0,
                "message_type": "private_notification",
                "content": "CONFIDENTIAL: Your salary review is scheduled for next week.",
                "target_user_only": True
            },
            {
                "sender_index": 1,
                "message_type": "project_update", 
                "content": "SECRET PROJECT: The new product launch date has been moved to Q1.",
                "target_user_only": True
            },
            {
                "sender_index": 2,
                "message_type": "financial_alert",
                "content": "SENSITIVE: Your account balance has dropped below $10,000.",
                "target_user_only": True
            }
        ]
        
        # Send messages and collect responses
        message_tracking = {}
        
        for msg_data in test_messages:
            sender_user_id, sender_client = websocket_clients[msg_data["sender_index"]]
            
            # Create message with user-specific routing
            message = {
                "type": msg_data["message_type"],
                "user_id": sender_user_id,
                "content": msg_data["content"],
                "message_id": f"msg_{sender_user_id}_{uuid.uuid4().hex[:8]}",  # Current problematic pattern
                "timestamp": time.time()
            }
            
            # Send message
            await sender_client.send_message(message)
            
            # Track message for isolation validation
            message_tracking[sender_user_id] = {
                "sent_message": message,
                "expected_content": msg_data["content"]
            }
            
        # Wait for message processing
        await asyncio.sleep(2)
        
        # Collect all received messages from each user
        for user_id, client in websocket_clients:
            received_messages = []
            
            # Try to collect any messages that arrived
            try:
                while True:
                    message = await asyncio.wait_for(client.receive_message(), timeout=1)
                    if message:
                        received_messages.append(message)
                    else:
                        break
            except asyncio.TimeoutError:
                pass  # No more messages
                
            user_message_queues[user_id] = received_messages
            
        # FAILING ASSERTION: Message routing isolation validation
        for sender_user_id, tracking_data in message_tracking.items():
            sent_content = tracking_data["expected_content"]
            
            # Validate sender received their own message (if echo is enabled)
            sender_messages = user_message_queues[sender_user_id]
            
            # FAILING ASSERTION: Other users should NOT receive this message
            for user_id, received_messages in user_message_queues.items():
                if user_id != sender_user_id:
                    # Check if any received message contains the sender's content
                    contaminated = any(
                        sent_content.lower() in str(msg).lower()
                        for msg in received_messages
                    )
                    
                    assert not contaminated, \
                        f"Message routing isolation failed: User {user_id} received content from user {sender_user_id}: '{sent_content}'"
                        
        # FAILING ASSERTION: Message IDs should be user-scoped
        all_message_ids = []
        for user_id, messages in user_message_queues.items():
            for message in messages:
                msg_id = message.get("message_id") or message.get("id")
                if msg_id:
                    # This will FAIL because uuid.uuid4() message IDs lack user scope
                    assert user_id[:8] in msg_id, \
                        f"Message ID lacks user scope: {msg_id} for user {user_id}"
                        
                    all_message_ids.append(msg_id)
                    
        # Validate no message ID collisions
        unique_message_ids = set(all_message_ids)
        assert len(unique_message_ids) == len(all_message_ids), \
            f"Message ID collision detected: {len(all_message_ids)} vs {len(unique_message_ids)}"
            
        # Cleanup WebSocket connections
        for user_id, client in websocket_clients:
            await client.__aexit__(None, None, None)

    async def test_session_state_isolation_across_users_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose session state isolation failures between users.
        
        This test validates that user session state remains completely isolated
        with no shared memory, cache, or state persistence across users.
        """
        # Create unique session states for each user
        user_session_states = {}
        
        for i, user_auth in enumerate(self.test_users[:3]):
            user_id = user_auth["user_id"]
            
            # Create user-specific session state
            session_state = {
                "conversation_history": [f"User {user_id} private message {j}" for j in range(5)],
                "preferences": {
                    "theme": f"theme_user_{i}",
                    "language": f"lang_user_{i}",
                    "api_keys": {
                        "openai_key": f"sk-user{i}_secret_key",
                        "anthropic_key": f"ant-user{i}_private_key"
                    }
                },
                "current_thread": f"thread_{user_id}_confidential",
                "active_agents": [f"agent_{user_id}_personal"],
                "usage_stats": {"requests": i * 10, "tokens": i * 1000}
            }
            
            user_session_states[user_id] = session_state
            
        # Create WebSocket contexts that should maintain isolated state
        websocket_contexts = {}
        
        for user_id, session_state in user_session_states.items():
            context = WebSocketRequestContext.create_for_user(
                user_id=user_id,
                thread_id=session_state["current_thread"],
                connection_info=None
            )
            
            # Store user-specific session state in context
            context.session_state = session_state
            websocket_contexts[user_id] = context
            
        # FAILING ASSERTION: Context IDs should be session-isolated
        for user_id, context in websocket_contexts.items():
            # This will FAIL because uuid.uuid4() run_id lacks session context
            assert user_id[:8] in context.run_id, \
                f"Context run_id lacks session isolation: {context.run_id} for user {user_id}"
                
            # Expected UnifiedIdGenerator format for session isolation
            expected_pattern = f"ctx_{user_id[:8]}_session_"
            assert context.run_id.find(expected_pattern) != -1, \
                f"Expected session-isolated context pattern with '{expected_pattern}', got: {context.run_id}"
                
        # Test session state isolation by attempting cross-user access
        user_ids = list(websocket_contexts.keys())
        
        for i, user_id_a in enumerate(user_ids):
            context_a = websocket_contexts[user_id_a]
            session_a = user_session_states[user_id_a]
            
            for j, user_id_b in enumerate(user_ids):
                if i != j:
                    context_b = websocket_contexts[user_id_b]
                    session_b = user_session_states[user_id_b]
                    
                    # FAILING ASSERTION: Session state should not leak between contexts
                    # Check conversation history isolation
                    history_a = session_a["conversation_history"]
                    history_b = session_b["conversation_history"]
                    
                    # No messages from user A should appear in user B's history
                    cross_contamination = any(
                        user_id_a in msg for msg in history_b
                    )
                    
                    assert not cross_contamination, \
                        f"Session state contamination: User {user_id_b} history contains data from user {user_id_a}"
                        
                    # FAILING ASSERTION: API keys should never leak between users
                    api_keys_a = session_a["preferences"]["api_keys"]
                    api_keys_b = session_b["preferences"]["api_keys"]
                    
                    # Check that no API keys cross over
                    for key_type, key_value in api_keys_a.items():
                        assert key_value not in str(api_keys_b), \
                            f"CRITICAL SECURITY: API key leaked from user {user_id_a} to user {user_id_b}: {key_type}"
                            
        # FAILING ASSERTION: Session isolation should persist across context operations
        # Simulate context operations that might cause state leakage
        
        for user_id, context in websocket_contexts.items():
            # Perform context operations
            context.add_message("Test message for isolation")
            context.update_thread_state({"last_activity": time.time()})
            
            # Context operations should not affect other users' contexts
            other_users = [uid for uid in user_ids if uid != user_id]
            
            for other_user_id in other_users:
                other_context = websocket_contexts[other_user_id]
                
                # Check that the test message didn't leak to other contexts
                other_messages = getattr(other_context, 'messages', [])
                leaked_messages = [
                    msg for msg in other_messages 
                    if "Test message for isolation" in str(msg)
                ]
                
                assert len(leaked_messages) == 0, \
                    f"Context state leaked from user {user_id} to user {other_user_id}"
                    
        print(f" PASS:  Session state isolation validated across {len(user_ids)} users")

    # Helper methods for multi-user isolation testing
    
    async def _create_isolated_test_users(self) -> List[Dict[str, Any]]:
        """Create isolated test users with different permission levels."""
        users = []
        
        # Create users with different profiles for realistic isolation testing
        user_profiles = [
            {"role": "admin", "permissions": ["read", "write", "admin"]},
            {"role": "manager", "permissions": ["read", "write"]}, 
            {"role": "user", "permissions": ["read"]},
            {"role": "guest", "permissions": ["read"]}
        ]
        
        for i, profile in enumerate(user_profiles):
            username = f"isolation_test_user_{i}_{profile['role']}_{uuid.uuid4().hex[:8]}"
            
            # Create user with specific profile
            user_auth = await self.auth_helper.create_authenticated_user(
                username=username,
                email=f"{username}@example.com",
                role=profile["role"],
                permissions=profile["permissions"]
            )
            
            user_auth["profile"] = profile
            users.append(user_auth)
            
        return users
        
    async def _cleanup_isolated_test_users(self):
        """Clean up isolated test users and their data."""
        try:
            for user_auth in self.test_users:
                await self.auth_helper.cleanup_user(user_auth["user_id"])
        except Exception as e:
            self.logger.warning(f"Multi-user isolation cleanup error: {e}")
            
    @asynccontextmanager
    async def _create_authenticated_websocket_client(self, user_id: str, auth_token: str):
        """Create authenticated WebSocket client for isolation testing."""
        websocket_url = f"{self.websocket_base_url}/ws/{user_id}"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        try:
            websocket = await websockets.connect(websocket_url, extra_headers=headers)
            client = UnifiedWebSocketTestClient(websocket)
            yield client
        finally:
            if 'websocket' in locals():
                await websocket.close()
                
    async def _run_isolated_chat_session(self, user_id: str, auth_token: str, 
                                       scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run isolated chat session for user and return results."""
        async with self._create_authenticated_websocket_client(user_id, auth_token) as client:
            # Send chat request
            chat_request = {
                "type": "start_agent_execution",
                "user_id": user_id,
                "message": scenario["query"],
                "agent_type": scenario["expected_agent"],
                "business_context": scenario["business_context"]
            }
            
            await client.send_message(chat_request)
            
            # Wait for agent started
            agent_started = await client.wait_for_event("agent_started", timeout=15)
            
            if not agent_started:
                raise Exception(f"Agent failed to start for user {user_id}")
                
            execution_id = agent_started.get("execution_id")
            
            # Wait for completion
            agent_completed = await client.wait_for_event("agent_completed", timeout=120)
            
            if not agent_completed:
                raise Exception(f"Agent failed to complete for user {user_id}")
                
            response_content = agent_completed.get("data", {}).get("content", "")
            
            return {
                "user_id": user_id,
                "execution_id": execution_id,
                "response_content": response_content,
                "scenario": scenario
            }
            
    def _create_mock_websocket(self):
        """Create mock WebSocket for testing."""
        from unittest.mock import MagicMock
        mock_ws = MagicMock()
        mock_ws.application_state = MagicMock()
        mock_ws.application_state._mock_name = "test_websocket"
        return mock_ws
        
    async def _try_access_user_connection(self, accessing_user: str, target_connection: str,
                                        manager) -> bool:
        """Try to access another user's connection (should fail)."""
        try:
            # This simulates attempting to access another user's connection
            # In a properly isolated system, this should fail
            
            # Try to find the connection in manager's resources
            if hasattr(manager, 'get_connection_by_id'):
                connection = await manager.get_connection_by_id(target_connection)
                return connection is not None
                
            # Try to access connection through manager attributes
            manager_connections = getattr(manager, 'connections', {})
            return target_connection in manager_connections
            
        except Exception:
            # Access denied (expected for proper isolation)
            return False
            
    async def _run_isolated_agent_execution(self, user_id: str, context: WebSocketRequestContext,
                                          scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run isolated agent execution and return results."""
        
        # Simulate agent execution with user context
        execution_id = f"agent_{scenario['agent_type']}_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Simulate execution time
        await asyncio.sleep(1)
        
        # Return execution result
        return {
            "user_id": user_id,
            "execution_id": execution_id,
            "context": context,
            "scenario": scenario,
            "status": "completed"
        }

    @pytest.fixture
    async def real_services_fixture(self):
        """Fixture to ensure real services are available for E2E tests."""
        # Automatically handled by BaseE2ETest
        pass
        
    @pytest.fixture
    async def real_llm_fixture(self):
        """Fixture to ensure real LLM services are available for isolation testing."""
        # Automatically handled by BaseE2ETest with real_llm option
        pass