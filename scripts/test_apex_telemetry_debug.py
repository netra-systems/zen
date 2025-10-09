#!/usr/bin/env python3
"""
Debug script to test apex telemetry and identify why spans aren't appearing in Cloud Trace.
Run this after setting COMMUNITY_CREDENTIALS to diagnose the issue.
"""

import sys
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_telemetry_manager():
    """Test that telemetry manager is properly initialized."""
    print("=" * 80)
    print("TEST 1: Telemetry Manager Initialization")
    print("=" * 80)

    from zen.telemetry import telemetry_manager

    print(f"Telemetry manager type: {type(telemetry_manager)}")
    print(f"Is enabled: {telemetry_manager.is_enabled()}")

    if hasattr(telemetry_manager, '_tracer'):
        print(f"Has _tracer: {telemetry_manager._tracer is not None}")
    else:
        print("❌ No _tracer attribute")

    if hasattr(telemetry_manager, '_provider'):
        print(f"Has _provider: {telemetry_manager._provider is not None}")
    else:
        print("❌ No _provider attribute")

    print()
    return telemetry_manager.is_enabled()


def test_apex_wrapper_import():
    """Test that apex wrapper can be imported."""
    print("=" * 80)
    print("TEST 2: Apex Telemetry Wrapper Import")
    print("=" * 80)

    try:
        from zen.telemetry.apex_telemetry import ApexTelemetryWrapper
        print("✅ ApexTelemetryWrapper imported successfully")

        wrapper = ApexTelemetryWrapper()
        print(f"✅ Wrapper instance created: {type(wrapper)}")
        print()
        return True
    except Exception as e:
        print(f"❌ Failed to import ApexTelemetryWrapper: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_manual_span_emission():
    """Test manual span emission using telemetry manager."""
    print("=" * 80)
    print("TEST 3: Manual Span Emission")
    print("=" * 80)

    from zen.telemetry import telemetry_manager

    if not telemetry_manager.is_enabled():
        print("⚠️  Telemetry is not enabled - skipping test")
        print()
        return False

    try:
        from opentelemetry.trace import SpanKind

        print("Creating test span...")
        with telemetry_manager._tracer.start_as_current_span(
            "test.apex.span", kind=SpanKind.INTERNAL
        ) as span:
            span.set_attribute("test.type", "manual")
            span.set_attribute("test.value", 123)
            print("✅ Span created and attributes set")

        print("Flushing provider...")
        if hasattr(telemetry_manager, '_provider') and telemetry_manager._provider:
            telemetry_manager._provider.force_flush(timeout_millis=5000)
            print("✅ Provider flushed")

        print("✅ Manual span test completed")
        print("   Check Cloud Trace for span: 'test.apex.span'")
        print()
        return True

    except Exception as e:
        print(f"❌ Manual span emission failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_apex_wrapper_emission():
    """Test apex wrapper span emission."""
    print("=" * 80)
    print("TEST 4: Apex Wrapper Span Emission")
    print("=" * 80)

    from zen.telemetry.apex_telemetry import ApexTelemetryWrapper

    wrapper = ApexTelemetryWrapper()
    wrapper.start_time = 1000.0
    wrapper.end_time = 1010.0
    wrapper.exit_code = 0
    wrapper.message = "test apex telemetry debug"
    wrapper.env = "staging"
    wrapper.stdout = ""
    wrapper.stderr = ""

    print("Emitting telemetry with wrapper...")
    try:
        wrapper._emit_telemetry()
        print("✅ Wrapper._emit_telemetry() completed")
        print("   Check Cloud Trace for span: 'apex.instance'")
        print()
        return True
    except Exception as e:
        print(f"❌ Wrapper emission failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_credentials():
    """Test credential loading."""
    print("=" * 80)
    print("TEST 5: Credential Loading")
    print("=" * 80)

    from zen.telemetry import get_embedded_credentials, get_project_id

    creds = get_embedded_credentials()
    if creds:
        print(f"✅ Credentials loaded")
        project_id = get_project_id()
        print(f"✅ Project ID: {project_id}")
        print()
        return True
    else:
        print("❌ No credentials found")
        print("   Set COMMUNITY_CREDENTIALS environment variable")
        print()
        return False


def main():
    """Run all diagnostic tests."""
    print("\n🔍 APEX TELEMETRY DEBUG TESTS")
    print("=" * 80)

    results = {}

    results['credentials'] = test_credentials()
    results['telemetry_manager'] = test_telemetry_manager()
    results['apex_wrapper_import'] = test_apex_wrapper_import()

    if results['telemetry_manager']:
        results['manual_span'] = test_manual_span_emission()
        results['apex_wrapper'] = test_apex_wrapper_emission()
    else:
        print("⚠️  Skipping span tests - telemetry not enabled")
        results['manual_span'] = False
        results['apex_wrapper'] = False

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {test_name}")

    print()

    if all(results.values()):
        print("✅ ALL TESTS PASSED!")
        print("\nIf spans still don't appear in Cloud Trace:")
        print("  1. Wait 60 seconds (BatchSpanProcessor batches spans)")
        print("  2. Check Cloud Trace console")
        print("  3. Verify project ID matches your GCP setup")
        print("  4. Check service account has cloudtrace.traces.patch permission")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\nTroubleshooting:")

        if not results['credentials']:
            print("  • Set COMMUNITY_CREDENTIALS: export COMMUNITY_CREDENTIALS='<base64-json>'")

        if not results['telemetry_manager']:
            print("  • Telemetry manager not initialized - check credentials")

        if results['telemetry_manager'] and not results['manual_span']:
            print("  • Manual span failed - check OpenTelemetry setup")

        if results['telemetry_manager'] and not results['apex_wrapper']:
            print("  • Apex wrapper failed - check implementation")

        return 1


if __name__ == "__main__":
    sys.exit(main())
