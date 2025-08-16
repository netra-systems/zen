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
    
    def _categorize_test(self, test_path: Path) -> str:
        """Categorize a test based on its path and name"""
        path_str = str(test_path).lower()
        primary_category = self._check_primary_categories(path_str)
        if primary_category:
            return primary_category
        return self._check_secondary_categories(path_str)
    
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
        issues = defaultdict(list)
        all_tests = self.discover_tests()
        self._validate_all_test_categories(all_tests, issues)
        return dict(issues)
    
    def _discover_backend_tests_into(self, path: Path, discovered: defaultdict):
        """Discover backend tests and add to discovered dict."""
        backend_test_dirs = self._get_backend_test_directories(path)
        self._scan_backend_test_directories(backend_test_dirs, discovered)
    
    def _discover_frontend_tests_into(self, path: Path, discovered: defaultdict):
        """Discover frontend tests and add to discovered dict."""
        # Check __tests__ directory
        frontend_test_dir = path / "frontend" / "__tests__"
        if frontend_test_dir.exists():
            for ext in ["ts", "tsx", "js", "jsx"]:
                for test_file in frontend_test_dir.rglob(f"*.test.{ext}"):
                    discovered["frontend"].append(str(test_file))
                for test_file in frontend_test_dir.rglob(f"*.spec.{ext}"):
                    discovered["frontend"].append(str(test_file))
        
        # Check for co-located tests in frontend directory
        frontend_dir = path / "frontend"
        if frontend_dir.exists():
            for ext in ["ts", "tsx", "js", "jsx"]:
                for test_file in frontend_dir.rglob(f"*.test.{ext}"):
                    if "__tests__" not in str(test_file) and "node_modules" not in str(test_file):
                        discovered["frontend"].append(str(test_file))
    
    def _discover_cypress_tests_into(self, path: Path, discovered: defaultdict):
        """Discover Cypress tests and add to discovered dict."""
        cypress_dir = path / "frontend" / "cypress" / "e2e"
        if cypress_dir.exists():
            for ext in ["ts", "js"]:
                for test_file in cypress_dir.rglob(f"*.cy.{ext}"):
                    discovered["e2e"].append(str(test_file))
                for test_file in cypress_dir.rglob(f"*.spec.{ext}"):
                    discovered["e2e"].append(str(test_file))
    
    def _add_jest_tests(self, path: Path, frontend_tests: List[str]):
        """Add Jest/React tests to frontend tests list."""
        frontend_test_dir = path / "frontend" / "__tests__"
        if frontend_test_dir.exists():
            for test_file in frontend_test_dir.rglob("*.test.{ts,tsx,js,jsx}"):
                frontend_tests.append(str(test_file))
    
    def _add_colocated_tests(self, path: Path, frontend_tests: List[str]):
        """Add co-located component tests to frontend tests list."""
        frontend_src_dir = path / "frontend"
        if frontend_src_dir.exists():
            for test_file in frontend_src_dir.rglob("*.test.{ts,tsx,js,jsx}"):
                if "__tests__" not in str(test_file):  # Avoid duplicates
                    frontend_tests.append(str(test_file))
    
    def _add_cypress_tests(self, path: Path, e2e_tests: List[str]):
        """Add Cypress tests to e2e tests list."""
        cypress_dir = path / "frontend" / "cypress" / "e2e"
        if cypress_dir.exists():
            for test_file in cypress_dir.rglob("*.cy.{ts,js}"):
                e2e_tests.append(str(test_file))
    
    def _add_playwright_tests(self, path: Path, e2e_tests: List[str]):
        """Add Playwright tests to e2e tests list."""
        playwright_dir = path / "tests" / "e2e"
        if playwright_dir.exists():
            for test_file in playwright_dir.rglob("*.spec.{ts,js}"):
                e2e_tests.append(str(test_file))
    
    def _check_primary_categories(self, path_str: str) -> str:
        """Check for primary test categories."""
        if "real_" in path_str or "_real" in path_str:
            return "real_e2e"
        elif "unit" in path_str or "app/tests/core" in path_str:
            return "unit"
        elif "integration" in path_str:
            return "integration"
        elif "e2e" in path_str or "cypress" in path_str:
            return "e2e"
        elif "smoke" in path_str:
            return "smoke"
        return ""
    
    def _check_secondary_categories(self, path_str: str) -> str:
        """Check for secondary test categories."""
        if "performance" in path_str or "perf" in path_str:
            return "performance"
        elif "security" in path_str or "auth" in path_str:
            return "security"
        elif "websocket" in path_str or "ws_" in path_str:
            return "websocket"
        elif "database" in path_str or "db" in path_str:
            return "database"
        elif "api" in path_str or "route" in path_str:
            return "api"
        elif "agent" in path_str:
            return "agent"
        elif "llm" in path_str:
            return "llm"
        else:
            return "other"
    
    def _get_critical_categories(self) -> Dict[str, Dict[str, str]]:
        """Get critical test categories."""
        return {
            "smoke": {
                "description": "Quick validation tests for pre-commit checks",
                "priority": "critical",
                "timeout": "30s"
            },
            "unit": {
                "description": "Unit tests for individual components", 
                "priority": "high",
                "timeout": "2m"
            }
        }
    
    def _get_standard_categories(self) -> Dict[str, Dict[str, str]]:
        """Get standard test categories."""
        return {
            "integration": {
                "description": "Integration tests for feature validation",
                "priority": "medium",
                "timeout": "5m"
            },
            "e2e": {
                "description": "End-to-end user journey tests",
                "priority": "medium", 
                "timeout": "10m"
            },
            "frontend": {
                "description": "React component and UI tests",
                "priority": "medium",
                "timeout": "5m"
            }
        }
    
    def _get_specialized_categories(self) -> Dict[str, Dict[str, str]]:
        """Get specialized test categories."""
        return {
            "performance": {
                "description": "Performance and load tests",
                "priority": "low",
                "timeout": "30m"
            },
            "security": {
                "description": "Security and authentication tests",
                "priority": "high",
                "timeout": "5m"
            },
            "websocket": {
                "description": "WebSocket communication tests",
                "priority": "medium",
                "timeout": "2m"
            },
            "database": {
                "description": "Database and data persistence tests",
                "priority": "high",
                "timeout": "5m"
            },
            "api": {
                "description": "API endpoint and route tests",
                "priority": "high",
                "timeout": "5m"
            },
            "agent": {
                "description": "AI agent and workflow tests",
                "priority": "medium",
                "timeout": "10m"
            },
            "llm": {
                "description": "LLM integration and prompt tests",
                "priority": "medium",
                "timeout": "5m"
            },
            "other": {
                "description": "Miscellaneous tests",
                "priority": "low",
                "timeout": "5m"
            }
        }
    
    def _get_real_llm_categories(self) -> Dict[str, Dict[str, str]]:
        """Get real LLM/service test categories."""
        return {
            "real_e2e": {
                "description": "[REAL E2E] Tests with actual LLM calls and services",
                "priority": "critical",
                "timeout": "15m",
                "requires_llm": True
            },
            "real_services": {
                "description": "[REAL] Service integration tests",
                "priority": "high",
                "timeout": "10m",
                "requires_services": True
            }
        }
    
    def _collect_matching_tests(self, all_tests: Dict, pattern_lower: str, matching_tests: List[str]):
        """Collect tests matching the pattern."""
        for category, tests in all_tests.items():
            for test in tests:
                if pattern_lower in test.lower():
                    matching_tests.append(test)
    
    def _validate_category_tests(self, category: str, tests: List[str], issues: defaultdict):
        """Validate tests in a specific category."""
        for test_path in tests:
            path = Path(test_path)
            
            self._check_naming_conventions(category, path, test_path, issues)
            self._check_file_existence(path, test_path, issues)
    
    def _check_naming_conventions(self, category: str, path: Path, test_path: str, issues: defaultdict):
        """Check test file naming conventions."""
        if category not in ["frontend", "e2e"]:
            if not path.name.startswith("test_"):
                issues["naming"].append(f"{test_path}: Should start with 'test_'")
    
    def _check_file_existence(self, path: Path, test_path: str, issues: defaultdict):
        """Check if test file exists and is not empty."""
        try:
            if path.stat().st_size == 0:
                issues["empty_files"].append(test_path)
        except FileNotFoundError:
            issues["missing_files"].append(test_path)