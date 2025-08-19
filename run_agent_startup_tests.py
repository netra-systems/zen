#!/usr/bin/env python
"""
Agent Startup E2E Test Runner - Simple Command Line Interface

Easy-to-use command line interface for running all agent startup E2E tests.
Provides simple integration with existing test_runner.py framework.

Business Value Justification (BVJ):
1. Segment: ALL customer segments 
2. Business Goal: Easy execution of critical agent startup validation
3. Value Impact: Simplifies testing workflow for development teams
4. Revenue Impact: Prevents startup issues that could block customer usage

USAGE EXAMPLES:
    python run_agent_startup_tests.py                    # Run with mocks
    python run_agent_startup_tests.py --real-llm         # Run with real LLM
    python run_agent_startup_tests.py --real-llm --sequential  # Real LLM sequential
    python run_agent_startup_tests.py --info             # Show test information

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Simple wrapper around comprehensive test runner
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import test framework components
from tests.unified.agent_startup_integration import (
    run_startup_tests_integration,
    get_startup_test_info,
    create_integration_handler
)


class SimpleStartupTestRunner:
    """Simple command-line interface for agent startup tests."""
    
    def __init__(self):
        """Initialize simple test runner."""
        self.integration = create_integration_handler()
    
    def create_argument_parser(self) -> argparse.ArgumentParser:
        """Create command line argument parser."""
        parser = argparse.ArgumentParser(
            description="Agent Startup E2E Test Runner",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_usage_examples()
        )
        
        self._add_test_execution_args(parser)
        self._add_information_args(parser)
        return parser
    
    def _add_test_execution_args(self, parser: argparse.ArgumentParser) -> None:
        """Add test execution arguments."""
        parser.add_argument(
            "--real-llm", action="store_true",
            help="Use real LLM API calls instead of mocks (increases duration and cost)"
        )
        parser.add_argument(
            "--sequential", action="store_true",
            help="Run tests sequentially instead of in parallel (safer but slower)"
        )
        parser.add_argument(
            "--timeout", type=int, default=300,
            help="Timeout in seconds for the entire test suite (default: 300)"
        )
    
    def _add_information_args(self, parser: argparse.ArgumentParser) -> None:
        """Add information and discovery arguments."""
        parser.add_argument(
            "--info", action="store_true",
            help="Show detailed information about agent startup tests"
        )
        parser.add_argument(
            "--list-categories", action="store_true",
            help="List all available test categories"
        )
        parser.add_argument(
            "--estimate", action="store_true",
            help="Show estimated execution time"
        )
    
    def _get_usage_examples(self) -> str:
        """Get usage examples for help text."""
        return """
Usage Examples:
  # Quick test with mocks (recommended for development)
  python run_agent_startup_tests.py
  
  # Full validation with real LLM (recommended for releases)
  python run_agent_startup_tests.py --real-llm
  
  # Safe sequential execution with real LLM
  python run_agent_startup_tests.py --real-llm --sequential
  
  # Show test information and categories
  python run_agent_startup_tests.py --info
  
  # List available test categories
  python run_agent_startup_tests.py --list-categories

