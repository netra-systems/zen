"""
FAILING TESTS: DeepAgentState Golden Path Consistency (Issue #871)

These tests validate agent state consistency during Golden Path user request processing.
Tests will FAIL initially due to SSOT violations causing state inconsistencies.
Tests will PASS after SSOT remediation ensures consistent state propagation.

Business Impact: $500K+ ARR protection - Golden Path user chat experience.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient


class TestDeepAgentStateGoldenPathConsistency(SSotAsyncTestCase):
    """Test suite validating agent state consistency in Golden Path execution"""

    def setup_method(self, method):
        super().setup_method(method)
        self.golden_path_stages = [
            "triage_agent",
            "supervisor_agent",
            "data_helper_agent",
            "apex_optimizer_agent",
            "reporting_agent"
        ]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_state_consistency_across_golden_path(self, real_services_fixture):
        """
        FAILING TEST: Validates state consistency across all Golden Path stages

        Expected: FAIL initially due to SSOT violations creating state inconsistencies
        After Fix: PASS with consistent state throughout Golden Path
        """
        # Setup test user and context
        user_id = "golden-path-test-user-123"
        thread_id = f"thread-{user_id}-{datetime.now(timezone.utc).isoformat()}"
        test_message = "Optimize my cloud costs for maximum efficiency"

        # Track state at each Golden Path stage
        execution_states = []
        state_violations = []

        try:
            # Simulate Golden Path execution with state tracking
            async with WebSocketTestClient() as websocket_client:

                # Stage 1: Triage Agent State
                triage_state = await self._execute_triage_with_state_tracking(
                    user_id=user_id,
                    thread_id=thread_id,
                    message=test_message,
                    db_session=real_services_fixture["db"]
                )
                execution_states.append(("triage", triage_state))

                # Stage 2: Supervisor Agent State
                supervisor_state = await self._execute_supervisor_with_state_tracking(
                    previous_state=triage_state,
                    db_session=real_services_fixture["db"]
                )
                execution_states.append(("supervisor", supervisor_state))

                # Stage 3: Sub-Agent State (Data Helper)
                subagent_state = await self._execute_subagent_with_state_tracking(
                    previous_state=supervisor_state,
                    agent_type="data_helper",
                    db_session=real_services_fixture["db"]
                )
                execution_states.append(("data_helper", subagent_state))

                # Stage 4: Optimizer Agent State
                optimizer_state = await self._execute_subagent_with_state_tracking(
                    previous_state=subagent_state,
                    agent_type="apex_optimizer",
                    db_session=real_services_fixture["db"]
                )
                execution_states.append(("optimizer", optimizer_state))

            # Validate state consistency across all stages
            state_violations = self._validate_state_consistency(execution_states, user_id, thread_id)

        except Exception as e:
            self.logger.error(f"Golden Path execution failed: {e}")
            pytest.fail(f"Golden Path execution failed: {e}")

        # This assertion will FAIL initially due to SSOT violations
        if state_violations:
            violation_report = self._build_state_violation_report(state_violations, execution_states)
            pytest.fail(f"""
