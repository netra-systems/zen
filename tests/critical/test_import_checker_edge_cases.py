#!/usr/bin/env python3
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Critical test cases for import checker to catch edge cases and syntax errors.
# REMOVED_SYNTAX_ERROR: These tests ensure the import checker catches ALL problematic import patterns.
# REMOVED_SYNTAX_ERROR: '''

import ast
import re
import sys
import tempfile
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest

from scripts.comprehensive_import_scanner import ComprehensiveImportScanner

# Add project root to path


# REMOVED_SYNTAX_ERROR: class TestImportCheckerEdgeCases:
    # REMOVED_SYNTAX_ERROR: """Test suite for edge cases that import checkers must catch"""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def setup_method(self):
    # REMOVED_SYNTAX_ERROR: """Setup test environment"""
    # REMOVED_SYNTAX_ERROR: self.temp_dir = tempfile.mkdtemp()
    # REMOVED_SYNTAX_ERROR: self.scanner = ComprehensiveImportScanner(self.temp_dir)

# REMOVED_SYNTAX_ERROR: def test_double_dot_syntax_error(self):
    # REMOVED_SYNTAX_ERROR: """Test that double dots in module path are caught"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_double_dot.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: from auth_service.app..config import AuthConfig
    # REMOVED_SYNTAX_ERROR: from auth_service.app..services.auth_service import AuthService
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # REMOVED_SYNTAX_ERROR: assert any(issue.issue_type == "syntax" for issue in result.issues)
    # REMOVED_SYNTAX_ERROR: assert any("invalid syntax" in issue.error_message for issue in result.issues)

# REMOVED_SYNTAX_ERROR: def test_triple_dot_syntax_error(self):
    # REMOVED_SYNTAX_ERROR: """Test that triple dots in module path are caught"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_triple_dot.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from some.module...config import Config
    # REMOVED_SYNTAX_ERROR: from another...module.service import Service
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # REMOVED_SYNTAX_ERROR: assert any(issue.issue_type == "syntax" for issue in result.issues)

# REMOVED_SYNTAX_ERROR: def test_consecutive_dots_in_middle(self):
    # REMOVED_SYNTAX_ERROR: """Test consecutive dots in the middle of import path"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_middle_dots.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from netra_backend..app.config import Config
    # REMOVED_SYNTAX_ERROR: from tests..unit.test_something import TestCase
    # REMOVED_SYNTAX_ERROR: import module..submodule.component
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # REMOVED_SYNTAX_ERROR: assert any(issue.issue_type == "syntax" for issue in result.issues)

# REMOVED_SYNTAX_ERROR: def test_trailing_dots(self):
    # REMOVED_SYNTAX_ERROR: """Test trailing dots in import statements"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_trailing_dots.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from module.submodule. import something
    # REMOVED_SYNTAX_ERROR: from another.module.. import Config
    # REMOVED_SYNTAX_ERROR: import package.module.
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # REMOVED_SYNTAX_ERROR: assert any(issue.issue_type == "syntax" for issue in result.issues)

# REMOVED_SYNTAX_ERROR: def test_leading_dots_in_absolute_import(self):
    # REMOVED_SYNTAX_ERROR: """Test incorrect leading dots in absolute imports"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_leading_dots.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from ..auth_service.config import Config  # Valid relative import
    # REMOVED_SYNTAX_ERROR: from ...netra_backend.app import app  # Valid relative import
    # REMOVED_SYNTAX_ERROR: from ....absolute.path import Something  # Too many dots for relative
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # The scanner should validate that relative imports make sense
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()

# REMOVED_SYNTAX_ERROR: def test_mixed_dots_and_spaces(self):
    # REMOVED_SYNTAX_ERROR: """Test dots mixed with spaces"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_dots_spaces.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from module. .submodule import Config
    # REMOVED_SYNTAX_ERROR: from another . . module import Service
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # REMOVED_SYNTAX_ERROR: assert any(issue.issue_type == "syntax" for issue in result.issues)

# REMOVED_SYNTAX_ERROR: def test_dots_in_alias(self):
    # REMOVED_SYNTAX_ERROR: """Test dots in import aliases"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_alias_dots.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: import module.submodule as sub..module
    # REMOVED_SYNTAX_ERROR: from package import module as mod..ule
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # REMOVED_SYNTAX_ERROR: assert any(issue.issue_type == "syntax" for issue in result.issues)

