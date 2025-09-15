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

class ImportCheckerEdgeCasesTests:
    """Test suite for edge cases that import checkers must catch"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = ComprehensiveImportScanner(self.temp_dir)

    def test_double_dot_syntax_error(self):
        """Test that double dots in module path are caught"""
        test_file = Path(self.temp_dir) / 'test_double_dot.py'
        test_file.write_text('\nfrom auth_service.app..config import AuthConfig\nfrom auth_service.app..services.auth_service import AuthService\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any((issue.issue_type == 'syntax' for issue in result.issues))
        assert any(('invalid syntax' in issue.error_message for issue in result.issues))

    def test_triple_dot_syntax_error(self):
        """Test that triple dots in module path are caught"""
        test_file = Path(self.temp_dir) / 'test_triple_dot.py'
        test_file.write_text('\nfrom some.module...config import Config\nfrom another...module.service import Service\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any((issue.issue_type == 'syntax' for issue in result.issues))

    def test_consecutive_dots_in_middle(self):
        """Test consecutive dots in the middle of import path"""
        test_file = Path(self.temp_dir) / 'test_middle_dots.py'
        test_file.write_text('\nfrom netra_backend..app.config import Config\nfrom tests..unit.test_something import TestCase\nimport module..submodule.component\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any((issue.issue_type == 'syntax' for issue in result.issues))

    def test_trailing_dots(self):
        """Test trailing dots in import statements"""
        test_file = Path(self.temp_dir) / 'test_trailing_dots.py'
        test_file.write_text('\nfrom module.submodule. import something\nfrom another.module.. import Config\nimport package.module.\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any((issue.issue_type == 'syntax' for issue in result.issues))

    def test_leading_dots_in_absolute_import(self):
        """Test incorrect leading dots in absolute imports"""
        test_file = Path(self.temp_dir) / 'test_leading_dots.py'
        test_file.write_text('\nfrom ..auth_service.config import Config  # Valid relative import\nfrom ...netra_backend.app import app  # Valid relative import\nfrom ....absolute.path import Something  # Too many dots for relative\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()

    def test_mixed_dots_and_spaces(self):
        """Test dots mixed with spaces"""
        test_file = Path(self.temp_dir) / 'test_dots_spaces.py'
        test_file.write_text('\nfrom module. .submodule import Config\nfrom another . . module import Service\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any((issue.issue_type == 'syntax' for issue in result.issues))

    def test_dots_in_alias(self):
        """Test dots in import aliases"""
        test_file = Path(self.temp_dir) / 'test_alias_dots.py'
        test_file.write_text('\nimport module.submodule as sub..module\nfrom package import module as mod..ule\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any((issue.issue_type == 'syntax' for issue in result.issues))

    def test_empty_module_segments(self):
        """Test empty segments between dots"""
        test_file = Path(self.temp_dir) / 'test_empty_segments.py'
        test_file.write_text('\nfrom module..config import Config  # Empty segment\nfrom .module import Service  # Valid relative\nfrom module. import Utils  # Invalid trailing dot\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert len([item for item in result.issues if item.issue_type == 'syntax']) >= 2

    def test_regex_precheck_for_double_dots(self):
        """Test that a regex precheck would catch double dots before AST parsing"""
        problematic_patterns = ['from auth_service.app..config import AuthConfig', 'from module..submodule import Something', 'import package..module', 'from ...module import Item', 'from module... import Config', 'from module.....submodule import Service']
        invalid_dots_pattern = re.compile('(?<!^from\\s)(?<!^from\\s\\.)\\.{2,}(?!\\s)')
        invalid_count = 0
        for pattern in problematic_patterns:
            if '..' in pattern and (not pattern.strip().startswith('from ..')):
                if not re.match('^from\\s+\\.{1,3}[a-zA-Z]', pattern.strip()):
                    invalid_count += 1
        assert invalid_count >= 4

    def test_syntax_error_line_numbers(self):
        """Test that syntax errors report correct line numbers"""
        test_file = Path(self.temp_dir) / 'test_line_numbers.py'
        test_file.write_text('# Line 1\nimport os  # Line 2\nimport sys  # Line 3\n\nfrom module..config import Config  # Line 5 - Error here\nfrom another.module import Service  # Line 6\n\ndef function():  # Line 8\n    pass\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        syntax_issues = [item for item in result.issues if item.issue_type == 'syntax']
        assert len(syntax_issues) > 0
        assert any((issue.line_number == 5 for issue in syntax_issues))

    def test_complex_nested_imports(self):
        """Test complex nested import patterns with errors"""
        test_file = Path(self.temp_dir) / 'test_complex.py'
        test_file.write_text('\ntry:\n    from module..config import Config\nexcept ImportError:\n    from backup.module import Config\n\nif True:\n    from another..module import Service\n\nclass MyClass:\n    def method(self):\n        from local..import import Something\n')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        syntax_issues = [item for item in result.issues if item.issue_type == 'syntax']
        assert len(syntax_issues) >= 1

    def test_unicode_and_special_chars(self):
        """Test imports with unicode and special characters"""
        test_file = Path(self.temp_dir) / 'test_unicode.py'
        test_file.write_text('\nfrom module..c[U+00F6]nfig import Config\nfrom module.. FIRE:  import Fire\nfrom module..config! import Config\n', encoding='utf-8')
        result = self.scanner.scan_file(test_file)
        assert result.has_issues()
        assert any((issue.issue_type == 'syntax' for issue in result.issues))

class ImportCheckerRegexPrevalidationTests:
    """Test regex-based pre-validation before AST parsing"""

    @staticmethod
    def validate_import_line(line: str) -> bool:
        """
        Pre-validate import lines with regex before AST parsing.
        Returns False if the line has obvious syntax errors.
        """
        line = line.strip()
        if not line or line.startswith('#'):
            return True
        if 'import' in line or 'from' in line:
            if re.search('[a-zA-Z_]\\.\\.[a-zA-Z_]', line):
                return False
            if re.match('^from\\s+\\.{4,}', line):
                return False
            if re.search('\\.\\s+(import|as|$)', line):
                return False
            if re.search('\\.\\s+\\.', line):
                return False
            if '..' in line and (not re.match('^from\\s+\\.{1,3}[a-zA-Z_]', line)):
                return False
        return True

    def test_prevalidation_catches_double_dots(self):
        """Test that pre-validation catches double dot errors"""
        invalid_lines = ['from auth_service.app..config import AuthConfig', 'from module..submodule import Something', 'import package..module', 'from module... import Config', 'from module. import Utils', 'from module . . config import Config']
        valid_lines = ['from ..relative import Something', 'from ...parent import Module', 'from .sibling import Config', 'import module.submodule.config', 'from module.sub.config import Config']
        for line in invalid_lines:
            assert not self.validate_import_line(line), f'Should be invalid: {line}'
        for line in valid_lines:
            assert self.validate_import_line(line), f'Should be valid: {line}'

    def test_integration_with_scanner(self):
        """Test that scanner could use pre-validation to fail fast"""
        content_with_errors = '\nimport os\nfrom pathlib import Path\n\nfrom auth_service.app..config import AuthConfig  # Error here\nfrom auth_service.app.services import AuthService  # Valid\n\ndef main():\n    pass\n'
        try:
            ast.parse(content_with_errors)
            assert False, 'AST should have failed'
        except SyntaxError as e:
            assert e.lineno == 5
        lines = content_with_errors.split('\n')
        errors = []
        for i, line in enumerate(lines, 1):
            if not self.validate_import_line(line):
                errors.append((i, line))
        assert len(errors) > 0
        assert errors[0][0] == 5
        assert 'app..config' in errors[0][1]

class EnhancedImportCheckerTests:
    """Test enhancements to make import checker more robust"""

    def test_pre_ast_validation(self):
        """Test that we can validate imports before AST parsing"""

        def pre_validate_file(file_path: Path) -> list:
            """Pre-validate a file for import syntax errors"""
            errors = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if 'import' in line or 'from' in line:
                            if '..' in line:
                                if not re.match('^from\\s+\\.{1,3}[a-zA-Z_]', line):
                                    if re.search('[a-zA-Z_]\\.\\.[a-zA-Z_]', line):
                                        errors.append({'line': line_num, 'error': 'Invalid double dots in import path', 'content': line})
            except Exception as e:
                errors.append({'error': str(e)})
            return errors
        temp_file = Path(tempfile.mkdtemp()) / 'test.py'
        temp_file.write_text('\nfrom auth_service.app..config import AuthConfig\nfrom valid.module import Something\n')
        errors = pre_validate_file(temp_file)
        assert len(errors) > 0
        assert errors[0]['line'] == 2
        assert 'double dots' in errors[0]['error']

    def test_comprehensive_validation_pipeline(self):
        """Test a comprehensive validation pipeline"""

        def comprehensive_validate(file_path: Path) -> dict:
            """Comprehensive validation with multiple checks"""
            results = {'pre_validation_errors': [], 'ast_errors': [], 'import_errors': []}
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if 'import' in line or 'from' in line:
                        if re.search('[a-zA-Z_]\\.\\.[a-zA-Z_]', line):
                            results['pre_validation_errors'].append({'line': line_num, 'pattern': 'double_dots', 'content': line.strip()})
                        if re.search('\\.\\s+import', line):
                            results['pre_validation_errors'].append({'line': line_num, 'pattern': 'trailing_dot', 'content': line.strip()})
            if not results['pre_validation_errors']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        ast.parse(f.read())
                except SyntaxError as e:
                    results['ast_errors'].append({'line': e.lineno, 'error': str(e)})
            return results
        temp_file = Path(tempfile.mkdtemp()) / 'test.py'
        temp_file.write_text('\nfrom auth_service.app..config import AuthConfig\n')
        results = comprehensive_validate(temp_file)
        assert len(results['pre_validation_errors']) > 0
        assert results['pre_validation_errors'][0]['pattern'] == 'double_dots'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')