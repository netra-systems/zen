"
WebSocket event structure inspection for Issue #1049

This test file examines the actual structure of events being delivered
through the WebSocket infrastructure to document the structure mismatch.
""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock
from pprint import pprint

from netra_backend.app.factories.websocket_bridge_factory import StandardWebSocketBridge
from shared.types.execution_types import StronglyTypedUserExecutionContext


@pytest.mark.integration
class WebSocketStructureInspectionTests:
    ""Inspect actual WebSocket event structures to document mismatch."

    @pytest.fixture
    def user_context(self):
        "Create test user context.""
        return StronglyTypedUserExecutionContext(
            user_id=test-user-123",
            request_id="req-123,
            run_id=run-123",
            thread_id="thread-123,
            websocket_client_id=ws-123"
        )

    @pytest.fixture
    def bridge_with_capture(self, user_context):
        "Create bridge with event capture capability.""
        captured_events = []

        # Mock WebSocket manager that captures everything
        mock_manager = Mock()

        def capture_send_event(*args, **kwargs):
            captured_events.append((send_event", args, kwargs))
            return True

        def capture_emit_event(*args, **kwargs):
            captured_events.append(("emit_event, args, kwargs))
            return True

        mock_manager.send_event = Mock(side_effect=capture_send_event)
        mock_manager.emit_event = AsyncMock(side_effect=capture_emit_event)
        mock_manager.is_connection_active = Mock(return_value=True)

        # Create bridge with mock manager
        bridge = StandardWebSocketBridge(user_context=user_context)
        bridge._websocket_manager = mock_manager

        return bridge, captured_events

    async def test_inspect_tool_executing_structure(self, bridge_with_capture):
        ""
        Inspect actual tool_executing event structure to document the format.
        "
        bridge, captured_events = bridge_with_capture

        # Execute tool_executing notification
        success = await bridge.notify_tool_executing(
            run_id="run-123,
            agent_name=data_analyzer_agent",
            tool_name="cost_optimization_tool,
            parameters={mode": "aggressive, target_reduction": 25}

        assert success, "Tool executing notification should succeed
        assert len(captured_events) > 0, Should capture at least one event"

        # Inspect the captured event structure
        method_name, args, kwargs = captured_events[0]

        print(f"\n=== CAPTURED TOOL_EXECUTING EVENT STRUCTURE ===)
        print(fMethod: {method_name}")
        print(f"Args: {args})
        print(fKwargs: {kwargs}")

        # Extract event data
        if args and len(args) > 1:
            event_data = args[1]
        elif kwargs and 'data' in kwargs:
            event_data = kwargs['data']
        else:
            event_data = kwargs

        print(f"\n=== EVENT DATA STRUCTURE ===)
        pprint(event_data)

        # Document the actual structure
        actual_structure = {
            has_type_field": "type in event_data,
            has_tool_name_field": "tool_name in event_data,
            tool_name_location": "top_level if tool_name" in event_data else "unknown,
            all_fields": list(event_data.keys()) if isinstance(event_data, dict) else "not_dict,
            event_data_type": type(event_data).__name__
        }

        print(f"\n=== STRUCTURE ANALYSIS ===)
        pprint(actual_structure)

        # This should fail if structure doesn't match expectations
        if not event_data.get(type"):
            pytest.fail(f"Event missing 'type' field. Actual structure: {json.dumps(actual_structure, indent=2)})

    async def test_inspect_tool_completed_structure(self, bridge_with_capture):
        ""
        Inspect actual tool_completed event structure to document the format.
        "
        bridge, captured_events = bridge_with_capture

        # Execute tool_completed notification
        tool_result = {
            "cost_savings: 23.5,
            recommendations": [
                "Switch to GPT-4o for 15% cost reduction,
                Implement request caching for 8% additional savings"
            ],
            "confidence: 0.94,
            details": {
                "current_cost: 1000,
                projected_cost": 765,
                "implementation_time: 2 weeks"
            }
        }

        success = await bridge.notify_tool_completed(
            run_id="run-123,
            agent_name=data_analyzer_agent",
            tool_name="cost_optimization_tool,
            result=tool_result,
            execution_time_ms=2450.0
        )

        assert success, Tool completed notification should succeed"
        assert len(captured_events) > 0, "Should capture at least one event

        # Inspect the captured event structure
        method_name, args, kwargs = captured_events[0]

        print(f\n=== CAPTURED TOOL_COMPLETED EVENT STRUCTURE ===")
        print(f"Method: {method_name})
        print(fArgs: {args}")
        print(f"Kwargs: {kwargs})

        # Extract event data
        if args and len(args) > 1:
            event_data = args[1]
        elif kwargs and 'data' in kwargs:
            event_data = kwargs['data']
        else:
            event_data = kwargs

        print(f\n=== EVENT DATA STRUCTURE ===")
        pprint(event_data)

        # Document the actual structure for results field
        actual_structure = {
            "has_type_field: type" in event_data,
            "has_tool_name_field: tool_name" in event_data,
            "has_result_field: result" in event_data,
            "has_results_field: results" in event_data,
            "result_location: top_level" if "result in event_data else unknown",
            "results_location: top_level" if "results in event_data else unknown",
            "all_fields: list(event_data.keys()) if isinstance(event_data, dict) else not_dict",
            "event_data_type: type(event_data).__name__
        }

        print(f\n=== STRUCTURE ANALYSIS ===")
        pprint(actual_structure)

        # This should fail if structure doesn't match expectations
        if not event_data.get("type):
            pytest.fail(fEvent missing 'type' field. Actual structure: {json.dumps(actual_structure, indent=2)}")

    async def test_compare_validator_expectations_vs_reality(self, bridge_with_capture):
        "
        Compare what the validator expects vs what the bridge actually delivers.
        ""
        from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator

        bridge, captured_events = bridge_with_capture
        validator = UnifiedEventValidator(validation_mode=realtime")

        # Get validator expectations
        validator_tool_executing_schema = validator.PAYLOAD_SCHEMAS.get("tool_executing, set())
        validator_tool_completed_schema = validator.PAYLOAD_SCHEMAS.get(tool_completed", set())

        print(f"\n=== VALIDATOR EXPECTATIONS ===)
        print(ftool_executing requires: {validator_tool_executing_schema}")
        print(f"tool_completed requires: {validator_tool_completed_schema})

        # Execute actual bridge notification
        await bridge.notify_tool_executing(
            run_id=run-123",
            agent_name="test_agent,
            tool_name=test_tool",
            parameters={"test: value"}

        # Get actual delivered structure
        method_name, args, kwargs = captured_events[0]
        event_data = args[1] if args and len(args) > 1 else kwargs.get('data', kwargs)

        print(f"\n=== ACTUAL DELIVERED STRUCTURE ===)
        print(fEvent data fields: {list(event_data.keys()) if isinstance(event_data, dict) else 'not_dict'}")
        print(f"Has tool_name: {'tool_name' in event_data})
        print(fHas type: {'type' in event_data}")

        # Test if actual structure would pass validator
        test_event_for_validator = {
            "type: tool_executing",
            "run_id: run-123",
            "agent_name: test_agent",
            "timestamp: 2025-09-14T12:00:00Z",
            "payload: {}
        }

        # Try to extract payload-like data from delivered event
        if isinstance(event_data, dict):
            # Filter out standard fields to see what would go in payload
            payload_fields = {k: v for k, v in event_data.items()
                            if k not in [run_id", "agent_name, timestamp", "type]}
            test_event_for_validator[payload"] = payload_fields

        print(f"\n=== VALIDATION TEST ===)
        print(fSimulated event for validator: {json.dumps(test_event_for_validator, indent=2)}")

        result = validator.validate_event(test_event_for_validator, "test-user-123)

        print(fValidator result: {result.is_valid}")
        print(f"Validator error: {result.error_message})

        # Document the mismatch
        mismatch_analysis = {
            validator_expects_tool_name_in_payload": "tool_name in validator_tool_executing_schema,
            bridge_delivers_tool_name_at_top_level": "tool_name in event_data,
            validator_expects_type_field": True,
            "bridge_delivers_type_field: type" in event_data,
            "structure_mismatch_detected: not result.is_valid,
            mismatch_details": result.error_message
        }

        print(f"\n=== STRUCTURE MISMATCH ANALYSIS ===)
        pprint(mismatch_analysis)

        # Let this test pass so we can see the output, but document the mismatch
        if not result.is_valid:
            print(f\nCONFIRMED: Structure mismatch detected!")
            print(f"The WebSocket bridge delivers events in a different format than the validator expects.)


if __name__ == __main__":
    pytest.main([__file__, "-v, -s"]  # -s to see print output