# REMOVED_SYNTAX_ERROR: def test_empty_module_segments(self):
    # REMOVED_SYNTAX_ERROR: """Test empty segments between dots"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_empty_segments.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from module..config import Config  # Empty segment
    # REMOVED_SYNTAX_ERROR: from .module import Service  # Valid relative
    # REMOVED_SYNTAX_ERROR: from module. import Utils  # Invalid trailing dot
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # REMOVED_SYNTAX_ERROR: assert len([item for item in []]) >= 2

# REMOVED_SYNTAX_ERROR: def test_regex_precheck_for_double_dots(self):
    # REMOVED_SYNTAX_ERROR: """Test that a regex precheck would catch double dots before AST parsing"""
    # REMOVED_SYNTAX_ERROR: problematic_patterns = [ )
    # REMOVED_SYNTAX_ERROR: "from auth_service.app..config import AuthConfig",
    # REMOVED_SYNTAX_ERROR: "from module..submodule import Something",
    # REMOVED_SYNTAX_ERROR: "import package..module",
    # REMOVED_SYNTAX_ERROR: "from ...module import Item",  # This is valid relative import
    # REMOVED_SYNTAX_ERROR: "from module... import Config",
    # REMOVED_SYNTAX_ERROR: "from module.....submodule import Service",
    

    # REMOVED_SYNTAX_ERROR: import re

    # Pattern to detect invalid consecutive dots (not at the start)
    # REMOVED_SYNTAX_ERROR: invalid_dots_pattern = re.compile(r"(?<!^from\s)(?<!^from\s\.)\.{2,}(?!\s)")

    # REMOVED_SYNTAX_ERROR: invalid_count = 0
    # REMOVED_SYNTAX_ERROR: for pattern in problematic_patterns:
        # REMOVED_SYNTAX_ERROR: if ".." in pattern and not pattern.strip().startswith("from .."):
            # Exclude valid relative imports
            # REMOVED_SYNTAX_ERROR: if not re.match(r"^from\s+\.{1,3}[a-zA-Z]", pattern.strip()):
                # REMOVED_SYNTAX_ERROR: invalid_count += 1

                # REMOVED_SYNTAX_ERROR: assert invalid_count >= 4  # Should catch most invalid patterns

# REMOVED_SYNTAX_ERROR: def test_syntax_error_line_numbers(self):
    # REMOVED_SYNTAX_ERROR: """Test that syntax errors report correct line numbers"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_line_numbers.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''# Line 1
    # REMOVED_SYNTAX_ERROR: import os  # Line 2
    # REMOVED_SYNTAX_ERROR: import sys  # Line 3

    # REMOVED_SYNTAX_ERROR: from module..config import Config  # Line 5 - Error here
    # REMOVED_SYNTAX_ERROR: from another.module import Service  # Line 6

# REMOVED_SYNTAX_ERROR: def function():  # Line 8
pass
# REMOVED_SYNTAX_ERROR: '''


result = self.scanner.scan_file(test_file)
assert result.has_issues()
syntax_issues = [item for item in []]
assert len(syntax_issues) > 0
# Line number should be 5
assert any(issue.line_number == 5 for issue in syntax_issues)

# REMOVED_SYNTAX_ERROR: def test_complex_nested_imports(self):
    # REMOVED_SYNTAX_ERROR: """Test complex nested import patterns with errors"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_complex.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: from module..config import Config
        # REMOVED_SYNTAX_ERROR: except ImportError:
            # REMOVED_SYNTAX_ERROR: from backup.module import Config

            # REMOVED_SYNTAX_ERROR: if True:
                # REMOVED_SYNTAX_ERROR: from another..module import Service

# REMOVED_SYNTAX_ERROR: class MyClass:
# REMOVED_SYNTAX_ERROR: def method(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from local..import import Something
    # REMOVED_SYNTAX_ERROR: '''
    

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # Should catch multiple syntax errors
    # REMOVED_SYNTAX_ERROR: syntax_issues = [item for item in []]
    # REMOVED_SYNTAX_ERROR: assert len(syntax_issues) >= 1  # AST won"t parse this at all

