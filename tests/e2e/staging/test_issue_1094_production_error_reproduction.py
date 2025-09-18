"""
Test Issue #1094: Production Error Reproduction in Staging Environment

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Validate production TypeError exists in staging before remediation
- Value Impact: Prevent agent stop operation failures affecting 500K+ ARR
- Revenue Impact: Ensure reliable agent lifecycle management across environments

Test Strategy:
1. Reproduce the exact TypeError occurring in production lines 194/202
2. Validate staging environment mirrors production async/await interface issues
3. Test both primary and fallback code paths in agent_service_core.py
4. Ensure comprehensive coverage of WebSocket manager interface patterns

Root Cause Validation:
- agent_service_core.py lines 194 and 202 await synchronous create_websocket_manager
- Both primary and fallback paths have identical interface error
- Production logs show TypeError: object UserExecutionContext can't be used in 'await' expression
"""

import pytest
import asyncio
from typing import Dict, Any

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.mark.e2e
class Issue1094ProductionErrorReproductionTests(BaseIntegrationTest):
    """Staging environment tests to reproduce Issue #1094 production errors."""

    @pytest.mark.staging
    @pytest.mark.critical
    async def test_staging_agent_service_core_interface_error_reproduction(self):
        """
        STAGING TEST: Reproduce exact TypeError from agent_service_core.py lines 194/202.

        This test validates that staging environment experiences the same async/await
        interface errors that are occurring in production, confirming the issue
        exists across environments before implementing the fix.
        """
        from netra_backend.app.services.agent_service_core import AgentService
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from unittest.mock import Mock
        from netra_backend.app.llm.manager import LLMManager

        # Create realistic test environment matching production
        mock_llm_manager = Mock(spec=LLMManager)
        supervisor = SupervisorAgent(llm_manager=mock_llm_manager)
        agent_service = AgentService(supervisor)
        test_user_id = "staging_test_user_1094"

        # This should trigger the TypeError on lines 194 or 202 in agent_service_core.py
        with pytest.raises(TypeError, match="object UserExecutionContext can't be used in 'await' expression|object is not awaitable"):
            await agent_service.stop_agent(test_user_id)

    @pytest.mark.staging
    @pytest.mark.critical
    async def test_staging_websocket_manager_interface_validation(self):
        """
        STAGING TEST: Validate WebSocket manager interface patterns in staging.

        This test confirms that the interface issue exists in the WebSocket
        manager factory patterns, providing evidence for the remediation approach.
        """
        from netra_backend.app.websocket_core import create_websocket_manager
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Create test user context
        user_context = UserExecutionContext(
            user_id="staging_interface_test_user",
            thread_id="staging_thread_456",
            request_id="staging_request_789",
            websocket_client_id="ws_staging_101",
            run_id="staging_run_123"
        )

        # Test what actually happens in production
        try:
            # This actually works (create_websocket_manager is async and returns a context)
            websocket_manager = await create_websocket_manager(user_context)

            # The REAL issue: context doesn't have send_to_user method
            # This will cause AttributeError when production code tries to call it
            with pytest.raises(AttributeError, match="'UserExecutionContext' object has no attribute 'send_to_user'"):
                await websocket_manager.send_to_user("test_user", {"type": "test"})

        except Exception as e:
            self.fail(f"Unexpected error in interface validation: {e}")

    @pytest.mark.staging
    async def test_staging_correct_async_interface_validation(self):
        """
        STAGING TEST: Validate correct async interface works in staging.

        This test confirms that the proposed fix (using get_websocket_manager)
        works correctly in the staging environment.
        """
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Create proper user context
        user_context = UserExecutionContext(
            user_id="staging_async_test_user",
            thread_id="staging_async_thread_456",
            request_id="staging_async_request_789",
            websocket_client_id="ws_staging_async_101",
            run_id="staging_async_run_123"
        )

        # This should work correctly (async interface)
        try:
            websocket_manager = get_websocket_manager(user_context=user_context)
            assert websocket_manager is not None, "get_websocket_manager should return manager in staging"
            assert hasattr(websocket_manager, 'send_to_user'), "Manager should have send_to_user method"
        except Exception as e:
            self.fail(f"Correct async interface should work in staging: {e}")

    @pytest.mark.staging
    @pytest.mark.critical
    async def test_staging_agent_stop_operation_both_paths_error(self):
        """
        STAGING TEST: Validate both primary and fallback paths fail with TypeError.

        This test confirms that both code paths in agent_service_core.py (lines 194 and 202)
        have the same interface error, ensuring comprehensive fix coverage.
        """
        from netra_backend.app.services.agent_service_core import AgentService
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from unittest.mock import patch, AsyncMock, Mock
        from netra_backend.app.llm.manager import LLMManager

        mock_llm_manager = Mock(spec=LLMManager)
        supervisor = SupervisorAgent(llm_manager=mock_llm_manager)
        agent_service = AgentService(supervisor)
        test_user_id = "staging_both_paths_test_user"

        # Test 1: Primary path (bridge available scenario)
        with patch.object(agent_service, '_ensure_bridge_ready', return_value=True):
            mock_bridge = AsyncMock()
            mock_bridge.get_status.return_value = {
                "dependencies": {"websocket_manager_available": True}
            }
            agent_service._bridge = mock_bridge

            # This should trigger TypeError on line 194
            with pytest.raises(TypeError, match="object UserExecutionContext can't be used in 'await' expression|object is not awaitable"):
                await agent_service.stop_agent(test_user_id)

        # Test 2: Fallback path (bridge unavailable scenario)
        with patch.object(agent_service, '_ensure_bridge_ready', return_value=False):
            # This should trigger TypeError on line 202
            with pytest.raises(TypeError, match="object UserExecutionContext can't be used in 'await' expression|object is not awaitable"):
                await agent_service.stop_agent(test_user_id)

    @pytest.mark.staging
    async def test_staging_golden_path_impact_assessment(self):
        """
        STAGING TEST: Assess Golden Path impact from async/await interface errors.

        This test validates that the interface error blocks critical Golden Path
        functionality, confirming the business impact and urgency of the fix.
        """
        from netra_backend.app.services.agent_service_core import AgentService
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from unittest.mock import Mock
        from netra_backend.app.llm.manager import LLMManager

        # Simulate Golden Path user scenario
        golden_path_user_id = "golden_path_user_1094_test"

        mock_llm_manager = Mock(spec=LLMManager)
        supervisor = SupervisorAgent(llm_manager=mock_llm_manager)
        agent_service = AgentService(supervisor)

        # Track Golden Path functionality impact
        golden_path_functions_blocked = []

        # Test agent stop operation (critical for Golden Path)
        try:
            await agent_service.stop_agent(golden_path_user_id)
        except TypeError as e:
            if "can't be used in 'await' expression" in str(e):
                golden_path_functions_blocked.append("agent_stop_operation")
        except Exception:
            # Other errors not related to async/await interface
            pass

        # Validate business impact
        assert len(golden_path_functions_blocked) > 0, \
            "Issue #1094 should block critical Golden Path functionality"
        assert "agent_stop_operation" in golden_path_functions_blocked, \
            "Agent stop operations should be blocked by async/await interface error"

        # Document specific functions affected for remediation priority
        print(f"Golden Path functions blocked by Issue #1094: {golden_path_functions_blocked}")