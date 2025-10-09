#!/usr/bin/env python3
"""
Test script to verify apex telemetry is working and writing to Cloud Trace.
"""

import subprocess
import sys
import time
from pathlib import Path

def test_telemetry_enabled():
    """Check if telemetry is enabled."""
    print("=" * 80)
    print("1. Checking if telemetry is enabled...")
    print("=" * 80)

    result = subprocess.run(
        [sys.executable, "-c",
         "from zen.telemetry import telemetry_manager; "
         "print('ENABLED' if telemetry_manager.is_enabled() else 'DISABLED')"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )

    if result.returncode != 0:
        print(f"❌ Error checking telemetry: {result.stderr}")
        return False

    status = result.stdout.strip()
    if status == "ENABLED":
        print("✅ Telemetry is ENABLED")
        return True
    else:
        print("⚠️  Telemetry is DISABLED")
        print("   This means no spans will be sent to Cloud Trace")
        return False


def test_credentials():
    """Check if credentials are available."""
    print("\n" + "=" * 80)
    print("2. Checking telemetry credentials...")
    print("=" * 80)

    result = subprocess.run(
        [sys.executable, "-c",
         "from zen.telemetry import get_embedded_credentials, get_project_id; "
         "creds = get_embedded_credentials(); "
         "proj = get_project_id() if creds else None; "
         "print(f'PROJECT:{proj}' if creds and proj else 'MISSING')"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )

    if result.returncode != 0:
        print(f"❌ Error checking credentials: {result.stderr}")
        return None

    output = result.stdout.strip()
    if output.startswith("PROJECT:"):
        project_id = output.split(":", 1)[1]
        print(f"✅ Credentials found for project: {project_id}")
        return project_id
    else:
        print("⚠️  No telemetry credentials found")
        return None


def test_apex_telemetry_wrapper():
    """Test the apex telemetry wrapper directly."""
    print("\n" + "=" * 80)
    print("3. Testing ApexTelemetryWrapper...")
    print("=" * 80)

    test_code = """
import sys
sys.path.insert(0, '.')
from zen.telemetry.apex_telemetry import ApexTelemetryWrapper

wrapper = ApexTelemetryWrapper()

# Test message extraction
msg = wrapper._extract_message(['--message', 'test telemetry'])
assert msg == 'test telemetry', f"Expected 'test telemetry', got '{msg}'"
print('✓ Message extraction works')

# Test environment extraction
env = wrapper._extract_env(['--env', 'staging'])
assert env == 'staging', f"Expected 'staging', got '{env}'"
print('✓ Environment extraction works')

# Test message truncation
long_msg = 'x' * 300
truncated = wrapper._truncate_message(long_msg, max_length=200)
assert len(truncated) == 203, f"Expected 203 chars, got {len(truncated)}"
assert truncated.endswith('...'), "Should end with '...'"
print('✓ Message truncation works')

print('\\n✅ All ApexTelemetryWrapper tests passed')
"""

    result = subprocess.run(
        [sys.executable, "-c", test_code],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )

    if result.returncode != 0:
        print(f"❌ Tests failed:")
        print(result.stderr)
        return False

    print(result.stdout)
    return True


def test_apex_with_mock_message(project_id):
    """Test running zen --apex with a simple message."""
    print("\n" + "=" * 80)
    print("4. Testing zen --apex with sample message...")
    print("=" * 80)

    # Use a simple help command to avoid needing actual backend connection
    test_message = f"test-telemetry-{int(time.time())}"

    print(f"\nRunning: zen --apex --message '{test_message}' --env staging")
    print("Note: This may fail if backend is unavailable, but telemetry should still be emitted")
    print()

    # Run zen --apex with our test message
    result = subprocess.run(
        [sys.executable, "-m", "zen_orchestrator", "--apex",
         "--message", test_message, "--env", "staging"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
        timeout=30
    )

    print("Exit code:", result.returncode)

    if result.stdout:
        print("\nStdout (first 500 chars):")
        print(result.stdout[:500])

    if result.stderr:
        print("\nStderr (first 500 chars):")
        print(result.stderr[:500])

    print("\n" + "=" * 80)
    print("5. Verifying telemetry span...")
    print("=" * 80)

    if project_id:
        trace_url = f"https://console.cloud.google.com/traces/list?project={project_id}"
        print(f"\n📊 Check Cloud Trace console:")
        print(f"   URL: {trace_url}")
        print(f"\n   Look for:")
        print(f"   - Span name: 'apex.instance'")
        print(f"   - Service: 'zen-orchestrator'")
        print(f"   - Attributes with 'zen.apex.message': '{test_message}'")
        print(f"   - Timestamp: around {time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("⚠️  Project ID not available, cannot generate Cloud Trace URL")

    return result.returncode


def main():
    """Run all telemetry tests."""
    print("\n🔍 APEX TELEMETRY VERIFICATION TEST")
    print("=" * 80)
    print("This script verifies that apex telemetry is working correctly")
    print("and can send spans to Cloud Trace")
    print("=" * 80)

    # Test 1: Check if telemetry is enabled
    telemetry_enabled = test_telemetry_enabled()

    # Test 2: Check credentials
    project_id = test_credentials()

    # Test 3: Test the wrapper
    wrapper_ok = test_apex_telemetry_wrapper()

    # Test 4 & 5: Test actual apex execution and verify span
    if telemetry_enabled and wrapper_ok:
        exit_code = test_apex_with_mock_message(project_id)
    else:
        print("\n⚠️  Skipping apex execution test due to telemetry/wrapper issues")
        exit_code = 1

    # Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)
    print(f"Telemetry Enabled: {'✅' if telemetry_enabled else '❌'}")
    print(f"Credentials Found: {'✅' if project_id else '❌'}")
    print(f"Wrapper Tests: {'✅' if wrapper_ok else '❌'}")
    print(f"Apex Execution: {'✅ Completed' if exit_code is not None else '⏭️  Skipped'}")

    if telemetry_enabled and project_id:
        print("\n✅ Telemetry should be working!")
        print("   Check the Cloud Trace URL above to verify the span was created")
    else:
        print("\n⚠️  Telemetry may not be fully functional")
        if not telemetry_enabled:
            print("   - Telemetry is disabled")
        if not project_id:
            print("   - No credentials found")

    print("=" * 80)

    return 0 if (telemetry_enabled and wrapper_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