# REMOVED_SYNTAX_ERROR: def test_unicode_and_special_chars(self):
    # REMOVED_SYNTAX_ERROR: """Test imports with unicode and special characters"""
    # REMOVED_SYNTAX_ERROR: test_file = Path(self.temp_dir) / "test_unicode.py"
    # REMOVED_SYNTAX_ERROR: test_file.write_text( )
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from module..cönfig import Config
    # REMOVED_SYNTAX_ERROR: from module..🔥 import Fire
    # REMOVED_SYNTAX_ERROR: from module..config! import Config
    # REMOVED_SYNTAX_ERROR: ''',
    # REMOVED_SYNTAX_ERROR: encoding="utf-8")

    # REMOVED_SYNTAX_ERROR: result = self.scanner.scan_file(test_file)
    # REMOVED_SYNTAX_ERROR: assert result.has_issues()
    # REMOVED_SYNTAX_ERROR: assert any(issue.issue_type == "syntax" for issue in result.issues)


# REMOVED_SYNTAX_ERROR: class TestImportCheckerRegexPrevalidation:
    # REMOVED_SYNTAX_ERROR: """Test regex-based pre-validation before AST parsing"""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @staticmethod
# REMOVED_SYNTAX_ERROR: def validate_import_line(line: str) -> bool:
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Pre-validate import lines with regex before AST parsing.
    # REMOVED_SYNTAX_ERROR: Returns False if the line has obvious syntax errors.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: line = line.strip()
    # REMOVED_SYNTAX_ERROR: if not line or line.startswith("#"):
        # REMOVED_SYNTAX_ERROR: return True

        # Check for invalid consecutive dots (not at start for relative )
        # imports)
        # REMOVED_SYNTAX_ERROR: if "import" in line or "from" in line:
            # Pattern 1: Dots not at the beginning of from statement
            # REMOVED_SYNTAX_ERROR: if re.search(r"[a-zA-Z_]\.\.[a-zA-Z_]", line):
                # REMOVED_SYNTAX_ERROR: return False

                # Pattern 2: More than 3 dots at the start (invalid relative )
                # import)
                # REMOVED_SYNTAX_ERROR: if re.match(r"^from\s+\.{4,}", line):
                    # REMOVED_SYNTAX_ERROR: return False

                    # Pattern 3: Trailing dots
                    # REMOVED_SYNTAX_ERROR: if re.search(r"\.\s+(import|as|$)", line):
                        # REMOVED_SYNTAX_ERROR: return False

                        # Pattern 4: Dots followed by dots with space
                        # REMOVED_SYNTAX_ERROR: if re.search(r"\.\s+\.", line):
                            # REMOVED_SYNTAX_ERROR: return False

                            # Pattern 5: Empty segments (module..config)
                            # REMOVED_SYNTAX_ERROR: if ".." in line and not re.match(r"^from\s+\.{1,3}[a-zA-Z_]", line):
                                # Not a valid relative import
                                # REMOVED_SYNTAX_ERROR: return False

                                # REMOVED_SYNTAX_ERROR: return True

# REMOVED_SYNTAX_ERROR: def test_prevalidation_catches_double_dots(self):
    # REMOVED_SYNTAX_ERROR: """Test that pre-validation catches double dot errors"""
    # REMOVED_SYNTAX_ERROR: invalid_lines = [ )
    # REMOVED_SYNTAX_ERROR: "from auth_service.app..config import AuthConfig",
    # REMOVED_SYNTAX_ERROR: "from module..submodule import Something",
    # REMOVED_SYNTAX_ERROR: "import package..module",
    # REMOVED_SYNTAX_ERROR: "from module... import Config",
    # REMOVED_SYNTAX_ERROR: "from module. import Utils",
    # REMOVED_SYNTAX_ERROR: "from module . . config import Config",
    

    # REMOVED_SYNTAX_ERROR: valid_lines = [ )
    # REMOVED_SYNTAX_ERROR: "from ..relative import Something",
    # REMOVED_SYNTAX_ERROR: "from ...parent import Module",
    # REMOVED_SYNTAX_ERROR: "from .sibling import Config",
    # REMOVED_SYNTAX_ERROR: "import module.submodule.config",
    # REMOVED_SYNTAX_ERROR: "from module.sub.config import Config",
    

    # REMOVED_SYNTAX_ERROR: for line in invalid_lines:
        # REMOVED_SYNTAX_ERROR: assert not self.validate_import_line(line), "formatted_string"

        # REMOVED_SYNTAX_ERROR: for line in valid_lines:
            # REMOVED_SYNTAX_ERROR: assert self.validate_import_line(line), "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_integration_with_scanner(self):
    # REMOVED_SYNTAX_ERROR: """Test that scanner could use pre-validation to fail fast"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: content_with_errors = '''
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: from pathlib import Path

    # REMOVED_SYNTAX_ERROR: from auth_service.app..config import AuthConfig  # Error here
    # REMOVED_SYNTAX_ERROR: from auth_service.app.services import AuthService  # Valid

