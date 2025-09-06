#!/usr/bin/env python
"""
Test Categories - Test categorization and category definitions
Defines test categories with descriptions and properties
"""

from typing import Dict
from shared.isolated_environment import IsolatedEnvironment


class TestCategories:
    """Handles test category definitions and management"""
    
    def get_all_categories(self) -> Dict[str, Dict[str, str]]:
        """Get all test categories with descriptions"""
        categories = {}
        self._add_critical_categories(categories)
        self._add_standard_categories(categories)
        self._add_specialized_categories(categories)
        self._add_real_llm_categories(categories)
        return categories
    
    def _add_critical_categories(self, categories: Dict[str, Dict[str, str]]):
        """Add critical test categories"""
        categories.update(self._get_critical_categories())
    
    def _add_standard_categories(self, categories: Dict[str, Dict[str, str]]):
        """Add standard test categories"""
        categories.update(self._get_standard_categories())
    
    def _add_specialized_categories(self, categories: Dict[str, Dict[str, str]]):
        """Add specialized test categories"""
        categories.update(self._get_specialized_categories())
    
    def _add_real_llm_categories(self, categories: Dict[str, Dict[str, str]]):
        """Add real LLM test categories"""
        categories.update(self._get_real_llm_categories())
    
    def categorize_test_by_path(self, path_str: str) -> str:
        """Categorize a test based on its path string"""
        primary_category = self._check_primary_categories(path_str)
        if primary_category:
            return primary_category
        return self._check_secondary_categories(path_str)
    
    def _get_critical_categories(self) -> Dict[str, Dict[str, str]]:
        """Get critical test categories"""
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
        """Get standard test categories"""
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
        """Get specialized test categories"""
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
        """Get real LLM/service test categories"""
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
    
    def _check_primary_categories(self, path_str: str) -> str:
        """Check for primary test categories"""
        if "real_" in path_str or "_real" in path_str:
            return "real_e2e"
        elif "unit" in path_str or "netra_backend/tests/core" in path_str:
            return "unit"
        elif "integration" in path_str:
            return "integration"
        elif "e2e" in path_str or "cypress" in path_str:
            return "e2e"
        elif "smoke" in path_str:
            return "smoke"
        return ""
    
    def _check_secondary_categories(self, path_str: str) -> str:
        """Check for secondary test categories"""
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