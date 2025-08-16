#!/usr/bin/env python
"""
Enhanced Real Service Test Runner with Comprehensive Reporting
ULTRA DEEP THINK: Module-based architecture - Main coordinator ≤300 lines

This script runs real service tests with detailed metrics collection and reporting:
- Tracks LLM API calls and costs
- Monitors database query performance
- Measures cache effectiveness
- Generates quality score reports
- Creates detailed HTML/JSON reports
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional
from real_service_test_metrics import RealServiceTestMetrics
from real_service_test_runner import EnhancedRealServiceTestRunner

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enhanced Real Service Test Runner")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["real_llm", "real_database", "real_redis", "real_clickhouse", "e2e"],
        help="Test categories to run"
    )
    parser.add_argument(
        "--model",
        default="gemini-1.5-flash",
        choices=["gemini-1.5-flash", "gemini-2.5-pro", "gpt-3.5-turbo", "gpt-4", "claude-3-sonnet"],
        help="LLM model to use for tests"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel test workers"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per test in seconds"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    runner = EnhancedRealServiceTestRunner(verbose=args.verbose)
    exit_code = runner.run_tests(
        categories=args.categories,
        model=args.model,
        parallel=args.parallel,
        timeout=args.timeout
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()