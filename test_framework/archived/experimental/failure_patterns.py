#!/usr/bin/env python
"""
Failure Patterns - Core failure pattern analysis and categorization
Provides pattern matching and basic failure analysis
"""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class FailurePatternAnalyzer:
    """Analyzes test failure patterns to identify common issues"""
    
    def __init__(self):
        self.common_error_patterns = self._load_error_patterns()
    
    def _load_error_patterns(self) -> Dict[str, str]:
        """Load common error patterns for classification"""
        return {
            r"ImportError|ModuleNotFoundError": "import_error",
            r"AttributeError.*has no attribute": "attribute_error",
            r"TypeError.*arguments?": "type_error",
            r"AssertionError": "assertion_error",
            r"TimeoutError|timed? out": "timeout_error",
            r"ConnectionError|ConnectionRefused": "connection_error",
            r"PermissionError|Access.*denied": "permission_error",
            r"KeyError": "key_error",
            r"ValueError": "value_error",
            r"IndexError|list index out of range": "index_error",
            r"ZeroDivisionError": "zero_division_error",
            r"MemoryError|out of memory": "memory_error",
            r"mock.*Mock.*assert": "mock_assertion_error",
            r"fixture.*not found": "fixture_error",
            r"database.*connection": "database_error",
            r"redis.*connection": "redis_error",
            r"websocket.*closed": "websocket_error",
            r"HTTP.*[45]\d\d": "http_error",
            r"SSL.*certificate": "ssl_error",
            r"JSON.*decode": "json_error"
        }
    
    def analyze_failure_patterns(self, test_results: List[Dict]) -> Dict[str, Any]:
        """Analyze failure patterns to identify common issues"""
        analysis = {
            "total_failures": 0,
            "error_categories": defaultdict(int),
            "failing_modules": defaultdict(int),
            "time_based_failures": defaultdict(int),
            "flaky_tests": [],
            "consistent_failures": [],
            "regression_candidates": [],
            "recommended_actions": []
        }
        
        for result in test_results:
            if result.get("status") in ["failed", "error"]:
                analysis["total_failures"] += 1
                
                # Categorize error
                error_msg = result.get("error", "")
                for pattern, category in self.common_error_patterns.items():
                    if re.search(pattern, error_msg, re.IGNORECASE):
                        analysis["error_categories"][category] += 1
                        break
                else:
                    analysis["error_categories"]["unknown"] += 1
                
                # Track failing modules
                test_path = result.get("path", "")
                module = self._extract_module(test_path)
                analysis["failing_modules"][module] += 1
                
                # Check time-based patterns
                timestamp = result.get("timestamp")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        hour = dt.hour
                        if hour < 6 or hour > 22:
                            analysis["time_based_failures"]["off_hours"] += 1
                        else:
                            analysis["time_based_failures"]["business_hours"] += 1
                    except (ValueError, TypeError):
                        pass
        
        # Identify flaky tests
        analysis["flaky_tests"] = self._identify_flaky_tests(test_results)
        
        # Identify consistent failures
        analysis["consistent_failures"] = self._identify_consistent_failures(test_results)
        
        # Generate recommendations
        analysis["recommended_actions"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _extract_module(self, test_path: str) -> str:
        """Extract module name from test path"""
        parts = Path(test_path).parts
        if "tests" in parts:
            idx = parts.index("tests")
            if idx + 1 < len(parts):
                return parts[idx + 1].replace("test_", "").replace(".py", "")
        return "unknown"
    
    def _identify_flaky_tests(self, test_results: List[Dict]) -> List[str]:
        """Identify tests with inconsistent results"""
        test_results_by_name = defaultdict(list)
        for result in test_results:
            test_results_by_name[result.get("name", "")].append(result.get("status"))
        
        flaky_tests = []
        for test_name, statuses in test_results_by_name.items():
            if len(set(statuses)) > 1:  # Mixed results
                flaky_tests.append(test_name)
        
        return flaky_tests
    
    def _identify_consistent_failures(self, test_results: List[Dict]) -> List[str]:
        """Identify tests that consistently fail"""
        test_results_by_name = defaultdict(list)
        for result in test_results:
            test_results_by_name[result.get("name", "")].append(result.get("status"))
        
        consistent_failures = []
        for test_name, statuses in test_results_by_name.items():
            if all(s in ["failed", "error"] for s in statuses) and len(statuses) > 1:
                consistent_failures.append(test_name)
        
        return consistent_failures
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate actionable recommendations based on failure analysis"""
        recommendations = []
        
        # Check for import errors
        if analysis["error_categories"].get("import_error", 0) > 5:
            recommendations.append("Fix dependency issues - multiple import errors detected")
        
        # Check for database errors
        if analysis["error_categories"].get("database_error", 0) > 3:
            recommendations.append("Check database connectivity and migrations")
        
        # Check for timeout errors
        if analysis["error_categories"].get("timeout_error", 0) > 5:
            recommendations.append("Review test timeouts - multiple timeout failures")
        
        # Check for flaky tests
        if len(analysis["flaky_tests"]) > 10:
            recommendations.append(f"Address {len(analysis['flaky_tests'])} flaky tests - consider adding retries or fixing race conditions")
        
        # Check for consistent failures
        if len(analysis["consistent_failures"]) > 0:
            recommendations.append(f"Priority: Fix {len(analysis['consistent_failures'])} consistently failing tests")
        
        # Check for module concentration
        if analysis["failing_modules"]:
            top_failing_module = max(analysis["failing_modules"].items(), key=lambda x: x[1])[0]
            if analysis["failing_modules"][top_failing_module] > 5:
                recommendations.append(f"Focus on {top_failing_module} module - highest failure concentration")
        
        # Check for connection-related errors
        connection_errors = (
            analysis["error_categories"].get("connection_error", 0) +
            analysis["error_categories"].get("database_error", 0) +
            analysis["error_categories"].get("redis_error", 0)
        )
        if connection_errors > 5:
            recommendations.append("Check external service connectivity (database, Redis, etc.)")
        
        return recommendations