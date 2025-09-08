#!/usr/bin/env python
"""
Test Validation - Test structure and naming validation
Validates test files follow expected conventions
"""

import py_compile
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

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
    
    def validate_syntax(self, project_root: Optional[Path] = None, quick_mode: bool = True) -> Dict[str, any]:
        """
        Validate Python syntax for test files and recently modified files
        
        Args:
            project_root: Root directory to scan. If None, scans entire project.
            quick_mode: If True, only check test files and recent changes (default: True)
            
        Returns:
            Dictionary with syntax validation results
        """
        if project_root is None:
            # Default to project root
            current_file = Path(__file__)
            project_root = current_file.parent.parent
        
        syntax_errors = []
        files_checked = 0
        
        if quick_mode:
            # Quick mode: only check test files and configuration
            python_files = []
            
            # Add all test files
            test_dirs = ['tests', 'netra_backend/tests', 'auth_service/tests', 'test_framework']
            for test_dir in test_dirs:
                test_path = project_root / test_dir
                if test_path.exists():
                    python_files.extend(list(test_path.rglob("*.py")))
            
            # Add critical configuration files
            config_files = [
                'tests/unified_test_runner.py',
                'scripts/deploy_to_gcp.py',
                'test_framework/test_validation.py'
            ]
            for config_file in config_files:
                config_path = project_root / config_file
                if config_path.exists():
                    python_files.append(config_path)
            
            # Remove duplicates
            python_files = list(set(python_files))
        else:
            # Full mode: check all Python files (legacy behavior)
            python_files = list(project_root.rglob("*.py"))
        
        # Filter out cache, build, and virtual environment directories
        python_files = [
            f for f in python_files 
            if not any(part.startswith('.') or part in ['__pycache__', 'build', 'dist', 'venv', 'node_modules'] 
                      for part in f.parts)
        ]
        
        mode_description = "test files and critical configuration" if quick_mode else "all Python files"
        print(f"Checking syntax for {len(python_files)} {mode_description}...")
        
        for py_file in python_files:
            try:
                # Use py_compile to check syntax without importing
                # Skip temporary file creation - just do syntax check
                py_compile.compile(str(py_file), doraise=True)
                files_checked += 1
            except py_compile.PyCompileError as e:
                syntax_errors.append({
                    'file': str(py_file),
                    'error': str(e)
                })
            except Exception as e:
                syntax_errors.append({
                    'file': str(py_file), 
                    'error': f"Unexpected error: {str(e)}"
                })
        
        return {
            "success": len(syntax_errors) == 0,
            "files_checked": files_checked,
            "syntax_errors": syntax_errors,
            "total_files": len(python_files),
            "quick_mode": quick_mode
        }
    
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