#!/usr/bin/env python3
"""
AI coding issue detector for code review system.
Detects common issues from AI-assisted coding patterns.
"""

from typing import Dict, List, Tuple

from scripts.review.command_runner import CommandRunner
from scripts.review.core import ReviewConfig, ReviewData


class AIDetector:
    """Detects common issues from AI-assisted coding"""
    
    def __init__(self, config: ReviewConfig, command_runner: CommandRunner):
        self.config = config
        self.runner = command_runner
    
    def detect_ai_coding_issues(self, review_data: ReviewData) -> None:
        """Detect common issues from AI-assisted coding"""
        print("\n[AI] Detecting AI Coding Issues...")
        if self.config.is_ai_focused():
            self._check_all_ai_issues(review_data)
    
    def _check_all_ai_issues(self, review_data: ReviewData) -> None:
        """Run all AI issue detection checks"""
        self._check_duplicates(review_data)
        self._check_type_consistency(review_data)
        self._check_error_handling(review_data)
        self._check_ai_patterns(review_data)
    
    def _check_duplicates(self, review_data: ReviewData) -> None:
        """Check for duplicate implementations"""
        patterns = self._get_duplicate_patterns()
        for pattern, search_dir in patterns:
            self._check_pattern_duplicates(pattern, search_dir, review_data)
    
    def _get_duplicate_patterns(self) -> List[Tuple[str, str]]:
        """Get patterns to check for duplicates"""
        return [
            ("get_config", "app/"),
            ("validate_", "app/"),
            ("format_", "app/"),
            ("parse_", "app/"),
        ]
    
    def _check_pattern_duplicates(self, pattern: str, search_dir: str, review_data: ReviewData) -> None:
        """Check for duplicate implementations of a pattern"""
        success, output = self.runner.grep_search(f"^def {pattern}", search_dir, "*.py", 20)
        if success and output:
            functions = self._parse_function_duplicates(output)
            self._report_duplicates(functions, review_data)
    
    def _parse_function_duplicates(self, output: str) -> Dict[str, List[str]]:
        """Parse function duplicates from grep output"""
        functions = {}
        lines = output.strip().split('\n')
        for line in lines:
            if ':def ' in line:
                parts = line.split(':def ')
                if len(parts) == 2:
                    file = parts[0]
                    func = parts[1].split('(')[0]
                    if func not in functions:
                        functions[func] = []
                    functions[func].append(file)
        return functions
    
    def _report_duplicates(self, functions: Dict[str, List[str]], review_data: ReviewData) -> None:
        """Report duplicate function implementations"""
        for func, files in functions.items():
            if len(files) > 1:
                review_data.add_ai_issue(f"Duplicate function '{func}' in {len(files)} files")
                review_data.issue_tracker.add_issue("medium", f"Duplicate implementation: {func}")
    
    def _check_type_consistency(self, review_data: ReviewData) -> None:
        """Check for type definition consistency"""
        self._check_typescript_any_types(review_data)
        self._check_missing_python_types(review_data)
    
    def _check_typescript_any_types(self, review_data: ReviewData) -> None:
        """Check for 'any' types in TypeScript"""
        success, output = self.runner.grep_search(": any", "frontend/types/", "*.ts,*.tsx", 10)
        if success and output:
            any_count = len(output.strip().split('\n'))
            if any_count > 0:
                review_data.add_ai_issue(f"Found {any_count} uses of 'any' type in TypeScript")
                review_data.issue_tracker.add_issue("medium", f"TypeScript 'any' types found: {any_count} instances")
    
    def _check_missing_python_types(self, review_data: ReviewData) -> None:
        """Check for missing type hints in Python"""
        success, output = self.runner.grep_search("^def .*):$", "app/", "*.py", 20)
        if success and output:
            lines = output.strip().split('\n')
            missing_types = sum(1 for line in lines if '-> ' not in line)
            if missing_types > 5:
                review_data.add_ai_issue(f"Found {missing_types} functions without return type hints")
                review_data.issue_tracker.add_issue("medium", f"Missing type hints: {missing_types} functions")
    
    def _check_error_handling(self, review_data: ReviewData) -> None:
        """Check for incomplete error handling"""
        self._check_bare_except_clauses(review_data)
        self._check_unhandled_promises(review_data)
    
    def _check_bare_except_clauses(self, review_data: ReviewData) -> None:
        """Check for bare except clauses"""
        success, output = self.runner.grep_search("except:", "app/", "*.py", 10)
        if success and output:
            bare_except_count = len(output.strip().split('\n'))
            if bare_except_count > 0:
                review_data.add_ai_issue(f"Found {bare_except_count} bare except clauses")
                review_data.issue_tracker.add_issue("high", f"Bare except clauses (catches all errors): {bare_except_count}")
    
    def _check_unhandled_promises(self, review_data: ReviewData) -> None:
        """Check for unhandled promises in TypeScript"""
        success, output = self.runner.run("grep -r --include='*.ts' --include='*.tsx' '\\.then(' frontend/ | grep -v '\\.catch(' | head -10")
        if success and output:
            unhandled = len(output.strip().split('\n'))
            if unhandled > 0:
                review_data.add_ai_issue(f"Potential unhandled promises: {unhandled}")
                review_data.issue_tracker.add_issue("medium", f"Promises without error handling: {unhandled}")
    
    def _check_ai_patterns(self, review_data: ReviewData) -> None:
        """Check for common AI coding patterns that may be problematic"""
        self._check_todo_comments(review_data)
        self._check_console_logs(review_data)
    
    def _check_todo_comments(self, review_data: ReviewData) -> None:
        """Check for TODO/FIXME comments"""
        success, output = self.runner.run("grep -r --include='*.py' --include='*.ts' --include='*.tsx' 'TODO\\|FIXME' . | head -20")
        if success and output:
            todo_count = len(output.strip().split('\n'))
            if todo_count > 10:
                review_data.add_ai_issue(f"Found {todo_count} TODO/FIXME comments")
                review_data.issue_tracker.add_issue("low", f"Unresolved TODO/FIXME comments: {todo_count}")
    
    def _check_console_logs(self, review_data: ReviewData) -> None:
        """Check for console.log statements"""
        success, output = self.runner.grep_search("console\\.log", "frontend/", "*.ts,*.tsx", 10)
        if success and output:
            console_count = len(output.strip().split('\n'))
            if console_count > 0:
                review_data.add_ai_issue(f"Found {console_count} console.log statements")
                review_data.issue_tracker.add_issue("medium", f"Debug console.log statements in production code: {console_count}")