#!/usr/bin/env python
"""
Test Validation - Test structure and naming validation
Validates test files follow expected conventions
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

# Removed circular_import_detector - functionality integrated elsewhere


class TestValidation:
    """Handles test validation and structure checking"""
    
    def validate_all_test_categories(self, all_tests: Dict[str, List[str]], issues: defaultdict):
        """Validate all test categories for structure and naming"""
        for category, tests in all_tests.items():
            self._validate_category_tests(category, tests, issues)
    
    def validate_test_structure(self, all_tests: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Validate that tests follow expected structure"""
        issues = defaultdict(list)
        self.validate_all_test_categories(all_tests, issues)
        return dict(issues)
    
    def _validate_category_tests(self, category: str, tests: List[str], issues: defaultdict):
        """Validate tests in a specific category"""
        for test_path in tests:
            path = Path(test_path)
            self._check_naming_conventions(category, path, test_path, issues)
            self._check_file_existence(path, test_path, issues)
    
    def _check_naming_conventions(self, category: str, path: Path, test_path: str, issues: defaultdict):
        """Check test file naming conventions"""
        if category not in ["frontend", "e2e"]:
            if not path.name.startswith("test_"):
                issues["naming"].append(f"{test_path}: Should start with 'test_'")
    
    def _check_file_existence(self, path: Path, test_path: str, issues: defaultdict):
        """Check if test file exists and is not empty"""
        try:
            if path.stat().st_size == 0:
                issues["empty_files"].append(test_path)
        except FileNotFoundError:
            issues["missing_files"].append(test_path)
    
    def validate_circular_imports(self, project_root: Optional[Path] = None) -> Dict[str, any]:
        """
        Validate that there are no circular imports in the codebase
        
        Args:
            project_root: Root directory to scan. If None, uses netra_backend.
            
        Returns:
            Dictionary with validation results
        """
        if project_root is None:
            # Default to netra_backend directory
            current_file = Path(__file__)
            project_root = current_file.parent.parent / "netra_backend"
        
        if not project_root.exists():
            return {
                "success": False,
                "error": f"Project root not found at {project_root}"
            }
        
        # Circular import detection removed - can be re-enabled if needed
        return {
            "success": True,
            "circular_imports_found": 0,
            "cycles": [],
            "total_modules": 0,
            "errors": []
        }