#!/usr/bin/env python3
"""
Mock test to verify apex telemetry implementation without real credentials.
This demonstrates that the code structure is correct and would emit spans if credentials were available.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_apex_telemetry_flow():
    """Test the complete apex telemetry flow with mocked components."""
    print("=" * 80)
    print("APEX TELEMETRY MOCK TEST")
    print("=" * 80)
    print("Testing telemetry implementation with mocked Cloud Trace client\n")

    # Import the wrapper
    from zen.telemetry.apex_telemetry import ApexTelemetryWrapper

    print("✅ Step 1: ApexTelemetryWrapper imported successfully")

    # Create wrapper instance
    wrapper = ApexTelemetryWrapper()
    print("✅ Step 2: ApexTelemetryWrapper instance created")

    # Set up test data
    wrapper.start_time = 1000.0
    wrapper.end_time = 1010.5
    wrapper.exit_code = 0
    wrapper.message = "test apex telemetry"
    wrapper.env = "staging"
    wrapper.stdout = '{"run_id": "test-123", "usage": {"total_tokens": 1500, "input_tokens": 1000, "output_tokens": 500}, "cost": {"total_usd": 0.045}}'
    wrapper.stderr = ""

    print("✅ Step 3: Test data configured")

    # Mock the telemetry manager and tracer
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    print("✅ Step 4: Mock tracer created")

    # Patch telemetry_manager to be enabled
    with patch('zen.telemetry.apex_telemetry.telemetry_manager') as mock_manager:
        mock_manager.is_enabled.return_value = True
        mock_manager._tracer = mock_tracer

        print("✅ Step 5: Telemetry manager mocked as enabled")

        # Call _emit_telemetry
        wrapper._emit_telemetry()

        print("✅ Step 6: _emit_telemetry() called successfully")

    # Verify span was created
    assert mock_tracer.start_as_current_span.called, "Span should have been created"
    call_args = mock_tracer.start_as_current_span.call_args

    # Check span name
    span_name = call_args[0][0]
    assert span_name == "apex.instance", f"Expected span name 'apex.instance', got '{span_name}'"
    print(f"✅ Step 7: Span created with correct name: '{span_name}'")

    # Verify attributes were set
    set_attribute_calls = mock_span.set_attribute.call_args_list
    attributes = {call[0][0]: call[0][1] for call in set_attribute_calls}

    print(f"✅ Step 8: Span attributes set ({len(attributes)} attributes)")

    # Verify key attributes
    expected_attrs = {
        'zen.instance.type': 'apex',
        'zen.instance.name': 'apex.instance',
        'zen.instance.status': 'completed',
        'zen.instance.success': True,
        'zen.instance.exit_code': 0,
        'zen.apex.environment': 'staging',
        'zen.apex.message': 'test apex telemetry',
        'zen.tokens.total': 1500,
        'zen.tokens.input': 1000,
        'zen.tokens.output': 500,
        'zen.cost.usd_total': 0.045,
        'zen.apex.run_id': 'test-123'
    }

    print("\n" + "=" * 80)
    print("ATTRIBUTE VERIFICATION")
    print("=" * 80)

    all_match = True
    for key, expected_value in expected_attrs.items():
        actual_value = attributes.get(key)
        match = actual_value == expected_value
        status = "✅" if match else "❌"
        print(f"{status} {key}: {actual_value} (expected: {expected_value})")
        if not match:
            all_match = False

    # Check duration
    duration = attributes.get('zen.instance.duration_ms')
    expected_duration = int((wrapper.end_time - wrapper.start_time) * 1000)
    duration_match = duration == expected_duration
    status = "✅" if duration_match else "❌"
    print(f"{status} zen.instance.duration_ms: {duration} (expected: {expected_duration})")
    if not duration_match:
        all_match = False

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    if all_match:
        print("✅ ALL TESTS PASSED!")
        print("\nThe apex telemetry implementation is working correctly.")
        print("When real credentials are available, spans will be sent to Cloud Trace with:")
        print("  - Span name: 'apex.instance'")
        print("  - Service: 'zen-orchestrator'")
        print(f"  - {len(attributes)} attributes including tokens, costs, and metadata")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the attribute mismatches above")
        return 1


def test_integration_with_zen_orchestrator():
    """Test that zen_orchestrator.py can import and use the telemetry wrapper."""
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: zen_orchestrator.py")
    print("=" * 80)

    try:
        # Simulate what zen_orchestrator.py does
        from zen.telemetry import run_apex_with_telemetry
        print("✅ run_apex_with_telemetry imported from zen.telemetry")

        # Check it's callable
        assert callable(run_apex_with_telemetry), "Should be callable"
        print("✅ run_apex_with_telemetry is callable")

        # Check signature
        import inspect
        sig = inspect.signature(run_apex_with_telemetry)
        params = list(sig.parameters.keys())
        expected_params = ['agent_cli_path', 'filtered_argv', 'env']
        assert params == expected_params, f"Expected params {expected_params}, got {params}"
        print(f"✅ Function has correct signature: {params}")

        print("\n✅ Integration test passed - zen_orchestrator.py can use the wrapper")
        return 0

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Run all mock tests."""
    print("\n🧪 APEX TELEMETRY MOCK TESTS")
    print("=" * 80)
    print("These tests verify the implementation without needing real credentials\n")

    # Test 1: Full telemetry flow
    result1 = test_apex_telemetry_flow()

    # Test 2: Integration test
    result2 = test_integration_with_zen_orchestrator()

    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Telemetry Flow Test: {'✅ PASSED' if result1 == 0 else '❌ FAILED'}")
    print(f"Integration Test: {'✅ PASSED' if result2 == 0 else '❌ FAILED'}")

    if result1 == 0 and result2 == 0:
        print("\n✅ ALL TESTS PASSED!")
        print("\nℹ️  To test with real Cloud Trace:")
        print("   1. Set COMMUNITY_CREDENTIALS environment variable")
        print("   2. Run: zen --apex --message 'test' --env staging")
        print("   3. Check Cloud Trace console for 'apex.instance' spans")
    else:
        print("\n❌ SOME TESTS FAILED")

    print("=" * 80)

    return max(result1, result2)


if __name__ == "__main__":
    sys.exit(main())
