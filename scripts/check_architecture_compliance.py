#!/usr/bin/env python3
"""
Architecture Compliance Checker - Main Entry Point
Enforces CLAUDE.md architectural rules using modular design.

This script has been refactored into focused modules under scripts/compliance/
to comply with the 300-line file limit and 8-line function limit.
"""

from compliance import ArchitectureEnforcer, CLIHandler, OutputHandler


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
    return ArchitectureEnforcer(
        root_path=args.path,
        max_file_lines=args.max_file_lines,
        max_function_lines=args.max_function_lines
    )


if __name__ == "__main__":
    main()