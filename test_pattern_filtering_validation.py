#!/usr/bin/env python3
"""
Final validation of Issue #1270 pattern filtering behavior
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "tests"))

from unified_test_runner import UnifiedTestRunner

def comprehensive_pattern_validation():
    """Comprehensive validation of pattern filtering behavior"""
    print("🔬 COMPREHENSIVE PATTERN FILTERING VALIDATION")
    print("="*70)

    runner = UnifiedTestRunner()

    # Test all categories with and without patterns
    categories = ["database", "unit", "integration", "e2e", "api", "smoke"]

    class MockArgs:
        def __init__(self, pattern=None):
            self.pattern = pattern
            self.no_coverage = True
            self.parallel = False
            self.verbose = False
            self.fast_fail = False
            self.env = "test"

    print("Testing all categories with and without patterns:\n")

    results = []
    bugs_found = []

    for category in categories:
        print(f"📂 CATEGORY: {category}")

        # Test without pattern
        args_no_pattern = MockArgs()
        try:
            cmd_no_pattern = runner._build_pytest_command("backend", category, args_no_pattern)
            has_k_no_pattern = " -k " in cmd_no_pattern

            print(f"  Without pattern: -k filter = {'YES' if has_k_no_pattern else 'NO'}")

            if has_k_no_pattern:
                print(f"    ⚠️  WARNING: Category {category} has -k filter without pattern")

        except Exception as e:
            print(f"  ❌ ERROR without pattern: {e}")
            continue

        # Test with pattern
        args_with_pattern = MockArgs(pattern="test_sample")
        try:
            cmd_with_pattern = runner._build_pytest_command("backend", category, args_with_pattern)
            has_k_with_pattern = " -k " in cmd_with_pattern

            print(f"  With pattern:    -k filter = {'YES' if has_k_with_pattern else 'NO'}")

            # Check for the bug
            if category == "database" and has_k_with_pattern:
                print(f"    🐛 BUG DETECTED: Database category has -k filter with pattern!")
                bugs_found.append(f"Database category with pattern has -k filter")
            elif category != "database" and not has_k_with_pattern:
                print(f"    ⚠️  UNEXPECTED: {category} category missing -k filter with pattern")
            else:
                print(f"    ✅ CORRECT: Expected behavior for {category}")

            results.append({
                "category": category,
                "with_pattern_has_k": has_k_with_pattern,
                "without_pattern_has_k": has_k_no_pattern,
                "is_database_bug": category == "database" and has_k_with_pattern
            })

        except Exception as e:
            print(f"  ❌ ERROR with pattern: {e}")

        print()

    # Summary
    print("="*70)
    print("🎯 VALIDATION SUMMARY")
    print("="*70)

    database_results = [r for r in results if r["category"] == "database"]
    if database_results:
        db_result = database_results[0]
        print(f"Database category validation:")
        print(f"  - With pattern has -k filter: {'YES' if db_result['with_pattern_has_k'] else 'NO'}")
        print(f"  - Without pattern has -k filter: {'YES' if db_result['without_pattern_has_k'] else 'NO'}")
        print(f"  - Bug present: {'YES' if db_result['is_database_bug'] else 'NO'}")

    print(f"\nTotal bugs found: {len(bugs_found)}")
    for bug in bugs_found:
        print(f"  🐛 {bug}")

    print(f"\nCategories tested: {len(results)}")
    correct_behaviors = sum(1 for r in results if not r["is_database_bug"])
    print(f"Correct behaviors: {correct_behaviors}")

    # Expected vs Actual analysis
    print("\n📊 EXPECTED VS ACTUAL BEHAVIOR:")
    print("Expected behavior:")
    print("  - Database + pattern → NO -k filter (test all files in database paths)")
    print("  - Other categories + pattern → YES -k filter (filter by test name)")
    print("  - Any category without pattern → NO -k filter")

    print("\nActual behavior:")
    for result in results:
        category = result["category"]
        with_k = "YES" if result["with_pattern_has_k"] else "NO"
        without_k = "YES" if result["without_pattern_has_k"] else "NO"

        status = "✅" if not result["is_database_bug"] else "🐛"
        print(f"  {status} {category}: with pattern={with_k}, without pattern={without_k}")

    return len(bugs_found) > 0

def test_specific_database_scenarios():
    """Test specific database scenarios that should work correctly"""
    print("\n🗄️  DATABASE SPECIFIC SCENARIO TESTING")
    print("="*70)

    runner = UnifiedTestRunner()

    class MockArgs:
        def __init__(self, pattern=None):
            self.pattern = pattern
            self.no_coverage = True
            self.parallel = False
            self.verbose = False
            self.fast_fail = False
            self.env = "test"

    # Common database test patterns that should NOT use -k filtering
    database_patterns = [
        "test_connection",
        "test_clickhouse",
        "test_postgresql",
        "test_database_init",
        "test_migration"
    ]

    print("Testing database-specific patterns that should run all database tests:")

    bugs_in_scenarios = []

    for pattern in database_patterns:
        args = MockArgs(pattern=pattern)
        cmd = runner._build_pytest_command("backend", "database", args)

        has_k_filter = " -k " in cmd

        print(f"\nPattern: '{pattern}'")
        print(f"  Command: {cmd}")
        print(f"  Has -k filter: {'YES' if has_k_filter else 'NO'}")

        if has_k_filter:
            print(f"  🐛 BUG: Database pattern '{pattern}' incorrectly has -k filter")
            bugs_in_scenarios.append(pattern)
        else:
            print(f"  ✅ CORRECT: Database pattern '{pattern}' runs all database tests")

    print(f"\n📊 Database Scenario Summary:")
    print(f"  - Patterns tested: {len(database_patterns)}")
    print(f"  - Bugs found: {len(bugs_in_scenarios)}")

    if bugs_in_scenarios:
        print(f"  - Problematic patterns: {', '.join(bugs_in_scenarios)}")

    return len(bugs_in_scenarios) > 0

def main():
    """Main validation function"""
    print("🚀 EXECUTING FINAL PATTERN FILTERING VALIDATION")
    print("Testing Issue #1270: Database category pattern filtering bug")
    print()

    # Run comprehensive validation
    general_bugs = comprehensive_pattern_validation()
    scenario_bugs = test_specific_database_scenarios()

    print("\n" + "="*70)
    print("🏁 FINAL VALIDATION RESULTS")
    print("="*70)

    total_bugs = general_bugs or scenario_bugs

    if total_bugs:
        print("✅ Issue #1270 bug SUCCESSFULLY REPRODUCED")
        print("📋 Evidence:")
        print("  - Database category with --pattern incorrectly applies -k filter")
        print("  - This prevents running all database tests when using patterns")
        print("  - Other categories correctly apply -k filter with patterns")
        print("\n🚨 RECOMMENDATION: PROCEED TO REMEDIATION PLANNING")
    else:
        print("❌ Issue #1270 bug NOT reproduced")
        print("⚠️  Pattern filtering appears to work correctly")
        print("\n📝 RECOMMENDATION: Re-examine issue description")

    return 0 if total_bugs else 1

if __name__ == "__main__":
    sys.exit(main())