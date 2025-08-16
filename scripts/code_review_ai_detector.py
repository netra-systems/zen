#!/usr/bin/env python3
"""
Code Review AI Coding Issue Detection
ULTRA DEEP THINK: Module-based architecture - AI issue detection extracted for 300-line compliance
"""

import subprocess
from pathlib import Path
from typing import Tuple

class CodeReviewAIDetector:
    """Handles AI coding issue detection for code review"""
    
    def __init__(self, project_root: Path, mode: str):
        self.project_root = project_root
        self.mode = mode
        self.ai_issues_found = []
        self.issues = {"high": [], "medium": [], "low": []}

    def run_command(self, cmd: str, cwd: str = None, timeout: int = 60) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd or self.project_root, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, str(e)

    def detect_ai_coding_issues(self):
        """Detect common issues from AI-assisted coding"""
        print("\n[AI] Detecting AI Coding Issues...")
        
        if self.mode == "ai-focus" or self.mode == "full":
            self._check_duplicates()
            self._check_type_consistency()
            self._check_error_handling()
            self._check_ai_patterns()

    def _check_duplicates(self):
        """Check for duplicate implementations"""
        patterns = [
            ("get_config", "app/"),
            ("validate_", "app/"),
            ("format_", "app/"),
            ("parse_", "app/"),
        ]
        
        for pattern, search_dir in patterns:
            success, output = self.run_command(
                f"grep -r --include='*.py' '^def {pattern}' {search_dir} | head -20"
            )
            if success and output:
                lines = output.strip().split('\n')
                if len(lines) > 3:
                    functions = {}
                    for line in lines:
                        if ':def ' in line:
                            parts = line.split(':def ')
                            if len(parts) == 2:
                                file = parts[0]
                                func = parts[1].split('(')[0]
                                if func not in functions:
                                    functions[func] = []
                                functions[func].append(file)
                    
                    for func, files in functions.items():
                        if len(files) > 1:
                            self.ai_issues_found.append(f"Duplicate function '{func}' in {len(files)} files")
                            self.issues["medium"].append(f"Duplicate implementation: {func}")

    def _check_type_consistency(self):
        """Check for type definition consistency"""
        success, output = self.run_command(
            "grep -r --include='*.ts' --include='*.tsx' ': any' frontend/types/ | head -10"
        )
        if success and output:
            any_count = len(output.strip().split('\n'))
            if any_count > 0:
                self.ai_issues_found.append(f"Found {any_count} uses of 'any' type in TypeScript")
                self.issues["medium"].append(f"TypeScript 'any' types found: {any_count} instances")
        
        success, output = self.run_command(
            "grep -r --include='*.py' '^def .*):$' app/ | head -20"
        )
        if success and output:
            lines = output.strip().split('\n')
            missing_types = 0
            for line in lines:
                if '-> ' not in line:
                    missing_types += 1
            
            if missing_types > 5:
                self.ai_issues_found.append(f"Found {missing_types} functions without return type hints")
                self.issues["medium"].append(f"Missing type hints: {missing_types} functions")

    def _check_error_handling(self):
        """Check for incomplete error handling"""
        success, output = self.run_command(
            "grep -r --include='*.py' 'except:' app/ | head -10"
        )
        if success and output:
            bare_except_count = len(output.strip().split('\n'))
            if bare_except_count > 0:
                self.ai_issues_found.append(f"Found {bare_except_count} bare except clauses")
                self.issues["high"].append(f"Bare except clauses (catches all errors): {bare_except_count}")
        
        success, output = self.run_command(
            "grep -r --include='*.ts' --include='*.tsx' '\\.then(' frontend/ | grep -v '\\.catch(' | head -10"
        )
        if success and output:
            unhandled = len(output.strip().split('\n'))
            if unhandled > 0:
                self.ai_issues_found.append(f"Potential unhandled promises: {unhandled}")
                self.issues["medium"].append(f"Promises without error handling: {unhandled}")

    def _check_ai_patterns(self):
        """Check for common AI coding patterns that may be problematic"""
        success, output = self.run_command(
            "grep -r --include='*.py' --include='*.ts' --include='*.tsx' 'TODO\\|FIXME' . | head -20"
        )
        if success and output:
            todo_count = len(output.strip().split('\n'))
            if todo_count > 10:
                self.ai_issues_found.append(f"Found {todo_count} TODO/FIXME comments")
                self.issues["low"].append(f"Unresolved TODO/FIXME comments: {todo_count}")
        
        success, output = self.run_command(
            "grep -r --include='*.ts' --include='*.tsx' 'console\\.log' frontend/ | head -10"
        )
        if success and output:
            console_count = len(output.strip().split('\n'))
            if console_count > 0:
                self.ai_issues_found.append(f"Found {console_count} console.log statements")
                self.issues["medium"].append(f"Debug console.log statements in production code: {console_count}")