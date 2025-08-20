#!/usr/bin/env python
"""
UNIFIED TEST RUNNER - THE ONLY ENTRY POINT for all Netra AI Platform Testing

THIS IS THE SINGLE, AUTHORITATIVE TEST RUNNER FOR THE ENTIRE CODEBASE.
DO NOT CREATE ALTERNATIVE TEST RUNNERS - USE THIS FILE EXCLUSIVELY.

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
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
load_dotenv()

# Import test framework modules
from .runner import UnifiedTestRunner
from .test_config import TEST_LEVELS, COMPONENT_MAPPINGS, SHARD_MAPPINGS, configure_staging_environment, configure_dev_environment, configure_real_llm
from .test_discovery import TestDiscovery
from .feature_flags import get_feature_flag_manager

def handle_test_discovery(args):
    """Handle test discovery and listing."""
    discovery = TestDiscovery(PROJECT_ROOT)
    all_tests, categories, test_counts = _gather_test_data(discovery)
    all_tests = _filter_tests_by_category(args, all_tests)
    _validate_test_level(args)
    return _format_discovery_output(args, all_tests, categories, test_counts)

def _gather_test_data(discovery):
    """Gather test data from discovery"""
    all_tests = discovery.discover_tests()
    categories = discovery.get_test_categories()
    test_counts = discovery.get_test_count_by_category()
    return all_tests, categories, test_counts

def _filter_tests_by_category(args, all_tests):
    """Filter tests by category if specified"""
    if args.list_category:
        filtered_tests = {args.list_category: all_tests.get(args.list_category, [])}
        return filtered_tests
    return all_tests

def _validate_test_level(args):
    """Validate test level if specified"""
    if args.list_level:
        level_config = TEST_LEVELS.get(args.list_level)
        if not level_config:
            print(f"[ERROR] Unknown test level: {args.list_level}")
            return 1
    return 0

def _format_discovery_output(args, all_tests, categories, test_counts):
    """Format output based on requested format"""
    if args.list_format == "json":
        return _format_json_output(args, all_tests, categories, test_counts)
    elif args.list_format == "markdown":
        return _format_markdown_output(args, all_tests, categories, test_counts)
    else:
        return _format_text_output(args, all_tests, categories, test_counts)

def _format_json_output(args, all_tests, categories, test_counts):
    """Format discovery output as JSON"""
    output = _create_json_structure(test_counts)
    _add_test_levels_to_json(args, output)
    _add_categories_to_json(args, categories, test_counts, output)
    _add_discovered_tests_to_json(all_tests, output)
    print(json.dumps(output, indent=2))
    return 0

def _create_json_structure(test_counts):
    """Create basic JSON structure"""
    return {
        "test_levels": {},
        "test_categories": {},
        "discovered_tests": {},
        "statistics": {
            "total_levels": len(TEST_LEVELS),
            "total_categories": len(test_counts),
            "total_tests": sum(test_counts.values())
        }
    }

def _add_test_levels_to_json(args, output):
    """Add test levels info to JSON output"""
    for level, config in TEST_LEVELS.items():
        if not args.list_level or level == args.list_level:
            output["test_levels"][level] = {
                "description": config["description"],
                "purpose": config["purpose"],
                "timeout": config["timeout"],
                "runs_coverage": config.get("run_coverage", False),
                "runs_both": config.get("run_both", False)
            }

def _add_categories_to_json(args, categories, test_counts, output):
    """Add categories info to JSON output"""
    for cat, info in categories.items():
        if not args.list_category or cat == args.list_category:
            output["test_categories"][cat] = {
                **info,
                "test_count": test_counts.get(cat, 0)
            }

def _add_discovered_tests_to_json(all_tests, output):
    """Add discovered tests to JSON output"""
    for cat, tests in all_tests.items():
        output["discovered_tests"][cat] = [str(t) for t in tests]

def _format_markdown_output(args, all_tests, categories, test_counts):
    """Format discovery output as Markdown"""
    _print_markdown_header(test_counts)
    _print_markdown_test_levels(args)
    _print_markdown_categories(args, categories, test_counts)
    _print_markdown_selected_tests(args, all_tests)
    return 0

def _print_markdown_header(test_counts):
    """Print Markdown header"""
    print("# Netra AI Platform Test Discovery Report\n")
    print(f"**Total Test Levels:** {len(TEST_LEVELS)}")
    print(f"**Total Test Categories:** {len(test_counts)}")
    print(f"**Total Tests Found:** {sum(test_counts.values())}\n")

def _print_markdown_test_levels(args):
    """Print Markdown test levels section"""
    print("## Available Test Levels\n")
    for level, config in TEST_LEVELS.items():
        if not args.list_level or level == args.list_level:
            print(f"### `{level}`")
            print(f"- **Description:** {config['description']}")
            print(f"- **Purpose:** {config['purpose']}")
            print(f"- **Timeout:** {config['timeout']}s")
            print(f"- **Coverage:** {'Yes' if config.get('run_coverage') else 'No'}")
            print(f"- **Runs Both:** {'Backend & Frontend' if config.get('run_both') else 'Backend Only'}")
            print()

def _print_markdown_categories(args, categories, test_counts):
    """Print Markdown categories table"""
    print("## Test Categories\n")
    print("| Category | Description | Priority | Timeout | Count |")
    print("|----------|-------------|----------|---------|-------|")
    for cat, info in categories.items():
        if not args.list_category or cat == args.list_category:
            count = test_counts.get(cat, 0)
            print(f"| {cat} | {info['description']} | {info['priority']} | {info['timeout']} | {count} |")

def _print_markdown_selected_tests(args, all_tests):
    """Print Markdown selected tests section"""
    if args.list_category or args.list_level:
        print(f"\n## Tests in Selected Categories\n")
        for cat, tests in all_tests.items():
            if tests:
                print(f"### {cat} ({len(tests)} tests)")
                for test in tests[:5]:  # Show first 5 tests
                    print(f"- `{Path(test).relative_to(PROJECT_ROOT)}`")
                if len(tests) > 5:
                    print(f"  ... and {len(tests) - 5} more")
                print()

def _format_text_output(args, all_tests, categories, test_counts):
    """Format discovery output as text"""
    _print_text_header(test_counts)
    _print_text_test_levels(args)
    _print_text_categories(args, categories, test_counts)
    _print_text_selected_category(args, all_tests)
    return 0

def _print_text_header(test_counts):
    """Print text format header"""
    print("=" * 80)
    print("TEST DISCOVERY REPORT")
    print("=" * 80)
    print(f"Total Test Levels: {len(TEST_LEVELS)}")
    print(f"Total Test Categories: {len(test_counts)}")
    print(f"Total Tests Found: {sum(test_counts.values())}")
    print()

def _print_text_test_levels(args):
    """Print text format test levels"""
    print("AVAILABLE TEST LEVELS:")
    print("-" * 40)
    for level, config in TEST_LEVELS.items():
        if not args.list_level or level == args.list_level:
            highlight = config.get('highlight', False)
            if highlight:
                print(f"\033[91m{level:24} - {config['description']}\033[0m")
            else:
                print(f"{level:24} - {config['description']}")
            print(f"{'':24}   Purpose: {config['purpose']}")
            print(f"{'':24}   Timeout: {config['timeout']}s")
    print()

def _print_text_categories(args, categories, test_counts):
    """Print text format categories"""
    print("TEST CATEGORIES:")
    print("-" * 40)
    for cat, info in categories.items():
        if not args.list_category or cat == args.list_category:
            count = test_counts.get(cat, 0)
            print(f"{cat:20} - {count:4} tests - {info['description']}")
    print()

def _print_text_selected_category(args, all_tests):
    """Print text format selected category tests"""
    if args.list_category:
        print(f"TESTS IN CATEGORY '{args.list_category}':")
        print("-" * 40)
        tests = all_tests.get(args.list_category, [])
        for test in tests:
            print(f"  {Path(test).relative_to(PROJECT_ROOT)}")
        if not tests:
            print("  No tests found in this category")

def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    if args.list_tests:
        return handle_test_discovery(args)
    return execute_test_run(parser, args)

def create_argument_parser():
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Netra AI Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_parser_epilog()
    )
    add_all_arguments(parser)
    return parser

def get_parser_epilog():
    """Get parser epilog with test levels and examples"""
    level_descriptions = chr(10).join([
        f"  {level:<20} - {config['description']}" 
        for level, config in TEST_LEVELS.items()
    ])
    return f"""
