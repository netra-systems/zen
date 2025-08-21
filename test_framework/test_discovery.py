#!/usr/bin/env python
"""
Test Discovery - Test file discovery and categorization logic
Finds and categorizes tests across the project structure
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from .test_categories import TestCategories
from .test_scanners import TestScanners
from .test_validation import TestValidation


class TestDiscovery:
    """Handles test discovery and categorization across the project"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.categories = TestCategories()
        self.scanners = TestScanners()
        self.validation = TestValidation()
    
    def discover_tests(self, path: Path = None) -> Dict[str, List[str]]:
        """Discover all tests in the project"""
        path = path or self.project_root
        discovered = defaultdict(list)
        self._populate_discovered_tests(path, discovered)
        return dict(discovered)
    
    def discover_backend_tests(self, path: Path = None) -> Dict[str, List[str]]:
        """Discover only backend Python tests"""
        path = path or self.project_root
        discovered = defaultdict(list)
        self._discover_backend_tests_into(path, discovered)
        return dict(discovered)
    
    def discover_frontend_tests(self, path: Path = None) -> List[str]:
        """Discover frontend tests"""
        path = path or self.project_root
        frontend_tests = []
        self._collect_frontend_tests(path, frontend_tests)
        return frontend_tests
    
    def discover_e2e_tests(self, path: Path = None) -> List[str]:
        """Discover E2E tests"""
        path = path or self.project_root
        e2e_tests = []
        self._collect_e2e_tests(path, e2e_tests)
        return e2e_tests
    
    def get_test_categories(self) -> Dict[str, Dict[str, str]]:
        """Get available test categories with descriptions"""
        categories = {}
        self._populate_all_categories(categories)
        return categories
    
    def get_tests_by_category(self, category: str) -> List[str]:
        """Get all tests in a specific category"""
        all_tests = self.discover_tests()
        return all_tests.get(category, [])
    
    def get_tests_by_pattern(self, pattern: str) -> List[str]:
        """Find tests matching a pattern"""
        all_tests = self.discover_tests()
        matching_tests = []
        pattern_lower = pattern.lower()
        self._collect_matching_tests(all_tests, pattern_lower, matching_tests)
        return matching_tests
    
    def get_test_count_by_category(self) -> Dict[str, int]:
        """Get count of tests per category"""
        all_tests = self.discover_tests()
        return {category: len(tests) for category, tests in all_tests.items()}
    
    def validate_test_structure(self) -> Dict[str, List[str]]:
        """Validate that tests follow expected structure"""
        all_tests = self.discover_tests()
        return self.validation.validate_test_structure(all_tests)
    
    def _categorize_test(self, test_path: Path) -> str:
        """Categorize a test based on its path and name"""
        path_str = str(test_path).lower()
        return self.categories.categorize_test_by_path(path_str)
    
    def _populate_discovered_tests(self, path: Path, discovered: defaultdict):
        """Discover and categorize tests from the project"""
        self._discover_backend_tests_into(path, discovered)
        self._discover_frontend_tests_into(path, discovered)
        self._discover_cypress_tests_into(path, discovered)
    
    def _populate_all_categories(self, categories: Dict[str, Dict[str, str]]):
        """Populate all test categories with descriptions"""
        categories.update(self.categories.get_all_categories())
    
    def _get_backend_test_directories(self, path: Path) -> List[Path]:
        """Return backend test directories to scan"""
        return self.scanners._get_backend_test_directories(path)
    
    def _scan_backend_test_directories(self, test_dirs: List[Path], discovered: defaultdict):
        """Scan backend test directories for Python test files"""
        self.scanners._scan_backend_test_directories(test_dirs, discovered)
    
    def _collect_frontend_tests(self, path: Path, frontend_tests: List[str]):
        """Collect frontend test files"""
        self.scanners.collect_frontend_tests(path, frontend_tests)
    
    def _collect_e2e_tests(self, path: Path, e2e_tests: List[str]):
        """Collect end-to-end test files"""
        self.scanners.collect_e2e_tests(path, e2e_tests)
    
    def _discover_backend_tests_into(self, path: Path, discovered: defaultdict):
        """Discover backend tests and add to discovered dict"""
        backend_test_dirs = self._get_backend_test_directories(path)
        self._scan_backend_test_directories(backend_test_dirs, discovered)
    
    def _discover_frontend_tests_into(self, path: Path, discovered: defaultdict):
        """Discover frontend tests and add to discovered dict"""
        self.scanners.discover_frontend_tests(path, discovered)
    
    def _discover_cypress_tests_into(self, path: Path, discovered: defaultdict):
        """Discover Cypress tests and add to discovered dict"""
        self.scanners.discover_cypress_tests(path, discovered)
    
    def _collect_matching_tests(self, all_tests: Dict, pattern_lower: str, matching_tests: List[str]):
        """Collect tests matching the pattern"""
        for category, tests in all_tests.items():
            for test in tests:
                if pattern_lower in test.lower():
                    matching_tests.append(test)