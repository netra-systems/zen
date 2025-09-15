"""Unit Tests: ChatOrchestrator User Context Requirement Reproduction

Business Value Justification (BVJ):
- Segment: Platform Security
- Business Goal: Ensure enterprise-grade user isolation for $500K+ ARR protection
- Value Impact: Validates SSOT security compliance and multi-user data isolation
- Strategic Impact: Foundation for HIPAA/SOC2/SEC regulatory compliance

This test suite reproduces and validates the user context requirement failures
discovered in Issue #1116 SSOT Agent Factory Migration.

Phase 1: Reproduction Tests - Demonstrate the exact failure modes
Phase 2: Validation Tests - Confirm proper factory patterns work (future)

CRITICAL: These tests validate security compliance and prevent data leakage.
"""

import pytest
import uuid
from typing import Any, Dict
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# SSOT imports for test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core SSOT imports
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState

# Class under test
from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator


@pytest.mark.unit
class TestChatOrchestratorUserContextReproduction(SSotAsyncTestCase):
    """Reproduction tests for ChatOrchestrator user context requirement failures."""

    def setup_method(self, method=None):
        """Set up test environment for reproduction testing."""
        super().setup_method(method)

        # Test identifiers
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        self.run_id = f"test_run_{uuid.uuid4().hex[:8]}"

        # Mock dependencies
        self.mock_db_session = self._create_mock_db_session()
        self.mock_llm_manager = self._create_mock_llm_manager()
        self.mock_websocket_manager = self._create_mock_websocket_manager()
        self.mock_tool_dispatcher = self._create_mock_tool_dispatcher()

    def test_chat_orchestrator_fails_without_user_context(self):
        """REPRODUCTION: ChatOrchestrator should fail when constructed without user_context.

        This test reproduces the exact failure from Issue #1116 SSOT Agent Factory Migration.
        The ChatOrchestrator inherits from SupervisorAgent which now requires user_context
        for security compliance and user isolation.
        """

        # SETUP: Attempt to create ChatOrchestrator without user_context (old pattern)
        # This should fail with a ValueError about missing user_context

        with pytest.raises(ValueError) as exc_info:
            # This is the exact pattern that fails in the integration tests
            chat_orchestrator = ChatOrchestrator(
                db_session=self.mock_db_session,
                llm_manager=self.mock_llm_manager,
                websocket_manager=self.mock_websocket_manager,
                tool_dispatcher=self.mock_tool_dispatcher,
                semantic_cache_enabled=True
            )

        # VALIDATE: Confirm the exact error message from Issue #1116
        error_message = str(exc_info.value)

        assert "SupervisorAgent now requires user_context parameter" in error_message, \
               "Error should explain user_context requirement"
        assert "prevent user data leakage" in error_message, \
               "Error should explain the security reason"
        assert "singleton factory pattern has been eliminated" in error_message, \
               "Error should explain the architectural change"
        assert "security compliance" in error_message, \
               "Error should mention security compliance"

        # Additional validation for the expected error pattern
        expected_patterns = [
            "user_context parameter",
            "data leakage",
            "singleton factory pattern",
            "security compliance",
            "SupervisorAgent(..., user_context=your_user_context)"
        ]

        for pattern in expected_patterns:
            assert pattern in error_message, \
                   f"Error message should contain guidance: {pattern}"

    def test_supervisor_agent_requires_user_context_directly(self):
        """REPRODUCTION: Verify SupervisorAgent directly requires user_context.

        This test reproduces the root cause - SupervisorAgent constructor
        now requires user_context parameter for Issue #1116 compliance.
        """
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent

        # SETUP: Attempt to create SupervisorAgent without user_context
        # This should fail with the same ValueError

        with pytest.raises(ValueError) as exc_info:
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_manager,
            )

        # VALIDATE: Confirm this is the same error as ChatOrchestrator
        error_message = str(exc_info.value)

        assert "SupervisorAgent now requires user_context parameter" in error_message, \
               "SupervisorAgent should require user_context"
        assert "prevent user data leakage" in error_message, \
               "SupervisorAgent error should explain security rationale"

    def test_user_context_creation_pattern_works(self):
        """REPRODUCTION: Verify UserExecutionContext can be created properly.

        This test validates that the required UserExecutionContext can be
        created with the proper pattern, setting up for future success tests.
        """

        # SETUP: Create proper UserExecutionContext using the correct constructor
        user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id
        )

        # VALIDATE: UserExecutionContext should be created successfully
        assert user_context is not None, "UserExecutionContext should be created"
        assert user_context.user_id == self.user_id, "User ID should match"
        assert user_context.thread_id == self.thread_id, "Thread ID should match"
        assert user_context.run_id == self.run_id, "Run ID should match"

        # Additional validation for agent context pattern
        assert hasattr(user_context, 'agent_context'), "Should have agent_context attribute"
        assert hasattr(user_context, 'audit_metadata'), "Should have audit_metadata attribute"

    def test_chat_orchestrator_constructor_signature_analysis(self):
        """REPRODUCTION: Analyze ChatOrchestrator constructor for user_context support.

        This test analyzes the ChatOrchestrator constructor to understand
        how to properly pass user_context to the SupervisorAgent parent.
        """

        # SETUP: Check if ChatOrchestrator constructor accepts user_context
        from inspect import signature

        chat_orchestrator_signature = signature(ChatOrchestrator.__init__)
        supervisor_signature = signature(ChatOrchestrator.__bases__[0].__init__)

        # VALIDATE: Constructor signature analysis
        chat_params = list(chat_orchestrator_signature.parameters.keys())
        supervisor_params = list(supervisor_signature.parameters.keys())

        # Log signatures for debugging
        print(f"ChatOrchestrator params: {chat_params}")
        print(f"SupervisorAgent params: {supervisor_params}")

        # Check if user_context is in SupervisorAgent signature
        assert "user_context" in supervisor_params, \
               "SupervisorAgent should accept user_context parameter"

        # ChatOrchestrator may not expose user_context directly, but should pass it to super()
        # This is the key architectural insight for the fix

    def test_issue_1116_security_compliance_validation(self):
        """REPRODUCTION: Validate Issue #1116 security compliance requirements.

        This test validates that the singleton elimination for security compliance
        is working as intended - no fallback patterns should exist.
        """

        # SETUP: Attempt various patterns that should all fail
        failure_patterns = [
            # Pattern 1: No user_context at all
            {
                "params": {
                    "llm_manager": self.mock_llm_manager,
                    "websocket_bridge": self.mock_websocket_manager,
                },
                "description": "No user_context parameter"
            },
            # Pattern 2: None user_context
            {
                "params": {
                    "llm_manager": self.mock_llm_manager,
                    "websocket_bridge": self.mock_websocket_manager,
                    "user_context": None
                },
                "description": "None user_context parameter"
            }
        ]

        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent

        # EXECUTE: All patterns should fail
        for pattern in failure_patterns:
            with pytest.raises(ValueError) as exc_info:
                SupervisorAgent(**pattern["params"])

            error_message = str(exc_info.value)
            assert "user_context parameter" in error_message, \
                   f"Pattern '{pattern['description']}' should require user_context"

    def _create_mock_db_session(self) -> AsyncSession:
        """Create mock database session for testing."""
        mock_session = MagicMock(spec=AsyncSession)
        return mock_session

    def _create_mock_llm_manager(self) -> LLMManager:
        """Create mock LLM manager for testing."""
        mock_llm = MagicMock(spec=LLMManager)
        mock_llm.generate_response = AsyncMock()
        return mock_llm

    def _create_mock_websocket_manager(self) -> AgentWebSocketBridge:
        """Create mock WebSocket manager for testing."""
        mock_websocket = MagicMock(spec=AgentWebSocketBridge)
        mock_websocket.emit_event = AsyncMock()
        return mock_websocket

    def _create_mock_tool_dispatcher(self) -> UnifiedToolDispatcher:
        """Create mock tool dispatcher for testing."""
        mock_dispatcher = MagicMock(spec=UnifiedToolDispatcher)
        mock_dispatcher.execute_tool = AsyncMock()
        return mock_dispatcher


if __name__ == "__main__":
    pytest.main([__file__, "-v"])