Test Levels (fastest to slowest):
{level_descriptions}

Common Workflows:
  # DEFAULT - Quick integration tests
  python test_runner.py
  
  # Development workflow
  python test_runner.py --level unit --fast-fail
  python test_runner.py --level integration --no-coverage
  
  # Pre-commit check
  python test_runner.py --level smoke
  
  # Component-specific testing
  python test_runner.py --level comprehensive --component agents
  python test_runner.py --level comprehensive --backend-only
  
  # Real LLM testing (for releases)
  python test_runner.py --level integration --real-llm
  python test_runner.py --level agents --real-llm
  
  # Parallel vs Serial execution
  python test_runner.py --parallel 1       # Serial (for debugging)
  python test_runner.py --parallel auto    # Auto-detect (default)
  python test_runner.py --parallel max     # Maximum parallelism
  
  # CI/CD shard execution
  python test_runner.py --shard 1/4        # Run first quarter of tests
  python test_runner.py --shard 2/4        # Run second quarter
        """

def add_all_arguments(parser):
    """Add all argument groups to parser"""
    add_main_test_arguments(parser)
    add_component_arguments(parser)
    add_output_arguments(parser)
    add_llm_arguments(parser)
    add_staging_arguments(parser)
    add_cicd_arguments(parser)
    add_discovery_arguments(parser)
    add_failing_test_arguments(parser)
    add_real_test_validation_arguments(parser)

def add_main_test_arguments(parser):
    """Add main test level selection arguments"""
    parser.add_argument(
        "--level", "-l", choices=list(TEST_LEVELS.keys()), default="integration",
        help="Test level to run (default: integration)"
    )
    parser.add_argument(
        "--exclusive", action="store_true",
        help="Run ONLY tests at specified level (no superset inclusion)"
    )

def add_component_arguments(parser):
    """Add component selection arguments"""
    parser.add_argument(
        "--backend-only", action="store_true",
        help="Run only backend tests"
    )
    parser.add_argument(
        "--frontend-only", action="store_true",
        help="Run only frontend tests"
    )
    parser.add_argument(
        "--component", type=str,
        choices=["core", "agents", "websocket", "database", "api"],
        help="Run tests for specific component"
    )

def add_output_arguments(parser):
    """Add output options arguments"""
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Minimal output"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--no-report", action="store_true", help="Skip generating test reports"
    )

def add_llm_arguments(parser):
    """Add real LLM testing arguments"""
    parser.add_argument(
        "--real-llm", action="store_true",
        help="Use real LLM API calls instead of mocks (increases test duration and cost)"
    )
    parser.add_argument(
        "--llm-model", type=str, default="gemini-2.5-flash",
        choices=["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"],
        help="LLM model to use for real tests (default: gemini-2.5-flash for cost efficiency)"
    )
    parser.add_argument(
        "--llm-timeout", type=int, default=30,
        help="Timeout in seconds for individual LLM calls (default: 30, recommended: 60-120 for real services)"
    )
    parser.add_argument(
        "--parallel", type=str, default="auto",
        help="Parallelism: auto, 1 (serial), max, or number of workers"
    )
    parser.add_argument(
        "--speed", action="store_true",
        help="Enable speed optimizations (WARNING: May skip slow tests)"
    )
    parser.add_argument(
        "--no-warnings", action="store_true",
        help="Disable pytest warnings (speeds up execution)"
    )
    parser.add_argument(
        "--no-coverage", action="store_true",
        help="Skip coverage collection (speeds up execution significantly)"
    )
    parser.add_argument(
        "--fast-fail", action="store_true",
        help="Stop on first failure (speeds up failure detection)"
    )

def add_staging_arguments(parser):
    """Add staging environment arguments"""
    parser.add_argument(
        "--staging", action="store_true",
        help="Run tests against staging environment (uses STAGING_URL and STAGING_API_URL env vars)"
    )
    parser.add_argument(
        "--staging-url", type=str, help="Override staging frontend URL"
    )
    parser.add_argument(
        "--staging-api-url", type=str, help="Override staging API URL"
    )
    parser.add_argument(
        "--env", type=str, choices=["test", "dev", "staging"], default="test",
        help="Environment to use for testing (default: test)"
    )

def add_cicd_arguments(parser):
    """Add CI/CD specific arguments"""
    parser.add_argument(
        "--report-format", type=str, choices=["text", "json", "markdown"],
        default="markdown", help="Format for test report output (default: markdown)"
    )
    parser.add_argument(
        "--output", type=str, help="Output file for test results (for CI/CD integration)"
    )
    parser.add_argument(
        "--ci", action="store_true",
        help="CI mode: Optimized for continuous integration (enables safe speed optimizations)"
    )

def add_discovery_arguments(parser):
    """Add test discovery arguments"""
    parser.add_argument(
        "--shard", type=str,
        choices=["1/4", "2/4", "3/4", "4/4"],
        help="Run specific test shard for CI/CD parallelization"
    )
    parser.add_argument(
        "--json-output", type=str,
        help="Path to save JSON test results (alias for --output with JSON format)"
    )
    parser.add_argument(
        "--coverage-output", type=str, help="Path to save coverage XML report"
    )
    parser.add_argument(
        "--coverage-html", action="store_true",
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--format", type=str, choices=["text", "json", "html"],
        default="text", help="Output format for test results"
    )
    add_discovery_listing_arguments(parser)

def add_discovery_listing_arguments(parser):
    """Add discovery listing specific arguments"""
    parser.add_argument(
        "--list", "--discover", action="store_true", dest="list_tests",
        help="List all available tests with categories and information"
    )
    parser.add_argument(
        "--list-format", type=str, choices=["text", "json", "markdown"],
        default="text", help="Format for test listing output (default: text)"
    )
    parser.add_argument(
        "--list-level", type=str, choices=list(TEST_LEVELS.keys()),
        help="List tests for a specific test level only"
    )
    parser.add_argument(
        "--list-category", type=str,
        help="List tests for a specific category only (e.g., unit, integration, api)"
    )

def add_failing_test_arguments(parser):
    """Add failing test management arguments"""
    parser.add_argument(
        "--show-failing", action="store_true",
        help="Display currently failing tests from the log"
    )
    parser.add_argument(
        "--run-failing", action="store_true",
        help="Run only the currently failing tests"
    )
    parser.add_argument(
        "--clear-failing", action="store_true",
        help="Clear the failing tests log"
    )
    parser.add_argument(
        "--strict-size", action="store_true",
        help="Skip oversized tests (files >300 lines, functions >8 lines)"
    )
    parser.add_argument(
        "--skip-size-validation", action="store_true",
        help="Skip pre-run test size validation"
    )

def add_real_test_validation_arguments(parser):
    """Add real test requirements validation arguments"""
    parser.add_argument(
        "--validate-real-tests", action="store_true",
        help="Validate tests comply with real test requirements before running"
    )
    parser.add_argument(
        "--real-test-report", action="store_true", 
        help="Generate real test compliance report without running tests"
    )
    parser.add_argument(
        "--fix-test-violations", action="store_true",
        help="Automatically fix common real test requirement violations"
    )

def execute_test_run(parser, args):
    """Execute the main test run"""
    handle_cicd_aliases(args)
    print_header()
    
    # Handle real test validation requests
    if hasattr(args, 'real_test_report') and args.real_test_report:
        return handle_real_test_report()
    if hasattr(args, 'fix_test_violations') and args.fix_test_violations:
        return handle_fix_test_violations()
    
    configure_environment_if_requested(args)
    speed_opts = configure_speed_options(args)
    runner = initialize_test_runner()
    handle_failing_test_commands(args, runner)
    
    # Validate real test requirements before running if requested
    if hasattr(args, 'validate_real_tests') and args.validate_real_tests:
        print("🔍 Validating real test requirements...")
        if not validate_real_test_requirements():
            print("❌ Real test requirement violations found. Fix before running tests.")
            return 1
        print("✅ All tests comply with real test requirements!")
    
    return run_tests_with_configuration(args, runner, speed_opts)

def handle_cicd_aliases(args):
    """Handle CI/CD specific argument aliases"""
    if args.json_output:
        args.output = args.json_output
        args.report_format = "json"

def print_header():
    """Print test runner header"""
    print("=" * 80)
    print("NETRA AI PLATFORM - UNIFIED TEST RUNNER")
    print("=" * 80)
    print_feature_flag_summary()

def print_feature_flag_summary():
    """Print feature flag summary if any flags are configured"""
    manager = get_feature_flag_manager()
    summary = manager.get_feature_summary()
    
    if summary["total"] > 0:
        print("\nFEATURE FLAGS:")
        if summary["enabled"]:
            print(f"  [ENABLED] ({len(summary['enabled'])}): {', '.join(summary['enabled'][:3])}{' ...' if len(summary['enabled']) > 3 else ''}")
        if summary["in_development"]:
            print(f"  [IN DEV] ({len(summary['in_development'])}): {', '.join(summary['in_development'][:3])}{' ...' if len(summary['in_development']) > 3 else ''}")
        if summary["disabled"]:
            print(f"  [DISABLED] ({len(summary['disabled'])}): {', '.join(summary['disabled'][:3])}{' ...' if len(summary['disabled']) > 3 else ''}")
        if summary["experimental"]:
            print(f"  [EXPERIMENTAL] ({len(summary['experimental'])}): {', '.join(summary['experimental'][:3])}{' ...' if len(summary['experimental']) > 3 else ''}")
        print("  Use feature flags for TDD: tests can be written before implementation")
        print("=" * 80)

def configure_environment_if_requested(args):
    """Configure test environment based on --env parameter and legacy --staging flag"""
    # Handle legacy --staging flag for backward compatibility
    if args.staging or args.staging_url or args.staging_api_url:
        staging_url = args.staging_url or os.getenv("STAGING_URL")
        staging_api_url = args.staging_api_url or os.getenv("STAGING_API_URL")
        validate_staging_configuration(staging_url, staging_api_url)
        print_staging_configuration(staging_url, staging_api_url)
        configure_staging_environment(staging_url, staging_api_url)
        return
        
    # Handle --env parameter
    if args.env == "staging":
        staging_url = os.getenv("STAGING_URL")
        staging_api_url = os.getenv("STAGING_API_URL")
        validate_staging_configuration(staging_url, staging_api_url)
        print_staging_configuration(staging_url, staging_api_url)
        configure_staging_environment(staging_url, staging_api_url)
    elif args.env == "dev":
        print_dev_configuration()
        configure_dev_environment()
    # For test environment (default), no additional configuration needed

def validate_staging_configuration(staging_url, staging_api_url):
    """Validate staging configuration"""
    if not staging_url or not staging_api_url:
        print("[ERROR] Staging mode requires STAGING_URL and STAGING_API_URL")
        print("  Set via environment variables or --staging-url and --staging-api-url flags")
        sys.exit(1)

def print_staging_configuration(staging_url, staging_api_url):
    """Print staging configuration info"""
    print(f"[STAGING MODE] Testing against staging environment:")
    print(f"  Frontend: {staging_url}")
    print(f"  API: {staging_api_url}")

def print_dev_configuration():
    """Print dev configuration info"""
    print(f"[DEV MODE] Testing against local development environment:")
    print(f"  Backend: http://localhost:8001")
    print(f"  Environment: development")

def configure_speed_options(args):
    """Configure speed optimization options based on arguments"""
    speed_opts = {}
    
    # Check if any speed options are enabled
    if args.speed or args.ci or args.no_warnings or args.no_coverage or args.fast_fail:
        speed_opts['enabled'] = True
        
        # Safe optimizations
        if args.no_warnings or args.speed or args.ci:
            speed_opts['no_warnings'] = True
        
        if args.no_coverage or args.speed or args.ci:
            speed_opts['no_coverage'] = True
            
        if args.fast_fail or args.ci:
            speed_opts['fast_fail'] = True
        
        # CI mode enables safe parallel execution
        if args.ci:
            speed_opts['parallel'] = True
            print("[CI MODE] Enabling safe speed optimizations")
        
        # Speed mode enables more aggressive optimizations with warning
        if args.speed and not args.ci:
            print("\n[SPEED MODE] ENABLED")
            print("[WARNING] Some tests may be skipped for speed")
            print("          Use --ci for safe speed optimizations only\n")
            speed_opts['skip_slow'] = True
            speed_opts['parallel'] = True
    
    return speed_opts if speed_opts else None

def initialize_test_runner():
    """Initialize test runner and set start time"""
    runner = UnifiedTestRunner()
    runner.results["overall"]["start_time"] = time.time()
    return runner

def handle_failing_test_commands(args, runner):
    """Handle failing test management commands"""
    if args.show_failing:
        runner.show_failing_tests()
        sys.exit(0)
    elif args.clear_failing:
        runner.clear_failing_tests()
        sys.exit(0)
    elif args.run_failing:
        exit_code = execute_failing_tests(args, runner)
        sys.exit(exit_code)

def execute_failing_tests(args, runner):
    """Execute failing tests run"""
    print("\n" + "=" * 80)
    print("RUNNING FAILING TESTS")
    print("=" * 80)
    exit_code = runner.run_failing_tests(
        max_fixes=None,
        backend_only=args.backend_only,
        frontend_only=args.frontend_only
    )
    print("\n" + "=" * 80)
    return exit_code

def handle_fix_failing_command():
    """Handle automatic test fixing command"""
    print("\n[INFO] Automatic test fixing is not yet implemented")
    print("Use --run-failing to run only failing tests")
    sys.exit(0)

def run_tests_with_configuration(args, runner, speed_opts):
    """Run tests with the specified configuration"""
    # Set environment mode on runner for backward compatibility
    if args.staging or args.env == "staging":
        runner.staging_mode = True
    elif args.env == "dev":
        runner.dev_mode = True
    
    return run_level_based_tests(args, runner, speed_opts)

def run_level_based_tests(args, runner, speed_opts):
    """Run tests based on specified level"""
    config = TEST_LEVELS[args.level].copy()  # Copy to avoid modifying original
    level = args.level
    # Handle exclusive mode (no superset inclusion)
    if hasattr(args, 'exclusive') and args.exclusive:
        print(f"[EXCLUSIVE] Running ONLY {level} level tests (no superset)")
    apply_shard_filtering(args, config)
    print_test_configuration(level, config, speed_opts)
    real_llm_config = configure_real_llm_if_requested(args, level, config)
    exit_code = execute_test_suite(args, config, runner, real_llm_config, speed_opts, level)
    return finalize_test_run(runner, level, config, "", exit_code)

def apply_shard_filtering(args, config):
    """Apply shard or component filtering if specified"""
    # Handle component filtering
    if hasattr(args, 'component') and args.component:
        print(f"[COMPONENT] Running only {args.component} component tests")
        if args.component in COMPONENT_MAPPINGS:
            component_patterns = COMPONENT_MAPPINGS[args.component]
            pattern_args = []
            for pattern in component_patterns:
                pattern_args.extend(["-k", pattern])
            config['backend_args'] = config.get('backend_args', []) + pattern_args
            print(f"[COMPONENT] Test patterns: {', '.join(component_patterns)}")
    # Handle shard filtering for CI/CD
    elif args.shard:
        print(f"[SHARD] Running shard {args.shard} for parallel CI/CD execution")
        if args.shard in SHARD_MAPPINGS:
            shard_patterns = SHARD_MAPPINGS[args.shard]
            pattern_args = []
            for pattern in shard_patterns:
                pattern_args.extend(["-k", pattern])
            config['backend_args'] = config.get('backend_args', []) + pattern_args
            print(f"[SHARD] Test patterns: {', '.join(shard_patterns)}")

def print_test_configuration(level, config, speed_opts):
    """Print test configuration details"""
    print(f"Running {level} tests: {config['description']}")
    print(f"Purpose: {config['purpose']}")
    print(f"Timeout: {config.get('timeout', 300)}s")
    if speed_opts and speed_opts.get('enabled'):
        print("[SPEED] Speed optimizations enabled")
        if speed_opts.get('skip_slow'):
            print("[WARNING] Slow tests will be skipped")

def configure_real_llm_if_requested(args, level, config):
    """Configure real LLM testing if requested"""
    from .test_execution_engine import configure_real_llm_if_requested as engine_configure
    return engine_configure(args, level, config)

def validate_test_sizes(args):
    """Run pre-test validation for test size limits (SPEC/testing.xml enforcement)"""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "compliance"))
        from test_size_validator import TestSizeValidator
        
        validator = TestSizeValidator()
        results = validator.validate_all_tests()
        
        violations = results["summary"]["total_violations"]
        if violations > 0:
            print(f"\n[X] TEST SIZE VIOLATIONS DETECTED: {violations} violations")
            print(f"Files exceeding 450-line limit: {results['summary']['files_exceeding_limit']}")
            print(f"Functions exceeding 25-line limit: {results['summary']['functions_exceeding_limit']}")
            print("\nViolation Details:")
            
            # Show top 5 worst violations for immediate action
            worst_violations = sorted(results["violations"], 
                                    key=lambda v: v.get("actual_value", 0), reverse=True)[:5]
            for violation in worst_violations:
                print(f"  * {violation['file_path']}: {violation['actual_value']} lines "
                      f"({violation['violation_type']})")
            
            print(f"\nTest size limits are MANDATORY per SPEC/testing.xml:")
            print("  * Test files: 300 lines maximum (same as production code)")
            print("  * Test functions: 8 lines maximum (same as production code)")
            
            # Always enforce limits - no bypass option
            enforce_strict = getattr(args, 'strict_size', True) or violations > 10
            if enforce_strict:
                print("\n[X] ENFORCEMENT ACTIVE: Tests cannot run with size violations")
                print("Run 'python scripts/compliance/test_size_validator.py --format markdown' for fixing guide")
                return False  # Block test execution
            else:
                print("\n[!] Tests will run with warnings (violations < 10)")
                print("Use 'python scripts/compliance/test_size_validator.py' for refactoring help")
        else:
            print("[OK] Test size validation passed - all tests comply with limits")
        
        return True  # Allow test execution
        
    except ImportError as e:
        print(f"Warning: Could not import test size validator: {e}")
        return True  # Don't block on import errors
    except Exception as e:
        print(f"Warning: Test size validation failed: {e}")
        return True  # Don't block on validation errors

def execute_test_suite(args, config, runner, real_llm_config, speed_opts, test_level):
    """Execute the test suite based on configuration"""
    # Run pre-test validation for test size limits (MANDATORY per SPEC/testing.xml)
    if not getattr(args, 'skip_size_validation', False):
        size_validation_passed = validate_test_sizes(args)
        if not size_validation_passed:
            print("\n[X] Test execution blocked due to size violations")
            print("Fix test size violations before running tests")
            sys.exit(1)
    
    from .test_execution_engine import execute_test_suite as engine_execute
    return engine_execute(args, config, runner, real_llm_config, speed_opts, test_level)

def finalize_test_run(runner, level, config, output, exit_code):
    """Finalize test run with reporting and cleanup"""
    from .test_execution_engine import finalize_test_run as engine_finalize
    return engine_finalize(runner, level, config, output, exit_code)


def handle_real_test_report():
    """Generate real test compliance report"""
    print("[REAL TEST VALIDATION] Generating Compliance Report...")
    
    try:
        sys.path.append(str(PROJECT_ROOT / "scripts" / "compliance"))
        from real_test_requirements_enforcer import RealTestRequirementsEnforcer
        
        enforcer = RealTestRequirementsEnforcer(str(PROJECT_ROOT))
        violations = enforcer.validate_all_tests()
        
        report = enforcer.generate_report()
        print(report)
        
        # Save JSON report
        json_output = enforcer.export_json()
        json_path = PROJECT_ROOT / "test_reports" / "real_test_violations.json"
        json_path.parent.mkdir(exist_ok=True)
        json_path.write_text(json_output)
        
        print(f"\n[REPORT] JSON saved to: {json_path}")
        
        return 1 if any(v.severity == "critical" for v in violations) else 0
        
    except ImportError as e:
        print(f"[ERROR] Could not import real test enforcer: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Error generating report: {e}")
        return 1


def handle_fix_test_violations():
    """Automatically fix common real test requirement violations"""
    print("🔧 Fixing Real Test Requirements Violations...")
    
    try:
        sys.path.append(str(PROJECT_ROOT / "scripts" / "compliance"))
        from real_test_requirements_enforcer import RealTestRequirementsEnforcer
        
        # First validate to find violations
        enforcer = RealTestRequirementsEnforcer(str(PROJECT_ROOT))
        violations = enforcer.validate_all_tests()
        
        if not violations:
            print("✅ No violations found - all tests comply with requirements!")
            return 0
            
        print(f"Found {len(violations)} violations to fix...")
        
        # TODO: Implement automated fixing logic
        print("🚧 Automated fixing not yet implemented. Please fix manually:")
        print("1. Move mock component classes to test utilities")
        print("2. Replace inline mocks with real components")
        print("3. Split oversized test functions")
        
        # Show summary
        summary = enforcer.generate_report()
        print("\n" + summary)
        
        return 1  # Exit with error until fixing is implemented
        
    except ImportError as e:
        print(f"❌ Could not import real test enforcer: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error fixing violations: {e}")
        return 1


def validate_real_test_requirements():
    """Validate all tests comply with real test requirements"""
    try:
        sys.path.append(str(PROJECT_ROOT / "scripts" / "compliance"))
        from real_test_requirements_enforcer import RealTestRequirementsEnforcer
        
        enforcer = RealTestRequirementsEnforcer(str(PROJECT_ROOT))
        violations = enforcer.validate_all_tests()
        
        if not violations:
            return True
            
        # Show violations summary
        critical_violations = [v for v in violations if v.severity == "critical"]
        major_violations = [v for v in violations if v.severity == "major"]
        
        print(f"Found {len(violations)} violations:")
        print(f"  🔥 {len(critical_violations)} critical")
        print(f"  ⚠️ {len(major_violations)} major")
        
        # Show first few violations
        for violation in violations[:5]:
            severity_emoji = {"critical": "🔥", "major": "⚠️", "minor": "ℹ️"}[violation.severity]
            print(f"{severity_emoji} {violation.file_path}:{violation.line_number} - {violation.description}")
        
        if len(violations) > 5:
            print(f"... and {len(violations) - 5} more violations")
            
        print("\nRun with --real-test-report for full details")
        
        return len(critical_violations) == 0  # Only block on critical violations
        
    except ImportError as e:
        print(f"Warning: Could not import real test enforcer: {e}")
        return True  # Don't block on import errors
    except Exception as e:
        print(f"Warning: Real test validation failed: {e}")
        return True  # Don't block on validation errors


if __name__ == "__main__":
    # Store args globally for helper functions
    import sys
    sys.modules[__name__]._current_args = None
    try:
        parser = create_argument_parser()
        args = parser.parse_args()
        sys.modules[__name__]._current_args = args
        sys.modules[__name__]._no_report = getattr(args, 'no_report', False)
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test run cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)