# REMOVED_SYNTAX_ERROR: def main():
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: '''

    # First, try to parse with AST (will fail)
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: ast.parse(content_with_errors)
        # REMOVED_SYNTAX_ERROR: assert False, "AST should have failed"
        # REMOVED_SYNTAX_ERROR: except SyntaxError as e:
            # REMOVED_SYNTAX_ERROR: assert e.lineno == 5  # Error on line 5

            # Now test with pre-validation
            # REMOVED_SYNTAX_ERROR: lines = content_with_errors.split(" )
            # REMOVED_SYNTAX_ERROR: ")
            # REMOVED_SYNTAX_ERROR: errors = []
            # REMOVED_SYNTAX_ERROR: for i, line in enumerate(lines, 1):
                # REMOVED_SYNTAX_ERROR: if not self.validate_import_line(line):
                    # REMOVED_SYNTAX_ERROR: errors.append((i, line))

                    # REMOVED_SYNTAX_ERROR: assert len(errors) > 0
                    # REMOVED_SYNTAX_ERROR: assert errors[0][0] == 5  # Line 5 has the error
                    # REMOVED_SYNTAX_ERROR: assert "app..config" in errors[0][1]


# REMOVED_SYNTAX_ERROR: class TestEnhancedImportChecker:
    # REMOVED_SYNTAX_ERROR: """Test enhancements to make import checker more robust"""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_pre_ast_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test that we can validate imports before AST parsing"""

# REMOVED_SYNTAX_ERROR: def pre_validate_file(file_path: Path) -> list:
    # REMOVED_SYNTAX_ERROR: """Pre-validate a file for import syntax errors"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: errors = []
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: with open(file_path, "r", encoding="utf-8") as f:
            # REMOVED_SYNTAX_ERROR: for line_num, line in enumerate(f, 1):
                # REMOVED_SYNTAX_ERROR: line = line.strip()
                # REMOVED_SYNTAX_ERROR: if not line or line.startswith("#"):
                    # REMOVED_SYNTAX_ERROR: continue

                    # Check for import statements
                    # REMOVED_SYNTAX_ERROR: if "import" in line or "from" in line:
                        # Check for double dots not in relative imports
                        # REMOVED_SYNTAX_ERROR: if ".." in line:
                            # Check if it's a valid relative import
                            # REMOVED_SYNTAX_ERROR: if not re.match(r"^from\s+\.{1,3}[a-zA-Z_]", line):
                                # REMOVED_SYNTAX_ERROR: if re.search(r"[a-zA-Z_]\.\.[a-zA-Z_]", line):
                                    # REMOVED_SYNTAX_ERROR: errors.append( )
                                    # REMOVED_SYNTAX_ERROR: { )
                                    # REMOVED_SYNTAX_ERROR: "line": line_num,
                                    # REMOVED_SYNTAX_ERROR: "error": "Invalid double dots in import path",
                                    # REMOVED_SYNTAX_ERROR: "content": line,
                                    
                                    
                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                        # REMOVED_SYNTAX_ERROR: errors.append({"error": str(e)})

                                        # REMOVED_SYNTAX_ERROR: return errors

                                        # Test with a file containing double dot error
                                        # REMOVED_SYNTAX_ERROR: temp_file = Path(tempfile.mkdtemp()) / "test.py"
                                        # REMOVED_SYNTAX_ERROR: temp_file.write_text( )
                                        # REMOVED_SYNTAX_ERROR: '''
                                        # REMOVED_SYNTAX_ERROR: from auth_service.app..config import AuthConfig
                                        # REMOVED_SYNTAX_ERROR: from valid.module import Something
                                        # REMOVED_SYNTAX_ERROR: '''
                                        

                                        # REMOVED_SYNTAX_ERROR: errors = pre_validate_file(temp_file)
                                        # REMOVED_SYNTAX_ERROR: assert len(errors) > 0
                                        # REMOVED_SYNTAX_ERROR: assert errors[0]["line"] == 2
                                        # REMOVED_SYNTAX_ERROR: assert "double dots" in errors[0]["error"]

