#!/usr/bin/env python
"""
Failure Analysis - Analyzes test failure patterns and generates insights
Provides pattern matching, categorization, and recommendations for test failures
"""

import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from collections import defaultdict


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


class TestInsightGenerator:
    """Generates insights about test suite health and performance"""
    
    def __init__(self):
        self.failure_analyzer = FailurePatternAnalyzer()
    
    def generate_insights(self, test_profiles: Dict[str, Any], test_results: List[Dict] = None) -> Dict[str, Any]:
        """Generate comprehensive insights about test suite health"""
        insights = {
            "total_tests": len(test_profiles),
            "categories": defaultdict(int),
            "priority_distribution": defaultdict(int),
            "health_metrics": {},
            "problem_tests": [],
            "recommended_fixes": [],
            "performance_insights": {},
            "failure_analysis": {}
        }
        
        # Analyze test profiles
        if test_profiles:
            insights.update(self._analyze_test_profiles(test_profiles))
        
        # Analyze recent test results
        if test_results:
            insights["failure_analysis"] = self.failure_analyzer.analyze_failure_patterns(test_results)
            insights["performance_insights"] = self._analyze_performance(test_results)
        
        return insights
    
    def _analyze_test_profiles(self, test_profiles: Dict) -> Dict:
        """Analyze test profiles for health metrics"""
        categories = defaultdict(int)
        priority_distribution = defaultdict(int)
        problem_tests = []
        
        total_failure_rate = 0
        total_duration = 0
        flaky_tests = []
        
        for profile in test_profiles.values():
            categories[profile.category] += 1
            priority_distribution[getattr(profile.priority, 'name', str(profile.priority))] += 1
            
            total_failure_rate += profile.failure_rate
            total_duration += profile.avg_duration
            
            if profile.flaky_score > 0.3:
                flaky_tests.append(profile)
            
            if profile.consecutive_failures >= 3:
                problem_tests.append({
                    "name": profile.name,
                    "category": profile.category,
                    "consecutive_failures": profile.consecutive_failures,
                    "failure_rate": profile.failure_rate
                })
        
        # Sort problem tests by severity
        problem_tests.sort(key=lambda x: x["consecutive_failures"], reverse=True)
        
        # Calculate health metrics
        health_metrics = {
            "overall_failure_rate": total_failure_rate / len(test_profiles) if test_profiles else 0,
            "avg_test_duration": total_duration / len(test_profiles) if test_profiles else 0,
            "flaky_test_count": len(flaky_tests),
            "flaky_test_percentage": len(flaky_tests) / len(test_profiles) * 100 if test_profiles else 0,
            "problem_test_count": len(problem_tests)
        }
        
        # Generate recommendations
        recommended_fixes = []
        if health_metrics["overall_failure_rate"] > 0.1:
            recommended_fixes.append("High overall failure rate - review test environment and dependencies")
        
        if health_metrics["flaky_test_percentage"] > 10:
            recommended_fixes.append(f"Fix {len(flaky_tests)} flaky tests to improve reliability")
        
        if problem_tests:
            recommended_fixes.append(f"Priority: Fix {len(problem_tests)} consistently failing tests")
        
        return {
            "categories": dict(categories),
            "priority_distribution": dict(priority_distribution),
            "health_metrics": health_metrics,
            "problem_tests": problem_tests,
            "recommended_fixes": recommended_fixes
        }
    
    def _analyze_performance(self, test_results: List[Dict]) -> Dict:
        """Analyze test performance metrics"""
        if not test_results:
            return {}
        
        durations = [r.get("duration", 0) for r in test_results if r.get("duration")]
        if not durations:
            return {}
        
        durations.sort()
        
        return {
            "total_duration": sum(durations),
            "avg_duration": sum(durations) / len(durations),
            "median_duration": durations[len(durations) // 2],
            "slowest_tests": sorted(
                [(r.get("name", "unknown"), r.get("duration", 0)) 
                 for r in test_results if r.get("duration")],
                key=lambda x: x[1], reverse=True
            )[:10],
            "performance_recommendations": self._generate_performance_recommendations(test_results)
        }
    
    def _generate_performance_recommendations(self, test_results: List[Dict]) -> List[str]:
        """Generate performance-related recommendations"""
        recommendations = []
        
        # Find slow tests
        slow_tests = [r for r in test_results if r.get("duration", 0) > 30]
        if len(slow_tests) > 10:
            recommendations.append(f"Optimize {len(slow_tests)} slow tests (>30s each)")
        
        # Check for timeout issues
        timeout_tests = [r for r in test_results if r.get("status") == "timeout"]
        if timeout_tests:
            recommendations.append(f"Review {len(timeout_tests)} timeout failures - may need timeout adjustments")
        
        return recommendations


class FailureReportGenerator:
    """Generates detailed failure reports"""
    
    def generate_failure_report(self, analysis: Dict) -> str:
        """Generate a formatted failure report"""
        report = ["# Test Failure Analysis Report", ""]
        
        # Summary
        report.extend([
            f"## Summary",
            f"- Total Failures: {analysis.get('total_failures', 0)}",
            f"- Flaky Tests: {len(analysis.get('flaky_tests', []))}",
            f"- Consistent Failures: {len(analysis.get('consistent_failures', []))}",
            ""
        ])
        
        # Error Categories
        if analysis.get("error_categories"):
            report.extend(["## Error Categories", ""])
            for category, count in sorted(analysis["error_categories"].items(), key=lambda x: x[1], reverse=True):
                report.append(f"- {category.replace('_', ' ').title()}: {count}")
            report.append("")
        
        # Failing Modules
        if analysis.get("failing_modules"):
            report.extend(["## Failing Modules", ""])
            for module, count in sorted(analysis["failing_modules"].items(), key=lambda x: x[1], reverse=True):
                report.append(f"- {module}: {count} failures")
            report.append("")
        
        # Recommendations
        if analysis.get("recommended_actions"):
            report.extend(["## Recommended Actions", ""])
            for i, action in enumerate(analysis["recommended_actions"], 1):
                report.append(f"{i}. {action}")
            report.append("")
        
        return "\n".join(report)