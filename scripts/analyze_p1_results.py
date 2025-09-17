#!/usr/bin/env python3
"""
Quick analysis of P1 critical test results from staging
"""

import json
import os

def analyze_test_results():
    results_file = "tests/e2e/staging/test_results.json"

    if not os.path.exists(results_file):
        print(f"❌ Results file not found: {results_file}")
        return

    try:
        with open(results_file, 'r') as f:
            data = json.load(f)

        print("🔍 E2E STAGING TEST RESULTS ANALYSIS")
        print("=" * 60)

        summary = data.get("summary", {})
        print(f"📊 SUMMARY:")
        print(f"   Total Tests: {summary.get('total', 0)}")
        print(f"   Collected: {summary.get('collected', 0)}")
        print(f"   Passed: {summary.get('passed', 0)}")
        print(f"   Failed: {summary.get('failed', 0)}")
        print(f"   Errors: {summary.get('error', 0)}")
        print(f"   Deselected: {summary.get('deselected', 0)}")
        print(f"   Exit Code: {data.get('exitcode', 'Unknown')}")
        print(f"   Duration: {data.get('duration', 0):.2f}s")

        # Look for tests section
        tests = data.get('tests', [])
        if tests:
            print(f"\n🧪 INDIVIDUAL TEST RESULTS:")

            p1_tests = []
            failed_tests = []
            error_tests = []

            for test in tests:
                test_id = test.get('nodeid', '')
                outcome = test.get('outcome', 'unknown')

                if 'priority1_critical' in test_id:
                    p1_tests.append({'id': test_id, 'outcome': outcome})

                if outcome == 'failed':
                    failed_tests.append(test)
                elif outcome == 'error':
                    error_tests.append(test)

            # Report P1 tests specifically
            if p1_tests:
                print(f"\n🔴 P1 CRITICAL TESTS:")
                for test in p1_tests:
                    status = "✅" if test['outcome'] == 'passed' else "❌"
                    print(f"   {status} {test['id']} - {test['outcome']}")
            else:
                print(f"\n⚠️  No P1 critical tests found in results")

            # Report failures
            if failed_tests:
                print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
                for test in failed_tests[:5]:  # Show first 5
                    print(f"   • {test.get('nodeid', 'Unknown')}")

            # Report errors
            if error_tests:
                print(f"\n💥 ERROR TESTS ({len(error_tests)}):")
                for test in error_tests[:5]:  # Show first 5
                    print(f"   • {test.get('nodeid', 'Unknown')}")

        else:
            print(f"\n⚠️  No individual test results found in JSON")

            # Check collectors for basic info
            collectors = data.get('collectors', [])
            if collectors:
                print(f"\n📁 TEST COLLECTION INFO:")
                for collector in collectors[:10]:  # Show first 10
                    node_id = collector.get('nodeid', '')
                    outcome = collector.get('outcome', 'unknown')
                    if 'priority1_critical' in node_id:
                        print(f"   🔴 P1: {node_id} - {outcome}")
                    elif node_id and 'test_' in node_id:
                        print(f"   📝 {node_id} - {outcome}")

        # Infrastructure assessment
        print(f"\n🏗️ INFRASTRUCTURE ASSESSMENT:")
        if summary.get('passed', 0) > 40:
            print(f"   ✅ Staging environment appears operational")
            print(f"   ✅ Most tests are passing ({summary.get('passed', 0)}/{summary.get('total', 0)})")
        elif summary.get('total', 0) == 0:
            print(f"   ❌ No tests executed - possible configuration or connectivity issue")
        else:
            print(f"   ⚠️  Some infrastructure issues detected")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if summary.get('failed', 0) > 0 or summary.get('error', 0) > 0:
            print(f"   • Investigate failed/error tests for infrastructure issues")
            print(f"   • Check staging environment connectivity")
            print(f"   • Verify authentication and WebSocket configurations")

        if summary.get('total', 0) == 0:
            print(f"   • Check test discovery and collection process")
            print(f"   • Verify pytest configuration and environment setup")

        if not p1_tests and summary.get('total', 0) > 0:
            print(f"   • P1 critical tests may not have been executed")
            print(f"   • Verify test file exists and is discoverable")

    except Exception as e:
        print(f"❌ Error analyzing results: {e}")

if __name__ == "__main__":
    analyze_test_results()