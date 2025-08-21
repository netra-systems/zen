#!/usr/bin/env python
"""
Test Scanners - Test file discovery and scanning logic
Handles scanning for different types of test files
"""

from collections import defaultdict
from pathlib import Path
from typing import List


class TestScanners:
    """Handles scanning for different types of test files"""
    
    def discover_backend_tests(self, path: Path, discovered: defaultdict):
        """Discover backend tests and add to discovered dict"""
        backend_test_dirs = self._get_backend_test_directories(path)
        self._scan_backend_test_directories(backend_test_dirs, discovered)
    
    def discover_frontend_tests(self, path: Path, discovered: defaultdict):
        """Discover frontend tests and add to discovered dict"""
        # Check __tests__ directory
        frontend_test_dir = path / "frontend" / "__tests__"
        if frontend_test_dir.exists():
            self._scan_jest_test_directory(frontend_test_dir, discovered)
        
        # Check for co-located tests in frontend directory
        frontend_dir = path / "frontend"
        if frontend_dir.exists():
            self._scan_colocated_frontend_tests(frontend_dir, discovered)
    
    def discover_cypress_tests(self, path: Path, discovered: defaultdict):
        """Discover Cypress tests and add to discovered dict"""
        cypress_dir = path / "frontend" / "cypress" / "e2e"
        if cypress_dir.exists():
            self._scan_cypress_test_directory(cypress_dir, discovered)
    
    def collect_frontend_tests(self, path: Path, frontend_tests: List[str]):
        """Collect frontend test files"""
        self._add_jest_tests(path, frontend_tests)
        self._add_colocated_tests(path, frontend_tests)
    
    def collect_e2e_tests(self, path: Path, e2e_tests: List[str]):
        """Collect end-to-end test files"""
        self._add_cypress_tests(path, e2e_tests)
        self._add_playwright_tests(path, e2e_tests)
    
    def _get_backend_test_directories(self, path: Path) -> List[Path]:
        """Return backend test directories to scan"""
        test_dirs = []
        
        # Primary location: netra_backend/tests
        netra_backend_tests = path / "netra_backend" / "tests"
        if netra_backend_tests.exists():
            test_dirs.append(netra_backend_tests)
        
        # Legacy location: app/tests (kept for backward compatibility)
        app_tests = path / "app" / "tests"
        if app_tests.exists():
            test_dirs.append(app_tests)
        
        # Additional location: tests (root level tests)
        root_tests = path / "tests"
        if root_tests.exists():
            test_dirs.append(root_tests)
        
        return test_dirs
    
    def _scan_backend_test_directories(self, test_dirs: List[Path], discovered: defaultdict):
        """Scan backend test directories for Python test files"""
        from .test_categories import TestCategories
        categories = TestCategories()
        
        for test_dir in test_dirs:
            for test_file in test_dir.rglob("test_*.py"):
                path_str = str(test_file).lower()
                category = categories.categorize_test_by_path(path_str)
                discovered[category].append(str(test_file))
    
    def _scan_jest_test_directory(self, test_dir: Path, discovered: defaultdict):
        """Scan Jest test directory for frontend tests"""
        for ext in ["ts", "tsx", "js", "jsx"]:
            for test_file in test_dir.rglob(f"*.test.{ext}"):
                discovered["frontend"].append(str(test_file))
            for test_file in test_dir.rglob(f"*.spec.{ext}"):
                discovered["frontend"].append(str(test_file))
    
    def _scan_colocated_frontend_tests(self, frontend_dir: Path, discovered: defaultdict):
        """Scan for co-located frontend tests"""
        for ext in ["ts", "tsx", "js", "jsx"]:
            for test_file in frontend_dir.rglob(f"*.test.{ext}"):
                if self._is_valid_colocated_test(test_file):
                    discovered["frontend"].append(str(test_file))
    
    def _scan_cypress_test_directory(self, cypress_dir: Path, discovered: defaultdict):
        """Scan Cypress test directory for e2e tests"""
        for ext in ["ts", "js"]:
            for test_file in cypress_dir.rglob(f"*.cy.{ext}"):
                discovered["e2e"].append(str(test_file))
            for test_file in cypress_dir.rglob(f"*.spec.{ext}"):
                discovered["e2e"].append(str(test_file))
    
    def _is_valid_colocated_test(self, test_file: Path) -> bool:
        """Check if colocated test file is valid"""
        return "__tests__" not in str(test_file) and "node_modules" not in str(test_file)
    
    def _add_jest_tests(self, path: Path, frontend_tests: List[str]):
        """Add Jest/React tests to frontend tests list"""
        frontend_test_dir = path / "frontend" / "__tests__"
        if frontend_test_dir.exists():
            for test_file in frontend_test_dir.rglob("*.test.{ts,tsx,js,jsx}"):
                frontend_tests.append(str(test_file))
    
    def _add_colocated_tests(self, path: Path, frontend_tests: List[str]):
        """Add co-located component tests to frontend tests list"""
        frontend_src_dir = path / "frontend"
        if frontend_src_dir.exists():
            for test_file in frontend_src_dir.rglob("*.test.{ts,tsx,js,jsx}"):
                if "__tests__" not in str(test_file):  # Avoid duplicates
                    frontend_tests.append(str(test_file))
    
    def _add_cypress_tests(self, path: Path, e2e_tests: List[str]):
        """Add Cypress tests to e2e tests list"""
        cypress_dir = path / "frontend" / "cypress" / "e2e"
        if cypress_dir.exists():
            for test_file in cypress_dir.rglob("*.cy.{ts,js}"):
                e2e_tests.append(str(test_file))
    
    def _add_playwright_tests(self, path: Path, e2e_tests: List[str]):
        """Add Playwright tests to e2e tests list"""
        playwright_dir = path / "tests" / "e2e"
        if playwright_dir.exists():
            for test_file in playwright_dir.rglob("*.spec.{ts,js}"):
                e2e_tests.append(str(test_file))