#!/usr/bin/env python3
"""
Architecture Compliance Checker - Main Entry Point
Enforces CLAUDE.md architectural rules using modular design.

This script has been refactored into focused modules under scripts/compliance/
to comply with the 450-line file limit and 25-line function limit.
"""

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.compliance import ArchitectureEnforcer, CLIHandler, OutputHandler


def main() -> None:
    """Main entry point with enhanced CI/CD features"""
    parser = CLIHandler.create_argument_parser()
    args = parser.parse_args()
    enforcer = _create_enforcer(args)
    results = enforcer.run_all_checks()
    OutputHandler.process_output(args, enforcer, results)
    OutputHandler.handle_exit_code(args, results)


def _create_enforcer(args):
    """Create architecture enforcer from arguments"""
    show_all = getattr(args, 'show_all', False)
    violation_limit = 999999 if show_all else getattr(args, 'violation_limit', 10)
    smart_limits = not getattr(args, 'no_smart_limits', False)
    use_emoji = not getattr(args, 'no_emoji', False)
    target_folders = getattr(args, 'target_folders', None)
    ignore_folders = getattr(args, 'ignore_folders', None)
    check_test_limits = not getattr(args, 'no_test_limits', False)
    return ArchitectureEnforcer(
        root_path=args.path,
        max_file_lines=args.max_file_lines,
        max_function_lines=args.max_function_lines,
        violation_limit=violation_limit,
        smart_limits=smart_limits,
        use_emoji=use_emoji,
        target_folders=target_folders,
        ignore_folders=ignore_folders,
        check_test_limits=check_test_limits
    )


if __name__ == "__main__":
    main()