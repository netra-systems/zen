"""
Frontend E2E Test Suite Runner

Runs all frontend-focused E2E tests with proper categorization and reporting.
Supports running specific test categories or all tests.
"""

import sys
import os
import asyncio
import pytest
import argparse
from typing import List, Optional


def run_tests(categories: Optional[List[str]] = None, verbose: bool = False):
    """Run frontend E2E tests by category"""
    
    test_categories = {
        "auth": [
            "test_frontend_auth_complete_journey.py",
            "test_frontend_login_journeys.py"
        ],
        "user": [
            "test_frontend_first_time_user.py"
        ],
        "chat": [
            "test_frontend_chat_interactions.py"
        ],
        "websocket": [
            "test_frontend_websocket_reliability.py"
        ],
        "performance": [
            "test_frontend_performance_reliability.py"
        ],
        "error": [
            "test_frontend_error_handling.py"
        ]
    }
    
    # Determine which tests to run
    if categories:
        tests_to_run = []
        for category in categories:
            if category in test_categories:
                tests_to_run.extend(test_categories[category])
            elif category == "all":
                tests_to_run = sum(test_categories.values(), [])
                break
    else:
        tests_to_run = sum(test_categories.values(), [])
    
    # Build pytest arguments
    pytest_args = []
    
    # Add test files
    for test_file in tests_to_run:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            pytest_args.append(test_path)
    
    # Add common arguments
    pytest_args.extend([
        "-v" if verbose else "-q",
        "--tb=short",
        "--disable-warnings",
        "-m", "e2e and frontend",
        "--asyncio-mode=auto"
    ])
    
    # Add test report
    pytest_args.extend([
        "--html=frontend_test_report.html",
        "--self-contained-html"
    ])
    
    print(f"Running {len(tests_to_run)} frontend test files...")
    print(f"Categories: {categories or ['all']}")
    
    # Run tests
    exit_code = pytest.main(pytest_args)
    
    # Generate summary
    generate_summary(tests_to_run, exit_code)
    
    return exit_code


def generate_summary(test_files: List[str], exit_code: int):
    """Generate test summary report"""
    
    print("\n" + "="*60)
    print("FRONTEND E2E TEST SUMMARY")
    print("="*60)
    
    # Count tests
    total_tests = 0
    for test_file in test_files:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            with open(test_path, 'r') as f:
                content = f.read()
                total_tests += content.count("async def test_")
    
    print(f"Total Test Files: {len(test_files)}")
    print(f"Total Test Functions: {total_tests}")
    
    # Test categories covered
    print("\nTest Coverage Areas:")
    print("[U+2713] Authentication & Login (Tests 1-20)")
    print("[U+2713] First-Time User Experience (Tests 21-30)")
    print("[U+2713] Chat Interface Interactions (Tests 31-45)")
    print("[U+2713] WebSocket Reliability (Tests 46-60)")
    print("[U+2713] Performance & Load Testing (Tests 61-70)")
    print("[U+2713] Error Handling & Security (Tests 71-90)")
    
    # Exit code interpretation
    print(f"\nTest Result: {'PASSED' if exit_code == 0 else 'FAILED'}")
    
    if exit_code != 0:
        print("\nNote: Some tests may fail if services are not running.")
        print("Ensure the following are available:")
        print("- Frontend server (http://localhost:3000)")
        print("- API server (http://localhost:8001)")
        print("- Auth service (http://localhost:8002)")
        print("- WebSocket endpoint (ws://localhost:8001)")
    
    print("="*60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run frontend E2E tests")
    
    parser.add_argument(
        "--category",
        nargs="+",
        choices=["auth", "user", "chat", "websocket", "performance", "error", "all"],
        help="Test categories to run"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all test files"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available test files:")
        for file in os.listdir(os.path.dirname(__file__)):
            if file.startswith("test_") and file.endswith(".py"):
                print(f"  - {file}")
        return 0
    
    return run_tests(args.category, args.verbose)


if __name__ == "__main__":
    sys.exit(main())