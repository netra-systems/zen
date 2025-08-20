#!/usr/bin/env python3
"""
Function Complexity CLI Handler
Contains all CLI argument parsing and main entry point logic.
"""

import argparse
import sys
from pathlib import Path

from function_complexity_linter import FunctionComplexityLinter
from function_complexity_templates import create_pre_commit_hook, handle_fix_suggestions

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Function Complexity Linter - Enforce 25-line function limit"
    )
    _add_basic_arguments(parser)
    _add_action_arguments(parser)
    return parser

def _add_basic_arguments(parser: argparse.ArgumentParser) -> None:
    """Add basic configuration arguments"""
    parser.add_argument("--max-lines", type=int, default=8,
                       help="Maximum lines per function (default: 8)")
    parser.add_argument("--path", default=".",
                       help="Root path to lint (default: current directory)")
    parser.add_argument("--json", action="store_true",
                       help="Output results in JSON format")

def _add_action_arguments(parser: argparse.ArgumentParser) -> None:
    """Add action-related arguments"""
    parser.add_argument("--check", action="store_true",
                       help="Check for violations and exit with error code if found")
    parser.add_argument("--fail-on-violation", action="store_true",
                       help="Exit with non-zero code if violations found")
    parser.add_argument("--fix-suggestions", action="store_true",
                       help="Provide suggestions for fixing violations")
    parser.add_argument("--install-hook", action="store_true",
                       help="Install pre-commit hook")

def handle_hook_installation() -> None:
    """Install pre-commit hook and exit"""
    hook_path = Path(".git/hooks/pre-commit")
    hook_path.parent.mkdir(exist_ok=True)
    hook_path.write_text(create_pre_commit_hook())
    hook_path.chmod(0o755)
    print("Pre-commit hook installed")

def create_linter_from_args(args: argparse.Namespace) -> FunctionComplexityLinter:
    """Create linter instance from CLI arguments"""
    return FunctionComplexityLinter(
        max_lines=args.max_lines,
        root_path=args.path
    )

def handle_exit_conditions(args: argparse.Namespace, has_violations: bool) -> None:
    """Handle exit conditions based on arguments and violations"""
    if args.fail_on_violation and has_violations:
        sys.exit(1)
    if args.check:
        sys.exit(1 if has_violations else 0)

def main() -> None:
    """Main CLI entry point with 25-line limit compliance"""
    parser = create_argument_parser()
    args = parser.parse_args()
    if args.install_hook:
        handle_hook_installation()
        return
    _execute_linting_workflow(args)

def _execute_linting_workflow(args: argparse.Namespace) -> None:
    """Execute the main linting workflow"""
    linter = create_linter_from_args(args)
    linter.lint_directory()
    linter.handle_output_generation(args.json)
    handle_fix_suggestions(args.fix_suggestions, bool(linter.violations))
    handle_exit_conditions(args, bool(linter.violations))

if __name__ == "__main__":
    main()