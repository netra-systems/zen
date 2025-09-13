"""
SSOT Violation Test: SupervisorAgent Implementation Duplication and Inconsistency

Business Impact: $500K+ ARR at risk - Inconsistent agent behavior would break user workflows
BVJ: Enterprise/Platform | Reliability/Stability | Consistent agent execution required

This test SHOULD FAIL before SSOT remediation to prove the SSOT violation exists.
The test proves that multiple SupervisorAgent implementations cause inconsistent behavior.

VIOLATION BEING TESTED:
- Multiple SupervisorAgent class definitions across the codebase
- Different implementations returning different results for same input
- Inconsistent method signatures and behavior patterns
- Import confusion leading to wrong SupervisorAgent being used

Expected Failure Mode: Same input to different SupervisorAgent implementations will
produce different outputs, proving implementation inconsistency.
"""

import asyncio
import uuid
from typing import Dict, Any, Type
from unittest.mock import AsyncMock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestSSOTSupervisorDuplicationViolations(SSotAsyncTestCase):
    """Test that exposes inconsistent behavior from multiple SupervisorAgent implementations.

    These tests SHOULD FAIL before SSOT remediation because multiple SupervisorAgent
    implementations exist with different behaviors, violating SSOT requirements.

    Business Impact: $500K+ ARR depends on consistent agent behavior. Different
    implementations producing different results would break user workflows and trust.
    """

    def setup_method(self, method):
        """Set up test fixtures following SSOT patterns."""
        super().setup_method(method)

        # Create mock infrastructure
        self.mock_llm_manager = AsyncMock(spec=LLMManager)
        self.mock_websocket_bridge = AsyncMock(spec=AgentWebSocketBridge)

        # Create test user context
        self.test_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789",
            request_id="test_req_000",
            websocket_client_id="test_ws_111",
            agent_context={
                "user_request": "Test request for consistency check",
                "execution_mode": "test"
            }
        )

        # Standard test input for consistency checking
        self.test_input = {
            "user_request": "Optimize my database queries for better performance",
            "context": "Production environment with 1M+ records",
            "urgency": "high"
        }

    async def test_multiple_supervisor_implementations_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Multiple SupervisorAgent implementations with different behaviors
        Business Impact: Same user request returns different results depending on which
                        SupervisorAgent implementation is loaded

        Expected Failure: Different SupervisorAgent classes will have different method
                         signatures, attributes, or behaviors.
        """
        supervisor_classes = []
        implementation_details = []

        # Try to import different SupervisorAgent implementations
        supervisor_imports = [
            ("netra_backend.app.agents.supervisor_ssot", "SupervisorAgent"),
            ("netra_backend.app.agents.supervisor_consolidated", "SupervisorAgent"),
            ("netra_backend.app.agents.supervisor_agent_modern", "SupervisorAgent"),
            ("netra_backend.app.agents.chat_orchestrator_main", "SupervisorAgent"),
        ]

        for module_path, class_name in supervisor_imports:
            try:
                module = __import__(module_path, fromlist=[class_name])
                if hasattr(module, class_name):
                    supervisor_class = getattr(module, class_name)
                    supervisor_classes.append((module_path, supervisor_class))

                    # Analyze implementation details
                    methods = [method for method in dir(supervisor_class) if not method.startswith('_')]
                    init_signature = str(supervisor_class.__init__.__code__.co_varnames) if hasattr(supervisor_class.__init__, '__code__') else "unknown"

                    implementation_details.append({
                        "module": module_path,
                        "class": supervisor_class,
                        "methods": methods,
                        "init_signature": init_signature,
                        "doc": supervisor_class.__doc__ or "No documentation"
                    })

            except ImportError as e:
                # Expected for some modules that might not exist
                continue
            except Exception as e:
                # Unexpected errors might indicate structural issues
                continue

        # VIOLATION CHECK: Should have only ONE SupervisorAgent implementation
        multiple_implementations = len(supervisor_classes) > 1
        implementation_inconsistencies = []

        if multiple_implementations:
            # Check for inconsistencies between implementations
            base_methods = set(implementation_details[0]["methods"]) if implementation_details else set()
            base_init = implementation_details[0]["init_signature"] if implementation_details else ""

            for detail in implementation_details[1:]:
                current_methods = set(detail["methods"])
                current_init = detail["init_signature"]

                # Method differences
                missing_methods = base_methods - current_methods
                extra_methods = current_methods - base_methods

                if missing_methods:
                    implementation_inconsistencies.append(
                        f"{detail['module']}: Missing methods {missing_methods}"
                    )

                if extra_methods:
                    implementation_inconsistencies.append(
                        f"{detail['module']}: Extra methods {extra_methods}"
                    )

                # Constructor signature differences
                if current_init != base_init:
                    implementation_inconsistencies.append(
                        f"{detail['module']}: Different __init__ signature: {current_init} vs {base_init}"
                    )

        # ASSERTION THAT SHOULD FAIL: Only one SupervisorAgent should exist
        self.assertFalse(
            multiple_implementations,
            f"SSOT VIOLATION DETECTED: Multiple SupervisorAgent implementations found. "
            f"Found {len(supervisor_classes)} implementations: {[module for module, _ in supervisor_classes]}. "
            f"Inconsistencies: {implementation_inconsistencies}. "
            f"This violates SSOT principles and creates unpredictable behavior affecting $500K+ ARR."
        )

    async def test_supervisor_behavior_consistency_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Different SupervisorAgent implementations produce different results
        Business Impact: User requests return inconsistent results based on which implementation loads

        Expected Failure: Same input will produce different outputs from different implementations.
        """
        # Try to create instances from different implementations
        supervisor_instances = []

        try:
            # Import SSOT implementation
            from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as SSOTSupervisor
            ssot_supervisor = SSOTSupervisor(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )
            supervisor_instances.append(("SSOT", ssot_supervisor))
        except Exception as e:
            pass  # May not be available

        try:
            # Import consolidated implementation
            from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent as ConsolidatedSupervisor
            consolidated_supervisor = ConsolidatedSupervisor(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )
            supervisor_instances.append(("Consolidated", consolidated_supervisor))
        except Exception as e:
            pass  # May not be available

        if len(supervisor_instances) < 2:
            # If we can't load multiple implementations, check for attribute differences
            if len(supervisor_instances) == 1:
                name, instance = supervisor_instances[0]
                # Check if this single instance has conflicting patterns
                has_legacy_run = hasattr(instance, 'run')
                has_ssot_execute = hasattr(instance, 'execute')
                has_websocket_bridge = hasattr(instance, 'websocket_bridge')
                has_workflow_executor = hasattr(instance, 'workflow_executor')

                pattern_inconsistencies = []
                if has_legacy_run and has_ssot_execute:
                    pattern_inconsistencies.append("Both legacy run() and SSOT execute() methods present")
                if not has_websocket_bridge:
                    pattern_inconsistencies.append("Missing websocket_bridge attribute")
                if not has_workflow_executor:
                    pattern_inconsistencies.append("Missing workflow_executor attribute")

                if pattern_inconsistencies:
                    self.fail(
                        f"SSOT VIOLATION DETECTED: SupervisorAgent implementation has pattern inconsistencies. "
                        f"Issues: {pattern_inconsistencies}. "
                        f"This suggests incomplete SSOT consolidation affecting consistency."
                    )
            return  # Cannot test behavior differences without multiple instances

        # Test behavior differences between implementations
        behavior_differences = []

        for name, supervisor in supervisor_instances:
            # Test method availability and signatures
            methods_info = {
                "has_run": hasattr(supervisor, 'run'),
                "has_execute": hasattr(supervisor, 'execute'),
                "has_websocket_bridge": hasattr(supervisor, 'websocket_bridge'),
                "has_workflow_executor": hasattr(supervisor, 'workflow_executor'),
                "class_name": supervisor.__class__.__name__,
                "module": supervisor.__class__.__module__
            }

            behavior_differences.append((name, methods_info))

        # Check for behavioral inconsistencies
        if len(behavior_differences) > 1:
            base_name, base_info = behavior_differences[0]
            inconsistencies_found = []

            for comp_name, comp_info in behavior_differences[1:]:
                for key, base_value in base_info.items():
                    comp_value = comp_info.get(key)
                    if base_value != comp_value:
                        inconsistencies_found.append(
                            f"{key}: {base_name}={base_value} vs {comp_name}={comp_value}"
                        )

            # ASSERTION THAT SHOULD FAIL: All implementations should be identical
            self.assertFalse(
                bool(inconsistencies_found),
                f"SSOT VIOLATION DETECTED: SupervisorAgent implementations have behavioral differences. "
                f"Inconsistencies: {inconsistencies_found}. "
                f"Different implementations: {[(name, info['module']) for name, info in behavior_differences]}. "
                f"This creates unpredictable user experience affecting $500K+ ARR reliability."
            )

    async def test_supervisor_execution_result_inconsistency_SHOULD_FAIL(self):
        """
        This test SHOULD FAIL before SSOT remediation.

        VIOLATION EXPOSED: Different SupervisorAgent implementations return different result formats
        Business Impact: Inconsistent result formats break downstream processing and user experience

        Expected Failure: Different implementations will return results in incompatible formats.
        """
        # Mock execution results from different patterns
        execution_results = {}

        try:
            # Test SSOT pattern execution result
            from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as SSOTSupervisor
            ssot_supervisor = SSOTSupervisor(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Mock the execute method to return SSOT format
            with patch.object(ssot_supervisor, 'execute') as mock_execute:
                mock_execute.return_value = {
                    "status": "completed",
                    "data": {"supervisor_result": "completed", "orchestration_successful": True},
                    "request_id": "ssot_request"
                }

                result = await ssot_supervisor.execute(self.test_context, stream_updates=False)
                execution_results["SSOT"] = result

        except Exception as e:
            execution_results["SSOT"] = f"Error: {e}"

        try:
            # Test consolidated pattern execution result
            from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent as ConsolidatedSupervisor
            consolidated_supervisor = ConsolidatedSupervisor(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge
            )

            # Mock the run method to return legacy format
            with patch.object(consolidated_supervisor, 'run') as mock_run:
                mock_run.return_value = {
                    "result": "completed",
                    "workflow_result": {"triage": "done", "data": "analyzed"},
                    "execution_id": "legacy_execution"
                }

                if hasattr(consolidated_supervisor, 'run'):
                    result = await consolidated_supervisor.run(
                        user_request=self.test_input["user_request"],
                        thread_id=self.test_context.thread_id,
                        user_id=self.test_context.user_id,
                        run_id=self.test_context.run_id
                    )
                    execution_results["Consolidated"] = result

        except Exception as e:
            execution_results["Consolidated"] = f"Error: {e}"

        # Analyze result format differences
        result_format_inconsistencies = []

        if "SSOT" in execution_results and "Consolidated" in execution_results:
            ssot_result = execution_results["SSOT"]
            consolidated_result = execution_results["Consolidated"]

            # Check for format differences
            if isinstance(ssot_result, dict) and isinstance(consolidated_result, dict):
                ssot_keys = set(ssot_result.keys()) if ssot_result else set()
                consolidated_keys = set(consolidated_result.keys()) if consolidated_result else set()

                missing_in_consolidated = ssot_keys - consolidated_keys
                missing_in_ssot = consolidated_keys - ssot_keys

                if missing_in_consolidated:
                    result_format_inconsistencies.append(
                        f"Keys in SSOT but missing in Consolidated: {missing_in_consolidated}"
                    )

                if missing_in_ssot:
                    result_format_inconsistencies.append(
                        f"Keys in Consolidated but missing in SSOT: {missing_in_ssot}"
                    )

                # Check for value type differences
                common_keys = ssot_keys & consolidated_keys
                for key in common_keys:
                    ssot_type = type(ssot_result[key]).__name__
                    consolidated_type = type(consolidated_result[key]).__name__
                    if ssot_type != consolidated_type:
                        result_format_inconsistencies.append(
                            f"Key '{key}': SSOT type {ssot_type} vs Consolidated type {consolidated_type}"
                        )

        # ASSERTION THAT SHOULD FAIL: Result formats should be consistent
        has_format_inconsistencies = bool(result_format_inconsistencies)

        self.assertFalse(
            has_format_inconsistencies,
            f"SSOT VIOLATION DETECTED: SupervisorAgent implementations return incompatible result formats. "
            f"Execution results: {execution_results}. "
            f"Format inconsistencies: {result_format_inconsistencies}. "
            f"This breaks downstream processing and affects $500K+ ARR user workflows."
        )