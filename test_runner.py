#!/usr/bin/env python
"""
UNIFIED TEST RUNNER - Single Entry Point for all Netra AI Platform Testing

PURPOSE:
Provides a consistent interface for running different levels of tests,
from quick smoke tests to comprehensive test suites.

TEST LEVELS:
- smoke: Quick validation (< 30s) - Run before commits
- unit: Component testing (1-2 min) - Run during development
- integration: Feature testing (3-5 min) - Run before merges
- comprehensive: Full coverage (30-45 min) - Run before releases
- critical: Essential paths (1-2 min) - Run for hotfixes

KEY FEATURES:
- Automatic test categorization and organization
- Parallel execution for faster results
- Detailed HTML and JSON reports
- Coverage tracking with targets
- Smart test selection based on changes

USAGE:
    python test_runner.py --level smoke        # Quick pre-commit check
    python test_runner.py --level unit         # Development testing
    python test_runner.py --level comprehensive # Full validation
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
load_dotenv()

# Import test framework modules
from test_framework import UnifiedTestRunner, TEST_LEVELS, SHARD_MAPPINGS
from test_framework.test_config import configure_staging_environment, configure_real_llm

def main():
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Netra AI Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Test Levels:
{chr(10).join([f"  {level:<12} - {config['description']}" for level, config in TEST_LEVELS.items()])}

Usage Examples:
  # Quick smoke tests (recommended for pre-commit)
  python test_runner.py --level smoke
  
  # Unit tests for development
  python test_runner.py --level unit
  
  # Full comprehensive testing
  python test_runner.py --level comprehensive
  
  # Backend only testing
  python test_runner.py --level unit --backend-only
  
  # Use simple test runner
  python test_runner.py --simple
  
  # Run ALL tests (backend, frontend, E2E) - comprehensive validation
  python test_runner.py --level all
  
  # Real LLM testing examples:
  # Unit tests with real LLM calls
  python test_runner.py --level unit --real-llm
  
  # Integration tests with specific model
  python test_runner.py --level integration --real-llm --llm-model gemini-2.5-pro
  
  # Critical tests sequentially to avoid rate limits
  python test_runner.py --level critical --real-llm --parallel 1
  
  # Comprehensive with extended timeout
  python test_runner.py --level comprehensive --real-llm --llm-timeout 120

Purpose Guide:
  - smoke:         Use before committing code, quick validation (never uses real LLM)
  - unit:          Use during development, test individual components  
  - integration:   Use when testing feature interactions
  - comprehensive: Use before releases, full system validation
  - critical:      Use to verify essential functionality only
  - all:           Complete validation including backend, frontend, and E2E tests
  
Real LLM Testing:
  - Adds --real-llm flag to use actual API calls instead of mocks
  - Increases test duration 3-5x and incurs API costs
  - Use gemini-2.5-flash (default) for cost efficiency
  - Run sequentially (--parallel 1) with production keys to avoid rate limits
        """
    )
    
    # Main test level selection
    parser.add_argument(
        "--level", "-l",
        choices=list(TEST_LEVELS.keys()),
        default="smoke",
        help="Test level to run (default: smoke)"
    )
    
    # Alternative runners
    parser.add_argument(
        "--simple",
        action="store_true", 
        help="Use simple test runner (overrides --level)"
    )
    
    # Component selection
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Run only backend tests"
    )
    parser.add_argument(
        "--frontend-only", 
        action="store_true",
        help="Run only frontend tests"
    )
    
    # Output options
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Verbose output"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating test reports"
    )
    
    # Real LLM testing options
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Use real LLM API calls instead of mocks (increases test duration and cost)"
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="gemini-2.5-flash",
        choices=["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"],
        help="LLM model to use for real tests (default: gemini-2.5-flash for cost efficiency)"
    )
    parser.add_argument(
        "--llm-timeout",
        type=int,
        default=30,
        help="Timeout in seconds for individual LLM calls (default: 30, recommended: 30-120)"
    )
    parser.add_argument(
        "--parallel",
        type=str,
        default="auto",
        help="Parallelism for tests: auto, 1 (sequential), or number of workers"
    )
    
    # Staging environment support
    parser.add_argument(
        "--staging",
        action="store_true",
        help="Run tests against staging environment (uses STAGING_URL and STAGING_API_URL env vars)"
    )
    parser.add_argument(
        "--staging-url",
        type=str,
        help="Override staging frontend URL"
    )
    parser.add_argument(
        "--staging-api-url",
        type=str,
        help="Override staging API URL"
    )
    parser.add_argument(
        "--report-format",
        type=str,
        choices=["text", "json", "markdown"],
        default="markdown",
        help="Format for test report output (default: markdown)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for test results (for CI/CD integration)"
    )
    
    # CI/CD specific arguments for compatibility with GitHub workflows
    parser.add_argument(
        "--shard",
        type=str,
        choices=["core", "agents", "websocket", "database", "api", "frontend"],
        help="Run a specific shard of tests for parallel execution"
    )
    parser.add_argument(
        "--json-output",
        type=str,
        help="Path to save JSON test results (alias for --output with JSON format)"
    )
    parser.add_argument(
        "--coverage-output", 
        type=str,
        help="Path to save coverage XML report"
    )
    
    # Failing test management options
    parser.add_argument(
        "--show-failing",
        action="store_true",
        help="Display currently failing tests from the log"
    )
    parser.add_argument(
        "--run-failing",
        action="store_true",
        help="Run only the currently failing tests"
    )
    parser.add_argument(
        "--fix-failing",
        action="store_true",
        help="Attempt to automatically fix failing tests (experimental)"
    )
    parser.add_argument(
        "--max-fixes",
        type=int,
        default=None,
        help="Maximum number of tests to attempt fixing (default: all)"
    )
    parser.add_argument(
        "--clear-failing",
        action="store_true",
        help="Clear the failing tests log"
    )
    
    args = parser.parse_args()
    
    # Handle CI/CD specific argument aliases
    if args.json_output:
        args.output = args.json_output
        args.report_format = "json"
    
    # Print header
    print("=" * 80)
    print("NETRA AI PLATFORM - UNIFIED TEST RUNNER")
    print("=" * 80)
    
    # Configure staging environment if requested
    if args.staging or args.staging_url or args.staging_api_url:
        staging_url = args.staging_url or os.getenv("STAGING_URL")
        staging_api_url = args.staging_api_url or os.getenv("STAGING_API_URL")
        
        if not staging_url or not staging_api_url:
            print("[ERROR] Staging mode requires STAGING_URL and STAGING_API_URL")
            print("  Set via environment variables or --staging-url and --staging-api-url flags")
            sys.exit(1)
        
        print(f"[STAGING MODE] Testing against staging environment:")
        print(f"  Frontend: {staging_url}")
        print(f"  API: {staging_api_url}")
        
        configure_staging_environment(staging_url, staging_api_url)
    
    # Initialize test runner
    runner = UnifiedTestRunner()
    runner.results["overall"]["start_time"] = time.time()
    
    # Add staging flag to runner if needed
    if args.staging:
        runner.staging_mode = True
    
    # Handle failing test management commands
    if args.show_failing:
        runner.show_failing_tests()
        sys.exit(0)
    
    elif args.clear_failing:
        runner.clear_failing_tests()
        sys.exit(0)
    
    elif args.run_failing:
        print("\n" + "=" * 80)
        print("RUNNING FAILING TESTS")
        print("=" * 80)
        
        exit_code = runner.run_failing_tests(
            max_fixes=args.max_fixes,
            backend_only=args.backend_only,
            frontend_only=args.frontend_only
        )
        
        print("\n" + "=" * 80)
        sys.exit(exit_code)
    
    elif args.fix_failing:
        # This would be where automatic fixing logic would go
        # For now, just inform that it's not yet implemented
        print("\n[INFO] Automatic test fixing is not yet implemented")
        print("Use --run-failing to run only failing tests")
        sys.exit(0)
    
    # Determine test configuration
    if args.simple:
        print(f"Running simple test validation...")
        exit_code, output = runner.run_simple_tests()
        config = {"description": "Simple test validation", "purpose": "Basic functionality check"}
        level = "simple"
    else:
        config = TEST_LEVELS[args.level]
        level = args.level
        
        # Handle shard filtering if specified
        if args.shard:
            print(f"[SHARD] Running only {args.shard} shard for {level} tests")
            
            # Modify backend args to include only shard-specific tests
            if args.shard in SHARD_MAPPINGS and args.shard != "frontend":
                shard_patterns = SHARD_MAPPINGS[args.shard]
                # Add pattern matching to backend args
                pattern_args = []
                for pattern in shard_patterns:
                    pattern_args.extend(["-k", pattern])
                config['backend_args'] = config.get('backend_args', []) + pattern_args
                print(f"[SHARD] Test patterns: {', '.join(shard_patterns)}")
            elif args.shard == "frontend":
                # Frontend shard runs only frontend tests
                args.frontend_only = True
                args.backend_only = False
        
        print(f"Running {level} tests: {config['description']}")
        print(f"Purpose: {config['purpose']}")
        print(f"Timeout: {config.get('timeout', 300)}s")
        
        # Prepare real LLM configuration if requested
        real_llm_config = None
        if args.real_llm:
            # Smoke tests should never use real LLM for speed
            if level == "smoke":
                print("[WARNING] Real LLM testing disabled for smoke tests (use unit or higher)")
            else:
                real_llm_config = configure_real_llm(args.llm_model, args.llm_timeout, args.parallel)
                print(f"[INFO] Real LLM testing enabled")
                print(f"  - Model: {args.llm_model}")
                print(f"  - Timeout: {args.llm_timeout}s per call")
                print(f"  - Parallelism: {args.parallel}")
                
                # Adjust test timeout for real LLM tests
                adjusted_timeout = config.get('timeout', 300) * 3  # Triple timeout for real LLM
                config['timeout'] = adjusted_timeout
                print(f"  - Adjusted test timeout: {adjusted_timeout}s")
        
        # Run tests based on selection
        backend_exit = 0
        frontend_exit = 0
        
        if args.backend_only:
            backend_exit, _ = runner.run_backend_tests(
                config['backend_args'], 
                config.get('timeout', 300),
                real_llm_config
            )
            runner.results["frontend"]["status"] = "skipped"
            exit_code = backend_exit
        elif args.frontend_only:
            frontend_exit, _ = runner.run_frontend_tests(
                config['frontend_args'],
                config.get('timeout', 300)  
            )
            runner.results["backend"]["status"] = "skipped"
            exit_code = frontend_exit
        else:
            # Run both if config specifies it, or if it's a comprehensive level
            if config.get('run_both', True):
                backend_exit, _ = runner.run_backend_tests(
                    config['backend_args'],
                    config.get('timeout', 300),
                    real_llm_config
                )
                frontend_exit, _ = runner.run_frontend_tests(
                    config['frontend_args'], 
                    config.get('timeout', 300)
                )
                exit_code = max(backend_exit, frontend_exit)
                
                # Run E2E tests if specified
                if config.get('run_e2e', False):
                    e2e_exit, _ = runner.run_e2e_tests(
                        [],  # E2E tests don't need additional args
                        config.get('timeout', 600)
                    )
                    exit_code = max(exit_code, e2e_exit)
            else:
                # Backend only for critical tests
                backend_exit, _ = runner.run_backend_tests(
                    config['backend_args'],
                    config.get('timeout', 300),
                    real_llm_config
                )
                runner.results["frontend"]["status"] = "skipped"
                exit_code = backend_exit
    
    # Record end time
    runner.results["overall"]["end_time"] = time.time()
    runner.results["overall"]["status"] = "passed" if exit_code == 0 else "failed"
    
    # Generate and save report
    if not args.no_report:
        runner.save_test_report(level, config, "", exit_code)
        
        # Save in additional formats if requested
        if args.output:
            if args.report_format == "json":
                # Generate JSON report for CI/CD
                json_report = runner.generate_json_report(level, config, exit_code)
                with open(args.output, "w", encoding='utf-8') as f:
                    json.dump(json_report, f, indent=2)
                print(f"[REPORT] JSON report saved to: {args.output}")
            elif args.report_format == "text":
                # Generate text report
                text_report = runner.generate_text_report(level, config, exit_code)
                with open(args.output, "w", encoding='utf-8') as f:
                    f.write(text_report)
                print(f"[REPORT] Text report saved to: {args.output}")
        
        # Generate coverage report if requested
        if args.coverage_output:
            try:
                # Try to generate coverage XML report
                coverage_cmd = [sys.executable, "-m", "coverage", "xml", "-o", args.coverage_output]
                subprocess.run(coverage_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
                if Path(args.coverage_output).exists():
                    print(f"[COVERAGE] Coverage report saved to: {args.coverage_output}")
                else:
                    print(f"[WARNING] Coverage report generation failed - file not created")
            except Exception as e:
                print(f"[WARNING] Could not generate coverage report: {e}")
    
    # Print summary
    runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(exit_code)

if __name__ == "__main__":
    main()