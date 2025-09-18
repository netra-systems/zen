#!/usr/bin/env python3
"""
Manual CLI testing for claude-instance-orchestrator.py
Tests basic CLI functionality to ensure changes don't break core usage.
"""

import subprocess
import sys
from pathlib import Path
import tempfile

def test_cli_help():
    """Test that the CLI shows help without errors"""
    scripts_path = Path(__file__).parent.parent / "scripts"
    orchestrator_path = scripts_path / "claude-instance-orchestrator.py"

    if not orchestrator_path.exists():
        print(f"X Script not found: {orchestrator_path}")
        return False

    try:
        result = subprocess.run([
            sys.executable, str(orchestrator_path), "--help"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("PASS: CLI help command works")
            print(f"   Help output length: {len(result.stdout)} characters")
            return True
        else:
            print(f"FAIL: CLI help failed with return code: {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"FAIL: Exception testing CLI help: {e}")
        return False

def test_cli_list_commands():
    """Test that the CLI can list commands"""
    scripts_path = Path(__file__).parent.parent / "scripts"
    orchestrator_path = scripts_path / "claude-instance-orchestrator.py"

    # Create a temporary workspace with .claude directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_workspace = Path(temp_dir)
        claude_dir = temp_workspace / ".claude" / "commands"
        claude_dir.mkdir(parents=True)

        # Create a sample command file
        sample_cmd = claude_dir / "test.md"
        sample_cmd.write_text("""---
description: Test command for validation
---

# Test Command
This is a test command for validation.
""")

        try:
            result = subprocess.run([
                sys.executable, str(orchestrator_path),
                "--workspace", str(temp_workspace),
                "--list-commands"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("PASS: CLI list-commands works")
                print(f"   Commands found in output: {'test' in result.stdout}")
                return True
            else:
                print(f"FAIL: CLI list-commands failed with return code: {result.returncode}")
                print(f"   Error: {result.stderr}")
                return False

        except Exception as e:
            print(f"FAIL: Exception testing CLI list-commands: {e}")
            return False

def test_cli_dry_run():
    """Test that the CLI can do a dry run"""
    scripts_path = Path(__file__).parent.parent / "scripts"
    orchestrator_path = scripts_path / "claude-instance-orchestrator.py"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_workspace = Path(temp_dir)
        claude_dir = temp_workspace / ".claude" / "commands"
        claude_dir.mkdir(parents=True)

        try:
            result = subprocess.run([
                sys.executable, str(orchestrator_path),
                "--workspace", str(temp_workspace),
                "--dry-run"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("PASS: CLI dry-run works")
                print(f"   Output contains 'DRY RUN MODE': {'DRY RUN MODE' in result.stdout}")
                return True
            else:
                print(f"FAIL: CLI dry-run failed with return code: {result.returncode}")
                print(f"   Error: {result.stderr}")
                return False

        except Exception as e:
            print(f"FAIL: Exception testing CLI dry-run: {e}")
            return False

def main():
    """Run manual CLI tests"""
    print("MANUAL CLI TEST: claude-instance-orchestrator.py")
    print("=" * 60)

    tests = [
        ("Help Command", test_cli_help),
        ("List Commands", test_cli_list_commands),
        ("Dry Run", test_cli_dry_run),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\nTesting: {test_name}")
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 60)
    print("MANUAL CLI TEST RESULTS")
    print("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("SUCCESS: All manual CLI tests passed - changes don't break basic functionality")
        return True
    else:
        print("FAILURE: Some manual CLI tests failed - changes may have broken functionality")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)