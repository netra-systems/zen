""""

Golden Path Phase 2 User Isolation Violation Tests

CRITICAL: These tests demonstrate SSOT compliance violations and user isolation failures 
that were previously caused by deprecated singleton patterns. They validate that the
migration to proper user context factories eliminates contamination between users.

Business Value Justification:
    - Segment: Platform/Enterprise
- Business Goal: Stability & Security 
""""

- Value Impact: Prevents $"500K" plus ARR loss from multi-user data leakage
- Strategic Impact: Enables regulatory compliance (HIPAA/SOC2) for enterprise customers

The tests prove that:
    1. DEPRECATED: get_agent_instance_factory() creates user contamination vulnerabilities
2. SSOT COMPLIANT: create_agent_instance_factory(user_context) provides proper isolation
"
""


import asyncio
import pytest
import time
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import ()
    AgentInstanceFactory,
    create_agent_instance_factory,
    get_agent_instance_factory  # This should now raise an error
)
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockAgent(BaseAgent):
    "Mock agent for testing with contamination tracking."
    
    def __init__(self, agent_name: str = "MockAgent, llm_manager=None, tool_dispatcher=None):"
        super().__init__()
        self.agent_name = agent_name
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.user_context = None
        self.contamination_marker = None  # Used to track cross-user contamination
        self.execution_history = []  # Track execution calls
        
    @classmethod
    def create_agent_with_context(cls, user_context: UserExecutionContext):
        Factory method that binds agent to specific user context."
        Factory method that binds agent to specific user context."
        agent = cls(agent_name=f"MockAgent_{user_context.user_id})"
        agent.user_context = user_context
        agent.contamination_marker = fuser_{user_context.user_id}_{int(time.time() * 1000)}
        return agent
        
    async def execute(self, state: Dict, run_id: str, **kwargs):
        Mock execution that tracks contamination.""
        execution_id = fexec_{run_id}_{int(time.time() * 1000)}
        self.execution_history.append({
            'execution_id': execution_id,
            'run_id': run_id,
            'user_context': self.user_context,
            'contamination_marker': self.contamination_marker,
            'timestamp': time.time()
        }
        
        # Return execution result with contamination tracking
        return {
            'result': f"Executed by {self.agent_name},"
            'execution_id': execution_id,
            'contamination_marker': self.contamination_marker,
            'user_id': self.user_context.user_id if self.user_context else 'unknown'
        }
        
    def get_contamination_marker(self) -> str:
        "Get the contamination marker for this agent instance."
        return self.contamination_marker
        
    def has_cross_user_contamination(self, expected_user_id: str) -> bool:
        "Check if this agent has been contaminated by another user's data.'"
        if not self.user_context:
            return True  # No user context is contamination
            
        # Check if the user context matches expected user
        if self.user_context.user_id != expected_user_id:
            return True
            
        # Check execution history for cross-user contamination
        for execution in self.execution_history:
            if execution['user_context'] and execution['user_context'].user_id != expected_user_id:
                return True
                
        return False


class TestGoldenPathPhase2UserIsolationViolations(SSotAsyncTestCase):
    "
    ""

    CRITICAL: Test user isolation violations in Golden Path Phase 2 migration.
    
    These tests demonstrate the security vulnerabilities created by deprecated
    singleton patterns and validate that proper SSOT patterns prevent contamination.
"
""


    async def asyncSetUp(self):
        Set up test infrastructure with proper SSOT patterns.""
        await super().asyncSetUp()
        
        # Create mock infrastructure components
        self.mock_agent_class_registry = AgentClassRegistry()
        self.mock_agent_class_registry.register_agent_class(MockAgent, MockAgent)
        
        self.mock_websocket_bridge = AsyncMock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        self.mock_websocket_bridge.emit_user_event = AsyncMock(return_value=True)
        
        # Track test executions for contamination analysis
        self.user_executions = {}
        
    async def asyncTearDown(self):
        "Clean up test resources."
        await super().asyncTearDown()
        
    def create_test_user_context(self, user_id: str, suffix: str = ) -> UserExecutionContext:"
    def create_test_user_context(self, user_id: str, suffix: str = ) -> UserExecutionContext:"
        "Create test user execution context with unique identifiers."
        thread_id = fthread_{user_id}_{suffix}_{uuid.uuid4().hex[:8]}""
        run_id = frun_{user_id}_{suffix}_{uuid.uuid4().hex[:8]}
        
        return UserExecutionContext.from_request_supervisor(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=freq_{user_id}_{suffix},
            metadata={'test_suffix': suffix, 'created_for': user_id}

    async def test_deprecated_singleton_factory_raises_error(self):
    """"

        TEST 1: Verify deprecated singleton factory is completely disabled.
        
        CRITICAL: The get_agent_instance_factory() function must raise an error
        to prevent multi-user contamination vulnerabilities.
        
        logger.info(TEST 1: Verifying deprecated singleton factory raises error")"
        
        # EXPECTATION: Deprecated function should raise ValueError
        with self.assertRaises(ValueError) as context:
            get_agent_instance_factory()
            
        # Validate error message contains security warning
        error_message = str(context.exception)
        self.assertIn(SINGLETON PATTERN ELIMINATED, error_message)
        self.assertIn(multi-user state contamination, error_message)"
        self.assertIn(multi-user state contamination, error_message)"
        self.assertIn("create_agent_instance_factory(user_context), error_message)"
        
        logger.info(CHECK PASS: Deprecated singleton factory correctly raises security error)

    async def test_ssot_factory_provides_user_isolation(self):
    """"

        TEST 2: Verify SSOT factory provides proper user isolation.
        
        CRITICAL: create_agent_instance_factory(user_context) must create
        completely isolated factories for different users.
        
        logger.info(TEST 2: Verifying SSOT factory provides user isolation")"
        
        # Create contexts for two different users
        user1_context = self.create_test_user_context(user1, isolation_test)
        user2_context = self.create_test_user_context(user2, isolation_test")"
        
        # Create per-user factories using SSOT pattern
        factory1 = create_agent_instance_factory(user1_context)
        factory2 = create_agent_instance_factory(user2_context)
        
        # Configure both factories with same infrastructure
        factory1.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        factory2.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create agents for each user
        agent1 = await factory1.create_agent_instance("MockAgent, user1_context)"
        agent2 = await factory2.create_agent_instance(MockAgent, user2_context)
        
        # VALIDATION: Agents should be completely isolated
        self.assertNotEqual(agent1, agent2, "Agents should be different instances)"
        self.assertEqual(agent1.user_context.user_id, user1)
        self.assertEqual(agent2.user_context.user_id, user2)"
        self.assertEqual(agent2.user_context.user_id, user2)""

        
        # VALIDATION: Contamination markers should be different
        marker1 = agent1.get_contamination_marker()
        marker2 = agent2.get_contamination_marker()
        self.assertNotEqual(marker1, marker2, Contamination markers should be unique")"
        
        # VALIDATION: No cross-user contamination
        self.assertFalse(agent1.has_cross_user_contamination(user1))
        self.assertFalse(agent2.has_cross_user_contamination(user2"))"
        
        logger.info(CHECK PASS: SSOT factory provides proper user isolation)

    async def test_concurrent_user_execution_isolation(self):
        """
        ""

        TEST 3: Verify concurrent user executions remain isolated.
        
        CRITICAL: Multiple users executing agents simultaneously should have
        no cross-contamination of state or context.
"
"
        logger.info(TEST 3: Testing concurrent user execution isolation)"
        logger.info(TEST 3: Testing concurrent user execution isolation)""

        
        # Create contexts for multiple concurrent users
        users = [alice", bob, charlie, diana]"
        user_contexts = {}
        factories = {}
        agents = {}
        
        # Set up isolated factories for each user
        for user_id in users:
            user_contexts[user_id] = self.create_test_user_context(user_id, concurrent")"
            factories[user_id) = create_agent_instance_factory(user_contexts[user_id)
            factories[user_id).configure(
                agent_class_registry=self.mock_agent_class_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            agents[user_id) = await factories[user_id).create_agent_instance(MockAgent, user_contexts[user_id)
        
        # Execute agents concurrently
        async def execute_for_user(user_id: str):
            "Execute agent for specific user and track results."
            context = user_contexts[user_id]
            agent = agents[user_id]
            
            # Perform multiple executions to increase contamination risk
            results = []
            for i in range(3):
                result = await agent.execute(
                    state={'task': f'task_{i}', 'user': user_id},
                    run_id=context.run_id
                )
                results.append(result)
                # Small delay to increase race condition potential
                await asyncio.sleep(0.1)
            
            return user_id, results
        
        # Run all users concurrently
        concurrent_tasks = [execute_for_user(user_id) for user_id in users]
        all_results = await asyncio.gather(*concurrent_tasks)
        
        # VALIDATION: Each user should only see their own data
        contamination_detected = False
        for user_id, results in all_results:
            agent = agents[user_id]
            
            # Check that agent maintained proper user binding
            self.assertEqual(agent.user_context.user_id, user_id)
            
            # Check that all execution results belong to correct user
            for result in results:
                if result['user_id'] != user_id:
                    contamination_detected = True
                    logger.error(fCONTAMINATION: User {user_id} got result for user {result['user_id']})
            
            # Check for cross-user contamination in agent
            if agent.has_cross_user_contamination(user_id):
                contamination_detected = True
                logger.error(fCONTAMINATION: Agent for {user_id} has cross-user contamination)"
                logger.error(fCONTAMINATION: Agent for {user_id} has cross-user contamination)""

        
        self.assertFalse(contamination_detected, "No cross-user contamination should be detected)"
        
        logger.info(CHECK PASS: Concurrent user executions remain properly isolated)

    async def test_factory_memory_isolation(self):
    """"

        TEST 4: Verify factory instances don't share memory state.'
        
        CRITICAL: Each factory instance should have completely separate
        memory space to prevent state leakage.
        
        logger.info(TEST 4: Testing factory memory isolation")"
        
        # Create multiple user contexts
        context1 = self.create_test_user_context(memory_user1, memory_test)
        context2 = self.create_test_user_context(memory_user2, memory_test")"
        
        # Create separate factories
        factory1 = create_agent_instance_factory(context1)
        factory2 = create_agent_instance_factory(context2)
        
        # Configure factories
        factory1.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        factory2.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # VALIDATION: Factories should be different instances
        self.assertNotEqual(factory1, factory2, "Factories should be different instances)"
        
        # VALIDATION: Factories should have separate user contexts
        self.assertEqual(factory1._user_context, context1)
        self.assertEqual(factory2._user_context, context2)
        self.assertNotEqual(factory1._user_context, factory2._user_context)
        
        # Create agents and check isolation
        agent1 = await factory1.create_agent_instance(MockAgent, context1)
        agent2 = await factory2.create_agent_instance("MockAgent, context2)"
        
        # VALIDATION: Agents should be bound to correct contexts
        self.assertEqual(agent1.user_context, context1)
        self.assertEqual(agent2.user_context, context2)
        
        # VALIDATION: Factory metrics should be independent
        metrics1 = factory1.get_factory_metrics()
        metrics2 = factory2.get_factory_metrics()
        
        # Both should have created 1 instance, but independently
        self.assertEqual(metrics1['total_instances_created'], 1)
        self.assertEqual(metrics2['total_instances_created'], 1)
        
        logger.info(CHECK PASS: Factory instances have proper memory isolation)

    async def test_user_context_binding_validation(self):
    """"

        TEST 5: Verify user context binding is mandatory and enforced.
        
        CRITICAL: Factories must require user context and fail gracefully
        without it to prevent context-less execution.
        
        logger.info(TEST 5: Testing user context binding validation)"
        logger.info(TEST 5: Testing user context binding validation)""

        
        # TEST: Factory creation without user context should work but be flagged
        factory_without_context = AgentInstanceFactory()  # No user context
        factory_without_context.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # TEST: Agent creation should require user context
        with self.assertRaises((ValueError, RuntimeError)) as context:
            await factory_without_context.create_agent_instance("MockAgent, None)"
        
        error_message = str(context.exception)
        self.assertIn(UserExecutionContext is required, error_message)
        
        # TEST: SSOT factory creation should require user context
        with self.assertRaises(ValueError) as context:
            create_agent_instance_factory(None)
        
        error_message = str(context.exception)
        self.assertIn("UserExecutionContext is required, error_message)"
        
        logger.info(CHECK PASS: User context binding is properly validated)

    async def test_resource_cleanup_isolation(self):
    """"

        TEST 6: Verify resource cleanup doesn't affect other users.'
        
        CRITICAL: When one user's context is cleaned up, other users'
        should remain unaffected.
        
        logger.info(TEST 6: Testing resource cleanup isolation)"
        logger.info(TEST 6: Testing resource cleanup isolation)""

        
        # Create contexts for multiple users
        user1_context = self.create_test_user_context("cleanup_user1, cleanup_test)"
        user2_context = self.create_test_user_context(cleanup_user2, cleanup_test)
        
        # Create factories and agents
        factory1 = create_agent_instance_factory(user1_context)
        factory2 = create_agent_instance_factory(user2_context)
        
        for factory in [factory1, factory2]:
            factory.configure(
                agent_class_registry=self.mock_agent_class_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
        
        agent1 = await factory1.create_agent_instance("MockAgent, user1_context)"
        agent2 = await factory2.create_agent_instance(MockAgent, user2_context)
        
        # Execute agents to create state
        result1 = await agent1.execute({'task': 'user1_task'}, user1_context.run_id)
        result2 = await agent2.execute({'task': 'user2_task'}, user2_context.run_id)
        
        # Verify both are working
        self.assertEqual(result1['user_id'], 'cleanup_user1')
        self.assertEqual(result2['user_id'], 'cleanup_user2')
        
        # Clean up user1's context'
        await factory1.cleanup_user_context(user1_context)
        
        # Verify user2 is still functional
        result2_after_cleanup = await agent2.execute({'task': 'user2_after_cleanup'}, user2_context.run_id)
        self.assertEqual(result2_after_cleanup['user_id'], 'cleanup_user2')
        
        # Verify user2's contamination marker unchanged'
        self.assertFalse(agent2.has_cross_user_contamination('cleanup_user2'))
        
        logger.info(CHECK PASS: Resource cleanup maintains proper isolation)"
        logger.info(CHECK PASS: Resource cleanup maintains proper isolation)""


    async def test_golden_path_contamination_prevention(self):
        """
        ""

        TEST 7: Golden Path end-to-end contamination prevention.
        
        CRITICAL: Full Golden Path workflow should maintain perfect user
        isolation throughout the entire execution pipeline.
"
"
        logger.info("TEST 7: Testing Golden Path contamination prevention)"
        
        # Simulate complete Golden Path workflow for multiple users
        golden_path_users = [golden_alice, golden_bob]
        results = {}
        
        for user_id in golden_path_users:
            # Step 1: Create user context (as would happen in real request)
            user_context = self.create_test_user_context(user_id, golden_path")"
            
            # Step 2: Create per-request factory (SSOT pattern)
            factory = create_agent_instance_factory(user_context)
            factory.configure(
                agent_class_registry=self.mock_agent_class_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            
            # Step 3: Create agent instance
            agent = await factory.create_agent_instance(MockAgent, user_context)
            
            # Step 4: Execute agent workflow
            async with factory.user_execution_scope(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id
            ) as scope_context:
                execution_result = await agent.execute(
                    state={'golden_path_task': f'task_for_{user_id}'},
                    run_id=scope_context.run_id
                )
                
                # Step 5: Store results for cross-contamination analysis
                results[user_id] = {
                    'execution_result': execution_result,
                    'agent_marker': agent.get_contamination_marker(),
                    'context_user_id': scope_context.user_id,
                    'agent_instance': agent
                }
        
        # VALIDATION: Complete isolation between users
        alice_result = results['golden_alice']
        bob_result = results['golden_bob']
        
        # Each user should only see their own data
        self.assertEqual(alice_result['execution_result']['user_id'], 'golden_alice')
        self.assertEqual(bob_result['execution_result']['user_id'], 'golden_bob')
        
        # Contamination markers should be unique
        self.assertNotEqual(alice_result['agent_marker'), bob_result['agent_marker')
        
        # No cross-user contamination
        self.assertFalse(alice_result['agent_instance'].has_cross_user_contamination('golden_alice'))
        self.assertFalse(bob_result['agent_instance'].has_cross_user_contamination('golden_bob'))
        
        logger.info(CHECK PASS: Golden Path maintains perfect user isolation)"
        logger.info(CHECK PASS: Golden Path maintains perfect user isolation)""


    async def test_performance_isolation_under_load(self):
        """
    ""

        TEST 8: Verify isolation holds under concurrent load.
        
        CRITICAL: User isolation must remain intact even under high
        concurrent load scenarios.
        "
        "
        logger.info(TEST 8: Testing performance isolation under load")"
        
        # Create high concurrent load scenario
        concurrent_users = 10
        executions_per_user = 5
        
        async def stress_test_user(user_index: int):
            Stress test for individual user with multiple executions.""
            user_id = fstress_user_{user_index}
            user_context = self.create_test_user_context(user_id, stress_test)"
            user_context = self.create_test_user_context(user_id, stress_test)""

            
            # Create factory and agent
            factory = create_agent_instance_factory(user_context)
            factory.configure(
                agent_class_registry=self.mock_agent_class_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            agent = await factory.create_agent_instance(MockAgent", user_context)"
            
            # Perform multiple rapid executions
            user_results = []
            for exec_num in range(executions_per_user):
                result = await agent.execute(
                    state={'stress_task': exec_num, 'user': user_id},
                    run_id=user_context.run_id
                )
                user_results.append(result)
                # Minimal delay to create race conditions
                await asyncio.sleep(0.1)
            
            return user_id, user_results, agent
        
        # Run concurrent stress tests
        stress_tasks = [stress_test_user(i) for i in range(concurrent_users)]
        all_stress_results = await asyncio.gather(*stress_tasks)
        
        # VALIDATION: No contamination detected under load
        contamination_errors = []
        for user_id, results, agent in all_stress_results:
            # Check all results belong to correct user
            for result in results:
                if result['user_id'] != user_id:
                    contamination_errors.append(fUser {user_id} got result for {result['user_id']})
            
            # Check agent contamination
            if agent.has_cross_user_contamination(user_id):
                contamination_errors.append(fAgent for {user_id} has cross-user contamination)"
                contamination_errors.append(fAgent for {user_id} has cross-user contamination)""

        
        # Report any contamination errors
        if contamination_errors:
            logger.error("CONTAMINATION ERRORS DETECTED:)"
            for error in contamination_errors:
                logger.error(f  - {error})
            self.fail(f"Contamination detected under load: {len(contamination_errors)} errors)"
        
        logger.info(fCHECK PASS: Isolation maintained under load ({concurrent_users} users, {executions_per_user} executions each)")"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short')
))))))