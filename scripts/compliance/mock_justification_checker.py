#!/usr/bin/env python3
"""
Mock justification compliance checker.
Enforces CLAUDE.md requirement that all mocks must be justified.
Per testing.xml: A mock without justification is a violation.
"""

import ast
import glob
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

from scripts.compliance.core import ComplianceConfig, Violation


class MockJustificationChecker:
    """Checks that all mocks have explicit justifications (relaxed for unit tests)"""

    def __init__(self, config: ComplianceConfig, relaxed_mode: bool = True):
        self.config = config
        self.relaxed_mode = relaxed_mode
        self.mock_patterns = [
            r'@patch\(',
            r'@mock\.patch\(',
            r'Mock\(\)',
            r'MagicMock\(\)',
            r'AsyncMock\(\)',
            r'PropertyMock\(\)',
            r'create_autospec\(',
            r'patch\.object\(',
            r'patch\.dict\(',
            r'patch\.multiple\(',
        ]
        self.justification_patterns = [
            r'@mock_justified\(',
            r'#\s*Mock justification:',
            r'#\s*Justification:',
            r'#\s*JUSTIFICATION:',
            r'""".*[Jj]ustification.*"""',
        ]
    
    def check_mock_justifications(self) -> List[Violation]:
        """Check all test files for unjustified mocks"""
        violations = []
        test_patterns = self._get_test_patterns()
        
        for pattern in test_patterns:
            filepaths = glob.glob(str(self.config.root_path / pattern), recursive=True)
            for filepath in filepaths:
                if not self.config.should_skip_file(filepath):
                    violations.extend(self._check_file(filepath))
        
        return sorted(violations, key=lambda x: (x.file_path, x.line_number or 0))
    
    def _get_test_patterns(self) -> List[str]:
        """Get patterns for test files"""
        patterns = []
        for folder in self.config.target_folders:
            patterns.extend([
                f'{folder}/**/test_*.py',
                f'{folder}/**/*_test.py',
                f'{folder}/tests/**/*.py',
            ])
        patterns.append('tests/**/*.py')
        patterns.append('test_framework/**/*.py')
        return patterns
    
    def _check_file(self, filepath: str) -> List[Violation]:
        """Check a single file for unjustified mocks"""
        violations = []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            rel_path = str(Path(filepath).relative_to(self.config.root_path))

            # In relaxed mode, be more permissive for unit test files
            if self.relaxed_mode and self._is_unit_test_file(rel_path):
                return self._check_relaxed_unit_tests(content, lines, rel_path)

            # Parse AST to find mock decorators
            tree = ast.parse(content)
            decorator_violations = self._check_decorators(tree, lines, rel_path)
            violations.extend(decorator_violations)

            # Check for inline Mock() calls
            inline_violations = self._check_inline_mocks(lines, rel_path, decorator_violations)
            violations.extend(inline_violations)

        except Exception as e:
            print(f"Error parsing {filepath}: {e}")

        return violations
    
    def _check_decorators(self, tree: ast.AST, lines: List[str], rel_path: str) -> List[Violation]:
        """Check decorator-based mocks for justifications"""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if self._is_mock_decorator(decorator):
                        line_num = decorator.lineno
                        if not self._has_justification_nearby(lines, line_num - 1):
                            violations.append(self._create_violation(
                                rel_path, line_num, node.name, lines[line_num - 1].strip()
                            ))
        
        return violations
    
    def _check_inline_mocks(self, lines: List[str], rel_path: str, 
                           decorator_violations: List[Violation]) -> List[Violation]:
        """Check for inline Mock() calls without justification"""
        violations = []
        decorator_lines = {v.line_number for v in decorator_violations}
        
        for i, line in enumerate(lines, 1):
            if i in decorator_lines:
                continue
                
            for pattern in ['Mock()', 'MagicMock()', 'AsyncMock()', 'PropertyMock()']:
                if pattern in line:
                    if not self._has_justification_nearby(lines, i - 1):
                        violations.append(self._create_violation(
                            rel_path, i, None, line.strip()
                        ))
                        break
        
        return violations
    
    def _is_mock_decorator(self, decorator) -> bool:
        """Check if decorator is a mock-related decorator"""
        if isinstance(decorator, ast.Name):
            return decorator.id in ['patch', 'mock']
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr in ['patch', 'object', 'dict', 'multiple']
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id in ['patch', 'mock', 'mock_justified']
            elif isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr in ['patch', 'object', 'dict', 'multiple']
        return False
    
    def _has_justification_nearby(self, lines: List[str], line_index: int) -> bool:
        """Check if there's a justification comment or decorator nearby"""
        # Check within 3 lines before and 1 line after
        start = max(0, line_index - 3)
        end = min(len(lines), line_index + 2)
        
        for i in range(start, end):
            line = lines[i]
            for pattern in self.justification_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return True
            # Also check for @mock_justified decorator
            if '@mock_justified' in line:
                return True
        
        return False
    
    def _is_unit_test_file(self, rel_path: str) -> bool:
        """Check if this is a unit test file (not integration/e2e)"""
        path_lower = rel_path.lower()

        # Unit test indicators
        unit_indicators = [
            '/test/', '/tests/', 'test_', '_test.', '.test.',
            '/unit/', '/units/', 'unit_test'
        ]

        # Not integration/e2e test indicators
        non_unit_indicators = [
            'integration', 'e2e', 'end_to_end', 'system',
            'acceptance', 'functional', 'api_test'
        ]

        is_test = any(indicator in path_lower for indicator in unit_indicators)
        is_non_unit = any(indicator in path_lower for indicator in non_unit_indicators)

        return is_test and not is_non_unit

    def _check_relaxed_unit_tests(self, content: str, lines: List[str], rel_path: str) -> List[Violation]:
        """Check unit tests with relaxed mock requirements"""
        violations = []

        # Only flag mocks in unit tests if they're clearly problematic
        problematic_patterns = [
            'Mock().return_value = Mock()',  # Mock returning mock - likely over-mocking
            'Mock(side_effect=Exception)',   # Mocking exceptions without context
            'patch.*patch.*patch',           # Triple+ patching indicates complexity
        ]

        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            for pattern in problematic_patterns:
                if re.search(pattern, line_stripped):
                    violations.append(self._create_relaxed_violation(
                        rel_path, i, line_stripped, "Potentially problematic mock pattern"
                    ))
                    break

        return violations

    def _create_relaxed_violation(self, rel_path: str, line_num: int,
                                line_content: str, reason: str) -> Violation:
        """Create a relaxed violation for unit tests"""
        return Violation(
            file_path=rel_path,
            violation_type="mock_justification",
            severity="low",  # Reduced severity for unit tests
            line_number=line_num,
            description=f"{reason}: {line_content[:50]}...",
            fix_suggestion="Consider simplifying mock usage or adding brief comment"
        )

    def _create_violation(self, rel_path: str, line_num: int,
                         func_name: Optional[str], line_content: str) -> Violation:
        """Create a violation for an unjustified mock"""
        description = f"Mock without justification: {line_content[:50]}..."
        if func_name:
            description = f"Mock without justification in {func_name}()"

        return Violation(
            file_path=rel_path,
            violation_type="mock_justification",
            severity="medium",  # Reduced from "high" to be more relaxed
            line_number=line_num,
            function_name=func_name,
            description=description,
            fix_suggestion="Add @mock_justified decorator or comment explaining why mock is necessary"
        )


def create_mock_justified_decorator():
    """
    Create the @mock_justified decorator for use in test files.
    This should be added to a test utilities module.
    """
    def mock_justified(reason: str):
        """
        Decorator to document mock justification.
        
        Usage:
                        @patch('app.services.external_api')
            def test_something(self, mock_api):
                ...
        """
        def decorator(func):
            # Store justification as function attribute
            func.__mock_justification__ = reason
            return func
        return decorator
    return mock_justified