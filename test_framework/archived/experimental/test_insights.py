#!/usr/bin/env python
"""
Test Insights - Generates insights about test suite health and performance
Provides comprehensive analysis and performance insights for test suites
"""

from collections import defaultdict
from typing import Any, Dict, List

from test_framework.archived.experimental.failure_patterns import FailurePatternAnalyzer


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