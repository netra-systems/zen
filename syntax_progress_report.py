#!/usr/bin/env python3
"""Report on syntax fixing progress"""

import subprocess
import sys

def test_critical_files():
    """Test the most critical files for Golden Path"""
    critical_files = [
        "C:/netra-apex/tests/mission_critical/test_websocket_agent_events_suite.py",
        "C:/netra-apex/tests/e2e/test_auth_backend_desynchronization.py",
        "C:/netra-apex/test_framework/ssot/base_test_case.py",
        "C:/netra-apex/tests/mission_critical/conftest_isolated.py",
        "C:/netra-apex/tests/mission_critical/conftest_isolated_websocket.py"
    ]

    print("CRITICAL FILES SYNTAX CHECK")
    print("=" * 50)

    valid_count = 0
    total_count = len(critical_files)

    for file_path in critical_files:
        try:
            result = subprocess.run(
                ['python', '-m', 'py_compile', file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ {file_path.replace('C:/netra-apex/', '')}")
                valid_count += 1
            else:
                print(f"❌ {file_path.replace('C:/netra-apex/', '')}")
        except Exception as e:
            print(f"❌ {file_path.replace('C:/netra-apex/', '')} (Error: {e})")

    print(f"\nRESULTS: {valid_count}/{total_count} critical files have valid syntax")
    print(f"SUCCESS RATE: {valid_count/total_count*100:.1f}%")

    return valid_count == total_count

def test_collection():
    """Test if we can collect tests"""
    print("\nTEST COLLECTION CHECK")
    print("=" * 50)

    try:
        result = subprocess.run([
            'python', '-m', 'pytest',
            'C:/netra-apex/tests/mission_critical/test_websocket_agent_events_suite.py',
            '--collect-only', '-q'
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ Test collection SUCCESSFUL")
            return True
        else:
            print("❌ Test collection FAILED")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Test collection ERROR: {e}")
        return False

def main():
    print("SYNTAX FIXING PROGRESS REPORT")
    print("=" * 60)
    print()

    syntax_ok = test_critical_files()
    collection_ok = test_collection()

    print("\nOVERALL ASSESSMENT")
    print("=" * 50)

    if syntax_ok:
        print("✅ CRITICAL FILES: All major syntax errors fixed")
    else:
        print("❌ CRITICAL FILES: Some syntax errors remain")

    if collection_ok:
        print("✅ TEST COLLECTION: Working")
    else:
        print("❌ TEST COLLECTION: Issues remain")

    if syntax_ok and collection_ok:
        print("\n🎉 SUCCESS: Major blockers resolved!")
        print("   - Golden Path validation can now proceed")
        print("   - Test collection is functional")
        print("   - Ready for next phase of testing")
    else:
        print("\n⚠️  PARTIAL SUCCESS: Some issues remain")

if __name__ == "__main__":
    main()