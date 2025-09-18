"""
SSOT Violation Test: Factory vs Singleton Pattern Violations

Business Impact: 500K+ ARR at risk - Factory pattern violations break user isolation
BVJ: Enterprise/Platform | Architecture/Stability | Factory pattern compliance required

This test SHOULD FAIL before SSOT remediation to prove the SSOT violation exists.
The test proves that singleton patterns are breaking factory pattern expectations.

VIOLATION BEING TESTED:
- Factory methods returning the same singleton instance instead of unique instances
- Singleton pattern breaking factory pattern isolation guarantees
- Global state sharing when factory pattern should provide isolation
- Factory methods not creating fresh instances as expected

Expected Failure Mode: Factory create methods will return the same singleton instance
instead of unique instances, violating factory pattern principles.
"""

import asyncio
import uuid
import gc
import weakref
from typing import Dict, Any, List, Set
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class SSOTFactorySingletonViolationsTests(SSotAsyncTestCase):
    """Test that exposes singleton patterns breaking factory pattern expectations.

    These tests SHOULD FAIL before SSOT remediation because singleton patterns
    violate factory pattern principles, breaking isolation and uniqueness guarantees.

    Business Impact: 500K+ ARR depends on factory patterns providing proper isolation.
    Singleton violations break multi-user execution and create security risks.
    """

    def setup_method(self, method):
        """Set up test fixtures following SSOT patterns."""
        super().setup_method(method)

        # Create mock infrastructure
        self.mock_llm_manager = AsyncMock(spec=LLMManager)
        self.mock_websocket_bridge = AsyncMock(spec=AgentWebSocketBridge)

        # Create multiple distinct user contexts for isolation testing
        self.user_contexts = [
            UserExecutionContext(
                user_id=f"user_{i}_{uuid.uuid4()}",
                thread_id=f"thread_{i}_{uuid.uuid4()}",
                run_id=f"run_{i}_{uuid.uuid4()}",
                request_id=f"req_{i}_{uuid.uuid4()}",
                websocket_client_id=f"ws_{i}_{uuid.uuid4()}",
                agent_context={
                    "user_request": f"User {i} specific request",
                    "user_index": i,
                    "isolation_test": True
                }
            )
            for i in range(5)  # Create 5 different user contexts
        ]

    async def test_factory_returns_singleton_instead_of_unique_instances_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Factory methods returning same singleton instead of unique instances
        Business Impact: Multiple users share the same agent instance, breaking isolation

        Expected Failure: All factory calls will return the same singleton instance
        instead of unique instances as factory pattern requires.
        """
        factory = get_agent_instance_factory()
        factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )

        created_instances = []
        instance_ids = set()

        # Create multiple agent instances using factory
        for i, context in enumerate(self.user_contexts):
            agent_instance = await factory.create_agent_instance(
                agent_name="DataSubAgent",
                user_context=context
            )

            created_instances.append((i, agent_instance))
            instance_ids.add(id(agent_instance))

        # VIOLATION CHECK: Factory should create unique instances, not singletons
        singleton_violations = []

        # Check if all instances are the same object (singleton violation)
        if len(instance_ids) == 1:
            singleton_violations.append(
                f"CRITICAL: All {len(created_instances)} factory calls returned the same singleton instance"
            )

        # Check for shared instances between different users
        for i, (user_i, instance_i) in enumerate(created_instances):
            for j, (user_j, instance_j) in enumerate(created_instances[i+1:], i+1):
                if instance_i is instance_j:
                    singleton_violations.append(
                        f"Users {user_i} and {user_j} share the same agent instance (singleton violation)"
                    )

        # Check factory method behavior - should create new instances
        factory_uniqueness_violation = len(instance_ids) < len(created_instances)

        # ASSERTION THAT SHOULD FAIL: Factory should create unique instances
        self.assertFalse(
            factory_uniqueness_violation,
            f"SSOT VIOLATION DETECTED: Factory pattern violation - singleton behavior detected. "
            f"Created {len(created_instances)} instances but only {len(instance_ids)} unique objects. "
            f"Violations: {singleton_violations}. "
            f"Factory pattern requires unique instances but singleton pattern is breaking isolation, "
            f"affecting 500K+ ARR multi-user execution safety."
        )

    async def test_factory_state_sharing_violation_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Factory-created instances sharing internal state
        Business Impact: User A's actions affect User B's agent behavior

        Expected Failure: Changes to one factory-created instance will affect other instances
        due to singleton pattern sharing internal state.
        """
        factory = get_agent_instance_factory()
        factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )

        # Create two agent instances for different users
        user_a_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_contexts[0]
        )

        user_b_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_contexts[1]
        )

        # Modify state in User A's agent
        user_a_state_changes = {
            "test_attribute": "USER_A_SPECIFIC_VALUE",
            "execution_count": 42,
            "user_specific_data": ["USER_A_DATA_1", "USER_A_DATA_2"]
        }

        # Apply state changes to User A's agent
        for attr, value in user_a_state_changes.items():
            if hasattr(user_a_agent, '__dict__'):
                setattr(user_a_agent, attr, value)

        # Check if User B's agent was affected by User A's changes
        state_contamination = []

        for attr, expected_value in user_a_state_changes.items():
            if hasattr(user_b_agent, attr):
                user_b_value = getattr(user_b_agent, attr)
                if user_b_value == expected_value:
                    state_contamination.append(
                        f"User A's {attr}='{expected_value}' appeared in User B's agent"
                    )

        # Check if the agents share the same __dict__ (singleton violation)
        if hasattr(user_a_agent, '__dict__') and hasattr(user_b_agent, '__dict__'):
            if user_a_agent.__dict__ is user_b_agent.__dict__:
                state_contamination.append("CRITICAL: Agents share the same __dict__ object")

        # Check for shared attributes by reference
        if hasattr(user_a_agent, '__dict__') and hasattr(user_b_agent, '__dict__'):
            for attr in user_a_agent.__dict__:
                if attr in user_b_agent.__dict__:
                    a_value = user_a_agent.__dict__[attr]
                    b_value = user_b_agent.__dict__[attr]
                    if a_value is b_value and not isinstance(a_value, (str, int, float, bool, type(None))):
                        state_contamination.append(
                            f"Attribute '{attr}' shared by reference between agents"
                        )

        # ASSERTION THAT SHOULD FAIL: No state sharing should occur
        self.assertFalse(
            bool(state_contamination),
            f"SSOT VIOLATION DETECTED: Factory-created instances sharing state. "
            f"State contamination: {state_contamination}. "
            f"Factory pattern should provide isolation but singleton pattern is causing "
            f"cross-user state sharing, affecting 500K+ ARR user data integrity."
        )

    async def test_factory_lifecycle_singleton_violation_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Factory instances not following proper lifecycle management
        Business Impact: Resource leaks and improper cleanup due to singleton sharing

        Expected Failure: Factory instances will not be properly garbage collected
        due to singleton pattern maintaining global references.
        """
        factory = get_agent_instance_factory()
        factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )

        # Create instances and track their lifecycle
        instance_refs = []

        for context in self.user_contexts[:3]:  # Use first 3 contexts
            agent_instance = await factory.create_agent_instance(
                agent_name="DataSubAgent",
                user_context=context
            )

            # Create weak reference to track garbage collection
            weak_ref = weakref.ref(agent_instance)
            instance_refs.append((context.user_id, weak_ref, agent_instance))

        # Clear strong references to allow garbage collection
        instances_to_clear = [ref[2] for ref in instance_refs]  # Keep strong refs temporarily
        del instances_to_clear

        # Force garbage collection
        gc.collect()

        # Check if instances are still alive (singleton violation)
        lifecycle_violations = []
        still_alive = 0

        for user_id, weak_ref, strong_ref in instance_refs:
            del strong_ref  # Remove strong reference
            gc.collect()   # Force collection

            if weak_ref() is not None:
                still_alive += 1
                lifecycle_violations.append(
                    f"Instance for user {user_id} still alive after reference removal (singleton global reference)"
                )

        # Check factory's internal state for retained references
        factory_retention_violations = []

        if hasattr(factory, '__dict__'):
            factory_dict = factory.__dict__
            for attr_name, attr_value in factory_dict.items():
                if isinstance(attr_value, (list, dict, set)):
                    if len(str(attr_value)) > 100:  # Likely contains references
                        factory_retention_violations.append(
                            f"Factory attribute '{attr_name}' may retain instance references"
                        )

        # Check for global singleton pattern indicators
        global_singleton_indicators = []

        # Check if factory itself is a singleton
        factory2 = get_agent_instance_factory()
        if factory is factory2:
            global_singleton_indicators.append("get_agent_instance_factory() returns singleton")

        # ASSERTION THAT SHOULD FAIL: Proper lifecycle management should occur
        has_lifecycle_violations = bool(lifecycle_violations) or bool(factory_retention_violations) or bool(global_singleton_indicators)

        self.assertFalse(
            has_lifecycle_violations,
            f"SSOT VIOLATION DETECTED: Factory lifecycle management violations detected. "
            f"Lifecycle violations: {lifecycle_violations}. "
            f"Factory retention: {factory_retention_violations}. "
            f"Singleton indicators: {global_singleton_indicators}. "
            f"Still alive instances: {still_alive}/{len(instance_refs)}. "
            f"Singleton patterns prevent proper resource cleanup, affecting 500K+ ARR performance."
        )

    async def test_factory_method_contract_violation_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Factory methods not adhering to factory pattern contracts
        Business Impact: Factory pattern expectations broken, leading to architectural inconsistency

        Expected Failure: Factory methods will violate factory pattern contracts by
        returning singletons instead of following factory instantiation patterns.
        """
        factory = get_agent_instance_factory()
        factory.configure(
            websocket_bridge=self.mock_websocket_bridge,
            llm_manager=self.mock_llm_manager
        )

        # Test factory pattern contracts
        contract_violations = []

        # Contract 1: Each create call should return a new instance
        instance1 = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_contexts[0]
        )
        instance2 = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_contexts[1]
        )

        if instance1 is instance2:
            contract_violations.append("Contract violation: create_agent_instance returns same instance for different users")

        # Contract 2: Factory should not maintain instance references
        initial_factory_state = str(factory.__dict__) if hasattr(factory, '__dict__') else ""

        instance3 = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_contexts[2]
        )

        final_factory_state = str(factory.__dict__) if hasattr(factory, '__dict__') else ""

        # Check if factory state grew (may indicate instance retention)
        if len(final_factory_state) > len(initial_factory_state) + 100:  # Allow for small changes
            contract_violations.append("Contract violation: Factory state grows with instance creation (possible retention)")

        # Contract 3: Factory should support multiple agent types without interference
        data_agent = await factory.create_agent_instance(
            agent_name="DataSubAgent",
            user_context=self.user_contexts[0]
        )
        optimization_agent = await factory.create_agent_instance(
            agent_name="OptimizationsCoreSubAgent",
            user_context=self.user_contexts[0]
        )

        if hasattr(data_agent, '__class__') and hasattr(optimization_agent, '__class__'):
            if data_agent.__class__ == optimization_agent.__class__:
                contract_violations.append("Contract violation: Different agent types return same class")

        # Contract 4: Factory reconfiguration should not affect existing instances
        original_websocket = data_agent.websocket_bridge if hasattr(data_agent, 'websocket_bridge') else None

        new_websocket = AsyncMock()
        factory.configure(websocket_bridge=new_websocket, llm_manager=self.mock_llm_manager)

        current_websocket = data_agent.websocket_bridge if hasattr(data_agent, 'websocket_bridge') else None

        if original_websocket is not None and current_websocket is not None:
            if original_websocket is not current_websocket:
                contract_violations.append("Contract violation: Factory reconfiguration affected existing instance")

        # ASSERTION THAT SHOULD FAIL: All factory contracts should be respected
        self.assertFalse(
            bool(contract_violations),
            f"SSOT VIOLATION DETECTED: Factory pattern contract violations. "
            f"Contract violations: {contract_violations}. "
            f"Factory methods are not following factory pattern principles, "
            f"breaking architectural consistency and affecting 500K+ ARR system reliability."
        )