#!/usr/bin/env python3
"""
Command line interface for architecture compliance checker.
Handles argument parsing and JSON output.
"""

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any

from .core import ComplianceResults


class CLIHandler:
    """Handles command line interface operations"""
    
    @staticmethod
    def create_argument_parser() -> argparse.ArgumentParser:
        """Create and configure argument parser"""
        parser = argparse.ArgumentParser(
            description='Check architecture compliance with enhanced CI/CD features',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=CLIHandler._get_usage_examples()
        )
        CLIHandler._add_parser_arguments(parser)
        return parser
    
    @staticmethod
    def _get_usage_examples() -> str:
        """Get usage examples for help text"""
        return """
Examples:
  python check_architecture_compliance.py --json-output report.json
  python check_architecture_compliance.py --max-file-lines 250 --threshold 90
  python check_architecture_compliance.py --fail-on-violation --json-only
        """
    
    @staticmethod
    def _add_parser_arguments(parser: argparse.ArgumentParser) -> None:
        """Add arguments to parser"""
        parser.add_argument('--path', default='.', help='Root path to check')
        parser.add_argument('--fail-on-violation', action='store_true', 
                           help='Exit with non-zero code on violations')
        parser.add_argument('--max-file-lines', type=int, default=300,
                           help='Maximum lines per file (default: 300)')
        parser.add_argument('--max-function-lines', type=int, default=8,
                           help='Maximum lines per function (default: 8)')
        CLIHandler._add_output_arguments(parser)
    
    @staticmethod
    def _add_output_arguments(parser: argparse.ArgumentParser) -> None:
        """Add output-related arguments"""
        parser.add_argument('--json-output', help='Output JSON report to file')
        parser.add_argument('--json-only', action='store_true',
                           help='Output only JSON, no human-readable report')
        parser.add_argument('--threshold', type=float, default=0.0,
                           help='Minimum compliance score (0-100) to pass')


class OutputHandler:
    """Handles output processing and formatting"""
    
    @staticmethod
    def process_output(args: Any, reporter: Any, results: ComplianceResults) -> None:
        """Process and output results"""
        if args.json_only:
            OutputHandler._print_json_output(results)
        else:
            reporter.generate_report()
        OutputHandler._save_json_output(args, results)
    
    @staticmethod
    def _print_json_output(results: ComplianceResults) -> None:
        """Print JSON output to stdout"""
        print(json.dumps(asdict(results), indent=2))
    
    @staticmethod
    def _save_json_output(args: Any, results: ComplianceResults) -> None:
        """Save JSON output if requested"""
        if args.json_output:
            with open(args.json_output, 'w') as f:
                json.dump(asdict(results), f, indent=2)
            print(f"\nJSON report saved to: {args.json_output}")
    
    @staticmethod
    def handle_exit_code(args: Any, results: ComplianceResults) -> None:
        """Handle exit code based on results"""
        should_fail = OutputHandler._should_exit_with_failure(args, results)
        sys.exit(1 if should_fail else 0)
    
    @staticmethod
    def _should_exit_with_failure(args: Any, results: ComplianceResults) -> bool:
        """Determine if should exit with failure code"""
        return (args.fail_on_violation and 
                (results.total_violations > 0 or 
                 results.compliance_score < args.threshold))