Integration with test_runner.py:
  # Use the main test runner for full integration
  python test_runner.py --level agent-startup --real-llm
        """
    
    async def execute_tests(self, args) -> int:
        """Execute agent startup tests based on arguments."""
        print(self._get_execution_header(args))
        
        if self._should_skip_execution(args):
            return 0
        
        try:
            return await self._run_startup_test_suite(args)
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Test execution cancelled by user")
            return 130
        except Exception as e:
            print(f"\n[ERROR] Test execution failed: {e}")
            return 1
    
    def _get_execution_header(self, args) -> str:
        """Get execution header with configuration info."""
        return f"""
{'='*80}
AGENT STARTUP E2E TEST RUNNER
{'='*80}
Real LLM: {'Enabled' if args.real_llm else 'Disabled (using mocks)'}
Execution: {'Sequential' if args.sequential else 'Parallel'}
Timeout: {args.timeout} seconds
{'='*80}"""
    
    def _should_skip_execution(self, args) -> bool:
        """Check if execution should be skipped for info commands."""
        if args.info:
            self._print_test_info()
            return True
        
        if args.list_categories:
            self._print_test_categories()
            return True
        
        if args.estimate:
            self._print_time_estimates(args)
            return True
        
        return False
    
    async def _run_startup_test_suite(self, args) -> int:
        """Run the startup test suite with timeout."""
        try:
            task = run_startup_tests_integration(
                real_llm=args.real_llm,
                parallel=not args.sequential
            )
            
            return await asyncio.wait_for(task, timeout=args.timeout)
        except asyncio.TimeoutError:
            print(f"\n[TIMEOUT] Test suite exceeded {args.timeout} seconds")
            return 124


class StartupTestInfoPrinter:
    """Handles printing test information and help."""
    
    def __init__(self, runner: SimpleStartupTestRunner):
        """Initialize info printer."""
        self.runner = runner
        self.test_info = get_startup_test_info()
    
    def print_test_info(self) -> None:
        """Print detailed test information."""
        print(f"\n{'='*80}")
        print("AGENT STARTUP TEST INFORMATION")
        print(f"{'='*80}")
        
        self._print_basic_info()
        self._print_category_details()
        self._print_execution_info()
    
    def _print_basic_info(self) -> None:
        """Print basic test suite information."""
        print(f"Name: {self.test_info['name']}")
        print(f"Description: {self.test_info['description']}")
        print(f"Total Categories: {len(self.test_info['categories'])}")
        print(f"Business Value: {self.test_info['business_value']}")
    
    def _print_category_details(self) -> None:
        """Print detailed category information."""
        print(f"\nTest Categories:")
        print("-" * 80)
        
        for category in self.test_info['categories']:
            name = category['name']
            desc = category['description']
            llm_req = "Yes" if category['requires_real_llm'] else "No"
            timeout = category['timeout']
            
            print(f"{name:<20} | {desc:<40} | LLM: {llm_req:<3} | {timeout}s")
    
    def _print_execution_info(self) -> None:
        """Print execution configuration information."""
        print(f"\nExecution Configuration:")
        print(f"Supports Real LLM: {self.test_info['supports_real_llm']}")
        print(f"Supports Parallel: {self.test_info['supports_parallel']}")
        print(f"Estimated Duration: {self.test_info['estimated_duration']} seconds")
    
    def print_test_categories(self) -> None:
        """Print just the test categories."""
        print("Available Test Categories:")
        for category in self.test_info['categories']:
            print(f"  - {category['name']}: {category['description']}")
    
    def print_time_estimates(self, args) -> None:
        """Print execution time estimates."""
        base_time = 60 if not args.real_llm else 120
        multiplier = 1.5 if args.sequential else 1.0
        estimated_time = int(base_time * multiplier)
        
        print(f"Estimated Execution Time:")
        print(f"  Configuration: {'Real LLM' if args.real_llm else 'Mocked'}, {'Sequential' if args.sequential else 'Parallel'}")
        print(f"  Estimated Time: {estimated_time} seconds ({estimated_time//60}m {estimated_time%60}s)")


def main():
    """Main entry point for command-line execution."""
    runner = SimpleStartupTestRunner()
    info_printer = StartupTestInfoPrinter(runner)
    
    # Add info printer methods to runner for convenience
    runner._print_test_info = info_printer.print_test_info
    runner._print_test_categories = info_printer.print_test_categories
    runner._print_time_estimates = info_printer.print_time_estimates
    
    parser = runner.create_argument_parser()
    args = parser.parse_args()
    
    async def async_main():
        """Async main function."""
        return await runner.execute_tests(args)
    
    # Run async main and exit with appropriate code
    exit_code = asyncio.run(async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()