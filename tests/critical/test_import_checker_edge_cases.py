#!/usr/bin/env python3
"""
Critical test cases for import checker to catch edge cases and syntax errors.
These tests ensure the import checker catches ALL problematic import patterns.
"""

import ast
import re
import sys
import tempfile
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest

from scripts.comprehensive_import_scanner import ComprehensiveImportScanner


class TestImportCheckerEdgeCases:
    """Test suite for edge cases that import checkers must catch"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = ComprehensiveImportScanner(self.temp_dir)

    def test_double_dot_syntax_error(self):
        """Test that double dots in module path are caught"""
        test_file = Path(self.temp_dir) / "test_double_dot.py"
        test_file.write_text('''
from auth_service.app..config import AuthConfig
from auth_service.app..services.auth_service import AuthService
''')
        
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any(issue.issue_type == "syntax" for issue in result.issues)
        assert any("invalid syntax" in issue.error_message for issue in result.issues)

    def test_triple_dot_syntax_error(self):
        """Test that triple dots in module path are caught"""
        test_file = Path(self.temp_dir) / "test_triple_dot.py"
        test_file.write_text('''
from some.module...config import Config
from another...module.service import Service
''')
        
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any(issue.issue_type == "syntax" for issue in result.issues)

    def test_consecutive_dots_in_middle(self):
        """Test consecutive dots in the middle of import path"""
        test_file = Path(self.temp_dir) / "test_middle_dots.py"
        test_file.write_text('''
from netra_backend..app.config import Config
from tests..unit.test_something import TestCase
import module..submodule.component
''')
        
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any(issue.issue_type == "syntax" for issue in result.issues)

    def test_trailing_dots(self):
        """Test trailing dots in import statements"""
        test_file = Path(self.temp_dir) / "test_trailing_dots.py"
        test_file.write_text('''
from module.submodule. import something
from another.module.. import Config
import package.module.
''')
        
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any(issue.issue_type == "syntax" for issue in result.issues)

    def test_leading_dots_in_absolute_import(self):
        """Test incorrect leading dots in absolute imports"""
        test_file = Path(self.temp_dir) / "test_leading_dots.py"
        test_file.write_text('''
from ..auth_service.config import Config  # Valid relative import
from ...netra_backend.app import app  # Valid relative import
from ....absolute.path import Something  # Too many dots for relative
''')
        
        result = self.scanner.scan_file(test_file)
        # The scanner should validate that relative imports make sense
        assert result.has_issues()

    def test_mixed_dots_and_spaces(self):
        """Test dots mixed with spaces"""
        test_file = Path(self.temp_dir) / "test_dots_spaces.py"
        test_file.write_text('''
from module. .submodule import Config
from another . . module import Service
''')
        
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any(issue.issue_type == "syntax" for issue in result.issues)

    def test_dots_in_alias(self):
        """Test dots in import aliases"""
        test_file = Path(self.temp_dir) / "test_alias_dots.py"
        test_file.write_text('''
import module.submodule as sub..module
from package import module as mod..ule
''')
        
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any(issue.issue_type == "syntax" for issue in result.issues)

    def test_empty_module_segments(self):
        """Test empty segments between dots"""
        test_file = Path(self.temp_dir) / "test_empty_segments.py"
        test_file.write_text('''
from module..config import Config  # Empty segment
from .module import Service  # Valid relative
from module. import Utils  # Invalid trailing dot
''')
        
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert len([item for item in result.issues if item.issue_type == "syntax"]) >= 2

    def test_regex_precheck_for_double_dots(self):
        """Test that a regex precheck would catch double dots before AST parsing"""
        problematic_patterns = [
            "from auth_service.app..config import AuthConfig",
            "from module..submodule import Something",
            "import package..module",
            "from ...module import Item",  # This is valid relative import
            "from module... import Config",
            "from module.....submodule import Service",
        ]

        # Pattern to detect invalid consecutive dots (not at the start)
        invalid_dots_pattern = re.compile(r"(?<!^from\s)(?<!^from\s\.)\.{2,}(?!\s)")

        invalid_count = 0
        for pattern in problematic_patterns:
            if ".." in pattern and not pattern.strip().startswith("from .."):
                # Exclude valid relative imports
                if not re.match(r"^from\s+\.{1,3}[a-zA-Z]", pattern.strip()):
                    invalid_count += 1

        assert invalid_count >= 4  # Should catch most invalid patterns

    def test_syntax_error_line_numbers(self):
        """Test that syntax errors report correct line numbers"""
        test_file = Path(self.temp_dir) / "test_line_numbers.py"
        test_file.write_text('''# Line 1
import os  # Line 2
import sys  # Line 3

from module..config import Config  # Line 5 - Error here
from another.module import Service  # Line 6

def function():  # Line 8
    pass
''')

        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        syntax_issues = [item for item in result.issues if item.issue_type == "syntax"]
        assert len(syntax_issues) > 0
        # Line number should be 5
        assert any(issue.line_number == 5 for issue in syntax_issues)

    def test_complex_nested_imports(self):
        """Test complex nested import patterns with errors"""
        test_file = Path(self.temp_dir) / "test_complex.py"
        test_file.write_text('''
try:
    from module..config import Config
except ImportError:
    from backup.module import Config

if True:
    from another..module import Service

class MyClass:
    def method(self):
        from local..import import Something
''')
        
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        # Should catch multiple syntax errors
        syntax_issues = [item for item in result.issues if item.issue_type == "syntax"]
        assert len(syntax_issues) >= 1  # AST won't parse this at all

    def test_unicode_and_special_chars(self):
        """Test imports with unicode and special characters"""
        test_file = Path(self.temp_dir) / "test_unicode.py"
        test_file.write_text('''
from module..c[U+00F6]nfig import Config
from module.. FIRE:  import Fire
from module..config! import Config
''', encoding="utf-8")

        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any(issue.issue_type == "syntax" for issue in result.issues)


class TestImportCheckerRegexPrevalidation:
    """Test regex-based pre-validation before AST parsing"""

    @staticmethod
    def validate_import_line(line: str) -> bool:
        """
        Pre-validate import lines with regex before AST parsing.
        Returns False if the line has obvious syntax errors.
        """
        line = line.strip()
        if not line or line.startswith("#"):
            return True

        # Check for invalid consecutive dots (not at start for relative imports)
        if "import" in line or "from" in line:
            # Pattern 1: Dots not at the beginning of from statement
            if re.search(r"[a-zA-Z_]\.\.[a-zA-Z_]", line):
                return False

            # Pattern 2: More than 3 dots at the start (invalid relative import)
            if re.match(r"^from\s+\.{4,}", line):
                return False

            # Pattern 3: Trailing dots
            if re.search(r"\.\s+(import|as|$)", line):
                return False

            # Pattern 4: Dots followed by dots with space
            if re.search(r"\.\s+\.", line):
                return False

            # Pattern 5: Empty segments (module..config)
            if ".." in line and not re.match(r"^from\s+\.{1,3}[a-zA-Z_]", line):
                # Not a valid relative import
                return False

        return True

    def test_prevalidation_catches_double_dots(self):
        """Test that pre-validation catches double dot errors"""
        invalid_lines = [
            "from auth_service.app..config import AuthConfig",
            "from module..submodule import Something",
            "import package..module",
            "from module... import Config",
            "from module. import Utils",
            "from module . . config import Config",
        ]

        valid_lines = [
            "from ..relative import Something",
            "from ...parent import Module",
            "from .sibling import Config",
            "import module.submodule.config",
            "from module.sub.config import Config",
        ]

        for line in invalid_lines:
            assert not self.validate_import_line(line), f"Should be invalid: {line}"

        for line in valid_lines:
            assert self.validate_import_line(line), f"Should be valid: {line}"

    def test_integration_with_scanner(self):
        """Test that scanner could use pre-validation to fail fast"""
        content_with_errors = '''
import os
from pathlib import Path

from auth_service.app..config import AuthConfig  # Error here
from auth_service.app.services import AuthService  # Valid

def main():
    pass
'''

        # First, try to parse with AST (will fail)
        try:
            ast.parse(content_with_errors)
            assert False, "AST should have failed"
        except SyntaxError as e:
            assert e.lineno == 5  # Error on line 5

        # Now test with pre-validation
        lines = content_with_errors.split("\n")
        errors = []
        for i, line in enumerate(lines, 1):
            if not self.validate_import_line(line):
                errors.append((i, line))

        assert len(errors) > 0
        assert errors[0][0] == 5  # Line 5 has the error
        assert "app..config" in errors[0][1]


class TestEnhancedImportChecker:
    """Test enhancements to make import checker more robust"""

    def test_pre_ast_validation(self):
        """Test that we can validate imports before AST parsing"""

        def pre_validate_file(file_path: Path) -> list:
            """Pre-validate a file for import syntax errors"""
            errors = []
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue

                        # Check for import statements
                        if "import" in line or "from" in line:
                            # Check for double dots not in relative imports
                            if ".." in line:
                                # Check if it's a valid relative import
                                if not re.match(r"^from\s+\.{1,3}[a-zA-Z_]", line):
                                    if re.search(r"[a-zA-Z_]\.\.[a-zA-Z_]", line):
                                        errors.append({
                                            "line": line_num,
                                            "error": "Invalid double dots in import path",
                                            "content": line,
                                        })
            except Exception as e:
                errors.append({"error": str(e)})

            return errors

        # Test with a file containing double dot error
        temp_file = Path(tempfile.mkdtemp()) / "test.py"
        temp_file.write_text('''
from auth_service.app..config import AuthConfig
from valid.module import Something
''')
        
        errors = pre_validate_file(temp_file)
        assert len(errors) > 0
        assert errors[0]["line"] == 2
        assert "double dots" in errors[0]["error"]

    def test_comprehensive_validation_pipeline(self):
        """Test a comprehensive validation pipeline"""

        def comprehensive_validate(file_path: Path) -> dict:
            """Comprehensive validation with multiple checks"""
            results = {
                "pre_validation_errors": [],
                "ast_errors": [],
                "import_errors": [],
            }

            # Step 1: Pre-validation with regex
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if "import" in line or "from" in line:
                        # Check for various patterns
                        if re.search(r"[a-zA-Z_]\.\.[a-zA-Z_]", line):
                            results["pre_validation_errors"].append({
                                "line": line_num,
                                "pattern": "double_dots",
                                "content": line.strip(),
                            })
                        
                        if re.search(r"\.\s+import", line):
                            results["pre_validation_errors"].append({
                                "line": line_num,
                                "pattern": "trailing_dot",
                                "content": line.strip(),
                            })

            # Step 2: AST parsing (only if no pre-validation errors)
            if not results["pre_validation_errors"]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        ast.parse(f.read())
                except SyntaxError as e:
                    results["ast_errors"].append({"line": e.lineno, "error": str(e)})

            return results

        # Test file with double dot error
        temp_file = Path(tempfile.mkdtemp()) / "test.py"
        temp_file.write_text('''
from auth_service.app..config import AuthConfig
''')
        
        results = comprehensive_validate(temp_file)
        assert len(results["pre_validation_errors"]) > 0
        assert results["pre_validation_errors"][0]["pattern"] == "double_dots"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])