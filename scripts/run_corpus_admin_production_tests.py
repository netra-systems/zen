#!/usr/bin/env python3
"""
Corpus Admin Agent Production Fix Test Runner

Quick way to run the comprehensive corpus admin test suite that validates
BaseExecutionEngine implementation and prevents mock regression.

Usage:
    python scripts/run_corpus_admin_production_tests.py [test_category]

Test categories:
    - all: Run all tests (default)
    - mock_regression: Test that no mocks are used
    - four_phase: Test the 4-phase execution pattern
    - hooks: Test pre/post execution hooks
    - error_handling: Test error handling and recovery
    - user_isolation: Test UserExecutionContext isolation
    - websocket: Test WebSocket integration
    - edge_cases: Test difficult edge cases
    - performance: Test performance benchmarks
"""

import sys
import subprocess
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
TEST_FILE = PROJECT_ROOT / "netra_backend" / "tests" / "unit" / "agents" / "test_corpus_admin_production_fix.py"

TEST_CATEGORIES = {
    "mock_regression": "TestNoMockRegression",
    "four_phase": "TestFourPhaseExecution", 
    "hooks": "TestExecutionHooks",
    "error_handling": "TestErrorHandlingAndRecovery",
    "user_isolation": "TestUserExecutionContextIsolation",
    "websocket": "TestWebSocketEventIntegration",
    "edge_cases": "TestDifficultEdgeCases",
    "performance": "TestPerformanceBenchmarks"
}

def run_tests(category=None):
    """Run tests for specified category or all tests."""
    cmd = ["python", "-m", "pytest", str(TEST_FILE), "-v"]
    
    if category and category != "all":
        if category in TEST_CATEGORIES:
            cmd.extend(["-k", TEST_CATEGORIES[category]])
        else:
            print(f"Unknown category: {category}")
            print(f"Available categories: {', '.join(TEST_CATEGORIES.keys())}")
            return 1
    
    # Change to project root
    import os
    os.chdir(PROJECT_ROOT)
    
    print(f"Running corpus admin production tests...")
    if category and category != "all":
        print(f"Category: {category} ({TEST_CATEGORIES[category]})")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)
    
    result = subprocess.run(cmd)
    return result.returncode

def main():
    """Main entry point."""
    category = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if category in ["-h", "--help", "help"]:
        print(__doc__)
        return 0
    
    return run_tests(category)

if __name__ == "__main__":
    sys.exit(main())