"MISSION CRITICAL: WebSocket Event Structure Golden Path - Issue #1021

CRITICAL BUSINESS REQUIREMENT: This test MUST pass 100% after unified_manager.py fix.
Business Value: $500K+ ARR - WebSocket events enable 90% of platform chat value.

PURPOSE: Validate that all 5 critical WebSocket events (agent_started, agent_thinking,
tool_executing, tool_completed, agent_completed) contain business data at the correct
structural level for Golden Path user flow.

ISSUE #1021: unified_manager.py incorrectly wraps business event data, hiding critical
fields like tool_name, execution_time, and results from frontend consumers.

ANY FAILURE HERE BLOCKS DEPLOYMENT.
""

import asyncio
import json
import time
import pytest
from datetime import datetime, timezone
from typing import Dict, List, Any

from tests.mission_critical.websocket_real_test_base import RealWebSocketTestBase
from test_framework.test_context import create_test_context


class WebSocketEventStructureGoldenPathTests(RealWebSocketTestBase):
    ""Mission Critical test suite for WebSocket event structure Golden Path compliance."

    @pytest.mark.mission_critical
    async def test_golden_path_websocket_event_structures_complete(self):
        "MISSION CRITICAL: Test all 5 Golden Path WebSocket events have correct structure.

        GOLDEN PATH REQUIREMENT: User must see real-time agent progress with proper business
        data visibility. This requires top-level business fields in WebSocket events.

        FAILS BEFORE FIX: Business fields wrapped in 'payload'/'data' preventing access
        PASSES AFTER FIX: All business fields at top level as expected by frontend

        Business Impact: Without proper event structure, users cannot see agent progress,
        tool execution transparency, or completion status - breaking chat experience.
        ""
        # Create test context for Golden Path user flow
        test_context = await create_test_context()
        user_id = test_context.user_id

        # Simulate Golden Path agent execution with all 5 critical events
        golden_path_events = [
            {
                type": "agent_started,
                user_id": user_id,
                "thread_id: thread_123",
                "agent_name: DataHelperAgent",
                "task_description: Analyze user data request",
                "run_id: frun_{int(time.time())}",
                "timestamp: time.time()
            },
            {
                type": "agent_thinking,
                reasoning": "I need to analyze the user's request and determine what tools to use,
                agent_name": "DataHelperAgent,
                step_number": 1,
                "timestamp: time.time()
            },
            {
                type": "tool_executing,
                tool_name": "data_analyzer,
                tool_args": {"query: user data patterns", "depth: comprehensive"},
                "execution_id: exec_456",
                "agent_name: DataHelperAgent",
                "timestamp: time.time()
            },
            {
                type": "tool_completed,
                tool_name": "data_analyzer,
                results": {
                    "patterns_found: 12,
                    insights": ["Data trend identified, Optimization opportunity found"],
                    "confidence: 0.85
                },
                execution_time": 3.42,
                "success: True,
                execution_id": "exec_456,
                agent_name": "DataHelperAgent,
                timestamp": time.time()
            },
            {
                "type: agent_completed",
                "agent_name: DataHelperAgent",
                "final_response: Analysis complete. Found 12 patterns with high confidence insights.",
                "status: success",
                "duration_ms: 8500,
                run_id": f"run_{int(time.time())},
                timestamp": time.time()
            }
        ]

        # Get WebSocket manager for testing
        websocket_manager = await self.get_websocket_manager(user_id)

        # Process each Golden Path event through WebSocket transmission pipeline
        structure_validation_failures = []

        for event in golden_path_events:
            event_type = event["type]

            try:
                # Test the serialization that occurs during WebSocket transmission
                from netra_backend.app.websocket_core.websocket_manager import _serialize_message_safely
                transmitted_event = _serialize_message_safely(event)

                # GOLDEN PATH STRUCTURE VALIDATION: Business fields must be at top level
                if event_type == agent_started":
                    required_top_level_fields = ["user_id, thread_id", "agent_name, task_description", "run_id]
                    for field in required_top_level_fields:
                        if field not in transmitted_event:
                            structure_validation_failures.append(
                                fGOLDEN PATH FAILURE: {event_type} missing top-level {field}. "
                                f"Event: {transmitted_event}
                            )

                elif event_type == agent_thinking":
                    required_top_level_fields = ["reasoning, agent_name", "step_number]
                    for field in required_top_level_fields:
                        if field not in transmitted_event:
                            structure_validation_failures.append(
                                fGOLDEN PATH FAILURE: {event_type} missing top-level {field}. "
                                f"Event: {transmitted_event}
                            )

                elif event_type == tool_executing":
                    # CRITICAL: tool_name and tool_args MUST be at top level for transparency
                    required_top_level_fields = ["tool_name, tool_args", "execution_id, agent_name"]
                    for field in required_top_level_fields:
                        if field not in transmitted_event:
                            structure_validation_failures.append(
                                f"GOLDEN PATH CRITICAL FAILURE: {event_type} missing top-level {field}. 
                                fTool transparency broken. Event: {transmitted_event}"
                            )

                    # Validate tool_name value preservation
                    if transmitted_event.get("tool_name) != event[tool_name"]:
                        structure_validation_failures.append(
                            f"GOLDEN PATH FAILURE: {event_type} tool_name value corrupted. 
                            fExpected: {event['tool_name']}, Got: {transmitted_event.get('tool_name')}"
                        )

                elif event_type == "tool_completed:
                    # CRITICAL: results, execution_time, tool_name MUST be at top level
                    required_top_level_fields = [tool_name", "results, execution_time", "success]
                    for field in required_top_level_fields:
                        if field not in transmitted_event:
                            structure_validation_failures.append(
                                fGOLDEN PATH CRITICAL FAILURE: {event_type} missing top-level {field}. "
                                f"Tool completion transparency broken. Event: {transmitted_event}
                            )

                    # Validate results structure preservation
                    if results" in transmitted_event and isinstance(transmitted_event["results], dict):
                        original_results = event[results"]
                        transmitted_results = transmitted_event["results]
                        if transmitted_results != original_results:
                            structure_validation_failures.append(
                                fGOLDEN PATH FAILURE: {event_type} results structure corrupted. "
                                f"Original: {original_results}, Transmitted: {transmitted_results}
                            )

                elif event_type == agent_completed":
                    # CRITICAL: final_response, status must be at top level for completion UI
                    required_top_level_fields = ["final_response, status", "duration_ms, agent_name"]
                    for field in required_top_level_fields:
                        if field not in transmitted_event:
                            structure_validation_failures.append(
                                f"GOLDEN PATH CRITICAL FAILURE: {event_type} missing top-level {field}. 
                                fCompletion status broken. Event: {transmitted_event}"
                            )

            except Exception as e:
                structure_validation_failures.append(
                    f"GOLDEN PATH TRANSMISSION FAILURE: {event_type} failed during serialization: {e}
                )

        # MISSION CRITICAL ASSERTION: Golden Path event structure must be 100% correct
        if structure_validation_failures:
            failure_report = \n".join(structure_validation_failures)
            pytest.fail(
                f"MISSION CRITICAL FAILURE - Issue #1021 WebSocket Event Structure (Golden Path):\n\n
                f{failure_report}\n\n"
                f"BUSINESS IMPACT: $500K+ ARR at risk - Users cannot see agent progress in real-time chat.\n
                fROOT CAUSE: unified_manager.py incorrectly wraps business data preventing frontend access.\n"
                f"REQUIRED FIX: Preserve business fields at top level during WebSocket transmission.
            )

    @pytest.mark.mission_critical
    async def test_websocket_transmission_end_to_end_structure(self):
        ""MISSION CRITICAL: Test complete WebSocket transmission preserves event structure.

        END-TO-END TEST: Validates that emit_critical_event -> WebSocket transmission ->
        frontend reception maintains proper business field structure throughout.
        "
        test_context = await create_test_context()
        user_id = test_context.user_id

        # Get real WebSocket manager
        websocket_manager = await self.get_websocket_manager(user_id)

        # Mock WebSocket connection to capture transmitted data
        transmitted_events = []

        class MockWebSocket:
            async def send_json(self, data):
                transmitted_events.append(data)

        # Create mock connection
        mock_connection = type('MockConnection', (), {
            'websocket': MockWebSocket(),
            'connection_id': 'test_conn_123'
        }()

        # Add connection to manager
        await websocket_manager.add_connection(mock_connection)
        websocket_manager._user_connections[user_id] = {"test_conn_123}

        # Test critical business events through complete transmission pipeline
        critical_business_events = [
            {
                event_type": "tool_executing,
                data": {
                    "tool_name: critical_analyzer",
                    "tool_args: {priority": "high, scope": "comprehensive},
                    execution_id": "critical_exec_789,
                    timestamp": time.time()
                }
            },
            {
                "event_type: tool_completed",
                "data: {
                    tool_name": "critical_analyzer,
                    results": {
                        "status: success",
                        "critical_findings: [Issue A resolved", "Performance improved 40%],
                        metrics": {"execution_time: 2.8, accuracy": 0.95}
                    },
                    "execution_time: 2.8,
                    success": True,
                    "execution_id: critical_exec_789"
                }
            }
        ]

        # Emit events through complete WebSocket pipeline
        for event_config in critical_business_events:
            await websocket_manager.emit_critical_event(
                user_id=user_id,
                event_type=event_config["event_type],
                data=event_config[data"]

        # Validate transmitted event structures
        assert len(transmitted_events) == 2, f"Expected 2 transmitted events, got {len(transmitted_events)}

        transmission_failures = []

        for i, transmitted_event in enumerate(transmitted_events):
            original_event = critical_business_events[i]
            event_type = original_event[event_type"]
            original_data = original_event["data]

            # CRITICAL VALIDATION: All business fields must be accessible at top level
            if event_type == tool_executing":
                if "tool_name not in transmitted_event:
                    transmission_failures.append(
                        ftool_executing transmission missing tool_name: {transmitted_event}"
                    )
                if transmitted_event.get("tool_name) != original_data[tool_name"]:
                    transmission_failures.append(
                        f"tool_executing tool_name corrupted during transmission
                    )
                if tool_args" not in transmitted_event:
                    transmission_failures.append(
                        f"tool_executing transmission missing tool_args: {transmitted_event}
                    )

            elif event_type == tool_completed":
                if "tool_name not in transmitted_event:
                    transmission_failures.append(
                        ftool_completed transmission missing tool_name: {transmitted_event}"
                    )
                if "results not in transmitted_event:
                    transmission_failures.append(
                        ftool_completed transmission missing results: {transmitted_event}"
                    )
                if "execution_time not in transmitted_event:
                    transmission_failures.append(
                        ftool_completed transmission missing execution_time: {transmitted_event}"
                    )

                # Validate results structure preservation
                if "results in transmitted_event:
                    transmitted_results = transmitted_event[results"]
                    original_results = original_data["results]
                    if transmitted_results != original_results:
                        transmission_failures.append(
                            ftool_completed results structure corrupted during transmission"
                        )

        # MISSION CRITICAL: No transmission structure failures allowed
        if transmission_failures:
            failure_summary = "\n.join(transmission_failures)
            pytest.fail(
                fMISSION CRITICAL: WebSocket transmission structure failures (Issue #1021):\n\n"
                f"{failure_summary}\n\n
                fIMPACT: Users cannot access business data from WebSocket events.\n"
                f"FIX REQUIRED: Preserve business field structure during transmission.
            )

    @pytest.mark.mission_critical
    async def test_frontend_event_consumption_compatibility(self):
        ""MISSION CRITICAL: Test event structure compatible with frontend consumption patterns.

        FRONTEND COMPATIBILITY: Validates that WebSocket events can be consumed by frontend
        JavaScript code expecting business fields at specific locations.
        "
        # Simulate frontend consumption patterns expecting top-level business fields
        frontend_consumption_tests = [
            {
                "event_type: tool_executing",
                "expected_js_access_patterns: [
                    event.tool_name",  # Frontend expects: const toolName = event.tool_name
                    "event.tool_args,  # Frontend expects: const args = event.tool_args
                    event.execution_id"  # Frontend expects: const execId = event.execution_id
                ],
                "sample_event: {
                    type": "tool_executing,
                    tool_name": "frontend_test_tool,
                    tool_args": {"test: True},
                    execution_id": "frontend_test_123,
                    timestamp": time.time()
                }
            },
            {
                "event_type: tool_completed",
                "expected_js_access_patterns: [
                    event.tool_name",
                    "event.results,
                    event.execution_time"
                ],
                "sample_event: {
                    type": "tool_completed,
                    tool_name": "frontend_test_tool,
                    results": {"test_result: success"},
                    "execution_time: 1.5,
                    success": True
                }
            }
        ]

        frontend_compatibility_failures = []

        for test_case in frontend_consumption_tests:
            sample_event = test_case["sample_event]
            expected_patterns = test_case[expected_js_access_patterns"]

            # Serialize through WebSocket transmission pipeline
            from netra_backend.app.websocket_core.websocket_manager import _serialize_message_safely
            transmitted_event = _serialize_message_safely(sample_event)

            # Test each frontend access pattern
            for js_pattern in expected_patterns:
                field_path = js_pattern.replace("event., ")

                if field_path not in transmitted_event:
                    frontend_compatibility_failures.append(
                        f"FRONTEND INCOMPATIBLE: {js_pattern} - field '{field_path}' not accessible at top level. 
                        fEvent: {transmitted_event}"
                    )

        # MISSION CRITICAL: Frontend must be able to access all business fields
        if frontend_compatibility_failures:
            compatibility_summary = "\n.join(frontend_compatibility_failures)
            pytest.fail(
                fMISSION CRITICAL: Frontend compatibility failures (Issue #1021):\n\n"
                f"{compatibility_summary}\n\n
                fIMPACT: Frontend JavaScript cannot access WebSocket event business data.\n"
                f"USER IMPACT: No real-time agent progress, tool transparency, or completion status.\n
                fREVENUE IMPACT: Chat functionality (90% of platform value) broken for users."
            )