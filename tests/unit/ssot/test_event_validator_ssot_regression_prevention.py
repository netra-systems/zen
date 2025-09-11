"""
SSOT Regression Prevention Tests for EventValidator

This test suite implements regression prevention for EventValidator SSOT consolidation.
Tests are designed to FAIL when SSOT violations are introduced, maintaining compliance.

Created: 2025-09-10
Purpose: Prevent regression in EventValidator SSOT consolidation
Requirements: Fail on SSOT violations, enforce import compliance, prevent duplicates
"""

import os
import ast
import pytest
import re
from pathlib import Path
from typing import Dict, List, Set, Any
import subprocess

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestEventValidatorSsotRegressionPrevention(SSotBaseTestCase):
    """
    Regression prevention tests for EventValidator SSOT consolidation.
    
    These tests are designed to FAIL immediately when any SSOT violations
    are introduced, preventing regression from the consolidated state.
    
    CRITICAL: These tests should PASS after consolidation and FAIL if
    anyone introduces SSOT violations.
    """
    
    def setUp(self):
        """Set up regression prevention test environment."""
        super().setUp()
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.ssot_validator_path = "netra_backend/app/websocket_core/event_validator.py"
        
        # SSOT compliance thresholds (strict after consolidation)
        self.max_allowed_event_validators = 1
        self.max_allowed_validation_duplicates = 0
        self.max_allowed_legacy_imports = 0
        self.max_allowed_custom_validators = 1  # Only SSOT allowed
    
    def test_fails_when_duplicate_event_validator_detected(self):
        """
        Test: FAIL immediately when duplicate EventValidator classes are detected.
        
        POST-CONSOLIDATION: PASS - Only SSOT EventValidator exists
        REGRESSION: FAIL - Additional EventValidator classes added
        
        This test enforces the SSOT principle by failing when anyone adds
        additional EventValidator class implementations.
        """
        event_validator_classes = []
        
        # Comprehensive search for EventValidator class definitions
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check for EventValidator or similar names
                            class_name = node.name
                            if (class_name == 'EventValidator' or 
                                'EventValidator' in class_name or
                                re.match(r'.*Event.*Validator.*', class_name) or
                                re.match(r'.*Validator.*Event.*', class_name)):
                                
                                relative_path = python_file.relative_to(self.project_root)
                                event_validator_classes.append({
                                    'class_name': class_name,
                                    'file_path': str(relative_path),
                                    'line_number': node.lineno,
                                    'is_ssot': str(relative_path) == self.ssot_validator_path
                                })
                except SyntaxError:
                    continue
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Count non-SSOT EventValidator classes
        non_ssot_validators = [v for v in event_validator_classes if not v['is_ssot']]
        
        print(f"\nEventValidator class detection (REGRESSION PREVENTION):")
        print(f"Total EventValidator classes found: {len(event_validator_classes)}")
        print(f"SSOT EventValidator classes: {len([v for v in event_validator_classes if v['is_ssot']])}")
        print(f"Non-SSOT EventValidator classes: {len(non_ssot_validators)}")
        
        for validator in event_validator_classes:
            ssot_marker = "✅ SSOT" if validator['is_ssot'] else "❌ VIOLATION"
            print(f"  {validator['class_name']} in {validator['file_path']}:{validator['line_number']} - {ssot_marker}")
        
        # REGRESSION PREVENTION: FAIL if any non-SSOT EventValidator classes exist
        self.assertEqual(
            len(non_ssot_validators), 0,
            f"SSOT REGRESSION DETECTED: Found {len(non_ssot_validators)} non-SSOT EventValidator classes. "
            f"Only SSOT EventValidator allowed at {self.ssot_validator_path}. "
            f"Violations: {[v['file_path'] for v in non_ssot_validators]}"
        )
        
        # Ensure exactly one SSOT EventValidator exists
        ssot_validators = [v for v in event_validator_classes if v['is_ssot']]
        self.assertEqual(
            len(ssot_validators), 1,
            f"SSOT INTEGRITY VIOLATION: Expected exactly 1 SSOT EventValidator, found {len(ssot_validators)}"
        )
    
    def test_fails_when_custom_validation_logic_added(self):
        """
        Test: FAIL when custom validation logic bypasses SSOT EventValidator.
        
        POST-CONSOLIDATION: PASS - Only SSOT validation logic exists
        REGRESSION: FAIL - Custom validation logic added
        
        This test prevents developers from creating custom validation logic
        that bypasses the consolidated SSOT EventValidator.
        """
        custom_validation_implementations = []
        
        # Patterns that indicate custom validation bypassing SSOT
        forbidden_patterns = [
            r'class.*Event.*Validator.*:',
            r'def\s+validate_websocket_event.*:',
            r'def\s+validate_agent_event.*:',
            r'def\s+custom.*event.*validation.*:',
            r'def\s+local.*event.*validation.*:',
            r'def\s+inline.*event.*validation.*:',
            r'validate.*event.*=\s*lambda',
            r'EventValidator\s*=\s*type\(',
            r'EventValidator\s*=\s*class'
        ]
        
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue
                
            # Skip the SSOT file itself
            relative_path = python_file.relative_to(self.project_root)
            if str(relative_path) == self.ssot_validator_path:
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for forbidden validation patterns
                for line_num, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    
                    # Skip comments and empty lines
                    if not line_stripped or line_stripped.startswith('#'):
                        continue
                    
                    for pattern in forbidden_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            custom_validation_implementations.append({
                                'file_path': str(relative_path),
                                'line_number': line_num,
                                'line_content': line_stripped,
                                'pattern_matched': pattern,
                                'violation_type': 'custom_validation_logic'
                            })
                            break
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        print(f"\nCustom validation logic detection (REGRESSION PREVENTION):")
        print(f"Custom validation implementations found: {len(custom_validation_implementations)}")
        
        for violation in custom_validation_implementations:
            print(f"  VIOLATION in {violation['file_path']}:{violation['line_number']}")
            print(f"    Line: {violation['line_content']}")
            print(f"    Pattern: {violation['pattern_matched']}")
        
        # REGRESSION PREVENTION: FAIL if any custom validation logic exists
        self.assertEqual(
            len(custom_validation_implementations), 0,
            f"CUSTOM VALIDATION REGRESSION DETECTED: Found {len(custom_validation_implementations)} "
            f"custom validation implementations that bypass SSOT EventValidator. "
            f"All validation must use SSOT at {self.ssot_validator_path}. "
            f"Violations: {[v['file_path'] for v in custom_validation_implementations]}"
        )
    
    def test_fails_when_import_patterns_violate_ssot(self):
        """
        Test: FAIL when import patterns violate SSOT compliance.
        
        POST-CONSOLIDATION: PASS - Only SSOT imports exist
        REGRESSION: FAIL - Legacy or custom imports added
        
        This test enforces that all EventValidator imports use the canonical
        SSOT import path and prevents reintroduction of legacy patterns.
        """
        import_violations = []
        expected_ssot_import = "netra_backend.app.websocket_core.event_validator"
        
        # Forbidden import patterns that violate SSOT
        forbidden_import_patterns = [
            r'from.*websocket_error_validator.*import',
            r'from.*custom.*event.*validator.*import',
            r'from.*legacy.*validator.*import',
            r'from.*test.*event.*validator.*import',
            r'from.*local.*validator.*import',
            r'from.*temp.*validator.*import',
            r'import.*websocket_error_validator',
            r'import.*custom.*event.*validator',
            r'import.*legacy.*validator',
            r'import.*local.*validator'
        ]
        
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for line_num, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    
                    # Skip comments and empty lines
                    if not line_stripped or line_stripped.startswith('#'):
                        continue
                    
                    # Check for EventValidator imports
                    if 'EventValidator' in line and ('import' in line or 'from' in line):
                        relative_path = python_file.relative_to(self.project_root)
                        
                        # Check for forbidden patterns
                        is_forbidden = False
                        matched_pattern = None
                        
                        for pattern in forbidden_import_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                is_forbidden = True
                                matched_pattern = pattern
                                break
                        
                        # Check if it's not using SSOT path (and not a comment)
                        if not line_stripped.startswith('#') and expected_ssot_import not in line:
                            # Additional check: EventValidator import not using SSOT path
                            if 'EventValidator' in line and ('import' in line or 'from' in line):
                                is_forbidden = True
                                matched_pattern = 'non_ssot_import_path'
                        
                        if is_forbidden:
                            import_violations.append({
                                'file_path': str(relative_path),
                                'line_number': line_num,
                                'import_line': line_stripped,
                                'pattern_matched': matched_pattern,
                                'violation_type': 'forbidden_import_pattern'
                            })
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        print(f"\nImport pattern violation detection (REGRESSION PREVENTION):")
        print(f"Expected SSOT import: {expected_ssot_import}")
        print(f"Import violations found: {len(import_violations)}")
        
        for violation in import_violations:
            print(f"  VIOLATION in {violation['file_path']}:{violation['line_number']}")
            print(f"    Import: {violation['import_line']}")
            print(f"    Pattern: {violation['pattern_matched']}")
        
        # REGRESSION PREVENTION: FAIL if any import violations exist
        self.assertEqual(
            len(import_violations), 0,
            f"IMPORT PATTERN REGRESSION DETECTED: Found {len(import_violations)} import violations. "
            f"All EventValidator imports must use SSOT path: {expected_ssot_import}. "
            f"Violations: {[v['file_path'] for v in import_violations]}"
        )
    
    def test_fails_when_ssot_file_modified_incorrectly(self):
        """
        Test: FAIL when SSOT EventValidator file is modified incorrectly.
        
        POST-CONSOLIDATION: PASS - SSOT file contains required functionality
        REGRESSION: FAIL - Required functionality removed from SSOT
        
        This test ensures that the SSOT EventValidator maintains all required
        functionality and prevents accidental removal of critical methods.
        """
        ssot_file_path = self.project_root / self.ssot_validator_path
        
        # Check SSOT file exists
        if not ssot_file_path.exists():
            self.fail(f"SSOT INTEGRITY FAILURE: SSOT EventValidator file missing: {ssot_file_path}")
        
        # Read SSOT file content
        with open(ssot_file_path, 'r', encoding='utf-8') as f:
            ssot_content = f.read()
        
        # Required SSOT components (consolidated from original implementations)
        required_components = {
            'classes': [
                'EventValidator'
            ],
            'methods': [
                'validate_websocket_event',
                'validate_agent_event',
                'validate_event_data',
                'validate_critical_event',
                'calculate_business_impact'
            ],
            'business_logic_patterns': [
                'revenue_impact',
                'user_experience',
                'critical_event',
                'business_value'
            ],
            'integration_patterns': [
                'websocket',
                'agent_execution',
                'event_validation'
            ]
        }
        
        missing_components = {
            'classes': [],
            'methods': [],
            'business_logic_patterns': [],
            'integration_patterns': []
        }
        
        # Check for required classes
        for required_class in required_components['classes']:
            if f"class {required_class}" not in ssot_content:
                missing_components['classes'].append(required_class)
        
        # Check for required methods
        for required_method in required_components['methods']:
            if f"def {required_method}" not in ssot_content:
                missing_components['methods'].append(required_method)
        
        # Check for business logic patterns
        for pattern in required_components['business_logic_patterns']:
            if pattern.lower() not in ssot_content.lower():
                missing_components['business_logic_patterns'].append(pattern)
        
        # Check for integration patterns
        for pattern in required_components['integration_patterns']:
            if pattern.lower() not in ssot_content.lower():
                missing_components['integration_patterns'].append(pattern)
        
        # Calculate completeness
        total_required = sum(len(components) for components in required_components.values())
        total_missing = sum(len(missing) for missing in missing_components.values())
        completeness_percentage = ((total_required - total_missing) / total_required) * 100
        
        print(f"\nSSOT EventValidator completeness check (REGRESSION PREVENTION):")
        print(f"File: {ssot_file_path}")
        print(f"File size: {len(ssot_content)} characters")
        print(f"Completeness: {completeness_percentage:.1f}%")
        
        for component_type, missing_items in missing_components.items():
            if missing_items:
                print(f"  Missing {component_type}: {missing_items}")
            else:
                print(f"  ✅ All {component_type} present")
        
        # REGRESSION PREVENTION: FAIL if critical components are missing
        critical_missing = missing_components['classes'] + missing_components['methods']
        self.assertEqual(
            len(critical_missing), 0,
            f"SSOT INTEGRITY REGRESSION DETECTED: Critical components missing from SSOT EventValidator: {critical_missing}"
        )
        
        # Business Logic Requirement: Essential business patterns must be present
        essential_business_missing = missing_components['business_logic_patterns']
        self.assertLessEqual(
            len(essential_business_missing), 1,  # Allow 1 missing pattern
            f"BUSINESS LOGIC REGRESSION DETECTED: Essential business patterns missing: {essential_business_missing}"
        )
        
        # Completeness Requirement: SSOT must be substantially complete
        self.assertGreaterEqual(
            completeness_percentage, 85.0,
            f"SSOT COMPLETENESS REGRESSION DETECTED: SSOT EventValidator only {completeness_percentage:.1f}% complete, minimum 85% required"
        )
    
    def test_fails_when_test_infrastructure_bypasses_ssot(self):
        """
        Test: FAIL when test infrastructure bypasses SSOT EventValidator.
        
        POST-CONSOLIDATION: PASS - Tests use SSOT EventValidator
        REGRESSION: FAIL - Tests create custom validators or bypass SSOT
        
        This test prevents test code from undermining SSOT compliance by
        creating custom validators or bypassing the consolidated implementation.
        """
        test_ssot_bypasses = []
        
        # Search specifically in test directories
        test_directories = [
            'tests',
            'test_framework', 
            'netra_backend/tests',
            'auth_service/tests',
            'frontend/tests'
        ]
        
        # Patterns that indicate test infrastructure bypassing SSOT
        bypass_patterns = [
            r'MockEventValidator',
            r'TestEventValidator',
            r'FakeEventValidator',
            r'StubEventValidator',
            r'DummyEventValidator',
            r'CustomEventValidator',
            r'LocalEventValidator',
            r'EventValidator\s*=\s*Mock',
            r'EventValidator\s*=\s*MagicMock',
            r'patch.*EventValidator',
            r'@patch.*event.*validator',
            r'monkeypatch.*event.*validator'
        ]
        
        for test_dir in test_directories:
            test_path = self.project_root / test_dir
            if not test_path.exists():
                continue
                
            for python_file in test_path.rglob("*.py"):
                if self._should_skip_file(python_file):
                    continue
                    
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for line_num, line in enumerate(content.split('\n'), 1):
                        line_stripped = line.strip()
                        
                        # Skip comments
                        if not line_stripped or line_stripped.startswith('#'):
                            continue
                        
                        for pattern in bypass_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                relative_path = python_file.relative_to(self.project_root)
                                test_ssot_bypasses.append({
                                    'file_path': str(relative_path),
                                    'line_number': line_num,
                                    'line_content': line_stripped,
                                    'pattern_matched': pattern,
                                    'violation_type': 'test_ssot_bypass'
                                })
                                break
                                
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        print(f"\nTest infrastructure SSOT bypass detection (REGRESSION PREVENTION):")
        print(f"Test SSOT bypasses found: {len(test_ssot_bypasses)}")
        
        for bypass in test_ssot_bypasses:
            print(f"  VIOLATION in {bypass['file_path']}:{bypass['line_number']}")
            print(f"    Line: {bypass['line_content']}")
            print(f"    Pattern: {bypass['pattern_matched']}")
        
        # REGRESSION PREVENTION: FAIL if test infrastructure bypasses SSOT
        self.assertLessEqual(
            len(test_ssot_bypasses), 2,  # Allow minimal test utilities
            f"TEST INFRASTRUCTURE REGRESSION DETECTED: Found {len(test_ssot_bypasses)} test SSOT bypasses. "
            f"Tests should use SSOT EventValidator or approved test utilities only. "
            f"Violations: {[b['file_path'] for b in test_ssot_bypasses]}"
        )
    
    def test_fails_when_architectural_boundaries_violated(self):
        """
        Test: FAIL when architectural boundaries around SSOT are violated.
        
        POST-CONSOLIDATION: PASS - Clean architectural boundaries
        REGRESSION: FAIL - Cross-service violations or boundary breaches
        
        This test ensures that the SSOT EventValidator maintains proper
        architectural boundaries and prevents cross-service violations.
        """
        boundary_violations = []
        
        # Define architectural boundaries for SSOT EventValidator
        ssot_service = "websocket_core"
        allowed_dependencies = [
            "netra_backend.app.core",
            "netra_backend.app.db",
            "netra_backend.app.websocket_core",
            "shared",
            "test_framework"
        ]
        
        forbidden_dependencies = [
            "auth_service",  # Should not directly import auth service
            "frontend",      # Should not import frontend
            "scripts"        # Should not import scripts
        ]
        
        # Check SSOT file for boundary violations
        ssot_file_path = self.project_root / self.ssot_validator_path
        if ssot_file_path.exists():
            try:
                with open(ssot_file_path, 'r', encoding='utf-8') as f:
                    ssot_content = f.read()
                    
                # Check for forbidden import patterns
                for line_num, line in enumerate(ssot_content.split('\n'), 1):
                    line_stripped = line.strip()
                    
                    if 'import' in line or 'from' in line:
                        for forbidden in forbidden_dependencies:
                            if forbidden in line:
                                boundary_violations.append({
                                    'file_path': self.ssot_validator_path,
                                    'line_number': line_num,
                                    'violation_type': 'forbidden_dependency',
                                    'forbidden_dependency': forbidden,
                                    'line_content': line_stripped
                                })
                                
            except (UnicodeDecodeError, PermissionError):
                pass
        
        # Check for reverse dependency violations (other services importing SSOT directly)
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue
                
            relative_path = python_file.relative_to(self.project_root)
            
            # Skip the SSOT file itself and allowed services
            if str(relative_path) == self.ssot_validator_path:
                continue
                
            # Check if file is in forbidden service trying to import SSOT
            file_service = str(relative_path).split('/')[0] if '/' in str(relative_path) else ''
            if file_service in forbidden_dependencies:
                try:
                    with open(python_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for SSOT imports from forbidden services
                    if 'websocket_core.event_validator' in content:
                        for line_num, line in enumerate(content.split('\n'), 1):
                            if 'websocket_core.event_validator' in line and ('import' in line or 'from' in line):
                                boundary_violations.append({
                                    'file_path': str(relative_path),
                                    'line_number': line_num,
                                    'violation_type': 'forbidden_reverse_dependency',
                                    'forbidden_service': file_service,
                                    'line_content': line.strip()
                                })
                                
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        print(f"\nArchitectural boundary violation detection (REGRESSION PREVENTION):")
        print(f"Allowed dependencies: {allowed_dependencies}")
        print(f"Forbidden dependencies: {forbidden_dependencies}")
        print(f"Boundary violations found: {len(boundary_violations)}")
        
        for violation in boundary_violations:
            print(f"  VIOLATION in {violation['file_path']}:{violation['line_number']}")
            print(f"    Type: {violation['violation_type']}")
            print(f"    Line: {violation['line_content']}")
            if 'forbidden_dependency' in violation:
                print(f"    Forbidden dependency: {violation['forbidden_dependency']}")
            if 'forbidden_service' in violation:
                print(f"    Forbidden service: {violation['forbidden_service']}")
        
        # REGRESSION PREVENTION: FAIL if architectural boundaries are violated
        self.assertEqual(
            len(boundary_violations), 0,
            f"ARCHITECTURAL BOUNDARY REGRESSION DETECTED: Found {len(boundary_violations)} boundary violations. "
            f"SSOT EventValidator must maintain proper service boundaries. "
            f"Violations: {[v['file_path'] for v in boundary_violations]}"
        )
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped during analysis."""
        skip_patterns = [
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv", 
            ".pytest_cache",
            "build",
            "dist",
            ".mypy_cache",
            ".DS_Store"
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)


if __name__ == "__main__":
    pytest.main([__file__])