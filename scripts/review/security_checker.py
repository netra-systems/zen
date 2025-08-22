#!/usr/bin/env python3
"""
Security issue checker for code review system.
Detects potential security vulnerabilities and misconfigurations.
"""

from typing import List, Tuple

from scripts.review.command_runner import CommandRunner
from scripts.review.core import ReviewConfig, ReviewData


class SecurityChecker:
    """Checks for security vulnerabilities"""
    
    def __init__(self, config: ReviewConfig, command_runner: CommandRunner):
        self.config = config
        self.runner = command_runner
    
    def check_security_issues(self, review_data: ReviewData) -> None:
        """Check for security vulnerabilities"""
        print("\n[SECURITY] Checking Security Issues...")
        self._check_hardcoded_secrets(review_data)
        self._check_sql_injection_risks(review_data)
    
    def _check_hardcoded_secrets(self, review_data: ReviewData) -> None:
        """Check for hardcoded secrets"""
        patterns = self._get_secret_patterns()
        for name, pattern in patterns:
            if self._find_hardcoded_credentials(pattern, name, review_data):
                break  # Stop after first finding to avoid spam
    
    def _get_secret_patterns(self) -> List[Tuple[str, str]]:
        """Get patterns for detecting hardcoded secrets"""
        return [
            ("API_KEY", "=\\s*[\"'][A-Za-z0-9]{20,}[\"']"),
            ("SECRET", "=\\s*[\"'][A-Za-z0-9]{20,}[\"']"),
            ("PASSWORD", "=\\s*[\"'][^\"']+[\"']"),
        ]
    
    def _find_hardcoded_credentials(self, pattern: str, name: str, review_data: ReviewData) -> bool:
        """Find hardcoded credentials matching pattern"""
        success, output = self.runner.run(
            f"grep -r --include='*.py' --include='*.ts' '{pattern}' . | grep -v test | head -5"
        )
        if success and output:
            lines = output.strip().split('\n')
            for line in lines:
                if self._is_real_credential(line):
                    review_data.add_security_issue(f"Potential hardcoded {name}")
                    review_data.issue_tracker.add_issue("critical", f"Possible hardcoded credential: {name}")
                    return True
        return False
    
    def _is_real_credential(self, line: str) -> bool:
        """Check if line contains real credential (not test/mock)"""
        line_lower = line.lower()
        return 'test' not in line_lower and 'mock' not in line_lower
    
    def _check_sql_injection_risks(self, review_data: ReviewData) -> None:
        """Check for SQL injection vulnerabilities"""
        success, output = self.runner.run(
            "grep -r --include='*.py' 'f\".*SELECT\\|f\".*INSERT\\|f\".*UPDATE\\|f\".*DELETE' app/ | head -5"
        )
        if success and output:
            review_data.add_security_issue("Potential SQL injection vulnerability")
            review_data.issue_tracker.add_issue("critical", "Possible SQL injection - using f-strings in queries")