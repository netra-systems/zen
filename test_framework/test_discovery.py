#!/usr/bin/env python
"""
Test Discovery - Test file discovery and categorization logic
Finds and categorizes tests across the project structure
"""

from pathlib import Path
from typing import Dict, List
from collections import defaultdict


class TestDiscovery:
    """Handles test discovery and categorization across the project"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def discover_tests(self, path: Path = None) -> Dict[str, List[str]]:
        """Discover all tests in the project"""
        path = path or self.project_root
        discovered = defaultdict(list)
        
        self._discover_backend_tests_into(path, discovered)
        self._discover_frontend_tests_into(path, discovered)
        self._discover_cypress_tests_into(path, discovered)
        
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
        
        self._add_jest_tests(path, frontend_tests)
        self._add_colocated_tests(path, frontend_tests)
        
        return frontend_tests
    
    def discover_e2e_tests(self, path: Path = None) -> List[str]:
        """Discover E2E tests"""
        path = path or self.project_root
        e2e_tests = []
        
        self._add_cypress_tests(path, e2e_tests)
        self._add_playwright_tests(path, e2e_tests)
        
        return e2e_tests
    
    def _categorize_test(self, test_path: Path) -> str:
        """Categorize a test based on its path and name"""
        path_str = str(test_path).lower()
        
        category = self._check_primary_categories(path_str)
        if category:
            return category
        
        return self._check_secondary_categories(path_str)
    
    def get_test_categories(self) -> Dict[str, Dict[str, str]]:
        """Get available test categories with descriptions"""
        categories = {}
        categories.update(self._get_critical_categories())
        categories.update(self._get_standard_categories())
        categories.update(self._get_specialized_categories())
        
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
        issues = defaultdict(list)
        all_tests = self.discover_tests()
        
        for category, tests in all_tests.items():
            self._validate_category_tests(category, tests, issues)
        
        return dict(issues)