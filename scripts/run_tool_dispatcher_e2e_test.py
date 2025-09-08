#!/usr/bin/env python
"""Test Runner for Agent Tool Dispatcher E2E Tests

This script runs the comprehensive E2E tests for UnifiedToolDispatcher
with real services to validate:
- Tool execution with WebSocket events
- User context isolation  
- Business value delivery
- Request-scoped dispatcher pattern
- Performance benchmarks

Usage:
    python scripts/run_tool_dispatcher_e2e_test.py [options]

Options:
    --fast          Run only core tests (faster feedback)
    --full          Run all tests including stress tests
    --performance   Run only performance benchmarks
    --isolation     Run only user isolation tests
    --websocket     Run only WebSocket event tests
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_e2e_tests(test_filter: str = "", verbose: bool = True):
    """Run E2E tests with pytest."""
    test_file = "tests/e2e/test_real_agent_tool_dispatcher.py"
    
    # Base pytest command
    cmd = [
        sys.executable, "-m", "pytest", 
        test_file,
        "-v" if verbose else "",
        "--tb=short",
        "-x",  # Stop on first failure
        "--disable-warnings",
        "-m", "e2e and real_services"
    ]
    
    # Add test filter if specified
    if test_filter:
        cmd.extend(["-k", test_filter])
    
    # Remove empty strings
    cmd = [arg for arg in cmd if arg]
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


def main():
    """Main test runner function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Agent Tool Dispatcher E2E Tests")
    parser.add_argument("--fast", action="store_true", help="Run core tests only")
    parser.add_argument("--full", action="store_true", help="Run all tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--isolation", action="store_true", help="Run isolation tests only")
    parser.add_argument("--websocket", action="store_true", help="Run WebSocket tests only")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    
    args = parser.parse_args()
    
    # Determine test filter based on arguments
    test_filter = ""
    
    if args.fast:
        test_filter = "test_tool_dispatcher_creation or test_websocket_enhancement or test_tool_execution_with_real"
    elif args.performance:
        test_filter = "performance"
    elif args.isolation:
        test_filter = "isolation"
    elif args.websocket:
        test_filter = "websocket"
    elif args.full:
        test_filter = ""  # Run all tests
    else:
        # Default: run core functionality tests
        test_filter = "not (stress_test or concurrent)"
    
    print("Agent Tool Dispatcher E2E Test Suite")
    print("=" * 40)
    print(f"Test filter: {test_filter or 'All tests'}")
    print(f"Project root: {project_root}")
    print()
    
    # Check if test file exists
    test_file_path = project_root / "tests" / "e2e" / "test_real_agent_tool_dispatcher.py"
    if not test_file_path.exists():
        print(f"❌ Test file not found: {test_file_path}")
        return 1
    
    print("✅ Test file found")
    print()
    
    # Run tests
    success = run_e2e_tests(test_filter, verbose=not args.quiet)
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())