# REMOVED_SYNTAX_ERROR: def test_comprehensive_validation_pipeline(self):
    # REMOVED_SYNTAX_ERROR: """Test a comprehensive validation pipeline"""

# REMOVED_SYNTAX_ERROR: def comprehensive_validate(file_path: Path) -> dict:
    # REMOVED_SYNTAX_ERROR: """Comprehensive validation with multiple checks"""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: results = { )
    # REMOVED_SYNTAX_ERROR: "pre_validation_errors": [],
    # REMOVED_SYNTAX_ERROR: "ast_errors": [],
    # REMOVED_SYNTAX_ERROR: "import_errors": [],
    

    # Step 1: Pre-validation with regex
    # REMOVED_SYNTAX_ERROR: with open(file_path, "r", encoding="utf-8") as f:
        # REMOVED_SYNTAX_ERROR: for line_num, line in enumerate(f, 1):
            # REMOVED_SYNTAX_ERROR: if "import" in line or "from" in line:
                # Check for various patterns
                # REMOVED_SYNTAX_ERROR: if re.search(r"[a-zA-Z_]\.\.[a-zA-Z_]", line):
                    # REMOVED_SYNTAX_ERROR: results["pre_validation_errors"].append( )
                    # REMOVED_SYNTAX_ERROR: { )
                    # REMOVED_SYNTAX_ERROR: "line": line_num,
                    # REMOVED_SYNTAX_ERROR: "pattern": "double_dots",
                    # REMOVED_SYNTAX_ERROR: "content": line.strip(),
                    
                    
                    # REMOVED_SYNTAX_ERROR: if re.search(r"\.\s+import", line):
                        # REMOVED_SYNTAX_ERROR: results["pre_validation_errors"].append( )
                        # REMOVED_SYNTAX_ERROR: { )
                        # REMOVED_SYNTAX_ERROR: "line": line_num,
                        # REMOVED_SYNTAX_ERROR: "pattern": "trailing_dot",
                        # REMOVED_SYNTAX_ERROR: "content": line.strip(),
                        
                        

                        # Step 2: AST parsing (only if no pre-validation errors)
                        # REMOVED_SYNTAX_ERROR: if not results["pre_validation_errors"]:
                            # REMOVED_SYNTAX_ERROR: try:
                                # REMOVED_SYNTAX_ERROR: with open(file_path, "r", encoding="utf-8") as f:
                                    # REMOVED_SYNTAX_ERROR: ast.parse(f.read())
                                    # REMOVED_SYNTAX_ERROR: except SyntaxError as e:
                                        # REMOVED_SYNTAX_ERROR: results["ast_errors"].append({"line": e.lineno, "error": str(e)})

                                        # REMOVED_SYNTAX_ERROR: return results

                                        # Test file with double dot error
                                        # REMOVED_SYNTAX_ERROR: temp_file = Path(tempfile.mkdtemp()) / "test.py"
                                        # REMOVED_SYNTAX_ERROR: temp_file.write_text( )
                                        # REMOVED_SYNTAX_ERROR: '''
                                        # REMOVED_SYNTAX_ERROR: from auth_service.app..config import AuthConfig
                                        # REMOVED_SYNTAX_ERROR: '''
                                        

                                        # REMOVED_SYNTAX_ERROR: results = comprehensive_validate(temp_file)
                                        # REMOVED_SYNTAX_ERROR: assert len(results["pre_validation_errors"]) > 0
                                        # REMOVED_SYNTAX_ERROR: assert results["pre_validation_errors"][0]["pattern"] == "double_dots"


                                        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])
