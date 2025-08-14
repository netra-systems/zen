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
        
        # Backend tests
        backend_test_dirs = [
            path / "app" / "tests",
            path / "tests",
            path / "integration_tests"
        ]
        
        for test_dir in backend_test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("test_*.py"):
                    category = self._categorize_test(test_file)
                    discovered[category].append(str(test_file))
        
        # Frontend tests
        frontend_test_dir = path / "frontend" / "__tests__"
        if frontend_test_dir.exists():
            for test_file in frontend_test_dir.rglob("*.test.{ts,tsx,js,jsx}"):
                discovered["frontend"].append(str(test_file))
        
        # Cypress tests
        cypress_dir = path / "frontend" / "cypress" / "e2e"
        if cypress_dir.exists():
            for test_file in cypress_dir.rglob("*.cy.{ts,js}"):
                discovered["e2e"].append(str(test_file))
        
        return dict(discovered)
    
    def discover_backend_tests(self, path: Path = None) -> Dict[str, List[str]]:
        """Discover only backend Python tests"""
        path = path or self.project_root
        discovered = defaultdict(list)
        
        backend_test_dirs = [
            path / "app" / "tests",
            path / "tests",
            path / "integration_tests"
        ]
        
        for test_dir in backend_test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("test_*.py"):
                    category = self._categorize_test(test_file)
                    discovered[category].append(str(test_file))
        
        return dict(discovered)
    
    def discover_frontend_tests(self, path: Path = None) -> List[str]:
        """Discover frontend tests"""
        path = path or self.project_root
        frontend_tests = []
        
        # Jest/React tests
        frontend_test_dir = path / "frontend" / "__tests__"
        if frontend_test_dir.exists():
            for test_file in frontend_test_dir.rglob("*.test.{ts,tsx,js,jsx}"):
                frontend_tests.append(str(test_file))
        
        # Tests co-located with components
        frontend_src_dir = path / "frontend"
        if frontend_src_dir.exists():
            for test_file in frontend_src_dir.rglob("*.test.{ts,tsx,js,jsx}"):
                if "__tests__" not in str(test_file):  # Avoid duplicates
                    frontend_tests.append(str(test_file))
        
        return frontend_tests
    
    def discover_e2e_tests(self, path: Path = None) -> List[str]:
        """Discover E2E tests"""
        path = path or self.project_root
        e2e_tests = []
        
        # Cypress tests
        cypress_dir = path / "frontend" / "cypress" / "e2e"
        if cypress_dir.exists():
            for test_file in cypress_dir.rglob("*.cy.{ts,js}"):
                e2e_tests.append(str(test_file))
        
        # Playwright tests (if they exist)
        playwright_dir = path / "tests" / "e2e"
        if playwright_dir.exists():
            for test_file in playwright_dir.rglob("*.spec.{ts,js}"):
                e2e_tests.append(str(test_file))
        
        return e2e_tests
    
    def _categorize_test(self, test_path: Path) -> str:
        """Categorize a test based on its path and name"""
        path_str = str(test_path).lower()
        
        # Check for specific patterns
        if "unit" in path_str or "app/tests/core" in path_str:
            return "unit"
        elif "integration" in path_str:
            return "integration"
        elif "e2e" in path_str or "cypress" in path_str:
            return "e2e"
        elif "smoke" in path_str:
            return "smoke"
        elif "performance" in path_str or "perf" in path_str:
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
    
    def get_test_categories(self) -> Dict[str, Dict[str, str]]:
        """Get available test categories with descriptions"""
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
            },
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
            "frontend": {
                "description": "React component and UI tests",
                "priority": "medium",
                "timeout": "5m"
            },
            "other": {
                "description": "Miscellaneous tests",
                "priority": "low",
                "timeout": "5m"
            }
        }
    
    def get_tests_by_category(self, category: str) -> List[str]:
        """Get all tests in a specific category"""
        all_tests = self.discover_tests()
        return all_tests.get(category, [])
    
    def get_tests_by_pattern(self, pattern: str) -> List[str]:
        """Find tests matching a pattern"""
        all_tests = self.discover_tests()
        matching_tests = []
        
        for category, tests in all_tests.items():
            for test in tests:
                if pattern.lower() in test.lower():
                    matching_tests.append(test)
        
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
            for test_path in tests:
                path = Path(test_path)
                
                # Check naming conventions
                if category != "frontend" and category != "e2e":
                    if not path.name.startswith("test_"):
                        issues["naming"].append(f"{test_path}: Should start with 'test_'")
                
                # Check for empty test files
                try:
                    if path.stat().st_size == 0:
                        issues["empty_files"].append(test_path)
                except FileNotFoundError:
                    issues["missing_files"].append(test_path)
        
        return dict(issues)