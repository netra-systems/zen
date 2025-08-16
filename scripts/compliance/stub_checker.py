#!/usr/bin/env python3
"""
Test stub compliance checker.
Enforces CLAUDE.md no test stubs in production rule.
"""

import glob
import re
from pathlib import Path
from typing import List, Tuple

from .core import Violation, ComplianceConfig, ViolationBuilder


class StubChecker:
    """Checks for test stubs in production code"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
    
    def check_test_stubs(self) -> List[Violation]:
        """Check for test stubs in production code"""
        suspicious_patterns = self._get_test_stub_patterns()
        violations = []
        filepaths = self._get_app_files()
        for filepath in filepaths:
            if self._should_skip_test_file(filepath):
                continue
            violations.extend(self._check_file_for_stubs(filepath, suspicious_patterns))
        return violations
    
    def _get_app_files(self) -> List[str]:
        """Get all app Python files"""
        pattern = 'app/**/*.py'
        return glob.glob(str(self.config.root_path / pattern), recursive=True)
    
    def _get_test_stub_patterns(self) -> List[Tuple[str, str]]:
        """Get patterns for detecting actual test stubs (more precise)"""
        return [
            (r'""".*placeholder for test compatibility.*"""', 'Test compatibility placeholder'),
            (r'# Mock implementation.*\n\s*pass\s*$', 'Mock implementation with pass'),
            (r'# Test stub.*\n\s*pass\s*$', 'Test stub with pass'),
            (r'def.*\*args.*\*\*kwargs.*:\s*\n\s*""".*test.*"""\s*\n\s*return\s*\{', 'Args kwargs test stub'),
            (r'return \[{"id": "1"', 'Hardcoded test data'),
            (r'return {"test": "data"}', 'Test data return'),
            (r'raise NotImplementedError\(".*stub.*"\)', 'NotImplementedError stub'),
            (r'# Real.*would be.*\n\s*pass\s*$', 'Placeholder with TODO comment')
        ]
    
    def _should_skip_test_file(self, filepath: str) -> bool:
        """Check if file should be skipped for test stub detection"""
        skip_patterns = ['__pycache__', 'app/tests', '/tests/']
        return any(pattern in filepath for pattern in skip_patterns)
    
    def _check_file_for_stubs(self, filepath: str, patterns: List[Tuple[str, str]]) -> List[Violation]:
        """Check single file for test stubs"""
        try:
            content = self._read_file(filepath)
            rel_path = str(Path(filepath).relative_to(self.config.root_path))
            return self._find_test_stubs_in_content(content, rel_path, patterns)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return []
    
    def _read_file(self, filepath: str) -> str:
        """Read file content"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _find_test_stubs_in_content(self, content: str, rel_path: str, patterns: List) -> List[Violation]:
        """Find test stubs in file content"""
        for pattern, description in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
            if matches:
                line_number = content[:matches[0].start()].count('\n') + 1
                violation = ViolationBuilder.test_stub_violation(rel_path, line_number, description)
                return [violation]  # Only report first match per file
        return []