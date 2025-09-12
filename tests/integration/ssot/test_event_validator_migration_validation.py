"""
SSOT Migration Validation Tests for EventValidator

This test suite validates the migration process for EventValidator SSOT consolidation.
Tests verify that legacy implementations are removed and SSOT patterns are enforced.

Created: 2025-09-10
Purpose: Validate EventValidator migration to SSOT compliance
Requirements: Detect legacy patterns and validate clean migration
"""

import os
import pytest
from pathlib import Path
from typing import List, Dict, Set
import subprocess
import re

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestEventValidatorMigrationValidation(SSotBaseTestCase):
    """
    Migration validation for EventValidator SSOT consolidation.
    
    These tests validate that the migration from multiple EventValidator
    implementations to a single SSOT implementation is successful.
    """
    
    def setUp(self):
        """Set up test environment for migration validation."""
        super().setUp()
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.ssot_validator_path = self.project_root / "netra_backend/app/websocket_core/event_validator.py"
        
        # Legacy files that should be removed
        self.legacy_validator_files = [
            "netra_backend/app/websocket_error_validator.py",
            "test_framework/custom_event_validator.py",
            "netra_backend/app/legacy_validators/event_validator.py",
            "tests/utils/test_event_validator.py"
        ]
    
    def test_legacy_websocket_error_validator_removed(self):
        """
        Test: Legacy websocket_error_validator file should be removed.
        
        CURRENT EXPECTATION: FAIL - Legacy file exists
        POST-CONSOLIDATION: PASS - Legacy file removed
        
        This test ensures that the legacy websocket error validator implementation
        is completely removed as part of SSOT consolidation.
        """
        legacy_files_found = []
        
        for legacy_file in self.legacy_validator_files:
            legacy_path = self.project_root / legacy_file
            if legacy_path.exists():
                legacy_files_found.append(str(legacy_file))
        
        # Check for any files with legacy validator patterns
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue
                
            # Check filename patterns
            filename = python_file.name.lower()
            if ('websocket_error_validator' in filename or 
                'legacy_event_validator' in filename or
                'custom_event_validator' in filename):
                
                relative_path = python_file.relative_to(self.project_root)
                if str(relative_path) not in legacy_files_found:
                    legacy_files_found.append(str(relative_path))
        
        print(f"\nLegacy validator file analysis:")
        print(f"Expected removed files: {len(self.legacy_validator_files)}")
        print(f"Found existing legacy files: {len(legacy_files_found)}")
        for legacy_file in legacy_files_found:
            print(f"  - {legacy_file}")
        
        # SSOT Requirement: No legacy files should exist
        self.assertEqual(
            len(legacy_files_found), 0,
            f"MIGRATION VIOLATION: Found {len(legacy_files_found)} legacy validator files that should be removed: {legacy_files_found}"
        )
    
    def test_all_imports_use_ssot_validator(self):
        """
        Test: All imports should use SSOT EventValidator path.
        
        CURRENT EXPECTATION: FAIL - Non-SSOT imports exist
        POST-CONSOLIDATION: PASS - Only SSOT imports exist
        
        This test scans the entire codebase to ensure all EventValidator imports
        use the canonical SSOT import path.
        """
        non_ssot_imports = []
        ssot_import_pattern = "netra_backend.app.websocket_core.event_validator"
        
        # Patterns that indicate non-SSOT imports
        non_ssot_patterns = [
            r"from.*websocket_error_validator.*import",
            r"from.*legacy.*event_validator.*import", 
            r"from.*custom.*event_validator.*import",
            r"from.*test.*event_validator.*import",
            r"import.*websocket_error_validator",
            r"import.*legacy.*event_validator",
            r"import.*custom.*event_validator"
        ]
        
        # Search all Python files for imports
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check each line for non-SSOT import patterns
                for line_num, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    
                    # Skip comments and empty lines
                    if not line_stripped or line_stripped.startswith('#'):
                        continue
                    
                    # Check for EventValidator imports
                    if 'EventValidator' in line and ('import' in line or 'from' in line):
                        # Check if it's NOT using SSOT pattern
                        if ssot_import_pattern not in line:
                            # Check if it matches known non-SSOT patterns
                            for pattern in non_ssot_patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    relative_path = python_file.relative_to(self.project_root)
                                    non_ssot_imports.append({
                                        'file_path': str(relative_path),
                                        'line_number': line_num,
                                        'import_line': line_stripped,
                                        'pattern_matched': pattern
                                    })
                                    break
                            else:
                                # EventValidator import that doesn't use SSOT path
                                if 'EventValidator' in line:
                                    relative_path = python_file.relative_to(self.project_root)
                                    non_ssot_imports.append({
                                        'file_path': str(relative_path),
                                        'line_number': line_num,
                                        'import_line': line_stripped,
                                        'pattern_matched': 'non_ssot_eventvalidator'
                                    })
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        print(f"\nNon-SSOT import analysis:")
        print(f"Expected SSOT import: {ssot_import_pattern}")
        print(f"Found {len(non_ssot_imports)} non-SSOT imports:")
        for import_violation in non_ssot_imports:
            print(f"  - {import_violation['file_path']}:{import_violation['line_number']}")
            print(f"    Import: {import_violation['import_line']}")
            print(f"    Pattern: {import_violation['pattern_matched']}")
        
        # SSOT Requirement: No non-SSOT imports
        self.assertEqual(
            len(non_ssot_imports), 0,
            f"MIGRATION VIOLATION: Found {len(non_ssot_imports)} non-SSOT EventValidator imports. "
            f"All imports must use SSOT path: {ssot_import_pattern}"
        )
    
    def test_no_custom_test_validators_remain(self):
        """
        Test: No custom test validators should remain after consolidation.
        
        CURRENT EXPECTATION: FAIL - 25+ custom validators exist
        POST-CONSOLIDATION: PASS - Only SSOT validator exists
        
        This test searches for custom EventValidator implementations that were
        created for testing purposes and should be consolidated.
        """
        custom_validators = []
        
        # Search for custom validator patterns
        custom_validator_patterns = [
            'MockEventValidator',
            'TestEventValidator', 
            'CustomEventValidator',
            'LocalEventValidator',
            'DevEventValidator',
            'DebugEventValidator',
            'TempEventValidator'
        ]
        
        # Search in test directories and throughout codebase
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Search for custom validator class definitions
                for pattern in custom_validator_patterns:
                    if f"class {pattern}" in content:
                        # Find line number
                        for line_num, line in enumerate(content.split('\n'), 1):
                            if f"class {pattern}" in line:
                                relative_path = python_file.relative_to(self.project_root)
                                custom_validators.append({
                                    'class_name': pattern,
                                    'file_path': str(relative_path),
                                    'line_number': line_num
                                })
                                break
                
                # Also check for inline validator creation
                validator_creation_patterns = [
                    r"EventValidator\s*\(",
                    r".*EventValidator.*=.*class",
                    r"def.*create.*event.*validator"
                ]
                
                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern in validator_creation_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Skip if it's the SSOT implementation
                            relative_path = python_file.relative_to(self.project_root)
                            if "websocket_core/event_validator.py" not in str(relative_path):
                                custom_validators.append({
                                    'class_name': 'inline_validator',
                                    'file_path': str(relative_path),
                                    'line_number': line_num,
                                    'pattern': pattern,
                                    'line_content': line.strip()
                                })
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        print(f"\nCustom validator analysis:")
        print(f"Found {len(custom_validators)} custom validators:")
        for validator in custom_validators:
            print(f"  - {validator['class_name']} in {validator['file_path']}:{validator['line_number']}")
            if 'line_content' in validator:
                print(f"    Line: {validator['line_content']}")
        
        # SSOT Requirement: No custom validators (consolidation target: 25+)
        self.assertLessEqual(
            len(custom_validators), 1,  # Allow for SSOT implementation
            f"MIGRATION VIOLATION: Found {len(custom_validators)} custom EventValidator implementations. "
            f"Expected  <= 1 (SSOT only). Custom validators found: {[v['class_name'] for v in custom_validators]}"
        )
    
    def test_ssot_validator_exists_and_complete(self):
        """
        Test: SSOT EventValidator should exist and be complete.
        
        CURRENT EXPECTATION: FAIL - SSOT file doesn't exist or incomplete
        POST-CONSOLIDATION: PASS - SSOT file exists and complete
        
        This test validates that the SSOT EventValidator file exists and contains
        all necessary functionality from consolidated implementations.
        """
        # Check SSOT file exists
        self.assertTrue(
            self.ssot_validator_path.exists(),
            f"SSOT EventValidator file not found: {self.ssot_validator_path}"
        )
        
        # Read and analyze SSOT implementation
        with open(self.ssot_validator_path, 'r', encoding='utf-8') as f:
            ssot_content = f.read()
        
        # Required SSOT functionality
        required_methods = [
            'validate_websocket_event',
            'validate_agent_event', 
            'validate_event_data',
            'validate_critical_event',
            'calculate_business_impact'
        ]
        
        required_classes = ['EventValidator']
        
        missing_methods = []
        missing_classes = []
        
        # Check for required classes
        for class_name in required_classes:
            if f"class {class_name}" not in ssot_content:
                missing_classes.append(class_name)
        
        # Check for required methods
        for method_name in required_methods:
            if f"def {method_name}" not in ssot_content:
                missing_methods.append(method_name)
        
        print(f"\nSSOT EventValidator completeness analysis:")
        print(f"File exists: {self.ssot_validator_path.exists()}")
        print(f"File size: {len(ssot_content)} characters")
        print(f"Required classes: {len(required_classes)} - Missing: {missing_classes}")
        print(f"Required methods: {len(required_methods)} - Missing: {missing_methods}")
        
        # SSOT Requirement: All functionality present
        self.assertEqual(
            len(missing_classes), 0,
            f"SSOT INCOMPLETE: Missing required classes: {missing_classes}"
        )
        
        self.assertEqual(
            len(missing_methods), 0,
            f"SSOT INCOMPLETE: Missing required methods: {missing_methods}"
        )
    
    def test_migration_preserves_business_critical_functionality(self):
        """
        Test: Migration preserves all business-critical validation functionality.
        
        CURRENT EXPECTATION: FAIL - Functionality scattered across files
        POST-CONSOLIDATION: PASS - All functionality in SSOT
        
        This test ensures that consolidation doesn't lose any business-critical
        validation capabilities.
        """
        business_critical_patterns = [
            'revenue_impact',
            'user_experience_impact',
            'critical_event_validation',
            'websocket_event_scoring',
            'agent_execution_validation'
        ]
        
        # Search for business critical functionality across codebase
        functionality_locations = {}
        
        for python_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(python_file):
                continue
                
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in business_critical_patterns:
                    if pattern in content.lower():
                        if pattern not in functionality_locations:
                            functionality_locations[pattern] = []
                        
                        relative_path = python_file.relative_to(self.project_root)
                        functionality_locations[pattern].append(str(relative_path))
                        
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Check if functionality is properly consolidated
        scattered_functionality = []
        
        for pattern, locations in functionality_locations.items():
            if len(locations) > 1:
                # Check if SSOT file contains this functionality
                ssot_location = "netra_backend/app/websocket_core/event_validator.py"
                if ssot_location not in locations:
                    scattered_functionality.append({
                        'pattern': pattern,
                        'locations': locations,
                        'ssot_missing': True
                    })
                elif len(locations) > 2:  # SSOT + 1 other location might be acceptable
                    scattered_functionality.append({
                        'pattern': pattern,
                        'locations': locations,
                        'ssot_missing': False
                    })
        
        print(f"\nBusiness critical functionality analysis:")
        for pattern, locations in functionality_locations.items():
            print(f"  Pattern '{pattern}': {len(locations)} locations")
            for location in locations[:3]:  # Show first 3
                print(f"    - {location}")
            if len(locations) > 3:
                print(f"    ... and {len(locations) - 3} more")
        
        print(f"\nScattered functionality: {len(scattered_functionality)}")
        for item in scattered_functionality:
            print(f"  - {item['pattern']}: {len(item['locations'])} locations (SSOT missing: {item['ssot_missing']})")
        
        # Business Requirement: Minimal scattering allowed
        self.assertLessEqual(
            len(scattered_functionality), 2,  # Allow some reasonable scattering
            f"MIGRATION VIOLATION: Too much business critical functionality scattered across files: {scattered_functionality}"
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
            ".mypy_cache"
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)


if __name__ == "__main__":
    pytest.main([__file__])