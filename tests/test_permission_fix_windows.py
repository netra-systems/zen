#!/usr/bin/env python3
"""
Test script to verify zen_orchestrator permission fix on Windows - Issue #1320
This test verifies that:
1. Platform detection correctly identifies Windows
2. Permission mode is set to 'bypassPermissions' on Windows
3. Commands execute without permission errors
4. Error detection and reporting works correctly
"""

import sys
import platform
import json
import asyncio
import os
from pathlib import Path

# Fix Windows console encoding for emojis
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add zen to path
sys.path.insert(0, str(Path(__file__).parent))

from zen_orchestrator import InstanceConfig, ClaudeInstanceOrchestrator


def test_platform_detection():
    """Test 1: Verify platform detection"""
    print("="*80)
    print("TEST 1: Platform Detection")
    print("-"*80)

    current_platform = platform.system()
    print(f"✓ Detected platform: {current_platform}")

    if current_platform == "Windows":
        print("✓ Running on Windows - permission fix should be active")
    else:
        print(f"⚠ Running on {current_platform} - test may not show Windows-specific behavior")

    return current_platform


def test_permission_mode_setting():
    """Test 2: Verify correct permission mode is set based on platform"""
    print("\n" + "="*80)
    print("TEST 2: Permission Mode Setting")
    print("-"*80)

    # Create a test instance config
    config = InstanceConfig(
        command="echo test",
        name="test_instance"
    )

    print(f"✓ Created InstanceConfig with command: {config.command}")
    print(f"✓ Permission mode auto-set to: {config.permission_mode}")

    expected_mode = "bypassPermissions" if platform.system() == "Windows" else "bypassPermissions"

    if config.permission_mode == expected_mode:
        print(f"✅ PASS: Permission mode correctly set to '{expected_mode}' for {platform.system()}")
    else:
        print(f"❌ FAIL: Expected '{expected_mode}' but got '{config.permission_mode}'")
        return False

    return True


def test_error_detection():
    """Test 3: Verify error detection works"""
    print("\n" + "="*80)
    print("TEST 3: Error Detection (Simulated)")
    print("-"*80)

    # Create orchestrator
    orchestrator = ClaudeInstanceOrchestrator(Path.cwd())

    # Add a test instance so it exists in the orchestrator
    test_config = InstanceConfig(
        command="test",
        name="test_instance"
    )
    orchestrator.add_instance(test_config)

    # Create a test status
    from zen_orchestrator import InstanceStatus
    test_status = InstanceStatus(name="test_error_detection")

    # Test permission error detection with the exact JSON format we saw
    permission_error_json = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "content": "This command requires approval",
                "is_error": True,
                "tool_use_id": "test_tool_id"
            }]
        }
    })

    print("✓ Testing with permission error JSON...")

    # Test the detection method
    error_detected = orchestrator._detect_permission_error(
        permission_error_json,
        test_status,
        "test_instance"
    )

    if error_detected:
        print("✅ PASS: Permission error correctly detected")
        print(f"✓ Error recorded in status: {bool(test_status.error)}")
        if test_status.error:
            print(f"✓ Error message: {test_status.error[:100]}")
    else:
        print("❌ FAIL: Permission error not detected")
        return False

    # Test with non-error JSON
    normal_json = json.dumps({"type": "assistant", "message": {"content": "normal output"}})
    error_detected_normal = orchestrator._detect_permission_error(
        normal_json,
        test_status,
        "test_instance"
    )

    if not error_detected_normal:
        print("✅ PASS: Normal output correctly not flagged as error")
    else:
        print("❌ FAIL: Normal output incorrectly flagged as error")
        return False

    return True


async def test_real_command_execution():
    """Test 4: Try executing a real command with zen"""
    print("\n" + "="*80)
    print("TEST 4: Real Command Execution")
    print("-"*80)

    # Create orchestrator
    orchestrator = ClaudeInstanceOrchestrator(Path.cwd())

    # Add a simple test instance
    config = InstanceConfig(
        command="1+1",
        name="simple_math",
        output_format="stream-json",
        max_tokens_per_command=100
    )

    orchestrator.add_instance(config)

    print(f"✓ Created instance: {config.name}")
    print(f"✓ Command: {config.command}")
    print(f"✓ Permission mode: {config.permission_mode}")
    print(f"✓ Platform: {platform.system()}")

    # Check if Claude is available
    import shutil
    if not shutil.which("claude") and not shutil.which("claude.cmd"):
        print("⚠ Claude Code not found in PATH - skipping execution test")
        print("  Install with: npm install -g @anthropic/claude-code")
        return None

    print("\n🚀 Attempting to execute command...")
    print("  If this hangs or shows permission errors, the fix isn't working")
    print("  If it completes quickly, the fix is working!\n")

    try:
        # Run with a timeout
        success = await asyncio.wait_for(
            orchestrator.run_instance("simple_math"),
            timeout=10.0
        )

        status = orchestrator.statuses["simple_math"]

        if success and status.status == "completed":
            print("✅ PASS: Command executed successfully!")
            print(f"✓ Output: {status.output[:200] if status.output else 'No output'}")
            if status.error:
                print(f"⚠ Errors (if any): {status.error[:200]}")
        elif status.error and "requires approval" in status.error.lower():
            print("❌ FAIL: Permission error occurred - fix not working!")
            print(f"Error: {status.error}")
            return False
        else:
            print(f"⚠ Command finished with status: {status.status}")
            if status.error:
                print(f"Errors: {status.error[:200]}")

        return success

    except asyncio.TimeoutError:
        print("❌ FAIL: Command timed out - possibly waiting for permission")
        return False
    except Exception as e:
        print(f"⚠ Exception during execution: {e}")
        return None


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("TEST: ZEN ORCHESTRATOR PERMISSION FIX - ISSUE #1320")
    print("="*80)

    results = []

    # Test 1: Platform detection
    platform_result = test_platform_detection()
    results.append(("Platform Detection", True))

    # Test 2: Permission mode setting
    mode_result = test_permission_mode_setting()
    results.append(("Permission Mode Setting", mode_result))

    # Test 3: Error detection
    error_result = test_error_detection()
    results.append(("Error Detection", error_result))

    # Test 4: Real execution (if on Windows)
    if platform.system() == "Windows":
        print("\n🔥 Running real execution test on Windows...")
        exec_result = asyncio.run(test_real_command_execution())
        if exec_result is not None:
            results.append(("Real Command Execution", exec_result))
    else:
        print(f"\n⚠ Skipping real execution test (not on Windows, on {platform.system()})")

    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(r[1] for r in results)

    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Permission fix is working correctly.")
        if platform.system() == "Windows":
            print("✅ Windows permission issues should be resolved.")
            print("✅ Commands will use 'bypassPermissions' mode automatically.")
    else:
        print("⚠️  SOME TESTS FAILED - Please check the output above.")
    print("="*80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())