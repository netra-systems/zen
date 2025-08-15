#!/usr/bin/env python3
"""
Type and test stub checking module for boundary enforcement system.
Handles duplicate type detection and test stub boundary validation.
"""

import glob
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from boundary_enforcer_core_types import (
    BoundaryViolation, SystemBoundaries, should_skip_file, get_test_stub_patterns
)

class TypeBoundaryChecker:
    """Handles duplicate type and test stub boundary validation"""
    
    def __init__(self, root_path: Path, boundaries: SystemBoundaries):
        self.root_path = root_path
        self.boundaries = boundaries
        self.violations: List[BoundaryViolation] = []

    def check_duplicate_type_boundaries(self) -> List[BoundaryViolation]:
        """Check for duplicate types across system"""
        self.violations.clear()
        type_definitions = defaultdict(list)
        self._collect_python_types(type_definitions)
        self._collect_typescript_types(type_definitions)
        self._create_duplicate_violations(type_definitions)
        return [v for v in self.violations if v.violation_type == "duplicate_type_boundary"]

    def check_test_stub_boundaries(self) -> List[BoundaryViolation]:
        """Check for test stubs in production code"""
        stub_violations = []
        patterns = get_test_stub_patterns()
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip_test_file(filepath):
                continue
            violation = self._scan_file_for_stubs(filepath, patterns)
            if violation:
                stub_violations.append(violation)
        return stub_violations

    def _collect_python_types(self, type_definitions: Dict[str, List[str]]) -> None:
        """Collect Python class definitions from app files"""
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if should_skip_file(filepath):
                continue
            self._extract_python_types(filepath, type_definitions)

    def _extract_python_types(self, filepath: str, type_definitions: Dict[str, List[str]]) -> None:
        """Extract Python type definitions from a single file"""
        content = self._read_file_safely(filepath)
        if content is None:
            return
        rel_path = str(Path(filepath).relative_to(self.root_path))
        self._find_python_class_definitions(content, rel_path, type_definitions)

    def _find_python_class_definitions(self, content: str, rel_path: str, 
                                     type_definitions: Dict[str, List[str]]) -> None:
        """Find Python class definitions in content"""
        for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
            type_name = match.group(1)
            type_definitions[type_name].append(rel_path)

    def _collect_typescript_types(self, type_definitions: Dict[str, List[str]]) -> None:
        """Collect TypeScript type definitions from frontend files"""
        for pattern in ['frontend/**/*.ts', 'frontend/**/*.tsx']:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if 'node_modules' in filepath:
                    continue
                self._extract_typescript_types(filepath, type_definitions)

    def _extract_typescript_types(self, filepath: str, type_definitions: Dict[str, List[str]]) -> None:
        """Extract TypeScript type definitions from a single file"""
        content = self._read_file_safely(filepath)
        if content is None:
            return
        rel_path = str(Path(filepath).relative_to(self.root_path))
        self._find_typescript_type_definitions(content, rel_path, type_definitions)

    def _find_typescript_type_definitions(self, content: str, rel_path: str,
                                        type_definitions: Dict[str, List[str]]) -> None:
        """Find TypeScript interface/type definitions in content"""
        for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
            type_name = match.group(1)
            type_definitions[type_name].append(rel_path)

class TestStubChecker:
    """Handles test stub detection in production code"""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path

    def scan_file_for_test_stubs(self, filepath: str, patterns: List[tuple]) -> Optional[BoundaryViolation]:
        """Scan a single file for test stub patterns"""
        content = self._read_file_safely(filepath)
        if content is None:
            return None
        rel_path = str(Path(filepath).relative_to(self.root_path))
        return self._check_stub_patterns(content, rel_path, patterns)

    def _check_stub_patterns(self, content: str, rel_path: str, 
                           patterns: List[tuple]) -> Optional[BoundaryViolation]:
        """Check all patterns in file content and create violation"""
        for pattern, description in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
            if matches:
                line_number = content[:matches[0].start()].count('\n') + 1
                return self._create_test_stub_violation(rel_path, line_number, description)
        return None

    def _create_test_stub_violation(self, rel_path: str, line_number: int, 
                                  description: str) -> BoundaryViolation:
        """Create test stub boundary violation"""
        return BoundaryViolation(
            file_path=rel_path, violation_type="test_stub_boundary", severity="critical",
            boundary_name="NO_TEST_STUBS", line_number=line_number, impact_score=7,
            description=f"Test stub in production: {description}",
            fix_suggestion="Replace with production implementation"
        )

    def _read_file_safely(self, filepath: str) -> Optional[str]:
        """Read file content safely, return None on error"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

class DuplicateTypeViolationFactory:
    """Creates duplicate type boundary violations"""
    
    @staticmethod
    def create_duplicate_violations(type_definitions: Dict[str, List[str]]) -> List[BoundaryViolation]:
        """Create violations for duplicate type definitions"""
        violations = []
        for type_name, files in type_definitions.items():
            if len(files) > 1:
                violation = DuplicateTypeViolationFactory._build_violation(type_name, files)
                violations.append(violation)
        return violations

    @staticmethod
    def _build_violation(type_name: str, files: List[str]) -> BoundaryViolation:
        """Build duplicate type violation object"""
        file_list = ", ".join(files[:2]) + ("..." if len(files) > 2 else "")
        return BoundaryViolation(
            file_path=file_list, violation_type="duplicate_type_boundary", severity="medium",
            boundary_name="NO_DUPLICATE_TYPES", actual_value=len(files), expected_value=1,
            description=f"Duplicate type '{type_name}' violates SINGLE SOURCE OF TRUTH",
            fix_suggestion=f"Consolidate '{type_name}' into shared module", impact_score=3
        )

# Integration methods for TypeBoundaryChecker
def _read_file_safely(self, filepath: str) -> Optional[str]:
    """Read file content safely, return None on error"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None

def _should_skip_test_file(self, filepath: str) -> bool:
    """Check if file should be skipped from test stub analysis"""
    skip_indicators = ['__pycache__', 'app/tests', '/tests/']
    return any(indicator in filepath for indicator in skip_indicators)

def _scan_file_for_stubs(self, filepath: str, patterns: List[tuple]) -> Optional[BoundaryViolation]:
    """Scan file for test stubs using checker"""
    checker = TestStubChecker(self.root_path)
    return checker.scan_file_for_test_stubs(filepath, patterns)

def _create_duplicate_violations(self, type_definitions: Dict[str, List[str]]) -> None:
    """Create violations for duplicate types using factory"""
    violations = DuplicateTypeViolationFactory.create_duplicate_violations(type_definitions)
    self.violations.extend(violations)

# Bind methods to TypeBoundaryChecker
TypeBoundaryChecker._read_file_safely = _read_file_safely
TypeBoundaryChecker._should_skip_test_file = _should_skip_test_file
TypeBoundaryChecker._scan_file_for_stubs = _scan_file_for_stubs
TypeBoundaryChecker._create_duplicate_violations = _create_duplicate_violations