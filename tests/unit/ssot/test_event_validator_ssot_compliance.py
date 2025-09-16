"""
SSOT Compliance Tests for EventValidator Consolidation

This test suite validates Single Source of Truth (SSOT) compliance for EventValidator.
Tests are designed to FAIL before consolidation and PASS after, proving SSOT violations exist.

Created: 2025-09-10
Purpose: Validate EventValidator SSOT consolidation success
Requirements: Must detect current violations to prove consolidation necessity
"""
import os
import ast
import pytest
from pathlib import Path
from typing import List, Dict, Set
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class EventValidatorSsotComplianceTests(SSotBaseTestCase):
    """
    SSOT Compliance validation for EventValidator consolidation.
    
    These tests SHOULD FAIL initially, proving SSOT violations exist.
    After consolidation, these tests SHOULD PASS, validating success.
    """

    def setUp(self):
        """Set up test environment with project root path."""
        super().setUp()
        self.project_root = Path('/Users/anthony/Desktop/netra-apex')
        self.expected_ssot_path = 'netra_backend/app/websocket_core/event_validator.py'

    @classmethod
    def setUpClass(cls):
        """Set up class-level test environment."""
        super().setUpClass()
        cls.project_root = Path('/Users/anthony/Desktop/netra-apex')
        cls.expected_ssot_path = 'netra_backend/app/websocket_core/event_validator.py'

    def test_only_one_event_validator_class_exists(self):
        """
        Test: Only ONE EventValidator class should exist in entire codebase.
        
        CURRENT EXPECTATION: FAIL - Multiple EventValidator classes exist
        POST-CONSOLIDATION: PASS - Only SSOT EventValidator exists
        
        This test searches the entire codebase for EventValidator class definitions
        and ensures only the SSOT implementation exists.
        """
        project_root = Path('/Users/anthony/Desktop/netra-apex')
        expected_ssot_path = 'netra_backend/app/websocket_core/event_validator.py'
        event_validator_classes = []
        for python_file in project_root.rglob('*.py'):
            if self._should_skip_file(python_file):
                continue
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and 'EventValidator' in node.name:
                            relative_path = python_file.relative_to(self.project_root)
                            event_validator_classes.append({'class_name': node.name, 'file_path': str(relative_path), 'line_number': node.lineno})
                except SyntaxError:
                    continue
            except (UnicodeDecodeError, PermissionError):
                continue
        print(f'\nFound EventValidator classes: {len(event_validator_classes)}')
        for validator_class in event_validator_classes:
            print(f"  - {validator_class['class_name']} in {validator_class['file_path']}:{validator_class['line_number']}")
        self.assertEqual(len(event_validator_classes), 1, f"SSOT VIOLATION: Found {len(event_validator_classes)} EventValidator classes. Expected exactly 1. Classes found: {[c['file_path'] for c in event_validator_classes]}")
        ssot_class = event_validator_classes[0]
        self.assertEqual(ssot_class['file_path'], self.expected_ssot_path, f"EventValidator not in SSOT location. Found: {ssot_class['file_path']}, Expected: {self.expected_ssot_path}")

    def test_no_duplicate_validation_logic_exists(self):
        """
        Test: No duplicate validation logic should exist across codebase.
        
        CURRENT EXPECTATION: FAIL - Multiple validate_* functions exist
        POST-CONSOLIDATION: PASS - Only SSOT validation functions exist
        
        This test searches for duplicate validation function patterns that indicate
        SSOT violations in event validation logic.
        """
        validation_functions = {}
        critical_validation_patterns = ['validate_websocket_event', 'validate_agent_event', 'validate_event_data', 'validate_event_structure', 'validate_critical_event']
        for python_file in self.project_root.rglob('*.py'):
            if self._should_skip_file(python_file):
                continue
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            func_name = node.name
                            for pattern in critical_validation_patterns:
                                if pattern in func_name:
                                    if pattern not in validation_functions:
                                        validation_functions[pattern] = []
                                    relative_path = python_file.relative_to(self.project_root)
                                    validation_functions[pattern].append({'function_name': func_name, 'file_path': str(relative_path), 'line_number': node.lineno})
                except SyntaxError:
                    continue
            except (UnicodeDecodeError, PermissionError):
                continue
        duplicates_found = []
        for pattern, functions in validation_functions.items():
            if len(functions) > 1:
                duplicates_found.append({'pattern': pattern, 'count': len(functions), 'locations': functions})
        print(f'\nValidation function analysis:')
        for pattern, functions in validation_functions.items():
            print(f"  Pattern '{pattern}': {len(functions)} implementations")
            for func in functions:
                print(f"    - {func['function_name']} in {func['file_path']}:{func['line_number']}")
        self.assertEqual(len(duplicates_found), 0, f'SSOT VIOLATION: Found duplicate validation logic patterns: {duplicates_found}')

    def test_ssot_import_paths_valid(self):
        """
        Test: All EventValidator imports should use SSOT path.
        
        CURRENT EXPECTATION: FAIL - Legacy import paths exist
        POST-CONSOLIDATION: PASS - Only SSOT imports exist
        
        This test validates that all imports of EventValidator use the canonical
        SSOT import path and no legacy imports remain.
        """
        import_violations = []
        expected_ssot_import = 'netra_backend.app.websocket_core.event_validator'
        legacy_import_patterns = ['websocket_error_validator', 'custom_event_validator', 'test_event_validator', 'legacy_validator']
        for python_file in self.project_root.rglob('*.py'):
            if self._should_skip_file(python_file):
                continue
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                for line_num, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    if not line_stripped or line_stripped.startswith('#'):
                        continue
                    if 'EventValidator' in line and ('import' in line or 'from' in line):
                        is_ssot_import = expected_ssot_import in line
                        uses_legacy_pattern = any((pattern in line for pattern in legacy_import_patterns))
                        if not is_ssot_import or uses_legacy_pattern:
                            relative_path = python_file.relative_to(self.project_root)
                            import_violations.append({'file_path': str(relative_path), 'line_number': line_num, 'import_line': line_stripped, 'is_ssot': is_ssot_import, 'uses_legacy': uses_legacy_pattern})
            except (UnicodeDecodeError, PermissionError):
                continue
        print(f'\nEventValidator import analysis:')
        print(f'Expected SSOT import pattern: {expected_ssot_import}')
        print(f'Found {len(import_violations)} import violations:')
        for violation in import_violations:
            print(f"  - {violation['file_path']}:{violation['line_number']}")
            print(f"    Import: {violation['import_line']}")
            print(f"    SSOT: {violation['is_ssot']}, Legacy: {violation['uses_legacy']}")
        self.assertEqual(len(import_violations), 0, f'SSOT VIOLATION: Found {len(import_violations)} import violations. All EventValidator imports must use SSOT path: {expected_ssot_import}')

    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Determine if file should be skipped during analysis.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file should be skipped
        """
        skip_patterns = ['__pycache__', '.git', 'node_modules', '.venv', 'venv', '.pytest_cache', 'build', 'dist', '.mypy_cache']
        file_str = str(file_path)
        return any((pattern in file_str for pattern in skip_patterns))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')