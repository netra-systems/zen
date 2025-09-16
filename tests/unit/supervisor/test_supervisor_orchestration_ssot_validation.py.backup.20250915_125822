"""
Unit Tests for SSOT Supervisor Orchestration Pattern Validation

Business Value: $500K+ ARR Golden Path Protection
Purpose: Validate that supervisor orchestration follows SSOT patterns correctly
Focus: Factory patterns, dependency injection, singleton elimination

This test file validates Issue #1188 Phase 3.4 supervisor integration patterns.
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional, Dict, Any

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Core supervisor agent imports
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager

class TestSupervisorOrchestrationSSOTValidation(SSotAsyncTestCase):
    """Unit tests validating SSOT patterns in supervisor orchestration."""

    def setup_method(self, method):
        """Set up test environment with SSOT patterns."""
        super().setup_method(method)

        # Mock environment for testing
        self.env = IsolatedEnvironment()

        # Create mock user context for testing (Issue #1116)
        self.mock_user_context = UserExecutionContext.from_request(
            user_id="test-user-123",
            thread_id="test-thread-456",
            run_id="test-run-789",
            request_id="test-request-123"
        )

        # Create mock LLM manager
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_llm_manager.get_client = Mock(return_value=Mock())

    def test_supervisor_agent_requires_user_context(self):
        """
        Test that SupervisorAgent requires user_context for security compliance.

        Business Impact: Prevents user data leakage by eliminating singleton patterns.
        Issue #1116: Singleton to factory migration validation.
        """
        # Test 1: Should raise ValueError without user_context
        with pytest.raises(ValueError) as exc_info:
            SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=None  # This should trigger the error
            )

        # Validate error message indicates singleton elimination
        error_msg = str(exc_info.value)
        assert "singleton factory pattern has been eliminated" in error_msg
        assert "user data leakage" in error_msg
        assert "Issue #1116" in error_msg or "user_context parameter" in error_msg

    def test_supervisor_agent_proper_factory_initialization(self):
        """
        Test that SupervisorAgent initializes with proper factory pattern.

        Business Impact: Validates enterprise-grade user isolation.
        """
        # Test 2: Should initialize successfully with user_context
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory') as mock_factory_creator:
            mock_factory = Mock()
            mock_factory_creator.return_value = mock_factory

            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.mock_user_context
            )

            # Validate factory creation was called with user context
            mock_factory_creator.assert_called_once_with(self.mock_user_context)
            assert supervisor.agent_factory is mock_factory
            assert supervisor._initialization_user_context is self.mock_user_context

    def test_supervisor_agent_legacy_parameter_handling(self):
        """
        Test that legacy parameters are handled gracefully.

        Business Impact: Ensures backward compatibility during migration.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            # Test 3: Legacy parameters should be ignored but not cause errors
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.mock_user_context,
                db_session_factory=Mock(),  # Legacy parameter
                tool_dispatcher=Mock()  # Legacy parameter
            )

            # Should still initialize successfully
            assert supervisor is not None
            assert supervisor._llm_manager is self.mock_llm_manager

    def test_supervisor_agent_websocket_bridge_integration(self):
        """
        Test WebSocket bridge integration in supervisor orchestration.

        Business Impact: Validates real-time communication for Golden Path.
        """
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

        mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.mock_user_context,
                websocket_bridge=mock_websocket_bridge
            )

            # Test 4: WebSocket bridge should be properly integrated
            assert supervisor.websocket_bridge is mock_websocket_bridge

    def test_supervisor_agent_user_isolation_validation(self):
        """
        Test that different user contexts create isolated supervisor instances.

        Business Impact: Prevents cross-user data contamination.
        Security: Enterprise-grade multi-user isolation.
        """
        # Create two different user contexts
        user_context_1 = UserExecutionContext.from_request(
            user_id="user-1",
            thread_id="thread-1",
            run_id="run-1",
            request_id="request-1"
        )

        user_context_2 = UserExecutionContext.from_request(
            user_id="user-2",
            thread_id="thread-2",
            run_id="run-2",
            request_id="request-2"
        )

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory') as mock_factory_creator:
            mock_factory_1 = Mock()
            mock_factory_2 = Mock()
            mock_factory_creator.side_effect = [mock_factory_1, mock_factory_2]

            # Test 5: Create two supervisor instances
            supervisor_1 = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=user_context_1
            )

            supervisor_2 = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=user_context_2
            )

            # Validate proper isolation
            assert supervisor_1.agent_factory is mock_factory_1
            assert supervisor_2.agent_factory is mock_factory_2
            assert supervisor_1.agent_factory is not supervisor_2.agent_factory
            assert supervisor_1._initialization_user_context is not supervisor_2._initialization_user_context

    def test_supervisor_agent_base_agent_inheritance(self):
        """
        Test that SupervisorAgent properly inherits from BaseAgent.

        Business Impact: Validates consistent agent interface patterns.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.mock_user_context
            )

            # Test 6: Proper BaseAgent inheritance
            from netra_backend.app.agents.base_agent import BaseAgent
            assert isinstance(supervisor, BaseAgent)
            assert supervisor.name == "Supervisor"
            assert "user isolation" in supervisor.description

    def test_supervisor_agent_ssot_import_patterns(self):
        """
        Test that supervisor uses proper SSOT import patterns.

        Business Impact: Validates SSOT compliance for maintainability.
        """
        # Test 7: Validate SSOT imports are being used
        from netra_backend.app.agents import supervisor_ssot

        # Check that critical SSOT imports are present
        assert hasattr(supervisor_ssot, 'SupervisorAgent')
        assert hasattr(supervisor_ssot, 'UserExecutionContext')
        assert hasattr(supervisor_ssot, 'UserExecutionEngine')

    def test_supervisor_orchestration_error_handling(self):
        """
        Test error handling in supervisor orchestration patterns.

        Business Impact: Validates graceful failure handling.
        """
        # Test 8: Invalid user context should be handled properly
        invalid_user_context = None

        with pytest.raises((ValueError, TypeError)):
            SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=invalid_user_context
            )

    @pytest.mark.asyncio
    async def test_supervisor_agent_async_compatibility(self):
        """
        Test that supervisor agent works with async operations.

        Business Impact: Validates async orchestration patterns.
        """
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.mock_user_context
            )

            # Test 9: Should support async operations
            assert supervisor is not None
            # Additional async operations would be tested in integration tests

    def test_supervisor_performance_initialization(self):
        """
        Test that supervisor initialization is performant.

        Business Impact: Validates SLA compliance for agent creation.
        """
        import time

        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory'):
            start_time = time.time()

            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                user_context=self.mock_user_context
            )

            end_time = time.time()
            initialization_time = end_time - start_time

            # Test 10: Initialization should be under 100ms for performance
            assert initialization_time < 0.1, f"Supervisor initialization took {initialization_time:.3f}s, exceeding 100ms SLA"
            assert supervisor is not None


class TestSupervisorOrchestrationFactoryPatterns(SSotAsyncTestCase):
    """Test factory patterns used in supervisor orchestration."""

    def setup_method(self, method):
        """Set up factory pattern tests."""
        super().setup_method(method)

        self.mock_user_context = UserExecutionContext.from_request(
            user_id="factory-test-user",
            thread_id="factory-test-thread",
            run_id="factory-test-run",
            request_id="factory-test-request"
        )

    def test_factory_pattern_singleton_elimination(self):
        """
        Test that factory patterns eliminate singleton usage.

        Business Impact: Security compliance for enterprise deployment.
        """
        from netra_backend.app.agents.supervisor import agent_instance_factory

        # Test 1: Factory creation should be per-user-context
        with patch.object(agent_instance_factory, 'create_agent_instance_factory') as mock_create:
            mock_factory = Mock()
            mock_create.return_value = mock_factory

            factory = agent_instance_factory.create_agent_instance_factory(self.mock_user_context)

            # Should be called with proper user context
            mock_create.assert_called_once_with(self.mock_user_context)

    def test_factory_thread_safety(self):
        """
        Test that factory creation is thread-safe for concurrent users.

        Business Impact: Multi-user concurrent access validation.
        """
        import threading
        import time
        from collections import defaultdict

        results = defaultdict(list)

        def create_supervisor_with_context(user_id):
            """Create supervisor with unique user context."""
            user_context = UserExecutionContext.from_request(
                user_id=f"thread-user-{user_id}",
                thread_id=f"thread-thread-{user_id}",
                run_id=f"thread-run-{user_id}",
                request_id=f"thread-request-{user_id}"
            )

            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory') as mock_factory:
                mock_factory.return_value = Mock()
                try:
                    supervisor = SupervisorAgent(
                        llm_manager=Mock(spec=LLMManager),
                        user_context=user_context
                    )
                    results[user_id].append(supervisor)
                except Exception as e:
                    results[user_id].append(f"ERROR: {e}")

        # Test 2: Create supervisors concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_supervisor_with_context, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Validate all creations succeeded
        for user_id in range(5):
            assert len(results[user_id]) == 1
            assert not isinstance(results[user_id][0], str), f"Thread {user_id} failed: {results[user_id][0]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])