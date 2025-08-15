#!/usr/bin/env python3
"""
Function Complexity Template Generators
Contains templates for pre-commit hooks and CI integration.
"""

from typing import List

def create_pre_commit_hook() -> str:
    """Create pre-commit hook script content"""
    header = _get_hook_header()
    check_logic = _get_hook_check_logic()
    success_message = _get_hook_success_message()
    return header + check_logic + success_message

def _get_hook_header() -> str:
    """Get pre-commit hook header"""
    return '''#!/bin/bash
# Function Complexity Pre-commit Hook
# Enforces 8-line function limit

echo "Checking function complexity..."

'''

def _get_hook_check_logic() -> str:
    """Get pre-commit hook check logic"""
    check_cmd = 'python scripts/function_complexity_linter.py --check\n\n'
    error_block = _get_hook_error_block()
    return check_cmd + error_block

def _get_hook_error_block() -> str:
    """Get pre-commit hook error handling block"""
    return '''if [ $? -ne 0 ]; then
    echo "Function complexity violations found!"
    echo "Please refactor functions to be ≤ 8 lines each."
    echo "Run: python scripts/function_complexity_linter.py --fix-suggestions"
    exit 1
fi

'''

def _get_hook_success_message() -> str:
    """Get pre-commit hook success message"""
    return '''echo "Function complexity check passed"
exit 0
'''

def create_ci_integration() -> str:
    """Create CI integration script"""
    header = _get_ci_header()
    jobs = _get_ci_jobs()
    return header + jobs

def _get_ci_header() -> str:
    """Get CI integration header"""
    return '''# GitHub Actions Integration
name: Function Complexity Check

on: [push, pull_request]

'''

def _get_ci_jobs() -> str:
    """Get CI integration jobs configuration"""
    job_header = 'jobs:\n  function-complexity:\n    runs-on: warp-custom-default\n'
    steps = _get_ci_steps()
    return job_header + steps

def _get_ci_steps() -> str:
    """Get CI steps configuration"""
    steps_header = '    steps:\n      - uses: actions/checkout@v2\n'
    python_setup = _get_python_setup_step()
    check_step = _get_complexity_check_step()
    return steps_header + python_setup + check_step

def _get_python_setup_step() -> str:
    """Get Python setup step for CI"""
    return '''      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
'''

def _get_complexity_check_step() -> str:
    """Get complexity check step for CI"""
    return '''      - name: Check Function Complexity
        run: |
          python scripts/function_complexity_linter.py --check --fail-on-violation
'''

def _get_fix_suggestions() -> List[str]:
    """Get list of fix suggestions for function complexity violations"""
    return [
        "1. Break large functions into smaller helper functions",
        "2. Extract complex logic into separate methods",
        "3. Use early returns to reduce nesting",
        "4. Consider using design patterns like Strategy or Command",
        "5. Move validation logic to separate validator functions"
    ]

def _print_fix_suggestions() -> None:
    """Print specific fix suggestions for violations"""
    suggestions = _get_fix_suggestions()
    for suggestion in suggestions:
        print(suggestion)

def handle_fix_suggestions(show_suggestions: bool, has_violations: bool) -> None:
    """Display fix suggestions if requested and violations exist"""
    if not (show_suggestions and has_violations):
        return
    print(f"\nFix Suggestions:")
    _print_fix_suggestions()