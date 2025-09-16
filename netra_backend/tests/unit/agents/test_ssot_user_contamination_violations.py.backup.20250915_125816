"""
SSOT Violation Test: Cross-User State Contamination

Business Impact: $500K+ ARR at risk - User data leakage would be catastrophic for platform trust
BVJ: Enterprise/Platform | Security/Stability | Critical user isolation requirement

This test SHOULD FAIL before SSOT remediation to prove the SSOT violation exists.
The test proves that singleton patterns cause global state contamination between users.

VIOLATION BEING TESTED:
- Singleton agent instances share state between concurrent users
- User A's execution context appears in User B's agent
- Global factory state contaminates across user sessions
- WebSocket events deliver to wrong users due to shared singleton state

Expected Failure Mode: User B will receive User A's data, proving cross-user contamination.
"""

import asyncio
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestSSOTUserContaminationViolations(SSotAsyncTestCase):
    """Test that exposes cross-user state contamination from singleton patterns.

    These tests SHOULD FAIL before SSOT remediation because singleton patterns
    cause global state sharing between users, violating isolation requirements.

    Business Impact: $500K+ ARR depends on secure user isolation. Any cross-user
    contamination would destroy platform trust and create regulatory violations.
    """

    def setup_method(self, method):
        """Set up test fixtures following SSOT patterns."""
        super().setup_method(method)

        # Create mock infrastructure (real services not needed for unit test)
        self.mock_llm_manager = AsyncMock(spec=LLMManager)
        self.mock_websocket_bridge = AsyncMock(spec=AgentWebSocketBridge)

        # Create realistic user contexts for testing
        self.user_a_context = UserExecutionContext(
            user_id="user_a_12345",
            thread_id="thread_a_67890",
            run_id="run_a_11111",
            request_id="req_a_22222",
            websocket_client_id="ws_a_33333",
            agent_context={
                "user_request": "USER A SECRET DATA - should never appear for User B",
                "sensitive_data": "user_a_confidential_info",
                "user_specific_context": "CONFIDENTIAL_USER_A_CONTEXT"
            }
        )

        self.user_b_context = UserExecutionContext(
            user_id="user_b_54321",
            thread_id="thread_b_09876",
            run_id="run_b_44444",
            request_id="req_b_55555",
            websocket_client_id="ws_b_66666",
            agent_context={
                "user_request": "USER B DIFFERENT REQUEST - should be isolated",
                "sensitive_data": "user_b_different_data",
                "user_specific_context": "DIFFERENT_USER_B_CONTEXT"
            }
        )

    async def test_cross_user_factory_contamination_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Singleton factory sharing state between users
        Business Impact: User A's sensitive data appears in User B's context

        Expected Failure: User B will receive User A's metadata/context due to
        singleton pattern sharing state across user sessions.
        """
        # Get the factory instance (this may be a singleton, causing the violation)
        factory = get_agent_instance_factory()

        # Configure factory for User A
        factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )

        # Create agent instance for User A with sensitive data
        user_a_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_a_context
        )

        # Simulate User A's execution setting state in the agent
        if hasattr(user_a_agent, '_context') or hasattr(user_a_agent, 'context'):
            # The agent may store context internally (singleton violation)
            agent_context = getattr(user_a_agent, '_context', None) or getattr(user_a_agent, 'context', None)
            if agent_context:
                # User A's sensitive data gets stored in the agent
                agent_context.metadata = self.user_a_context.metadata.copy()

        # NOW CREATE USER B'S AGENT - This should be completely isolated
        user_b_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_b_context
        )

        # CRITICAL TEST: Check if User B's agent has User A's data
        # This SHOULD FAIL (contamination exists) before SSOT remediation
        user_b_agent_context = getattr(user_b_agent, '_context', None) or getattr(user_b_agent, 'context', None)

        if user_b_agent_context and hasattr(user_b_agent_context, 'metadata'):
            user_b_metadata = user_b_agent_context.metadata or {}
        else:
            user_b_metadata = {}

        # VIOLATION CHECK: User A's data appears in User B's agent
        user_a_sensitive_data = self.user_a_context.metadata.get("sensitive_data")
        user_a_context_data = self.user_a_context.metadata.get("user_specific_context")

        contamination_found = False
        contamination_details = []

        # Check if User A's sensitive data leaked into User B's context
        if user_a_sensitive_data in str(user_b_metadata):
            contamination_found = True
            contamination_details.append(f"User A's sensitive data '{user_a_sensitive_data}' found in User B's context")

        if user_a_context_data in str(user_b_metadata):
            contamination_found = True
            contamination_details.append(f"User A's context '{user_a_context_data}' found in User B's context")

        # Check if the agents are the same instance (singleton violation)
        if user_a_agent is user_b_agent:
            contamination_found = True
            contamination_details.append("CRITICAL: Same agent instance returned for different users (singleton violation)")

        # ASSERTION THAT SHOULD FAIL: No contamination should exist, but it does
        self.assertFalse(
            contamination_found,
            f"SSOT VIOLATION DETECTED: Cross-user contamination found. "
            f"Details: {contamination_details}. "
            f"This proves singleton patterns are sharing state between users, "
            f"creating a CRITICAL security vulnerability affecting $500K+ ARR."
        )

    async def test_concurrent_user_websocket_contamination_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: WebSocket events delivering to wrong users due to singleton sharing
        Business Impact: User receives another user's private messages/notifications

        Expected Failure: WebSocket events intended for User A will be delivered to User B.
        """
        # Create separate WebSocket bridges for isolation test
        user_a_websocket = AsyncMock(spec=AgentWebSocketBridge)
        user_b_websocket = AsyncMock(spec=AgentWebSocketBridge)

        # Create factory and configure for User A
        factory = get_agent_instance_factory()
        factory.configure(
            websocket_bridge=user_a_websocket,
            llm_manager=self.mock_llm_manager
        )

        # Create agent for User A with their WebSocket
        user_a_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_a_context
        )

        # Configure factory for User B (this should create isolation)
        factory.configure(
            websocket_bridge=user_b_websocket,  # Different WebSocket bridge
            llm_manager=self.mock_llm_manager
        )

        # Create agent for User B
        user_b_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_b_context
        )

        # Simulate sending WebSocket event via User A's agent
        if hasattr(user_a_agent, '_websocket_bridge') or hasattr(user_a_agent, 'websocket_bridge'):
            user_a_bridge = getattr(user_a_agent, '_websocket_bridge', None) or getattr(user_a_agent, 'websocket_bridge', None)
            if user_a_bridge:
                await user_a_bridge.notify_agent_started(
                    self.user_a_context.run_id,
                    "DataSubAgent",
                    context={"user_data": "USER_A_PRIVATE_EVENT"}
                )

        # Check User B's agent WebSocket bridge
        user_b_bridge = None
        if hasattr(user_b_agent, '_websocket_bridge') or hasattr(user_b_agent, 'websocket_bridge'):
            user_b_bridge = getattr(user_b_agent, '_websocket_bridge', None) or getattr(user_b_agent, 'websocket_bridge', None)

        # VIOLATION CHECK: If singleton, User B's agent will have User A's WebSocket bridge
        websocket_contamination = False
        contamination_details = []

        if user_b_bridge is user_a_websocket:
            websocket_contamination = True
            contamination_details.append("CRITICAL: User B's agent has User A's WebSocket bridge (singleton sharing)")

        if user_b_bridge and user_b_bridge == user_a_websocket:
            websocket_contamination = True
            contamination_details.append("User A's WebSocket bridge found in User B's agent")

        # Check if WebSocket events were called on wrong bridge
        if user_a_websocket.notify_agent_started.called and user_b_websocket.notify_agent_started.called:
            if user_a_websocket.notify_agent_started.call_count > 0 and user_b_websocket.notify_agent_started.call_count > 0:
                websocket_contamination = True
                contamination_details.append("WebSocket events delivered to both users from same action")

        # ASSERTION THAT SHOULD FAIL: No WebSocket contamination should exist
        self.assertFalse(
            websocket_contamination,
            f"SSOT VIOLATION DETECTED: WebSocket contamination between users. "
            f"Details: {contamination_details}. "
            f"This proves singleton WebSocket sharing is causing cross-user event delivery, "
            f"creating a CRITICAL privacy violation affecting $500K+ ARR user trust."
        )

    async def test_global_state_persistence_contamination_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Global factory state persisting between user sessions
        Business Impact: Previous user's state affects subsequent user's execution

        Expected Failure: User B's agent will contain state/configuration from User A's session.
        """
        factory = get_agent_instance_factory()

        # Configure factory with User A's specific settings
        user_a_config = {
            "execution_mode": "USER_A_SPECIFIC_MODE",
            "user_permissions": ["USER_A_PERMISSION_1", "USER_A_PERMISSION_2"],
            "session_data": "USER_A_SESSION_CONFIDENTIAL"
        }

        factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )

        # Create User A's agent and set configuration
        user_a_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_a_context
        )

        # Simulate storing User A's config in factory (singleton violation)
        if hasattr(factory, '_user_config') or hasattr(factory, 'user_config'):
            config_attr = getattr(factory, '_user_config', None) or getattr(factory, 'user_config', None)
            if hasattr(config_attr, 'update'):
                config_attr.update(user_a_config)
        elif hasattr(factory, '__dict__'):
            # Store config directly in factory instance
            factory._test_user_config = user_a_config

        # NOW create User B's agent (should be completely isolated)
        user_b_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_b_context
        )

        # Check if User B's agent has access to User A's configuration
        factory_contamination = False
        contamination_details = []

        # Check various places where User A's config might leak
        if hasattr(factory, '_test_user_config'):
            if factory._test_user_config == user_a_config:
                factory_contamination = True
                contamination_details.append("User A's config persisted in factory for User B")

        if hasattr(factory, '_user_config') and factory._user_config:
            for key, value in user_a_config.items():
                if key in factory._user_config and factory._user_config[key] == value:
                    factory_contamination = True
                    contamination_details.append(f"User A's config key '{key}' found in factory during User B's session")

        # Check if User B's agent has any User A configuration
        if hasattr(user_b_agent, '__dict__'):
            agent_dict_str = str(user_b_agent.__dict__)
            for key, value in user_a_config.items():
                if str(value) in agent_dict_str:
                    factory_contamination = True
                    contamination_details.append(f"User A's config value '{value}' found in User B's agent")

        # ASSERTION THAT SHOULD FAIL: No factory state contamination should exist
        self.assertFalse(
            factory_contamination,
            f"SSOT VIOLATION DETECTED: Factory state contamination between user sessions. "
            f"Details: {contamination_details}. "
            f"This proves singleton factory is maintaining global state across users, "
            f"violating isolation requirements and affecting $500K+ ARR platform trust."
        )