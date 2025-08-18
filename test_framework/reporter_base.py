#!/usr/bin/env python
"""Base reporter functionality and constants."""

from pathlib import Path
from typing import Dict

class ReporterConstants:
    """Test reporting constants and configurations."""
    
    # ALL test levels from test_config.py
    TEST_LEVELS = [
        "smoke", "unit", "agents", "integration", "critical",
        "comprehensive", "comprehensive-backend", "comprehensive-frontend",
        "comprehensive-core", "comprehensive-agents", "comprehensive-websocket",
        "comprehensive-database", "comprehensive-api", "all",
        "real_e2e", "real_services", "mock_only"
    ]
    
    # Complete test category mapping with expected counts
    TEST_CATEGORIES = {
        "smoke": {"description": "Quick smoke tests", "expected": 10},
        "unit": {"description": "Unit tests", "expected": 450},
        "integration": {"description": "Integration tests", "expected": 60},
        "critical": {"description": "Critical path tests", "expected": 20},
        "agents": {"description": "Agent tests", "expected": 45},
        "websocket": {"description": "WebSocket tests", "expected": 25},
        "database": {"description": "Database tests", "expected": 35},
        "api": {"description": "API tests", "expected": 50},
        "e2e": {"description": "End-to-end tests", "expected": 20},
        "real_services": {"description": "Real service tests", "expected": 15},
        "auth": {"description": "Authentication tests", "expected": 30},
        "corpus": {"description": "Corpus management tests", "expected": 20},
        "synthetic_data": {"description": "Synthetic data tests", "expected": 25},
        "metrics": {"description": "Metrics tests", "expected": 15},
        "frontend": {"description": "Frontend tests", "expected": 40},
        "comprehensive": {"description": "Full comprehensive suite", "expected": 500}
    }
    
    @staticmethod
    def get_default_structure() -> Dict:
        """Get default test results structure."""
        return {
            "metadata": {
                "version": "2.0",
                "last_update": None,
                "total_runs": 0
            },
            "current_state": {
                "overall_status": "unknown",
                "last_run_level": None,
                "last_run_time": None,
                "last_exit_code": None
            },
            "known_test_counts": {},  # Persistent test counts by level/component
            "category_results": {},    # Results by category
            "component_results": {},   # Results by component (backend/frontend/e2e)
            "failing_tests": [],       # Currently failing tests
            "test_history": [],        # Last 20 runs
            "statistics": {
                "total_tests_known": 0,
                "total_tests_run": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_skipped": 0,
                "pass_rate": 0.0
            }
        }