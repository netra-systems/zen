#!/usr/bin/env python3
"""
Comprehensive Code Review Script - Main Entry Point
Implements SPEC/review.xml for automated code quality validation.

This script has been refactored into focused modules under scripts/review/
to comply with the 300-line file limit and 8-line function limit.
"""

from review import CodeReviewer, CLIHandler


def main() -> None:
    """Main entry point for code review system"""
    parser = CLIHandler.create_argument_parser()
    args = parser.parse_args()
    config = CLIHandler.create_config_from_args(args)
    reviewer = CodeReviewer(config)
    success = reviewer.run()
    CLIHandler.handle_exit_code(success)


if __name__ == "__main__":
    main()