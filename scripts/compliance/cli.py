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

from scripts.compliance.core import ComplianceResults


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
  python check_architecture_compliance.py --check-test-limits --test-suggestions
  python check_architecture_compliance.py --no-test-limits
        """
    
    @staticmethod
    def _add_parser_arguments(parser: argparse.ArgumentParser) -> None:
        """Add arguments to parser"""
        parser.add_argument('--path', default='.', help='Root path to check')
        parser.add_argument('--fail-on-violation', action='store_true', 
                           help='Exit with non-zero code on violations')
        parser.add_argument('--max-file-lines', type=int, default=500,
                           help='Maximum lines per file (default: 500 per CLAUDE.md)')
        parser.add_argument('--max-function-lines', type=int, default=25,
                           help='Maximum lines per function (default: 25 per CLAUDE.md)')
        parser.add_argument('--target-folders', nargs='+', 
                           help='Folders to check (default: app frontend auth_service)')
        parser.add_argument('--ignore-folders', nargs='+',
                           help='Folders to ignore (default: scripts test_framework)')
        CLIHandler._add_test_arguments(parser)
        CLIHandler._add_display_arguments(parser)
        CLIHandler._add_output_arguments(parser)
    
    @staticmethod
    def _add_test_arguments(parser: argparse.ArgumentParser) -> None:
        """Add test-specific arguments"""
        parser.add_argument('--check-test-limits', action='store_true', default=True,
                           help='Check test file limits (300 lines) and test function limits (8 lines)')
        parser.add_argument('--no-test-limits', action='store_true',
                           help='Skip test limits checking')
        parser.add_argument('--test-suggestions', action='store_true',
                           help='Generate automated splitting suggestions for test violations')
    
    @staticmethod
    def _add_display_arguments(parser: argparse.ArgumentParser) -> None:
        """Add display-related arguments"""
        parser.add_argument('--show-all', action='store_true',
                           help='Show all violations instead of top ones')
        parser.add_argument('--violation-limit', type=int, default=10,
                           help='Max violations to display per category (default: 10)')
        parser.add_argument('--no-smart-limits', action='store_true',
                           help='Disable smart limit detection')
        parser.add_argument('--no-emoji', action='store_true',
                           help='Disable emoji severity markers')
        parser.add_argument('--mro-audit', action='store_true',
                           help='Run MRO (Method Resolution Order) complexity audit')
    
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
    def process_output(args: Any, enforcer: Any, results: ComplianceResults) -> None:
        """Process and output results"""
        if args.json_only:
            OutputHandler._print_json_output(results)
        else:
            enforcer.reporter.generate_report(results)
        
        # Generate test splitting suggestions if requested
        if getattr(args, 'test_suggestions', False):
            OutputHandler._print_test_suggestions(enforcer)
        
        OutputHandler._save_json_output(args, results)
    
    @staticmethod
    def _print_json_output(results: ComplianceResults) -> None:
        """Print JSON output to stdout"""
        print(json.dumps(asdict(results), indent=2))
    
    @staticmethod
    def _print_test_suggestions(enforcer: Any) -> None:
        """Print test splitting suggestions"""
        suggestions = enforcer.generate_test_splitting_suggestions()
        if not suggestions:
            print("\n PASS:  No test splitting suggestions needed.")
            return
        
        print("\n" + "="*80)
        print("[U+1F527] TEST SPLITTING SUGGESTIONS")
        print("="*80)
        
        for identifier, suggestion_list in suggestions.items():
            print(f"\n[U+1F4C1] {identifier}")
            print("-" * 60)
            for suggestion in suggestion_list:
                print(f"  {suggestion}")
        
        print("\n" + "="*80)
    
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