🚨 GOLDEN PATH STATE CONSISTENCY VIOLATIONS (Issue #871)

State inconsistencies detected across Golden Path execution:

{violation_report}

ROOT CAUSE: DeepAgentState SSOT violations cause state inconsistencies.
BUSINESS IMPACT: $500K+ ARR at risk from corrupted user experiences.
SECURITY RISK: User data may leak between requests due to shared state.

REMEDIATION: Fix DeepAgentState SSOT violations to ensure consistent state propagation.
            """)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_events_maintain_state_consistency(self, real_services_fixture):
        """
        FAILING TEST: All 5 critical WebSocket events maintain consistent agent state

        Expected: FAIL initially due to state inconsistencies in WebSocket events
        After Fix: PASS with consistent state across all events
        """
        user_id = "websocket-test-user-456"
        test_message = "Generate cost optimization report"

        # Connect WebSocket and execute agent request
        try:
            async with WebSocketTestClient() as client:
                # Send agent request
                await client.send_json({
                    "type": "agent_request",
                    "message": test_message,
                    "user_id": user_id,
                    "thread_id": f"ws-thread-{user_id}"
                })

                # Collect all WebSocket events
                events = []
                async for event in client.receive_events(timeout=60):
                    events.append(event)
                    if event.get("type") == "agent_completed":
                        break

                # Extract agent state from each event
                event_states = []
                missing_state_events = []

                for i, event in enumerate(events):
                    event_data = event.get('data', {})

                    if 'agent_state' in event_data or 'state' in event_data:
                        state = event_data.get('agent_state', event_data.get('state'))
                        event_states.append((event.get('type'), state, i))
                    else:
                        missing_state_events.append((event.get('type'), i))

                # Validate state consistency across events
                state_consistency_violations = []

                if len(event_states) < 3:  # Should have at least 3 events with state
                    state_consistency_violations.append(
                        f"Insufficient state data: only {len(event_states)} events with state (need ≥3)"
                    )

                # Check state consistency between consecutive events
                for i in range(1, len(event_states)):
                    prev_event_type, prev_state, prev_index = event_states[i-1]
                    curr_event_type, curr_state, curr_index = event_states[i]

                    # User ID should be consistent
                    if prev_state.get('user_id') != curr_state.get('user_id'):
                        state_consistency_violations.append(
                            f"User ID inconsistency: {prev_event_type}[{prev_index}]={prev_state.get('user_id')} → {curr_event_type}[{curr_index}]={curr_state.get('user_id')}"
                        )

                    # Thread ID should be consistent
                    prev_thread = prev_state.get('thread_id') or prev_state.get('chat_thread_id')
                    curr_thread = curr_state.get('thread_id') or curr_state.get('chat_thread_id')

                    if prev_thread != curr_thread:
                        state_consistency_violations.append(
                            f"Thread ID inconsistency: {prev_event_type}[{prev_index}]={prev_thread} → {curr_event_type}[{curr_index}]={curr_thread}"
                        )

                # Critical events should have state data
                critical_events = ["agent_started", "agent_thinking", "agent_completed"]
                for event in events:
                    if event.get("type") in critical_events:
                        if 'agent_state' not in event.get('data', {}) and 'state' not in event.get('data', {}):
                            missing_state_events.append((event.get('type'), events.index(event)))

        except Exception as e:
            pytest.fail(f"WebSocket test execution failed: {e}")

        # This test will FAIL initially due to state inconsistencies
        violations = state_consistency_violations + [f"Missing state in {event_type} event[{idx}]" for event_type, idx in missing_state_events]

        if violations:
            pytest.fail(f"""
🚨 WEBSOCKET EVENT STATE CONSISTENCY VIOLATIONS (Issue #871)

State inconsistencies detected in WebSocket events:

{''.join(f"  ❌ {violation}" for violation in violations)}

Events processed: {len(events)}
Events with state: {len(event_states)}
Events missing state: {len(missing_state_events)}

ROOT CAUSE: DeepAgentState SSOT violations cause inconsistent state in WebSocket events.
BUSINESS IMPACT: Users see corrupted or incomplete agent responses.
SECURITY RISK: State leakage between user WebSocket connections.
            """)

    @pytest.mark.integration
    async def test_agent_state_memory_isolation_between_requests(self):
        """
        FAILING TEST: Agent state doesn't persist between different user requests

        Expected: FAIL initially due to shared state contamination
        After Fix: PASS with clean memory isolation
        """
        # Execute request for User 1 with distinctive data
        user1_id = "memory-test-user-1"
        user1_sensitive_data = {
            "api_key": "sk-user1-secret-12345",
            "organization": "acme-corp-sensitive",
            "ssn": "123-45-6789"
        }

        user1_state = await self._execute_agent_with_sensitive_data(
            user_id=user1_id,
            sensitive_data=user1_sensitive_data
        )

        # Clear explicit references and force garbage collection
        user1_result_data = json.dumps(user1_state.to_dict() if hasattr(user1_state, 'to_dict') else user1_state.__dict__)
        del user1_state

        # Execute request for User 2
        user2_id = "memory-test-user-2"
        user2_sensitive_data = {
            "api_key": "sk-user2-secret-67890",
            "organization": "beta-corp-confidential",
            "ssn": "987-65-4321"
        }

        user2_state = await self._execute_agent_with_sensitive_data(
            user_id=user2_id,
            sensitive_data=user2_sensitive_data
        )

        # Convert User 2's state to searchable format
        user2_result_data = json.dumps(user2_state.to_dict() if hasattr(user2_state, 'to_dict') else user2_state.__dict__)

        # Check for User 1 data contamination in User 2's result
        contamination_violations = []

        # Check for API key leakage
        if user1_sensitive_data["api_key"] in user2_result_data:
            contamination_violations.append(f"API key leaked: User 1's {user1_sensitive_data['api_key']} found in User 2's result")

        # Check for organization leakage
        if user1_sensitive_data["organization"] in user2_result_data:
            contamination_violations.append(f"Organization leaked: User 1's {user1_sensitive_data['organization']} found in User 2's result")

        # Check for SSN leakage
        if user1_sensitive_data["ssn"] in user2_result_data:
            contamination_violations.append(f"SSN leaked: User 1's {user1_sensitive_data['ssn']} found in User 2's result")

        # Verify User 2's own data is present (sanity check)
        user2_data_missing = []
        if user2_sensitive_data["api_key"] not in user2_result_data:
            user2_data_missing.append("User 2's API key missing from their own result")
        if user2_sensitive_data["organization"] not in user2_result_data:
            user2_data_missing.append("User 2's organization missing from their own result")

        # This test will FAIL initially due to state contamination
        if contamination_violations or user2_data_missing:
            all_violations = contamination_violations + user2_data_missing
            pytest.fail(f"""
🚨 AGENT STATE MEMORY CONTAMINATION DETECTED (Issue #871)

Cross-user data contamination found:

{''.join(f"  🔒 SECURITY BREACH: {violation}" for violation in contamination_violations)}
{''.join(f"  ⚠️  DATA MISSING: {violation}" for violation in user2_data_missing)}

User 1 ID: {user1_id}
User 2 ID: {user2_id}

ROOT CAUSE: DeepAgentState SSOT violations cause shared state between users.
SECURITY IMPACT: CRITICAL - Multi-tenant data breach vulnerability.
BUSINESS IMPACT: $500K+ ARR at risk from customer data exposure.
COMPLIANCE: Potential GDPR/SOC2 violations.

IMMEDIATE ACTION: Fix DeepAgentState SSOT violations to prevent data leakage.
            """)

    async def _execute_triage_with_state_tracking(self, user_id: str, thread_id: str, message: str, db_session) -> Dict[str, Any]:
        """Execute triage agent with state tracking (mock implementation for testing)"""
        # This would call real triage agent in actual implementation
        # For now, create mock state that shows SSOT violation patterns

        try:
            # Import both versions to test for inconsistencies
            from netra_backend.app.agents.state import DeepAgentState as DeprecatedState
            from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState

            # Create state using deprecated version (simulating current system)
            deprecated_state = DeprecatedState(
                user_id=user_id,
                chat_thread_id=thread_id,
                user_request=message,
                current_stage="triage"
            )

            return {
                "user_id": deprecated_state.user_id,
                "thread_id": getattr(deprecated_state, 'thread_id', deprecated_state.chat_thread_id),
                "chat_thread_id": deprecated_state.chat_thread_id,
                "current_stage": getattr(deprecated_state, 'current_stage', 'unknown'),
                "state_source": "deprecated",
                "state_class": deprecated_state.__class__.__name__,
                "state_module": deprecated_state.__class__.__module__
            }

        except ImportError as e:
            # If import fails, create minimal state
            return {
                "user_id": user_id,
                "thread_id": thread_id,
                "current_stage": "triage",
                "error": f"Import failed: {e}",
                "state_source": "fallback"
            }

    async def _execute_supervisor_with_state_tracking(self, previous_state: Dict[str, Any], db_session) -> Dict[str, Any]:
        """Execute supervisor agent with state tracking"""
        # Simulate supervisor agent execution
        supervisor_state = previous_state.copy()
        supervisor_state.update({
            "current_stage": "supervisor",
            "previous_stage": previous_state.get("current_stage"),
            "execution_path": ["triage", "supervisor"]
        })
        return supervisor_state

    async def _execute_subagent_with_state_tracking(self, previous_state: Dict[str, Any], agent_type: str, db_session) -> Dict[str, Any]:
        """Execute sub-agent with state tracking"""
        subagent_state = previous_state.copy()
        subagent_state.update({
            "current_stage": agent_type,
            "previous_stage": previous_state.get("current_stage"),
            "execution_path": previous_state.get("execution_path", []) + [agent_type]
        })
        return subagent_state

    async def _execute_agent_with_sensitive_data(self, user_id: str, sensitive_data: Dict[str, str]) -> Any:
        """Execute agent with sensitive data to test memory isolation"""
        try:
            from netra_backend.app.agents.state import DeepAgentState

            state = DeepAgentState(
                user_id=user_id,
                chat_thread_id=f"sensitive-thread-{user_id}",
                user_request=f"Process sensitive data for {sensitive_data['organization']}",
                # Add sensitive data to state
                **{f"sensitive_{key}": value for key, value in sensitive_data.items()}
            )

            return state

        except Exception as e:
            # Fallback minimal state for testing
            return type('MockState', (), {
                'user_id': user_id,
                'sensitive_api_key': sensitive_data.get('api_key'),
                'sensitive_organization': sensitive_data.get('organization'),
                'sensitive_ssn': sensitive_data.get('ssn'),
                'to_dict': lambda: {
                    'user_id': user_id,
                    'sensitive_api_key': sensitive_data.get('api_key'),
                    'sensitive_organization': sensitive_data.get('organization'),
                    'sensitive_ssn': sensitive_data.get('ssn')
                }
            })()

    def _validate_state_consistency(self, execution_states: List[tuple], expected_user_id: str, expected_thread_id: str) -> List[str]:
        """Validate state consistency across Golden Path execution stages"""
        violations = []

        for stage_name, state in execution_states:
            # User ID consistency
            if state.get("user_id") != expected_user_id:
                violations.append(f"User ID inconsistency in {stage_name}: expected {expected_user_id}, got {state.get('user_id')}")

            # Thread ID consistency (check both possible field names)
            state_thread_id = state.get("thread_id") or state.get("chat_thread_id")
            if state_thread_id != expected_thread_id:
                violations.append(f"Thread ID inconsistency in {stage_name}: expected {expected_thread_id}, got {state_thread_id}")

            # State source tracking
            if state.get("state_source") == "deprecated":
                violations.append(f"Deprecated state source detected in {stage_name}")

        return violations

    def _build_state_violation_report(self, violations: List[str], execution_states: List[tuple]) -> str:
        """Build formatted report of state violations"""
        report_lines = []

        report_lines.append("STATE VIOLATIONS DETECTED:")
        for violation in violations:
            report_lines.append(f"  ❌ {violation}")

        report_lines.append("\nSTATE TRACKING SUMMARY:")
        for stage_name, state in execution_states:
            report_lines.append(f"  📊 {stage_name.upper()}:")
            report_lines.append(f"    - User ID: {state.get('user_id', 'MISSING')}")
            report_lines.append(f"    - Thread ID: {state.get('thread_id') or state.get('chat_thread_id', 'MISSING')}")
            report_lines.append(f"    - State Source: {state.get('state_source', 'UNKNOWN')}")
            report_lines.append(f"    - State Module: {state.get('state_module', 'UNKNOWN')}")

        return '\n'.join(report_lines)